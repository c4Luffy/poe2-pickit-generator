"""Python<->JS bridge for the modern (WebView2) UI.

Reuses the EXISTING engine end-to-end: api.client for payloads,
generators/assembly for the snapshot-driven rule pipeline (the same one the
Tkinter app uses), ui.config for the shared config file. The web UI reads and
writes the SAME config/item-state data as the Tk app, so the two front-ends
can be used interchangeably while the modern UI matures.

Everything JS-callable returns plain JSON-able dicts/lists. Long work
(generation) runs on a worker thread; the page polls status() for log lines.
"""

import math
import os
import random
import re
import shutil
import threading
import time

from exilebot_pickit import generator as gen
from exilebot_pickit.generators import assembly as asm
from exilebot_pickit.ui.config import (
    OUTPUT_DIR, PRESET_KEYS, PRESETS, PRICE_CACHE_DIR, load_config, log_exc, log_info,
    save_config,
    _default_poe2_filter_dir as _default_dir,
)
from exilebot_pickit.version import VERSION

# Settings JS may write via set_setting() — a whitelist so a compromised page
# can't scribble arbitrary keys into the config file.
_SETTABLE = {
    "league", "output_base", "bot_folder", "auto_copy", "theme",
    "min_exalt_gear", "min_exalt_unique", "include_bases",
    "auto_floor", "auto_floor_pct",
    "base_quality", "base_min_level", "backup_count",
    "copy_filter_to_game", "poe2_filter_dir", "filter_theme",
    "magic_rare_flasks", "known_leagues", "rare_gear_enabled",
    "setup_done",
}


def _config_warning() -> str:
    from exilebot_pickit.ui import config as _c
    return _c.CONFIG_LOAD_ERROR or ""


def _theme_or_default(value) -> str:
    """THE theme normalization — read path, write path and import path all use
    this one membership test so the stored value, the dropdown and the written
    filter can never disagree about which theme applies."""
    return value if value in gen.FILTER_THEMES else gen.DEFAULT_FILTER_THEME


class AppApi:
    def __init__(self):
        self._lock = threading.Lock()
        self._status = {"running": False, "log": [], "done": None}
        self._dl = {"active": False, "pct": 0, "done_mb": 0.0, "total_mb": 0.0, "result": None}
        self._last_lines: list = []
        self._eco = {"running": False, "result": None}
        self.cfg = load_config()
        gen.set_disk_cache_dir(PRICE_CACHE_DIR)
        gen.prune_disk_cache(max_age_days=60)
        # latest.ipd was an always-same-name duplicate of the output pickit that
        # nothing ever read — users opening the folder couldn't tell which file
        # their bot needed. We stopped writing it; remove any stale copy.
        # UNLESS the user's own output name is "latest" — then latest.ipd IS
        # their real pickit and deleting it here would destroy it every launch.
        if (self.cfg.get("output_base") or "").strip().lower() != "latest":
            try:
                os.remove(os.path.join(OUTPUT_DIR, "latest.ipd"))
            except OSError:
                pass
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
            # First-run wizard. "Have you ever actually generated?" is the only honest
            # test of a new user: league is auto-saved the moment the list loads (v4.25.0)
            # and bot_folder is auto-detected, so neither says anything about experience.
            "setup_done": bool(c.get("setup_done", False)),
            "has_history": bool(c.get("history")),
            "theme": (c.get("theme") or "dark").lower(),
            "output_base": c.get("output_base", "poe2_pickit"),
            "bot_folder": c.get("bot_folder", ""),
            "auto_copy": bool(c.get("auto_copy", False)),
            "min_gear": float(c.get("min_exalt_gear", 0.0)),
            "min_unique": float(c.get("min_exalt_unique", 0.0)),
            "include_bases": bool(c.get("include_bases", True)),
            "auto_floor": bool(c.get("auto_floor", False)),
            "auto_floor_pct": int(c.get("auto_floor_pct", 40) or 40),
            "base_quality": int(c.get("base_quality", 25)),
            "base_min_level": int(c.get("base_min_level", 82)),
            "copy_filter_to_game": bool(c.get("copy_filter_to_game", False)),
            "poe2_filter_dir": c.get("poe2_filter_dir", "") or _default_dir(),
            "backup_count": int(c.get("backup_count", 5)),
            "config_warning": _config_warning(),
            "known_leagues": list(c.get("known_leagues") or []),
            "active_preset": c.get("active_preset", "") or "",
            "filter_theme": _theme_or_default(c.get("filter_theme")),
            # The style table itself: the ground-label preview and the tier
            # chips render from it, so the UI can never drift from
            # generators/filter_themes.THEMES.
            "filter_themes": gen.FILTER_THEMES,
        }

    def set_setting(self, key, value):
        if key not in _SETTABLE:
            return {"error": f"setting '{key}' not allowed"}
        if key == "output_base":
            # This becomes a filename (and a backup-name prefix). Unsanitized it
            # broke three ways: an absolute path made os.path.join ignore
            # OUTPUT_DIR entirely; Windows-reserved chars (: ? * < > | " / \)
            # made the atomic write raise AFTER backup rotation already ran; and
            # a backslash broke every startswith(base + "-") backup-prefix check.
            value = re.sub(r'[<>:"/\\|?*\x00-\x1f]', "_", str(value)).strip(". ") \
                or "poe2_pickit"
        if key == "filter_theme":
            # Never store a theme the engine doesn't know — the lookup would
            # fall back anyway, but the UI dropdown must reflect a real choice.
            value = _theme_or_default(value)
        self.cfg[key] = value
        if key == "min_exalt_gear":            # keep legacy mirror in sync
            self.cfg["min_exalt"] = value
        if key in PRESET_KEYS:
            # Hand-editing a floor means the numbers no longer match the preset
            # they came from — stop claiming that preset is active.
            self.cfg["active_preset"] = ""
        save_config(self.cfg)
        return {"ok": True}

    def presets(self):
        """The ready-made setting bundles, plus which one is currently active.
        `cfg` is stripped — the UI only needs the human-facing copy."""
        return {"presets": [{k: v for k, v in p.items() if k != "cfg"} for p in PRESETS],
                "active": self.cfg.get("active_preset", "") or ""}

    def apply_preset(self, key):
        """Apply a ready-made preset over the current settings."""
        p = next((x for x in PRESETS if x["key"] == key), None)
        if not p:
            return {"ok": False, "error": f"unknown preset '{key}'"}
        self.cfg.update(p["cfg"])
        self.cfg["min_exalt"] = self.cfg["min_exalt_gear"]      # legacy mirror
        # The unique economy categories are the one thing a preset can switch off
        # wholesale (Currency only) — put them back on for every other preset.
        want_uniques = not p.get("uniques_off", False)
        ce = dict(self.cfg.get("category_enabled", {}))
        for c in gen.ALL_CATEGORIES:
            if c[0].startswith("unique_"):
                ce[c[0]] = want_uniques
        self.cfg["category_enabled"] = ce
        self.cfg["active_preset"] = key
        save_config(self.cfg)
        log_info(f"preset applied: {key}")
        return {"ok": True, "name": p["name"], "floors": p["floors"]}

    def leagues(self):
        try:
            # current leagues only — finished ones come suffixed "(old)"
            # from the client and just clutter the dropdown
            return [{"name": n, "display": d}
                    for n, _, d in gen.fetch_live_leagues()
                    if not d.endswith("(old)")]
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
            # name → icon URL: poe2db art for the always-pick items, plus
            # anything the fetched payloads carry
            from exilebot_pickit.data.icons import STATIC_ICONS
            icon_idx = dict(STATIC_ICONS)
            for _p in payloads.values():
                if not isinstance(_p, dict):
                    continue
                for i in _p.get("items", []):
                    img = i.get("image") or ""
                    if i.get("name") and img:
                        icon_idx.setdefault(
                            i["name"],
                            ("https://web.poecdn.com" + img) if img.startswith("/") else img)
                for ln in _p.get("lines", []):
                    if ln.get("name") and ln.get("icon"):
                        icon_idx.setdefault(ln["name"], ln["icon"])
            out = []
            priced = set()      # names shown in priced categories (dedupe)
            for key, _t, label, is_unique in gen.ALL_CATEGORIES:
                if key == "waystones":
                    # poe.ninja doesn't price waystones — show the three
                    # pickup rules as toggleable rows instead of an empty list
                    ws = states.get("waystones", {})
                    out.append({"key": key, "label": label, "unique": False,
                                "items": [{"name": nm, "base": "any tier",
                                           "ex": 0, "icon": icon_idx.get("Waystone", ""),
                                           "chg": None, "static": True, "emj": "🗺️",
                                           "enabled": ws.get(nm, {}).get("enabled", True)}
                                          for nm in gen.WAYSTONE_TOGGLE_NAMES.values()]})
                    continue
                p = payloads.get(key)
                if not isinstance(p, dict):
                    out.append({"key": key, "label": label, "unique": is_unique,
                                "error": str(p) if p else "no data", "items": []})
                    continue
                cat_states = states.get(key, {})
                prev_cat = prev.get(key, {}) if isinstance(prev, dict) else {}
                r = gen.exalted_rate(p)
                items, seen = [], set()

                def _chg(nm, ev, spark=None, prev_cat=prev_cat):
                    """% change: poe.ninja 7-day sparkline for uniques, else
                    vs the price snapshot from the last generate. prev_cat is
                    bound per-iteration via the default arg (ruff B023)."""
                    if spark and spark.get("totalChange") is not None:
                        return round(float(spark["totalChange"]), 1)
                    old = prev_cat.get(nm)
                    if isinstance(old, (int, float)) and old > 0 and ev > 0:
                        return round((ev - old) / old * 100, 1)
                    return None

                def _spark(spark):
                    """The 7-day shape poe.ninja already sends us, for a row sparkline.

                    Each point is the cumulative % change from day 0, so the line shows
                    the trend, not absolute prices. We only ever read totalChange out of
                    this and threw the curve away. poe.ninja does emit nulls, and a
                    single point can't be drawn, so both come back as None.
                    """
                    pts = (spark or {}).get("data") or []
                    # isfinite: a NaN/Infinity reaching the bridge is fatal — pywebview
                    # json.dumps emits the bare token, JS JSON.parse throws, and the
                    # awaiting promise hangs forever (Economy stuck on its spinner).
                    vals = [float(v) for v in pts
                            if isinstance(v, (int, float)) and math.isfinite(v)]
                    return [round(v, 2) for v in vals] if len(vals) >= 2 else None

                if is_unique:
                    for line in p.get("lines", []):
                        nm = line.get("name")
                        if not nm or nm in seen:
                            continue
                        seen.add(nm)
                        ev = float(line.get("primaryValue") or 0.0) * (r or 1.0)
                        if not math.isfinite(ev):
                            ev = 0.0           # NaN over the bridge hangs the JS promise
                        items.append({"name": nm, "base": line.get("baseType", ""),
                                      "ex": round(ev, 2),
                                      "enabled": cat_states.get(nm, {}).get("enabled", True),
                                      "icon": line.get("icon") or "",
                                      "chg": _chg(nm, ev, line.get("sparkLine")),
                                      "spark": _spark(line.get("sparkLine"))})
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
                        if not math.isfinite(ev):
                            ev = 0.0           # NaN over the bridge hangs the JS promise
                        img = it.get("image") or ""
                        if img and img.startswith("/"):
                            img = "https://web.poecdn.com" + img
                        items.append({"name": nm, "base": "", "ex": round(ev, 2),
                                      "enabled": cat_states.get(nm, {}).get("enabled", True),
                                      "icon": img, "chg": _chg(nm, ev)})
                items.sort(key=lambda i: -i["ex"])
                if not is_unique:
                    priced.update(i["name"] for i in items)
                out.append({"key": key, "label": label, "unique": is_unique, "items": items})

            # Synthetic always-pick categories (no poe.ninja prices — picked
            # because they're map juice/valuable bases, not exchange value).
            # Each group is its own sidebar entry with its own toggles.
            _emj = {"_ap_tablets": "🗿", "_ap_frag": "🧩", "_ap_exotic": "🧿"}
            for key, label, rows in self._ap_groups():
                st = {**states.get("_static", {}), **states.get(key, {})}  # _static = pre-split legacy
                items = [{"name": nm, "base": base, "ex": 0,
                          "icon": icon_idx.get(nm, ""),
                          "chg": None, "static": True, "emj": _emj.get(key, "📌"),
                          "enabled": st.get(nm, {}).get("enabled", True)}
                         # ninja prices it → it lives in its priced category
                         # (force-kept above the floor there), not here too
                         for nm, base in rows if nm not in priced]
                out.append({"key": key, "label": label, "unique": False,
                            "items": items})

            enabled_cfg = self.cfg.get("category_enabled", {})
            cat_en = {c[0]: enabled_cfg.get(c[0], True) for c in gen.ALL_CATEGORIES}
            for key, _l, _r in self._ap_groups():
                cat_en[key] = enabled_cfg.get(key, enabled_cfg.get("_static", True))
            return {"divine_rate": round(div_rate, 1),
                    "cats": out, "stale": sorted(stale),
                    "cat_enabled": cat_en}
        except Exception as e:
            return {"error": str(e)}

    def economy_start(self, league):
        """Non-blocking entry point for the Economy tab. `economy()` itself
        does several parallel poe.ninja fetches with retry/backoff (up to ~30s
        per stalled category) — called directly from JS on every tab open and
        league switch, that synchronous wait was freezing the whole window
        whenever poe.ninja was slow or rate-limited. Same fire-and-poll
        pattern as generate()/download_update()."""
        with self._lock:
            if self._eco.get("running"):
                return {"error": "already running"}
            self._eco = {"running": True, "result": None}
        threading.Thread(target=self._economy_worker, args=(league,), daemon=True).start()
        return {"ok": True}

    def _economy_worker(self, league):
        result = self.economy(league)
        with self._lock:
            self._eco["running"] = False
            self._eco["result"] = result

    def economy_poll(self):
        with self._lock:
            return {"running": self._eco.get("running", False), "result": self._eco.get("result")}

    @staticmethod
    def _ap_groups():
        """The always-pick groups shown as their own Economy categories.
        Each: (category key, sidebar label, [(item name, sub label), ...])."""
        return [
            ("_ap_tablets", "Tablets",
             [(t, "all rarities") for t in gen.TABLET_TYPES]
             + [(un, f"unique · {typ}") for typ, un in gen.TABLET_UNIQUES]),
            ("_ap_frag", "Fragments & Keys",
             [(s, "splinter") for s in gen.SPLINTERS]
             + [(w, "wombgift") for w in gen.WOMBGIFTS]
             + [(sp, "key") for sp in gen.SPECIAL_ITEMS]),
            ("_ap_exotic",  "Exotic Bases", [(b, "") for b in gen.EXOTIC_BASES]),
        ]

    def _ap_disabled(self, snap):
        """Names switched off across all always-pick groups — a group whose
        whole category is off contributes every one of its names."""
        states = snap["item_states"]
        legacy = states.get("_static", {})
        dis = {n for n, s in legacy.items() if not s.get("enabled", True)}
        for key, _label, rows in self._ap_groups():
            if not snap["cat_enabled"].get(key, True):
                dis.update(n for n, _b in rows)
                continue
            st = states.get(key, {})
            dis.update(n for n, s in st.items() if not s.get("enabled", True))
        return dis

    def set_items_bulk(self, cat_key, names, enabled):
        """Enable/disable every listed item of a category at once."""
        states = self.cfg.setdefault("item_states", {}).setdefault(cat_key, {})
        for n in names:
            states.setdefault(n, {})["enabled"] = bool(enabled)
        save_config(self.cfg)
        return {"ok": True}

    def copy_text(self, text):
        """Copy to the Windows clipboard natively — navigator.clipboard is
        unreliable inside WebView2 (blocked in non-secure contexts)."""
        try:
            import ctypes
            from ctypes import wintypes
            # Explicit types on private DLL handles. ctypes defaults every return to a
            # 32-bit int, which TRUNCATES GlobalAlloc's 64-bit handle whenever the
            # allocation lands above 4 GB — GlobalLock on the mangled handle returned
            # NULL and memmove wrote to address 0. So every Copy button in the app
            # failed intermittently, and (EmptyClipboard having already run) wiped the
            # user's clipboard on the way down.
            u32 = ctypes.WinDLL("user32", use_last_error=True)
            k32 = ctypes.WinDLL("kernel32", use_last_error=True)
            k32.GlobalAlloc.restype = wintypes.HGLOBAL
            k32.GlobalAlloc.argtypes = [wintypes.UINT, ctypes.c_size_t]
            k32.GlobalLock.restype = wintypes.LPVOID
            k32.GlobalLock.argtypes = [wintypes.HGLOBAL]
            k32.GlobalUnlock.argtypes = [wintypes.HGLOBAL]
            k32.GlobalFree.restype = wintypes.HGLOBAL
            k32.GlobalFree.argtypes = [wintypes.HGLOBAL]
            u32.SetClipboardData.restype = wintypes.HANDLE
            u32.SetClipboardData.argtypes = [wintypes.UINT, wintypes.HANDLE]
            s = str(text)
            if not u32.OpenClipboard(None):
                return {"error": "clipboard busy"}
            try:
                u32.EmptyClipboard()
                buf = ctypes.create_unicode_buffer(s)
                size = ctypes.sizeof(buf)
                h = k32.GlobalAlloc(0x0042, size)          # GMEM_MOVEABLE|ZEROINIT
                if not h:
                    return {"error": "clipboard alloc failed"}
                p = k32.GlobalLock(h)
                if not p:
                    k32.GlobalFree(h)                      # ours until SetClipboardData takes it
                    return {"error": "clipboard lock failed"}
                ctypes.memmove(p, buf, size)
                k32.GlobalUnlock(h)
                # The system owns the handle ONLY if this succeeds; on failure we
                # must free it — and must not report ok with an emptied clipboard.
                if not u32.SetClipboardData(13, h):        # CF_UNICODETEXT
                    k32.GlobalFree(h)
                    return {"error": "clipboard write failed"}
            finally:
                u32.CloseClipboard()
            return {"ok": True}
        except Exception as e:
            return {"error": str(e)}

    def get_clipboard(self):
        """Read the Windows clipboard — the mirror of copy_text, for Item Check's
        auto-paste: the user just pressed Ctrl+C on an item in game, so opening the
        tab should not also demand a Ctrl+V. Returns {"text": ""} on anything odd
        (empty, non-text, clipboard busy) — auto-paste is best-effort by design."""
        try:
            import ctypes
            from ctypes import wintypes
            # Private DLL instances with explicit types. ctypes defaults every return
            # to a 32-bit int, which TRUNCATES the 64-bit clipboard handle — GlobalLock
            # on the mangled handle then faults. (ctypes.windll.* is also process-wide
            # shared state; setting argtypes there would leak into copy_text.)
            u32 = ctypes.WinDLL("user32", use_last_error=True)
            k32 = ctypes.WinDLL("kernel32", use_last_error=True)
            u32.GetClipboardData.restype = wintypes.HANDLE
            k32.GlobalLock.restype = wintypes.LPVOID
            k32.GlobalLock.argtypes = [wintypes.HGLOBAL]
            k32.GlobalUnlock.argtypes = [wintypes.HGLOBAL]
            if not u32.IsClipboardFormatAvailable(13):     # CF_UNICODETEXT
                return {"text": ""}
            if not u32.OpenClipboard(None):
                return {"text": ""}
            try:
                h = u32.GetClipboardData(13)
                if not h:
                    return {"text": ""}
                p = k32.GlobalLock(h)
                try:
                    text = ctypes.wstring_at(p) if p else ""
                finally:
                    k32.GlobalUnlock(h)
                # an item copy is ~2 KB; anything huge is not an item
                return {"text": text[:20000]}
            finally:
                u32.CloseClipboard()
        except Exception:
            return {"text": ""}

    def rule_for(self, cat_key, name, is_unique, base, ex):
        """The pickit rule line for one item — for right-click 'copy rule'."""
        safe = name.replace('"', '\\"')
        if is_unique:
            sb = gen.strip_runeforged_base(base or "").replace('"', '\\"')
            return (f'[Type] == "{sb}" && [Rarity] == "Unique" # [UniqueName] == "{safe}" '
                    f'&& [StashItem] == "true" // ExValue = {float(ex):.2f}')
        if cat_key == "waystones":
            for rar, nm in gen.WAYSTONE_TOGGLE_NAMES.items():
                if nm == name:
                    return next((r for r in gen.WAYSTONE_FALLBACK_RULES
                                 if f'"{rar}"' in r), "")
        if cat_key == "_static" or cat_key.startswith("_ap_"):
            if any(name == n for _t, n in gen.TABLET_UNIQUES):
                typ = next(t for t, n in gen.TABLET_UNIQUES if n == name)
                st = typ.replace('"', '\\"')
                return (f'[Type] == "{st}" && [Rarity] == "Unique" # [UniqueName] == "{safe}" '
                        f'&& [StashItem] == "true" && [IgnoreRitual] == "true"')
            return f'[Type] == "{safe}" # [StashItem] == "true"'
        return f'[Type] == "{safe}" # [StashItem] == "true" // ExValue = {float(ex):.2f}'

    # ── Profiles ──────────────────────────────────────────────────────────────

    def _profile_snapshot(self):
        c = self.cfg
        import copy as _copy
        return {"item_states": _copy.deepcopy(c.get("item_states", {})),
                "category_enabled": _copy.deepcopy(c.get("category_enabled", {})),
                "min_exalt": float(c.get("min_exalt_gear", 0.0)),
                "min_exalt_gear": float(c.get("min_exalt_gear", 0.0)),
                "min_exalt_unique": float(c.get("min_exalt_unique", 0.0)),
                "output_base": c.get("output_base", "poe2_pickit"),
                "include_bases": bool(c.get("include_bases", True)),
                "auto_floor": bool(c.get("auto_floor", False)),
            "auto_floor_pct": int(c.get("auto_floor_pct", 40) or 40),
                "base_quality": int(c.get("base_quality", 25)),
                "base_min_level": int(c.get("base_min_level", 82))}

    # item_states buckets that aren't economy categories — used to describe a
    # profile in plain language ("what did this profile actually change?").
    _PROFILE_SECTIONS = {
        "_chance": "Chance bases",
        "_craftbase": "Craft bases",
        "_excbase": "Exceptional bases",
        "_fracture": "Fracture targets",
        "_raregear": "Rare gear slots",
    }

    def _describe_profile(self, prof):
        """Plain-language rows describing what a profile changes.

        A profile stores absolute state, not a diff, so "what's in it" means:
        the floors it pins, and — the part that actually matters when someone
        shares a profile — everything it switches OFF. A silently disabled
        Divine Orb or a whole category turned off would otherwise cost the
        importer real loot with no warning, so those rows are NAMED (not just
        counted) and flagged so the UI can shout about them.
        """
        prof = prof or {}
        rows = []

        def add(k, v, warn=False):
            rows.append({"k": k, "v": v, "warn": bool(warn)})

        gear = float(prof.get("min_exalt_gear", 0) or 0)
        uniq = float(prof.get("min_exalt_unique", 0) or 0)
        if prof.get("auto_floor"):
            add("Floors", "Auto-floor ON — keeps the top "
                          f"{int(prof.get('auto_floor_pct', 40) or 40)}%")
        else:
            add("Floors", f"currency & items >= {gear:g} ex  ·  uniques >= {uniq:g} ex")
        add("Output file", (prof.get("output_base") or "poe2_pickit") + ".ipd")

        def names_off(bucket):
            return sorted(n for n, v in (bucket or {}).items()
                          if isinstance(v, dict) and v.get("enabled") is False)

        def listing(names, cap=6):
            shown = ", ".join(names[:cap])
            return shown + (f"  +{len(names) - cap} more" if len(names) > cap else "")

        states = prof.get("item_states") or {}
        total_off = 0

        # whole categories switched off — the biggest silent loot-killer
        cats_off = sorted(k for k, v in (prof.get("category_enabled") or {}).items()
                          if v is False)
        if cats_off:
            total_off += len(cats_off)
            add("Whole categories OFF", listing(cats_off, 8), warn=True)

        # named sections (chance / craft / exceptional / fracture / rare slots)
        for key, label in self._PROFILE_SECTIONS.items():
            off = names_off(states.get(key))
            if off:
                total_off += len(off)
                add(f"{label} off", f"{len(off)} — {listing(off)}", warn=True)

        # economy items, BY NAME per category (a bare count would hide a
        # disabled Divine Orb, which is exactly what people need to see)
        eco = {}
        for key, bucket in states.items():
            if key in self._PROFILE_SECTIONS or not isinstance(bucket, dict):
                continue
            off = names_off(bucket)
            if off:
                eco[key] = off
        if eco:
            eco_total = sum(len(v) for v in eco.values())
            total_off += eco_total
            for key in sorted(eco)[:4]:
                add(f"Economy · {key} off", f"{len(eco[key])} — {listing(eco[key])}",
                    warn=True)
            if len(eco) > 4:
                rest = sum(len(v) for k, v in eco.items() if k not in sorted(eco)[:4])
                add("Economy · other categories off",
                    f"{rest} more items across {len(eco) - 4} categories", warn=True)
            add("Items disabled in total", str(eco_total), warn=True)

        if not prof.get("include_bases", True):
            total_off += 1
            add("Base rules", "EXCLUDED — no craft/exceptional base rules at all",
                warn=True)

        if not total_off:
            add("Loot rules", "Nothing disabled — every category and item stays ON")

        add("Exceptional bases",
            f"quality >= {prof.get('base_quality', 25)}%  ·  ilvl >= {prof.get('base_min_level', 82)}")
        return rows

    def profile_summary(self, name):
        """What does this saved profile actually change? (for the UI preview)"""
        prof = (self.cfg.get("profiles") or {}).get(name)
        if not prof:
            return {"error": "profile not found"}
        return {"name": name, "rows": self._describe_profile(prof)}

    def profile_export(self, name):
        """Write one profile to a shareable .json file."""
        import json
        import webview
        prof = (self.cfg.get("profiles") or {}).get(name)
        if not prof:
            return {"error": "Pick a profile to export first."}
        safe = re.sub(r"[^A-Za-z0-9_.-]+", "_", name).strip("_") or "profile"
        w = webview.windows[0]
        path = w.create_file_dialog(webview.SAVE_DIALOG,
                                    save_filename=f"{safe}.pickitprofile.json")
        if not path:
            return {"cancelled": True}
        if isinstance(path, (list, tuple)):
            path = path[0]
        path = str(path)
        payload = {"kind": "exilebot-pickit-profile", "v": 1,
                   "name": name, "app": VERSION, "profile": prof}
        try:
            gen.write_text_atomic(path, json.dumps(payload, indent=1))
        except OSError as e:
            return {"error": f"Couldn't write that file: {e}"}
        return {"ok": True, "path": path}

    def profile_import_preview(self):
        """Pick a .json profile and describe it — nothing is saved yet."""
        import json
        import webview
        w = webview.windows[0]
        res = w.create_file_dialog(
            webview.OPEN_DIALOG,
            file_types=("Pickit profile (*.json)", "All files (*.*)"))
        if not res:
            return {"cancelled": True}
        path = str(res[0] if isinstance(res, (list, tuple)) else res)
        try:
            if os.path.getsize(path) > 4 * 1024 * 1024:
                return {"error": "That file is far too big to be a profile."}
            with open(path, encoding="utf-8-sig") as f:
                data = json.load(f)
        except (OSError, ValueError) as e:
            return {"error": f"That isn't a readable profile file ({e})."}
        prof = data.get("profile") if isinstance(data, dict) else None
        if not isinstance(prof, dict) or data.get("kind") != "exilebot-pickit-profile":
            return {"error": "That JSON isn't an ExileBot pickit profile."}
        name = str(data.get("name") or "imported")
        self._pending_profile = (name, prof)
        return {"ok": True, "name": name, "path": path,
                "exists": name in (self.cfg.get("profiles") or {}),
                "rows": self._describe_profile(prof)}

    def profile_import_commit(self, name):
        """Save the previewed profile under `name`. Does NOT switch to it —
        importing shouldn't silently replace the settings you're using."""
        pending = getattr(self, "_pending_profile", None)
        if not pending:
            return {"error": "Nothing to import — pick a file again."}
        name = (name or pending[0] or "").strip()
        if not name:
            return {"error": "empty name"}
        self.cfg.setdefault("profiles", {})[name] = pending[1]
        self._pending_profile = None
        save_config(self.cfg)
        return {"ok": True, "name": name}

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
        # category-wide toggles drive generation, so restore them too (older
        # profiles saved before this existed simply carry an empty dict = all on)
        self.cfg["category_enabled"] = _copy.deepcopy(prof.get("category_enabled", {}))
        self.cfg["min_exalt_gear"]   = prof.get("min_exalt_gear", 0.0)
        self.cfg["min_exalt"]        = self.cfg["min_exalt_gear"]
        self.cfg["min_exalt_unique"] = prof.get("min_exalt_unique", 0.0)
        self.cfg["output_base"]      = prof.get("output_base", "poe2_pickit")
        self.cfg["include_bases"]    = prof.get("include_bases", True)
        self.cfg["auto_floor"]       = prof.get("auto_floor", False)
        self.cfg["auto_floor_pct"]   = prof.get("auto_floor_pct", 40)
        self.cfg["base_quality"]     = prof.get("base_quality", 25)
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

    def _raregear_states(self) -> dict:
        """Per-slot on/off, stored like the Fracture tab's (item_states)."""
        return self.cfg.get("item_states", {}).get("_raregear", {})

    def rare_slot_disabled(self) -> set:
        """Slots the user has switched off — passed to rare_gear_body(disabled=)."""
        st = self._raregear_states()
        return {name for name, s in st.items() if not s.get("enabled", True)}

    def rare_recipes(self):
        """Rare-gear WeightedSum recipes per slot, for the Magic & Rare tab.

        ``enabled`` (top level) is the master switch; each slot carries its own
        ``enabled`` too — a slot that's off is skipped when the pickit is built.
        """
        from exilebot_pickit.data.rare import rules as rare_rules
        off = self.rare_slot_disabled()
        slots = {}
        for slot, spec in rare_rules.RARE_GEAR.items():
            slots[slot] = {
                "bases": list(spec["bases"]),
                "threshold": spec["threshold"],
                "item_tier": spec["item_tier"],
                "enabled": slot not in off,
                "weights": [
                    {"stat": sid, "w": w,
                     "label": rare_rules.STAT_LABELS.get(sid, sid)}
                    for sid, w in spec["weights"].items()],
                "lines": rare_rules.rare_gear_example_lines(slot),
            }
        return {"enabled": bool(self.cfg.get("rare_gear_enabled", True)),
                "slots": slots}

    def enable_all_rules(self):
        """One click before a full run: every category, item, chance base,
        craft/exceptional base, fracture target, rare slot and flask rule ON.

        Both value floors drop to 0, Auto-floor is switched OFF, and the
        exceptional-base gates open to their loosest legal values (quality 21,
        item level 79), because that is what "everything" means: a 200 ex floor
        (or auto-floor recomputing one next generate, or a quality-30 gate)
        would silently re-filter almost everything this just enabled and make
        the button a lie. undo_all_on puts every one of those back.

        Before flipping, the previous switch state is snapshotted (in memory,
        this session only) so undo_all_on can put carefully-tuned switches
        back — one click must not be able to destroy an hour of curation."""
        _ABSENT = "__absent__"
        undo = {"categories": dict(self.cfg.get("category_enabled") or {}),
                "items": [],
                "flags": {k: self.cfg.get(k) for k in
                          ("rare_gear_enabled", "include_bases",
                           "magic_rare_flasks", "active_preset", "auto_floor",
                           "min_exalt_gear", "min_exalt_unique", "min_exalt",
                           "base_quality", "base_min_level")}}
        self.cfg["category_enabled"] = {}          # empty = every category on
        flipped = 0
        for cat, states in (self.cfg.get("item_states") or {}).items():
            if not isinstance(states, dict):
                continue
            for name, st in states.items():
                if isinstance(st, dict) and st.get("enabled") is not True:
                    undo["items"].append([cat, name, st.get("enabled", _ABSENT)])
                    st["enabled"] = True
                    flipped += 1
        self.cfg["rare_gear_enabled"] = True
        self.cfg["include_bases"] = True
        self.cfg["magic_rare_flasks"] = True
        # these would otherwise re-gate every switch we just turned on
        self.cfg["auto_floor"] = False
        self.cfg["min_exalt_gear"] = 0.0
        self.cfg["min_exalt_unique"] = 0.0
        self.cfg["min_exalt"] = 0.0          # legacy mirror of the gear floor
        # loosest ends of the valid exceptional-base ranges (21-30 / 79-82)
        self.cfg["base_quality"] = 21
        self.cfg["base_min_level"] = 79
        # hand-flipping every switch means no preset's promise still holds
        self.cfg["active_preset"] = ""
        save_config(self.cfg)
        self._all_on_undo = undo
        # "changed" drives the undo button: floors/auto-floor can change even
        # when no switch flipped, and that still needs a way back.
        f = undo["flags"]
        changed = bool(flipped or undo["categories"]
                       or f.get("auto_floor")
                       or float(f.get("min_exalt_gear") or 0)
                       or float(f.get("min_exalt_unique") or 0)
                       or f.get("rare_gear_enabled") is False
                       or f.get("include_bases") is False
                       or f.get("magic_rare_flasks") is False
                       or int(f.get("base_quality") or 21) != 21
                       or int(f.get("base_min_level") or 79) != 79)
        return {"ok": True, "flipped": flipped, "changed": changed}

    def undo_all_on(self):
        """Put every switch back exactly as it was before the last All ON.

        One-shot and session-only by design: it restores the snapshot taken by
        enable_all_rules and then discards it. Floors/numbers were never
        touched, so only switch state comes back."""
        _ABSENT = "__absent__"
        undo = getattr(self, "_all_on_undo", None)
        if not undo:
            return {"error": "nothing to undo"}
        self._all_on_undo = None
        self.cfg["category_enabled"] = dict(undo["categories"])
        restored = 0
        item_states = self.cfg.get("item_states") or {}
        for cat, name, prev in undo["items"]:
            st = (item_states.get(cat) or {}).get(name)
            if not isinstance(st, dict):
                continue
            if prev == _ABSENT:
                st.pop("enabled", None)
            else:
                st["enabled"] = prev
            restored += 1
        for k, v in undo["flags"].items():
            if v is None:
                self.cfg.pop(k, None)
            else:
                self.cfg[k] = v
        save_config(self.cfg)
        return {"ok": True, "restored": restored}

    def set_rare_slot(self, slot, enabled):
        """Turn one rare-gear slot on/off. Off = its rules leave the pickit."""
        from exilebot_pickit.data.rare import rules as rare_rules
        if slot not in rare_rules.RARE_GEAR:
            return {"error": "unknown slot"}
        states = self.cfg.setdefault("item_states", {}).setdefault("_raregear", {})
        states.setdefault(slot, {})["enabled"] = bool(enabled)
        save_config(self.cfg)
        return {"ok": True, "slot": slot, "enabled": bool(enabled)}

    def download_update(self):
        """Start downloading the newest release exe on a worker thread and return
        immediately; the page polls download_progress() to drive a progress bar.
        Deliberately NOT self-replacing (AV locks / half-swaps bricked installs
        in the past) — the user runs the fresh exe themselves."""
        with self._lock:
            if self._dl.get("active"):
                return {"error": "already downloading"}
            self._dl = {"active": True, "pct": 0, "done_mb": 0.0,
                        "total_mb": 0.0, "result": None}
        threading.Thread(target=self._download_update_worker, daemon=True).start()
        return {"ok": True, "started": True}

    def download_progress(self):
        """Live download state for the UI: percent, MB done/total, and — once
        finished — the final result dict (ok/path/version or error)."""
        with self._lock:
            return dict(self._dl)

    def _dl_finish(self, result: dict):
        with self._lock:
            self._dl["active"] = False
            self._dl["result"] = result
            if result.get("ok"):
                self._dl["pct"] = 100

    def _download_update_worker(self):
        try:
            import requests
            from exilebot_pickit.ui.updater import VERSION_URL
            r = requests.get(VERSION_URL, timeout=10,
                             headers={"User-Agent": f"poe2-pickit/{VERSION}",
                                      "Accept": "application/vnd.github+json"})
            if r.status_code != 200:
                self._dl_finish({"error": f"GitHub said {r.status_code}"})
                return
            data = r.json() or {}
            ver = str(data.get("tag_name") or "").lstrip("v")
            asset = next((a for a in data.get("assets", [])
                          if a.get("name", "").endswith(".exe")), None)
            if not asset:
                self._dl_finish({"error": "no .exe in the latest release"})
                return
            # Download beside the running .exe (same drive → the helper can
            # swap it in place). In dev (not frozen) fall back to Downloads.
            import sys as _sys
            if getattr(_sys, "frozen", False):
                dl = os.path.dirname(_sys.executable)
            else:
                dl = os.path.join(os.path.expanduser("~"), "Downloads")
            os.makedirs(dl, exist_ok=True)
            dest = os.path.join(dl, f"ExileBot2PickitGenerator-v{ver}.exe")
            with requests.get(asset["browser_download_url"], stream=True, timeout=120) as resp:
                resp.raise_for_status()
                total = int(resp.headers.get("Content-Length") or 0)
                done = 0
                with open(dest + ".part", "wb") as f:
                    for chunk in resp.iter_content(1 << 18):
                        if not chunk:
                            continue
                        f.write(chunk)
                        done += len(chunk)
                        with self._lock:
                            self._dl["done_mb"] = round(done / 1048576, 1)
                            self._dl["total_mb"] = round(total / 1048576, 1) if total else 0.0
                            self._dl["pct"] = int(done * 100 / total) if total else 0
            # ── integrity gate ── a corrupt/truncated exe must NEVER be installed
            # (that bricks the app with a "failed to load python3xx.dll" error), so
            # verify size + SHA256 against the release's SHA256SUMS.txt before the
            # file is ever eligible for the swap. On any mismatch we raise, the
            # .part is deleted, and the old version is left completely untouched.
            if total and done != total:
                raise OSError(f"incomplete download: got {done} of {total} bytes")
            sums = next((a for a in data.get("assets", [])
                         if a.get("name", "").lower() == "sha256sums.txt"), None)
            want = None
            if sums:
                sr = requests.get(sums["browser_download_url"], timeout=30)
                if sr.status_code == 200:
                    for line in sr.text.splitlines():
                        parts = line.split()
                        if len(parts) >= 2 and parts[-1].lstrip("*") == asset["name"]:
                            want = parts[0].lower()
                            break
            if want:
                import hashlib
                h = hashlib.sha256()
                with open(dest + ".part", "rb") as vf:
                    for blk in iter(lambda: vf.read(1 << 20), b""):
                        h.update(blk)
                if h.hexdigest().lower() != want:
                    raise OSError("checksum mismatch — the download was corrupted")
            os.replace(dest + ".part", dest)
            import sys as _sys
            frozen = bool(getattr(_sys, "frozen", False))
            if not frozen:
                try:
                    import subprocess
                    subprocess.Popen(["explorer", "/select,", dest])
                except Exception:
                    pass
            # Keep this release's notes: after the swap the app relaunches and shows
            # them as "what's new", and doing it now means that works with no network.
            try:
                self.cfg["pending_version"] = ver
                self.cfg["pending_notes"] = str(data.get("body") or "")[:8000]
                save_config(self.cfg)
            except Exception:
                pass
            self._dl_finish({"ok": True, "path": dest, "version": ver, "frozen": frozen})
        except Exception as e:
            # download failed — the old version is completely untouched
            try:
                if os.path.exists(dest + ".part"):
                    os.remove(dest + ".part")
            except Exception:
                pass
            self._dl_finish({"error": str(e)[:200]})

    @staticmethod
    def _clean_env():
        """The environment minus PyInstaller's one-file bookkeeping.

        A frozen exe unpacks to %TEMP%\\_MEIxxxxxx and exports that path (_MEIPASS2 on
        older PyInstaller, _PYI_* on 6.x). Any process we spawn inherits it. That is
        fine for explorer.exe — but the update helper relaunches *our own exe*, and a
        one-file exe that sees those vars assumes it is a child of an already-unpacked
        parent and skips unpacking. The parent is by then dead and has deleted the
        folder, so the new copy crashes on startup:
            FileNotFoundError: ...\\_MEI599002\\base_library.zip
        Strip them and the new exe unpacks itself properly.
        """
        return {k: v for k, v in os.environ.items()
                if not (k.startswith("_MEIPASS") or k.startswith("_PYI"))}

    def install_update(self):
        """Swap the freshly-downloaded exe in for the running one and relaunch.

        A running .exe is locked by Windows, so this writes a tiny helper that
        runs AFTER we exit: it backs up the old exe, moves the new one into its
        place, launches it, and only then deletes the backup. If the swap fails
        the backup is restored — the user always keeps a working version."""
        import sys as _sys
        res = self._dl.get("result") or {}
        new = res.get("path")
        if not (res.get("ok") and new and os.path.isfile(new)):
            return {"error": "no downloaded update to install"}
        if not getattr(_sys, "frozen", False):
            return {"error": "self-install only works in the built .exe — "
                             "the download is in your Downloads folder"}
        cur = _sys.executable
        pid = os.getpid()
        import tempfile
        bat = os.path.join(tempfile.gettempdir(), "exilebot_pickit_update.bat")
        script = (
            "@echo off\r\n"
            # Plain setlocal, NOT enabledelayedexpansion: with delayed expansion
            # active, a '!' anywhere in the install path is eaten at parse time —
            # TGT/SRC then point at nonexistent files, every move fails, :restore
            # restores nothing and the app never relaunches. The counters below
            # use goto-loops (each line re-parsed per jump), so plain %n% works.
            "setlocal\r\n"
            # A one-file exe unpacks itself to %TEMP%\\_MEIxxxxxx and advertises that
            # path in _MEIPASS2. Anything we spawn inherits it — so the new exe would
            # think it is a child of the old one, SKIP unpacking itself, and read from
            # a folder the dying old process just deleted:
            #   FileNotFoundError: ...\\_MEI599002\\base_library.zip
            # Clear them here (and in the env we hand cmd) so the new exe unpacks fresh.
            'set "_MEIPASS2="\r\n'
            'set "_PYI_ARCHIVE_FILE="\r\n'
            'set "_PYI_APPLICATION_HOME_DIR="\r\n'
            'set "_PYI_PARENT_PROCESS_LEVEL="\r\n'
            f'set "TGT={cur}"\r\n'
            f'set "SRC={new}"\r\n'
            f'set "BAK={cur}.bak"\r\n'
            # 1) wait for the app process to go
            "set /a n=0\r\n"
            ":waitpid\r\n"
            f'tasklist /FI "PID eq {pid}" 2>NUL | find "{pid}" >NUL\r\n'
            "if errorlevel 1 goto ready\r\n"
            "set /a n+=1\r\n"
            "if %n% GEQ 90 goto giveup\r\n"
            "ping -n 2 127.0.0.1 >NUL\r\n"
            "goto waitpid\r\n"
            ":ready\r\n"
            # 2) A one-file exe is TWO processes: the bootloader that unpacked it, and
            #    the app. os.getpid() only knows the app's — the bootloader outlives it,
            #    still holding the .exe open while it deletes %TEMP%\\_MEIxxxxxx. Overwriting
            #    the exe inside that window is what produced:
            #      pyi_rth_inspect: No module named 'collections.abc'
            #      Failed to remove temporary directory: ..._MEI657242
            #    Windows lets you *rename* a running exe but never *overwrite* one, so the
            #    move is itself the only lock test worth trusting: retry it until it takes.
            'copy /y "%TGT%" "%BAK%" >NUL\r\n'
            "set /a n=0\r\n"
            ":swap\r\n"
            'move /y "%SRC%" "%TGT%" >NUL 2>NUL\r\n'
            "if not errorlevel 1 goto done\r\n"
            "set /a n+=1\r\n"
            "if %n% GEQ 60 goto restore\r\n"
            "ping -n 2 127.0.0.1 >NUL\r\n"
            "goto swap\r\n"
            ":restore\r\n"
            'copy /y "%BAK%" "%TGT%" >NUL\r\n'
            'start "" "%TGT%"\r\n'
            "del \"%~f0\" & exit\r\n"
            ":done\r\n"
            # Keep the previous exe as "<name>.bak" (a working fallback if the new
            # build misbehaves) instead of deleting it — only ever one copy, since
            # the next update overwrites it. The user can rename it back by hand.
            'start "" "%TGT%"\r\n'
            'del "%~f0"\r\n'
            "exit\r\n"
            # Never leave the user without an app: if the old one somehow never let go,
            # start what is there and keep the downloaded exe for a manual swap.
            ":giveup\r\n"
            'start "" "%TGT%"\r\n'
            'del "%~f0"\r\n'
        )
        try:
            with open(bat, "w", encoding="ascii", errors="replace") as f:
                f.write(script)
            import subprocess
            subprocess.Popen(["cmd", "/c", bat],
                             creationflags=0x08000000,   # CREATE_NO_WINDOW
                             env=self._clean_env())
        except Exception as e:
            return {"error": f"couldn't start the installer: {e}"}

        # Close the app so the helper can replace the exe. This has to be a REAL exit:
        # a process that lingers keeps the .exe locked, the swap never lands, and the
        # helper gives up and relaunches the OLD exe. The hard exit covers a webview
        # teardown that hangs. (Minimize-to-tray used to cancel this close outright —
        # that is exactly why the setting is gone.)
        def _close():
            time.sleep(0.5)
            try:
                import webview
                webview.windows[0].destroy()
            except Exception:
                pass
            time.sleep(1.5)
            os._exit(0)
        threading.Thread(target=_close, daemon=True).start()
        return {"ok": True}

    def whats_new(self, force=False):
        """The release notes for the version now running — shown once, on the first
        launch after an update. ``force`` re-opens them on demand (the version label).

        The app already told you what was in an update *before* you installed it; it
        never told you what changed once you were actually on it. That mattered after
        the update crashes: people got a new exe and no idea what had happened.

        Notes come from the copy stashed at download time (so this works offline), and
        fall back to GitHub for anyone who downloaded the exe by hand.
        """
        try:
            # force = the user clicked the version number to re-read the notes: skip
            # both the already-seen check and the fresh-install guard, and leave the
            # seen-state alone — a deliberate look is not an announcement.
            if not force:
                seen = str(self.cfg.get("last_seen_version") or "")
                if seen == VERSION:
                    return {"show": False}
                # A brand-new install has nothing to catch up on — don't greet a
                # first-time user with a changelog. Only someone with existing
                # settings has *upgraded*.
                upgraded = bool(self.cfg.get("history") or self.cfg.get("league")
                                or self.cfg.get("bot_folder"))
                if not upgraded:
                    self.mark_whats_new_seen()
                    return {"show": False}

            notes = ""
            if str(self.cfg.get("pending_version") or "") == VERSION:
                notes = str(self.cfg.get("pending_notes") or "")
            if not notes:
                # The highlights ship inside the exe (version.py) — the dialog
                # must work offline and while GitHub is unreachable.
                from exilebot_pickit.version import HIGHLIGHTS
                notes = HIGHLIGHTS
            if not notes:
                try:
                    import requests
                    from exilebot_pickit.ui.updater import VERSION_URL
                    base = VERSION_URL.rsplit("/", 1)[0]
                    r = requests.get(f"{base}/tags/v{VERSION}", timeout=8,
                                     headers={"User-Agent": f"poe2-pickit/{VERSION}",
                                              "Accept": "application/vnd.github+json"})
                    if r.status_code == 200:
                        notes = str((r.json() or {}).get("body") or "")[:8000]
                except Exception:
                    notes = ""
            return {"show": True, "version": VERSION, "notes": notes,
                    "url": f"https://github.com/c4Luffy/poe2-pickit-generator/releases/tag/v{VERSION}"}
        except Exception as e:
            return {"show": False, "error": str(e)}

    def mark_whats_new_seen(self):
        """Don't show these notes again."""
        try:
            self.cfg["last_seen_version"] = VERSION
            self.cfg["pending_version"] = ""
            self.cfg["pending_notes"] = ""
            save_config(self.cfg)
        except Exception:
            pass
        return {"ok": True}

    def check_update(self):
        try:
            from exilebot_pickit.ui.updater import AutoUpdateMixin, VERSION_URL, RELEASES_URL
            import requests
            r = requests.get(VERSION_URL, timeout=8,
                             headers={"User-Agent": f"poe2-pickit/{VERSION}",
                                      "Accept": "application/vnd.github+json"})
            if r.status_code != 200:
                return {"update": False}
            data = r.json() or {}
            remote = str(data.get("tag_name") or "").lstrip("v").strip()
            if AutoUpdateMixin._should_offer_update(remote, VERSION):
                notes = str(data.get("body") or "").strip()
                return {"update": True, "version": remote, "url": RELEASES_URL,
                        "notes": notes[:4000], "current": VERSION}
            return {"update": False, "current": VERSION}
        except Exception:
            return {"update": False, "current": VERSION}

    # ── Game-data health check ────────────────────────────────────────────────
    # PoE2 renames stats and removes bases every patch. When it does, our rules
    # still look correct but match nothing and the bot silently walks past loot —
    # no error anywhere. This surfaces that in the app instead of leaving it to a
    # dev script. Runs on a worker thread (the sources are ~9 MB) and is entirely
    # best-effort: a failure reports itself and never breaks a launch.

    def start_game_data_check(self, force=False):
        """Kick the health check off in the background. Poll game_data_result()."""
        if getattr(self, "_gd_running", False):
            return {"running": True}
        self._gd_running = True
        self._gd_result = None

        def _work():
            try:
                from exilebot_pickit.data.game_data_check import run_check
                self._gd_result = run_check(force=bool(force))
            except Exception:
                log_exc("game_data_check")
                self._gd_result = {
                    "ok": True, "critical": 0, "advisory": 0, "findings": [],
                    "sources": {}, "checked_at": "",
                    "error": "The game-data check couldn't run."}
            finally:
                self._gd_running = False

        threading.Thread(target=_work, daemon=True).start()
        return {"running": True}

    def game_data_result(self):
        """{running:true} while it works, then the finished check result."""
        if getattr(self, "_gd_running", False):
            return {"running": True}
        r = getattr(self, "_gd_result", None)
        if r is None:
            return {"running": False, "idle": True}
        return {"running": False, **r}

    def open_url(self, url):
        # Only the app's own outbound links (allowlist): GitHub, poe.ninja,
        # the community Discord, and the Exiled Bot website.
        u = str(url)
        _allowed = ("https://github.com/", "https://poe.ninja/",
                    "https://discord.gg/", "https://discord.com/",
                    "https://exiled-bot.net/", "https://www.exiled-bot.net/")
        if not u.startswith(_allowed):
            return {"error": "blocked"}
        import webbrowser
        webbrowser.open(u)
        return {"ok": True}

    def output_path(self):
        """Full path of the generated .ipd (the file the bot reads)."""
        base = (self.cfg.get("output_base") or "poe2_pickit").strip() or "poe2_pickit"
        return {"path": os.path.join(OUTPUT_DIR, base + ".ipd"), "dir": OUTPUT_DIR}

    def open_output_folder(self):
        """Open the pickit output folder in the OS file browser, selecting the
        .ipd if it exists (Explorer /select). Best-effort, never fatal."""
        import sys
        base = (self.cfg.get("output_base") or "poe2_pickit").strip() or "poe2_pickit"
        ipd = os.path.join(OUTPUT_DIR, base + ".ipd")
        try:
            if sys.platform.startswith("win") and os.path.exists(ipd):
                import subprocess
                subprocess.Popen(["explorer", "/select,", os.path.normpath(ipd)])
            elif sys.platform.startswith("win"):
                os.startfile(OUTPUT_DIR)          # noqa: S606 (folder, no args)
            else:
                import webbrowser
                webbrowser.open("file://" + OUTPUT_DIR)
            return {"ok": True}
        except Exception:
            return {"error": "could not open folder", "dir": OUTPUT_DIR}

    def export_settings(self):
        """Save the whole setup (floors, toggles, profiles, exclusions…) to a
        JSON file the user picks — for backup or moving to another PC. Caches
        and window geometry are excluded."""
        import json as _json
        import webview
        w = webview.windows[0]
        default = f"pickit-settings-{time.strftime('%Y%m%d')}.json"
        path = w.create_file_dialog(webview.SAVE_DIALOG, save_filename=default)
        if not path:
            return {"cancelled": True}
        if isinstance(path, (list, tuple)):
            path = path[0]
        data = {k: v for k, v in self.cfg.items()
                if k not in ("last_gen_prices", "window_geometry_web")}
        try:
            with open(path, "w", encoding="utf-8") as f:
                _json.dump(data, f, indent=2)
            return {"ok": True, "path": str(path)}
        except OSError as e:
            return {"error": str(e)}

    def import_settings(self):
        """Load a settings JSON exported above. Only keys that exist in
        DEFAULT_CONFIG are applied (typo/garbage keys are ignored), and the
        result goes through the same type-coercion guard as startup."""
        import json as _json
        import webview
        from exilebot_pickit.ui.config import DEFAULT_CONFIG, _coerce_types
        w = webview.windows[0]
        res = w.create_file_dialog(webview.OPEN_DIALOG,
                                   file_types=("Settings backup (*.json)",))
        if not res:
            return {"cancelled": True}
        try:
            with open(res[0], encoding="utf-8") as f:
                data = _json.load(f)
        except (OSError, ValueError) as e:
            return {"error": f"couldn't read that file: {e}"}
        if not isinstance(data, dict):
            return {"error": "that file isn't a settings backup"}
        applied = 0
        for k, v in data.items():
            if k in DEFAULT_CONFIG and k != "window_geometry_web":
                self.cfg[k] = v
                applied += 1
        _coerce_types(self.cfg)
        # _coerce_types only checks TYPES; a backup can carry a str theme the
        # engine doesn't know — normalize so cfg and the dropdown agree.
        self.cfg["filter_theme"] = _theme_or_default(self.cfg.get("filter_theme"))
        save_config(self.cfg)
        return {"ok": True, "applied": applied, "info": self.app_info()}

    # ── From my pickit: any .ipd → matching in-game loot filter ──────────────

    def import_pickit_choose(self):
        """File picker for the From-my-pickit tab. Starts in the bot's pickit
        folder when one is configured — the user's .ipd usually lives there.
        The chosen file is only ever read, never modified."""
        import webview
        w = webview.windows[0]
        kw = {"file_types": ("Exiled Bot pickit (*.ipd)", "All files (*.*)")}
        bot = (self.cfg.get("bot_folder") or "").strip()
        if bot and os.path.isdir(bot):
            kw["directory"] = bot
        res = w.create_file_dialog(webview.OPEN_DIALOG, **kw)
        if not res:
            return {"cancelled": True}
        return {"path": str(res[0] if isinstance(res, (list, tuple)) else res)}

    def import_pickit_bot(self):
        """The pickit the bot is ACTUALLY running, resolved from its own config.

        Create-your-filter's most common real input is "whatever my bot uses" —
        which is bot_folder/<active_profile>.ipd, the exact file bot_connection
        verifies. Resolving it here means one click instead of a file-picker
        hunt, and it can never pick the wrong profile. Read-only, like every
        import path."""
        folder = (self.cfg.get("bot_folder") or "").strip()
        if not folder or not os.path.isdir(folder):
            return {"error": "No bot folder is set — connect the bot in Settings "
                             "first, then this button knows where its pickit lives."}
        ini = self._bot_ini_path()
        profile = ""
        try:
            with open(ini, encoding="utf-8", errors="replace") as f:
                m = re.search(r"(?mi)^\s*active_profile\s*=\s*(.+?)\s*$", f.read())
            profile = m.group(1).strip() if m else ""
        except OSError:
            pass
        if not profile:
            return {"error": "Couldn't read active_profile from the bot's "
                             "pickit.ini — pick the file by hand instead."}
        path = os.path.join(folder, profile + ".ipd")
        if not os.path.isfile(path):
            return {"error": f"The bot's config points at \"{profile}.ipd\", but that "
                             "file isn't in its Pickit folder."}
        return {"path": path, "profile": profile}

    def import_pickit_convert(self, path, hide_rest=False):
        """Read a pickit file and convert it to loot-filter lines + a report."""
        from exilebot_pickit.generators.pickit_import import convert_pickit_text
        path = str(path or "").strip()
        if not path or not os.path.isfile(path):
            return {"error": "That file doesn't exist any more."}
        try:
            if os.path.getsize(path) > 5 * 1024 * 1024:
                return {"error": "That file is over 5 MB — not a pickit."}
            with open(path, "rb") as f:
                raw = f.read()
        except OSError as e:
            return {"error": f"Couldn't read the file: {e}"}
        # Hand-made pickits are often ANSI (Notepad legacy save): a strict
        # UTF-8 try first, then Windows-1252 — errors="replace" alone turned
        # accented names into '�', which then matched nothing in game.
        try:
            text = raw.decode("utf-8-sig")
        except UnicodeDecodeError:
            try:
                text = raw.decode("cp1252")
            except UnicodeDecodeError:
                text = raw.decode("utf-8-sig", errors="replace")
        res = convert_pickit_text(text, hide_rest=bool(hide_rest),
                                  source_name=os.path.basename(path),
                                  theme=_theme_or_default(self.cfg.get("filter_theme")))
        # One writer at a time: convert can be triggered from the picker, the
        # hide switch and drag&drop — without the lock a slow convert could
        # leave file A's filter stored under file B's name for Save to write.
        with self._lock:
            self._import_filter_text = ("\n".join(res["filter_lines"]) + "\n"
                                        if res["ok"] else "")
            self._import_filter_name = (
                os.path.splitext(os.path.basename(path))[0] + ".filter")
            self._import_src_path = path
        out = {"ok": res["ok"], "report": res["report"],
               "name": os.path.basename(path)}
        if res["ok"]:
            out["preview"] = "\n".join(res["filter_lines"][:120])
            out["lines"] = len(res["filter_lines"])
        return out

    def import_pickit_save(self):
        """Save the converted filter; the dialog starts in the PoE2 client
        filter folder so the game sees it right after."""
        import webview
        with self._lock:
            text = getattr(self, "_import_filter_text", "")
            fname = getattr(self, "_import_filter_name", "my_pickit.filter")
            src = getattr(self, "_import_src_path", "")
        if not text:
            return {"error": "Convert a pickit first."}
        w = webview.windows[0]
        fdir = (self.cfg.get("poe2_filter_dir") or "").strip() or _default_dir()
        kw = {"save_filename": fname}
        if fdir and os.path.isdir(fdir):
            kw["directory"] = fdir
        path = w.create_file_dialog(webview.SAVE_DIALOG, **kw)
        if not path:
            return {"cancelled": True}
        if isinstance(path, (list, tuple)):
            path = path[0]
        path = str(path)
        # "The pickit is only read, never changed" — a save target that IS the
        # source pickit (or any .ipd) would replace a pickit with filter text.
        if src and os.path.normcase(os.path.abspath(path)) == \
                os.path.normcase(os.path.abspath(src)):
            return {"error": "That's your pickit file — pick a different name."}
        if path.lower().endswith(".ipd"):
            return {"error": "That would overwrite a pickit — save as .filter."}
        try:
            gen.write_text_atomic(path, text)
        except OSError as e:
            return {"error": f"Couldn't save: {e}"}
        # Remember the conversion so the tab can warn when the source pickit
        # changes after this save (the filter would silently drift stale).
        # The theme rides along: switching themes later makes the saved file
        # stale too — it still wears the old look until re-saved.
        self.cfg["filter_from_pickit"] = {
            "src": src, "out": path, "at": time.time(),
            "theme": _theme_or_default(self.cfg.get("filter_theme"))}
        save_config(self.cfg)
        self._log(f"✓ Filter created from pickit: {os.path.basename(str(path))}")
        return {"ok": True, "path": str(path)}

    def import_pickit_open_saved(self):
        """Open the folder holding the last filter saved from this tab."""
        out = (self.cfg.get("filter_from_pickit") or {}).get("out") or ""
        folder = os.path.dirname(out) if out else ""
        if not folder or not os.path.isdir(folder):
            return {"error": "Nothing saved yet."}
        try:
            os.startfile(folder)          # noqa: S606 (folder, no args)
            return {"ok": True}
        except OSError as e:
            return {"error": str(e)}

    def import_pickit_status(self):
        """Stale check for the Create-your-filter tab: has the source pickit
        changed — or the label theme — since the filter was saved from it?"""
        info = self.cfg.get("filter_from_pickit") or {}
        src, at = info.get("src") or "", info.get("at") or 0
        if not src or not at or not os.path.isfile(src):
            return {"stale": False}
        try:
            stale = os.path.getmtime(src) > float(at) + 1
        except (OSError, ValueError):
            return {"stale": False}
        # Older saves carry no theme — don't declare every pre-theme save stale.
        saved_theme = info.get("theme")
        theme_stale = bool(saved_theme and saved_theme !=
                           _theme_or_default(self.cfg.get("filter_theme")))
        return {"stale": bool(stale or theme_stale),
                "theme_stale": theme_stale and not stale,
                "src": os.path.basename(src),
                "out": os.path.basename(info.get("out") or ""), "path": src}

    def list_backups(self):
        """Rotated .ipd backups (newest first) for the Settings restore picker."""
        base = (self.cfg.get("output_base") or "poe2_pickit").strip() or "poe2_pickit"
        bdir = os.path.join(OUTPUT_DIR, "backups")
        out = []
        try:
            for f in os.listdir(bdir):
                if not (f.startswith(base + "-") and f.endswith(".ipd")):
                    continue
                st = os.stat(os.path.join(bdir, f))
                out.append({"name": f, "kb": round(st.st_size / 1024),
                            "ts": time.strftime("%Y-%m-%d %H:%M",
                                                time.localtime(st.st_mtime))})
        except OSError:
            pass
        out.sort(key=lambda b: b["name"], reverse=True)
        return out

    def backup_diff(self, name):
        """Rule-level diff: the current pickit vs one rotated backup.

        Compares ACTIVE rules with their ExValue comment stripped — prices move
        every run, and a wall of price-only churn would bury the answer people
        actually want from a diff: which rules appeared, which disappeared.
        Read-only on both files."""
        base = (self.cfg.get("output_base") or "poe2_pickit").strip() or "poe2_pickit"
        bdir = os.path.join(OUTPUT_DIR, "backups")
        name = os.path.basename(str(name or ""))
        bpath = os.path.join(bdir, name)
        cpath = os.path.join(OUTPUT_DIR, base + ".ipd")
        if not (name.startswith(base + "-") and name.endswith(".ipd")
                and os.path.isfile(bpath)):
            return {"error": "That backup doesn't exist any more."}
        if not os.path.isfile(cpath):
            return {"error": "No current pickit to compare — generate first."}

        def _active_rules(path):
            rules = set()
            try:
                with open(path, encoding="utf-8-sig", errors="replace") as f:
                    for ln in f:
                        ln = ln.strip()
                        if not ln or ln.startswith("/") or "[StashItem]" not in ln:
                            continue
                        rules.add(re.sub(r"\s*//\s*ExValue.*$", "", ln).strip())
            except OSError:
                pass
            return rules

        cur, old = _active_rules(cpath), _active_rules(bpath)
        added = sorted(cur - old)
        removed = sorted(old - cur)
        return {"backup": name, "added": added[:300], "removed": removed[:300],
                "added_total": len(added), "removed_total": len(removed),
                "cur_total": len(cur), "old_total": len(old)}

    def restore_backup(self, name):
        """Make a rotated backup the current pickit again. The pickit being
        replaced is itself backed up first, so a restore never loses anything."""
        base = (self.cfg.get("output_base") or "poe2_pickit").strip() or "poe2_pickit"
        bdir = os.path.join(OUTPUT_DIR, "backups")
        name = os.path.basename(str(name))            # no path traversal
        src = os.path.join(bdir, name)
        if not (name.startswith(base + "-") and name.endswith(".ipd")
                and os.path.isfile(src)):
            return {"error": "backup not found"}
        ipd = os.path.join(OUTPUT_DIR, base + ".ipd")
        try:
            if os.path.isfile(ipd):                    # save what we're replacing
                os.makedirs(bdir, exist_ok=True)
                stamp = time.strftime("%Y%m%d-%H%M%S")
                shutil.copy2(ipd, os.path.join(bdir, f"{base}-{stamp}.ipd"))
            shutil.copy2(src, ipd)
            with open(ipd, encoding="utf-8") as f:
                content = f.read()
            self._last_lines = content.splitlines()   # Preview shows the restored file
            copied = False
            bot = (self.cfg.get("bot_folder") or "").strip()
            if self.cfg.get("auto_copy") and bot and os.path.isdir(bot):
                shutil.copy2(ipd, os.path.join(bot, os.path.basename(ipd)))
                copied = True
            active = sum(1 for l in self._last_lines
                         if l and not l.startswith("//") and "[StashItem]" in l)
            return {"ok": True, "name": name, "active": active, "copied": copied}
        except OSError as e:
            return {"error": str(e)}

    def open_bot_folder(self):
        """Open the configured Exiled Bot folder (where the .ipd is copied) in
        the OS file browser. Returns a hint if no bot folder is set."""
        import sys
        folder = (self.cfg.get("bot_folder") or "").strip()
        if not folder:
            return {"error": "no bot folder set"}
        if not os.path.isdir(folder):
            return {"error": "bot folder not found", "dir": folder}
        try:
            if sys.platform.startswith("win"):
                os.startfile(folder)          # noqa: S606 (folder, no args)
            else:
                import webbrowser
                webbrowser.open("file://" + folder)
            return {"ok": True}
        except Exception:
            return {"error": "could not open folder", "dir": folder}

    def debug_info(self):
        """Debug payload — including an ERROR DIGEST, not just a log dump.

        The Debug tab used to show the log only as raw text you had to read. It
        hid a real problem for a whole day: 318 load_config failures and 107
        save_config failures were sitting in there, every one of them silently
        dropping the app onto default settings, and nobody noticed because
        nothing counted them. Errors are now summarised and surfaced.
        """
        import collections
        import re
        from exilebot_pickit.ui.config import LOG_PATH, CONFIG_PATH
        ci = gen.cache_info()

        tail, errors, by_type, recent_total = [], [], [], 0
        try:
            with open(LOG_PATH, encoding="utf-8", errors="replace") as f:
                lines = f.read().splitlines()
            tail = lines[-80:]
            # The log is append-only (rotated by size, not age), so an old,
            # long-fixed incident stays in it for weeks. Counting it forever
            # made a healthy app open Debug on a scary "53 errors" (the July
            # save-race scar). The headline number is therefore the LAST 24
            # HOURS — "is the app healthy NOW" — and the all-time total rides
            # along as a footnote. (Live errors additionally bump the nav
            # badge the moment they happen, so nothing hides.)
            day_ago = time.strftime(
                "%Y-%m-%d %H:%M:%S", time.localtime(time.time() - 86400))
            counts, recent_counts, last_seen = (
                collections.Counter(), collections.Counter(), {})
            for ln in lines:
                m = re.search(r"(ERROR|CRITICAL)\s+EXC\s+(\S+)", ln)
                if m:
                    kind = m.group(2)
                elif re.search(r"(ERROR|CRITICAL)\s+JSERR", ln):
                    # JS/UI errors were NOT counted here — the digest matched only EXC,
                    # so a wave of front-end crashes (the kind this app actually hits)
                    # showed "errors: clean". Group them under one kind.
                    kind = "JS error (UI)"
                else:
                    continue
                counts[kind] += 1
                last_seen[kind] = ln[:19]           # timestamp prefix
                if ln[:19] >= day_ago:             # ISO prefix sorts by time
                    recent_counts[kind] += 1
            by_type = [{"kind": k, "count": n, "last": last_seen.get(k, ""),
                        "recent": recent_counts.get(k, 0)}
                       for k, n in counts.most_common()]
            recent_total = sum(recent_counts.values())
            errors = [ln for ln in lines if " ERROR " in ln or " CRITICAL " in ln][-25:]
        except OSError:
            pass

        return {"cache": ci, "log": tail, "config_path": CONFIG_PATH,
                "cache_dir": PRICE_CACHE_DIR,
                "unique_cats": len(gen.UNIQUE_CATEGORIES),
                "all_cats": len(gen.ALL_CATEGORIES),
                "log_path": LOG_PATH,
                "errors": {"total": sum(e["count"] for e in by_type),
                           "recent_total": recent_total,
                           "by_type": by_type, "recent": errors}}

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

    # (prune_cache bridge removed — pruning happens automatically at every
    #  launch, see __init__; the Debug button for it only confused people.)

    def reset_defaults(self):
        """Reset to defaults: turn every item/category toggle back ON and clear
        all tuned settings (floors, quality gates, folders, etc.). Deliberately
        does NOT keep item_states/category_enabled — those hold the user's
        on/off toggles, and a 'reset to defaults' that preserved them left
        everything the user had switched off still off (reported as a bug).
        Genuine user *data* is kept: run history, saved profiles, the last
        price snapshot, window size and current league."""
        from exilebot_pickit.ui.config import DEFAULT_CONFIG
        keep = {k: self.cfg.get(k) for k in
                ("history", "profiles", "last_gen_prices",
                 "window_geometry_web", "league")}
        import copy
        self.cfg.clear()
        # deepcopy: plain update() shares DEFAULT_CONFIG's nested dicts, and
        # set_item() then mutates the DEFAULTS in place — the next reset
        # "restores" those stale toggles (the reported reset-didn't-reset bug).
        self.cfg.update(copy.deepcopy(DEFAULT_CONFIG))
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

    def chance_bases(self, league=None):
        st = self.cfg.get("item_states", {}).get("_chance", {})
        from exilebot_pickit.data.icons import STATIC_ICONS, UNIQUE_ICONS

        # Live price of the target unique ("what you're chancing FOR") — every
        # target is an accessory (belt/ring/amulet), so one cached fetch prices
        # them all. Best-effort: no league or a failed fetch just omits prices,
        # never blocks the tab. The BEST price among multi-target entries wins
        # (that's the jackpot you're hoping for).
        acc, div_rate = None, 0.0
        if league:
            # Derive the ninja type/flags from the category table so a rename
            # there can't silently break pricing (it did: "UniqueAccessory" vs
            # "UniqueAccessories" returned nothing).
            spec = next((c for c in gen.ALL_CATEGORIES
                         if c[0] == "unique_accessories"), None)
            try:
                if spec:
                    acc = gen.fetch_category(league, spec[0], spec[1], spec[3])
                cur = gen.fetch_category(league, "currency", "Currency", False)
                div_rate = asm.compute_divine_rate(cur)[0] if isinstance(cur, dict) else 0.0
            except Exception:
                acc = None

        # name -> live poe.ninja art, used when we don't ship a local icon for
        # a target (only some uniques have bundled art). Local wins: it works
        # offline; the remote URL is the fallback so every target still shows.
        live_icon = {}
        if isinstance(acc, dict):
            for ln in acc.get("lines", []):
                if ln.get("name") and ln.get("icon"):
                    live_icon.setdefault(ln["name"], ln["icon"])

        def _one(name):
            """Price + art for a single target unique."""
            ex = self._payload_price(acc, {name}, True) if isinstance(acc, dict) else None
            return {"name": name,
                    "icon": UNIQUE_ICONS.get(name) or live_icon.get(name, ""),
                    "ex": round(ex, 1) if ex is not None else None,
                    "div": round(ex / div_rate, 1)
                    if ex is not None and div_rate > 1 else None}

        out = []
        for cat, base, tgt in gen.CHANCE_BASES:
            # a base can chance into several uniques ("A / B / C") — show them all
            targets = [_one(n.strip()) for n in tgt.split(" / ") if n.strip()]
            priced = [t["ex"] for t in targets if t["ex"] is not None]
            best = max(priced) if priced else None
            out.append({"cat": cat, "base": base, "target": tgt,
                        "icon": STATIC_ICONS.get(base, ""),
                        # first target's art kept for older callers/tests
                        "target_icon": targets[0]["icon"] if targets else "",
                        "targets": targets,
                        "target_ex": best,
                        "target_div": round(best / div_rate, 1)
                        if best is not None and div_rate > 1 else None,
                        "enabled": st.get(base, {}).get("enabled", True)})
        return out

    def exceptional_bases(self):
        """Exceptional bases grouped by slot, with per-base toggle state,
        icon and stats — powers the Exceptional tab grid."""
        from exilebot_pickit.data.icons import STATIC_ICONS, BASE_STATS
        st = self.cfg.get("item_states", {}).get("_excbase", {})

        def _profile(stats: str):
            """Attribute label + primary-stat total from the stats string
            ('AR 496 · EV 0 · ES 76' → ('Str/Int', 572))."""
            ar = ev = es = 0
            for part in stats.split("·"):
                p = part.strip()
                if p.startswith("AR "): ar = int(p[3:] or 0)
                elif p.startswith("EV "): ev = int(p[3:] or 0)
                elif p.startswith("ES "): es = int(p[3:] or 0)
            tags = []
            if ar: tags.append("Str")
            if ev: tags.append("Dex")
            if es: tags.append("Int")
            return ("/".join(tags) or "—"), (ar + ev + es)

        # fixed attribute order so groups always read Str → Dex → Int → hybrids
        ATTR_ORDER = {"Str": 0, "Dex": 1, "Int": 2, "Str/Dex": 3,
                      "Str/Int": 4, "Dex/Int": 5, "Str/Dex/Int": 6, "—": 9}
        out = []
        # list(): snapshot in one C-level op — the background game-data refresh
        # can swap this dict's contents mid-iteration on another thread.
        for cat, entries in list(gen._BASE_TYPES_BY_CATEGORY.items()):
            bases = []
            for n, _s in entries:
                bi = BASE_STATS.get(n, {})
                stats = bi.get("stats", "")
                attr, total = _profile(stats)
                bases.append({"name": n,
                              "enabled": st.get(n, {}).get("enabled", True),
                              "icon": STATIC_ICONS.get(n, ""),
                              "lvl": bi.get("lvl", 0),
                              "stats": stats, "attr": attr, "total": total})
            # group by attribute, best (highest stat) first inside each group
            bases.sort(key=lambda b: (ATTR_ORDER.get(b["attr"], 8), -b["total"], -b["lvl"]))
            # max rune sockets an exceptional of this slot can roll (0 = none)
            sockets = max((s for _n, s in entries), default=0)
            out.append({"cat": cat, "bases": bases, "sockets": sockets})
        return out

    def _excbase_disabled(self, snap):
        return {n for n, s_ in snap["item_states"].get("_excbase", {}).items()
                if not s_.get("enabled", True)}

    def fracture_classes(self):
        """Fracture Bases roadmap: item classes in game order, each with its
        verified fracture targets (empty list = no natural target exists for
        that class, per the strict verification rule). Each target carries an
        illustrative example .ipd line. Classes with at least one target whose
        bot stat id is actually confirmed (``has_verified_target``) are wired
        into real pickit output when enabled; the rest stay reference-only."""
        def _with_example(t):
            return {**t, "example": gen.fracture_example_rule(t)}
        fb_states = self.cfg.get("item_states", {}).get("_fracture", {})
        return [{"group": g,
                 "classes": [{"name": n,
                              "targets": [_with_example(t) for t in gen.fracture_targets_for_class(n)],
                              "has_verified_target": gen.fracture_has_verified_target(n),
                              "enabled": fb_states.get(n, gen.fracture_default(n)).get("enabled", False)}
                             for n in names]}
                for g, names in gen.FRACTURE_CLASS_GROUPS]

    def set_fracture(self, name, enabled):
        valid = {n for _g, names in gen.FRACTURE_CLASS_GROUPS for n in names}
        if name not in valid:
            return {"error": "unknown class"}
        states = self.cfg.setdefault("item_states", {}).setdefault("_fracture", {})
        states.setdefault(name, {})["enabled"] = bool(enabled)
        save_config(self.cfg)
        return {"ok": True}

    # ── Magic & Rare tab ──────────────────────────────────────────────────────

    def magic_rare_data(self):
        """Content for the Magic & Rare tab. Currently the best-flask section:
        its enabled state, the flask base names, and the exact lines emitted."""
        return {
            "flasks": {
                "enabled": bool(self.cfg.get("magic_rare_flasks", True)),
                "bases": list(gen.MAGIC_RARE_FLASK_BASES),
                "lines": gen.magic_rare_flask_example_lines(),
            }
        }

    def set_magic_rare_flasks(self, enabled):
        self.cfg["magic_rare_flasks"] = bool(enabled)
        save_config(self.cfg)
        return {"ok": True}

    def craft_bases(self):
        from exilebot_pickit.data.icons import STATIC_ICONS as _ci, BASE_STATS as _bs
        st = self.cfg.get("item_states", {}).get("_craftbase", {})
        out = []
        for cat, names in gen.craft_base_categories():
            for n in names:
                s = st.get(n, {})
                out.append({"cat": cat, "base": n, "icon": _ci.get(n, ""),
                            "lvl": _bs.get(n, {}).get("lvl", 0),
                            "stats": _bs.get(n, {}).get("stats", ""),
                            "defence": gen.craft_base_defence(n),
                            "ilvl": int(s.get("ilvl", gen.craft_base_default_ilvl(n))),
                            "enabled": s.get("enabled", True)})
        return out

    def set_craft(self, name, enabled, ilvl):
        states = self.cfg.setdefault("item_states", {}).setdefault("_craftbase", {})
        e = states.setdefault(name, {})
        e["enabled"] = bool(enabled)
        try:
            # The card enforces the real floor — its own base's drop level.
            # This is only a garbage guard, so it must stay BELOW the lowest
            # drop level (65) or it would store a value the card never showed.
            e["ilvl"] = max(60, min(82, int(ilvl)))
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
            keep = max(5, min(100, int(keep_pct)))
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
                if not vals or keep >= 100:   # keep everything → no floor
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
        # Coerce BEFORE committing running=True: a bad value (or a failed thread
        # start) after the flag was set left status stuck on "running" forever —
        # every later Generate answered "already running" until an app restart.
        try:
            g, u = float(min_gear or 0), float(min_unique or 0)
        except (TypeError, ValueError):
            return {"error": "floors must be numbers"}
        with self._lock:
            if self._status["running"]:
                return {"error": "already running"}
            self._status = {"running": True, "log": [], "done": None}
        try:
            threading.Thread(target=self._generate, args=(league, g, u),
                             daemon=True).start()
        except Exception as e:
            with self._lock:
                self._status = {"running": False, "log": [],
                                "done": {"ok": False, "error": str(e)}}
            return {"error": str(e)}
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
        cat_enabled = {c[0]: enabled_cfg.get(c[0], True) for c in gen.ALL_CATEGORIES}
        for apk, _l, _r in self._ap_groups():
            cat_enabled[apk] = enabled_cfg.get(apk, enabled_cfg.get("_static", True))
        return {
            "cat_enabled": cat_enabled,
            "cat_thresh": {},          # per-category floors removed by design
            "item_states": item_states,
            "include_bases": bool(self.cfg.get("include_bases", True)),
            "base_quality": int(self.cfg.get("base_quality", 25)),
            "base_min_level": int(self.cfg.get("base_min_level", 82)),
            "magic_rare_flasks": bool(self.cfg.get("magic_rare_flasks", True)),
            "rare_gear_enabled": bool(self.cfg.get("rare_gear_enabled", True)),
        }

    def _generate(self, league, min_gear, min_unique):
        t0 = time.time()
        try:
            if self.cfg.get("auto_floor"):
                sf = self.suggest_floors(league, int(self.cfg.get("auto_floor_pct", 40) or 40))
                if not sf.get("error"):
                    min_unique = float(sf["unique"]); min_gear = float(sf["gear"])
                    self.cfg["min_exalt_unique"] = min_unique
                    self.cfg["min_exalt_gear"] = self.cfg["min_exalt"] = min_gear
                    save_config(self.cfg)
                    self._log(f"✨ Auto floor ({sf['keep_pct']}%): uniques ≥ {min_unique} ex · rest ≥ {min_gear} ex")
            snap = self._snapshot()
            self._log(f"Fetching live prices for {league}…")
            stale = set()
            cats = [c for c in gen.ALL_CATEGORIES if snap["cat_enabled"].get(c[0], True)]
            payloads = gen.fetch_all_payloads(league, cats, stale_out=stale)
            cur = payloads.get("currency")
            if not isinstance(cur, dict):
                raise RuntimeError("poe.ninja unreachable and no cached prices for this league")
            div_rate, div_found, _rate = asm.compute_divine_rate(cur)

            W = gen._W
            out = ["/" * W,
                   "//" + "  EXILEBOT 2  |  AUTO-GENERATED PICKIT".center(W - 4) + "//",
                   "/" * W,
                   f"// League  : {league}",
                   f"// Floors  : uniques >= {min_unique:g} ex · everything else >= {min_gear:g} ex",
                   # A missing Divine rate must not write the 1.0 placeholder —
                   # the filter's value ladder would read it as a real rate and
                   # paint every 1-ex item mythic purple.
                   (f"// Divine  : 1 Divine = {div_rate:.2f} Exalted"
                    if div_found else "// Divine  : rate unavailable"),
                   f"// Source  : poe.ninja PoE2 economy API  ·  Pickit Generator v{VERSION}",
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
                                                 eff, min_gear, en,
                                                 cat_states=snap["item_states"].get(key, {}))
                top_pool += asm.top_items_from_lines(lines)
                out += [gen.header_sub(label), ""] + lines + [""]
                ok += 1
                self._log(f"✓ {label}")

            # Always-pick sections — each group is its own Economy category;
            # single items and whole groups can be switched off there.
            sdis = self._ap_disabled(snap)
            # dedupe: items poe.ninja prices already got a force-kept rule in
            # their own category above — don't write a second static rule
            priced = set()
            for _p in payloads.values():
                if isinstance(_p, dict):
                    priced.update(
                        gen.ITEM_NAME_CORRECTIONS.get(i["name"], i["name"])
                        for i in _p.get("items", []) if i.get("name"))
            sdis |= priced & gen.always_pick_force_names()
            out += gen.build_tablet_rules(sdis)
            out += gen.build_wombgift_rules(sdis)
            out += gen.build_special_item_rules(sdis)
            out += gen.build_exotic_base_rules(sdis)
            out += gen.build_chance_base_rules(asm.chance_base_disabled(snap))
            craft_lines, _n, _floor = asm.craft_base_section(snap)
            out += craft_lines
            out += asm.fracture_pickit_section(snap)
            out += gen.build_magic_rare_rules(snap.get("magic_rare_flasks", True))
            # Rare-gear WeightedSum recipes (17 slots) live INSIDE the Magic & Rare
            # section, not in one of their own: both are managed from the Magic &
            # Rare tab, and a standalone 2-rule "Magic & Rare" section next to a
            # 51-rule "Rare Gear" one just looked broken in the Preview sidebar.
            # rare_gear_body() already emits its own per-slot sub-headers.
            if snap.get("rare_gear_enabled", True):
                from exilebot_pickit.data.rare.rules import rare_gear_body
                # Per-slot switches: a slot the user turned off leaves the pickit
                # entirely. Read from the snapshot, not self.cfg — the worker runs
                # on a thread and must see the settings as they were at Generate.
                _rgst = (snap.get("item_states", {}) or {}).get("_raregear", {})
                _off = {s for s, v in _rgst.items() if not v.get("enabled", True)}
                _rg = rare_gear_body(disabled=_off)
                if _rg:
                    out += [""] + _rg
            excdis = self._excbase_disabled(snap)
            if snap["include_bases"]:
                out += ["", gen.header_major("Exceptional Bases"), ""]
                out += gen.build_base_rules(min_quality=snap["base_quality"],
                                            min_level=snap["base_min_level"],
                                            disabled=excdis)

            # Validate the FLATTENED lines — multi-line banner headers in
            # `out` would shift line numbers vs what Preview displays.
            flat = "\n".join(out).splitlines()
            validation = gen.validate_pickit(flat)
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
                # exalt value of 1 Chaos Orb, from the currency payload already
                # fetched — the alert text renders moves in chaos ("c"); passing
                # 0 here silently showed raw exalt values under a "c" label.
                cur_by_id = {i["id"]: i for i in cur.get("items", [])}
                cur_rate = gen.exalted_rate(cur)
                chaos_v = next((float(ln.get("primaryValue") or 0) * (cur_rate or 1.0)
                                for ln in cur.get("lines", [])
                                if (cur_by_id.get(ln.get("id")) or {}).get("name") == "Chaos Orb"),
                               0.0)
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
            flt = os.path.join(OUTPUT_DIR, base + ".filter")
            gen.write_text_atomic(flt, "\n".join(gen.build_loot_filter(
                out, theme=self.cfg.get("filter_theme"))))
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
                    # Atomic, like every other write: a plain copy2 into the folder
                    # the bot READS could be seen half-written (truncated rule list —
                    # the bot silently walks past loot), and an error here used to
                    # fail the WHOLE generate even though the .ipd on disk is fine.
                    try:
                        dst = os.path.join(bot, os.path.basename(ipd))
                        shutil.copy2(ipd, dst + ".tmp")
                        os.replace(dst + ".tmp", dst)
                        copied = bot
                        self._log(f"✓ Auto-copied to {bot}")
                    except OSError as e:
                        self._log(f"✗ Auto-copy failed ({e}) — the pickit is in the "
                                  "output folder, copy it by hand")
                else:
                    self._log("✗ Auto-copy skipped: bot folder doesn't exist")
            fdir = (self.cfg.get("poe2_filter_dir") or "").strip() or _default_dir()
            if self.cfg.get("copy_filter_to_game") and fdir and os.path.isdir(fdir):
                try:
                    shutil.copy2(flt, os.path.join(fdir, os.path.basename(flt)))
                    self._log("✓ .filter copied to the PoE2 folder")
                except OSError:
                    self._log("✗ Couldn't copy .filter to the game folder")

            # Headers are multi-line strings; Preview's section parser works
            # line-by-line, so flatten to real lines (same shape as the file).
            self._last_lines = content.splitlines()
            active = sum(1 for l in out if l and not l.startswith("//") and "[StashItem]" in l)
            commented = sum(1 for l in out if l.startswith("//") and "[StashItem]" in l)
            top_pool.sort(key=lambda t: -t[1])
            _seen = set()
            top_pool = [t for t in top_pool
                        if not (t[0] in _seen or _seen.add(t[0]))]
            self.cfg.update({"league": league,
                             "min_exalt_gear": min_gear, "min_exalt": min_gear,
                             "min_exalt_unique": min_unique,
                             # Stamp the version so Preview can tell you when the
                             # pickit it is showing predates your current rules.
                             "last_gen_version": VERSION})
            # Run history (same shape the Tk app writes)
            hist = self.cfg.setdefault("history", [])
            # Divine rate of the previous run — the summary shows the economy
            # moving ("Divine 412 → 433") instead of a bare number.
            prev_divine = float((hist[-1] if hist else {}).get("divine_rate") or 0)
            hist.append({"ts": time.strftime("%Y-%m-%d %H:%M"),
                         "active": active, "commented": commented,
                         "uf": float(min_unique), "gf": float(min_gear),
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
            # name -> poe.ninja icon URL, from the payloads already fetched this
            # run (no extra network) — used by the UI's top-picks table.
            icon_by: dict = {}
            try:
                for _p in payloads.values():
                    if not isinstance(_p, dict):
                        continue
                    for _ln in _p.get("lines", []):
                        _nm, _ic = _ln.get("name"), _ln.get("icon")
                        if _nm and _ic and _nm not in icon_by:
                            icon_by[_nm] = _ic
                    for _it in _p.get("items", []):
                        _nm = _it.get("name")
                        _nm = gen.ITEM_NAME_CORRECTIONS.get(_nm, _nm) if _nm else None
                        _img = _it.get("image") or ""
                        if _img.startswith("/"):
                            _img = "https://web.poecdn.com" + _img
                        if _nm and _img and _nm not in icon_by:
                            icon_by[_nm] = _img
            except Exception:
                icon_by = {}
            with self._lock:
                self._status["running"] = False
                self._status["done"] = {
                    "ok": True, "path": ipd, "active": active, "commented": commented,
                    "cats_ok": ok, "cats_fail": fail, "stale": len(stale),
                    "divine_rate": round(div_rate, 1),
                    "prev_divine": round(prev_divine, 1),
                    "secs": round(time.time() - t0, 1),
                    "top": [{"name": t[0], "ex": round(t[1], 1),
                             "cat": (t[2] if len(t) > 2 else ""),
                             "icon": icon_by.get(t[0], "")} for t in top_pool[:5]],
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

    # ── Bot connection ────────────────────────────────────────────────────────
    # Setting the folder and turning on auto-copy is NOT enough, and the old
    # Settings card implied it was. Exiled Bot loads only the single .ipd named
    # by `active_profile` in its own pickit.ini; if that doesn't match our output
    # name, the copy succeeds, the file lands, and the bot keeps reading an old
    # pickit — silently. The owner's bot was doing exactly this for a day. So
    # don't claim "connected": go and read the bot's config, and check.

    def _bot_ini_path(self):
        """The bot's pickit.ini — it sits beside the Pickit folder we copy into."""
        folder = (self.cfg.get("bot_folder") or "").strip()
        if not folder:
            return ""
        return os.path.join(os.path.dirname(os.path.normpath(folder)), "pickit.ini")

    def detect_bot_folder(self):
        """Best-effort guess at the Exiled Bot 2 pickit folder by scanning the usual
        install spots (Desktop, Downloads, Documents, home, Program Files, drive
        roots). A hit is confirmed only when a `pickit.ini` sits beside a `Pickit`
        folder — the signature of a real bot install — so false positives are rare.
        Returns ``{found, path, all}``; never writes config."""
        import glob
        home = os.path.expanduser("~")
        sub = os.path.join("Configuration", "default", "Pickit")
        hits: list = []

        def _scan(root, patterns):
            if not root or not os.path.isdir(root):
                return
            for pat in patterns:
                try:
                    matches = glob.glob(os.path.join(root, pat, sub))
                except OSError:
                    continue
                for cand in matches:
                    cand = os.path.normpath(cand)
                    ini = os.path.join(os.path.dirname(cand), "pickit.ini")
                    if os.path.isdir(cand) and os.path.isfile(ini) and cand not in hits:
                        hits.append(cand)

        # Small, well-known folders: safe to look up to two levels deep.
        for root in (os.path.join(home, "Desktop"), os.path.join(home, "Downloads"),
                     os.path.join(home, "Documents"), home):
            _scan(root, ("", "*", os.path.join("*", "*")))
        # Big trees (drive roots, Program Files): one level only, to stay fast.
        big = []
        for pf in ("ProgramFiles", "ProgramFiles(x86)"):
            if os.environ.get(pf):
                big.append(os.environ[pf])
        for d in "CDEFG":
            big.append(d + ":\\")
        for root in big:
            _scan(root, ("", "*"))

        return {"found": bool(hits), "path": hits[0] if hits else "", "all": hits}

    def bot_connection(self):
        """Will the bot actually read what we generate? Verified, not assumed."""
        folder = (self.cfg.get("bot_folder") or "").strip()
        out = (self.cfg.get("output_base") or "poe2_pickit").strip() or "poe2_pickit"
        r = {"folder": folder, "output": out, "profile": "", "ini": "",
             "auto_copy": bool(self.cfg.get("auto_copy")), "state": "", "detail": ""}

        if not folder:
            r["state"] = "unset"
            r["detail"] = ("No bot folder set. Generating writes a pickit, but nothing "
                           "reaches Exiled Bot until you point this at its Pickit folder.")
            return r
        if not os.path.isdir(folder):
            r["state"] = "badfolder"
            r["detail"] = "That folder doesn't exist any more. Pick it again."
            return r

        ini = self._bot_ini_path()
        r["ini"] = ini
        if not os.path.isfile(ini):
            r["state"] = "noini"
            r["detail"] = ("Couldn't find the bot's pickit.ini next to that folder, so I "
                           "can't confirm which file the bot loads. Check it by hand: "
                           f"active_profile must be \"{out}\".")
            return r

        try:
            with open(ini, encoding="utf-8", errors="replace") as f:
                m = re.search(r"(?mi)^\s*active_profile\s*=\s*(.+?)\s*$", f.read())
            r["profile"] = m.group(1).strip() if m else ""
        except OSError:
            r["state"] = "noini"
            r["detail"] = "Couldn't read the bot's pickit.ini."
            return r

        if not r["profile"]:
            r["state"] = "mismatch"
            r["detail"] = ("The bot's pickit.ini has no active_profile line, so it won't "
                           f"load your pickit. It needs: active_profile={out}")
        elif r["profile"] != out:
            r["state"] = "mismatch"
            r["detail"] = (f"Your bot is reading \"{r['profile']}.ipd\" — but you generate "
                           f"\"{out}.ipd\". Everything you generate is being ignored.")
        elif not r["auto_copy"]:
            r["state"] = "nocopy"
            r["detail"] = ("Names match, but Auto-copy is off — the pickit won't be "
                           "deployed to the bot on its own.")
        else:
            r["state"] = "ok"
            r["detail"] = f"Your bot reads {out}.ipd, and every Generate deploys it there."
        return r

    def fix_bot_profile(self):
        """Point the bot's active_profile at our output file. Backs the ini up first."""
        ini = self._bot_ini_path()
        out = (self.cfg.get("output_base") or "poe2_pickit").strip() or "poe2_pickit"
        if not ini or not os.path.isfile(ini):
            return {"ok": False, "error": "Couldn't find the bot's pickit.ini."}
        try:
            with open(ini, encoding="utf-8", errors="replace") as f:
                src = f.read()
            bak = ini + ".bak"
            if not os.path.exists(bak):
                shutil.copyfile(ini, bak)          # never overwrite an existing backup
            new, n = re.subn(r"(?mi)^(\s*active_profile\s*=\s*).*$", r"\g<1>" + out, src)
            if n == 0:                             # no line at all — add one
                new = src.rstrip() + f"\n\n[profile]\nactive_profile={out}\n"
            gen.write_text_atomic(ini, new)
            log_info(f"bot pickit.ini active_profile -> {out}")
            return {"ok": True, "profile": out, "backup": bak}
        except Exception as e:
            log_exc("fix_bot_profile")
            return {"ok": False, "error": str(e)}

    def preview_meta(self):
        """How fresh is what Preview is showing?

        Preview renders the LAST generated pickit. Showing a 14-hour-old file
        from a previous app version, with no hint that it is old, reads as a
        bug — it did to the owner, who had every reason to know better. So say
        so: age, and whether the rules have changed since it was written.
        """
        base = (self.cfg.get("output_base") or "poe2_pickit").strip() or "poe2_pickit"
        try:
            mtime = os.path.getmtime(os.path.join(OUTPUT_DIR, base + ".ipd"))
        except OSError:
            return {"empty": True}
        gen_ver = str(self.cfg.get("last_gen_version") or "")
        return {
            "empty": False,
            "age_secs": max(0, int(time.time() - mtime)),
            "generated_at": time.strftime("%Y-%m-%d %H:%M", time.localtime(mtime)),
            "gen_version": gen_ver,
            "current_version": VERSION,
            # No recorded version means it predates this field entirely.
            "outdated": (gen_ver != VERSION),
        }

    def validation(self):
        """Full error/warning list from the last generate (Preview banner)."""
        v = getattr(self, "_last_validation", None) or {"errors": [], "warnings": []}
        return {"errors": [f"Line {n}: {m}" for n, m in v.get("errors", [])],
                "warnings": [f"Line {n}: {m}" for n, m in v.get("warnings", [])]}

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
        try:
            os.startfile(p)   # noqa: S606
        except OSError:
            # no default app for the extension — fall back to Notepad
            try:
                import subprocess
                subprocess.Popen(["notepad.exe", p])
            except Exception as e:
                return {"error": f"couldn't open: {e}"}
        return {"ok": True}

    # ── Item Check ────────────────────────────────────────────────────────────

    @staticmethod
    def _parse_item_text(text):
        """Parse a PoE2 Ctrl+C item copy into the fields the pickit keys on.

        The name lines sit between ``Rarity:`` and the first ``--------``, but
        ``Item Level:`` and ``Quality:`` live in *later* blocks — so keep reading past
        that separator instead of stopping at it.
        """
        fields, name_lines, in_head = {}, [], False
        for raw in (text or "").splitlines():
            ln = raw.strip()
            if not ln:
                continue
            if ln.startswith("Item Class:"):
                fields["class"] = ln.split(":", 1)[1].strip()
            elif ln.startswith("Rarity:"):
                fields["rarity"] = ln.split(":", 1)[1].strip()
                in_head = True
            elif ln.startswith("Item Level:"):
                m = re.search(r"\d+", ln)
                if m:
                    fields["ilvl"] = int(m.group())
            elif ln.startswith("Quality:"):
                m = re.search(r"\d+", ln)
                if m:
                    fields["quality"] = int(m.group())
            elif set(ln) == {"-"}:
                in_head = False
            elif in_head and len(name_lines) < 2:
                name_lines.append(ln)
        if not fields.get("class") and not name_lines:
            return None
        fields["base"] = name_lines[-1] if name_lines else ""
        fields["name"] = name_lines[0] if name_lines else ""
        return fields

    @staticmethod
    def _payload_price(payload, candidates, is_unique):
        """This item's exalt value in one poe.ninja category payload, or None when
        that category doesn't price it. Mirrors the two shapes ``economy()`` reads."""
        r = gen.exalted_rate(payload) or 1.0
        if is_unique:
            for ln in payload.get("lines", []):
                if ln.get("name") in candidates:
                    return float(ln.get("primaryValue") or 0.0) * r
            return None
        by_id = {i["id"]: i for i in payload.get("items", []) if i.get("id")}
        for ln in payload.get("lines", []):
            it = by_id.get(ln.get("id"))
            if not it or not it.get("name") or it["name"] in gen.ITEM_NAME_SKIP:
                continue
            if gen.ITEM_NAME_CORRECTIONS.get(it["name"], it["name"]) in candidates:
                return float(ln.get("primaryValue") or 0.0) * r
        return None

    def _economy_rows(self, league, snap, gear, uniq, cands):
        """Verdict rows for a priced item — and the .ipd line, when it is picked.

        This does not *simulate* anything: it runs the same ``assembly`` call that
        writes the pickit and reports whether a rule for this item really comes out
        of it. If the answer here and the file ever disagreed, the file would be wrong.
        """
        rows, rule = [], None
        payloads = gen.fetch_all_payloads(league, gen.ALL_CATEGORIES)
        cur = payloads.get("currency")
        div = asm.compute_divine_rate(cur)[0] if isinstance(cur, dict) else 1.0
        chaos = self._chaos_rate(cur)
        # people price things in different units — show all three
        px = lambda v: self._price_str(v, div, chaos)          # noqa: E731

        for key, _t, label, is_uniq in gen.ALL_CATEGORIES:
            p = payloads.get(key)
            if not isinstance(p, dict):
                continue
            price = self._payload_price(p, cands, is_uniq)
            if price is None:
                continue                       # this category doesn't price it
            cat_on = bool(snap["cat_enabled"].get(key, True))
            eff = asm.effective_min(snap, key, is_uniq, gear, uniq)
            hit = None
            if cat_on:
                cs = snap["item_states"].get(key, {})
                en = asm.enabled_names_for(key, is_uniq, p, cs)
                for line in asm.build_category_lines(key, is_uniq, p, div, eff,
                                                     gear, en, cat_states=cs):
                    if (line and not line.startswith("//") and "[StashItem]" in line
                            and asm.extract_rule_name(line) in cands):
                        hit = line
                        break
            what = "unique floor" if is_uniq else "item floor"
            if hit:
                rule = hit
                # A rule can come out for three different reasons, and saying "it clears
                # your floor" when the floor was never applied would be a lie.
                always = (gen.ALWAYS_PICK_CURRENCY if key == "currency" else
                          gen.ALWAYS_PICK_RUNES if key == "runes" else [])
                if key in gen.PICK_ALL_CATEGORIES:
                    detail = (f"Everything in {label} is picked up whatever it is worth — your "
                              f"{eff:g} ex floor does not apply here. poe.ninja: {px(price)}.")
                elif cands & (set(always) | gen.always_pick_force_names()):
                    detail = ("Always picked up, whatever the price — it is on the always-take "
                              f"list. poe.ninja: {px(price)}.")
                else:
                    detail = (f"poe.ninja prices it at {px(price)}, at or above your "
                              f"{eff:g} ex {what}.")
                rows.append({"kind": "pick", "rule": label, "detail": detail})
            elif not cat_on:
                rows.append({"kind": "ignore", "rule": label,
                             "detail": f"The whole {label} category is switched off.",
                             "fix": f"Economy → turn {label} back on."})
            elif price < eff:
                rows.append({"kind": "ignore", "rule": label,
                             "detail": f"Worth {px(price)}, but your {what} is {eff:g} ex — "
                                       f"it misses by {self._ex(eff - price)} ex.",
                             "fix": f"Lower the {what} to {self._ex(price)} ex or less and it gets taken."})
            else:
                rows.append({"kind": "ignore", "rule": label,
                             "detail": f"Worth {px(price)}, which clears your {eff:g} ex "
                                       f"{what} — but you switched this item off.",
                             "fix": f"Economy → {label} → switch it back on."})
            break                              # priced in exactly one category

        if not rows:                           # always-pick groups carry no price
            ap_off = self._ap_disabled(snap)
            for key, label, ap_rows in self._ap_groups():
                nm = next((n for n, _b in ap_rows if n in cands), None)
                if nm is None:
                    continue
                if snap["cat_enabled"].get(key, True) and nm not in ap_off:
                    rows.append({"kind": "pick", "rule": label,
                                 "detail": "Always picked up — no price floor applies to it."})
                else:
                    rows.append({"kind": "ignore", "rule": label,
                                 "detail": f"{nm} is switched off.",
                                 "fix": f"Economy → {label} → switch it back on."})
                break
        return rows, rule

    def _base_rows(self, snap, cands, base, klass, rarity, ilvl, fractured):
        """Verdict rows for the curated base sections: craft, chance, exceptional,
        fracture. These are name/class/ilvl rules, so the answer is exact."""
        rows = []

        cb = next((c for c in self.craft_bases() if c["base"] in cands), None)
        if cb:
            ok_ilvl = ilvl is None or ilvl >= cb["ilvl"]
            if not cb["enabled"]:
                rows.append({"kind": "ignore", "rule": "Craft base",
                             "detail": f"{cb['base']} is switched off.",
                             "fix": "Craft → switch it back on."})
            elif not ok_ilvl:
                rows.append({"kind": "ignore", "rule": "Craft base",
                             "detail": f"Needs item level {cb['ilvl']}+, this one is {ilvl}.",
                             "fix": f"Craft → lower {cb['base']} to ilvl {ilvl}."})
            else:
                rows.append({"kind": "pick", "rule": "Craft base",
                             "detail": f"On, and item level {ilvl if ilvl is not None else '?'} "
                                       f"meets the {cb['ilvl']}+ requirement."})

        chb = next((c for c in self.chance_bases() if c["base"] in cands), None)
        if chb:
            rows.append({"kind": "pick" if chb["enabled"] else "ignore",
                         "rule": "Chance base",
                         "detail": ("On — picked for chancing." if chb["enabled"]
                                    else f"{chb['base']} is switched off."),
                         **({} if chb["enabled"] else {"fix": "Chance → switch it back on."})})

        exb = None
        for cat in self.exceptional_bases():
            exb = next((b for b in cat["bases"] if b["name"] in cands), None)
            if exb:
                break
        if exb:
            min_l = int(self.cfg.get("base_min_level", 82))
            min_q = int(self.cfg.get("base_quality", 25))
            inc = bool(snap.get("include_bases", True))
            is_norm = rarity.lower() == "normal"
            if not inc:
                rows.append({"kind": "ignore", "rule": "Exceptional base",
                             "detail": "Base pickup is switched off entirely.",
                             "fix": "Settings → turn base pickup back on."})
            elif not exb["enabled"]:
                rows.append({"kind": "ignore", "rule": "Exceptional base",
                             "detail": f"{exb['name']} is switched off.",
                             "fix": "Exceptional → switch it back on."})
            elif not is_norm:
                rows.append({"kind": "ignore", "rule": "Exceptional base",
                             "detail": f"This rule only takes Normal (white) items — yours is {rarity}."})
            elif ilvl is not None and ilvl < min_l:
                rows.append({"kind": "ignore", "rule": "Exceptional base",
                             "detail": f"Needs item level {min_l}+, this one is {ilvl}.",
                             "fix": f"Settings → lower the base item level to {ilvl}."})
            else:
                rows.append({"kind": "pick", "rule": "Exceptional base",
                             "detail": f"On, Normal rarity, item level {min_l}+ — "
                                       f"but it also needs {min_q}%+ quality, which the "
                                       "copied text doesn't include. Check that in-game."})

        # Only speak up when the item actually *is* fractured — a fracture rule can
        # never fire otherwise, so mentioning it on every wand is noise, not a verdict.
        if klass and fractured:
            targets = gen.fracture_targets_for_class(klass)
            fb = snap["item_states"].get("_fracture", {})
            on = fb.get(klass, gen.fracture_default(klass)).get("enabled", False)
            if not targets:
                rows.append({"kind": "ignore", "rule": "Fracture",
                             "detail": f"No fracture targets are defined for {klass}, so a "
                                       "fractured one isn't picked up for its fracture."})
            elif not on:
                rows.append({"kind": "ignore", "rule": "Fracture",
                             "detail": f"{klass} is switched off in Fracture.",
                             "fix": f"Fracture → switch {klass} back on."})
            else:
                rows.append({"kind": "depends", "rule": "Fracture",
                             "detail": f"{klass} is on. It is picked up only if the *fractured* "
                                       "mod is one of the targets below — compare it against your "
                                       "item's fractured line.",
                             # the target's own explanation trails after " (" — the mod
                             # itself is what the user compares against, so cut there
                             "targets": [{"tier": t.get("tier", ""),
                                          "text": (t.get("text") or t.get("id", "")).split(" (")[0]}
                                         for t in targets][:12]})
        return rows

    def _rare_rows(self, snap, base, rarity):
        """Verdict rows for rare gear. Two of the three answers are definitive: a base
        no recipe covers is never taken, and a switched-off slot is never taken. Only
        a covered, enabled slot depends on the rolls — and the bot scores those with
        [WeightedSum] from the item's real mods, which the copied text can't give us.
        Saying "it depends" there is the honest answer; a number would be invented."""
        if rarity.lower() != "rare" or not base:
            return []
        from exilebot_pickit.data.rare import rules as rare_rules
        if not snap.get("rare_gear_enabled", True):
            return [{"kind": "ignore", "rule": "Rare gear",
                     "detail": "Rare-gear pickup is switched off entirely.",
                     "fix": "Magic & Rare → turn rare gear back on."}]
        slot = next((s for s, spec in rare_rules.RARE_GEAR.items()
                     if base in spec["bases"]), None)
        if slot is None:
            return [{"kind": "ignore", "rule": "Rare gear",
                     "detail": f"No rare recipe covers the base '{base}', so this rare is "
                               "never picked up no matter how it rolled."}]
        spec = rare_rules.RARE_GEAR[slot]
        if slot in self.rare_slot_disabled():
            return [{"kind": "ignore", "rule": f"Rare gear · {slot}",
                     "detail": f"The {slot} slot is switched off, so this rare is never picked up.",
                     "fix": f"Magic & Rare → switch {slot} back on."}]
        stats = [{"stat": rare_rules.STAT_LABELS.get(sid, sid), "w": w}
                 for sid, w in spec["weights"].items()]
        return [{"kind": "depends", "rule": f"Rare gear · {slot}",
                 "detail": f"This base is covered and the slot is on, so it comes down to the "
                           f"rolls: the bot adds up the stats below and takes it at "
                           f"{spec['threshold']}+. The copied text doesn't carry the rolls, so "
                           f"the bot makes this call in-game, not here.",
                 "weights": stats, "threshold": spec["threshold"]}]

    # poe.ninja writes mods as "[EnergyShield|Energy Shield]" markup over a value
    # range; the game writes the shown name and a rolled number.
    _MOD_LINK  = re.compile(r"\[([^\]|]+)\|([^\]]+)\]")           # [Key|Shown] -> Shown
    _MOD_TAG   = re.compile(r"\[([^\]|]+)\]")                     # [Word]      -> Word
    _MOD_RANGE = re.compile(r"\((\d+(?:\.\d+)?)-(\d+(?:\.\d+)?)\)")  # (10-20) -> 15

    @staticmethod
    def _ex(v):
        """Prices run from 0.05 ex to millions — neither end should print badly."""
        return f"{v:,.0f}" if v >= 1000 else f"{v:.2f}"

    def _price_str(self, v, div_rate, chaos_ex):
        """The same price in the units people actually think in. A unit is left out
        when it would round to noise — "0.00 div" tells nobody anything."""
        out = [f"{self._ex(v)} ex"]
        if div_rate > 0 and v / div_rate >= 0.1:
            out.append(f"{self._ex(v / div_rate)} div")
        if chaos_ex > 0 and v / chaos_ex >= 1:
            out.append(f"{self._ex(v / chaos_ex)} chaos")
        return " · ".join(out)

    @staticmethod
    def _chaos_rate(currency_payload):
        """Exalt value of one Chaos Orb, or 0 when it isn't priced."""
        if not isinstance(currency_payload, dict):
            return 0.0
        r = gen.exalted_rate(currency_payload) or 1.0
        by_id = {i["id"]: i for i in currency_payload.get("items", []) if i.get("id")}
        for ln in currency_payload.get("lines", []):
            it = by_id.get(ln.get("id"))
            if it and it.get("name") == "Chaos Orb":
                return float(ln.get("primaryValue") or 0.0) * r
        return 0.0

    @classmethod
    def _as_item_text(cls, line):
        """Render a poe.ninja unique as the game's Ctrl+C copy looks."""
        def mid(m):
            lo, hi = float(m.group(1)), float(m.group(2))
            v = (lo + hi) / 2
            return f"{v:g}" if v % 1 else str(int(v))

        def mod(t):
            t = cls._MOD_LINK.sub(r"\2", t)
            t = cls._MOD_TAG.sub(r"\1", t)
            return cls._MOD_RANGE.sub(mid, t)

        out = [f"Item Class: {line.get('category') or 'Unknown'}", "Rarity: Unique",
               line["name"], line["baseType"], "--------"]
        lv = line.get("levelRequired")
        if lv:
            out += ["Requirements:", f"Level: {lv}", "--------"]
        out += ["Item Level: 82", "--------"]
        mods = [mod(m["text"]) for m in (line.get("explicitModifiers") or []) if m.get("text")]
        return "\n".join(out + (mods or ["(unique modifiers)"]))

    # RARE_GEAR is keyed by slot ("Wand"); the game's item class is the plural
    # ("Wands"), which is also how FRACTURE_TARGETS and the craft-base lists key it.
    _SLOT_CLASS = {"Body Armour": "Body Armours", "Helmet": "Helmets", "Gloves": "Gloves",
                   "Boots": "Boots", "Amulet": "Amulets", "Ring": "Rings", "Belt": "Belts",
                   "Focus": "Foci", "Quiver": "Quivers", "Bow": "Bows",
                   "Crossbow": "Crossbows", "Quarterstaff": "Quarterstaves",
                   "Spear": "Spears", "Mace": "One Hand Maces", "Sceptre": "Sceptres",
                   "Wand": "Wands", "Staff": "Staves"}
    # Rares roll a generated two-word name in game, so any of these is as real as
    # the next — only the base name and the mods decide anything.
    _RARE_NAMES = ["Dust Song", "Widow Grasp", "Gloom Bite", "Carrion Whisper",
                   "Bramble Sorrow", "Vestige Howl", "Hollow Vow", "Rift Mourning"]

    @staticmethod
    def _bases_by_class():
        """base names the game can actually drop, grouped by item class."""
        from exilebot_pickit.data.rare import rules as rare_rules
        out = {cat: list(names) for cat, names in gen.craft_base_categories()}
        for slot, spec in rare_rules.RARE_GEAR.items():
            out.setdefault(AppApi._SLOT_CLASS.get(slot, slot), []).extend(spec["bases"])
        return {k: sorted(set(v)) for k, v in out.items() if v}

    # our target text states a mod's range ("20-45%"); a real item shows one roll
    _BARE_RANGE = re.compile(r"(?<![\w.])(\d+(?:\.\d+)?)-(\d+(?:\.\d+)?)(?![\w.])")

    @classmethod
    def _mods_for_class(cls, klass, n):
        """Real mod text for this item class, taken from our own verified fracture
        targets — so an example item's mods are mods that actually roll on it."""
        def rolled(m):
            v = (float(m.group(1)) + float(m.group(2))) / 2
            return f"{v:g}" if v % 1 else str(int(v))

        pool = [cls._BARE_RANGE.sub(rolled, t["text"].split(" (")[0])
                for t in gen.FRACTURE_TARGETS
                if klass in t.get("classes", []) and t.get("text")]
        random.shuffle(pool)
        return pool[:n]

    def _example_unique(self, league):
        uniq_cats = [c for c in gen.ALL_CATEGORIES if c[3]]
        payloads = gen.fetch_all_payloads(league, uniq_cats)
        pool = []
        for key, _t, _label, _u in uniq_cats:
            p = payloads.get(key)
            if not isinstance(p, dict):
                continue
            r = gen.exalted_rate(p) or 1.0
            for ln in p.get("lines", []):
                if not ln.get("name") or not ln.get("baseType"):
                    continue
                if float(ln.get("primaryValue") or 0.0) * r > 0:
                    pool.append(ln)
        if not pool:
            return None
        ln = random.choice(pool)
        return {"text": self._as_item_text(ln), "name": ln["name"], "kind": "unique"}

    def _example_rare(self):
        from exilebot_pickit.data.rare import rules as rare_rules
        slot = random.choice(list(rare_rules.RARE_GEAR))
        base = random.choice(rare_rules.RARE_GEAR[slot]["bases"])
        klass = self._SLOT_CLASS.get(slot, slot)
        out = [f"Item Class: {klass}", "Rarity: Rare", random.choice(self._RARE_NAMES),
               base, "--------", "Item Level: 81", "--------"]
        out += self._mods_for_class(klass, 3) or ["(rare modifiers)"]
        return {"text": "\n".join(out), "name": f"a rare {slot}", "kind": "rare"}

    def _example_fractured(self):
        by_class = self._bases_by_class()
        pool = [t for t in gen.FRACTURE_TARGETS
                if t.get("text") and any(c in by_class for c in t.get("classes", []))]
        if not pool:
            return None
        t = random.choice(pool)
        klass = next(c for c in t["classes"] if c in by_class)
        base = random.choice(by_class[klass])
        frac = self._BARE_RANGE.sub(
            lambda m: str(int((float(m.group(1)) + float(m.group(2))) / 2)),
            t["text"].split(" (")[0])
        out = [f"Item Class: {klass}", "Rarity: Rare", random.choice(self._RARE_NAMES),
               base, "--------", "Item Level: 82", "--------", "Fractured Item",
               f"{frac} (fractured)"]
        out += [m for m in self._mods_for_class(klass, 2) if m != frac]
        return {"text": "\n".join(out), "name": f"a fractured {klass[:-1] if klass.endswith('s') else klass}",
                "kind": "fractured"}

    def example_item(self, league=None):
        """A random example item — sometimes a unique, sometimes a rare, sometimes a
        fractured one — so pressing the button a few times shows all three verdicts
        rather than the same one every time.

        Everything in it is real: uniques (with their live price) come straight from
        poe.ninja, bases come from the game's own base list, and the mods are real mod
        text pulled from our verified fracture targets for that item class. Only a
        rare's generated two-word name is arbitrary, which is what it is in game too."""
        try:
            league = league or self.cfg.get("league") or ""
            kinds = ["rare", "fractured"] + (["unique"] if league else [])
            random.shuffle(kinds)
            for kind in kinds:
                r = (self._example_unique(league) if kind == "unique" else
                     self._example_rare() if kind == "rare" else
                     self._example_fractured())
                if r:
                    return {"ok": True, **r}
            return {"error": "Couldn't build an example — open Economy once to load prices."}
        except Exception as e:
            return {"error": str(e)}

    def check_item(self, text, league=None):
        """Item Check — paste an item's in-game text, get the verdict your pickit
        will actually give it, and the reason.

        Economy items are answered by running the *same* assembly that writes the .ipd
        and reporting whether a rule for this item really comes out of it, plus the
        exact line. Bases are exact too. Rare gear is scored by [WeightedSum] inside
        the bot from the item's real mod rolls, so where that is the deciding factor
        this says so instead of inventing a verdict."""
        try:
            it = self._parse_item_text(text)
            if it is None:
                return {"error": "Paste an item first — hover it in-game, press Ctrl+C, "
                                 "then paste the whole thing here."}
            name, base = it.get("name", ""), it.get("base", "")
            rarity, klass = it.get("rarity", ""), it.get("class", "")
            ilvl, qual = it.get("ilvl"), it.get("quality")
            cands = {n for n in (name, base) if n}
            league = league or self.cfg.get("league") or ""
            snap = self._snapshot()
            gear = float(self.cfg.get("min_exalt_gear", 0.0) or 0.0)
            uniq = float(self.cfg.get("min_exalt_unique", 0.0) or 0.0)

            rows, rule = [], None
            if league:
                rows, rule = self._economy_rows(league, snap, gear, uniq, cands)
            fractured = "fractured" in (text or "").lower()
            rows += self._base_rows(snap, cands, base, klass, rarity, ilvl, fractured)
            rows += self._rare_rows(snap, base, rarity)

            if any(r["kind"] == "pick" for r in rows):
                verdict = "pick"
            elif any(r["kind"] == "depends" for r in rows):
                verdict = "depends"
            elif not league:
                # No league means the poe.ninja half never ran. Saying "nothing matches"
                # here would be a claim we didn't check — say what we actually know.
                verdict = "depends"
                rows.append({"kind": "info", "rule": "Prices not checked",
                             "detail": "No league is selected, so I couldn't look up poe.ninja "
                                       "prices — uniques and currency weren't checked. Pick a "
                                       "league on the Generate tab and run this again."})
            elif any(r["kind"] == "ignore" for r in rows):
                verdict = "ignore"
            else:
                verdict = "none"
                rows.append({"kind": "ignore", "rule": "No rule matches",
                             "detail": "Nothing in your pickit targets this item — poe.ninja "
                                       "doesn't price it, and no base or rare recipe covers it. "
                                       "The bot will walk past it."})
            return {"ok": True, "verdict": verdict, "rule": rule, "rows": rows,
                    "league": league,
                    "item": {"name": name, "base": base, "class": klass,
                             "rarity": rarity, "ilvl": ilvl, "quality": qual}}
        except Exception as e:
            return {"error": str(e)}

    def js_error(self, msg):
        """UI-side error reporter — lands in debug.log for diagnosis."""
        from exilebot_pickit.ui.config import log_info
        log_info(f"JSERR {str(msg)[:500]}")
        return {"ok": True}

    def clear_history(self):
        self.cfg["history"] = []
        save_config(self.cfg)
        return {"ok": True}

    def chaos_ex(self, league):
        """Exalt value of 1 Chaos Orb AND 1 Divine Orb, from the one currency payload.

        The Generate tab needs both — chaos for the reference line under each floor, divine
        for the floor slider's top end — and this is the only currency fetch it makes on
        load (the divine rate otherwise only arrived after opening Economy or generating,
        which is why the slider was stuck on its 100 ex fallback)."""
        try:
            p = gen.fetch_all_payloads(league, [("currency", "Currency", "Currency", False)])["currency"]
            r = gen.exalted_rate(p) or 1.0
            by_id = {i["id"]: i for i in p.get("items", [])}
            chaos = divine = 0.0
            for line in p.get("lines", []):
                it = by_id.get(line.get("id"))
                nm = it.get("name") if it else ""
                if nm == "Chaos Orb":
                    chaos = float(line.get("primaryValue") or 0) * r
                elif nm == "Divine Orb":
                    divine = float(line.get("primaryValue") or 0) * r
            if not math.isfinite(chaos):
                chaos = 0.0                    # NaN over the bridge hangs the JS promise
            if not math.isfinite(divine):
                divine = 0.0
            return {"ex": chaos, "div": divine}
        except Exception:
            return {"ex": 0.0, "div": 0.0}

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

