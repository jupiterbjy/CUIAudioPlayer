import sounddevice as sd
import soundfile as sf
import itertools
from tinytag import TinyTag
from typing import Callable, Type

from LoggingConfigurator import logger


class StreamState:
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


class AudioUnloadedState(StreamState):
    @staticmethod
    def start_stream(stream_manager: "StreamManager"):
        raise FileNotFoundError("No audio file is loaded.")

    @staticmethod
    def stop_stream(stream_manager: "StreamManager"):
        raise FileNotFoundError("No audio file is loaded.")

    @staticmethod
    def pause_stream(stream_manager: "StreamManager"):
        raise FileNotFoundError("No audio file is loaded.")

    @staticmethod
    def load_stream(stream_manager: "StreamManager", audio_dir: str):
        # noinspection PyAttributeOutsideInit
        try:
            stream_manager.audio_info = AudioInfo(sf.SoundFile(audio_dir))
        except Exception as err:
            logger.critical(f"Failed to load <{audio_dir}>!")
            raise err

        # noinspection PyAttributeOutsideInit
        stream_manager.stream = sd.OutputStream(
            samplerate=stream_manager.audio_info.loaded_data.samplerate,
            channels=stream_manager.audio_info.loaded_data.channels,
            callback=AudioUnloadedState.stream_callback_closure(stream_manager),
            finished_callback=AudioUnloadedState.finished_callback_wrapper(stream_manager),
        )

        stream_manager.new_state(StreamStoppedState)

    @staticmethod
    def stream_callback_closure(stream_manager: "StreamManager") -> Callable:
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
            nonlocal last_frame
            assert not status

            if (written := audio_ref.buffer_read_into(data_out, dtype)) < frames:
                logger.debug(f"Writing underflow buffer - {written} frames written.")
                data_out[written:] = [[0.0] * channel for _ in range(frames - written)]
                raise sd.CallbackStop

            if last_frame == (current_frame := audio_ref.tell()):
                raise sd.CallbackAbort

            last_frame = current_frame

            if next(cycle):
                callback(audio_info, current_frame)
                # Stream callback signature for user-supplied callbacks
                # Providing current_frame and duration to reduce call overhead from user-callback side.

        return stream_cb

    @staticmethod
    def finished_callback_wrapper(stream_manager: "StreamManager"):
        def callback():
            logger.debug(f"Playback finished.")
            stream_manager.new_state(StreamStoppedState)
            stream_manager.finished_cb()

        return callback


class StreamStoppedState(StreamState):
    @staticmethod
    def stop_stream(stream_manager: "StreamManager"):
        raise RuntimeError("Stream is not active.")

    @staticmethod
    def pause_stream(stream_manager: "StreamManager"):
        raise RuntimeError("Stream is not active.")

    @staticmethod
    def start_stream(stream_manager: "StreamManager"):
        logger.debug("Starting Stream.")
        try:
            stream_manager.stream.start()
        except Exception as err:
            logger.critical(f"Got {type(err)}")
            raise
        else:
            stream_manager.new_state(StreamPlayingState)

    @staticmethod
    def load_stream(stream_manager: "StreamManager", audio_dir: str):
        logger.debug("Loading new file.")
        AudioUnloadedState.load_stream(stream_manager, audio_dir)


class StreamPlayingState(StreamState):
    @staticmethod
    def stop_stream(stream_manager: "StreamManager"):
        logger.debug("Stopping Stream and resetting playback progress.")
        stream_manager.stream.stop()
        stream_manager.audio_info.loaded_data.seek(0)
        # AudioUnloadedState.load_stream(stream_manager, stream_manager.audio_info.audio_dir)

    @staticmethod
    def pause_stream(stream_manager: "StreamManager"):
        logger.debug("Pausing Stream.")
        stream_manager.stream.stop()
        stream_manager.new_state(StreamPausedState)

    @staticmethod
    def start_stream(stream_manager: "StreamManager"):
        raise RuntimeError("Stream already running.")
        # Might need a better choice here. Merging with pause_stream or not.
        # I guess implementing `stop and play this instead` would be better done UI class side.

    @staticmethod
    def load_stream(stream_manager: "StreamManager", audio_dir: str):
        logger.debug("Stopping and loading new audio.")
        StreamPlayingState.stop_stream(stream_manager)
        AudioUnloadedState.load_stream(stream_manager, audio_dir)


class StreamPausedState(StreamState):
    @staticmethod
    def stop_stream(stream_manager: "StreamManager"):
        logger.debug("Delegating to: StreamPlayingState.stop_stream")
        StreamPlayingState.stop_stream(stream_manager)

    @staticmethod
    def pause_stream(stream_manager: "StreamManager"):
        logger.debug("Resuming Stream")
        stream_manager.new_state(StreamPlayingState)
        stream_manager.stream.start()

    @staticmethod
    def start_stream(stream_manager: "StreamManager"):
        raise RuntimeError("Stream is paused, stop stream first.")

    @staticmethod
    def load_stream(stream_manager: "StreamManager", audio_dir: str):
        pass


class AudioInfo:
    def __init__(self, audio_fp: sf.SoundFile):
        self.loaded_data = audio_fp

        self.audio_dir = audio_fp.name
        self.total_frame = audio_fp.frames
        self.tag_data = TinyTag.get(self.audio_dir)

        # saving reference for tiny bit faster access
        self.duration_tag = round(self.tag_data.duration, 1)
        self.title = self.tag_data.title

        logger.debug(f"Audio detail - Title: {self.title}, Duration: {self.duration_tag}")

    def __del__(self):
        self.loaded_data.close()


class StreamManager:
    def __init__(self, stream_callback: Callable = None, finished_callback: Callable = None, callback_every_n=2):
        self.callback_minimum_cycle = callback_every_n

        self.stream_cb = stream_callback if stream_callback else lambda audio_info, current_frame: None
        self.finished_cb = finished_callback if finished_callback else lambda: None

        # noinspection PyTypeChecker
        self.audio_info: AudioInfo = None

        # noinspection PyTypeChecker
        self.stream: sd.OutputStream = None

        self.stream_state = AudioUnloadedState

    def new_state(self, status: Type[StreamState]):
        logger.debug(f"Switching state: {self.stream_state} -> {status}")
        self.stream_state = status

    def load_stream(self, audio_location):
        return self.stream_state.load_stream(self, audio_location)

    def start_stream(self):
        return self.stream_state.start_stream(self)

    def stop_stream(self):
        return self.stream_state.stop_stream(self)

    def pause_stream(self):
        return self.stream_state.pause_stream(self)

    def __del__(self):
        try:
            self.stream_state.stop_stream(self)
        except (RuntimeError, FileNotFoundError):
            pass


if __name__ == '__main__':
    def test():
        from SoundModule import StreamManager
        audio_location_1 = r"E:\github\CUIAudioPlayer\audio_files\short_sample_okayu_rejection.ogg"
        audio_location_2 = r"E:\github\CUIAudioPlayer\audio_files\Higher's High   ナナヲアカリ.ogg"
        ref = StreamManager()
        ref.load_stream(audio_location_2)
        ref.start_stream()

        # Originally meant to hold doctest, but it was inconvenience to copy-pasting so remove it.

    # Try this in python console. of course change the audio.
