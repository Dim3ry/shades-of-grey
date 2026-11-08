"""KR10 test for Minifolio (applying-transfers paragraph 6 reworded). New behaviour only. No browser needed."""
import json, os

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
results = []

def check(name, ok, detail=""):
    results.append(bool(ok))
    print(("PASS " if ok else "FAIL ") + name + ("" if ok else f"  -> {detail}"))

NEW = ("Softened film looks wrinkled at first. After about fifteen minutes, roll out wrinkles or air with a damp cotton bud. "
       "With neither bottle, water over gloss works on flat areas, and thinned white glue helps it grip. Let it dry fully, ideally overnight. "
       "A hair dryer held well back is quicker, but it may blow a wet transfer out of place. If a fold won't settle, paint it over as a scratch or chip.")

def main():
    d = json.load(open(os.path.join(ROOT, "knowledge-base", "data", "k2-techniques.json"), encoding="utf-8"))
    e = next(g for g in d["guides"] if g["key"] == "applying-transfers")
    check("entry still has 8 paragraphs", len(e["body"]) == 8, len(e["body"]))
    check("paragraph 6 is the approved text", e["body"][5] == NEW)
    check("paragraph 6 within 400 characters", len(e["body"][5]) <= 400, len(e["body"][5]))
    check("hair dryer warning present", "may blow a wet transfer out of place" in e["body"][5])
    check("sealing paragraph 7 untouched", e["body"][6].startswith("Seal with gloss to hide the film edge"))
    check("title and key unchanged", e["title"] == "Applying waterslide transfers" and e["key"] == "applying-transfers")
    gd = open(os.path.join(ROOT, "guides-data.js"), encoding="utf-8").read()
    check("guides-data.js carries the new text", "it may blow a wet transfer out of place" in gd)
    check("old wording gone from guides-data.js", "speeds it up" not in gd.split("applying-transfers")[1][:4000])
    print(f"\n{sum(results)}/{len(results)} checks passed")
    raise SystemExit(0 if all(results) else 1)

main()
