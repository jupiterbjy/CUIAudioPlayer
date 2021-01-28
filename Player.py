import sounddevice as sd
import py_cui
import array
import functools
import itertools
from collections import OrderedDict
from tinytag import TinyTag
from wcwidth import wcswidth, wcwidth
from sys import platform
from os import listdir
from os.path import dirname, join, split
from typing import Callable, Mapping, Generator, Iterable, Tuple, List

from LoggingConfigurator import logger
import CompatibilityPatch
from SDManager import StreamManager, StreamStates

try:
    # noinspection PyUnresolvedReferences
    import pretty_errors
    pretty_errors.activate()
except ImportError:
    pass

assert CompatibilityPatch


# THIS WILL NOT RUN PROPERLY ON WINDOWS TERMINAL! Currently Developing on CMD!
# Assuming relative location
AUDIO_FOLDER = "audio_files"
AUDIO_TYPES = ".ogg", ".mp3", ".m4a", ".flac"
VERSION_TAG = "0.0.2a"
WINDOWS = platform == 'win32'


def extract_metadata(abs_file_dir):
    tag = TinyTag.get(abs_file_dir)
    filtered = sorted(((k, v) for k, v in tag.as_dict().items() if v))
    return OrderedDict(filtered)


def fetch_files():
    try:
        # check cached path first
        file_list = listdir(fetch_files.cached_location)
    except AttributeError:
        # initializing path first
        path_ = join(dirname(__file__), AUDIO_FOLDER)
        fetch_files.cached_location = path_
        return fetch_files()
    else:
        return [fn for fn in file_list if fn.endswith(AUDIO_TYPES)]


def add_callback_patch(widget_: py_cui.widgets.Widget, callback: Callable) -> None:
    """
    Adding callback support for widget that lacks such as ScrollMenu.

    :param widget_: Any widget you want to add callback on each update.
    :param callback: Any callables
    :return: None
    """
    # Seems like sequence is _draw -> _handle_mouse_press, so patching on _draw results 1 update behind.
    # Therefore we need to patch both _handle_mouse_press and _handle_keyboard_press first.

    def patch_factory(old_func):
        # fix for late binding issue: stackoverflow.com/questions/3431676
        @functools.wraps(old_func)
        def wrapper(*args, **kwargs):
            old_func(*args, **kwargs)
            callback()

        return wrapper

    for target in ("_handle_key_press", "_handle_mouse_press"):
        setattr(widget_, target, patch_factory(getattr(widget_, target)))


def audio_list_str_gen(dict_: Mapping, ellipsis_: str = "..", offset: int = 1) -> Generator[str, None, None]:
    """
    Cuts text in avg. of given dict_'s keys.
    :param dict_: Mapping containing metadata.
    :param ellipsis_: Suffix to use as ellipsis, when text is longer than avg.
    :param offset: Offset to add / reduce max displayed length from avg.
    """
    key_avg = (sum(map(len, dict_.keys())) // len(dict_)) + offset

    for key, val in ((k, v) for k, v in dict_.items() if v):
        formatted = key if len(key) < key_avg else key[:key_avg - len(ellipsis_)] + ellipsis_
        yield f"{formatted.ljust(key_avg)}: {val}"


def pad_actual_length(source: str, pad: str = "\u200b") -> Tuple[str, str]:
    """
    Determine real-displaying character length, and provide padding accordingly to match length.
    This way slicing will cut asian letters properly, not breaking tidy layouts.
    :return: padding character and padded string
    """
    if wcswidth(source) == len(source):
        return pad, source

    def inner_gen(source_: str) -> Generator[str, None, None]:
        for ch in source_:
            yield ch + pad if wcwidth(ch) == 2 else ch

    return pad, "".join(inner_gen(source.replace(pad, "")))
    # WHAT'S WRONG WITH POWERSHELL AND WINDOWS TERMINAL? IT'S BAD THAN CMD ABOUT CURSES!
    # TOOK WEEKS TO FIGURE OUT THIS, GJ MS


def fit_to_actual_width(text: str, length_lim: int) -> str:

    padding, padded = pad_actual_length(text)
    limited = padded[:length_lim]
    if wcwidth(limited[-1]) == 2:
        # if so, last padding was wear off, so last 2-width character shouldn't be displayed.
        limited = limited[:-1]

    return limited.rstrip(padding)


# ------------------------------------------------------------------
# UI definition, using py-cui examples. Would've been nice if it followed PEP8.


class AudioPlayer:
    ellipsis_ = ".."  # 3 dots 2 long
    usable_offset_y, usable_offset_x = 2, 6  # Excl. Border, Spacing of widget from abs size.
    next_audio_delay = 1  # not sure yet how to implement this in main thread without spawning one.

    symbols = {"play": "⏵", "pause": "⏸", "stop": "⏹"}

    # EXPECTING 5, 7 Layout!

    def __init__(self, root: py_cui.PyCUI):
        self.root_ = root

        # row-idx then col-idx, it's reversed x,y - reminder to self!
        self.audio_list = self.root_.add_scroll_menu("Files", 0, 0, column_span=5, row_span=3)
        self.meta_list = self.root_.add_scroll_menu("Meta", 0, 5, column_span=2, row_span=5)

        self.info_box = self.root_.add_text_box("Info", 3, 0, column_span=4)
        self.volume_slider = self.root_.add_slider("Volume", 3, 4, column_span=1, min_val=0, max_val=8, init_val=4)
        self.handle_volume_patch()
        self.volume_slider.toggle_border()
        self.volume_slider.toggle_title()
        self.volume_slider.toggle_value()
        self.volume_slider.set_bar_char("█")

        self.play_btn = self.root_.add_button("Play", 4, 0, command=self.play_cb)
        self.stop_btn = self.root_.add_button("Stop", 4, 1, command=self.stop_cb)
        self.reload_btn = self.root_.add_button("Reload", 4, 2, command=self.reload_cb)

        self.reserved_1 = self.root_.add_button("reserved", 4, 3)
        self.reserved_2 = self.root_.add_button("reserved", 4, 4)

        # just for ease of clearing
        self.clear_target = [self.audio_list, self.meta_list, self.info_box]

        # add callback to update metadata on every redraw.
        add_callback_patch(self.audio_list, self.update_meta)

        # Key binds
        self.play_btn.add_key_command(py_cui.keys.KEY_SPACE, self.play_cb)
        self.audio_list.add_key_command(py_cui.keys.KEY_ENTER, self.play_stream)

        # add color rules - might be better implementing custom coloring methods, someday.
        self.audio_list.add_text_color_rule(r"[0-9 ].*" + self.symbols["play"], py_cui.WHITE_ON_YELLOW, "contains")
        self.audio_list.add_text_color_rule(r"[0-9 ].*" + self.symbols["pause"], py_cui.WHITE_ON_YELLOW, "contains")
        self.audio_list.add_text_color_rule(r"[0-9 ].*" + self.symbols["stop"], py_cui.WHITE_ON_YELLOW, "contains")
        # self.audio_list.add_text_color_rule(r"►", py_cui.WHITE_ON_YELLOW, "contains")
        self.info_box.add_text_color_rule("ERR:", py_cui.WHITE_ON_RED, "startswith")

        self.files: List[str] = []
        self.current_play_generator = None
        self.shuffle = False

        self.stream: StreamManager.StreamManager = StreamManager.StreamManager(self.show_progress, self.play_next)

        self.reload_cb()

    # Media control callback definitions -----------------------
    # TODO: fix malfunctioning play next when force-starting different tracks mid-playing.

    def play_cb(self):
        try:
            self.stream.error_flag = False
            self.stream.pause_stream()  # assuming State: Paused
            self.mark_as_paused(self.currently_playing)
        except RuntimeError:
            self.stream.start_stream()  # State: stopped
            self.mark_as_playing(self.currently_playing)
        except FileNotFoundError:
            # State: Unloaded
            self.play_stream()

    def play_stream(self, audio_idx=None) -> bool:
        if not audio_idx:
            audio_idx = self.selected_idx

        try:
            self.stream.load_stream(self.abs_dir(audio_idx))
        except IndexError:
            logger.debug(f"Invalid idx: {audio_idx} / {len(self.files)}")
            return False

        except RuntimeError as err:
            self.write_info(f"ERR: {str(err).split(':')[-1]}")
            return False

        self.refresh_list(False)
        self.stream.start_stream()
        self.mark_as_playing(audio_idx)
        self.init_playlist()

        return True

    def stop_cb(self):
        self.stream.error_flag = False  # need this before final callback is called, what a mess.
        try:
            self.stream.stop_stream()
        except (RuntimeError, FileNotFoundError):
            return

        # store current idx
        idx_last = self.audio_list.get_selected_item_index()

        # revert texts
        self.refresh_list(search_files=False)
        self.mark_as_stopped(self.currently_playing)
        self.write_info("")

        # revert idx back
        self.audio_list.set_selected_item_index(idx_last)

    def refresh_list(self, search_files=True):
        self.audio_list.clear()

        if search_files:
            self.files = fetch_files()

        digits = len(str(len(self.files))) + 2

        lazy_line_gen = (f"{str(idx).center(digits)}| {fn}" for idx, fn in enumerate(self.files))
        self.write_audio_list(lazy_line_gen)

        self.write_info(f"Found {len(self.files)} file(s).")

    def reload_cb(self):
        self.stop_cb()

        # clear widgets
        for widget in self.clear_target:
            widget.clear()

        self.refresh_list()

    # TODO: fetch metadata area's physical size and put line breaks or text cycling accordingly.
    def update_meta(self):
        # Extract metadata
        try:
            ordered = extract_metadata(self.abs_dir(self.selected_idx))
        except IndexError:
            return

        self.write_meta_list(audio_list_str_gen(ordered))

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
        self.stream.error_flag = True

        # if self.stream.stream_state == SoundModule.StreamPausedState:
        #     self.mark_target(track_idx, self.symbols["pause"], self.symbols["play"])

        if self.stream.stream_state == StreamStates.StreamStoppedState:
            self.mark_target(track_idx, self.symbols["stop"], self.symbols["play"])
        else:
            self.mark_target(track_idx, "|", self.symbols["play"])

    def mark_as_paused(self, track_idx):
        if self.stream.stream_state == StreamStates.StreamPausedState:

            self.stream.error_flag = False
            self.mark_target(track_idx, self.symbols["play"], self.symbols["pause"])
        else:
            self.mark_target(track_idx, self.symbols["pause"], self.symbols["play"])
            # This fits more to mark_as_playing, but consequences does not allow to do so, for now.

    def mark_as_stopped(self, track_idx):
        self.stream.error_flag = False

        if self.stream.stream_state == StreamStates.StreamPausedState:
            self.mark_target(track_idx, self.symbols["pause"], self.symbols["stop"])
        else:
            self.mark_target(track_idx, self.symbols["play"], self.symbols["stop"])

    def set_current_selected(self, track_idx):
        pass

    @staticmethod
    @functools.lru_cache(256)
    def digit(int_):
        return len(str(int_))

    def show_progress(self, audio_info: StreamManager.AudioInfo, current_frame):
        # counting in some marginal errors of mismatching frames and total frames count.
        file_name = audio_info.title
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

        cycle_gen = itertools.cycle(array.array('i', (n for n in range(len(self.files)))))
        for _ in range(self.currently_playing + 1):
            next(cycle_gen)

        self.current_play_generator = cycle_gen
        # self.current_play_generator = itertools.dropwhile(lambda x: x <= self.currently_playing, cycle_gen)

        logger.debug(f"Initialized playlist generator.")

    def play_next(self):
        # There's no way to stop this when error is on UI side
        logger.debug(f"Condition: {self.stream.error_flag}")

        if self.stream.error_flag:
            next_ = next(self.current_play_generator)
            logger.debug(f"Playing Next - {next_}")

            if not self.play_stream(next_):
                logger.warning("Error playing next track. Moving on.")
                self.play_next()

    # UI related -----------------------------------------------

    def get_absolute_size(self, widget: py_cui.widgets.Widget) -> Tuple[int, int]:
        abs_y, abs_x = widget.get_absolute_dimensions()
        return abs_y - self.usable_offset_y, abs_x - self.usable_offset_x

    @property
    def selected_idx(self) -> int:
        return self.audio_list.get_selected_item_index()

    @property
    def selected_track(self) -> str:
        return self.files[self.selected_idx]

    @property
    def currently_playing(self) -> int:
        file_name = self.stream.audio_info.loaded_data.name
        return self.files.index(split(file_name)[1])

    def abs_dir(self, idx):
        # noinspection PyUnresolvedReferences
        return join(fetch_files.cached_location, self.files[idx])  # dirty trick


def draw_player():
    root = py_cui.PyCUI(5, 7)
    root.set_refresh_timeout(0.1)  # this don't have to be a second. Might be an example of downside of ABC
    root.set_title(f"CUI Audio Player - v{VERSION_TAG}")
    player_ref = AudioPlayer(root)
    assert player_ref  # Preventing unused variable check

    root.start()


if __name__ == '__main__':
    try:
        draw_player()
    finally:
        sd.stop()
