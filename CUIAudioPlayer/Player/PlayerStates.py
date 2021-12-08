"""
Implementation of state machine using __class__ attribute manipulation from Python Cookbook 3E.
"""

from __future__ import annotations
from typing import TYPE_CHECKING

from LoggingConfigurator import logger
from SDManager.StreamManager import StreamManager, NoAudioPlayingError

if TYPE_CHECKING:
    from .PlayerLogic import AudioPlayer


class PlayerStates:
    """
    Player state base class.
    """

    @staticmethod
    def on_file_click(audio_player: AudioPlayer):
        """
        Action to do when *audio list* widget is accessed.
        """

        if audio_player.path_wrapper[audio_player.selected_idx] in audio_player.path_wrapper.folder_list:
            audio_player._clear_meta()
        else:
            audio_player._update_meta()

    @staticmethod
    def on_next_track_click(audio_player: AudioPlayer):
        """
        Action to do when *next track* button is pressed.
        """

    @staticmethod
    def on_previous_track_click(audio_player: AudioPlayer):
        """
        Action to do when *previous track* button is pressed.
        """

    @staticmethod
    def on_stop_click(audio_player: AudioPlayer):
        """
        Action to do when *stop* button is pressed.
        """

        try:
            audio_player.stream.stop_stream()
        except (RuntimeError, FileNotFoundError, NoAudioPlayingError):
            return

        with audio_player.maintain_current_view():
            # revert texts
            audio_player.refresh_list(search_files=False)
            try:
                audio_player.mark_as_stopped(audio_player.current_playing_idx)
            except IndexError:
                # playing audio is not in current dir, ignore
                pass
            audio_player.write_info("")

        audio_player.player_state = AudioStopped

        reference = audio_player.stream.audio_info

        # Trigger playback callback to display paused state
        callback = audio_player.show_progress_wrapper(paused=True)
        callback(reference, reference.loaded_data.tell())

    @staticmethod
    def on_reload_click(audio_player: AudioPlayer):
        """
        Action to do when *reload* button is pressed.
        """

        PlayerStates.on_stop_click(audio_player)

        # clear widgets

        for widget in audio_player.clear_target:
            widget.clear()

        audio_player.stream = StreamManager(audio_player.show_progress_wrapper(), audio_player.play_next)
        audio_player.refresh_list(search_files=True)
        audio_player.volume_callback()

        audio_player.player_state = AudioUnloaded

    @staticmethod
    def on_audio_list_enter_press(audio_player: AudioPlayer):
        """
        Enters if selected item is directory. Else will stop current track and play selected track.
        """

        if audio_player.selected_idx_path.is_dir():
            audio_player.path_wrapper.step_in(audio_player.selected_idx)
            # PlayerStates.on_reload_click(audio_player)
            audio_player.refresh_list(search_files=True)
        else:
            # force play audio
            with audio_player.maintain_current_view():
                try:
                    audio_player.stream.stop_stream()
                except (RuntimeError, FileNotFoundError, NoAudioPlayingError) as err:
                    logger.warning(str(err))

                if audio_player.play_stream():
                    try:
                        audio_player.mark_as_playing(audio_player.current_playing_idx)
                    except IndexError:
                        pass
                    audio_player.player_state = AudioRunning

    @staticmethod
    def on_audio_list_space_press(audio_player: AudioPlayer):
        """
        Action to do when *space* is pressed in *audio_list*.
        """

    @staticmethod
    def adjust_playback_left(audio_player: AudioPlayer):
        """
        Moves audio playback cursor to the left.
        """

    @staticmethod
    def adjust_playback_right(audio_player: AudioPlayer):
        """
        Moves audio playback cursor to the right.
        """


class AudioUnloaded(PlayerStates):
    """
    PlayerState with Audio unloaded state.
    """

    @staticmethod
    def on_stop_click(audio_player: AudioPlayer):
        """
        No audio, so no stream to stop.
        """

    @staticmethod
    def on_next_track_click(audio_player: AudioPlayer):
        """
        No audio, no playlist is generated.
        """


class AudioStopped(PlayerStates):
    """
    PlayerState with Audio stopped state.
    """

    @staticmethod
    def on_audio_list_space_press(audio_player: AudioPlayer):
        """
        Starts current track and switch to AudioRunning State.
        """

        with audio_player.maintain_current_view():
            audio_player.stream.start_stream()
            try:
                audio_player.mark_as_playing(audio_player.current_playing_idx)
            except IndexError:
                pass

        audio_player.player_state = AudioRunning

    @staticmethod
    def adjust_playback_left(audio_player: AudioPlayer):
        """
        Moves audio playback cursor to the left. Moves by 5% of total playback
        """

        AudioPaused.adjust_playback_left(audio_player)

    @staticmethod
    def adjust_playback_right(audio_player: AudioPlayer):
        """
        Moves audio playback cursor to the left. Moves by 5% of total playback
        """

        AudioPaused.adjust_playback_right(audio_player)


class AudioRunning(PlayerStates):
    """
    PlayerState with Audio running state.
    """

    @staticmethod
    def on_next_track_click(audio_player: AudioPlayer):
        """
        Skips to next track.
        """

        audio_player.stream.stop_stream(run_finished_callback=False)

    @staticmethod
    def on_audio_list_space_press(audio_player: AudioPlayer):
        """
        Pauses current track and switch to AudioPaused State.
        """

        with audio_player.maintain_current_view():
            audio_player.stream.pause_stream()
            try:
                audio_player.mark_as_paused(audio_player.current_playing_idx)
            except IndexError:
                pass

        audio_player.player_state = AudioPaused

        reference = audio_player.stream.audio_info

        # Trigger playback callback to display paused state
        callback = audio_player.show_progress_wrapper(paused=True)
        callback(reference, reference.loaded_data.tell())

    @staticmethod
    def adjust_playback_left(audio_player: AudioPlayer):
        """
        Moves audio playback cursor to the left. Moves by 5% of total playback.
        Will stop briefly as changing mid-streaming don't work.
        """

        AudioRunning.on_audio_list_space_press(audio_player)

        AudioPaused.adjust_playback_left(audio_player)

        AudioPaused.on_audio_list_space_press(audio_player)

    @staticmethod
    def adjust_playback_right(audio_player: AudioPlayer):
        """
        Moves audio playback cursor to the right. Moves by 5% of total playback.
        Will stop briefly as changing mid-streaming don't work.
        """

        AudioRunning.on_audio_list_space_press(audio_player)

        AudioPaused.adjust_playback_right(audio_player)

        AudioPaused.on_audio_list_space_press(audio_player)


class AudioPaused(PlayerStates):
    """
    PlayerState with Audio paused state.
    """

    @staticmethod
    def on_audio_list_space_press(audio_player: AudioPlayer):
        """
        Resumes current track and switch to AudioRunning State.
        """

        with audio_player.maintain_current_view():
            audio_player.stream.pause_stream()
            try:
                audio_player.mark_as_playing(audio_player.current_playing_idx)
            except IndexError:
                pass

        audio_player.player_state = AudioRunning

    @staticmethod
    def adjust_playback_left(audio_player: AudioPlayer):
        """
        Moves audio playback cursor to the left. Moves by 5% of total playback
        """

        reference = audio_player.stream.audio_info.loaded_data

        current_frame = reference.tell()
        total_frame = reference.frames
        offset = total_frame // 20

        reference.seek(0 if offset > current_frame else (current_frame - offset))

        logger.debug(f"Adjusted left from {current_frame} to {reference.tell()}")

        # Trigger playback callback to display new values
        callback = audio_player.show_progress_wrapper(paused=True)
        callback(audio_player.stream.audio_info, reference.tell())

    @staticmethod
    def adjust_playback_right(audio_player: AudioPlayer):
        """
        Moves audio playback cursor to the left. Moves by 5% of total playback
        """

        reference = audio_player.stream.audio_info.loaded_data

        current_frame = reference.tell()
        total_frame = reference.frames
        offset = total_frame // 20

        if (offset + current_frame) > total_frame:
            reference.seek(total_frame)
        else:
            reference.seek(current_frame + offset)

        logger.debug(f"Adjusted right from {current_frame} to {reference.tell()}")

        # Trigger playback callback to display new values
        callback = audio_player.show_progress_wrapper(paused=True)
        callback(audio_player.stream.audio_info, reference.tell())
