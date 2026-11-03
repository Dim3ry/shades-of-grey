"""LR1 tests for Minifolio (the start-up loading ring is a real loading bar from the first frame). New behaviour only:
1. The ring is in the page itself: with every script blocked it is already there (a progress bar named Loading), moving (the sweep) and
   centred on the Mentor button, with the four segments held back.
2. It follows real progress: with app.js held back, early.js has already lit part of it from the script files that arrived; then it reaches
   full and goes, never going backwards, lighting the Futuristic look's five segments in turn, clockwise from 12 o'clock.
3. Magical and Grounded keep Mo4a's three turning arcs.
4. Reduced motion: no sweep and nothing turning, the segments light in whole steps, and it still finishes and goes.
5. Opening the app on a section takes it away at once. Sizes, light and dark, three themes: in place before and after app.js runs.
Run all tests with `python3 tests/run_all.py`, or serve the repo folder and run this file on its own."""
import os, re, sys
from playwright.sync_api import sync_playwright

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import test_v31 as t

results = []

def check(name, ok, detail=""):
    results.append(bool(ok))
    print(("PASS " if ok else "FAIL ") + name + ("" if ok else f"  -> {detail}"))

# records the ring every time early.js or app.js lights it, from the very start of the page
RECORD = """(() => { window.__ring = [];
  const rec = () => { const s = document.querySelector('.tabs .mo-load'); if (!s) return;
    window.__ring.push({ now: +s.getAttribute('aria-valuenow'), op: [...s.querySelectorAll('.lr-s')].map(c => parseFloat(c.style.opacity || '0.2')) }); };
  new MutationObserver(rec).observe(document, { attributes: true, subtree: true, attributeFilter: ['aria-valuenow', 'style'] }); })();"""
GONE = "() => typeof settings === 'object' && !document.querySelector('.mo-load, .lr-sweep') && !document.body.classList.contains('ring-loading')"
PLACE = """() => { const r = document.querySelector('.mo-load').getBoundingClientRect(), o = document.getElementById('mentor-button').getBoundingClientRect();
    return { dx: (r.left + r.width / 2) - (o.left + o.width / 2), dy: (r.top + r.height / 2) - (o.top + o.height / 2), cx: o.left + o.width / 2, cy: o.top + o.height / 2,
             inside: r.left >= -0.5 && r.right <= innerWidth + 0.5 && r.top >= 0 && r.bottom <= innerHeight + 1, sideways: document.documentElement.scrollWidth > document.documentElement.clientWidth }; }"""

def seed(page, settings=None):
    page.goto(t.BASE + "manifest.json")
    page.evaluate("s => { localStorage.clear(); localStorage.setItem('shades-of-grey-recipes', JSON.stringify({ parts: [], techniques: [], paints: [], recipes: [], schemes: [], shorthand: {}, v15: true }));"
                  " if (s) localStorage.setItem('shades-of-grey-settings', JSON.stringify(s)); }", settings)

def held_load(page, url=None):
    """Load with app.js held back; returns the held routes (call release)."""
    held = []
    page.route("**/app.js*", lambda r: held.append(r))
    page.goto(url or t.URL, wait_until="commit")
    for _ in range(300):
        if held:
            break
        page.wait_for_timeout(50)
    page.wait_for_selector(".mo-load", state="attached")
    return held

def release(page, held):
    for r in held:
        r.continue_()
    page.unroute("**/app.js*")

def main():
    html = t.read("index.html")
    errors = []
    with sync_playwright() as p:
        browser = p.chromium.launch()

        print("--- 1. In the page before any script ---")
        body = html[html.find("\n<body") + 1:]
        check("index.html itself holds the ring, before its first script, with the circle and the segments held back",
              body.startswith('<body class="launching ring-loading">') and 0 < body.find('class="mo-load"') < body.find("<script")
              and len(re.findall(r'<button data-tab="\w+" class="ring-hold"', body)) == 4)
        ctx = browser.new_context(viewport={"width": 390, "height": 844}, service_workers="block")
        page = ctx.new_page()
        page.on("pageerror", lambda x: errors.append(str(x)))
        seed(page)
        page.route("**/*.js*", lambda r: r.abort())
        page.goto(t.URL, wait_until="domcontentloaded")
        s = page.evaluate("""() => { const r = document.querySelector('.mo-load'), sw = document.querySelector('.lr-sweep');
            const a = sw && sw.getAnimations()[0];
            return { role: r && r.getAttribute('role'), name: r && r.getAttribute('aria-label'), scripts: typeof settings + typeof MENTOR_LOOKS,
                     moving: !!a && a.playState === 'running' && a.effect.getComputedTiming().iterations === Infinity,
                     held: [...document.querySelectorAll('.arc [data-tab]')].every(b => getComputedStyle(b).visibility === 'hidden'),
                     launching: document.body.classList.contains('launching') }; }""")
        check("with every script blocked: the ring is there, a progress bar named Loading", s["role"] == "progressbar" and s["name"] == "Loading" and s["scripts"] == "undefinedundefined", s)
        check("...and it moves (the sweep turns by CSS alone), on the start circle, segments held back", s["moving"] and s["held"] and s["launching"], s)
        pl = page.evaluate(PLACE)
        check("...centred on the Mentor button", abs(pl["dx"]) < 1.5 and abs(pl["dy"]) < 1.5, pl)
        page.unroute("**/*.js*")

        print("\n--- 2. It follows real progress ---")
        ctx.add_init_script(RECORD)
        seed(page)
        held = held_load(page)
        pre = page.evaluate("() => [+document.querySelector('.mo-load').getAttribute('aria-valuenow'), window.minifolioRing.progress, typeof settings]")
        check("before app.js runs, the arrived script files have lit part of it (up to 60%)", pre[2] == "undefined" and 30 <= pre[0] <= 60, pre)
        before = page.evaluate(PLACE)
        release(page, held)
        page.wait_for_function("() => typeof settings === 'object'")
        after = page.evaluate(PLACE)
        check("the circle does not jump when the app starts", abs(before["cx"] - after["cx"]) < 3 and abs(before["cy"] - after["cy"]) < 3, (before, after))
        page.wait_for_function(GONE, timeout=10000)
        rec = page.evaluate("() => window.__ring")
        nows = [r["now"] for r in rec]
        check("it never goes backwards and reaches full", nows and nows == sorted(nows) and nows[-1] == 100, nows[-5:])
        ops = [r["op"] for r in rec if len(r["op"]) == 5]
        check("each segment goes from faint to full, and never fades back", ops and ops[-1] == [1, 1, 1, 1, 1]
              and all(all(b[i] >= a[i] - 1e-6 for i in range(5)) for a, b in zip(ops, ops[1:])), ops[-2:])
        check("clockwise from 12 o'clock: a segment only lights once the one before is full", all(all(o[i + 1] <= 0.2 + 1e-6 or o[i] >= 1 - 1e-6 for i in range(4)) for o in ops))
        check("then it goes: the segments and the Mentor button can be tapped", page.evaluate(
            "() => [...document.querySelectorAll('.arc [data-tab], #mentor-button')].every(b => getComputedStyle(b).visibility === 'visible' && getComputedStyle(b).pointerEvents !== 'none')"))

        print("\n--- 3. Magical and Grounded keep the three arcs ---")
        for look in ("magical", "grounded"):
            seed(page, {"mentorLook": look})
            page.goto(t.URL, wait_until="commit")
            page.wait_for_function("() => window.minifolioRing && window.minifolioRing.progress > 0 && document.querySelector('.mo-load')")
            m = page.evaluate("""() => { const s = document.querySelector('.mo-load'), d = e => getComputedStyle(e).display;
                const turn = s.querySelector('.mo-load-turn').getAnimations()[0];
                return [d(s.querySelector('.lr-three')), d(s.querySelector('.lr-five')), s.querySelectorAll('.lr-three .a').length,
                        parseFloat(s.querySelector('.lr-three .a0').getAttribute('stroke-dasharray')) > 0, !!turn && turn.effect.getComputedTiming().duration]; }""")
            check(f"{look}: three arcs (not the five segments), already filling, turning every 4 s", m[0] != "none" and m[1] == "none" and m[2] == 3 and m[3] and m[4] == 4000, m)
        ctx.close()

        print("\n--- 4. Reduced motion ---")
        rm = browser.new_context(viewport={"width": 390, "height": 844}, service_workers="block", reduced_motion="reduce")
        rm.add_init_script(RECORD)
        rp = rm.new_page()
        rp.on("pageerror", lambda x: errors.append(str(x)))
        seed(rp)
        held = held_load(rp)
        r = rp.evaluate("""() => ({ sweep: getComputedStyle(document.querySelector('.lr-sweep')).display,
            moving: document.querySelector('.tabs .arc').getAnimations({ subtree: true }).filter(a => a.playState === 'running').length,
            now: +document.querySelector('.mo-load').getAttribute('aria-valuenow') })""")
        check("no sweep and nothing turning, but it is already lit part way", r["sweep"] == "none" and r["moving"] == 0 and r["now"] > 0, r)
        release(rp, held)
        rp.wait_for_function(GONE, timeout=10000)
        ops = [x["op"] for x in rp.evaluate("() => window.__ring") if len(x["op"]) == 5]
        values = {round(v, 3) for o in ops for v in o}
        steps = sorted({tuple(o) for o in ops}, key=sum)
        check("the segments light in whole steps (only faint or full), more than one step, ending full",
              values <= {0.2, 1.0} and len(steps) >= 3 and ops[-1] == [1, 1, 1, 1, 1], (sorted(values), steps, ops[-1:]))
        check("then it goes and the circle can be used", rp.evaluate("() => document.body.classList.contains('launching') && !document.querySelector('.ring-hold')"))
        rm.close()

        print("\n--- 5. A section by its address, sizes, themes ---")
        ctx = browser.new_context(viewport={"width": 390, "height": 844}, service_workers="block")
        page = ctx.new_page()
        page.on("pageerror", lambda x: errors.append(str(x)))
        seed(page)
        page.goto(t.URL + "#units")
        page.wait_for_function("() => typeof settings === 'object'")
        check("opened on a section: the ring is gone at once and nothing is held back", page.evaluate(
            "() => !document.querySelector('.mo-load, .lr-sweep, .ring-hold') && !document.body.classList.contains('ring-loading') && !document.body.classList.contains('launching') && settings.tab === 'units'"))
        for (w, h, mode, theme) in ((360, 640, "dark", "parchment"), (320, 568, "light", "forge"), (1280, 800, "dark", "bench")):
            page.set_viewport_size({"width": w, "height": h})
            seed(page, {"theme": theme, "appearance": mode})
            held = held_load(page)
            a = page.evaluate(PLACE)
            release(page, held)
            page.wait_for_function("() => typeof settings === 'object'")
            b = page.evaluate(PLACE)
            check(f"{w}x{h} {mode} {theme}: the ring is centred on the button and in view before and after app.js, no sideways scroll",
                  all(abs(x["dx"]) < 1.5 and abs(x["dy"]) < 1.5 and x["inside"] and not x["sideways"] for x in (a, b)) and abs(a["cy"] - b["cy"]) < 8, (a, b))
        check("no page errors", not errors, errors[:3])
        browser.close()
    print(f"\n{sum(results)}/{len(results)} checks passed")
    return 0 if all(results) else 1

if __name__ == "__main__":
    sys.exit(main())
