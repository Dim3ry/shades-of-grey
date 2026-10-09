"""v16 tests for Shades of Grey (paste-import, shared paint matcher, copy as text, label scan, last backed up).
Serve the repo folder with `python3 -m http.server 8765`, then run: python3 tests/test_v16.py <folder for screenshots>."""
import json, os, sys
from playwright.sync_api import sync_playwright
import os as _os
PORT = _os.environ.get("SOG_PORT", "8765")

URL = f"http://localhost:{PORT}/index.html"
SHOTS = sys.argv[1] if len(sys.argv) > 1 else "."
KEEP_NOTE = open(os.path.join(os.path.dirname(__file__), "keep_note.txt")).read()
results = []
def check(name, ok, detail=""):
    results.append(bool(ok))
    print(("PASS " if ok else "FAIL ") + name + ("" if ok else f"  -> {detail}"))

# A recipe book saved by v15 (no "shorthand" list yet).
V15_BOOK = {
    "v15": True, "parts": ["Whole model", "Armour"], "techniques": ["Prime", "Layer", "Wash"],
    "paints": [{"id": 1, "brand": "Citadel", "name": "Nuln Oil", "colour": "#222222"}],
    "recipes": [{"id": 1, "name": "Black armour", "part": "Armour", "notes": "",
                 "steps": [{"technique": "Wash", "coats": 1, "ratio": "", "note": "", "optional": False,
                            "paints": [{"paint": 1, "mix": 100}]}]}],
    "schemes": [],
}

# How George answers the questions the Keep note raises.
ANSWERS = {"Bleck Templar": "Black Templar", "CM": "Contrast Medium", "Ice": "Basing material", "SS": "Screaming Skull",
           "Khorn red": "Khorne Red", "gothor brown": "Gorthor Brown", "white": "White Primer",
           "blangels red": "Blood Angels Red", "ultramarine blue": "Ultramarines Blue"}

with sync_playwright() as pw:
    browser = pw.chromium.launch(args=["--use-fake-ui-for-media-stream", "--use-fake-device-for-media-stream"])
    for size, (w, h) in {"phone": (390, 844), "desktop": (1280, 900)}.items():
        page = browser.new_page(viewport={"width": w, "height": h})
        errors = []
        page.on("pageerror", lambda e: errors.append(str(e)))
        page.goto(URL)
        page.evaluate("b => { localStorage.clear(); localStorage.setItem('shades-of-grey-recipes', JSON.stringify(b)); }", V15_BOOK)
        page.reload()
        page.wait_for_timeout(300)

        if size == "phone":
            check("version starts with v17 (v16 tests still pass)", page.evaluate("APP_VERSION").startswith("v17"))
            b = page.evaluate("book")
            check("old book loads, shorthand defaults to empty", b["shorthand"] == {} and b["recipes"][0]["name"] == "Black armour", b.get("shorthand"))

            # The shared matcher.
            m = lambda t, hints=None: page.evaluate("([t, h]) => matchPaint(t, h || {})", [t, hints])
            r = m("macragge BLUE")
            check("matcher: ignores capitals", r["status"] == "sure" and r["paint"]["name"] == "Macragge Blue", r)
            r = m("Nurgle rot")
            check("matcher: missing 's still exact", r["status"] == "sure" and r["paint"]["name"] == "Nurgle's Rot", r)
            r = m("nuln")
            check("matcher: start of a name only one paint has", r["status"] == "sure" and r["paint"]["name"] == "Nuln Oil", r)
            r = m("Khorn red")
            check("matcher: typo is asked, not guessed", r["status"] == "unsure" and r["suggestions"][0]["name"] == "Khorne Red", r)
            r = m("CM")
            check("matcher: initials are asked", r["status"] == "unsure" and r["suggestions"][0]["name"] == "Contrast Medium", r)
            r = m("SS", {"earlier": [{"name": "Seraphim Sepia"}, {"name": "Screaming Skull"}]})
            check("matcher: initials prefer the latest paint in the notes", r["suggestions"][0]["name"] == "Screaming Skull", r)
            r = m("white")
            check("matcher: vague word is asked", r["status"] == "unsure", r)
            r = m("Gloss")
            check("matcher: Gloss = 'Ardcoat", r["status"] == "sure" and r["paint"]["name"] == "'Ardcoat", r)
            r = m("static grass")
            check("matcher: basing material", r["status"] == "material", r)
            r = m("Vallejo Mystic blue")
            check("matcher: unknown name kept as typed with brand", r["status"] == "new" and r["paint"]["name"] == "Mystic Blue" and r["paint"]["brand"] == "Vallejo", r)

            # The Keep note, read without saving.
            parsed = page.evaluate("t => parseRecipeText(t)", KEEP_NOTE)
            names = [s["name"] for s in parsed["schemes"]]
            check("keep: two schemes", names == ["Tyranids", "T'au"], names)
            tyr = {p["name"]: p for p in parsed["schemes"][0]["parts"]}
            tau = {p["name"]: p for p in parsed["schemes"][1]["parts"]}
            check("keep: Tyranid parts", list(tyr) == ["Whole model", "Skin/gun", "Eyes", "Chitin", "Hoofs/scythes", "Teeth", "Tongues",
                                                      "Red brains", "Blue and red", "Juicy green bits", "Bases"], list(tyr))
            check("keep: T'au parts (group labels dropped, = sub-parts)", list(tau) == ["Whole model", "Green bits", "Metal bits", "Creamy bits",
                  "Red bits", "Gold bits", "Skin", "Bases – Rocks", "Bases – Dirt", "Rusty bits", "Viorla", "Blood angel", "Ultramarine"], list(tau))
            pn = lambda step: [x["paint"]["name"] if x["paint"] else "?" + x["typed"] for x in step["paints"]]
            wm = tyr["Whole model"]
            check("keep: Prime step, 'No basecoat' kept as a note", wm["steps"][0]["technique"] == "Prime" and wm["notes"] == ["No basecoat"], wm)
            check("keep: drybrush + bracket note", wm["steps"][1]["technique"] == "Dry brush" and pn(wm["steps"][1]) == ["Grey Seer"]
                  and wm["steps"][1]["note"] == "heavier on the top", wm["steps"][1])
            sg = tyr["Skin/gun"]["steps"]
            check("keep: Vallejo 50/50 = one mixed step", len(sg) == 1 and pn(sg[0]) == ["Mystic Blue", "Storm Blue"] and sg[0]["ratio"] == "50/50"
                  and sg[0]["paints"][0]["paint"]["brand"] == "Vallejo", sg)
            eyes = tyr["Eyes"]["steps"]
            check("keep: 'take it or leave it' = optional", eyes[1]["optional"] and pn(eyes[1]) == ["Seraphim Sepia"], eyes[1])
            ch = tyr["Chitin"]["steps"]
            check("keep: technique in brackets", ch[1]["technique"] == "Dry brush" and ch[1]["optional"], ch[1])
            check("keep: trailing words become a note", pn(ch[2]) == ["Sigvald Burgundy"] and ch[2]["note"] == "in gaps", ch[2])
            hs = tyr["Hoofs/scythes"]["steps"]
            check("keep: Bleck Templar Contrast asked", hs[0]["technique"] == "Contrast" and hs[0]["paints"][0]["status"] == "unsure", hs[0])
            check("keep: Ardcoat Gloss", pn(hs[1]) == ["'Ardcoat"], hs[1])
            check("keep: shortened names", pn(tyr["Teeth"]["steps"][1]) == ["Agrax Earthshade"] and pn(tyr["Tongues"]["steps"][1]) == ["Carroburg Crimson"])
            rb = tyr["Red brains"]["steps"]
            check("keep: 1:1 Baal:CM = mixed step", rb[1]["ratio"] == "1:1" and pn(rb[1]) == ["Baal Red", "?CM"], rb[1])
            br = tyr["Blue and red"]["steps"]
            check("keep: 2:1 and 4:1 mixes in order", br[1]["ratio"] == "2:1" and pn(br[1]) == ["Frostheart", "?CM"]
                  and br[2]["ratio"] == "4:1" and pn(br[2]) == ["?CM", "Baal Red"], br)
            check("keep: Nurgle rot", pn(tyr["Juicy green bits"]["steps"][2]) == ["Nurgle's Rot"])
            bs = tyr["Bases"]["steps"]
            check("keep: materials", bs[0]["paints"][0]["status"] == "material" and bs[5]["paints"][0]["status"] == "material", bs[0])
            check("keep: nickname (real name) - note", pn(bs[2]) == ["Agrellan Earth"] and "Magical crack brown" in bs[2]["note"]
                  and "mottled around the base" in bs[2]["note"], bs[2])
            check("keep: 'Agrax wash' = Wash", bs[3]["technique"] == "Wash" and pn(bs[3]) == ["Agrax Earthshade"], bs[3])
            check("keep: Ice asked, bracket kept as note", bs[6]["paints"][0]["status"] == "unsure" and "pylar glacier" in bs[6]["note"], bs[6])
            twm = tau["Whole model"]["steps"]
            check("keep: T'au base coat and 'Drybrush in dawnstone'", twm[1]["technique"] == "Base coat" and pn(twm[1]) == ["Corvus Black"]
                  and twm[2]["technique"] == "Dry brush" and pn(twm[2]) == ["Dawnstone"], twm)
            check("keep: commas split steps", [pn(s) for s in tau["Metal bits"]["steps"]] == [["Leadbelcher"], ["Nuln Oil"]])
            rocks = tau["Bases – Rocks"]["steps"]
            check("keep: 'base + nuln' is two steps, not a mix", len(rocks) == 2 and rocks[0]["technique"] == "Base coat" and pn(rocks[1]) == ["Nuln Oil"], rocks)
            dirt = tau["Bases – Dirt"]["steps"]
            check("keep: 'drybrushed;' applies to the rest", [s["technique"] for s in dirt[2:]] == ["Dry brush"] * 3
                  and pn(dirt[4]) == ["Ushabti Bone"], dirt)
            via = tau["Viorla"]["steps"]
            check("keep: 'dilute corvus' = Corvus Black, note dilute", pn(via[1]) == ["Corvus Black"] and via[1]["note"] == "dilute", via[1])
            check("keep: 'Part - paint' lines", pn(tau["Blood angel"]["steps"][0]) == ["?blangels red"]
                  and pn(tau["Ultramarine"]["steps"][0]) == ["?ultramarine blue"])
            groups = page.evaluate("t => unsureMentions(parseRecipeText(t)).map(g => [g.typed, g.count])", KEEP_NOTE)
            check("keep: unsure paints grouped, each asked once", sorted(g[0] for g in groups) == sorted(ANSWERS), groups)
            check("keep: CM asked once for 3 uses", ["CM", 3] in groups, groups)

        # Through the screen: paste, preview, answer, save.
        page.evaluate("showTab('recipes')")
        page.click("#paste-recipes")
        page.fill("#import-text", KEEP_NOTE)
        page.click("text=Read notes")
        page.wait_for_timeout(200)
        check(f"{size}: unsure paints highlighted", page.locator(".import-paint.unsure").count() >= 9)
        check(f"{size}: save blocked until answered", page.locator("#import-save").is_disabled() and "Pick 9 more paints" in page.locator("#import-save").text_content())
        page.screenshot(path=f"{SHOTS}/v16-{size}-import-preview.png", full_page=False)
        for typed, answer in ANSWERS.items():
            row = page.locator(".import-ask", has=page.locator(".import-typed", has_text=f"“{typed}”"))
            row.locator("button.chip", has_text=answer).first.click()
        check(f"{size}: all answered, Save shows count", page.locator("#import-save").text_content() == "Save 24 recipes", page.locator("#import-save").text_content())
        check(f"{size}: answers shown in preview", page.locator(".import-paint.resolved", has_text="CM → Contrast Medium").count() == 3)
        page.screenshot(path=f"{SHOTS}/v16-{size}-import-answered.png", full_page=True)
        page.click("#import-save")
        page.wait_for_timeout(300)
        saved = page.evaluate("JSON.parse(localStorage.getItem('shades-of-grey-recipes'))")
        schemes = {s["name"]: s for s in saved["schemes"]}
        check(f"{size}: two schemes saved", set(schemes) == {"Tyranids", "T'au"}, list(schemes))
        check(f"{size}: one recipe per part", len(schemes["Tyranids"]["recipes"]) == 11 and len(schemes["T'au"]["recipes"]) == 13)
        recipes = {r["id"]: r for r in saved["recipes"]}
        paints = {p["id"]: p for p in saved["paints"]}
        rb = [recipes[i] for i in schemes["Tyranids"]["recipes"] if recipes[i]["name"] == "Red brains"][0]
        mix = rb["steps"][1]
        check(f"{size}: Baal:CM saved 1:1 = 50/50", mix["ratio"] == "1:1" and [p["mix"] for p in mix["paints"]] == [50, 50]
              and paints[mix["paints"][1]["paint"]]["name"] == "Contrast Medium", mix)
        check(f"{size}: technique left on Auto when not written", mix["technique"] == "", mix)
        bases = [recipes[i] for i in schemes["T'au"]["recipes"] if recipes[i]["name"].startswith("Bases (")]
        check(f"{size}: duplicate name gets scheme added", len(bases) == 0 and any(recipes[i]["name"] == "Bases – Rocks" for i in schemes["T'au"]["recipes"]))
        ice = [p for p in saved["paints"] if p["name"] == "Ice"]
        check(f"{size}: Ice saved as basing material", ice and ice[0].get("type") == "material", ice)
        check(f"{size}: new part name kept as written", [recipes[i]["part"] for i in schemes["Tyranids"]["recipes"] if recipes[i]["name"] == "Bases"] == ["Bases"])
        sh = saved["shorthand"]
        check(f"{size}: shorthand remembered", sh.get("cm", {}).get("name") == "Contrast Medium" and sh.get("ss", {}).get("name") == "Screaming Skull"
              and sh.get("khorn red", {}).get("name") == "Khorne Red", sh)
        check(f"{size}: 'Keep'/material answers not remembered as shorthand", "ice" not in sh, sh)
        check(f"{size}: palette opens after save, to check the new paints (v17.1)", page.evaluate("settings.recipeView") == "palette")
        page.click("#recipe-seg button[data-view='schemes']")
        page.screenshot(path=f"{SHOTS}/v16-{size}-schemes.png", full_page=False)

        # Remembered shorthand is now matched straight away.
        r = page.evaluate("matchPaint('cm')")
        check(f"{size}: CM now sure", r["status"] == "sure" and r["paint"]["name"] == "Contrast Medium", r)
        again = page.evaluate("unsureMentions(parseRecipeText('Brains:\\n1:1 Baal:CM\\nDrybrush SS')).length")
        check(f"{size}: re-paste asks nothing", again == 0, again)

        # Copy as text, and it pastes straight back in.
        tyr_id = schemes["Tyranids"]["id"]
        text = page.evaluate("id => schemeToText(book.schemes.find(s => s.id === id))", tyr_id)
        check(f"{size}: copy starts with the scheme", text.startswith("Scheme: Tyranids\n\nWhole model:"), text[:80])
        check(f"{size}: copy writes mixes as ratios", "1:1 Baal Red:Contrast Medium" in text, text)
        back = page.evaluate("""([t, id]) => {
          const p = parseRecipeText(t); const s = book.schemes.find(x => x.id === id);
          const orig = s.recipes.map(recipeById);
          return { name: p.schemes[0].name, unsure: unsureMentions(p).length,
                   same: p.schemes[0].parts.length === orig.length && p.schemes[0].parts.every((part, i) =>
                     part.name === orig[i].name && part.steps.length === orig[i].steps.length &&
                     part.steps.every((st, j) => st.technique === orig[i].steps[j].technique && st.optional === orig[i].steps[j].optional &&
                       JSON.stringify(st.paints.map(m => m.paint && m.paint.name)) === JSON.stringify(orig[i].steps[j].paints.map(sp => paintById(sp.paint).name)))) };
        }""", [text, tyr_id])
        check(f"{size}: copied scheme reads back the same", back["name"] == "Tyranids" and back["unsure"] == 0 and back["same"], back)
        page.locator(".scheme-item", has_text="Tyranids").locator("button", has_text="Copy as text").click()
        page.wait_for_timeout(200)
        check(f"{size}: copy button says copied", "copied" in page.inner_text("body"))

        # Recipe page has Copy as text.
        page.evaluate("id => openRecipe(id)", rb["id"])
        check(f"{size}: recipe has Copy as text", page.locator("#recipe-page button", has_text="Copy as text").count() == 1)
        rt = page.evaluate("id => recipeToText(recipeById(id))", rb["id"])
        check(f"{size}: recipe text", rt.splitlines()[0] == "Red brains:" and "Dry brush Corax White" in rt, rt)

        # Label scan: suggestions from label text, then "do I own it" and "add".
        sug = page.evaluate("suggestFromLabel('CITADEL\\nBASE\\nMACRAGGE\\nBLUE\\n12ml').suggestions.map(p => p.name)")
        check(f"{size}: label text -> Macragge Blue first", sug[:1] == ["Macragge Blue"], sug)
        sug = page.evaluate("suggestFromLabel('LAYER\\nKHORNE RFD').suggestions.map(p => p.name)")
        check(f"{size}: misread label still suggests", "Khorne Red" in sug, sug)
        # v16.1: what the reader actually got from George's pots (framed in the box), and junk.
        for text, want in [("STORMHO Sens | 'STORMHO SEs | 'STORMH O SiRES, 'STORMHO SBE", "Stormhost Silver"),
                           ("WE aveR wuire scar an LAYER | write SCAP Me avER eb ware SCAT _", "White Scar"),
                           ("& uver _ LOTHERN BLUE' caver _ LOTHERN BLUE' Pur -", "Lothern Blue")]:
            sug = page.evaluate("t => suggestFromLabel(t).suggestions.map(p => p.name)", text)
            check(f"{size}: real label read -> {want} first", sug[:1] == [want], sug)
        junk = page.evaluate("suggestFromLabel('Tv ———! PY TADEI, (oe = OOS we 4. CYTADEL COL!').suggestions.length")
        check(f"{size}: junk text suggests nothing", junk == 0, junk)
        strips = page.evaluate("""() => { const c = document.createElement('canvas'); c.width = 800; c.height = 600;
          const g = c.getContext('2d'); g.fillStyle = '#888'; g.fillRect(0, 0, 800, 600);
          return [labelStrips(c, { x: 100, y: 250, w: 600, h: 100 }).map(s => s.width), labelStrips(c, null).length]; }""")
        check(f"{size}: box gives 4 sized strips, photo gives 9", strips == [[260, 350, 260, 350], 9], strips)
        page.evaluate("openRecipeId = null; settings.recipeView = 'palette'; showTab('recipes'); renderRecipes()")
        page.click("#scan-button")
        page.locator("#scan-panel button", has_text="Scan a label").click()
        page.wait_for_selector("#scan-camera video", timeout=5000)
        check(f"{size}: camera opens with a box", page.locator("#scan-camera .cam-box").count() == 1)
        page.wait_for_timeout(500)
        page.screenshot(path=f"{SHOTS}/v16-{size}-camera.png", full_page=False)
        page.click("#cam-cancel")
        check(f"{size}: camera closes", page.locator("#scan-camera").count() == 0)
        page.fill("#scan-typed", "macrage blue")
        page.locator("#scan-typed").dispatch_event("change")
        page.wait_for_timeout(100)
        check(f"{size}: typed typo suggests, doesn't pick", page.locator("#scan-result").count() == 0
              and page.locator("#scan-panel .chip", has_text="Macragge Blue").count() == 1)
        page.locator("#scan-panel .chip", has_text="Macragge Blue").click()
        check(f"{size}: not owned yet", "Not in your palette yet" in page.locator("#scan-result").inner_text())
        page.screenshot(path=f"{SHOTS}/v16-{size}-scan.png", full_page=False)
        page.locator("#scan-result button", has_text="Add to my palette").click()
        page.wait_for_timeout(200)
        mb = page.evaluate("book.paints.find(p => p.name === 'Macragge Blue')")
        check(f"{size}: added as owned", mb and mb.get("owned") is True, mb)
        page.evaluate("pruneUnusedPaints()")
        check(f"{size}: owned paint survives tidy-up", page.evaluate("!!book.paints.find(p => p.name === 'Macragge Blue')"))
        page.fill("#scan-typed", "nuln oil")
        page.locator("#scan-typed").dispatch_event("change")
        page.locator("#scan-panel .chip", has_text="Nuln Oil").click()
        check(f"{size}: owned paint recognised", "Already in your palette" in page.locator("#scan-result").inner_text())

        # Last backed up.
        page.evaluate("showTab('settings')")
        page.wait_for_timeout(100)
        age = page.locator("#backup-age").text_content()
        check(f"{size}: backup age says never", "never" in age, age)
        page.evaluate("settings.lastBackup = new Date(Date.now() - 10 * 864e5).toISOString().slice(0, 10); renderSettings()")
        age = page.locator("#backup-age").text_content()
        check(f"{size}: backup age in days, flagged", "10 days ago" in age and "backup-old" in page.locator("#backup-age").get_attribute("class"), age)
        page.screenshot(path=f"{SHOTS}/v16-{size}-backup.png", full_page=False)

        # Undo of an import.
        page.evaluate("showTab('recipes')")
        n_before = page.evaluate("book.recipes.length")
        page.evaluate("startImport()")
        page.fill("#import-text", "Test scheme\n\nArmour:\nLeadbelcher, nuln")
        page.click("text=Read notes")
        page.click("#import-save")
        check(f"{size}: small import saved", page.evaluate("book.recipes.length") == n_before + 1)
        page.locator("#toast button, .toast button").first.click()
        page.wait_for_timeout(200)
        check(f"{size}: undo removes the import", page.evaluate("book.recipes.length") == n_before and
              not page.evaluate("book.schemes.some(s => s.name === 'Test scheme')"))

        # Horizontal scroll check on phone.
        if size == "phone":
            page.evaluate("startImport()")
            page.fill("#import-text", KEEP_NOTE)
            page.click("text=Read notes")
            wide = page.evaluate("document.documentElement.scrollWidth > window.innerWidth + 1")
            check("phone: no sideways scrolling on preview", not wide)

        check(f"{size}: no page errors", not errors, errors)
        page.close()
    browser.close()

print(f"\n{sum(results)}/{len(results)} passed")
sys.exit(0 if all(results) else 1)
