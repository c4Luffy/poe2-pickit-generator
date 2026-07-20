"""Rare-gear WeightedSum rules, per slot.

Each slot spec carries:
  - ``bases``    : the craft bases to match (one rule line per base, Rare only).
  - ``weights``  : bot stat id -> weight, where weight = 100 / the stat's live
                   T1 max-roll from Craft of Exile (normalisation, so every
                   stat contributes ~100 points at a perfect roll).
  - ``threshold``: the WeightedSum cutoff (strictness dial).
  - ``item_tier``: minimum [ItemTier] gate.

Every stat id is verified in the bot's ModsList; every base is a real craft
base (see generator._CRAFT_BEST_BASES). Nothing here is guessed — the comments
record the live max-roll each weight was derived from.

NOTE: every base below is a PURE single-defence base, so the pure %-defence
ids (local_energy_shield_+% etc.) are the ones that roll. If a HYBRID base
(ar/ev, ar/es, ev/es) is ever added to a slot, its %-defence roll uses the
hybrid ids (local_evasion_and_energy_shield_+% etc.) — those must be added
to the weights or the roll scores zero (audited 2026-07-12).
"""

# Human labels for the recipe view in the Magic & Rare tab.
STAT_LABELS = {
    "base_maximum_life": "maximum Life",
    "minion_skill_gem_level_+": "+ Minion Skill levels",
    "melee_skill_gem_level_+": "+ Melee Skill levels",
    "attack_speed_+%": "Attack Speed %",
    "base_critical_strike_multiplier_+": "Crit Damage Bonus (flat)",
    "base_item_found_rarity_+%": "Rarity of Items Found %",
    "critical_strike_chance_+%": "Global Crit Chance %",
    "base_spirit_from_equipment": "flat Spirit",
    "spell_skill_gem_level_+": "+ Spell Skill levels",
    "projectile_skill_gem_level_+": "+ Projectile Skill levels",
    "maximum_life_+%": "% maximum Life",
    "additional_all_attributes": "+ all Attributes",
    "base_resist_all_elements_%": "+ all Elemental res %",
    "base_fire_damage_resistance_%": "Fire res %",
    "base_cold_damage_resistance_%": "Cold res %",
    "base_lightning_damage_resistance_%": "Lightning res %",
    "base_chaos_damage_resistance_%": "Chaos res %",
    "base_movement_velocity_+%": "Movement Speed %",
    "local_energy_shield": "flat Energy Shield",
    "local_energy_shield_+%": "increased Energy Shield %",
    "attack_maximum_added_physical_damage": "added Phys to Attacks (max roll)",
    "attack_maximum_added_fire_damage": "added Fire to Attacks (max roll)",
    "attack_maximum_added_cold_damage": "added Cold to Attacks (max roll)",
    "attack_maximum_added_lightning_damage": "added Lightning to Attacks (max roll)",
    "fire_damage_+%": "% Fire damage",
    "cold_damage_+%": "% Cold damage",
    "lightning_damage_+%": "% Lightning damage",
    "chaos_damage_+%": "% Chaos damage",
    "charm_charges_gained_+%": "Charm charges gained %",
    "flask_charges_gained_+%": "Flask charges gained %",
    "charm_duration_+%": "Charm duration %",
    "spell_damage_+%": "% Spell damage",
    "base_cast_speed_+%": "Cast Speed %",
    "spell_critical_strike_chance_+%": "Spell Crit Chance %",
    "base_spell_critical_strike_multiplier_+": "Spell Crit Damage Bonus (flat)",
    "chance_to_fire_1_additional_projectile_%_with_rollover_with_bow_attacks": "Chance to fire +1 projectile (bow) %",
    "damage_+%_with_bow_skills": "% Damage with Bow Skills",
    "attack_critical_strike_chance_+%": "Attack Crit Chance %",
    "attack_critical_strike_multiplier_+": "Attack Crit Damage Bonus (flat)",
    "base_projectile_speed_+%": "Projectile Speed %",
    "local_physical_damage_+%": "% Physical Damage (local)",
    "elemental_damage_with_attack_skills_+%": "% Elemental Damage with Attacks",
    "local_attack_speed_+%": "Attack Speed % (local)",
    "local_critical_strike_chance_+%": "Crit Chance +% (local)",
    "local_critical_strike_multiplier_+": "Crit Damage Bonus (local)",
    "local_maximum_added_physical_damage": "added Phys (max roll, local)",
    "local_maximum_added_fire_damage": "added Fire (max roll, local)",
    "local_maximum_added_cold_damage": "added Cold (max roll, local)",
    "local_maximum_added_lightning_damage": "added Lightning (max roll, local)",
    "base_number_of_crossbow_bolts": "+ Bolts loaded",
    "fire_spell_skill_gem_level_+": "+ Fire Spell Skill levels",
    "cold_spell_skill_gem_level_+": "+ Cold Spell Skill levels",
    "lightning_spell_skill_gem_level_+": "+ Lightning Spell Skill levels",
    "chaos_spell_skill_gem_level_+": "+ Chaos Spell Skill levels",
    "physical_spell_skill_gem_level_+": "+ Physical Spell Skill levels",
    "non_skill_base_all_damage_%_to_gain_as_fire": "Gain % of damage as extra Fire",
    "non_skill_base_all_damage_%_to_gain_as_cold": "Gain % of damage as extra Cold",
    "non_skill_base_all_damage_%_to_gain_as_lightning": "Gain % of damage as extra Lightning",
    "allies_in_presence_damage_+%": "Allies in Presence damage %",
    "allies_in_presence_resist_all_elements_%": "Allies in Presence all res %",
    "allies_in_presence_critical_strike_chance_+%": "Allies in Presence crit chance %",
    "minion_maximum_life_+%": "Minion maximum Life %",
    "local_spirit_+%": "% increased Spirit (local)",
}

RARE_GEAR = {
    # Body Armour — owner-approved 2026-07-12. Recipe designed from the live
    # poe.ninja Runes of Aldur ladder (124k chars: ~44% attack builds -> Life+
    # res; ~13% Spirit Walker & minion users -> flat Spirit, a body/amulet-
    # exclusive chase stat; ~18% casters -> ES). T1 max-rolls from the game's
    # own mod database, 2026-07-12: Life 214 (body-exclusive top tier), Spirit
    # 61, ele res 45, chaos res 27, flat ES 96, %ES 110 (body-exclusive tier).
    # Threshold 250 ~= 2.5 perfect stats' worth. A bare T1-%ES body scores
    # under it on purpose — the Fracture %ES>=101 rule already catches those.
    "Body Armour": {
        "bases": ["Warlord Cuirass", "Corsair Coat", "Feathered Raiment"],
        "weights": {
            "base_maximum_life": 0.47,                   # T1 max 214
            "base_spirit_from_equipment": 1.64,          # T1 max 61
            "base_fire_damage_resistance_%": 2.22,       # T1 max 45
            "base_cold_damage_resistance_%": 2.22,       # T1 max 45
            "base_lightning_damage_resistance_%": 2.22,  # T1 max 45
            "base_chaos_damage_resistance_%": 3.7,       # T1 max 27 (premium)
            "local_energy_shield": 1.04,                 # T1 max 96 (ES bases)
            "local_energy_shield_+%": 0.91,              # T1 max 110
        },
        "threshold": "250",
        "item_tier": "4",
    },
    # Helmet — owner-approved 2026-07-12. Helmet-specific premiums on top of
    # the Life+res backbone: +2 Minion Skills is a helmet-exclusive suffix
    # (minion classes ~17% of the poe.ninja ladder), Rarity feeds MF farmers,
    # global crit feeds crit builds. T1 max-rolls from the game's mod database
    # 2026-07-12: Life 174 (helmet cap, IncreasedLife10), minion skills 2,
    # rarity 19, global crit 34, ele res 45, chaos 27, flat ES 96.
    "Helmet": {
        "bases": ["Imperial Greathelm", "Freebooter Cap", "Ancestral Tiara"],
        "weights": {
            "base_maximum_life": 0.57,                   # T1 max 174
            "minion_skill_gem_level_+": 50.0,            # T1 max +2
            "base_item_found_rarity_+%": 5.26,           # T1 max 19
            "critical_strike_chance_+%": 2.94,           # T1 max 34
            "base_fire_damage_resistance_%": 2.22,       # T1 max 45
            "base_cold_damage_resistance_%": 2.22,       # T1 max 45
            "base_lightning_damage_resistance_%": 2.22,  # T1 max 45
            "base_chaos_damage_resistance_%": 3.7,       # T1 max 27 (premium)
            "local_energy_shield": 1.04,                 # T1 max 96 (ES bases)
            "local_energy_shield_+%": 1.0,               # T1 max 100 (92-100 @65 on any
                                                         # ES base; 101-110 is body/shield only)
        },
        "threshold": "250",
        "item_tier": "4",
    },
    # Gloves — owner-approved 2026-07-12. The attack slot: attack speed +
    # melee skill levels + crit multi on the Life/res backbone (attack builds
    # are ~44% of the poe.ninja ladder; Martial Artist alone 20%). Added
    # attack damage deliberately EXCLUDED — the Fracture tab's OR-rule already
    # hunts those gloves (magic + rare); scoring it here would double-cover.
    # T1 max-rolls from the game's mod database 2026-07-12: attack speed 16,
    # melee skills 2, crit multi 34, life 149 (gloves cap), ele res 45,
    # chaos 27, flat ES 96.
    "Gloves": {
        "bases": ["Massive Mitts", "Polished Bracers", "Sirenscale Gloves"],
        "weights": {
            "attack_speed_+%": 6.25,                     # T1 max 16
            "melee_skill_gem_level_+": 50.0,             # T1 max +2
            "base_critical_strike_multiplier_+": 2.94,   # T1 max 34
            "base_maximum_life": 0.67,                   # T1 max 149
            "base_fire_damage_resistance_%": 2.22,       # T1 max 45
            "base_cold_damage_resistance_%": 2.22,       # T1 max 45
            "base_lightning_damage_resistance_%": 2.22,  # T1 max 45
            "base_chaos_damage_resistance_%": 3.7,       # T1 max 27 (premium)
            "local_energy_shield": 1.04,                 # T1 max 96 (ES bases)
            "local_energy_shield_+%": 1.0,               # T1 max 100 (92-100 @65 on any
                                                         # ES base; 101-110 is body/shield only)
            "base_item_found_rarity_+%": 5.56,           # T1 max 18 (audit add)
        },
        "threshold": "250",
        "item_tier": "4",
    },
    # Boots — movement speed is the identity stat (fixed steps 10..35, so
    # 30/35 dominate the score) on the Life/res backbone, plus Rarity for the
    # MF market (owner call 2026-07-12: rarity boots sell). Audited vs the
    # game's mod database 2026-07-12: added missing Life (boots T1 120-149)
    # and chaos res, fixed the flat-ES weight (real T1 is 91-96, the old
    # "max 60" over-scored ES boots by ~60%), aligned ItemTier to 4.
    "Boots": {
        "bases": ["Tasalian Greaves", "Drakeskin Boots", "Sekhema Sandals"],
        "weights": {
            "base_movement_velocity_+%": 2.86,           # T1 max 35
            "base_maximum_life": 0.67,                   # T1 max 149 (boots cap)
            "base_item_found_rarity_+%": 5.56,           # T1 max 18 (MF market)
            "base_fire_damage_resistance_%": 2.22,       # T1 max 45
            "base_cold_damage_resistance_%": 2.22,       # T1 max 45
            "base_lightning_damage_resistance_%": 2.22,  # T1 max 45
            "base_chaos_damage_resistance_%": 3.7,       # T1 max 27 (premium)
            "local_energy_shield": 1.04,                 # T1 max 96 (ES bases)
            "local_energy_shield_+%": 1.0,               # T1 max 100 (92-100 @65 on any
                                                         # ES base; 101-110 is body/shield only)
        },
        "threshold": "250",  # aligned with the other slots after the audit
        "item_tier": "4",    # widened the stat list (owner call 2026-07-12)
    },
    # Amulet — owner-approved 2026-07-12. The deepest slot: +3 skill-family
    # suffixes are amulet-exclusive (a +3 scores the full 100, +2 scores 67);
    # % maximum Life is the amulet life stat (not flat); all-res / all-attrs /
    # Rarity (strongest rarity slot) / Spirit (amulet cap 50) / the game's
    # highest Crit Damage Bonus roll (39). Bases chosen for their implicits:
    # Solar (Spirit), Gold (Rarity), Stellar (all Attributes). The Fracture
    # amulet rule already ORs the +3 families on Solar/Gold; this recipe adds
    # Stellar and amulets that sell on stats other than skills. T1 max-rolls
    # from the game's mod database 2026-07-12.
    "Amulet": {
        "bases": ["Solar Amulet", "Gold Amulet", "Stellar Amulet"],
        "weights": {
            "spell_skill_gem_level_+": 33.33,            # T1 max +3
            "minion_skill_gem_level_+": 33.33,           # T1 max +3
            "melee_skill_gem_level_+": 33.33,            # T1 max +3
            "projectile_skill_gem_level_+": 33.33,       # T1 max +3
            "maximum_life_+%": 12.5,                     # T1 max 8%
            "additional_all_attributes": 4.17,           # T1 max 24
            "base_resist_all_elements_%": 5.56,          # T1 max 18
            "base_fire_damage_resistance_%": 2.22,       # T1 max 45
            "base_cold_damage_resistance_%": 2.22,       # T1 max 45
            "base_lightning_damage_resistance_%": 2.22,  # T1 max 45
            "base_chaos_damage_resistance_%": 3.7,       # T1 max 27 (premium)
            "base_spirit_from_equipment": 2.0,           # T1 max 50 (amulet cap)
            "base_critical_strike_multiplier_+": 2.56,   # T1 max 39
            "base_item_found_rarity_+%": 5.26,           # T1 max 19 (MF slot)
        },
        "threshold": "250",
        "item_tier": "4",
    },
    # Ring — owner-approved 2026-07-12 ("no attributes on rings"). Rings sell
    # on DAMAGE: flat added-to-attacks prefixes (gated on the max-roll stat,
    # same approach as Fracture weapons — and Fracture does NOT cover rings,
    # so no double-cover) and %-elemental/chaos damage for casters; plus the
    # second MF slot (people wear two), all-res (ring cap 16), res backbone,
    # small flat life (ring cap 119). Bases by implicit: Biostatic (+1% to all
    # MAXIMUM Resistances — the best ring implicit in the game and the highest
    # ring base at ilvl 52), Prismatic (all-res), Gold (rarity). Amethyst was
    # dropped 2026-07-12: it is an ilvl-20 base whose +7-13% chaos-res implicit
    # is strictly worse than the chaos-res SUFFIX this recipe already scores
    # (24-27%). T1 max-rolls from the game's mod database 2026-07-12.
    "Ring": {
        "bases": ["Biostatic Ring", "Prismatic Ring", "Gold Ring"],
        "weights": {
            "attack_maximum_added_physical_damage": 3.13,   # T1 max 32
            "attack_maximum_added_fire_damage": 2.22,       # T1 max 45
            "attack_maximum_added_cold_damage": 2.7,        # T1 max 37
            "attack_maximum_added_lightning_damage": 1.41,  # T1 max 71
            "fire_damage_+%": 3.33,                         # T1 max 30
            "cold_damage_+%": 3.33,                         # T1 max 30
            "lightning_damage_+%": 3.33,                    # T1 max 30
            "chaos_damage_+%": 3.33,                        # T1 max 30
            "base_item_found_rarity_+%": 5.26,              # T1 max 19 (MF)
            "base_resist_all_elements_%": 6.25,             # T1 max 16 (ring cap)
            "base_fire_damage_resistance_%": 2.22,          # T1 max 45
            "base_cold_damage_resistance_%": 2.22,          # T1 max 45
            "base_lightning_damage_resistance_%": 2.22,     # T1 max 45
            "base_chaos_damage_resistance_%": 3.7,          # T1 max 27
            "base_maximum_life": 0.84,                      # T1 max 119 (ring cap)
        },
        "threshold": "250",
        "item_tier": "4",
    },
    # Belt — owner-approved 2026-07-12 (incl. "no mana on belt"). The plain
    # jewellery slot: belts have NO rarity/all-res/skills, they sell on Life
    # (T1 174, helmet-tier) + resistances, garnished by the PoE2 charm/flask
    # QoL rolls. The Fracture belt rule already stashes any T2+ single-res
    # belt; this recipe is the value layer for multi-stat belts. Attributes
    # and mana skipped by owner rule. T1 max-rolls from the game's mod
    # database 2026-07-12.
    "Belt": {
        "bases": ["Fine Belt", "Utility Belt", "Heavy Belt"],
        "weights": {
            "base_maximum_life": 0.57,                   # T1 max 174
            "base_fire_damage_resistance_%": 2.22,       # T1 max 45
            "base_cold_damage_resistance_%": 2.22,       # T1 max 45
            "base_lightning_damage_resistance_%": 2.22,  # T1 max 45
            "base_chaos_damage_resistance_%": 3.7,       # T1 max 27 (premium)
            "charm_charges_gained_+%": 2.5,              # T1 max 40
            "flask_charges_gained_+%": 2.5,              # T1 max 40
            "charm_duration_+%": 3.03,                   # T1 max 33
        },
        "threshold": "250",
        "item_tier": "4",
    },
    # Focus — owner-approved 2026-07-12. Pure caster stat-stick: NO life/res/
    # defences roll on foci at all. Sells on +2 Spell Skills, %spell/element
    # damage (89, the big caster prefix), spell crit chance/multi, cast speed
    # (32, the highest roll of any slot). Mana/regen/ES-recharge skipped —
    # garnish. Fracture already solo-catches +2-spells and 54+ crit foci;
    # this is the multi-stat value layer. T1 max-rolls from the game's mod
    # database 2026-07-12.
    "Focus": {
        "bases": ["Tasalian Focus", "Sacred Focus", "Leyline Focus"],
        "weights": {
            "spell_skill_gem_level_+": 50.0,             # T1 max +2
            "spell_damage_+%": 1.12,                     # T1 max 89
            "fire_damage_+%": 1.12,                      # T1 max 89 (focus tier)
            "cold_damage_+%": 1.12,                      # T1 max 89 (focus tier)
            "lightning_damage_+%": 1.12,                 # T1 max 89 (focus tier)
            "chaos_damage_+%": 1.12,                     # T1 max 89 (focus tier)
            "spell_critical_strike_chance_+%": 1.69,     # T1 max 59
            "base_spell_critical_strike_multiplier_+": 2.94,  # T1 max 34
            "base_cast_speed_+%": 3.13,                  # T1 max 32
        },
        "threshold": "250",
        "item_tier": "4",
    },
    # Quiver — owner-approved 2026-07-12. Pure bow-offense slot (no life/res).
    # The chase is the "Surpassing" family suffix — chance to fire +1
    # projectile with bow attacks, quiver cap 60% ("of Splintering"; the BOW
    # version reaches 200%, scored there when the Bow slot is built). +1
    # Projectile Skills is the cap so it scores full 100. Added-damage gates
    # use the max-roll stats (same approach as Fracture). Fracture already
    # solo-catches +1-proj-skills / crit / bow-dmg / proj-speed quivers; this
    # is the multi-stat layer. Pierce/accuracy/dex/on-kill skipped (garnish).
    # T1 max-rolls from the game's mod database 2026-07-12.
    "Quiver": {
        "bases": ['Visceral Quiver', 'Volant Quiver', 'Penetrating Quiver'],
        "weights": {
            "chance_to_fire_1_additional_projectile_%_with_rollover_with_bow_attacks": 1.67,  # T1 max 60
            "projectile_skill_gem_level_+": 100.0,       # T1 max +1 (the cap)
            "attack_speed_+%": 6.25,                     # T1 max 16
            "damage_+%_with_bow_skills": 1.69,           # T1 max 59 (game id)
            "attack_critical_strike_chance_+%": 2.63,    # T1 max 38
            "attack_critical_strike_multiplier_+": 2.56, # T1 max 39
            "base_projectile_speed_+%": 2.17,            # T1 max 46
            "attack_maximum_added_physical_damage": 3.13,   # T1 max 32
            "attack_maximum_added_fire_damage": 2.22,       # T1 max 45
            "attack_maximum_added_cold_damage": 2.7,        # T1 max 37
            "attack_maximum_added_lightning_damage": 1.41,  # T1 max 71
        },
        "threshold": "250",
        "item_tier": "4",
    },
    # Bow — owner-approved 2026-07-12. The chase is "of Many": up to 200%
    # chance to fire +1 arrow (Surpassing family, rolls over past 100%).
    # Bows reach +4 Projectile Skills (game data; the Fracture bow rule now
    # uses the same projectile_skill_gem_level_+ engine id — the renamed-id
    # case was fixed this pass, like body-Spirit). Added-damage terms gate on
    # the LOCAL max-roll stats; %ele-with-attacks uses the bow-tag 100 cap.
    # Accuracy/dex/leech/on-kill/stun skipped. Weapon-local crit chance is
    # scored in PERCENT scale (owner call 2026-07-12: the bot reads the roll
    # as 4.41-5, matching the fracture crit rule's format) — sanity-check on
    # the first live bot run that crit weapons stash sensibly. T1 max-rolls
    # from the game's mod database 2026-07-12.
    "Bow": {
        "bases": ["Obliterator Bow", "Warmonger Bow", "Guardian Bow"],
        "weights": {
            "chance_to_fire_1_additional_projectile_%_with_rollover_with_bow_attacks": 0.5,  # T1 max 200
            "projectile_skill_gem_level_+": 25.0,        # T1 max +4
            "local_physical_damage_+%": 0.56,            # T1 max 179
            "elemental_damage_with_attack_skills_+%": 1.0,  # T1 max 100 (bow cap)
            "local_attack_speed_+%": 3.57,               # T1 max 28
            "local_critical_strike_chance_+%": 20.0,     # T1 max +5% (owner call
                                                         # 2026-07-12: bot reads it
                                                         # as 4.41-5, % scale)
            "local_critical_strike_multiplier_+": 4.0,   # T1 max +25
            "local_maximum_added_physical_damage": 1.52, # T1 max 66
            "local_maximum_added_fire_damage": 0.65,     # T1 max 154
            "local_maximum_added_cold_damage": 0.81,     # T1 max 123
            "local_maximum_added_lightning_damage": 0.43,  # T1 max 234
        },
        "threshold": "250",
        "item_tier": "4",
    },
    # Crossbow — owner-approved 2026-07-12. Chase: +2 bolts (lvl82 suffix;
    # game stat is base_number_of_crossbow_bolts — the Fracture rule now uses
    # that same id, fixed this pass, same renamed-id family as bow skills).
    # +5 Projectile Skills (highest ranged
    # skill roll). Crossbows use the 2H added-damage tables (~1.5x bow).
    # T1 max-rolls from the game's mod database 2026-07-12.
    "Crossbow": {
        "bases": ["Elegant Crossbow", "Desolate Crossbow", "Flexed Crossbow"],
        "weights": {
            "base_number_of_crossbow_bolts": 50.0,       # T1 max +2
            "projectile_skill_gem_level_+": 20.0,        # T1 max +5
            "local_physical_damage_+%": 0.56,            # T1 max 179
            "elemental_damage_with_attack_skills_+%": 0.72,  # T1 max 139 (2H cap)
            "local_attack_speed_+%": 3.57,               # T1 max 28
            "local_critical_strike_chance_+%": 20.0,     # T1 max +5% (owner call
                                                         # 2026-07-12: bot reads it
                                                         # as 4.41-5, % scale)
            "local_critical_strike_multiplier_+": 4.0,   # T1 max +25
            "local_maximum_added_physical_damage": 1.06, # T1 max 94 (2H)
            "local_maximum_added_fire_damage": 0.42,     # T1 max 236 (2H)
            "local_maximum_added_cold_damage": 0.53,     # T1 max 189 (2H)
            "local_maximum_added_lightning_damage": 0.28,  # T1 max 358 (2H)
        },
        "threshold": "250",
        "item_tier": "4",
    },
    # Quarterstaff — owner-approved 2026-07-12. No exclusive chase mod; the
    # value is +5 Melee Skills plus the full 2H damage kit — and the deepest
    # buyer pool in the league (Martial Artist = 20% of the poe.ninja ladder).
    # T1 max-rolls from the game's mod database 2026-07-12.
    "Quarterstaff": {
        "bases": ['Dreaming Quarterstaff', 'Razor Quarterstaff', 'Striking Quarterstaff'],
        "weights": {
            "melee_skill_gem_level_+": 20.0,             # T1 max +5
            "local_physical_damage_+%": 0.56,            # T1 max 179
            "elemental_damage_with_attack_skills_+%": 0.72,  # T1 max 139 (2H cap)
            "local_attack_speed_+%": 3.57,               # T1 max 28
            "local_critical_strike_chance_+%": 20.0,     # T1 max +5% (owner call
                                                         # 2026-07-12: bot reads it
                                                         # as 4.41-5, % scale)
            "local_critical_strike_multiplier_+": 4.0,   # T1 max +25
            "local_maximum_added_physical_damage": 1.06, # T1 max 94 (2H)
            "local_maximum_added_fire_damage": 0.42,     # T1 max 236 (2H)
            "local_maximum_added_cold_damage": 0.53,     # T1 max 189 (2H)
            "local_maximum_added_lightning_damage": 0.28,  # T1 max 358 (2H)
        },
        "threshold": "250",
        "item_tier": "4",
    },
    # Spear — owner-approved 2026-07-12. The hybrid weapon: rolls BOTH +5
    # Melee and +4 Projectile Skills (throw builds). 1H damage tables.
    # T1 max-rolls from the game's mod database 2026-07-12.
    "Spear": {
        "bases": ['Grand Spear', 'Flying Spear', 'Stalking Spear'],
        "weights": {
            "melee_skill_gem_level_+": 25.0,             # T1 max +4 (1H cap)
            "projectile_skill_gem_level_+": 25.0,        # T1 max +4
            "local_physical_damage_+%": 0.56,            # T1 max 179
            "elemental_damage_with_attack_skills_+%": 1.0,  # T1 max 100 (1H cap)
            "local_attack_speed_+%": 3.57,               # T1 max 28
            "local_critical_strike_chance_+%": 20.0,     # T1 max +5% (owner call
                                                         # 2026-07-12: bot reads it
                                                         # as 4.41-5, % scale)
            "local_critical_strike_multiplier_+": 4.0,   # T1 max +25
            "local_maximum_added_physical_damage": 1.52, # T1 max 66 (1H)
            "local_maximum_added_fire_damage": 0.65,     # T1 max 154 (1H)
            "local_maximum_added_cold_damage": 0.81,     # T1 max 123 (1H)
            "local_maximum_added_lightning_damage": 0.43,  # T1 max 234 (1H)
        },
        "threshold": "250",
        "item_tier": "4",
    },
    # Mace — owner-approved 2026-07-12. ONE slot covers both mace classes:
    # weighted by the 2H tables (owner-accepted trade-off — 1H maces score
    # conservatively, erring toward fewer junk picks), bases from both.
    # T1 max-rolls from the game's mod database 2026-07-12.
    "Mace": {
        "bases": ['Tawhoan Greatclub', 'Massive Greathammer', 'Fortified Hammer'],
        "weights": {
            "melee_skill_gem_level_+": 20.0,             # T1 max +5
            "local_physical_damage_+%": 0.56,            # T1 max 179
            "elemental_damage_with_attack_skills_+%": 0.72,  # T1 max 139 (2H cap)
            "local_attack_speed_+%": 3.57,               # T1 max 28
            "local_critical_strike_chance_+%": 20.0,     # T1 max +5% (owner call
                                                         # 2026-07-12: bot reads it
                                                         # as 4.41-5, % scale)
            "local_critical_strike_multiplier_+": 4.0,   # T1 max +25
            "local_maximum_added_physical_damage": 1.06, # T1 max 94 (2H)
            "local_maximum_added_fire_damage": 0.42,     # T1 max 236 (2H)
            "local_maximum_added_cold_damage": 0.53,     # T1 max 189 (2H)
            "local_maximum_added_lightning_damage": 0.28,  # T1 max 358 (2H)
        },
        "threshold": "250",
        "item_tier": "4",
    },
    # Sceptre — owner-approved 2026-07-12. The minion-support weapon: +4
    # Minion Skills, %Spirit (local, sceptre cap 65), Allies-in-Presence
    # damage/all-res/crit, Minion Life. Allies added-damage suite skipped
    # (garnish). Fracture solo-catches the single chases; this is the
    # multi-stat layer. T1 max-rolls from the game's mod database 2026-07-12.
    "Sceptre": {
        # Hallowed Sceptre dropped 2026-07-12 — in the game's item table but it
        # does NOT drop (owner confirmed in-game; NeverSink lists no sceptre above
        # Wrath). Shrine Sceptre was briefly dropped 2026-07-19 as "unique-only"
        # and PUT BACK the same day: FourSceptreUnique1 is only one of its four
        # metadata entries — FourSceptre6a/6b/6c are ordinary drops. It drops.
        "bases": ["Wrath Sceptre", "Shrine Sceptre", "Omen Sceptre"],
        "weights": {
            "minion_skill_gem_level_+": 25.0,            # T1 max +4
            "allies_in_presence_damage_+%": 0.84,        # T1 max 119
            "local_spirit_+%": 1.54,                     # T1 max 65
            "minion_maximum_life_+%": 2.0,               # T1 max 50
            "allies_in_presence_resist_all_elements_%": 5.56,  # T1 max 18
            "allies_in_presence_critical_strike_chance_+%": 2.63,  # T1 max 38
        },
        "threshold": "250",
        "item_tier": "4",
    },
    # Wand — owner-approved 2026-07-12. Owner-caught: wands ALSO roll
    # "+4 to Level of all Spell Skills" (GlobalSpellGemsLevelWeapon4) on top
    # of the five per-element +5 suffixes. Spell/element damage to 119,
    # gain-as-extra to 30, cast speed 35, spell crit 73 / multi 39.
    # T1 max-rolls from the game's mod database 2026-07-12.
    "Wand": {
        "bases": ["Dueling Wand", "Acrid Wand", "Galvanic Wand"],
        "weights": {
            "spell_skill_gem_level_+": 25.0,             # T1 max +4 (ALL spells)
            "fire_spell_skill_gem_level_+": 20.0,        # T1 max +5
            "cold_spell_skill_gem_level_+": 20.0,        # T1 max +5
            "lightning_spell_skill_gem_level_+": 20.0,   # T1 max +5
            "chaos_spell_skill_gem_level_+": 20.0,       # T1 max +5
            "physical_spell_skill_gem_level_+": 20.0,    # T1 max +5
            "spell_damage_+%": 0.84,                     # T1 max 119
            "fire_damage_+%": 0.84,                      # T1 max 119 (wand tier)
            "cold_damage_+%": 0.84,                      # T1 max 119 (wand tier)
            "lightning_damage_+%": 0.84,                 # T1 max 119 (wand tier)
            "chaos_damage_+%": 0.84,                     # T1 max 119 (wand tier)
            "non_skill_base_all_damage_%_to_gain_as_fire": 3.33,       # T1 max 30
            "non_skill_base_all_damage_%_to_gain_as_cold": 3.33,       # T1 max 30
            "non_skill_base_all_damage_%_to_gain_as_lightning": 3.33,  # T1 max 30
            "base_cast_speed_+%": 2.86,                  # T1 max 35 (wand tier)
            "spell_critical_strike_chance_+%": 1.37,     # T1 max 73 (wand tier)
            "base_spell_critical_strike_multiplier_+": 2.56,  # T1 max 39
        },
        "threshold": "250",
        "item_tier": "4",
    },
    # Staff — owner-approved 2026-07-12. The big caster two-hander: all
    # tables doubled — +5-6 ALL Spell Skills, +7 per-element, spell/element
    # damage to 238, gain-as-extra to 60, cast speed 52, spell crit 109 /
    # multi 59 (the v4.9.2-fixed stat). T1 max-rolls from the game's mod
    # database 2026-07-12.
    "Staff": {
        # Dark Staff dropped 2026-07-12 (same reason as Hallowed Sceptre).
        # Permafrost Staff and Reflecting Staff dropped 2026-07-19: their
        # metadata is FourStaffUnique1/Unique3 — unique-only bases hosting The
        # Whispering Ice and Atziri's Rule. A rare one never drops, so these
        # recipes could never match. Sanctified (56) and Paralysing (52) take
        # their place: the next two real staves, both NeverSink-listed. Every
        # other slot keeps the top 3 that exist even when the levels fall off
        # (Wand runs 65/33/25), so a lone staff would be the odd one out.
        "bases": ["Ravenous Staff", "Sanctified Staff", "Paralysing Staff"],
        "weights": {
            "spell_skill_gem_level_+": 16.67,            # T1 max +6 (ALL spells)
            "fire_spell_skill_gem_level_+": 14.29,       # T1 max +7
            "cold_spell_skill_gem_level_+": 14.29,       # T1 max +7
            "lightning_spell_skill_gem_level_+": 14.29,  # T1 max +7
            "chaos_spell_skill_gem_level_+": 14.29,      # T1 max +7
            "physical_spell_skill_gem_level_+": 14.29,   # T1 max +7
            "spell_damage_+%": 0.42,                     # T1 max 238
            "fire_damage_+%": 0.42,                      # T1 max 238 (staff tier)
            "cold_damage_+%": 0.42,                      # T1 max 238 (staff tier)
            "lightning_damage_+%": 0.42,                 # T1 max 238 (staff tier)
            "chaos_damage_+%": 0.42,                     # T1 max 238 (staff tier)
            "non_skill_base_all_damage_%_to_gain_as_fire": 1.67,       # T1 max 60
            "non_skill_base_all_damage_%_to_gain_as_cold": 1.67,       # T1 max 60
            "non_skill_base_all_damage_%_to_gain_as_lightning": 1.67,  # T1 max 60
            "base_cast_speed_+%": 1.92,                  # T1 max 52 (staff tier)
            "spell_critical_strike_chance_+%": 0.92,     # T1 max 109 (staff tier)
            "base_spell_critical_strike_multiplier_+": 1.69,  # T1 max 59 (staff tier)
        },
        "threshold": "250",
        "item_tier": "4",
    },
}


# Strictness dial — scales every slot's WeightedSum cutoff by one multiplier.
# "Balanced" is the hand-tuned defaults above; higher = a rare must score more
# to be kept (fewer, better rares), lower = more rares slip through. The per-slot
# recipes (which stats, what weights) never change — only the bar they clear.
STRICTNESS_LEVELS = {
    "looser":      0.80,
    "balanced":    1.00,   # default / recommended — the tuned thresholds
    "strict":      1.25,
    "very_strict": 1.50,
}
DEFAULT_STRICTNESS = "balanced"


def strictness_mult(level) -> float:
    """Multiplier for a strictness level name; unknown/blank -> balanced (1.0)."""
    return STRICTNESS_LEVELS.get(str(level or "").lower(), 1.0)


def scaled_threshold(spec: dict, mult: float = 1.0) -> int:
    """A slot's WeightedSum cutoff after the strictness multiplier."""
    return int(round(float(spec["threshold"]) * mult))


def _slot_lines(spec: dict, mult: float = 1.0) -> list:
    """One validated rule line per base for a slot spec.

    Post-# order: hard gates (required minimums) first, then the WeightedSum
    over the remaining stats, then the pickup action. ``mult`` is the strictness
    dial — it scales only the cutoff, never the weights or gates."""
    terms = ",".join(f"{sid}:{w}" for sid, w in spec["weights"].items())
    gates = "".join(f'[{sid}] >= "{v}" && '
                    for sid, v in spec.get("gates", {}).items())
    cutoff = scaled_threshold(spec, mult)
    return [
        f'[Type] == "{base}" && [ItemTier] >= "{spec["item_tier"]}" '
        f'&& [Rarity] == "Rare" # {gates}[WeightedSum({terms})] >= '
        f'"{cutoff}" && [StashItem] == "true"'
        for base in spec["bases"]
    ]


def rare_gear_body(disabled=None, mult: float = 1.0, mults: dict | None = None) -> list:
    """Rule lines for all enabled rare-gear slots, each under its own
    ``// -- Rare {slot}`` sub-header. The caller adds the major section banner.
    Empty when everything is off.

    ``mult`` is the global strictness dial (applied to every slot). ``mults`` is
    an optional ``{slot: multiplier}`` map of PER-SLOT overrides — a slot listed
    there uses its own multiplier instead of the global one, so Body Armour can
    be very strict while Helmet is looser."""
    disabled = set(disabled or ())
    mults = mults or {}
    body: list = []
    for slot, spec in RARE_GEAR.items():
        if slot in disabled:
            continue
        m = mults.get(slot, mult)
        body.append(f"// -- Rare {slot} ({len(spec['bases'])} bases, "
                    f"WeightedSum >= {scaled_threshold(spec, m)}) "
                    + "-" * 20)
        body.extend(_slot_lines(spec, m))
        body.append("")
    return body


def rare_gear_example_lines(slot: str, mult: float = 1.0) -> list:
    """The exact emitted lines for one slot, for tab display (== output)."""
    spec = RARE_GEAR.get(slot)
    return _slot_lines(spec, mult) if spec else []


def rare_gear_slots() -> list:
    """Slot names that currently have wired rules (for the tab)."""
    return list(RARE_GEAR)
