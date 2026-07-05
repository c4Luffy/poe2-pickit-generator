"""Python<->JS bridge for the modern (WebView2) UI.

Reuses the EXISTING engine end-to-end: api.client for payloads,
generators/assembly for the snapshot-driven rule pipeline (the same one the
Tkinter app uses), ui.config for the shared config file. The web UI reads and
writes the SAME config/item-state data as the Tk app, so the two front-ends
can be used interchangeably while the modern UI matures.

Everything JS-callable returns plain JSON-able dicts/lists. Long work
(generation) runs on a worker thread; the page polls status() for log lines.
"""

import os
import shutil
import threading
import time

from exilebot_pickit import generator as gen
from exilebot_pickit.generators import assembly as asm
from exilebot_pickit.ui.config import (
    OUTPUT_DIR, PRICE_CACHE_DIR, load_config, save_config,
)
from exilebot_pickit.version import VERSION

# Settings JS may write via set_setting() — a whitelist so a compromised page
# can't scribble arbitrary keys into the config file.
_SETTABLE = {
    "league", "output_base", "bot_folder", "auto_copy", "theme",
    "min_exalt_gear", "min_exalt_unique", "include_bases",
    "base_quality", "base_min_level", "auto_regen_hours", "backup_count",
    "copy_filter_to_game", "poe2_filter_dir", "confirm_overwrite_secs",
    "minimize_to_tray",
}


def _config_warning() -> str:
    from exilebot_pickit.ui import config as _c
    return _c.CONFIG_LOAD_ERROR or ""


class AppApi:
    def __init__(self):
        self._lock = threading.Lock()
        self._status = {"running": False, "log": [], "done": None}
        self._last_lines: list = []
        self.cfg = load_config()
        gen.set_disk_cache_dir(PRICE_CACHE_DIR)
        gen.prune_disk_cache(max_age_days=60)
        # Self-updating game data (new bases / unique categories from the repo):
        # cached copy synchronously, fresh copy in the background — same as Tk.
        try:
            from exilebot_pickit.data import remote_data as _rd
            _rd.load_cached_game_data(PRICE_CACHE_DIR)
            _rd.refresh_game_data_async(PRICE_CACHE_DIR)
        except Exception:
            pass

    # ── App/config ────────────────────────────────────────────────────────────

    def app_info(self):
        c = self.cfg
        return {
            "version": VERSION, "output_dir": OUTPUT_DIR,
            "league": c.get("league") or "",
            "theme": (c.get("theme") or "dark").lower(),
            "output_base": c.get("output_base", "poe2_pickit"),
            "bot_folder": c.get("bot_folder", ""),
            "auto_copy": bool(c.get("auto_copy", False)),
            "min_gear": float(c.get("min_exalt_gear", 0.0)),
            "min_unique": float(c.get("min_exalt_unique", 0.0)),
            "include_bases": bool(c.get("include_bases", True)),
            "base_quality": int(c.get("base_quality", 28)),
            "base_min_level": int(c.get("base_min_level", 82)),
            "auto_regen_hours": int(c.get("auto_regen_hours", 0) or 0),
            "copy_filter_to_game": bool(c.get("copy_filter_to_game", False)),
            "poe2_filter_dir": c.get("poe2_filter_dir", ""),
            "backup_count": int(c.get("backup_count", 5)),
            "confirm_overwrite_secs": int(c.get("confirm_overwrite_secs", 120)),
            "config_warning": _config_warning(),
            "minimize_to_tray": bool(c.get("minimize_to_tray", False)),
        }

    def set_setting(self, key, value):
        if key not in _SETTABLE:
            return {"error": f"setting '{key}' not allowed"}
        self.cfg[key] = value
        if key == "min_exalt_gear":            # keep legacy mirror in sync
            self.cfg["min_exalt"] = value
        save_config(self.cfg)
        return {"ok": True}

    def leagues(self):
        try:
            return [{"name": n, "display": d} for n, _, d in gen.fetch_live_leagues()]
        except Exception as e:
            return {"error": str(e)}

    # ── Economy browser ───────────────────────────────────────────────────────

    def economy(self, league):
        """All categories with their items, live/cached values, icons, price
        changes and on/off state."""
        try:
            stale = set()
            payloads = gen.fetch_all_payloads(league, gen.ALL_CATEGORIES, stale_out=stale)
            cur = payloads.get("currency")
            div_rate, _, rate = asm.compute_divine_rate(cur) if isinstance(cur, dict) else (1.0, False, 0.0)
            states = self.cfg.get("item_states", {})
            prev = self.cfg.get("last_gen_prices", {}).get(league, {})
            out = []
            for key, _t, label, is_unique in gen.ALL_CATEGORIES:
                p = payloads.get(key)
                if not isinstance(p, dict):
                    out.append({"key": key, "label": label, "unique": is_unique,
                                "error": str(p) if p else "no data", "items": []})
                    continue
                cat_states = states.get(key, {})
                prev_cat = prev.get(key, {}) if isinstance(prev, dict) else {}
                r = gen.exalted_rate(p)
                items, seen = [], set()

                def _chg(nm, ev, spark=None):
                    """% change: poe.ninja 7-day sparkline for uniques, else
                    vs the price snapshot from the last generate."""
                    if spark and spark.get("totalChange") is not None:
                        return round(float(spark["totalChange"]), 1)
                    old = prev_cat.get(nm)
                    if isinstance(old, (int, float)) and old > 0 and ev > 0:
                        return round((ev - old) / old * 100, 1)
                    return None

                if is_unique:
                    for line in p.get("lines", []):
                        nm = line.get("name")
                        if not nm or nm in seen:
                            continue
                        seen.add(nm)
                        ev = float(line.get("primaryValue") or 0.0) * (r or 1.0)
                        items.append({"name": nm, "base": line.get("baseType", ""),
                                      "ex": round(ev, 2), "enabled": True,
                                      "icon": line.get("icon") or "",
                                      "chg": _chg(nm, ev, line.get("sparkLine"))})
                else:
                    by_id = {i["id"]: i for i in p.get("items", [])}
                    for line in p.get("lines", []):
                        it = by_id.get(line.get("id"))
                        if not it or not it.get("name") or it["name"] in gen.ITEM_NAME_SKIP:
                            continue
                        nm = gen.ITEM_NAME_CORRECTIONS.get(it["name"], it["name"])
                        if nm is None or nm in seen:
                            continue
                        seen.add(nm)
                        ev = float(line.get("primaryValue") or 0.0) * (r or 1.0)
                        img = it.get("image") or ""
                        if img and img.startswith("/"):
                            img = "https://web.poecdn.com" + img
                        items.append({"name": nm, "base": "", "ex": round(ev, 2),
                                      "enabled": cat_states.get(nm, {}).get("enabled", True),
                                      "icon": img, "chg": _chg(nm, ev)})
                items.sort(key=lambda i: -i["ex"])
                out.append({"key": key, "label": label, "unique": is_unique, "items": items})
            enabled_cfg = self.cfg.get("category_enabled", {})
            return {"divine_rate": round(div_rate, 1),
                    "cats": out, "stale": sorted(stale),
                    "cat_enabled": {c[0]: enabled_cfg.get(c[0], True) for c in gen.ALL_CATEGORIES}}
        except Exception as e:
            return {"error": str(e)}

    def set_items_bulk(self, cat_key, names, enabled):
        """Enable/disable every listed item of a category at once."""
        states = self.cfg.setdefault("item_states", {}).setdefault(cat_key, {})
        for n in names:
            states.setdefault(n, {})["enabled"] = bool(enabled)
        save_config(self.cfg)
        return {"ok": True}

    def rule_for(self, cat_key, name, is_unique, base, ex):
        """The pickit rule line for one item — for right-click 'copy rule'."""
        safe = name.replace('"', '\\"')
        if is_unique:
            sb = (base or "").replace('"', '\\"')
            return (f'[Type] == "{sb}" && [Rarity] == "Unique" # [UniqueName] == "{safe}" '
                    f'&& [StashItem] == "true" // ExValue = {float(ex):.2f}')
        return f'[Type] == "{safe}" # [StashItem] == "true" // ExValue = {float(ex):.2f}'

    # ── Profiles ──────────────────────────────────────────────────────────────

    def _profile_snapshot(self):
        c = self.cfg
        import copy as _copy
        return {"item_states": _copy.deepcopy(c.get("item_states", {})),
                "min_exalt": float(c.get("min_exalt_gear", 0.0)),
                "min_exalt_gear": float(c.get("min_exalt_gear", 0.0)),
                "min_exalt_unique": float(c.get("min_exalt_unique", 0.0)),
                "output_base": c.get("output_base", "poe2_pickit"),
                "include_bases": bool(c.get("include_bases", True)),
                "base_quality": int(c.get("base_quality", 28)),
                "base_min_level": int(c.get("base_min_level", 82))}

    def profiles(self):
        return {"names": sorted(self.cfg.get("profiles", {}).keys()),
                "active": self.cfg.get("active_profile", "")}

    def profile_save(self, name):
        name = (name or "").strip()
        if not name:
            return {"error": "empty name"}
        self.cfg.setdefault("profiles", {})[name] = self._profile_snapshot()
        self.cfg["active_profile"] = name
        save_config(self.cfg)
        return {"ok": True}

    def profile_load(self, name):
        prof = self.cfg.get("profiles", {}).get(name)
        if not prof:
            return {"error": "profile not found"}
        import copy as _copy
        self.cfg["item_states"]      = _copy.deepcopy(prof.get("item_states", {}))
        self.cfg["min_exalt_gear"]   = prof.get("min_exalt_gear", 0.0)
        self.cfg["min_exalt"]        = self.cfg["min_exalt_gear"]
        self.cfg["min_exalt_unique"] = prof.get("min_exalt_unique", 0.0)
        self.cfg["output_base"]      = prof.get("output_base", "poe2_pickit")
        self.cfg["include_bases"]    = prof.get("include_bases", True)
        self.cfg["base_quality"]     = prof.get("base_quality", 28)
        self.cfg["base_min_level"]   = prof.get("base_min_level", 82)
        self.cfg["active_profile"]   = name
        save_config(self.cfg)
        return {"ok": True, "info": self.app_info()}

    def profile_delete(self, name):
        self.cfg.get("profiles", {}).pop(name, None)
        if self.cfg.get("active_profile") == name:
            self.cfg["active_profile"] = ""
        save_config(self.cfg)
        return {"ok": True}

    # ── History / update check / debug ────────────────────────────────────────

    def history(self):
        return list(reversed(self.cfg.get("history", [])))[:30]

    def check_update(self):
        try:
            from exilebot_pickit.ui.updater import AutoUpdateMixin, VERSION_URL, RELEASES_URL
            import requests
            r = requests.get(VERSION_URL, timeout=8,
                             headers={"User-Agent": f"poe2-pickit/{VERSION}",
                                      "Accept": "application/vnd.github+json"})
            if r.status_code != 200:
                return {"update": False}
            remote = str((r.json() or {}).get("tag_name") or "").lstrip("v").strip()
            if AutoUpdateMixin._should_offer_update(remote, VERSION):
                return {"update": True, "version": remote, "url": RELEASES_URL}
            return {"update": False}
        except Exception:
            return {"update": False}

    def open_url(self, url):
        if not str(url).startswith("https://github.com/"):
            return {"error": "blocked"}
        import webbrowser
        webbrowser.open(url)
        return {"ok": True}

    def debug_info(self):
        from exilebot_pickit.ui.config import LOG_PATH, CONFIG_PATH
        ci = gen.cache_info()
        tail = []
        try:
            with open(LOG_PATH, encoding="utf-8", errors="replace") as f:
                tail = f.read().splitlines()[-80:]
        except OSError:
            pass
        return {"cache": ci, "log": tail, "config_path": CONFIG_PATH,
                "cache_dir": PRICE_CACHE_DIR,
                "unique_cats": len(gen.UNIQUE_CATEGORIES),
                "all_cats": len(gen.ALL_CATEGORIES)}

    def api_test(self, league):
        out = []
        for key, ninja_type, label, is_unique in gen.ALL_CATEGORIES:
            try:
                p = gen.fetch_category(league, key, ninja_type, is_unique)
                out.append({"label": label, "ok": True, "rows": len(p.get("lines", []))})
            except Exception as e:
                out.append({"label": label, "ok": False, "error": str(e)[:120]})
        return out

    def clear_cache(self):
        gen.clear_cache()
        return {"ok": True}

    def league_start_preset(self):
        """One-click 'day 1' setup: floors to 0 and every category enabled —
        early league, everything sells. Item-level exclusions are kept."""
        self.cfg["min_exalt_gear"] = self.cfg["min_exalt"] = 0.0
        self.cfg["min_exalt_unique"] = 0.0
        ce = self.cfg.setdefault("category_enabled", {})
        for c in gen.ALL_CATEGORIES:
            ce[c[0]] = True
        self.cfg["include_bases"] = True
        save_config(self.cfg)
        return {"ok": True, "info": self.app_info()}

    def prune_cache(self):
        return {"removed": gen.prune_disk_cache(max_age_days=60)}

    def reset_defaults(self):
        """Reset settings to defaults; keep history, profiles, selections and
        price baselines — mirrors the Tk app's Reset behaviour."""
        from exilebot_pickit.ui.config import DEFAULT_CONFIG
        keep = {k: self.cfg.get(k) for k in
                ("history", "profiles", "item_states", "last_gen_prices",
                 "window_geometry", "active_profile", "league")}
        self.cfg.clear()
        self.cfg.update(DEFAULT_CONFIG)
        self.cfg.update({k: v for k, v in keep.items() if v is not None})
        save_config(self.cfg)
        return {"ok": True, "info": self.app_info()}

    def set_item(self, cat_key, name, enabled):
        """Toggle one item (also used for '_chance' pseudo-category)."""
        states = self.cfg.setdefault("item_states", {})
        states.setdefault(cat_key, {}).setdefault(name, {})["enabled"] = bool(enabled)
        save_config(self.cfg)
        return {"ok": True}

    def set_category(self, cat_key, enabled):
        self.cfg.setdefault("category_enabled", {})[cat_key] = bool(enabled)
        save_config(self.cfg)
        return {"ok": True}

    # ── Chance / Craft bases ──────────────────────────────────────────────────

    def chance_bases(self):
        st = self.cfg.get("item_states", {}).get("_chance", {})
        return [{"cat": cat, "base": base, "target": tgt,
                 "enabled": st.get(base, {}).get("enabled", True)}
                for cat, base, tgt in gen.CHANCE_BASES]

    def craft_bases(self):
        st = self.cfg.get("item_states", {}).get("_craftbase", {})
        out = []
        for cat, names in gen.craft_base_categories():
            for n in names:
                s = st.get(n, {})
                out.append({"cat": cat, "base": n,
                            "defence": gen.craft_base_defence(n),
                            "ilvl": int(s.get("ilvl", gen.craft_base_default_ilvl(n))),
                            "enabled": s.get("enabled", True)})
        return out

    def set_craft(self, name, enabled, ilvl):
        states = self.cfg.setdefault("item_states", {}).setdefault("_craftbase", {})
        e = states.setdefault(name, {})
        e["enabled"] = bool(enabled)
        try:
            e["ilvl"] = max(1, min(82, int(ilvl)))
        except (TypeError, ValueError):
            pass
        save_config(self.cfg)
        return {"ok": True}

    # ── Auto value floor ──────────────────────────────────────────────────────

    def suggest_floors(self, league, keep_pct=40):
        """Data-driven floor suggestion: the exalt value that keeps roughly the
        top *keep_pct*% most valuable items — computed separately for uniques
        and for everything else, from the CURRENT league prices. This is the
        'Auto' floor: it adapts to the economy instead of a fixed number."""
        try:
            keep = max(5, min(95, int(keep_pct)))
            payloads = gen.fetch_all_payloads(league, gen.ALL_CATEGORIES)
            uniq_vals, gear_vals = [], []
            for key, _t, _l, is_unique in gen.ALL_CATEGORIES:
                p = payloads.get(key)
                if not isinstance(p, dict) or key in gen.PICK_ALL_CATEGORIES:
                    continue
                r = gen.exalted_rate(p)
                for line in p.get("lines", []):
                    ev = float(line.get("primaryValue") or 0.0) * (r or 1.0)
                    if ev > 0:
                        (uniq_vals if is_unique else gear_vals).append(ev)

            def pct_floor(vals):
                if not vals:
                    return 0.0
                vals.sort(reverse=True)
                idx = min(len(vals) - 1, max(0, int(len(vals) * keep / 100) - 1))
                v = vals[idx]
                # round to a human number
                for step in (0.5, 1, 2, 5, 10, 25, 50, 100):
                    if v <= step * 10:
                        return round(v / step) * step or step
                return round(v / 100) * 100
            uf, gf = pct_floor(uniq_vals), pct_floor(gear_vals)
            return {"unique": uf, "gear": gf, "keep_pct": keep,
                    "kept_unique": sum(1 for v in uniq_vals if v >= uf),
                    "total_unique": len(uniq_vals),
                    "kept_gear": sum(1 for v in gear_vals if v >= gf),
                    "total_gear": len(gear_vals)}
        except Exception as e:
            return {"error": str(e)}

    # ── Generation (same snapshot pipeline as the Tk app) ────────────────────

    def _log(self, msg):
        with self._lock:
            self._status["log"].append(msg)

    def status(self):
        with self._lock:
            out = {"running": self._status["running"], "done": self._status["done"],
                   "log": list(self._status["log"])}
            self._status["log"] = []
            return out

    def generate(self, league, min_gear, min_unique):
        with self._lock:
            if self._status["running"]:
                return {"error": "already running"}
            self._status = {"running": True, "log": [], "done": None}
        threading.Thread(target=self._generate,
                         args=(league, float(min_gear or 0), float(min_unique or 0)),
                         daemon=True).start()
        return {"ok": True}

    def _snapshot(self):
        st = self.cfg.get("item_states", {})
        enabled_cfg = self.cfg.get("category_enabled", {})
        # bake craft-base default ilvls in, like the Tk app does pre-generate
        cb = {n: dict(s) for n, s in st.get("_craftbase", {}).items()}
        for _cat, names in gen.craft_base_categories():
            for n in names:
                cb.setdefault(n, {}).setdefault("ilvl", gen.craft_base_default_ilvl(n))
        item_states = dict(st)
        item_states["_craftbase"] = cb
        return {
            "cat_enabled": {c[0]: enabled_cfg.get(c[0], True) for c in gen.ALL_CATEGORIES},
            "cat_thresh": {},          # per-category floors removed by design
            "item_states": item_states,
            "include_bases": bool(self.cfg.get("include_bases", True)),
            "base_quality": int(self.cfg.get("base_quality", 28)),
            "base_min_level": int(self.cfg.get("base_min_level", 82)),
        }

    def _generate(self, league, min_gear, min_unique):
        t0 = time.time()
        try:
            snap = self._snapshot()
            self._log(f"Fetching live prices for {league}…")
            stale = set()
            cats = [c for c in gen.ALL_CATEGORIES if snap["cat_enabled"].get(c[0], True)]
            payloads = gen.fetch_all_payloads(league, cats, stale_out=stale)
            cur = payloads.get("currency")
            if not isinstance(cur, dict):
                raise RuntimeError("poe.ninja unreachable and no cached prices for this league")
            div_rate, _found, _rate = asm.compute_divine_rate(cur)

            W = gen._W
            out = ["/" * W,
                   "//" + "  EXILEBOT 2  |  AUTO-GENERATED PICKIT".center(W - 4) + "//",
                   "/" * W,
                   f"// League  : {league}",
                   f"// Floors  : uniques >= {min_unique:g} ex · everything else >= {min_gear:g} ex",
                   f"// Divine  : 1 Divine = {div_rate:.2f} Exalted",
                   "// Source  : poe.ninja PoE2 economy API  ·  Modern UI",
                   "/" * W, "",
                   gen.header_major("Economy Items"), ""]
            top_pool = []
            ok = fail = 0
            for key, _t, label, is_unique in cats:
                p = payloads.get(key)
                if not isinstance(p, dict):
                    self._log(f"✗ {label}: no data")
                    fail += 1
                    continue
                eff = asm.effective_min(snap, key, is_unique, min_gear, min_unique)
                en = asm.enabled_names_for(key, is_unique, p,
                                           snap["item_states"].get(key, {}))
                lines = asm.build_category_lines(key, is_unique, p, div_rate,
                                                 eff, min_gear, en)
                top_pool += asm.top_items_from_lines(lines)
                out += [gen.header_sub(label), ""] + lines + [""]
                ok += 1
                self._log(f"✓ {label}")

            out += gen.STATIC_TABLET_RULES.splitlines()
            out += gen.STATIC_WOMBGIFT_RULES.splitlines()
            out += gen.STATIC_SPECIAL_WAYSTONE_RULES.splitlines()
            out += gen.build_chance_base_rules(asm.chance_base_disabled(snap))
            craft_lines, _n, _floor = asm.craft_base_section(snap)
            out += craft_lines
            if snap["include_bases"]:
                out += ["", gen.header_major("Base Types"), ""]
                out += gen.build_base_rules(min_quality=snap["base_quality"],
                                            min_level=snap["base_min_level"])

            validation = gen.validate_pickit(out)
            self._last_validation = validation
            os.makedirs(OUTPUT_DIR, exist_ok=True)
            base = (self.cfg.get("output_base") or "poe2_pickit").strip() or "poe2_pickit"
            ipd = os.path.join(OUTPUT_DIR, base + ".ipd")

            # What changed vs the previous pickit (+added / -removed rules)
            added, removed = [], []
            try:
                if os.path.isfile(ipd):
                    with open(ipd, encoding="utf-8") as f:
                        prev_ids = asm.active_rule_ids(f.read().splitlines())
                    new_ids = asm.active_rule_ids(out)
                    added   = sorted(new_ids - prev_ids)[:8]
                    removed = sorted(prev_ids - new_ids)[:8]
            except OSError:
                pass

            # Price movers (>=20% vs the last generate's snapshot)
            alerts = []
            try:
                prev_prices = self.cfg.get("last_gen_prices", {}).get(league, {})
                chaos_v = 0.0
                _, price_alerts = asm.compute_price_alerts(
                    cats, payloads, prev_prices, chaos_v, threshold=0.20)
                price_alerts.sort(key=lambda t: t[0], reverse=True)
                alerts = [t for _, t in price_alerts[:8]]
            except Exception:
                pass
            # Rotate backups of the previous pickit (keep backup_count copies)
            nkeep = int(self.cfg.get("backup_count", 5) or 0)
            if nkeep > 0 and os.path.isfile(ipd):
                try:
                    bdir = os.path.join(OUTPUT_DIR, "backups")
                    os.makedirs(bdir, exist_ok=True)
                    stamp = time.strftime("%Y%m%d-%H%M%S")
                    shutil.copy2(ipd, os.path.join(bdir, f"{base}-{stamp}.ipd"))
                    old = sorted(f for f in os.listdir(bdir)
                                 if f.startswith(base + "-") and f.endswith(".ipd"))
                    for f in old[:-nkeep]:
                        os.remove(os.path.join(bdir, f))
                except OSError:
                    self._log("✗ Backup rotation failed (continuing)")
            content = "\n".join(out)
            gen.write_text_atomic(ipd, content)
            gen.write_text_atomic(os.path.join(OUTPUT_DIR, "latest.ipd"), content)
            flt = os.path.join(OUTPUT_DIR, base + ".filter")
            gen.write_text_atomic(flt, "\n".join(gen.build_loot_filter(out)))
            self._log(f"Wrote {os.path.basename(ipd)} + .filter")

            # ── Safety net ────────────────────────────────────────────────
            # A malformed poe.ninja payload or an over-aggressive floor can
            # produce a pickit that silently skips real loot. If this run has
            # dramatically fewer active rules than the last one, or lost the
            # always-pick currency, write the file but DO NOT auto-deploy it.
            safety = ""
            try:
                prev_active = (self.cfg.get("history") or [{}])[-1].get("active", 0)
                new_active = sum(1 for l in out
                                 if l and not l.startswith("//") and "[StashItem]" in l)
                if prev_active >= 200 and new_active < prev_active * 0.6:
                    safety = (f"rule count collapsed: {new_active} vs {prev_active} last run "
                              f"(-{100 - new_active * 100 // prev_active}%)")
                joined = "\n".join(out)
                missing = [n for n in ("Divine Orb", "Exalted Orb")
                           if f'"{n}"' not in joined]
                if missing and snap["cat_enabled"].get("currency", True):
                    safety = (safety + "; " if safety else "") + \
                        "missing core currency rules: " + ", ".join(missing)
            except Exception:
                pass
            if safety:
                self._log(f"⚠ SAFETY: {safety} — auto-copy blocked, check before using this pickit")

            copied = ""
            bot = (self.cfg.get("bot_folder") or "").strip()
            if safety and self.cfg.get("auto_copy"):
                pass    # blocked — the .ipd is on disk for manual inspection only
            elif self.cfg.get("auto_copy") and bot:
                if os.path.isdir(bot):
                    shutil.copy2(ipd, os.path.join(bot, os.path.basename(ipd)))
                    copied = bot
                    self._log(f"✓ Auto-copied to {bot}")
                else:
                    self._log("✗ Auto-copy skipped: bot folder doesn't exist")
            fdir = (self.cfg.get("poe2_filter_dir") or "").strip()
            if self.cfg.get("copy_filter_to_game") and fdir and os.path.isdir(fdir):
                try:
                    shutil.copy2(flt, os.path.join(fdir, os.path.basename(flt)))
                    self._log("✓ .filter copied to the PoE2 folder")
                except OSError:
                    self._log("✗ Couldn't copy .filter to the game folder")

            self._last_lines = out
            active = sum(1 for l in out if l and not l.startswith("//") and "[StashItem]" in l)
            commented = sum(1 for l in out if l.startswith("//") and "[StashItem]" in l)
            top_pool.sort(key=lambda t: -t[1])
            _seen = set()
            top_pool = [t for t in top_pool
                        if not (t[0] in _seen or _seen.add(t[0]))]
            self.cfg.update({"league": league,
                             "min_exalt_gear": min_gear, "min_exalt": min_gear,
                             "min_exalt_unique": min_unique})
            # Run history (same shape the Tk app writes)
            hist = self.cfg.setdefault("history", [])
            hist.append({"ts": time.strftime("%Y-%m-%d %H:%M"),
                         "active": active, "commented": commented,
                         "divine_rate": div_rate,
                         "top_item": top_pool[0][0] if top_pool else "",
                         "top_value": round(top_pool[0][1], 1) if top_pool else 0,
                         "duration": f"{time.time() - t0:.1f}s"})
            del hist[:-50]
            # Price snapshot for next run's change arrows
            try:
                snap_prices = {}
                for key, _t, _l, is_u in cats:
                    p2 = payloads.get(key)
                    if not isinstance(p2, dict):
                        continue
                    r2 = gen.exalted_rate(p2)
                    d2 = {}
                    if is_u:
                        for ln in p2.get("lines", []):
                            if ln.get("name"):
                                d2[ln["name"]] = float(ln.get("primaryValue") or 0) * (r2 or 1.0)
                    else:
                        by2 = {i["id"]: i for i in p2.get("items", [])}
                        for ln in p2.get("lines", []):
                            it2 = by2.get(ln.get("id"))
                            if it2 and it2.get("name"):
                                d2[it2["name"]] = float(ln.get("primaryValue") or 0) * (r2 or 1.0)
                    snap_prices[key] = d2
                self.cfg["last_gen_prices"] = {league: snap_prices}
            except Exception:
                pass
            save_config(self.cfg)
            with self._lock:
                self._status["running"] = False
                self._status["done"] = {
                    "ok": True, "path": ipd, "active": active, "commented": commented,
                    "cats_ok": ok, "cats_fail": fail, "stale": len(stale),
                    "divine_rate": round(div_rate, 1),
                    "secs": round(time.time() - t0, 1),
                    "top": [{"name": n, "ex": round(v, 1)} for n, v in top_pool[:3]],
                    "val_errors": len(validation.get("errors", [])),
                    "val_warnings": len(validation.get("warnings", [])),
                    "copied": copied,
                    "added": added, "removed": removed, "alerts": alerts,
                    "safety": safety,
                }
        except Exception as e:
            with self._lock:
                self._status["running"] = False
                self._status["done"] = {"ok": False, "error": str(e)}

    # ── Preview / misc ────────────────────────────────────────────────────────

    def preview(self):
        if self._last_lines:
            return self._last_lines
        # fall back to the last file on disk so Preview works right after launch
        base = (self.cfg.get("output_base") or "poe2_pickit").strip() or "poe2_pickit"
        try:
            with open(os.path.join(OUTPUT_DIR, base + ".ipd"), encoding="utf-8") as f:
                return f.read().splitlines()
        except OSError:
            return []

    def validation(self):
        """Full error/warning list from the last generate (Preview banner)."""
        v = getattr(self, "_last_validation", None) or {"errors": [], "warnings": []}
        return {"errors": [f"Line {n}: {m}" for n, m in v.get("errors", [])],
                "warnings": [f"Line {n}: {m}" for n, m in v.get("warnings", [])]}

    def profile_get(self, name):
        """Profile snapshot summary for the Compare view."""
        p = self.cfg.get("profiles", {}).get(name)
        if not p:
            return {"error": "not found"}
        st = p.get("item_states", {})
        return {"min_gear": p.get("min_exalt_gear", 0), "min_unique": p.get("min_exalt_unique", 0),
                "output_base": p.get("output_base", ""), "include_bases": p.get("include_bases", True),
                "base_quality": p.get("base_quality", 28), "base_min_level": p.get("base_min_level", 82),
                "disabled_counts": {k: sum(1 for s in v.values() if not s.get("enabled", True))
                                    for k, v in st.items() if isinstance(v, dict)}}

    def open_file(self, kind):
        """Open the last .ipd / .filter / debug log / config with the default app."""
        from exilebot_pickit.ui.config import LOG_PATH, CONFIG_PATH
        base = (self.cfg.get("output_base") or "poe2_pickit").strip() or "poe2_pickit"
        paths = {"ipd": os.path.join(OUTPUT_DIR, base + ".ipd"),
                 "filter": os.path.join(OUTPUT_DIR, base + ".filter"),
                 "log": LOG_PATH, "config": CONFIG_PATH}
        p = paths.get(kind)
        if not p or not os.path.isfile(p):
            return {"error": "file not found — generate first"}
        os.startfile(p)   # noqa: S606
        return {"ok": True}

    def clear_history(self):
        self.cfg["history"] = []
        save_config(self.cfg)
        return {"ok": True}

    def chaos_ex(self, league):
        """Exalt value of 1 Chaos Orb (for the Chaos display unit)."""
        try:
            p = gen.fetch_all_payloads(league, [("currency", "Currency", "Currency", False)])["currency"]
            r = gen.exalted_rate(p)
            by_id = {i["id"]: i for i in p.get("items", [])}
            for line in p.get("lines", []):
                it = by_id.get(line.get("id"))
                if it and it.get("name") == "Chaos Orb":
                    return {"ex": float(line.get("primaryValue") or 0) * (r or 1.0)}
            return {"ex": 0.0}
        except Exception:
            return {"ex": 0.0}

    def open_output(self):
        try:
            os.startfile(OUTPUT_DIR)   # noqa: S606 — local folder open, Windows only
            return {"ok": True}
        except Exception as e:
            return {"error": str(e)}

    def browse_folder(self):
        """Native folder picker for the bot-folder setting."""
        try:
            import webview
            w = webview.windows[0]
            res = w.create_file_dialog(webview.FOLDER_DIALOG)
            return {"path": res[0] if res else ""}
        except Exception as e:
            return {"error": str(e)}


# Back-compat alias (poc.py of the first preview imported PocApi)
PocApi = AppApi
