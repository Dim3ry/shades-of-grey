#!/usr/bin/env python3
"""check_knowledge.py: checks Minifolio knowledge base data files and reports problems in plain words.

How to run it (plain python3, nothing to install):
    python3 knowledge-base/check_knowledge.py data/k1-colour-basics.json
    python3 knowledge-base/check_knowledge.py knowledge-base/data/*.json detail-recipes.js
    python3 knowledge-base/check_knowledge.py --partial my-chunk.json     (while you work: other chunks' entries may not exist yet)
    python3 knowledge-base/check_knowledge.py --final   my-chunk.json     (before you hand back: sample entries not allowed)

Exit code 0 means clean. Exit code 1 means at least one problem. Exit code 2 means a file could not be read.

Files it understands:
  - JSON files: an object whose keys are kinds ("guides", "starters", "mentor-tips", "detail-recipes", "basing-tips"),
    each holding a list of entries. See SCHEMA.md.
  - The app's own data files (detail-recipes.js, basing-tips.js, mentor-tips.js): read as text, never run.

Where the banned words came from (the same lists the app's own tests use, copied so this works on its own):
  GW_WORDS and GW_MORE: tests/test_v31.py (also used by test_v32, v35, v37, v38, v39, v44)
  BRAND_WORDS: tests/test_v35.py (the same line is in test_v37 and test_v38)
This file only reads the data. It changes nothing.
"""
import json
import os
import re
import sys

# ---------- banned words (copied from the app's tests, see the top of this file) ----------
GW_WORDS = re.compile(r"\b(warhammer|games workshop|citadel|space marines?|ultramarines?|tyranids?|orks?|eldar|necrons?|blood angels?|dark angels?|chaos|imperium|adeptus|astartes|sigmar|40k|age of)\b", re.I)
GW_MORE = re.compile(r"\b(primaris|aeldari|skaven|nurgle|khorne|slaanesh|tzeentch|cadian|ultramar|adepta|sororitas|stormcast|space wolves|"
                     r"grey knights|imperial|hive fleet|waaagh|tau|t'au|kroot|gretchin|dreadnought|bolter|primarch|legion|crusade|"
                     r"macragge|mephiston|abaddon|retributor|leadbelcher|caliban|averland|zandri|rhinox|khemri|nuln|kantor|"
                     r"fists|wolves|ravens|salamanders|iron hands|white scars|imperial fists|raven guard|night lords|word bearers|"
                     r"death guard|thousand sons|world eaters|emperor.?s children|alpha legion|iron warriors|black legion|"
                     r"custodes|mechanicus|skitarii|harlequin|drukhari|ynnari|genestealer|hormagaunt|termagant|carnifex|"
                     r"gloomhaven|lord of the rings|middle.?earth|old world|kill team|necromunda|blood bowl|warcry|"
                     r"games workshop|citadel|warhammer)\b", re.I)
BRAND_WORDS = re.compile(r"\b(citadel|vallejo|army painter|scale ?75|tamiya|games workshop|warhammer|amazon|ebay|etsy|shop|buy|store)\b", re.I)

EM_DASH = "—"
EMOJI = re.compile("[←-⇿⌀-⏿①-➿⤀-⥿⬀-⯿〰〽㊗㊙"
                   "\U0001f000-\U0001faff️‍⃣]")

# ---------- the rules (the same numbers are written out in SCHEMA.md) ----------
KINDS = ["guides", "starters", "mentor-tips", "detail-recipes", "basing-tips"]
CATEGORIES = ["colour-basics", "techniques", "tools-prep", "problems"]
TECHNIQUES = ["Prime", "Base coat", "Contrast", "Layer", "Wash", "Shade", "Glaze", "Dry brush", "Edge highlight",
              "Wet blend", "Stipple", "Sponge", "Airbrush", "Technical", "Texture", "Varnish"]
THIN_TECHNIQUES = ("Wash", "Shade", "Glaze")
ID_FORMAT = re.compile(r"[a-z0-9]+(-[a-z0-9]+)*")
HEX_FORMAT = re.compile(r"#[0-9a-f]{6}")

FIELDS = {
    "guides": ({"key", "category", "title", "summary", "body", "related", "keywords"}, {"credit", "sample"}),
    "starters": ({"key", "text", "targets"}, {"sample"}),
    "mentor-tips": ({"key", "part", "colour", "technique", "advice", "colours"}, {"credit", "sample"}),
    "detail-recipes": ({"key", "group", "name", "summary", "steps"}, {"sample"}),
    "basing-tips": ({"key", "group", "name", "summary", "materials", "howto", "paintSteps"}, {"sample"}),
}
# One key already shared by two of the app's own files today (a detail recipe and a basing tip are both called "mud").
# It is allowed only for that pair. Every new key must be unique across all kinds.
LEGACY_SHARED_KEYS = {"mud": {"detail-recipes", "basing-tips"}}
STEP_FIELDS = {"technique", "coats", "mix", "look", "hex", "note"}

# The app's own group lists. Used when a JS data file is not given; the keys are the ones in the app today.
DEFAULT_GROUPS = {
    "detail-recipes": ["body", "metal", "material", "light"],
    "basing-tips": ["ground", "cold", "plants", "stone"],
    "mentor-tips": ["armour", "eyes", "weapon", "base"],
}
JS_NAMES = {  # the name in the .js file -> (kind, the name of its group list)
    "DETAIL_RECIPES": ("detail-recipes", "DETAIL_GROUPS"),
    "BASING_TIPS": ("basing-tips", "BASING_GROUPS"),
    "MENTOR_TIPS": ("mentor-tips", "MENTOR_PARTS"),
}


# ---------- reading files ----------
def strip_js_comments(src):
    out, i, n = [], 0, len(src)
    while i < n:
        c = src[i]
        if c in "\"'`":
            j = i + 1
            while j < n and src[j] != c:
                j += 2 if src[j] == "\\" else 1
            out.append(src[i:j + 1])
            i = j + 1
        elif src.startswith("//", i):
            while i < n and src[i] != "\n":
                i += 1
        elif src.startswith("/*", i):
            end = src.find("*/", i + 2)
            i = n if end < 0 else end + 2
        else:
            out.append(c)
            i += 1
    return "".join(out)


def js_to_json(text):
    """Turns a plain JS literal (comments, bare keys, trailing commas) into JSON text. Only for the app's data files."""
    tokens, i, n = [], 0, len(text)
    while i < n:
        c = text[i]
        if c == '"':
            j = i + 1
            while j < n and text[j] != '"':
                j += 2 if text[j] == "\\" else 1
            tokens.append(text[i:j + 1])
            i = j + 1
        elif c.isspace():
            i += 1
        elif c.isalpha() or c == "_":
            j = i
            while j < n and (text[j].isalnum() or text[j] == "_"):
                j += 1
            word, k = text[i:j], j
            while k < n and text[k].isspace():
                k += 1
            tokens.append('"' + word + '"' if k < n and text[k] == ":" else word)
            i = j
        else:
            tokens.append(c)
            i += 1
    kept = []
    for idx, t in enumerate(tokens):
        if t == "," and idx + 1 < len(tokens) and tokens[idx + 1] in ("]", "}"):
            continue
        kept.append(t)
    return "".join(kept)


def grab_literal(src, name):
    """Finds 'const NAME = [ ... ];' and returns the bracketed text, or None."""
    m = re.search(r"\bconst\s+" + name + r"\s*=\s*", src)
    if not m:
        return None
    start = m.end()
    opener = src[start]
    closer = "]" if opener == "[" else "}"
    depth, i, n = 0, start, len(src)
    while i < n:
        c = src[i]
        if c == '"':
            i += 1
            while i < n and src[i] != '"':
                i += 2 if src[i] == "\\" else 1
        elif c == opener:
            depth += 1
        elif c == closer:
            depth -= 1
            if depth == 0:
                return src[start:i + 1]
        i += 1
    return None


def load_file(path):
    """Returns (data, groups, problems). data is {kind: [entries]}; groups is {kind: [allowed group keys]}."""
    try:
        with open(path, encoding="utf-8") as f:
            raw = f.read()
    except OSError as e:
        return None, {}, [f"{path}: cannot open the file ({e.strerror})"]
    if path.endswith(".js"):
        data, groups = {}, {}
        src = strip_js_comments(raw)
        for name, (kind, group_name) in JS_NAMES.items():
            lit = grab_literal(src, name)
            if lit is None:
                continue
            try:
                data[kind] = json.loads(js_to_json(lit))
                glit = grab_literal(src, group_name)
                if glit:
                    groups[kind] = [g["key"] for g in json.loads(js_to_json(glit))]
            except (ValueError, KeyError, TypeError) as e:
                return None, {}, [f"{path}: could not read the {name} list ({e})"]
        if not data:
            return None, {}, [f"{path}: no DETAIL_RECIPES, BASING_TIPS or MENTOR_TIPS list found"]
        return data, groups, []
    try:
        data = json.loads(raw)
    except ValueError as e:
        return None, {}, [f"{path}: this is not valid JSON ({e}). Check commas, quotes and brackets near that spot."]
    if not isinstance(data, dict):
        return None, {}, [f"{path}: the file must be an object with kind names as keys, for example {{\"guides\": [...]}}"]
    return data, {}, []


# ---------- the checks ----------
class Report:
    def __init__(self):
        self.problems = []

    def add(self, where, message):
        self.problems.append(f"{where}: {message}")


def all_strings(value):
    if isinstance(value, str):
        yield value
    elif isinstance(value, list):
        for v in value:
            yield from all_strings(v)
    elif isinstance(value, dict):
        for k, v in value.items():
            yield from all_strings(v)


def check_text(rep, where, text):
    if EM_DASH in text:
        rep.add(where, "has an em dash. Use a full stop, a comma or the word 'to' instead.")
    if EMOJI.search(text):
        rep.add(where, "has an emoji or symbol picture. Use words only.")
    if "<" in text or ">" in text:
        rep.add(where, "has an angle bracket (< or >). Write the words out instead.")
    for rx, what in ((GW_WORDS, "a Games Workshop or faction word"), (GW_MORE, "a game, faction, character, unit, scheme or paint-range word"),
                     (BRAND_WORDS, "a brand, product or shop word")):
        m = rx.search(text)
        if m:
            rep.add(where, f"has '{m.group(0)}', {what}. Describe the thing instead (for example 'a dark red').")


def need_str(rep, where, entry, field, lo, hi):
    v = entry.get(field)
    if not isinstance(v, str):
        rep.add(where, f"'{field}' must be text")
        return None
    if not (lo <= len(v.strip()) <= hi):
        rep.add(where, f"'{field}' is {len(v.strip())} characters long; it must be {lo} to {hi}")
    if v != v.strip():
        rep.add(where, f"'{field}' has spaces at the start or end")
    return v


def need_list(rep, where, entry, field, lo, hi):
    v = entry.get(field)
    if not isinstance(v, list):
        rep.add(where, f"'{field}' must be a list")
        return None
    if not (lo <= len(v) <= hi):
        rep.add(where, f"'{field}' has {len(v)} items; it must have {lo} to {hi}")
    return v


def check_hex(rep, where, value, label="hex"):
    if not (isinstance(value, str) and HEX_FORMAT.fullmatch(value)):
        rep.add(where, f"'{label}' must be a colour like #1f3a66 (lower case, 6 digits)")


def check_credit(rep, where, credit):
    if not isinstance(credit, dict) or set(credit) != {"name", "url"}:
        rep.add(where, "'credit' must have exactly 'name' and 'url'")
        return
    if not (isinstance(credit["name"], str) and credit["name"].strip()):
        rep.add(where, "credit 'name' must be text")
    if not (isinstance(credit["url"], str) and re.fullmatch(r"https://\S+", credit["url"])):
        rep.add(where, "credit 'url' must be a link starting with https://")


def one_sentence(text):
    return len([s for s in re.split(r"(?<=[.!?])\s+", text.strip()) if s]) == 1


def check_steps(rep, where, steps, label, lo, hi):
    if not isinstance(steps, list):
        rep.add(where, f"'{label}' must be a list")
        return
    if not (lo <= len(steps) <= hi):
        rep.add(where, f"'{label}' has {len(steps)} steps; it must have {lo} to {hi}")
    hexes = []
    for i, s in enumerate(steps, 1):
        w = f"{where}, {label} step {i}"
        if not isinstance(s, dict):
            rep.add(w, "must be an object")
            continue
        missing, extra = STEP_FIELDS - set(s), set(s) - STEP_FIELDS
        if missing:
            rep.add(w, "is missing " + ", ".join(sorted(missing)))
        if extra:
            rep.add(w, "has extra field(s) " + ", ".join(sorted(extra)) + " (a paint name or brand field is never allowed)")
        if missing:
            continue
        if s["technique"] not in TECHNIQUES:
            rep.add(w, f"technique '{s['technique']}' is not one of the app's technique names: " + ", ".join(TECHNIQUES))
        if not (isinstance(s["coats"], int) and not isinstance(s["coats"], bool) and 1 <= s["coats"] <= 3):
            rep.add(w, "'coats' must be a whole number from 1 to 3")
        if not (isinstance(s["mix"], int) and not isinstance(s["mix"], bool) and 1 <= s["mix"] <= 100):
            rep.add(w, "'mix' must be a whole number from 1 to 100")
        elif (s["mix"] < 100) != (s["technique"] in THIN_TECHNIQUES):
            rep.add(w, "a Wash, Shade or Glaze must be thinned (mix under 100) and every other technique must be full strength (mix 100)")
        if not (isinstance(s["look"], str) and 0 < len(s["look"].strip()) <= 30):
            rep.add(w, "'look' must be a plain colour word or two, up to 30 characters")
        check_hex(rep, w, s["hex"])
        hexes.append(s["hex"])
        if not (isinstance(s["note"], str) and 0 < len(s["note"]) <= 100 and one_sentence(s["note"])):
            rep.add(w, "'note' must be one sentence of up to 100 characters")
    if len(set(hexes)) != len(hexes):
        rep.add(where, f"two {label} steps have the same hex colour; each step needs its own")


def check_entry(rep, kind, entry, groups):
    key = entry.get("key") if isinstance(entry, dict) else None
    where = f"{kind} '{key}'" if isinstance(key, str) else f"{kind} entry"
    if not isinstance(entry, dict):
        rep.add(where, "must be an object")
        return
    required, optional = FIELDS[kind]
    missing, extra = required - set(entry), set(entry) - required - optional
    if missing:
        rep.add(where, "is missing field(s): " + ", ".join(sorted(missing)))
    if extra:
        rep.add(where, "has field(s) that do not belong: " + ", ".join(sorted(extra)))
    if "sample" in entry and entry["sample"] is not True:
        rep.add(where, "'sample' must be true or left out")
    if not isinstance(key, str) or not ID_FORMAT.fullmatch(key) or not (2 <= len(key) <= 50):
        rep.add(where, "the key must be lower case words joined by dashes (letters and digits only), 2 to 50 characters, like 'warm-and-cool'")

    if kind == "guides":
        if entry.get("category") not in CATEGORIES:
            rep.add(where, f"'category' must be one of: {', '.join(CATEGORIES)}")
        need_str(rep, where, entry, "title", 3, 60)
        need_str(rep, where, entry, "summary", 20, 140)
        if isinstance(entry.get("summary"), str) and not one_sentence(entry["summary"]):
            rep.add(where, "'summary' must be one sentence")
        body = need_list(rep, where, entry, "body", 3, 8)
        for i, p in enumerate(body or [], 1):
            if not (isinstance(p, str) and 20 <= len(p) <= 400):
                rep.add(where, f"body paragraph {i} must be text of 20 to 400 characters")
        rel = need_list(rep, where, entry, "related", 0, 4)
        for r in rel or []:
            if not isinstance(r, str):
                rep.add(where, "'related' must hold keys (text)")
        if rel and key in rel:
            rep.add(where, "'related' lists the entry itself")
        if rel and len(set(rel)) != len(rel):
            rep.add(where, "'related' lists the same key twice")
        kws = need_list(rep, where, entry, "keywords", 6, 12)
        for k in kws or []:
            if not (isinstance(k, str) and 2 <= len(k) <= 40 and k == k.lower().strip()):
                rep.add(where, f"keyword {k!r} must be lower case text of 2 to 40 characters with no spaces at the ends")
        if kws and len({str(k).lower() for k in kws}) != len(kws):
            rep.add(where, "'keywords' has a word twice")
    elif kind == "starters":
        need_str(rep, where, entry, "text", 8, 90)
        tg = need_list(rep, where, entry, "targets", 1, 6)
        for t in tg or []:
            if not isinstance(t, str):
                rep.add(where, "'targets' must hold keys (text)")
        if tg and len(set(tg)) != len(tg):
            rep.add(where, "'targets' lists the same key twice")
    elif kind == "mentor-tips":
        if entry.get("part") not in groups.get(kind, DEFAULT_GROUPS[kind]):
            rep.add(where, f"'part' must be one of: {', '.join(groups.get(kind, DEFAULT_GROUPS[kind]))}")
        need_str(rep, where, entry, "colour", 3, 40)
        need_str(rep, where, entry, "technique", 3, 40)
        need_str(rep, where, entry, "advice", 20, 400)
        cols = need_list(rep, where, entry, "colours", 1, 4)
        for c in cols or []:
            if not (isinstance(c, dict) and set(c) == {"look", "hex"}):
                rep.add(where, "each colour must have exactly 'look' and 'hex'")
                continue
            if not (isinstance(c["look"], str) and 0 < len(c["look"]) <= 30):
                rep.add(where, "a colour 'look' must be a plain colour word or two, up to 30 characters")
            check_hex(rep, where, c["hex"])
    elif kind == "detail-recipes":
        if entry.get("group") not in groups.get(kind, DEFAULT_GROUPS[kind]):
            rep.add(where, f"'group' must be one of: {', '.join(groups.get(kind, DEFAULT_GROUPS[kind]))}")
        nm = need_str(rep, where, entry, "name", 3, 40)
        if nm and not re.fullmatch(r"[A-Za-z' -]{3,40}", nm):
            rep.add(where, "'name' may only use letters, spaces, apostrophes and dashes (no digits or brackets)")
        need_str(rep, where, entry, "summary", 10, 100)
        check_steps(rep, where, entry.get("steps"), "recipe", 3, 4)
    elif kind == "basing-tips":
        if entry.get("group") not in groups.get(kind, DEFAULT_GROUPS[kind]):
            rep.add(where, f"'group' must be one of: {', '.join(groups.get(kind, DEFAULT_GROUPS[kind]))}")
        nm = need_str(rep, where, entry, "name", 3, 40)
        if nm and not re.fullmatch(r"[A-Za-z' -]{3,40}", nm):
            rep.add(where, "'name' may only use letters, spaces, apostrophes and dashes (no digits or brackets)")
        need_str(rep, where, entry, "summary", 10, 100)
        mats = need_list(rep, where, entry, "materials", 3, 6)
        for m in mats or []:
            if not (isinstance(m, str) and 0 < len(m) <= 70 and not m.endswith(".")):
                rep.add(where, f"material {m!r} must be up to 70 characters and not end with a full stop")
        how = need_list(rep, where, entry, "howto", 3, 5)
        for h in how or []:
            if not (isinstance(h, str) and 0 < len(h) <= 120 and h.endswith(".") and one_sentence(h)):
                rep.add(where, f"how-to step {h!r} must be one sentence of up to 120 characters ending in a full stop")
        ps = entry.get("paintSteps")
        if isinstance(ps, list) and ps:
            check_steps(rep, where, ps, "paint", 1, 5)
        elif not isinstance(ps, list):
            rep.add(where, "'paintSteps' must be a list (it may be empty)")

    if "credit" in entry:
        check_credit(rep, where, entry["credit"])
    for s in all_strings({k: v for k, v in entry.items() if k != "key"}):
        check_text(rep, where, s)


def check_all(paths, partial=False, final=False):
    """Returns (problems, notes, counts). Reads every file, then checks entries and the links between them."""
    rep, notes = Report(), []
    loaded, counts = [], {}
    for path in paths:
        data, groups, bad = load_file(path)
        if bad:
            rep.problems.extend(bad)
            continue
        loaded.append((path, data, groups))
    first_seen, all_keys, links = {}, set(), []
    for path, data, groups in loaded:
        for kind in data:
            if kind not in KINDS:
                rep.add(path, f"'{kind}' is not a kind of entry. The kinds are: {', '.join(KINDS)}")
                continue
            if not isinstance(data[kind], list):
                rep.add(path, f"'{kind}' must be a list of entries")
                continue
            for entry in data[kind]:
                check_entry(rep, kind, entry, groups)
                if not isinstance(entry, dict):
                    continue
                key = entry.get("key")
                counts[kind] = counts.get(kind, 0) + 1
                if entry.get("sample") is True and final:
                    rep.add(f"{kind} '{key}'", "is a SAMPLE entry. Take sample entries out before you hand back.")
                if isinstance(key, str):
                    if key in first_seen:
                        old_kind, old_where = first_seen[key]
                        if {old_kind, kind} != LEGACY_SHARED_KEYS.get(key):
                            rep.add(f"{kind} '{key}'", f"the key is already used by {old_kind} in {old_where}; every key must be unique across all kinds")
                    else:
                        first_seen[key] = (kind, os.path.basename(path))
                    all_keys.add(key)
                    if kind == "guides":
                        links.append((kind, key, "related", entry.get("related")))
                    elif kind == "starters":
                        links.append((kind, key, "targets", entry.get("targets")))
    for kind, key, field, targets in links:
        for t in targets if isinstance(targets, list) else []:
            if isinstance(t, str) and t not in all_keys:
                msg = f"'{field}' points at '{t}', which does not exist in the files checked"
                if partial:
                    notes.append(f"{kind} '{key}': {msg} (allowed with --partial)")
                else:
                    rep.add(f"{kind} '{key}'", msg + ". Fix the key, or run with --partial while other chunks are missing.")
    return rep.problems, notes, counts


def main(argv):
    partial, final = "--partial" in argv, "--final" in argv
    paths = [a for a in argv if not a.startswith("--")]
    if not paths or "--help" in argv or "-h" in argv:
        print(__doc__)
        return 0 if "--help" in argv or "-h" in argv else 2
    unreadable = [p for p in paths if not os.path.isfile(p)]
    for p in unreadable:
        print(f"PROBLEM: {p}: this file does not exist")
    problems, notes, counts = check_all([p for p in paths if p not in unreadable], partial, final)
    for p in problems:
        print("PROBLEM: " + p)
    for n in notes:
        print("note: " + n)
    summary = ", ".join(f"{v} {k}" for k, v in counts.items()) or "no entries"
    if problems or unreadable:
        print(f"\nNOT CLEAN: {len(problems) + len(unreadable)} problem(s). Checked {summary}.")
        return 1
    print(f"CLEAN: checked {summary}. No problems found.")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
