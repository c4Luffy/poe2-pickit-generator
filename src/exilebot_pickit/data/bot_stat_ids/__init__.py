"""Folder-per-module package for `bot_stat_ids`.

Re-exports every name (public and private) from the `.bot_stat_ids` submodule so
`exilebot_pickit.data.bot_stat_ids` behaves exactly as the old flat module did.
"""
from . import bot_stat_ids as _src
globals().update({_k: _v for _k, _v in vars(_src).items()
                  if not _k.startswith("__")})
del _src
