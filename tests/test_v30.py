"""v30 tests for Minifolio (Coach 4): "Your schemes" in the Colour ideas panel (Pro preview).

Two new parts inside the recipe editor's Colour ideas card:
  (1) "Colours you've used on this faction before": the paints in the user's own other saved recipes that are linked to units
      of the same faction as the recipe being edited, most-used first, with the same honest "You own this" tag. Tap one to add
      it as a step. No faction or no history: it says so plainly and shows nothing else.
  (2) "Starter schemes": a small hand-written set of generic colour schemes. Pick one to see its colours as matching paints
      (yours first), with the same honest tags; tap one to add it as a step. No Games Workshop names, faction names, scheme
      names or artwork.
"Whole model" still means the main colour of the recipe filed under the Whole model part (Coach 2); nothing about that changed.

Checks:
1. Versions, the v30 Updates entry, wiring unchanged (no new file), CSP and data unchanged, no network or storage code, no GW names.
2. Faction history: which units count, the order (most units, then recipes, then name), tags, reasons, tapping adds a step.
3. Plain messages: no faction, a unit with no faction, no history, everything already in the recipe, more than six paints.
4. Starter schemes: the data itself (generic, short, a handful of colours), chips, picking, deselecting, tapping adds a step.
5. Honesty: an owned close paint says You own this, a wishlist paint never does, an empty palette says Not in your palette.
6. Where it sits in the card, state kept across roles, the main three ideas unchanged, it also shows with no start colour.
7. Hostile text (text-injection test): faction, paint, brand and recipe names full of HTML never become markup.
8. Offline: no network requests at all, and it works with the network switched off.
9. Dark and light at 390 and 360 px, including a very long faction name: inside the screen, 44 px rows, contrast 4.5.
10. Nothing else changed: v29 check, Add step, Cancel, no pop-ups, no page errors.
Run all tests with `python3 tests/run_all.py`, or serve the repo folder and run this file on its own."""
import json, os, re, sys
from playwright.sync_api import sync_playwright

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from notice_watch import attach_notices

PORT = os.environ.get("SOG_PORT", "8765")
BASE = f"http://localhost:{PORT}/"
URL = BASE + "index.html"
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.realpath(os.path.join(HERE, ".."))
SHOTS = sys.argv[1] if len(sys.argv) > 1 else os.path.join(HERE, "screenshots")
results = []

def check(name, ok, detail=""):
    results.append(bool(ok))
    print(("PASS " if ok else "FAIL ") + name + ("" if ok else f"  -> {detail}"))

def read(name):
    return open(os.path.join(ROOT, name), encoding="utf-8").read()

HOSTILE = '<img src=x onerror="window.__pwned=1">Evil <b>Blue</b>'
HOSTILE_BRAND = '<script>window.__pwned=2</script>Brand'
# Games Workshop names, factions and game words that must never appear in the new text.
GW_WORDS = re.compile(r"\b(warhammer|games workshop|citadel|space marines?|ultramarines?|tyranids?|orks?|eldar|necrons?|blood angels?|dark angels?|chaos|imperium|adeptus|astartes|sigmar|40k|age of)\b", re.I)

PAINTS = [
    {"id": 1, "brand": "Citadel", "name": "Macragge Blue", "colour": "#0d407f", "status": "owned"},
    {"id": 2, "brand": "Citadel", "name": "Troll Slayer Orange", "colour": "#f4741c", "status": "owned"},
    {"id": 3, "brand": "Vallejo", "name": "Turquoise", "colour": "#2fb5a8", "status": "owned"},
    {"id": 4, "brand": "Citadel", "name": "Eshin Grey", "colour": "#4a4d52", "status": "owned"},
    {"id": 5, "brand": "Citadel", "name": "Fire Dragon Bright", "colour": "#ff6a00", "status": "wishlist"},
    {"id": 6, "brand": "Citadel", "name": "Rakarth Flesh", "colour": "#a7a28f", "status": "owned"},
    {"id": 7, "brand": "Citadel", "name": "Evil Sunz Scarlet", "colour": "#c1272d", "status": "owned"},
    {"id": 8, "brand": "Vallejo", "name": "Ink Sky", "colour": "#b5d7ee", "status": "owned"},
    {"id": 20, "brand": "Vallejo", "name": "Forest Green", "colour": "#228b22", "status": "owned"},
    {"id": 21, "brand": "Vallejo", "name": "Deep Purple", "colour": "#7b2d8b", "status": "owned"},
    {"id": 22, "brand": "Vallejo", "name": "Mid Blue A", "colour": "#3b6fb0", "status": "owned"},
    {"id": 23, "brand": "Vallejo", "name": "Mid Blue B", "colour": "#6b8fc2", "status": "owned"},
    {"id": 24, "brand": "Vallejo", "name": "Mid Blue C", "colour": "#5a7fb5", "status": "owned"},
    {"id": 25, "brand": "Vallejo", "name": "Burnt Orange", "colour": "#d2691e", "status": "owned"},
    {"id": 26, "brand": "Vallejo", "name": "Violet Storm", "colour": "#8a2be2", "status": "owned"},
]

def book(paints=None, recipes=None):
    return {"parts": ["Whole model", "Armour"], "techniques": ["Layer", "Base coat", "Wash"],
            "paints": PAINTS if paints is None else paints, "recipes": recipes or [], "schemes": [], "shorthand": {}, "v15": True}

def load(page, paints=None, settings=None, recipes=None, units=None):
    page.goto(URL)
    page.evaluate("""([b, s, u]) => { localStorage.clear();
        localStorage.setItem('shades-of-grey-recipes', JSON.stringify(b));
        if (u) localStorage.setItem('mini-tracker-models', JSON.stringify(u));
        if (s) localStorage.setItem('shades-of-grey-settings', JSON.stringify(s)); }""", [book(paints, recipes), settings, units])
    page.evaluate("""async () => { await new Promise(done => { const r = indexedDB.deleteDatabase('shades-of-grey-photos');
        r.onsuccess = r.onerror = r.onblocked = () => done(); }); }""")
    page.reload()
    page.wait_for_function("() => typeof APP_VERSION === 'string'")
    page.wait_for_timeout(400)

def blur(page):
    page.evaluate("() => document.activeElement && document.activeElement.blur()")
    page.wait_for_timeout(100)

def open_editor(page):
    blur(page)
    page.click('nav button[data-tab="recipes"]')
    page.wait_for_timeout(120)
    page.click("#new-recipe")
    page.wait_for_timeout(200)

def set_step_paint(page, step, name):
    """Type a paint into a step's first paint box; leaving the box fills in a known paint's brand and colour."""
    box = page.locator(f'[data-key="step-{step}-paint-0"]')
    box.fill(name)
    box.blur()
    page.wait_for_timeout(400)   # the panel waits a moment before redrawing

def add_step(page):
    page.click("#recipe-page button:has-text('+ Add step')")
    page.wait_for_timeout(150)

def rec(rid, name, part, paint_ids):
    return {"id": rid, "name": name, "part": part, "notes": "",
            "steps": [{"technique": "Base coat", "coats": 1, "paints": [{"paint": pid, "mix": None}], "ratio": "", "note": "", "optional": False} for pid in paint_ids]}

def edit_recipe(page, rid):
    blur(page)
    page.click('nav button[data-tab="recipes"]')
    page.wait_for_timeout(150)
    page.evaluate("(id) => startRecipeDraft(draftFrom(recipeById(id)))", rid)
    page.wait_for_timeout(300)

def open_panel(page):
    if not page.evaluate("() => document.getElementById('colour-ideas').open"):
        page.click("#colour-ideas > summary")
        page.wait_for_timeout(150)

def ideas(page):
    return page.evaluate("""() => [...document.querySelectorAll('#colour-ideas button.idea')].map(b => ({
        name: b.querySelector('.idea-name').childNodes[0].textContent,
        tag: b.querySelector('.idea-tag').textContent, why: b.querySelector('.idea-why').textContent }))""")

def pick_role(page, key):
    page.click(f'#colour-ideas [data-role="{key}"]')
    page.wait_for_timeout(120)

def tip(page):
    return page.evaluate("() => (document.getElementById('colour-ideas-tip') || {}).textContent || ''")

def press_check(page):
    page.click("#scheme-check-toggle")
    page.wait_for_timeout(150)

def result_text(page):
    return page.evaluate("() => (document.getElementById('scheme-result') || {}).innerText || ''")

def rows(page):
    return page.evaluate("""() => [...document.querySelectorAll('#scheme-result .scheme-list li')].map(li => ({
        cls: li.querySelector('.idea-tag').className.replace('idea-tag ', ''), tag: li.querySelector('.idea-tag').textContent,
        label: li.querySelector('.scheme-what strong').textContent, text: li.querySelector('.scheme-what').textContent.replace(li.querySelector('.scheme-what strong').textContent, '') }))""")

def verdict(page):
    return page.evaluate("() => (document.querySelector('#scheme-result .scheme-verdict') || {}).textContent || ''")

def shot(page, name):
    os.makedirs(SHOTS, exist_ok=True)
    page.screenshot(path=os.path.join(SHOTS, name))

def no_sideways(page):
    return page.evaluate("() => document.documentElement.scrollWidth <= window.innerWidth + 1")

def rgb(text):
    return [float(x) for x in re.findall(r"\d+(?:\.\d+)?", text)[:3]]

def luminance(c):
    def f(v):
        v = v / 255
        return v / 12.92 if v <= 0.03928 else ((v + 0.055) / 1.055) ** 2.4
    r, g, b = [f(x) for x in c]
    return 0.2126 * r + 0.7152 * g + 0.0722 * b

def contrast(a, b):
    la, lb = luminance(a), luminance(b)
    hi, lo = max(la, lb), min(la, lb)
    return (hi + 0.05) / (lo + 0.05)

def sentences(text):
    return [s for s in re.split(r"(?<=[.!?])\s+", text.strip()) if s]


def rec2(rid, name, part, paint_ids):
    return rec(rid, name, part, paint_ids)

def hist_rows(page):
    return page.evaluate("""() => [...document.querySelectorAll('#faction-history button.idea-pick')].map(b => ({
        name: b.querySelector('.idea-name').childNodes[0].textContent,
        tag: b.querySelector('.idea-tag').textContent, why: b.querySelector('.idea-why').textContent,
        note: (b.querySelector('.idea-note') || {}).textContent || '' }))""")

def hist_text(page):
    return page.evaluate("() => (document.getElementById('faction-history') || {}).innerText || ''")

def starter_rows(page):
    return page.evaluate("""() => [...document.querySelectorAll('#starter-list button.idea-pick')].map(b => ({
        name: b.querySelector('.idea-name').childNodes[0].textContent,
        tag: b.querySelector('.idea-tag').textContent, why: b.querySelector('.idea-why').textContent }))""")

def pick_scheme(page, key):
    page.click(f'#starter-schemes [data-scheme="{key}"]')
    page.wait_for_timeout(150)

def draft_steps(page):
    return page.evaluate("() => recipeDraft.steps.map(s => ({ n: s.paints[0].name, b: s.paints[0].brand, c: s.paints[0].colour, mix: s.paints[0].mix, note: s.note }))")

def new_from_unit(page, uid):
    blur(page)
    page.click('nav button[data-tab="recipes"]')
    page.wait_for_timeout(150)
    page.evaluate("(id) => startNewRecipe(id)", uid)
    page.wait_for_timeout(300)

def unit(uid, name, faction, recipes=None):
    u = {"id": uid, "name": name, "hobby": "Test game", "faction": faction, "stage": 2, "count": 5}
    if recipes: u["recipes"] = recipes
    return u

# Made-up factions and recipes (nothing here names a real army).
UNITS = [unit(1, "Troop A", "Gloom Legion", [101, 102, 106]), unit(2, "Troop B", "gloom legion ", [101, 103]),
         unit(3, "Other", "Other Host", [104]), unit(4, "No faction", "", [105]), unit(5, "Lonely", "Lonely Host")]
RECIPES = [rec(101, "Armour blue", "Whole model", [1, 22]), rec(102, "Orange trim", "Armour", [2, 22]),
           rec(103, "Skin and glow", "Skin", [25, 5, 22]), rec(104, "Other host recipe", "Armour", [7]),
           rec(105, "No faction recipe", "Armour", [21]), rec(106, "Visor glow", "Eyes", [8])]

def main():
    with sync_playwright() as p:
        browser = p.chromium.launch()
        ctx = browser.new_context(viewport={"width": 390, "height": 844})
        page = ctx.new_page()
        errors, dialogs, requests = [], [], []
        page.on("pageerror", lambda e: errors.append(str(e)))
        page.on("dialog", lambda d: (dialogs.append(d.message), d.dismiss()))
        notices = []
        attach_notices(page, notices.append)

        # ---------- 1. Versions and wiring ----------
        print("\n--- 1. Versions, wiring, what did not change ---")
        load(page, recipes=RECIPES, units=UNITS)
        html, app, sw, colour = read("index.html"), read("app.js"), read("sw.js"), read("colour.js")
        version = page.evaluate("APP_VERSION")
        check("APP_VERSION is v30 or later", float(version[1:]) >= 30, version)
        m = re.search(r'const VERSION = "([^"]+)"', sw)
        check("sw.js VERSION matches APP_VERSION", m and m.group(1) == version, m and m.group(1))
        tags = re.findall(r'<script src="(early|colour|app)\.js\?v=([\d.]+)"></script>', html)
        check("index.html still loads early.js, colour.js, then app.js, all with ?v= matching the version (v31 adds schemes.js in between, so four tags in all)",
              [t[0] for t in tags] == ["early", "colour", "app"] and len(re.findall(r"<script\b", html)) in (3, 4) and all(t[1] == version[1:] for t in tags), tags)
        check("sw.js lists the same app files as before (v31 adds schemes.js) and nothing else new", '"./colour.js" + CODE_TAG' in sw
              and len(re.findall(r'"\./[a-z-]+\.js" \+ CODE_TAG', sw)) in (3, 4), re.findall(r'"\./[^"]+"', sw))
        check("the comments naming the version number match", f'The "?v={version[1:]}" makes' in html and f'e.g. "app.js?v={version[1:]}"' in app)
        entry = page.evaluate("CHANGELOG.find(r => r.version === 'v30')")
        check("Updates has a v30 entry with at least two lines", entry and len(entry["changes"]) >= 2, entry)
        check("the newest Updates entry is the current version", page.evaluate("CHANGELOG[0].version") == version)
        check("the Updates entry says Pro preview, names both new parts and that nothing leaves the phone",
              entry and "Pro preview" in entry["changes"][0] and "used on this faction before" in entry["changes"][0]
              and "Starter schemes" in entry["changes"][1] and "sends nothing anywhere" in entry["changes"][1], entry)
        check("the v29 Updates entry is still there", page.evaluate("!!CHANGELOG.find(r => r.version === 'v29')"))
        check("DATA_VERSION is still 1", page.evaluate("DATA_VERSION") == 1)
        check("the three storage names are unchanged",
              all(k in app for k in ['STORAGE_KEY = "mini-tracker-models"', 'SETTINGS_KEY = "shades-of-grey-settings"', 'RECIPES_KEY = "shades-of-grey-recipes"']))
        csp = re.search(r'http-equiv="Content-Security-Policy"\s+content="([^"]+)"', html, re.S)
        policy = " ".join(csp.group(1).split()) if csp else ""
        hosts = set(re.findall(r"https?://[^\s;'\"]+", policy))
        check("script-src and connect-src are untouched, and the only outside address is still the one GoatCounter picture address",
              "script-src 'self' 'wasm-unsafe-eval';" in policy and "connect-src 'self';" in policy and hosts == {"https://dim3ry.goatcounter.com/count"}, (policy, hosts))
        panel_code = app[app.index("v28: \"COLOUR IDEAS\""):app.index('v18c: TIDY BRANDS')]
        check("the panel code has no network code, no storage, and still exactly one innerHTML (the panel's own clear)",
              not re.search(r"\bfetch\s*\(|XMLHttpRequest|sendBeacon|WebSocket|localStorage|sessionStorage|\beval\s*\(|new Function|insertAdjacentHTML|outerHTML", panel_code)
              and panel_code.count("innerHTML") == 1 and 'body.innerHTML = ""' in panel_code, [m.group(0) for m in re.finditer(r"innerHTML[^\n]*", panel_code)])
        check("colour.js was not touched by this chunk (no new maths needed)", "schemeCheck" in colour and "root.MinifolioColour = api;" in colour)
        schemes = page.evaluate("STARTER_SCHEMES")
        new_text = json.dumps(schemes) + json.dumps(page.evaluate("STARTER_MOODS")) + page.evaluate("""() => JSON.stringify(['Colours you\\'ve used on this faction before', 'Starter schemes',
            document.getElementById('colour-ideas') ? '' : ''])""")
        gw_extra = re.compile(r"\b(primaris|aeldari|skaven|nurgle|khorne|slaanesh|tzeentch|cadian|ultramar|adepta|sororitas|stormcast|space wolves|grey knights|imperial|hive fleet|waaagh)\b", re.I)
        check("the starter scheme text (v31: all schemes and the mood names) names no Games Workshop game, faction, scheme or product",
              not GW_WORDS.search(new_text) and not gw_extra.search(new_text), GW_WORDS.findall(new_text) + gw_extra.findall(new_text))
        check("there is no list of factions in the new code (faction names only ever come from the user's own units)",
              not re.search(r"(?i)faction[s]?\s*[:=]\s*\[", panel_code))

        # ---------- 2. Faction history ----------
        print("\n--- 2. Faction history ---")
        load(page, recipes=RECIPES, units=UNITS)
        edit_recipe(page, 106)
        open_panel(page)
        check("the card has a 'Colours you've used on this faction before' heading",
              page.inner_text("#faction-history .scheme-title") == "Colours you've used on this faction before")
        check("it names the faction as the user typed it", page.inner_text("#faction-history-for") == "Faction: Gloom Legion.", page.inner_text("#faction-history-for"))
        rows_h = hist_rows(page)
        names = [r["name"] for r in rows_h]
        check("paints from other recipes on units in the same faction are listed, most used first (units, then recipes, then name)",
              names == ["Mid Blue A", "Macragge Blue", "Burnt Orange", "Fire Dragon Bright", "Troll Slayer Orange"], names)
        check("a unit whose faction differs only by capitals and spaces counts as the same faction (Burnt Orange is only on that unit)", "Burnt Orange" in names)
        check("paints from another faction's recipe are not listed", "Evil Sunz Scarlet" not in names and "Deep Purple" not in names, names)
        check("the recipe being edited is not counted as history (its own paint, Ink Sky, is absent)", "Ink Sky" not in names, names)
        check("the reasons say how many units and recipes", [r["why"] for r in rows_h[:3]] == [
            "Used on 2 units in this faction, in 3 recipes.", "Used on 2 units in this faction, in 1 recipe.", "Used on 1 unit in this faction, in 1 recipe."],
              [r["why"] for r in rows_h[:3]])
        tag_by = {r["name"]: r["tag"] for r in rows_h}
        check("an owned paint says You own this, and a wishlist paint says You don't own this (never the first)",
              tag_by["Mid Blue A"] == "You own this" and tag_by["Fire Dragon Bright"] == "You don't own this", tag_by)
        check("every row is a button of at least 44 px with a swatch", page.evaluate("""() => [...document.querySelectorAll('#faction-history button.idea-pick')]
            .every(b => b.getBoundingClientRect().height >= 44 && b.querySelector('.swatch'))"""))
        check("the main three ideas are still exactly three 'idea' buttons (the new rows use another class)", page.locator("#colour-ideas button.idea").count() == 3)
        n0 = len(draft_steps(page))
        page.locator("#faction-history button.idea-pick").first.click()
        page.wait_for_timeout(250)
        steps = draft_steps(page)
        check("tapping a paint adds one new last step with that paint at 100%, 1 coat, and a plain note",
              len(steps) == n0 + 1 and steps[-1]["n"] == "Mid Blue A" and steps[-1]["b"] == "Vallejo" and steps[-1]["c"] == "#3b6fb0"
              and steps[-1]["mix"] == 100 and steps[-1]["note"] == "Used before on this faction", steps[-1])
        check("the card stays open and the paint just added is no longer offered",
              page.evaluate("() => document.getElementById('colour-ideas').open") and "Mid Blue A" not in [r["name"] for r in hist_rows(page)])
        check("a message says which step was added", any("Added step" in n and "Mid Blue A" in n for n in notices), notices[-3:])
        before = len(draft_steps(page))
        page.click("#recipe-page button:has-text('+ Add step')")
        page.wait_for_timeout(150)
        set_step_paint(page, before, "Macragge Blue")
        check("typing a paint into a step takes it out of the list too (the same paint is never offered twice)",
              "Macragge Blue" not in [r["name"] for r in hist_rows(page)], [r["name"] for r in hist_rows(page)])

        # A new recipe started from a unit uses that unit's faction.
        load(page, recipes=RECIPES, units=UNITS)
        new_from_unit(page, 2)
        open_panel(page)
        check("a new recipe started from a unit uses that unit's faction",
              page.inner_text("#faction-history-for") == "Faction: gloom legion." and "Mid Blue A" in [r["name"] for r in hist_rows(page)],
              (page.inner_text("#faction-history-for"), [r["name"] for r in hist_rows(page)]))
        check("for a brand-new recipe every other saved recipe counts, including 'Visor glow' on the same faction (so Ink Sky shows)",
              len(hist_rows(page)) == 6 and "Ink Sky" in [r["name"] for r in hist_rows(page)], [r["name"] for r in hist_rows(page)])

        # ---------- 3. Plain messages ----------
        print("\n--- 3. Plain messages ---")
        load(page, recipes=RECIPES, units=UNITS)
        open_editor(page)
        open_panel(page)
        txt = hist_text(page)
        check("a new recipe that is linked to no unit says so plainly and shows no paints",
              page.locator("#faction-history-none").count() == 1 and "not linked to a unit that has a faction" in txt
              and page.locator("#faction-history button").count() == 0 and page.locator("#faction-history-list").count() == 0, txt)
        check("the starter schemes show here too", page.locator("#starter-chips .chip").count() >= 6)
        load(page, recipes=[RECIPES[1]], units=UNITS)   # no Whole model recipe and no paints in the draft: there is no start colour
        open_editor(page)
        open_panel(page)
        check("with no start colour at all the card says so, and the faction history and starter schemes still show below it",
              "Add a paint to a step first" in page.inner_text("#colour-ideas .ideas-body") and page.locator("#colour-ideas button.idea").count() == 0
              and page.locator("#faction-history-none").count() == 1 and page.locator("#starter-chips .chip").count() >= 6)
        pick_scheme(page, "sand-teal")
        check("and a starter scheme can still be picked there", len(starter_rows(page)) == 4)
        load(page, recipes=RECIPES, units=UNITS)
        open_editor(page)
        open_panel(page)
        new_from_unit(page, 4)
        open_panel(page)
        check("a unit with no faction says the same plain thing", page.locator("#faction-history-none").count() == 1 and page.locator("#faction-history button").count() == 0)
        new_from_unit(page, 5)
        open_panel(page)
        txt = hist_text(page)
        check("a faction with no history says so plainly and shows nothing else",
              page.inner_text("#faction-history-for") == "Faction: Lonely Host." and "No history yet" in page.inner_text("#faction-history-empty")
              and page.locator("#faction-history button").count() == 0, txt)
        many = UNITS + [unit(6, "Big", "Big Host", [110]), unit(7, "Tiny", "Tiny Host", [120])]
        more = RECIPES + [rec(110, "Everything", "Armour", [1, 2, 3, 4, 5, 6, 7, 8, 20]), rec(120, "One paint", "Armour", [1])]
        load(page, recipes=more, units=many)
        new_from_unit(page, 6)
        open_panel(page)
        check("more than six paints: only the six most used are shown, and a line says so",
              len(hist_rows(page)) == 6 and "Showing the 6 most used of 9." in hist_text(page), (len(hist_rows(page)), hist_text(page)[-80:]))
        new_from_unit(page, 7)
        open_panel(page)
        set_step_paint(page, 0, "Macragge Blue")
        check("when every paint used on the faction is already in the recipe, it says that",
              "Every paint you have used on this faction is already in this recipe." in hist_text(page) and page.locator("#faction-history button").count() == 0, hist_text(page))

        # ---------- 4. Starter schemes ----------
        print("\n--- 4. Starter schemes ---")
        check("a set of schemes (v31 grew it to 24) with unique keys and names", len(schemes) >= 6 and len({s["key"] for s in schemes}) == len(schemes)
              and len({s["name"] for s in schemes}) == len(schemes), len(schemes))
        check("each scheme is a handful (3 to 5) of colours with a part, a plain word and a real hex, no repeated hex",
              all(3 <= len(s["colours"]) <= 5 and all(re.fullmatch(r"#[0-9a-f]{6}", c["hex"]) and c["part"] and c["look"] for c in s["colours"])
                  and len({c["hex"] for c in s["colours"]}) == len(s["colours"]) for s in schemes))
        check("each reason is one or two short sentences, and each summary is a short phrase",
              all(1 <= len(sentences(s["reason"])) <= 2 and len(s["reason"]) <= 200 and len(s["summary"]) <= 70 for s in schemes), [len(s["reason"]) for s in schemes])
        check("the example scheme from the plan is there (cold blue armour, gold trim, red eyes)", any(s["summary"] == "Cold blue armour, gold trim, red eyes" for s in schemes))
        load(page, recipes=RECIPES, units=UNITS)
        edit_recipe(page, 106)
        open_panel(page)
        chips = page.evaluate("() => [...document.querySelectorAll('#starter-chips .chip')].map(c => [c.textContent, c.getAttribute('aria-pressed')])")
        check("one chip per scheme (all moods shown to start), named after the colours, none picked to start, and no rows yet",
              len(chips) == len(schemes) and all(c[1] == "false" for c in chips) and [c[0] for c in chips] == [s["name"] for s in schemes]
              and page.locator("#starter-list").count() == 0, chips)
        pick_scheme(page, "blue-gold")
        rows_s = starter_rows(page)
        check("picking a scheme shows its summary, its reason and one paint row per colour",
              page.inner_text("#starter-summary") == "Cold blue armour, gold trim, red eyes" and page.inner_text("#starter-reason") == schemes[0]["reason"]
              and len(rows_s) == 4, (page.inner_text("#starter-summary"), len(rows_s)))
        check("the chip is pressed and keeps the focus", page.get_attribute('#starter-schemes [data-scheme="blue-gold"]', "aria-pressed") == "true"
              and page.evaluate("() => document.activeElement.dataset.scheme") == "blue-gold")
        check("each row says which part it is for and the colour in plain words",
              [r["why"] for r in rows_s] == ["Armour: a deep blue.", "Armour highlight: a lighter blue.", "Trim: gold.", "Eyes: a bright red."], [r["why"] for r in rows_s])
        check("the four paints are four different paints", len({r["name"] for r in rows_s}) == 4, rows_s)
        check("every row has one of the three honest tags",
              all(r["tag"] in ("You own this", "Closest you own", "Not in your palette") for r in rows_s), [r["tag"] for r in rows_s])
        n0 = len(draft_steps(page))
        page.locator("#starter-list button.idea-pick").first.click()
        page.wait_for_timeout(250)
        steps = draft_steps(page)
        check("tapping a paint adds one new last step (that paint, 100%, 1 coat) with a plain note saying which scheme and part",
              len(steps) == n0 + 1 and steps[-1]["n"] == rows_s[0]["name"] and steps[-1]["mix"] == 100
              and steps[-1]["note"] == "Starter scheme (Cold blue and gold): armour", steps[-1])
        check("the scheme is still picked after the step is added", page.get_attribute('#starter-schemes [data-scheme="blue-gold"]', "aria-pressed") == "true"
              and page.locator("#starter-list button.idea-pick").count() == 4)
        pick_scheme(page, "green-bone")
        check("picking another scheme replaces the first", page.inner_text("#starter-summary") == "Dark green armour, bone trim, orange glow"
              and page.get_attribute('#starter-schemes [data-scheme="blue-gold"]', "aria-pressed") == "false")
        pick_role(page, "trim")
        check("changing the role keeps the scheme picked (and the role's tip still shows)",
              page.inner_text("#starter-summary") == "Dark green armour, bone trim, orange glow" and tip(page).startswith("Tip: "))
        pick_scheme(page, "green-bone")
        check("tapping the picked chip again closes it", page.locator("#starter-list").count() == 0
              and page.get_attribute('#starter-schemes [data-scheme="green-bone"]', "aria-pressed") == "false")
        for s in schemes:
            pick_scheme(page, s["key"])
            r = starter_rows(page)
            check(f"{s['name']}: one row per colour, all different paints, honest tags", len(r) == len(s["colours"]) and len({x["name"] for x in r}) == len(r)
                  and all(x["tag"] in ("You own this", "Closest you own", "Not in your palette") for x in r), r)
            pick_scheme(page, s["key"])

        # ---------- 5. Honesty ----------
        print("\n--- 5. Honesty ---")
        owned_exact = [{"id": 1, "brand": "Test", "name": "Exact Blue", "colour": "#1f4287", "status": "owned"}] + PAINTS[1:]
        wish_exact = [{"id": 1, "brand": "Test", "name": "Wishlist Blue", "colour": "#1f4287", "status": "wishlist"}]
        load(page, paints=owned_exact, recipes=RECIPES, units=UNITS)
        edit_recipe(page, 106)
        open_panel(page)
        pick_scheme(page, "blue-gold")
        r = starter_rows(page)
        check("an owned paint of exactly the colour asked for says You own this", r[0]["name"] == "Exact Blue" and r[0]["tag"] == "You own this", r[0])
        load(page, paints=wish_exact, recipes=[rec(106, "Visor glow", "Eyes", [1])], units=[unit(1, "Troop A", "Gloom Legion", [106])])
        edit_recipe(page, 106)
        open_panel(page)
        pick_scheme(page, "blue-gold")
        r = starter_rows(page)
        check("a wishlist paint of exactly the colour asked for never says You own this (it says Not in your palette)",
              r[0]["name"] == "Wishlist Blue" and r[0]["tag"] == "Not in your palette" and all(x["tag"] != "You own this" for x in r), r)
        load(page, paints=[], recipes=[], units=UNITS)
        open_editor(page)
        open_panel(page)
        allnone = True
        for s in schemes:
            pick_scheme(page, s["key"])
            allnone = allnone and all(x["tag"] == "Not in your palette" for x in starter_rows(page)) and len(starter_rows(page)) == len(s["colours"])
            pick_scheme(page, s["key"])
        check("with an empty palette every starter paint says Not in your palette (the built-in list is used, nothing is claimed as owned)", allnone)
        load(page, paints=[{"id": 1, "brand": "Test", "name": "Rough Blue", "colour": "#3b6fb0", "status": "owned"}], recipes=[rec(106, "Visor glow", "Eyes", [1])],
             units=[unit(1, "Troop A", "Gloom Legion", [106])])
        edit_recipe(page, 106)
        open_panel(page)
        pick_scheme(page, "blue-gold")
        notes_text = page.evaluate("() => [...document.querySelectorAll('#starter-list .idea-pick')].map(b => [b.querySelector('.idea-tag').textContent, (b.querySelector('.idea-note') || {}).textContent || ''])")
        check("an owned paint that is only close says Closest you own and 'Similar, not exact' or 'Not very close'",
              any(t == "Closest you own" and n in ("Similar, not exact.", "Not very close. It is the nearest we found.") for t, n in notes_text), notes_text)

        # ---------- 6. Where it sits ----------
        print("\n--- 6. Where it sits, other things unchanged ---")
        load(page, recipes=RECIPES, units=UNITS)
        edit_recipe(page, 106)
        open_panel(page)
        order = page.evaluate("""() => { const ids = ['colour-ideas-tip', 'faction-history', 'starter-schemes', 'scheme-check'];
            const pos = ids.map(i => { const e = document.getElementById(i); return e ? [...e.parentElement.children].indexOf(e) : -1; });
            return { pos, sameParent: ids.every(i => document.getElementById(i).parentElement === document.querySelector('#colour-ideas .ideas-body')) }; }""")
        check("order in the card: tip, then the three ideas, then faction history, then starter schemes, then the check",
              order["sameParent"] and order["pos"] == sorted(order["pos"]) and -1 not in order["pos"], order)
        check("the card is still labelled Pro preview", page.inner_text("#colour-ideas .pro-pill") == "Pro preview")
        check("the footnote is still last", page.evaluate("() => document.querySelector('#colour-ideas .ideas-body').lastElementChild.textContent.includes('Nothing leaves your phone')"))
        check("the main ideas, tip and Whole model start-from still work", page.locator("#colour-ideas button.idea").count() == 3 and page.locator("#colour-ideas-base").count() == 1)

        # ---------- 7. Hostile text ----------
        print("\n--- 7. Hostile text (text-injection test) ---")
        hostile_paints = [{"id": 90, "brand": HOSTILE_BRAND, "name": HOSTILE, "colour": "#3b6fb0", "status": "owned"},
                          {"id": 91, "brand": "Test", "name": "Plain Red", "colour": "#c1272d", "status": "owned"}]
        hostile_units = [unit(1, HOSTILE + " Troop", HOSTILE + " Faction", [140, 106]), unit(2, "Second", HOSTILE + " Faction", [141])]
        hostile_recipes = [rec(140, HOSTILE + " recipe", "Armour", [90]), rec(141, "Second recipe", "Armour", [90, 91]), rec(106, "Mine", "Eyes", [91])]
        load(page, paints=hostile_paints, recipes=hostile_recipes, units=hostile_units)
        edit_recipe(page, 106)
        open_panel(page)
        pick_scheme(page, "blue-gold")
        texth = hist_text(page)
        check("a faction and a paint full of HTML show as plain text, in the history",
              "<img" in texth and "Evil" in texth and page.locator("#faction-history img, #faction-history script, #faction-history b").count() == 0, texth[:200])
        check("nothing ran (no onerror, no script), and the whole card has no injected tags",
              page.evaluate("() => window.__pwned") is None and page.locator("#colour-ideas img, #colour-ideas script, #colour-ideas ideas-body b").count() == 0)
        page.locator("#faction-history button.idea-pick").first.click()
        page.wait_for_timeout(250)
        steps = draft_steps(page)
        check("tapping the hostile paint adds it as text (the step holds the characters, no markup is built from them)",
              steps[-1]["n"] == HOSTILE and page.evaluate("() => window.__pwned") is None and page.locator("#recipe-page img[src='x']").count() == 0)
        check("the aria label of the row is plain text too", page.evaluate("() => [...document.querySelectorAll('#faction-history button')].every(b => !b.querySelector('img'))"))

        # ---------- 8. Offline ----------
        print("\n--- 8. Offline ---")
        load(page, recipes=RECIPES, units=UNITS)
        edit_recipe(page, 106)
        open_panel(page)
        requests.clear()
        page.on("request", lambda rq: requests.append(rq.url))
        ctx.set_offline(True)
        for key in ["blue-gold", "sand-teal", "dark-bright"]:
            pick_scheme(page, key)
        pick_role(page, "gems")
        ok_off = len(starter_rows(page)) == 4 and len(hist_rows(page)) == 5
        page.locator("#faction-history button.idea-pick").first.click()
        page.wait_for_timeout(250)
        ctx.set_offline(False)
        check("with the network switched off, the history and the starter schemes still work", ok_off)
        check("picking schemes, changing roles and tapping paints made no network requests at all", requests == [], requests)

        # ---------- 9. Phone sizes, dark and light ----------
        print("\n--- 9. Dark and light at 390 and 360 px ---")
        LONG = "Averyveryveryverylongfactionnamewithnospacesatalltotestwrapping" + "x" * 30
        long_units = [unit(1, "Troop A", LONG, [101, 106]), unit(2, "Troop B", LONG, [103])]
        for appearance in ["dark", "light"]:
            for width in [390, 360]:
                page.set_viewport_size({"width": width, "height": 844})
                for case, uns in [("normal", UNITS), ("long name", long_units)]:
                    tag = f"{appearance} {width}px {case}"
                    load(page, recipes=RECIPES, units=uns, settings={"appearance": appearance})
                    edit_recipe(page, 106)
                    open_panel(page)
                    pick_scheme(page, "blue-gold")
                    page.locator("#faction-history").scroll_into_view_if_needed()
                    page.wait_for_timeout(200)
                    geo = page.evaluate("""() => { const c = document.getElementById('colour-ideas').getBoundingClientRect();
                        const inside = (el) => { const r = el.getBoundingClientRect(); return r.left >= c.left - 0.5 && r.right <= c.right + 0.5; };
                        const picks = [...document.querySelectorAll('button.idea-pick')];
                        const chips = [...document.querySelectorAll('#starter-schemes .chip')];
                        const parts = ['#faction-history', '#faction-history-for', '#starter-schemes', '#starter-summary', '#starter-reason'].map(s => document.querySelector(s));
                        return { cl: c.left, cr: c.right, w: window.innerWidth, picks: picks.length, picksInside: picks.every(inside),
                                 minH: Math.min(...picks.map(b => b.getBoundingClientRect().height)), chipsInside: chips.every(inside),
                                 partsInside: parts.every(inside), chipH: Math.min(...chips.map(b => b.getBoundingClientRect().height)) }; }""")
                    check(f"{tag}: the card is inside the screen, and the new parts, rows and chips are inside the card",
                          geo["cl"] >= 0 and geo["cr"] <= geo["w"] + 0.5 and geo["partsInside"] and geo["picksInside"] and geo["chipsInside"], geo)
                    check(f"{tag}: there are history rows and four starter rows, each at least 44 px tall", geo["picks"] >= 5 and geo["minH"] >= 44, geo)
                    check(f"{tag}: the chips are tappable size (at least 36 px, like the other chips)", geo["chipH"] >= 36, geo)
                    check(f"{tag}: no sideways scroll", no_sideways(page))
                    col = page.evaluate("""() => { const bg = (el) => { let e = el; while (e) { const v = getComputedStyle(e).backgroundColor;
                            const m = v.match(/rgba\\(.*,\\s*([\\d.]+)\\)/);
                            if (v && v !== 'transparent' && !(m && parseFloat(m[1]) < 0.9)) return v; e = e.parentElement; } return 'rgb(0,0,0)'; };
                        const out = {};
                        const pairs = [['history title', '#faction-history .scheme-title'], ['faction line', '#faction-history-for'], ['starter title', '#starter-schemes .scheme-title'],
                                       ['starter hint', '#starter-schemes > .hint'], ['summary', '#starter-summary'], ['reason', '#starter-reason'],
                                       ['chip off', '#starter-schemes .chip[aria-pressed="false"]'], ['chip on', '#starter-schemes .chip[aria-pressed="true"]'],
                                       ['row name', '.idea-pick .idea-name'], ['row why', '.idea-pick .idea-why'], ['row add', '.idea-pick .idea-add']];
                        for (const [k, s] of pairs) { const el = document.querySelector(s); if (el) out[k] = [getComputedStyle(el).color, bg(el)]; }
                        [...document.querySelectorAll('.idea-pick .idea-tag')].forEach((el, i) => { out['pill ' + i + ' ' + el.className] = [getComputedStyle(el).color, bg(el)]; });
                        [...document.querySelectorAll('.idea-pick .idea-note')].forEach((el, i) => { out['note ' + i] = [getComputedStyle(el).color, bg(el)]; });
                        return out; }""")
                    bad = {k: round(contrast(rgb(v[0]), rgb(v[1])), 2) for k, v in col.items() if contrast(rgb(v[0]), rgb(v[1])) < 4.5}
                    check(f"{tag}: titles, lines, chips, rows, pills and notes all have contrast of at least 4.5", not bad and len(col) >= 12, (bad, list(col)))
                    shot(page, f"v30-schemes-{case.replace(' ', '-')}-{appearance}-{width}.png")
        page.set_viewport_size({"width": 390, "height": 844})

        # ---------- 10. Nothing else changed ----------
        print("\n--- 10. Nothing else changed ---")
        load(page)
        open_editor(page)
        n = page.locator(".step-edit").count()
        add_step(page)
        check("+ Add step still adds an empty step", page.locator(".step-edit").count() == n + 1)
        set_step_paint(page, 0, "Brand New Paint X")
        page.wait_for_timeout(150)
        check("the 'Do you own these?' card still appears for a paint that is new to your palette",
              page.locator("#recipe-own").count() == 1 and page.is_visible("#recipe-own"))
        check("the Colour ideas card starts closed", page.evaluate("() => document.getElementById('colour-ideas').open") is False)
        add_step(page)
        set_step_paint(page, 1, "Macragge Blue")
        open_panel(page)
        check("the card is still labelled Pro preview, still has the scheme check, and still ends with the v28 footnote",
              page.inner_text("#colour-ideas .pro-pill") == "Pro preview" and page.locator("#scheme-check-toggle").count() == 1
              and "Nothing leaves your phone" in page.inner_text("#colour-ideas .ideas-body"))
        page.click("#recipe-page button.plain-button:has-text('Cancel')")
        page.wait_for_timeout(250)
        if page.is_visible("#dialog-yes"):
            page.click("#dialog-yes")
            page.wait_for_timeout(250)
        check("Cancel still leaves the editor", page.evaluate("() => recipeDraft") is None)
        check("no real browser pop-ups appeared", not dialogs, dialogs)
        check("no page errors", not errors, errors[:3])
        browser.close()

    print(f"\n{sum(results)} of {len(results)} checks passed")
    sys.exit(0 if all(results) else 1)

if __name__ == "__main__":
    main()
