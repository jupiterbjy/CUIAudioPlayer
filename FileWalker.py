import pathlib
# import numpy as np
import soundfile as sf
from tinytag import TinyTag
from typing import Generator, Union, List

try:
    import pydub
except ImportError:
    PY_DUB_ENABLED = False
else:
    import io
    PY_DUB_ENABLED = True


class PathWrapper:
    primary_formats = set("." + key.lower() for key in sf.available_formats().keys())
    secondary_formats = {".m4a", ".mp3"} if PY_DUB_ENABLED else {}
    supported_formats = primary_formats | secondary_formats
    # re_match_pattern = "$|".join(final_supported_formats)
    # subtypes = soundfile.available_subtypes()

    def __init__(self, path: str = "./"):
        self.current_path = pathlib.Path(path).absolute()
        self.audio_file_list: List[pathlib.Path] = []
        self.folder_list: List[pathlib.Path] = []

    def list_audio(self) -> Generator[pathlib.Path, None, None]:
        return (path_obj for path_obj in self.list_file() if path_obj.suffix in self.supported_formats)

    def list_folder(self) -> Generator[pathlib.Path, None, None]:
        """First element will be current folder location. either use next() or list()[1:] to skip it.."""
        return (item for item in self.current_path.glob("*/") if item.is_dir())

    def list_file(self) -> Generator[pathlib.Path, None, None]:
        """Can't use glob as it match folders such as .git"""
        return (item for item in self.current_path.glob("*/") if item.is_file())

    def step_in(self, directory: Union[str, pathlib.Path]):
        """Relative / Absolute paths supported."""

        self.current_path = self.current_path.joinpath(directory)
        return self.current_path

    def step_out(self, depth=1):
        if depth <= 0:
            return self.current_path

        self.current_path = self.current_path.parents[depth - 1]
        return self.current_path

    def fetch_meta(self):
        # This might have to deal the cases such as path changing before generator fires up.
        def generator():
            for file_dir in self.list_audio():
                yield TinyTag.get(file_dir)

        return generator()

    def fetch_tag_data(self):
        def generator():
            for file_dir in self.list_audio():
                yield TinyTag.get(file_dir)

        return generator()

    def __len__(self):
        return len(self.folder_list) + len(self.audio_file_list)

    def __getitem__(self, item: int):
        try:
            return self.folder_list[item]
        except IndexError:
            return self.audio_file_list[item - len(self.folder_list)]

    def index(self, target: Union[str, pathlib.Path]):
        try:
            return len(self.folder_list) + self.audio_file_list.index(target)
        except ValueError:
            # assuming it's pure string directory.
            path_converted = pathlib.Path(target)
            return len(self.folder_list) + self.audio_file_list.index(path_converted)
