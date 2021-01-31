import sounddevice as sd

from .Typehint import StreamState, StreamManagerABC
from .AudioObject import AudioInfo
from .Callbacks import stream_callback_closure, finished_callback_wrapper
from LoggingConfigurator import logger


"""
Finite-State Machine implementation, idea from Python Cookbook 3E.
"""


class AudioUnloadedState(StreamState):
    @staticmethod
    def start_stream(stream_manager: "StreamManagerABC"):
        raise FileNotFoundError("No audio file is loaded.")

    @staticmethod
    def stop_stream(stream_manager: "StreamManagerABC"):
        raise FileNotFoundError("No audio file is loaded.")

    @staticmethod
    def pause_stream(stream_manager: "StreamManagerABC"):
        raise FileNotFoundError("No audio file is loaded.")

    @staticmethod
    def load_stream(stream_manager: "StreamManagerABC", audio_dir: str):
        # noinspection PyAttributeOutsideInit
        try:
            stream_manager.audio_info = AudioInfo(audio_dir)
        except Exception as err:
            logger.critical(f"Failed to load <{audio_dir}>!")
            raise err

        # noinspection PyAttributeOutsideInit
        stream_manager.stream = sd.OutputStream(
            samplerate=stream_manager.audio_info.loaded_data.samplerate,
            channels=stream_manager.audio_info.loaded_data.channels,
            callback=stream_callback_closure(stream_manager),
            finished_callback=finished_callback_wrapper(stream_manager, StreamStoppedState),
        )

        stream_manager.new_state(StreamStoppedState)


class StreamStoppedState(StreamState):
    @staticmethod
    def stop_stream(stream_manager: "StreamManagerABC"):
        raise RuntimeError("Stream is not active.")

    @staticmethod
    def pause_stream(stream_manager: "StreamManagerABC"):
        stream_manager.stream.stop()
        # raise RuntimeError("Stream is not active.")

    @staticmethod
    def start_stream(stream_manager: "StreamManagerABC"):
        logger.debug("Starting Stream.")
        try:
            stream_manager.stream.start()
        except Exception as err:
            logger.critical(f"Got {type(err)}")
            raise
        else:
            stream_manager.new_state(StreamPlayingState)

    @staticmethod
    def load_stream(stream_manager: "StreamManagerABC", audio_dir: str):
        logger.debug("Loading new file.")
        AudioUnloadedState.load_stream(stream_manager, audio_dir)


class StreamPlayingState(StreamState):
    @staticmethod
    def stop_stream(stream_manager: "StreamManagerABC"):
        logger.debug("Stopping Stream and resetting playback progress.")
        stream_manager.stream.stop()
        stream_manager.audio_info.loaded_data.seek(0)
        # AudioUnloadedState.load_stream(stream_manager, stream_manager.audio_info.audio_dir)

    @staticmethod
    def pause_stream(stream_manager: "StreamManagerABC"):
        logger.debug("Pausing Stream.")
        stream_manager.stream.stop()
        stream_manager.new_state(StreamPausedState)

    @staticmethod
    def start_stream(stream_manager: "StreamManagerABC"):
        raise RuntimeError("Stream already running.")
        # Might need a better choice here. Merging with pause_stream or not.
        # I guess implementing `stop and play this instead` would be better done UI class side.

    @staticmethod
    def load_stream(stream_manager: "StreamManagerABC", audio_dir: str):
        logger.debug("Stopping and loading new audio.")
        StreamPlayingState.stop_stream(stream_manager)
        AudioUnloadedState.load_stream(stream_manager, audio_dir)


class StreamPausedState(StreamState):
    @staticmethod
    def stop_stream(stream_manager: "StreamManagerABC"):
        logger.debug("Delegating to: StreamPlayingState.stop_stream")
        StreamPlayingState.stop_stream(stream_manager)

    @staticmethod
    def pause_stream(stream_manager: "StreamManagerABC"):
        logger.debug("Resuming Stream")
        stream_manager.new_state(StreamPlayingState)
        stream_manager.stream.start()

    @staticmethod
    def start_stream(stream_manager: "StreamManagerABC"):
        raise RuntimeError("Stream is paused, stop stream first.")

    @staticmethod
    def load_stream(stream_manager: "StreamManagerABC", audio_dir: str):
        pass
