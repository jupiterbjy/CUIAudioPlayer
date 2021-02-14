from __future__ import annotations
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from Player import AudioPlayer


class PlayerStates:
    @staticmethod
    def on_file_click(self: AudioPlayer):
        if self.selected_track in self.path_wrapper.folder_list:
            self._clear_meta()
        else:
            self._update_meta()

    @staticmethod
    def on_next_track_click(self: AudioPlayer):
        pass

    @staticmethod
    def on_previous_track_click(self: AudioPlayer):
        pass

    @staticmethod
    def on_stop_click(self: AudioPlayer):
        pass

    @staticmethod
    def on_reload_click(self: AudioPlayer):
        pass


class AudioUnloaded(PlayerStates):
    pass


class AudioStopped(PlayerStates):
    pass


class AudioRunning(PlayerStates):
    pass


class AudioPaused(PlayerStates):
    pass
