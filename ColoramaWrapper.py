from sys import stdout

# Code from github.com/jupiterbjy/Sorting_in_visual


class EscapeCode:
    BR_BLACK = '\033[90m'
    BR_RED = '\033[91m'
    BR_GREEN = '\033[92m'
    BR_YELLOW = '\033[93m'
    BR_BLUE = '\033[94m'
    BR_MAGENTA = '\033[95m'
    BR_CYAN = '\033[96m'
    BR_WHITE = '\033[97m'
    RESET = '\033[0m'
    BOLD = '\033[1m'
    FAINT = '\033[2m'
    ITALIC = '\033[3m'
    UNDERLINE = '\033[4m'


def _colorize_closure():
    try:
        import colorama

    except ModuleNotFoundError:
        print("colorama not installed, disabling colored text.")
        return lambda txt, color: str(txt)

    else:
        colorama.init()

        def ansi_wrapper(txt, color):
            return getattr(EscapeCode, color) + str(txt) + EscapeCode.RESET

        return ansi_wrapper


colorize = _colorize_closure()


def clear():
    # might need module 'reprint'..
    stdout.write("\x1b[2J\x1b[H")


def go_back(line: int):
    stdout.write(f"\x1b[{line}F")


def _color_function_string_gen():
    """
    I'm too lazy to copy paste all those convenience functions manually.
    """

    formatting = '''
    def {}(txt: str):
        return colorize(txt, '{}')
    '''
    for n in EscapeCode.__dict__.keys():
        try:
            print(formatting.format(n.lower(), n))
        except AttributeError:
            pass


def br_black(txt: str):
    return colorize(txt, 'BR_BLACK')


def br_red(txt: str):
    return colorize(txt, 'BR_RED')


def br_green(txt: str):
    return colorize(txt, 'BR_GREEN')


def br_yellow(txt: str):
    return colorize(txt, 'BR_YELLOW')


def br_blue(txt: str):
    return colorize(txt, 'BR_BLUE')


def br_magenta(txt: str):
    return colorize(txt, 'BR_MAGENTA')


def br_cyan(txt: str):
    return colorize(txt, 'BR_CYAN')


def br_white(txt: str):
    return colorize(txt, 'BR_WHITE')


def reset(txt: str):
    return colorize(txt, 'RESET')


def bold(txt: str):
    return colorize(txt, 'BOLD')


def faint(txt: str):
    return colorize(txt, 'FAINT')


def italic(txt: str):
    return colorize(txt, 'ITALIC')


def underline(txt: str):
    return colorize(txt, 'UNDERLINE')


