"""AB4 tests for Minifolio (motion: easing, start circle travel, ripple and hover, small effects, basket pop). New behaviour only:
1. Two new easing tokens exist; things arriving (dialog, toast, name slide in) use ease-out, the name sliding out uses ease-in.
2. The start circle's travel is about half a second on a curve with no overshoot; a tap on the bar  cuts it short and is used up.
3. No ripple (no rule, no keyframes, nothing added on a tap). Hover on a main button changes no transform, translate or shadow.
4. No chip fill sweep (no transition on the fill, no copy layer after a tap), no stage-chip cascade, no pip stagger.
5. The basket pop peaks at 1.06 and never goes below 1. 6. Reduced motion runs none of these.
No speed timings. Run with `python3 tests/run_all.py`, or serve the repo folder and run this file on its own."""
import os, re, sys
from playwright.sync_api import sync_playwright

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import test_v31 as t

results = []

def check(name, ok, detail=""):
    results.append(bool(ok))
    print(("PASS " if ok else "FAIL ") + name + ("" if ok else f"  -> {detail}"))

UNITS = [{"id": 1, "name": "Squad", "hobby": "40K", "stage": 2, "count": 5, "added": "2026-10-01", "log": [["2026-10-01", 2]]}]

# the rules of every style sheet, flattened (media rules included): [selector text, style]
RULES = """() => { const out = []; const walk = (rules) => { for (const r of rules) { if (r.cssRules && !r.selectorText && r.type !== 7) walk(r.cssRules);
    else if (r.selectorText) out.push([r.selectorText, r.style.cssText]); } }; for (const s of document.styleSheets) { try { walk(s.cssRules); } catch (e) {} } return out; }"""
KEYFRAMES = """(name) => { for (const s of document.styleSheets) for (const r of s.cssRules) if (r.type === 7 && r.name === name) return [...r.cssRules].map(k => k.style.cssText); return null; }"""

def rule(rules, *needles):
    return [css for sel, css in rules if all(n in sel for n in needles)]

def main():
    errors = []
    with sync_playwright() as p:
        browser = p.chromium.launch()
        ctx = browser.new_context(viewport={"width": 390, "height": 844}, service_workers="block")
        page = ctx.new_page()
        page.on("pageerror", lambda x: errors.append(str(x)))
        t.load(page, units=UNITS, launch=True)
        root = lambda v: page.evaluate("(v) => getComputedStyle(document.documentElement).getPropertyValue(v).trim()", v)

        print("\n--- 1. Easing ---")
        check("--motion-ease-out and --motion-ease-in exist", root("--motion-ease-out") == "cubic-bezier(0.2, 0.7, 0.3, 1)" and root("--motion-ease-in") == "cubic-bezier(0.4, 0, 1, 1)",
              (root("--motion-ease-out"), root("--motion-ease-in")))
        check("--motion-ease is still linear (fades, the drain line and the loading sweep keep it)", root("--motion-ease") == "linear")
        rules = page.evaluate(RULES)
        for name, needles, want in [("the dialog rise", (".dialog-backdrop:not(.hidden) > .dialog",), "ease-out"), ("the toast coming up", ("toast:not(.hidden)",), "ease-out"),
                                    ("the stage name sliding in", (".mo-slide > .stage-in",), "ease-out"), ("the stage name sliding out", (".mo-slide::before",), "ease-in")]:
            found = [c for c in rule(rules, *needles) if "animation" in c]
            check(f"{name} uses {want}", found and f"--motion-{want}" in found[0], found)
        check("the toast's drain line is still linear", any("mo-drain" in c and "linear" in c for c in rule(rules, ".toast.draining::after")))

        print("\n--- 2. The travel ---")
        ms = float(root("--motion-travel").replace("ms", ""))
        check("the travel is between 450 and 650 ms", 450 <= ms <= 650, ms)
        check("the travel curve is cubic-bezier(0.4, 0, 0.2, 1): y values stay between 0 and 1, so no overshoot", root("--motion-travel-ease") == "cubic-bezier(0.4, 0, 0.2, 1)", root("--motion-travel-ease"))
        page.evaluate("() => document.querySelector('.tabs button[data-tab=dashboard]').click()")
        started = page.evaluate("() => document.body.classList.contains('mo-travelling')")
        box = page.evaluate("() => { const r = document.querySelector('.tabs button[data-tab=units]').getBoundingClientRect(); return [r.left + r.width / 2, r.top + r.height / 2]; }")   # a piece of the bar (not the Mentor button, not the title)
        page.mouse.move(*box)
        page.mouse.down()
        cut = page.evaluate("() => !document.body.classList.contains('mo-travelling') && document.querySelectorAll('.mo-tr').length === 0")
        page.mouse.up()
        page.wait_for_timeout(300)
        check("the travel was running, and a tap on the bar cuts it short", started and cut, (started, cut))
        check("the tap does not open the section under it (the pieces were not tappable during the travel)", page.evaluate("() => !document.body.classList.contains('launching') && settings.tab === 'dashboard'"))
        check("the bar is the real one afterwards (nothing left over)", page.evaluate("() => !document.body.classList.contains('mo-travelling') && document.querySelectorAll('.mo-tr, .mo-ring, .mo-ghost').length === 0"))
        page.evaluate("() => document.getElementById('home-button').click()")
        page.wait_for_timeout(1500)
        check("a tap on the title with no travel still works as before", page.evaluate("() => document.body.classList.contains('launching')"))

        page.evaluate("() => { document.querySelector('.tabs button[data-tab=dashboard]').click(); }")
        page.wait_for_function("() => !document.body.classList.contains('mo-travelling')", timeout=6000)
        page.evaluate("() => document.getElementById('home-button').click()")
        page.click("#mentor-button")
        page.wait_for_selector(".mentor-window", timeout=5000)
        check("a tap on the Mentor button during the travel still opens Mentor (a tap there is not changed)", page.locator(".mentor-window").count() == 1)

        print("\n--- 3. Ripple and hover ---")
        check("no .ripple rule and no mo-ripple keyframes", not rule(rules, ".ripple") and page.evaluate(KEYFRAMES, "mo-ripple") is None)
        check("the ripple script is gone (nothing is added when a button is pressed)", page.evaluate("""() => { const b = document.createElement('button'); b.className = 'plain-button'; document.body.appendChild(b);
            b.dispatchEvent(new PointerEvent('pointerdown', { bubbles: true, clientX: 5, clientY: 5 })); const n = b.querySelectorAll('.ripple').length + (b.classList.contains('rip-host') ? 1 : 0); b.remove(); return n === 0; }"""))
        hover = [c for sel, c in rules if ":hover" in sel and ("primary-button" in sel or "plain-button" in sel)]
        check("hover on a main button sets no transform, translate, scale or shadow", hover and not any(re.search(r"transform|translate|scale|box-shadow", c) for c in hover), hover)
        check("hover on a main button changes the border colour", any("border-color" in c for c in hover), hover)
        check("the press is kept: 1 px down, scale 0.97, brightness 0.92",
              any("translate: 0px 1px" in c and "scale: 0.97" in c and "brightness(0.92)" in c for c in rule(rules, ".primary-button:not(:disabled):active")), rule(rules, ".primary-button:not(:disabled):active"))

        print("\n--- 4. Small effects ---")
        t.load(page, units=UNITS)
        page.click('nav button[data-tab="units"]'); t.quiet(page)
        page.evaluate("() => document.querySelector('#group-chips .chip').click()")
        after = page.evaluate("""() => { const chip = document.querySelector('#group-chips .chip[aria-pressed=true]'), cs = chip && getComputedStyle(chip);
            return { chip: !!chip, fill: cs && /background|size/.test(cs.transitionProperty), layers: document.querySelectorAll('.lq-ghost').length, sweep: document.querySelectorAll('.chip.sweep').length,
                     cascade: document.getElementById('stage-chips').classList.contains('cascade'), anims: document.getElementById('stage-chips').getAnimations({ subtree: true }).length,
                     stages: document.querySelectorAll('#stage-chips .chip').length }; }""")
        check("a chip tapped on: its colour switches at once (no fill transition, no sweep, no copy layer)", after["chip"] and not after["fill"] and not after["layers"] and not after["sweep"], after)
        check("the stage chips show at once: no cascade class and no animation on them", after["stages"] > 0 and not after["cascade"] and after["anims"] == 0, after)
        check("no cascade rule or keyframes left", not rule(rules, "cascade") and page.evaluate(KEYFRAMES, "mo-cascade") is None)
        pip = page.evaluate("""() => { const el = document.createElement('div'); markPip(el, 3, { fromStage: 1 }); return { i: el.style.getPropertyValue('--i'), cls: el.classList.contains('mo-pip') }; }""")
        check("a pip fade carries no stagger index", pip["cls"] and pip["i"] == "", pip)
        check("the pip rule has no animation delay", all("delay" not in c for c in rule(rules, ".mo-pip")), rule(rules, ".mo-pip"))
        check("the stage-name slide, the colour fade and the ring pulse are kept", all(rule(rules, s) for s in (".mo-slide::before", "li.unit.mo-stage", "li.unit.mo-up::after")))

        print("\n--- 5. Basket pop ---")
        frames = page.evaluate(KEYFRAMES, "basket-pop") or []
        scales = [float(m) for c in frames for m in re.findall(r"scale\(([\d.]+)\)", c)]
        check("basket-pop peaks at 1.06 and never goes below 1", scales and max(scales) == 1.06 and min(scales) >= 1, scales)
        check("it arrives on ease-out", any("basket-pop" in c and "--motion-ease-out" in c for c in rule(rules, ".basket.pop")), rule(rules, ".basket.pop"))
        ctx.close()

        print("\n--- 6. Reduced motion ---")
        ctx = browser.new_context(viewport={"width": 360, "height": 640}, service_workers="block", reduced_motion="reduce")
        page = ctx.new_page()
        t.load(page, units=UNITS, launch=True)
        page.evaluate("() => document.querySelector('.tabs button[data-tab=dashboard]').click()")
        check("no travel: no copies and nothing travelling", page.evaluate("() => !document.body.classList.contains('mo-travelling') && document.querySelectorAll('.mo-tr').length === 0"))
        page.evaluate("() => document.querySelector('nav button[data-tab=units]').click()"); t.quiet(page)
        page.evaluate("() => document.querySelector('#group-chips .chip').click()")
        check("a chip tap starts no animation", page.evaluate("() => document.getAnimations().filter(a => a.effect && a.effect.target && a.effect.target.closest('#group-chips, #stage-chips')).length === 0"))
        check("the basket pop and the stage animations are off", page.evaluate("""() => { const b = document.querySelector('.app-actions .basket'); b.classList.add('pop'); const el = document.createElement('div'); el.className = 'mo-pip'; document.body.appendChild(el);
            const r = getComputedStyle(b).animationName === 'none' && getComputedStyle(el).animationName === 'none'; el.remove(); return r; }"""))
        ctx.close()
        browser.close()
    check("no page errors", not [e for e in errors if "woff2" not in e], errors)
    bad = results.count(False)
    print(f"\n{len(results) - bad} passed, {bad} failed")
    sys.exit(1 if bad else 0)

if __name__ == "__main__":
    main()
