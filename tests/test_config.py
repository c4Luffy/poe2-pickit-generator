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
