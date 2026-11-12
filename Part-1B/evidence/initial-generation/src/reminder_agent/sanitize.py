"""Output sanitisation (SAF-6). Strips control, bidi and zero-width characters; never touches markup."""

from __future__ import annotations

import re
import unicodedata

_WHITESPACE_CONTROLS = re.compile(r"[\t\n\r\x0b\x0c]+")
_HIDDEN = re.compile("[\u0000-\u001f\u007f​-‍⁠﻿‪-‮⁦-⁩]")
_SPACES = re.compile(r" {2,}")


def sanitize_text(text: str) -> str:
    """NFC-normalise, turn whitespace controls into spaces, drop hidden characters, collapse spaces, trim."""
    text = unicodedata.normalize("NFC", text)
    text = _WHITESPACE_CONTROLS.sub(" ", text)
    text = _HIDDEN.sub("", text)
    return _SPACES.sub(" ", text).strip()
