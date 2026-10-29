"""v38 tests for Minifolio (Compendium 3): paint links in the colour wheel's lists.

What changed in the Compendium tab (Pro preview):
 - In the colour wheel's paint lists (and nowhere else yet) a paint is a button. Tapping it opens a short panel right under it with the colours that
   go with it (opposite, the two neighbours, the two in its triad, from the colour engine, yours first) and the starter schemes that use a similar colour.
 - It works with a keyboard (Enter, Space, Escape, Tab) and a screen reader (aria-expanded, aria-controls, a labelled group), on a phone, inside the
   wheel groups, and for paints revealed by Show all.
 - Reuse: the door flag door.links switches it on in the Compendium only. The rows are the shared buildIdeaItem rows, Copy as text is the shared
   buildShareRow, the matches come from the shared colour helpers. No new libraries, no new files, no links of any kind.

Checks:
1. Versions (v38 everywhere), the Updates entry, Help, wiring, no network, storage, innerHTML or links in the new code, nothing else touched.
2. The row: a button, closed state, the hint line, 44 px tall, only in the wheel lists.
3. The panel's content for a known colour: Opposite, Neighbours, Triad against paints made to be exact matches; yours first; never the paint itself;
   the starter schemes checked against an independent copy of the rule; a grey (accents), a metallic (rough note), the Copy as text.
4. Keyboard and screen reader: Enter, Space, Escape, Tab, focus, aria-expanded, aria-controls, the labelled group, one panel at a time.
5. Inside the wheel groups: Show all, tapping a revealed paint, Show fewer closes a panel whose paint goes away, the panel stays open when its paint stays.
6. Hostile text (text-injection test) and a text scan for Games Workshop and brand words.
7. Offline, speed, the recipe card and the other parts unchanged.
8. Phone widths 360, 375, 390 and 400 and a real touch phone.
9. Dark and light at 390 and 360 px: contrast.
Run all tests with `python3 tests/run_all.py`, or serve the repo folder and run this file on its own."""
import colorsys, os, re, subprocess, sys, time
from playwright.sync_api import sync_playwright
from launch_helpers import quiet
from launch_helpers import leave_launch

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import wheel_helpers as wh   # v43
from notice_watch import attach_notices
import test_v31 as t   # the helpers (loading the app, the palette, the colours) and the Games Workshop word lists

SHOTS, ROOT = t.SHOTS, t.ROOT
read, load, blur = t.read, t.load, t.blur
shot, no_sideways, rgb, contrast = t.shot, t.no_sideways, t.rgb, t.contrast
rec, unit, HOSTILE, HOSTILE_BRAND, PAINTS = t.rec, t.unit, t.HOSTILE, t.HOSTILE_BRAND, t.PAINTS
GW_WORDS, GW_MORE = t.GW_WORDS, t.GW_MORE
results = []

def check(name, ok, detail=""):
    results.append(bool(ok))
    print(("PASS " if ok else "FAIL ") + name + ("" if ok else f"  -> {detail}"))

BRAND_WORDS = re.compile(r"\b(citadel|vallejo|army painter|scale ?75|tamiya|games workshop|warhammer|amazon|ebay|etsy|shop|buy|store)\b", re.I)

def hx(h, s, l):
    r, g, b = colorsys.hls_to_rgb((h % 360) / 360, l, s)
    return "#%02x%02x%02x" % tuple(round(x * 255) for x in (r, g, b))

def P(pid, name, colour, status="owned", brand="Test Paints", **extra):
    return dict({"id": pid, "brand": brand, "name": name, "colour": colour, "status": status}, **extra)

# A made-up palette where every colour match for "Probe Blue" is an exact, owned paint (nothing here names a real paint).
BASE_HEX = "#2244aa"
_h, _l, _s = colorsys.rgb_to_hls(*[int(BASE_HEX[i:i + 2], 16) / 255 for i in (1, 3, 5)])
def at(deg):
    # v64: the Opposite of a colour darker than 0.45 lightness is lifted to 0.45 (saturation at least 0.55), so the paint planted exactly opposite is lifted the same way
    if deg == 180:
        return hx(_h * 360 + 180, max(_s, 0.55), max(_l, 0.45))
    return hx(_h * 360 + deg, _s, _l)
PAL = [P(1, "Probe Blue", BASE_HEX), P(2, "Probe Opposite", at(180)), P(3, "Probe Left", at(-30)), P(4, "Probe Right", at(30)),
       P(5, "Probe Triad A", at(120)), P(6, "Probe Triad B", at(240)), P(7, "Probe Grey", "#7f7f7f"), P(8, "Probe gold metal", "#c9a227")]
FIRST = lambda tag: tag

PANEL_JS = """() => { const p = document.getElementById('cmp-paint-panel'); if (!p) return null;
    const sections = []; let cur = null;
    for (const el of p.children) {
        if (el.classList.contains('paint-panel-label')) { cur = { label: el.textContent, rows: [], hints: [] }; sections.push(cur); }
        else if (el.tagName === 'UL' && cur) { for (const b of el.querySelectorAll('.idea-static')) cur.rows.push({ name: b.querySelector('.idea-name').childNodes[0].textContent,
            tag: b.querySelector('.idea-tag').textContent, why: b.querySelector('.idea-why').textContent, note: (b.querySelector('.idea-note') || {}).textContent || '' }); }
        else if (el.classList.contains('hint') && cur) cur.hints.push(el.textContent);
    }
    const intro = [...p.querySelectorAll(':scope > .hint')].filter(h => !sections.some(s => s.hints.includes(h.textContent)));
    return { title: p.querySelector('.paint-panel-title').textContent, titleId: p.querySelector('.paint-panel-title').id, intro: intro.map(h => h.textContent),
             sections, role: p.getAttribute('role'), labelledby: p.getAttribute('aria-labelledby'), tag: p.querySelector('.paint-panel-title').tagName }; }"""
EXPECT_SCHEMES_JS = """([c, rough]) => { const C = MinifolioColour;
    return STARTER_SCHEMES.map(s => ({ name: s.name, d: Math.min(...s.colours.map(k => C.colourDistance(c, k.hex))) }))
        .filter(x => x.d <= 15 * (rough ? 4 / 3 : 1)).sort((a, b) => a.d - b.d || a.name.localeCompare(b.name)); }"""
ROWS_JS = """() => [...document.querySelectorAll('#cmp-wheel-detail button.idea-link')].map(b => b.querySelector('.idea-name').childNodes[0].textContent)"""

def open_tab(page):
    blur(page)
    page.click('nav button[data-tab="compendium"]')
    quiet(page)

def tap(page, key):
    wh.tap(page, key)   # v43: a colour opens its groups first (see wheel_helpers.py); same meaning as before

def row(page, name):
    names = page.evaluate(ROWS_JS)
    return page.locator("#cmp-wheel-detail button.idea-link").nth(names.index(name))

def open_row(page, name, wait=120):
    row(page, name).click()
    quiet(page) if wait <= 300 else page.wait_for_timeout(wait)

def panel(page):
    return page.evaluate(PANEL_JS)

def panel_names(page):
    p = panel(page)
    return {s["label"]: [r["name"] for r in s["rows"]] for s in p["sections"]} if p else None

def copy_spy(page):
    page.evaluate("""() => { window.__copied = null;
        Object.defineProperty(navigator, 'clipboard', { configurable: true, value: { writeText: (x) => { window.__copied = x; return Promise.resolve(); } } }); }""")

def copied(page):
    page.wait_for_timeout(200)
    return page.evaluate("() => window.__copied")

def active(page):
    return page.evaluate("() => { const a = document.activeElement; return a ? { id: a.id, text: a.textContent.slice(0, 40), cls: a.className, tag: a.tagName } : null; }")

def main():
    with sync_playwright() as p:
        browser = p.chromium.launch()
        ctx = browser.new_context(viewport={"width": 390, "height": 844}, service_workers="block")
        page = ctx.new_page()
        errors, dialogs, requests = [], [], []
        page.on("pageerror", lambda e: errors.append(str(e)))
        page.on("dialog", lambda d: (dialogs.append(d.message), d.dismiss()))
        attach_notices(page, dialogs.append)
        page.on("request", lambda r: requests.append(r.url))

        # ---------- 1. Versions and wiring ----------
        print("\n--- 1. Versions and wiring ---")
        load(page, paints=PAL)
        app = read("app.js")
        root_js = sorted(f for f in os.listdir(ROOT) if f.endswith(".js") and f != "sw.js")
        entry = page.evaluate("CHANGELOG.find(r => r.version === 'v38')")
        joined = " ".join(entry["changes"]) if entry else ""
        if page.evaluate("['v34', 'v35', 'v36', 'v37'].every(v => CHANGELOG.some(r => r.version === v))"):
            check("the v37, v36, v35 and v34 entries are still there", page.evaluate("['v37', 'v36', 'v35', 'v34'].every(v => !!CHANGELOG.find(r => r.version === v))"))
        else:
            print("SKIP (entry no longer in the public Updates list): " + 'the v37, v36, v35 and v34 entries are still there')
        help_text = page.evaluate("() => document.getElementById('help-tabs').textContent")
        # v75: removed check "Help says a paint in the wheel can be tapped": Help's tab line is now one short sentence (v75, HELP-3), so it no longer describes the Compendium
        # (v47: early.js left this list; it now puts the theme on the page too.)
        new_code = app[app.index("v38: PAINT LINKS"):app.index("function buildWheelDetail(")] + app[app.index("v38: a door that has no recipe"):app.index("v35: how a door that has no recipe")]
        check("reuse, not copy: the panel is made from the shared row, the shared Copy as text, the shared colour helpers and the same nearest-paint search, and each is still defined once",
              all(w in new_code for w in ["buildIdeaItem(", "buildShareRow(", "colourIdeaWanted(", "colourIdeaReason(", "colourIdeaTag(", "colourIdeaPool(", "ideaTextLine(", "C.suggestPaint(", "C.harmonies(", "colourDistance("])
              and all(app.count(f"function {n}(") == 1 for n in ["buildIdeaItem", "buildShareRow", "colourIdeaWanted", "colourIdeaReason", "buildPaintPanel", "togglePaintPanel", "starterSchemesLike", "buildWheelDetail"]))
        door_c = app[app.index("function compendiumDoor"):app.index("function startRecipeFromCompendium")]
        card_door = app[app.index("function buildColourIdeasCard"):]
        card_door = card_door[:card_door.index("id: doorId,")]
        check("the door flag is the switch: the Compendium door has links: true, the recipe card's door has no such flag, and the door comment names door.links",
              "links: true" in door_c and "links" not in card_door and "door.links" in app)
        check("the panel's own sentences name no shop and the wheel code builds no web link", "createElement(\"a\")" not in app[app.index("v36: THE COLOUR WHEEL"):app.index("function renderCompendium(")])

        # ---------- 2. The row ----------
        print("\n--- 2. The row ---")
        open_tab(page)
        tap(page, "blue")
        hint = page.inner_text("#cmp-wheel-links-hint")
        # v75: COMP-9 shortened this line
        check("the open wheel part says a paint can be tapped (one plain line)", hint == "Tap a paint for colours that go with it.", hint)
        info = page.evaluate("""() => [...document.querySelectorAll('#cmp-wheel-detail ul.idea-list > li')].map(li => { const b = li.firstElementChild; const r = b.getBoundingClientRect();
            return { tag: b.tagName, type: b.type, exp: b.getAttribute('aria-expanded'), ctl: b.getAttribute('aria-controls'), label: b.getAttribute('aria-label'), h: r.height, kids: li.children.length,
                     open: (b.querySelector('.idea-open') || {}).textContent, cls: b.className }; })""")
        check("every paint in the open wheel part is a real button (type button) in its own list item, closed (aria-expanded false), controls nothing yet, says Matching colours and is 44 px tall",
              len(info) >= 2 and all(i["tag"] == "BUTTON" and i["type"] == "button" and i["exp"] == "false" and i["ctl"] is None and i["open"] == "Matching colours" and i["h"] >= 44 and i["kids"] == 1 for i in info), info[:2])
        check("a row has no aria-label of its own: its words (name, brand, tag, why, Matching colours) are its spoken name", all(i["label"] is None for i in info))
        check("the row keeps the classes the old rows had (idea idea-static), plus idea-link", all("idea" in i["cls"].split() and "idea-static" in i["cls"].split() and "idea-link" in i["cls"].split() for i in info))
        check("no panel is open at the start", page.locator(".paint-panel").count() == 0 and page.evaluate("() => compendiumState.paintOpen") == "")
        open_all = lambda: [page.click(f"#cmp-fold-{k}-button") for k in ["ideas", "history", "starter", "detail", "basing"]]
        open_all()
        page.click("#cmp-starter-search")
        page.fill("#cmp-starter-search", "blue")
        page.wait_for_timeout(100)
        links = page.evaluate("() => [...document.querySelectorAll('#compendium-body .idea-link')].map(b => !!b.closest('#cmp-wheel-detail'))")
        check("only the wheel's paint lists have these buttons: the ideas, your schemes, starter schemes, detail recipes and basing tips rows are unchanged (no idea-link anywhere else)", links and all(links) and len(links) == len(info))

        # ---------- 3. The panel's content ----------
        print("\n--- 3. The panel's content ---")
        open_row(page, "Probe Blue")
        pn = panel(page)
        check("tapping Probe Blue opens one panel with the title Matching colours for Probe Blue (Test Paints), as a heading inside a labelled group",
              pn and pn["title"] == "Matching colours for Probe Blue (Test Paints)" and pn["tag"] == "H5" and pn["role"] == "group" and pn["labelledby"] == pn["titleId"] and page.locator(".paint-panel").count() == 1, pn and pn["title"])
        li_kids = page.evaluate("() => { const p = document.getElementById('cmp-paint-panel'); return [p.parentElement.tagName, p.previousElementSibling.tagName, p.previousElementSibling.getAttribute('aria-expanded'), p.previousElementSibling.getAttribute('aria-controls')]; }")
        check("the panel sits in the same list item, straight after the paint's button, which now says expanded and controls it", li_kids == ["LI", "BUTTON", "true", "cmp-paint-panel"], li_kids)
        check("the intro says its colour (blue) and that yours come first", pn["intro"] == ["Its colour is blue. These go with it, yours first."], pn["intro"])
        names = {s["label"]: [r["name"] for r in s["rows"]] for s in pn["sections"]}
        check("the groups are Opposite, Neighbours, Triad and the starter schemes, in that order", [s["label"] for s in pn["sections"]] == ["Opposite", "Neighbours", "Triad", "Starter schemes with a similar colour"], [s["label"] for s in pn["sections"]])
        check("known answers: the opposite is the paint made exactly opposite, the neighbours are the ones 30 degrees either side, the triad the ones 120 and 240 degrees round (all yours, so all You own this)",
              names["Opposite"] == ["Probe Opposite"] and names["Neighbours"] == ["Probe Left", "Probe Right"] and names["Triad"] == ["Probe Triad A", "Probe Triad B"]
              and all(r["tag"] == "You own this" for s in pn["sections"][:3] for r in s["rows"]), names)
        check("the paint itself is never offered as its own match, and no paint shows twice in the colour rows",
              "Probe Blue" not in sum(names.values(), []) and len(set(sum([names[k] for k in ["Opposite", "Neighbours", "Triad"]], []))) == 5)
        why = [r["why"] for s in pn["sections"][:3] for r in s["rows"]]
        check("each row says why in plain colour words (opposite, next to, evenly spaced) and never repeats a paint name", all(w.endswith((".", "calmly.", "clash.")) for w in why)
              and "opposite" in why[0] and "right next to" in why[1] and "spaced evenly" in why[3] and not any("Probe" in w for w in why), why)
        # the starter schemes, against an independent copy of the rule
        want = page.evaluate(EXPECT_SCHEMES_JS, [BASE_HEX, False])
        sec = pn["sections"][3]
        listed = [r["name"] for r in sec["rows"]]
        check("starter schemes: exactly the closest three of the schemes with a colour within reach (checked against an independent copy of the rule), closest first",
              len(want) >= 4 and listed == [w["name"] for w in want[:3]], (listed, [w["name"] for w in want[:6]]))
        check("a line says how many there are when there are more than three, and each row says which colour part matched and how close", (len(want) > 3) == any(f"Showing the 3 closest of {len(want)}." in h for h in sec["hints"])
              and all(re.match(r"^[A-Z][a-z ]+: .+\.$", r["why"]) and r["tag"] in ("Very close colour", "Similar colour") for r in sec["rows"]), (sec["hints"], sec["rows"][0]))
        check("and a scheme row shows the scheme's own summary line as its note", all(r["note"] and r["note"] == page.evaluate("(n) => STARTER_SCHEMES.find(s => s.name === n).summary", r["name"]) for r in sec["rows"]))
        # yours first: a wishlist paint exactly opposite, an owned one a little off
        load(page, paints=[P(1, "Probe Blue", BASE_HEX), P(2, "Wish Opposite", at(180), status="wishlist"), P(3, "Own Near Opposite", at(180 + 14))])
        open_tab(page)
        tap(page, "blue")
        open_row(page, "Probe Blue")
        names2 = panel_names(page)
        check("yours first: an owned paint a little off beats a closer paint that is only on the wishlist (Closest you own)", names2["Opposite"] == ["Own Near Opposite"] and
              panel(page)["sections"][0]["rows"][0]["tag"] in ("You own this", "Yours, poor fit"), names2)
        load(page, paints=[P(1, "Probe Blue", BASE_HEX)])
        open_tab(page)
        tap(page, "blue")
        open_row(page, "Probe Blue")
        pn3 = panel(page)
        check("with only built-in paints to offer, the rows say Not in your palette (honest tags) and the panel still has all three groups", pn3 and [s["label"] for s in pn3["sections"]][:3] == ["Opposite", "Neighbours", "Triad"]
              and all(r["tag"] == "Not in your palette" for s in pn3["sections"][:3] for r in s["rows"]) and sum(len(s["rows"]) for s in pn3["sections"][:3]) == 5)
        # a grey has no true opposite
        load(page, paints=PAL)
        open_tab(page)
        tap(page, "grey")
        open_row(page, "Probe Grey")
        pg = panel(page)
        check("a grey says it is neutral and has no true opposite, and offers three accents (no Opposite, Neighbours or Triad headings)",
              pg and "neutral" in pg["intro"][0] and "no true opposite" in pg["intro"][0] and [s["label"] for s in pg["sections"]][0] == "Accents that stand out"
              and len(pg["sections"][0]["rows"]) == 3 and not any(s["label"] in ("Opposite", "Neighbours", "Triad") for s in pg["sections"]), pg and (pg["intro"], [s["label"] for s in pg["sections"]]))
        check("the accents are three different colours' worth of paints and each says it is an accent", len({r["name"] for r in pg["sections"][0]["rows"]}) == 3 and all("accent" in r["why"] for r in pg["sections"][0]["rows"]), [r["why"] for r in pg["sections"][0]["rows"]])
        # a metallic is only a guide
        tap(page, "metallic")
        open_row(page, "Probe gold metal")
        pm = panel(page)
        check("a metallic says its colour is only a guide, so the matches are too", pm and any("only a guide for this kind of paint" in h and "matches are only a guide too" in h for h in pm["intro"]), pm and pm["intro"])
        want_m = page.evaluate(EXPECT_SCHEMES_JS, ["#c9a227", True])
        check("and for a metallic the starter schemes use the looser reach (a third more), checked the same independent way", [r["name"] for r in pm["sections"][-1]["rows"]] == [w["name"] for w in want_m[:3]], ([r["name"] for r in pm["sections"][-1]["rows"]], [w["name"] for w in want_m[:3]]))
        # Copy as text
        copy_spy(page)
        page.click("#cmp-paint-panel .share-row button")
        text = copied(page)
        check("Copy as text in the panel copies the title, the group names, the rows and the footer, as plain text", text and text.startswith("Matching colours for Probe gold metal (Test Paints)") and "Starter schemes with a similar colour" in text
              and "Colours on a screen are only a guide" in text and "<" not in text and text.count("\n- ") >= 4, (text or "")[:200])
        # v62: the panel's paint now has Use in a recipe and Add to a recipe at the top, so the panel has those two plus Copy as text (still no Save into a new recipe). v65: and a third, Similar paints, in the same row (so 3 buttons there)
        check("and the panel has Copy as text plus the v62 paint buttons and (v65) Similar paints, only (no Save into a new recipe, no links inside)", page.locator("#cmp-paint-panel .share-row button").count() == 1 and page.locator("#cmp-paint-panel > .paint-recipe .paint-recipe-buttons button").count() == 3 and page.locator("#cmp-paint-panel a:not(.shop-more a), #cmp-paint-panel [href]:not(.shop-more *), #cmp-paint-panel [role=link]:not(.shop-more *)").count() == 0)   # v64: a paint you do not own can sit in the panel (a poor owned match no longer goes first), and it has the v39 Shop links fold-out

        # ---------- 4. Keyboard and screen reader ----------
        print("\n--- 4. Keyboard and screen reader ---")
        load(page, paints=PAL)
        open_tab(page)
        tap(page, "blue")
        btn_sel = "#cmp-wheel-detail button.idea-link"
        names_in = page.evaluate(ROWS_JS)
        i_blue = names_in.index("Probe Blue")
        page.locator(btn_sel).nth(i_blue).focus()
        page.keyboard.press("Enter")
        page.wait_for_timeout(100)
        check("Enter on a focused paint opens its panel, and the focus stays on the paint", page.locator(".paint-panel").count() == 1 and page.locator(btn_sel).nth(i_blue).get_attribute("aria-expanded") == "true" and active(page)["cls"].split()[-1] == "idea-link")
        page.keyboard.press("Enter")
        page.wait_for_timeout(100)
        check("Enter again closes it (aria-expanded false, no aria-controls, panel gone)", page.locator(".paint-panel").count() == 0 and page.locator(btn_sel).nth(i_blue).get_attribute("aria-expanded") == "false"
              and page.locator(btn_sel).nth(i_blue).get_attribute("aria-controls") is None)
        page.keyboard.press("Space")
        page.wait_for_timeout(100)
        check("Space opens it too", page.locator(".paint-panel").count() == 1)
        page.keyboard.press("Tab")
        a = active(page)
        # v62: the first tap target in the panel is now Use in a recipe (Copy as text is still in the panel, after the two v62 buttons)
        check("Tab goes from the paint into the panel (to its first button), not past it", a["text"] == "Use in a recipe" and page.evaluate("() => !!document.activeElement.closest('#cmp-paint-panel')"), a)
        page.keyboard.press("Escape")
        page.wait_for_timeout(100)
        a = active(page)
        check("Escape from inside the panel closes it and puts the focus back on the paint that opened it", page.locator(".paint-panel").count() == 0 and a["cls"].split()[-1] == "idea-link"
              and page.evaluate("() => document.activeElement.querySelector('.idea-name').childNodes[0].textContent") == "Probe Blue", a)
        page.keyboard.press("Escape")
        check("Escape with nothing open does nothing (no error, still on the paint)", page.locator(".paint-panel").count() == 0 and active(page)["cls"].split()[-1] == "idea-link")
        page.keyboard.press("Space")
        page.wait_for_timeout(100)
        page.keyboard.press("Escape")
        page.wait_for_timeout(100)
        check("Escape on the paint itself closes the panel too", page.locator(".paint-panel").count() == 0)
        # screen reader facts
        open_row(page, "Probe Blue")
        sr = page.evaluate("""() => { const p = document.getElementById('cmp-paint-panel'), b = p.previousElementSibling, t = document.getElementById(p.getAttribute('aria-labelledby'));
            const heads = [...document.querySelectorAll('#cmp-wheel-detail h3, #cmp-wheel-detail h4, #cmp-wheel-detail h5')].map(h => h.tagName);
            return { ctl: b.getAttribute('aria-controls') === p.id, named: t && t.textContent, ids: [...document.querySelectorAll('[id]')].map(e => e.id).filter((x, i, a) => a.indexOf(x) !== i),
                     hidden: p.closest('[aria-hidden=true], [hidden]') === null, lists: p.querySelectorAll('ul > li').length, heads, tabbable: [...p.querySelectorAll('[tabindex]')].map(e => e.tabIndex) }; }""")
        check("for a screen reader: the button says expanded and points at the panel, the panel is a group named by its heading, it is not hidden, its rows are real list items, no odd tabindex, and no id appears twice",
              sr["ctl"] and sr["named"].startswith("Matching colours for") and sr["hidden"] and sr["lists"] >= 6 and sr["tabbable"] == [] and sr["ids"] == [], sr)
        check("the headings stay in order (the wheel part h3, groups h4, the panel h5)", "H5" in sr["heads"] and sr["heads"][:1] == ["H3"] and "H4" in sr["heads"], sr["heads"])
        # one at a time, and switching parts
        open_row(page, "Probe Left")
        check("opening a second paint closes the first (one panel at a time)", page.locator(".paint-panel").count() == 1 and panel(page)["title"].startswith("Matching colours for Probe Left")
              and page.locator(btn_sel).nth(i_blue).get_attribute("aria-expanded") == "false" and page.locator(btn_sel + '[aria-expanded="true"]').count() == 1)
        tap(page, "red")
        tap(page, "blue")
        check("switching to another colour part and back never carries a panel over", page.locator(".paint-panel").count() == 0 and page.evaluate("() => compendiumState.paintOpen") == "")
        open_row(page, "Probe Blue")
        tap(page, "blue")   # v43: back up to the whole wheel
        check("closing the wheel part removes the panel with it, and the state is clear", page.locator(".paint-panel").count() == 0 and page.evaluate("() => compendiumState.paintOpen") == "")
        tap(page, "blue")
        open_row(page, "Probe Blue")
        page.click('nav button[data-tab="dashboard"]')
        page.wait_for_timeout(150)
        page.click('nav button[data-tab="compendium"]')
        page.wait_for_timeout(250)
        ok_back = page.locator(".paint-panel").count() == page.locator(btn_sel + '[aria-expanded="true"]').count()
        check("leaving the tab and coming back keeps the page consistent (a panel is shown only with its button open, never two, never a stale one)", ok_back and page.locator(".paint-panel").count() <= 1)
        page.reload()
        page.wait_for_function("() => typeof APP_VERSION === 'string'")
        leave_launch(page)   # U4b: tap through the start page
        open_tab(page)
        check("closing and reopening the app starts with nothing open", page.locator(".paint-panel").count() == 0 and page.evaluate("() => compendiumState.paintOpen") == "")

        # ---------- 5. Inside the wheel groups ----------
        print("\n--- 5. Inside the wheel groups: Show all ---")
        load(page, paints=PAL)
        open_tab(page)
        wh.zoom_in(page, "blue")
        wh.open_group(page, "blue", "blue")   # v43: the Blues group, opened by itself
        page.click("#cmp-wheel-others")
        page.wait_for_timeout(150)
        total_blue = page.evaluate("() => wheelItems().filter(x => x.at.seg === 'blue' && x.at.sub === 'blue').length")
        check("the Blues group has more than eight paints, so it starts collapsed behind Show all", total_blue > 9 and page.get_attribute("#cmp-wheel-more-blue", "aria-expanded") == "false")
        before = page.evaluate("""() => [...document.querySelectorAll('#cmp-wheel-detail ul.idea-list')][0].querySelectorAll('li').length""")
        page.click("#cmp-wheel-more-blue")
        page.wait_for_timeout(150)
        grp = page.evaluate("""() => { const ul = [...document.querySelectorAll('#cmp-wheel-detail ul.idea-list')][0]; return [...ul.querySelectorAll(':scope > li > button.idea-link .idea-name')].map(n => n.childNodes[0].textContent); }""")
        check("Show all reveals the rest, and every revealed paint is a button too", len(grp) == total_blue > before and page.locator("#cmp-wheel-detail li > .idea-link").count() >= total_blue)
        last_name = grp[-1]
        open_row(page, last_name)
        pl = panel(page)
        check("tapping the very last paint, which was hidden before Show all, opens its panel", pl and pl["title"].startswith(f"Matching colours for {last_name}") and page.locator(".paint-panel").count() == 1, pl and pl["title"])
        check("the panel for a built-in paint is complete (three groups, five matches, the schemes group)", [s["label"] for s in pl["sections"]][:3] == ["Opposite", "Neighbours", "Triad"] and sum(len(s["rows"]) for s in pl["sections"][:3]) == 5)
        page.click("#cmp-wheel-more-blue")
        page.wait_for_timeout(150)
        check("Show fewer puts the paint away, so its panel goes with it, nothing stale is kept, and the focus is on the Show all button",
              page.locator(".paint-panel").count() == 0 and page.evaluate("() => compendiumState.paintOpen") == "" and active(page)["id"] == "cmp-wheel-more-blue" and page.inner_text("#cmp-wheel-more-blue").startswith("Show all"))
        page.click("#cmp-wheel-more-blue")
        page.wait_for_timeout(150)
        check("Show all again does not bring the panel back (it was closed on purpose)", page.locator(".paint-panel").count() == 0)
        page.click("#cmp-wheel-more-blue")
        page.wait_for_timeout(100)
        open_row(page, "Probe Blue")
        page.click("#cmp-wheel-more-blue")
        page.wait_for_timeout(150)
        check("when the paint with the open panel stays on show (Show all, then Show fewer), its panel stays open", page.locator(".paint-panel").count() == 1 and panel(page)["title"].startswith("Matching colours for Probe Blue"))
        navy = page.locator('#cmp-wheel-detail button[id^="cmp-wheel-more-"]')
        if navy.count() > 1:
            other = navy.nth(0)
            other.click()
            page.wait_for_timeout(150)
            check("pressing Show all on a different group leaves the open panel alone", page.locator(".paint-panel").count() == 1 and panel(page)["title"].startswith("Matching colours for Probe Blue"))
        page.click("#cmp-wheel-others")
        page.wait_for_timeout(150)
        check("Hide other paints keeps the panel of one of yours (Probe Blue is yours)", page.locator(".paint-panel").count() == 1)
        tap(page, "blue")
        tap(page, "blue")
        page.click("#cmp-wheel-others")
        page.wait_for_timeout(100)
        built = page.evaluate("() => wheelItems().filter(x => x.at.seg === 'blue' && x.origin === 2).length")
        open_row(page, page.evaluate(ROWS_JS)[-1])
        page.click("#cmp-wheel-others")
        page.wait_for_timeout(150)
        check("Hide other paints closes the panel of a built-in paint that goes away", built > 0 and page.locator(".paint-panel").count() == 0 and page.evaluate("() => compendiumState.paintOpen") == "")
        ids = page.evaluate("() => { const ids = [...document.querySelectorAll('[id]')].map(e => e.id); return ids.filter((x, i) => ids.indexOf(x) !== i); }")
        check("no page id appears twice and every id the panel adds starts with cmp-", ids == [] and page.evaluate("() => [...document.querySelectorAll('#compendium-body [id]')].every(e => e.id.startsWith('cmp-'))"))

        # ---------- 6. Hostile text and the text scan ----------
        print("\n--- 6. Hostile text and the text scan ---")
        evil = [P(1, "Probe Blue", BASE_HEX), P(90, HOSTILE, "#2244aa", brand=HOSTILE_BRAND), P(91, HOSTILE + " Match", at(180), brand=HOSTILE_BRAND), P(92, "Evil <i>Left</i>", at(-30), brand=HOSTILE_BRAND)]
        load(page, paints=evil)
        open_tab(page)
        tap(page, "blue")
        copy_spy(page)
        open_row(page, HOSTILE)
        pe = panel(page)
        check("a hostile paint name in the panel's title is plain text (it shows as typed), and no script runs", pe and "<img src=x" in pe["title"] and page.locator("#cmp-paint-panel img, #cmp-paint-panel b, #cmp-paint-panel i, #cmp-paint-panel script").count() == 0
              and page.evaluate("() => window.__pwned") is None, pe and pe["title"])
        open_row(page, "Probe Blue")
        pe2 = panel(page)
        match_names = [r["name"] for s in pe2["sections"][:3] for r in s["rows"]]
        check("a hostile name as a match is plain text too (Opposite and Neighbours show it as typed), with no element made from it", any("<img src=x" in n for n in match_names) and any("<i>Left</i>" in n for n in match_names)
              and page.locator("#view-compendium img, #view-compendium script, #view-compendium b, #view-compendium i, #view-compendium iframe").count() == 0 and page.evaluate("() => window.__pwned") is None, match_names)
        page.click("#cmp-paint-panel .share-row button")
        text = copied(page)
        check("and Copy as text keeps the hostile name as plain text", text and "<img src=x" in text and "<i>Left</i>" in text)
        check("the button's attributes are not broken by the name (aria-expanded and aria-controls are exactly what they should be)", page.evaluate("() => [...document.querySelectorAll('#cmp-wheel-detail button.idea-link')].every(b => ['true', 'false'].includes(b.getAttribute('aria-expanded')) && (b.getAttribute('aria-controls') || 'cmp-paint-panel') === 'cmp-paint-panel')"))
        # the text scan over everything we wrote in the panel
        load(page, paints=PAL)
        open_tab(page)
        shown = []
        def grab():
            shown.append(page.evaluate("""() => { const p = document.getElementById('cmp-paint-panel'); if (!p) return '';
                const c = p.cloneNode(true); c.querySelectorAll('.idea-name, .paint-panel-title, .shop-more').forEach(e => e.remove());   // v64: .shop-more is the v39 Shop links fold-out on a paint you do not own (test_v39 covers its words)
                return c.innerText + ' ' + [...c.querySelectorAll('[aria-label], title')].map(e => e.getAttribute('aria-label') || e.textContent).join(' '); }"""))
        for key, name in [("blue", "Probe Blue"), ("grey", "Probe Grey"), ("metallic", "Probe gold metal")]:
            tap(page, key)
            open_row(page, name)
            grab()
            tap(page, key)
        everything = "\n".join(shown)
        hits = GW_WORDS.findall(everything) + GW_MORE.findall(everything)
        check("everything we wrote in the panels (intro, group names, reasons, tags, notes, buttons) names no Games Workshop game, faction, scheme, paint or product",
              not hits and all(w in everything for w in ["Opposite", "Neighbours", "Triad", "Starter schemes with a similar colour", "Accents that stand out", "yours first", "Copy as text"]), (hits[:10], everything[:200]))
        own = "\n".join([joined, help_text, new_code, "Tap a paint to see colours that go with it, and starter schemes with a similar colour.", "Matching colours"])
        own_hits = GW_WORDS.findall(own) + GW_MORE.findall(own)
        check("there are no links at all in the new parts (no shop links, no web links of any kind)", page.locator("#compendium-body a, #compendium-body [href], #compendium-body [role=link]").count() == 0)

        # ---------- 7. Offline, speed, nothing else changed ----------
        print("\n--- 7. Offline, speed, nothing else changed ---")
        load(page, paints=PAL, recipes=[rec(101, "Armour blue", "Whole model", [1, 22])], units=[unit(1, "Troop A", "Gloom Legion", [101])])
        mark = len(requests)
        open_tab(page)
        ctx.set_offline(True)
        tap(page, "blue")
        page.click("#cmp-wheel-others")
        open_row(page, "Probe Blue")
        ok_off = page.locator(".paint-panel").count() == 1 and sum(len(s["rows"]) for s in panel(page)["sections"][:3]) == 5
        ctx.set_offline(False)
        outside = [u for u in requests[mark:] if not u.startswith(t.BASE) and not u.startswith("data:") and not u.startswith("blob:")]
        check("it works with the network off, and nothing outside the app was asked for", ok_off and not outside, outside[:3])
        page.evaluate("() => { window.__t = []; }")
        name_last = page.evaluate(ROWS_JS)[-1]
        t0 = time.time()
        row(page, name_last).click()
        page.wait_for_function("() => !!document.getElementById('cmp-paint-panel')")
        took = (time.time() - t0) * 1000
        check("opening a panel with 1,200 built-in paints to search is quick (under a second, including the click)", took < 1000, round(took))
        open_row(page, name_last)
        t.edit_recipe(page, 101)
        t.open_panel(page)
        check("the Colour ideas card in a recipe is unchanged: no panel, no idea-link, its rows still say how to add a step",
              page.locator("#colour-ideas .idea-link, #colour-ideas .paint-panel").count() == 0 and page.locator("#colour-ideas .idea-add").count() >= 3)
        load(page, paints=PAL)
        open_tab(page)
        ring = page.evaluate("() => [...document.querySelectorAll('#cmp-wheel path.wheel-seg')].map(e => e.dataset.wheel)")
        check("the wheel still has its ten slices in the same order and the same hint line", ring == ["red", "orange", "yellow", "green", "blue", "purple", "white", "grey", "black", "metallic"]
              and page.inner_text("#cmp-wheel-hint") == "Tap a colour to see what's in it")

        # ---------- 8. Phone widths ----------
        print("\n--- 8. Phone widths 360, 375, 390 and 400 ---")
        for width in (360, 375, 390, 400):
            page.set_viewport_size({"width": width, "height": 800})
            load(page, paints=PAL)
            open_tab(page)
            tap(page, "blue")
            page.click("#cmp-wheel-others")
            page.click("#cmp-wheel-more-blue")
            page.wait_for_timeout(150)
            open_row(page, "Probe Blue")
            geo = page.evaluate("""() => { const card = document.querySelector('#view-compendium .card').getBoundingClientRect(), p = document.getElementById('cmp-paint-panel'), pr = p.getBoundingClientRect();
                const out = [...p.querySelectorAll('*')].filter(e => { const r = e.getBoundingClientRect(); return r.width > 0 && (r.right > card.right + 0.5 || r.left < card.left - 0.5); }).map(e => e.className || e.tagName);
                const btn = p.querySelector('.share-row button').getBoundingClientRect(), row = p.previousElementSibling.getBoundingClientRect();
                return { inCard: pr.left >= card.left - 0.5 && pr.right <= card.right + 0.5, out, w: pr.width, copyH: btn.height, rowH: row.height, vw: window.innerWidth, sw: document.documentElement.scrollWidth }; }""")
            check(f"at {width} px the open panel is inside the card, nothing in it pokes out, the Copy button and the paint row are 44 px tall and nothing scrolls sideways", geo["inCard"] and not geo["out"] and geo["copyH"] >= 44 and geo["rowH"] >= 44 and no_sideways(page), geo)
            open_row(page, page.evaluate(ROWS_JS)[-1])
            check(f"at {width} px the panel for the very last paint of a long group fits too", panel(page) is not None and no_sideways(page) and page.evaluate("""() => { const c = document.querySelector('#view-compendium .card').getBoundingClientRect(), r = document.getElementById('cmp-paint-panel').getBoundingClientRect(); return r.left >= c.left - 0.5 && r.right <= c.right + 0.5; }"""))
            visible = page.evaluate("""() => { const r = document.getElementById('cmp-paint-panel').getBoundingClientRect(); return r.top < window.innerHeight && r.bottom > 0; }""")
            check(f"at {width} px opening a panel brings it into view (it is not left below the screen)", visible)
            tap_long = page.evaluate("() => { const l = [...document.querySelectorAll('#cmp-wheel-detail .idea-name')].map(n => n.textContent.length); return Math.max(...l); }")
            if width in (360, 400):
                page.evaluate("() => document.getElementById('cmp-paint-panel').scrollIntoView({ block: 'center' })")
                shot(page, f"v38-panel-{width}.png")
        page.set_viewport_size({"width": 390, "height": 844})
        # a very long paint name must not break the layout either
        long_name = "A very very very long paint name with Averyveryveryveryveryverylongwordwithoutspaces " * 2
        load(page, paints=[P(1, long_name, BASE_HEX, brand="Averyveryveryverylongbrandnamewithoutanyspacesatall"), P(2, "Probe Opposite", at(180))])
        for width in (360, 400):
            page.set_viewport_size({"width": width, "height": 800})
            open_tab(page)
            tap(page, "blue")
            page.locator("#cmp-wheel-detail button.idea-link").first.click()
            page.wait_for_timeout(150)
            check(f"at {width} px a very long paint name, with a long brand and a long word, stays inside the card in the row and the panel title", no_sideways(page) and page.evaluate("""() => { const c = document.querySelector('#view-compendium .card').getBoundingClientRect();
                return [...document.querySelectorAll('#cmp-wheel-detail li, #cmp-paint-panel, #cmp-paint-panel *')].every(e => { const r = e.getBoundingClientRect(); return r.width === 0 || (r.left >= c.left - 0.5 && r.right <= c.right + 0.5); }); }"""))
            tap(page, "blue")
        page.set_viewport_size({"width": 390, "height": 844})
        # a real touch phone
        touch = browser.new_context(viewport={"width": 390, "height": 844}, has_touch=True, is_mobile=True, service_workers="block")
        tp = touch.new_page()
        tp.on("pageerror", lambda e: errors.append(str(e)))
        load(tp, paints=PAL)
        open_tab(tp)
        wh.touch_open(tp, "blue")
        names_t = tp.evaluate(ROWS_JS)
        tp.locator("#cmp-wheel-detail button.idea-link").nth(names_t.index("Probe Blue")).tap()
        tp.wait_for_timeout(200)
        check("on a touch phone, tapping a paint opens its panel and the page does not jump sideways", tp.locator(".paint-panel").count() == 1 and no_sideways(tp))
        tp.locator("#cmp-wheel-detail button.idea-link").nth(names_t.index("Probe Left")).tap()
        tp.wait_for_timeout(200)
        check("tapping another paint moves the panel to it", tp.locator(".paint-panel").count() == 1 and tp.evaluate(PANEL_JS)["title"].startswith("Matching colours for Probe Left"))
        tp.locator("#cmp-wheel-detail button.idea-link").nth(names_t.index("Probe Left")).tap()
        tp.wait_for_timeout(200)
        check("tapping the same paint again closes it", tp.locator(".paint-panel").count() == 0)
        tp.tap("#cmp-wheel-others")
        tp.wait_for_timeout(150)
        tp.tap("#cmp-wheel-more-blue")
        tp.wait_for_timeout(200)
        names_t = tp.evaluate(ROWS_JS)
        last = tp.locator("#cmp-wheel-detail button.idea-link").nth(len(names_t) - 1)
        last.scroll_into_view_if_needed()
        last.tap()
        tp.wait_for_timeout(250)
        check("on a touch phone, a paint revealed by Show all can be tapped too", tp.locator(".paint-panel").count() == 1 and tp.evaluate(PANEL_JS)["title"].startswith("Matching colours for " + names_t[-1]), tp.evaluate(PANEL_JS))
        tp.locator("#cmp-paint-panel .share-row button").tap()
        tp.wait_for_timeout(200)
        check("and Copy as text in the panel can be tapped without closing it", tp.locator(".paint-panel").count() == 1)
        touch.close()

        # ---------- 9. Dark and light ----------
        print("\n--- 9. Dark and light, 390 and 360 px ---")
        for appearance in ("dark", "light"):
            for width in (390, 360):
                page.set_viewport_size({"width": width, "height": 844})
                load(page, paints=PAL, settings={"appearance": appearance})
                open_tab(page)
                tap(page, "blue")
                open_row(page, "Probe Blue")
                tag = f"{appearance} {width}px"
                col = page.evaluate("""() => { const bg = (el) => { let e = el; while (e) { const v = getComputedStyle(e).backgroundColor; const m = v.match(/rgba\\(.*,\\s*([\\d.]+)\\)/);
                        if (v && v !== 'transparent' && !(m && parseFloat(m[1]) < 0.9)) return v; e = e.parentElement; } return 'rgb(0,0,0)'; };
                    const out = {}; const pairs = [['title', '#cmp-paint-panel .paint-panel-title'], ['intro', '#cmp-paint-panel > .hint'], ['group label', '#cmp-paint-panel .paint-panel-label'],
                        ['row name', '#cmp-paint-panel .idea-name'], ['row why', '#cmp-paint-panel .idea-why'], ['row tag', '#cmp-paint-panel .idea-tag'], ['row note', '#cmp-paint-panel .idea-note'],
                        ['copy button', '#cmp-paint-panel .share-row button'], ['Matching colours', '#cmp-wheel-detail button.idea-link .idea-open'], ['tap hint', '#cmp-wheel-links-hint']];
                    for (const [k, s] of pairs) { const el = document.querySelector(s); if (el) out[k] = [getComputedStyle(el).color, bg(el)]; } return out; }""")
                bad = {k: round(contrast(rgb(v[0]), rgb(v[1])), 2) for k, v in col.items() if contrast(rgb(v[0]), rgb(v[1])) < 4.5}
                check(f"{tag}: the panel's title, intro, group names, row words, tags, notes and button, and the Matching colours words and the tap hint, all have contrast of at least 4.5", not bad and len(col) >= 9, (bad, len(col)))
                ring = page.evaluate("""() => { const b = document.querySelector('#cmp-wheel-detail button.idea-link[aria-expanded="true"]'); const cs = getComputedStyle(b); const card = getComputedStyle(document.querySelector('#view-compendium .card')).backgroundColor;
                    const p = getComputedStyle(document.getElementById('cmp-paint-panel')); return { border: cs.borderTopColor, card, panelBorder: p.borderTopColor }; }""")
                check(f"{tag}: the open paint and its panel have an accent border you can see (contrast 3 or more against the card)", contrast(rgb(ring["border"]), rgb(ring["card"])) >= 3 and contrast(rgb(ring["panelBorder"]), rgb(ring["card"])) >= 3, ring)
                page.locator("#cmp-wheel-detail button.idea-link").first.focus()
                page.keyboard.press("Shift+Tab")
                page.keyboard.press("Tab")   # arrive by keyboard, so the focus ring shows (a script's focus() after a mouse click does not show it)
                fo = page.evaluate("() => { const cs = getComputedStyle(document.activeElement); return [cs.outlineColor, cs.outlineStyle, parseFloat(cs.outlineWidth)]; }")
                check(f"{tag}: a paint that has the keyboard focus shows an outline (contrast 3 or more against the card)", fo[1] != "none" and fo[2] >= 2 and contrast(rgb(fo[0]), rgb(ring["card"])) >= 3, fo)
                check(f"{tag}: nothing scrolls sideways", no_sideways(page))
                page.evaluate("() => document.getElementById('cmp-paint-panel').scrollIntoView({ block: 'center' })")
                shot(page, f"v38-panel-{appearance}-{width}.png")
        page.set_viewport_size({"width": 390, "height": 844})
        check("no page error and no unexpected dialog during all of this", not errors and not dialogs, (errors[:3], dialogs[:3]))
        browser.close()

    print(f"\n{sum(results)}/{len(results)} checks passed")
    sys.exit(0 if all(results) else 1)

if __name__ == "__main__":
    main()
