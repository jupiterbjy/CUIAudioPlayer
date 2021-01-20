import sounddevice as sd
import soundfile as sf
import threading
import itertools
from tinytag import TinyTag, Ogg, ID3, Flac, Wave
from typing import Callable, Tuple, Union

from LoggingConfigurator import logger


# TODO: add logging tab with stacked widget or something
def play_audio(
    audio_location: str,
    stream_callback: Callable = None,
    finished_callback: Callable = None,
):
    # Really want to run this in event loop, that's sad.
    """
    Intended to run on threads, to not block curses loops.

    :param audio_location: Location of audio file in str
    :param stream_callback:
    :param finished_callback:
    :return:
    """

    event_ = threading.Event()

    if stream_callback is None:

        def stream_callback():
            pass

    if finished_callback is None:

        def finished_callback():
            pass

    def finish_cb() -> None:
        finished_callback()
        event_.set()

    with sf.SoundFile(audio_location) as audio_fp:
        last_frame = -1
        dtype = sd.default.dtype[1]

        def callback(data_out, frames: int, time, status: sd.CallbackFlags) -> None:
            nonlocal last_frame

            assert not status
            assert last_frame != (current_frame := audio_fp.tell())

            last_frame = current_frame

            audio_fp.buffer_read_into(data_out, dtype)
            stream_callback()

        with sd.OutputStream(
            samplerate=audio_fp.samplerate,
            channels=audio_fp.channels,
            callback=callback,
            finished_callback=finish_cb,
        ):
            event_.wait()


def play_audio_not_safe(
    audio_location: str,
    stream_callback: Callable = None,
    finished_callback: Callable = None,
) -> Tuple[sf.SoundFile, sd.OutputStream]:
    # Really want to run this in event loop, that's sad.
    """
    Intended to run normally in main threads.
    User should make sure to close and drop reference for gc on both of returns.

    :param audio_location: Location of audio file in str
    :param stream_callback:
    :param finished_callback:
    :return: sf.SoundFile, sd.OutputStream
    """

    if stream_callback is None:

        def stream_callback(audio_file, frames):
            pass

    if finished_callback is None:

        def finished_callback():
            pass

    def finish_cb() -> None:
        logger.debug("Playback finished.")
        audio_fp.close()
        finished_callback()

    audio_fp = sf.SoundFile(audio_location)

    def wrapper():
        # gather names closer to callback function in the hope of reducing call overhead.

        last_frame = -1
        audio_file = audio_fp
        dtype = sd.default.dtype[1]
        duration = int(TinyTag.get(audio_location).as_dict()['duration'])
        next_callback_run = 3

        def callback(data_out, frames: int, time, status: sd.CallbackFlags) -> None:
            nonlocal last_frame, stream_callback, next_callback_run

            assert not status
            # assert last_frame != (current_frame := audio_fp.tell())
            try:
                if last_frame == (current_frame := audio_file.tell()):
                    raise sd.CallbackStop
            except RuntimeError as err:
                raise sd.CallbackStop from err

            last_frame = current_frame

            audio_file.buffer_read_into(data_out, dtype)
            if next_callback_run == 0:
                stream_callback(audio_fp, current_frame, duration)
                next_callback_run = 3
            else:
                next_callback_run -= 1
            # Stream callback signature for other functions

        return callback

    stream = sd.OutputStream(
        samplerate=audio_fp.samplerate,
        channels=audio_fp.channels,
        callback=wrapper(),
        finished_callback=finish_cb,
    )

    return audio_fp, stream


class StreamManager:
    def __init__(self, stream_callback: Callable = None, finished_callback: Callable = None, callback_every_n=3):
        self.audio_dir = ""
        self.callback_minimum_cycle = callback_every_n

        self.stream_cb = stream_callback if stream_callback else lambda x, y, z: None
        self.finished_cb = finished_callback if stream_callback else lambda: None

        self.audio_data: sf.SoundFile = None
        self.tag_data: Union[TinyTag, ID3, Ogg, Wave, Flac] = None

        self.total_frame: int = None
        self.duration_tag: int = None

        self.stream: sd.OutputStream = None
        self.abort = False
        self.paused = True

    def stream_callback_closure(self) -> Callable:
        # Collecting names here to reduce call overhead.
        last_frame = -1
        dtype = sd.default.dtype[1]
        audio_ref = self.audio_data
        callback = self.stream_cb
        duration = self.duration_tag

        cycle = itertools.cycle((not n for n in range(self.callback_minimum_cycle)))
        # this looks much neat than changing variable inside callback.

        def stream_cb(data_out, frames: int, time, status: sd.CallbackFlags) -> None:
            nonlocal last_frame

            assert not status

            # changing order would results in micro bit faster runs, but IDE complains so..
            if last_frame == (current_frame := audio_ref.tell()) or self.abort:
                raise sd.CallbackStop

            audio_ref.buffer_read_into(data_out, dtype)
            if next(cycle):
                callback(audio_ref, current_frame, duration)
            # Stream callback signature for other functions

        return stream_cb

    def finished_callback_wrapper(self):
        logger.debug(f"Playback finished. State:{'Abort' if self.abort else 'Finished'}")
        self.audio_data.close()
        if not self.abort:
            self.finished_cb()

    def load_new_stream(self, audio_location):
        self.audio_dir = audio_location

        self.audio_data = sf.SoundFile(self.audio_dir)
        self.tag_data = TinyTag.get(self.audio_dir)

        self.total_frame = self.audio_data.frames
        self.duration_tag = round(self.tag_data.duration)

        self.abort = False

        self.stream = sd.OutputStream(
            samplerate=self.audio_data.samplerate,
            channels=self.audio_data.channels,
            callback=self.stream_callback_closure(),
            finished_callback=self.finished_cb
        )

    def start_stream(self):
        self.stream.start()

    def stop_stream(self):
        self.stream.stop()

    def pause_stream(self):
        if self.paused:
            self.start_stream()
        else:
            self.stop_stream()

        self.paused = not self.paused

    def __del__(self):
        self.stream.stop()
        self.audio_data.close()


if __name__ == '__main__':
    def test():
        """
        >>> from SoundModule import StreamManager
        >>> audio_location_ = r"E:\github\CUIAudioPlayer\audio_files\Higher's High   ナナヲアカリ.ogg"
        >>> ref = StreamManager()
        >>> ref.load_new_stream(audio_location_)
        >>> ref.start_stream()
        """

    # Try this in python console. of course change the audio.
