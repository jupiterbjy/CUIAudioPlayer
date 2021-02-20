import py_cui
import functools
from math import sin, pi
from collections import deque
from typing import Callable, Sequence, Iterator


def monkey_patch_loop(widget_: py_cui.widgets.Widget, callback: Callable):
    # Sequence is _draw -> _handle_mouse_press, so patching on _draw results 1 update behind.
    # Therefore we need to patch both _handle_mouse_press and _handle_keyboard_press.

    def patch_factory(original_func):
        @functools.wraps(original_func)
        def wrapper(*args, **kwargs):
            original_func(*args, **kwargs)
            callback()

        return wrapper

    setattr(widget_, "_draw", patch_factory(getattr(widget_, "_draw")))


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
        self.slider_f1 = self.root.add_slider("Frequency", 2, 0, min_val=0, max_val=10, init_val=5)
        self.graph = self.root.add_text_block("Graph", 0, 0, 2, 2)
        self.slider_y = self.root.add_slider("Height", 2, 1, min_val=0, max_val=20, init_val=10)

        # setup
        self.data = deque((sin(n * pi / 10) for n in range(40)))

        # monkey patch draw
        monkey_patch_loop(self.graph, self.continuous_call)

    def continuous_call(self):

        data = [int(self.slider_y.get_slider_value() * n) for n in self.data]
        min_ = min(data)

        text = "\n".join(visualize([n - min_ for n in data]))
        self.graph.set_text(text + "\n test")
        self.data.rotate(-1)


if __name__ == '__main__':
    root = py_cui.PyCUI(3, 2)
    ref = Main(root)
    root.set_widget_border_characters("╔", "╗", "╚", "╝", "═", "║")
    root.set_refresh_timeout(0.2)
    root.start()
