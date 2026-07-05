"""Unit tests for the update-notification logic.

The updater is now a simple check-and-notify: compare the latest GitHub tag to
the running version and, if newer, surface a clickable banner that opens the
Releases page. The old auto-download + backup/swap/rollback machinery was
removed (it kept failing in the field), so only the pure version compare and
the version-sync guard remain to test.

Run with:  python -m pytest tests/test_updater.py -v
"""
from exilebot_pickit.ui.updater import AutoUpdateMixin, VERSION

M = AutoUpdateMixin


# ── _should_offer_update ──────────────────────────────────────────────────────

def test_offer_when_remote_is_newer():
    assert M._should_offer_update("2.7.0", "2.6.24") is True
    assert M._should_offer_update("v2.7.0", "2.6.24") is True          # 'v' tolerated
    assert M._should_offer_update("2.6.25", "2.6.24") is True


def test_no_offer_when_equal_or_older():
    assert M._should_offer_update("2.6.24", "2.6.24") is False
    assert M._should_offer_update("2.6.23", "2.6.24") is False


def test_no_offer_when_remote_blank():
    assert M._should_offer_update("", "2.6.24") is False
    assert M._should_offer_update(None, "2.6.24") is False


def test_ver_tuple_handles_junk_gracefully():
    # a malformed tag must not crash the check; it just won't be "newer".
    assert M._ver_tuple("not.a.version") == (0,)
    assert M._should_offer_update("garbage", "2.6.24") is False


# ── no self-replacement machinery survives ────────────────────────────────────

def test_no_auto_install_machinery():
    """The download/swap/rollback path was removed for good — guard against it
    creeping back in (which is what kept bricking updates)."""
    for gone in ("_install_update", "_build_swap_script", "_reconcile_update_state",
                 "_apply_update_swap", "_finalize_update", "_signal_boot_ok"):
        assert not hasattr(M, gone), f"{gone} should be gone from the updater"


# ── version stays in sync ─────────────────────────────────────────────────────

def test_updater_version_matches_package_version():
    """Guards the release: version.py and updater.py VERSION must match or the
    tagged Release build's version check fails."""
    from exilebot_pickit.version import VERSION as PKG_VERSION
    assert VERSION == PKG_VERSION
