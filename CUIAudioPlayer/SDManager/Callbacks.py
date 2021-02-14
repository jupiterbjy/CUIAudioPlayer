"""
Callback definitions for sounddevice streams.
"""

from __future__ import annotations
from typing import TYPE_CHECKING, Callable, Type
import itertools
import sounddevice as sd
from LoggingConfigurator import logger

if TYPE_CHECKING:
    from .StreamManager import StreamManager
    from .StreamStates import StreamState


def stream_callback_closure(stream_manager: StreamManager, raw=False) -> Callable:
    # Collecting names here to reduce call overhead.
    last_frame = -1
    dtype = sd.default.dtype[1]
    audio_ref = stream_manager.audio_info.loaded_data
    channel = audio_ref.channels
    callback = stream_manager.stream_cb
    audio_info = stream_manager.audio_info

    cycle = itertools.cycle((not n for n in range(stream_manager.callback_minimum_cycle)))

    # to reduce load, custom callback will be called every n-th iteration of this generator.

    def stream_cb(data_out, frames: int, time, status: sd.CallbackFlags) -> None:
        nonlocal last_frame, stream_manager
        assert not status

        read = audio_ref.read(frames, fill_value=0) * stream_manager.multiplier
        try:
            data_out[:] = read
        except ValueError:
            try:
                data_out[:] = read.reshape(read.shape[0], 1)
            except Exception:
                stream_manager.stop_flag = True
                raise

        if last_frame == (current_frame := audio_ref.tell()):
            raise sd.CallbackAbort

        last_frame = current_frame

        if next(cycle):
            callback(audio_info, current_frame)
            # Stream callback signature for user-supplied callbacks
            # Providing current_frame and duration to reduce call overhead from user-callback side.

    def stream_cb_raw(data_out, frames: int, time, status: sd.CallbackFlags) -> None:
        nonlocal last_frame

        try:
            assert not status
        except AssertionError:
            logger.critical(str(status))
            raise

        if (written := audio_ref.buffer_read_into(data_out, dtype)) < frames:
            data_out[written:] = [[0.0] * channel for _ in range(frames - written)]
            raise sd.CallbackStop

        if last_frame == (current_frame := audio_ref.tell()):
            raise sd.CallbackAbort

        last_frame = current_frame

        if next(cycle):
            callback(audio_info, current_frame)
            # Stream callback signature for user-supplied callbacks
            # Providing current_frame and duration to reduce call overhead from user-callback side.

    logger.debug(f"Using {'Raw' if raw else 'Numpy'} callback.")
    return stream_cb_raw if raw else stream_cb


def finished_callback_wrapper(stream_manager: StreamManager, new_next_state: Type[StreamState]):
    def callback():
        logger.debug(f"Playback finished. Stop flag: {stream_manager.stop_flag}")
        stream_manager.new_state(new_next_state)

        if not stream_manager.stop_flag:
            stream_manager.finished_cb()

    return callback
