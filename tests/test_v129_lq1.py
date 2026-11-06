"""LQ1 tests for Minifolio (the liquid feel, from the 3 Nov smoothness sweep). New behaviour only, and no speed timings:
1. A pressed look (a light change, never a move) appears the moment a finger touches, and goes when the touch becomes a scroll.
   The bar's segments and the Mentor button get none.
2. A fold-out's content below moves by transform (one smooth slide), not by a one-frame jump, and is left with no transform.
3. The Undo message and the question box are hidden at once, as before, and leave through a see-through copy that plays an animation
   and then goes (no ids, cannot be tapped, hidden from screen readers).
4. Back from a recipe keeps the list's scroll position.
5. The palette search's answer box changes height smoothly.
6. (AB7b: Painting, Colour Lab and Tools are now tab rows with a sliding line and no fill; these checks run on Guides' Topics / A to Z.) The in-section switches "slow empty and slow fill" (James, 3 Nov): the old option's fill drains while the
   new one's floods in, drawn with clip-path over the option, its label in the selected colours; the Tools pages themselves still
   switch instantly. Pages inside the Painting section fade in; a shopping row that leaves fades through a copy outside the list.
7. The Dashboard graph's dates read the same as before (LQ12 only made them faster).
8. Reduce motion: none of the above starts an animation.
Run all tests with `python3 tests/run_all.py`, or serve the repo folder and run this file on its own."""
import os, sys
from playwright.sync_api import sync_playwright

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import test_v31 as t
from common import open_unit_card

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

# Button sweep (James, 3 Nov). Every kind of button on the screen: (a) no browser tap square; (b) its colour changes on a clock, not in one frame
# (transitions present); (c) anything drawn in a ::before or ::after with a fill stays inside the rounded shape.
KINDS = [".primary-button", ".plain-button", ".danger-button", ".link-button", ".chip", ".seg > button", ".step-back", ".up-button", ".group-button",
         ".faction-button", ".recipe-item", ".recipe-chip", ".guides-row", ".swatch-tile", ".theme-swatch", ".more-info-button", ".card-fold-button"]
SWEEP = """(kinds) => { const seen = {}, still = [], square = [], noTrans = [];
    const tap = document.querySelectorAll('a, button, summary, label, [role=button], [role=tab], .chip');
    for (const el of tap) if (el.getClientRects().length && getComputedStyle(el).webkitTapHighlightColor !== 'rgba(0, 0, 0, 0)') square.push(el.className || el.tagName);
    for (const k of kinds) { const el = [...document.querySelectorAll(k)].find(e => e.getClientRects().length && !e.closest('.lq-ghost')); if (!el) continue; seen[k] = 1;
      const cs = getComputedStyle(el), props = cs.transitionProperty.split(', '), durs = cs.transitionDuration.split(', ').map(parseFloat);
      const colourOn = props.some((p, i) => /^(background-color|border-color|color|outline-color|background-size|all)$/.test(p) && (durs[i] ?? durs[durs.length - 1]) > 0);
      if (!colourOn && k !== '.seg > button') noTrans.push(k);   // (a switch's fill and label change by clip-path, checked in part 5)
      for (const ps of ['::before', '::after']) { const pc = getComputedStyle(el, ps); if (pc.content === 'none' || pc.content === 'normal') continue;
        const filled = pc.backgroundColor !== 'rgba(0, 0, 0, 0)' || pc.backgroundImage !== 'none';
        const clipped = /hidden|clip/.test(cs.overflow) || pc.borderTopLeftRadius === cs.borderTopLeftRadius || pc.position === 'static';
        if (filled && !clipped) still.push(k + ps); } }
    return { seen: Object.keys(seen), square: square.slice(0, 5), noTrans, unclipped: still }; }"""
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
        open_unit_card(page, "#unit-list > li.unit:nth-child(2)")   # MC1 (v130): cards start closed; the stage arrows are in the open card
        page.wait_for_timeout(400)
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
        # AB7b: the Painting, Colour Lab and Tools section tabs are now a row of words with one sliding line (tests/test_v139_ab7b.py), so they no
        # longer drain and fill. The fill is still LQ1's look for the boxed two-way switches, so those checks now run on Guides' Topics / A to Z.
        page.click("#recipe-seg button[data-view=schemes]")
        f = page.evaluate("""() => { const o = document.querySelector('#recipe-seg [data-view=recipes]'), n = document.querySelector('#recipe-seg [data-view=schemes]');
            return { fills: document.querySelectorAll('#recipe-seg .lq-fill').length,
                     view: (document.getElementById('scheme-view').getAnimations()[0] || {effect: {getKeyframes: () => []}}).effect.getKeyframes().map(k => k.opacity) }; }""")
        check("picking Schemes: the section tab row no longer drains and fills (AB7b: its line slides instead)", f["fills"] == 0, f)
        check("the Schemes page fades in", [float(x) for x in f["view"]] == [0, 1], f["view"])
        page.wait_for_timeout(550)
        page.click("#recipe-seg button[data-view=colourlab]")
        page.wait_for_timeout(550)
        page.evaluate("() => document.querySelectorAll('#lab-seg button')[1].click()")
        lab = page.evaluate(ANIMS, ["#colourlab-body", False]) or []
        check("a Colour Lab part fades in", any("opacity" in a for a in lab), lab)
        check("the Colour Lab tab row no longer fills (AB7b)", page.evaluate("() => document.querySelectorAll('#lab-seg .lq-fill').length") == 0)
        page.wait_for_timeout(550)

        print("\n--- 6. Tools: the pages stay instant; Guides' boxed switch still fills ---")
        page.evaluate("() => { document.querySelector('nav .arc button[data-tab=guides]').click(); }")
        page.wait_for_timeout(450)
        page.click("#more-seg button[data-page=settings]")
        page.wait_for_timeout(550)
        page.click("#more-seg button[data-page=help]")
        tl = page.evaluate("""() => ({ fills: document.querySelectorAll('#more-seg .lq-fill').length,
            page: document.getElementById('view-help').getAnimations().length, shown: !document.getElementById('view-help').classList.contains('hidden') })""")
        check("the Tools tab row no longer fills (AB7b)", tl["fills"] == 0, tl)
        check("the Help page itself appears at once, with no fade (Mo3a's instant switch kept)", tl["shown"] and tl["page"] == 0, tl)
        page.wait_for_timeout(550)
        page.click("#more-seg button[data-page=guides]")
        page.wait_for_timeout(550)
        page.click(".guides-order [data-order=az]")
        f = page.evaluate("""() => { const seg = document.querySelector('.guides-order'); const o = seg.querySelector('[data-order=topics]'), n = seg.querySelector('[data-order=az]');
            const kf = (el) => el.getAnimations({ subtree: true }).filter(x => x.effect.pseudoElement === '::after' && x.effect.target === el).map(x => x.effect.getKeyframes().map(k => k.clipPath));
            const pa = getComputedStyle(n, '::after');
            return { cls: o.classList.contains('lq-fill') && n.classList.contains('lq-fill'), old: kf(o), now: kf(n), label: n.dataset.lqLabel, text: n.textContent.trim(),
                     content: pa.content, afterColour: pa.color, afterBg: pa.backgroundColor, baseBg: getComputedStyle(n).backgroundColor }; }""")
        full = lambda s: s.startswith("inset(0px") and "100%" not in s and " round " in s
        check("picking A to Z: the old option drains and the new one floods (clip-path on their fill, its edge rounded like the option)",
              f["cls"] and f["old"] and f["now"] and full(f["old"][0][0]) and full(f["now"][0][-1]), f)
        check("the colour moves across: A to Z fills from the side nearest Topics, Topics empties towards it",
              f["now"] and f["now"][0][0].split()[1] == "100%" and f["old"] and f["old"][0][-1].split()[3] == "100%", f)
        check("the fill carries the option's own label, hidden from screen readers", f["label"] == f["text"] and f["content"].endswith('/ ""') if f["content"] else False, f)
        page.wait_for_timeout(550)
        r = page.evaluate("""() => { const n = document.querySelector('.guides-order [data-order=az]'); const c = getComputedStyle(n);
            return { cls: document.querySelectorAll('.lq-fill').length, bg: c.backgroundColor, colour: c.color, label: 'lqLabel' in n.dataset }; }""")
        check("the fill's colours are the selected option's own (so contrast never drops)",
              f["afterBg"] == r["bg"] and f["afterColour"] == r["colour"] and f["baseBg"] in ("rgba(0, 0, 0, 0)", "transparent"), [f, r])
        check("when it ends the switch is back to its plain look", r["cls"] == 0 and not r["label"], r)

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

        print("\n--- 10. Button sweep: no tap square, smooth and clipped colour changes ---")
        seen, problems = set(), {"square": [], "noTrans": [], "unclipped": []}
        for go in ("showTab('units')", "showTab('settings')"):
            page.evaluate(go)
            page.wait_for_timeout(350)
            r = page.evaluate(SWEEP, KINDS)
            seen.update(r["seen"])
            for k in problems: problems[k] += r[k]
        check("no tappable thing shows the browser's own square when pressed (tap highlight transparent)", not problems["square"], problems["square"])
        # AB4 (AT-34): chips are the exception now: their colour switches at once (no fill and no colour transition)
        check("every kind of button except chips changes colour on a clock, not in a single frame", set(problems["noTrans"]) <= {".chip"} and len(seen) >= 8, [problems["noTrans"], sorted(seen)])
        check("every fill drawn beside a button stays inside its rounded shape", not problems["unclipped"], problems["unclipped"])
        page.evaluate("showTab('units')")
        page.wait_for_timeout(350)
        page.evaluate("() => { if (document.getElementById('filter-card').classList.contains('hidden')) document.getElementById('toggle-filters').click(); }")
        page.wait_for_timeout(450)
        page.tap("#group-chips .chip:nth-child(1)")
        ch = page.evaluate("""() => { const g = document.querySelector('body > .lq-ghost > .chip'); const el = document.querySelector('#group-chips .chip:nth-child(1)');
            const a = g && g.getAnimations()[0]; const k = a ? a.effect.getKeyframes().map(x => x.clipPath) : [];
            return { ghost: !!g, aria: g && g.parentElement.getAttribute('aria-hidden'), ids: g ? g.querySelectorAll('[id]').length + (g.id ? 1 : 0) : -1, k,
                     copyBg: g && getComputedStyle(g).backgroundColor, copyColour: g && getComputedStyle(g).color, baseBg: getComputedStyle(el).backgroundColor,
                     focusRing: document.activeElement === el && el.matches(':focus-visible') }; }""")
        page.wait_for_timeout(500)
        fin = page.evaluate("""() => { const el = document.querySelector('#group-chips .chip:nth-child(1)'); const c = getComputedStyle(el);
            return { on: el.getAttribute('aria-pressed'), bg: c.backgroundColor, colour: c.color, left: document.querySelectorAll('.lq-ghost, .lq-chip-hold').length,
                     inline: el.getAttribute('style') || '' }; }""")
        # AB4 (AT-34): the chip fill (the rounded copy that was uncovered) is gone, so these two checks now say the opposite: no copy, the colour is there at once.
        check("a chip switched on has no fill copy over it", not ch["ghost"], ch)
        check("a chip switched on has its switched-on colours at once (so contrast never drops)", fin["on"] == "true" and ch["baseBg"] == fin["bg"], [ch, fin])
        check("when the fill ends the chip is back to its own look, with nothing left over", fin["left"] == 0 and "important" not in fin["inline"], fin)
        check("a touch tap leaves no focus ring", not ch["focusRing"], ch)
        page.evaluate("() => { settings.appearance = 'light'; applyPalette(settings.palette); }")
        moving = page.evaluate("() => document.getAnimations().filter(a => a instanceof CSSTransition && a.playState === 'running').map(a => a.transitionProperty + ' ' + (a.effect.target.className || ''))")
        check("a change of look (Light here) stays instant: no colour transitions play", not moving, moving[:5])
        page.evaluate("() => { settings.appearance = 'dark'; applyPalette(settings.palette); }")
        print("\n--- 9. Reduce motion ---")
        page.emulate_media(reduced_motion="reduce")
        page.evaluate("showTab('recipes')")
        page.wait_for_timeout(300)
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
        r = page.evaluate(SWEEP, KINDS)
        check("with Reduce motion on, every kind of button changes colour at once (no transitions)", len(r["seen"]) >= 4 and set(r["noTrans"]) == set(r["seen"]) - {".seg > button"}, r)
        ctx.close()
        browser.close()
    check("no page errors", not errors, errors[:3])
    print(f"\n{sum(results)}/{len(results)} passed")
    sys.exit(0 if all(results) else 1)

main()
