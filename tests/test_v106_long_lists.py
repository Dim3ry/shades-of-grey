"""X8d tests for Minifolio (long lists on a phone). New behaviour only:
1. Guides > Techniques shows 30 rows first; Show more adds the next 30; search still finds an entry past the first page.
2. Detail recipes and Basing open on their first group (Body, Dry ground); All is still a choice.
3. The Colour ideas card in the recipe editor shows its Detail recipes and Basing lists collapsed, and expands.
4. Layout at 390 and 360: no sideways scroll, Show more is 44 px or more.
Run all tests with `python3 tests/run_all.py`, or serve the repo folder and run this file on its own."""
import os, sys
from playwright.sync_api import sync_playwright

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import test_v31 as t
from launch_helpers import wait_settled, tap_tab

results = []

def check(name, ok, detail=""):
    results.append(bool(ok))
    print(("PASS " if ok else "FAIL ") + name + ("" if ok else f"  -> {detail}"))

def open_guides(page, first=False):
    if first:
        page.evaluate("() => { settings.tab = 'dashboard'; }")
        tap_tab(page, "guides")
        page.click('#more-seg button[data-page="guides"]')
    page.evaluate("() => { Object.assign(guidesState, { view: 'home', cat: '', key: '', kind: '', query: '', shownRows: {} }); Object.assign(compendiumState, { detailGroup: '', basingGroup: '' }); renderGuides(); }")
    wait_settled(page)

def main():
    errors = []
    with sync_playwright() as p:
        browser = p.chromium.launch()
        for width, scheme in ((390, "dark"), (360, "light")):
            ctx = browser.new_context(viewport={"width": width, "height": 844}, service_workers="block", color_scheme=scheme)
            page = ctx.new_page()
            page.on("pageerror", lambda x: errors.append(str(x)))
            page.on("dialog", lambda d: (errors.append("dialog: " + d.message), d.dismiss()))
            t.load(page, launch=True, settings={"tab": "guides", "examplesChecked": True})
            print(f"\n--- {width} px, {scheme} ---")
            open_guides(page, True)
            page.click('.guides-cats [data-cat="techniques"]')
            rows = lambda: page.evaluate("() => document.querySelectorAll('.guides-main .guides-row').length")
            check("Techniques shows 30 rows first", rows() == 30, rows())
            page.click(".guides-more")
            check("Show more adds the next 30", rows() == 60, rows())
            check("the focus moves to the first new row", page.evaluate("() => document.activeElement.classList.contains('guides-row') && document.activeElement.dataset.guide") == page.evaluate("() => document.querySelectorAll('.guides-main .guides-row')[30].dataset.guide"))
            check("Show more is 44 px or more", page.evaluate("() => document.querySelector('.guides-more').getBoundingClientRect().height") >= 44)
            check("no sideways scroll", page.evaluate("() => document.documentElement.scrollWidth <= document.documentElement.clientWidth"))
            last = page.evaluate("() => { const l = knowledgeIndex().list({ category: 'techniques' }); return l[l.length - 1].title; }")
            page.click("#guides-back")
            page.fill("#guides-search", last)
            check("search finds an entry beyond the first page", page.evaluate("(t) => [...document.querySelectorAll('.guides-lower .guides-row-title')].some(e => e.textContent === t)", last))

            open_guides(page)
            page.click('.guides-cats [data-cat="detail"]')
            wait_settled(page)
            check("Detail recipes opens on Body", page.evaluate("() => document.querySelector('[data-detail-group=\"body\"]').getAttribute('aria-pressed')") == "true")
            n_body = page.evaluate("() => document.querySelectorAll('#guides-main [data-detail], [data-detail]').length")
            page.click('[data-detail-group="all"]')
            check("All is still a choice and lists more", page.evaluate("() => document.querySelectorAll('[data-detail]').length") > n_body)
            open_guides(page)
            page.click('.guides-cats [data-cat="basing"]')
            wait_settled(page)
            check("Basing opens on Dry ground", page.evaluate("() => document.querySelector('[data-basing-group=\"ground\"]').getAttribute('aria-pressed')") == "true")
            ctx.close()

        print("\n--- Colour ideas card in the recipe editor ---")
        ctx = browser.new_context(viewport={"width": 390, "height": 844}, service_workers="block")
        page = ctx.new_page()
        page.on("pageerror", lambda x: errors.append(str(x)))
        t.load(page, launch=True, settings={"tab": "recipes", "examplesChecked": True})
        built = page.evaluate("""() => {
            const door = { short: false, state: colourIdeasState, id: (s) => 'x8d-' + s, addSteps: true };
            const box = buildDetailRecipes(door, () => {}, () => {}, () => {});
            document.body.appendChild(box);
            const chips = [...box.querySelectorAll('#x8d-detail-chips .chip')];
            const visible = chips.filter(c => !c.hidden).length;
            const btn = box.querySelector('.chips-more');
            const before = [chips.length, visible, btn && btn.textContent, btn && btn.getAttribute('aria-expanded')];
            btn.click();
            const after = [chips.filter(c => !c.hidden).length, btn.textContent, btn.getAttribute('aria-expanded')];
            return { before, after, tall: btn.getBoundingClientRect().height };
        }""")
        check("Colour ideas shows only the first 12 of the detail recipes", built["before"][1] == 12 and built["before"][0] > 100, built)
        check("the button says how many there are and starts closed", built["before"][2].startswith("Show all") and built["before"][3] == "false", built)
        check("tapping it shows every recipe and the state is announced", built["after"][0] == built["before"][0] and built["after"][2] == "true" and built["after"][1] == "Show fewer", built)
        check("the button is 44 px or more", built["tall"] >= 44, built)
        ctx.close()
        browser.close()
    check("no page errors or pop-ups", not errors, errors)
    print(f"\n{sum(results)} / {len(results)} passed")
    sys.exit(0 if all(results) else 1)

main()
