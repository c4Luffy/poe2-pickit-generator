"""Folder-per-module package for `magic_rare`.

Re-exports every name (public and private) from the `.magic_rare` submodule so
`exilebot_pickit.data.magic_rare` behaves exactly as the old flat module did.
"""
from . import magic_rare as _src
globals().update({_k: _v for _k, _v in vars(_src).items()
                  if not _k.startswith("__")})
del _src
