import sys
import colors
from . import const

def _print(text, x=0, y=0):
    sys.stdout.write("\033[{};{}H".format(y, x))
    sys.stdout.write("\033[K")
    sys.stdout.write(text)
    sys.stdout.flush()


def print_part_status(id, text):
    _print(colors.blue(f"[Part {id}]") + f"\t{text}",
           y=(id + const.CLI_STATUS_STARTLINE))


def print_captcha_status(text, parts):
    _print(colors.yellow("[Link solve]") +
           f"\t{text}", y=(parts + 0 + const.CLI_STATUS_STARTLINE))


def print_tor_status(text, parts):
    _print(colors.yellow("[Tor  start]") +
           f"\t{text}", y=(parts + 0 + const.CLI_STATUS_STARTLINE))


def print_saved_status(text, parts):
    _print(colors.yellow(f"[Progress]\t {text}"),
           y=(parts + 1 + const.CLI_STATUS_STARTLINE))
