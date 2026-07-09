"""Magic & Rare tab — pickit rules for Magic/Rare items that don't belong to
the Fracture (fracturing-orb) reference.

First content (owner request, 2026-07-09): pick up the best Life and Mana
flasks with a top-tier "increased Charges" roll. Flasks are Normal/Magic in
PoE2 (never Rare), so these emit a [Rarity] == "Magic" rule per base — named
by [Type] (not [Category] == "Flask", which the bot's validator rejects).

Every stat id here is verified against the bot's own ModsList.html and every
base against live Craft of Exile 2 + NeverSink; nothing is guessed.
"""

# Best Life + Mana flask bases (top tier, verified live from CoE, drop-checked
# against NeverSink). Named individually so the [Type] gate is a real base.
MAGIC_RARE_FLASK_BASES = ("Ultimate Life Flask", "Ultimate Mana Flask")

# "#% increased Charges" — the flask charges suffix. Verified in ModsList.html
# (id local_max_charges_+%). T1 rolls 63-70% at ilvl81; ">= 63" gates on T1.
_FLASK_CHARGES_ID = "local_max_charges_+%"
_FLASK_CHARGES_MIN = "63"


def build_magic_rare_rules(flasks_enabled: bool = True) -> list:
    """Return the Magic & Rare section lines. Empty when everything is off."""
    body: list = []
    if flasks_enabled:
        body.append("// -- Flasks (best Life/Mana, T1 charges, Magic) "
                    + "-" * 33)
        for base in MAGIC_RARE_FLASK_BASES:
            body.append(
                f'[Type] == "{base}" && [Rarity] == "Magic" '
                f'# [{_FLASK_CHARGES_ID}] >= "{_FLASK_CHARGES_MIN}" && [StashItem] == "true"'
            )
        body.append("")
    if not body:
        return []
    from exilebot_pickit.generator import header_major as _header_major
    return [
        _header_major("Magic & Rare"),
        "",
        "//  Hand-picked Magic/Rare item rules (not fracture reference).                    //",
        "//  Manage in the Magic & Rare tab.                                                //",
        "",
    ] + body


def magic_rare_flask_example_lines() -> list:
    """The exact flask lines, for the tab's display (same as emitted)."""
    return [
        f'[Type] == "{b}" && [Rarity] == "Magic" '
        f'# [{_FLASK_CHARGES_ID}] >= "{_FLASK_CHARGES_MIN}" && [StashItem] == "true"'
        for b in MAGIC_RARE_FLASK_BASES
    ]
