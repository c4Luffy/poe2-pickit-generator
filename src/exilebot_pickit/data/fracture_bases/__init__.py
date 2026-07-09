"""Folder-per-module package for `fracture_bases`.

Re-exports every name (public and private) from the `.fracture_bases` submodule so
`exilebot_pickit.data.fracture_bases` behaves exactly as the old flat module did.
"""
from . import fracture_bases as _src
globals().update({_k: _v for _k, _v in vars(_src).items()
                  if not _k.startswith("__")})
del _src
