"""
Implementation of state machine using __class__ attribute manipulation from Python Cookbook 3E.
"""

from __future__ import annotations
from typing import TYPE_CHECKING

from FileWalker import PathWrapper
from SDManager.StreamManager import StreamManager

if TYPE_CHECKING:
    import pathlib


class PlayerStates:
    ellipsis_ = ".."  # 3 dots 2 long
    usable_offset_y, usable_offset_x = 2, 6  # Excl. Border, Spacing of widget from abs size.

    symbols = {"play": "⏵", "pause": "⏸", "stop": "⏹"}

    def __init__(self, *args):

        # -- Generator instance and states
        self._current_play_generator = None
        self._current_name_cycler = None

        # -- Path and stream instance
        self.stream: StreamManager = StreamManager(self.show_progress_wrapper(), self.play_next)
        self.path_wrapper = PathWrapper()

    def on_file_click(self):
        """
        Action to do when *audio list* widget is accessed.
        """

        if self.selected_track in self.path_wrapper.folder_list:
            self.clear_meta()
        else:
            self.update_meta()

    def on_next_track_click(self):
        """
        Action to do when *next track* button is pressed.
        :param self:
        :return:
        """

    def on_previous_track_click(self):
        pass

    def on_stop_click(self):
        pass

    def on_reload_click(self):
        pass

    @property
    def selected_track(self) -> pathlib.Path:
        """
        Returns name of selected track. Convenient method.

        :return: Path object representing selected audio file.
        """

        return self.path_wrapper[self.selected_idx]

    @property
    def currently_playing(self) -> int:
        """
        Returns index of currently played track. Currently using slow method for simplicity.

        :return: index of played file
        """

        file_name = self.stream.audio_info.loaded_data.name
        return self.path_wrapper.index(file_name)


class AudioUnloaded(PlayerStates):
    pass


class AudioStopped(PlayerStates):
    pass


class AudioRunning(PlayerStates):
    pass


class AudioPaused(PlayerStates):
    pass
