"""v108 tests for Minifolio (chunk Mo4a: the loading ring on the start circle, fresh page load only).

New behaviour only:
1. Fresh load: a ring (role progressbar, name "Loading", aria-valuenow rising) sits around the Mentor button; its three arcs fill one after
   another; the four segments appear one by one and cannot be tapped until it is full; then the ring is gone and the circle works as before.
2. No ring when the app is opened on a section or on a warm return (title button). (LR1, v126: with reduced motion the ring now lights in steps
   and goes as soon as it is full.)
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
# one sample of the ring: aria, how lit each of its parts is (0 to 1 each), which segments are hidden / tappable
# v129 (MO6): the ring is the loading screen's icon ring now, with five segments lit by --l0 to --l4 (it was Mo4a's three arcs, lit by their dash length)
SAMPLE = """() => { const r = document.querySelector('.mo-load'); if (!r) return null;
    return { role: r.getAttribute('role'), name: r.getAttribute('aria-label'), now: +r.getAttribute('aria-valuenow'),
             arcs: [0, 1, 2, 3, 4].map(i => parseFloat(r.style.getPropertyValue('--l' + i) || '0')),
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
        # v129 (MO6, James): the loading ring is no longer drawn round the Mentor button inside the circle; it is the loading screen, the app icon's
        # ring in the middle of the screen (the circle is held back under it), and it uses the icon's own five colours while it loads
        check("it sits in the middle of the screen (the loading screen), not round the Mentor button", page.evaluate("""() => {
            const r = document.querySelector('.mo-load .mo6-ring').getBoundingClientRect();
            return Math.abs((r.left + r.width / 2) - innerWidth / 2) < 1 && Math.abs((r.top + r.height / 2) - innerHeight / 2) < 1; }"""))
        check("the five segments use round 7's Futuristic ring colours while it loads (U7: the theme's own, with fallbacks)", page.evaluate("""() => {
            const p = document.createElement('i'); document.body.appendChild(p);
            const want = ['var(--mentor-t3, var(--mentor-rim))', 'var(--mentor-t2, var(--mentor-b))', 'color-mix(in srgb, var(--mentor-t2, var(--mentor-b)) 50%, var(--mentor-dot, var(--mentor-core)))',
                          'var(--mentor-dot, var(--mentor-core))', 'var(--mentor-t1, var(--mentor-a))'].map(v => { p.style.color = v; return getComputedStyle(p).color; });
            p.remove();
            return [0, 1, 2, 3, 4].every(i => getComputedStyle(document.querySelector('.mo-load .ml-segs .ml-k' + i)).stroke === want[i]); }"""))
        check("it moves slowly (an endless 2.4 s sweep)", page.evaluate("""() => { const a = document.querySelector('.lr-sweep').getAnimations()[0];
            return a && a.effect.getComputedTiming().iterations === Infinity && a.effect.getComputedTiming().duration === 2400; }"""))
        fresh(page)
        samples = page.evaluate(WATCH)
        live = [x for x in samples if x]
        check("the ring was seen filling and then left (gone at the end)", len(live) > 5 and samples[-1] is None, len(samples))
        nows = [x[1]["now"] for x in live]
        check("aria-valuenow only ever rises", nows == sorted(nows) and nows[-1] >= 90, nows[-3:])
        last = [i for i, x in enumerate(live) if x[1]["arcs"][3] > 0.99]
        after = [i for i, x in enumerate(live) if x[1]["arcs"][4] > 0.01]
        check("the parts light one after another (the last starts only after the one before is full)", last and after and after[0] >= last[0] - 1, (last[:1], after[:1]))
        counts = [sum(1 for h in x[1]["hidden"] if not h) for x in live]
        check("segments appear one by one (visible count goes 0, then up by 1 at a time to 4)", counts[0] == 0 and counts[-1] == 4 and all(b - a <= 1 for a, b in zip(counts, counts[1:])), counts[::6])
        check("nothing can be tapped until the ring is full", all(not any(x[1]["tappable"]) for x in live[:-1] if x[1]["arcs"][4] < 0.99))
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
        # LR1 (v126): with reduced motion the ring now shows too (lit in whole steps, nothing moving), so the app does not look frozen; it goes as
        # soon as it is full (no minimum time), and then the circle and all segments show (was: no ring at all)
        rp.wait_for_function("() => !document.querySelector('.mo-load')", timeout=6000)
        check("reduced motion: once the ring is full it goes at once, and the circle and all segments show", rp.evaluate("() => !document.querySelector('.mo-load') && !document.querySelector('.ring-hold') && document.body.classList.contains('launching')"))
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
