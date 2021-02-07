import sounddevice as sd
import py_cui
import array
import pathlib
import functools
import itertools
from contextlib import contextmanager
from collections import OrderedDict
from tinytag import TinyTag
from wcwidth import wcswidth, wcwidth
from sys import platform
from typing import Callable, Mapping, Generator, Iterable, Tuple

from LoggingConfigurator import logger
import CompatibilityPatch
from SDManager import StreamManager, StreamStates
from FileWalker import PathWrapper

try:
    # noinspection PyUnresolvedReferences
    import pretty_errors
    pretty_errors.activate()
except ImportError:
    pass

assert CompatibilityPatch


VERSION_TAG = "0.0.3a - dev"
WINDOWS = platform == 'win32'


def extract_metadata(abs_file_dir):
    tag = TinyTag.get(abs_file_dir)
    filtered = sorted(((k, v) for k, v in tag.as_dict().items() if v))
    return OrderedDict(filtered)


def add_callback_patch(widget_: py_cui.widgets.Widget, callback: Callable):
    """
    Adding callback support for widget that lacks such as ScrollMenu.

    :param widget_: Any widget you want to add callback on each input events.
    :param callback: Any callables

    :return: None
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

    for target in ("_handle_key_press", "_handle_mouse_press"):
        setattr(widget_, target, patch_factory(getattr(widget_, target)))


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


def pad_actual_length(source: str, pad: str = "\u200b") -> Tuple[str, str]:
    """
    Determine real-displaying character length, and provide padding accordingly to match length.
    This way slicing will cut asian letters properly, not breaking tidy layouts.

    :param source: Original string to be manipulated
    :param pad: Default character to pad, default ZWSP

    :return: padding character and padded string
    """
    if wcswidth(source) == len(source):
        return pad, source

    def inner_gen(source_: str) -> Generator[str, None, None]:
        for ch in source_:
            yield ch + pad if wcwidth(ch) == 2 else ch

    return pad, "".join(inner_gen(source.replace(pad, "")))
    # https://github.com/microsoft/terminal/issues/1472
    # Windows Terminal + (Powershell/CMD) combo can't run this due to ZWSP width issue.
    # Expected to run in purely CMD / Linux Terminal. or WSL + Windows Terminal.
    # Tested on Xfce4 & CMD.


def fit_to_actual_width(text: str, length_lim: int) -> str:

    padding, padded = pad_actual_length(text)
    limited = padded[:length_lim - 3]

    if wcwidth(limited[-1]) == 2:
        # if so, last padding was chopped off, so last 2-width character shouldn't be displayed.
        limited = limited[:-1]

    if len(padded) > length_lim - 3:
        limited += " .."

    return limited


# ------------------------------------------------------------------


class AudioPlayer:
    ellipsis_ = ".."  # 3 dots 2 long
    usable_offset_y, usable_offset_x = 2, 6  # Excl. Border, Spacing of widget from abs size.
    next_audio_delay = 1  # not sure yet how to implement this in main thread without spawning one.

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
        self.stop_btn = self.root_.add_button("Stop", 4, 1, command=self.stop_cb)
        self.reload_btn = self.root_.add_button("Reload", 4, 2, command=self.reload_cb)

        self.prev_btn = self.root_.add_button("Reserved", 4, 3, command=lambda a=None: None)
        self.next_btn = self.root_.add_button("Next", 4, 4, command=self.on_next_track_click)

        self.clear_target = (self.audio_list, self.meta_list, self.info_box)

        # -- UI setup
        add_callback_patch(self.audio_list, self.on_file_click)
        self.handle_volume_patch()
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
        self.shuffle = False

        # -- Path and stream instance
        self.stream: StreamManager.StreamManagerABC = StreamManager.StreamManager(self.show_progress, self.play_next)
        self.path_wrapper = PathWrapper()

        # -- Initialize
        self.reload_cb()

    # Primary callbacks

    def on_file_click(self):
        if self.selected_track in self.path_wrapper.folder_list:
            self.update_meta(clear=True)
        else:
            self.update_meta()

    def on_next_track_click(self):
        self.stream.stop_stream(set_flag=False)

    def on_previous_track_click(self):
        pass

    # Media control callback definitions -----------------------
    # TODO: fix malfunctioning play next when force-starting different tracks mid-playing.

    def play_cb_enter(self):
        if self.selected_track in self.path_wrapper.folder_list:
            self.path_wrapper.step_in(self.selected_track)
            self.reload_cb()
        else:
            # force play audio
            with self.maintain_current_view():
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
        with self.maintain_current_view():
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
        """Load audio and starts audio stream. Returns True if successful."""

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

        self.refresh_list(search_files=False)
        self.stream.start_stream()
        self.init_playlist()

        return True

    def stop_cb(self):
        try:
            self.stream.stop_stream()
        except (RuntimeError, FileNotFoundError):
            return

        with self.maintain_current_view():
            # revert texts
            self.refresh_list(search_files=False)
            self.mark_as_stopped(self.currently_playing)
            self.write_info("")

    def refresh_list(self, search_files=True):
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

    def reload_cb(self):
        self.stop_cb()

        # clear widgets

        for widget in self.clear_target:
            widget.clear()

        self.stream = StreamManager.StreamManager(self.show_progress, self.play_next)
        self.refresh_list(search_files=True)

    # TODO: fetch metadata area's physical size and put line breaks or text cycling accordingly.
    def update_meta(self, clear=False):
        if clear:
            self.meta_list.clear()
            return

        # Extract metadata
        ordered = extract_metadata(self.selected_track)
        self.write_meta_list(meta_list_str_gen(ordered))

    def handle_volume_patch(self):
        original = self.volume_slider._handle_key_press

        def handler(handle_key_press):
            original(handle_key_press)
            self.stream.multiplier = self.stream.step * self.volume_slider.get_slider_value()

        self.volume_slider._handle_key_press = handler

    # Implementation / helper / wrappers -----------------------

    def write_info(self, text: str):
        if text:
            # Will have hard time to implement cycling texts.
            fit_text = fit_to_actual_width(str(text), self.get_absolute_size(self.info_box)[-1])
            self.info_box.set_text(fit_text)
        else:
            self.info_box.clear()
            # Sometimes you just want to unify interfaces.

    def write_scroll_wrapped(self, lines: Iterable, widget: py_cui.widgets.ScrollMenu):
        widget.clear()
        offset = -1
        _, usable_x = self.get_absolute_size(widget)
        for line_ in lines:
            widget.add_item(fit_to_actual_width(line_, usable_x + offset))

    def write_meta_list(self, lines: Iterable):
        self.write_scroll_wrapped(lines, self.meta_list)

    def write_audio_list(self, lines: Iterable):
        self.write_scroll_wrapped(lines, self.audio_list)

    def mark_target(self, track_idx, search_target: str, replace_target: str):
        source = self.audio_list.get_item_list()
        source[track_idx] = source[track_idx].replace(search_target, replace_target)
        self.write_audio_list(source)

    def mark_as_playing(self, track_idx):
        if self.stream.stream_state == StreamStates.StreamStoppedState:
            self.mark_target(track_idx, self.symbols["stop"], self.symbols["play"])
        else:
            self.mark_target(track_idx, "|", self.symbols["play"])

    def mark_as_paused(self, track_idx):
        if self.stream.stream_state == StreamStates.StreamPausedState:
            self.mark_target(track_idx, self.symbols["play"], self.symbols["pause"])
        else:
            self.mark_target(track_idx, self.symbols["pause"], self.symbols["play"])
            # This fits more to mark_as_playing, but consequences does not allow to do so, for now.

    def mark_as_stopped(self, track_idx):
        if self.stream.stream_state == StreamStates.StreamPausedState:
            self.mark_target(track_idx, self.symbols["pause"], self.symbols["stop"])
        else:
            self.mark_target(track_idx, self.symbols["play"], self.symbols["stop"])

    @staticmethod
    @functools.lru_cache(256)
    def digit(int_):
        return len(str(int_))

    def show_progress(self, audio_info: StreamManager.AudioInfo, current_frame):
        # counting in some marginal errors of mismatching frames and total frames count.

        file_name = title if (title := audio_info.title) else self.path_wrapper[self.currently_playing].name
        max_frame = audio_info.total_frame
        duration = audio_info.duration_tag
        format_specifier = f"0{self.digit(duration)}.1f"

        self.write_info(f"[{current_frame * duration / max_frame:{format_specifier}}/{duration}] "
                        f"Playing now - {file_name}")

    # Playlist control callback --------------------------------

    def init_playlist(self):
        # if self.shuffle:
        #     self.current_play_generator =
        # Shuffling is harder than imagined!
        # https://engineering.atspotify.com/2014/02/28/how-to-shuffle-songs/

        cycle_gen = itertools.cycle(array.array('i', (n for n in range(len(self.path_wrapper.audio_file_list)))))
        for _ in range(self.currently_playing + 1):
            next(cycle_gen)

        self.current_play_generator = cycle_gen
        # self.current_play_generator = itertools.dropwhile(lambda x: x <= self.currently_playing, cycle_gen)

        logger.debug(f"Initialized playlist generator.")

    def play_next(self):
        # There's no way to stop this when error is on UI side
        logger.debug(f"Condition: {self.stream.stop_flag}")

        if not self.stream.stop_flag:
            try:
                next_ = next(self.current_play_generator)
            except TypeError:
                self.init_playlist()
                next_ = next(self.current_play_generator)

            logger.debug(f"Playing Next - {next_}")

            with self.maintain_current_view():
                if not self.play_stream(next_):
                    logger.warning("Error playing next track. Moving on.")
                    self.play_next()
                else:
                    self.mark_as_playing(self.currently_playing)

    # Helper functions -----------------------------------------

    def get_absolute_size(self, widget: py_cui.widgets.Widget) -> Tuple[int, int]:
        abs_y, abs_x = widget.get_absolute_dimensions()
        return abs_y - self.usable_offset_y, abs_x - self.usable_offset_x

    @property
    def selected_idx(self) -> int:
        return self.audio_list.get_selected_item_index()

    @property
    def selected_track(self) -> pathlib.Path:
        # logger.debug(f"selected track: {self.path_wrapper[self.selected_idx]}, idx: {self.selected_idx}")
        return self.path_wrapper[self.selected_idx]

    @property
    def currently_playing(self) -> int:
        file_name = self.stream.audio_info.loaded_data.name
        return self.path_wrapper.index(file_name)

    @contextmanager
    def maintain_current_view(self):
        """Remembers indices of both `selected / visible top item` and restores it."""
        current_idx = self.audio_list.get_selected_item_index()
        visible_idx = self.audio_list._top_view
        try:
            yield
        finally:
            self.audio_list.set_selected_item_index(current_idx)
            self.audio_list._top_view = visible_idx


def draw_player():
    root = py_cui.PyCUI(5, 7)
    root.set_refresh_timeout(0.1)  # this don't have to be a second. Might be an example of downside of ABC
    root.set_title(f"CUI Audio Player - v{VERSION_TAG}")
    # root.toggle_unicode_borders()
    root.set_widget_border_characters("╔", "╗", "╚", "╝", "═", "║")

    player_ref = AudioPlayer(root)
    assert player_ref  # Preventing unused variable check

    root.start()


def main():
    try:
        draw_player()
    finally:
        sd.stop()


if __name__ == '__main__':
    main()
