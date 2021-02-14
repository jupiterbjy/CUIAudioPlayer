"""
Main CUI(TUI) interface definitions.
Currently using master branch of py_cui.

Written and ran on Python 3.9. Expects 3.8+
"""

from __future__ import annotations
from typing import TYPE_CHECKING, Callable, Mapping, Generator, Iterable, Iterator, Tuple, Any
from sys import platform
import array
import inspect
import functools
import itertools

from contextlib import contextmanager
from collections import OrderedDict
from tinytag import TinyTag
from wcwidth import wcswidth, wcwidth
import py_cui

import CompatibilityPatch
from LoggingConfigurator import logger
from SDManager import StreamManager, StreamStates
from FileWalker import PathWrapper

if TYPE_CHECKING:
    from SDManager import AudioObject
    import pathlib

try:
    # noinspection PyUnresolvedReferences
    import pretty_errors
    pretty_errors.activate()
except ImportError:
    pass

assert CompatibilityPatch


VERSION_TAG = "0.0.3a - dev"
logger.debug(f"Platform: {platform} Version: {VERSION_TAG}")


def extract_metadata(abs_file_dir):
    """
    Extracts metadata as OrderedDict.

    :param abs_file_dir: absolute location of audio file

    :return: OrderedDict[str, Any]
    """

    tag = TinyTag.get(abs_file_dir)
    filtered = sorted(((k, v) for k, v in tag.as_dict().items() if v))
    return OrderedDict(filtered)


def add_callback_patch(widget_: py_cui.widgets.Widget, callback: Callable, keypress_only=False):
    """
    Adding callback support for widget that lacks such as ScrollMenu.

    :param widget_: Any widget you want to add callback on each input events.
    :param callback: Any callables
    :param keypress_only: Decides whether to replace mouse input handler alongside with key input one.
    """

    # Sequence is _draw -> _handle_mouse_press, so patching on _draw results 1 update behind.
    # Therefore we need to patch both _handle_mouse_press and _handle_keyboard_press.

    def patch_factory(old_func):
        # fix for late binding issue: stackoverflow.com/questions/3431676
        @functools.wraps(old_func)
        def wrapper(*args, **kwargs):
            old_func(*args, **kwargs)
            callback()

        return wrapper

    setattr(widget_, "_handle_key_press", patch_factory(getattr(widget_, "_handle_key_press")))
    if not keypress_only:
        setattr(widget_, "_handle_mouse_press", patch_factory(getattr(widget_, "_handle_mouse_press")))


def meta_list_str_gen(dict_: Mapping) -> Generator[str, None, None]:
    """
    Formats metadata. Returns generator that yields 3 lines per metadata entry.

    :param dict_: Mapping containing metadata.

    :return: Generator[str, None, None]
    """

    for key, val in ((k, v) for k, v in dict_.items() if v):
        yield f"[{key}]"
        yield f":{val}"
        yield " "


def pad_actual_length(source: Iterator[str], pad: str = "\u200b") -> Tuple[str, Generator[str, None, None]]:
    """
    Determine real-displaying character length, and provide padding accordingly to match length.
    This way slicing will cut asian letters properly, not breaking tidy layouts.
    Don't expect to have 0-width characters in given string!

    :param source: Original string to be manipulated. Accepts Iterator[str], allowing lazy generator.
    :param pad: Default character to pad, default ZWSP

    :return: padding character and lazy generator for padded string
    """

    def inner_gen(source_: Iterator[str]) -> Generator[str, None, None]:
        for char in source_:
            yield char + pad if wcwidth(char) == 2 else char

    return pad, inner_gen(source)
    # https://github.com/microsoft/terminal/issues/1472
    # Windows Terminal + (Powershell/CMD) combo can't run this due to ZWSP width issue.
    # Expected to run in purely CMD / Linux Terminal. or WSL + Windows Terminal.
    # Tested on Xfce4 & CMD.


def fit_to_actual_width(text: str, length_lim: int) -> str:
    """
    Cuts given text with varying character width to fit inside given width.
    Expects that lines is short enough, will read entire lines on memory multiple times.

    :param text: Source text
    :param length_lim: length limit in 1-width characters

    :return: cut string
    """

    ellipsis_ = "..."

    # returns immediately if no action is needed
    if wcswidth(text) != len(text):

        _, padded = pad_actual_length(text)
        source = "".join(padded)
        limited = source[:length_lim]

        # if last character was 2-width, padding unicode wore off, so last 2-width character can't fit.
        # instead pad with space for consistent ellipsis position.
        if wcwidth(limited[-1]) == 2:
            limited = limited[:-1] + " "
    else:
        source = text
        limited = text[:length_lim]

    # Add ellipsis if original text was longer than given width
    if len(source) > length_lim:
        limited = limited[:length_lim - len(ellipsis_) - 1]
        limited += ellipsis_

    return limited


def fit_to_actual_width_multiline(text: str, length_lim: int) -> Generator[str, None, None]:
    """
    Cuts given text with varying character width to fit inside given width.
    Will yield multiple lines if line length exceed given length_lim.

    :param text: Source text
    :param length_lim: length limit in 1-width characters

    :return: lazy generator yielding multi-line cut strings
    """

    _, padded = pad_actual_length(text)

    def generator():
        next_line = ''
        line_size = length_lim

        while line := "".join(itertools.islice(padded, 0, line_size)):
            # Add contents of next_line, then reset line length if next_line is not empty
            if next_line:
                line = next_line + line
                next_line = ''

            # check if last text was 2-width character. If so, move it to next_line and adjust next line_size.
            if wcwidth(line[-1]) == 2:
                next_line = line[-1]
                line = line[:-1]
                line_size -= 1

            yield line

    return generator()

# ------------------------------------------------------------------


class AudioPlayer:
    """
    Main TUI Class containing UI definitions and controls.
    """

    ellipsis_ = ".."  # 3 dots 2 long
    usable_offset_y, usable_offset_x = 2, 6  # Excl. Border, Spacing of widget from abs size.

    symbols = {"play": "⏵", "pause": "⏸", "stop": "⏹"}

    # EXPECTING 5, 7 Layout!

    def __init__(self, root: py_cui.PyCUI):
        self.root_ = root

        # -- UI definitions
        # row-idx then col-idx, it's reversed x,y - reminder to self!
        self.audio_list = self.root_.add_scroll_menu("Files", 0, 0, column_span=5, row_span=3)
        self.meta_list = self.root_.add_scroll_menu("Meta", 0, 5, column_span=2, row_span=5)

        self.info_box = self.root_.add_text_box("Info", 3, 0, column_span=4)
        self.volume_slider = self.root_.add_slider("Volume", 3, 4, column_span=1, min_val=0, max_val=8, init_val=4)

        self.play_btn = self.root_.add_button("Play", 4, 0, command=self.play_cb_space_bar)
        self.stop_btn = self.root_.add_button("Stop", 4, 1, command=self.on_stop_click)
        self.reload_btn = self.root_.add_button("Reload", 4, 2, command=self.on_reload_click)

        self.prev_btn = self.root_.add_button("Reserved", 4, 3, command=lambda a=None: None)
        self.next_btn = self.root_.add_button("Next", 4, 4, command=self.on_next_track_click)

        self.clear_target = (self.audio_list, self.meta_list, self.info_box)

        # -- UI setup
        def volume_callback():
            nonlocal self
            self.stream.multiplier = self.stream.step * self.volume_slider.get_slider_value()

        add_callback_patch(self.audio_list, self.on_file_click)
        add_callback_patch(self.volume_slider, volume_callback, keypress_only=True)

        self.volume_slider.toggle_border()
        self.volume_slider.toggle_title()
        self.volume_slider.toggle_value()
        self.volume_slider.set_bar_char("█")

        # -- Key binds
        self.audio_list.add_key_command(py_cui.keys.KEY_ENTER, self.play_cb_enter)
        self.audio_list.add_key_command(py_cui.keys.KEY_SPACE, self.play_cb_space_bar)

        # -- add color rules - might be better implementing custom coloring methods, someday.
        self.audio_list.add_text_color_rule(r"[0-9 ].*" + self.symbols["play"], py_cui.WHITE_ON_YELLOW, "contains")
        self.audio_list.add_text_color_rule(r"[0-9 ].*" + self.symbols["pause"], py_cui.WHITE_ON_YELLOW, "contains")
        self.audio_list.add_text_color_rule(r"[0-9 ].*" + self.symbols["stop"], py_cui.WHITE_ON_YELLOW, "contains")
        self.audio_list.add_text_color_rule(r"DIR", py_cui.CYAN_ON_BLACK, "startswith", include_whitespace=False)
        self.info_box.add_text_color_rule("ERR:", py_cui.WHITE_ON_RED, "startswith")
        # Below don't work!
        # self.audio_list.add_text_color_rule(r"DIR", py_cui.CYAN_ON_BLACK, "startswith", match_type="regex")
        # self.audio_list.add_text_color_rule(r"►", py_cui.WHITE_ON_YELLOW, "contains")

        # -- Generator instance and states
        self.current_play_generator = None
        self.current_name_cycler = None
        self.shuffle = False

        # -- Path and stream instance
        self.stream: StreamManager = StreamManager.StreamManager(self.show_progress_wrapper(), self.play_next)
        self.path_wrapper = PathWrapper()

        # -- Initialize
        self.on_reload_click()

    # Primary callbacks

    def on_file_click(self):
        """
        Callback for clicking an item from audio_list.
        """

        if self.selected_track in self.path_wrapper.folder_list:
            self._clear_meta()
        else:
            self._update_meta()

    def on_next_track_click(self):
        """
        Callback for clicking next track button.
        """

        self.stream.stop_stream(run_finished_callback=False)

    def on_previous_track_click(self):
        """
        Callback for clicking previous button.
        """

    def on_stop_click(self):
        """
        Callback for clicking stop button.
        """

        try:
            self.stream.stop_stream()
        except (RuntimeError, FileNotFoundError):
            return

        with self._maintain_current_view():
            # revert texts
            self._refresh_list(search_files=False)
            self.mark_as_stopped(self.currently_playing)
            self.write_info("")

    def on_reload_click(self):
        """
        Callback for clicking reload button.
        """

        self.on_stop_click()

        # clear widgets

        for widget in self.clear_target:
            widget.clear()

        self.stream = StreamManager.StreamManager(self.show_progress_wrapper(), self.play_next)
        self._refresh_list(search_files=True)

    # Media control callback definitions -----------------------
    # TODO: Refactor to state machine

    def play_cb_enter(self):
        """
        Enters directory if selected item is one of them. Else will stop current track and play selected track.
        """

        if self.selected_track in self.path_wrapper.folder_list:
            self.path_wrapper.step_in(self.selected_track)
            self.on_reload_click()
        else:
            # force play audio
            with self._maintain_current_view():
                try:
                    self.stream.stop_stream()
                except RuntimeError as err:
                    logger.warning(str(err))
                except FileNotFoundError:
                    pass

                if self.play_stream():
                    self.mark_as_playing(self.currently_playing)

    def play_cb_space_bar(self):
        """
        Determine actions depending on selected item when space bar is pressed on audio list.
        Also a callback for Play Button.
        """

        with self._maintain_current_view():
            try:
                # assuming State: Paused
                self.stream.pause_stream()
                self.mark_as_paused(self.currently_playing)

            except RuntimeError:
                # State: stopped
                self.stream.start_stream()
                self.mark_as_playing(self.currently_playing)

            except FileNotFoundError:
                # State: Unloaded
                if self.play_stream():
                    self.mark_as_playing(self.currently_playing)

    def play_stream(self, audio_idx=None) -> int:
        """
        Load audio and starts audio stream. Returns True if successful.

        :param audio_idx: If not None, will play given index of track instead
        """

        if not audio_idx:
            audio_idx = self.selected_idx

        try:
            self.stream.load_stream(self.path_wrapper[audio_idx])
        except IndexError:
            logger.debug(f"Invalid idx: {audio_idx} / {len(self.path_wrapper)}")
            return False

        except RuntimeError as err:
            msg = f"ERR: {str(err).split(':')[-1]}"
            logger.warning(msg)
            self.write_info(msg)
            return False

        self._refresh_list(search_files=False)
        self.stream.start_stream()
        self.init_playlist()

        return True

    def _refresh_list(self, search_files=True):
        """
        Refresh directory contents. If search_files is True, will also update cached files list.
        Will separate this after changing list generating method to use internal item list of ScrollWidget.

        :param search_files: Flag whether to update cached files list
        """

        self.audio_list.clear()

        if search_files:
            self.path_wrapper.refresh_list()

        digits = len(str(len(self.path_wrapper.audio_file_list))) + 2

        def folder_gen():
            format_ = f"{('DIR'.ljust(digits))[:digits]}| "
            yield format_ + ".."
            for dir_n in itertools.islice(self.path_wrapper.folder_list, 1, None):
                yield format_ + str(dir_n.name)

        def audio_gen():
            for idx, file_dir in enumerate(self.path_wrapper.audio_file_list):
                yield f"{str(idx).center(digits)}| {file_dir.name}"

        self.write_audio_list(itertools.chain(folder_gen(), audio_gen()))
        self.write_info(f"Found {len(self.path_wrapper.audio_file_list)} file(s).")
        self.audio_list.set_title(f"Audio List - "
                                  f"{len(self.path_wrapper.audio_file_list)} track(s)")

    def _update_meta(self):
        """
        Updates metadata to show selected item.
        """

        ordered = extract_metadata(self.selected_track)
        self.write_meta_list(meta_list_str_gen(ordered), wrap_line=True)

    def _clear_meta(self):
        """
        Clears meta list. Unified interface purpose.
        """

        self.meta_list.clear()

    # Implementation / helper / wrappers -----------------------

    def write_info(self, text: str):
        """
        Writes text to info TextBox.

        :param text: text to write on TextBox
        """

        if text:
            # Will have hard time to implement cycling texts.
            fit_text = fit_to_actual_width(str(text), self._get_absolute_size(self.info_box)[-1])
            self.info_box.set_text(fit_text)
        else:
            self.info_box.clear()
            # Sometimes you just want to unify interfaces.

    def _write_to_scroll_widget(self, lines: Iterable, widget: py_cui.widgets.ScrollMenu, wrap_line=False):
        """
        Internal function that handles writing on scroll widget.

        :param lines: lines to write on audio_list
        :param widget: ScrollMenu Widget to write on
        """

        widget.clear()
        offset = -1
        _, usable_x = self._get_absolute_size(widget)

        if wrap_line:
            def wrapper_gen():
                for source_line in lines:
                    yield from fit_to_actual_width_multiline(source_line, usable_x + offset)

            for line in wrapper_gen():
                widget.add_item(line)
        else:
            for line_ in lines:
                widget.add_item(fit_to_actual_width(line_, usable_x + offset))

    def write_meta_list(self, lines: Iterable, wrap_line=False):
        """
        writes to the meta_list.

        :param lines: lines to write on audio_list
        :param wrap_line: If True, instead of shortening line it will write on multiple lines.
        """

        self._write_to_scroll_widget(lines, self.meta_list, wrap_line)

    def write_audio_list(self, lines: Iterable):
        """
        writes to the audio_list.

        :param lines: lines to write on audio_list
        """

        self._write_to_scroll_widget(lines, self.audio_list)

    def _mark_target(self, track_idx, search_target: str, replace_target: str):
        """
        internal function that changes search_target in line at index to replace_target.

        :param track_idx: index of item to mark
        :param search_target: string to search
        :param replace_target: string to replace with
        """

        source = self.audio_list.get_item_list()
        source[track_idx] = source[track_idx].replace(search_target, replace_target)
        self.write_audio_list(source)

    def mark_as_playing(self, track_idx):
        """
        Set line at given index to playing state

        :param track_idx: index of item to mark
        """

        # Mark the track on the audio list, and initialize name cycling generator
        if self.stream.stream_state == StreamStates.StreamStoppedState:
            self._mark_target(track_idx, self.symbols["stop"], self.symbols["play"])
        else:
            self._mark_target(track_idx, "|", self.symbols["play"])

    def mark_as_paused(self, track_idx):
        """
        Set line at given index to paused state

        :param track_idx: index of item to mark
        """

        if self.stream.stream_state == StreamStates.StreamPausedState:
            self._mark_target(track_idx, self.symbols["play"], self.symbols["pause"])
        else:
            self._mark_target(track_idx, self.symbols["pause"], self.symbols["play"])
            # This fits more to mark_as_playing, but consequences does not allow to do so, for now.

    def mark_as_stopped(self, track_idx):
        """
        Set line at given index to stopped state

        :param track_idx: index of item to mark
        """

        if self.stream.stream_state == StreamStates.StreamPausedState:
            self._mark_target(track_idx, self.symbols["pause"], self.symbols["stop"])
        else:
            self._mark_target(track_idx, self.symbols["play"], self.symbols["stop"])

    def show_progress_wrapper(self) -> Callable[[AudioObject.AudioInfo, Any], None]:
        """
        Wrapper for function that handles progress. Returning callable is meant to run in sounddevice callback.

        :return:
        """

        def digit(int_):
            return len(str(int_))

        def show_progress(audio_info: AudioObject.AudioInfo, current_frame):
            # counting in some marginal errors of mismatching frames and total frames count.

            file_name = title if (title := audio_info.title) else self.path_wrapper[self.currently_playing].name
            max_frame = audio_info.total_frame
            duration = audio_info.duration_tag
            format_specifier = f"0{digit(duration)}.1f"

            self.write_info(f"[{current_frame * duration / max_frame:{format_specifier}}/{duration}] "
                            f"Playing now - {file_name}")

        return show_progress

    # Playlist control callback --------------------------------

    def init_playlist(self):
        """
        Create itertools.cycle generator that acts as a playlist
        """

        # Shuffling is harder than imagined!
        # https://engineering.atspotify.com/2014/02/28/how-to-shuffle-songs/

        cycle_gen = itertools.cycle(array.array('i', (n for n in range(len(self.path_wrapper.audio_file_list)))))
        for _ in range(self.currently_playing + 1):
            next(cycle_gen)

        self.current_play_generator = cycle_gen
        logger.debug("Initialized playlist generator.")

    def play_next(self):
        """
        Play next track. Called by finished callback of sounddevice when conditions are met.
        """

        logger.debug(f"Condition: {self.stream.stop_flag}")

        if not self.stream.stop_flag:
            try:
                next_ = next(self.current_play_generator)
            except TypeError:
                self.init_playlist()
                next_ = next(self.current_play_generator)

            logger.debug(f"Playing Next - {next_}")

            with self._maintain_current_view():
                if not self.play_stream(next_):
                    logger.warning("Error playing next track. Moving on.")
                    self.play_next()
                else:
                    self.mark_as_playing(self.currently_playing)

    # Helper functions -----------------------------------------

    def _get_absolute_size(self, widget: py_cui.widgets.Widget) -> Tuple[int, int]:
        """
        Get absolute dimensions of widget including borders.

        :param widget: widget instance to get dimensions of
        :return: y-height and x-height
        """

        abs_y, abs_x = widget.get_absolute_dimensions()
        return abs_y - self.usable_offset_y, abs_x - self.usable_offset_x

    @property
    def selected_idx(self) -> int:
        """
        Returns index of selected track. Convenient method.

        :return: index of selected track.
        """

        return self.audio_list.get_selected_item_index()

    @property
    def selected_track(self) -> pathlib.Path:
        """
        Returns name of selected track. Convenient method.

        :return: Path object representing selected audio file.
        """

        return self.path_wrapper[self.selected_idx]

    @property
    def currently_playing(self) -> int:
        """
        Returns index of currently played track. Currently using slow method for simplicity.

        :return: index of played file
        """

        file_name = self.stream.audio_info.loaded_data.name
        return self.path_wrapper.index(file_name)

    @contextmanager
    def _maintain_current_view(self):
        """
        Remembers indices of both `selected / visible top item` and restores it.
        Will not be necessary when directly manipulating ScrollWidget's internal item list.
        """

        current_idx = self.audio_list.get_selected_item_index()
        visible_idx = self.audio_list._top_view
        try:
            yield
        finally:
            self.audio_list.set_selected_item_index(current_idx)
            self.audio_list._top_view = visible_idx


def draw_player():
    """
    TUI driver
    """

    root = py_cui.PyCUI(5, 7)
    root.set_title(f"CUI Audio Player - v{VERSION_TAG}")
    root.set_widget_border_characters("╔", "╗", "╚", "╝", "═", "║")
    root.set_refresh_timeout(0.1)
    # this don't have to be a second. Might be an example of downside of ABC

    player_ref = AudioPlayer(root)
    assert player_ref
    # Preventing unused variable check

    root.start()


def main():
    """
    Interface purpose wrapper
    """

    draw_player()


if __name__ == '__main__':
    main()
