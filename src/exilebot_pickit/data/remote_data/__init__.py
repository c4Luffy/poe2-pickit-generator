"""Folder-per-module package for `remote_data`.

Re-exports every name (public and private) from the `.remote_data` submodule so
`exilebot_pickit.data.remote_data` behaves exactly as the old flat module did.
"""
from . import remote_data as _src
globals().update({_k: _v for _k, _v in vars(_src).items()
                  if not _k.startswith("__")})
del _src
