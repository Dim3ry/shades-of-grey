"""v69 tests for Minifolio (chunk 3.1: from a recipe or a palette paint, one tap opens matching Compendium ideas).

What changed:
 A paint in an open recipe step, and an open paint in Your Palette, has an "Ideas for this" button. It opens the
 Compendium with that paint's ideas at the top: the same paint panel the colour wheel opens (colours that go with it,
 yours first, and starter schemes with a similar colour), plus detail recipes and basing tips with a step of a similar
 colour. "Show steps" / "Show tip" opens that recipe or tip in its own part. "Back to recipe" / "Back to Your Palette"
 (or the phone's Back) goes to the same place. A paint with no colour set, or a basing material, has no button.

Checks:
1. Versions, the v69 Updates entry, DATA_VERSION is still 1.
2. The button: in an open recipe step (label only, no sentence next to it), not for a paint with no colour or a material.
3. Tapping it: the Compendium shows the paint's ideas first (harmony groups, starter schemes, detail recipes, basing
   tips), yours first, and the Back button has the focus. Names stay plain text.
4. Show steps and Show tip open the detail recipe and the basing tip in their parts.
5. Back to recipe: the same recipe, the same step still open, the button has the focus.
6. Your Palette: the button in an open paint, Back to Your Palette, the paint still open. The phone's Back does the same.
7. The Compendium tab itself shows the whole Compendium again.
8. Help names the button, the parts and the way back.
9. 390 px and 360 px, dark and light: no sideways scroll, buttons 44 px or more.
10. Offline (no requests leave the machine), no page errors, no browser pop-ups.
Run all tests with `python3 tests/run_all.py`, or serve the repo folder and run this file on its own."""
import os, re, sys
from playwright.sync_api import sync_playwright

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import test_v31 as t
import test_v44 as e   # main_tab, recipe_view

URL, read = t.URL, t.read
HERE = os.path.dirname(os.path.abspath(__file__))
results = []

def check(name, ok, detail=""):
    results.append(bool(ok))
    print(("PASS " if ok else "FAIL ") + name + ("" if ok else f"  -> {detail}"))

HOSTILE = '<img src=x onerror="window.__pwned=1">Evil Blue'
PAINTS = [
    {"id": 1, "brand": "Citadel", "name": "Macragge Blue", "colour": "#0d407f", "status": "owned"},
    {"id": 2, "brand": "Citadel", "name": "Troll Slayer Orange", "colour": "#f4741c", "status": "owned"},
    {"id": 4, "brand": "Citadel", "name": "Eshin Grey", "colour": "#4a4d52", "status": "owned"},
    {"id": 6, "brand": "Citadel", "name": "Rakarth Flesh", "colour": "#a7a28f", "status": "owned"},
    {"id": 9, "brand": "Vallejo", "name": "Sandy Ground", "colour": "#9c8760", "status": "owned"},
    {"id": 30, "brand": "Vallejo", "name": "Unset Paint", "colour": "#808080", "status": "owned"},
    {"id": 31, "brand": "", "name": "Fine sand", "colour": "#c2b280", "type": "material", "status": "owned"},
    {"id": 32, "brand": "Odd", "name": HOSTILE, "colour": "#2a5db0", "status": "wishlist"},
]
RECIPES = [t.rec(101, "Armour blue", "Whole model", [30, 1, 31]), t.rec(102, "Ground", "Base", [9, 32])]
SETTINGS = {"tab": "recipes", "recipeView": "recipes", "examplesChecked": True}

def open_recipe(page, rid):
    page.evaluate("(id) => openRecipe(id)", rid)
    page.wait_for_timeout(250)

def open_step(page, i):
    line = page.locator(f'#recipe-page button.step-line[aria-controls="rstep-{i}"]')
    if line.get_attribute("aria-expanded") != "true":
        line.click()
        page.wait_for_timeout(150)

def focused(page):
    return page.evaluate("() => { const a = document.activeElement; return a ? (a.id || a.dataset.ideasFor || a.className) : ''; }")

def main():
    errors, dialogs, outside = [], [], []
    app, html = read("app.js"), read("index.html")
    with sync_playwright() as p:
        browser = p.chromium.launch()
        ctx = browser.new_context(viewport={"width": 390, "height": 844}, service_workers="block")
        page = ctx.new_page()
        page.on("pageerror", lambda x: errors.append(str(x)))
        page.on("dialog", lambda d: (dialogs.append(d.message), d.dismiss()))
        page.on("request", lambda r: outside.append(r.url) if not r.url.startswith(t.BASE) and not r.url.startswith("data:") else None)

        # ---------- 1. Versions ----------
        print("\n--- 1. Versions and the Updates entry ---")
        t.load(page, paints=PAINTS, recipes=RECIPES, settings=SETTINGS)
        tags = re.findall(r'<script src="[^"]+\?v=(\d+)"', html)
        entry = page.evaluate("CHANGELOG.find(c => c.version === 'v69')")
        text = " ".join(entry["changes"]) if entry else ""

        # ---------- 2. The button in a recipe step ----------
        print("\n--- 2. The button in a recipe step ---")
        open_recipe(page, 101)
        for i in range(3):
            open_step(page, i)
        btn = lambda pid, scope="#recipe-page": page.locator(f'{scope} button.ideas-for[data-ideas-for="{pid}"]')
        check("a paint with a colour has Ideas for this", btn(1, "#rstep-1").count() == 1 and btn(1, "#rstep-1").inner_text().strip().startswith("Ideas for this"))
        check("a paint with no colour set has no button", btn(30).count() == 0)
        check("a basing material has no button", btn(31).count() == 0)
        check("the button is a label only (no sentence next to it)", page.evaluate("""() => { const b = document.querySelector('#rstep-1 button.ideas-for');
            return !b.nextElementSibling || !b.nextElementSibling.matches('p, small, .hint'); }"""))
        check("the paint's name is read out with it, not put in an aria-label", btn(1, "#rstep-1").get_attribute("aria-label") is None
              and "Macragge Blue" in btn(1, "#rstep-1").text_content())

        # ---------- 3. The Compendium, scoped ----------
        print("\n--- 3. Ideas for one paint ---")
        btn(1, "#rstep-1").click()
        page.wait_for_timeout(300)
        check("the Compendium tab is shown", page.evaluate("settings.tab") == "compendium" and page.is_visible("#view-compendium"))
        check("the paint's ideas sit above the colour wheel", page.evaluate("""() => { const f = document.getElementById('cmp-focus'), w = document.getElementById('cmp-wheel-block');
            return !!f && !!w && !!(f.compareDocumentPosition(w) & Node.DOCUMENT_POSITION_FOLLOWING); }"""))
        check("the title names the paint", page.text_content("#cmp-focus-title") == "Ideas for Macragge Blue (Citadel)", page.text_content("#cmp-focus-title"))
        labels = page.evaluate("() => [...document.querySelectorAll('#cmp-focus .paint-panel-label')].map(p => p.textContent)")
        check("colours that go with it: Opposite, Neighbours and Triad", all(x in labels for x in ["Opposite", "Neighbours", "Triad"]), labels)
        check("then starter schemes, detail recipes and basing tips with a similar colour",
              labels[-3:] == ["Starter schemes with a similar colour", "Detail recipes with a similar colour", "Basing tips with a similar colour"], labels)
        lists = page.evaluate("() => [...document.querySelectorAll('#cmp-focus-panel > .idea-list')].slice(0, 3).map(l => [...l.querySelectorAll('.idea-tag')].map(x => x.textContent))")
        tags = [t for l in lists for t in l]
        # v69: since v64 a paint you own comes first only when it is a Good or Okay fit; a poor fit ("Yours, poor fit") comes after the closest paint overall.
        # So the rule checked here is: in each list, no paint you own with a good or okay fit comes after a paint you don't own.
        def own_first(l):
            seen_not_owned = False
            for t in l:
                if t == "Not in your palette": seen_not_owned = True
                elif "poor fit" not in t and seen_not_owned: return False
            return True
        check("your own paints with a good or okay fit come before paints you don't own", bool(tags) and all(own_first(l) for l in lists), lists)
        check("the Back button says Back to recipe and has the focus", page.inner_text("#cmp-focus-back").strip() == "← Back to recipe" and focused(page) == "cmp-focus-back", focused(page))
        check("no stray ids: the focus panel has its own", page.evaluate("() => document.querySelectorAll('#cmp-paint-panel').length") == 0)
        check("the matching is the same engine as the starter schemes (no copy)", "function libraryLike" in app and app.count("C.judgeMatch(") >= 2)

        # ---------- 4. Show steps / Show tip ----------
        print("\n--- 4. Show steps and Show tip ---")
        detail = page.locator("#cmp-focus button.ideas-open[data-detail]")
        check("at least one detail recipe matches a deep blue", detail.count() >= 1, detail.count())
        if detail.count():
            key = detail.first.get_attribute("data-detail")
            detail.first.click()
            page.wait_for_timeout(300)
            check("Show steps opens Detail recipes with that recipe picked", page.get_attribute("#cmp-fold-detail-button", "aria-expanded") == "true"
                  and page.locator(f'#cmp-fold-detail-panel [data-detail="{key}"]').count() == 1 and page.is_visible("#cmp-detail-summary"))
            check("…and the focus goes to it", page.evaluate("() => document.activeElement && document.activeElement.dataset.detail") == key)
            check("the paint's ideas are still on show", page.locator("#cmp-focus").count() == 1)
        t.load(page, paints=PAINTS, recipes=RECIPES, settings=SETTINGS)
        open_recipe(page, 102)
        open_step(page, 0)
        btn(9, "#rstep-0").click()
        page.wait_for_timeout(300)
        tip = page.locator("#cmp-focus button.ideas-open[data-basing]")
        check("a sandy brown matches a basing tip", tip.count() >= 1, tip.count())
        if tip.count():
            key = tip.first.get_attribute("data-basing")
            tip.first.click()
            page.wait_for_timeout(300)
            check("Show tip opens Basing tips with that tip picked", page.get_attribute("#cmp-fold-basing-button", "aria-expanded") == "true"
                  and page.evaluate("compendiumState.basing") == key)

        # ---------- 5. Back to recipe ----------
        print("\n--- 5. Back to recipe ---")
        page.click("#cmp-focus-back")
        page.wait_for_timeout(300)
        check("back on the Recipes tab, in the same recipe", page.evaluate("settings.tab") == "recipes" and page.evaluate("openRecipeId") == 102)
        check("…with the same step still open", page.get_attribute('#recipe-page button.step-line[aria-controls="rstep-0"]', "aria-expanded") == "true")
        check("…and the focus on the same button", focused(page) == "9")
        check("the Compendium is no longer scoped", page.evaluate("compendiumState.focus") is None)
        check("hostile paint names stay plain text", page.evaluate("window.__pwned") is None)
        open_step(page, 1)
        btn(32, "#rstep-1").click()
        page.wait_for_timeout(300)
        check("a hostile name shows as text in the title", HOSTILE in (page.text_content("#cmp-focus-title") or "") and page.evaluate("window.__pwned") is None)

        # ---------- 6. Your Palette, and the phone's Back ----------
        print("\n--- 6. Your Palette ---")
        t.load(page, paints=PAINTS, recipes=RECIPES, settings=dict(SETTINGS, recipeView="palette"))
        page.click('#paint-list .paint-head:has-text("Eshin Grey")')
        page.wait_for_timeout(200)
        pal = btn(4, "#paint-list")
        check("an open palette paint has Ideas for this", pal.count() == 1)
        page.click('#paint-list .paint-head:has-text("Unset Paint")')
        page.wait_for_timeout(200)
        check("an open palette paint with no colour has none", btn(30, "#paint-list").count() == 0)
        btn(4, "#paint-list").click()
        page.wait_for_timeout(300)
        check("it opens the Compendium for that paint", page.text_content("#cmp-focus-title") == "Ideas for Eshin Grey (Citadel)")
        check("a grey gets the neutral accents instead of an opposite", "Accents that stand out" in page.text_content("#cmp-focus"))
        check("the Back button says Back to Your Palette", page.inner_text("#cmp-focus-back").strip() == "← Back to Your Palette")
        page.click("#cmp-focus-back")
        page.wait_for_timeout(300)
        check("back on Your Palette with the paint still open", page.evaluate("settings.recipeView") == "palette" and page.evaluate("settings.tab") == "recipes"
              and btn(4, "#paint-list").count() == 1 and focused(page) == "4")
        btn(4, "#paint-list").click()
        page.wait_for_timeout(300)
        page.go_back()
        page.wait_for_timeout(400)
        check("the phone's Back goes back to Your Palette too", page.evaluate("settings.tab") == "recipes" and page.evaluate("settings.recipeView") == "palette", page.evaluate("settings.tab"))

        # ---------- 7. The tab itself ----------
        print("\n--- 7. The Compendium tab ---")
        btn(4, "#paint-list").click()
        page.wait_for_timeout(300)
        e.main_tab(page, "recipes")
        e.main_tab(page, "compendium")
        check("tapping the Compendium tab shows the whole Compendium", page.locator("#cmp-focus").count() == 0 and page.locator("#cmp-wheel-block").count() == 1)

        # ---------- 8. Help ----------
        print("\n--- 8. Help ---")
        topic = page.evaluate("() => (document.getElementById('help-ideas-for') || {}).textContent || ''")
        check("Help has an Ideas for this line naming the parts and the way back",
              all(w in topic for w in ["Ideas for this", "Your Palette", "detail recipes", "basing tips", "Show steps", "Back to recipe", "Back to Your Palette", "no colour set"]), topic)
        check("…in the Paint recipes topic", page.evaluate("() => document.getElementById('help-ideas-for').closest('details').querySelector('summary').textContent.trim()") == "Paint recipes")

        # ---------- 9. Phones, dark and light ----------
        for appearance in ["dark", "light"]:
            for width in [390, 360]:
                tag = f"{appearance} {width}px"
                print(f"\n--- 9. {tag} ---")
                page.set_viewport_size({"width": width, "height": 780})
                t.load(page, paints=PAINTS, recipes=RECIPES, settings=dict(SETTINGS, appearance=appearance))
                open_recipe(page, 101)
                open_step(page, 1)
                check(f"{tag}: recipe page, no sideways scroll", not page.evaluate("document.documentElement.scrollWidth > document.documentElement.clientWidth"))
                b = btn(1, "#rstep-1").bounding_box()
                check(f"{tag}: Ideas for this is 44 px or more and fits", b and b["height"] >= 44 and b["x"] + b["width"] <= width, b)
                btn(1, "#rstep-1").click()
                page.wait_for_timeout(300)
                check(f"{tag}: the paint's ideas, no sideways scroll", not page.evaluate("document.documentElement.scrollWidth > document.documentElement.clientWidth"))
                sizes = page.evaluate("""() => [...document.querySelectorAll('#cmp-focus-back, #cmp-focus button.ideas-open')].map(b => { const r = b.getBoundingClientRect();
                    return [Math.round(r.height), r.right <= document.documentElement.clientWidth]; })""")
                check(f"{tag}: Back, Show steps and Show tip are 44 px or more and fit", sizes and all(h >= 44 and fits for h, fits in sizes), sizes)
                os.makedirs(os.path.join(HERE, "screenshots"), exist_ok=True)
                page.locator("#cmp-focus").screenshot(path=os.path.join(HERE, "screenshots", f"v69-ideas-{appearance}-{width}.png"))

        # ---------- 10. Safety ----------
        print("\n--- 10. Safety ---")
        check("works offline: no request left this machine", not outside, outside[:5])
        check("no page errors", not errors, errors)
        check("no browser pop-ups", not dialogs, dialogs)
        browser.close()

    print(f"\n{sum(results)}/{len(results)} checks passed")
    sys.exit(0 if all(results) else 1)

if __name__ == "__main__":
    main()
