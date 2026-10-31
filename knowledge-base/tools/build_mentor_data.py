"""Builds mentor-data.js, the one plain data file the Mentor answer engine (mentor-engine.js) reads for its extra words.

    python3 -I build_mentor_data.py [--extras DIR] [--starters FILE] [--out FILE] [--max-quick N] [--no-quick]

Standard library only. Reads the knowledge-base extras and writes one script that defines MENTOR_DATA:

  keywords   { key: [keyword phrase, ...] }       recipe-and-basing-keywords.json (recipes and basing tips have no keywords of their own)
  synonyms   [ [canonical, variant, ...], ... ]   beginner-synonyms.json (the canonical first)
  phrases    { key: [phrase, ...] }               asked-as-phrases.json (about ten ways people ask for each entry)
  quick      { key: [answer or "", ...] }         quick-answers.json, one per phrase, in the same order; "" where there is none
  starters   { starter key: answer }              quick-answers.json, the answer to a starter question's own text (for its first target)

Quick answers are left out ("") when they are weak ("See: ..."), longer than two sentences or 260 characters, or contain words the
engine may never say (the same list as tests/mentor_engine_check.js: dashes, apologies, brand or faction words, angle brackets).
--max-quick N keeps at most N quick answers per entry (the first N good ones, in phrase order), to keep the file small. The default, 5,
makes about 760 KB (about 230 KB compressed); 0 keeps all (about 1.2 MB) and gives a quick lead about a fifth more often.
"""
import argparse, json, os, re, sys

HERE = os.path.dirname(os.path.abspath(__file__))
KB = os.path.join(HERE, "..")   # knowledge-base/
BAD = re.compile(r"—|–|great question|sorry|unfortunately|as an ai|games workshop|citadel|vallejo|army painter|\bchaos\b|\bimperial\b|"
                 r"\blegion\b|\bcrusade\b|space marine|\bork\b|\beldar\b|\btyranid|\bthe mentor\b|<|>", re.I)
SENTENCE_END = re.compile(r"[.!?](\s|$)")


def clean(s):
    """One line of plain text: single spaces, straight quotes."""
    s = str(s).replace("’", "'").replace("‘", "'").replace("“", '"').replace("”", '"')
    return re.sub(r"\s+", " ", s).strip()


def good_answer(a):
    a = clean(a)
    if not a or a.startswith("See:") or BAD.search(a):
        return ""
    if len(a) > 260 or len(SENTENCE_END.findall(a if a[-1] in ".!?" else a + ".")) > 2:
        return ""
    return a


def safe_phrase(p):
    p = clean(p)
    return "" if (not p or BAD.search(p)) else p


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--extras", default=os.path.join(KB, "extras"))
    ap.add_argument("--starters", default=os.path.join(KB, "data", "k7-starters.json"))
    ap.add_argument("--out", default=os.path.join(KB, "..", "mentor-data.js"))
    ap.add_argument("--max-quick", type=int, default=5)
    ap.add_argument("--no-quick", action="store_true", help="leave out quick answers and starter answers: the lead stays the entry's own words")
    args = ap.parse_args()
    load = lambda name: json.load(open(os.path.join(args.extras, name), encoding="utf-8"))

    keywords_in = load("recipe-and-basing-keywords.json")
    groups_in = load("beginner-synonyms.json")["groups"]
    asked_in = load("asked-as-phrases.json")
    quick_in = load("quick-answers.json")
    starters_in = json.load(open(args.starters, encoding="utf-8"))["starters"]

    keywords = {}
    for key in sorted(keywords_in):
        ks = []
        for k in keywords_in[key]:
            k = safe_phrase(k).lower()
            if k and k not in ks:
                ks.append(k)
        if ks:
            keywords[key] = ks

    synonyms, seen = [], set()
    for g in groups_in:
        canon = safe_phrase(g["canonical"]).lower()
        vs = []
        for v in g["variants"]:
            v = safe_phrase(v).lower()
            # a variant belongs to one group only (the first), and never rewrites to itself
            if v and v != canon and v not in seen:
                vs.append(v)
                seen.add(v)
        if canon and vs:
            synonyms.append([canon] + vs)

    phrases, quick, counts = {}, {}, {"phrases": 0, "quick": 0, "weak": 0, "dropped": 0, "capped": 0}
    for key in sorted(asked_in):
        ps, qs = [], []
        answers = quick_in.get(key, {})
        kept = 0
        for p in asked_in[key]:
            p2 = safe_phrase(p)
            if not p2 or p2.lower() in [x.lower() for x in ps]:
                continue
            raw = answers.get(p, "")
            a = good_answer(raw)
            if raw and not a:
                counts["weak" if clean(raw).startswith("See:") else "dropped"] += 1
            if a and args.max_quick and kept >= args.max_quick:
                a = ""
                counts["capped"] += 1
            if a:
                kept += 1
            ps.append(p2)
            qs.append(a)
        if ps:
            phrases[key] = ps
            counts["phrases"] += len(ps)
            if any(qs):
                # trailing empty answers are left off to save space; the engine treats a missing one as ""
                while qs and not qs[-1]:
                    qs.pop()
                quick[key] = qs
                counts["quick"] += sum(1 for a in qs if a)

    starters = {}
    for s in starters_in:
        targets = s.get("targets") or []
        if not targets:
            continue
        a = good_answer(quick_in.get(targets[0], {}).get(s["text"], ""))
        if a:
            starters[s["key"]] = a

    if args.no_quick:
        quick, starters = {}, {}
        counts["quick"] = 0
    data = {"keywords": keywords, "synonyms": synonyms, "phrases": phrases, "quick": quick, "starters": starters}
    dump = lambda v: json.dumps(v, ensure_ascii=True, separators=(",", ":"))
    lines = [
        "// ===== mentor-data.js: extra words for the Mentor answer engine (plain data) =====",
        "// This file is only data. It draws nothing, talks to nothing and stores nothing. mentor-engine.js reads MENTOR_DATA when it answers.",
        "//",
        "// How it is shared: loaded as a plain script just before mentor-engine.js, so MENTOR_DATA is there when the engine first answers.",
        "// Made by a script from the knowledge base's extras (build_mentor_data.py). Do not edit by hand: change the extras and build it again.",
        "//",
        "//  keywords  { entry key: [keyword phrase] }   extra keywords, so recipes and basing tips (which have none) can be found by topic",
        "//  synonyms  [ [canonical, variant, ...] ]     every variant in a question or an entry is read as the canonical word or phrase",
        "//  phrases   { entry key: [phrase] }           about ten ways people ask for each entry",
        "//  quick     { entry key: [answer] }           a one- or two-line answer for each phrase, in the same order; \"\" or missing: none",
        "//  starters  { starter key: answer }           the answer to a starter question, for its first target",
        "// Shown as plain text only, and kept free of angle brackets.",
        "",
        "const MENTOR_DATA = {",
    ]
    for name in ["keywords", "synonyms", "phrases", "quick"]:
        v = data[name]
        lines.append(f"  {name}: {{" if isinstance(v, dict) else f"  {name}: [")
        if isinstance(v, dict):
            lines += [f"    {dump(k)}: {dump(x)}," for k, x in v.items()]
            lines.append("  },")
        else:
            lines += [f"    {dump(x)}," for x in v]
            lines.append("  ],")
    lines.append(f"  starters: {dump(starters)},")
    lines.append("};")
    text = "\n".join(lines) + "\n"
    with open(args.out, "w", encoding="utf-8", newline="\n") as f:
        f.write(text)
    size = os.path.getsize(args.out)
    print(json.dumps({"out": args.out, "bytes": size, "keywords": len(keywords), "synonym_groups": len(synonyms),
                      "variants": sum(len(g) - 1 for g in synonyms), "phrase_entries": len(phrases), **counts,
                      "starters": len(starters)}))


if __name__ == "__main__":
    sys.exit(main())
