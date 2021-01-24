import sounddevice as sd
import soundfile as sf
import itertools
from numpy import ndarray


# So technically I can make an equalizer out of this. But idk how.
class VolumeChangeDemonstrator:
    def __init__(self):
        self.multiplier = 1
        self.offset = 0

        # noinspection PyTypeChecker
        self.audio_file: sf.SoundFile = None

        # noinspection PyTypeChecker
        self.stream: sd.OutputStream = None

    def load_audio(self, audio_dir: str):
        self.audio_file = sf.SoundFile(audio_dir)

    def callback_closure(self):
        last_frame = -1
        output_limiter = itertools.cycle((not n for n in range(10)))

        def callback(data_out: ndarray, frames: int, time, status: sd.CallbackFlags) -> None:
            nonlocal last_frame
            assert not status

            data_out[:] = self.audio_file.read(frames, fill_value=0) * self.multiplier + self.offset

            if last_frame == (current_frame := self.audio_file.tell()):
                raise sd.CallbackAbort

            last_frame = current_frame

            if next(output_limiter):
                print(f"Playback: {current_frame * 100 // self.audio_file.frames}%, "
                      f"Multiplier: {self.multiplier}, Offset: {self.offset}")

        return callback

    def play(self):
        self.stream = sd.OutputStream(
            samplerate=self.audio_file.samplerate,
            channels=self.audio_file.channels,
            callback=self.callback_closure()
        )
        self.stream.start()

    def __del__(self):
        self.stream.close(ignore_errors=True)
