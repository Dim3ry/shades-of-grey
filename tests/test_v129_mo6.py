"""MO6 tests for Minifolio (James, 3 Nov): no flashes in the start circle and the bar, the app icon's ring is the loading screen, and the lit
section's colour slides along the bar. New behaviour only, and no timings (every check holds on a slow machine too):
1. The first paint, before any script runs, is the loading screen: the page colour with the app icon's ring and centre dot in the middle, the size
   and colours of the phone's own launch screen (installed, the screen is the manifest's background colour).
2. Its five segments light clockwise from 12 o'clock and never go backwards; then the ring lands exactly on the round Ask Mentor button's drawing
   while the four segments grow out one by one, clockwise from the top left.
3. No colour, background, shadow, glow or visibility on the circle, the bar, the travelling copies, the Mentor button, the words or the ring changes
   by more than a small step between two frames during each move (computed styles sampled every frame; a longer frame allows a bigger step).
4. The hand-over from the travelling copies to the real bar (and back) is the same picture: same colours, same places.
5. The lit colour slides from the old piece to the new one through the pieces between and ends exactly on the new piece; reduced motion
   crossfades it. Reduced motion: no movement on the loading screen either.
Run all tests with `python3 tests/run_all.py`, or serve the repo folder and run this file on its own."""
import json, os, re, sys
from playwright.sync_api import sync_playwright

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import test_v31 as t
from launch_helpers import wait_settled

results = []

def check(name, ok, detail=""):
    results.append(bool(ok))
    print(("PASS " if ok else "FAIL ") + name + ("" if ok else f"  -> {str(detail)[:600]}"))

# the loading ring's five colours, clockwise from 12 o'clock: round 7's Futuristic ring (U7, the theme's colours; with fallbacks before U7)
RING = """() => { const p = document.createElement('i'); document.body.appendChild(p); const want = ['var(--mentor-t3, var(--mentor-rim))', 'var(--mentor-t2, var(--mentor-b))', 'color-mix(in srgb, var(--mentor-t2, var(--mentor-b)) 50%, var(--mentor-dot, var(--mentor-core)))', 'var(--mentor-dot, var(--mentor-core))', 'var(--mentor-t1, var(--mentor-a))'].map(v => { p.style.color = v; return getComputedStyle(p).color; }); p.remove(); return want; }"""

# Every frame: what is on screen, channel by channel. A segment is its travelling copy while one is drawn, else the real one; the bar's fade and the
# circle's glow are the travel's layers while it runs, else the real bar's (the bar outside the start page, the glow on it).
SAMPLER = r"""(() => { const S = window.__mo6t = { frames: [], on: false };
  const eff = (el) => { if (!el || !el.isConnected) return 0; if (getComputedStyle(el).visibility === 'hidden') return 0; let e = el, o = 1;
    while (e && e.nodeType === 1) { const c = getComputedStyle(e); if (c.display === 'none') return 0; o *= parseFloat(c.opacity); e = e.parentElement; } return Math.round(o * 1000) / 1000; };
  const rgb = (s) => { let m = /rgba?\(([^)]*)\)/.exec(s || ''); if (m) { const v = m[1].split(/[\s,/]+/).filter(Boolean).map(Number); return [v[0], v[1], v[2], v.length > 3 ? v[3] : 1]; }
    m = /color\(srgb ([^)]*)\)/.exec(s || ''); if (m) { const v = m[1].split(/[\s/]+/).filter(Boolean).map(Number); return [v[0] * 255, v[1] * 255, v[2] * 255, v.length > 3 ? v[3] : 1]; } return null; };
  const ghost = (text) => [...document.querySelectorAll('.mo6-ghost')].filter(g => g.textContent === text).reduce((a, g) => a + eff(g), 0);
  function snap() {
    const f = { t: performance.now() }, body = document.body;
    if (!body) return f;
    const travelling = body.classList.contains('mo-travelling'), launching = body.classList.contains('launching');
    const load = document.querySelector('.mo6-load'), bg = load && load.querySelector('.mo6-bg'), ring = load && load.querySelector('.mo6-ring');
    f.screen = bg ? eff(bg) : 0;
    if (ring) { ring.querySelectorAll('.ml-segs circle').forEach((c, i) => { f['ring ' + i] = rgb(getComputedStyle(c).stroke); });
      f['ring dot'] = rgb(getComputedStyle(ring.querySelector('.ml-dot')).fill);
      const r = ring.getBoundingClientRect(); f.ringBox = [r.left + r.width / 2, r.top + r.height / 2, r.width]; }
    const real = [...document.querySelectorAll('nav.tabs .arc [data-tab]')], copies = [...document.querySelectorAll('.mo-tr .w')];
    real.forEach((b, i) => { const c = copies[i], k = b.dataset.tab;
      f['seen ' + k] = c ? eff(c) : eff(b);
      f['words ' + k] = rgb(getComputedStyle(c ? c.querySelector('.c') : b).color);
      if (c) f['piece ' + k] = rgb(getComputedStyle(c).backgroundColor);
      else if (!b.style.backgroundImage) f['piece ' + k] = rgb(getComputedStyle(b).backgroundColor); });
    const orb = document.getElementById('mentor-button');
    if (!orb || !document.getElementById('version-tag')) return f;   // the page is still being read
    const oc = getComputedStyle(orb), osvg = orb.querySelector('svg');
    const scale = orb.offsetWidth ? orb.getBoundingClientRect().width / orb.offsetWidth : 1;
    const sh = /^(rgba?\([^)]*\)|color\([^)]*\))\s+(-?[\d.]+)px\s+(-?[\d.]+)px\s+([\d.]+)px/.exec(oc.boxShadow);
    f['button seen'] = eff(orb); f['button'] = rgb(oc.backgroundColor);
    if (sh) { f['button glow'] = parseFloat(sh[4]) * scale; f['button glow colour'] = rgb(sh[1]); }
    f['drawing'] = Math.min(1, eff(osvg) + (ring ? eff(ring) : 0));
    const fadeL = document.querySelector('html > .tabs.mo6-fade'), glowL = document.querySelector('html > .tabs.mo6-glow');
    f['bar fade'] = (fadeL ? eff(fadeL) : 0) + (!travelling && !launching ? 1 : 0);
    if (!load) f['circle glow'] = (glowL ? eff(glowL) : 0) + (!travelling && launching ? 1 : 0);
    const line = document.getElementById('start-line'), ver = document.getElementById('version-tag');
    f['start line'] = eff(line) + ghost(line.textContent); f['version'] = eff(ver) + ghost(ver.textContent);
    f['page'] = Math.max(0, ...[...document.querySelectorAll('main > section')].map(eff));
    f['back arrow'] = eff(document.getElementById('back-menu'));
    return f; }
  S.start = () => { S.frames = []; S.on = true; const loop = () => { if (!S.on) return; S.frames.push(snap()); requestAnimationFrame(loop); }; loop(); };
  S.stop = () => { S.on = false; return S.frames; };
})();"""

def cdiff(a, b):
    return max(abs(a[i] * a[3] - b[i] * b[3]) for i in range(3)) + 255 * abs(a[3] - b[3]) * 0.5

def jumps(frames):
    """Each channel, frame to frame: a step is too big when it is more than a small step and more than a smooth blend could make in that time
    (a whole colour swing in 110 ms, a whole fade in 100 ms, a glow of 28 px in 110 ms). While the loading screen covers everything, only it counts."""
    bad = []
    for a, b in zip(frames, frames[1:]):
        dt = max(1.0, b["t"] - a["t"])
        covered = a.get("screen", 0) >= 0.99 and b.get("screen", 0) >= 0.99
        for k in set(a) & set(b):
            if k in ("t", "ringBox") or (covered and not (k.startswith("ring") or k == "screen")):
                continue
            x, y = a[k], b[k]
            if x is None or y is None:
                continue
            if isinstance(x, list):
                seen_k = "seen " + k.split(" ", 1)[1] if k.split(" ")[0] in ("words", "piece") else None
                if seen_k and min(a.get(seen_k, 1), b.get(seen_k, 1)) < 0.05:
                    continue
                d, limit = cdiff(x, y), max(48, 255 * dt / 110)
            elif k == "button glow":
                d, limit = abs(x - y), max(8, 28 * dt / 110)
            else:
                d, limit = abs(x - y), max(0.3, dt / 100)
            if d > limit:
                bad.append((round(b["t"]), k, x, y, round(dt)))
    return bad

def seed(page, settings=None, units=None):
    page.goto(t.BASE + "manifest.json")
    page.evaluate("""([s, u]) => { localStorage.clear(); localStorage.setItem('shades-of-grey-recipes', JSON.stringify({ parts: [], techniques: [], paints: [], recipes: [], schemes: [], shorthand: {}, v15: true }));
        if (s) localStorage.setItem('shades-of-grey-settings', JSON.stringify(s)); if (u) localStorage.setItem('mini-tracker-models', JSON.stringify(u)); }""", [settings, units])

def sample(page, action, until, timeout=15000):
    page.evaluate("() => window.__mo6t.start()")
    page.evaluate(action)
    page.wait_for_function(until, timeout=timeout)
    page.evaluate("() => new Promise(r => requestAnimationFrame(() => requestAnimationFrame(r)))")
    return page.evaluate("() => window.__mo6t.stop()")

SETTLED = """() => !document.querySelector('.mo-tr, .mo6-load, .mo6-ghost, html > .tabs') && !document.body.classList.contains('mo-travelling')
    && !document.body.classList.contains('ring-loading') && document.querySelector('nav.tabs').getAnimations({ subtree: true }).length === 0
    && [...document.querySelectorAll('main > section')].every(s => s.getAnimations().length === 0)"""
# freeze every move a hair before its end (the page's own fades end long before), for the hand-over frame
FREEZE = """() => { for (const a of document.getAnimations()) { const tm = a.effect.getComputedTiming(); if (tm.iterations === Infinity) continue;
    const el = a.effect.target; if (!(el && el.closest && el.closest('.tabs, .mo-tr, #mentor-button'))) { a.finish(); continue; }
    a.pause(); a.currentTime = Math.max(0, tm.endTime - 0.05); } }"""
RAF2 = "() => new Promise(r => requestAnimationFrame(() => requestAnimationFrame(r)))"
# each segment as drawn: its colours, and where its icon and label are (centres, page pixels); a travelling copy when one is drawn
LOOK = r"""() => { const copies = [...document.querySelectorAll('.mo-tr .w')];
  return [...document.querySelectorAll('nav.tabs .arc [data-tab]')].map((b, i) => { const c = copies[i];
    const box = (el) => { const r = el.getBoundingClientRect(); return [Math.round((r.left + r.width / 2) * 100) / 100, Math.round((r.top + r.height / 2) * 100) / 100]; };
    let label;
    if (c) { const ts = [...c.querySelectorAll('.t')].filter(s => getComputedStyle(s).visibility !== 'hidden' && parseFloat(getComputedStyle(s).opacity) > 0.5); label = box(ts[0]); }
    else { const r = document.createRange(); r.selectNodeContents([...b.childNodes].find(n => n.nodeType === 3 && n.textContent.trim())); const q = r.getBoundingClientRect(); label = [Math.round((q.left + q.width / 2) * 100) / 100, Math.round((q.top + q.height / 2) * 100) / 100]; }
    const cs = getComputedStyle(c || b), ccs = getComputedStyle(c ? c.querySelector('.c') : b);
    return { tab: b.dataset.tab, bg: cs.backgroundColor, color: ccs.color, icon: box((c || b).querySelector('.icon')), label }; }); }"""

def col(s):
    m = re.match(r"rgba?\(([^)]*)\)", s or "")
    if m:
        v = [float(x) for x in re.split(r"[\s,/]+", m.group(1).strip()) if x]
        return v[:3] + [v[3] if len(v) > 3 else 1.0]
    m = re.match(r"color\(srgb ([^)]*)\)", s or "")
    v = [float(x) for x in re.split(r"[\s/]+", m.group(1).strip()) if x] if m else [0, 0, 0, 0]
    return [v[0] * 255, v[1] * 255, v[2] * 255, v[3] if len(v) > 3 else 1.0]

def same_look(a, b):
    far = []
    for x, y in zip(a, b):
        d = max(abs(x["icon"][0] - y["icon"][0]), abs(x["icon"][1] - y["icon"][1]), abs(x["label"][0] - y["label"][0]), abs(x["label"][1] - y["label"][1]))
        if d > 0.5 or cdiff(col(x["bg"]), col(y["bg"])) > 1.5 or cdiff(col(x["color"]), col(y["color"])) > 1.5:
            far.append((x["tab"], round(d, 2), x["bg"], y["bg"], x["color"], y["color"]))
    return far

def main():
    html = t.read("index.html")
    manifest = json.loads(t.read("manifest.json"))
    errors = []
    with sync_playwright() as p:
        browser = p.chromium.launch()
        ctx = browser.new_context(viewport={"width": 390, "height": 844}, service_workers="block")
        ctx.add_init_script(SAMPLER)
        page = ctx.new_page()
        page.on("pageerror", lambda x: errors.append(str(x) + " @ " + str(getattr(x, "stack", ""))[:400]))

        print("--- 1. The first paint is the icon ring on the page colour ---")
        body = html[html.find("\n<body") + 1:]
        check("index.html draws the loading screen first in the page, before any script", 0 < body.find('class="mo-load mo6-load"') < body.find("<script") and body.find('class="mo-load mo6-load"') < body.find('<nav class="tabs"'))
        check("installed, the screen is the manifest's background colour (the phone's own launch screen)", manifest.get("background_color") == "#0b1220"
              and re.search(r"@media \(display-mode: standalone\) \{\s*\.mo6-bg \{ background-color: #0b1220; \}", html) is not None)
        seed(page)
        page.route("**/*.js*", lambda r: r.abort())
        page.goto(t.URL, wait_until="domcontentloaded")
        s = page.evaluate("""() => { const load = document.querySelector('.mo-load'), ring = load.querySelector('.mo6-ring'), r = ring.getBoundingClientRect(), b = load.getBoundingClientRect();
            const segs = [...ring.querySelectorAll('.ml-segs circle')].map(c => getComputedStyle(c).stroke); const p = document.createElement('i'); document.body.appendChild(p); const want = ['var(--mentor-t3, var(--mentor-rim))', 'var(--mentor-t2, var(--mentor-b))', 'color-mix(in srgb, var(--mentor-t2, var(--mentor-b)) 50%, var(--mentor-dot, var(--mentor-core)))', 'var(--mentor-dot, var(--mentor-core))', 'var(--mentor-t1, var(--mentor-a))'].map(v => { p.style.color = v; return getComputedStyle(p).color; }); p.remove();
            const k4 = ring.querySelector('.ml-segs .ml-k4'), w = parseFloat(getComputedStyle(k4).strokeWidth), rad = parseFloat(getComputedStyle(k4).r);
            return { scripts: typeof settings + typeof MENTOR_LOOKS, cover: [b.left, b.top, b.width, b.height], page: getComputedStyle(load.querySelector('.mo6-bg')).backgroundColor,
                     body: getComputedStyle(document.body).backgroundColor, centre: [r.left + r.width / 2 - innerWidth / 2, r.top + r.height / 2 - innerHeight / 2],
                     across: (rad + w / 2) * 2 * r.width / 166.67, segs, dot: getComputedStyle(ring.querySelector('.ml-dot')).fill,
                     z: +getComputedStyle(load).zIndex, want, dotWant: (() => { const q = document.createElement('i'); document.body.appendChild(q); q.style.color = 'var(--mentor-dot, var(--mentor-core))'; const v = getComputedStyle(q).color; q.remove(); return v; })(), held: [...document.querySelectorAll('.arc [data-tab]')].every(x => getComputedStyle(x).visibility === 'hidden') }; }""")
        check("with every script blocked: it covers the whole screen in the page colour", s["scripts"] == "undefinedundefined" and s["cover"] == [0, 0, 390, 844] and s["page"] == s["body"] and s["z"] > 12, s)
        check("the ring is in the middle of the screen, 132 px across like the phone's launch screen", abs(s["centre"][0]) < 0.5 and abs(s["centre"][1]) < 0.5 and abs(s["across"] - 132.2) < 1.5, s)
        check("its five segments are round 7's ring colours and its centre dot the theme's dot", s["segs"] == s["want"] and s["dot"] == s["dotWant"] and s["dot"] == "rgb(125, 211, 252)", s)
        check("the start circle is held back under it", s["held"])
        page.unroute("**/*.js*")

        print("\n--- 2. It lights clockwise, never backwards, then lands on the Mentor button ---")
        ctx.add_init_script("""(() => { window.__lit = []; requestAnimationFrame(() => { if (window.__mo6t) window.__mo6t.start(); });
            new MutationObserver(() => { const s = document.querySelector('.mo-load'); if (s) window.__lit.push([0, 1, 2, 3, 4].map(i => parseFloat(s.style.getPropertyValue('--l' + i) || '0'))); })
              .observe(document, { attributes: true, subtree: true, attributeFilter: ['style'] }); })();""")
        seed(page)
        page.goto(t.URL)
        page.wait_for_function(SETTLED, timeout=15000)
        page.evaluate(RAF2)
        start = page.evaluate("() => window.__mo6t.stop()")
        lit = page.evaluate("() => window.__lit")
        check("the five segments only ever light up, ending all lit", lit and lit[-1] == [1, 1, 1, 1, 1] and all(all(b[i] >= a[i] - 1e-6 for i in range(5)) for a, b in zip(lit, lit[1:])), lit[-3:])
        check("clockwise from 12 o'clock: a segment lights only once the one before is full", all(all(o[i + 1] <= 1e-6 or o[i] >= 1 - 1e-6 for i in range(4)) for o in lit))
        boxes = [f for f in start if "ringBox" in f]
        target = page.evaluate("() => { const r = document.querySelector('#mentor-button svg').getBoundingClientRect(); return [r.left + r.width / 2, r.top + r.height / 2, r.width]; }")
        end = boxes[-1]["ringBox"] if boxes else None
        check("the ring moves from the middle of the screen and lands exactly on the button's drawing", boxes and abs(boxes[0]["ringBox"][1] - 422) < 2 and end
              and abs(end[0] - target[0]) < 1 and abs(end[1] - target[1]) < 1 and abs(end[2] - target[2]) < 1, (boxes[:1], end, target))
        ring_end = [boxes[-1]["ring " + str(i)] for i in range(5)] if boxes else []
        orb_cols = page.evaluate("() => [...document.querySelectorAll('#mentor-button .ml-segs circle')].map(c => getComputedStyle(c).stroke)")
        check("...by then in the button drawing's own colours", boxes and len(orb_cols) == 5 and all(cdiff(a, col(b)) <= 1.5 for a, b in zip(ring_end, orb_cols)), (ring_end, orb_cols))
        order = []
        for f in start:
            for k in ("units", "recipes", "guides", "dashboard"):
                if f.get("seen " + k, 0) > 0 and k not in order:
                    order.append(k)
        check("the four segments grow out one after another, clockwise from the top left", order == ["units", "recipes", "guides", "dashboard"], order)
        bad = jumps(start)
        check("start-up: no colour, glow or visibility changes in one frame (screen, ring, circle, button, words)", not bad, bad[:6])

        print("\n--- 3. The travel to the bar and back, the lit piece, the Mentor window ---")
        page.evaluate("() => document.querySelector('.tabs button[data-tab=units]').click()")
        page.evaluate(RAF2)
        page.evaluate(FREEZE)
        page.evaluate(RAF2)
        copies = page.evaluate(LOOK)
        page.evaluate("() => document.getAnimations().forEach(a => { if (a.effect.getComputedTiming().iterations !== Infinity) a.finish(); })")
        page.wait_for_function(SETTLED, timeout=10000)
        real = page.evaluate(LOOK)
        check("hand-over to the bar: the last frame of the copies is the real bar (colours, icon and label within half a pixel)", not same_look(copies, real), same_look(copies, real))
        page.evaluate("() => document.getElementById('home-button').click()")
        page.wait_for_function(SETTLED, timeout=10000)
        frames = sample(page, "() => document.querySelector('.tabs button[data-tab=units]').click()", SETTLED)
        bad = jumps(frames)
        check("circle to bar: no colour, glow or visibility changes in one frame", not bad, bad[:6])
        check("...the travel ran (copies drawn) and the bar's fade and the circle's glow crossfaded under them", any("seen units" in f and 0 < f.get("bar fade", 0) < 1 for f in frames)
              and page.evaluate("() => !document.querySelector('html > .tabs')"))

        # the lit colour slides from Models to Tools over Painting, and lands on Tools
        page.evaluate("""() => { window.__fill = []; const segs = [...document.querySelectorAll('nav.tabs .arc [data-tab]')];
            const rec = () => { const row = {}; segs.forEach(b => { const g = b.style.backgroundImage, m = /^conic-gradient\\((?:from (-?[\\d.]+)deg )?.*rgba\\(0, 0, 0, 0\\) (-?[\\d.]+)deg\\)$/.exec(g);
                if (m) row[b.dataset.tab] = [parseFloat(m[1] || "0"), parseFloat(m[2])]; }); if (Object.keys(row).length) window.__fill.push(row); if (window.__fillOn) requestAnimationFrame(rec); };
            window.__fillOn = true; requestAnimationFrame(rec); }""")
        frames = sample(page, "() => document.querySelector('.tabs button[data-tab=guides]').click()", SETTLED)
        fill = page.evaluate("() => { window.__fillOn = false; return window.__fill; }")
        froms = [min(v[0] for v in row.values()) for row in fill]
        covered = {k for row in fill for k in row}
        check("switching Models to Tools: one fill slides along the bar, over Painting on the way", len(fill) >= 3 and "recipes" in covered and froms == sorted(froms), (len(fill), covered, froms[:8]))
        check("...and ends exactly on Tools: the real lit look, no fill left drawn", page.evaluate("""() => { const b = [...document.querySelectorAll('nav.tabs .arc [data-tab]')];
            const lit = b.find(x => x.getAttribute('aria-current') === 'page'), plain = b.find(x => x !== lit);
            return lit.dataset.tab === 'guides' && b.every(x => !x.getAttribute('style')) && getComputedStyle(lit).backgroundColor !== getComputedStyle(plain).backgroundColor
                && getComputedStyle(lit).fontWeight === '700'; }"""))
        bad = jumps(frames)
        check("...the words and icons crossfade as it passes: no colour changes in one frame", not bad, bad[:6])
        check("the fill is drawn inside the four pieces only (never over the Mentor button)", page.evaluate("""() => { const b = document.querySelector('nav.tabs .arc [data-tab=dashboard]');
            b.click(); const inside = [...document.querySelectorAll('[style*="conic-gradient"]')].every(e => e.matches('nav.tabs .arc > [data-tab]'));
            return inside && document.querySelectorAll('[style*="conic-gradient"]').length > 0; }"""))
        page.wait_for_function(SETTLED, timeout=10000)
        frames = sample(page, "() => document.getElementById('mentor-button').click()", "() => document.body.classList.contains('mentor-open') && getComputedStyle(document.getElementById('back-menu')).visibility === 'hidden'")
        check("opening the Mentor window: the back arrow fades out (it vanished in one frame)", not [b for b in jumps(frames) if b[1] == "back arrow"], jumps(frames)[:4])
        page.keyboard.press("Escape")
        page.wait_for_function("() => !document.body.classList.contains('mentor-open')", timeout=5000)
        page.wait_for_function(SETTLED, timeout=10000)
        page.wait_for_timeout(300)

        frames = sample(page, "() => document.getElementById('back-menu').click()", "() => document.body.classList.contains('launching') && " + SETTLED[6:])
        bad = jumps(frames)
        check("bar to circle: no colour, glow or visibility changes in one frame (the page fades out, the words cross)", not bad, bad[:6])
        check("...the page faded out over the wait instead of going at once", any(0.1 < f.get("page", 0) < 0.9 for f in frames))
        page.evaluate("() => document.querySelector('.tabs button[data-tab=recipes]').click()")
        page.wait_for_function(SETTLED, timeout=10000)
        page.evaluate("() => document.getElementById('back-menu').click()")
        page.evaluate(RAF2)
        page.evaluate(FREEZE)
        page.evaluate(RAF2)
        copies = page.evaluate(LOOK)
        page.evaluate("() => document.getAnimations().forEach(a => { if (a.effect.getComputedTiming().iterations !== Infinity) a.finish(); })")
        page.wait_for_function(SETTLED, timeout=10000)
        real = page.evaluate(LOOK)
        check("hand-over to the circle: the last frame of the copies is the real circle", not same_look(copies, real), same_look(copies, real))
        check("nothing is left behind (no layers, copies or inline looks)", page.evaluate("""() => !document.querySelector('html > .tabs, .mo-tr, .mo6-ghost')
            && !document.getElementById('mentor-button').getAttribute('style') && [...document.querySelectorAll('main > section')].every(s => !s.inert && !s.style.position)"""))
        ctx.close()

        print("\n--- 4. Reduced motion ---")
        rm = browser.new_context(viewport={"width": 390, "height": 844}, service_workers="block", reduced_motion="reduce")
        rm.add_init_script("""(() => { window.__moved = []; const look = () => { for (const a of document.getAnimations()) { const k = a.effect.getKeyframes ? a.effect.getKeyframes() : [];
            if (k.some(f => f.transform && f.transform !== 'none')) window.__moved.push(a.effect.target && (a.effect.target.className.baseVal !== undefined ? a.effect.target.className.baseVal : a.effect.target.className)); }
            if (!window.__stop) requestAnimationFrame(look); }; requestAnimationFrame(look); })();""")
        rp = rm.new_page()
        rp.on("pageerror", lambda x: errors.append(str(x) + " @ " + str(getattr(x, "stack", ""))[:400]))
        seed(rp)
        rp.goto(t.URL)
        sweep = rp.evaluate("() => { const s = document.querySelector('.lr-sweep'); return s ? getComputedStyle(s).display : 'gone'; }")
        rp.wait_for_function(SETTLED, timeout=15000)
        moved = rp.evaluate("() => { window.__stop = true; return window.__moved; }")
        check("the loading screen: no sheen and nothing moves; the circle fades in under it", sweep in ("none", "gone") and not moved, (sweep, moved[:4]))
        rp.evaluate("() => document.querySelector('.tabs button[data-tab=units]').click()")
        rp.wait_for_function(SETTLED, timeout=10000)
        rp.evaluate("""() => { window.__x = []; const b = [...document.querySelectorAll('nav.tabs .arc [data-tab]')];
            const rec = () => { const g = b.map(x => /conic/.test(x.style.backgroundImage) ? x.style.backgroundImage : ''); window.__x.push(g); if (window.__x.length < 400 && b.some(x => x.style.backgroundImage)) requestAnimationFrame(rec); };
            document.querySelector('.tabs button[data-tab=guides]').click(); rec(); }""")
        rp.wait_for_function(SETTLED, timeout=10000)
        x = rp.evaluate("() => window.__x")
        drawn = [i for row in x for i, v in enumerate(row) if v]
        check("switching sections: the lit colour crossfades (only the old and the new piece, nothing slides over Painting)", drawn and set(drawn) <= {1, 3}
              and rp.evaluate("() => document.querySelector('nav.tabs .arc [aria-current=page]').dataset.tab === 'guides'"), (set(drawn), len(x)))
        rm.close()

        print("\n--- 5. Another look, sizes ---")
        ctx = browser.new_context(viewport={"width": 390, "height": 844}, service_workers="block")
        page = ctx.new_page()
        page.on("pageerror", lambda x: errors.append(str(x) + " @ " + str(getattr(x, "stack", ""))[:400]))
        # (one load per size, the first with the Magical look, so the file stays quick)
        for (w, h, s) in ((320, 568, {"mentorLook": "magical", "theme": "forge", "appearance": "light"}), (1280, 800, {"theme": "bench"})):
            page.set_viewport_size({"width": w, "height": h})
            seed(page, s)
            page.goto(t.URL, wait_until="commit")
            page.wait_for_selector(".mo6-load .mo6-ring", state="attached")
            page.wait_for_function("() => !!document.body")
            r = page.evaluate("""() => { const r = document.querySelector('.mo6-ring').getBoundingClientRect();
                return [Math.abs(r.left + r.width / 2 - innerWidth / 2) < 0.5 && Math.abs(r.top + r.height / 2 - innerHeight / 2) < 0.5, r.width,
                        [...document.querySelectorAll('.mo6-load .ml-segs circle')].map(c => getComputedStyle(c).stroke)]; }""")
            ring_want = page.evaluate(RING)
            page.wait_for_function(SETTLED, timeout=15000)
            fit = page.evaluate("""() => { const o = document.getElementById('mentor-button').getBoundingClientRect(); return o.top >= 0 && o.bottom <= innerHeight && o.left >= 0 && o.right <= innerWidth
                && document.documentElement.scrollWidth <= document.documentElement.clientWidth && (innerWidth >= 900 || [...document.querySelectorAll('main > section')].every(s => s.offsetParent === null)); }""")
            check(f"{w}x{h}: the ring is in the middle of the screen at the same size, then the start circle shows whole, no sideways scroll (and on a phone nothing behind it)", r[0] and abs(r[1] - 157.5) < 0.5 and fit, (r[:2], fit))
            if s.get("mentorLook"):
                check("Magical: the loading screen is the same icon ring, and it hands over to the Magical drawing in the button",
                      r[2] == ring_want and page.evaluate("() => document.querySelector('#mentor-button svg').classList.contains('ml-magical') && getComputedStyle(document.querySelector('#mentor-button svg')).visibility === 'visible'"), r[2])
        check("no page errors", not errors, errors[:3])
        browser.close()
    print(f"\n{sum(results)}/{len(results)} checks passed")
    return 0 if all(results) else 1

if __name__ == "__main__":
    sys.exit(main())
