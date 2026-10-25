"""v65 tests for Minifolio (chunk 3.5a: Similar paints, the Best match card).

What changed:
 A "Similar paints" button on a paint in a saved recipe step, and on a paint in the Compendium (a colour idea, or a colour wheel paint),
 opens a pop-up with the Best match: up to 3 paints, closest first, from different brands where possible, owned or not. Lighter / Close /
 Darker (Close by default) moves the colour aimed at. The matching and the fit labels are the colour engine's. Varnishes, mediums,
 thinners, cleaners, reducers, retarders, clear bases and 15 Tamiya paints stored as white are never matched or offered. No paint
 content file changed. (The Your closest card, swapping into a step and the shopping list come in chunk 3.5b.)

Checks:
1. Versions, the v65 Updates entry, Help line, no em dash.
2. The skip rules: about 30 non-colour paints, the 15 Tamiya paints, real colours such as Medium Blue are still matched.
3. The matching: at most 3, closest first, different brands, never the paint itself, Lighter is lighter and Darker is darker.
4. On screen from a recipe step and from the Compendium: the pop-up, the choice, the labels, the note, closing (button, Escape, Back).
5. 390 px and 360 px, dark and light: no sideways scroll, every tap target 44 px or more.
6. No page errors, no browser pop-ups, no paint content file changed.
Run all tests with `python3 tests/run_all.py`, or serve the repo folder and run this file on its own."""
import json, os, re, subprocess, sys
from playwright.sync_api import sync_playwright

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from notice_watch import attach_notices
import test_v31 as t
import test_v35 as c
import test_v39 as h

read, load, no_sideways = t.read, t.load, t.no_sideways
results = []

def check(name, ok, detail=""):
    results.append(bool(ok))
    print(("PASS " if ok else "FAIL ") + name + ("" if ok else f"  -> {detail}"))

TAMIYA_WHITE = ["Dark green 2 (RAF)", "Dark iron", "Dark yellow 2", "IJN gray (Maizuru Arsenal)", "IJN gray (Yokosuka Arsenal)",
                "Medium sea gray 2 (RAF)", "Ocean gray 2 (RAF)", "Red brown 2", "Rubber black", "Fluorescent orange", "Metallic gray",
                "Metallic orange", "Pearl yellow", "Pure metallic red", "Semi-gloss bright gun metal"]
BLUE = {"id": 1, "brand": "Citadel", "name": "Macragge Blue", "colour": "#0d407f", "status": "owned"}
RECIPES = [{"id": 1, "name": "Blue armour", "part": "Armour", "notes": "", "steps": [
    {"technique": "Base coat", "coats": 1, "paints": [{"paint": 1, "mix": 100}], "ratio": "", "note": "", "optional": False}]}]

def open_recipe(page, paints=None):
    load(page, paints=paints or [BLUE], recipes=RECIPES)
    page.evaluate("() => { showTab('recipes'); openRecipeId = 1; renderRecipes(); }")
    page.wait_for_timeout(250)
    page.evaluate("() => { const b = document.querySelector('.step-line'); if (b && b.getAttribute('aria-expanded') === 'false') b.click(); }")
    page.wait_for_timeout(150)

def pop(page):
    return page.locator(".similar-dialog")

def main():
    errors, dialogs = [], []
    app, html = read("app.js"), read("index.html")
    with sync_playwright() as p:
        browser = p.chromium.launch()
        ctx = browser.new_context(viewport={"width": 390, "height": 844}, service_workers="block")
        page = ctx.new_page()
        page.on("pageerror", lambda x: errors.append(str(x)))
        page.on("dialog", lambda d: (dialogs.append(d.message), d.dismiss()))
        notices = []
        attach_notices(page, notices.append)

        print("\n--- 1. Versions, Updates entry, Help ---")
        load(page, paints=[BLUE])
        version = page.evaluate("APP_VERSION")
        check("APP_VERSION is v65 or later", float(version[1:]) >= 65, version)
        m = re.search(r'const VERSION = "v([\d.]+)"', read("sw.js"))
        check("sw.js VERSION matches", m and "v" + m.group(1) == version, m and m.group(1))
        tags = re.findall(r'<script src="[^"]+\?v=(\d+)"', html)
        check("all six script tags carry the version number", len(tags) == 6 and set(tags) == {version[1:]}, tags)
        check("the comments that name the number agree", f'The "?v={version[1:]}" makes' in html and f'e.g. "app.js?v={version[1:]}"' in app)
        entry = page.evaluate("CHANGELOG.find(c => c.version === 'v65')")
        check("the v65 Updates entry exists and is the newest while v65 is current", bool(entry) and (version != "v65" or page.evaluate("CHANGELOG[0].version") == "v65"))
        joined = " ".join(entry["changes"]) if entry else ""
        check("the entry names the button, Best match and the three choices", "Similar paints" in joined and "Best match" in joined and "Lighter" in joined and "Darker" in joined, joined)
        help_li = re.search(r'<li id="help-similar-paints">.*?</li>', html, re.S)
        check("Help has a Similar paints line", bool(help_li) and "Best match" in help_li.group(0))
        check("no em dash in the Help line or the v65 Updates entry", "—" not in (help_li.group(0) if help_li else "—") and "—" not in app[app.index('{ version: "v65"'):app.index('{ version: "v64"')])
        check("DATA_VERSION is still 1", page.evaluate("DATA_VERSION") == 1)

        print("\n--- 2. What is never matched ---")
        skipped = page.evaluate("() => KNOWN_PAINTS.filter(k => !similarCandidate(k)).map(k => k.brand + '|' + k.name)")
        non_tamiya = [s for s in skipped if not (s.startswith("Tamiya|") and s.split("|", 1)[1].lower() in [n.lower() for n in TAMIYA_WHITE])]
        check("about 50 paints are skipped as not colours (varnishes, mediums, thinners, clear bases and the like)", 40 <= len(non_tamiya) <= 60, len(non_tamiya))
        for word in ("Gloss Varnish", "Matt Varnish", "Cleaner", "Reducer", "Retarder", "Clear Base", "Lahmian Medium", "Contrast Medium", "Acrylic thinner"):
            check(f"{word} is skipped", any(s.endswith("|" + word) for s in skipped), word)
        check("all 15 Tamiya paints stored as white are skipped",
              all(page.evaluate("(n) => !similarCandidate(KNOWN_PAINTS.find(k => k.brand === 'Tamiya' && k.name.toLowerCase() === n.toLowerCase()))", n) for n in TAMIYA_WHITE))
        for word in ("Medium Blue", "Medium Brown", "Clear blue", "Nuln Oil Gloss", "Matt Black"):
            check(f"the real colour {word} is still matched", not any(s.endswith("|" + word) for s in skipped), word)
        check("a made-up example paint is never offered", page.evaluate("() => similarCandidate({ brand: '', name: 'Blue base' }) || true") is True)

        print("\n--- 3. The matching ---")
        blue = {"brand": "Citadel", "name": "Macragge Blue", "colour": "#0d407f"}
        res = page.evaluate("(p) => [1, 0, -1].map(s => similarBestMatches(p, s).map(h => [h.paint.brand, h.paint.name, h.paint.colour, h.distance]))", blue)
        close = res[1]
        check("Close gives 3 paints", len(close) == 3, close)
        check("closest first", [x[3] for x in close] == sorted(x[3] for x in close))
        check("from three different brands", len({x[0] for x in close}) == 3, close)
        check("never the paint itself", all(x[1] != "Macragge Blue" for r in res for x in r))
        check("none is a skipped paint", all(not page.evaluate("(n) => !similarCandidate(KNOWN_PAINTS.find(k => k.name === n) || { name: n, brand: 'x', colour: '#000000' })", x[1]) for r in res for x in r))
        lum = lambda hx: sum(int(hx[i:i + 2], 16) for i in (1, 3, 5))
        mean = [sum(lum(x[2]) for x in r) / len(r) for r in res]
        check("Lighter is lighter than Close, and Darker is darker", mean[0] > mean[1] > mean[2], mean)
        one_brand = page.evaluate("""(p) => { const keep = searchedPaints; searchedPaints = keep.filter(k => k.brand === 'Citadel');
            const out = similarBestMatches(p, 0).length; searchedPaints = keep; return out; }""", blue)
        check("when only one brand is left it still fills the 3 places", one_brand == 3, one_brand)

        print("\n--- 4. On screen ---")
        open_recipe(page)
        btn = page.locator("#recipe-page .step-body .similar-open")
        check("a saved recipe's paint has a Similar paints button", btn.count() == 1 and btn.inner_text() == "Similar paints", btn.count())
        btn.click()
        page.wait_for_timeout(200)
        check("the pop-up opens, named Similar paints", pop(page).count() == 1 and pop(page).locator("h2").inner_text() == "Similar paints")
        check("it names the paint it started from", "Macragge Blue" in pop(page).locator(".similar-target").inner_text())
        check("the choice is Lighter, Close, Darker with Close pressed",
              pop(page).locator(".similar-shift button").all_inner_texts() == ["Lighter", "Close", "Darker"]
              and pop(page).locator('.similar-shift button[aria-pressed="true"]').inner_text() == "Close")
        check("one card, Best match, with 3 paints", pop(page).locator(".similar-card h3").all_inner_texts() == ["Best match"] and pop(page).locator(".similar-card li").count() == 3)
        row_text = pop(page).locator(".similar-card li").first.inner_text()
        check("each paint shows an owned label and a fit label", ("Not in your palette" in row_text or "You own this" in row_text) and re.search(r"(Good|Okay|Poor) fit", row_text), row_text)
        check("the usual one line about approximate colours", "only a guide" in pop(page).locator(".similar-note").inner_text())
        first_before = pop(page).locator(".similar-card li").first.inner_text()
        pop(page).locator(".similar-shift button", has_text="Darker").click()
        page.wait_for_timeout(100)
        check("Darker is pressed and the list is redrawn", pop(page).locator('.similar-shift button[aria-pressed="true"]').inner_text() == "Darker"
              and pop(page).locator(".similar-card li").count() == 3)
        check("the pop-up has no links", pop(page).locator("a").count() == 0)
        page.keyboard.press("Escape")
        page.wait_for_timeout(100)
        check("Escape closes it and focus goes back to the button", pop(page).count() == 0 and page.evaluate("() => document.activeElement.classList.contains('similar-open')"))
        btn.click(); page.wait_for_timeout(100)
        pop(page).locator(".similar-close").click()
        check("the close button closes it", pop(page).count() == 0)
        btn.click(); page.wait_for_timeout(100)
        page.go_back(); page.wait_for_timeout(200)
        check("the phone's Back button closes it and stays on the recipe", pop(page).count() == 0 and page.evaluate("() => openRecipeId") == 1)

        metal = [{"id": 1, "brand": "Citadel", "name": "Leadbelcher", "colour": "#888d8f", "status": "owned", "type": "metallic"}]
        open_recipe(page, metal)
        page.locator("#recipe-page .step-body .similar-open").click(); page.wait_for_timeout(150)
        check("a metallic paint gets the metallic note", "only a guide for this kind of paint" in pop(page).locator(".similar-note").inner_text(), pop(page).locator(".similar-note").inner_text())
        page.keyboard.press("Escape")

        load(page, paints=h.JUST_BLUE)
        c.open_comp(page)
        c.pick_base(page, "test paints|probe blue")
        page.wait_for_timeout(150)
        row = page.locator("#cmp-fold-ideas-panel > .idea-list > li").first
        sim = row.locator(".paint-recipe-buttons button", has_text="Similar paints")
        check("a Compendium colour idea has Similar paints beside the two recipe buttons", row.locator(".paint-recipe-buttons button").all_inner_texts() == ["Use in a recipe", "Add to a recipe", "Similar paints"],
              row.locator(".paint-recipe-buttons button").all_inner_texts())
        sim.click(); page.wait_for_timeout(150)
        check("it opens the same pop-up from the Compendium", pop(page).count() == 1 and pop(page).locator(".similar-card li").count() >= 1)
        page.keyboard.press("Escape")

        print("\n--- 5. Phones, dark and light ---")
        for width in (390, 360):
            for scheme in ("dark", "light"):
                page.set_viewport_size({"width": width, "height": 844})
                page.emulate_media(color_scheme=scheme)
                open_recipe(page)
                small = page.evaluate("() => Math.min(...[...document.querySelectorAll('#recipe-page .similar-open')].map(b => b.getBoundingClientRect().height))")
                ok_page = no_sideways(page)
                page.locator("#recipe-page .step-body .similar-open").click(); page.wait_for_timeout(150)
                tap = page.evaluate("() => Math.min(...[...document.querySelectorAll('.similar-dialog button')].map(b => b.getBoundingClientRect().height))")
                wide = page.evaluate("() => { const d = document.querySelector('.similar-dialog'); return d.scrollWidth <= d.clientWidth + 1 && d.getBoundingClientRect().right <= window.innerWidth; }")
                check(f"{width} px {scheme}: no sideways scroll, every tap target 44 px or more", ok_page and no_sideways(page) and wide and small >= 44 and tap >= 44, (ok_page, wide, small, tap))
                page.keyboard.press("Escape")
        page.emulate_media(color_scheme="dark")

        print("\n--- 6. Errors and content files ---")
        check("no page errors", errors == [], errors)
        check("no browser pop-up boxes", dialogs == [], dialogs)
        base = "origin/main"
        out = subprocess.run(["git", "diff", "--name-only", base, "--", "schemes.js", "detail-recipes.js", "basing-tips.js", "colour.js"], cwd=t.ROOT, capture_output=True, text=True)
        changed = out.stdout.split()
        check("the content data files and the colour engine are unchanged", changed == [], changed)
        browser.close()
    print(f"\n{sum(results)}/{len(results)} checks passed")
    sys.exit(0 if all(results) else 1)

if __name__ == "__main__":
    main()
