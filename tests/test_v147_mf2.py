"""Chunk MF2 tests for Minifolio: Mentor fixes from the v146 spot check. New behaviour only.

1. "how do I paint <colour> <part>" gets a how-to, not a Colour Lab pairing list; the exact title comes first.
2. A lone common noun does not make an answer ("how tall is a tree").
3. "paint is too watery" goes to the paint-thickness guides; "bubbles in my paint" is not the airbrush guide.
4. The colour line names the part that was asked.
5. A recipe or basing answer starts with its summary, with no "Title:" in front.
Run all tests with `python3 tests/run_all.py`, or serve the repo folder and run this file on its own."""
import os, sys
from playwright.sync_api import sync_playwright

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import test_v24 as t

results = []

def check(name, ok, detail=""):
    results.append(bool(ok))
    print(("PASS " if ok else "FAIL ") + name + ("" if ok else f"  -> {detail}"))

ASK = """(qs) => qs.map((q) => { const a = MinifolioMentor.mentorAnswer(q, { index: knowledgeIndex(), paints: [], tips: MENTOR_TIPS });
    return { q, kind: a.kind, band: a.band || '', lead: a.lead, keys: (a.sources || []).map(s => s.key), types: (a.sources || []).map(s => s.type) }; })"""

def main():
    errors, dialogs = [], []
    with sync_playwright() as p:
        browser = p.chromium.launch()
        ctx = browser.new_context(viewport={"width": 390, "height": 844}, service_workers="block", reduced_motion="reduce")
        page = ctx.new_page()
        page.on("pageerror", lambda x: errors.append(str(x)))
        page.on("dialog", lambda d: (dialogs.append(d.message), d.dismiss()))
        t.fresh(page)

        def ask(*qs):
            return {a["q"]: a for a in page.evaluate(ASK, list(qs))}

        print("\n--- 1. Colour and part questions ---")
        g = ask("how do I paint black armour", "how do I paint blue armour", "how do I paint a green cloak", "black armour", "how do I paint a grey cloak")
        check("'how do I paint black armour' shows the guide with that exact title first",
              g["how do I paint black armour"]["kind"] == "answer" and g["how do I paint black armour"]["keys"][0] == "painting-black-armour", g["how do I paint black armour"])
        check("'how do I paint blue armour' and 'a green cloak' get an entry, not the pairing list",
              all(g[q]["kind"] == "answer" and g[q]["types"][0] != "colour-lab" for q in ["how do I paint blue armour", "how do I paint a green cloak"]), [g["how do I paint blue armour"], g["how do I paint a green cloak"]])
        check("with no 'how do I paint', a colour and a part is still the pairing list", g["black armour"]["kind"] == "colour", g["black armour"])
        check("a colour and part with no entry that fits keeps the colour rule's answer path (no error, a clear reply)", g["how do I paint a grey cloak"]["kind"] in ("answer", "colour"), g["how do I paint a grey cloak"])

        print("\n--- 2. A lone common noun ---")
        n = ask("how tall is a tree", "how do I paint trees", "tree", "my brush is splitting")
        check("'how tall is a tree' gets 'I do not know that yet.'", n["how tall is a tree"]["kind"] == "none", n["how tall is a tree"])
        check("a tree question about painting, and the word alone, still answer", n["how do I paint trees"]["kind"] == "answer" and n["tree"]["kind"] == "answer", [n["how do I paint trees"], n["tree"]])
        check("a normal two-word question is untouched", n["my brush is splitting"]["keys"][0] == "split-or-hooked-brush-tips", n["my brush is splitting"])

        print("\n--- 3. Watery paint and bubbles ---")
        w = ask("paint is too watery", "my paint is too runny", "paint too thin", "bubbles in my paint", "airbrush bubbles", "how do I make water on a base")
        thick = {"thinning-paint", "paint-consistency-by-technique"}
        check("'too watery', 'too runny' and 'too thin' go to the paint-thickness guides first",
              all(w[q]["keys"][0] in thick for q in ["paint is too watery", "my paint is too runny", "paint too thin"]), [w[q]["keys"] for q in ["paint is too watery", "my paint is too runny", "paint too thin"]])
        check("'bubbles in my paint' does not go to the airbrush guide", "fix-airbrush-bubbling" not in w["bubbles in my paint"]["keys"][:1] and w["bubbles in my paint"]["keys"][0] in ("wet-palette-problems", "pre-mixing-colours"), w["bubbles in my paint"])
        check("'airbrush bubbles' still goes to it, and water on a base still goes to the puddles",
              w["airbrush bubbles"]["keys"][0] == "fix-airbrush-bubbling" and w["how do I make water on a base"]["keys"][0] == "puddles-and-water", [w["airbrush bubbles"], w["how do I make water on a base"]])

        print("\n--- 4. The part in the colour line ---")
        c = ask("blue cloak", "red base", "red eyes", "blue armour")
        check("the colour line names the part asked", "the cloak" in c["blue cloak"]["lead"] and "the base" in c["red base"]["lead"] and "armour" not in c["blue cloak"]["lead"], [c["blue cloak"]["lead"], c["red base"]["lead"]])
        check("armour and eyes keep their own names", "armour" in c["blue armour"]["lead"] and "eyes" in c["red eyes"]["lead"], [c["blue armour"]["lead"], c["red eyes"]["lead"]])

        print("\n--- 5. Recipe and basing leads ---")
        r = ask("how do I paint gold", "gold metal")
        for q in r:
            lead = r[q]["lead"]
            check(f"'{q}' (a recipe) starts with its summary, not 'Gold metal:'", r[q]["types"][0] == "recipe" and not lead.startswith("Gold metal") and lead.startswith("Rich gold"), r[q])

        check("no page errors", not errors, errors)
        check("no browser pop-ups", not dialogs, dialogs)
        browser.close()
    print(f"\n{sum(results)}/{len(results)} checks passed")
    return all(results)

if __name__ == "__main__":
    sys.exit(0 if main() else 1)
