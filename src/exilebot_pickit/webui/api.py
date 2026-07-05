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
}


class AppApi:
    def __init__(self):
        self._lock = threading.Lock()
        self._status = {"running": False, "log": [], "done": None}
        self._last_lines: list = []
        self.cfg = load_config()
        gen.set_disk_cache_dir(PRICE_CACHE_DIR)

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
        """All categories with their items, live/cached values, and on/off state."""
        try:
            payloads = gen.fetch_all_payloads(league, gen.ALL_CATEGORIES)
            cur = payloads.get("currency")
            div_rate, _, rate = asm.compute_divine_rate(cur) if isinstance(cur, dict) else (1.0, False, 0.0)
            states = self.cfg.get("item_states", {})
            out = []
            for key, _t, label, is_unique in gen.ALL_CATEGORIES:
                p = payloads.get(key)
                if not isinstance(p, dict):
                    out.append({"key": key, "label": label, "unique": is_unique,
                                "error": str(p) if p else "no data", "items": []})
                    continue
                cat_states = states.get(key, {})
                r = gen.exalted_rate(p)
                items, seen = [], set()
                if is_unique:
                    for line in p.get("lines", []):
                        nm = line.get("name")
                        if not nm or nm in seen:
                            continue
                        seen.add(nm)
                        ev = float(line.get("primaryValue") or 0.0) * (r or 1.0)
                        items.append({"name": nm, "base": line.get("baseType", ""),
                                      "ex": round(ev, 2), "enabled": True})
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
                        items.append({"name": nm, "base": "", "ex": round(ev, 2),
                                      "enabled": cat_states.get(nm, {}).get("enabled", True)})
                items.sort(key=lambda i: -i["ex"])
                out.append({"key": key, "label": label, "unique": is_unique, "items": items})
            enabled_cfg = self.cfg.get("category_enabled", {})
            return {"divine_rate": round(div_rate, 1),
                    "cats": out,
                    "cat_enabled": {c[0]: enabled_cfg.get(c[0], True) for c in gen.ALL_CATEGORIES}}
        except Exception as e:
            return {"error": str(e)}

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
            return {"unique": pct_floor(uniq_vals), "gear": pct_floor(gear_vals),
                    "keep_pct": keep}
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
            os.makedirs(OUTPUT_DIR, exist_ok=True)
            base = (self.cfg.get("output_base") or "poe2_pickit").strip() or "poe2_pickit"
            ipd = os.path.join(OUTPUT_DIR, base + ".ipd")
            content = "\n".join(out)
            gen.write_text_atomic(ipd, content)
            gen.write_text_atomic(os.path.join(OUTPUT_DIR, "latest.ipd"), content)
            flt = os.path.join(OUTPUT_DIR, base + ".filter")
            gen.write_text_atomic(flt, "\n".join(gen.build_loot_filter(out)))
            self._log(f"Wrote {os.path.basename(ipd)} + .filter")

            copied = ""
            bot = (self.cfg.get("bot_folder") or "").strip()
            if self.cfg.get("auto_copy") and bot:
                if os.path.isdir(bot):
                    shutil.copy2(ipd, os.path.join(bot, os.path.basename(ipd)))
                    copied = bot
                    self._log(f"✓ Auto-copied to {bot}")
                else:
                    self._log("✗ Auto-copy skipped: bot folder doesn't exist")

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
