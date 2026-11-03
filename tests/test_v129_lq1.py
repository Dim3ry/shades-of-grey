"""LQ1 tests for Minifolio (the liquid feel, from the 3 Nov smoothness sweep). New behaviour only, and no speed timings:
1. A pressed look (a light change, never a move) appears the moment a finger touches, and goes when the touch becomes a scroll.
   The bar's segments and the Mentor button get none.
2. A fold-out's content below moves by transform (one smooth slide), not by a one-frame jump, and is left with no transform.
3. The Undo message and the question box are hidden at once, as before, and leave through a see-through copy that plays an animation
   and then goes (no ids, cannot be tapped, hidden from screen readers).
4. Back from a recipe keeps the list's scroll position.
5. The palette search's answer box changes height smoothly.
6. The in-section switches (Painting, Tools, Colour Lab) "slow empty and slow fill" (James, 3 Nov): the old option's fill drains while the
   new one's floods in, drawn with clip-path over the option, its label in the selected colours; the Tools pages themselves still
   switch instantly. Pages inside the Painting section fade in; a shopping row that leaves fades through a copy outside the list.
7. The Dashboard graph's dates read the same as before (LQ12 only made them faster).
8. Reduce motion: none of the above starts an animation.
Run all tests with `python3 tests/run_all.py`, or serve the repo folder and run this file on its own."""
import os, sys
from playwright.sync_api import sync_playwright

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import test_v31 as t

results = []

def check(name, ok, detail=""):
    results.append(bool(ok))
    print(("PASS " if ok else "FAIL ") + name + ("" if ok else f"  -> {detail}"))

UNITS = [{"id": i, "name": f"Squad {i}", "hobby": "Test game", "stage": i % 4, "count": 3, "added": "2026-09-01",
          "log": [["2026-09-01", 0], ["2026-10-01", i % 4]]} for i in range(1, 13)]
PAINTS = [{"id": i, "brand": "Brand", "name": f"Colour {chr(65 + i % 26)}{i}", "colour": "#%02x%02x%02x" % (40 + i * 3, 90, 200 - i * 3),
           "status": "wishlist" if i <= 6 else "owned"} for i in range(1, 41)]
RECIPES = [{"id": r, "name": f"Recipe {r:02d}", "part": "Armour", "notes": "",
            "steps": [{"technique": "Layer", "coats": 1, "paints": [{"paint": 1 + r % 40, "mix": None}], "ratio": "", "note": "", "optional": False}]}
           for r in range(1, 41)]
SETTINGS = {"tab": "units", "examplesChecked": True, "recipeExamplesChecked": True, "feedbackShown": True, "backupNudgeDone": True}

# the animations running on an element (and, with pseudo, on its ::after), as [property names in the keyframes]
ANIMS = """([sel, pseudo]) => { const el = typeof sel === 'string' ? document.querySelector(sel) : sel; if (!el) return null;
    return el.getAnimations({ subtree: !!pseudo }).filter(a => !pseudo || (a.effect.pseudoElement === '::after' && a.effect.target === el))
      .map(a => a.effect.getKeyframes().flatMap(k => Object.keys(k).filter(x => !['offset', 'easing', 'composite', 'computedOffset'].includes(x)))); }"""
OURS = """() => ({ anims: document.getAnimations().filter(a => a.playState === 'running' || a.playState === 'paused').length,
    ghosts: document.querySelectorAll('.lq-ghost').length, fills: document.querySelectorAll('.lq-fill').length })"""

def touch(page, sel, kind):
    page.evaluate("""([s, k]) => { const el = document.querySelector(s); const r = el.getBoundingClientRect();
        el.dispatchEvent(new PointerEvent(k, { bubbles: true, cancelable: true, pointerType: 'touch', isPrimary: true, clientX: r.left + 5, clientY: r.top + 5 })); }""", [sel, kind])

def to_painting(page, view):
    page.evaluate("v => { document.querySelector('nav .arc button[data-tab=recipes]').click(); }", view)
    page.wait_for_timeout(400)
    page.evaluate("v => document.querySelector(`#recipe-seg button[data-view=${v}]`).click()", view)
    page.wait_for_timeout(400)

def main():
    errors = []
    with sync_playwright() as p:
        browser = p.chromium.launch()
        ctx = browser.new_context(viewport={"width": 390, "height": 844}, service_workers="block", has_touch=True, is_mobile=True)
        page = ctx.new_page()
        page.on("pageerror", lambda x: errors.append(str(x)))
        t.load(page, paints=PAINTS, recipes=RECIPES, units=UNITS, settings=SETTINGS)
        page.wait_for_timeout(300)

        print("\n--- 1. Pressed look from the touch ---")
        sel = "#unit-list > li.unit:nth-child(2) .up-button"
        touch(page, sel, "pointerdown")
        st = page.evaluate("s => { const el = document.querySelector(s); const c = getComputedStyle(el); return [el.classList.contains('lq-press'), c.filter, c.transform, c.scale, c.translate]; }", sel)
        check("a stage arrow shows its pressed look as soon as the finger touches", st[0] and "brightness" in st[1], st)
        check("the pressed look is a light change only (no move or shrink)", st[2] == "none" and st[3] == "none" and st[4] == "none", st)
        touch(page, sel, "pointercancel")
        check("a touch that becomes a scroll takes the pressed look off at once", page.evaluate("s => !document.querySelector(s).classList.contains('lq-press')", sel))
        for s, name in (("nav .arc button[data-tab=dashboard]", "a bar segment"), ("#mentor-button", "the Mentor button")):
            touch(page, s, "pointerdown")
            check(f"{name} gets no pressed look (MO6 and MW1 own it)", not page.evaluate("s => document.querySelector(s).classList.contains('lq-press')", s))
            touch(page, s, "pointerup")

        print("\n--- 2. A fold-out: what is below slides ---")
        page.evaluate("scrollTo(0, 0)")
        page.click("#toggle-filters")
        # the list below moves as one piece, or (a long list) its cards near the screen move
        list_anims = page.evaluate(ANIMS, ["#unit-split", True]) or page.evaluate("""() => document.getElementById('unit-split').getAnimations({ subtree: true })
            .map(a => a.effect.getKeyframes().flatMap(k => Object.keys(k).filter(x => x === 'transform')))""")
        first = page.evaluate("""() => { const a = document.getElementById('unit-split').getAnimations({ subtree: true }).find(x => x.effect.getKeyframes()[0].transform);
            const h = document.getElementById('filter-card').getBoundingClientRect().height;
            return a ? [a.effect.getKeyframes()[0].transform, Math.round(h)] : null; }""")
        panel_anims = page.evaluate(ANIMS, ["#filter-card", False]) or []
        check("the list below the opened Filters slides by transform", first is not None, list_anims)
        check("the list starts from where it was (moved back by the panel's height, so no one-frame jump)",
              first and first[0].startswith("translateY(-") and abs(abs(float(first[0][11:-3])) - first[1]) < 30, first)
        check("the Filters panel unrolls with clip-path", any("clipPath" in a for a in panel_anims), panel_anims)
        page.wait_for_timeout(450)
        rest = page.evaluate("""() => [[document.getElementById('unit-split'), ...document.querySelectorAll('#unit-list > li')].filter(e => getComputedStyle(e).transform !== 'none').length,
            document.getElementById('unit-split').getAnimations({ subtree: true }).filter(a => a.effect.getKeyframes().some(k => k.transform)).length]""")
        check("once it ends, nothing is left with a transform", rest == [0, 0], rest)
        page.click("#toggle-filters")
        check("closing slides the list back up too", page.evaluate("() => document.getElementById('unit-split').getAnimations({ subtree: true }).some(a => a.effect.getKeyframes().some(k => k.transform))"))
        page.wait_for_timeout(450)

        print("\n--- 3. The Undo message and the question box leave smoothly ---")
        page.evaluate("showToast('Deleted a thing', () => {})")
        page.wait_for_timeout(400)
        page.click("#toast-undo")
        g = page.evaluate("""() => { const t = document.getElementById('toast'); const gh = document.querySelector('.toast.lq-ghost');
            return { hidden: t.classList.contains('hidden'), ghost: !!gh, ids: gh ? gh.querySelectorAll('[id]').length + (gh.id ? 1 : 0) : -1,
                     aria: gh && gh.getAttribute('aria-hidden'), inert: gh && gh.inert, anims: gh ? gh.getAnimations().length : 0,
                     found: document.querySelector('#toast') === t }; }""")
        check("Undo hides the message at once, as before", g["hidden"] and g["found"], g)
        check("a see-through copy of it plays the way out", g["ghost"] and g["anims"] > 0, g)
        check("the copy has no ids, cannot be tapped and is hidden from screen readers", g["ids"] == 0 and g["aria"] == "true" and g["inert"], g)
        page.wait_for_timeout(550)
        check("the copy is gone when it has played", page.evaluate("() => !document.querySelector('.toast.lq-ghost')"))
        page.evaluate("askYesNo('Delete this?', () => {})")
        page.wait_for_timeout(400)
        page.click("#dialog-no")
        d = page.evaluate("""() => { const gh = document.querySelector('.dialog-backdrop.lq-ghost');
            return { hidden: document.getElementById('dialog-backdrop').classList.contains('hidden'), ghost: !!gh,
                     ids: gh ? gh.querySelectorAll('[id]').length + (gh.id ? 1 : 0) : -1, anims: gh ? gh.getAnimations({ subtree: true }).length : 0,
                     focus: document.activeElement && document.activeElement.closest('.lq-ghost') === null }; }""")
        check("the question box is hidden at once and fades out through a copy", d["hidden"] and d["ghost"] and d["anims"] > 0 and d["ids"] == 0, d)
        check("focus goes back to the page, never into the copy", d["focus"], d)
        page.wait_for_timeout(400)
        check("the question box's copy is gone afterwards", page.evaluate("() => !document.querySelector('.dialog-backdrop.lq-ghost')"))

        print("\n--- 4. Back from a recipe keeps your place ---")
        to_painting(page, "recipes")
        page.evaluate("scrollTo(0, 1200)")
        page.wait_for_timeout(200)
        y0 = page.evaluate("scrollY")
        page.evaluate("""() => { const r = [...document.querySelectorAll('#recipe-list .recipe-item')].find(i => i.getBoundingClientRect().top > 150); r.click(); }""")
        page.wait_for_timeout(400)
        page.evaluate("""() => { const b = [...document.querySelectorAll('#recipe-page button')].find(b => /recipes/i.test(b.textContent)); b.click(); }""")
        page.wait_for_timeout(400)
        y1 = page.evaluate("scrollY")
        check("Back returns the list to where it was scrolled", y0 > 600 and abs(y1 - y0) <= 2, [y0, y1])

        print("\n--- 5. Switch fill and pages inside a section ---")
        page.evaluate("scrollTo(0, 0)")
        page.click("#recipe-seg button[data-view=schemes]")
        f = page.evaluate("""([a]) => { const seg = document.getElementById('recipe-seg'); const o = seg.querySelector('[data-view=recipes]'), n = seg.querySelector('[data-view=schemes]');
            const kf = (el) => el.getAnimations({ subtree: true }).filter(x => x.effect.pseudoElement === '::after' && x.effect.target === el).map(x => x.effect.getKeyframes().map(k => k.clipPath));
            const pa = getComputedStyle(n, '::after');
            return { cls: o.classList.contains('lq-fill') && n.classList.contains('lq-fill'), old: kf(o), now: kf(n), label: n.dataset.lqLabel, text: n.textContent.trim(),
                     content: pa.content, afterColour: pa.color, afterBg: pa.backgroundColor, baseBg: getComputedStyle(n).backgroundColor,
                     view: (document.getElementById('scheme-view').getAnimations()[0] || {effect: {getKeyframes: () => []}}).effect.getKeyframes().map(k => k.opacity) }; }""", [0])
        check("picking Schemes: the old option drains and the new one floods (clip-path on their fill)",
              f["cls"] and f["old"] and f["now"] and f["old"][0][0] == "inset(0px)" and f["now"][0][-1] == "inset(0px)", f)
        check("the colour moves across: Schemes fills from the side nearest Recipes, Recipes empties towards it",
              f["now"] and "100%" in f["now"][0][0].split()[1] and f["old"] and f["old"][0][-1].endswith("100%)"), f)
        check("the fill carries the option's own label, hidden from screen readers", f["label"] == f["text"] and f["content"].endswith('/ ""') if f["content"] else False, f)
        page.wait_for_timeout(550)
        r = page.evaluate("""() => { const n = document.querySelector('#recipe-seg [data-view=schemes]'); const c = getComputedStyle(n);
            return { cls: document.querySelectorAll('.lq-fill').length, bg: c.backgroundColor, colour: c.color, label: 'lqLabel' in n.dataset }; }""")
        check("the fill's colours are the selected option's own (so contrast never drops)",
              f["afterBg"] == r["bg"] and f["afterColour"] == r["colour"] and f["baseBg"] in ("rgba(0, 0, 0, 0)", "transparent"), [f, r])
        check("when it ends the switch is back to its plain look", r["cls"] == 0 and not r["label"], r)
        check("the Schemes page fades in", [float(x) for x in f["view"]] == [0, 1], f["view"])
        page.click("#recipe-seg button[data-view=colourlab]")
        page.wait_for_timeout(550)
        page.evaluate("() => document.querySelectorAll('#lab-seg button')[1].click()")
        lab = page.evaluate(ANIMS, ["#colourlab-body", False]) or []
        check("a Colour Lab part fades in", any("opacity" in a for a in lab), lab)
        check("the Colour Lab parts switch fills too", page.evaluate("() => document.querySelectorAll('#lab-seg .lq-fill').length") == 2)
        page.wait_for_timeout(550)

        print("\n--- 6. Tools: the switch fills, the pages stay instant ---")
        page.evaluate("() => { document.querySelector('nav .arc button[data-tab=guides]').click(); }")
        page.wait_for_timeout(450)
        page.click("#more-seg button[data-page=settings]")
        page.wait_for_timeout(550)
        page.click("#more-seg button[data-page=help]")
        tl = page.evaluate("""() => ({ fills: document.querySelectorAll('#more-seg .lq-fill').length,
            page: document.getElementById('view-help').getAnimations().length, shown: !document.getElementById('view-help').classList.contains('hidden') })""")
        check("the Tools switch drains and fills", tl["fills"] == 2, tl)
        check("the Help page itself appears at once, with no fade (Mo3a's instant switch kept)", tl["shown"] and tl["page"] == 0, tl)
        page.wait_for_timeout(550)

        print("\n--- 7. The palette search box and the shopping list ---")
        to_painting(page, "palette")
        page.fill("#palette-search", "Colour")
        page.wait_for_timeout(400)
        page.fill("#palette-search", "Colour B1")
        hs = page.evaluate(ANIMS, ["#palette-search-result", False]) or []
        check("the palette search's answer box changes height smoothly", any("height" in a for a in hs), hs)
        page.fill("#palette-search", "")
        page.wait_for_timeout(400)
        page.evaluate("() => document.querySelector('#recipe-seg button[data-view=shopping]').click()")
        page.wait_for_timeout(550)
        n0 = page.evaluate("() => document.querySelectorAll('#shop-panel .shop-item').length")
        page.evaluate("() => document.querySelector('#shop-panel .shop-remove').click()")
        sh = page.evaluate("""() => ({ rows: document.querySelectorAll('#shop-panel .shop-item').length, ghost: document.querySelectorAll('body > .lq-ghost .shop-item').length,
            glide: [...document.querySelectorAll('#shop-panel .shop-item')].some(el => el.getAnimations().length) })""")
        check("a removed shopping row fades through a copy outside the list, and the rows below glide", sh["ghost"] == 1 and sh["glide"] and sh["rows"] == n0 - 1, [n0, sh])
        page.wait_for_timeout(550)
        check("the leaving copy is gone afterwards", page.evaluate("() => !document.querySelector('.lq-ghost')"))

        print("\n--- 8. The Dashboard graph's dates ---")
        same = page.evaluate("""() => [19000, 19723, 20333, 20400].every(d => dayLabel(d, true) === new Date(d * 86400000).toLocaleDateString('en-GB', { month: 'short', year: 'numeric', timeZone: 'UTC' })
            && dayLabel(d, false) === new Date(d * 86400000).toLocaleDateString('en-GB', { day: 'numeric', month: 'short', timeZone: 'UTC' }))""")
        check("the graph's date labels read exactly as before", same)

        print("\n--- 9. Reduce motion ---")
        page.emulate_media(reduced_motion="reduce")
        page.wait_for_timeout(200)
        steps = [("the Painting switch", lambda: page.click("#recipe-seg button[data-view=schemes]")),
                 ("a shopping row leaving", lambda: (page.click("#recipe-seg button[data-view=shopping]"), page.wait_for_timeout(200),
                                                     page.evaluate("document.querySelector('#shop-panel .shop-remove').click()"))),
                 ("open Filters", lambda: (page.evaluate("showTab('units')"), page.wait_for_timeout(200), page.click("#toggle-filters"))),
                 ("the Undo message leaving", lambda: (page.evaluate("showToast('x', () => {})"), page.click("#toast-undo"))),
                 ("the question box leaving", lambda: (page.evaluate("askYesNo('Delete this?', () => {})"), page.click("#dialog-no")))]
        moving = []
        for name, act in steps:
            act()
            o = page.evaluate(OURS)
            if o["anims"] or o["ghosts"] or o["fills"]:
                moving.append([name, o])
        check("with Reduce motion on, none of them starts an animation", not moving, moving)
        ctx.close()
        browser.close()
    check("no page errors", not errors, errors[:3])
    print(f"\n{sum(results)}/{len(results)} passed")
    sys.exit(0 if all(results) else 1)

main()
