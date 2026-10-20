"""v54 tests for Minifolio (declutter chunk D7: Updates folds, the last three Settings card folds, fainter disabled buttons).

What changed:
 F5  Updates: each entry shows its version and date; its lines sit behind More info. The newest entry starts open, the rest shut. Whether
     each is open is kept only while the app is open (nothing is saved).
 F14 Settings: Stages, Import and Your data fold shut as whole cards (the same foldCard / openCardFold as Faction colours and Paint brands:
     a 44 px heading button with aria-expanded, shut every time the app opens). Delete all units stays inside Your data and works as before.
     Backups, Appearance, Theme, Counting visits, Shop links and Colours stay open. One more sentence in the existing Help item.
 F15 button:disabled is 0.55 (was 0.35). The reorder arrows and Clean up photo storage still read as switched off.

Checks:
1. Versions, the v54 Updates entry and the Help line.
2. F5: the Updates entries and their More info (open state, kept while open, nothing saved).
3. F14: the three new folded cards, Delete all units, the cards that stay open, the keep-open state.
4. F15: the fainter disabled look, and that disabled still differs from live.
5. Tap targets and sideways scroll on Settings (cards open) and Updates (entries open), three widths.
6. What the new code is (and is not) allowed to contain.
7. No page errors, no browser pop-ups.
Run all tests with `python3 tests/run_all.py`, or serve the repo folder and run this file on its own."""
import json, os, re, sys
from playwright.sync_api import sync_playwright

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from notice_watch import attach_notices
import test_v31 as t
import test_v42 as w   # load
import test_v52 as v52   # tab, more_page, press, paints_with_needs
import test_v53 as v53   # SMALL_JS, parse_colour, blend, storage_dump, open_card_folds

URL, read = t.URL, t.read
results = []

def check(name, ok, detail=""):
    results.append(bool(ok))
    print(("PASS " if ok else "FAIL ") + name + ("" if ok else f"  -> {detail}"))

tab, more_page, press = v52.tab, v52.more_page, v52.press
storage_dump, parse_colour, blend = v53.storage_dump, v53.parse_colour, v53.blend

NEW_CARDS = (("stages", "#stages-card", "#stage-list"), ("import", "#import-card", "#csv-button"), ("your-data", "#your-data-card", "#delete-all"))

def scan(page, label):
    small = page.evaluate(v53.SMALL_JS)
    check(f"{label}: every tap target is 44 px or more", not small, small[:8])
    check(f"{label}: nothing scrolls sideways", t.no_sideways(page))

def release_states(page):
    return page.evaluate("() => [...document.querySelectorAll('#changelog .release')].map(r => r.querySelector('.more-info-button').getAttribute('aria-expanded'))")

def ratio(fg, bg):
    def lin(v):
        v /= 255
        return v / 12.92 if v <= 0.03928 else ((v + 0.055) / 1.055) ** 2.4
    def lum(c):
        return 0.2126 * lin(c[0]) + 0.7152 * lin(c[1]) + 0.0722 * lin(c[2])
    a, b = lum(fg), lum(bg)
    return (max(a, b) + 0.05) / (min(a, b) + 0.05)

def look(page, selector):
    """The colour a button's label really shows (its text colour at its real opacity over the card behind it), and that card colour."""
    return page.evaluate("""(sel) => {
      const e = document.querySelector(sel);
      let o = 1, n = e; while (n && n.nodeType === 1) { o *= parseFloat(getComputedStyle(n).opacity); n = n.parentElement; }
      let bg = 'rgb(0, 0, 0)', m = e; while (m && m.nodeType === 1) { const b = getComputedStyle(m).backgroundColor; if (!/rgba\\(.*, 0\\)|transparent/.test(b)) { bg = b; break; } m = m.parentElement; }
      return { colour: getComputedStyle(e).color, bg, opacity: o, disabled: !!e.disabled, cursor: getComputedStyle(e).cursor };
    }""", selector)

def effective_ratio(info, card_bg):
    fg, _ = parse_colour(info["colour"])
    base, _ = parse_colour(card_bg)
    shown = blend(fg, info["opacity"], base)
    return ratio(shown, base)

def run_pages(page, width, mode):
    tag = f"{width} px {mode}"
    page.set_viewport_size({"width": width, "height": 844})
    w.load(page, paints=v52.paints_with_needs(), recipes=t.RECIPES, units=t.UNITS, settings={"appearance": mode})
    more_page(page, "settings")
    v53.open_card_folds(page)
    scan(page, f"{tag}, Settings with every folded card open")
    more_page(page, "updates")
    page.evaluate("() => document.querySelectorAll('#changelog .more-info-button[aria-expanded=\"false\"]').forEach(b => b.click())")
    page.wait_for_timeout(120)
    scan(page, f"{tag}, Updates with every entry open")

def main():
    errors, dialogs = [], []
    app, html = read("app.js"), read("index.html")
    with sync_playwright() as p:
        browser = p.chromium.launch()
        ctx = browser.new_context(viewport={"width": 390, "height": 844}, service_workers="block")
        page = ctx.new_page()
        page.on("pageerror", lambda e: errors.append(str(e)))
        page.on("dialog", lambda d: (dialogs.append(d.message), d.dismiss()))
        attach_notices(page, dialogs.append)

        # ---------- 1. Versions ----------
        print("\n--- 1. Versions, the Updates entry and the Help line ---")
        w.load(page, paints=[])
        version = page.evaluate("APP_VERSION")
        check("APP_VERSION is v54 or later", float(version[1:]) >= 54, version)
        sw = read("sw.js")
        m = re.search(r'const VERSION = "v([\d.]+)"', sw)
        check("sw.js VERSION matches", m and "v" + m.group(1) == version, m and m.group(1))
        tags = re.findall(r'<script src="[^"]+\?v=(\d+)"', html)
        check("all six script tags carry the version number", len(tags) == 6 and set(tags) == {version[1:]}, tags)
        check("the comments that name the number agree", f'The "?v={version[1:]}" makes' in html and f'e.g. "app.js?v={version[1:]}"' in app)
        entry = page.evaluate("CHANGELOG.find(c => c.version === 'v54')")
        check("the v54 Updates entry exists and is the newest while v54 is current", bool(entry) and (version != "v54" or page.evaluate("CHANGELOG[0].version") == "v54"))
        check("the v54 entry is dated 20 Oct 2026 and has no em dash", entry and entry["date"] == "20 Oct 2026" and not any("—" in x for x in entry["changes"]))
        check("the v54 entry mentions Updates, More info, Stages, Import, Your data, Delete all units and switched off",
              entry and all(any(word in x for x in entry["changes"]) for word in ("Updates", "More info", "Stages", "Import", "Your data", "Delete all units", "switched off")))
        line = page.evaluate("() => { const li = document.querySelectorAll('#help-card-folds'); return { n: li.length, text: li[0] ? li[0].textContent : '' }; }")
        check("the existing Help item about card folds is still one item and now names Stages, Import and Your data as well",
              line["n"] == 1 and all(x in line["text"] for x in ("Faction colours", "Paint brands", "Stages", "Import", "Your data")), line)
        check("the Help item has no em dash", "—" not in line["text"])

        # ---------- 2. F5: Updates ----------
        print("\n--- 2. F5: the Updates entries ---")
        w.load(page, paints=v52.paints_with_needs(), recipes=t.RECIPES, units=t.UNITS)
        more_page(page, "updates")
        shown_n = page.evaluate("UPDATES_SHOWN")
        n = page.locator("#changelog .release").count()
        check("the page draws the newest five entries", n == shown_n == 5, (n, shown_n))
        heads = page.evaluate("() => [...document.querySelectorAll('#changelog .release h3')].map(h => h.textContent)")
        versions = page.evaluate("CHANGELOG.slice(0, UPDATES_SHOWN).map(r => [r.version, r.date])")
        check("each entry shows its version and its date", all(v in h and d in h for h, (v, d) in zip(heads, versions)), heads)
        buttons = page.locator("#changelog .release .more-info-button")
        check("each entry has one More info button, a real button, at least 44 px, with aria-expanded and aria-controls",
              buttons.count() == 5 and all(buttons.nth(i).evaluate("e => e.tagName") == "BUTTON" and buttons.nth(i).bounding_box()["height"] >= 43.5
                                           and buttons.nth(i).get_attribute("aria-expanded") in ("true", "false")
                                           and page.locator("#" + buttons.nth(i).get_attribute("aria-controls")).count() == 1 for i in range(5)))
        check("the buttons are named with their version (no paint names)", page.evaluate("() => [...document.querySelectorAll('#changelog .more-info-button')].map(b => b.getAttribute('aria-label'))")
              == [f"{'Less' if i == 0 else 'More'} info: {v}" for i, (v, d) in enumerate(versions)])
        check("the newest entry is open, the other four are shut", release_states(page) == ["true", "false", "false", "false", "false"], release_states(page))
        newest_lines = page.locator("#changelog .release").nth(0).locator("li")
        check("the newest entry's lines are in view", newest_lines.count() == page.evaluate("CHANGELOG[0].changes.length") and newest_lines.first.is_visible())
        older = page.locator("#changelog .release").nth(1)
        check("an older entry's lines are not in view", not older.locator("li").first.is_visible())
        check("an older entry still holds all its lines in the page (read with text_content)",
              all(c[:30] in (page.locator("#changelog .release").nth(1).text_content() or "") for c in page.evaluate("CHANGELOG[1].changes")))
        h_before = page.evaluate("document.getElementById('view-updates').getBoundingClientRect().height")
        check("the page is much shorter than before (the lines of four entries are tucked away)", h_before < 1400, h_before)
        check("the You're on version line and the Unofficial line are still shown",
              f"You're on version {version}" in page.inner_text("#view-updates") and "Unofficial fan-made app" in page.inner_text("#view-updates"))
        before = storage_dump(page)
        press(page, buttons.nth(1))
        check("tapping More info on an older entry opens it (Less info, lines in view)",
              buttons.nth(1).get_attribute("aria-expanded") == "true" and "Less info" in buttons.nth(1).inner_text() and older.locator("li").first.is_visible())
        check("opening it did not close the newest", release_states(page)[:2] == ["true", "true"])
        press(page, buttons.nth(0))
        check("tapping the newest entry's button shuts it (More info)", buttons.nth(0).get_attribute("aria-expanded") == "false" and "More info" in buttons.nth(0).inner_text()
              and not newest_lines.first.is_visible())
        check("opening and shutting entries saved nothing (every stored value is the same)", storage_dump(page) == before)
        page.evaluate("renderUpdates()")
        check("drawing the page again keeps each entry as it was left", release_states(page) == ["false", "true", "false", "false", "false"], release_states(page))
        tab(page, "dashboard")
        more_page(page, "updates")
        check("the entries stay as left while the app is open (to another tab and back)", release_states(page) == ["false", "true", "false", "false", "false"], release_states(page))
        page.reload(); page.wait_for_function("() => typeof APP_VERSION === 'string'"); page.wait_for_timeout(300)
        more_page(page, "updates")
        check("opened afresh: the newest is open and the rest are shut again (the state is not saved)", release_states(page) == ["true", "false", "false", "false", "false"], release_states(page))

        # ---------- 3. F14: Stages, Import, Your data ----------
        print("\n--- 3. F14: Stages, Import and Your data fold shut ---")
        w.load(page, paints=v52.paints_with_needs(), recipes=t.RECIPES, units=t.UNITS)
        more_page(page, "settings")
        for key, card, inside in NEW_CARDS:
            btn = page.locator(f"{card} > h2 > button.card-fold-button")
            check(f"{key}: the heading is a real button inside the h2, aria-expanded false, controls its panel, at least 44 px",
                  btn.count() == 1 and btn.get_attribute("aria-expanded") == "false" and btn.get_attribute("aria-controls") == f"card-fold-{key}-panel"
                  and btn.bounding_box()["height"] >= 43.5 and page.locator(f"{card} > h2").count() == 1)
            check(f"{key}: it carries the same chevron as the other folded cards", page.locator(f"{card} .card-fold-button .fold-mark").count() == 1)
            check(f"{key}: shut at the start, its contents are not on show", not page.locator(inside).first.is_visible())
            check(f"{key}: the heading still reads as the card's name", page.locator(f"{card} > h2").inner_text().strip() in ("Stages", "Import", "Your data"))
        before = storage_dump(page)
        buttons = {key: page.locator(f"{card} > h2 > button.card-fold-button") for key, card, inside in NEW_CARDS}
        press(page, buttons["stages"])
        check("Stages: tapping the heading opens it (aria-expanded true) and the stage list shows",
              buttons["stages"].get_attribute("aria-expanded") == "true" and page.locator("#stage-list li").first.is_visible() and page.locator("#add-stage").is_visible())
        check("Stages: its explanation is still behind its own More info inside the card", page.locator("#stages-card .more-info-button").count() == 1)
        press(page, buttons["import"])
        check("Import: tapping the heading opens it and the Import CSV button shows", buttons["import"].get_attribute("aria-expanded") == "true" and page.locator("#csv-button").is_visible())
        press(page, buttons["your-data"])
        check("Your data: tapping the heading opens it and Clean up photo storage, Restore example recipes and Delete all units show",
              buttons["your-data"].get_attribute("aria-expanded") == "true" and page.locator("#clean-photos").is_visible()
              and page.locator("#restore-examples").is_visible() and page.locator("#delete-all").is_visible())
        check("Delete all units sits inside Your data, once, and nowhere else",
              page.locator("#your-data-card #delete-all").count() == 1 and page.locator("#delete-all").count() == 1 and page.locator("#card-fold-your-data-panel #delete-all").count() == 1)
        n_units = page.evaluate("() => models.length")
        press(page, page.locator("#delete-all"))
        asked = page.locator("#dialog-yes").is_visible() and page.locator("#dialog-no").is_visible()
        check("Delete all units still asks first in the app's own box, with Yes and No", asked and "Delete all" in (page.locator("#dialog").text_content() or ""))
        press(page, page.locator("#dialog-no"))
        check("saying No deletes nothing and puts focus back on Delete all units",
              page.evaluate("() => models.length") == n_units and page.evaluate("() => document.activeElement.id") == "delete-all", page.evaluate("() => document.activeElement.id"))
        check("Your data: the summary lines are still filled in",
              len((page.locator("#data-summary").text_content() or "").strip()) > 0)
        press(page, buttons["stages"]); press(page, buttons["import"]); press(page, buttons["your-data"])
        check("tapping the headings again shuts all three",
              all(b.get_attribute("aria-expanded") == "false" for b in buttons.values())
              and not page.locator("#stage-list").is_visible() and not page.locator("#csv-button").is_visible() and not page.locator("#delete-all").is_visible())
        check("opening and shutting them saved nothing (every stored value is the same)", storage_dump(page) == before)
        press(page, buttons["import"])
        tab(page, "dashboard")
        more_page(page, "settings")
        check("an open card stays open while the app is open (to another tab and back)", buttons["import"].get_attribute("aria-expanded") == "true" and page.locator("#csv-button").is_visible())
        page.reload(); page.wait_for_function("() => typeof APP_VERSION === 'string'"); page.wait_for_timeout(300)
        more_page(page, "settings")
        check("all three are shut again when the app is opened afresh",
              all(page.locator(f"{card} > h2 > button.card-fold-button").get_attribute("aria-expanded") == "false" for key, card, inside in NEW_CARDS))
        folded = page.evaluate("() => [...document.querySelectorAll('#view-settings .card-fold')].map(c => c.id)")
        check("five cards fold in all (Stages, Faction colours, Paint brands, Import, Your data), in the page's order",
              folded == ["stages-card", "faction-colours-card", "brands-card", "import-card", "your-data-card"], folded)
        stay = page.evaluate("""() => [...document.querySelectorAll('#view-settings > .card, #view-settings .card')].filter(c => c.getClientRects().length && !c.classList.contains('card-fold'))
                                 .map(c => (c.querySelector(':scope > h2') || { textContent: '' }).textContent.trim()).filter(Boolean)""")
        check("Backups, Appearance, Theme, Counting visits, Shop links and Colours are not folded and are in view",
              all(any(name in s for s in stay) for name in ("Backups", "Appearance", "Theme", "Counting visits", "Shop links", "Colours")), stay)
        check("the Backups buttons are still in view and 44 px (the five big buttons)",
              page.evaluate("() => [...document.querySelectorAll('#backup-card .plain-button')].filter(b => b.getClientRects().length).every(b => b.getBoundingClientRect().height >= 43.5)"))
        check("each card's own More info is still there (Stages, Import, Your data)",
              all(page.locator(f"{card} .more-info-button").count() >= 1 for key, card, inside in NEW_CARDS))
        gone = page.evaluate("() => document.querySelectorAll('#view-settings > .card > h2, #view-settings .card-fold > h2').length")
        check("the page height with the five folded cards shut is much shorter than the old long Settings page",
              page.evaluate("document.getElementById('view-settings').getBoundingClientRect().height") < 2500)

        # ---------- 4. F15: disabled buttons ----------
        print("\n--- 4. F15: the fainter disabled look ---")
        check("the global rule is 0.55 and the old 0.35 is gone", re.search(r"button:disabled \{ opacity: 0\.55;", html) and not re.search(r"button:disabled \{ opacity: 0\.35", html))
        for mode in ("dark", "light"):
            w.load(page, paints=v52.paints_with_needs(), recipes=t.RECIPES, units=t.UNITS, settings={"appearance": mode})
            more_page(page, "settings")
            v53.open_card_folds(page)
            clean = look(page, "#clean-photos")
            first_up = look(page, "#stage-list li:first-child button:disabled")
            live_up = look(page, "#stage-list li:nth-child(2) button:not(:disabled)")
            card_bg = clean["bg"]
            check(f"{mode}: Clean up photo storage is disabled, at 0.55, with the plain cursor", clean["disabled"] and abs(clean["opacity"] - 0.55) < 0.01 and clean["cursor"] == "default", clean)
            check(f"{mode}: the first stage's up arrow is disabled and at 0.55", first_up["disabled"] and abs(first_up["opacity"] - 0.55) < 0.01, first_up)
            check(f"{mode}: a live reorder arrow is at full strength", live_up["disabled"] is False and abs(live_up["opacity"] - 1) < 0.01, live_up)
            last_down = look(page, "#stage-list li:last-child button:disabled")
            check(f"{mode}: the last stage's down arrow is disabled and at 0.55", last_down["disabled"] and abs(last_down["opacity"] - 0.55) < 0.01, last_down)
            bg_list = page.evaluate("() => { let m = document.querySelector('#stages-card'); return getComputedStyle(m).backgroundColor; }")
            r_off = effective_ratio(first_up, bg_list)
            r_on = effective_ratio(live_up, bg_list)
            r_clean = effective_ratio(clean, page.evaluate("() => getComputedStyle(document.querySelector('#your-data-card')).backgroundColor"))
            check(f"{mode}: the disabled arrow is easier to read than before (about 2.5:1; it was 1.7 to 1.8:1 at 0.35)", r_off >= 2.3, round(r_off, 2))
            check(f"{mode}: Clean up photo storage is easier to read than before (about 3:1 or better; it was 2.2 to 2.8:1)", r_clean >= 2.8, round(r_clean, 2))
            check(f"{mode}: a disabled arrow still reads as switched off (clearly dimmer than a live one)", r_on >= r_off * 1.3, (round(r_on, 2), round(r_off, 2)))
            check(f"{mode}: the disabled arrows really are not pressable", page.locator("#stage-list li:first-child button:disabled").count() >= 1
                  and page.evaluate("() => document.querySelector('#stage-list li:first-child button:disabled').disabled"))

        # ---------- 5. Targets and sideways scroll ----------
        print("\n--- 5. Tap targets and sideways scroll ---")
        for width, mode in ((360, "light"), (390, "dark"), (1000, "dark")):
            run_pages(page, width, mode)

        # ---------- 6. What the new code is allowed to contain ----------
        print("\n--- 6. The new code ---")
        snippet = app[app.index("// v54: the version and date stay in view"):app.index("box.appendChild(div);")]
        check("the Updates code uses the shared pageMoreInfo and infoState (no new helper)", "pageMoreInfo(" in snippet and "infoState(" in snippet)
        check("the Updates addition has no innerHTML, no storage and no network code",
              not re.search(r"innerHTML|insertAdjacentHTML|localStorage|sessionStorage|indexedDB|fetch\(|XMLHttpRequest|WebSocket", snippet))
        check("foldCard and openCardFold are each still defined once (the shared pieces from v53 are reused, nothing copied)",
              len(re.findall(r"function foldCard\(", app)) == 1 and len(re.findall(r"function openCardFold\(", app)) == 1)
        check("the three new folds are one line each at start-up, using foldCard",
              all(f'foldCard(document.getElementById("{c}"), "{k}");' in app for c, k in (("stages-card", "stages"), ("import-card", "import"), ("your-data-card", "your-data"))))
        check("no new function was added for the folds (the v36 and v37 scanned code is untouched)", "function foldStages" not in app and "function foldImport" not in app)
        check("the new CSS adds no colour (only the opacity changed)", "button:disabled { opacity: 0.55; cursor: default; }" in html)
        check("no em dash in the v54 Updates entry or the new Help words", "—" not in app[app.index('{ version: "v54"'):app.index('{ version: "v53"')] and "fold shut the same way" in html)

        # ---------- 7. No errors ----------
        print("\n--- 7. No errors ---")
        check("no page errors", not errors, errors[:3])
        check("no browser pop-ups were shown", not dialogs, dialogs[:3])
        browser.close()

    ok = all(results)
    print(f"\n{sum(results)} of {len(results)} checks passed")
    sys.exit(0 if ok else 1)

if __name__ == "__main__":
    main()
