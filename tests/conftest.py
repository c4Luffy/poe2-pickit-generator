"""Shared test fixtures.

The one thing every test must NOT do: write to the developer's real debug.log.
Several tests deliberately corrupt throwaway configs (proving recovery works) —
config.py's module-level logger points at the real %APPDATA% log, so those
intentional EXC lines landed in the live file and showed up in the app's Debug
tab as scary fake errors (reported 2026-07-16). Redirect the logger to a
throwaway file for the whole test session.
"""
import logging

import pytest


@pytest.fixture(autouse=True, scope="session")
def _quarantine_debug_log(tmp_path_factory):
    log = logging.getLogger("pickit")
    old = list(log.handlers)
    for h in old:
        log.removeHandler(h)
    fh = logging.FileHandler(
        str(tmp_path_factory.mktemp("log") / "debug.log"), encoding="utf-8")
    fh.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(message)s"))
    log.addHandler(fh)
    yield
    log.removeHandler(fh)
    fh.close()
    for h in old:
        log.addHandler(h)
