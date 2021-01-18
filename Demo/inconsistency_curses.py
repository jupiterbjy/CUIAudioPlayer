import curses


def main(stdscr_: curses.window):
    stdscr_.clear()
    string = "【ENG】【日本語】しぐれうい"
    compensated = "\u200b" + "\u200b".join(string)
    stdscr_.addstr(2, 0, "Original: " + string)
    stdscr_.addstr(3, 0, "Fitted  : " + compensated)
    stdscr_.addstr(4, 0, "Raw     : " + repr(compensated))

    stdscr_.refresh()
    stdscr_.getkey()


curses.wrapper(main)
