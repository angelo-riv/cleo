"""
Simple colour-coded terminal logger for the quadruped robot.
Keeps all output readable when running on the Pi over SSH.
"""

import sys
from datetime import datetime

# ANSI colour codes — fall back gracefully on terminals that don't support them
_COLOURS = {
    "debug": "\033[90m",    # dark grey
    "info":  "\033[36m",    # cyan
    "warn":  "\033[33m",    # yellow
    "error": "\033[31m",    # red
    "reset": "\033[0m",
}

_LABELS = {
    "debug": "DEBUG",
    "info":  "INFO ",
    "warn":  "WARN ",
    "error": "ERROR",
}

# Set to False to suppress debug messages in production
VERBOSE = True


def log(message: str, level: str = "info"):
    """
    Print a timestamped, colour-coded log line to stdout.

    Usage
    -----
    log("Servo initialised")                 # info by default
    log("PIR not found", level="warn")
    log("Gemini returned bad JSON", level="error")
    log("Sending: walk_forward", level="debug")
    """
    if level == "debug" and not VERBOSE:
        return

    timestamp = datetime.now().strftime("%H:%M:%S")
    colour    = _COLOURS.get(level, "")
    reset     = _COLOURS["reset"]
    label     = _LABELS.get(level, "INFO ")

    line = f"{colour}[{timestamp}] {label} | {message}{reset}"
    print(line, flush=True)

    if level == "error":
        # Also write errors to stderr so they stand out when piped
        print(line, file=sys.stderr, flush=True)
