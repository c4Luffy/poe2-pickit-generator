"""Folder-per-module package for `icons`.

Re-exports every name (public and private) from the `.icons` submodule so
`exilebot_pickit.data.icons` behaves exactly as the old flat module did.
"""
from . import icons as _src
globals().update({_k: _v for _k, _v in vars(_src).items()
                  if not _k.startswith("__")})
del _src
from .unique_icons import UNIQUE_ICONS  # noqa: E402,F401
