"""G3 tests for Minifolio (numbers for Detail recipes and Basing in Guides, and the Filters button). New behaviour only:
1. Numbers follow A to Z: each section's groups are numbered A to Z after its section number (3.2), and each recipe or tip A to Z
   inside its group (3.2.5). Worked out here independently from the data, then compared with the chips on screen.
2. In Guides the group buttons and the recipe or tip chips show those numbers, in number order; keys are unchanged, so a chip still
   opens its recipe. The recipe editor's card and the old door show no numbers and no Filters button.
3. The Filters button folds the row of group buttons away and shows it again (shown at first, arrow down when shown and right when
   folded); a chosen group still filters while folded and after showing again; the state is kept while the app is open, not saved.
4. Layout at 390x844 dark, 360x640 light and 320 px dark and light: no sideways scroll, taps 44 px or more, the Filters button on
   one line, each number on one line, inside its chip, on the first line of the title.
Run all tests with `python3 tests/run_all.py`, or serve the repo folder and run this file on its own."""
import os, sys
from playwright.sync_api import sync_playwright

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import test_v31 as t
from launch_helpers import wait_settled, tap_tab, app_ready, leave_launch, quiet

results = []

def check(name, ok, detail=""):
    results.append(bool(ok))
    print(("PASS " if ok else "FAIL ") + name + ("" if ok else f"  -> {str(detail)[:600]}"))

PARTS = {"detail": ("DETAIL_GROUPS", "DETAIL_RECIPES", "detail-group", "detail"), "basing": ("BASING_GROUPS", "BASING_TIPS", "basing-group", "basing")}

def arrow(page, sel):
    quiet(page)   # the arrow turns with a short transition
    return page.evaluate(ARROW, sel)

def open_cat(page, cat):
    page.evaluate("() => { Object.assign(guidesState, { view: 'home', cat: '', group: '', key: '', kind: '', query: '', order: 'topics' }); renderGuides(); }")
    page.click(f'.guides-cats [data-cat="{cat}"]')
    page.wait_for_selector(f"#cmp-{cat}-groups", state="attached")   # (it may be folded away)
    wait_settled(page)

# the numbers worked out here from the data (A to Z by name, ignoring case and accents, like the other sections), not from the app's function
WANT = """([cat, groups, items]) => { const az = (a, b) => a.name.localeCompare(b.name, 'en', { sensitivity: 'base' });
    const sec = String(GUIDE_CATEGORIES.findIndex(c => c.key === cat) + 1), out = { groups: [], items: [] };
    [...groups].sort(az).forEach((g, i) => { out.groups.push([g.key, sec + '.' + (i + 1)]);
        items.filter(x => x.group === g.key).sort(az).forEach((x, j) => out.items.push([x.key, sec + '.' + (i + 1) + '.' + (j + 1)])); });
    return out; }"""
CHIPS = """(sel) => [...document.querySelectorAll(sel)].map(c => [c.dataset.detailGroup || c.dataset.basingGroup || c.dataset.detail || c.dataset.basing, (c.querySelector('.guides-num') || {}).textContent || ''])"""
ARROW = """(sel) => { const m = getComputedStyle(document.querySelector(sel + ' .fold-mark')).transform.match(/matrix\\(([^,]+), ([^,]+)/); return m ? Math.round(Math.atan2(+m[2], +m[1]) * 180 / Math.PI) : null; }"""

# visible numbered chips: number on one line, inside the chip, on the title's first line; the Filters button on one line; no sideways scroll; taps 44 px or more
LAYOUT = """() => {
    const bad = [];
    for (const c of [...document.querySelectorAll('#compendium-body .g3-num-chip')].filter(c => c.offsetParent)) {
        const n = c.querySelector('.guides-num').getBoundingClientRect(), ti = c.querySelector('.g3-chip-title'), cr = c.getBoundingClientRect();
        const g = document.createRange(); g.setStart(ti.firstChild, 0); g.setEnd(ti.firstChild, 1); const first = g.getBoundingClientRect();
        if (n.height > 22 || n.right > cr.right - 4 || n.left < ti.getBoundingClientRect().right - 1 || n.top > first.bottom || n.bottom < first.top) bad.push(ti.textContent);
    }
    const f = [...document.querySelectorAll('#compendium-body .g3-filters')].filter(b => b.offsetParent).map(b => { const r = document.createRange(); r.selectNodeContents(b.firstChild); return r.getClientRects().length; });
    const small = [...document.querySelectorAll('#compendium-body button')].filter(b => b.offsetParent && b.getBoundingClientRect().height < 44).map(b => b.textContent);
    return { chips: document.querySelectorAll('#compendium-body .g3-num-chip').length, bad, filtersLines: f, small, sideways: document.documentElement.scrollWidth > innerWidth + 1 };
}"""

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
        page.wait_for_function("() => typeof guideListNumbers === 'function'")
        wait_settled(page)

        print("\n--- 1 and 2. Numbers follow A to Z, on the chips in Guides ---")
        for cat, (G, I, gattr, iattr) in PARTS.items():
            want = page.evaluate(WANT, [cat, page.evaluate(f"() => {G}"), page.evaluate(f"() => {I}.map(x => ({{ key: x.key, name: x.name, group: x.group }}))")])
            n_items = page.evaluate(f"() => {I}.length")
            check(f"{cat}: every group and every one of the {n_items} entries has a number, none twice (worked out from A to Z)",
                  len(want["items"]) == n_items and len({n for _, n in want["items"]}) == n_items and len(want["groups"]) == page.evaluate(f"() => {G}.length"), want["groups"])
            open_cat(page, cat)
            got = page.evaluate(CHIPS, f"#cmp-{cat}-groups .chip")
            check(f"{cat}: the group buttons are All (no number), then the groups A to Z with their numbers",
                  got == [["all", ""]] + [list(x) for x in want["groups"]], got)
            first = want["groups"][0][0]
            check(f"{cat}: the section opens on its first group A to Z", page.get_attribute(f'#cmp-{cat}-groups [data-{gattr}="{first}"]', "aria-pressed") == "true")
            # every group in turn, then All: the chips show exactly that group's entries, in number order, each with its number
            bad = []
            for gkey, gnum in want["groups"]:
                if page.get_attribute(f'#cmp-{cat}-groups [data-{gattr}="{gkey}"]', "aria-pressed") != "true":
                    page.click(f'#cmp-{cat}-groups [data-{gattr}="{gkey}"]')
                shown = page.evaluate(CHIPS, f"#cmp-{cat}-chips .chip")
                exp = [list(x) for x in want["items"] if x[1].startswith(gnum + ".")]
                if shown != exp: bad.append((gkey, shown[:3], exp[:3]))
            check(f"{cat}: each group shows its own entries A to Z with numbers counting up from {want['groups'][0][1]}.1", not bad, bad[:2])
            page.click(f'#cmp-{cat}-groups [data-{gattr}="all"]')
            shown = page.evaluate(CHIPS, f"#cmp-{cat}-chips .chip")
            check(f"{cat}: All shows every entry in number order (group by group, A to Z inside each)", shown == [list(x) for x in want["items"]], shown[:3])
            key, num = want["items"][4]
            page.click(f'#cmp-{cat}-chips [data-{iattr}="{key}"]')
            page.wait_for_selector(f"#cmp-{cat}-summary")
            check(f"{cat}: keys are unchanged: a numbered chip ({num}) still opens its own entry", page.evaluate(f"() => compendiumState.{cat}") == key
                  and page.get_attribute(f'#cmp-{cat}-chips [data-{iattr}="{key}"]', "aria-pressed") == "true", key)
        r = page.evaluate("""() => { const parts = libraryParts(compendiumDoor(), () => {}), out = {};
            for (const k of ['detail', 'basing']) { const box = parts[k](); out[k] = [box.querySelectorAll('.guides-num').length, box.querySelectorAll('.g3-filters').length]; }
            return out; }""")
        check("outside Guides (the same parts in another door) there are no numbers and no Filters button", r == {"detail": [0, 0], "basing": [0, 0]}, r)
        check("nothing is stored on the data: no number field on any recipe or tip",
              page.evaluate("() => [...DETAIL_RECIPES, ...BASING_TIPS, ...DETAIL_GROUPS, ...BASING_GROUPS].every(x => !('num' in x) && !('number' in x))"))

        print("\n--- 3. The Filters button ---")
        open_cat(page, "detail")
        btn, row = "#cmp-detail-groups-toggle", "#cmp-detail-groups"
        info = page.evaluate("""([b, r]) => { const x = document.querySelector(b), y = document.querySelector(r);
            return { text: x.textContent, exp: x.getAttribute('aria-expanded'), ctl: x.getAttribute('aria-controls'), above: x.getBoundingClientRect().bottom <= y.getBoundingClientRect().top + 0.5,
                     next: x.nextElementSibling === y, search: document.getElementById('cmp-detail-search-box').getBoundingClientRect().bottom <= x.getBoundingClientRect().top + 0.5 }; }""", [btn, row])
        check("Detail recipes: a Filters button sits right above the group buttons (under the search box), shown at first",
              info == {"text": "Filters", "exp": "true", "ctl": "cmp-detail-groups", "above": True, "next": True, "search": True} and page.is_visible(row), info)
        check("its arrow points down while the group buttons show", arrow(page, btn) == 45, arrow(page, btn))
        page.click(f'{row} [data-detail-group="metal"]')
        metal = page.evaluate("() => DETAIL_RECIPES.filter(r => r.group === 'metal').map(r => r.key).sort()")
        page.click(btn)
        wait_settled(page)
        check("tapping Filters folds the group buttons away; the arrow points right and the button says it is folded",
              not page.is_visible(row) and page.locator(f"{row} .chip").count() == 5 and page.get_attribute(btn, "aria-expanded") == "false" and arrow(page, btn) == -45,
              (page.is_visible(row), arrow(page, btn)))
        shown = sorted(page.evaluate("() => [...document.querySelectorAll('#cmp-detail-chips .chip')].map(c => c.dataset.detail)"))
        check("while folded, the chosen group (Metal) still filters the list", shown == metal, shown[:3])
        page.click(f'#cmp-detail-chips [data-detail="{metal[0]}"]')
        page.wait_for_selector("#cmp-detail-summary")
        check("picking a recipe while folded keeps the row folded (the page redraws) and the group still filters",
              not page.is_visible(row) and page.get_attribute(btn, "aria-expanded") == "false"
              and sorted(page.evaluate("() => [...document.querySelectorAll('#cmp-detail-chips .chip')].map(c => c.dataset.detail)")) == metal)
        tap_tab(page, "dashboard")
        wait_settled(page)
        tap_tab(page, "guides")
        page.click('#more-seg button[data-page="guides"]')
        wait_settled(page)
        open_cat(page, "detail")
        check("the folded state is kept while the app is open (leave Guides and come back)", page.get_attribute(btn, "aria-expanded") == "false" and not page.is_visible(row))
        page.click(btn)
        wait_settled(page)
        check("tapping Filters again shows the row, Metal still on, arrow down again",
              page.is_visible(row) and page.get_attribute(f'{row} [data-detail-group="metal"]', "aria-pressed") == "true" and arrow(page, btn) == 45)
        page.click(f'{row} [data-detail-group="light"]')
        light = page.evaluate("() => DETAIL_RECIPES.filter(r => r.group === 'light').map(r => r.key).sort()")
        check("after folding and showing again, another group filters correctly (Light)",
              sorted(page.evaluate("() => [...document.querySelectorAll('#cmp-detail-chips .chip')].map(c => c.dataset.detail)")) == light)
        open_cat(page, "basing")
        bb, br = "#cmp-basing-groups-toggle", "#cmp-basing-groups"
        page.click(f'{br} [data-basing-group="plants"]')
        page.click(bb)
        plants = page.evaluate("() => BASING_TIPS.filter(t => t.group === 'plants').map(t => t.key).sort()")
        check("Basing: its own Filters button folds its group buttons, and Plants still filters while folded",
              page.get_attribute(bb, "aria-expanded") == "false" and not page.is_visible(br)
              and sorted(page.evaluate("() => [...document.querySelectorAll('#cmp-basing-chips .chip')].map(c => c.dataset.basing)")) == plants)
        page.click(bb)
        check("Basing: Filters shows them again, Plants still on", page.is_visible(br) and page.get_attribute(f'{br} [data-basing-group="plants"]', "aria-pressed") == "true")
        page.click(bb)   # leave Basing folded for the reload
        stored = page.evaluate("() => Object.keys(localStorage).map(k => localStorage.getItem(k) || '').some(v => v.includes('filtersShut'))")
        page.reload()
        app_ready(page)
        leave_launch(page)
        tap_tab(page, "guides")
        page.click('#more-seg button[data-page="guides"]')
        wait_settled(page)
        open_cat(page, "basing")
        check("the open or folded state is not saved: after the app is opened again the group buttons show",
              not stored and page.get_attribute(bb, "aria-expanded") == "true" and page.is_visible(br))

        print("\n--- 4. Phones, light and dark ---")
        for w, h, scheme in [(390, 844, "dark"), (360, 640, "light"), (320, 640, "dark"), (320, 640, "light")]:
            page.set_viewport_size({"width": w, "height": h})
            page.evaluate("(lt) => { settings.appearance = lt ? 'light' : 'dark'; applyPalette(settings.palette); render(); }", scheme == "light")
            seen = []
            for cat, (G, I, gattr, iattr) in PARTS.items():
                open_cat(page, cat)
                if page.get_attribute(f'#cmp-{cat}-groups [data-{gattr}="all"]', "aria-pressed") != "true":   # (tapping All when it is on puts it away)
                    page.click(f'#cmp-{cat}-groups [data-{gattr}="all"]')
                wait_settled(page)
                seen.append((cat, page.evaluate(LAYOUT)))
            badness = [x for x in seen if x[1]["bad"] or x[1]["small"] or x[1]["sideways"] or x[1]["filtersLines"] != [1] or x[1]["chips"] < 60]
            check(f"{w}x{h} {scheme}: no sideways scroll, taps 44 px, Filters on one line, every number on one line on its title's first line inside the chip",
                  page.evaluate("() => document.documentElement.dataset.m") == scheme and not badness, badness)

        check("no page errors or pop-ups", errors == [], errors)
        browser.close()
    print(f"\n{sum(results)}/{len(results)} checks passed")
    return 0 if all(results) else 1

if __name__ == "__main__":
    sys.exit(main())
