"""Test (v18a): Copy as text -> Paste recipes round trip.

A recipe you copy with "Copy as text" should paste straight back in as the SAME recipe:
the same steps, techniques, paints, mix ratios and amounts, coats, notes and optional
flags, using the paints already in your palette (no new paints added).

v17.1 got simple recipes right but broke recipes with a ratio mix ("1:2"), even mixes
("Nuln Oil + Lahmian Medium") and basing materials ("Texture Sand"). Fixed in v18b:
Copy as text now always writes the ratio, so an even mix comes back as "1:1"; this test
counts "1:1" and no ratio as the same thing (both mean equal parts).

How it works: it loads a small recipe book into the app, then for each recipe it takes the
text "Copy as text" would copy (the app's own recipeToText), pastes it into Paste recipes,
presses Read notes and Save, and compares the new recipe with the original.

Serve the repo folder first (run_all.py does this for you), then run:
python3 tests/test_v18_round_trip.py
The port comes from the SOG_PORT environment variable, or 8765 if it isn't set."""
import json, os, re, sys
from playwright.sync_api import sync_playwright

PORT = os.environ.get("SOG_PORT", "8765")
BASE = f"http://localhost:{PORT}"

def paint(pid, name, brand="Citadel", **extra):
    return {"id": pid, "brand": brand, "name": name, "colour": "#3b5b7a", "status": "owned", **extra}

PAINTS = [
    paint(1, "Mephiston Red"), paint(2, "Agrax Earthshade"), paint(3, "Skeleton Horde"),
    paint(4, "Contrast Medium"), paint(5, "Kantor Blue"), paint(6, "White Scar"),
    paint(7, "Nuln Oil"), paint(8, "Lahmian Medium"),
    paint(9, "Sand", brand="", type="material"),
]

def step(technique, paints, ratio="", coats=1, note="", optional=False):
    """paints: a list of (paint id, mix %)."""
    return {"technique": technique, "coats": coats, "ratio": ratio, "note": note, "optional": optional,
            "paints": [{"paint": pid, "mix": mix} for pid, mix in paints]}

# The recipes to send round. "why" says what each one tests.
RECIPES = [
    {"id": 1, "name": "Cloak", "part": "Cloak", "notes": "", "why": "a simple recipe (already works)",
     "steps": [step("Base coat", [(1, 100)]), step("Wash", [(2, 100)], coats=2)]},
    {"id": 2, "name": "Skin", "part": "Skin", "notes": "", "why": "a 1:2 Contrast mix",
     "steps": [step("Contrast", [(3, 33), (4, 67)], ratio="1:2")]},
    {"id": 3, "name": "Armour", "part": "Armour", "notes": "", "why": "a 3:1 Wet blend mix",
     "steps": [step("Wet blend", [(5, 75), (6, 25)], ratio="3:1"), step("Wash", [(2, 100)])]},
    {"id": 4, "name": "Gems", "part": "Gems", "notes": "", "why": "an even mix (no ratio written)",
     "steps": [step("Wash", [(7, 50), (8, 50)])]},
    {"id": 5, "name": "Ground", "part": "Base", "notes": "", "why": "Texture Sand (a basing material)",
     "steps": [step("Texture", [(9, 100)]), step("Wash", [(2, 100)])]},
    {"id": 6, "name": "Edges", "part": "Armour", "notes": "Keep it neat", "why": "a note, 2 coats and an optional step",
     "steps": [step("Edge highlight", [(6, 100)], coats=2, note="thin it down", optional=True)]},
]

BOOK = {"paints": PAINTS, "recipes": [{k: v for k, v in r.items() if k != "why"} for r in RECIPES],
        "schemes": [], "v15": True}

# A recipe cut down to what should survive the round trip (paint names, not ids).
SUMMARY_JS = """([book, id]) => {
  const r = book.recipes.find(x => x.id === id);
  const name = pid => { const p = book.paints.find(x => x.id === pid); return p ? p.name : "?"; };
  return { notes: (r.notes || "").trim(), steps: r.steps.map(s => ({
    technique: s.technique, coats: s.coats, ratio: s.ratio || "", note: s.note || "", optional: !!s.optional,
    paints: s.paints.map(sp => name(sp.paint)), mix: s.paints.map(sp => sp.mix) })) };
}"""

def even_as_blank(ratio):
    """An equal-parts ratio ("1:1", "1:1:1") means the same as no ratio: an even mix."""
    parts = re.split(r"[:/]", ratio) if ratio else []
    return "" if parts and len(set(parts)) == 1 else ratio

results = []
def check(name, ok, detail=""):
    results.append(bool(ok))
    print(("PASS " if ok else "FAIL ") + name + ("" if ok else f"  -> {detail}"))

def read_book(page):
    return json.loads(page.evaluate("localStorage.getItem('shades-of-grey-recipes') || '{}'"))

def main():
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(viewport={"width": 390, "height": 844})
        errors = []
        page.on("pageerror", lambda e: errors.append(str(e)))
        # Start with no units (no example units) and the recipe book above.
        page.goto(f"{BASE}/manifest.json")
        page.evaluate("""book => { localStorage.clear(); localStorage.setItem('mini-tracker-models', '[]');
                         localStorage.setItem('shades-of-grey-recipes', JSON.stringify(book)); }""", BOOK)
        page.goto(f"{BASE}/index.html")
        page.wait_for_timeout(300)
        start_book = read_book(page)
        check("the test recipe book loaded", len(start_book.get("recipes", [])) == len(RECIPES),
              f"{len(start_book.get('recipes', []))} recipes loaded")

        for recipe in RECIPES:
            label = f"round trip: {recipe['name']} ({recipe['why']})"
            before = read_book(page)
            original = page.evaluate(SUMMARY_JS, [before, recipe["id"]])
            # Exactly what the "Copy as text" button copies.
            text = page.evaluate("id => recipeToText(book.recipes.find(r => r.id === id))", recipe["id"])

            page.evaluate("startImport()")   # what "Paste recipes from your notes" does
            page.fill("#import-text", text)
            page.click("#import-page button.primary-button")   # "Read notes"
            page.wait_for_timeout(100)
            save = page.locator("#import-save")
            if save.count() != 1 or save.is_disabled():
                why = "no preview" if save.count() != 1 else f"Save is blocked: {save.inner_text()!r}"
                check(label, False, f"{why}. Copied text was: {text!r}")
                continue
            save.click()
            page.wait_for_timeout(150)

            after = read_book(page)
            old_ids = {r["id"] for r in before["recipes"]}
            new = [r for r in after["recipes"] if r["id"] not in old_ids]
            if len(new) != 1:
                check(label, False, f"made {len(new)} recipes, want 1 ({[r['name'] for r in new]}). "
                                    f"Copied text was: {text!r}")
                continue
            pasted = page.evaluate(SUMMARY_JS, [after, new[0]["id"]])
            diffs = []
            if len(pasted["steps"]) != len(original["steps"]):
                diffs.append(f"{len(pasted['steps'])} steps, want {len(original['steps'])}")
            for i, (got, want) in enumerate(zip(pasted["steps"], original["steps"]), 1):
                for key in want:
                    g, w = got[key], want[key]
                    if key == "ratio":   # Copy as text writes an even mix as "1:1"
                        g, w = even_as_blank(g), even_as_blank(w)
                    if g != w:
                        diffs.append(f"step {i} {key} is {got[key]!r}, want {want[key]!r}")
            if pasted["notes"] != original["notes"]:
                diffs.append(f"notes {pasted['notes']!r}, want {original['notes']!r}")
            check(label, not diffs, "; ".join(diffs) + f". Copied text was: {text!r}")

            added = [p["name"] for p in after["paints"] if p["id"] not in {x["id"] for x in before["paints"]}]
            check(f"round trip: {recipe['name']} adds no new paints", not added, f"added {added}")

        check("no page errors", not errors, errors)
        browser.close()

    print(f"\n{sum(results)} of {len(results)} checks passed")
    sys.exit(0 if all(results) else 1)

if __name__ == "__main__":
    main()
