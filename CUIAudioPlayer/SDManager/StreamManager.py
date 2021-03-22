from __future__ import annotations
from typing import TYPE_CHECKING, Callable, Type
if TYPE_CHECKING:
    from .AudioObject import AudioInfo
    import sounddevice as sd

from .StreamStates import StreamState, AudioUnloadedState
from LoggingConfigurator import logger


class StreamManager:
    def __init__(self, stream_callback: Callable = None, finished_callback: Callable = None, callback_every_n=2):

        self.callback_minimum_cycle = callback_every_n

        self.stream_cb = stream_callback if stream_callback else lambda audio_info, current_frame: None
        self.finished_cb = finished_callback if finished_callback else lambda: None

        # noinspection PyTypeChecker
        self.audio_info: AudioInfo = None

        # noinspection PyTypeChecker
        self.stream: sd.OutputStream = None

        self.multiplier = 1
        self.stream_state = AudioUnloadedState
        self.stop_flag = False

    def new_state(self, status: Type[StreamState]):
        logger.debug(f"Switching state: {self.stream_state} -> {status}")
        self.stream_state = status

    def load_stream(self, audio_location):
        return self.stream_state.load_stream(self, audio_location)

    def start_stream(self):
        self.stop_flag = False
        return self.stream_state.start_stream(self)

    def stop_stream(self, run_finished_callback=True):
        self.stop_flag = True if run_finished_callback else self.stop_flag
        return self.stream_state.stop_stream(self)

    def pause_stream(self):
        self.stop_flag = not self.stop_flag
        return self.stream_state.pause_stream(self)

    def __del__(self):
        try:
            self.stream_state.stop_stream(self)
        except (RuntimeError, FileNotFoundError):
            pass
