import pathlib
import soundfile as sf
from tinytag import TinyTag
from typing import Generator, Union, List

from LoggingConfigurator import logger

try:
    import pydub
except ImportError:
    PY_DUB_ENABLED = False
else:
    import io
    PY_DUB_ENABLED = True


# TODO: separate audio related logic from pathwrapper via subclass
class PathWrapper:
    primary_formats = set("." + key.lower() for key in sf.available_formats().keys())
    secondary_formats = {".m4a", ".mp3"} if PY_DUB_ENABLED else set()
    supported_formats = primary_formats | secondary_formats
    supported_formats = supported_formats | set(key.upper() for key in supported_formats)

    # re_match_pattern = "$|".join(final_supported_formats)
    # subtypes = soundfile.available_subtypes()
    logger.debug(f"Available formats: {supported_formats}")

    # Considering idx 0 to always be step out!

    def __init__(self, path: str = "./"):
        self.current_path = pathlib.Path(path).absolute()
        self.audio_file_list: List[pathlib.Path] = []
        self.folder_list: List[pathlib.Path] = []

    def list_audio(self) -> Generator[pathlib.Path, None, None]:
        yield from (path_obj for path_obj in self.list_file() if path_obj.suffix in self.supported_formats)

    def list_folder(self) -> Generator[pathlib.Path, None, None]:
        """
        First element will be current folder location. either use next() or list()[1:] to skip it.
        """

        yield self.current_path.parent
        yield from (path_ for path_ in self.current_path.iterdir() if path_.is_dir())

    def list_file(self) -> Generator[pathlib.Path, None, None]:
        """
        Can't use glob as it match folders such as .git, using pathlib.Path object instead.
        """

        yield from (item for item in self.current_path.iterdir() if item.is_file())

    def step_in(self, directory_idx: int):
        """
        Relative / Absolute paths supported.
        """

        try:
            self.current_path = self.folder_list[directory_idx]
        except IndexError as err:
            raise NotADirectoryError(f"Directory index {directory_idx} does not exist!") from err

        self.refresh_list()
        return self.current_path

    def step_out(self):

        if self.current_path == self.current_path.parent:
            return self.current_path

        self.current_path = self.current_path.parent

        self.refresh_list()
        return self.current_path

    def refresh_list(self):
        self.audio_file_list.clear()
        self.folder_list.clear()

        self.audio_file_list.extend(self.list_audio())
        self.folder_list.extend(self.list_folder())

    def fetch_meta(self):
        # This might have to deal the cases such as path changing before generator fires up.
        for file_dir in self.list_audio():
            yield TinyTag.get(file_dir)

    def fetch_tag_data(self):
        for file_dir in self.list_audio():
            yield TinyTag.get(file_dir)

    def __len__(self):
        return len(self.folder_list) + len(self.audio_file_list)

    def __getitem__(self, item: int):
        # logger.debug(f"idx: {item}, len_f: {len(self.folder_list)}, len_a: {len(self.audio_file_list)}")
        try:
            return self.folder_list[item]
        except IndexError as err:
            if len(self) == 0:
                raise IndexError("No file or folder to index in current directory.") from err

            return self.audio_file_list[item - len(self.folder_list)]

    def index(self, target: Union[str, pathlib.Path]):
        path_ = pathlib.Path(target)
        try:
            return len(self.folder_list) + self.audio_file_list.index(path_)
        except ValueError as err:
            raise IndexError(f"Cannot find given target '{path_.as_posix()}'!") from err

