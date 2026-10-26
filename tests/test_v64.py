"""v64 tests for Minifolio (chunk 3.4c: match fit rules and the Opposite fix).

What changed:
 One fit rule in colour.js: Good fit (CIEDE2000 distance up to 6), Okay fit (up to 15), Poor fit (over 15); rough paints (metallic, Contrast,
 wash and so on) get a third more room. All cut-offs and the words are in one place (GOOD_UNDER, CLOSE_UNDER, ROUGH_STRETCH, FIT_WORDS).
 suggestPaint() gives the one suggestion a screen shows: your paint first if it is Good or Okay; if your best paint is Poor, the best paint
 overall first and yours second ("Yours, poor fit"). Used by Colour ideas, starter schemes, detail recipes, basing and the wheel panel.
 The sentences under a suggestion ("Closest you own", "Not very close...", "Similar, not exact.") are gone: labels only.
 The wheel panel's Opposite lifts a colour darker than 0.45 lightness to 0.45 (saturation at least 0.55). Split, triad and the recipe roles
 are as before. No paint content file changed.

Checks:
1. Versions, the v64 Updates entry, Help line, no em dash.
2. The rule: cut-offs, rough paints, labels, in one place.
3. suggestPaint: only a poor match owned, a good match owned, an okay match owned, nothing owned, an empty list, poor owned that is also the best.
4. Colour ideas on screen: poor owned goes second, good owned goes first, empty palette, labels only (no note sentences).
5. Opposite of dark blues: clear oranges or golds; light colours, split, triad and the recipe roles unchanged.
6. Wheel panel on screen: Opposite for a dark blue, and the second line when the owned paint is a poor fit.
7. 390 px and 360 px, dark and light: no sideways scroll, tap targets 44 px or more.
8. No network use, no page errors, no browser pop-ups.
Run all tests with `python3 tests/run_all.py`, or serve the repo folder and run this file on its own."""
import os, re, sys
from playwright.sync_api import sync_playwright

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from notice_watch import attach_notices
import wheel_helpers as wh
import test_v31 as t
import test_v38 as w38   # the wheel panel helpers (open the tab, tap a colour, open a paint's panel)

read, load, no_sideways = t.read, t.load, t.no_sideways
results = []

def check(name, ok, detail=""):
    results.append(bool(ok))
    print(("PASS " if ok else "FAIL ") + name + ("" if ok else f"  -> {detail}"))

DARK_BLUES = ["Kantor Blue", "Night Lords Blue", "Macragge Blue", "Imperium Blue", "Lapislazuli"]
TARGET = "#e66c00"   # a clear orange
POOL_JS = """(rows) => rows.map(([name, colour, status]) => ({ brand: 'Test', name, colour, status }))"""

IDEA_ROWS_JS = """() => [...document.querySelectorAll('#colour-ideas ul.idea-list > li')].map(li => {
    const also = li.querySelector('.idea-also');
    return { name: li.querySelector('.idea-name').childNodes[0].textContent, tag: li.querySelector('.idea-tag').textContent,
             fit: (li.querySelector('.idea-fit') || {}).textContent || '',
             also: also ? { name: also.querySelector('.idea-name').childNodes[0].textContent, tag: also.querySelector('.idea-tag').textContent, add: !!also.querySelector('button') } : null };
}); """

def ideas_for(page, paints):
    load(page, paints=paints)
    t.open_editor(page)
    t.set_step_paint(page, 0, "Macragge Blue")
    t.open_panel(page)
    return page.evaluate(IDEA_ROWS_JS)

def main():
    errors, dialogs, requests = [], [], []
    app, colour = read("app.js"), read("colour.js")
    with sync_playwright() as p:
        browser = p.chromium.launch()
        ctx = browser.new_context(viewport={"width": 390, "height": 844}, service_workers="block")
        page = ctx.new_page()
        page.on("pageerror", lambda x: errors.append(str(x)))
        page.on("dialog", lambda d: (dialogs.append(d.message), d.dismiss()))
        page.on("request", lambda r: requests.append(r.url) if not r.url.startswith(("http://localhost", "data:", "blob:")) else None)
        notices = []
        attach_notices(page, notices.append)

        # ---------- 1. Versions ----------
        print("\n--- 1. Versions, Updates entry, Help ---")
        load(page, paints=[])
        entry = page.evaluate("CHANGELOG.find(c => c.version === 'v64')")
        joined = " ".join(entry["changes"]) if entry else ""
        check("the entry names the three labels and Yours, poor fit", all(w in joined for w in ("Good fit", "Okay fit", "Poor fit", "Yours, poor fit")), joined)
        help_li = page.evaluate("() => { const e = document.getElementById('help-fit'); return e ? e.textContent : ''; }")
        check("Help has a line on the fit labels", all(w in help_li for w in ("Good fit", "Okay fit", "Poor fit", "Yours, poor fit")), help_li)
        check("no em dash in the new Help line or Updates entry", "—" not in help_li and "—" not in joined)

        # ---------- 2. The rule ----------
        print("\n--- 2. The fit rule ---")
        j = page.evaluate("""() => { const C = MinifolioColour, q = (d, r) => C.judgeMatch(d, r).quality;
            return { g: [q(5.9), q(6), q(6.1)], c: [q(14.9), q(15), q(15.1)], rg: [q(7.9, true), q(8.1, true)], rc: [q(19.9, true), q(20.1, true)],
                     words: C.FIT_WORDS, lab: [C.fitLabel({ quality: 'good', owned: true }), C.fitLabel({ quality: 'close', owned: true }),
                     C.fitLabel({ quality: 'poor', owned: false }), C.fitLabel({ quality: 'poor', owned: true }), C.fitLabel(null)] }; }""")
        check("Good up to 6, Okay up to 15, Poor over 15", j["g"] == ["good", "good", "close"] and j["c"] == ["close", "close", "poor"], j)
        check("rough paints (metallic, Contrast, wash...) get a third more room: 8 and 20", j["rg"] == ["good", "close"] and j["rc"] == ["close", "poor"], j)
        check("the words: Good fit, Okay fit, Poor fit, and Yours, poor fit for a poor paint you own",
              j["lab"] == ["Good fit", "Okay fit", "Poor fit", "Yours, poor fit", ""], j["lab"])
        check("the cut-offs are set once, in colour.js", len(re.findall(r"const GOOD_UNDER = 6, CLOSE_UNDER = 15", colour)) == 1 and "GOOD_UNDER" not in app and "CLOSE_UNDER" not in app)
        app_code = re.sub(r"const CHANGELOG = \[.*?\n    \];", "", app, flags=re.S)   # (the v64 Updates entry names them, on purpose)
        check("the old note sentences are gone from the app", not any(s in app_code for s in ("Closest you own", "Not very close. It is the nearest we found.", "Similar, not exact.")))

        # ---------- 3. suggestPaint ----------
        print("\n--- 3. Who goes first ---")
        def suggest(rows, exclude=None):
            return page.evaluate("""([rows, target, exclude]) => { const C = MinifolioColour;
                const pool = rows.map(([name, colour, status]) => ({ brand: 'Test', name, colour, status }));
                const h = C.suggestPaint(target, pool, exclude ? { exclude } : undefined);
                if (!h) return null;
                return { name: h.paint.name, owned: h.owned, quality: h.quality, label: C.fitLabel(h),
                         also: h.alsoOwned ? { name: h.alsoOwned.paint.name, owned: h.alsoOwned.owned, quality: h.alsoOwned.quality, label: C.fitLabel(h.alsoOwned) } : null }; }""", [rows, TARGET, exclude])
        # slightly different shades of the target, found by moving lightness until the distance is where we want it
        shade = lambda lo, hi: page.evaluate("""([target, lo, hi]) => { const C = MinifolioColour, hsl = C.hexToHsl(target);
            for (let k = 1; k < 80; k++) { const hex = C.hslToHex(hsl.h, hsl.s, Math.max(0, hsl.l - k * 0.01)); const d = C.colourDistance(target, hex);
                if (d > lo && d < hi) return hex; } return null; }""", [TARGET, lo, hi])
        near_good, near_okay = shade(2, 5), shade(8, 13)
        check("test colours found (a Good and an Okay shade of the target)", bool(near_good and near_okay), (near_good, near_okay))
        r = suggest([["Own Green", "#2e7d32", "owned"], ["Shop Orange", TARGET, "notowned"]])
        check("only a poor match owned: the best paint overall is first (Good fit), yours is second as Yours, poor fit",
              r and r["name"] == "Shop Orange" and not r["owned"] and r["label"] == "Good fit" and r["also"] and r["also"]["name"] == "Own Green" and r["also"]["label"] == "Yours, poor fit", r)
        r = suggest([["Own Green", "#2e7d32", "owned"]])
        check("only a poor match owned and nothing better: that one paint, Yours, poor fit, no second line",
              r and r["name"] == "Own Green" and r["owned"] and r["label"] == "Yours, poor fit" and r["also"] is None, r)
        r = suggest([["Own Near", near_good, "owned"], ["Shop Orange", TARGET, "notowned"]])
        check("a good match owned goes first even though a shop paint is closer; Good fit, no second line",
              r and r["name"] == "Own Near" and r["owned"] and r["label"] == "Good fit" and r["also"] is None, r)
        r = suggest([["Own Okay", near_okay, "owned"], ["Shop Orange", TARGET, "notowned"]])
        check("an okay match owned goes first and says Okay fit, no second line", r and r["name"] == "Own Okay" and r["owned"] and r["label"] == "Okay fit" and r["also"] is None, r)
        r = suggest([["Own Okay", near_okay, "low"], ["Own Green", "#2e7d32", "owned"]])
        check("a paint running low counts as owned", r and r["name"] == "Own Okay" and r["owned"], r)
        r = suggest([["Shop Orange", TARGET, "notowned"], ["Shop Near", near_good, "wishlist"]])
        check("nothing owned: the closest paint, not in your palette, with its fit and no second line", r and r["name"] == "Shop Orange" and not r["owned"] and r["label"] == "Good fit" and r["also"] is None, r)
        check("an empty collection and an empty list give nothing, no error", suggest([]) is None and page.evaluate("() => MinifolioColour.suggestPaint('nope', [])") is None)
        r = suggest([["Own Green", "#2e7d32", "owned"], ["Shop Orange", TARGET, "notowned"]], exclude=[TARGET])
        check("a colour in the exclude list is skipped (the same paint is never suggested twice)", r and r["name"] == "Own Green", r)
        r = page.evaluate("""([target]) => { const C = MinifolioColour; const pool = [{ brand: 'T', name: 'Own Green', colour: '#2e7d32', status: 'owned' }, { brand: 'T', name: 'Shop', colour: target, status: 'notowned' }];
            return { lead: C.nearestPaints(target, pool, { limit: 2 }).map(x => x.paint.name), off: C.nearestPaints(target, pool, { limit: 2, ownedFirst: false }).map(x => x.paint.name) }; }""", [TARGET])
        check("nearestPaints: a poor owned paint no longer jumps the queue", r["lead"] == ["Shop", "Own Green"] and r["off"] == ["Shop", "Own Green"], r)
        r = page.evaluate("""() => { const C = MinifolioColour; const t = '#c8c8c8';
            const rough = { brand: 'T', name: 'Own Silver Metallic', colour: '#9a9a9a', type: 'metallic', status: 'owned' };
            const plain = { brand: 'T', name: 'Own Grey', colour: '#9a9a9a', status: 'owned' };
            const d = C.colourDistance(t, '#9a9a9a');
            return { d, rough: C.nearestPaints(t, [rough], {})[0].quality, plain: C.nearestPaints(t, [plain], {})[0].quality }; }""")
        check("a metallic paint is judged with the looser rule", r["d"] > 6 and ((r["d"] <= 8) == (r["rough"] == "good")) and (r["plain"] != "good" if r["d"] > 6 else True), r)

        # ---------- 4. Colour ideas on screen ----------
        print("\n--- 4. Colour ideas on screen ---")
        base = {"id": 1, "brand": "Citadel", "name": "Macragge Blue", "colour": "#0d407f", "status": "owned"}
        wanted = page.evaluate("() => colourIdeaWanted(MinifolioColour.harmonies('#0d407f'), COLOUR_ROLES[0], 'complementary', 0).hex")
        rows = ideas_for(page, [base, {"id": 2, "brand": "Test", "name": "Only Owned Green", "colour": "#2e7d32", "status": "owned"}])
        check("only a poor match owned: the first idea is a paint you do not own with a fit label, and Only Owned Green is under it as Yours, poor fit",
              rows and rows[0]["tag"] == "Not in your palette" and rows[0]["fit"] in ("Good fit", "Okay fit", "Poor fit") and rows[0]["also"]
              and rows[0]["also"]["name"] == "Only Owned Green" and rows[0]["also"]["tag"] == "Yours, poor fit" and rows[0]["also"]["add"], rows)
        check("the number of ideas is still three (the second paint sits inside the row)", len(rows) == 3, len(rows))
        page.click("#colour-ideas li:first-child .idea-also button")
        page.wait_for_timeout(200)
        added = page.evaluate("() => recipeDraft.steps[recipeDraft.steps.length - 1].paints[0].name")
        check("tapping the second line adds your own paint as a new last step", added == "Only Owned Green", added)
        rows = ideas_for(page, [base, {"id": 2, "brand": "Test", "name": "Exact Owned Orange", "colour": wanted, "status": "owned"}])
        check("a good match owned: first, You own this, Good fit, nothing second",
              rows and rows[0]["name"] == "Exact Owned Orange" and rows[0]["tag"] == "You own this" and rows[0]["fit"] == "Good fit" and rows[0]["also"] is None, rows)
        okay = page.evaluate("""([target]) => { const C = MinifolioColour, hsl = C.hexToHsl(target);
            for (let k = 1; k < 80; k++) { const hex = C.hslToHex(hsl.h, hsl.s, Math.max(0, hsl.l - k * 0.01)); const d = C.colourDistance(target, hex); if (d > 8 && d < 13) return hex; } return null; }""", [wanted])
        rows = ideas_for(page, [base, {"id": 2, "brand": "Test", "name": "Okay Owned Orange", "colour": okay, "status": "owned"}])
        check("an okay match owned: first, You own this, Okay fit, nothing second",
              rows and rows[0]["name"] == "Okay Owned Orange" and rows[0]["tag"] == "You own this" and rows[0]["fit"] == "Okay fit" and rows[0]["also"] is None, rows)
        rows = ideas_for(page, [base])
        check("an empty collection: every idea is Not in your palette with a fit label, none says Yours, no second line",
              len(rows) == 3 and all(r["tag"] == "Not in your palette" and r["fit"] in ("Good fit", "Okay fit", "Poor fit") and r["also"] is None for r in rows), rows)
        body = page.evaluate("() => document.getElementById('colour-ideas').textContent")
        check("labels only: no note under any idea, and none of the old sentences",
              page.evaluate("() => document.querySelectorAll('#colour-ideas .idea-note').length") == 0
              and not any(s in body for s in ("Closest you own", "Not very close", "Similar, not exact", "nearest we found", "Close enough")), body[:200])

        # ---------- 5. Opposite of dark colours ----------
        print("\n--- 5. Opposite ---")
        load(page, paints=[])
        out = page.evaluate("""(names) => { const C = MinifolioColour;
            return names.map(n => { const k = KNOWN_PAINTS.find(x => x.name === n); const h = C.harmonies(k.colour);
                const w = colourIdeaWanted(h, PAINT_PANEL_ROLE, 'complementary', 0), hsl = C.hexToHsl(w.hex);
                const pool = KNOWN_PAINTS.map(x => ({ brand: x.brand, name: x.name, colour: x.colour, status: 'notowned' }));
                const hit = C.suggestPaint(w.hex, pool, { exclude: [k.colour] });
                return { n, base: C.hexToHsl(k.colour).l, l: hsl.l, s: hsl.s, wanted: C.colourFamily(w.hex), got: C.colourFamily(hit.paint.colour), name: hit.paint.name, q: hit.quality }; }); }""", DARK_BLUES)
        check("each dark blue is darker than 0.45, and its Opposite is lifted to at least 0.45 lightness and 0.55 saturation",
              all(o["base"] < 0.45 and o["l"] >= 0.449 and o["s"] >= 0.549 for o in out), out)
        check("the matches are clear oranges or golds (not browns): " + ", ".join(f"{o['n']} -> {o['name']}" for o in out),
              all(o["got"] in ("orange", "yellow") and o["wanted"] in ("orange", "yellow") for o in out), out)
        same = page.evaluate("""() => { const C = MinifolioColour, plain = { boost: { s: 0, l: [0, 1] } }, out = [];
            for (const hex of ['#6fa8dc', '#cc4444', '#88aa44', '#e0b040']) {   // lightness above 0.45: no lift
                const h = C.harmonies(hex); out.push(colourIdeaWanted(h, PAINT_PANEL_ROLE, 'complementary', 0).hex === colourIdeaWanted(h, plain, 'complementary', 0).hex); }
            const h = C.harmonies('#02134e');   // dark: split, triad and neighbours are as before
            for (const pick of ['split0', 'split1', 'triad0', 'triad1', 'analogous0', 'analogous1']) out.push(colourIdeaWanted(h, PAINT_PANEL_ROLE, pick, 0).hex === colourIdeaWanted(h, plain, pick, 0).hex);
            out.push(colourIdeaWanted(h, PAINT_PANEL_ROLE, 'complementary', 0).hex !== colourIdeaWanted(h, plain, 'complementary', 0).hex);   // only the Opposite changes
            return out; }""")
        check("light colours, split, triad and neighbours are not lifted; the dark Opposite is", all(same), same)
        check("the recipe Colour ideas roles have no Opposite lift of their own (they already lift)", page.evaluate("() => COLOUR_ROLES.every(r => !('opposite' in r))"))

        # ---------- 6. Wheel panel ----------
        print("\n--- 6. Wheel panel on screen ---")
        PANEL_ROWS = """() => [...document.querySelectorAll('#cmp-paint-panel ul.idea-list > li')].map(li => { const also = li.querySelector('.idea-also');
            return { name: li.querySelector('.idea-name').childNodes[0].textContent, tag: li.querySelector('.idea-tag').textContent, fit: (li.querySelector('.idea-fit') || {}).textContent || '',
                     also: also ? { name: also.querySelector('.idea-name').childNodes[0].textContent, tag: also.querySelector('.idea-tag').textContent } : null,
                     notes: li.querySelectorAll('.idea-note').length, colour: li.querySelector('.swatch').style.getPropertyValue('--swatch') }; })"""
        kantor = w38.P(1, "Kantor Blue", "#02134e", brand="Citadel")
        load(page, paints=[kantor])
        w38.open_tab(page)
        w38.tap(page, "blue")
        w38.open_row(page, "Kantor Blue")
        rows = page.evaluate(PANEL_ROWS)
        fam = page.evaluate("(c) => MinifolioColour.colourFamily(c)", rows[0]["colour"] if rows else "#000000")
        check("Kantor Blue's Opposite in the panel is a clear orange or gold, with a fit label and Not in your palette",
              rows and fam in ("orange", "yellow") and rows[0]["tag"] == "Not in your palette" and rows[0]["fit"] in ("Good fit", "Okay fit"), rows[:1] and (rows[0], fam))
        check("no note sentences in the panel's five colour rows (the starter schemes below keep their own summary line)", len(rows) >= 5 and all(r["notes"] == 0 for r in rows[:5]), [r["notes"] for r in rows])
        load(page, paints=[kantor, w38.P(2, "Own Green", "#2e7d32", brand="Test Paints")])
        w38.open_tab(page)
        w38.tap(page, "blue")
        w38.open_row(page, "Kantor Blue")
        rows = page.evaluate(PANEL_ROWS)
        check("the panel with only a poor owned match: the best paint first, Own Green second as Yours, poor fit",
              rows and rows[0]["tag"] == "Not in your palette" and rows[0]["also"] and rows[0]["also"]["name"] == "Own Green" and rows[0]["also"]["tag"] == "Yours, poor fit", rows[:1])
        sec = page.evaluate("() => { const l = [...document.querySelectorAll('#cmp-paint-panel .paint-panel-label')].map(e => e.textContent); return l; }")
        check("the panel still has Opposite, Neighbours, Triad and the starter schemes", sec[:3] == ["Opposite", "Neighbours", "Triad"], sec)

        # ---------- 7. Phones ----------
        print("\n--- 7. Phones, dark and light ---")
        for width in (390, 360):
            for scheme in ("dark", "light"):
                page.set_viewport_size({"width": width, "height": 844})
                page.emulate_media(color_scheme=scheme)
                ideas_for(page, [base, {"id": 2, "brand": "Test", "name": "Only Owned Green", "colour": "#2e7d32", "status": "owned"}])
                h = page.evaluate("() => Math.min(...[...document.querySelectorAll('#colour-ideas .idea-also button, #colour-ideas button.idea')].map(b => b.getBoundingClientRect().height))")
                check(f"{width} px {scheme}: no sideways scroll, every tap target 44 px or more", no_sideways(page) and h >= 44, h)
        page.emulate_media(color_scheme="dark")
        page.set_viewport_size({"width": 390, "height": 844})

        # ---------- 8. Errors ----------
        print("\n--- 8. Errors ---")
        import subprocess
        changed = []
        for base in ("HEAD", "origin/main"):
            out = subprocess.run(["git", "diff", "--name-only", base, "--", "schemes.js", "detail-recipes.js", "basing-tips.js"], cwd=t.ROOT, capture_output=True, text=True)
            if out.returncode == 0:
                changed += out.stdout.split()
        check("no recipe, scheme or tip content file changed (schemes.js, detail-recipes.js, basing-tips.js)", changed == [], changed)
        check("no outside network requests (works offline)", not requests, requests[:3])
        check("no page errors", not errors, errors)
        check("no browser pop-ups", not dialogs, dialogs)
        browser.close()
    failed = results.count(False)
    print(f"\n{len(results) - failed} passed, {failed} failed")
    sys.exit(1 if failed else 0)

if __name__ == "__main__":
    main()
