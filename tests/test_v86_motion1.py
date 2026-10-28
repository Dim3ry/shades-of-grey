"""v86 tests for Minifolio (chunk Mo1: shared motion).

New behaviour only:
1. One place for the timings (--motion-fast / med / slow / ease), and one shared reduced-motion block.
2. Main buttons lift on hover and press on tap; a ripple starts at the tap point; the tab bar and chips get none.
3. Chips: the fill sweeps when switched on (To do / Done / Repaint also tick); the stage chips cascade in once, on opening.
4. The question box fades and rises; Escape still means No.
5. The Undo message slides up and its line drains over the real lifetime (one timer).
6. A new unit drops in once; the outline flash stays.
7. With reduced motion on: no ripple, no sweep, no cascade, no animation at all.
8. 390 and 360 px, dark and light: no sideways scroll, tap targets 44 px or more.
Item 7 of the chunk (Dashboard bars) is not built: the Dashboard has doughnuts and a line graph, no bars."""
import os, sys
from playwright.sync_api import sync_playwright

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import test_v31 as t

load, no_sideways = t.load, t.no_sideways
results = []

def check(name, ok, detail=""):
    results.append(bool(ok))
    print(("PASS " if ok else "FAIL ") + name + ("" if ok else f"  -> {detail}"))

def units(n):
    return [{"id": i + 1, "name": f"Squad {i + 1}", "hobby": "40K", "stage": i % 4, "count": 5, "added": "2026-01-01",
             "log": [["2026-01-01", i % 4]]} for i in range(n)]

def css(page, sel, prop):
    return page.evaluate("([s, p]) => getComputedStyle(document.querySelector(s))[p]", [sel, prop])

def life(page):
    return page.evaluate("() => document.getElementById('toast').style.getPropertyValue('--toast-life')")

def main():
    errors, dialogs = [], []
    with sync_playwright() as p:
        browser = p.chromium.launch()
        ctx = browser.new_context(viewport={"width": 390, "height": 900}, service_workers="block")
        page = ctx.new_page()
        page.on("pageerror", lambda x: errors.append(str(x)))
        page.on("dialog", lambda d: (dialogs.append(d.message), d.dismiss()))

        print("\n--- 1. Shared values ---")
        load(page, units=units(3))
        vals = page.evaluate("""() => { const s = getComputedStyle(document.documentElement);
            return ['--motion-fast', '--motion-med', '--motion-slow', '--motion-ease'].map(v => s.getPropertyValue(v).trim()); }""")
        check("the four timing values exist: 120 ms, 240 ms, 480 ms, linear", vals == ["120ms", "240ms", "480ms", "linear"], vals)
        page.click('nav button[data-tab="units"]')
        page.wait_for_timeout(200)

        print("\n--- 2. Buttons ---")
        btn = page.locator("#toggle-select")
        btn.hover()
        page.wait_for_timeout(200)
        check("hover lifts a main button", css(page, "#toggle-select", "translate").startswith("0px -2px"), css(page, "#toggle-select", "translate"))
        box = btn.bounding_box()
        page.mouse.move(box["x"] + 10, box["y"] + 10)
        page.mouse.down()
        page.wait_for_timeout(60)
        check("a ripple starts inside the button at the tap point",
              page.evaluate("() => { const r = document.querySelector('#toggle-select .ripple'); return !!r && Math.abs(parseFloat(r.style.left) - 10) < 2; }"))
        page.wait_for_timeout(120)
        check("pressing shrinks it slightly", css(page, "#toggle-select", "scale").startswith("0.97"), css(page, "#toggle-select", "scale"))
        page.mouse.up()
        page.wait_for_timeout(700)
        check("the ripple removes itself", page.locator("#toggle-select .ripple").count() == 0)
        page.click("#toggle-select")   # leave select mode again
        page.wait_for_timeout(200)
        check("tab bar buttons get no lift", css(page, 'nav button[data-tab="units"]', "translate") in ("none", "0px"))
        page.mouse.move(5, 5)

        print("\n--- 3. Chips ---")
        page.click("#toggle-filters")
        page.wait_for_timeout(200)
        sweep = page.evaluate("() => { document.querySelector('#group-chips .chip').click(); const c = document.querySelector('#group-chips .chip[aria-pressed=\"true\"]'); return !!c && c.classList.contains('sweep'); }")
        check("a chip you switch on starts empty and fills (aria-pressed is already true)", sweep)
        page.wait_for_timeout(400)
        check("…then has the full fill and a tick",
              page.evaluate("""() => { const c = document.querySelector('#group-chips .chip[aria-pressed="true"]');
                  return !c.classList.contains('sweep') && getComputedStyle(c).backgroundSize.startsWith('100%') && getComputedStyle(c, '::before').width !== '0px'; }"""))
        check("the stage chips cascade in when they open, one after another",
              page.evaluate("""() => { const r = document.getElementById('stage-chips'), c = r.querySelectorAll('.chip');
                  return r.classList.contains('cascade') && c.length > 4 && getComputedStyle(c[2]).animationDelay === '0.1s'; }"""))
        page.click("#group-chips .chip >> nth=1")   # another redraw with the stages already open
        page.wait_for_timeout(100)
        check("…and not again on later redraws", not page.evaluate("() => document.getElementById('stage-chips').classList.contains('cascade')"))

        print("\n--- 4. Question box ---")
        page.evaluate("() => { askYesNo('Delete this unit?', () => { window.__yes = true; }); }")
        page.wait_for_timeout(50)
        check("the dim layer fades and the box rises",
              css(page, ".dialog-backdrop", "animationName") == "mo-fade" and css(page, ".dialog", "animationName") == "mo-rise")
        page.keyboard.press("Escape")
        page.wait_for_timeout(100)
        check("Escape still means No", page.locator(".dialog-backdrop.hidden").count() == 1 and not page.evaluate("() => !!window.__yes"))

        print("\n--- 5. Undo message ---")
        page.evaluate("() => showToast('Moved', () => {}, 'Undo', 5)")
        page.wait_for_timeout(60)
        check("it slides up", css(page, "#toast", "animationName") == "mo-toast-in")
        check("the line drains over the message's own 5 seconds, from the one timer",
              life(page) == "5s" and page.evaluate("() => document.getElementById('toast').classList.contains('draining')")
              and css(page, "#toast", "animationName") != "none")
        page.evaluate("() => showToast('Again', null, null, 8)")
        check("a new message restarts the line with its own time", life(page) == "8s")
        page.wait_for_timeout(100)

        print("\n--- 6. New unit ---")
        page.evaluate("() => { clearFilters(); render(); }")
        page.click("#toggle-add")
        page.fill("#name-input", "Newcomers")
        page.click("#add-form button[type=submit]")
        page.wait_for_timeout(60)
        check("it drops in and is outlined",
              page.evaluate("""() => { const li = [...document.querySelectorAll('#view-units li.unit')].find(l => l.textContent.includes('Newcomers'));
                  return !!li && li.classList.contains('just-dropped') && li.classList.contains('just-added') && getComputedStyle(li).animationName.includes('mo-drop'); }"""))
        page.evaluate("() => render()")
        check("…and does not drop again on a redraw",
              page.evaluate("""() => { const li = [...document.querySelectorAll('#view-units li.unit')].find(l => l.textContent.includes('Newcomers'));
                  return !li.classList.contains('just-dropped'); }"""))
        page.wait_for_timeout(2700)
        check("the outline goes after a few seconds", page.locator("li.unit.just-added").count() == 0)

        print("\n--- 7. Reduced motion ---")
        rctx = browser.new_context(viewport={"width": 390, "height": 900}, service_workers="block", reduced_motion="reduce")
        rp = rctx.new_page()
        rp.on("pageerror", lambda x: errors.append(str(x)))
        load(rp, units=units(3))
        rp.click('nav button[data-tab="units"]')
        rp.click("#toggle-filters")
        rp.wait_for_timeout(200)
        rp.click("#toggle-select")
        rp.wait_for_timeout(80)
        check("no ripple is made", rp.locator(".ripple").count() == 0)
        rp.click("#toggle-select")
        rp.click("#group-chips .chip >> nth=0")
        rp.wait_for_timeout(20)
        check("chips fill at once, no cascade",
              not rp.evaluate("() => !!document.querySelector('.chip.sweep') || document.getElementById('stage-chips').classList.contains('cascade')"))
        rp.evaluate("() => askYesNo('Sure?', () => {})")
        rp.wait_for_timeout(20)
        rp.evaluate("() => showToast('Moved', () => {}, 'Undo', 5)")
        rp.wait_for_timeout(20)
        check("question box, message and line have no animation",
              all(css(rp, s, "animationName") == "none" for s in (".dialog-backdrop", ".dialog", "#toast")))
        check("buttons have no transition", set(css(rp, "#dialog-yes", "transitionDuration").split(", ")) == {"0s"}, css(rp, "#dialog-yes", "transitionDuration"))
        rctx.close()

        print("\n--- 8. Layout ---")
        for width in (390, 360):
            for scheme in ("dark", "light"):
                c2 = browser.new_context(viewport={"width": width, "height": 900}, service_workers="block", color_scheme=scheme)
                p2 = c2.new_page()
                load(p2, units=units(3))
                p2.evaluate("() => showToast('Moved to Battle ready', () => {}, 'Undo', 5)")
                p2.wait_for_timeout(300)
                small = p2.evaluate("""() => [...document.querySelectorAll('#toast button')].filter(b => b.offsetParent && b.getBoundingClientRect().height < 43).length""")
                check(f"{width} px {scheme}: no sideways scroll, message button 44 px or more", no_sideways(p2) and small == 0, small)
                c2.close()

        check("no page errors", not errors, errors)
        check("no browser pop-ups", not dialogs, dialogs)
        browser.close()
    print(f"\n{sum(results)}/{len(results)} checks passed")
    sys.exit(0 if all(results) else 1)

if __name__ == "__main__":
    main()
