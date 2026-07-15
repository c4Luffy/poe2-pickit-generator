#!/usr/bin/env python3
"""Static safety gate for webui/app.html — the single-file UI.

app.html is one ~3,600-line file of HTML + CSS + JS. A single missing element id, a JS
syntax error, or a dropped <head> kills the *entire* app (symptom: league dropdown stuck
on "Loading…", blank version label). None of that is caught by pytest or ruff, so this
runs in CI as its own gate.

Checks (exit 1 on any failure):
  0. document structure — DOCTYPE, html/head/title/body, balanced <style> + CSS braces
  1. JS syntax          — `node --check` on the app's <script> body
  2. id audit           — every $("id") resolves to exactly one id="..."; no duplicates
  3. bridge audit       — every api().method has a matching `def` in webui/api.py
  4. orphan-class        — classes used in markup with no CSS rule (warning, not failure)

Run:  python tools/check_ui.py
"""
from __future__ import annotations

import os
import re
import shutil
import subprocess
import sys
from collections import Counter

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
APP = os.path.join(ROOT, "src", "exilebot_pickit", "webui", "app.html")
API = os.path.join(ROOT, "src", "exilebot_pickit", "webui", "api.py")

# classes only ever toggled from JS (never styled directly) — not orphans
JS_HOOKS = {"frac-copy", "rare-copy", "rare-slot-sw", "bak-r", "hdet", "hrerun",
            "on", "l-a", "l-c"}


def main() -> int:
    h = open(APP, encoding="utf-8").read()
    apisrc = open(API, encoding="utf-8").read()
    fail: list[str] = []

    # 0) document structure
    struct = []
    if not h.lstrip().startswith("<!DOCTYPE"):
        struct.append("missing <!DOCTYPE>")
    if not h.rstrip().endswith("</html>"):
        struct.append("does not end with </html>")
    for tag in ("html", "head", "title", "body"):
        if f"<{tag}" not in h.lower() or f"</{tag}>" not in h.lower():
            struct.append(f"missing <{tag}> or </{tag}>")
    if h.count("<style") != h.count("</style>"):
        struct.append("unbalanced <style>")
    css_all = "".join(re.findall(r"<style[^>]*>(.*?)</style>", h, re.S))
    if css_all.count("{") != css_all.count("}"):
        struct.append(f"CSS braces unbalanced ({css_all.count('{')} open / "
                      f"{css_all.count('}')} close)")
    if struct:
        fail.append("DOCUMENT STRUCTURE: " + "; ".join(struct))
    else:
        print("structure : OK (doctype, html/head/title/body, style + css braces balanced)")

    # 1) JS syntax via node --check on the largest <script> body (the app script)
    scripts = re.findall(r"<script[^>]*>(.*?)</script>", h, re.S)
    body = max(scripts, key=len) if scripts else ""
    if not shutil.which("node"):
        print("node --check: SKIPPED (node not installed) — install Node.js to run this check")
    else:
        tmp = os.path.join(os.path.dirname(APP), "_uicheck_tmp.js")
        try:
            with open(tmp, "w", encoding="utf-8") as f:
                f.write(body)
            r = subprocess.run(["node", "--check", tmp], capture_output=True, text=True)
            if r.returncode != 0:
                fail.append("JS node --check FAILED:\n" + (r.stderr or r.stdout))
            else:
                print(f"node --check: OK ({len(body)} chars of JS)")
        finally:
            if os.path.exists(tmp):
                os.remove(tmp)

    # 2) id audit
    ids_defined = re.findall(r'\bid="([^"]+)"', h)
    dup = [k for k, v in Counter(ids_defined).items() if v > 1]
    if dup:
        fail.append("DUPLICATE id= attributes: " + ", ".join(dup))
    used = set(re.findall(r'\$\("([^"]+)"\)', body))
    missing = sorted(used - set(ids_defined))
    if missing:
        fail.append('$("id") with NO matching id=: ' + ", ".join(missing))
    print(f"id audit  : {len(set(ids_defined))} defined, {len(used)} referenced, "
          f"{len(missing)} missing, {len(dup)} dup")

    # 3) bridge audit — every api().method exists in api.py
    called = set(re.findall(r"api\(\)\.([a-zA-Z_]\w*)", body))
    apidefs = set(re.findall(r"^\s*def ([a-zA-Z_]\w*)\(", apisrc, re.M))
    phantom = sorted(called - apidefs)
    if phantom:
        fail.append("api() call with NO bridge method: " + ", ".join(phantom))
    print(f"bridge    : {len(called)} called, {len(phantom)} missing")

    # 4) orphan-class audit (warning only — some classes are dynamic)
    css = "\n".join(re.findall(r"<style[^>]*>(.*?)</style>", h, re.S))
    css_classes = set(re.findall(r"\.([A-Za-z_][\w-]*)", css))
    markup_classes: set[str] = set()
    for chunk in re.findall(r'class="([^"]+)"', h):
        markup_classes.update(chunk.split())
    orphans = sorted(c for c in markup_classes
                     if c not in css_classes and c not in JS_HOOKS
                     and "${" not in c and not c.startswith("l-"))
    print("orphan    : " + ("none" if not orphans
                            else "WARN (in markup, no CSS rule): " + ", ".join(orphans)))

    print()
    if fail:
        print("FAIL:\n- " + "\n- ".join(fail))
        return 1
    print("ALL CHECKS PASSED")
    return 0


if __name__ == "__main__":
    sys.exit(main())
