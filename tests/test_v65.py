"""v65 tests for Minifolio (chunk 3.5a: Similar paints, the Best match card).

What changed:
 A paint in the Compendium (a colour idea row, and the open panel of a colour wheel paint) has a "Similar paints" button. It opens a
 pop-up (same box as the question box, theme colours only) with the paint's swatch and name, Lighter / Close / Darker (Close by default)
 and one card, Best match: up to 3 paints from different brands where possible, closest first, whether or not you own them, each with its
 fit word. A paint you do not own can go on the shopping list (with Undo); a paint you own says so. Varnishes, mediums, thinners and the
 15 Tamiya paints stored as white are never offered; nor are example or made-up paints, nor the paint itself.
 Your closest and the Best / Yours tabs came in v66 (chunk 3.5b-1, see test_v66); swapping into a recipe step comes after. No paint content file changed.

Checks:
1. Versions, the v65 Updates entry, Help line, no em dash.
2. The button: on a colour idea row and a wheel paint panel; not offered without a Compendium door, for example paints or a paint with no colour.
3. The pop-up on screen: label, title, Lighter / Close / Darker (Close pressed), Best match, up to 3 rows, fit words, the approximate note,
   no Mentor-only parts (no arrows, no Sample label), no Your closest yet.
4. The matching: closest first, different brands, the paint itself and the skip list never offered, the 15 Tamiya paints and the
   varnishes and mediums skipped, every skip-list name is a real paint, owned paints say so, example paints are never offered.
5. Lighter and Darker move the colour the right way and the list on screen follows.
6. Add to shopping list: Wishlist in Your Palette, the row says so, Undo is above the pop-up and puts it back.
7. Escape, the close button, a tap on the dimmed area and the Back button close it; focus goes back to the button that opened it.
8. 390 px and 360 px, dark and light: no sideways scroll, tap targets 44 px or more; no colour written into the pop-up's styles.
9. Content files unchanged, no network use, no page errors, no browser pop-ups.
Run all tests with `python3 tests/run_all.py`, or serve the repo folder and run this file on its own."""
import json, os, re, subprocess, sys
from playwright.sync_api import sync_playwright

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from notice_watch import attach_notices
import test_v31 as t
import test_v35 as c   # Compendium helpers (open every part, pick a start colour)
import test_v39 as h   # the Probe Blue paint

read, no_sideways = t.read, t.no_sideways

def load(page, **kw):
    # T1: closing the pop-up (Escape) removes the app's spare Back step with history.back(), which finishes a moment
    # later. A page.goto sent right after could be cut off (net::ERR_ABORTED). So wait for that step to be gone first,
    # and if the browser still cuts the page load off, load once more. No check is touched.
    try:
        page.wait_for_function("() => !(history.state && history.state.minifolio === 'back')", timeout=2000)
    except Exception:
        pass
    try:
        return t.load(page, **kw)
    except Exception as e:
        if "ERR_ABORTED" not in str(e):
            raise
        return t.load(page, **kw)
results = []

def check(name, ok, detail=""):
    results.append(bool(ok))
    print(("PASS " if ok else "FAIL ") + name + ("" if ok else f"  -> {detail}"))

BASE = "test paints|probe blue"
SKIP_15_TAMIYA = ["Dark green 2 (RAF)", "Dark iron", "Dark yellow 2", "IJN gray (Maizuru Arsenal)", "IJN gray (Yokosuka Arsenal)",
                  "Medium sea gray 2 (RAF)", "Ocean gray 2 (RAF)", "Red brown 2", "Rubber black", "Fluorescent orange", "Metallic gray",
                  "Metallic orange", "Pearl yellow", "Pure metallic red", "Semi-gloss bright gun metal"]

def P(id, brand, name, colour, **more):
    return dict({"id": id, "brand": brand, "name": name, "colour": colour}, **more)

SOURCE = P(1, "Test Paints", "Probe Source", "#3a6ea5", status="owned")
TWIN = P(2, "Alpha Paints", "Owned Twin", "#3a6fa5", status="owned")                 # almost the same colour, and yours
GHOST = P(3, "", "Ghost Twin", "#3a6ea5", example=True)                               # an example paint: never offered
PALETTE = [SOURCE, TWIN, GHOST]

def stored(page):
    return page.evaluate("() => JSON.parse(localStorage.getItem('shades-of-grey-recipes'))")

def palette_entry(page, name):
    return next((p for p in stored(page)["paints"] if p["name"] == name), None)

def open_ideas(page, paints):
    load(page, paints=paints)
    c.open_comp(page)
    c.pick_base(page, BASE)
    page.wait_for_timeout(150)

def first_row(page):
    return page.locator("#cmp-fold-ideas-panel > .idea-list > li").first

def open_popup_from_row(page):
    btn = first_row(page).locator("button", has_text="Similar paints")
    btn.click()
    page.wait_for_timeout(250)
    return btn

def open_popup_for(page, index=0):
    """Opens the pop-up for a palette paint straight from the code (no button), for the matching checks."""
    page.evaluate(f"() => openSimilarPaints(book.paints[{index}], null)")
    page.wait_for_timeout(200)

def rows(page):
    return page.evaluate("""() => [...document.querySelectorAll('.similar-row')].map(li => ({
        name: li.querySelector('.similar-name').childNodes[0].textContent,
        brand: (li.querySelector('.similar-name small') || {}).textContent || '',
        fit: li.querySelector('.similar-fit').textContent,
        own: !!li.querySelector('.similar-own'),
        add: li.querySelector('.similar-add') ? li.querySelector('.similar-add').textContent : null }))""")

def popup_open(page):
    return page.evaluate("() => !!document.querySelector('.similar-backdrop')")

def main():
    errors, dialogs, requests = [], [], []
    app, html = read("app.js"), read("index.html")
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
        print("\n--- 1. Versions and the Updates entry ---")
        load(page, paints=h.JUST_BLUE)
        entry = page.evaluate("CHANGELOG.find(c => c.version === 'v65')")
        joined = " ".join(entry["changes"]) if entry else ""
        check("the entry names Similar paints, Best match, Lighter, Darker and the shopping list",
              all(w in joined for w in ["Similar paints", "Best match", "Lighter", "Darker", "shopping list"]), joined)
        help_text = page.evaluate("() => (document.getElementById('help-similar-paints') || {}).textContent || ''")
        check("Help describes Similar paints, Best match, Lighter, Darker, Undo and the skipped paints",
              all(w in help_text for w in ["Similar paints", "Best match", "Lighter", "Darker", "Undo", "not colours"]), help_text)
        check("no em dash in the new Help line", "—" not in help_text)

        # ---------- 2. The button ----------
        print("\n--- 2. The button ---")
        open_ideas(page, h.JUST_BLUE)
        labels = first_row(page).locator(".paint-recipe-buttons button").all_inner_texts()
        check("a colour idea row has Similar paints after the two recipe buttons", labels == ["Use in a recipe", "Add to a recipe", "Similar paints"], labels)
        btn = first_row(page).locator("button", has_text="Similar paints")
        label = btn.get_attribute("aria-label")
        name_in_row = first_row(page).locator(".idea-name").evaluate("el => el.childNodes[0].textContent")
        check("its aria-label is the action only, the paint's name is read from the hidden line", label == "Similar paints" and name_in_row not in label, label)
        offered = page.evaluate("""() => ({
            share: similarOffered({ share: true }, { brand: 'Vallejo', name: 'Model Color X', colour: '#336699' }),
            noDoor: similarOffered({ share: null }, { brand: 'Vallejo', name: 'Model Color X', colour: '#336699' }),
            grey: similarOffered({ share: true }, { brand: 'Vallejo', name: 'Model Color X', colour: '#808080' }),
            varnish: similarOffered({ share: true }, { brand: 'Vallejo', name: 'Gloss Varnish', colour: '#ffffff' }),
            noColour: similarOffered({ share: true }, { brand: 'Vallejo', name: 'Model Color X', colour: '' }),
            material: similarOffered({ share: true }, { brand: '', name: 'Sand', colour: '#aa9966', type: 'material' }) })""")
        check("offered only with a Compendium door and a real colour",
              offered["share"] is True and offered["noDoor"] is False and offered["noColour"] is False and offered["material"] is False, offered)
        check("a varnish is not offered", offered["varnish"] is False, offered)
        # the open panel of a colour wheel paint
        load(page, paints=h.UNOWNED)
        h.open_tab(page)
        h.tap(page, "blue")
        h.open_row(page, "Probe Blue")
        panel = page.locator("#cmp-paint-panel")
        wheel_labels = panel.locator(":scope > .paint-recipe .paint-recipe-buttons button").all_inner_texts()
        check("the open panel of a colour wheel paint has Similar paints too", wheel_labels == ["Use in a recipe", "Add to a recipe", "Similar paints"], wheel_labels)
        panel.locator(":scope > .paint-recipe button", has_text="Similar paints").click()
        page.wait_for_timeout(250)
        check("it opens the pop-up for that paint", popup_open(page) and "Probe Blue" in page.inner_text(".similar-title"))
        page.keyboard.press("Escape")
        page.wait_for_timeout(150)
        check("Escape closes it and focus is back on that button", not popup_open(page) and page.evaluate("() => document.activeElement.textContent") == "Similar paints")

        # ---------- 3. The pop-up on screen ----------
        print("\n--- 3. The pop-up ---")
        open_ideas(page, h.JUST_BLUE)
        opener = open_popup_from_row(page)
        check("the pop-up opened", popup_open(page))
        box = page.locator(".similar")
        check("it is a modal dialog named by the paint's title", box.get_attribute("role") == "dialog" and box.get_attribute("aria-modal") == "true"
              and page.evaluate("() => document.getElementById(document.querySelector('.similar').getAttribute('aria-labelledby')).tagName") == "H2")
        check("the label reads Similar paints", page.inner_text(".similar-label").strip().lower() == "similar paints")
        title = page.locator(".similar-title")
        check("the title has the paint's swatch and name", title.locator(".swatch").count() == 1 and name_in_row in title.inner_text(), title.inner_text())
        shift = page.evaluate("() => [...document.querySelectorAll('.similar-shift button')].map(b => [b.textContent, b.getAttribute('aria-pressed')])")
        check("Lighter, Close, Darker in a row, Close pressed by default", shift == [["Lighter", "false"], ["Close", "true"], ["Darker", "false"]], shift)
        check("the choices are in a labelled group", page.get_attribute(".similar-shift", "role") == "group" and bool(page.get_attribute(".similar-shift", "aria-label")))
        check("the card is Best match", page.inner_text(".similar-card h3") == "Best match")
        got = rows(page)
        check("up to 3 rows, each with a name, a brand and a fit word",
              1 <= len(got) <= 3 and all(r["name"] and r["brand"] and r["fit"] in ("Good fit", "Okay fit", "Poor fit", "Yours, poor fit") for r in got), got)
        check("the one-line note says colours are only a guide", "only a guide" in page.inner_text(".similar-note"), page.inner_text(".similar-note"))
        text = page.inner_text(".similar")
        # v66 (chunk 3.5b-1): this used to say there was no Your closest card yet. It now exists (see test_v66), so only the other two parts stay here.
        check("no Sample label, no previous or next arrows",
              "Sample" not in text and page.locator(".similar button", has_text=re.compile("^[‹›←→]$")).count() == 0, text)
        check("the close button says Close in its aria-label", page.locator(".similar-head button").get_attribute("aria-label") == "Close")
        check("the question box and the pop-up are separate (the question box stays hidden)", page.evaluate("() => document.getElementById('dialog-backdrop').classList.contains('hidden')"))
        check("the page behind does not scroll while it is open", page.evaluate("() => document.body.style.overflow") == "hidden")
        page.keyboard.press("Escape")
        page.wait_for_timeout(150)
        check("Escape closed it and the page scrolls again", not popup_open(page) and page.evaluate("() => document.body.style.overflow") == "")

        # ---------- 4. The matching ----------
        print("\n--- 4. The matching ---")
        load(page, paints=PALETTE)
        data = page.evaluate("""() => {
            const src = book.paints[0];
            const hits = similarBestMatches(src, 0);
            const pool = similarPool();
            return { hits: hits.map(h => ({ name: h.paint.name, brand: h.paint.brand, d: h.distance, owned: h.owned })),
                     skipInPool: pool.filter(p => NOT_A_COLOUR.has(paintKey(p))).length,
                     poolSize: pool.length, searched: searchedPaints.length,
                     tableNames: Object.entries(NOT_A_COLOUR_TABLE).flatMap(([b, ns]) => ns.map(n => [b, n])),
                     real: Object.entries(NOT_A_COLOUR_TABLE).flatMap(([b, ns]) => ns.filter(n => !searchedPaints.some(k => k.brand === b && k.name === n))),
                     ghostInPool: pool.some(p => p.name === 'Ghost Twin'), selfInPool: similarPool().some(p => p.name === 'Probe Source') } }""")
        hits = data["hits"]
        check("three paints, closest first", len(hits) == 3 and all(hits[i]["d"] <= hits[i + 1]["d"] for i in range(2)), hits)
        check("from three different brands", len({x["brand"] for x in hits}) == 3, hits)
        check("the paint itself is never offered as its own match", all(x["name"] != "Probe Source" for x in hits), hits)
        check("your near-identical paint is the best match, and is yours", hits[0]["name"] == "Owned Twin" and hits[0]["owned"] is True, hits[0])
        check("an example paint is never offered", not data["ghostInPool"] and all(x["name"] != "Ghost Twin" for x in hits))
        check("nothing on the skip list is in the pool", data["skipInPool"] == 0, data["skipInPool"])
        check("every skip-list name is a real paint in the built-in list (no typos)", data["real"] == [], data["real"])
        tamiya = [n for b, n in data["tableNames"] if b == "Tamiya"]
        check("all 15 Tamiya paints stored as white are on the skip list", all(n in tamiya for n in SKIP_15_TAMIYA), [n for n in SKIP_15_TAMIYA if n not in tamiya])
        check("the skip list is exact, not a wide word match: the Tamiya paint 'Medium sea gray 2' (a real colour) is still offered",
              page.evaluate("() => similarPool().some(p => p.brand === 'Tamiya' && p.name === 'Medium sea gray 2')"))
        check("a colour named Medium (Vallejo Medium Flesh) is still offered", page.evaluate("() => similarPool().some(p => p.brand === 'Vallejo' && p.name === 'Medium Flesh')"))
        check("the pool is the built-in list minus the skip list, plus your own real paints",
              data["poolSize"] == data["searched"] - page.evaluate("() => searchedPaints.filter(p => NOT_A_COLOUR.has(paintKey(p))).length") + 2, (data["poolSize"], data["searched"]))
        # offered for a white-ish colour: a white target never gets a varnish
        white = page.evaluate("""() => similarBestMatches({ brand: 'Test', name: 'Probe White', colour: '#ffffff' }, 0)
            .map(h => h.paint.brand + '|' + h.paint.name)""")
        check("a white target is never answered with a varnish, medium, thinner or the skipped white Tamiya paints",
              all(not re.search(r"varnish|medium|thinner|reducer|retarder|cleaner|clear base", w, re.I) for w in white) and not any(n in " ".join(white) for n in SKIP_15_TAMIYA), white)
        # many palette paints of one brand do not crowd out other brands
        crowd = [SOURCE] + [P(10 + i, "Crowd", f"Crowd Blue {i}", "#3a6ea5" if i == 0 else "#3a6ea" + str(i), status="owned") for i in range(1, 6)]
        load(page, paints=crowd)
        brands = page.evaluate("() => similarBestMatches(book.paints[0], 0).map(h => h.paint.brand)")
        check("one brand never fills all three places while other brands have paints", len(set(brands)) == 3, brands)
        # fewer than three brands: the next closest fills in
        few = page.evaluate("""() => { const saved = searchedPaints, mine = book.paints; book.paints = [mine[0]]; searchedPaints = [{ brand: 'OnlyBrand', name: 'A', colour: '#3a6ea6' }, { brand: 'OnlyBrand', name: 'B', colour: '#3a6ea7' },
            { brand: 'OnlyBrand', name: 'C', colour: '#3a6ea8' }, { brand: 'OnlyBrand', name: 'D', colour: '#3a6ea9' }];
            const out = similarBestMatches(book.paints[0], 0).map(h => h.paint.name); searchedPaints = saved; book.paints = mine; return out; }""")
        check("with only one brand available, the next closest paints fill the three places", few == ["A", "B", "C"], few)
        # nothing to offer: a short line, no crash
        none = page.evaluate("""() => { const keep = [book.paints, searchedPaints]; book.paints = []; searchedPaints = [];
            const out = similarBestMatches({ brand: 'X', name: 'Lone', colour: '#112233' }, 0).length;
            openSimilarPaints({ brand: 'X', name: 'Lone', colour: '#112233' }, null);
            const line = document.querySelector('.similar-none'); const shown = !line.classList.contains('hidden') && line.textContent;
            closeSimilar(); book.paints = keep[0]; searchedPaints = keep[1]; return [out, shown]; }""")
        check("no paints to offer: an empty list and one short line, no error", none == [0, "No similar paints found."], none)

        # ---------- 5. Lighter and Darker ----------
        print("\n--- 5. Lighter and Darker ---")
        load(page, paints=PALETTE)
        lum = page.evaluate("""() => {
            const L = (hits) => hits.reduce((a, h) => a + MinifolioColour.hexToHsl(h.paint.colour).l, 0) / hits.length;
            const src = book.paints[0];
            return { lighter: L(similarBestMatches(src, SIMILAR_SHIFT.lighter)), close: L(similarBestMatches(src, 0)), darker: L(similarBestMatches(src, SIMILAR_SHIFT.darker)) } }""")
        check("Lighter finds lighter paints and Darker finds darker ones", lum["lighter"] > lum["close"] > lum["darker"], lum)
        check("Close looks for the paint's own colour", page.evaluate("() => similarTarget('#3a6ea5', 0)") == "#3a6ea5")
        check("the shift never goes past black or white", page.evaluate("() => [similarTarget('#050505', -0.12), similarTarget('#fafafa', 0.12)].every(x => /^#[0-9a-f]{6}$/.test(x))"))
        open_popup_for(page)
        before = [r["name"] for r in rows(page)]
        page.click(".similar-shift button:has-text('Lighter')")
        page.wait_for_timeout(150)
        pressed = page.evaluate("() => [...document.querySelectorAll('.similar-shift button')].map(b => b.getAttribute('aria-pressed'))")
        lighter_rows = [r["name"] for r in rows(page)]
        check("tapping Lighter presses it (Close lets go) and changes the list", pressed == ["true", "false", "false"] and lighter_rows != before, (pressed, before, lighter_rows))
        page.click(".similar-shift button:has-text('Darker')")
        page.wait_for_timeout(150)
        darker_rows = [r["name"] for r in rows(page)]
        check("Darker gives a different list again, and Close brings the first one back", darker_rows != lighter_rows)
        page.click(".similar-shift button:has-text('Close')")
        page.wait_for_timeout(150)
        check("Close brings the first list back", [r["name"] for r in rows(page)] == before)
        check("the pressed choice is not shown by colour alone: it is aria-pressed and has a thicker outline",
              page.evaluate("() => { const b = document.querySelector('.similar-shift button[aria-pressed=true]'); const o = document.querySelector('.similar-shift button[aria-pressed=false]');"
                            " return getComputedStyle(b).boxShadow !== 'none' && getComputedStyle(o).boxShadow === 'none'; }"))
        page.keyboard.press("Escape")

        # ---------- 6. Add to shopping list ----------
        print("\n--- 6. Add to shopping list ---")
        load(page, paints=PALETTE)
        open_popup_for(page)
        got = rows(page)
        check("the paint you own says so and has no Add button; the others have one",
              got[0]["own"] and got[0]["add"] is None and all(not r["own"] and r["add"] == "Add to shopping list" for r in got[1:]), got)
        target = got[1]["name"]
        row = page.locator(".similar-row").nth(1)
        al = row.locator(".similar-add").get_attribute("aria-label")
        check("the Add button's aria-label is the action only", al == "Add to shopping list" and target not in al, al)
        row.locator(".similar-add").click()
        page.wait_for_timeout(250)
        entry_now = palette_entry(page, target)
        check("the paint is in Your Palette as Wishlist", entry_now and entry_now.get("status") == "wishlist", entry_now)
        check("the row says it is on the shopping list, and the button stays where it was (focus is not lost)",
              row.locator(".similar-add").inner_text() == "On your shopping list" and row.locator(".similar-add").get_attribute("aria-disabled") == "true"
              and page.evaluate("() => document.activeElement.classList.contains('similar-add')"))
        check("the Added line shows with an Undo", page.is_visible("#toast-undo") and target in page.inner_text("#toast-text"), page.inner_text("#toast-text"))
        above = page.evaluate("""() => { const r = document.getElementById('toast').getBoundingClientRect();
            const el = document.elementFromPoint(r.left + r.width / 2, r.top + r.height / 2); return !!el && document.getElementById('toast').contains(el); }""")
        check("the Undo line sits above the pop-up (you can see and tap it)", above)
        row.locator(".similar-add").dispatch_event("click")   # (Playwright will not press a button marked aria-disabled, a finger can)
        page.wait_for_timeout(150)
        check("tapping a paint that is already listed does nothing more", palette_entry(page, target).get("status") == "wishlist")
        page.click("#toast-undo")
        page.wait_for_timeout(300)
        check("Undo takes it off the list again", (palette_entry(page, target) or {}).get("status", "") == "")
        check("and the pop-up is still open, with the Add button back", popup_open(page) and page.locator(".similar-row").nth(1).locator(".similar-add").inner_text() == "Add to shopping list")
        page.keyboard.press("Escape")

        # ---------- 7. Closing and focus ----------
        print("\n--- 7. Closing ---")
        open_ideas(page, h.JUST_BLUE)
        opener = open_popup_from_row(page)
        check("focus starts inside the pop-up", page.evaluate("() => !!document.activeElement.closest('.similar')"))
        page.keyboard.press("Escape")
        page.wait_for_timeout(150)
        back_on = page.evaluate("() => document.activeElement.textContent") == "Similar paints"
        check("Escape closes it and focus is back on the Similar paints button", not popup_open(page) and back_on)
        open_popup_from_row(page)
        for _ in range(12):
            page.keyboard.press("Tab")
        check("Tab stays inside the pop-up", page.evaluate("() => !!document.activeElement.closest('.similar')"))
        page.click(".similar-head button")
        page.wait_for_timeout(150)
        check("the close button closes it, focus back on the opener", not popup_open(page) and page.evaluate("() => document.activeElement.textContent") == "Similar paints")
        open_popup_from_row(page)
        page.mouse.click(4, 400)   # the dimmed area outside the card
        page.wait_for_timeout(150)
        check("a tap on the dimmed area closes it", not popup_open(page))
        open_popup_from_row(page)
        page.go_back()
        page.wait_for_timeout(300)
        check("the phone's Back button closes it", not popup_open(page))
        check("only one pop-up at a time: opening again does not stack", (open_popup_for(page, 0), open_popup_for(page, 0), page.locator(".similar-backdrop").count())[2] == 1)
        page.keyboard.press("Escape")

        # ---------- 8. Phones ----------
        print("\n--- 8. Phones, dark and light ---")
        for width in (390, 360):
            for scheme in ("dark", "light"):
                page.set_viewport_size({"width": width, "height": 844})
                page.emulate_media(color_scheme=scheme)
                open_ideas(page, h.JUST_BLUE)
                open_popup_from_row(page)
                sizes = page.evaluate("""() => [...document.querySelectorAll('.similar button')].map(b => { const r = b.getBoundingClientRect(); return [r.width, r.height]; })""")
                inside = page.evaluate("() => { const b = document.querySelector('.similar'); return b.scrollWidth <= b.clientWidth + 1 && b.getBoundingClientRect().left >= 15 && b.getBoundingClientRect().right <= window.innerWidth - 15; }")
                check(f"{width} px {scheme}: no sideways scroll, 16 px side margins, every button 44 px or more",
                      no_sideways(page) and inside and all(w >= 44 and hh >= 44 for w, hh in sizes), (sizes, inside))
                contrast = page.evaluate("""() => { const el = document.querySelector('.similar-note'); const bg = getComputedStyle(document.querySelector('.similar')).backgroundColor;
                    return [getComputedStyle(el).color, bg]; }""")
                lc, bc = t.luminance(t.rgb(contrast[0])), t.luminance(t.rgb(contrast[1]))
                ratio = (max(lc, bc) + 0.05) / (min(lc, bc) + 0.05)
                check(f"{width} px {scheme}: the small note is readable against the card (contrast 4.5 or more)", ratio >= 4.5, round(ratio, 2))
                page.screenshot(path=os.path.join(t.SHOTS, f"v65-similar-{width}-{scheme}.png")) if os.path.isdir(t.SHOTS) else None
                page.keyboard.press("Escape")
        page.emulate_media(color_scheme="dark")
        page.set_viewport_size({"width": 390, "height": 844})
        css = html[html.index("v65: the Similar paints pop-up"):html.index("/* ----- v14: banners at the top of the screen")]
        check("no colour is written into the pop-up's styles (no #hex, rgb or named colour): only the theme's variables",
              not re.search(r"#[0-9a-fA-F]{3,8}\b|rgba?\(|\b(white|black|red|blue|green|grey|gray)\b", re.sub(r"/\*.*?\*/", "", css, flags=re.S)), css[:200])
        code = app[app.index("v65: SIMILAR PAINTS"):app.index("---- v36: THE COLOUR WHEEL")]
        check("no colour is written into the pop-up's code either (swatches take the paint's own colour)", not re.search(r"#[0-9a-fA-F]{6}\b|rgba?\(", code))
        check("the new text has no em dash", "—" not in code)

        # ---------- 9. Errors ----------
        print("\n--- 9. Errors ---")
        check("no outside network requests (works offline)", not requests, requests[:3])
        check("no page errors", not errors, errors)
        check("no browser pop-ups", not dialogs, dialogs)
        browser.close()
    failed = results.count(False)
    print(f"\n{len(results) - failed} passed, {failed} failed")
    sys.exit(1 if failed else 0)

if __name__ == "__main__":
    main()
