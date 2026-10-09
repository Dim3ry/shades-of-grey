"""v15 tests for Shades of Grey (recipe fixes B1-B4 and basing materials). Serve the repo folder with
`python3 -m http.server 8765`, then run: python3 tests/test_v15.py <folder for screenshots>."""
import json, sys
from playwright.sync_api import sync_playwright

URL = "http://localhost:8765/index.html"
SHOTS = sys.argv[1] if len(sys.argv) > 1 else "."
results = []
def check(name, ok, detail=""):
    results.append(bool(ok))
    print(("PASS " if ok else "FAIL ") + name + ("" if ok else f"  -> {detail}"))

# A recipe book saved by v14: no "v15" mark, own parts list without "Whole model", old-style steps.
OLD_BOOK = {
    "parts": ["Armour", "Eyes", "Base"],
    "techniques": ["Prime", "Base coat", "Wash"],
    "paints": [{"id": 1, "brand": "Citadel", "name": "Nuln Oil", "colour": "#222222"},
               {"id": 2, "brand": "Citadel", "name": "Macragge Blue", "colour": "#1f3a8a"}],
    "recipes": [{"id": 1, "name": "Blue armour", "part": "Armour", "notes": "",
                 "steps": [{"technique": "Base coat", "coats": 2, "paints": [{"paint": 2, "mix": None}]},
                           {"technique": "Wash", "coats": 1, "paints": [{"paint": 1, "mix": None}]}]}],
    "schemes": [],
}

with sync_playwright() as pw:
    browser = pw.chromium.launch()
    for size, (w, h) in {"phone": (390, 844), "desktop": (1280, 900)}.items():
        page = browser.new_page(viewport={"width": w, "height": h})
        errors = []
        page.on("pageerror", lambda e: errors.append(str(e)))
        page.goto(URL)
        page.evaluate("b => { localStorage.clear(); localStorage.setItem('shades-of-grey-recipes', JSON.stringify(b)); }", OLD_BOOK)
        page.reload()
        page.wait_for_timeout(300)

        if size == "phone":
            # Old data upgraded once, nothing lost.
            b = page.evaluate("book")
            check("upgrade: Whole model added and first", b["parts"][0] == "Whole model", b["parts"])
            check("upgrade: own parts kept", b["parts"][1:] == ["Armour", "Eyes", "Base"], b["parts"])
            check("upgrade: Technical/Texture/Varnish added", all(t in b["techniques"] for t in ["Technical", "Texture", "Varnish"]), b["techniques"])
            check("upgrade: old steps kept", b["recipes"][0]["steps"][0]["coats"] == 2 and b["recipes"][0]["steps"][0]["technique"] == "Base coat")
            check("upgrade: new step fields have defaults", b["recipes"][0]["steps"][0]["note"] == "" and b["recipes"][0]["steps"][0]["optional"] is False and b["recipes"][0]["steps"][0]["ratio"] == "")
            # Removing Whole model sticks after the one-off upgrade.
            again = page.evaluate("""() => { const c = JSON.parse(JSON.stringify(book)); c.parts = c.parts.filter(p => p !== 'Whole model');
                                            return cleanRecipeBook(c).parts; }""")
            check("removed Whole model stays removed", "Whole model" not in again, again)
            moved = page.evaluate("cleanRecipeBook({ v15: true, parts: ['Eyes', 'Whole model'] }).parts")
            check("Whole model always listed first", moved[0] == "Whole model", moved)
            fresh = page.evaluate("cleanRecipeBook(null).parts[0]")
            check("new users start with Whole model", fresh == "Whole model", fresh)

            # B1 technique guesses.
            cases = {
                "Nuln Oil": "Wash", "Agrax": "Wash", "Seraphim Sepia": "Wash", "Pink Horror": "Layer",
                "Black Templar": "Contrast", "Bleck Templar Contrast": "Contrast", "Luxion Purple": "Contrast",
                "'Ardcoat": "Varnish", "Ardcoat Gloss": "Varnish", "Agrellan Earth": "Texture", "Nurgle's Rot": "Technical",
                "Macragge Blue": "Layer", "Chaos Black Spray": "Prime", "Rocks": "Texture", "Static grass": "Texture",
            }
            for name, want in cases.items():
                got = page.evaluate("n => guessTechnique([{ brand: 'Citadel', name: n }])", name)
                check(f"guess: {name} -> {want}", got == want, got)
            got = page.evaluate("guessTechnique([{ name: 'Baal Red' }, { name: 'Contrast Medium' }])")
            check("guess: Contrast + Contrast Medium -> Contrast", got == "Contrast", got)
            check("guess: no paints -> blank", page.evaluate("guessTechnique([])") == "")

            # B3 ratios.
            for ratio, n, want in [("2:1", 2, [67, 33]), ("1:1:2", 3, [25, 25, 50]), ("50/50", 2, [50, 50]),
                                   ("1:1:1", 3, [34, 33, 33]), ("2:1", 3, None), ("abc", 2, None), (" 4 : 1 ", 2, [80, 20])]:
                got = page.evaluate("([r, n]) => ratioPercents(r, n)", [ratio, n])
                check(f"ratio {ratio!r} x{n} -> {want}", got == want, got)
                if want:
                    check(f"ratio {ratio!r} adds to 100", sum(got) == 100)

            # Materials.
            mats = page.evaluate("['Rocks', 'AK and rocks', 'Snow', 'Static grass', 'Texture paste', 'Macragge Blue', 'Ice Yellow', 'Sandy Brown'].map(n => isMaterial({ name: n }))")
            check("materials spotted by name", mats == [True, True, True, True, True, False, False, False], mats)

        # Build a recipe through the editor: blank technique, ratio, note, optional, a material.
        page.evaluate("startNewRecipe(null)")
        page.wait_for_timeout(200)
        page.evaluate("""() => {
          const d = recipeDraft;
          d.name = 'Red brains'; d.part = 'Eyes';
          d.steps = [
            { technique: '', coats: 1, ratio: '', note: 'heavier on the top', optional: false,
              paints: [{ brand: 'Citadel', name: 'Corax White', colour: '#ffffff', mix: 100 }] },
            { technique: '', coats: 1, ratio: '1:1', note: '', optional: false,
              paints: [{ brand: 'Citadel', name: 'Baal Red', colour: '#aa1111', mix: 50 },
                       { brand: '', name: 'Contrast Medium', colour: '#808080', mix: 50 }] },
            { technique: '', coats: 1, ratio: '', note: '', optional: true,
              paints: [{ brand: 'Citadel', name: "'Ardcoat", colour: '#808080', mix: 100 }] },
            { technique: '', coats: 1, ratio: '', note: '', optional: false,
              paints: [{ brand: '', name: 'Rocks', colour: '#808080', mix: 100 }] },
          ];
          renderRecipeEditor();
        }""")
        page.wait_for_timeout(200)
        sel = page.locator(".step-edit select").first.locator("option").first.text_content()
        check(f"{size}: editor shows Auto guess", sel.startswith("Auto"), sel)
        auto2 = page.locator(".step-edit").nth(1).locator("select option").first.text_content()
        check(f"{size}: editor guesses Contrast for step 2", auto2 == "Auto: Contrast", auto2)
        check(f"{size}: ratio box shown for mixed step", page.locator(".step-edit").nth(1).locator("input[aria-label='Mix ratio']").count() == 1)
        check(f"{size}: no ratio box for single paint", page.locator(".step-edit").nth(0).locator("input[aria-label='Mix ratio']").count() == 0)
        # Typing a ratio fills in the %s.
        box = page.locator(".step-edit").nth(1).locator("input[aria-label='Mix ratio']")
        box.fill("2:1")
        mixes = page.locator(".step-edit").nth(1).locator("input[aria-label='Mix %']").evaluate_all("els => els.map(e => e.value)")
        check(f"{size}: typing 2:1 sets 67/33", mixes == ["67", "33"], mixes)
        box.fill("2:1:1")
        warn = page.locator(".step-edit").nth(1).locator(".mix-warning").text_content()
        check(f"{size}: wrong ratio length warns", "needs 2 numbers" in warn, warn)
        box.fill("2:1")
        page.screenshot(path=f"{SHOTS}/v15-{size}-editor.png", full_page=True)

        page.evaluate("saveRecipeDraft()")
        page.wait_for_timeout(300)
        saved = page.evaluate("JSON.parse(localStorage.getItem('shades-of-grey-recipes'))")
        r = [x for x in saved["recipes"] if x["name"] == "Red brains"][0]
        check(f"{size}: saved blank technique", r["steps"][0]["technique"] == "", r["steps"][0])
        check(f"{size}: saved note", r["steps"][0]["note"] == "heavier on the top")
        check(f"{size}: saved ratio", r["steps"][1]["ratio"] == "2:1", r["steps"][1])
        check(f"{size}: saved optional", r["steps"][2]["optional"] is True)
        cm = [p for p in saved["paints"] if p["name"] == "Contrast Medium"][0]
        check(f"{size}: Contrast Medium gets Citadel brand and colour", cm["brand"] == "Citadel" and cm["colour"] != "#808080", cm)
        rocks = [p for p in saved["paints"] if p["name"] == "Rocks"][0]
        check(f"{size}: Rocks saved as a material", rocks.get("type") == "material", rocks)
        check(f"{size}: saved book marked v15", saved.get("v15") is True)

        # The recipe page.
        text = page.locator("#recipe-page").inner_text() if page.locator("#recipe-page").count() else page.inner_text("body")
        check(f"{size}: view shows guessed Layer", "1. Layer" in text, text[:300])
        check(f"{size}: view shows Contrast and mix ratio", "2. Contrast" in text and "mix 2:1" in text)
        check(f"{size}: view shows Varnish (optional)", "3. Varnish" in text and "(optional)" in text)
        check(f"{size}: view shows Texture for rocks", "4. Texture" in text)
        check(f"{size}: view shows note", "heavier on the top" in text)
        check(f"{size}: optional step faded", page.locator("li.optional-step").count() == 1)
        page.screenshot(path=f"{SHOTS}/v15-{size}-recipe.png", full_page=True)

        # Palette: rocks are a basing material, last in colour order, not "needs a colour".
        page.evaluate("showTab('recipes')")
        has_palette = page.evaluate("typeof renderPalette === 'function'")
        if has_palette:
            page.evaluate("settings.paintSort = 'colour'; renderPalette()")
            names = page.locator(".paint-item .name").all_text_contents()
            check(f"{size}: material last in colour sort", names and names[-1] == "Rocks", names)
            details = page.locator(".paint-item .details").all_text_contents()
            check(f"{size}: material labelled basing material", any("basing material" in d for d in details), details)

        check(f"{size}: no page errors", not errors, errors)
        page.close()
    browser.close()

print(f"\n{sum(results)}/{len(results)} passed")
sys.exit(0 if all(results) else 1)
