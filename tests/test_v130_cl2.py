"""CL2 tests for Minifolio: Colour Lab colours morph from one set to the next (James, 3 Nov: "When a colour is pressed, non chosen
colours smoothly slide in behind the pressed colour and the next set of colours smoothly slide out"). New behaviour only, no speed timings:
1. Start from: pressing a swatch slides the other swatches in behind it (and back), and its colour ideas slide out from behind it;
   the pressed swatch stays where it is and is drawn over the rest. Everything ends in place with no transform.
2. The wheel: a hue opens into its groups through a see-through copy of the old wheel (no ids but its own cmp- one, no classes, data-,
   aria- or role; cannot be tapped; hidden from screen readers) whose other colours slide in behind the pressed one, while the groups
   slide out. A group's paints slide out from behind the group. Back reverses it. Focus lands where it did before.
3. A quick second press finishes the first morph at once and leaves nothing stuck.
4. Reduce motion: no animation and no copy.
Run all tests with `python3 tests/run_all.py`, or serve the repo folder and run this file on its own."""
import os, sys
from playwright.sync_api import sync_playwright

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import test_v31 as t

results = []

def check(name, ok, detail=""):
    results.append(bool(ok))
    print(("PASS " if ok else "FAIL ") + name + ("" if ok else f"  -> {detail}"))

def P(i, name, colour):
    return {"id": i, "brand": "Test Paints", "name": name, "colour": colour, "status": "owned"}

OWN = [P(i + 1, f"Own {c}", h) for i, (c, h) in enumerate([("Red", "#b22222"), ("Blue", "#2a4d9b"), ("Green", "#2e8b57"), ("Yellow", "#e0c020"),
       ("Orange", "#e07020"), ("Purple", "#6a3d9a"), ("Bone", "#d8cba0"), ("Grey", "#808890")])]
LAB = {"tab": "recipes", "recipeView": "colourlab", "examplesChecked": True, "recipeExamplesChecked": True, "feedbackShown": True, "backupNudgeDone": True}

# what moves: for each element, the transform and opacity at the start and the end of its animations (or None when it has none)
MOVES = """(sel) => [...document.querySelectorAll(sel)].map(el => { const a = el.getAnimations().find(x => !(x instanceof CSSTransition) && !(x instanceof CSSAnimation)); if (!a) return null;
    const k = a.effect.getKeyframes(); return { t0: k[0].transform || null, o0: +k[0].opacity, t1: k[k.length - 1].transform || null, o1: +k[k.length - 1].opacity,
      mid: k.filter(f => f.computedOffset === 0.5).map(f => [f.transform || null, +f.opacity]) }; })"""
# what is left once it has played: transforms, animations, copies and the "drawn over" mark, anywhere on the page
LEFT = """() => { const lab = document.getElementById('colourlab-body');
    const moved = [...lab.querySelectorAll('.start-swatch, .idea-list > li, .wheel-svg, .wheel-svg *')].filter(el => getComputedStyle(el).transform !== 'none').map(el => el.className.baseVal ?? el.className);
    return { moved, anims: document.getAnimations().filter(a => a.playState === 'running' || a.playState === 'paused').length,
             ghosts: document.querySelectorAll('.cl2-ghost').length, front: document.querySelectorAll('.cl2-front').length }; }"""
ON_SCREEN = """(sel) => [...document.querySelectorAll(sel)].map(el => { const r = el.getBoundingClientRect(); return r.bottom > 0 && r.top < innerHeight; })"""
CLEAN = {"moved": [], "anims": 0, "ghosts": 0, "front": 0}

def settle(page, ms=700):
    page.wait_for_timeout(ms)

def main():
    errors = []
    with sync_playwright() as p:
        browser = p.chromium.launch()
        ctx = browser.new_context(viewport={"width": 390, "height": 844}, service_workers="block")
        page = ctx.new_page()
        page.on("pageerror", lambda x: errors.append(str(x)))
        t.load(page, paints=OWN, recipes=[t.rec(1, "Uses", "Armour", [1, 2])], units=[t.unit(1, "Troop A", "Gloom Legion", [1])], settings=LAB)
        page.evaluate("() => openColourLab('ideas')")
        settle(page)

        print("\n--- 1. Start from: the others slide in behind the pressed swatch, its ideas slide out ---")
        key = page.evaluate("() => document.querySelectorAll('#cmp-start-swatches .start-swatch')[2].dataset.startSwatch")
        sel = f'#cmp-start-swatches .start-swatch[data-start-swatch="{key}"]'
        before = page.evaluate("(s) => { const r = document.querySelector(s).getBoundingClientRect(); return [r.left, r.top]; }", sel)
        page.click(sel)
        m = page.evaluate(MOVES, "#cmp-start-swatches .start-swatch")
        idx = page.evaluate("(k) => [...document.querySelectorAll('#cmp-start-swatches .start-swatch')].findIndex(b => b.dataset.startSwatch === k)", key)
        pressed, others = m[idx], [x for i, x in enumerate(m) if i != idx]
        rows = [r for r, seen in zip(page.evaluate(MOVES, "#cmp-lab-ideas .idea-list > li"), page.evaluate(ON_SCREEN, "#cmp-lab-ideas .idea-list > li")) if seen]
        st = page.evaluate("""(s) => { const b = document.querySelector(s), r = b.getBoundingClientRect();
            return { at: [r.left, r.top], front: b.classList.contains('cl2-front'), z: getComputedStyle(b).zIndex, focus: document.activeElement === b, on: b.getAttribute('aria-pressed') }; }""", sel)
        check("the other swatches slide in behind the pressed one and fade (shrunk), then come back to their own places",
              others and all(o and o["t0"] == "none" and o["o0"] == 1 and o["mid"] and o["mid"][0][0].startswith("translate(") and o["mid"][0][1] == 0
                             and o["t1"] == "none" and o["o1"] == 1 for o in others), others[:2])
        check("the pressed swatch stays where it is, drawn over the rest, chosen and focused as before",
              pressed is None and st["at"] == before and st["front"] and st["z"] == "2" and st["focus"] and st["on"] == "true", [pressed, st, before])
        check("its colour ideas slide out from behind it into place", rows and all(r and r["t0"].startswith("translate(") and r["o0"] == 0 and r["t1"] == "none" and r["o1"] == 1 for r in rows), rows)
        settle(page)
        left = page.evaluate(LEFT)
        check("when it ends everything is in place: no transform, no animation, nothing left drawn over the rest", left == CLEAN, left)
        page.click(sel)
        check("pressing the chosen swatch again starts nothing (no new set)", page.evaluate(LEFT)["anims"] == 0)

        print("\n--- 2. The wheel: a hue opens into its groups, a group's paints, Back ---")
        page.evaluate("() => openColourLab('wheel')")
        settle(page)
        page.click('[data-wheel="red"]')
        g = page.evaluate("""() => { const l = document.querySelector('.cl2-ghost'); if (!l) return null; const svg = l.querySelector('svg');
            const all = [l, ...l.querySelectorAll('*')];
            return { aria: l.getAttribute('aria-hidden'), inert: l.inert, tap: getComputedStyle(l).pointerEvents, parent: l.parentElement === document.body,
                     ids: all.filter(e => e.id).map(e => e.id), cls: all.slice(1).filter(e => e.getAttribute('class')).length,
                     attrs: all.flatMap(e => [...e.attributes].map(a => a.name)).filter(n => n.startsWith('data-') || n.startsWith('aria-') && n !== 'aria-hidden' || n === 'role' || n === 'tabindex'),
                     moving: [...svg.children].filter(c => c.getAnimations().length).length, pieces: svg.querySelectorAll('path').length }; }""")
        check("a see-through copy of the old wheel stays where it was and plays (hidden from screen readers, cannot be tapped)",
              g and g["aria"] == "true" and g["inert"] and g["tap"] == "none" and g["parent"] and g["moving"] >= 10, g)
        check("the copy has no classes, data-, aria- or role, and no id but its own cmp- one", g and g["cls"] == 0 and not g["attrs"] and all(i.startswith("cmp-") for i in g["ids"]), g)
        gm = page.evaluate("""() => { const svg = document.querySelector('.cl2-ghost svg'); return [...svg.children].filter(c => c.tagName === 'path').map(c => {
            const k = c.getAnimations()[0].effect.getKeyframes(); return [k[0].transform || null, k[k.length - 1].transform || null, +k[k.length - 1].opacity]; }); }""")
        check("in the copy, the other colours slide in behind the pressed one and fade; the pressed one, drawn last, stays and fades",
              sum(1 for x in gm if x[1] and x[1].startswith("translate(") and x[2] == 0) == len(gm) - 1 and gm[-1][1] is None and gm[-1][2] == 0, gm)
        groups = page.evaluate(MOVES, "#cmp-wheel .wheel-sub-seg")
        check("the red groups slide out from behind it into place", len(groups) == 3 and all(x and x["t0"].startswith("translate(") and x["o0"] == 0 and x["t1"] == "none" and x["o1"] == 1 for x in groups), groups)
        check("focus is on the first group, as before", page.evaluate("() => document.activeElement === document.querySelector('#cmp-wheel .wheel-sub-seg')"))
        settle(page)
        left = page.evaluate(LEFT)
        check("when it ends the copy is gone and nothing is left with a transform", left == CLEAN, left)

        sub = "red/red"   # the group with a paint you own, so its list has rows
        page.evaluate("() => scrollTo(0, 300)")   # (on a phone the list starts just under the screen; here it is on it)
        page.click(f'[data-wheel-sub="{sub}"]')
        gs = page.evaluate(MOVES, "#cmp-wheel .wheel-sub-seg")
        rows = [r for r, seen in zip(page.evaluate(MOVES, "#cmp-wheel-detail .idea-list > li"), page.evaluate(ON_SCREEN, "#cmp-wheel-detail .idea-list > li")) if seen]
        pressed_i = page.evaluate("(k) => [...document.querySelectorAll('#cmp-wheel .wheel-sub-seg')].findIndex(e => e.dataset.wheelSub === k)", sub)
        check("pressing a group: the other groups slide in behind it and back, it stays", gs[pressed_i] is None and all(x and x["mid"] and x["mid"][0][0].startswith("translate(") for i, x in enumerate(gs) if i != pressed_i), gs)
        check("its paints on the screen slide out from behind it", rows and all(r and r["t0"].startswith("translate(") and r["o0"] == 0 and r["t1"] == "none" for r in rows), rows[:3])
        settle(page)
        check("the group's morph ends with nothing left over", page.evaluate(LEFT) == CLEAN, page.evaluate(LEFT))

        page.click('[data-wheel-back]')
        back = page.evaluate(MOVES, "#cmp-wheel .wheel-seg")
        check("Back: a copy of the groups plays, and all the colours slide out from the Back disc",
              page.evaluate("() => document.querySelectorAll('.cl2-ghost').length") == 1 and len(back) == 10 and all(x and x["t0"].startswith("translate(") and x["t1"] == "none" for x in back), back[:2])
        check("focus is on the hue you came from, as before", page.evaluate("() => document.activeElement === document.querySelector('[data-wheel=\"red\"]')"))
        settle(page)
        check("Back's morph ends with nothing left over", page.evaluate(LEFT) == CLEAN, page.evaluate(LEFT))

        print("\n--- 3. Quick presses ---")
        page.focus('[data-wheel="blue"]')
        page.keyboard.press("Enter")
        page.evaluate("() => document.querySelectorAll('#cmp-wheel .wheel-sub-seg')[2].dispatchEvent(new MouseEvent('click', { bubbles: true }))")
        mid = page.evaluate("() => ({ ghosts: document.querySelectorAll('.cl2-ghost').length, open: document.querySelectorAll('#cmp-wheel .wheel-sub-seg[aria-pressed=\"true\"]').length })")
        check("a press while a morph runs finishes it at once (its copy is gone) and starts its own", mid == {"ghosts": 0, "open": 1}, mid)
        page.evaluate("() => openColourLab('ideas')")
        page.wait_for_timeout(50)
        page.evaluate("""() => { const bs = () => document.querySelectorAll('#cmp-start-swatches .start-swatch'); for (const i of [0, 3, 5, 1]) bs()[i].click(); }""")
        settle(page)
        q = page.evaluate("() => { const b = document.querySelectorAll('#cmp-start-swatches .start-swatch')[1]; return [b.getAttribute('aria-pressed'), document.activeElement === b]; }")
        left = page.evaluate(LEFT)
        check("four quick taps in a row: the last one is chosen and focused, and nothing is stuck", q == ["true", True] and left == CLEAN, [q, left])
        check("Enter on a hue still opens its groups (the keyboard gets the same morph)", page.evaluate("() => compendiumState.wheelZoom") == "blue")

        print("\n--- 4. Reduce motion ---")
        page.emulate_media(reduced_motion="reduce")
        page.evaluate("() => { compendiumState.wheelZoom = ''; compendiumState.wheelGroup = ''; openColourLab('wheel'); }")
        page.wait_for_timeout(100)
        seen = []
        for name, s in (("a hue", '[data-wheel="green"]'), ("a group", "#cmp-wheel .wheel-sub-seg"), ("Back", "[data-wheel-back]")):
            page.click(s)
            o = page.evaluate("() => ({ anims: document.getAnimations().length, ghosts: document.querySelectorAll('.cl2-ghost, .cl2-front').length })")
            if o != {"anims": 0, "ghosts": 0}:
                seen.append([name, o])
        page.evaluate("() => openColourLab('ideas')")
        page.wait_for_timeout(100)
        page.click("#cmp-start-swatches .start-swatch:nth-child(4)")
        o = page.evaluate("() => ({ anims: document.getAnimations().length, ghosts: document.querySelectorAll('.cl2-ghost, .cl2-front').length })")
        if o != {"anims": 0, "ghosts": 0}:
            seen.append(["a swatch", o])
        check("with Reduce motion on, the new set appears at once: no animation, no copy", not seen, seen)
        ctx.close()
        browser.close()
    check("no page errors", not errors, errors[:3])
    print(f"\n{sum(results)}/{len(results)} passed")
    sys.exit(0 if all(results) else 1)

main()
