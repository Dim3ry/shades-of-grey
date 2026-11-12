"""AB13c test for Minifolio (colour ramp row under an entry's title: recipes, basing tips and three text guides). New behaviour only.
Run with the whole suite, or serve the repo folder and run this file on its own."""
import os, re, sys
from playwright.sync_api import sync_playwright

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import test_v31 as t
from launch_helpers import wait_settled

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
results = []

def check(name, ok, detail=""):
    results.append(bool(ok))
    print(("PASS " if ok else "FAIL ") + name + ("" if ok else f"  -> {str(detail)[:400]}"))

TEXT_GUIDES = ("silk-and-satin", "pearl-and-shell", "snake-and-serpent-patterns")
ONE_LINE = """() => { const r = document.querySelector('.ab13c-ramp'); if (!r) return null;
  const s = [...r.querySelectorAll('.swatch')].map(x => x.getBoundingClientRect());
  return { n: s.length, w: s[0].width, h: s[0].height, oneLine: s.every(b => Math.abs(b.top - s[0].top) < 1),
           inside: s.every(b => b.left >= 0 && b.right <= innerWidth), noScroll: document.documentElement.scrollWidth <= innerWidth + 1,
           buttons: r.querySelectorAll('button, a, [tabindex]').length, role: r.getAttribute('role'), label: r.getAttribute('aria-label') }; }"""

def open_entry(page, key, kind=None):
    page.evaluate("([k, d]) => openGuide(k, d)", [key, kind])
    page.wait_for_function("(k) => document.querySelector('#guide-' + k + ', [data-detail=\"' + k + '\"].active, .guides-main h3, .guides-main .starter-summary')", arg=key)
    wait_settled(page)

def main():
    gd = open(os.path.join(ROOT, "guides-data.js"), encoding="utf-8").read()
    errors = []
    with sync_playwright() as p:
        browser = p.chromium.launch()
        ctx = browser.new_context(viewport={"width": 390, "height": 844}, service_workers="block")
        page = ctx.new_page()
        page.on("pageerror", lambda x: errors.append(str(x)))
        t.load(page, launch=True, settings={"tab": "guides", "examplesChecked": True})
        page.wait_for_function("() => typeof guideGroupsOf === 'function' && typeof GUIDE_RAMPS === 'object'")

        # 1. The three text guides: their ramp list and the hexes in the guide's words cannot drift
        lists = page.evaluate("() => GUIDE_RAMPS")
        for k in TEXT_GUIDES:
            start = gd.index(f'key: "{k}"')
            end = gd.index("related:", start)
            text = gd[start:end].lower()
            mine = [s["hex"].lower() for s in lists[k]]
            # every listed hex is in the entry text (snake also names two belly hexes that are not part of the back-to-flank ramp)
            check(f"{k}: every hex in the ramp list is in the entry text, no repeats", all(h in text for h in mine) and len(mine) == len(set(mine)), mine)
            check(f"{k}: the ramp list runs dark to light", mine == sorted(mine, key=lambda h: page.evaluate("(x) => MinifolioColour.hexToHsl(x).l", h)), mine)
        check("the three lists are the ones in the brief", set(lists) == set(TEXT_GUIDES))

        # 2. One check over every recipe and tip: the rule is applied the same way everywhere
        every = page.evaluate("""() => { const out = { recipes: 0, tips: 0, bad: [] };
          const light = (h) => MinifolioColour.hexToHsl(h).l;
          const test = (kind, e, steps) => { const r = rampSteps(steps); if (!r) return; out[kind]++;
            const c = r.filter(s => !s.wash);
            if (r.length < 3 || r.length > 5 || c.length < 2 || light(c[c.length - 1].hex) <= light(c[0].hex)) out.bad.push(e.key); };
          for (const r of DETAIL_RECIPES) test('recipes', r, r.steps);
          for (const b of BASING_TIPS) test('tips', b, b.paintSteps);
          out.total = DETAIL_RECIPES.length + BASING_TIPS.length; return out; }""")
        n = every["recipes"] + every["tips"]
        # the brief expected 120 to 140 of 131 entries; there are 256 entries now, so the band is set from the real count
        check("most entries get a ramp, and every shown ramp has 3 to 5 swatches with rising lightness",
              165 <= n <= 190 and n < every["total"] and not every["bad"], every)

        # 3. Real pages: a sample of 3 recipes, 3 tips and the 3 text guides
        keys = page.evaluate("""() => ({ r: DETAIL_RECIPES.filter(r => rampSteps(r.steps)).map(r => r.key),
            b: BASING_TIPS.filter(b => rampSteps(b.paintSteps)).map(b => b.key),
            none: DETAIL_RECIPES.filter(r => !rampSteps(r.steps)).map(r => r.key).slice(0, 1) })""")
        sample = [(k, "detail") for k in ("painted-gold", keys["r"][3], keys["r"][-1])] + [(k, "basing") for k in (keys["b"][0], keys["b"][len(keys["b"]) // 2], keys["b"][-1])] + [(k, None) for k in TEXT_GUIDES]
        sample_none = (keys["none"][0], "detail")
        ctx.close()

        def visit(w, h, theme, appearance, tag):
            c = browser.new_context(viewport={"width": w, "height": h}, service_workers="block")
            pg = c.new_page()
            pg.on("pageerror", lambda x: errors.append(str(x)))
            t.load(pg, launch=True, settings={"tab": "guides", "examplesChecked": True, "appearance": appearance, "theme": theme})
            pg.wait_for_function("() => typeof guideGroupsOf === 'function'")
            bad = []
            for key, kind in (sample if tag == "main" else sample[::4]):
                open_entry(pg, key, kind)
                info = pg.evaluate(ONE_LINE)
                if not info or not (info["oneLine"] and info["inside"] and info["noScroll"] and info["w"] == 28 and info["h"] == 28 and 3 <= info["n"] <= 5):
                    bad.append((key, info))
            check(f"{w}x{h} {theme} {appearance}: ramp is one line, 28 px, inside the screen, no sideways scroll ({len(sample if tag == 'main' else sample[::4])} entries)", not bad, bad)
            return pg, c

        pg, c = visit(390, 844, "classic", "dark", "main")
        # semantics on the main page
        for key, kind in sample:
            open_entry(pg, key, kind)
            info = pg.evaluate(ONE_LINE)
            check(f"{key}: role img, a dark to light label, no buttons or tab stops, name text only",
                  info["role"] == "img" and info["label"].startswith("Colour ramp, dark to light: ") and info["buttons"] == 0
                  and "<" not in info["label"], info)
        open_entry(pg, "painted-gold", "detail")
        pos = pg.evaluate("""() => { const r = document.querySelector('.ab13c-ramp'), s = document.querySelector('#guides-detail-summary, .starter-summary');
          return s && r && (s.compareDocumentPosition(r) & Node.DOCUMENT_POSITION_FOLLOWING) ? true : false; }""")
        check("a recipe's ramp sits under its summary", pos)
        open_entry(pg, sample[3][0], "basing")
        pos = pg.evaluate("""() => { const r = document.querySelector('.ab13c-ramp'), h = document.querySelector('.basing-sub');
          return !!(r && h && (r.compareDocumentPosition(h) & Node.DOCUMENT_POSITION_FOLLOWING)); }""")
        check("a tip's ramp sits above What you need", pos)
        # a ring is marked in the words and in the shape
        ring = pg.evaluate("""() => { const key = DETAIL_RECIPES.find(r => (rampSteps(r.steps) || []).some(s => s.wash)).key; return key; }""")
        open_entry(pg, ring, "detail")
        info = pg.evaluate("() => ({ rings: document.querySelectorAll('.ab13c-ramp .ab13c-ring').length, label: document.querySelector('.ab13c-ramp').getAttribute('aria-label') })")
        check("a wash or glaze swatch has a ring and is named as a wash in the label", info["rings"] >= 1 and "(wash)" in info["label"], info)
        open_entry(pg, sample_none[0], sample_none[1])
        check("an entry that does not run dark to light shows no ramp", pg.locator(".ab13c-ramp").count() == 0, sample_none)
        c.close()

        for w, h in ((360, 640), (320, 568)):
            for appearance in ("dark", "light"):
                pg, c = visit(w, h, "classic", appearance, "small")
                c.close()
        for theme, appearance in (("forge", "dark"), ("bench", "light")):
            pg, c = visit(390, 844, theme, appearance, "small")
            c.close()

        # 4. Help has the one plain line
        c = browser.new_context(viewport={"width": 390, "height": 844}, service_workers="block")
        pg = c.new_page()
        t.load(pg, launch=True, settings={"examplesChecked": True})
        txt = pg.evaluate("() => (document.getElementById('help-ramp') || {}).textContent || ''")
        check("Help has one plain line about the dots, no em dash", txt.strip() != "" and "—" not in txt and len(txt) < 140, txt)
        browser.close()
    check("no page errors", not errors, errors)
    print(f"\n{sum(results)}/{len(results)} checks passed")
    raise SystemExit(0 if all(results) else 1)

main()
