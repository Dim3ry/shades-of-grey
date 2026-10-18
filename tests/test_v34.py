"""v34 tests for Minifolio (IP tidy): the examples a brand-new start comes with, and the hints in the boxes and in Help, now use
plain made-up names instead of well-known game, army and paint names. Nothing saved is read differently.

What is checked:
1. Versions: APP_VERSION v34, sw.js v34, every script tag ?v=34, a v34 Updates entry that is the newest, and the Updates entry
   text is free of Games Workshop words.
2. A brand-new start: the 3 example units, 5 example recipes, 2 example schemes and 16 example paints use only plain names (scanned with the same
   Games Workshop word lists as the library tests), the paints have no brand and a real colour, the units are marked as examples,
   the recipes are linked to the right units, and the example card says so.
3. The reworded hints: the box hints (game, palette search, army list game and faction) and the Help lines are free of those
   words, and the old example wording is gone from index.html.
4. Nothing saved changes: units saved by v21 to v33 with the old example names, marks and recipes are left exactly as they were;
   unmarked old examples are still recognised once (as before); the backup reminder still treats old examples as examples.
5. Safety: no markup is created from the new text (the example card has only the usual tags), nothing runs, and a fresh start
   makes no request to any other address (offline).
6. Fresh start, dashboard and Recipes tab, dark and light at 390 and 360 px: nothing scrolls sideways, the example cards show.
Run all tests with `python3 tests/run_all.py`, or serve the repo folder and run this file on its own."""
import json, os, re, sys
from playwright.sync_api import sync_playwright

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import test_v31 as t   # the helpers and the Games Workshop word lists

URL, read, shot, no_sideways = t.URL, t.read, t.shot, t.no_sideways
GW_WORDS, GW_MORE = t.GW_WORDS, t.GW_MORE
results = []

def check(name, ok, detail=""):
    results.append(bool(ok))
    print(("PASS " if ok else "FAIL ") + name + ("" if ok else f"  -> {detail}"))

# extra words from the old examples and the old hints
OLD_WORDS = re.compile(r"\b(boyz|boy|liberators?|nuln|macragge|calgar|fenrisian|waaagh|agrax|warboss|skarsnik|baal|seraphim|ushabti|"
                       r"wraithbone|death guard|stormcast|eternals?|ork)\b", re.I)

def dirty(text):
    return bool(GW_WORDS.search(text) or GW_MORE.search(text) or OLD_WORDS.search(text))

def fresh(page, settings=None):
    page.goto(URL)
    page.evaluate("""(s) => { localStorage.clear(); if (s) localStorage.setItem('shades-of-grey-settings', JSON.stringify(s)); }""", settings)
    page.evaluate("""async () => { await new Promise(done => { const r = indexedDB.deleteDatabase('shades-of-grey-photos');
        r.onsuccess = r.onerror = r.onblocked = () => done(); }); }""")
    page.goto(URL)
    page.wait_for_timeout(500)

def main():
    with sync_playwright() as p:
        browser = p.chromium.launch()
        ctx = browser.new_context(viewport={"width": 390, "height": 844}, service_workers="block")
        page = ctx.new_page()
        errors, dialogs, requests = [], [], []
        page.on("pageerror", lambda e: errors.append(str(e)))
        page.on("dialog", lambda d: (dialogs.append(d.message), d.dismiss()))
        page.on("request", lambda r: requests.append(r.url))

        # ---------- 1. Versions ----------
        print("\n--- 1. Versions ---")
        fresh(page)
        html, sw = read("index.html"), read("sw.js")
        check("APP_VERSION is v34 or later", float(page.evaluate("APP_VERSION")[1:]) >= 34, page.evaluate("APP_VERSION"))
        check("sw.js VERSION is v34 or later", float(re.search(r'const VERSION = "v([\d.]+)"', sw).group(1)) >= 34)
        tags = re.findall(r'<script src="[^"]+\?v=(\d+)"', html)
        check("every script tag carries the same ?v= number, 34 or later", tags and len(set(tags)) == 1 and float(tags[0]) >= 34, tags)
        entry = page.evaluate("CHANGELOG.find(r => r.version === 'v34')")
        check("Updates has a v34 entry with at least two lines", entry and len(entry["changes"]) >= 2, entry)
        check("the newest Updates entry is v34 or later", float(page.evaluate("CHANGELOG[0].version")[1:]) >= 34)
        check("the v34 Updates entry has no Games Workshop words", entry and not dirty(" ".join(entry["changes"])), entry)
        check("the Pro preview label is still there", "Pro preview" in read("app.js"))

        # ---------- 2. A brand-new start ----------
        print("\n--- 2. A brand-new start ---")
        fresh(page)
        units = json.loads(page.evaluate("localStorage.getItem('mini-tracker-models')"))
        check("3 example units, all marked as examples", len(units) == 3 and all(u.get("example") is True for u in units), units)
        check("the example units use plain made-up names",
              [u["name"] for u in units] == ["Captain", "Brutes", "Guardians"]
              and [u["faction"] for u in units] == ["Blue army", "Green army", "Gold army"]
              and [u["hobby"] for u in units] == ["Sci-fi", "Sci-fi", "Fantasy"], units)
        check("no unit text has a Games Workshop word", not dirty(json.dumps(units)), units)
        book = page.evaluate("book")
        check("5 example recipes with plain names (v44: was 2)", [r["name"] for r in book["recipes"]] == ["Blue armour", "Gold metal", "Green skin", "Glowing eyes", "Stone base"]
              and all(r.get("example") is True and len(r["steps"]) in (3, 4) for r in book["recipes"]), book["recipes"])
        paints = book["paints"]
        check("16 example paints, no brand, plain names, a real colour, marked (v44: was 8)",
              len(paints) == 16 and all(p["brand"] == "" and p["name"].startswith("Example ") and p.get("example") is True
                                       and re.match(r"^#[0-9a-f]{6}$", p["colour"]) and p["colour"] != "#808080" for p in paints), paints)
        check("no recipe, scheme or paint text has a Games Workshop word", not dirty(json.dumps(book["recipes"]) + json.dumps(book["schemes"]) + json.dumps(paints)))
        linked = page.evaluate("() => models.filter(m => m.recipes).map(m => [m.name, m.recipes.map(id => recipeById(id).name)])")
        check("the example units are linked to the example recipes that suit them (v44: more of them)",
              linked == [["Captain", ["Blue armour", "Gold metal", "Glowing eyes", "Stone base"]],
                         ["Brutes", ["Green skin", "Glowing eyes", "Stone base"]],
                         ["Guardians", ["Gold metal", "Stone base"]]], linked)
        page.click('button[data-tab="recipes"]'); page.wait_for_timeout(300)
        card = page.inner_text("#examples-card-recipes")
        check("the Recipes card counts the new examples in plain words", "5 example recipes" in card and "2 example schemes" in card and not dirty(card), card)
        check("Clear examples is offered", page.locator("#examples-card-recipes button").count() == 2)

        # ---------- 3. The reworded hints and Help ----------
        print("\n--- 3. Hints and Help ---")
        hints = page.evaluate("""() => ['hobby-input','palette-search','wh-game','wh-faction'].map(id => document.getElementById(id).getAttribute('placeholder'))""")
        check("the four box hints are plain", hints == ["Game, e.g. Sci-fi", "Search or add a paint, e.g. Mid Blue", "e.g. Sci-fi", "e.g. Green army"], hints)
        check("the box hints have no Games Workshop words", not any(dirty(h) for h in hints), hints)
        for sel in ["#help-example-recipes", "#help-faction-part"]:
            txt = page.evaluate("(s) => document.querySelector(s).textContent", sel)
            check(f"Help {sel} is plain", not dirty(txt), txt)
        for old in ['"Nuln Oill"', '"My Ultramarines"', "Baal Red:CM", "Seraphim Sepia 1:2", "Ushabti Bone", "Ultramarines armour and Ork skin",
                    "Ultramarines Blue.", 'e.g. 40K"', 'e.g. Tyranids"', "e.g. Macragge Blue"]:
            check(f"the old wording {old} is gone from index.html", old not in html)
        check("the Help lines about the Warhammer app import are still there (a plain statement of what it reads)",
              "From the Warhammer app" in html and "Only unit names and model counts are kept" in html)
        check("the unofficial wording is unchanged", "Unofficial fan-made app" in html and "not affiliated with or endorsed by Games Workshop" in html)

        # ---------- 4. Nothing saved changes ----------
        print("\n--- 4. Saved data is left alone ---")
        old_units = [
            {"id": 1, "name": "Captain", "hobby": "40K", "faction": "Ultramarines", "stage": 3, "count": 1, "example": True},
            {"id": 2, "name": "Boyz", "hobby": "40K", "faction": "Orks", "stage": 0, "count": 10, "example": True},
            {"id": 3, "name": "Liberators", "hobby": "Age of Sigmar", "faction": "Stormcast Eternals", "stage": 6, "count": 5, "example": True},
        ]
        old_book = {"paints": [{"id": 1, "brand": "Citadel", "name": "Macragge Blue", "colour": "#0d407f", "example": True}],
                    "parts": ["Armour"], "techniques": ["Base coat"], "schemes": [], "shorthand": {},
                    "recipes": [{"id": 1, "name": "Ultramarines armour", "part": "Armour", "notes": "", "example": True,
                                 "steps": [{"technique": "Base coat", "coats": 2, "paints": [{"paint": 1, "mix": None}], "ratio": "", "note": "", "optional": False}]}]}
        page.goto(URL)
        page.evaluate("""([u, b]) => { localStorage.clear(); localStorage.setItem('mini-tracker-models', JSON.stringify(u));
            localStorage.setItem('shades-of-grey-recipes', JSON.stringify(b));
            localStorage.setItem('shades-of-grey-settings', JSON.stringify({examplesChecked: true, recipeExamplesChecked: true})); }""", [old_units, old_book])
        page.goto(URL); page.wait_for_timeout(500)
        now = json.loads(page.evaluate("localStorage.getItem('mini-tracker-models')"))
        check("units saved with the old example names are unchanged",
              [(u["name"], u["hobby"], u["faction"], u.get("example")) for u in now] == [(u["name"], u["hobby"], u["faction"], True) for u in old_units], now)
        rb = page.evaluate("book")
        check("a recipe and paint saved with the old names are unchanged",
              [r["name"] for r in rb["recipes"]] == ["Ultramarines armour"] and [(q["brand"], q["name"]) for q in rb["paints"]] == [("Citadel", "Macragge Blue")], rb)
        check("no example recipes or paints are added to someone who already has data", len(rb["recipes"]) == 1 and len(rb["paints"]) == 1)
        # unmarked old examples (saved before v21) are still recognised once
        unmarked = [{k: v for k, v in u.items() if k != "example"} for u in old_units]
        page.evaluate("""(u) => { localStorage.clear(); localStorage.setItem('mini-tracker-models', JSON.stringify(u)); }""", unmarked)
        page.goto(URL); page.wait_for_timeout(500)
        check("old examples saved before v21 are still recognised and marked",
              all(u.get("example") is True for u in json.loads(page.evaluate("localStorage.getItem('mini-tracker-models')"))))
        # a renamed one is yours
        renamed = [dict(unmarked[0], name="Chapter Master")] + unmarked[1:]
        page.evaluate("""(u) => { localStorage.clear(); localStorage.setItem('mini-tracker-models', JSON.stringify(u)); }""", renamed)
        page.goto(URL); page.wait_for_timeout(500)
        marks = [u.get("example") is True for u in json.loads(page.evaluate("localStorage.getItem('mini-tracker-models')"))]
        check("a renamed old example is not marked", marks[0] is False and marks[1:] == [True, True], marks)
        # the new examples are recognised too, if unmarked
        new_unmarked = [{"id": 1, "name": "Captain", "hobby": "Sci-fi", "faction": "Blue army", "stage": 3, "count": 1}]
        page.evaluate("""(u) => { localStorage.clear(); localStorage.setItem('mini-tracker-models', JSON.stringify(u)); }""", new_unmarked)
        page.goto(URL); page.wait_for_timeout(500)
        check("an unmarked new-style example is recognised too", json.loads(page.evaluate("localStorage.getItem('mini-tracker-models')"))[0].get("example") is True)

        # ---------- 5. Safety and offline ----------
        print("\n--- 5. Safety and offline ---")
        requests.clear()
        fresh(page)
        page.click('button[data-tab="recipes"]'); page.wait_for_timeout(300)
        tags_in_card = page.evaluate("() => [...new Set([...document.querySelectorAll('#examples-card-recipes *, #examples-card-dash *')].map(e => e.tagName))].sort()")
        check("the example cards contain only the usual tags", set(tags_in_card) <= {"P", "STRONG", "BUTTON", "DIV"}, tags_in_card)
        check("no script ran and nothing was injected", page.evaluate("() => window.__pwned === undefined && !document.querySelector('#view-recipes img')"))
        outside = [u for u in requests if not u.startswith(t.BASE) and not u.startswith("data:") and not u.startswith("blob:")
                   and "goatcounter" not in u]
        check("a fresh start makes no request to any other address", not outside, outside)
        check("no page errors or dialogs", not errors and not dialogs, (errors, dialogs))

        # ---------- 6. Screens ----------
        print("\n--- 6. Fresh start on screen ---")
        for appearance in ["dark", "light"]:
            for width in [390, 360]:
                tag = f"{appearance} {width}px"
                page.set_viewport_size({"width": width, "height": 844})
                fresh(page, {"appearance": appearance})
                check(f"{tag}: the dashboard shows the examples card and the three example units",
                      page.is_visible("#examples-card-dash") and all(n in page.inner_text("#view-dashboard") for n in ["Captain", "Brutes", "Guardians"]),
                      page.inner_text("#view-dashboard")[:200])
                check(f"{tag}: dashboard, nothing scrolls sideways", no_sideways(page))
                shot(page, f"v34-dashboard-{appearance}-{width}.png")
                page.click('button[data-tab="recipes"]'); page.wait_for_timeout(300)
                check(f"{tag}: the Recipes tab shows the examples card", page.is_visible("#examples-card-recipes"))
                check(f"{tag}: recipes, nothing scrolls sideways", no_sideways(page))
                shot(page, f"v34-recipes-{appearance}-{width}.png")
        browser.close()
    print(f"\n{sum(results)}/{len(results)} checks passed")
    sys.exit(0 if all(results) else 1)

if __name__ == "__main__":
    main()
