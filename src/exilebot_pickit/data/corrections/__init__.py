"""Folder-per-module package for `corrections`.

Re-exports every name (public and private) from the `.corrections` submodule so
`exilebot_pickit.data.corrections` behaves exactly as the old flat module did.
"""
from . import corrections as _src
# The shim copies *references*, so this package attribute and the submodule
# attribute point to the SAME object. remote_data relies on that: it updates
# these structures by in-place mutation (.clear()/.update()/slice assignment)
# and must NEVER reassign the attribute, or the two namespaces would diverge.
globals().update({_k: _v for _k, _v in vars(_src).items()
                  if not _k.startswith("__")})
del _src
