import sounddevice as sd
import soundfile as sf
import py_cui
import functools
from collections import OrderedDict
from tinytag import TinyTag
from os import listdir
from os.path import abspath, dirname, join
from numpy import ndarray
from typing import Callable

import pretty_errors
pretty_errors.activate()


# Assuming relative location
AUDIO_FOLDER = "audio_files"
AUDIO_TYPES = ".ogg", ".mp3", ".m4a", ".flac"


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


# ------------------------------------------------------------------
# UI definition, using py-cui examples. Would've been nice if it followed PEP8.


class AudioPlayer:
    ellipsis_ = ".."  # 3 dots 2 long
    # EXPECTING 5, 3 Layout!

    def __init__(self, root: py_cui.PyCUI):
        self.root_ = root

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

        self.files = []
        self.playing = False

    # callback definitions

    def write_info(self, text: str):
        if text:
            self.info_box.set_text(str(text))
        else:
            self.info_box.clear()
            # Sometimes you just want to unify interfaces.

    def play_cb(self):
        if self.playing:
            self.stop_cb()

        self.playing = True
        try:
            play_track(self.abs_dir(self.current))
        except IndexError:
            self.playing = False
        else:
            self.write_info(f"Playing Now - {self.current}")

    def stop_cb(self):
        self.playing = False
        stop_track()
        self.write_info("")
        # Just to provide consistency. Double-wrapped single line method, yes.

    def reload_cb(self):
        self.stop_cb()

        # clear widgets
        for widget in self.clear_target:
            widget.clear()

        # fetch new file list
        self.files = fetch_files()
        digits = len(str(len(self.files))) + 2

        for idx, fn in enumerate(self.files):
            self.audio_list.add_item(f"{str(idx).center(digits)}| {fn}")
            # Actually there is *add_item_list* but I think this is more clean.

        self.write_info(f"Found {len(self.files)} file(s).")
        self.update_meta()

    # TODO: add exception handling later
    # TODO: fetch metadata area's physical size and put line breaks accordingly.
    def update_meta(self):
        # clear meta first
        self.meta_list.clear()

        # Extract metadata
        try:
            ordered = extract_metadata(self.abs_dir(self.current))
        except IndexError:
            return

        # calculate average key length - in case it's too long. Maybe violation of KISS.
        # +1 is mere offset.
        key_avg = (sum(map(len, ordered.keys())) // len(ordered)) + 1

        for key, val in ((k, v) for k, v in ordered.items() if v):
            formatted = key if len(key) < key_avg else key[:key_avg - len(self.ellipsis_)] + self.ellipsis_
            self.meta_list.add_item(f"{formatted.ljust(key_avg)}: {val}")

        # redraw scroll_view

    @property
    def current(self):
        return self.files[self.audio_list.get_selected_item_index()]

    @staticmethod
    def abs_dir(file_name):
        return join(fetch_files.cached_location, file_name)  # dirty trick


def draw_player():
    root = py_cui.PyCUI(5, 5)
    root.set_title("CUI Player")
    player = AudioPlayer(root)

    root.start()


if __name__ == '__main__':

    draw_player()
