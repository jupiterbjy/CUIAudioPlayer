import sounddevice as sd
import soundfile as sf
import py_cui
import functools
from collections import OrderedDict
from tinytag import TinyTag
from os import listdir
from os.path import abspath, dirname, join
from numpy import ndarray
from typing import Callable, Mapping, Generator, Iterable, Tuple, List

from ColoramaWrapper import br_green

import pretty_errors
pretty_errors.activate()


# Assuming relative location
AUDIO_FOLDER = "audio_files"
AUDIO_TYPES = ".ogg", ".mp3", ".m4a", ".flac"
VERSION_TAG = "0.0.1a"


class Device:
    # Singleton? is this correct?
    name: str = ""
    frequency: int = 48000
    channels: int = 2


def play_track(file_name: str, blocking=False):
    data, fs = sf.read(file_name)

    sd.play(data, fs)
    if blocking:
        sd.wait()


def stop_track():  # She's so smol
    sd.stop()


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
        # I love this shiny new suffix / prefix search. Only in 3.9+.


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


# ------------------------------------------------------------------
# UI definition, using py-cui examples. Would've been nice if it followed PEP8.


class AudioPlayer:
    ellipsis_ = ".."  # 3 dots 2 long
    # EXPECTING 5, 3 Layout!

    def __init__(self, root: py_cui.PyCUI):
        self.root_ = root

        # row-idx then col-idx, it's reversed x,y - reminder to self!
        self.audio_list = self.root_.add_scroll_menu("Files", 0, 0, column_span=3, row_span=3)
        self.meta_list = self.root_.add_scroll_menu("Meta", 0, 3, column_span=2, row_span=5)
        self.info_box = self.root_.add_text_box("Info", 3, 0, column_span=3)
        self.play_btn = self.root_.add_button("Play", 4, 0, command=self.play_cb)
        self.stop_btn = self.root_.add_button("Stop", 4, 1, command=self.stop_cb)
        self.reload_btn = self.root_.add_button("Reload", 4, 2, command=self.reload_cb)

        # just for ease of clearing
        self.clear_target = [self.audio_list, self.meta_list, self.info_box]

        # add callback to update metadata on every redraw.
        add_callback_patch(self.audio_list, self.update_meta)

        # Key binds
        self.play_btn.add_key_command(py_cui.keys.KEY_SPACE, self.play_cb)

        # add color rules - might be better implementing custom coloring methods, someday.
        # self.audio_list.add_text_color_rule(r"[0-9 ]►", py_cui.WHITE_ON_YELLOW, "startswith")
        self.audio_list.add_text_color_rule(r"►", py_cui.WHITE_ON_YELLOW, "contains")
        self.info_box.add_text_color_rule("ERR:", py_cui.WHITE_ON_RED, "startswith")

        self.files: List[str] = []
        self.playing = False

    # callback definitions

    def play_cb(self):
        self.stop_cb()

        try:
            play_track(self.abs_dir(self.current[1]))
        except IndexError:
            return
        except RuntimeError as err:
            self.write_info(f"ERR: {str(err).split(':')[-1]}")
            return

        self.write_info(f"Playing Now - {self.current[1]}")
        self.mark_current_playing(self.current[0])
        self.playing = True

    def stop_cb(self):
        if not self.playing:
            return

        self.playing = False
        stop_track()

        # store current idx
        idx_last = self.audio_list.get_selected_item_index()

        # revert texts
        self.refresh_list(search_files=False)
        self.write_info("")

        # revert idx back
        self.audio_list.set_selected_item_index(idx_last)

    def refresh_list(self, search_files=True):
        self.audio_list.clear()

        if search_files:
            self.files = fetch_files()

        digits = len(str(len(self.files))) + 2

        for idx, fn in enumerate(self.files):
            self.audio_list.add_item(f"{str(idx).center(digits)}| {fn}")
            # Actually there is *add_item_list* but I think this reduces memory spikes.
            # check source code of add_item_list, it uses str(list) for logging.

        self.write_info(f"Found {len(self.files)} file(s).")
        self.update_meta()
        # TODO: maintain original item if possible, then move update_meta call to reload_cb.

    def reload_cb(self):
        self.stop_cb()

        # clear widgets
        for widget in self.clear_target:
            widget.clear()

        self.refresh_list()

    # TODO: fetch metadata area's physical size and put line breaks or text cycling accordingly.
    def update_meta(self):
        # clear meta first
        self.meta_list.clear()

        # Extract metadata
        try:
            ordered = extract_metadata(self.abs_dir(self.current[1]))
        except IndexError:
            return

        self.write_meta_list(audio_list_str_gen(ordered))

    # Wrappers

    def write_info(self, text: str):
        if text:
            self.info_box.set_text(str(text))
        else:
            self.info_box.clear()
            # Sometimes you just want to unify interfaces.

    def write_meta_list(self, lines: Iterable):
        self.meta_list.clear()
        self.meta_list.add_item_list(lines)  # Might need to open a issue about false warnings.

    # TODO: create branch to implement full-color support for py_cui.
    def write_audio_list(self, lines: Iterable):
        self.audio_list.clear()
        for line in lines:
            self.audio_list.add_item(line)

    # Extra functions

    def mark_current_playing(self, track_idx):
        source = self.audio_list.get_item_list()
        source[track_idx] = source[track_idx].replace("|", "►")
        self.write_audio_list(source)

    @property
    def current(self) -> Tuple[int, str]:
        idx = self.audio_list.get_selected_item_index()
        return idx, self.files[idx]

    @staticmethod
    def abs_dir(file_name):
        # noinspection PyUnresolvedReferences
        return join(fetch_files.cached_location, file_name)  # dirty trick


def draw_player():
    root = py_cui.PyCUI(5, 5)
    root.set_title(f"CUI Audio Player - v{VERSION_TAG}")
    player_ref = AudioPlayer(root)

    root.start()


if __name__ == '__main__':
    draw_player()
