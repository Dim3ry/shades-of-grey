"""UX2 tests for Minifolio (Guides keep your place). New behaviour only:
1. Opening a guide shows its Back button and title fully below the menu bar (not under it), and not under the bottom band, at 390x844,
   360x640 and 320x568: from search results scrolled down, from deep in A to Z, from a topic group, and from a See also link.
2. Back from a guide returns to the list it was opened from, at the same scroll position, with the focus on the row you opened:
   search results (the search text kept), A to Z (Show more kept), a topic group. Related and See also links inside the entry keep
   that way back. A Detail recipe or Basing tip opened from search goes back to the results, and Detail recipes keeps its own chosen
   group and Filters fold. On a wide screen, Back goes to the list beside the entry (Detail recipes, group and fold kept). An entry
   with an open Where to buy fold-out still goes back to the right row. Opening from another screen goes back as before (its group).
Run all tests with `python3 tests/run_all.py`, or serve the repo folder and run this file on its own."""
import os, sys
from playwright.sync_api import sync_playwright

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import test_v31 as t
from launch_helpers import wait_settled, tap_tab

results = []

def check(name, ok, detail=""):
    results.append(bool(ok))
    print(("PASS " if ok else "FAIL ") + name + ("" if ok else f"  -> {str(detail)[:600]}"))

def home(page, order="topics", query=""):
    page.evaluate("(o) => { Object.assign(guidesState, { view: 'home', cat: '', group: '', key: '', kind: '', query: '', order: o, shownRows: {}, from: null }); renderGuides(); scrollTo(0, 0); }", order)
    if query:
        page.fill("#guides-search", query)
    wait_settled(page)

# the Back button and the title: the bar's bottom, and what a tap at the title's top-left and centre would hit (the title itself, not
# the menu bar or the bottom band over it)
SEEN = """() => { const bar = document.querySelector('main > .app-bar').getBoundingClientRect(), back = document.getElementById('guides-back'),
    h = document.querySelector('.guides-main .guides-title'); if (!back || !h) return null; const r = h.getBoundingClientRect();
    const hits = (x, y) => { const el = document.elementFromPoint(x, y); return !!el && h.contains(el); };
    return { bar: Math.round(bar.bottom), back: Math.round(back.getBoundingClientRect().top), top: Math.round(r.top), bottom: Math.round(r.bottom),
             corner: hits(r.left + 2, r.top + 2), centre: hits(r.left + Math.min(r.width, 40) / 2, (r.top + r.bottom) / 2), title: h.textContent }; }"""

def fully_seen(s):
    return bool(s) and s["back"] >= s["bar"] and s["top"] >= s["bar"] and s["corner"] and s["centre"]

# a visible row near the middle of the screen in a list (not hidden by the menu bar or the bottom band)
MIDDLE = """(sel) => { const rows = [...document.querySelectorAll(sel)].filter(r => r.offsetParent);
    const mid = innerHeight * 0.45; let best = null;
    for (const r of rows) { const b = r.getBoundingClientRect(); if (b.top > 80 && (!best || Math.abs(b.top - mid) < Math.abs(best.getBoundingClientRect().top - mid))) best = r; }
    return best ? [best.dataset.guide, best.dataset.kind] : null; }"""

# where the focus is after Back: the row, in which list, on screen (a tap at its centre hits it), and the scroll position
FOCUS = """() => { const a = document.activeElement, b = a.getBoundingClientRect(), el = document.elementFromPoint(b.left + b.width / 2, b.top + b.height / 2);
    return { key: a.dataset.guide || '', kind: a.dataset.kind || '', nav: !!a.closest('.guides-nav'), seen: !!el && a.contains(el), y: Math.round(scrollY),
             q: (document.getElementById('guides-search') || {}).value, view: guidesState.view, back: (document.getElementById('guides-back') || {}).textContent || '' }; }"""

def open_row(page, list_sel, scroll_to):
    """Scroll the page, pick a row near the middle of the screen, tap it. Returns (key, kind, scroll before)."""
    page.evaluate("(y) => scrollTo(0, y)", scroll_to)
    wait_settled(page)
    key, kind = page.evaluate(MIDDLE, f"{list_sel} .guides-row[data-guide]")
    y = page.evaluate("Math.round(scrollY)")
    page.click(f'{list_sel} .guides-row[data-guide="{key}"][data-kind="{kind}"]')
    wait_settled(page)
    return key, kind, y

def back(page):
    page.click("#guides-back")
    wait_settled(page)
    return page.evaluate(FOCUS)

def main():
    errors = []
    with sync_playwright() as p:
        browser = p.chromium.launch()
        ctx = browser.new_context(viewport={"width": 390, "height": 844}, service_workers="block")
        page = ctx.new_page()
        page.on("pageerror", lambda x: errors.append(str(x)))
        page.on("dialog", lambda d: (errors.append("dialog: " + d.message), d.dismiss()))
        t.load(page, settings={"tab": "guides", "examplesChecked": True})
        tap_tab(page, "guides")
        page.click('#more-seg button[data-page="guides"]')
        page.wait_for_function("() => typeof guidesNote === 'function'")
        wait_settled(page)
        # an entry with a See also link to an entry in another group, and the group it sits in (G2a, G2b)
        src, target, grp, cat = page.evaluate("""() => { const kn = knowledgeIndex();
            for (const [k, ks] of Object.entries(GUIDE_GROUPS.seeAlso)) { const e = kn.get(k), p = guidePlace(e); if (!p) continue;
                const other = ks.find(x => { const q = guidePlace(kn.get(x)); return q && q.group !== p.group; });
                if (other) return [k, other, p.group, e.category]; } }""")

        print("\n--- 1. Opening a guide shows its title below the menu bar ---")
        for w, h, scheme in [(390, 844, "dark"), (360, 640, "light"), (320, 568, "dark")]:
            page.set_viewport_size({"width": w, "height": h})
            page.evaluate("(lt) => { settings.appearance = lt ? 'light' : 'dark'; applyPalette(settings.palette); render(); }", scheme == "light")
            seen = []
            home(page, query="paint")
            open_row(page, ".guides-nav", 600)
            seen.append(("search", page.evaluate(SEEN)))
            home(page, "az")
            page.click(".guides-more")
            open_row(page, ".guides-az", 2400)
            seen.append(("A to Z", page.evaluate(SEEN)))
            home(page)
            page.click(f'.guides-cats [data-cat="{cat}"]')
            page.click(f'.guides-main [data-group="{grp}"]')
            wait_settled(page)
            page.locator(f'.guides-main [data-guide="{src}"]').scroll_into_view_if_needed()
            page.click(f'.guides-main [data-guide="{src}"]')
            wait_settled(page)
            seen.append(("group", page.evaluate(SEEN)))
            page.evaluate("() => scrollTo(0, document.documentElement.scrollHeight)")
            page.click(f'.guides-seealso-link[data-see-also="{target}"]')
            wait_settled(page)
            seen.append(("See also", page.evaluate(SEEN)))
            bad = [x for x in seen if not fully_seen(x[1])]
            check(f"{w}x{h} {scheme}: from search, A to Z, a group and See also, Back and the title show in full under the menu bar", not bad, bad)

        print("\n--- 2. Back returns to the list you came from ---")
        page.set_viewport_size({"width": 390, "height": 844})
        home(page, query="paint")
        n_results = page.locator(".guides-nav .guides-row").count()
        key, kind, y = open_row(page, ".guides-nav", 700)
        check("from search results, Back says Back to results", page.inner_text("#guides-back") == "Back to results", page.inner_text("#guides-back"))
        f = back(page)
        check("Back from a search result: the results again, search text kept, same rows",
              f["view"] == "home" and f["q"] == "paint" and page.locator(".guides-nav .guides-row").count() == n_results, f)
        check("... at the same scroll position, with the focus on the row you opened (on screen)",
              abs(f["y"] - y) <= 1 and y > 300 and f["key"] == key and f["kind"] == kind and f["nav"] and f["seen"], (y, f))

        home(page, "az")
        page.click(".guides-more")
        page.click(".guides-more")
        wait_settled(page)
        n_az = page.locator(".guides-az .guides-row").count()
        key, kind, y = open_row(page, ".guides-az", 3600)
        check("from A to Z, Back says Back to A to Z", page.inner_text("#guides-back") == "Back to A to Z", page.inner_text("#guides-back"))
        f = back(page)
        check("Back from an A to Z entry: A to Z again with the rows Show more had added",
              page.locator(".guides-az").count() == 1 and page.locator(".guides-az .guides-row").count() == n_az and n_az >= 90, (n_az, f))
        check("... at the same scroll position, with the focus on the row you opened (on screen)",
              abs(f["y"] - y) <= 1 and y > 2000 and f["key"] == key and f["nav"] and f["seen"], (y, f))

        big = page.evaluate("(c) => guideGroupsOf(c).groups.slice().sort((a, b) => b.entries.length - a.entries.length)[0].name", "techniques")
        home(page)
        page.click('.guides-cats [data-cat="techniques"]')
        page.click(f'.guides-main [data-group="{big}"]')
        wait_settled(page)
        key, kind, y = open_row(page, ".guides-main", 900)
        check(f"from a topic group, Back says Back to {big}", page.inner_text("#guides-back") == f"Back to {big}", page.inner_text("#guides-back"))
        f = back(page)
        check("Back from a group's entry: the group again, same scroll position, the focus on the row you opened (on screen)",
              f["view"] == "group" and page.inner_text(".guides-main .guides-title") == big and abs(f["y"] - y) <= 1 and y > 300
              and f["key"] == key and not f["nav"] and f["seen"], (y, f))

        print("\n--- Links inside an entry keep the way back ---")
        home(page, query="paint")
        key, kind, y = open_row(page, ".guides-nav", 500)
        page.click(".guides-entry .guides-related button")
        wait_settled(page)
        hop = page.evaluate("() => guidesState.key")
        rel_ok = hop != key and page.inner_text("#guides-back") == "Back to results" and fully_seen(page.evaluate(SEEN))
        page.evaluate("() => scrollTo(0, document.documentElement.scrollHeight)")
        also = page.evaluate("() => (document.querySelector('.guides-seealso-link') || {}).dataset")
        if also and also.get("seeAlso"):
            page.click(".guides-seealso-link")
            wait_settled(page)
        check("a Related link, then a See also link: the new entry shows at the top and Back still says Back to results",
              rel_ok and page.inner_text("#guides-back") == "Back to results", (hop, also, page.inner_text("#guides-back")))
        f = back(page)
        check("... and Back goes to the search results, focus on the row first opened, same scroll position",
              f["q"] == "paint" and f["key"] == key and f["nav"] and f["seen"] and abs(f["y"] - y) <= 1, (y, f))

        print("\n--- Detail recipes, Basing and Where to buy ---")
        home(page)
        page.click('.guides-cats [data-cat="detail"]')
        wait_settled(page)
        if page.get_attribute('#cmp-detail-groups [data-detail-group="metal"]', "aria-pressed") != "true":
            page.click('#cmp-detail-groups [data-detail-group="metal"]')
        page.click("#cmp-detail-groups-toggle")
        wait_settled(page)
        before = page.evaluate("() => [compendiumState.detailGroup, compendiumState.detail, document.getElementById('cmp-detail-groups-toggle').getAttribute('aria-expanded')]")
        home(page, query="eye")
        pick = page.evaluate("() => [...document.querySelectorAll('.guides-nav .guides-row[data-kind=\"detail\"]')].map(r => r.dataset.guide).find(k => DETAIL_RECIPES.find(x => x.key === k).group !== 'metal')")
        y = page.evaluate("Math.round(scrollY)")
        page.click(f'.guides-nav .guides-row[data-kind="detail"][data-guide="{pick}"]')
        wait_settled(page)
        opened = page.evaluate("(k) => compendiumState.detail === k && guidesState.view === 'category' && !!document.querySelector('#cmp-detail-chips [data-detail=\"' + k + '\"][aria-pressed=\"true\"]')", pick)
        check("a Detail recipe from search opens in Detail recipes, title in full, Back says Back to results",
              opened and fully_seen(page.evaluate(SEEN)) and page.inner_text("#guides-back") == "Back to results", (pick, opened))
        f = back(page)
        check("Back goes to the search results, focus on that recipe's row", f["q"] == "eye" and f["key"] == pick and f["kind"] == "detail" and f["seen"] and abs(f["y"] - y) <= 1, f)
        page.fill("#guides-search", "")
        page.click('.guides-cats [data-cat="detail"]')
        wait_settled(page)
        after = page.evaluate("() => [compendiumState.detailGroup, compendiumState.detail, document.getElementById('cmp-detail-groups-toggle').getAttribute('aria-expanded')]")
        check("Detail recipes keeps your own chosen group (Metal) and Filters fold after that", before == after == ["metal", "", "false"]
              and page.get_attribute('#cmp-detail-groups [data-detail-group="metal"]', "aria-pressed") == "true", (before, after))

        bad = []
        for q, k, kd in [("varnish", "varnishing", "guide"), ("grass fibres", "static-grass", "basing")]:
            home(page, query=q)
            page.click(f'.guides-nav .guides-row[data-guide="{k}"][data-kind="{kd}"]')
            wait_settled(page)
            fold = page.locator(f'#compendium-body .guides-main [data-where-buy="{k}"] > summary')
            had = fold.count() == 1
            if had:
                fold.click()
                wait_settled(page)
            f = back(page)
            if not (had and f["key"] == k and f["kind"] == kd and f["seen"] and f["q"] == q): bad.append((k, had, f))
        check("an entry and a Basing tip with their Where to buy fold-out open still go back to the right row", not bad, bad)

        print("\n--- Wide screen and other screens ---")
        page.set_viewport_size({"width": 1280, "height": 900})
        home(page)
        page.click('.guides-cats [data-cat="detail"]')
        wait_settled(page)
        page.fill("#guides-search", "rust")
        wait_settled(page)
        key = page.get_attribute('.guides-nav .guides-row[data-kind="guide"]', "data-guide")
        page.click(f'.guides-nav .guides-row[data-kind="guide"][data-guide="{key}"]')
        wait_settled(page)
        label = page.inner_text("#guides-back")
        f = back(page)
        check("wide screen: an entry opened from the list beside Detail recipes goes Back to Detail recipes, group and Filters fold kept, focus on the row",
              label == "Back to Detail recipes" and f["view"] == "category" and page.evaluate("() => guidesState.cat") == "detail"
              and page.get_attribute('#cmp-detail-groups [data-detail-group="metal"]', "aria-pressed") == "true"
              and page.get_attribute("#cmp-detail-groups-toggle", "aria-expanded") == "false" and f["key"] == key and f["nav"] and f["seen"], (label, f))
        page.set_viewport_size({"width": 390, "height": 844})

        home(page, query="paint")
        open_row(page, ".guides-nav", 0)
        tap_tab(page, "dashboard")
        wait_settled(page)
        page.evaluate("(k) => openGuide(k)", src)
        wait_settled(page)
        check("opened from another screen (openGuide), the entry shows in full and Back goes to its group, as before",
              fully_seen(page.evaluate(SEEN)) and page.inner_text("#guides-back") == f"Back to {grp}", page.inner_text("#guides-back"))

        check("no page errors or pop-ups", errors == [], errors)
        browser.close()
    print(f"\n{sum(results)}/{len(results)} checks passed")
    return 0 if all(results) else 1

if __name__ == "__main__":
    sys.exit(main())
