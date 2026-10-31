#!/usr/bin/env python3
"""kb_import.py: merge the knowledge base (knowledge-base/data/*.json) into Minifolio's data files (chunk X8).

    python3 -I kb_import.py REPO [DATA_DIR]

REPO      the app folder (the one with guides-data.js, detail-recipes.js and basing-tips.js)
DATA_DIR  the folder of k*.json files (default: ../data next to this script, that is knowledge-base/data)

What it writes (standard library only, safe to run again):
  - guides-data.js:    GUIDE_ENTRIES (every "guides" entry) and GUIDE_STARTERS (every "starters" entry). The header
                       comment is kept; only the two lists are rewritten.
  - detail-recipes.js: the new "detail-recipes" entries, added at the end of their group's section in DETAIL_RECIPES.
  - basing-tips.js:    the new "basing-tips" entries, added at the end of their group's section in BASING_TIPS.
Added recipes and tips sit between an "// X8 start" and an "// X8 end" comment line. A second run removes those blocks
first and writes them again, so existing entries are never changed or moved and nothing is added twice.

It stops without writing anything if: a key is used twice (only the old detail/basing pair "mud" may share a key),
a new key is already in the app, a group is not one of the file's groups, an entry has a field the app does not know,
a related/targets key points nowhere, or the files read back differently from the data.
"""
import json
import os
import re
import sys

KINDS = ("guides", "starters", "detail-recipes", "basing-tips")
FIELDS = {
    "guides": ["key", "category", "title", "summary", "body", "related", "keywords", "credit"],
    "starters": ["key", "text", "targets"],
    "detail-recipes": ["key", "group", "name", "summary", "steps"],
    "basing-tips": ["key", "group", "name", "summary", "materials", "howto", "paintSteps"],
}
REQUIRED_OPTIONAL = {"guides": {"credit"}}
STEP_FIELDS = ["technique", "coats", "mix", "look", "hex", "note"]
GUIDE_CATEGORIES = ["colour-basics", "techniques", "tools-prep", "problems"]
CATEGORY_NAMES = {"colour-basics": "Colour basics", "techniques": "Techniques", "tools-prep": "Tools and prep", "problems": "Problems"}
LEGACY_SHARED_KEYS = {"mud"}  # the one old detail recipe / basing tip pair that shares a key
START = "// X8 start"
END = "// X8 end"


class Stop(Exception):
    pass


# ---------- reading the app's JS data (same approach as knowledge-base/check_knowledge.py) ----------
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
    kept = [t for idx, t in enumerate(tokens)
            if not (t == "," and idx + 1 < len(tokens) and tokens[idx + 1] in ("]", "}"))]
    return "".join(kept)


def literal_span(src, name):
    """(start, end) of the [...] or {...} after 'const NAME =' in src (end is one past the closing bracket), or None."""
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
        elif src.startswith("//", i):
            while i < n and src[i] != "\n":
                i += 1
            continue
        elif c == opener:
            depth += 1
        elif c == closer:
            depth -= 1
            if depth == 0:
                return start, i + 1
        i += 1
    return None


def read_list(src, name):
    clean = strip_js_comments(src)
    span = literal_span(clean, name)
    if span is None:
        raise Stop(f"no 'const {name} = ...' found")
    return json.loads(js_to_json(clean[span[0]:span[1]]))


# ---------- writing plain JS in the files' own style ----------
def s(value):
    """A double-quoted JS string (JSON escaping is valid JS)."""
    return json.dumps(value, ensure_ascii=False).replace("\u2028", "\\u2028").replace("\u2029", "\\u2029")


def v(value):
    if isinstance(value, str):
        return s(value)
    if isinstance(value, bool) or value is None:
        return json.dumps(value)
    if isinstance(value, (int, float)):
        return json.dumps(value)
    if isinstance(value, list):
        return "[" + ", ".join(v(x) for x in value) + "]"
    if isinstance(value, dict):
        return "{ " + ", ".join(f"{k}: {v(x)}" for k, x in value.items()) + " }"
    raise Stop(f"cannot write a value of type {type(value).__name__}")


def step_line(step):
    return "      { " + ", ".join(f"{k}: {v(step[k])}" for k in STEP_FIELDS) + " },"


def text_block(name, items, indent="    "):
    lines = [f"{indent}{name}: ["]
    lines += [f"{indent}  {s(x)}," for x in items]
    lines.append(f"{indent}],")
    return lines


def close(lines):
    """The last line of an entry ends in ' },' (as in the app's files: '    ] },')."""
    last = lines[-1]
    lines[-1] = (last[:-1] if last.endswith(",") else last) + " },"
    return lines


def render_recipe(r):
    lines = [f"  {{ key: {s(r['key'])}, group: {s(r['group'])}, name: {s(r['name'])}, summary: {s(r['summary'])},",
             "    steps: ["]
    lines += [step_line(st) for st in r["steps"]]
    lines.append("    ],")
    return close(lines)


def render_tip(t):
    lines = [f"  {{ key: {s(t['key'])}, group: {s(t['group'])}, name: {s(t['name'])}, summary: {s(t['summary'])},",
             f"    materials: {v(t['materials'])},"]
    lines += text_block("howto", t["howto"])
    if t["paintSteps"]:
        lines.append("    paintSteps: [")
        lines += [step_line(st) for st in t["paintSteps"]]
        lines.append("    ],")
    else:
        lines.append("    paintSteps: [],")
    return close(lines)


def render_guide(g):
    lines = [f"  {{ key: {s(g['key'])}, category: {s(g['category'])}, title: {s(g['title'])},",
             f"    summary: {s(g['summary'])},"]
    lines += text_block("body", g["body"])
    lines.append(f"    related: {v(g['related'])},")
    lines.append(f"    keywords: {v(g['keywords'])},")
    if "credit" in g:
        lines.append(f"    credit: {{ name: {s(g['credit']['name'])}, url: {s(g['credit']['url'])} }},")
    return close(lines)


def render_starter(st):
    return [f"  {{ key: {s(st['key'])}, text: {s(st['text'])}, targets: {v(st['targets'])} }},"]


# ---------- the data ----------
def load_data(data_dir):
    data = {k: [] for k in KINDS}
    files = sorted(f for f in os.listdir(data_dir) if f.endswith(".json"))
    if not files:
        raise Stop(f"no .json files in {data_dir}")
    for f in files:
        with open(os.path.join(data_dir, f), encoding="utf-8") as fh:
            d = json.load(fh)
        for kind, entries in d.items():
            if kind not in KINDS:
                raise Stop(f"{f}: kind '{kind}' is not imported by X8 (only {', '.join(KINDS)})")
            for e in entries:
                if e.get("sample"):
                    raise Stop(f"{f}: '{e.get('key')}' is a sample entry")
                extra = [k for k in e if k not in FIELDS[kind]]
                missing = [k for k in FIELDS[kind] if k not in e and k not in REQUIRED_OPTIONAL.get(kind, set())]
                if extra or missing:
                    raise Stop(f"{f}: {kind} '{e.get('key')}' has unknown fields {extra} or is missing {missing}")
                for st in e.get("steps", []) + e.get("paintSteps", []):
                    if sorted(st) != sorted(STEP_FIELDS):
                        raise Stop(f"{f}: '{e['key']}' has a step with fields {sorted(st)}")
                data[kind].append(e)
    return data, files


def check_keys(data, old_recipes, old_tips, old_tips_mentor, groups):
    seen = {}
    for kind, entries in [("detail-recipes", old_recipes), ("basing-tips", old_tips), ("mentor-tips", old_tips_mentor)]:
        for e in entries:
            if e["key"] in seen and e["key"] not in LEGACY_SHARED_KEYS:
                raise Stop(f"the app already has two entries with key '{e['key']}'")
            seen.setdefault(e["key"], f"existing {kind}")
    for kind in KINDS:
        for e in data[kind]:
            if e["key"] in seen:
                raise Stop(f"{kind} key '{e['key']}' is already used by {seen[e['key']]}")
            seen[e["key"]] = f"new {kind}"
    for kind, field in (("guides", "related"), ("starters", "targets")):
        for e in data[kind]:
            for t in e[field]:
                if t not in seen:
                    raise Stop(f"{kind} '{e['key']}': {field} key '{t}' does not exist")
    for e in data["guides"]:
        if e["category"] not in GUIDE_CATEGORIES:
            raise Stop(f"guide '{e['key']}' has category '{e['category']}'")
    for kind in ("detail-recipes", "basing-tips"):
        for e in data[kind]:
            if e["group"] not in groups[kind]:
                raise Stop(f"{kind} '{e['key']}' has group '{e['group']}', not one of {groups[kind]}")


# ---------- editing the files ----------
def drop_old_blocks(src):
    """Removes earlier X8 blocks (a re-run), so the file is back to George's own entries."""
    out, skipping = [], False
    for line in src.split("\n"):
        stripped = line.strip()
        if stripped.startswith(START):
            if skipping:
                raise Stop("an X8 start line without its end line")
            skipping = True
            continue
        if skipping:
            if stripped == END:
                skipping = False
            continue
        out.append(line)
    if skipping:
        raise Stop("an X8 start line without its end line")
    return "\n".join(out)


def add_grouped(src, list_name, groups_name, entries, render, source):
    """Puts each group's new entries at the end of that group's section of LIST_NAME (before the next
    '// ---------- Name ----------' line, or before the closing '];')."""
    groups = read_list(src, groups_name)
    lines = src.split("\n")
    open_at = next(i for i, l in enumerate(lines) if re.match(r"const\s+" + list_name + r"\s*=\s*\[", l))
    close_at = next(i for i in range(open_at + 1, len(lines)) if lines[i] == "];")
    headers = {}
    for i in range(open_at + 1, close_at):
        m = re.match(r"\s*// -{3,} (.+?) -{3,}\s*$", lines[i])
        if m:
            headers[m.group(1)] = i
    starts = sorted(headers.values())
    inserts = {}  # line index -> lines to insert before it
    for g in groups:
        new = [e for e in entries if e["group"] == g["key"]]
        if not new:
            continue
        h = headers.get(g["name"])
        if h is None:
            at = close_at
        else:
            nxt = [x for x in starts if x > h]
            at = nxt[0] if nxt else close_at
            while lines[at - 1].strip() == "":  # keep the blank line between sections after the block
                at -= 1
        block = [f"  {START}: new {g['name']} entries from {source}. kb_import.py writes this block, so re-run it rather than editing here."]
        for e in new:
            block += render(e)
        block.append(f"  {END}")
        inserts.setdefault(at, []).extend(block)
    out = []
    for i, line in enumerate(lines):
        out.extend(inserts.get(i, []))
        out.append(line)
    return "\n".join(out)


def replace_list(src, name, body_lines, comment):
    span = literal_span(src, name)
    if span is None:
        raise Stop(f"guides-data.js has no 'const {name} = ...'")
    start = src.rfind("\n", 0, span[0]) + 1  # the start of the 'const' line
    # an earlier run's comment line directly above
    prev_start = src.rfind("\n", 0, start - 1) + 1
    if src[prev_start:start].startswith("// X8:"):
        start = prev_start
    text = comment + "\n" + f"const {name} = [" + ("\n" + "\n".join(body_lines) + "\n" if body_lines else "") + "]"
    return src[:start] + text + src[span[1]:]


def guide_lines(guides):
    out = []
    for cat in GUIDE_CATEGORIES:
        these = [g for g in guides if g["category"] == cat]
        if not these:
            continue
        if out:
            out.append("")
        out.append(f"  // ---------- {CATEGORY_NAMES[cat]} ----------")
        for g in these:
            out += render_guide(g)
    return out


def read(path):
    with open(path, encoding="utf-8", newline="") as f:
        text = f.read()
    if "\r\n" in text:
        raise Stop(f"{path} has Windows line endings; this script writes plain newlines only")
    return text


def write(path, text):
    with open(path, "w", encoding="utf-8", newline="") as f:
        f.write(text)


def main(argv):
    if not argv or argv[0] in ("-h", "--help"):
        print(__doc__)
        return 0 if argv else 2
    repo = os.path.abspath(argv[0])
    here = os.path.dirname(os.path.abspath(__file__))
    data_dir = os.path.abspath(argv[1]) if len(argv) > 1 else os.path.join(here, "..", "data")
    paths = {n: os.path.join(repo, n) for n in ("guides-data.js", "detail-recipes.js", "basing-tips.js", "mentor-tips.js")}
    try:
        data, files = load_data(data_dir)
        src = {n: read(p) for n, p in paths.items()}
        rec_src = drop_old_blocks(src["detail-recipes.js"])
        tip_src = drop_old_blocks(src["basing-tips.js"])
        old_recipes = read_list(rec_src, "DETAIL_RECIPES")
        old_tips = read_list(tip_src, "BASING_TIPS")
        mentor = read_list(src["mentor-tips.js"], "MENTOR_TIPS")
        groups = {"detail-recipes": [g["key"] for g in read_list(rec_src, "DETAIL_GROUPS")],
                  "basing-tips": [g["key"] for g in read_list(tip_src, "BASING_GROUPS")]}
        check_keys(data, old_recipes, old_tips, mentor, groups)

        def source(kind):
            return ", ".join(f for f in files if kind in json.load(open(os.path.join(data_dir, f), encoding="utf-8")))

        new_rec = add_grouped(rec_src, "DETAIL_RECIPES", "DETAIL_GROUPS", data["detail-recipes"], render_recipe, source("detail-recipes"))
        new_tip = add_grouped(tip_src, "BASING_TIPS", "BASING_GROUPS", data["basing-tips"], render_tip, source("basing-tips"))
        g = src["guides-data.js"]
        g = replace_list(g, "GUIDE_ENTRIES", guide_lines(data["guides"]),
                         f"// X8: {len(data['guides'])} guide entries from {source('guides')}. Written by kb_import.py; re-run it rather than editing here.")
        g = replace_list(g, "GUIDE_STARTERS", [l for st in data["starters"] for l in render_starter(st)],
                         f"// X8: {len(data['starters'])} starter questions from {source('starters')}. Written by kb_import.py.")

        # read everything back: old entries unchanged and in order, new ones exactly the data
        def by_key(lst):
            return sorted(lst, key=lambda e: (e["key"], json.dumps(e, sort_keys=True)))
        for name, text, old, new in (("DETAIL_RECIPES", new_rec, old_recipes, data["detail-recipes"]),
                                     ("BASING_TIPS", new_tip, old_tips, data["basing-tips"])):
            back = read_list(text, name)
            new_keys = {e["key"] for e in new}
            kept = [e for e in back if e["key"] not in new_keys]
            if kept != old:
                raise Stop(f"{name}: existing entries would change or move")
            if by_key([e for e in back if e not in old]) != by_key(new):
                raise Stop(f"{name}: the new entries do not read back the same as the data")
        if read_list(g, "GUIDE_ENTRIES") != sorted(data["guides"], key=lambda e: GUIDE_CATEGORIES.index(e["category"])) \
                or read_list(g, "GUIDE_STARTERS") != data["starters"]:
            raise Stop("guides-data.js does not read back the same as the data")
    except (Stop, ValueError, OSError, StopIteration) as e:
        print(f"STOPPED, nothing written: {e}")
        return 1

    changed = []
    for name, text in (("guides-data.js", g), ("detail-recipes.js", new_rec), ("basing-tips.js", new_tip)):
        if text != src[name]:
            write(paths[name], text)
            changed.append(name)
    print(f"guides: {len(data['guides'])}, starters: {len(data['starters'])}, "
          f"detail recipes: {len(old_recipes)} + {len(data['detail-recipes'])} new, "
          f"basing tips: {len(old_tips)} + {len(data['basing-tips'])} new")
    print("written: " + (", ".join(changed) if changed else "nothing (already up to date)"))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
