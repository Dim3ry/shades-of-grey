#!/usr/bin/env python3
"""lint_recipes_tips.py: applies the content rules of George's tests/test_v32.py (detail recipes) and tests/test_v33.py
(basing tips) to our new entries, without starting a browser.

How to run it (python3 and node, nothing to install):
    python3 -I lint_recipes_tips.py                      # new entries in ../data (k3, k4) against the repo two folders up
    python3 -I lint_recipes_tips.py --data DIR           # k3-detail-recipes.json / k4-basing-tips.json, or detail-recipes.json /
                                                         #   basing-tips.json (the compile4/final names), in DIR
    python3 -I lint_recipes_tips.py --source app         # every entry in the repo's detail-recipes.js and basing-tips.js as they
                                                         #   are now, plus the whole-file scans (run after kb_import.py)
    python3 -I lint_recipes_tips.py --source main        # George's original 18 recipes and 12 tips (git show main:...)
    --repo PATH   the app repo (default: the repo this script sits in, two folders up)
    --quiet       print only the totals
    --phrase TEXT [TEXT ...]   try wordings against the paint, brand, product-word, Games Workshop and plain-text rules

Where the rules come from (nothing is hand-copied that can be read):
  - KNOWN_PAINTS, COMMON_BRANDS, DEFAULT_TECHNIQUES: evaluated by Node from the repo's app.js (the part from
    "const V15_TECHNIQUES" up to "----- v48: Paint brands", which builds KNOWN_PAINTS from both paint tables).
  - GW_WORDS, GW_MORE (tests/test_v31.py), BRAND_WORDS (tests/test_v33.py), the two colour_words lists (inside main() of
    test_v32 and test_v33) and sentences(): read from the test files with Python's ast module.
  - The numeric limits, field sets, regexes and groups below are written out with the test line they come from.
Not checked (whole-list counts George hard-codes and will update): 18 recipes / 12 tips, at least two per group,
the REQUIRED subject words, "at least 10 of the 12 tips have paint steps" (reported as a ratio instead).
The on-screen scans in section 3 of both tests are covered by the data scans, except text the app adds itself.

Exit code 0: no violations. 1: violations. 2: could not read something.
"""
import ast
import json
import os
import re
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))

# ---------- reading the rules from the repo ----------

NODE_PAINTS = r"""
const fs = require("fs"), vm = require("vm");
const src = fs.readFileSync(process.argv[1], "utf8");
const a = src.indexOf("const V15_TECHNIQUES"), b = src.indexOf("// ----- v48: Paint brands (Settings) -----");
if (a < 0 || b < 0 || b < a) { console.error("app.js: could not find the paint tables"); process.exit(2); }
const out = vm.runInNewContext(src.slice(a, b) + "\n;({ known: KNOWN_PAINTS.map(k => [k.name, k.brand]), brands: COMMON_BRANDS, techniques: DEFAULT_TECHNIQUES })", {});
process.stdout.write(JSON.stringify(out));
"""

NODE_DATA = r"""
const vm = require("vm");
let src = ""; process.stdin.on("data", d => src += d).on("end", () => {
  const names = process.argv[1].split(",");
  const out = vm.runInNewContext(src + "\n;({ groups: " + names[0] + ", items: " + names[1] + " })", {});
  process.stdout.write(JSON.stringify(out));
});
"""


def node(code, args, stdin=None):
    r = subprocess.run(["node", "-e", code] + args, input=stdin, capture_output=True, text=True)
    if r.returncode:
        sys.exit(f"node failed: {r.stderr.strip()}")
    return json.loads(r.stdout)


def test_tree(path):
    return ast.parse(open(path, encoding="utf-8").read(), path)


def module_regex(tree, name):
    """NAME = re.compile(r"...", re.I) at the top of a test file."""
    for n in tree.body:
        if isinstance(n, ast.Assign) and any(isinstance(t, ast.Name) and t.id == name for t in n.targets):
            call = n.value
            flags = 0
            for f in call.args[1:]:
                if isinstance(f, ast.Attribute) and f.attr in ("I", "IGNORECASE"):
                    flags |= re.I
            return re.compile(call.args[0].value, flags)
    raise SystemExit(f"{name} not found")


def colour_words(tree):
    """colour_words = set("...".split()) inside main()."""
    for n in ast.walk(tree):
        if isinstance(n, ast.Assign) and any(isinstance(t, ast.Name) and t.id == "colour_words" for t in n.targets):
            return set(n.value.args[0].func.value.value.split())
    raise SystemExit("colour_words not found")


def sentences_func(tree):
    """sentences(text) from test_v31.py, compiled from its own source."""
    for n in tree.body:
        if isinstance(n, ast.FunctionDef) and n.name == "sentences":
            ns = {"re": re}
            exec(compile(ast.Module(body=[n], type_ignores=[]), "test_v31.py", "exec"), ns)
            return ns["sentences"]
    raise SystemExit("sentences() not found")


def load_rules(repo):
    tests = os.path.join(repo, "tests")
    t31, t32, t33 = (test_tree(os.path.join(tests, f)) for f in ("test_v31.py", "test_v32.py", "test_v33.py"))
    paints = node(NODE_PAINTS, [os.path.join(repo, "app.js")])
    return {
        "GW_WORDS": module_regex(t31, "GW_WORDS"), "GW_MORE": module_regex(t31, "GW_MORE"),
        "BRAND_WORDS": module_regex(t33, "BRAND_WORDS"),
        "colour32": colour_words(t32), "colour33": colour_words(t33),
        "sentences": sentences_func(t31),
        "known": paints["known"], "brands": paints["brands"], "techniques": paints["techniques"],
    }


# ---------- reading the entries ----------

def from_js(text, names):
    return node(NODE_DATA, [",".join(names)], stdin=text)


def load_entries(source, repo, data):
    """Returns (recipes, tips, recipe_groups, tip_groups, file texts or None)."""
    def js(name, ref):
        if ref == "main":
            r = subprocess.run(["git", "-C", repo, "show", "main:" + name], capture_output=True, text=True)
            if r.returncode:
                sys.exit(r.stderr)
            return r.stdout
        return open(os.path.join(repo, name), encoding="utf-8").read()

    det_text, bas_text = js("detail-recipes.js", source), js("basing-tips.js", source)
    det = from_js(det_text, ["DETAIL_GROUPS", "DETAIL_RECIPES"])
    bas = from_js(bas_text, ["BASING_GROUPS", "BASING_TIPS"])
    if source in ("app", "main"):
        return det["items"], bas["items"], det["groups"], bas["groups"], (det_text, bas_text)

    def pick(*names):
        for n in names:
            p = os.path.join(data, n)
            if os.path.exists(p):
                return json.load(open(p, encoding="utf-8"))
        sys.exit(f"none of {names} in {data}")
    recipes = pick("k3-detail-recipes.json", "detail-recipes.json")["detail-recipes"]
    tips = pick("k4-basing-tips.json", "basing-tips.json")["basing-tips"]
    return recipes, tips, det["groups"], bas["groups"], None


# ---------- the rules ----------

PLAIN = re.compile(r"[A-Za-z0-9 ',.\-]+")         # v32 line 178, v33 line 200
HEX = re.compile(r"#[0-9a-f]{6}")                    # v32 line 157, v33 line 180
STEP_FIELDS = {"technique", "coats", "mix", "look", "hex", "note"}   # v32 line 152, v33 line 174
TIP_FIELDS = {"key", "group", "name", "summary", "materials", "howto", "paintSteps"}   # v33 line 163
THIN = ("Wash", "Shade", "Glaze")                    # v32 line 155, v33 line 177


def paint_hits(text, R, words):
    """v32 lines 171-172 / v33 lines 193-194: a built-in paint name of 6+ characters with at least one word that is not a
    plain colour word, found as a whole phrase anywhere in the entry's JSON."""
    key = id(words)
    if key not in _ELIGIBLE:   # the same filter as the test, done once; each name keeps its words for a quick pre-check
        _ELIGIBLE[key] = [(name, set(re.findall(r"[a-z0-9]+", name.lower()))) for name, _brand in R["known"]
                          if len(name) >= 6 and any(w not in words for w in re.findall(r"[a-z']+", name.lower()))]
    present = set(re.findall(r"[a-z0-9]+", text.lower()))
    out = []
    for name, name_words in _ELIGIBLE[key]:
        # pre-check only skips names with a word missing from the text; the match itself is the test's own regex
        if name_words <= present and re.search(r"\b" + re.escape(name) + r"\b", text, re.I):
            out.append(name)
    return sorted(set(out))


_ELIGIBLE = {}


def brand_hits(text, R):
    return [b for b in R["brands"] if re.search(r"\b" + re.escape(b) + r"\b", text, re.I)]


def gw_hits(text, R):
    return R["GW_WORDS"].findall(text) + R["GW_MORE"].findall(text)


def lint_recipe(r, R, groups):
    v = []
    add = lambda field, why: v.append((r.get("key", "?"), field, why))
    if set(r) - {"key", "group", "name", "summary", "steps"} or not {"key", "group", "name", "summary", "steps"} <= set(r):
        add("fields", f"unexpected fields {sorted(set(r))}")
    if r.get("group") not in [g["key"] for g in groups]:
        add("group", f"unknown group {r.get('group')!r}")
    steps = r.get("steps", [])
    if not 3 <= len(steps) <= 4:                                                         # v32 line 150
        add("steps", f"{len(steps)} steps (3 or 4 allowed)")
    if not re.fullmatch(r"[A-Za-z' -]{4,40}", r.get("name", "")):                       # v32 line 162
        add("name", f"must match [A-Za-z' -]{{4,40}}: {r.get('name')!r}")
    for field in ("name", "summary"):                                                    # v32 line 178
        if not PLAIN.fullmatch(r.get(field, "")):
            add(field, f"not plain text (letters, digits, space ' , . - only): {bad_chars(r.get(field, ''))}")
    for i, s in enumerate(steps, 1):
        f = f"steps[{i}]"
        if set(s) != STEP_FIELDS:
            add(f, f"fields must be exactly {sorted(STEP_FIELDS)}")
            continue
        if s["technique"] not in R["techniques"]:                                         # v32 line 154
            add(f + ".technique", f"not an app technique: {s['technique']!r}")
        if not (isinstance(s["coats"], int) and 1 <= s["coats"] <= 3 and isinstance(s["mix"], int) and 1 <= s["mix"] <= 100):
            add(f, f"coats 1-3 and mix 1-100 as whole numbers (coats {s['coats']!r}, mix {s['mix']!r})")   # v32 line 156
        if (s["mix"] < 100) != (s["technique"] in THIN):                                   # v32 line 158
            add(f + ".mix", f"{s['technique']} with mix {s['mix']} (only Wash, Shade, Glaze are under 100)")
        if not (s["look"].strip() and HEX.fullmatch(s["hex"])):                            # v32 line 157
            add(f + ".hex", f"look empty or hex not #rrggbb: {s['look']!r} {s['hex']!r}")
        n = R["sentences"](s["note"])
        if len(n) != 1:                                                                     # v32 line 160
            add(f + ".note", f"{len(n)} sentences (one allowed): {s['note']!r}")
        if not 0 < len(s["note"]) <= 100:
            add(f + ".note", f"{len(s['note'])} characters (1 to 100 allowed): {s['note']!r}")
        if len(s["look"]) > 30:
            add(f + ".look", f"{len(s['look'])} characters (30 allowed)")
        if not PLAIN.fullmatch(s["look"] + " " + s["note"]):                              # v32 line 178
            add(f + ".note", f"not plain text: {bad_chars(s['look'] + ' ' + s['note'])} in {s['note']!r}")
    if len({s.get("hex") for s in steps}) != len(steps):                                   # v32 line 158
        add("steps", "two steps share a hex colour")
    text = json.dumps(r)                                                                    # v32 line 168: data_text
    for p in paint_hits(text, R, R["colour32"]):
        add(where(r, p), f"built-in paint name {p!r}")
    for b in brand_hits(text, R):
        add(where(r, b), f"paint brand {b!r}")
    if re.search(r"[<>&`]", text):                                                          # v32 line 176
        add("text", "contains < > & or `")
    for h in gw_hits(text, R):                                                               # v32 line 186
        add(where(r, h), f"Games Workshop word {h!r}")
    return v


def lint_tip(x, R, groups):
    v = []
    add = lambda field, why: v.append((x.get("key", "?"), field, why))
    if set(x) != TIP_FIELDS:                                                                 # v33 line 163
        add("fields", f"fields must be exactly {sorted(TIP_FIELDS)}, got {sorted(set(x))}")
        return v
    if x["group"] not in [g["key"] for g in groups]:
        add("group", f"unknown group {x['group']!r}")
    if not 3 <= len(x["materials"]) <= 6:                                                    # v33 line 165
        add("materials", f"{len(x['materials'])} materials (3 to 6 allowed)")
    if not 3 <= len(x["howto"]) <= 5:
        add("howto", f"{len(x['howto'])} how-to steps (3 to 5 allowed)")
    if not 0 <= len(x["paintSteps"]) <= 5:
        add("paintSteps", f"{len(x['paintSteps'])} paint steps (0 to 5 allowed)")
    for i, m in enumerate(x["materials"], 1):                                                 # v33 line 169
        if not (0 < len(m) <= 70 and "\n" not in m and not m.endswith(".")):
            add(f"materials[{i}]", f"must be 1-70 characters, one line, no closing full stop ({len(m)}): {m!r}")
    if len(set(x["materials"])) != len(x["materials"]):
        add("materials", "two materials are the same")
    for i, h in enumerate(x["howto"], 1):                                                     # v33 line 172
        n = R["sentences"](h)
        if len(n) != 1:
            add(f"howto[{i}]", f"{len(n)} sentences (one allowed): {h!r}")
        if not 0 < len(h) <= 120:
            add(f"howto[{i}]", f"{len(h)} characters (120 allowed): {h!r}")
        if not h.endswith("."):
            add(f"howto[{i}]", f"does not end with a full stop: {h!r}")
    for i, s in enumerate(x["paintSteps"], 1):
        f = f"paintSteps[{i}]"
        if set(s) != STEP_FIELDS:                                                              # v33 line 176
            add(f, f"fields must be exactly {sorted(STEP_FIELDS)}")
            continue
        if (s["mix"] < 100) != (s["technique"] in THIN):                                       # v33 line 177
            add(f + ".mix", f"{s['technique']} with mix {s['mix']} (only Wash, Shade, Glaze are under 100)")
        if not (s["look"].strip() and HEX.fullmatch(s["hex"])):                                # v33 line 180
            add(f + ".hex", f"look empty or hex not #rrggbb: {s['look']!r} {s['hex']!r}")
        if not PLAIN.fullmatch(s["look"] + " " + s["note"]):                                  # v33 line 200
            add(f + ".note", f"not plain text: {bad_chars(s['look'] + ' ' + s['note'])} in {s['note']!r}")
    if len({s.get("hex") for s in x["paintSteps"]}) != len(x["paintSteps"]):                   # v33 line 181
        add("paintSteps", "two paint steps share a hex colour")
    if not re.fullmatch(r"[A-Za-z' -]{3,40}", x["name"]):                                       # v33 line 182
        add("name", f"must match [A-Za-z' -]{{3,40}}: {x['name']!r}")
    for field in ("name", "summary"):                                                          # v33 line 198
        if not PLAIN.fullmatch(x[field]):
            add(field, f"not plain text: {bad_chars(x[field])}")
    for field in ("materials", "howto"):
        for i, t in enumerate(x[field], 1):
            if not PLAIN.fullmatch(t):
                add(f"{field}[{i}]", f"not plain text: {bad_chars(t)} in {t!r}")
    text = json.dumps(x)                                                                        # v33 line 184: data_text
    for p in paint_hits(text, R, R["colour33"]):
        add(where(x, p), f"built-in paint name {p!r}")
    for b in brand_hits(text, R):
        add(where(x, b), f"paint brand {b!r}")
    for b in R["BRAND_WORDS"].findall(text):                                                    # v33 line 197
        add(where(x, b), f"brand or product word {b!r}")
    for h in gw_hits(text, R):                                                                   # v33 line 210
        add(where(x, h), f"Games Workshop word {h!r}")
    return v


def bad_chars(t):
    return "".join(sorted({c for c in t if not PLAIN.fullmatch(c)})) or "(empty)"


def where(entry, phrase):
    """The field a phrase was found in, for the message."""
    pat = re.compile(r"\b" + re.escape(phrase) + r"\b", re.I)
    def walk(o, path):
        if isinstance(o, dict):
            for k, val in o.items():
                yield from walk(val, f"{path}.{k}" if path else k)
        elif isinstance(o, list):
            for i, val in enumerate(o, 1):
                yield from walk(val, f"{path}[{i}]")
        elif isinstance(o, str) and pat.search(o):
            yield path
    found = list(walk(entry, ""))
    return ",".join(found) if found else "text"


def lint_files(det_text, bas_text, R):
    """v32 line 185 and v33 lines 147-148, 208: the whole data files, apart from comment lines."""
    v = []
    code = lambda t: "\n".join(l for l in t.splitlines() if not l.strip().startswith("//"))
    for name, t in (("detail-recipes.js", det_text), ("basing-tips.js", bas_text)):
        for h in gw_hits(code(t), R):
            v.append((name, "file", f"Games Workshop word {h!r} outside a comment line"))
    if re.search(r"https?:|www\.|\.com\b|\.co\.uk|href", bas_text, re.I):
        v.append(("basing-tips.js", "file", "web address or link"))
    for b in R["BRAND_WORDS"].findall(code(bas_text)):
        v.append(("basing-tips.js", "file", f"brand or product word {b!r} outside a comment line"))
    return v


def main(argv):
    def opt(name, default):
        return argv[argv.index(name) + 1] if name in argv else default
    repo = opt("--repo", os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
    data = opt("--data", os.path.join(HERE, "..", "data"))
    source = opt("--source", "data")
    quiet = "--quiet" in argv
    R = load_rules(repo)
    if "--phrase" in argv:   # try a wording: python3 -I lint_recipes_tips.py --phrase "a grey undercoat" ["another" ...]
        bad = 0
        for t in argv[argv.index("--phrase") + 1:]:
            hits = ([f"paint (v32) {p!r}" for p in paint_hits(json.dumps(t), R, R["colour32"])]
                    + [f"paint (v33) {p!r}" for p in paint_hits(json.dumps(t), R, R["colour33"])]
                    + [f"brand {b!r}" for b in brand_hits(t, R)] + [f"word {b!r}" for b in R["BRAND_WORDS"].findall(t)]
                    + [f"GW {h!r}" for h in gw_hits(t, R)] + ([] if PLAIN.fullmatch(t) else [f"chars {bad_chars(t)}"]))
            bad += bool(hits)
            print(("OK   " if not hits else "BAD  ") + t + ("" if not hits else "  -> " + ", ".join(hits)))
        return 1 if bad else 0
    recipes, tips, rgroups, tgroups, files = load_entries(source, repo, data)
    violations = []
    bad_r, bad_t = set(), set()
    for r in recipes:
        vs = lint_recipe(r, R, rgroups)
        violations += [("recipe",) + x for x in vs]
        if vs:
            bad_r.add(r["key"])
    for x in tips:
        vs = lint_tip(x, R, tgroups)
        violations += [("tip",) + y for y in vs]
        if vs:
            bad_t.add(x["key"])
    if files:
        violations += [("file",) + y for y in lint_files(*files, R)]
    if not quiet:
        for kind, key, field, why in violations:
            print(f"{kind:6} {key:34} {field:28} {why}")
    with_paint = len([x for x in tips if x["paintSteps"]])
    print(f"\nsource={source}  rules from {repo} (KNOWN_PAINTS {len(R['known'])}, COMMON_BRANDS {len(R['brands'])})")
    print(f"recipes: {len(recipes)} checked, {len(bad_r)} with violations")
    print(f"tips:    {len(tips)} checked, {len(bad_t)} with violations; {with_paint} of {len(tips)} have paint steps")
    print(f"violations: {len(violations)}")
    return 1 if violations else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
