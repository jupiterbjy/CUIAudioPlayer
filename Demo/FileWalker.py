import os
import pathlib
import itertools
import numpy as np
import soundfile as sf
from tinytag import TinyTag
from typing import Generator, Union

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

    def list_audio(self) -> Generator[pathlib.Path, None, None]:
        return (path_obj for path_obj in self.list_file() if path_obj.suffix in self.supported_formats)

    def list_folder(self) -> Generator[pathlib.Path, None, None]:
        """First element will be current folder location. either use next() or list()[1:] to skip it.."""
        return self.list_file("**/")

    def list_file(self, pattern: str = "*.*") -> Generator[pathlib.Path, None, None]:
        """This doesn't include folders!"""

        return self.current_path.glob(pattern)

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

    def fetch_sf_data(self):
        def generator():
            for file_dir in self.list_audio():
                try:
                    yield sf.SoundFile(file_dir)

                except RuntimeError:
                    if PY_DUB_ENABLED:
                        # https://stackoverflow.com/questions/53633177
                        loaded = pydub.AudioSegment.from_file(file_dir)
                        np_arr = np.array(loaded.get_array_of_samples())

                        yield np_arr if loaded.channels != 1 else np_arr.reshape((-1, loaded.channels))
                    else:
                        continue

        return generator()
