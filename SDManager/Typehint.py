import abc
import sounddevice as sd
import soundfile as sf
import tinytag
from typing import Callable, Type, Union
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
    def start_stream(stream_manager: "StreamManager"):
        raise NotImplementedError()

    @staticmethod
    def stop_stream(stream_manager: "StreamManager"):
        raise NotImplementedError()

    @staticmethod
    def pause_stream(stream_manager: "StreamManager"):
        raise NotImplementedError()

    @staticmethod
    def load_stream(stream_manager: "StreamManager", audio_dir: str):
        raise NotImplementedError()


class StreamManager(abc.ABC):
    # Faking it into class attribute, but actually instance attribute.
    audio_info: AudioInfo
    stream: Union[sd.OutputStream, sd.RawStream]
    callback_minimum_cycle: int
    stream_cb: Callable
    finished_cb: Callable
    stream_state: Type[StreamState]

    def new_state(self, status: Type[StreamState]):
        pass

    def load_stream(self, audio_location):
        pass

    def start_stream(self):
        pass

    def stop_stream(self):
        pass

    def pause_stream(self):
        pass
