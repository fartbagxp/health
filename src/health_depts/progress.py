"""
Progress narration for the directory scrapers.

The NACCHO scrape walks 51 states at roughly six seconds each, so a run is a
five-minute wait that otherwise prints nothing at all until it finishes -- with
no way to tell a working run from a hung one. These helpers narrate it on
stderr, which keeps stdout clean for ``-f csv``/``-f json`` piping and gives CI
a timestamped trail to read a failure back from.
"""

import sys
import time

_enabled = True


def set_enabled(enabled: bool) -> None:
    """Turn narration on or off (the CLI's ``--quiet`` flag)."""
    global _enabled
    _enabled = enabled


def log(message: str) -> None:
    """Write one timestamped progress line to stderr."""
    if _enabled:
        print(f"[{time.strftime('%H:%M:%S')}] {message}", file=sys.stderr, flush=True)


def duration(seconds: float) -> str:
    """Human-readable elapsed time: ``4.2s`` or ``5m 32s``."""
    if seconds < 60:
        return f"{seconds:.1f}s"
    minutes, secs = divmod(int(seconds), 60)
    return f"{minutes}m {secs:02d}s"
