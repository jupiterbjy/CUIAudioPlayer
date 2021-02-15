from __future__ import annotations

import itertools
import array
from contextlib import contextmanager
from typing import TYPE_CHECKING, Iterable, Tuple, Callable, Any

import py_cui
from .PlayerStates import PlayerStates
from .TUI import AudioPlayerTUI
from . import add_callback_patch, fit_to_actual_width, fit_to_actual_width_multiline, extract_meta, meta_list_str_gen
from SDManager.StreamStates import StreamPausedState, StreamStoppedState
from SDManager.StreamManager import StreamManager
from LoggingConfigurator import logger

if TYPE_CHECKING:
    from SDManager import AudioObject


class AudioPlayer(AudioPlayerTUI, PlayerStates):
    def __init__(self, root: py_cui.PyCUI):
        super().__init__(root)

        self.play_btn.command = self.play_cb_space_bar
        self.stop_btn.command = self._on_stop_click
        self.reload_btn.command = self._on_reload_click
        self.next_btn.command = self._on_next_track_click
        self.prev_btn.command = lambda a=None: None

        self.clear_target = (self.audio_list, self.meta_list, self.info_box)

        # -- UI setup
        def volume_callback():
            self.stream.multiplier = self.stream.step * self.volume_slider.get_slider_value()

        add_callback_patch(self.audio_list, self._on_file_click)
        add_callback_patch(self.volume_slider, volume_callback, keypress_only=True)

        self.volume_slider.toggle_border()
        self.volume_slider.toggle_title()
        self.volume_slider.toggle_value()
        self.volume_slider.set_bar_char("█")

        # -- Key binds
        self.audio_list.add_key_command(py_cui.keys.KEY_ENTER, self.play_cb_enter)
        self.audio_list.add_key_command(py_cui.keys.KEY_SPACE, self.play_cb_space_bar)

        # -- Color rules
        self.audio_list.add_text_color_rule(r"[0-9 ].*" + self.symbols["play"], py_cui.WHITE_ON_YELLOW, "contains")
        self.audio_list.add_text_color_rule(r"[0-9 ].*" + self.symbols["pause"], py_cui.WHITE_ON_YELLOW, "contains")
        self.audio_list.add_text_color_rule(r"[0-9 ].*" + self.symbols["stop"], py_cui.WHITE_ON_YELLOW, "contains")
        self.audio_list.add_text_color_rule(r"DIR", py_cui.CYAN_ON_BLACK, "startswith", include_whitespace=False)
        self.info_box.add_text_color_rule("ERR:", py_cui.WHITE_ON_RED, "startswith")

        self._on_reload_click()

    # Primary callbacks

    def _on_file_click(self):
        """
        Callback for clicking an item from audio_list.
        """

        if self.selected_track in self.path_wrapper.folder_list:
            self.clear_meta()
        else:
            self.update_meta()

    def _on_next_track_click(self):
        """
        Callback for clicking next track button.
        """

        self.stream.stop_stream(run_finished_callback=False)

    def _on_previous_track_click(self):
        """
        Callback for clicking previous button.
        """

    def _on_stop_click(self):
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

    def _on_reload_click(self):
        """
        Callback for clicking reload button.
        """

        self._on_stop_click()

        # clear widgets

        for widget in self.clear_target:
            widget.clear()

        self.stream = StreamManager(self.show_progress_wrapper(), self.play_next)
        self._refresh_list(search_files=True)

    # Media control callback definitions -----------------------
    # TODO: Refactor to state machine

    def play_cb_enter(self):
        """
        Enters directory if selected item is one of them. Else will stop current track and play selected track.
        """

        if self.selected_track in self.path_wrapper.folder_list:
            self.path_wrapper.step_in(self.selected_track)
            self._on_reload_click()
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
        self._init_playlist()

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

    def update_meta(self):
        """
        Updates metadata to show selected item.
        """

        ordered = extract_meta(self.selected_track)
        self.write_meta_list(meta_list_str_gen(ordered), wrap_line=True)

    def clear_meta(self):
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
        if self.stream.stream_state == StreamStoppedState:
            self._mark_target(track_idx, self.symbols["stop"], self.symbols["play"])
        else:
            self._mark_target(track_idx, "|", self.symbols["play"])

    def mark_as_paused(self, track_idx):
        """
        Set line at given index to paused state

        :param track_idx: index of item to mark
        """

        if self.stream.stream_state == StreamPausedState:
            self._mark_target(track_idx, self.symbols["play"], self.symbols["pause"])
        else:
            self._mark_target(track_idx, self.symbols["pause"], self.symbols["play"])
            # This fits more to mark_as_playing, but consequences does not allow to do so, for now.

    def mark_as_stopped(self, track_idx):
        """
        Set line at given index to stopped state

        :param track_idx: index of item to mark
        """

        if self.stream.stream_state == StreamPausedState:
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

    def _init_playlist(self):
        """
        Create itertools.cycle generator that acts as a playlist
        """

        # Shuffling is harder than imagined!
        # https://engineering.atspotify.com/2014/02/28/how-to-shuffle-songs/

        cycle_gen = itertools.cycle(array.array('i', (n for n in range(len(self.path_wrapper.audio_file_list)))))
        for _ in range(self.currently_playing + 1):
            next(cycle_gen)

        self._current_play_generator = cycle_gen
        logger.debug("Initialized playlist generator.")

    def play_next(self):
        """
        Play next track. Called by finished callback of sounddevice when conditions are met.
        """

        logger.debug(f"Condition: {self.stream.stop_flag}")

        if not self.stream.stop_flag:
            try:
                next_ = next(self._current_play_generator)
            except TypeError:
                self._init_playlist()
                next_ = next(self._current_play_generator)

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

