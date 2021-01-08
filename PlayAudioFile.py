import sounddevice as sd
import soundfile as sf
import py_cui
from collections import OrderedDict
from tinytag import TinyTag
from os import listdir
from os.path import abspath, dirname, join
from numpy import ndarray


# Assuming relative location
AUDIO_FOLDER = "files"
AUDIO_TYPES = ".ogg", ".mp3", ".m4a"


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
    tag = TinyTag.get(abs_file_dir)  # dirty trick
    return OrderedDict(sorted(tag.as_dict().items()))


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

# ------------------------------------------------------------------
# UI definition, using py-cui examples. Would've been nice if it followed PEP8.


class AudioPlayer:
    ellipsis_ = ".."  # 3 dots 2 long
    # EXPECTING 5, 3 Layout!

    def __init__(self, root: py_cui.PyCUI):
        self.root_ = root

        # Doing a trick, putting button and scroll view at same position,
        # then update scroll menu to re-draw over button.
        self.audio_list = self.root_.add_scroll_menu("Files", 0, 0, column_span=3, row_span=3)
        # self.hidden_btn = self.root_.add_button("U Nya", 0, 0, column_span=3, row_span=3, command=self.update_meta)

        self.meta_list = self.root_.add_scroll_menu("Meta", 0, 3, column_span=2, row_span=5)
        self.progress_blk = self.root_.add_text_box("Info", 3, 0, column_span=3)
        self.play_btn = self.root_.add_button("Play", 4, 0, command=self.play_cb)
        self.stop_btn = self.root_.add_button("Stop", 4, 1, command=self.stop_cb)
        self.reload_btn = self.root_.add_button("Reload", 4, 2, command=self.reload_cb)

        # self.hidden_btn.is_selectable = False

        # just for ease of clearing
        self.clear_target = [self.audio_list, self.meta_list, self.progress_blk]

        # Key-binding space bar to play. No, no toggle yet.
        self.play_btn.add_key_command(py_cui.keys.KEY_SPACE, self.play_cb)
        self.meta_list.add_key_command(py_cui.keys.KEY_ENTER, self.wrapper)

        self.files = []
        self.playing = False

    # callback definitions

    def play_cb(self):
        if self.playing:
            self.stop_cb()

        self.playing = True
        play_track(self.abs_dir(self.current))

    def stop_cb(self):
        self.playing = False
        stop_track()
        # Just to provide consistency. Double-wrapped single line method, yes.

    def reload_cb(self):
        # clear widgets
        for widget in self.clear_target:
            try:
                widget.clear()
            except AttributeError:
                print(f"{type(widget)} don't have clear()!")

        # fetch new file list
        self.files = fetch_files()
        digits = len(str(len(self.files))) + 2

        for idx, fn in enumerate(self.files):
            self.audio_list.add_item(f"{str(idx).center(digits)}| {fn}")
            # Actually there is *add_item_list* but I think this is more clean.

        self.update_meta()

    def wrapper(self):
        self.progress_blk.set_text("a")
        return self.update_meta()

    # TODO: add exception handling later
    # TODO: fetch metadata area's physical size and put ellipsis accordingly.
    def update_meta(self):
        # clear meta first
        self.meta_list.clear()

        # Extract metadata
        ordered = extract_metadata(self.abs_dir(self.current))

        # calculate average key length - in case it's too long. Maybe violation of KISS.
        key_average = sum(map(len, ordered.keys())) // len(ordered)

        for key, val in ((k, v) for k, v in ordered.items() if v):
            formatted = key[::key_average - len(self.ellipsis_)] + self.ellipsis_
            self.meta_list.add_item(f"{formatted.ljust(key_average)}: {val}")

        # redraw scroll_view
        self.update_widget(self.audio_list)

    @staticmethod
    def update_widget(target):
        # updating target to re-draw over overlapping widgets.
        target.set_border_color(target.get_border_color())

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
