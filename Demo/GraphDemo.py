import functools
import itertools
from math import sin, pi
from collections import deque
from typing import Callable, Sequence, Iterator

import py_cui


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


def visualizer_closure(table, fill=True):
    conversion_table = table
    lim = len(conversion_table) - 1

    def inner(data: Sequence) -> Iterator[str]:
        def string_gen(item: int):
            while True:
                try:
                    yield conversion_table[item]
                except IndexError:
                    yield conversion_table[-1] if fill else conversion_table[0]
                    item -= lim
                else:
                    break

        string_lines = ["".join(string_gen(n)) for n in data]
        max_length = max(map(len, string_lines))
        length_normalized = (line.ljust(max_length) for line in string_lines)

        return reversed(["".join(n) for n in zip(*length_normalized)])

    inner.num_per_ch = len(table) - 1

    return inner


def visualizer_closure_alt(table):
    conversion_table = table
    lim = len(conversion_table) - 1
    quotient = 0

    def inner(data: Sequence) -> Iterator[str]:
        nonlocal quotient

        min_val = min(data)
        min_idx = data.index(min_val)

        if data[min_idx] < 0:
            for quotient_ in itertools.count(1):
                if quotient_ * lim > -min_val:
                    quotient = quotient_
                    break

        def string_gen(item: int):
            while item > 0:
                try:
                    yield conversion_table[item]
                except IndexError:
                    yield conversion_table[-1]
                    item -= lim
                else:
                    break

        pad = quotient * lim
        string_lines = ["".join(string_gen(n)) for n in (val + pad for val in data)]
        max_length = len(max(string_lines))
        length_normalized = (line.ljust(max_length) for line in string_lines)

        return reversed(["".join(n) for n in zip(*length_normalized)])

    inner.num_per_ch = len(table) - 1

    return inner


visualize = visualizer_closure((" ", "▁", "▂", "▃", "▄", "▅", "▆", "▇", "█"))
visualize_dot = visualizer_closure((" ", ".", "·", "˙"), fill=False)
visualize_alt = visualizer_closure_alt((" ", "▁", "▂", "▃", "▄", "▅", "▆", "▇", "█"))


def double_sine_wave_gen():
    scale_1 = 10
    scale_2 = 15
    steps = 0.5

    for frame in (n * steps for n in itertools.count(1)):
        yield sin(frame * (pi / scale_1)) + sin(frame * (pi / scale_2))


class Main:
    def __init__(self, root_: py_cui.PyCUI):
        self.root = root_

        # Slider settings
        self.slider_f_range = {"min_val": 1, "max_val": 10, "init_val": 1}
        self.slider_y_range = {"min_val": 1, "max_val": 20, "init_val": 15}

        # UI Def
        self.slider_f = self.root.add_slider(
            "Cycle per update", 4, 0, **self.slider_f_range
        )
        self.slider_y = self.root.add_slider(
            "Value multiplier", 4, 1, **self.slider_y_range
        )
        self.graph = self.root.add_text_block("Graph", 0, 0, 2, 1)
        self.graph_alt = self.root.add_text_block("Graph", 2, 0, 2, 1)
        self.graph_dot = self.root.add_text_block("Graph", 0, 1, 4, 1)

        # generator instance
        self.data_stream = double_sine_wave_gen()

        # setup
        self._data = deque([], 40)
        self.graph_alt.add_text_color_rule("-", py_cui.BLACK_ON_WHITE, "contains")

        for slider_widget in (self.slider_f, self.slider_y):
            slider_widget.toggle_border()
            slider_widget.align_to_top()
            slider_widget.toggle_title()
            slider_widget.set_bar_char("█")

        # monkey patch draw
        monkey_patch_loop(self.graph, self.continuous_call_closure())

    def continuous_call_closure(self) -> Callable:

        cycle_instance = itertools.cycle(
            range(self.slider_f_range["min_val"], self.slider_f_range["max_val"])
        )

        def check_update():
            return 0 == (next(cycle_instance) % self.slider_f.get_slider_value())

        def inject_new_data():
            self._data.append(next(self.data_stream))

        def callback():

            if check_update():
                inject_new_data()

                self.graph_draw_standard()
                self.graph_draw_dot()
                self.graph_draw_alternative()

        return callback
    
    def graph_draw_standard(self):
        self._graph_draw_main(self.graph, visualize)

    def graph_draw_dot(self):
        self._graph_draw_main(self.graph_dot, visualize_dot)

    def _graph_draw_main(self, draw_target: py_cui.widgets.ScrollTextBlock, visualizer: Callable):

        data = [int(self.slider_y.get_slider_value() * n) for n in self._data]
        min_ = min(data)

        text = list(visualizer([n - min_ for n in data]))

        text[-1] = f"{text[-1]} _ {min_}"

        for line_idx in range(0, len(text) - 1):
            text[line_idx] += f" _ {min_ + visualizer.num_per_ch * (len(text) - 1 - line_idx)}"

        text.append("| " * (len(self._data) // 2))

        draw_target.set_text("\n".join(text))

    def graph_draw_alternative(self):
        draw_target = self.graph_alt
        visualizer = visualize_alt
        
        data = [int(self.slider_y.get_slider_value() * n) for n in self._data]
        min_ = min(data)

        text = list(visualizer(data))
        num_per_char = visualizer.num_per_ch

        quotient = 0

        for quotient_ in itertools.count(1):
            if quotient_ * num_per_char > -min_:
                quotient = quotient_
                break

        if not quotient:
            for line_idx in range(0, len(text) - 1):
                text[line_idx] += f" _ {min_ + num_per_char * (len(text) - 1 - line_idx)}"

        else:
            for idx, multiplier in zip(reversed(range(len(text))), range(-quotient, len(text))):
                text[idx] += f"_ {multiplier * num_per_char}"

        text.append("| " * (len(self._data) // 2))

        draw_target.set_text("\n".join(text))


if __name__ == "__main__":
    root = py_cui.PyCUI(5, 2)
    ref = Main(root)
    root.set_widget_border_characters("╔", "╗", "╚", "╝", "═", "║")
    root.set_refresh_timeout(0.1)
    root.start()
