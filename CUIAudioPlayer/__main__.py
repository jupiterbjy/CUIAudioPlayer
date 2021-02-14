from __future__ import annotations
from sys import platform

import py_cui
import CompatibilityPatch
from LoggingConfigurator import logger
from Player.PlayerLogic import AudioPlayer

try:
    # noinspection PyUnresolvedReferences
    import pretty_errors
    pretty_errors.activate()
except ImportError:
    pass

assert CompatibilityPatch


VERSION_TAG = "0.0.3a - dev"
logger.debug(f"Platform: {platform} Version: {VERSION_TAG}")


# ------------------------------------------------------------------


def draw_player():
    """
    TUI driver
    """

    root = py_cui.PyCUI(5, 7)
    root.set_title(f"CUI Audio Player - v{VERSION_TAG}")
    root.set_widget_border_characters("╔", "╗", "╚", "╝", "═", "║")
    root.set_refresh_timeout(0.1)
    # this don't have to be a second. Might be an example of downside of ABC

    player_ref = AudioPlayer(root)
    assert player_ref
    # Preventing unused variable check

    root.start()


def main():
    """
    Interface purpose wrapper
    """

    draw_player()


if __name__ == '__main__':
    main()
