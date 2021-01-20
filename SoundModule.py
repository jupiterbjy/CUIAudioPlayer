import sounddevice as sd
import soundfile as sf
import threading
from tinytag import TinyTag
from typing import Callable, Tuple

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
        finished_callback()
        audio_fp.close()

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


def stop_audio():
    sd.stop()
