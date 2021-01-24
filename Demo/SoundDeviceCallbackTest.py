import sounddevice as sd
import soundfile as sf
import threading


def start_audio_stream(audio_file):
    event_ = threading.Event()
    modifier_mul = 2
    modifier_add = 0

    def finish_cb():
        print("Stopped!")
        event_.set()

    with sf.SoundFile(audio_file) as audio:
        last_frame = -1
        # audio.seek(9300000)

        def callback(data_out, frames: int, time, status: sd.CallbackFlags) -> None:
            nonlocal last_frame
            assert not status

            data_out[:] = audio.read(frames, fill_value=0) * modifier_mul

            if last_frame == (current_frame := audio.tell()):
                raise sd.CallbackAbort

            last_frame = current_frame
            print(frames, current_frame, audio.frames, modifier_mul, modifier_add)

        with sd.OutputStream(
            samplerate=audio.samplerate,
            channels=audio.channels,
            callback=callback,
            finished_callback=finish_cb,
        ):
            event_.wait()


if __name__ == "__main__":
    audio_location = r"E:\github\CUIAudioPlayer\audio_files\Higher's High   ナナヲアカリ.ogg"
    start_audio_stream(audio_location)
