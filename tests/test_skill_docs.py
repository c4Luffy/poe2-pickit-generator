"""Guards project skill docs (.claude/skills/*) against drifting from the real
code they describe.

Skill files copy facts out of the code so a human/agent can follow a checklist
without reading the source first. A copied fact can silently go stale — the
`verify-game-data` skill once quoted a NeverSink filter URL that had drifted
from the real `NEVERSINK_URL` constant (different repo name AND branch), and
nobody noticed until a manual read-through caught it. These tests pin the
skill text to the real constant so a future change to either is caught here
instead of by chance.

Skipped entirely if a skill file isn't present in the checkout (e.g. a
stripped-down clone) — this only guards against the two staying in sync when
both exist, it never requires the skill file to exist.
"""
import os

import pytest

from exilebot_pickit.data.game_data_check.game_data_check import NEVERSINK_URL

_ROOT = os.path.join(os.path.dirname(__file__), "..")
_SKILLS = os.path.join(_ROOT, ".claude", "skills")


def _read_skill(name: str) -> str:
    path = os.path.join(_SKILLS, name, "SKILL.md")
    if not os.path.isfile(path):
        pytest.skip(f"{name}/SKILL.md not present in this checkout")
    with open(path, encoding="utf-8") as f:
        return f.read()


def test_verify_game_data_skill_quotes_the_real_neversink_url():
    text = _read_skill("verify-game-data")
    assert NEVERSINK_URL in text, (
        "verify-game-data/SKILL.md's NeverSink link has drifted from the real "
        f"NEVERSINK_URL constant ({NEVERSINK_URL!r}) in game_data_check.py — "
        "update the skill file to match.")


def test_add_rare_stat_skill_does_not_duplicate_the_coe_url():
    """The Craft of Exile 2 URL must live in exactly ONE skill (verify-bases-coe),
    or the two can drift apart from each other the same way the NeverSink URL
    drifted from the code — a copy nobody remembers to update."""
    coe = _read_skill("verify-bases-coe")
    rare = _read_skill("add-rare-stat")
    assert "craftofexile.com" in coe, "verify-bases-coe should be the one place with this URL"
    assert "craftofexile.com" not in rare, (
        "add-rare-stat re-copied the Craft of Exile URL instead of pointing at "
        "verify-bases-coe — that reintroduces the duplicate-copy drift risk.")
