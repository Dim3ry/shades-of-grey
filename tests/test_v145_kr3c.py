"""KR3c tests for Minifolio (Techniques rewrites, then contractions and spelling swaps in the Guides). New behaviour only:
a sample of Techniques rewrites, the contractions, and the three spellings in guides, detail recipes and basing tips.
Run with `python3 tests/run_all.py`, or serve the repo folder and run this file on its own."""
import os, sys
from playwright.sync_api import sync_playwright

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import test_v31 as t
from launch_helpers import wait_settled

results = []

def check(name, ok, detail=""):
    results.append(bool(ok))
    print(("PASS " if ok else "FAIL ") + name + ("" if ok else f"  -> {detail}"))

# (guide key, new text, old text): Techniques rewrites (already in contractions)
REWRITES = [
    ("white-armour", "Don't be afraid of a fairly dark grey right next to white; strong contrast keeps the white crisp, not chalky.", "Bold contrast keeps white crisp rather than chalky"),
    ("brush-control", "Check each stroke against what you planned; that is how control gets better, and speed comes later.", "speed follows"),
    ("two-thin-coats", "Treat this as a rough guide.", "a guideline, not a law"),
    ("finishing-touches", "make a model look finished.", "make a model read as finished."),
    ("clean-crisp-painting", "A crisp model comes down to clean paint and clear definition.", "Two things make a model look crisp"),
]

JS = """() => {
  const re = (p) => new RegExp(p, 'i');
  // reader text only: summaries, bodies, notes, materials, how-to (never titles, names, keywords, technique values)
  const guideText = GUIDE_ENTRIES.map(e => [e.summary, ...e.body]).flat();
  const recipeText = DETAIL_RECIPES.map(e => [e.summary, ...e.steps.map(s => s.note)]).flat();
  const tipText = BASING_TIPS.map(e => [e.summary, ...e.materials, ...e.howto, ...(e.paintSteps || []).map(s => s.note)]).flat();
  const all = [...guideText, ...recipeText, ...tipText];
  const count = (p) => all.filter(x => re(p).test(x)).length;
  return {
    guides: Object.fromEntries(GUIDE_ENTRIES.map(e => [e.key, JSON.stringify(e)])),
    matt: count('\\\\bmatt\\\\b'), dry: count('dry brush'), under: count('under suit'),
    matte: count('\\\\bmatte\\\\b'), drybrush: count('drybrush'), undersuit: count('undersuit'),
    doNot: count("\\\\b(do|does|did|is|are|was|will|would|should|could|has|have) not\\\\b"), cannot: count('\\\\bcannot\\\\b'),
    dont: count("don't"), wont: count("won't"), cant: count("can't"),
    itIs: count('\\\\bit is\\\\b'),
    dash: all.filter(x => /[\\u2013\\u2014]/.test(x)).length,
    overbrush: JSON.stringify(GUIDE_ENTRIES.find(e => /overbrush/i.test(e.title)) || null).length > 4,
    dryStep: DETAIL_RECIPES.some(r => r.steps.some(s => s.technique === 'Dry brush')),
  };
}"""

def main():
    errors = []
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_context(viewport={"width": 390, "height": 844}, service_workers="block").new_page()
        page.on("pageerror", lambda x: errors.append(str(x)))
        page.goto(t.URL)
        wait_settled(page)
        r = page.evaluate(JS)
        print("\n--- Part 1: Techniques rewrites ---")
        for key, new, old in REWRITES:
            s = r["guides"].get(key, "")
            check(f"{key}: new wording in, old gone", new in s and old not in s)
        print("\n--- Part 2: spellings ---")
        check("no 'matt' left in reader text", r["matt"] == 0, r["matt"])
        check("no 'dry brush' left in reader text", r["dry"] == 0, r["dry"])
        check("no 'under suit' left in reader text", r["under"] == 0, r["under"])
        check("matte, drybrush and undersuit are used", r["matte"] > 100 and r["drybrush"] > 50 and r["undersuit"] >= 1, (r["matte"], r["drybrush"], r["undersuit"]))
        check("technique value 'Dry brush' in recipe steps is untouched", r["dryStep"])
        g = r["guides"]
        check("a 'matt' keyword is untouched (Mentor matching)", any('"matt vs gloss"' in v for v in g.values()))
        print("\n--- Part 2: contractions ---")
        check("negations are contracted", r["doNot"] == 0 and r["cannot"] == 0, (r["doNot"], r["cannot"]))
        check("don't, won't and can't appear", r["dont"] > 100 and r["wont"] > 30 and r["cant"] > 30, (r["dont"], r["wont"], r["cant"]))
        check("'it is' left alone (taste call)", r["itIs"] > 100, r["itIs"])
        check("no dashes in reader text", r["dash"] == 0, r["dash"])
        s = g.get("white-armour", "")
        check("sample: white-armour has don't", "Don't be afraid" in s)
        check("no page errors", errors == [], errors)
        browser.close()
    print(f"\n{sum(results)}/{len(results)} checks passed")
    return 0 if all(results) else 1

if __name__ == "__main__":
    sys.exit(main())
