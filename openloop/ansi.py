import sys
import re


class Ansi:
    ESC = chr(27)
    RESET = ESC + "[0m"
    BOLD = ESC + "[1m"
    ITALIC = ESC + "[3m"
    UNDERLINE = ESC + "[4m"
    INVERSE = ESC + "[7m"
    STRIKETHROUGH = ESC + "[9m"
    BOLD_OFF = ESC + "[22m"
    ITALIC_OFF = ESC + "[23m"
    UNDERLINE_OFF = ESC + "[24m"
    INVERSE_OFF = ESC + "[27m"
    STRIKETHROUGH_OFF = ESC + "[29m"
    # TXT_BLACK = ESC + "[30m"
    # TXT_RED = ESC + "[31m"
    # TXT_GREEN = ESC + "[32m"
    # TXT_YELLOW = ESC + "[33m"
    # TXT_BLUE = ESC + "[34m"
    # TXT_MAGENTA = ESC + "[35m"
    # TXT_CYAN = ESC + "[36m"
    # TXT_WHITE = ESC + "[37m"

    #
    TXT_BLACK = ESC + "[%d;30m"
    TXT_RED = ESC + "[%d;31m"
    TXT_GREEN = ESC + "[%d;32m"
    TXT_YELLOW = ESC + "[%d;33m"
    TXT_BLUE = ESC + "[%d;34m"
    TXT_MAGENTA = ESC + "[%d;35m"
    TXT_CYAN = ESC + "[%d;36m"
    TXT_WHITE = ESC + "[%d;37m"
    @classmethod
    def is_tty(cls, fd=sys.stdout):
        return fd.isatty()

    @classmethod
    def make(cls, prefix, txt):
        if Ansi.is_tty():
            txt = txt.replace(Ansi.RESET, Ansi.RESET + prefix)
            return "%s%s%s" % (prefix, txt, Ansi.RESET)
        return txt

    @classmethod
    def make_bold(cls, txt):
        return cls.make(Ansi.BOLD, txt)

    @classmethod
    def make_red(cls, txt, light=False):
        return cls.make(Ansi.TXT_RED % light, txt)

    @classmethod
    def make_green(cls, txt, light=False):
        return cls.make(Ansi.TXT_GREEN % light, txt)

    @classmethod
    def make_yellow(cls, txt, light=False):
        return cls.make(Ansi.TXT_YELLOW % light, txt)

    @classmethod
    def strip(cls, txt):
        return re.sub(chr(27) + "\[[0-9]+;([0-9]+)?m", '', txt)
