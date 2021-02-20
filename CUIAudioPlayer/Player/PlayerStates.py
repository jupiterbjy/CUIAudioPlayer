"""
Implementation of state machine using __class__ attribute manipulation from Python Cookbook 3E.
"""

from __future__ import annotations
from typing import TYPE_CHECKING

from LoggingConfigurator import logger
from SDManager.StreamManager import StreamManager

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
        except (RuntimeError, FileNotFoundError):
            return

        with audio_player.maintain_current_view():
            # revert texts
            audio_player._refresh_list(search_files=False)
            audio_player.mark_as_stopped(audio_player.currently_playing)
            audio_player.write_info("")

        audio_player.player_state = AudioStopped

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
        audio_player._refresh_list(search_files=True)
        audio_player.volume_callback()

        audio_player.player_state = AudioUnloaded

    @staticmethod
    def on_audio_list_enter_press(audio_player: AudioPlayer):
        """
        Enters directory if selected item is one of them. Else will stop current track and play selected track.
        """

        if audio_player.selected_idx_path in audio_player.path_wrapper.folder_list:
            audio_player.path_wrapper.step_in(audio_player.selected_idx_path)
            PlayerStates.on_reload_click(audio_player)
        else:
            # force play audio
            with audio_player.maintain_current_view():
                try:
                    audio_player.stream.stop_stream()
                except RuntimeError as err:
                    logger.warning(str(err))
                except FileNotFoundError as err:
                    logger.warning(str(err))

                if audio_player.play_stream():
                    audio_player.mark_as_playing(audio_player.currently_playing)
                    audio_player.player_state = AudioRunning

    @staticmethod
    def on_audio_list_space_press(audio_player: AudioPlayer):
        """
        Action to do when *space* is pressed in *audio_list*.
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
            audio_player.mark_as_playing(audio_player.currently_playing)

        audio_player.player_state = AudioRunning


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
        audio_player.player_state = AudioStopped

    @staticmethod
    def on_audio_list_space_press(audio_player: AudioPlayer):
        """
        Pauses current track and switch to AudioPaused State.
        """

        with audio_player.maintain_current_view():
            audio_player.stream.pause_stream()
            audio_player.mark_as_paused(audio_player.currently_playing)

        audio_player.player_state = AudioPaused


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
            audio_player.mark_as_playing(audio_player.currently_playing)

        audio_player.player_state = AudioRunning
