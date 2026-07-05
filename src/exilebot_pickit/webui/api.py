"""Python<->JS bridge for the modern-UI proof of concept.

Everything here reuses the EXISTING engine (generator.py / api.client) — this
file only adapts it for a web front-end: a js_api object whose methods JS can
call, plus a thread-safe status snapshot that the page polls while a
generation runs. No Tkinter anywhere.
"""

import os
import threading
import time

from exilebot_pickit import generator as gen
from exilebot_pickit.ui.config import OUTPUT_DIR, PRICE_CACHE_DIR, load_config, save_config
from exilebot_pickit.version import VERSION


class PocApi:
    def __init__(self):
        self._lock = threading.Lock()
        self._status = {"running": False, "log": [], "done": None}
        self.cfg = load_config()
        gen.set_disk_cache_dir(PRICE_CACHE_DIR)

    # ── Simple getters the page calls once at load ────────────────────────────

    def app_info(self):
        return {"version": VERSION, "output_dir": OUTPUT_DIR,
                "league": self.cfg.get("league") or "",
                "min_gear": float(self.cfg.get("min_exalt_gear", 0.0)),
                "min_unique": float(self.cfg.get("min_exalt_unique", 0.0))}

    def leagues(self):
        try:
            return [{"name": n, "display": d} for n, _, d in gen.fetch_live_leagues()]
        except Exception as e:
            return {"error": str(e)}

    # ── Generation ────────────────────────────────────────────────────────────

    def _log(self, msg):
        with self._lock:
            self._status["log"].append(msg)

    def status(self):
        """Polled by JS every ~400 ms; returns and drains new log lines."""
        with self._lock:
            out = dict(self._status)
            out["log"] = list(self._status["log"])
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

    def _generate(self, league, min_gear, min_unique):
        t0 = time.time()
        try:
            self._log(f"Fetching live prices for {league}…")
            stale = set()
            payloads = gen.fetch_all_payloads(league, gen.ALL_CATEGORIES, stale_out=stale)

            cur = payloads.get("currency")
            if not isinstance(cur, dict):
                raise RuntimeError("poe.ninja unreachable and no cached prices for this league")
            rate = gen.exalted_rate(cur)
            div_rate = 1.0
            items_by_id = {i["id"]: i for i in cur.get("items", [])}
            for line in cur.get("lines", []):
                it = items_by_id.get(line.get("id"))
                if it and it.get("name") == "Divine Orb":
                    pv = float(line.get("primaryValue") or 0.0)
                    div_rate = pv * rate if rate else pv
                    break

            out = [gen.header_major("Economy Items"), ""]
            active_cats = 0
            for key, _t, label, is_unique in gen.ALL_CATEGORIES:
                p = payloads.get(key)
                if not isinstance(p, dict):
                    self._log(f"✗ {label}: no data")
                    continue
                floor = min_unique if is_unique else min_gear
                if is_unique:
                    lines = gen.build_unique_lines(p, div_rate, min_exalt=floor)
                elif key == "uncut_gems":
                    lines = gen.build_uncut_gem_lines(p, div_rate, min_exalt=floor)
                elif key == "waystones":
                    lines = gen.build_waystone_lines()
                else:
                    pick_all = key in gen.PICK_ALL_CATEGORIES
                    always = (gen.ALWAYS_PICK_CURRENCY if key == "currency"
                              else gen.ALWAYS_PICK_RUNES if key == "runes" else None)
                    lines = gen.build_exchange_lines(p, div_rate, pick_all=pick_all,
                                                     min_exalt=floor,
                                                     tier_sort=(key == "essences"),
                                                     always_names=always)
                out += [gen.header_sub(label), ""] + lines + [""]
                active_cats += 1
                self._log(f"✓ {label}")

            out += gen.STATIC_TABLET_RULES.splitlines()
            out += gen.STATIC_WOMBGIFT_RULES.splitlines()
            out += gen.STATIC_SPECIAL_WAYSTONE_RULES.splitlines()
            out += gen.build_chance_base_rules()
            out += ["", gen.header_major("Base Types"), ""] + gen.build_base_rules()

            os.makedirs(OUTPUT_DIR, exist_ok=True)
            path = os.path.join(OUTPUT_DIR, "poe2_pickit_modern_poc.ipd")
            gen.write_text_atomic(path, "\n".join(out))

            active = sum(1 for l in out if l and not l.startswith("//") and "[StashItem]" in l)
            commented = sum(1 for l in out if l.startswith("//") and "[StashItem]" in l)
            self.cfg.update({"league": league, "min_exalt_gear": min_gear,
                             "min_exalt_unique": min_unique})
            save_config(self.cfg)
            with self._lock:
                self._status["running"] = False
                self._status["done"] = {
                    "ok": True, "path": path, "active": active, "commented": commented,
                    "cats": active_cats, "stale": len(stale),
                    "divine_rate": round(div_rate, 1),
                    "secs": round(time.time() - t0, 1),
                }
        except Exception as e:
            with self._lock:
                self._status["running"] = False
                self._status["done"] = {"ok": False, "error": str(e)}

    def open_output(self):
        try:
            os.startfile(OUTPUT_DIR)   # noqa: S606 — local folder open, Windows only
            return {"ok": True}
        except Exception as e:
            return {"error": str(e)}
