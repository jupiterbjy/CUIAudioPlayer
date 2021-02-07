import py_cui
import functools
from math import sin
from typing import Callable, Sequence, Iterator


def monkey_patch_callback(widget_: py_cui.widgets.Widget, callback: Callable):
    # Sequence is _draw -> _handle_mouse_press, so patching on _draw results 1 update behind.
    # Therefore we need to patch both _handle_mouse_press and _handle_keyboard_press.

    def patch_factory(original_func):
        @functools.wraps(original_func)
        def wrapper(*args, **kwargs):
            original_func(*args, **kwargs)
            callback()

        return wrapper

    for func_name in ("_handle_key_press", "_handle_mouse_press"):
        setattr(widget_, func_name, patch_factory(getattr(widget_, func_name)))


def visualize(data: Sequence) -> Iterator[str]:
    conversion_table = (" ", "▁", "▂", "▃", "▄", "▅", "▆", "▇", "█")
    lim = len(conversion_table) - 1

    def string_gen(item: int):
        while True:
            try:
                yield conversion_table[item]
            except IndexError:
                yield conversion_table[-1]
                item -= lim
            else:
                break

    string_lines = ["".join(string_gen(n)) for n in data]
    max_length = len(max(string_lines))
    length_normalized = (line.ljust(max_length) for line in string_lines)

    return reversed(["".join(n) for n in zip(*length_normalized)])


class Main:
    def __init__(self, root_: py_cui.PyCUI):
        self.root = root_

        # UI Def
        self.scroll = self.root.add_scroll_menu("Data", 0, 0)
        self.graph = self.root.add_text_block("Graph", 0, 1)

        # setup
        monkey_patch_callback(self.scroll, self.callback_scroll)
        for n in range(40):
            self.scroll.add_item(int(round(sin(n / 4), 2) * 10) + 10)

    def callback_scroll(self):
        self.graph.clear()

        text = "\n".join(visualize(self.scroll.get_item_list()))

        data_length = len(self.scroll.get_item_list())
        selected = self.scroll.get_selected_item_index()
        indicator = " " * selected + "↑" + " " * (data_length - selected - 1)

        self.graph.set_text(text + "\n" + indicator)


if __name__ == '__main__':
    root = py_cui.PyCUI(1, 2)
    ref = Main(root)
    root.toggle_unicode_borders()
    root.start()
