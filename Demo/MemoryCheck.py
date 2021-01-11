import py_cui
import memory_profiler
from typing import Iterable


class TestingBase:
    def __init__(self, root: py_cui.PyCUI):
        self.root = root

        self.scroll = self.root.add_scroll_menu("", 0, 0, row_span=3)
        self.start_insert = self.root.add_button("start injecting", 3, 0)
        self.add_count = self.root.add_text_box("Enter injecting MBs.", 4, 0)

    @memory_profiler.profile(precision=4)
    def write_multiple_scroll(self, lines: Iterable):
        self.scroll.clear()
        self.scroll.add_item_list(lines)  # getting warning that list is expected.

    def inject_cb(self):
        try:
            target = int(self.add_count.get())
        except ValueError:
            pass


if __name__ == '__main__':
    root_ = py_cui.PyCUI(5, 1)
    root_.set_title("Mem usage tester")
    ref = TestingBase(root_)
    root_.start()
