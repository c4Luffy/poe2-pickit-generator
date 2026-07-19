"""Config persistence: atomic save, corruption recovery, type coercion.

These target the failure mode the 2026-07 audit flagged as the app's worst:
a bad config write silently wiping every setting/profile/exclusion.
"""
import json
import os

import pytest

from exilebot_pickit.ui import config as cfgmod


@pytest.fixture
def tmp_config(tmp_path, monkeypatch):
    """Point CONFIG_PATH at a temp file for the duration of a test."""
    p = tmp_path / "pickit_gui_config.json"
    monkeypatch.setattr(cfgmod, "CONFIG_PATH", str(p))
    monkeypatch.setattr(cfgmod, "CONFIG_LOAD_ERROR", "", raising=False)
    return p


def test_round_trip(tmp_config):
    cfg = dict(cfgmod.DEFAULT_CONFIG)
    cfg["league"] = "Standard"
    cfg["min_exalt_gear"] = 12.5
    cfg["item_states"] = {"currency": {"Mirror of Kalandra": {"enabled": False}}}
    cfgmod.save_config(cfg)
    loaded = cfgmod.load_config()
    assert loaded["league"] == "Standard"
    assert loaded["min_exalt_gear"] == 12.5
    assert loaded["item_states"]["currency"]["Mirror of Kalandra"] == {"enabled": False}


def test_save_leaves_no_tmp_file(tmp_config):
    cfgmod.save_config(dict(cfgmod.DEFAULT_CONFIG))
    assert os.path.exists(str(tmp_config))
    assert not os.path.exists(str(tmp_config) + ".tmp")


def test_corrupt_config_backs_up_and_warns(tmp_config):
    tmp_config.write_text("{ this is not json", encoding="utf-8")
    loaded = cfgmod.load_config()
    assert loaded == dict(cfgmod.DEFAULT_CONFIG)          # falls back to defaults
    assert os.path.exists(str(tmp_config) + ".corrupt.bak")  # original preserved
    assert cfgmod.CONFIG_LOAD_ERROR                        # UI gets told


def test_missing_config_is_clean_first_run(tmp_config):
    # File doesn't exist: defaults, no error, no .bak
    loaded = cfgmod.load_config()
    assert loaded == dict(cfgmod.DEFAULT_CONFIG)
    assert cfgmod.CONFIG_LOAD_ERROR == ""
    assert not os.path.exists(str(tmp_config) + ".corrupt.bak")


def test_type_coercion_rejects_wrong_shapes(tmp_config):
    # Each of these used to crash Tk var construction on startup.
    bad = dict(cfgmod.DEFAULT_CONFIG)
    bad["category_enabled"] = []          # list where dict expected
    bad["history"] = {}                   # dict where list expected
    bad["backup_count"] = "many"          # str where int expected
    bad["item_states"] = "nope"           # str where dict expected
    tmp_config.write_text(json.dumps(bad), encoding="utf-8")
    loaded = cfgmod.load_config()
    assert loaded["category_enabled"] == {}
    assert loaded["history"] == []
    assert loaded["backup_count"] == cfgmod.DEFAULT_CONFIG["backup_count"]
    assert loaded["item_states"] == {}


def test_numeric_types_are_interchangeable(tmp_config):
    ok = dict(cfgmod.DEFAULT_CONFIG)
    ok["min_exalt_gear"] = 5              # int where float default — fine
    ok["backup_count"] = 7.0              # float where int default — fine
    tmp_config.write_text(json.dumps(ok), encoding="utf-8")
    loaded = cfgmod.load_config()
    assert loaded["min_exalt_gear"] == 5
    assert loaded["backup_count"] == 7.0


def test_unknown_keys_survive(tmp_config):
    # Forward-compat: a newer version's keys must not be dropped by an older one.
    data = dict(cfgmod.DEFAULT_CONFIG)
    data["some_future_key"] = {"x": 1}
    tmp_config.write_text(json.dumps(data), encoding="utf-8")
    assert cfgmod.load_config()["some_future_key"] == {"x": 1}


def test_concurrent_saves_never_corrupt_the_config(tmp_config):
    """Many savers at once must never produce an unreadable config.

    Regression guard for 2026-07-12. save_config wrote to a single shared
    ``config.json.tmp``: the UI thread and the generate worker (or a second app
    process) opened the *same* temp path, the second truncated the first's
    half-written JSON, and whichever finished first atomically moved that garbage
    into place. os.replace being atomic never helped — the file it moved was
    already corrupt. The owner's log had 318 load_config JSONDecodeErrors in a
    day, and *every one of them* silently dropped the app onto DEFAULT_CONFIG:
    one save landing at the wrong moment would have wiped league, profiles,
    history and every item toggle.
    """
    import threading

    base = dict(cfgmod.DEFAULT_CONFIG)
    base["league"] = "Runes of Aldur"
    base["profiles"] = {"mine": {"a": 1}}
    cfgmod.save_config(base)

    corrupt = []

    def saver(n):
        for i in range(25):
            cfg = dict(base)
            cfg["backup_count"] = n * 100 + i
            cfgmod.save_config(cfg)

    def reader():
        for _ in range(80):
            try:
                with open(cfgmod.CONFIG_PATH, encoding="utf-8") as f:
                    json.load(f)
            except json.JSONDecodeError as e:      # the bug: corrupt CONTENT
                corrupt.append(str(e))
            except OSError:
                pass                               # transient lock — harmless

    threads = [threading.Thread(target=saver, args=(n,)) for n in range(4)]
    threads += [threading.Thread(target=reader) for _ in range(2)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    assert not corrupt, f"config was corrupted by concurrent saves: {corrupt[:2]}"

    # and nothing was lost, nor left lying around
    loaded = cfgmod.load_config()
    assert loaded["league"] == "Runes of Aldur"
    assert loaded["profiles"] == {"mine": {"a": 1}}
    leftovers = [f for f in os.listdir(os.path.dirname(cfgmod.CONFIG_PATH))
                 if f.endswith(".tmp")]
    assert not leftovers, f"temp files left behind: {leftovers}"


def test_config_with_utf8_bom_still_loads(tmp_config):
    """A UTF-8 BOM (Notepad "Save As", PowerShell Set-Content -Encoding UTF8, some
    editors) must not make the app lose every setting. Plain utf-8 json.load chokes on
    the leading BOM; utf-8-sig strips it. This corrupted a real user's live config."""
    import json
    payload = {"league": "Runes of Aldur", "min_exalt_gear": 7.0, "theme": "relic"}
    # write the file WITH a BOM, the way the offending tools do
    with open(cfgmod.CONFIG_PATH, "w", encoding="utf-8-sig") as f:
        json.dump(payload, f)
    assert open(cfgmod.CONFIG_PATH, "rb").read()[:3] == b"\xef\xbb\xbf"   # BOM really there

    cfg = cfgmod.load_config()
    assert cfg["league"] == "Runes of Aldur"     # loaded, not wiped to defaults
    assert cfg["min_exalt_gear"] == 7.0
    assert not os.path.exists(cfgmod.CONFIG_PATH + ".corrupt.bak")  # never quarantined


# ── Full-scan regression tests (2026-07-15) ──────────────────────────────────

def test_second_corruption_never_overwrites_first_quarantine(tmp_config):
    """corruption #1 quarantines the user's REAL config to .corrupt.bak — often
    hand-recoverable. corruption #2 must not overwrite that only surviving copy
    with fresh junk; it gets its own timestamped name."""
    with open(cfgmod.CONFIG_PATH, "w", encoding="utf-8") as f:
        f.write('{"league": "precious user data...')          # truncated JSON
    cfgmod.load_config()
    bak = cfgmod.CONFIG_PATH + ".corrupt.bak"
    assert os.path.exists(bak)
    first = open(bak, encoding="utf-8").read()

    with open(cfgmod.CONFIG_PATH, "w", encoding="utf-8") as f:
        f.write("totally different junk")                     # corruption #2
    cfgmod.load_config()
    assert open(bak, encoding="utf-8").read() == first        # untouched
    import glob
    others = [p for p in glob.glob(cfgmod.CONFIG_PATH + ".corrupt-*.bak")]
    assert others, "second corruption was not quarantined separately"


def test_defaults_are_never_polluted_by_config_mutation(tmp_config):
    """load_config must hand out DEEP copies: mutating the returned config's
    nested dicts used to write into DEFAULT_CONFIG itself, so 'Reset to
    defaults' restored the pollution instead of the defaults."""
    cfg = cfgmod.load_config()                                # first run path
    cfg["item_states"].setdefault("currency", {})["Chaos Orb"] = {"enabled": False}
    cfg["history"].append({"run": 1})
    assert cfgmod.DEFAULT_CONFIG["item_states"] == {}         # pristine
    assert cfgmod.DEFAULT_CONFIG["history"] == []


def test_explicit_null_in_config_is_reset_to_default(tmp_config):
    """An explicit JSON null (hand-edit, imported backup) used to sail through
    type coercion, persist, and crash dict consumers on every launch."""
    import json
    with open(cfgmod.CONFIG_PATH, "w", encoding="utf-8") as f:
        json.dump({"category_enabled": None, "history": None, "league": "L"}, f)
    cfg = cfgmod.load_config()
    assert cfg["category_enabled"] == {}                      # reset, not None
    assert cfg["history"] == []
    assert cfg["league"] == "L"                               # good keys kept


def test_save_config_reports_failure_instead_of_pretending(tmp_path, monkeypatch):
    """save_config must SAY whether the config reached disk.

    It swallows every exception by design (a failed save must not crash the
    app) but it also returned None, so ~25 bridge methods answered the UI with
    a hard-coded {"ok": True}. With the config directory gone or unwritable,
    set_setting() and profile_save() both reported success having written
    nothing at all: the toast said "Saved" and the setting was simply absent at
    the next launch. It now returns True/False — and still never raises, and
    still leaves any existing file untouched on failure."""
    missing = tmp_path / "not-there" / "pickit_gui_config.json"
    monkeypatch.setattr(cfgmod, "CONFIG_PATH", str(missing))
    assert cfgmod.save_config(dict(cfgmod.DEFAULT_CONFIG)) is False
    assert not missing.exists()

    good = tmp_path / "pickit_gui_config.json"
    monkeypatch.setattr(cfgmod, "CONFIG_PATH", str(good))
    cfg = dict(cfgmod.DEFAULT_CONFIG, league="Standard")
    assert cfgmod.save_config(cfg) is True
    assert cfgmod.load_config()["league"] == "Standard"

    # A failing save reports False AND leaves the good file exactly as it was —
    # the guarantee tests above depend on (never wipe a user's settings).
    def boom(*a, **k):
        raise OSError("disk full")
    monkeypatch.setattr(cfgmod.os, "replace", boom)
    assert cfgmod.save_config(dict(cfg, league="Wiped")) is False
    assert cfgmod.load_config()["league"] == "Standard"
    leftovers = [f for f in os.listdir(str(tmp_path)) if f.startswith(".pickit_cfg-")]
    assert not leftovers, "failed save left a temp file behind"
