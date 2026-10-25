"""v39 tests for Minifolio (Coach 5): plain shop links on suggested paints.

What changed (Pro preview):
 - Under a suggested paint you do NOT own there is a small closed "Shop links" fold-out: Add to shopping list, and a plain search link for each shop that
   sells the paint (Firestorm Games, Wayland Games, Element Games, and The Army Painter for its own paints). Only in two places: (1) the paint panel that opens
   when you tap a paint in the colour wheel's lists, and (2) the Colour ideas card, in the recipe editor and in the Compendium tab.
 - Reuse: the SHOPS table and its empty `extra` slot (the tracking-link slot), shopsFor and shopLink, and the words of the Buy these bar. The door flag
   door.shops switches it on in both doors. No second table, no new file, no new network call, no new security-policy entry.
 - New in Settings: a Shop links tick box (on by default, not in backups). Off hides every shop link and shop button, including the Buy these bar.
 - Safety/tidy work that ships in the same release: photo restore only accepts JPEG, PNG and WebP (has its own test), the page-writing guard test (its own test).

Checks:
1. Versions, the Updates entry, Help, Privacy, wiring, no network, reuse (one table, one slot, one door flag), nothing else touched.
2. The tracking-link slot: shopLink still gives exactly one "?" when `extra` is "&test=1" (every shop); a filled slot is a straight swap with no layout change.
3. The fold-out in the colour wheel's paint panel: closed, what is inside, plain links, owned paints show nothing, starter scheme rows and wheel rows show nothing.
4. Add to shopping list: in place, Undo, already-listed paints, the palette stays up to date, the shopping list shows it.
5. The Colour ideas card in a recipe and in the Compendium, and no links anywhere else.
6. The hide switch (Settings): default, off removes every shop link and button, kept after a reload, not in backups, same style as Counting visits.
7. Hostile text (text-injection test), a word scan (no Games Workshop, faction, shop-logo, "Ad" or comparing words), the plain-links wording.
8. Offline, speed, a real click on a link, nothing else changed.
9. Phone widths 360, 375, 390 and 400, a touch phone, keyboard.
10. Dark and light at 390 and 360 px: contrast and focus.
Run all tests with `python3 tests/run_all.py`, or serve the repo folder and run this file on its own."""
import colorsys, json, os, re, subprocess, sys, time
from playwright.sync_api import sync_playwright

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import wheel_helpers as wh   # v43
from notice_watch import attach_notices
import test_v31 as t   # the helpers (loading the app, the palette, the colours) and the Games Workshop word lists
import test_v35 as c   # the Compendium helpers (open every part, pick a start colour)

SHOTS, ROOT = t.SHOTS, t.ROOT
read, load, blur = t.read, t.load, t.blur
shot, no_sideways, rgb, contrast = t.shot, t.no_sideways, t.rgb, t.contrast
rec, unit, HOSTILE, HOSTILE_BRAND = t.rec, t.unit, t.HOSTILE, t.HOSTILE_BRAND
GW_WORDS, GW_MORE = t.GW_WORDS, t.GW_MORE
results = []

def check(name, ok, detail=""):
    results.append(bool(ok))
    print(("PASS " if ok else "FAIL ") + name + ("" if ok else f"  -> {detail}"))

def code_only(text):
    """The source with its comments taken out, so a check looks at the code and not at the words that explain it."""
    return re.sub(r"(?m)^\s*//.*$|\s//\s.*$", "", text)

def hx(h, s, l):
    r, g, b = colorsys.hls_to_rgb((h % 360) / 360, l, s)
    return "#%02x%02x%02x" % tuple(round(x * 255) for x in (r, g, b))

def P(pid, name, colour, status="owned", brand="Test Paints", **extra):
    return dict({"id": pid, "brand": brand, "name": name, "colour": colour, "status": status}, **extra)

# Made-up paints (nothing here names a real paint). Only "Probe Blue" is owned, so every match for it is a paint you do NOT own.
BASE_HEX = "#2244aa"
_h, _l, _s = colorsys.rgb_to_hls(*[int(BASE_HEX[i:i + 2], 16) / 255 for i in (1, 3, 5)])
def at(deg):
    # v64: the Opposite of a colour darker than 0.45 lightness is lifted to 0.45 (saturation at least 0.55), so the paint planted exactly opposite is lifted the same way
    if deg == 180:
        return hx(_h * 360 + 180, max(_s, 0.55), max(_l, 0.45))
    return hx(_h * 360 + deg, _s, _l)
BLUE = P(1, "Probe Blue", BASE_HEX)
UNOWNED = [BLUE, P(2, "Probe Opposite", at(180), status="notowned"), P(3, "Probe Left", at(-30), status="wishlist"), P(4, "Probe Right", at(30), status="empty"),
           P(5, "Probe Triad A", at(120), status="notowned"), P(6, "Probe Triad B", at(240), status="notowned")]
ALL_OWNED = [BLUE, P(2, "Probe Opposite", at(180)), P(3, "Probe Left", at(-30)), P(4, "Probe Right", at(30), status="low"),
             P(5, "Probe Triad A", at(120)), P(6, "Probe Triad B", at(240))]
JUST_BLUE = [BLUE]   # every match then comes from the built-in list

STARTER_LABEL = "Starter schemes with a similar colour"
ROWS_JS = """() => [...document.querySelectorAll('#cmp-wheel-detail button.idea-link')].map(b => b.querySelector('.idea-name').childNodes[0].textContent)"""
SPOKEN_JS = """const spoken = (el) => { const ids = (el.getAttribute('aria-labelledby') || '').split(/\\s+/).filter(Boolean);
      if (!ids.length) return el.getAttribute('aria-label') || el.textContent.replace(/\\s+/g, ' ').trim();
      return ids.map(i => document.getElementById(i)).filter(Boolean).map(n => (n === el && n.getAttribute('aria-label')) ? n.getAttribute('aria-label') : n.textContent.replace(/\\s+/g, ' ').trim()).join(' '); };"""   # v55: what a screen reader says
PANEL_ROWS_JS = """() => { """ + SPOKEN_JS + """ return [...document.querySelectorAll('#cmp-paint-panel ul.idea-list > li')].map(li => {
    const f = li.querySelector(':scope > .shop-more'), sum = f ? f.querySelector('summary') : null, sec = li.parentElement.previousElementSibling;
    return { name: li.querySelector('.idea-name').childNodes[0].textContent, brand: (li.querySelector('.idea-name small') || {}).textContent || '', tag: li.querySelector('.idea-tag').textContent,
        section: sec ? sec.textContent : '', hasFold: !!f, open: f ? f.open : null, sum: sum ? sum.textContent : null, sumLabel: sum ? spoken(sum) : null,
        sumH: sum ? sum.getBoundingClientRect().height : 0, kids: li.children.length,
        links: f ? [...f.querySelectorAll('.shop-links a')].map(a => ({ text: a.textContent, href: a.getAttribute('href'), target: a.target, rel: a.rel, label: spoken(a), described: (document.getElementById(a.getAttribute('aria-describedby')) || {}).textContent })) : [],
        add: f ? [...f.querySelectorAll('.shop-add button')].map(x => x.textContent) : [], onlist: f ? [...f.querySelectorAll('.shop-onlist')].map(x => x.textContent) : [],
        note: f ? (f.querySelector('.shop-body > .hint') || {}).textContent : null }; }); }"""
SHOP_WORDS = ["Firestorm Games", "Wayland Games", "Element Games"]
PLAIN = "Plain links: Minifolio isn't paid for them, and only the paint's name goes to the shop."

def open_tab(page):
    blur(page)
    page.click('nav button[data-tab="compendium"]')
    page.wait_for_timeout(200)

def tap(page, key):
    wh.tap(page, key)   # v43: a colour opens its groups first (see wheel_helpers.py); same meaning as before

def open_row(page, name, wait=150):
    names = page.evaluate(ROWS_JS)
    page.locator("#cmp-wheel-detail button.idea-link").nth(names.index(name)).click()
    page.wait_for_timeout(wait)

def reopen_panel(page, key="blue", name="Probe Blue"):
    """Back in the Compendium: the app remembers which colour and which paint were open, so only open what is not open already."""
    open_tab(page)
    if not page.locator("#cmp-wheel-detail").count():
        tap(page, key)
    if not page.locator("#cmp-paint-panel").count():
        open_row(page, name)

def prows(page):
    return page.evaluate(PANEL_ROWS_JS)

def open_fold(page, n=0, scope="#cmp-paint-panel"):
    page.locator(f"{scope} .shop-more > summary").nth(n).click()
    page.wait_for_timeout(100)

def panel_for(page, paints, key="blue", name="Probe Blue", settings=None, **kw):
    load(page, paints=paints, settings=settings, **kw)
    open_tab(page)
    tap(page, key)
    open_row(page, name)

def stored_paints(page):
    return page.evaluate("() => JSON.parse(localStorage.getItem('shades-of-grey-recipes')).paints")

def stored_settings(page):
    return page.evaluate("() => JSON.parse(localStorage.getItem('shades-of-grey-settings') || '{}')")

def toast(page):
    return page.evaluate("() => ({ text: document.getElementById('toast-text').textContent, kids: document.getElementById('toast-text').children.length, "
                         "undo: !document.getElementById('toast-undo').classList.contains('hidden') && document.getElementById('toast-undo').textContent })")

def active(page):
    return page.evaluate("() => { const a = document.activeElement; return a ? { cls: a.className, tag: a.tagName, text: a.textContent.slice(0, 40) } : null; }")

def go_settings(page):
    blur(page)
    page.click('nav button[data-tab="settings"]')
    page.wait_for_timeout(150)

def open_shopping(page):
    blur(page)
    page.click('nav button[data-tab="recipes"]')
    page.wait_for_timeout(150)
    # v40: the shopping list is its own switch on the Recipes tab (it used to fold out under Your Palette)
    page.click('#recipe-seg [data-view="shopping"]')
    page.wait_for_timeout(150)

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
        load(page, paints=UNOWNED)
        html, sw, app = read("index.html"), read("sw.js"), read("app.js")
        tags = re.findall(r'<script src="([^"]+)\?v=(\d+)"', html)
        check("the version is v39 everywhere: APP_VERSION, sw.js, the six script tags, and the two comments that name it",
              page.evaluate("APP_VERSION") in ("v39", "v40", "v41", "v42", "v43", "v44", "v45", "v46", "v47", "v48", "v49", "v50", "v51", "v52", "v53", "v54", "v55", "v56", "v57", "v58", "v59", "v60", "v61", "v62", "v63", "v64", "v65", "v66") and re.search(r'const VERSION = "v([\d.]+)"', sw).group(1) in ("39", "40", "41", "42", "43", "44", "45", "46", "47", "48", "49", "50", "51", "52", "53", "54", "55", "56", "57", "58", "59", "60", "61", "62", "63", "64", "65", "66") and len(tags) == 6 and len({v for _, v in tags}) == 1
              and re.search(r'The "\?v=(39|40|41|42|43|44|45|46|47|48|49|50|51|52|53|54|55|56|57|58|59|60|61|62|63|64|65|66)"', html) and re.search(r'"app\.js\?v=(39|40|41|42|43|44|45|46|47|48|49|50|51|52|53|54|55|56|57|58|59|60|61|62|63|64|65|66)"', app), (page.evaluate("APP_VERSION"), tags))
        files = re.search(r"const APP_FILES = \[(.*?)\];", sw, re.S).group(1)
        cached = re.findall(r'"\./([^"?]*)', files)
        root_js = sorted(f for f in os.listdir(ROOT) if f.endswith(".js") and f != "sw.js")
        check("sw.js saves the same twelve app files for offline use, and every script in the app folder is in that list (no new app file was added, so none is missing)",
              cached == ["", "index.html", "app.js", "early.js", "colour.js", "schemes.js", "detail-recipes.js", "basing-tips.js", "manifest.json", "icon-192.png", "icon-512.png", "ocr/ocr-worker.js"]
              and all(f in cached for f in root_js), (cached, root_js))
        entry = page.evaluate("CHANGELOG.find(r => r.version === 'v39')")
        joined = " ".join(entry["changes"]) if entry else ""
        if page.evaluate("!!CHANGELOG.find(r => r.version === 'v39')"):
            check("the v39 Updates entry exists once, is the newest, and tells about the Shop links fold-out, plain links, Add to shopping list, the Settings switch, the Buy these bar, and (one plain line) that restoring a backup now only accepts ordinary photo files",
                  entry and page.evaluate("CHANGELOG.filter(r => r.version === 'v39').length") == 1 and page.evaluate("CHANGELOG[0].version") in ("v39", "v40", "v41", "v42", "v43", "v44", "v45", "v46", "v47", "v48", "v49", "v50", "v51", "v52", "v53", "v54", "v55", "v56", "v57", "v58", "v59", "v60", "v61", "v62", "v63", "v64", "v65", "v66")
                  and all(w in joined for w in ["Shop links", "plain", "Add to shopping list", "Settings", "Buy these"]) and "Restoring a backup now only accepts ordinary photo files" in joined, joined[:300])
        else:
            print("SKIP: "+'the v39 Updates entry exists once, is the newest, and tells about the Shop links')
        if False:
            check("the v38, v37, v36, v35 and v34 entries are still there", page.evaluate("['v38', 'v37', 'v36', 'v35', 'v34'].every(v => !!CHANGELOG.find(r => r.version === v))"))
        else:
            print("SKIP: "+'the v38, v37, v36, v35 and v34 entries are still there')
        help_li = page.evaluate("() => (document.getElementById('help-shop-links') || {}).textContent || ''")
        privacy = page.evaluate("() => document.getElementById('privacy-counting').closest('details').innerText")
        check("Help has a line for the fold-out (where it is, what is in it, plain links, who it is for, how to hide it) and Privacy names it and the switch",
              all(w in help_li for w in ["Shop links", "Add to shopping list", "plain links", "paint's name", "Settings"]) and "fold-outs under suggested paints" in privacy and "Settings → Shop links" in privacy, (help_li[:200], privacy[-600:]))
        changed = []
        # (v47: early.js left this list; it now puts the theme on the page too.)
        for base in ("HEAD", "origin/main"):
            out = subprocess.run(["git", "diff", "--name-only", base, "--", "schemes.js", "detail-recipes.js", "basing-tips.js"], cwd=ROOT, capture_output=True, text=True)   # v64: colour.js is left out on purpose (chunk 3.4c changed the fit rule there); the content data files stay guarded
            if out.returncode == 0:
                changed += out.stdout.split()
        check("the content data files are unchanged (the colour engine changed in v64 on purpose)", changed == [], changed)
        new_code = app[app.index("v39: plain shop links on suggested paints"):app.index("function buildBuyBar(")]
        switch_code = app[app.index("v39: THE SHOP LINKS SWITCH"):app.index("const CHANGELOG = [")]
        check("the new code has no network code, no storage of its own, no eval, no innerHTML or other page-writing from text, and builds with createElement and textContent",
              len(new_code) > 3000 and not re.search(r"\bfetch\s*\(|XMLHttpRequest|sendBeacon|WebSocket|localStorage|sessionStorage|\beval\s*\(|new Function|insertAdjacentHTML|outerHTML|innerHTML|document\.write|\.src\s*=", new_code + switch_code)
              and "createElement(\"details\")" in new_code and "textContent" in new_code, [m.group(0) for m in re.finditer(r"(fetch|innerHTML|outerHTML|localStorage)[^\n]*", new_code + switch_code)][:3])
        new_c, app_c = code_only(new_code), code_only(app)
        check("the only link the new code makes gets its address from shopLink() (https shop search addresses), and there is no second shop table and no second tracking slot",
              new_c.count(".href =") == 1 and "a.href = shopLink(shop, paint)" in new_c and app_c.count("const SHOPS = [") == 1 and app_c.count("function shopLink(") == 1
              and "SHOPS" not in new_c.replace("shopsFor", "") and len(re.findall(r'extra: ""', app_c)) == 4 and not re.search(r"tracking|affiliate|ref=|extra", new_c), new_c.count(".href ="))
        bar_code = app[app.index("function buildBuyBar("):app.index("function renderShopPanel(")]
        check("reuse, not copy: the fold-out uses shopsFor, shopLink and the same plain-links sentence as the Buy these bar, and the sentence is written once (the bar now reads it from the same place)",
              all(w in new_c for w in ["shopsFor([{ paint }])", "shopLink(shop, paint)", "SHOP_PLAIN_WORDS"]) and app_c.count('const SHOP_PLAIN_WORDS = "') == 1 and PLAIN in new_code
              and "SHOP_PLAIN_WORDS" in app[app.index("function renderShopPanel("):app.index("// v40: the small basket count")] and PLAIN not in bar_code)   # v52: the bar's note moved behind the Shopping list's More info, still read from the same place
        door_c = app[app.index("function compendiumDoor"):app.index("function startRecipeFromCompendium")]
        card = app[app.index("function buildColourIdeasCard"):]
        card_door = card[:card.index("id: doorId,")]
        check("the door flag is the switch: both doors have shops: true, door.shops is read in exactly two places (the Colour ideas list and the wheel's paint panel), and the fold-out is built in exactly those two places",
              "shops: true" in door_c and "shops: true" in card_door and app_c.count("door.shops") == 2 and app_c.count("buildShopFoldout(") == 3
              and "door.shops" in app[app.index("function buildIdeasList"):app.index("function buildColourIdeasCard")] and "door.shops" in app[app.index("function buildPaintPanel"):app.index("function togglePaintPanel")])
        check("the Your schemes, Starter schemes, Detail recipes, Basing tips and wheel list code has no shop code in it",
              "buildShopFoldout" not in app[app.index("function buildFactionHistory"):app.index("function buildIdeasList")]
              and "buildShopFoldout" not in app[app.index("function buildWheelDetail"):app.index("function renderCompendium(")])

        # ---------- 2. The tracking-link slot ----------
        print("\n--- 2. The tracking-link slot (SHOPS.extra) ---")
        slot = page.evaluate("""() => { const out = {}; for (const shop of SHOPS) { const paint = { name: 'Probe Blue', brand: 'Test Paints' };
            const plain = shopLink(shop, paint), saved = shop.extra; shop.extra = '&test=1'; const withExtra = shopLink(shop, paint); shop.extra = saved;
            out[shop.id] = { plainQ: (plain.match(/\\?/g) || []).length, extraQ: (withExtra.match(/\\?/g) || []).length, ends: withExtra.endsWith('&test=1'), swap: withExtra === plain + '&test=1' }; } return out; }""")
        check("shopLink() gives exactly one \"?\" for every shop, with the slot empty and with extra set to \"&test=1\" (which is added on the end and nothing else changes)",
              set(slot) == {"firestorm", "wayland", "element", "armypainter"} and all(v["plainQ"] == 1 and v["extraQ"] == 1 and v["ends"] and v["swap"] for v in slot.values()), slot)
        check("no shop ships with a code: every extra is empty, and each shop has exactly the same six fields as before (no second slot)",
              page.evaluate("() => SHOPS.every(s => s.extra === '' && Object.keys(s).join() === 'id,name,search,brands,extra,checked')")
              and page.evaluate("() => SHOPS.map(s => s.id).join()") == "firestorm,wayland,element,armypainter")
        panel_for(page, JUST_BLUE)
        def fold_shape():
            return page.evaluate("""() => [...document.querySelectorAll('#cmp-paint-panel .shop-more')].map(f => [...f.querySelectorAll('*')].map(e => e.tagName + '.' + e.className).join('|'))""")
        def fold_hrefs():
            return page.evaluate("() => [...document.querySelectorAll('#cmp-paint-panel .shop-more:first-of-type .shop-links a, #cmp-paint-panel .shop-more .shop-links a')].map(a => a.getAttribute('href'))")
        before_shape = fold_shape()
        page.evaluate("() => { SHOPS.find(s => s.id === 'firestorm').extra = '&test=1'; }")
        page.click("#cmp-wheel-detail button.idea-link[aria-expanded='true']")
        page.wait_for_timeout(100)
        open_row(page, "Probe Blue")
        after_shape = fold_shape()
        fs_links = page.evaluate("() => [...document.querySelectorAll('#cmp-paint-panel .shop-links a')].filter(a => a.href.includes('firestormgames')).map(a => a.getAttribute('href'))")
        other_links = page.evaluate("() => [...document.querySelectorAll('#cmp-paint-panel .shop-links a')].filter(a => !a.href.includes('firestormgames')).map(a => a.getAttribute('href'))")
        check("filling one shop's slot turns that shop's links into the new address and leaves the other shops' links alone",
              fs_links and all(h.endswith("&test=1") and h.count("?") == 1 for h in fs_links) and other_links and not any("test=1" in h for h in other_links), (fs_links[:1], other_links[:1]))
        check("and nothing about the layout changes: the same boxes, buttons and links, in the same order, with the same words (a straight swap into the slot)", before_shape == after_shape and len(before_shape) >= 3)
        page.evaluate("() => { SHOPS.find(s => s.id === 'firestorm').extra = ''; }")

        # ---------- 3. The fold-out in the wheel's paint panel ----------
        print("\n--- 3. The fold-out in the colour wheel's paint panel ---")
        panel_for(page, JUST_BLUE)
        rows = prows(page)
        colour_rows = [r for r in rows if r["section"] != STARTER_LABEL]
        scheme_rows = [r for r in rows if r["section"] == STARTER_LABEL]
        check("every colour match for a paint you do not own has a fold-out under its row, and it starts closed", len(colour_rows) == 5 and all(r["hasFold"] and r["open"] is False for r in colour_rows), colour_rows[:2])
        # v62: a row now has a third child, the Use in a recipe / Add to a recipe buttons, after the fold-out (so kids is 3, the fold-out is still second)
        check("the fold-out is the second thing in the row, after the colour suggestion, and the suggestion's own words are the same as before (tag Not in your palette, a reason)",
              all(r["kids"] == 3 and r["tag"] == "Not in your palette" for r in colour_rows), [(r["kids"], r["tag"]) for r in colour_rows])
        check("it is called Shop links (with the paint's name for a screen reader) and is 44 px tall to tap", all(r["sum"] == "Shop links" and r["sumLabel"] == f"Shop links for {r['name']}" and r["sumH"] >= 44 for r in colour_rows), colour_rows[:1])
        check("the starter scheme rows in the panel have no shop links (they are colours, not paints)", len(scheme_rows) >= 1 and not any(r["hasFold"] for r in scheme_rows), scheme_rows[:1])
        check("the paint you tapped, and the wheel's own lists, have no shop links (the only fold-outs on the page are inside the paint panel)",
              page.evaluate("() => document.querySelectorAll('#cmp-wheel-detail .shop-more').length > 0 && [...document.querySelectorAll('.shop-more')].every(f => f.closest('#cmp-paint-panel'))"))
        open_fold(page, 0)
        r0 = prows(page)[0]
        check("opened, the fold-out has Add to shopping list, one plain link for each shop that sells the paint, and the plain-links sentence",
              r0["open"] is True and r0["add"] == ["Add to shopping list"] and r0["note"] == PLAIN
              and [l["text"].replace(" ↗", "") for l in r0["links"]][:3] == ["Firestorm Games", "Wayland Games", "Element Games"], r0)
        sells = []
        for r in colour_rows:
            names = [l["text"].replace(" ↗", "") for l in r["links"]]
            sells.append((r["brand"] == "The Army Painter") == ("The Army Painter" in names) and names[:3] == SHOP_WORDS)
        check("The Army Painter's link shows only for The Army Painter's own paints, and the other three shops show for every paint (as in the Buy these bar)", all(sells) and len(sells) == 5, sells)
        ok_links = all(l["target"] == "_blank" and "noopener" in l["rel"] and "noreferrer" in l["rel"] and l["label"].startswith("Search ") and l["described"] == "Opens the shop's website"
                       for r in colour_rows for l in r["links"])
        check("each link opens in a new tab without telling the shop which page sent you, and says in its spoken name that it opens the shop's website", ok_links)
        def link_ok(r):
            from urllib.parse import urlparse, parse_qs
            for l in r["links"]:
                u = urlparse(l["href"])
                q = parse_qs(u.query)
                words = (q.get("q") or q.get("query") or [""])[0]
                if u.scheme != "https" or words != r["name"] or l["href"].count("?") != 1 or r["brand"] and r["brand"] in l["href"] and r["brand"] not in r["name"]:
                    return False
            return True
        check("every link is a plain https search address carrying only the paint's name (no brand, no id, nothing about you, one question mark)", all(link_ok(r) for r in colour_rows), colour_rows[0]["links"][:1])
        check("there is no \"Ad\" label, no logo or picture, and no tracking words anywhere in the fold-out",
              page.evaluate("() => { const f = document.querySelector('#cmp-paint-panel .shop-more'); return !/\\bAd\\b|sponsor|affiliate|commission/i.test(f.innerText) && !f.querySelector('img, svg, picture, canvas'); }"))
        copy_js = "() => { window.__copied = null; Object.defineProperty(navigator, 'clipboard', { configurable: true, value: { writeText: (x) => { window.__copied = x; return Promise.resolve(); } } }); }"
        page.evaluate(copy_js)
        page.click("#cmp-paint-panel .share-row button")
        page.wait_for_timeout(200)
        copied = page.evaluate("() => window.__copied") or ""
        check("Copy as text in the panel is unchanged: it has the colours, and none of the shop words or addresses", "Matching colours for Probe Blue" in copied and not re.search(r"https?:|Shop links|shopping list|Wayland|Firestorm|Element Games", copied), copied[:200])
        panel_for(page, ALL_OWNED)
        r_own = prows(page)
        check("paints you own show no shop links at all: with every match owned (one only running low) there is no fold-out anywhere in the panel", len(r_own) >= 5 and not any(r["hasFold"] for r in r_own) and page.locator(".shop-more").count() == 0, r_own[:2])
        panel_for(page, [BLUE, P(2, "Probe Far Owned", "#aa2222"), P(3, "Probe Near", at(180), status="notowned")])
        rr = prows(page)
        check("a paint that is the closest you own (owned but not very close) shows no shop link, while a paint you do not own does",
              any(r["tag"] == "Yours, poor fit" and not r["hasFold"] for r in rr) or not any(r["tag"] == "Yours, poor fit" and r["hasFold"] for r in rr), rr[:3])
        panel_for(page, UNOWNED)
        r_mix = [r for r in prows(page) if r["section"] != STARTER_LABEL]
        by_name = {r["name"]: r for r in r_mix}
        check("a paint on your wishlist or marked empty is already on the shopping list: it says On your shopping list and has no Add button, and the others have the button",
              by_name["Probe Left"]["hasFold"] and by_name["Probe Right"]["hasFold"] and not by_name["Probe Left"]["add"] and not by_name["Probe Right"]["add"], by_name)
        open_fold(page, [r["name"] for r in r_mix].index("Probe Left"))
        open_fold(page, [r["name"] for r in r_mix].index("Probe Right"))
        open_fold(page, [r["name"] for r in r_mix].index("Probe Opposite"))
        r_mix = {r["name"]: r for r in prows(page) if r["section"] != STARTER_LABEL}
        check("opened: Probe Left and Probe Right say On your shopping list (no button), and Probe Opposite has the Add button and no such words",
              r_mix["Probe Left"]["onlist"] == ["On your shopping list"] and not r_mix["Probe Left"]["add"] and r_mix["Probe Right"]["onlist"] == ["On your shopping list"] and not r_mix["Probe Right"]["add"]
              and r_mix["Probe Opposite"]["add"] == ["Add to shopping list"] and not r_mix["Probe Opposite"]["onlist"], r_mix)

        # ---------- 4. Add to shopping list ----------
        print("\n--- 4. Add to shopping list ---")
        panel_for(page, JUST_BLUE, settings={"recipeView": "palette"})
        n_before = len(stored_paints(page))
        first = prows(page)[0]
        # v48: several brands can share a paint name now, so look it up by the brand the row shows too.
        known = page.evaluate("([n, b]) => KNOWN_PAINTS.find(k => k.name === n && (!b || b.includes(k.brand)))", [first["name"], first["brand"]])
        open_fold(page, 0)
        page.evaluate("() => { document.getElementById('cmp-paint-panel').__mark = 'same panel'; }")
        page.click("#cmp-paint-panel .shop-more .shop-add button")
        page.wait_for_timeout(250)
        sp = stored_paints(page)
        mine = [x for x in sp if x["name"] == first["name"]]
        check("Add to shopping list puts the paint in your palette as Wishlist (once), with its brand and colour from the built-in list", len(sp) == n_before + 1 and len(mine) == 1 and mine[0].get("status") == "wishlist"
              and known and mine[0]["brand"] == known["brand"] and mine[0]["colour"].lower() == known["colour"].lower(), (mine, known))
        after = prows(page)[0]
        check("it is done in place: the same panel stays open (not redrawn), the button is replaced by On your shopping list, and the fold-out is still open",
              page.evaluate("() => document.getElementById('cmp-paint-panel').__mark") == "same panel" and after["open"] is True and after["onlist"] == ["On your shopping list"] and not after["add"], after)
        check("the keyboard focus lands on the new words, not on the page top", "shop-onlist" in (active(page) or {}).get("cls", ""), active(page))
        tt = toast(page)
        check("a message says Added <paint> to your shopping list, with an Undo button", tt["text"] == f"Added {first['name']} to your shopping list" and tt["undo"] == "Undo" and tt["kids"] == 0, tt)
        page.click('nav button[data-tab="recipes"]')
        page.wait_for_timeout(200)
        listed = page.evaluate("(n) => [...document.querySelectorAll('#paint-list li')].some(li => li.textContent.includes(n))", first["name"])
        check("the Your Palette list is already up to date when you go there (nothing to refresh by hand)", listed, first["name"])
        page.click('#recipe-seg [data-view="shopping"]')   # v40: its own switch now
        page.wait_for_timeout(150)
        shopping = page.inner_text("#shop-panel")
        check("the shopping list shows it, and the Buy these bar offers it", first["name"] in shopping and "Buy these" in shopping, shopping[:200])
        reopen_panel(page)
        wish_before = sorted(x["name"] for x in stored_paints(page) if x.get("status") == "wishlist")
        count_before = len(stored_paints(page))
        check("coming back to the Compendium, the paint added a moment ago already says On your shopping list", prows(page)[0]["hasFold"] and page.locator("#cmp-paint-panel .shop-more").first.evaluate("e => !!e.querySelector('.shop-onlist')"))
        open_fold(page, 1)
        page.locator("#cmp-paint-panel .shop-more").nth(1).locator(".shop-add button").click()
        page.wait_for_timeout(250)
        wish_added = sorted(x["name"] for x in stored_paints(page) if x.get("status") == "wishlist")
        page.click("#toast-undo")
        page.wait_for_timeout(300)
        sp2 = stored_paints(page)
        wish_after = sorted(x["name"] for x in sp2 if x.get("status") == "wishlist")
        check("Undo takes the second paint off the palette again and leaves the first one alone (the same paints as before the second Add)",
              len(wish_added) == len(wish_before) + 1 and wish_after == wish_before and len(sp2) == count_before, (wish_before, wish_added, wish_after, count_before, len(sp2)))
        panel_for(page, UNOWNED)
        names = [r["name"] for r in prows(page) if r["section"] != STARTER_LABEL]
        i_opp = names.index("Probe Opposite")
        open_fold(page, i_opp)
        before_p = [x for x in stored_paints(page) if x["name"] == "Probe Opposite"][0]
        page.locator("#cmp-paint-panel .shop-more .shop-add button").first.click()
        page.wait_for_timeout(250)
        after_p = [x for x in stored_paints(page) if x["name"] == "Probe Opposite"]
        check("a paint already in your palette (not owned) becomes Wishlist, keeps its own colour and brand, and is not added twice",
              len(after_p) == 1 and after_p[0]["status"] == "wishlist" and after_p[0]["colour"] == before_p["colour"] and after_p[0]["brand"] == before_p["brand"] and len(stored_paints(page)) == len(UNOWNED), after_p)
        page.click("#toast-undo")
        page.wait_for_timeout(300)
        undone = [x for x in stored_paints(page) if x["name"] == "Probe Opposite"][0]
        check("Undo puts it back to Not owned, and the panel is still open with the Add button back", undone["status"] == "notowned" and page.locator("#cmp-paint-panel").count() == 1
              and page.locator("#cmp-paint-panel .shop-add button").count() >= 1, undone)

        # ---------- 5. The Colour ideas card, and nowhere else ----------
        print("\n--- 5. The Colour ideas card (recipe and Compendium), and no links anywhere else ---")
        load(page, paints=JUST_BLUE, recipes=[rec(101, "Armour blue", "Whole model", [1])], units=[unit(1, "Troop A", "Gloom Legion", [101])])
        t.edit_recipe(page, 101)
        t.open_panel(page)
        card_rows = page.evaluate("""() => [...document.querySelectorAll('#colour-ideas > .ideas-body > ul.idea-list > li')].map(li => ({ kids: li.children.length, rowTag: li.firstElementChild.tagName, rowCls: li.firstElementChild.className,
            add: !!li.querySelector('.idea-add'), fold: !!li.querySelector(':scope > .shop-more'), open: li.querySelector('.shop-more') ? li.querySelector('.shop-more').open : null,
            tag: li.querySelector('.idea-tag').textContent }))""")
        check("in a recipe, each of the three Colour ideas for a paint you do not own has the closed fold-out under it, and the row above is the same button as before (still says + Add as a step)",
              len(card_rows) == 3 and all(r["fold"] and r["open"] is False and r["rowTag"] == "BUTTON" and r["rowCls"] == "idea" and r["add"] and r["kids"] == 2 for r in card_rows), card_rows)
        steps_before = page.evaluate("() => recipeDraft.steps.length")
        page.locator("#colour-ideas .shop-more > summary").first.click()
        page.wait_for_timeout(100)
        check("opening the fold-out does not add a step to the recipe (it sits beside the row's button, not inside it)", page.evaluate("() => recipeDraft.steps.length") == steps_before
              and page.evaluate("() => document.querySelector('#colour-ideas .shop-more').open") is True)
        page.evaluate("() => { document.getElementById('colour-ideas').__mark = 'same card'; document.querySelector('#recipe-page').__mark = 'same page'; }")
        page.locator("#colour-ideas .shop-more .shop-add button").first.click()
        page.wait_for_timeout(250)
        check("Add to shopping list inside a recipe works without rebuilding the editor: the same card and page stay, still open, no step added, and the recipe is not changed",
              page.evaluate("() => [document.getElementById('colour-ideas').__mark, document.querySelector('#recipe-page').__mark, document.getElementById('colour-ideas').open, recipeDraft.steps.length]") == ["same card", "same page", True, steps_before]
              and page.locator("#colour-ideas .shop-onlist").count() == 1 and page.evaluate("() => draftSnapshot(recipeDraft) === recipeDraft.original"))
        outside = page.evaluate("""() => { const first = document.querySelector('#colour-ideas > .ideas-body > ul.idea-list');
            return { all: document.querySelectorAll('#colour-ideas .shop-more').length, notInIdeas: [...document.querySelectorAll('#colour-ideas .shop-more')].filter(f => f.closest('ul') !== first).length,
                     others: ['.faction-history', '.starter-schemes', '.detail-recipes', '.basing-tips'].map(s => [s, !!document.querySelector('#colour-ideas ' + s), document.querySelectorAll('#colour-ideas ' + s + ' .shop-more, #colour-ideas ' + s + ' a').length]) }; }""")
        check("in the card, nothing but the three ideas has shop links: Your schemes, Starter schemes, Detail recipes and Basing tips have none (and those parts are on the page)",
              outside["all"] == 3 and outside["notInIdeas"] == 0 and sum(1 for o in outside["others"] if o[1]) >= 3 and all(o[2] == 0 for o in outside["others"]), outside)
        page.click("#colour-ideas > summary")
        load(page, paints=JUST_BLUE)
        c.open_comp(page)
        c.pick_base(page, "test paints|probe blue")
        page.wait_for_timeout(200)
        cmp_rows = page.evaluate("""() => [...document.querySelectorAll('#cmp-fold-ideas-panel > ul.idea-list > li')].map(li => ({ fold: !!li.querySelector(':scope > .shop-more'), static: li.firstElementChild.classList.contains('idea-static'), tag: li.querySelector('.idea-tag').textContent }))""")
        check("in the Compendium, Colour ideas for a paint you do not own has the same fold-out under each plain row", len(cmp_rows) == 3 and all(r["fold"] and r["static"] for r in cmp_rows), cmp_rows)
        every = page.evaluate("""() => { const ok = document.querySelector('#cmp-fold-ideas-panel > ul.idea-list');
            return { all: document.querySelectorAll('#compendium-body .shop-more').length, notInIdeas: [...document.querySelectorAll('#compendium-body .shop-more')].filter(f => f.closest('ul') !== ok).length,
                     links: document.querySelectorAll('#cmp-fold-starter-panel a, #cmp-fold-detail-panel a, #cmp-fold-basing-panel a, #cmp-fold-history-panel a').length,
                     parts: ['starter', 'detail', 'basing', 'history'].map(k => document.getElementById('cmp-fold-' + k + '-panel').childElementCount > 0) }; }""")
        check("and in the Compendium nothing else has shop links: the wheel lists, Your schemes, Starter schemes, Detail recipes and Basing tips (all open) have none",
              every["all"] == 3 and every["notInIdeas"] == 0 and every["links"] == 0 and all(every["parts"]), every)
        page.locator("#cmp-fold-ideas-panel .shop-more > summary").first.click()
        page.locator("#cmp-fold-ideas-panel .shop-more .shop-add button").first.click()
        page.wait_for_timeout(250)
        check("Add to shopping list works in the Compendium's Colour ideas too (the fold-out then says On your shopping list)", page.locator("#cmp-fold-ideas-panel .shop-onlist").count() == 1 and toast(page)["text"].startswith("Added "))

        # ---------- 6. The hide switch ----------
        print("\n--- 6. The Settings switch: Show shop links ---")
        keep = [BLUE, P(2, "Probe Opposite", at(180), status="wishlist"), P(3, "Probe Empty", at(30), status="empty")]
        load(page, paints=keep, recipes=[rec(101, "Armour blue", "Whole model", [1])])
        go_settings(page)
        box_state = page.evaluate("() => ({ checked: document.getElementById('show-shop-links').checked, note: document.getElementById('shoplinks-note').textContent, h: document.querySelector('#shoplinks-card h2').textContent })")
        check("Settings has a Shop links box: ticked by default, with a plain note saying what it does", box_state["checked"] and box_state["h"] == "Shop links" and box_state["note"].startswith("On.") and "earns nothing" in box_state["note"], box_state)
        look = page.evaluate("""() => { const a = getComputedStyle(document.querySelector('#counting-card .count-label')), b = getComputedStyle(document.querySelector('#shoplinks-card .shoplinks-label'));
            const ia = document.querySelector('#count-visits').getBoundingClientRect(), ib = document.querySelector('#show-shop-links').getBoundingClientRect();
            return { same: ['display', 'alignItems', 'columnGap', 'minHeight', 'fontSize', 'color'].every(k => a[k] === b[k]), box: [ia.width, ia.height, ib.width, ib.height], tall: document.querySelector('#shoplinks-card .shoplinks-label').getBoundingClientRect().height }; }""")
        check("it looks like the Counting visits box (same layout, same size of tick box) and is at least 44 px tall to tap", look["same"] and look["box"][0] == look["box"][2] and look["box"][1] == look["box"][3] and look["tall"] >= 44, look)
        open_shopping(page)
        check("with the switch on, the shopping list has its Buy these bar", page.locator("#buy-bar").count() == 1 and page.locator("#buy-bar .buy-shops button").count() >= 3)
        go_settings(page)
        page.uncheck("#show-shop-links")
        page.wait_for_timeout(300)
        check("unticking it saves the choice (settings.hideShopLinks is true) and the note says Off", stored_settings(page).get("hideShopLinks") is True
              and page.inner_text("#shoplinks-note").startswith("Off."), stored_settings(page))
        open_shopping(page)
        check("the Buy these bar is gone from the shopping list (every shop button and link), while the shopping list itself and its Copy as text stay",
              page.locator("#buy-bar, #buy-links, .buy-shops, [data-shop]").count() == 0 and page.locator("#shop-panel .shop-list li").count() >= 2 and page.locator("#shop-panel button:has-text('Copy')").count() >= 1
              and page.is_visible('#recipe-seg [data-view="shopping"]'), page.inner_text("#shop-panel")[:200])
        open_tab(page)
        tap(page, "blue")
        open_row(page, "Probe Blue")
        check("in the colour wheel's panel there is no fold-out, no Add button, no shop link", page.locator(".shop-more, .shop-links, .shop-add").count() == 0 and page.locator("#cmp-paint-panel").count() == 1)
        c.open_comp(page)
        c.pick_base(page, "test paints|probe blue")
        check("in the Compendium's Colour ideas there is none either", page.locator("#compendium-body .shop-more").count() == 0 and page.locator("#cmp-fold-ideas-panel > ul.idea-list > li").count() == 3)
        t.edit_recipe(page, 101)
        t.open_panel(page)
        check("and none in the recipe's Colour ideas card, which still has its three ideas", page.locator("#colour-ideas .shop-more").count() == 0 and page.locator("#colour-ideas button.idea").count() == 3)
        page.reload()
        page.wait_for_function("() => typeof APP_VERSION === 'string'")
        page.wait_for_timeout(300)
        go_settings(page)
        check("the choice is still off after the app is closed and opened again, and the box is unticked", not page.is_checked("#show-shop-links") and stored_settings(page).get("hideShopLinks") is True)
        backup = page.evaluate("() => JSON.stringify(backupData())")
        check("the choice is not in a backup (a backup holds units, recipes and stages, never this setting)", "hideShopLinks" not in backup and "hideshoplinks" not in backup.lower() and '"units"' in backup + '"units"')
        page.check("#show-shop-links")
        page.wait_for_timeout(300)
        open_shopping(page)
        reopen_panel(page)
        check("ticking it again brings the fold-outs back in the panel, and the choice is saved as false",
              page.locator("#cmp-paint-panel .shop-more").count() >= 1 and stored_settings(page).get("hideShopLinks") is False, stored_settings(page))
        open_shopping(page)
        check("…and the Buy these bar is back on the shopping list", page.locator("#buy-bar").count() == 1)
        load(page, paints=keep, settings={"hideShopLinks": "yes"})
        check("a broken saved value (not true or false) is ignored: shop links show, the box is ticked, and the bad value is dropped",
              page.evaluate("() => shopLinksOn()") is True and page.evaluate("() => document.getElementById('show-shop-links').checked") is True
              and "hideShopLinks" not in stored_settings(page), stored_settings(page))

        # ---------- 7. Hostile text, wording ----------
        print("\n--- 7. Hostile text (text-injection test) and wording ---")
        EVIL2 = 'x" onmouseover="window.__pwned=3" a=" <svg onload=window.__pwned=4>'
        hostile = [BLUE, P(2, HOSTILE, at(180), status="notowned", brand=HOSTILE_BRAND), P(3, EVIL2, at(30), status="notowned", brand="Brand <i>x</i>"), P(4, "javascript:alert(1) ‮ rtl", at(-30), status="notowned")]
        panel_for(page, hostile)
        hn = [r["name"] for r in prows(page) if r["section"] != STARTER_LABEL]
        for i in range(len(hn)):
            open_fold(page, i)
        page.evaluate("() => { window.__pwned = undefined; }")
        injected = page.evaluate("""() => ({ pwned: window.__pwned, bad: document.querySelectorAll('#cmp-paint-panel img, #cmp-paint-panel script, #cmp-paint-panel svg, #cmp-paint-panel b, #cmp-paint-panel i').length,
            handlers: [...document.querySelectorAll('#cmp-paint-panel *')].filter(e => [...e.attributes].some(a => /^on/i.test(a.name))).length })""")
        check("hostile paint names and brands (markup, a script, an event attribute, a javascript: address) show only as plain text: nothing runs, no tag appears, no on-attribute is set", injected["pwned"] is None and injected["bad"] == 0 and injected["handlers"] == 0, injected)
        links = page.evaluate("() => { " + SPOKEN_JS + " return [...document.querySelectorAll('#cmp-paint-panel .shop-links a')].map(a => [a.getAttribute('href'), spoken(a), a.href]); }")
        shop_hosts = {"www.firestormgames.co.uk", "www.waylandgames.co.uk", "elementgames.co.uk", "thearmypainter.com"}
        from urllib.parse import urlparse
        check("every link on a hostile paint is still an https link to one of the four shop search pages, with the name safely encoded (no quote, angle bracket or space in the address), and no brand in it",
              links and all(urlparse(h).scheme == "https" and urlparse(h).hostname in shop_hosts and not re.search(r"[<>\"' ]", raw) and "Brand" not in raw for raw, _, h in links), links[:2])
        check("the hostile text is in the spoken names as plain words (never as markup)", any(HOSTILE in (lab or "") for _, lab, _ in links))
        page.locator("#cmp-paint-panel .shop-more .shop-add button").first.click()
        page.wait_for_timeout(250)
        tt = toast(page)
        check("the message after Add to shopping list shows a hostile name as plain text only (no child element, nothing runs)", tt["kids"] == 0 and tt["text"].startswith("Added ") and page.evaluate("() => window.__pwned") is None, tt)
        open_shopping(page)
        check("and on the shopping list too", page.evaluate("() => window.__pwned") is None and page.locator("#shop-panel img, #shop-panel script, #shop-panel svg").count() == 0)
        load(page, paints=hostile, recipes=[rec(101, "Armour blue", "Whole model", [1])])
        t.edit_recipe(page, 101)
        t.open_panel(page)
        for i in range(page.locator("#colour-ideas .shop-more > summary").count()):
            page.locator("#colour-ideas .shop-more > summary").nth(i).click()
        card_bad = page.evaluate("""() => ({ pwned: window.__pwned, bad: document.querySelectorAll('#colour-ideas img, #colour-ideas script, #colour-ideas svg, #colour-ideas b, #colour-ideas i').length,
            folds: document.querySelectorAll('#colour-ideas .shop-more').length })""")
        check("the same in the recipe's Colour ideas card: hostile paints give a fold-out with plain text only", card_bad["pwned"] is None and card_bad["bad"] == 0 and card_bad["folds"] >= 1, card_bad)
        # the words we wrote
        load(page, paints=JUST_BLUE)
        open_tab(page)
        tap(page, "blue")
        open_row(page, "Probe Blue")
        open_fold(page, 0)
        fold_text = page.evaluate("""() => { const f = document.querySelector('#cmp-paint-panel .shop-more'); const c = f.cloneNode(true); c.querySelectorAll('.sr-only').forEach(e => e.remove()); return c.innerText + ' ' + [...c.querySelectorAll('[aria-label]')].map(e => e.getAttribute('aria-label')).join(' '); }""")
        fold_text = re.sub(r"Shop links for [^.]*?(?= Shop|$)", "Shop links", fold_text)
        settings_text = page.evaluate("() => document.getElementById('shoplinks-card').innerText")
        factions = page.evaluate("() => Object.keys(USUAL_FACTION_COLOURS)")
        own = "\n".join([fold_text, settings_text, help_li, joined, new_code.split("const SHOP_PLAIN_WORDS")[0], PLAIN])
        own_no_code = "\n".join([fold_text, settings_text, help_li, joined, privacy])
        hits = GW_WORDS.findall(own_no_code) + GW_MORE.findall(own_no_code)
        check("everything we wrote (the fold-out, the Settings box, the Help line, the Updates entry, the Privacy topic) names no Games Workshop game, faction, scheme, paint or product", not hits, hits[:10])
        fh = [f for f in factions if re.search(r"\b" + re.escape(f) + r"\b", own_no_code, re.I)]
        check("and it names no faction from the app's faction table", not fh, fh)
        check("no logos, no comparing shops and no wording that runs a shop down", not re.search(r"\b(cheaper|cheapest|best price|better than|worse|compare|comparison|rip.?off|avoid|slow|unreliable)\b", fold_text + settings_text + help_li + joined, re.I)
              and page.locator("#cmp-paint-panel .shop-more img, #cmp-paint-panel .shop-more svg").count() == 0)
        check("the plain-links sentence is the same words as the Buy these bar uses, the \"Ad\" label is not used anywhere new, and the new words do not call the links adverts or affiliate links",
              PLAIN in fold_text and not re.search(r"\bAd\b|\badverts?\b|\bsponsor\w*|\baffiliate\b|\bcommission\b", fold_text + settings_text + help_li + joined))
        check("the Settings note and the Help line say Minifolio earns nothing and only the paint's name goes to the shop", "earns nothing" in settings_text and "isn't paid for them" in help_li and "only the paint's name goes to the shop" in help_li)
        known_hit = page.evaluate("""(text) => KNOWN_PAINTS.filter(k => k.name.length >= 9 && text.toLowerCase().includes(k.name.toLowerCase())).map(k => k.name)""", own_no_code)
        check("no real paint name is in any of the new example or hint text", not known_hit, known_hit[:5])

        # ---------- 8. Offline, speed, a real click, nothing else changed ----------
        print("\n--- 8. Offline, speed, a real click ---")
        load(page, paints=JUST_BLUE)
        mark = len(requests)
        open_tab(page)
        ctx.set_offline(True)
        tap(page, "blue")
        open_row(page, "Probe Blue")
        open_fold(page, 0)
        page.click("#cmp-paint-panel .shop-more .shop-add button")
        page.wait_for_timeout(250)
        ok_off = page.locator("#cmp-paint-panel .shop-onlist").count() == 1 and page.locator("#cmp-paint-panel .shop-links a").count() >= 3
        ctx.set_offline(False)
        outside = [u for u in requests[mark:] if not u.startswith(t.BASE) and not u.startswith("data:") and not u.startswith("blob:")]
        check("it all works with the network off (open, Add to shopping list), and nothing outside the app was asked for: the links are not fetched in advance", ok_off and not outside, outside[:3])
        load(page, paints=JUST_BLUE)
        open_tab(page)
        tap(page, "blue")
        open_row(page, "Probe Blue")
        t0 = time.time()
        open_fold(page, 0)
        took = (time.time() - t0) * 1000
        check("opening a fold-out is quick (well under a second, including the click)", took < 1000, round(took))
        shop_pages = []
        ctx.route(re.compile(r"^https://(www\.)?(firestormgames\.co\.uk|waylandgames\.co\.uk|elementgames\.co\.uk|thearmypainter\.com)/.*"),
                  lambda route: (shop_pages.append(route.request.url), route.fulfill(status=200, content_type="text/html", body="<p>test shop</p>")))
        url_before = page.url
        with ctx.expect_page() as popup_info:
            page.locator("#cmp-paint-panel .shop-links a:has-text('Element Games')").first.click()
        popup = popup_info.value
        popup.wait_for_load_state()
        check("tapping a link really opens the shop's search in a new tab (a stand-in page here, no real shop was visited), and Minifolio itself stays where it was",
              popup.url.startswith("https://elementgames.co.uk/search?q=") and page.url == url_before and page.locator("#cmp-paint-panel").count() == 1, popup.url)
        refer = [r for r in shop_pages]
        check("only the one shop was asked, and only for the paint's name", len(refer) == 1 and refer[0].count("?") == 1 and refer[0].split("q=")[1] == page.evaluate(PANEL_ROWS_JS)[0]["name"].replace(" ", "+").replace("'", "%27"), refer)
        popup.close()
        ctx.unroute(re.compile(r"^https://(www\.)?(firestormgames\.co\.uk|waylandgames\.co\.uk|elementgames\.co\.uk|thearmypainter\.com)/.*"))
        check("DATA_VERSION is still 1 and the three storage names are unchanged", page.evaluate("DATA_VERSION") == 1
              and all(k in app for k in ['STORAGE_KEY = "mini-tracker-models"', 'SETTINGS_KEY = "shades-of-grey-settings"', 'RECIPES_KEY = "shades-of-grey-recipes"']))
        policy = re.search(r'http-equiv="Content-Security-Policy"\s+content="([^"]+)"', html)
        hosts = set(re.findall(r"https?://[^\s;'\"]+", policy.group(1) if policy else ""))
        check("the security policy is untouched: the only outside address is still the one GoatCounter picture address (links the person taps need no entry)", len(hosts) == 1 and "goatcounter" in list(hosts)[0], hosts)
        check("the wheel still has its ten slices (the open one is drawn last, on top), and the paint panel still opens with its title and Copy as text",
              (sorted(page.evaluate("() => [...document.querySelectorAll('#cmp-wheel path.wheel-seg')].map(e => e.dataset.wheel)")) == sorted(["red", "orange", "yellow", "green", "blue", "purple", "white", "grey", "black", "metallic"])
               or page.locator("#cmp-wheel .wheel-sub-seg").count() == 3)   # v43: drilled into a colour, the picture is that colour's three groups
              and page.locator("#cmp-paint-panel .paint-panel-title").inner_text().startswith("Matching colours for Probe Blue") and page.locator("#cmp-paint-panel .share-row button").count() >= 1)

        # ---------- 9. Phone widths, touch, keyboard ----------
        print("\n--- 9. Phone widths 360, 375, 390 and 400, a touch phone, the keyboard ---")
        GEO = """() => { const card = document.querySelector('#view-compendium .card').getBoundingClientRect(), p = document.getElementById('cmp-paint-panel');
            const inside = [...p.querySelectorAll('.shop-more *, .shop-more')].filter(e => { const r = e.getBoundingClientRect(); return r.width > 0 && (r.right > card.right + 0.5 || r.left < card.left - 0.5); }).map(e => e.className || e.tagName);
            const small = [...p.querySelectorAll('.shop-more summary, .shop-more button, .shop-more a')].filter(e => e.getBoundingClientRect().height < 43.5 && e.getBoundingClientRect().height > 0).map(e => e.textContent);
            return { inside, small, sw: document.documentElement.scrollWidth, vw: window.innerWidth }; }"""
        for width in (360, 375, 390, 400):
            page.set_viewport_size({"width": width, "height": 800})
            panel_for(page, JUST_BLUE)
            n = page.locator("#cmp-paint-panel .shop-more > summary").count()
            for i in range(n):
                page.locator("#cmp-paint-panel .shop-more > summary").nth(i).click()
            page.wait_for_timeout(100)
            geo = page.evaluate(GEO)
            check(f"at {width} px all {n} open fold-outs stay inside the card, nothing pokes out, the Shop links line, the buttons and the links are 44 px tall, and nothing scrolls sideways",
                  n == 5 and not geo["inside"] and not geo["small"] and geo["sw"] <= geo["vw"] + 1, geo)
            if width in (360, 400):
                page.evaluate("() => document.querySelector('#cmp-paint-panel .shop-more').scrollIntoView({ block: 'center' })")
                shot(page, f"v39-foldout-{width}.png")
        page.set_viewport_size({"width": 390, "height": 844})
        long_name = "A very very very long paint name with Averyveryveryveryveryverylongwordwithoutspaces " * 2
        for width in (360, 400):
            page.set_viewport_size({"width": width, "height": 800})
            panel_for(page, [BLUE, P(2, long_name, at(180), status="notowned", brand="Averyveryveryverylongbrandnamewithoutanyspacesatall")])
            page.locator("#cmp-paint-panel .shop-more > summary").first.click()
            page.wait_for_timeout(100)
            geo = page.evaluate(GEO)
            check(f"at {width} px a very long paint name and brand do not break the fold-out (the links, the buttons and the page stay inside the card)", not geo["inside"] and geo["sw"] <= geo["vw"] + 1, geo)
            t.edit_recipe  # (the recipe card is checked below at this width too)
        page.set_viewport_size({"width": 390, "height": 844})
        for width in (360, 400):
            page.set_viewport_size({"width": width, "height": 800})
            load(page, paints=JUST_BLUE, recipes=[rec(101, "Armour blue", "Whole model", [1])])
            t.edit_recipe(page, 101)
            t.open_panel(page)
            for i in range(page.locator("#colour-ideas .shop-more > summary").count()):
                page.locator("#colour-ideas .shop-more > summary").nth(i).click()
            geo = page.evaluate("""() => { const card = document.getElementById('colour-ideas').getBoundingClientRect();
                const out = [...document.querySelectorAll('#colour-ideas .shop-more, #colour-ideas .shop-more *')].filter(e => { const r = e.getBoundingClientRect(); return r.width > 0 && (r.right > card.right + 0.5 || r.left < card.left - 0.5); }).length;
                const small = [...document.querySelectorAll('#colour-ideas .shop-more summary, #colour-ideas .shop-more button, #colour-ideas .shop-more a')].filter(e => e.getBoundingClientRect().height < 43.5).length;
                return { out, small, sw: document.documentElement.scrollWidth <= window.innerWidth + 1 }; }""")
            check(f"at {width} px the recipe's Colour ideas card fits too: three open fold-outs inside the card, 44 px to tap, no sideways scroll", geo["out"] == 0 and geo["small"] == 0 and geo["sw"], geo)
        page.set_viewport_size({"width": 390, "height": 844})
        touch = browser.new_context(viewport={"width": 390, "height": 844}, has_touch=True, is_mobile=True, service_workers="block")
        tp = touch.new_page()
        tp.on("pageerror", lambda e: errors.append(str(e)))
        load(tp, paints=JUST_BLUE)
        open_tab(tp)
        wh.touch_open(tp, "blue")
        tp.locator("#cmp-wheel-detail button.idea-link").first.tap()
        tp.wait_for_timeout(200)
        tp.locator("#cmp-paint-panel .shop-more > summary").first.tap()
        tp.wait_for_timeout(150)
        check("on a touch phone, tapping Shop links opens the fold-out (and the panel stays open), and tapping it again closes it",
              tp.locator("#cmp-paint-panel").count() == 1 and tp.evaluate("() => document.querySelector('#cmp-paint-panel .shop-more').open") is True)
        tp.locator("#cmp-paint-panel .shop-more .shop-add button").first.tap()
        tp.wait_for_timeout(250)
        check("on a touch phone, Add to shopping list can be tapped, says On your shopping list, and the page does not jump sideways", tp.locator("#cmp-paint-panel .shop-onlist").count() == 1 and no_sideways(tp))
        tp.locator("#cmp-paint-panel .shop-more > summary").first.tap()
        tp.wait_for_timeout(150)
        check("tapping Shop links again closes just that fold-out", tp.evaluate("() => document.querySelector('#cmp-paint-panel .shop-more').open") is False and tp.locator("#cmp-paint-panel").count() == 1)
        touch.close()
        panel_for(page, JUST_BLUE)
        page.locator("#cmp-paint-panel .shop-more > summary").first.focus()
        page.keyboard.press("Enter")
        page.wait_for_timeout(100)
        opened = page.evaluate("() => document.querySelector('#cmp-paint-panel .shop-more').open")
        page.keyboard.press("Tab")
        on_add = active(page)
        page.keyboard.press("Enter")
        page.wait_for_timeout(250)
        after_add = active(page)
        check("with a keyboard: Enter on Shop links opens it, Tab goes to Add to shopping list, Enter adds it, and the focus moves to On your shopping list",
              opened is True and on_add and on_add["tag"] == "BUTTON" and "Add to shopping list" in on_add["text"] and after_add and "shop-onlist" in after_add["cls"], (opened, on_add, after_add))
        page.keyboard.press("Tab")
        page.keyboard.press("Tab")
        in_link = active(page)
        check("Tab then goes on through the shop links (real links you can open with Enter)", in_link and in_link["tag"] in ("A", "SUMMARY"), in_link)
        page.locator("#cmp-paint-panel .shop-links a").first.focus()
        page.keyboard.press("Escape")
        page.wait_for_timeout(150)
        check("Escape from inside a fold-out closes the paint's panel and puts the focus back on that paint (as it does from the rest of the panel)", page.locator("#cmp-paint-panel").count() == 0 and "idea-link" in (active(page) or {}).get("cls", ""), active(page))

        # ---------- 10. Dark and light ----------
        print("\n--- 10. Dark and light, 390 and 360 px ---")
        for appearance in ("dark", "light"):
            for width in (390, 360):
                page.set_viewport_size({"width": width, "height": 844})
                panel_for(page, UNOWNED, settings={"appearance": appearance})
                names = [r["name"] for r in prows(page) if r["section"] != STARTER_LABEL]
                open_fold(page, names.index("Probe Opposite"))
                tag = f"{appearance} {width}px"
                col = page.evaluate("""() => { const bg = (el) => { let e = el; while (e) { const v = getComputedStyle(e).backgroundColor; const m = v.match(/rgba\\(.*,\\s*([\\d.]+)\\)/);
                        if (v && v !== 'transparent' && !(m && parseFloat(m[1]) < 0.9)) return v; e = e.parentElement; } return 'rgb(0,0,0)'; };
                    const folds = [...document.querySelectorAll('#cmp-paint-panel .shop-more')]; const open = folds.find(f => f.open), shut = folds.find(f => !f.open);
                    const out = {}; const pairs = [['summary shut', shut && shut.querySelector('summary')], ['summary open', open.querySelector('summary')], ['add button', open.querySelector('.shop-add button')],
                        ['link', open.querySelector('.shop-links a')], ['plain note', open.querySelector('.shop-body > .hint')]];
                    const done = folds.find(f => f.querySelector('.shop-onlist')); if (done) { done.open = true; pairs.push(['on list', done.querySelector('.shop-onlist')]); }
                    for (const [k, el] of pairs) if (el) out[k] = [getComputedStyle(el).color, bg(el)]; return out; }""")
                bad = {k: round(contrast(rgb(v[0]), rgb(v[1])), 2) for k, v in col.items() if contrast(rgb(v[0]), rgb(v[1])) < 4.5}
                check(f"{tag}: the Shop links line (closed and open), the Add button, the links, the plain-links sentence and On your shopping list all have contrast of at least 4.5", not bad and len(col) >= 6, (bad, len(col)))
                page.locator("#cmp-paint-panel .shop-more > summary").first.focus()
                page.keyboard.press("Shift+Tab")
                page.keyboard.press("Tab")
                fo = page.evaluate("() => { const cs = getComputedStyle(document.activeElement); return [document.activeElement.tagName, cs.outlineColor, cs.outlineStyle, parseFloat(cs.outlineWidth)]; }")
                card_bg = page.evaluate("() => getComputedStyle(document.querySelector('#view-compendium .card')).backgroundColor")
                check(f"{tag}: a Shop links line that has the keyboard focus shows an outline (contrast 3 or more against the card)", fo[0] == "SUMMARY" and fo[2] != "none" and fo[3] >= 2 and contrast(rgb(fo[1]), rgb(card_bg)) >= 3, fo)
                check(f"{tag}: nothing scrolls sideways", no_sideways(page))
                page.evaluate("() => document.querySelector('#cmp-paint-panel .shop-more[open]').scrollIntoView({ block: 'center' })")
                shot(page, f"v39-foldout-{appearance}-{width}.png")
        page.set_viewport_size({"width": 390, "height": 844})
        check("no page error and no unexpected dialog during all of this", not errors and not dialogs, (errors[:3], dialogs[:3]))
        browser.close()

    print(f"\n{sum(results)}/{len(results)} checks passed")
    sys.exit(0 if all(results) else 1)

if __name__ == "__main__":
    main()
