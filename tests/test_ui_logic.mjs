// Behaviour tests for the pure logic inside webui/app.html.
//
// app.html is one big file, and its JS is only checked for SYNTAX by tools/check_ui.py —
// never for whether the math is right. That gap is why bugs like the floor being 58x off,
// or the Preview "jump to rule" silently missing, reached users. This harness pulls the
// REAL functions out of app.html (not a copy) and runs them under Node with the few
// globals they need mocked, so their behaviour is verified in CI.
//
// Run:  node tests/test_ui_logic.mjs
import fs from "node:fs";
import path from "node:path";
import vm from "node:vm";
import assert from "node:assert/strict";
import { fileURLToPath } from "node:url";

const ROOT = path.dirname(path.dirname(fileURLToPath(import.meta.url)));
const html = fs.readFileSync(
  path.join(ROOT, "src", "exilebot_pickit", "webui", "app.html"), "utf8");
const script = html.match(/<script[^>]*>([\s\S]*)<\/script>/)[1];

// Pull one top-level function/const definition out of the script by name, brace-matched.
// Skips braces inside '...', "...", `...` and // comments so string/regex/template content
// can't fool the counter.
function pull(name) {
  let i = script.search(new RegExp(`(^|\\n)\\s*(function\\s+${name}\\b|const\\s+${name}\\s*=)`));
  assert.ok(i >= 0, `function ${name} not found in app.html`);
  i = script.indexOf(name, i);
  // arrow const with no block body -> take to the terminating semicolon
  const head = script.slice(i, script.indexOf("\n", i));
  const isBlock = script.slice(i, i + 400).includes("{");
  if (!isBlock || /=>\s*[^\{]/.test(head)) {
    const end = script.indexOf(";", i);
    return script.slice(script.lastIndexOf(name === "" ? "" : "", i), end + 1);
  }
  const start = script.lastIndexOf(name.startsWith("function") ? "function" : "", i);
  const from = script.lastIndexOf("function", i) >= 0 &&
               script.slice(script.lastIndexOf("function", i), i).match(/^function\s+\w*$/)
    ? script.lastIndexOf("function", i) : i;
  // walk from the first "{" after the name, brace-matching
  let j = script.indexOf("{", i), depth = 0, q = null, prev = "";
  for (; j < script.length; j++) {
    const c = script[j];
    if (q) {                       // inside a string/template
      if (c === q && prev !== "\\") q = null;
    } else if (c === "'" || c === '"' || c === "`") {
      q = c;
    } else if (c === "/" && script[j + 1] === "/") {
      j = script.indexOf("\n", j);
    } else if (c === "{") {
      depth++;
    } else if (c === "}") {
      if (--depth === 0) { j++; break; }
    }
    prev = c;
  }
  return script.slice(from, j);
}

// `pull` can't see `async function f(){...}` (its regex expects `function` right after the
// newline). These fixes live in async functions, so brace-match them directly.
function pullFn(name) {
  const m = script.match(new RegExp(`(^|\\n)\\s*(?:async\\s+)?function\\s+${name}\\s*\\(`));
  assert.ok(m, `function ${name} not found in app.html`);
  const kw = script.indexOf("function", m.index);
  const from = script.startsWith("async", kw - 6) ? kw - 6 : kw;   // keep the `async `
  let j = script.indexOf("{", script.indexOf("(", kw)), depth = 0, q = null, prev = "";
  for (; j < script.length; j++) {
    const c = script[j];
    if (q) { if (c === q && prev !== "\\") q = null; }
    else if (c === "'" || c === '"' || c === "`") q = c;
    else if (c === "/" && script[j + 1] === "/") j = script.indexOf("\n", j);
    else if (c === "{") depth++;
    else if (c === "}" && --depth === 0) { j++; break; }
    prev = c;
  }
  return script.slice(from, j);
}

// A DOM element stub good enough for the code under test to write into.
const mkEl = () => ({ value: "", textContent: "", innerHTML: "", title: "", style: {},
  classList: { add() {}, remove() {}, toggle() {}, contains: () => false } });

// Build a sandbox with the given globals, define the named functions in it, return it.
function load(names, globals = {}) {
  const ctx = vm.createContext({ Math, ...globals });
  for (const n of names) vm.runInContext(pull(n), ctx);
  return ctx;
}

let passed = 0;
function test(label, fn) {
  fn();
  passed++;
  console.log("  ok  " + label);
}

// ── pvRuleKey: rule identity, ignoring the drifting "// ExValue = ..." comment ──────────
{
  const c = load(["pvRuleKey"]);
  const key = c.pvRuleKey;
  test("pvRuleKey strips the ExValue comment so a price change still matches", () => {
    const today = '[Type] == "Divine Orb" # [StashItem] == "true" // ExValue = 503.80';
    const older = '[Type] == "Divine Orb" # [StashItem] == "true" // ExValue = 421.10';
    assert.equal(key(today), key(older));
    assert.equal(key(today), '[Type] == "Divine Orb" # [StashItem] == "true"');
  });
  test("pvRuleKey treats a commented-out (skipped) rule as the same rule", () => {
    const active = '[Type] == "Big Sword" && [StashItem] == "true" // ExValue = 9';
    const skipped = '// [Type] == "Big Sword" && [StashItem] == "true" // ExValue = 9';
    assert.equal(key(active), key(skipped));
  });
  test("pvRuleKey handles empty / null safely", () => {
    assert.equal(key(""), "");
    assert.equal(key(null), "");
  });
}

// ── sparkSvg: the 7-day trend line ──────────────────────────────────────────────────────
{
  const c = load(["sparkSvg"]);
  const svg = c.sparkSvg;
  test("sparkSvg needs at least two points", () => {
    assert.equal(svg([], 1), "");
    assert.equal(svg([5], 1), "");
    assert.equal(svg(null, 1), "");
  });
  test("sparkSvg draws one path point per data point", () => {
    const out = svg([0, -1, -4, -2], -1);
    assert.equal((out.match(/[ML]\d/g) || []).length, 4);   // M + 3×L
    assert.ok(out.includes("var(--err)"));                  // dir<0 → red
  });
  test("sparkSvg puts a flat line at mid-height, not at the top or bottom", () => {
    const out = svg([3, 3, 3], 0);
    assert.ok(out.includes("7.0"));            // H/2 with H=14
    assert.ok(out.includes("var(--dim)"));     // dir 0 → neutral
  });
}

// ── wnMd: the What's-New markdown renderer (literal *asterisks* reached users once) ──────
{
  const c = load(["wnMd"]);
  const md = c.wnMd;
  test("wnMd renders headings, bold and italic — no raw markdown left", () => {
    const out = md("## Fixed\n**big** and *small*");
    assert.ok(out.includes("<h3>Fixed</h3>"));
    assert.ok(out.includes("<b>big</b>"));
    assert.ok(out.includes("<i>small</i>"));
    assert.ok(!out.includes("**") && !/(^|[^<])\*small/.test(out));
  });
  test("wnMd escapes HTML in the notes", () => {
    assert.ok(md("a <script> b").includes("&lt;script&gt;"));
  });
}

// ── subCalc + floorMax: the floor reference and slider ceiling (the 58x-bug family) ──────
{
  // subCalc reads $(id).value and writes $(id).textContent; mock $ with an element store.
  function makeCtx(chaosEx, divRate, amount) {
    const els = { amt: { value: String(amount) }, sub: { textContent: "" } };
    return { els, ctx: load(["subCalc", "floorMax"],
      { $: (id) => els[id], chaosEx, divRate }) };
  }
  test("subCalc shows chaos always, divine only once it's readable (>=0.1 div)", () => {
    const { els, ctx } = makeCtx(58, 424, 25);   // 25 ex
    ctx.subCalc("amt", "sub", "everything");
    assert.ok(els.sub.textContent.includes("0.43 chaos"));
    assert.ok(!els.sub.textContent.includes("div"));   // 25/424 = 0.06 < 0.1 → hidden
  });
  test("subCalc adds divine on a big floor", () => {
    const { els, ctx } = makeCtx(58, 424, 200);
    ctx.subCalc("amt", "sub", "everything");
    assert.ok(els.sub.textContent.includes("chaos") && els.sub.textContent.includes("div"));
  });
  test("subCalc says 'picking up everything' at a zero floor", () => {
    const { els, ctx } = makeCtx(58, 424, 0);
    assert.equal(ctx.subCalc("amt", "sub", "everything"), 0);
    assert.ok(els.sub.textContent.toLowerCase().includes("picking up everything"));
  });
  test("floorMax is one divine when the rate is loaded, else the 100 ex fallback", () => {
    assert.equal(load(["floorMax"], { divRate: 424 }).floorMax(), 424);
    assert.equal(load(["floorMax"], { divRate: 0 }).floorMax(), 100);
  });
}

// ── TAB_ORDER: Ctrl+1..0 must select the tab at that position in the sidebar ─────────────
{
  const navOrder = [...html.matchAll(/class="nav-btn[^"]*"\s+data-p="([a-z]+)"/g)].map(m => m[1]);
  const expr = script.match(/const TAB_ORDER=([\s\S]*?);\r?\n/)[1];
  const ctx = vm.createContext({
    document: { querySelectorAll: () => navOrder.map(p => ({ dataset: { p } })) } });
  const TAB_ORDER = vm.runInContext(expr, ctx);

  test("TAB_ORDER is read off the sidebar, never a hand-copied list", () => {
    assert.ok(/querySelectorAll/.test(expr),
      "TAB_ORDER must be derived from the nav markup — a hardcoded copy drifts");
    assert.ok(navOrder.length >= 10);
  });
  test("Ctrl+N opens the Nth sidebar tab (the omitted-'mypk' off-by-one)", () => {
    assert.equal(navOrder[3], "mypk");        // 4th thing you see = Create your filter
    assert.equal(TAB_ORDER[3], "mypk");       // …so Ctrl+4 must open it, not History
    for (let i = 0; i < TAB_ORDER.length; i++) assert.equal(TAB_ORDER[i], navOrder[i]);
    assert.equal(TAB_ORDER.length, 10);       // Ctrl+1..9 + Ctrl+0
  });
}

// ── applyAutoFloor: the slider FILLS must follow the numbers it writes ───────────────────
{
  const els = {};
  const $ = (id) => (els[id] ||= mkEl());
  let tracks = 0;
  const ctx = vm.createContext({ Math, $, updTracks: () => tracks++,
    uEx: () => 12, gEx: () => 34,
    api: () => ({ set_setting: async () => ({ ok: true }),
      suggest_floors: async () => ({ unique: 12, gear: 34, keep_pct: 40,
        kept_unique: 1, total_unique: 2, kept_gear: 3, total_gear: 4 }) }) });
  vm.runInContext(pullFn("applyAutoFloor"), ctx);
  await ctx.applyAutoFloor();

  test("applyAutoFloor redraws the drag-track fills, not just the numbers", () => {
    assert.equal(els.uAmt.value, 12);
    assert.equal(els.gAmt.value, 34);
    assert.ok(tracks >= 1, "updTracks() never ran — sliders freeze beside a live number");
  });
}

// ── _loadEco: the 250ms poll interval must die on every exit path ────────────────────────
// The old loop awaited the bridge BEFORE clearInterval, so one bad poll orphaned the timer
// AND hung the promise: "Loading prices…" forever, plus a new immortal timer per visit.
{
  const run = async (poll) => {
    const els = {}, liveTimers = new Set();
    els.league = mkEl(); els.league.value = "Fate of the Vaal";
    const ctx = vm.createContext({
      Math, $: (id) => (els[id] ||= mkEl()), eco: null, ecoCat: null, ecoUnit: "ex", chaosEx: 0,
      setDivRate() {}, renderChips() {}, renderEco() {},
      api: () => ({ economy_start: async () => ({ ok: true }), economy_poll: poll,
        chaos_ex: async () => ({ ex: 0 }) }),
      setInterval: (fn, ms) => { const h = setInterval(fn, ms); liveTimers.add(h); return h; },
      clearInterval: (h) => { liveTimers.delete(h); clearInterval(h); } });
    vm.runInContext(pullFn("_loadEco"), ctx);
    await ctx._loadEco();                      // must RESOLVE — hanging here is the bug
    return { els, liveTimers, eco: ctx.eco };
  };

  const thrown = await run(async () => { throw new Error("bridge died"); });
  test("a rejected economy_poll clears its interval and reports a retryable error", () => {
    assert.equal(thrown.liveTimers.size, 0, "the 250ms poll interval leaked");
    assert.equal(thrown.eco, null, "eco must stay null so re-opening the tab retries");
    assert.ok(/bridge died/.test(thrown.els.ecoInfo.textContent));
    assert.ok(/Refresh prices/.test(thrown.els.ecoInfo.textContent));
  });

  const empty = await run(async () => undefined);
  test("an undefined economy_poll clears its interval instead of hanging forever", () => {
    assert.equal(empty.liveTimers.size, 0, "the 250ms poll interval leaked");
    assert.equal(empty.eco, null);
    assert.ok(empty.els.ecoInfo.textContent.startsWith("✗"));
  });

  const noResult = await run(async () => ({ running: false, result: null }));
  test("a finished-but-empty price load still ends the loop with an error", () => {
    assert.equal(noResult.liveTimers.size, 0);
    assert.equal(noResult.eco, null);
    assert.ok(/without returning any prices/.test(noResult.els.ecoInfo.textContent));
  });
}

// ── the profile dropdown's blank entry must not pretend to be an action ──────────────────
{
  test("'— no profile —' is disabled (the bridge has no way to clear active_profile)", () => {
    // Two copies exist: the initial markup and the one loadProfiles() rebuilds.
    const opts = [...html.matchAll(/<option value=""([^>]*)>— no profile —<\/option>/g)];
    assert.equal(opts.length, 2, "expected the markup + the loadProfiles() rebuild");
    for (const o of opts)
      assert.ok(/\bdisabled\b/.test(o[1]),
        "the placeholder must be disabled — selecting it did nothing and snapped back");
  });
}

console.log(`\n${passed} UI-logic checks passed`);
