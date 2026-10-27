"""v52 tests for Minifolio (declutter chunk D5: Shopping list, Settings, Dashboard and Units, Help).

What changed:
 (a) Shopping list (Recipes tab, Shopping switch): the explanatory sentence, the warning line, the shop bar note and the shop links
     explanation sit behind ONE More info. The paints, the Copy as text button, the Buy these bar and the basket count stay in view.
 (b) Settings and Updates: each card keeps its buttons and switches in view, and its explanation sits behind a More info (Backups,
     Stages, Appearance, Counting visits, Shop links, Faction colours, Import, Your data, and the feedback card on Updates).
 (c) Dashboard and Units: the note on the example units card is behind More info. Nothing else on those pages changed.
 (d) Help: the topics are still native folds, but they now read More info / Less info with the same arrow, and carry aria-expanded.
     New Help lines: Swatches switch and More options, folded steps and More options in recipes, Compendium tick boxes.
 (e) Open or closed is kept only while the app is open. Nothing is saved.

Checks:
1. Versions and the v52 Updates entry.
2. Shopping list.
3. Settings and Updates.
4. Dashboard and Units.
5. Help.
6. What the new code is (and is not) allowed to contain.
7. Layout at 360, 390 and 1000 px, dark and light: targets, contrast, no sideways scroll.
8. No page errors, no browser pop-ups.
Run all tests with `python3 tests/run_all.py`, or serve the repo folder and run this file on its own."""
import os, re, sys
from playwright.sync_api import sync_playwright
import fold_opener   # v54: Stages, Import and Your data fold shut; this older test works inside them

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from notice_watch import attach_notices
import test_v31 as t
import test_v42 as w   # load, basket, stored
import test_v51 as v51   # tap, contrast, all_local

URL, read = t.URL, t.read
results = []

def check(name, ok, detail=""):
    results.append(bool(ok))
    print(("PASS " if ok else "FAIL ") + name + ("" if ok else f"  -> {detail}"))

def tab(page, name):
    page.evaluate("() => document.activeElement && document.activeElement.blur()")
    page.click(f'nav button[data-tab="{name}"]')
    page.wait_for_timeout(150)

def more_page(page, name):
    tab(page, "settings")
    page.click(f'#more-seg button[data-page="{name}"]')
    page.wait_for_timeout(150)

def open_shopping(page):
    tab(page, "recipes")
    page.click('#recipe-seg button[data-view="shopping"]')
    page.wait_for_timeout(150)

def paints_with_needs():
    pals = [dict(p) for p in t.PAINTS]
    for i, p in enumerate(pals[:4]):
        p["status"] = ("low", "empty", "wishlist", "low")[i]
    return pals

def shown(page, selector):
    return page.locator(selector).count() > 0 and page.locator(selector).first.is_visible()

def text(page, selector):
    return page.evaluate("(s) => { const e = document.querySelector(s); return e ? e.textContent.replace(/\\s+/g, ' ').trim() : null; }", selector)

def height(page, selector, nth=0):
    return page.locator(selector).nth(nth).bounding_box()["height"]

def more(page, scope):
    """The More info button in a scope (a CSS selector)."""
    return page.locator(f"{scope} .more-info-button").first

def press(page, button):
    button.evaluate("e => e.scrollIntoView({ block: 'center' })")
    page.wait_for_timeout(60)
    button.click()
    page.wait_for_timeout(80)

SETTINGS_FOLDS = {
    "backups": ("#backup-card", ["backup-explain"], "Save backup leaves out photos"),
    "stages": ("#stages-explain", ["stages-explain"], "Rename, reorder"),
    "appearance": ("#appearance-card", ["appearance-note"], None),
    "counting": ("#counting-card", ["counting-note", "counting-effect"], "Takes effect"),
    "shoplinks": ("#shoplinks-card", ["shoplinks-note"], None),
    "faction-colours": ("#faction-colours-card", ["faction-colour-hint"], None),
    "import": ("#import-explain", ["import-explain"], "CSV columns"),
    "your-data": ("#restore-examples", ["data-summary", "photo-summary", "storage-note", "restore-examples-hint"], None),
}

def main():
    errors, dialogs = [], []
    app, html = read("app.js"), read("index.html")
    with sync_playwright() as p:
        browser = p.chromium.launch()
        ctx = browser.new_context(viewport={"width": 390, "height": 844}, service_workers="block")
        page = ctx.new_page()
        fold_opener.open_cards_on_load(page)   # v54: open the folded Settings cards whenever the app loads
        page.on("pageerror", lambda e: errors.append(str(e)))
        page.on("dialog", lambda d: (dialogs.append(d.message), d.dismiss()))
        attach_notices(page, dialogs.append)

        # ---------- 1. Versions ----------
        print("\n--- 1. Versions and wording ---")
        w.load(page, paints=[])
        entry = page.evaluate("CHANGELOG.find(c => c.version === 'v52')")
        check("the v52 entry mentions More info, the Shopping list, Settings and Help",
              entry and all(any(word in x for x in entry["changes"]) for word in ("More info", "Shopping list", "Settings", "Help")))

        # ---------- 2. Shopping list ----------
        print("\n--- 2. Shopping list ---")
        w.load(page, paints=paints_with_needs(), recipes=t.RECIPES, units=t.UNITS)
        open_shopping(page)
        n_items = page.locator("#shop-panel .shop-list li").count()
        check("the list has paints to show", n_items >= 2, n_items)
        check("the paints, the Buy these bar, Copy as text and the basket count are all in view without opening anything",
              n_items >= 2 and shown(page, "#shop-panel .shop-list li") and shown(page, "#buy-bar") and shown(page, "#shop-panel .primary-button")
              and text(page, "#shop-panel .primary-button") == "Copy as text" and w.basket(page) != "", (n_items, w.basket(page)))
        check("there is exactly one More info in the card, closed, with aria-expanded false",
              page.locator("#shop-panel .more-info-button").count() == 1 and page.get_attribute("#shop-panel .more-info-button", "aria-expanded") == "false")
        check("it says More info and is at least 44 px tall", text(page, "#shop-panel .more-info-button") == "More info" and height(page, "#shop-panel .more-info-button") >= 43.5)
        check("while closed, the sentence, the warning and the shop note are all hidden",
              not any(page.get_by_text(x).first.is_visible() for x in ("paints to get", "No statuses set yet", "Plain links")))
        panel = text(page, "#shop-panel .more-info-panel")
        check("the panel holds the sentence, the shop note and the shop links words",
              # v75: the sentence is now just "N paints to get." and the shop note is only the plain-links words (SHOP-1, SHOP-4)
              panel and "paints to get" in panel and "Plain links" in panel, panel)
        before = v51.all_local(page)
        press(page, page.locator("#shop-panel .more-info-button").first)
        check("tapping it opens the panel, the button says Less info and aria-expanded is true",
              page.get_attribute("#shop-panel .more-info-button", "aria-expanded") == "true" and text(page, "#shop-panel .more-info-button") == "Less info"
              and page.locator("#shop-panel .more-info-panel").first.is_visible())
        check("the button controls the panel (aria-controls matches its id)",
              page.get_attribute("#shop-panel .more-info-button", "aria-controls") == page.get_attribute("#shop-panel .more-info-panel", "id"))
        page.click("#buy-bar .buy-shops button >> nth=0")
        page.wait_for_timeout(100)
        check("opening a shop redraws the list and More info stays open (kept while the app is open)",
              page.get_attribute("#shop-panel .more-info-button", "aria-expanded") == "true")
        check("opening More info and a shop saved nothing", v51.all_local(page) == before)
        check("the shop's links still show under the bar", page.locator("#buy-links li").count() >= 1)
        w.load(page, paints=paints_with_needs(), recipes=t.RECIPES, units=t.UNITS)
        open_shopping(page)
        check("after a reload More info is closed again", page.get_attribute("#shop-panel .more-info-button", "aria-expanded") == "false")
        # shop links switched off: no shop note
        w.load(page, paints=paints_with_needs(), recipes=t.RECIPES, units=t.UNITS, settings={"hideShopLinks": True})
        open_shopping(page)
        panel = text(page, "#shop-panel .more-info-panel") or ""
        check("with shop links off, the panel has no shop words and the bar is gone", "Tap a shop" not in panel and "Plain links" not in panel and page.locator("#buy-bar").count() == 0, panel)
        # warning goes when a status is set (it is the same panel)
        w.load(page, paints=[], recipes=[], units=[])
        open_shopping(page)
        check("with nothing to buy: the short empty line shows and there is no More info",
              "Nothing to buy" in (text(page, "#shop-panel") or "") and page.locator("#shop-panel .more-info-button").count() == 0)

        # ---------- 3. Settings and Updates ----------
        print("\n--- 3. Settings and Updates ---")
        w.load(page, paints=[], recipes=[], units=t.UNITS)
        more_page(page, "settings")
        keys = list(SETTINGS_FOLDS)
        have = page.evaluate("(ks) => ks.map(k => { const b = document.querySelector('#more-' + k); return !!b && !!document.querySelector('[aria-controls=\"more-' + k + '\"]'); })", keys)
        check("every Settings card with an explanation has one More info (" + ", ".join(keys) + ")", all(have), dict(zip(keys, have)))
        check("each is closed, says More info and carries aria-expanded false",
              page.evaluate("(ks) => ks.every(k => { const b = document.querySelector('[aria-controls=\"more-' + k + '\"]'); return b && b.getAttribute('aria-expanded') === 'false' && b.textContent.trim() === 'More info'; })", keys))
        page.evaluate("() => document.querySelectorAll('.card-fold-button[aria-expanded=\"false\"]').forEach(b => b.click())")   # v53: Faction colours folds shut as a whole card
        page.wait_for_timeout(100)
        check("each More info button is at least 44 px tall",
              page.evaluate("(ks) => ks.every(k => document.querySelector('[aria-controls=\"more-' + k + '\"]').getBoundingClientRect().height >= 43.5)", keys))
        check("each one's panel holds the lines it should (they moved, they were not copied)",
              page.evaluate("(spec) => Object.entries(spec).every(([k, ids]) => ids.every(id => { const e = document.getElementById(id); return e && e.closest('#more-' + k) && document.querySelectorAll('#' + id).length === 1; }))",
                            {k: v[1] for k, v in SETTINGS_FOLDS.items()}))
        check("closed, the explanations are hidden", not any(page.locator(f"#{i}").is_visible() for i in ("backup-explain", "appearance-note", "counting-note", "shoplinks-note", "data-summary", "stages-explain", "import-explain")))
        check("the Backups buttons stay in view, closed, and are at least 44 px tall",
              all(page.locator(f"#{i}").is_visible() and height(page, f"#{i}") >= 43.5 for i in ("export-button", "share-button", "full-export-button", "full-share-button", "restore-button")))
        check("the last-backup line stays visible", page.locator("#backup-age").is_visible())
        check("the other controls stay in view: the Appearance buttons, the counting and shop links boxes, Save stages and Delete all units",
              all(page.locator(s).first.is_visible() for s in ("#appearance-card .chip", "#count-visits", "#show-shop-links", "#save-stages", "#delete-all", "#clean-photos", "#restore-examples", "#csv-button")))
        before = v51.all_local(page)
        press(page, page.locator('[aria-controls="more-backups"]'))
        check("opening Backups More info shows the explanation and the button says Less info",
              page.locator("#backup-explain").is_visible() and
              page.get_attribute('[aria-controls="more-backups"]', "aria-expanded") == "true" and text(page, '[aria-controls="more-backups"]') == "Less info")
        press(page, page.locator('[aria-controls="more-your-data"]'))
        check("opening Your data More info shows the summary and the restore-examples line", page.locator("#data-summary").is_visible() and page.locator("#restore-examples-hint").is_visible())
        check("the summary still has its numbers (the code still writes into it)", re.search(r"\d+ units", text(page, "#data-summary") or "") is not None, text(page, "#data-summary"))
        check("opening them saved nothing", v51.all_local(page) == before)
        # the notes still update
        press(page, page.locator('[aria-controls="more-appearance"]'))
        page.click('[data-appearance-choice="auto"]')
        page.wait_for_timeout(150)
        check("the Appearance note still follows the choice (and sits behind More info)", "Right now" in (text(page, "#appearance-note") or "") and page.locator("#appearance-note").is_visible(), text(page, "#appearance-note"))
        page.click('[data-appearance-choice="dark"]')
        page.wait_for_timeout(100)
        more_page(page, "help")
        more_page(page, "settings")
        check("More info stays open when you leave the page and come back (kept while the app is open)", page.get_attribute('[aria-controls="more-backups"]', "aria-expanded") == "true")
        w.load(page, paints=[], recipes=[], units=t.UNITS)
        more_page(page, "settings")
        check("after a reload every Settings More info is closed again",
              page.evaluate("(ks) => ks.every(k => document.querySelector('[aria-controls=\"more-' + k + '\"]').getAttribute('aria-expanded') === 'false')", keys))
        more_page(page, "updates")
        check("Updates: the feedback card keeps its heading and Give feedback in view; its explanation is behind More info",
              page.locator("#feedback-link").is_visible() and not page.locator("#feedback-explain").is_visible() and page.locator('[aria-controls="more-feedback"]').count() == 1)
        check("Updates: the unofficial note stays visible", page.locator("#unofficial-note").is_visible())

        # ---------- 4. Dashboard and Units ----------
        print("\n--- 4. Dashboard and Units ---")
        page.goto(URL)
        page.evaluate("() => localStorage.clear()")   # a first visit: the three example units are made
        page.reload()
        page.wait_for_timeout(300)
        page.evaluate("() => document.querySelector('nav button[data-tab=\"dashboard\"]').click()")
        page.wait_for_timeout(150)
        check("Dashboard: the examples card shows its heading line, the two buttons and one More info (closed)",
              page.locator("#examples-card-dash").is_visible() and "These are examples" in (text(page, "#examples-card-dash") or "") and
              page.locator("#examples-card-dash .clear-examples").is_visible() and page.locator("#examples-card-dash .keep-examples").is_visible() and
              page.get_attribute("#examples-card-dash .more-info-button", "aria-expanded") == "false")
        check("…the explanation and the unit names are hidden until it is opened", not page.locator("#examples-card-dash .more-info-panel").is_visible()
              and all(n in (text(page, "#examples-card-dash .more-info-panel") or "") for n in ("Captain", "Brutes", "Guardians")))
        press(page, page.locator("#examples-card-dash .more-info-button"))
        check("…opened, it says what the examples are for", "to start your own" in (text(page, "#examples-card-dash .more-info-panel") or "") and page.locator("#examples-card-dash .more-info-panel").is_visible())
        check("Dashboard: the buttons are still at least 44 px tall", height(page, "#examples-card-dash .clear-examples") >= 43.5 and height(page, "#examples-card-dash .keep-examples") >= 43.5)
        page.evaluate("() => document.querySelector('nav button[data-tab=\"units\"]').click()")
        page.wait_for_timeout(150)
        check("Units: the same card has its own More info, closed, and the buttons in view",
              page.get_attribute("#examples-card .more-info-button", "aria-expanded") == "false" and page.locator("#examples-card .clear-examples").is_visible())
        check("the Units filter note and unit list are unchanged (still there)", page.locator("#filter-note").is_visible() and page.locator("#unit-list > li").count() >= 3)
        page.click("#examples-card .keep-examples")
        page.wait_for_timeout(150)
        check("Keep them removes the card from both pages", page.locator("#examples-card").is_hidden() and page.evaluate("document.getElementById('examples-card-dash').classList.contains('hidden')"))

        # ---------- 5. Help ----------
        print("\n--- 5. Help ---")
        w.load(page, paints=[], recipes=[], units=t.UNITS)
        more_page(page, "help")
        topics = page.locator("#view-help .help details").count()
        check("every topic title carries aria-expanded",
              page.evaluate("() => [...document.querySelectorAll('#view-help .help details')].every(d => d.querySelector(':scope > summary').hasAttribute('aria-expanded'))"))
        check("every topic starts closed (aria-expanded false), v53 (the first used to be open)",
              page.evaluate("() => [...document.querySelectorAll('#view-help .help details')].every(d => d.querySelector(':scope > summary').getAttribute('aria-expanded') === 'false' && !d.open)"))
        press(page, page.locator("#view-help .help details > summary").nth(0))
        words = page.evaluate("""() => { const d = document.querySelectorAll('#view-help .help details');
            return [getComputedStyle(d[0].querySelector('summary'), '::after').content, getComputedStyle(d[1].querySelector('summary'), '::after').content]; }""")
        check("an open topic reads Less info and a closed one reads More info", words == ['"Less info"', '"More info"'], words)
        press(page, page.locator("#view-help .help details > summary").nth(0))   # shut it again
        press(page, page.locator("#view-help .help details > summary").nth(1))
        check("tapping a topic opens it, flips the word and sets aria-expanded true",
              page.evaluate("() => { const d = document.querySelectorAll('#view-help .help details')[1]; return d.open && d.querySelector('summary').getAttribute('aria-expanded') === 'true' && getComputedStyle(d.querySelector('summary'), '::after').content === '\"Less info\"'; }"))
        page.evaluate("() => { const d = document.getElementById('about'); d.open = true; }")
        page.wait_for_timeout(100)
        check("a topic opened by code (a link, the Back button) gets aria-expanded true too", page.evaluate("() => document.querySelector('#about > summary').getAttribute('aria-expanded') === 'true'"))
        check("Help topic titles are still real folds (details and summary) and at least 44 px tall",
              page.evaluate("() => [...document.querySelectorAll('#view-help summary')].every(s => s.getBoundingClientRect().height >= 43.5)"))
        page.evaluate("document.querySelectorAll('#view-help details').forEach(d => d.open = true)")
        lines = {"help-palette-swatches": ["Swatches", "More options", "Merge", "Remove"],
                 "help-recipe-steps": ["folded", "More options", "technique", "Optional"],
                 "help-compendium-ticks": ["Compendium", "Select all", "Add to shopping list", "Copy as text", "Save into a new recipe"]}
        for hid, wanted in lines.items():
            line = text(page, f"#{hid}") or ""
            check(f"the new Help line {hid} exists and mentions {', '.join(wanted)}", all(x in line for x in wanted), line[:140])
        check("the new Help lines have no em dashes", not any("—" in (text(page, f"#{h_}") or "") for h_ in lines))
        check("the new lines sit in the Paint recipes topic", page.evaluate("() => ['help-palette-swatches', 'help-recipe-steps', 'help-compendium-ticks'].every(id => document.getElementById(id).closest('details').querySelector('summary').textContent.trim() === 'Paint recipes')"))

        # ---------- 6. The code ----------
        print("\n--- 6. The new code ---")
        a = app.index("function pageMoreInfo(")
        mine = app[a:app.index("// A greyed-out shopping list button")]   # pageMoreInfo, foldPageText and markHelpFolds
        check("no paint name can reach an aria-label from the new helpers", not re.search(r"aria-label", mine))
        shop = app[app.index("function renderShopPanel("):app.index("// v40: the small basket count")]
        check("the Shopping list code adds no innerHTML and no aria-label", "innerHTML" not in shop and "aria-label" not in shop)
        css = html[html.index("/* v52: More info on the Shopping list"):html.index(".idea-more .more-info-button")]
        check("no new subtitles, badges or pills in the new CSS", not re.search(r"pill|badge", css))

        # ---------- 7. Layout, targets and contrast ----------
        print("\n--- 7. Layout, dark and light ---")
        for mode in ("dark", "light"):
            for width, height_ in ((360, 780), (390, 844), (1000, 900)):
                tag = f"{mode} {width} px"
                page.set_viewport_size({"width": width, "height": height_})
                w.load(page, paints=paints_with_needs(), recipes=t.RECIPES, units=t.UNITS, settings={"appearance": mode})
                page.set_viewport_size({"width": width, "height": height_})
                open_shopping(page)
                press(page, page.locator("#shop-panel .more-info-button").first)
                check(f"{tag}: Shopping list, no sideways scrolling, Copy as text at least 44 px and inside the screen",
                      t.no_sideways(page) and height(page, "#shop-panel .primary-button") >= 43.5 and page.locator("#shop-panel .primary-button").bounding_box()["x"] >= 0)
                low = v51.contrast(page, "#shop-panel .more-info-button")
                hint = v51.contrast(page, "#shop-panel .more-info-panel > .hint", "color", False)
                check(f"{tag}: Shopping list, the More info text and the lines inside it have contrast of at least 4.5", low >= 4.5 and hint >= 4.5, (low, hint))
                if width == 390: t.shot(page, f"v52-shopping-{mode}.png")
                more_page(page, "settings")
                check(f"{tag}: Settings, no sideways scrolling and the five Backups buttons are at least 44 px and inside the screen",
                      t.no_sideways(page) and all(height(page, f"#{i}") >= 43.5 and page.locator(f"#{i}").bounding_box()["x"] >= -0.5 and
                      page.locator(f"#{i}").bounding_box()["x"] + page.locator(f"#{i}").bounding_box()["width"] <= width + 0.5
                      for i in ("export-button", "share-button", "full-export-button", "full-share-button", "restore-button")))
                press(page, page.locator('[aria-controls="more-backups"]'))
                low = v51.contrast(page, '[aria-controls="more-backups"]')
                hint = v51.contrast(page, "#backup-explain", "color", False)
                check(f"{tag}: Settings, the More info text and the explanation inside it have contrast of at least 4.5", low >= 4.5 and hint >= 4.5, (low, hint))
                if width == 390: t.shot(page, f"v52-settings-{mode}.png")
                more_page(page, "help")
                check(f"{tag}: Help, no sideways scrolling and every title at least 44 px",
                      t.no_sideways(page) and page.evaluate("() => [...document.querySelectorAll('#view-help summary')].every(s => s.getBoundingClientRect().height >= 43.5)"))
                same = page.evaluate("""() => { const s = document.querySelectorAll('#view-help summary')[1];
                    const a = getComputedStyle(s, '::after').color, b = getComputedStyle(s, '::before').borderRightColor;
                    const probe = document.createElement('button'); probe.className = 'more-info-button'; document.body.appendChild(probe);
                    const c = getComputedStyle(probe).color; probe.remove(); return [a, b, c]; }""")
                check(f"{tag}: Help's More info word and arrow use the same colour as the More info button (so the same contrast)", same[0] == same[2] and same[1] == same[2], same)
                if width == 390: t.shot(page, f"v52-help-{mode}.png")
                tab(page, "dashboard")
                check(f"{tag}: Dashboard, no sideways scrolling", t.no_sideways(page))
                tab(page, "units")
                check(f"{tag}: Units, no sideways scrolling", t.no_sideways(page))

        # ---------- 8. Clean run ----------
        print("\n--- 8. A clean run ---")
        check("no page errors", not errors, errors[:2])
        other = [d for d in dialogs if not d.startswith(("Took ", "Started a new recipe", "Nothing added", "Kept "))]
        check("no browser pop-ups", not other, other[:2])
        browser.close()
    failed = results.count(False)
    print(f"\n{len(results) - failed} passed, {failed} failed")
    sys.exit(1 if failed else 0)

if __name__ == "__main__":
    main()
