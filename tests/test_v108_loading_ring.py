"""v108 tests for Minifolio (chunk Mo4a: the loading ring on the start circle, fresh page load only).

New behaviour only:
1. Fresh load: a ring (role progressbar, name "Loading", aria-valuenow rising) sits around the Mentor button; its three arcs fill one after
   another; the four segments appear one by one and cannot be tapped until it is full; then the ring is gone and the circle works as before.
2. No ring when the app is opened on a section, on a warm return (title button), or with reduced motion (the circle shows at once).
3. Leaving the circle while the ring runs removes it at once. Sizes, no sideways scroll, every theme in light and dark, a wide screen."""
import os, sys
from playwright.sync_api import sync_playwright

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import test_v31 as t
from launch_helpers import wait_settled, app_ready

load = t.load
results = []

def check(name, ok, detail=""):
    results.append(bool(ok))
    print(("PASS " if ok else "FAIL ") + name + ("" if ok else f"  -> {detail}"))

RING = "() => !!document.querySelector('.mo-load')"
# one sample of the ring: aria, arc fill (0 to 1 each), which segments are hidden / tappable
SAMPLE = """() => { const r = document.querySelector('.mo-load'); if (!r) return null;
    const L = 2 * Math.PI * 71 * 100 / 360;
    return { role: r.getAttribute('role'), name: r.getAttribute('aria-label'), now: +r.getAttribute('aria-valuenow'),
             arcs: [...r.querySelectorAll('.a')].map(c => parseFloat(c.getAttribute('stroke-dasharray')) / L),
             hidden: [...document.querySelectorAll('.arc [data-tab]')].map(b => getComputedStyle(b).visibility === 'hidden'),
             tappable: [...document.querySelectorAll('.arc [data-tab]')].map(b => getComputedStyle(b).pointerEvents !== 'none') }; }"""
# collect samples every frame from page load until the ring is gone
WATCH = """() => new Promise(done => { const out = [], t0 = performance.now();
    const f = () => { const s = (%s)(); out.push(s ? [Math.round(performance.now() - t0), s] : null);
        if (!s || performance.now() - t0 > 4000) done(out); else requestAnimationFrame(f); }; f(); })""" % SAMPLE

def fresh(page, **kw):
    """A fresh load that stays on the start circle and does not wait for the ring."""
    page.goto(t.URL)
    page.evaluate("""([b, s]) => { localStorage.clear(); localStorage.setItem('shades-of-grey-recipes', JSON.stringify(b));
        if (s) localStorage.setItem('shades-of-grey-settings', JSON.stringify(s)); }""", [t.book(), kw.get("settings")])
    page.reload()
    page.wait_for_function("() => typeof settings === 'object'")

def main():
    errors = []
    with sync_playwright() as p:
        browser = p.chromium.launch()
        ctx = browser.new_context(viewport={"width": 390, "height": 844}, service_workers="block")
        page = ctx.new_page()
        page.on("pageerror", lambda x: errors.append(str(x)))

        print("\n--- 1. Fresh load shows the ring ---")
        fresh(page)
        s = page.evaluate(SAMPLE)
        check("a ring is there, role progressbar, named Loading, 0 to 100", s and s["role"] == "progressbar" and s["name"] == "Loading", s)
        check("no words are drawn by the ring (no text inside it)", page.evaluate("() => document.querySelector('.mo-load').textContent.trim() === ''"))
        check("it sits inside the circle: between the Mentor button and the segments' inner edge (radius 71 of 62 to 80)", page.evaluate("""() => {
            const r = document.querySelector('.mo-load').getBoundingClientRect(), o = document.getElementById('mentor-button').getBoundingClientRect();
            return Math.abs((r.left + r.width / 2) - (o.left + o.width / 2)) < 1 && Math.abs((r.top + r.height / 2) - (o.top + o.height / 2)) < 1; }"""))
        check("the three arcs use the Mentor orb's own colours (the --mentor tokens)", page.evaluate("""() => {
            const cs = n => getComputedStyle(document.querySelector('.mo-load .' + n)).stroke, orb = n => getComputedStyle(document.querySelector('.' + n)).stroke;
            return cs('a0') === orb('orb-a') && cs('a1') === orb('orb-b') && cs('a2') === orb('orb-c'); }"""))
        check("it turns slowly (an endless 4 s animation)", page.evaluate("""() => { const a = document.querySelector('.mo-load-turn').getAnimations()[0];
            return a && a.effect.getComputedTiming().iterations === Infinity && a.effect.getComputedTiming().duration === 4000; }"""))
        fresh(page)
        samples = page.evaluate(WATCH)
        live = [x for x in samples if x]
        check("the ring was seen filling and then left (gone at the end)", len(live) > 5 and samples[-1] is None, len(samples))
        nows = [x[1]["now"] for x in live]
        check("aria-valuenow only ever rises", nows == sorted(nows) and nows[-1] >= 90, nows[-3:])
        first_full = [i for i, x in enumerate(live) if x[1]["arcs"][0] > 0.99]
        second_start = [i for i, x in enumerate(live) if x[1]["arcs"][1] > 0.01]
        check("arcs fill one after another (the second starts only after the first is full)", first_full and second_start and second_start[0] >= first_full[0] - 1, (first_full[:1], second_start[:1]))
        counts = [sum(1 for h in x[1]["hidden"] if not h) for x in live]
        check("segments appear one by one (visible count goes 0, then up by 1 at a time to 4)", counts[0] == 0 and counts[-1] == 4 and all(b - a <= 1 for a, b in zip(counts, counts[1:])), counts[::6])
        check("nothing can be tapped until the ring is full", all(not any(x[1]["tappable"]) for x in live[:-1] if x[1]["arcs"][2] < 0.99))
        check("shown for at least 1.2 s", live[-1][0] >= 1100, live[-1][0])
        page.wait_for_timeout(900)
        check("ring finished and removed: no ring in the page, circle still showing", page.evaluate("() => !document.querySelector('.mo-load') && document.body.classList.contains('launching') && !document.body.classList.contains('ring-loading')"))
        check("all four segments and the Mentor button are there, visible and tappable", page.evaluate("""() => [...document.querySelectorAll('.arc [data-tab], #mentor-button')]
            .map(b => getComputedStyle(b).visibility === 'visible' && getComputedStyle(b).pointerEvents !== 'none').filter(Boolean).length === 5"""))
        page.click('.tabs button[data-tab="units"]')
        wait_settled(page)
        check("tapping a segment opens its section as before", page.evaluate("() => settings.tab === 'units' && !document.body.classList.contains('launching')"))

        print("\n--- 2. No ring on a warm return, a linked section or with reduced motion ---")
        page.click("#home-button")
        wait_settled(page)
        check("title button back to the circle: no ring, segments showing", page.evaluate("() => !document.querySelector('.mo-load') && document.body.classList.contains('launching') && !document.querySelector('.ring-hold')"))
        page.goto(t.URL + "#recipes")
        page.reload()
        app_ready(page)
        check("opened on a section by its address: no ring", page.evaluate("() => !document.querySelector('.mo-load') && !document.body.classList.contains('launching')"))
        ctx2 = browser.new_context(viewport={"width": 390, "height": 844}, service_workers="block", reduced_motion="reduce")
        rp = ctx2.new_page()
        fresh(rp)
        check("reduced motion: no ring, the circle and all segments show at once", rp.evaluate("() => !document.querySelector('.mo-load') && !document.querySelector('.ring-hold') && document.body.classList.contains('launching')"))
        ctx2.close()

        print("\n--- 3. Leaving while it runs ends it at once ---")
        fresh(page)
        r = page.evaluate("() => { const had = !!document.querySelector('.mo-load'); document.querySelector('.tabs button[data-tab=\"dashboard\"]').click();"
                          " return [had, !!document.querySelector('.mo-load'), !document.body.classList.contains('ring-loading'), !document.querySelector('.ring-hold')]; }")
        check("a ring was running, a tap ends it: no ring, nothing hidden or locked left behind", r == [True, False, True, True], r)

        print("\n--- 4. Sizes, themes, light and dark ---")
        themes = page.evaluate("() => Object.keys(THEMES)")
        for w, h, scheme in ((390, 844, "dark"), (360, 740, "light"), (1280, 800, "dark"), (1920, 1000, "light")):
            page.set_viewport_size({"width": w, "height": h})
            page.emulate_media(color_scheme=scheme)
            for th in (themes if w < 400 else themes[:1]):
                fresh(page, settings={"theme": th})
                mid = page.evaluate(SAMPLE)
                scroll = page.evaluate("() => document.documentElement.scrollWidth > document.documentElement.clientWidth")
                ok_sizes = page.evaluate("""() => [...document.querySelectorAll('.arc [data-tab], #mentor-button')].every(b => {
                    const r = b.getBoundingClientRect(); return r.width >= 44 && r.height >= 44; })""")
                ring_in = page.evaluate("() => { const r = document.querySelector('.mo-load'); if (!r) return true; const b = r.getBoundingClientRect(); return b.left >= 0 && b.right <= innerWidth && b.top >= 0; }")
                check(f"{w}x{h} {scheme} {th}: ring in view, no sideways scroll, tap targets 44 px or more", mid and not scroll and ok_sizes and ring_in, (mid, scroll, ok_sizes, ring_in))
        page.wait_for_function("() => !document.querySelector('.mo-load')", timeout=5000)
        check("at the end the wide screen's circle is whole (four segments tappable)", page.evaluate("() => [...document.querySelectorAll('.arc [data-tab]')].every(b => getComputedStyle(b).pointerEvents !== 'none')"))
        check("no page errors", not errors, errors)
        browser.close()
    print(f"\n{sum(results)}/{len(results)} checks passed")
    sys.exit(0 if all(results) else 1)

main()
