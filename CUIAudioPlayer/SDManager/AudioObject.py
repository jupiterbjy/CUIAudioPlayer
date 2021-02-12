import soundfile as sf
from tinytag import TinyTag

from LoggingConfigurator import logger


class AudioInfo:
    def __init__(self, audio_dir: str):
        self.audio_dir = audio_dir
        self.loaded_data = sf.SoundFile(self.audio_dir)

        self.total_frame = self.loaded_data.frames
        self.tag_data = TinyTag.get(self.audio_dir)

        # saving reference for tiny bit faster access
        try:
            self.duration_tag = round(self.tag_data.duration, 1)
        except TypeError:
            logger.warning(f"No tag 'duration' exists, calculating estimate.")
            self.duration_tag = round(self.loaded_data.frames / self.loaded_data.samplerate, 1)

        self.title = self.tag_data.title

        logger.debug(f"Audio detail - Title: {self.title}, Duration: {self.duration_tag}")

    def __del__(self):
        self.loaded_data.close()
