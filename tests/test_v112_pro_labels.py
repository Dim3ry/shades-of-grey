"""P1 tests for Minifolio (Pro preview labels). New behaviour only:
1. The tag is plain text (no fill, border or icon) in the accent colour, small spaced capitals.
2. Free parts carry no tag: the Colour Lab page and Wheel, Colours you've used, recipes, schemes, Your Palette, shopping, the Palette tile.
3. Guides: a tag on every row of the sections list and one "Free while in preview." line under it (not shown while searching).
4. Single tools: Colour ideas (recipe editor card and Colour Lab), Colour plans, Paint Picker carry one tag; Achievements is an empty
   placeholder and Palette insights does not exist, so neither gets one.
5. 390, 360 and 320 px, dark and light: the tag stays on its row at the right end, does not wrap, and no sideways scroll.
Run all tests with `python3 tests/run_all.py`, or serve the repo folder and run this file on its own."""
import os, sys
from playwright.sync_api import sync_playwright

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import test_v24 as t

results = []
THEMES = ["classic", "blueprint", "parchment", "forge", "bench", "rulebook"]

def check(name, ok, detail=""):
    results.append(bool(ok))
    print(("PASS " if ok else "FAIL ") + name + ("" if ok else f"  -> {detail}"))

def tags(page, scope):
    return page.evaluate("(s) => [...document.querySelectorAll(s + ' .pro-pill')].map(x => x.textContent)", scope)

def lab_open(page, key):
    page.click(f'#lab-seg [data-lab="{key}"]')
    page.wait_for_selector(f"#cmp-lab-{key}")

def main():
    errors = []
    with sync_playwright() as p:
        browser = p.chromium.launch()
        ctx = browser.new_context(viewport={"width": 390, "height": 844}, service_workers="block")
        page = ctx.new_page()
        page.on("pageerror", lambda x: errors.append(str(x)))

        print("\n--- 1 and 2. Free parts carry no tag ---")
        t.fresh(page)
        check("Dashboard (Palette tile, Achievements) has no tag", tags(page, "#view-dashboard") == [])
        t.main_tab(page, "recipes")
        for view in ("recipes", "schemes", "palette", "shopping"):
            if page.locator(f'#recipe-seg button[data-view="{view}"]').count():
                t.recipe_view(page, view)
                check(f"Painting > {view} has no tag", page.locator(".pro-pill:visible").count() == 0)
        t.recipe_view(page, "colourlab")
        check("Colour Lab: the page as a whole has no tag of its own", page.locator("#colourlab-view > .card > .lab-pro, #colourlab-view .card > .pro-row").count() == 0)
        check("Wheel is open first and carries no tag", page.locator("#cmp-lab-wheel").count() == 1 and tags(page, "#colourlab-view") == [])
        lab_open(page, "history")
        check("Colours you've used carries no tag", tags(page, "#colourlab-view") == [])

        print("\n--- 4. Single tools ---")
        for key in ("ideas", "plans", "picker"):
            lab_open(page, key)
            got = tags(page, "#colourlab-view")
            first = page.evaluate("() => document.querySelector('#colourlab-body .lab-section').firstElementChild.className")
            check(f"Colour Lab > {key}: exactly one 'Pro preview' tag, on the top row, at the right", got == ["Pro preview"] and first == "pro-row", (got, first))
        page.evaluate("() => startRecipeDraft(draftFrom(book.recipes[0]))")
        t.quiet(page)
        check("Colour ideas card in the recipe editor has one tag in its heading row", tags(page, "#colour-ideas > summary") == ["Pro preview"], tags(page, "#colour-ideas"))
        info = page.evaluate("""() => { const s = document.querySelector('#colour-ideas > summary'), g = s.querySelector('.pro-pill').getBoundingClientRect(), h = s.querySelector('h2').getBoundingClientRect();
            return { right: g.right <= s.getBoundingClientRect().right && g.left >= h.right, oneLine: Math.abs(g.top - h.top) < 20 } }""")
        check("Colour ideas tag sits to the right of the title on the same line", info["right"] and info["oneLine"], info)
        check("Achievements is an empty placeholder (no tag) and Palette insights does not exist",
              page.evaluate("() => !document.querySelector('#achievements-card .pro-pill') && !/Palette insights/i.test(document.body.textContent)"))

        print("\n--- 3. Guides ---")
        t.main_tab(page, "compendium")
        rows = page.locator(".guides-cats .guides-row")
        n = rows.count()
        check("every row of the sections list has the tag, as its last item", n >= 4 and page.evaluate(
            "() => [...document.querySelectorAll('.guides-cats .guides-row')].every(r => r.lastElementChild.classList.contains('pro-pill') && r.lastElementChild.textContent === 'Pro preview')"))
        check("no other tag on the Guides page", tags(page, "#view-guides") == ["Pro preview"] * n, tags(page, "#view-guides"))
        free = page.locator(".guides-free")
        check("one line of plain text under the list: 'Free while in preview.'", free.count() == 1 and free.inner_text() == "Free while in preview."
              and page.evaluate("() => document.querySelector('.guides-free').previousElementSibling.classList.contains('guides-cats')"))
        page.fill("#guides-search", "colour")
        check("while searching the line and the tags are not shown", page.locator(".guides-free").count() == 0 and page.locator(".guides-cats").count() == 0)
        page.fill("#guides-search", "")
        check("clearing the search brings the list and the line back", page.locator(".guides-free").count() == 1)

        print("\n--- 1. Look ---")
        look = page.evaluate("""() => { const e = document.querySelector('.guides-cats .pro-pill'), c = getComputedStyle(e), r = getComputedStyle(document.documentElement);
            return { fs: c.fontSize, tt: c.textTransform, ls: parseFloat(c.letterSpacing) > 0, bg: c.backgroundColor, bd: c.borderTopWidth, img: c.backgroundImage,
                     col: c.color, accent: getComputedStyle(document.body).getPropertyValue('--accent').trim(), kids: e.children.length } }""")
        check("plain text: no fill, no border, no icon; small spaced capitals", look["bg"] in ("rgba(0, 0, 0, 0)", "transparent") and look["bd"] == "0px"
              and look["img"] == "none" and look["kids"] == 0 and look["tt"] == "uppercase" and look["ls"] and look["fs"] == "11px", look)

        print("\n--- 5. Layout and colours ---")
        def layout(pg):
            return pg.evaluate("""() => [...document.querySelectorAll('.guides-cats .guides-row')].map(r => { const g = r.querySelector('.pro-pill').getBoundingClientRect(),
                ti = r.querySelector('.guides-row-title').getBoundingClientRect(), rr = r.getBoundingClientRect();
                return { inside: g.right <= rr.right && g.left >= rr.left, clear: g.left >= ti.right - 1, oneLine: g.height < 20, title: ti.width > 40, h: rr.height } })""")
        for width in (390, 360, 320):
            for scheme in ("dark", "light"):
                c2 = browser.new_context(viewport={"width": width, "height": 700}, color_scheme=scheme, service_workers="block")
                pg = c2.new_page(); pg.on("pageerror", lambda x: errors.append(str(x)))
                t.fresh(pg)
                t.main_tab(pg, "compendium")
                L = layout(pg)
                check(f"{width} px {scheme}: Guides tags stay on their rows, never wrap or push the title off, rows 44 px or more, no sideways scroll",
                      L and all(x["inside"] and x["clear"] and x["oneLine"] and x["title"] and x["h"] >= 44 for x in L) and t.no_sideways(pg), L)
                t.main_tab(pg, "recipes"); t.recipe_view(pg, "colourlab"); lab_open(pg, "ideas")
                m = pg.evaluate("() => { const g = document.querySelector('#colourlab-view .pro-pill').getBoundingClientRect(); return { right: g.right <= innerWidth, oneLine: g.height < 20 } }")
                check(f"{width} px {scheme}: Colour Lab tag inside the screen on one line", m["right"] and m["oneLine"] and t.no_sideways(pg), m)
                c2.close()
        # contrast of the tag text on its row in every theme, light and dark (11 px text needs 4.5)
        c3 = browser.new_context(viewport={"width": 390, "height": 700}, service_workers="block")
        pg = c3.new_page(); pg.on("pageerror", lambda x: errors.append(str(x)))
        t.fresh(pg); t.main_tab(pg, "compendium")
        bad = {}
        for theme in THEMES:
            for light in (False, True):
                pg.evaluate("([th, lt]) => { const r = document.documentElement; r.dataset.t = th; if (lt) r.dataset.appearance = 'light'; else delete r.dataset.appearance; }", [theme, light])
                v = pg.evaluate("""() => { const e = document.querySelector('.guides-cats .guides-row .pro-pill'); let b = e.parentElement, bg = 'rgba(0, 0, 0, 0)';
                    while (b && /rgba\\(0, 0, 0, 0\\)|transparent/.test(bg = getComputedStyle(b).backgroundColor)) b = b.parentElement;
                    return [getComputedStyle(e).color, bg]; }""")
                cr = t.contrast(t.rgb(v[0]), t.rgb(v[1]))
                if cr < 4.5: bad[f"{theme}-{'light' if light else 'dark'}"] = round(cr, 2)
        check("the tag text is readable (4.5:1) in every theme, light and dark", not bad, bad)
        c3.close()
        check("no page errors", not errors, errors)
        browser.close()

    passed = sum(results)
    print(f"\n{passed}/{len(results)} checks passed")
    sys.exit(0 if passed == len(results) else 1)

if __name__ == "__main__":
    main()
