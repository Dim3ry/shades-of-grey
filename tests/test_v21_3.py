"""v21.3 tests for Minifolio: the pot-label reader knows more brands.

v21.3 adds built-in name lists (EXTRA_PAINT_TABLE) for Vallejo Game Color, Model Color and Xpress Color, The Army
Painter's Warpaints Fanatic, Pro Acryl and AK 3rd Gen, from the open "miniature-paints" list (MIT
licence), and reads Vallejo code numbers like 72.021. Citadel matching must not change.

Checks:
1. Version numbers (plain numbers), sw.js matches, the Updates entry, CNAME, the ocr folder and the
   ZAP workflow kept, storage names and the data version unchanged, the CSP exactly as in v21.2.
2. The lists: about the right number of paints per brand, every colour a real colour, codes in the
   right shape, no paint listed twice, Citadel's list unchanged, the licence file and credits.
3. Each new brand is recognised from sample label text, and a sweep of EVERY new paint's name
   (with the brand words a pot prints) finds it.
4. Vallejo codes: every code picks its paint, misread forms (72.O21, 72021, 72-021) still work, and
   typing a code in pasted notes works.
5. Citadel unchanged: every Citadel label and paste result matches what v21.2 gave
   (tests/v21_2_citadel_matches.json, recorded from v21.2 before the change).
6. Names two brands share: the app asks which one, unless the brand is given.
7. The real label reader, end to end: a picture of a Vallejo label read on the scan panel.
8. Help and About text; no page errors, no CSP errors.
Run all tests with `python3 tests/run_all.py`, or serve the repo folder and run this file on its own."""
import json, os, re, sys
from playwright.sync_api import sync_playwright

PORT = os.environ.get("SOG_PORT", "8765")
URL = f"http://localhost:{PORT}/index.html"
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.join(HERE, "..")
SHOTS = sys.argv[1] if len(sys.argv) > 1 else os.path.join(HERE, "screenshots")
results = []

def check(name, ok, detail=""):
    results.append(bool(ok))
    print(("PASS " if ok else "FAIL ") + name + ("" if ok else f"  -> {detail}"))

def read(name):
    return open(os.path.join(ROOT, name), encoding="utf-8").read()

V21_2_CSP = ("default-src 'self'; script-src 'self' 'unsafe-inline' 'wasm-unsafe-eval'; style-src 'self' 'unsafe-inline'; "
             "img-src 'self' blob: data:; media-src 'self' blob:; font-src 'self'; connect-src 'self'; worker-src 'self'; "
             "manifest-src 'self'; object-src 'none'; base-uri 'none'; form-action 'none'; frame-src 'none'")

# What a pot of each brand prints around the paint's name.
BRAND_WORDS = {"Vallejo": "VALLEJO GAME COLOR", "The Army Painter": "THE ARMY PAINTER WARPAINTS FANATIC",
               "Pro Acryl": "PRO ACRYL", "AK Interactive": "AK INTERACTIVE 3RD GEN ACRYLICS"}
# Rough sizes of each list (a few names appear in two Vallejo ranges and are listed once).
SIZES = {"Vallejo": 415, "The Army Painter": 205, "Pro Acryl": 115, "AK Interactive": 215}

def seed(page):
    page.goto(URL)
    page.evaluate("() => { localStorage.clear(); localStorage.setItem('mini-tracker-models', '[]'); }")
    page.reload()
    page.wait_for_timeout(600)

def top(page, text):
    return page.evaluate("t => suggestFromLabel(t).suggestions.map(s => s.brand + '|' + s.name)", text)

def paste(page, text):
    return page.evaluate("""t => { const r = matchPaint(t, {});
      return { status: r.status, paint: r.paint ? r.paint.brand + '|' + r.paint.name : null,
               sug: r.suggestions.map(s => s.brand + '|' + s.name) }; }""", text)

with sync_playwright() as p:
    browser = p.chromium.launch()
    context = browser.new_context(viewport={"width": 390, "height": 844})
    page = context.new_page()
    errors, csp = [], []
    page.on("pageerror", lambda e: errors.append(str(e)))
    page.on("console", lambda m: csp.append(m.text) if "Content Security Policy" in m.text and "csp-probe" not in m.text else None)
    page.on("dialog", lambda d: d.accept())
    seed(page)
    html, sw = read("index.html"), read("sw.js")

    # ---------- 1. Versions and kept things ----------
    print("\n--- 1. Versions and kept things ---")
    version = page.evaluate("APP_VERSION")
    check("APP_VERSION is v21.3 or later", float(version[1:]) >= 21.3, version)
    check("APP_VERSION is a plain number (no letters)", re.fullmatch(r"v\d+(\.\d+)?", version), version)
    m = re.search(r'const VERSION = "([^"]+)"', sw)
    check("sw.js VERSION matches APP_VERSION", m and m.group(1) == version, m and m.group(1))
    entry = page.evaluate("CHANGELOG.find(r => r.version === 'v21.3')")
    check("Updates has a v21.3 entry", entry and len(entry["changes"]) >= 1, entry)
    check("the v21.3 entry names the new brands and codes", entry and all(w in " ".join(entry["changes"])
          for w in ["Vallejo", "Fanatic", "Pro Acryl", "AK", "72.021"]))
    page.click('nav button[data-tab="updates"]')
    heads = page.locator("#view-updates h3").all_inner_texts()
    check("the Updates tab shows v21.3", any(h.startswith("v21.3") for h in heads), heads[:3])
    check("CNAME is kept (minifolio.app)", read("CNAME").strip() == "minifolio.app")
    check("ocr folder is kept", all(os.path.exists(os.path.join(ROOT, "ocr", f)) for f in
          ["ocr-worker.js", "tesseract-core-simd-lstm.wasm", "tesseract-core-lstm.wasm", "eng.traineddata"]))
    check("ZAP scan workflow is kept", os.path.exists(os.path.join(ROOT, ".github", "workflows", "zap-scan.yml")))
    check("DATA_VERSION is still 1", page.evaluate("DATA_VERSION") == 1)
    for key in ["mini-tracker-models", "shades-of-grey-settings", "shades-of-grey-recipes"]:
        check(f"storage key {key} still used", key in html)
    tags = re.findall(r'<meta\s+http-equiv="Content-Security-Policy"\s+content="([^"]+)"', html)
    check("the CSP is exactly as in v21.2 (lists live inside the app)", tags == [V21_2_CSP], tags)
    check("no web address is fetched for the lists", "fetch(" not in html[html.find("EXTRA_PAINT_TABLE"):html.find("EXTRA_PAINT_TABLE") + 40000])

    # ---------- 2. The lists ----------
    print("\n--- 2. The lists ---")
    info = page.evaluate("""() => {
      const extra = KNOWN_PAINTS.filter(k => k.extra);
      const by = {};
      for (const k of extra) by[k.brand] = (by[k.brand] || 0) + 1;
      const keys = KNOWN_PAINTS.map(k => (k.brand + '|' + k.name).toLowerCase());
      return { by, total: extra.length,
        badColour: extra.filter(k => !/^#[0-9a-f]{6}$/.test(k.colour)).map(k => k.name),
        badCode: extra.filter(k => k.codes && !k.codes.every(c => /^7[0-3]\\.[0-9]{3}$/.test(c))).map(k => k.name),
        codesNotVallejo: extra.filter(k => k.codes && k.brand !== 'Vallejo').length,
        vallejoNoCode: extra.filter(k => k.brand === 'Vallejo' && !k.codes).map(k => k.name),
        twice: keys.filter((k, i) => keys.indexOf(k) !== i),
        citadel: KNOWN_PAINTS.filter(k => k.brand === 'Citadel').length,
        citadelExtra: KNOWN_PAINTS.filter(k => k.brand === 'Citadel' && k.extra).length,
        oldOnes: ['Matt Black', 'Matt White', 'Strong Tone', 'Dark Tone'].every(n => KNOWN_PAINTS.some(k => k.brand === 'The Army Painter' && k.name === n && !k.extra)),
      }; }""")
    for brand, size in SIZES.items():
        check(f"{brand}: about {size}+ paints listed", info["by"].get(brand, 0) >= size, info["by"])
    check("about 950 new paints in all", info["total"] >= 950, info["total"])
    check("every new paint has a real colour", not info["badColour"], info["badColour"][:5])
    check("every Vallejo code is like 72.021", not info["badCode"], info["badCode"][:5])
    check("every Vallejo paint has a code", not info["vallejoNoCode"], info["vallejoNoCode"][:5])
    check("only Vallejo paints have codes", info["codesNotVallejo"] == 0, info["codesNotVallejo"])
    check("no paint is listed twice (same brand and name)", not info["twice"], info["twice"][:5])
    base = json.load(open(os.path.join(HERE, "v21_2_citadel_matches.json"), encoding="utf-8"))
    check("Citadel's list is unchanged", info["citadel"] == base["citadel_count"] and info["citadelExtra"] == 0,
          (info["citadel"], info["citadelExtra"]))
    check("the older Army Painter entries are kept as they were", info["oldOnes"])
    lic = read("LICENSE-paint-list.txt")
    check("LICENSE-paint-list.txt has the MIT licence and the source", "MIT License" in lic and "Rick Fleuren" in lic
          and "Arcturus5404/miniature-paints" in lic)
    check("README credits the list", "miniature-paints" in read("README.md") and "LICENSE-paint-list.txt" in read("README.md"))

    # ---------- 3. Each new brand recognised ----------
    print("\n--- 3. Each brand recognised from label text ---")
    samples = [
        ("VALLEJO GAME COLOR\n17ml\nDEAD WHITE", "Vallejo|Dead White"),
        ("VALLEJO MODEL COLOR\nFLAT EARTH\n17 ml", "Vallejo|Flat Earth"),
        ("Vallejo Game Color\nScarlet Red", "Vallejo|Scarlet Red"),
        ("THE ARMY PAINTER\nWARPAINTS FANATIC\nABYSSAL BLUE", "The Army Painter|Abyssal Blue"),
        ("WARPAINTS FANATIC\nPURE RED", "The Army Painter|Pure Red"),
        ("FANATIC\nARMY GREEN", "The Army Painter|Army Green"),
        ("PRO ACRYL\nCOAL BLACK", "Pro Acryl|Coal Black"),
        ("MONUMENT HOBBIES PRO ACRYL\nBOLD TITANIUM WHITE", "Pro Acryl|Bold Titanium White"),
        ("AK interactive 3rd GEN\nALGA GREEN", "AK Interactive|Alga Green"),
        ("AK INTERACTIVE\nDEEP ORANGE\nACRYLICS 3RD GENERATION", "AK Interactive|Deep Orange"),
        ("VALLEJO XPRESS COLOR\nSTORM BLUE", "Vallejo|Storm Blue"),
        ("VALLEJO GAME COLOR\nSTORMY BLUE", "Vallejo|Stormy Blue"),
    ]
    for text, want in samples:
        got = top(page, text)
        check(f"{text.splitlines()[-1] if 'ml' not in text.splitlines()[-1] else text.splitlines()[1]!r} → {want} first",
              got[:1] == [want], got)
    # A misread name still works.
    check("misread 'ABYSAL BLUE' (Fanatic) → Abyssal Blue first",
          top(page, "WARPAINTS FANATIC\nABYSAL BLUE")[:1] == ["The Army Painter|Abyssal Blue"])
    check("misread 'DEAD WHlTE' (Vallejo) still offers Dead White",
          "Vallejo|Dead White" in top(page, "VALLEJO\nDEAD WHlTE"))
    sweep = page.evaluate("""words => {
      const res = {};
      for (const k of KNOWN_PAINTS.filter(k => k.extra)) {
        const r = res[k.brand] = res[k.brand] || { n: 0, first: 0, in4: 0, plain: 0, miss: [] };
        r.n++;
        const s = suggestFromLabel(words[k.brand] + "\\n" + k.name.toUpperCase()).suggestions;
        const i = s.findIndex(x => x.brand === k.brand && x.name === k.name);
        if (i === 0) r.first++;
        if (i >= 0) r.in4++; else r.miss.push(k.name);
        if (suggestFromLabel(k.name.toUpperCase()).suggestions.some(x => x.brand === k.brand && x.name === k.name)) r.plain++;
      }
      return res; }""", BRAND_WORDS)
    for brand, r in sweep.items():
        check(f"sweep {brand}: every paint's label offers it ({r['in4']}/{r['n']})", r["in4"] == r["n"], r["miss"][:8])
        check(f"sweep {brand}: almost always first ({r['first']}/{r['n']}, need 97%)", r["first"] >= 0.97 * r["n"], r["first"])
        check(f"sweep {brand}: offered even without the brand words ({r['plain']}/{r['n']}, need 98%)",
              r["plain"] >= 0.98 * r["n"], r["plain"])

    # ---------- 4. Vallejo codes ----------
    print("\n--- 4. Vallejo code numbers ---")
    codes = page.evaluate("""() => {
      const all = KNOWN_PAINTS.filter(k => k.codes).flatMap(k => k.codes.map(c => [c, k.name]));
      const miss = all.filter(([c, n]) => { const s = suggestFromLabel("VALLEJO\\n" + c).suggestions; return !(s[0] && s[0].name === n); });
      return { n: all.length, miss }; }""")
    check(f"every Vallejo code on a label picks its paint first ({codes['n'] - len(codes['miss'])}/{codes['n']})",
          codes["n"] >= 380 and not codes["miss"], codes["miss"][:5])
    check("72.021 = Magic Blue (Game Color)", top(page, "VALLEJO GAME COLOR\n72.021")[:1] == ["Vallejo|Magic Blue"])
    check("70.950 = Black (Model Color)", top(page, "70.950")[:1] == ["Vallejo|Black"])
    check("the code wins over a blurred name", top(page, "VALLEJO\n72.034\nB0NE WH")[:1] == ["Vallejo|Bone White"])
    for form in ["72.021", "72,021", "72-021", "72 021", "72021", "72.O21", "72.02l", "Ref. 72.021 17ml"]:
        check(f"code written {form!r} is read as 72.021", page.evaluate("t => vallejoCodes(t)", form) == ["72.021"])
    for form in ["17ml", "0.57 fl oz", "1772.021", "72.0211", "72.OIL", "Batch 2026"]:
        check(f"{form!r} is not taken for a code", page.evaluate("t => vallejoCodes(t)", form) == [])
    check("typing 72.021 in pasted notes → Vallejo Magic Blue (sure)",
          paste(page, "72.021") == {"status": "sure", "paint": "Vallejo|Magic Blue", "sug": []})
    check("typing 'Vallejo 72.021' → Magic Blue (sure)", paste(page, "Vallejo 72.021")["paint"] == "Vallejo|Magic Blue")
    steps = page.evaluate("""t => parseRecipeText(t).schemes[0].parts[0].steps.map(st =>
        [st.technique, st.paints.map(m => m.paint ? m.paint.brand + '|' + m.paint.name : m.typed)])""",
        "Armour:\nBase: 72.021\nWash: Nuln Oil\nAbyssal Blue\nCoal Black")
    check("a pasted note with a code and new-brand names reads right", steps == [
        ["Base coat", ["Vallejo|Magic Blue"]], ["Wash", ["Citadel|Nuln Oil"]],
        ["", ["The Army Painter|Abyssal Blue"]], ["", ["Pro Acryl|Coal Black"]]], steps)

    # ---------- 5. Citadel unchanged ----------
    print("\n--- 5. Citadel matching unchanged ---")
    after = page.evaluate("""([labels, pastes]) => {
      const label = {}, paste = {};
      for (const t of labels) label[t] = suggestFromLabel(t).suggestions.map(s => s.brand + '|' + s.name);
      for (const t of pastes) { const r = matchPaint(t, {});
        paste[t] = { status: r.status, paint: r.paint ? r.paint.brand + '|' + r.paint.name : null,
                     sug: r.suggestions.map(s => s.brand + '|' + s.name) }; }
      return { label, paste }; }""", [list(base["label"]), list(base["paste"])])
    first_changed = [t for t, v in base["label"].items() if after["label"][t][:1] != v[:1]]
    check(f"label text: the first suggestion is the same as v21.2 ({len(base['label'])} labels)", not first_changed, first_changed[:5])
    # The Citadel (and older) suggestions are all still there, in the same order; new brands only fill spare places.
    same_old = [t for t, v in base["label"].items()
                if [x for x in after["label"][t] if x.split("|")[0] == "Citadel" or x in v] != v]
    check("label text: every v21.2 suggestion is still offered, in the same order", not same_old,
          [(t, base["label"][t], after["label"][t]) for t in same_old[:3]])
    paste_changed = [t for t, v in base["paste"].items() if after["paste"][t]["status"] != v["status"]
                     or after["paste"][t]["paint"] != v["paint"] or after["paste"][t]["sug"][:len(v["sug"])] != v["sug"]]
    check(f"pasted names: same result as v21.2 ({len(base['paste'])} names; new brands only add suggestions after)",
          not paste_changed, [(t, base["paste"][t], after["paste"][t]) for t in paste_changed[:3]])
    check("'Citadel Macragge Blue' still Citadel", paste(page, "Citadel Macragge Blue")["paint"] == "Citadel|Macragge Blue")
    check("label 'CITADEL BASE MACRAGGE BLUE' → Macragge Blue only",
          top(page, "CITADEL\nBASE\nMACRAGGE\nBLUE\n12ml") == ["Citadel|Macragge Blue"])
    check("label 'BLACK TEMPLAR' → Black Templar first", top(page, "CITADEL CONTRAST\nBLACK TEMPLAR")[:1] == ["Citadel|Black Templar"])

    # ---------- 6. Names two brands share ----------
    print("\n--- 6. Shared names ---")
    r = paste(page, "Scarlet Red")
    check("'Scarlet Red' (Vallejo and AK) asks which", r["status"] == "unsure"
          and {"Vallejo|Scarlet Red", "AK Interactive|Scarlet Red"} <= set(r["sug"]), r)
    check("'Vallejo Scarlet Red' is sure", paste(page, "Vallejo Scarlet Red") == {"status": "sure", "paint": "Vallejo|Scarlet Red", "sug": []})
    check("'AK Interactive Scarlet Red' is sure", paste(page, "AK Interactive Scarlet Red")["paint"] == "AK Interactive|Scarlet Red")
    r = paste(page, "Ivory")
    check("'Ivory' (three brands) asks which", r["status"] == "unsure" and len(r["sug"]) >= 2, r)
    check("'Vallejo Ivory' is now a known paint", paste(page, "Vallejo Ivory")["status"] == "sure")
    check("a label naming the brand picks that brand: AK SCARLET RED",
          top(page, "AK INTERACTIVE\nSCARLET RED")[:1] == ["AK Interactive|Scarlet Red"])
    check("…and VALLEJO SCARLET RED", top(page, "VALLEJO\nSCARLET RED")[:1] == ["Vallejo|Scarlet Red"])
    both = top(page, "SCARLET RED")
    check("no brand on the label: both brands offered", {"Vallejo|Scarlet Red", "AK Interactive|Scarlet Red"} <= set(both), both)
    # Your own paint with a shared name is still picked first.
    page.evaluate("""() => { book.paints.push({ id: 'p-mine', brand: 'AK Interactive', name: 'Ivory', colour: '#eeeecc' }); candidateCache = null; }""")
    check("your own 'Ivory' (AK) is picked, not asked", paste(page, "Ivory")["paint"] == "AK Interactive|Ivory")
    page.evaluate("() => { book.paints = book.paints.filter(p => p.id !== 'p-mine'); }")
    speed = page.evaluate("() => { const t = performance.now(); for (let i = 0; i < 20; i++) suggestFromLabel('VALLEJO GAME COLOR 72.021 MAGIC BLUE'); return (performance.now() - t) / 20; }")
    check(f"a label is matched quickly ({speed:.1f} ms, need < 100)", speed < 100, speed)

    # ---------- 7. The real label reader, end to end ----------
    print("\n--- 7. Real label reader on the scan panel ---")
    page.evaluate("openRecipeId = null; settings.recipeView = 'palette'; showTab('recipes'); renderRecipes()")
    page.click("#scan-button")
    page.evaluate("""async () => {
      // A camera-sized picture with the label inside the box, as the camera view passes it.
      const c = document.createElement('canvas'); c.width = 1200; c.height = 900;
      const g = c.getContext('2d'); g.fillStyle = '#fff'; g.fillRect(0, 0, 1200, 900);
      g.fillStyle = '#000'; g.font = 'bold 60px Arial'; g.fillText('VALLEJO', 300, 380);
      g.fillText('72.034', 300, 460); g.fillText('BONE WHITE', 300, 540);
      await scanLabel(c, { x: 250, y: 300, w: 700, h: 280 }); }""")
    page.wait_for_function("() => /Is it one of these|Couldn't/.test(document.getElementById('scan-panel').innerText)", timeout=120000)
    chips = page.locator("#scan-panel .chip").all_inner_texts()
    check("a Vallejo label picture → Bone White offered on the scan panel", any("Bone White" in c for c in chips), chips)
    os.makedirs(SHOTS, exist_ok=True)
    page.screenshot(path=os.path.join(SHOTS, "v21-3-scan-vallejo.png"))
    page.locator("#scan-panel .chip", has_text="Bone White").first.click()
    check("tapping it shows Vallejo Bone White", "Vallejo" in page.locator("#scan-result").inner_text()
          and "Bone White" in page.locator("#scan-result").inner_text(), page.locator("#scan-result").inner_text())
    page.locator("#scan-result button", has_text="Add to my palette").click()
    page.wait_for_timeout(200)
    added = page.evaluate("book.paints.find(p => p.name === 'Bone White')")
    check("added to Your Palette as Vallejo, owned, with the list's colour", added and added.get("brand") == "Vallejo"
          and added.get("owned") is True and re.fullmatch(r"#[0-9a-f]{6}", added.get("colour", "")) and added["colour"] != "#808080", added)
    page.screenshot(path=os.path.join(SHOTS, "v21-3-palette-bone-white.png"))

    # ---------- 8. Help, About, errors ----------
    print("\n--- 8. Help and About ---")
    page.click('nav button[data-tab="help"]')
    helps = page.locator("#help-scan-brands").text_content() or ""
    check("Help lists the brands the scanner knows", all(w in helps for w in ["Vallejo Game Color", "Model Color", "Xpress Color", "Fanatic", "Pro Acryl", "AK 3rd Gen"]), helps[:200])
    check("Help explains Vallejo code numbers", "code number" in helps and "72.021" in helps)
    check("Help says shared names ask which", "Black" in helps and "asked which" in helps)
    about = page.locator("#about").text_content() or ""
    check("About credits the miniature-paints list (MIT)", "miniature-paints" in about and "MIT" in about and "Rick Fleuren" in about)
    check("no page errors", not errors, errors[:3])
    check("no CSP errors", not csp, csp[:3])
    browser.close()

passed = sum(results)
print(f"\n{passed}/{len(results)} checks passed")
sys.exit(0 if passed == len(results) else 1)
