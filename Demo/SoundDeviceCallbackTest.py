import sounddevice as sd
import soundfile as sf
import threading


def start_audio_stream(audio_file):
    event_ = threading.Event()

    def finish_cb(*args):
        print("Stopped! ", args)
        event_.set()

    with sf.SoundFile(audio_file) as audio:

        last_frame = -1

        def callback(data_out, frames: int, time, status: sd.CallbackFlags) -> None:
            nonlocal last_frame

            assert not status

            assert last_frame != (current_frame := audio.tell())

            last_frame = current_frame

            audio.buffer_read_into(data_out, sd.default.dtype[1])
            print(frames, last_frame, audio.frames)

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
