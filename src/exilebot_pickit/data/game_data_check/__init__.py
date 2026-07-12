"""Folder-per-module package for `game_data_check`.

Re-exports every name (public and private) from the `.game_data_check` submodule
so `exilebot_pickit.data.game_data_check` behaves exactly as a flat module would.
"""
from . import game_data_check as _src
globals().update({_k: _v for _k, _v in vars(_src).items()
                  if not _k.startswith("__")})
del _src
