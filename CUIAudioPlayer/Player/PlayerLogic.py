"""
Combined logic with TUI and PlayerLogixMixin.
"""

from __future__ import annotations

import array
import itertools
from contextlib import contextmanager
from typing import TYPE_CHECKING, Iterable, Callable, Type, Tuple

import py_cui
from FileWalker import PathWrapper
from SDManager.StreamManager import StreamManager
from LoggingConfigurator import logger
from .TUI import AudioPlayerTUI
from .PlayerStates import PlayerStates, AudioUnloaded
from . import (
    add_callback_patch,
    fit_to_actual_width,
    fit_to_actual_width_multiline,
    extract_meta,
    meta_list_str_gen,
    gen_progress_bar,
)

if TYPE_CHECKING:
    import pathlib
    from SDManager import AudioObject


class PlayerLogicMixin:
    """
    Mixin dealing with Logics.
    """

    # Excl. Border, Spacing of widget from abs size.
    usable_offset_y, usable_offset_x = 2, 6

    # Symbols for play state indicator
    symbols = {"play": "⏵", "pause": "⏸", "stop": "⏹"}

    def _init_playlist(self: AudioPlayer):
        """
        Create itertools.cycle generator that acts as a playlist
        """

        # Shuffling is harder than imagined!
        # https://engineering.atspotify.com/2014/02/28/how-to-shuffle-songs/

        cycle_gen = itertools.cycle(
            array.array("i", (n for n in range(len(self.path_wrapper.audio_file_list))))
        )

        for _ in range(self.currently_playing + 1):
            next(cycle_gen)

        self._current_play_generator = cycle_gen
        logger.debug("Initialized playlist generator.")

    def playlist_next(self: AudioPlayer):
        """
        Separated logic from TUI
        :return:
        """

        try:
            return next(self._current_play_generator)
        except TypeError:
            self._init_playlist()
            return next(self._current_play_generator)

    def get_absolute_size(self: AudioPlayer, widget: py_cui.widgets.Widget) -> Tuple[int, int]:
        """
        Get absolute dimensions of widget including borders.

        :param widget: widget instance to get dimensions of
        :return: y-height and x-height
        """

        abs_y, abs_x = widget.get_absolute_dimensions()
        return abs_y - self.usable_offset_y, abs_x - self.usable_offset_x

    @property
    def currently_playing(self: AudioPlayer) -> int:
        """
        Returns index of currently played track. Currently using slow method for simplicity.

        :return: index of played file
        """

        file_name = self.stream.audio_info.loaded_data.name
        return self.path_wrapper.index(file_name)


class AudioPlayer(AudioPlayerTUI, PlayerLogicMixin):
    """
    Main player class.
    """

    def __init__(self, root: py_cui.PyCUI):
        super().__init__(root)

        self.play_btn.command = self._play_cb_space_bar
        self.stop_btn.command = self._on_stop_click
        self.reload_btn.command = self._on_reload_click
        self.next_btn.command = self._on_next_track_click
        # self.prev_btn.command = lambda a=None: None

        self.clear_target = (self.audio_list, self.meta_list, self.info_box)

        # -- UI setup
        add_callback_patch(self.audio_list, self._on_file_click)
        add_callback_patch(self.volume_slider, self.volume_callback, keypress_only=True)

        self.volume_slider.toggle_border()
        self.volume_slider.toggle_title()
        self.volume_slider.toggle_value()
        self.volume_slider.align_to_bottom()
        self.volume_slider.set_bar_char("█")

        # -- Key binds
        self.audio_list.add_key_command(py_cui.keys.KEY_ENTER, self._play_cb_enter)
        self.volume_slider.add_key_command(py_cui.keys.KEY_SPACE, self._play_cb_space_bar)

        for widget in (
            self.audio_list,
            self.info_box,
            self.meta_list,
        ):
            widget.add_key_command(py_cui.keys.KEY_SPACE, self._play_cb_space_bar)
            widget.add_key_command(py_cui.keys.KEY_LEFT_ARROW, self._adjust_playback_left)
            widget.add_key_command(py_cui.keys.KEY_RIGHT_ARROW, self._adjust_playback_right)

        # -- Color rules
        self.info_box.add_text_color_rule("ERR:", py_cui.WHITE_ON_RED, "startswith")

        self.audio_list.add_text_color_rule(self.symbols["play"], py_cui.WHITE_ON_YELLOW, "contains")
        self.audio_list.add_text_color_rule(self.symbols["pause"], py_cui.WHITE_ON_YELLOW, "contains")
        self.audio_list.add_text_color_rule(self.symbols["stop"], py_cui.WHITE_ON_YELLOW, "contains")
        self.audio_list.add_text_color_rule(
            r"DIR", py_cui.CYAN_ON_BLACK, "startswith", include_whitespace=False
        )

        # -- State
        self.player_state: Type[PlayerStates] = AudioUnloaded
        self._digit: int = 0

        # -- Path and stream instance
        self.stream = StreamManager(self.show_progress_wrapper(), self.play_next)
        self.path_wrapper = PathWrapper()

        # -- Generator instance and states
        self._current_play_generator = None
        self._current_name_cycler = None

        self._on_reload_click()

    # Primary callbacks

    def _on_file_click(self):
        """
        Callback for clicking item in audio list.
        """

        # logger.debug(f"State: {self.player_state}")
        return self.player_state.on_file_click(self)

    def _on_next_track_click(self):
        """
        Callback for clicking next track button.
        """

        logger.debug(f"State: {self.player_state}")
        return self.player_state.on_next_track_click(self)

    def _on_previous_track_click(self):
        """
        Callback for clicking previous button.
        """

        logger.debug(f"State: {self.player_state}")
        return self.player_state.on_previous_track_click(self)

    def _on_stop_click(self):
        """
        Callback for clicking stop button.
        """

        logger.debug(f"State: {self.player_state}")
        return self.player_state.on_stop_click(self)

    def _on_reload_click(self):
        """
        Callback for clicking reload button.
        """

        logger.debug(f"State: {self.player_state}")
        return self.player_state.on_reload_click(self)

    def _play_cb_enter(self):
        """
        Callback for pressing enter on audio list.
        """

        logger.debug(f"State: {self.player_state}")
        return self.player_state.on_audio_list_enter_press(self)

    def _play_cb_space_bar(self):
        """
        Callback for pressing space bar on audio list.
        """

        logger.debug(f"State: {self.player_state}")
        return self.player_state.on_audio_list_space_press(self)

    def _adjust_playback_left(self):
        """
        Moves audio playback cursor to left
        """

        logger.debug(f"State: {self.player_state}")
        return self.player_state.adjust_playback_left(self)

    def _adjust_playback_right(self):
        """
        Move audio playback cursor to right
        """

        logger.debug(f"State: {self.player_state}")
        return self.player_state.adjust_playback_right(self)

    def volume_callback(self):
        """
        Callback for volume slider that adjust multiplier inside StreamManager.
        """

        self.stream.multiplier = self.volume_slider.get_slider_value() / 4

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
        self._init_playlist()

        return True

    # End of primary callback

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
        self._digit = digits

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
        self.audio_list.set_title(
            f"Audio List - " f"{len(self.path_wrapper.audio_file_list)} track(s)"
        )

    def _update_meta(self):
        """
        Updates metadata to show selected item.
        """

        ordered = extract_meta(self.selected_idx_path)
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
            fit_text = fit_to_actual_width(str(text), self.get_absolute_size(self.info_box)[-1])
            self.info_box.set_text(fit_text)
        else:
            self.info_box.clear()
            # Sometimes you just want to unify interfaces.

    def _write_to_scroll_widget(
        self, lines: Iterable, widget: py_cui.widgets.ScrollMenu, wrap_line=False
    ):
        """
        Internal function that handles writing on scroll widget.

        :param lines: lines to write on audio_list
        :param widget: ScrollMenu Widget to write on
        """

        widget.clear()
        offset = -1
        _, usable_x = self.get_absolute_size(widget)

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

    def _mark_target(self, track_idx, replace_target: str):
        """
        internal function that changes search_target in line at index to replace_target.

        :param track_idx: index of item to mark
        :param replace_target: string to replace with
        """

        source = self.audio_list.get_item_list()
        string = source[track_idx]

        source[track_idx] = (string[: self._digit] + replace_target + string[self._digit + 1:])
        self.write_audio_list(source)

    def reset_marking(self, track_idx):
        """
        Set line at given index to default state

        :param track_idx: index of item to mark
        """

        self._mark_target(track_idx, "|")

    def mark_as_playing(self, track_idx):
        """
        Set line at given index to playing state

        :param track_idx: index of item to mark
        """

        self._mark_target(track_idx, self.symbols["play"])

    def mark_as_paused(self, track_idx):
        """
        Set line at given index to paused state

        :param track_idx: index of item to mark
        """

        self._mark_target(track_idx, self.symbols["pause"])

    def mark_as_stopped(self, track_idx):
        """
        Set line at given index to stopped state

        :param track_idx: index of item to mark
        """

        self._mark_target(track_idx, self.symbols["stop"])

    def show_progress_wrapper(self, paused=False) -> Callable[[AudioObject.AudioInfo, int], None]:
        """
        Wrapper for function that handles progress. Returning callable that is meant to run in sounddevice callback.

        :param paused: if True, change message to display paused state.

        :return: Callback for sounddevice Numpy sound stream
        """

        message = "Paused" if paused else "Playing now"

        def digit(int_):
            return len(str(int_))

        def show_progress(audio_info: AudioObject.AudioInfo, current_frame):

            file_name = audio_info.title
            max_frame = audio_info.total_frame

            duration = audio_info.duration_tag
            duration_digit = digit(duration)

            format_specifier = f"0{duration_digit}.1f"
            time_string = f"|{current_frame * duration / max_frame:{format_specifier}}/{duration}"

            _, x_width = self.info_box.get_absolute_dimensions()

            self.info_box.set_title(
                f"{time_string}"
                f"{gen_progress_bar(current_frame / max_frame, x_width - len(time_string) - 2)}"
            )

            self.write_info(f"{message} - {file_name}")

        return show_progress

    # Playlist control callback --------------------------------

    def play_next(self):
        """
        Play next track. Called by finished callback of sounddevice when conditions are met.
        """

        logger.debug(f"Condition: {self.stream.stop_flag}")

        if not self.stream.stop_flag:
            next_ = self.playlist_next()

            logger.debug(f"Playing Next - {next_}")

            with self.maintain_current_view():
                if not self.play_stream(next_):
                    logger.warning("Error playing next track. Moving on.")
                    self.play_next()
                else:
                    self.mark_as_playing(self.currently_playing)

    # Helper functions -----------------------------------------

    @property
    def selected_idx(self) -> int:
        """
        Returns index of selected track. Convenient method.

        :return: index of selected track.
        """

        return self.audio_list.get_selected_item_index()

    @property
    def selected_idx_path(self) -> pathlib.Path:
        """
        Returns pathlib.Path object of selected track. Convenient method.

        :return: pathlib.Path object indicating directory of selected item
        """

        return self.path_wrapper[self.selected_idx]

    @contextmanager
    def maintain_current_view(self):
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
