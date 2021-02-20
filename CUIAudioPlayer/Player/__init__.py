import functools
import itertools
from collections import OrderedDict
from typing import Callable, Mapping, Generator, Iterator, Tuple

import py_cui
from wcwidth import wcwidth, wcswidth
from tinytag import TinyTag

from LoggingConfigurator import logger


def add_callback_patch(widget_: py_cui.widgets.Widget, callback: Callable, keypress_only=False):
    """
    Adding callback support for widget that lacks such as ScrollMenu.

    :param widget_: Any widget you want to add callback on each input events.
    :param callback: Any callables
    :param keypress_only: Decides whether to replace mouse input handler alongside with key input one.
    """

    # Sequence is _draw -> _handle_mouse_press, so patching on _draw results 1 update behind.
    # Therefore we need to patch both _handle_mouse_press and _handle_keyboard_press.

    def patch_factory(old_func):
        # fix for late binding issue: stackoverflow.com/questions/3431676
        @functools.wraps(old_func)
        def wrapper(*args, **kwargs):
            old_func(*args, **kwargs)
            callback()

        return wrapper

    setattr(widget_, "_handle_key_press", patch_factory(getattr(widget_, "_handle_key_press")))
    if not keypress_only:
        setattr(widget_, "_handle_mouse_press", patch_factory(getattr(widget_, "_handle_mouse_press")))


def progress_bar_mimic(max_width, character_set=(" ",)):
    pass


def extract_meta(abs_file_dir):
    """
    Extracts metadata as OrderedDict.

    :param abs_file_dir: absolute location of audio file

    :return: OrderedDict[str, Any]
    """

    tag = TinyTag.get(abs_file_dir)
    filtered = sorted(((k, v) for k, v in tag.as_dict().items() if v))
    return OrderedDict(filtered)


def meta_list_str_gen(dict_: Mapping) -> Generator[str, None, None]:
    """
    Formats metadata. Returns generator that yields 3 lines per metadata entry.

    :param dict_: Mapping containing metadata.

    :return: Generator[str, None, None]
    """

    for key, val in ((k, v) for k, v in dict_.items() if v):
        yield f"[{key}]"
        yield f":{val}"
        yield " "


def pad_actual_length(source: Iterator[str], pad: str = "\u200b") -> Tuple[str, Generator[str, None, None]]:
    """
    Determine real-displaying character length, and provide padding accordingly to match length.
    This way slicing will cut asian letters properly, not breaking tidy layouts.
    Don't expect to have 0-width characters in given string!

    :param source: Original string to be manipulated. Accepts Iterator[str], allowing lazy generator.
    :param pad: Default character to pad, default ZWSP

    :return: padding character and lazy generator for padded string
    """

    def inner_gen(source_: Iterator[str]) -> Generator[str, None, None]:
        for char in source_:
            yield char
            if wcwidth(char) == 2:
                yield pad

    return pad, inner_gen(source)
    # https://github.com/microsoft/terminal/issues/1472
    # Windows Terminal + (Powershell/CMD) combo can't run this due to ZWSP width issue.
    # Expected to run in purely CMD / Linux Terminal. or WSL + Windows Terminal.
    # Tested on Xfce4 & CMD.


def fit_to_actual_width(text: str, length_lim: int) -> str:
    """
    Cuts given text with varying character width to fit inside given width.
    Expects that lines is short enough, will read entire lines on memory multiple times.

    :param text: Source text
    :param length_lim: length limit in 1-width characters

    :return: cut string
    """

    ellipsis_ = "..."

    # returns immediately if no action is needed
    if wcswidth(text) != len(text):

        _, padded = pad_actual_length(text)
        source = "".join(padded)
        limited = source[:length_lim]

        # if last character was 2-width, padding unicode wore off, so last 2-width character can't fit.
        # instead pad with space for consistent ellipsis position.
        if wcwidth(limited[-1]) == 2:
            limited = limited[:-1] + " "
    else:
        source = text
        limited = text[:length_lim]

    # Add ellipsis if original text was longer than given width
    if len(source) > length_lim:
        limited = limited[:length_lim - len(ellipsis_)]

        # check if last character was 2-width, if so, strip last char and add space
        if wcwidth(limited[-1]):
            limited = limited[:-1] + ' '

        limited += ellipsis_

    return limited


# TODO: support to accept sequence, discarding extra step on player.
def fit_to_actual_width_multiline(text: str, length_lim: int) -> Generator[str, None, None]:
    """
    Cuts given text with varying character width to fit inside given width.
    Will yield multiple lines if line length exceed given length_lim.

    :param text: Source text
    :param length_lim: length limit in 1-width characters

    :return: lazy generator yielding multi-line cut strings
    """

    _, padded = pad_actual_length(text)

    def generator():
        next_line = ''
        line_size = length_lim

        while line := "".join(itertools.islice(padded, 0, line_size)):
            # Add contents of next_line, then reset line length if next_line is not empty
            if next_line:
                line = next_line + line
                next_line = ''
                line_size = length_lim

            # check if last text was 2-width character. If so, move it to next_line and adjust next line_size.
            if wcwidth(line[-1]) == 2:
                next_line = line[-1]
                line = line[:-1]
                line_size -= 1

            yield line

    return generator()
