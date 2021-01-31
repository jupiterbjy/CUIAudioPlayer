import abc
import sounddevice as sd
import soundfile as sf
import tinytag
from typing import Callable, Type, Union, Tuple
"""
This is Abstract Base classes only for typing purposes to prevent circular import.
Even though I'm one making this, I can't remember my things without such ample IDE supports.
"""


class AudioInfo:
    # Faking it into class attribute, but actually instance attribute.
    audio_dir: str
    loaded_data: sf.SoundFile

    total_frame: int
    tag_data: Union[tinytag.Ogg, tinytag.Wave, tinytag.Flac, tinytag.ID3]

    duration_tag: float
    title: str


class StreamState(abc.ABC):
    @staticmethod
    def start_stream(stream_manager: "StreamManagerABC"):
        raise NotImplementedError()

    @staticmethod
    def stop_stream(stream_manager: "StreamManagerABC"):
        raise NotImplementedError()

    @staticmethod
    def pause_stream(stream_manager: "StreamManagerABC"):
        raise NotImplementedError()

    @staticmethod
    def load_stream(stream_manager: "StreamManagerABC", audio_dir: str):
        raise NotImplementedError()


class StreamManagerABC(abc.ABC):
    # Faking it into class attribute, but actually instance attribute.
    audio_info: AudioInfo
    stream: Union[sd.OutputStream, sd.RawStream]

    callback_minimum_cycle: int

    stream_cb: Callable
    finished_cb: Callable

    stream_state: Type[StreamState]

    multiplier: float
    volume_range: Tuple[float, float]
    step: float

    stop_flag: bool

    def new_state(self, status: Type[StreamState]) -> None:
        pass

    def load_stream(self, audio_location) -> None:
        # Might need to return depending on success or failure.
        pass

    def start_stream(self) -> None:
        pass

    def stop_stream(self) -> None:
        pass

    def pause_stream(self) -> None:
        pass

    def volume_up(self) -> None:
        pass

    def volume_down(self) -> None:
        pass

