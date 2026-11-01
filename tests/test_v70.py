"""v70 tests for Minifolio (chunk 4.1: the Mentor tips library, no screen yet).

What changed:
 A new data file, mentor-tips.js, holds the Mentor tips: MENTOR_PARTS (armour, eyes, weapon, base), MENTOR_TECHNIQUES (a short list of
 usual technique words) and MENTOR_TIPS. Each tip has a key, a part, a colour word, a technique (free text), the advice, suggested colours
 (a plain look and a hex) and an optional credit (name and link). The three tips in it are samples that only show the format; real tips
 come from George's notes. A small loader, mentorTipsFor(), hands back the tips that fit a part, technique and colour. Nothing is drawn yet.

Checks:
1. Every tip has the required fields in the right shape, a unique key, a known part, colours with a hex, and a well-formed credit when it has one.
2. The text of every tip names no Games Workshop game, faction or product, has no em dash and no angle brackets.
3. The loader: no filter gives all tips, part, technique and colour narrow it (capitals ignored), nothing matching gives none, and it
   hands back nothing (not an error) when the data file is missing.
4. The samples are marked as samples; a tip that is not a sample must carry advice (so a real tip can never ship empty).
5. No page errors, no browser pop-ups.
Run all tests with `python3 tests/run_all.py`, or serve the repo folder and run this file on its own."""
import os, re, sys
from playwright.sync_api import sync_playwright

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import use_sample_tips
import test_v31 as t

load, GW_WORDS, GW_MORE = t.load, t.GW_WORDS, t.GW_MORE
results = []

def check(name, ok, detail=""):
    results.append(bool(ok))
    print(("PASS " if ok else "FAIL ") + name + ("" if ok else f"  -> {detail}"))

# The same shape as the tips, written as a page check so the real loaded data is what gets tested (not a copy of it).
SHAPE_JS = """() => {
  const bad = [], keys = new Set(), parts = MENTOR_PARTS.map(p => p.key);
  const text = s => typeof s === 'string' && s.trim().length > 0;
  for (const tip of MENTOR_TIPS) {
    const id = tip.key || '(no key)';
    if (!/^[a-z0-9-]+$/.test(tip.key || '') || keys.has(tip.key)) bad.push([id, 'key']);
    keys.add(tip.key);
    if (!parts.includes(tip.part)) bad.push([id, 'part']);
    for (const f of ['colour', 'technique', 'advice']) if (!text(tip[f])) bad.push([id, f]);
    if (!Array.isArray(tip.colours) || !tip.colours.length || !tip.colours.every(c => text(c.look) && /^#[0-9a-f]{6}$/i.test(c.hex || ''))) bad.push([id, 'colours']);
    if ('credit' in tip && !(text(tip.credit.name) && /^https:\\/\\/[^\\s<>"]+$/.test(tip.credit.url || ''))) bad.push([id, 'credit']);
    if ('sample' in tip && tip.sample !== true) bad.push([id, 'sample']);
  }
  return { bad, n: MENTOR_TIPS.length, samples: MENTOR_TIPS.filter(x => x.sample).length, parts };
}"""

TEXT_JS = """() => JSON.stringify([MENTOR_PARTS, MENTOR_TECHNIQUES, MENTOR_TIPS])"""

def main():
    errors, dialogs = [], []
    with sync_playwright() as p:
        browser = p.chromium.launch()
        ctx = browser.new_context(viewport={"width": 390, "height": 844}, service_workers="block")
        use_sample_tips(ctx)   # A1: the real file no longer holds the sample tips, this test puts them back in memory
        page = ctx.new_page()
        page.on("pageerror", lambda x: errors.append(str(x)))
        page.on("dialog", lambda d: (dialogs.append(d.message), d.dismiss()))
        load(page)

        print("\n--- 1. The shape of every tip ---")
        shape = page.evaluate(SHAPE_JS)
        check("the four parts are armour, eyes, weapon and base", shape["parts"] == ["armour", "eyes", "weapon", "base"], shape["parts"])
        check("every tip has a unique key, a known part, colour, technique, advice, colours with a hex and a well-formed credit", not shape["bad"], shape["bad"][:3])
        check("there are tips, and the technique list is a short list of words", shape["n"] >= 3 and page.evaluate("MENTOR_TECHNIQUES.length >= 3 && MENTOR_TECHNIQUES.length <= 12 && MENTOR_TECHNIQUES.every(x => typeof x === 'string')"))
        check("one sample tip shows the optional credit and at least one has none",
              page.evaluate("MENTOR_TIPS.some(x => x.credit) && MENTOR_TIPS.some(x => !x.credit)"))

        print("\n--- 2. The words ---")
        everything = page.evaluate(TEXT_JS)
        hits = GW_WORDS.findall(everything) + GW_MORE.findall(everything)
        check("no Games Workshop game, faction, scheme, paint or product is named", not hits, hits[:5])
        check("no em dash and no angle brackets in any tip", "—" not in everything and "<" not in everything and ">" not in everything)

        print("\n--- 3. The loader ---")
        ask = lambda a: page.evaluate("a => mentorTipsFor(a).map(x => x.key)", a)
        total = shape["n"]
        check("asking for nothing gives every tip", len(ask({})) == total and page.evaluate("mentorTipsFor().length") == total)
        eyes = ask({"part": "eyes"})
        check("a part gives only that part's tips", eyes and page.evaluate("p => mentorTipsFor({ part: p }).every(x => x.part === p)", "eyes"))
        check("technique and colour match on words, capitals ignored", ask({"technique": "LAYER"}) and ask({"colour": "Cold BLUE"}) and "sample-armour" in ask({"technique": "layer", "colour": "blue"}))
        check("asking for two things narrows to tips that fit both", ask({"part": "eyes", "technique": "Layer"}) == [])
        check("nothing matching gives an empty list, not an error", ask({"colour": "no such colour"}) == [] and ask({"part": "nothing"}) == [])
        # the file really missing: block it and load the app
        page2 = ctx.new_page()
        page2.route("**/mentor-tips.js*", lambda r: r.abort())
        page2.on("pageerror", lambda x: errors.append("blocked-file page: " + str(x)))
        t.load(page2)
        check("with mentor-tips.js missing the app still runs and the loader gives no tips",
              page2.evaluate("typeof MENTOR_TIPS === 'undefined' && Array.isArray(mentorTipsFor()) && mentorTipsFor({ part: 'eyes' }).length === 0"))
        page2.close()

        print("\n--- 4. Samples and real tips ---")
        check("the three starter tips are all marked as samples and say so", shape["samples"] == shape["n"] and page.evaluate("MENTOR_TIPS.every(x => x.sample !== true || /^Sample tip/.test(x.advice))"))
        check("a tip that is not a sample has real advice (more than a few words)", page.evaluate("MENTOR_TIPS.every(x => x.sample === true || x.advice.trim().split(/\\\\s+/).length >= 5)"))

        print("\n--- 5. Errors ---")
        check("no page errors", not errors, errors)
        check("no browser pop-ups", not dialogs, dialogs)
        browser.close()
    failed = results.count(False)
    print(f"\n{len(results) - failed} passed, {failed} failed")
    sys.exit(1 if failed else 0)

if __name__ == "__main__":
    main()
