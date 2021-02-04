import sounddevice as sd
from typing import Callable, Type

from LoggingConfigurator import logger
from .StreamStates import StreamState, AudioUnloadedState, AudioInfo
from .Typehint import StreamManagerABC


class StreamManager(StreamManagerABC):
    def __init__(self, stream_callback: Callable = None, finished_callback: Callable = None, callback_every_n=2):
        self.callback_minimum_cycle = callback_every_n

        self.stream_cb = stream_callback if stream_callback else lambda audio_info, current_frame: None
        self.finished_cb = finished_callback if finished_callback else lambda: None

        # noinspection PyTypeChecker
        self.audio_info: AudioInfo = None

        # noinspection PyTypeChecker
        self.stream: sd.OutputStream = None

        self.multiplier = 1
        self.volume_range = 0, 2
        self.step = 0.25
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

    def stop_stream(self, set_flag=True):
        self.stop_flag = False if set_flag else self.stop_flag
        return self.stream_state.stop_stream(self)

    def pause_stream(self):
        self.stop_flag = not self.stop_flag
        return self.stream_state.pause_stream(self)

    def volume_up(self):
        if (n := self.multiplier + self.step) <= self.volume_range[1]:
            self.multiplier = n

    def volume_down(self):
        if (n := self.multiplier - self.step) >= self.volume_range[0]:
            self.multiplier = n

    def __del__(self):
        try:
            self.stream_state.stop_stream(self)
        except (RuntimeError, FileNotFoundError):
            pass


if __name__ == '__main__':
    def test():
        from StreamManager import StreamManagerABC
        audio_location_1 = r"E:\github\CUIAudioPlayer\audio_files\short_sample_okayu_rejection.ogg"
        audio_location_2 = r"E:\github\CUIAudioPlayer\audio_files\Higher's High   ナナヲアカリ.ogg"
        ref = StreamManagerABC()
        ref.load_stream(audio_location_2)
        ref.start_stream()

        # Originally meant to hold doctest, but it was inconvenience to copy-pasting so remove it.

    # Try this in python console. of course change the audio.
