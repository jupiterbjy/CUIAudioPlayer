import py_cui


class AudioPlayerTUI:
    """
    Main TUI Class containing UI definitions.
    Designed for 5, 7 layout
    """

    def __init__(self, root: py_cui.PyCUI):
        super().__init__()

        self._root = root

        # -- UI definitions
        # row-idx then col-idx, it's reversed x,y - reminder to self!
        self.audio_list = self._root.add_scroll_menu("Files", 0, 0, column_span=5, row_span=3)
        self.meta_list = self._root.add_scroll_menu("Meta", 0, 5, column_span=2, row_span=5)

        self.info_box = self._root.add_text_box("Info", 3, 0, column_span=4)
        self.volume_slider = self._root.add_slider("Volume", 3, 4, column_span=1, min_val=0, max_val=10, init_val=5)

        self.play_btn = self._root.add_button("Play", 4, 0)
        self.stop_btn = self._root.add_button("Stop", 4, 1)
        self.reload_btn = self._root.add_button("Reload", 4, 2)

        self.prev_btn = self._root.add_button("Reserved", 4, 3)
        self.next_btn = self._root.add_button("Next", 4, 4)

        # Symbols for play state indicator
        self.symbols = {"play": "⏵", "pause": "⏸", "stop": "⏹"}

        # Theme changes
        self.volume_slider.toggle_value()
        self.volume_slider.align_to_bottom()
        self.volume_slider.set_bar_char("█")

        self.play_btn.set_color(py_cui.YELLOW_ON_BLACK)
        self.stop_btn.set_color(py_cui.YELLOW_ON_BLACK)
        self.prev_btn.set_color(py_cui.RED_ON_BLACK)
        self.next_btn.set_color(py_cui.GREEN_ON_BLACK)

