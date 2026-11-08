"""KR9 tests for Minifolio (it is -> it's in reader text; nmm-basics second paragraph). New behaviour only.
Reads the knowledge-base files and the three app data files as text, so it needs no browser."""
import glob, json, os, re

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
results = []

def check(name, ok, detail=""):
    results.append(bool(ok))
    print(("PASS " if ok else "FAIL ") + name + ("" if ok else f"  -> {detail}"))

def load(name):
    return json.load(open(os.path.join(ROOT, "knowledge-base", "data", name), encoding="utf-8"))

def reader_text(d):
    """Summaries, bodies, notes, materials and how-to steps only (never titles, names, keywords or keys)."""
    out = []
    for e in d.get("guides", []):
        out += [e["summary"]] + e["body"]
    for e in d.get("detail-recipes", []):
        out += [e["summary"]] + [s["note"] for s in e["steps"] if "note" in s]
    for e in d.get("basing-tips", []):
        out += [e["summary"]] + e.get("materials", []) + e.get("howto", []) + [s["note"] for s in e.get("paintSteps", []) if "note" in s]
    return out

def main():
    files = sorted(glob.glob(os.path.join(ROOT, "knowledge-base", "data", "k*.json")))
    texts = []
    for f in files:
        texts += reader_text(json.load(open(f, encoding="utf-8")))

    print("--- Part 1: it is -> it's ---")
    left = []
    for t in texts:
        for m in re.finditer(r"\b[Ii]t is\b", t):
            nxt = t[m.end():m.end() + 1]
            if nxt != "" and nxt not in ".,:;?)\"'”’":
                left.append(t[max(0, m.start() - 20):m.end() + 20])
    check("no 'it is' left in the middle of a clause", not left, left[:3])
    check("some it's now present", sum(t.count("it's") + t.count("It's") for t in texts) > 150)
    # a changed sample, and a kept one that ends a clause
    guides = {e["key"]: e for e in load("k1-colour-basics.json")["guides"]}
    flat = " ".join(" ".join(e["body"]) for e in guides.values())
    check("sentence-end 'it is' kept", re.search(r"\bit is[.,]", " ".join(texts)) is not None)
    check("'It's' capitalised at a sentence start", re.search(r"(^|\. )It's\b", " ".join(texts)) is not None)
    check("no em or en dashes in reader text", not any(re.search("[–—]", t) for t in texts))

    print("--- Part 2: nmm-basics second paragraph ---")
    nmm = next(e for e in load("k2-techniques.json")["guides"] if e["key"] == "nmm-basics")
    p2 = nmm["body"][1]
    check("bounce light explained in plain words", "a second dimmer shine on the side away from the main light" in p2)
    check("sword exercise sentence kept", "A first NMM exercise: a straight sword walks through one blade step by step." in p2)
    check("paragraph within 400 characters", len(p2) <= 400, len(p2))

    print("--- Part 3: transfers paragraph left alone, titles and keys unchanged ---")
    at = next(e for e in load("k2-techniques.json")["guides"] if e["key"] == "applying-transfers")
    check("applying-transfers still 8 paragraphs", len(at["body"]) == 8)
    check("hair dryer sentence not yet split out", "some painters advise against it" not in " ".join(at["body"]))
    titles = [e["title"] for f in files for e in json.load(open(f, encoding="utf-8")).get("guides", [])]
    check("no title contains it's", not any("it's" in t.lower() for t in titles))

    print("--- Part 4: app data files match ---")
    gd = open(os.path.join(ROOT, "guides-data.js"), encoding="utf-8").read()
    check("guides-data.js carries the nmm-basics text", "a second dimmer shine on the side away from the main light" in gd)
    bt = open(os.path.join(ROOT, "basing-tips.js"), encoding="utf-8").read()
    check("original basing tips use it's too", "while it's soft, of different widths" in bt and "while it's wet, if you like" in bt)

    print(f"\n{sum(results)}/{len(results)} checks passed")
    raise SystemExit(0 if all(results) else 1)

main()
