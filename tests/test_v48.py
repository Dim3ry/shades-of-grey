"""v48 tests for Minifolio (more paint ranges).

What changed:
 (a) New brands the app knows by name: Scale75 (every range in the open list), Formula P3, Two Thin Coats, Tamiya Acrylics
     (X and XF mini pots, with code numbers) and Green Stuff World (every range in the list).
 (b) More of the brands it already knew: the rest of the current Citadel range, The Army Painter's Speedpaint 2.0 and colour
     primers, Pro Acryl primers and washes, and AK 3rd Gen figures, primers, auxiliaries and pastels.
 (c) All in George's existing format ("Name|colour" or "Name|colour|codes"), from the same MIT-licensed list as before.
 (d) Brand words: "Monument Hobbies" now means the Pro Acryl paints; P3, Tamiya and other spellings are recognised, in typed and
     pasted text and on scanned pot labels.

Checks:
1. Versions, the v48 Updates entry, Help, README and the licence note.
2. The tables: every row is well formed, no brand lists the same paint twice, each range comment's count is right,
   and every brand loads with the expected number of paints.
3. Finding paints: a paint from each new range is found by name, with the right brand; typos and brand words still work.
4. Brands on labels and in text, including Monument Hobbies.
5. Names shared between brands still ask which brand (nothing is picked silently).
6. Speed: the app still opens and matches names quickly with about 2,400 paints.
7. No page errors, no browser pop-ups, no CSP errors.
Run all tests with `python3 tests/run_all.py`, or serve the repo folder and run this file on its own."""
import os, re, sys, time
from playwright.sync_api import sync_playwright

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import test_v31 as t

URL, read = t.URL, t.read
results = []

def check(name, ok, detail=""):
    results.append(bool(ok))
    print(("PASS " if ok else "FAIL ") + name + ("" if ok else f"  -> {detail}"))

EXPECTED = {"Citadel": 402, "The Army Painter": 535, "Vallejo": 941, "Pro Acryl": 131, "AK Interactive": 778,
            "Scale75": 350, "Formula P3": 130, "Two Thin Coats": 180, "Tamiya": 208, "Green Stuff World": 219}

def tables(app):
    out = {}
    for name in ("KNOWN_PAINT_TABLE", "EXTRA_PAINT_TABLE"):
        a = app.index(f"const {name} = {{"); b = app.index("\n    };", a)
        cur = None
        for line in app[a:b].split("\n"):
            if line.strip().startswith("//"): continue
            m = re.match(r'\s{6}(?:"([^"]+)"|(\w+)):\s*\[', line)
            if m: cur = m.group(1) or m.group(2); out.setdefault((name, cur), [])
            if cur: out[(name, cur)] += re.findall(r'"([^"]*)"', line[line.index("[") + 1:] if m else line)
    return out

def main():
    errors, csp, popups = [], [], []
    app, html, readme, lic = read("app.js"), read("index.html"), read("README.md"), read("LICENSE-paint-list.txt")
    with sync_playwright() as p:
        browser = p.chromium.launch()
        ctx = browser.new_context(viewport={"width": 390, "height": 844}, service_workers="block")
        page = ctx.new_page()
        page.on("pageerror", lambda e: errors.append(str(e)))
        page.on("console", lambda m: csp.append(m.text) if "Content Security Policy" in m.text else None)
        page.on("dialog", lambda d: (popups.append(d.message), d.dismiss()))
        page.goto(t.BASE + "manifest.json"); page.evaluate("localStorage.clear()")
        page.goto(URL); page.wait_for_function("() => typeof APP_VERSION === 'string'")

        # ---------- 1. Versions and wording ----------
        print("\n--- 1. Versions and wording ---")
        version = page.evaluate("APP_VERSION")
        check("APP_VERSION is v48 or later", float(version[1:]) >= 48, version)
        m = re.search(r'const VERSION = "v([\d.]+)"', read("sw.js"))
        check("sw.js VERSION matches", m and "v" + m.group(1) == version)
        tags = re.findall(r'<script src="[^"]+\?v=(\d+)"', html)
        check("all six script tags carry the version number", len(tags) == 6 and set(tags) == {version[1:]}, tags)
        log = page.evaluate("CHANGELOG.find(r => r.version === 'v48')")
        names = ["Scale 75", "Formula P3", "Two Thin Coats", "Tamiya", "Green Stuff World", "Speedpaint", "Pro Acryl", "AK Interactive", "Citadel", "Vallejo"]
        check("Updates has a v48 line naming every new and topped-up brand, and one for Paint brands",
              log and len(log["changes"]) == 2 and all(n in log["changes"][0] for n in names) and "Settings: Paint brands" in log["changes"][1], log)
        check("Help lists all ten brands for the scanner, with the new total, and points to Settings → Paint brands",
              "Scale 75, Formula P3, Two Thin Coats, Tamiya and Green Stuff World (about 3,900 paints)" in html and "<strong>Settings → Paint brands</strong>" in html)
        check("Help, README and the licence note credit the list for the new brands",
              "Two Thin Coats, Tamiya and Green Stuff World paint names, colours and codes (and some Citadel ones) come from the free" in html
              and "Tamiya and Green Stuff World paint names (and some Citadel ones)" in readme and "copied 19 Oct 2026" in lic and "MIT License" in lic)

        # ---------- 2. The tables ----------
        print("\n--- 2. The tables ---")
        tab = tables(app)
        bad, dupes = [], []
        for (tbl, brand), rows in tab.items():
            seen = set()
            for r in rows:
                if not re.fullmatch(r"[^|]+\|#[0-9a-f]{6}(\|[0-9A-Za-z.\- ]+)?", r): bad.append((brand, r))
                k = re.sub(r"[^a-z0-9]+", " ", r.split("|")[0].lower().replace("'", "").replace("’", "")).strip()
                if k in seen: dupes.append((brand, r))
                seen.add(k)
        check("every row is 'Name|#colour' or 'Name|#colour|codes' (George's format)", not bad, bad[:5])
        OLD = {"Gorthor Brown", "Grey Knights Steel", "Rhinox Hide", "Kislev Flesh", "Necron Compound"}   # repeats already in v47's Citadel list; the loader skips them
        check("no brand lists the same paint twice (apart from five Citadel repeats from before v48, which the loader skips)",
              all(b == "Citadel" and r.split("|")[0] in OLD for b, r in dupes), [d for d in dupes if d[1].split("|")[0] not in OLD])
        counts_ok = []
        for m in re.finditer(r'      // ([^\n]+): (\d+)\n      "([^"]+)": \[', app):
            counts_ok.append((m.group(3), int(m.group(2)), len(tab[("EXTRA_PAINT_TABLE", m.group(3))])))
        check("each range comment in EXTRA_PAINT_TABLE gives its true count", counts_ok and all(a == b for _, a, b in counts_ok), counts_ok)
        loaded = page.evaluate("() => { const c = {}; for (const k of KNOWN_PAINTS) c[k.brand] = (c[k.brand] || 0) + 1; return c; }")
        check("every brand loads with the expected number of paints", loaded == EXPECTED, loaded)
        tam = page.evaluate("KNOWN_PAINTS.filter(k => k.brand === 'Tamiya')")
        check("every Tamiya paint carries its X or XF code number", all(k.get("codes") and all(re.fullmatch(r"(XF|X|LP|TS|AS)-\d+[A-Z]?", c) for c in k["codes"]) for k in tam), [k for k in tam if not k.get("codes")][:3])
        check("the new paints are marked as extra (Citadel and your own paints are tried first), the Citadel ones are not",
              page.evaluate("KNOWN_PAINTS.filter(k => ['Scale75','Formula P3','Two Thin Coats','Tamiya','Green Stuff World'].includes(k.brand)).every(k => k.extra === true)")
              and page.evaluate("KNOWN_PAINTS.filter(k => k.brand === 'Citadel').every(k => !k.extra)"))

        # ---------- 3. Finding paints ----------
        print("\n--- 3. Finding paints by name ---")
        samples = [("XV-88", "Citadel"), ("Balthasar Gold", "Citadel"), ("Kindleflame", "Citadel"), ("Absolution Green", "The Army Painter"),
                   ("Wurm Green", "Formula P3"), ("Witching Hour Blue", "Two Thin Coats"), ("Zima Blue", "Green Stuff World"),
                   ("Airnrhod Blue", "Scale75"), ("Tamiya Flat Earth", "Tamiya"), ("Scale 75 Abyssal Blue", "Scale75"), ("P3 Wurm Green", "Formula P3")]
        for text, brand in samples:
            got = page.evaluate("(t) => { const r = matchPaint(t); const p = r && (r.paint || r.match || r); return p && p.brand ? { brand: p.brand, name: p.name } : r; }", text)
            check(f"'{text}' is found as a {brand} paint", isinstance(got, dict) and got.get("brand") == brand, got)
        got = page.evaluate("(t) => { const r = matchPaint(t); return [r.status, (r.suggestions || []).map(s => s.brand + ' ' + s.name)]; }", "Khorn Red")
        check("a typo is still offered back as the Citadel paint, not swapped silently (Khorn Red → Khorne Red?)", got[0] == "unsure" and got[1][:1] == ["Citadel Khorne Red"], got)
        got = page.evaluate("(t) => { const r = matchPaint(t); return [r.status, (r.suggestions || []).map(s => s.brand)]; }", "Abyssal Blue")
        check("Abyssal Blue (Army Painter and Scale75) asks which brand", got[0] == "unsure" and set(got[1]) == {"The Army Painter", "Scale75"}, got)

        # ---------- 4. Brand words ----------
        print("\n--- 4. Brand words ---")
        words = page.evaluate("""() => ({ monument: brandFromText('Monument Hobbies'), p3: brandFromText('Formula P3'), tamiya: brandFromText('Tamiya'),
            split: splitBrand('Monument Hobbies Pure Black'), gsw: splitBrand('GSW Zima Blue') })""")
        check("'Monument Hobbies' now means the Pro Acryl paints", words["monument"] == "Pro Acryl" and words["split"]["brand"] == "Pro Acryl" and words["split"]["rest"] == "Pure Black", words)
        check("Formula P3, Tamiya and GSW are understood as brands", words["p3"] == "Formula P3" and words["tamiya"] == "Tamiya" and words["gsw"]["brand"] == "Green Stuff World", words)
        labels = page.evaluate("""() => ['SCALE 75 SCALECOLOR', 'Formula P3 hobby paint', 'TAMIYA COLOR ACRYLIC PAINT', 'Two Thin Coats', 'GREEN STUFF WORLD', 'Monument Hobbies Pro Acryl', 'Citadel'].map(brandOnLabel)""")
        check("pot labels name the new brands", labels == ["Scale75", "Formula P3", "Tamiya", "Two Thin Coats", "Green Stuff World", "Pro Acryl", "Citadel"], labels)
        check("Formula P3 and Tamiya are in the brand menu", page.evaluate("COMMON_BRANDS.includes('Formula P3') && COMMON_BRANDS.includes('Tamiya')"))

        # ---------- 5. Shared names still ask ----------
        print("\n--- 5. Shared names ---")
        shared = page.evaluate("""() => { const by = {}; for (const k of KNOWN_PAINTS) if (k.extra) (by[k.name.toLowerCase()] = by[k.name.toLowerCase()] || new Set()).add(k.brand);
            return Object.entries(by).filter(([n, b]) => b.size >= 3 && !KNOWN_PAINTS.some(k => !k.extra && k.name.toLowerCase() === n)).slice(0, 5).map(([n, b]) => [n, [...b]]); }""")
        res = [page.evaluate("(t) => matchPaint(t).status", n) for n, _ in shared]
        check("a name that several of the extra brands share (and Citadel doesn't) is never picked silently: the app asks which",
              shared and all(r != "sure" for r in res), list(zip(shared, res)))
        r = page.evaluate("(t) => { const m = matchPaint(t); return [m.status, m.paint && m.paint.brand]; }", "Scale 75 Abyssal Blue")
        check("…and with the brand written first it is sure", r == ["sure", "Scale75"], r)

        # ---------- 5b. Paint brands ----------
        print("\n--- 5b. Paint brands in Settings ---")
        page.goto(t.BASE + "manifest.json"); page.evaluate("localStorage.clear()")
        page.goto(URL); page.wait_for_function("() => typeof APP_VERSION === 'string'")
        page.click('.tabs button[data-tab="settings"]')
        chips = page.evaluate("[...document.querySelectorAll('#brand-toggles [data-brand-choice]')].map(b => [b.textContent, b.getAttribute('aria-pressed'), b.type])")
        check("Settings has one button per brand, all pressed (searched) to start with",
              [c[0] for c in chips] == list(EXPECTED) and all(c[1] == "true" and c[2] == "button" for c in chips), chips)
        check("the card has a title and the buttons only (no helper text)", page.evaluate("document.querySelectorAll('#brands-card .hint').length") == 0
              and page.evaluate("document.querySelector('#brands-card h2').textContent") == "Paint brands")
        check("the Your Palette brand filter is untouched (still its own element)", page.evaluate("!!document.getElementById('brand-chips') && document.getElementById('brand-chips') !== document.getElementById('brand-toggles')"))
        page.click('[data-brand-choice="Formula P3"]')
        st = page.evaluate("""() => ({ pressed: document.querySelector('[data-brand-choice="Formula P3"]').getAttribute('aria-pressed'),
            saved: JSON.parse(localStorage.getItem('shades-of-grey-settings')).brandsOff, n: searchedPaints.length,
            p3: searchedPaints.some(k => k.brand === 'Formula P3'), match: matchPaint('Wurm Green').status,
            ideas: matchCandidates().some(c => c.brand === 'Formula P3') })""")
        check("switching Formula P3 off: unpressed, saved, and its paints are no longer searched, matched or offered",
              st["pressed"] == "false" and st["saved"] == ["Formula P3"] and not st["p3"] and st["n"] == sum(EXPECTED.values()) - EXPECTED["Formula P3"]
              and st["match"] != "sure" and not st["ideas"], st)
        page.reload(); page.wait_for_function("() => typeof APP_VERSION === 'string'")
        check("…and it stays off after a reload", page.evaluate("!searchedPaints.some(k => k.brand === 'Formula P3')")
              and page.get_attribute('[data-brand-choice="Formula P3"]', "aria-pressed") == "false")
        page.evaluate("""() => { book.paints.push({ id: 'mine-p3', brand: 'Formula P3', name: 'Wurm Green', colour: '#3b5a36' }); }""")
        check("your own paint of a switched-off brand is still found", page.evaluate("matchPaint('Wurm Green').status") == "sure")
        page.evaluate("() => { book.paints = book.paints.filter(p => p.id !== 'mine-p3'); }")
        page.click('.tabs button[data-tab="settings"]'); page.click('[data-brand-choice="Formula P3"]')
        check("switching it back on brings its paints back", page.evaluate("searchedPaints.length") == sum(EXPECTED.values()) and page.evaluate("matchPaint('Wurm Green').status") == "sure")
        bad = page.evaluate("""() => [cleanBrandsOff(['Nope', 'Tamiya', 'Tamiya', 5, null, '__proto__']), cleanBrandsOff('Tamiya'), cleanBrandsOff(null)]""")
        check("unknown, repeated and non-text brands are dropped from the setting", bad == [["Tamiya"], [], []], bad)
        page.evaluate("settings.brandsOff = ['Scale75']")
        check("a backup carries the switched-off brands", page.evaluate("backupData().brandsOff") == ["Scale75"])
        page.evaluate("settings.brandsOff = []; saveSettings(); updateSearchedPaints();")

        # ---------- 6. Speed ----------
        print("\n--- 6. Speed ---")
        took = page.evaluate("() => { const t0 = performance.now(); for (const w of ['nuln oil','khorn red','xv88','balthasar gold','flat black','abyssal blue','wurm green','zima blue','absolution green','arctic white']) matchPaint(w); return performance.now() - t0; }")
        check("ten names match in under a second (desktop speed)", took < 1000, round(took))
        page.click('.tabs button[data-tab="recipes"]')
        t0 = time.time(); page.reload(); page.wait_for_function("() => typeof APP_VERSION === 'string'")
        check("the app opens in under three seconds with about 3,900 built-in paints", time.time() - t0 < 3, round(time.time() - t0, 2))

        # ---------- 7. Clean run ----------
        print("\n--- 7. A clean run ---")
        check("no page errors", not errors, errors[:2])
        check("no browser pop-ups", not popups, popups[:2])
        check("no Content Security Policy errors", not csp, csp[:2])
        browser.close()
    failed = results.count(False)
    print(f"\n{len(results) - failed} passed, {failed} failed")
    sys.exit(1 if failed else 0)

if __name__ == "__main__":
    main()
