"""Drop-list delta: what the PATCH changed, as opposed to whether our rules broke."""

import json
import os

import pytest

from exilebot_pickit.data.game_data_check import game_data_check as gdc


@pytest.fixture
def cache(tmp_path, monkeypatch):
    monkeypatch.setattr(gdc, "_cache_dir", lambda: str(tmp_path))
    return tmp_path


def _snap(cache):
    with open(os.path.join(str(cache), "drop_snapshot.json"), encoding="utf-8") as f:
        return json.load(f)


def test_first_check_records_a_baseline_and_claims_nothing(cache):
    """With nothing to compare against, reporting a 'change' would be a fabrication."""
    r = gdc._drop_delta({"Sacred Focus", "Attuned Wand"})
    assert r["baseline"] is True
    assert r["added"] == [] and r["removed"] == []
    assert set(_snap(cache)["bases"]) == {"Sacred Focus", "Attuned Wand"}


def test_second_check_reports_what_started_and_stopped_dropping(cache):
    gdc._drop_delta({"Sacred Focus", "Attuned Wand"})
    r = gdc._drop_delta({"Sacred Focus", "Gloam Ring"})
    assert r["baseline"] is False
    assert r["added"] == ["Gloam Ring"] and r["n_added"] == 1
    assert r["removed"] == ["Attuned Wand"] and r["n_removed"] == 1


def test_an_unchanged_check_keeps_the_last_real_delta(cache):
    """The delta is only detectable on the run that first sees it. If a quiet run
    overwrote it, the finding would vanish before the user ever looked."""
    gdc._drop_delta({"A"})
    gdc._drop_delta({"A", "B"})                 # B starts dropping
    again = gdc._drop_delta({"A", "B"})         # nothing moved since
    assert again["added"] == ["B"]              # still reported
    assert _snap(cache)["last_delta"]["added"] == ["B"]


def test_huge_restructures_are_capped(cache):
    """A NeverSink reshuffle can move hundreds at once — a wall of names helps nobody,
    but the true count must survive."""
    gdc._drop_delta(set())
    r = gdc._drop_delta({f"Base {i:03d}" for i in range(200)})
    assert r["n_added"] == 200
    assert len(r["added"]) == 40


def test_a_corrupt_snapshot_is_treated_as_a_first_run(cache):
    """Never let a bad cache file take the health check down with it."""
    with open(os.path.join(str(cache), "drop_snapshot.json"), "w", encoding="utf-8") as f:
        f.write("{not json")
    r = gdc._drop_delta({"A"})
    assert r["baseline"] is True
