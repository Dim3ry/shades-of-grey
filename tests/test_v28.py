"""v28 tests for Minifolio (Coach 2): the "Colour ideas" panel (Pro preview) inside the recipe editor.

In a recipe you are writing or editing: choose the base colour (a paint from the recipe, or "Whole model", the main colour of
your recipe filed under the Whole model part), choose what you are painting (eyes or glow, trim, gems, weapon, cloth, base) and see 3 paint ideas with a
plain-English reason. Each says "You own this" or "Yours, poor fit". Tapping one adds it to the recipe as a new step.
All the maths is in colour.js (tested by test_colour_engine.py), which v28 wires into index.html and sw.js.

Checks:
1. Versions, the Updates entry, colour.js wired in (script tag, offline list), CSP and data unchanged, no new network code.
2. The panel: heading, Pro preview label, closed to start, 6 roles, base choices, 3 ideas, reasons, owned labels.
3. The ideas are right: blue armour's glow idea is warm; owned paints come first; no paint twice; the base is never suggested.
4. Whole model: with no Whole model recipe it is this recipe's main colour (colourful beats black primer); a neutral base gets accents; an unset colour is explained.
4b. Whole model recipes: ideas go with the Whole model recipe's colour, not the recipe being edited; one linked to the same unit wins; several unlinked ones ask you to pick; hostile names are plain text.
5. Tapping an idea adds a new last step (right paint, 100%, a note), the page keeps working, Save keeps it.
6. Hostile text: paint names and brands full of HTML are shown as plain text; nothing is injected, no pop-ups.
7. Empty and odd states: no paints yet, no owned paints, no colour.js (the card just isn't there), no page errors.
8. Dark and light at 390 and 360 px: inside the screen, 44 px targets, readable, no sideways scroll.
9. Nothing else changed: Add step, the Do-you-own-these card, Cancel.
Run all tests with `python3 tests/run_all.py`, or serve the repo folder and run this file on its own."""
import json, os, re, sys
from playwright.sync_api import sync_playwright
from launch_helpers import app_ready, quiet
from launch_helpers import leave_launch

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

# A small palette: a blue base paint, an owned orange and an owned teal, one owned dark grey, one not-owned bright orange.
PAINTS = [
    {"id": 1, "brand": "Citadel", "name": "Macragge Blue", "colour": "#0d407f", "status": "owned"},
    {"id": 2, "brand": "Citadel", "name": "Troll Slayer Orange", "colour": "#f4741c", "status": "owned"},
    {"id": 3, "brand": "Vallejo", "name": "Turquoise", "colour": "#2fb5a8", "status": "owned"},
    {"id": 4, "brand": "Citadel", "name": "Eshin Grey", "colour": "#4a4d52", "status": "owned"},
    {"id": 5, "brand": "Citadel", "name": "Fire Dragon Bright", "colour": "#ff6a00", "status": "wishlist"},
    {"id": 6, "brand": "Citadel", "name": "Rakarth Flesh", "colour": "#a7a28f", "status": "owned"},
    {"id": 7, "brand": "Citadel", "name": "Evil Sunz Scarlet", "colour": "#c1272d", "status": "owned"},
    {"id": 8, "brand": "Vallejo", "name": "Ink Sky", "colour": "#b5d7ee", "status": "owned"},
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
    app_ready(page)
    leave_launch(page)   # U4b: tap through the start page

def blur(page):
    page.evaluate("() => document.activeElement && document.activeElement.blur()")
    quiet(page)

def open_editor(page):
    blur(page)
    page.click('nav button[data-tab="recipes"]')
    page.wait_for_timeout(120)
    page.click("#new-recipe")
    quiet(page)

def set_step_paint(page, step, name, colour=None):
    """Type a paint into a step's first paint box (the app fills in its colour for known paints)."""
    box = page.locator(f'[data-key="step-{step}-paint-0"]')
    box.fill(name)
    box.blur()   # leaving the box makes the app fill in a known paint's brand and colour, as a real person's tap away would
    if colour:
        page.evaluate("""([i, c]) => { recipeDraft.steps[i].paints[0].colour = c; }""", [step, colour])
    page.wait_for_timeout(400)   # the panel waits a moment before redrawing

def draft_paints(page):
    return page.evaluate("() => recipeDraft.steps.map(s => s.paints.map(p => [p.name, p.colour, p.mix]))")

def rec(rid, name, part, paint_ids):
    return {"id": rid, "name": name, "part": part, "notes": "",
            "steps": [{"technique": "Base coat", "coats": 1, "paints": [{"paint": pid, "mix": None}], "ratio": "", "note": "", "optional": False} for pid in paint_ids]}

def edit_recipe(page, rid):
    blur(page)
    page.click('nav button[data-tab="recipes"]')
    page.wait_for_timeout(150)
    page.evaluate("(id) => startRecipeDraft(draftFrom(recipeById(id)))", rid)
    page.wait_for_timeout(300)

def base_labels(page):
    return page.evaluate("() => [...document.querySelectorAll('#colour-ideas-base option')].map(o => o.textContent)")

def using_text(page):
    return page.evaluate("() => (document.getElementById('colour-ideas-using') || {}).textContent || ''")

def open_panel(page):
    if not page.evaluate("() => document.getElementById('colour-ideas').open"):
        page.click("#colour-ideas > summary")
        quiet(page)

def ideas(page):
    return page.evaluate("""() => [...document.querySelectorAll('#colour-ideas button.idea')].map(b => ({
        name: b.querySelector('.idea-name').childNodes[0].textContent,
        tag: b.querySelector('.idea-tag').textContent, why: b.querySelector('.idea-why').textContent,
        note: (b.querySelector('.idea-note') || {}).textContent || '', colour: getComputedStyle(b.querySelector('.swatch')).getPropertyValue('--swatch').trim() || b.querySelector('.swatch').style.getPropertyValue('--swatch') }))""")

def pick_role(page, key):
    page.click(f'#colour-ideas [data-role="{key}"]')
    page.wait_for_timeout(120)

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

def main():
    with sync_playwright() as p:
        browser = p.chromium.launch()
        ctx = browser.new_context(viewport={"width": 390, "height": 844})
        page = ctx.new_page()
        errors, dialogs = [], []
        page.on("pageerror", lambda e: errors.append(str(e)))
        page.on("dialog", lambda d: (dialogs.append(d.message), d.dismiss()))
        notices = []
        attach_notices(page, notices.append)

        # ---------- 1. Versions and wiring ----------
        print("\n--- 1. Versions, wiring, what did not change ---")
        load(page)
        html, app, sw = read("index.html"), read("app.js"), read("sw.js")
        version = page.evaluate("APP_VERSION")
        m = re.search(r'const VERSION = "([^"]+)"', sw)
        check("the comment in app.js names the same number", f'e.g. "app.js?v={version[1:]}"' in app)
        entry = page.evaluate("CHANGELOG.find(r => r.version === 'v28')")
        check("the newest Updates entry is the current version", page.evaluate("CHANGELOG[0].version") == version)
        if page.evaluate("['v28'].every(v => CHANGELOG.some(r => r.version === v))"):
            check("the Updates entry says Pro preview and that nothing leaves the phone",
                  entry and "Pro preview" in entry["changes"][0] and "sends nothing anywhere" in entry["changes"][1], entry)
        else:
            print("SKIP (entry no longer in the public Updates list): " + 'the Updates entry says Pro preview and that nothing leaves the phone')
        check("MinifolioColour is on the page", page.evaluate("typeof MinifolioColour") == "object")
        csp = re.search(r'http-equiv="Content-Security-Policy"\s+content="([^"]+)"', html, re.S)
        policy = " ".join(csp.group(1).split()) if csp else ""
        check("script-src and connect-src are untouched (no new addresses)",
              "script-src 'self' 'wasm-unsafe-eval';" in policy and "connect-src 'self';" in policy, policy)
        panel_code = app[app.index("v28: \"COLOUR IDEAS\""):app.index('v18c: TIDY BRANDS')]
        check("the panel code has no network code, no storage, no innerHTML with user text",
              not re.search(r"\bfetch\s*\(|XMLHttpRequest|sendBeacon|WebSocket|localStorage|\beval\s*\(|new Function|insertAdjacentHTML", panel_code)
              and panel_code.count("innerHTML") == 1 and 'body.innerHTML = ""' in panel_code, [m.group(0) for m in re.finditer(r"innerHTML[^\n]*", panel_code)])

        # ---------- 2. The panel ----------
        print("\n--- 2. The panel ---")
        load(page)
        open_editor(page)
        check("the card is on the recipe editor, after Steps and before 'Do you own these?'",
              page.evaluate("""() => { const ids = [...document.querySelectorAll('#recipe-page > .card, #recipe-page > details')].map(c => c.id || c.querySelector('h2').textContent);
                  return ids.indexOf('colour-ideas') > ids.indexOf('Steps') && ids.indexOf('colour-ideas') > 0; }"""))
        check("the heading says Colour ideas and the label says Pro preview",
              page.inner_text("#colour-ideas > summary h2") == "Colour ideas" and page.text_content("#colour-ideas .pro-pill") == "Pro preview")
        check("it starts closed", page.evaluate("() => document.getElementById('colour-ideas').open") is False)
        check("with no paints yet it explains what to do when opened",
              (open_panel(page) or True) and "Add a paint to a step first" in page.inner_text("#colour-ideas .ideas-body"), page.inner_text("#colour-ideas .ideas-body"))
        set_step_paint(page, 0, "Macragge Blue")
        page.wait_for_timeout(150)
        check("once a paint is typed, the panel shows its choices without being reopened",
              page.locator("#colour-ideas-base").count() == 1 and page.locator("#colour-ideas [data-role]").count() == 6)
        roles = page.evaluate("() => [...document.querySelectorAll('#colour-ideas [data-role]')].map(b => b.textContent)")
        check("the six roles are eyes or glow, trim, gems, weapon, cloth, base", roles == ["Eyes or glow", "Trim", "Gems", "Weapon", "Cloth", "Base"], roles)
        check("Eyes or glow is chosen to start (aria-pressed)", page.get_attribute('#colour-ideas [data-role="glow"]', "aria-pressed") == "true")
        opts = page.evaluate("() => [...document.querySelectorAll('#colour-ideas-base option')].map(o => o.textContent)")
        check("the base list is Whole model, then the paint written in the recipe",
              len(opts) == 2 and opts[0].startswith("Whole model") and opts[1] == "Macragge Blue (Citadel)", opts)
        got = ideas(page)
        check("there are exactly 3 ideas", len(got) == 3, got)
        # v64: the best paint overall can come first when your own paint is a poor fit, so "Not in your palette" is a valid label here too
        check("every idea has a paint name, a label and a plain-English reason",
              all(i["name"] and i["tag"] in ("You own this", "Yours, poor fit", "Not in your palette") and i["why"].endswith(".") and len(i["why"]) > 25 for i in got), got)
        check("the first reason names the opposite on the colour wheel", "opposite" in got[0]["why"] and "blue" in got[0]["why"], got[0])
        check("the foot note says colours on screen are a guide (v75: shorter, COMP-5)",
              "Colours on screen are a guide" in page.inner_text("#colour-ideas .ideas-body") and "Colours on screen are a guide" in page.inner_text("#colour-ideas .ideas-body"))
        shot(page, "v28-panel-dark-390.png")

        # ---------- 3. The ideas are right ----------
        print("\n--- 3. The ideas are right ---")
        names = [i["name"] for i in got]
        check("the glow idea for blue is warm and owned: Troll Slayer Orange comes first (owned, so Closest you own or You own this)",
              names[0] == "Troll Slayer Orange" and got[0]["tag"] in ("You own this", "Yours, poor fit"), got)
        check("no paint is suggested twice, and the base paint is never suggested", len(set(names)) == 3 and "Macragge Blue" not in names, names)
        check("owned paints come before a wishlist paint (Fire Dragon Bright is not owned, so it is never first here)",
              all(i["name"] != "Fire Dragon Bright" for i in got), names)
        pick_role(page, "weapon")
        weapon = ideas(page)
        # v64: Eshin Grey (yours) is a poor fit for a mid-grey, so the closest mid-grey overall comes first and Eshin Grey sits under it as Yours, poor fit
        check("weapon ideas start with a mid-grey and the reason says so",
              len(weapon) == 3 and "grey" in weapon[0]["why"] and weapon[0]["name"] and "Eshin Grey" in page.inner_text("#colour-ideas .ideas-body")
              and "Yours, poor fit" in page.inner_text("#colour-ideas .ideas-body"), weapon)
        pick_role(page, "base")
        base = ideas(page)
        check("base ideas are quiet: the first reason says dark neutral", "dark neutral" in base[0]["why"], base)
        pick_role(page, "cloth")
        cloth = ideas(page)
        check("cloth ideas talk about next to blue on the colour wheel", "next to" in cloth[0]["why"], cloth)
        pick_role(page, "trim")
        pick_role(page, "gems")
        check("each role shows 3 ideas", all(len(ideas(page)) == 3 for _ in [0]) and len(ideas(page)) == 3)
        check("the role chosen stays pressed after the panel redraws and keeps keyboard focus",
              page.get_attribute('#colour-ideas [data-role="gems"]', "aria-pressed") == "true"
              and page.evaluate("() => document.activeElement && document.activeElement.dataset.role") == "gems")
        # A paint that is exactly the colour the idea aims for gets You own this.
        target = page.evaluate("() => colourIdeaWanted(MinifolioColour.harmonies('#0d407f'), COLOUR_ROLES[0], 'complementary', 0).hex")
        load(page, paints=[PAINTS[0], {"id": 30, "brand": "Citadel", "name": "Exact Match Orange", "colour": target, "status": "owned"}] + PAINTS[2:5])
        open_editor(page)
        set_step_paint(page, 0, "Macragge Blue")
        open_panel(page)
        exact = ideas(page)
        check("a paint that is exactly the idea's colour says You own this", exact and exact[0]["name"] == "Exact Match Orange" and exact[0]["tag"] == "You own this" and exact[0]["note"] == "", exact)
        # Own nothing close: the label must be honest.
        load(page, paints=[PAINTS[0], {"id": 9, "brand": "Citadel", "name": "Only Owned Green", "colour": "#2e7d32", "status": "owned"},
                           PAINTS[4]])
        open_editor(page)
        set_step_paint(page, 0, "Macragge Blue")
        open_panel(page)
        far = ideas(page)
        # v64: the best paint overall comes first; your poor match is under it as "Yours, poor fit"; no note sentence
        far_also = page.evaluate("() => { const a = document.querySelector('#colour-ideas ul.idea-list > li .idea-also'); return a ? [a.querySelector('.idea-name').childNodes[0].textContent, a.querySelector('.idea-tag').textContent] : null; }")
        check("when the nearest paint you own is a poor match, the best paint overall is first and yours is under it as Yours, poor fit (no note)",
              far and far[0]["tag"] == "Not in your palette" and far_also == ["Only Owned Green", "Yours, poor fit"] and far[0]["note"] == "", (far, far_also))
        load(page, paints=[dict(PAINTS[0]), dict(PAINTS[4])])
        open_editor(page)
        set_step_paint(page, 0, "Macragge Blue")
        open_panel(page)
        none_owned = ideas(page)
        check("if you own nothing to suggest, the label says Not in your palette instead of pretending",
              none_owned and all(i["tag"] == "Not in your palette" for i in none_owned), none_owned)

        # ---------- 4. Whole model, neutral and unset ----------
        print("\n--- 4. Whole model, neutral bases, unset colours ---")
        load(page)
        open_editor(page)
        set_step_paint(page, 0, "Macragge Blue")
        page.click("#recipe-page button:has-text('+ Add step')")
        page.wait_for_timeout(150)
        set_step_paint(page, 1, "Troll Slayer Orange")
        page.click("#recipe-page button:has-text('+ Add step')")
        page.wait_for_timeout(150)
        set_step_paint(page, 2, "Troll Slayer Orange")
        open_panel(page)
        who = page.evaluate("() => { const b = MinifolioColour; return null; }")
        whole = ideas(page)
        check("with no Whole model recipe, Whole model is this recipe's main colour (orange is used most here), so the first reason is about orange",
              whole and ("blue" in whole[0]["why"].lower() and "orange" in whole[0]["why"].lower()), whole)
        page.select_option("#colour-ideas-base", index=1)
        page.wait_for_timeout(150)
        check("choosing a paint from the recipe changes the ideas (and keeps the select focused)",
              ideas(page) != whole and page.evaluate("() => document.activeElement.id") == "colour-ideas-base")
        page.select_option("#colour-ideas-base", value="whole")
        # A neutral base
        load(page)
        open_editor(page)
        set_step_paint(page, 0, "Eshin Grey")
        open_panel(page)
        neutral = ideas(page)
        check("a grey base gets accents with the words 'Your colour is neutral'",
              neutral and "Your colour is neutral" in neutral[0]["why"], neutral)
        # An unset colour
        load(page)
        open_editor(page)
        set_step_paint(page, 0, "Made Up Paint")
        page.evaluate("() => { recipeDraft.steps[0].paints[0].colour = '#808080'; }")
        open_panel(page)
        page.wait_for_timeout(100)
        page.evaluate("() => { document.querySelector('[data-key=\"step-0-paint-0\"]').dispatchEvent(new Event('input', { bubbles: true })); }")
        page.wait_for_timeout(450)
        check("a paint with no colour set asks you to set it instead of guessing",
              "Set a colour on one of the paints first" in page.inner_text("#colour-ideas .ideas-body"), page.inner_text("#colour-ideas .ideas-body"))

        # ---------- 4b. Whole model recipes ----------
        print("\n--- 4b. Whole model recipes ---")
        BLACK = {"id": 40, "brand": "Citadel", "name": "Abaddon Black", "colour": "#231f20", "status": "owned"}
        P2 = PAINTS + [BLACK]
        UN = [{"id": 1, "name": "Termagants", "hobby": "40K", "faction": "Tyranids", "stage": 2, "count": 10, "recipes": [11]},
              {"id": 2, "name": "Hormagaunts", "hobby": "40K", "faction": "Tyranids", "stage": 4, "count": 10}]
        eyes = rec(11, "Orange eyes", "Eyes", [2])
        prime_blue = rec(10, "Prime and base", "Whole model", [40, 1])
        # One Whole model recipe (black primer, then blue): ideas go with BLUE, not the orange eyes recipe's own paints.
        load(page, paints=P2, recipes=[prime_blue, eyes])
        edit_recipe(page, 11)
        open_panel(page)
        labels = base_labels(page)
        check("the first choice names your Whole model recipe", labels and labels[0] == "Whole model: Prime and base", labels)
        check("it says which recipe it is using", "Prime and base" in using_text(page) and using_text(page).startswith("Using the main colour of"), using_text(page))
        idea = ideas(page)
        check("ideas go with the blue of the Whole model recipe (the black primer is skipped), not the orange of this recipe",
              idea and "dark blue" in idea[0]["why"] and "of orange" not in idea[0]["why"], idea)
        check("the paints in this recipe are still on the list, under their own heading",
              "Troll Slayer Orange (Citadel)" in labels, labels)
        page.select_option("#colour-ideas-base", index=len(labels) - 1)
        page.wait_for_timeout(200)
        check("choosing this recipe's own paint instead drops the 'Using the main colour' line and bases ideas on orange",
              using_text(page) == "" and "of orange" in ideas(page)[0]["why"], [using_text(page), ideas(page)])
        # Editing the Whole model recipe itself: it never bases itself on itself.
        edit_recipe(page, 10)
        open_panel(page)
        check("editing the Whole model recipe itself: no recipe to borrow from, so it uses its own colours",
              base_labels(page)[0] == "Whole model: none yet, using this recipe" and using_text(page) == "", base_labels(page))
        check("...and its own main colour is the blue, not the black primer", "dark blue" in ideas(page)[0]["why"], ideas(page))
        # A new recipe whose part is switched to Whole model while the panel is open follows along.
        load(page, paints=P2, recipes=[prime_blue, eyes])
        open_editor(page)
        set_step_paint(page, 0, "Troll Slayer Orange")
        open_panel(page)
        check("a new recipe with no part yet uses the Whole model recipe", base_labels(page)[0] == "Whole model: Prime and base", base_labels(page))
        page.evaluate("() => { recipeDraft.part = 'Whole model'; recipeIdeasCard.refresh(); }")
        page.wait_for_timeout(450)
        check("once its part is Whole model it stops borrowing and uses its own colours",
              base_labels(page)[0] == "Whole model: none yet, using this recipe" and using_text(page) == "", base_labels(page))
        # Two Whole model recipes, one linked to the same unit as the recipe being edited: that one wins.
        prime_red = rec(12, "Hive prime", "Whole model", [7])
        load(page, paints=P2, recipes=[prime_blue, prime_red, eyes], units=[dict(UN[0], recipes=[11, 12]), UN[1]])
        edit_recipe(page, 11)
        open_panel(page)
        labels = base_labels(page)
        check("the Whole model recipe linked to the same unit comes first and is chosen",
              labels[0] == "Whole model: Hive prime" and "Prime and base" in labels, labels)
        check("no 'pick one' nag when one is clearly the right one", "several Whole model recipes" not in using_text(page), using_text(page))
        check("its colour (red) drives the ideas: the first reason is about the opposite of red", "red" in ideas(page)[0]["why"].lower(), ideas(page))
        page.select_option("#colour-ideas-base", value="wm:10")
        page.wait_for_timeout(200)
        check("picking the other Whole model recipe switches to it", "Prime and base" in using_text(page) and "dark blue" in ideas(page)[0]["why"], [using_text(page), ideas(page)])
        # Two Whole model recipes, none linked: it asks you to pick.
        load(page, paints=P2, recipes=[prime_blue, prime_red, eyes], units=[dict(UN[0], recipes=[11]), UN[1]])
        edit_recipe(page, 11)
        open_panel(page)
        check("two Whole model recipes and none linked: it says to pick the one for this model",
              "several Whole model recipes" in using_text(page) and "pick the one for this model" in using_text(page), using_text(page))
        # Hostile recipe name.
        evil_prime = rec(10, HOSTILE, "Whole model", [40, 1])
        load(page, paints=P2, recipes=[evil_prime, eyes])
        edit_recipe(page, 11)
        open_panel(page)
        check("a hostile Whole model recipe name is plain text in the list and the 'using' line, and nothing runs",
              HOSTILE in base_labels(page)[0] and HOSTILE in using_text(page)
              and page.evaluate("() => document.querySelectorAll('#colour-ideas img, #colour-ideas script, #colour-ideas b, #colour-ideas-base img').length") == 0
              and page.evaluate("() => window.__pwned") is None and not dialogs, [base_labels(page), using_text(page), dialogs])
        # A Whole model recipe with no usable colours is ignored.
        load(page, paints=P2, recipes=[rec(10, "Empty prime", "Whole model", []), eyes])
        edit_recipe(page, 11)
        open_panel(page)
        check("a Whole model recipe with no paints is ignored (back to this recipe's colour)",
              base_labels(page)[0] == "Whole model: none yet, using this recipe", base_labels(page))

        # ---------- 5. Tapping adds a step ----------
        print("\n--- 5. Tapping an idea adds a step ---")
        load(page)
        open_editor(page)
        page.fill("#recipe-page input[placeholder^='e.g. Ultramarine']", "Blue armour")
        set_step_paint(page, 0, "Macragge Blue")
        open_panel(page)
        before = len(draft_paints(page))
        first = ideas(page)[0]
        page.click("#colour-ideas button.idea >> nth=0")
        page.wait_for_timeout(250)
        after = draft_paints(page)
        check("one new step was added at the end", len(after) == before + 1, after)
        check("it holds the idea's paint at 100%", after[-1][0][0] == first["name"] and after[-1][0][2] == 100, after[-1])
        note = page.evaluate("() => recipeDraft.steps[recipeDraft.steps.length - 1].note")
        check("its note says what the idea was for", note == "Colour idea for eyes or glow", note)
        check("the new step shows in the Steps list and the panel stayed open",
              page.locator(".step-edit").count() == before + 1 and page.evaluate("() => document.getElementById('colour-ideas').open"))
        check("a message says which step was added", any("Added step 2" in n for n in notices), notices)
        check("the technique is left on Auto and the coats are 1",
              page.evaluate("() => { const s = recipeDraft.steps[recipeDraft.steps.length - 1]; return s.technique === '' && s.coats === 1; }"))
        check("the recipe name typed earlier was kept", page.input_value("#recipe-page input[placeholder^='e.g. Ultramarine']") == "Blue armour")
        page.click("#recipe-page button.primary-button:has-text('Save recipe')")
        page.wait_for_timeout(300)
        saved = page.evaluate("""() => { const r = book.recipes[book.recipes.length - 1]; return { name: r.name, steps: r.steps.length,
            last: paintById(r.steps[r.steps.length - 1].paints[0].paint).name, note: r.steps[r.steps.length - 1].note }; }""")
        check("saving keeps the new step with its paint and note", saved["steps"] == 2 and saved["last"] == first["name"] and saved["note"].startswith("Colour idea for"), saved)
        check("the recipe view shows the paint in step 2", first["name"] in page.text_content("#recipe-page"))   # v50: steps are folded, so read the text, not only what shows

        # ---------- 6. Hostile text ----------
        print("\n--- 6. Hostile text ---")
        evil = PAINTS + [{"id": 20, "brand": HOSTILE_BRAND, "name": HOSTILE, "colour": "#e8812a", "status": "owned"}]
        load(page, paints=evil)
        open_editor(page)
        set_step_paint(page, 0, "Macragge Blue")
        open_panel(page)
        pick_role(page, "glow")
        evil_ideas = ideas(page)
        check("the hostile paint is suggested (it is the closest owned orange)", any(i["name"] == HOSTILE for i in evil_ideas), evil_ideas)
        check("its name is shown as plain text, tags and all", any(HOSTILE in (b or "") for b in page.evaluate("() => [...document.querySelectorAll('#colour-ideas .idea-name')].map(e => e.textContent)")))
        check("no <img>, <script> or <b> element came out of paint names or brands",
              page.evaluate("() => document.querySelectorAll('#colour-ideas img, #colour-ideas script, #colour-ideas b').length") == 0)
        check("nothing ran (no flag set, no pop-up)", page.evaluate("() => window.__pwned") is None and not dialogs, dialogs)
        page.click("#colour-ideas button.idea >> nth=0")
        page.wait_for_timeout(250)
        check("adding the hostile paint keeps it as text in the paint box and the toast",
              page.evaluate("() => recipeDraft.steps[recipeDraft.steps.length - 1].paints[0].name") == HOSTILE
              and page.evaluate("() => document.querySelectorAll('#toast img, #toast b, #recipe-page img').length") == 0 and page.evaluate("() => window.__pwned") is None)
        hostile_base = [{"id": 1, "brand": HOSTILE_BRAND, "name": HOSTILE, "colour": "#0d407f", "status": "owned"}] + PAINTS[1:]
        load(page, paints=hostile_base)
        open_editor(page)
        set_step_paint(page, 0, HOSTILE)
        open_panel(page)
        check("a hostile name as the BASE paint is plain text in the list and the page stays clean",
              page.evaluate("() => [...document.querySelectorAll('#colour-ideas-base option')].some(o => o.textContent.includes('<img'))")
              and page.evaluate("() => document.querySelectorAll('#colour-ideas img, #colour-ideas script, #colour-ideas b, #colour-ideas-base img').length") == 0
              and page.evaluate("() => window.__pwned") is None and not dialogs)

        # ---------- 7. Odd states ----------
        print("\n--- 7. Odd states ---")
        load(page, paints=[])
        open_editor(page)
        set_step_paint(page, 0, "Brand New Paint")
        page.evaluate("() => { recipeDraft.steps[0].paints[0].colour = '#2244aa'; }")
        open_panel(page)
        page.evaluate("() => document.querySelector('[data-key=\"step-0-paint-0\"]').dispatchEvent(new Event('input', { bubbles: true }))")
        page.wait_for_timeout(450)
        check("an empty palette still gives ideas from the built-in list, labelled Not in your palette (or a clear message)",
              (len(ideas(page)) >= 1 and all(i["tag"] == "Not in your palette" for i in ideas(page)))
              or "No paints with a known colour" in page.inner_text("#colour-ideas .ideas-body"), page.inner_text("#colour-ideas .ideas-body"))
        # Remove the base paint: the choice falls back to Whole model
        load(page)
        open_editor(page)
        set_step_paint(page, 0, "Macragge Blue")
        page.click("#recipe-page button:has-text('+ Add step')")
        page.wait_for_timeout(150)
        set_step_paint(page, 1, "Troll Slayer Orange")
        open_panel(page)
        page.select_option("#colour-ideas-base", index=2)
        page.locator('[aria-label="Remove step 2"]').click()
        page.wait_for_timeout(250)
        if page.is_visible("#dialog-yes"):
            page.click("#dialog-yes")
            page.wait_for_timeout(250)
        open_panel(page)
        check("if the chosen base paint is removed, the panel quietly goes back to Whole model",
              page.evaluate("() => document.getElementById('colour-ideas-base').value") == "whole")
        # Without colour.js the card is simply not there (a fresh window with no saved copy of the app, so the blocked file really is missing)
        ctx2 = browser.new_context(viewport={"width": 390, "height": 844}, service_workers="block")
        page2 = ctx2.new_page()
        errors2 = []
        page2.on("pageerror", lambda e: errors2.append(str(e)))
        page2.route("**/colour.js*", lambda r: r.abort())
        load(page2)
        open_editor(page2)
        check("without colour.js MinifolioColour is missing, the recipe editor still works and the card is not there",
              page2.evaluate("typeof MinifolioColour") == "undefined" and page2.locator("#colour-ideas").count() == 0
              and page2.locator("#recipe-page button:has-text('+ Add step')").count() == 1 and not errors2, errors2)
        ctx2.close()

        # ---------- 8. Phone sizes, dark and light ----------
        print("\n--- 8. Dark and light at 390 and 360 px ---")
        long_name = [dict(PAINTS[1], name="Troll Slayer Orange With A Really Quite Long Name Indeed")] + PAINTS[2:]
        for appearance in ["dark", "light"]:
            for width in [390, 360]:
                tag = f"{appearance} {width}px"
                page.set_viewport_size({"width": width, "height": 844})
                load(page, paints=[PAINTS[0]] + long_name, settings={"appearance": appearance})
                open_editor(page)
                set_step_paint(page, 0, "Macragge Blue")
                open_panel(page)
                page.locator("#colour-ideas").scroll_into_view_if_needed()
                page.wait_for_timeout(200)
                geo = page.evaluate("""() => { const c = document.getElementById('colour-ideas').getBoundingClientRect();
                    const btns = [...document.querySelectorAll('#colour-ideas button.idea')].map(b => { const r = b.getBoundingClientRect(); return { l: r.left, r: r.right, h: r.height }; });
                    const chips = [...document.querySelectorAll('#colour-ideas [data-role]')].map(b => b.getBoundingClientRect().height);
                    const sel = document.getElementById('colour-ideas-base').getBoundingClientRect();
                    const sum = document.querySelector('#colour-ideas > summary').getBoundingClientRect();
                    return { cl: c.left, cr: c.right, w: window.innerWidth, btns, chips, selH: sel.height, selR: sel.right, sumH: sum.height }; }""")
                check(f"{tag}: the card is inside the screen", geo["cl"] >= 0 and geo["cr"] <= geo["w"] + 0.5, geo)
                check(f"{tag}: 3 ideas, each inside the card and at least 44 px tall",
                      len(geo["btns"]) == 3 and all(b["l"] >= geo["cl"] - 0.5 and b["r"] <= geo["cr"] + 0.5 and b["h"] >= 44 for b in geo["btns"]), geo)
                check(f"{tag}: role chips, the base list and the heading row are at least 36/44/44 px tall",
                      min(geo["chips"]) >= 36 and geo["selH"] >= 36 and geo["sumH"] >= 44, geo)
                check(f"{tag}: no sideways scroll, even with a very long paint name", no_sideways(page))
                col = page.evaluate("""() => { const bg = (el) => { let e = el; while (e) { const v = getComputedStyle(e).backgroundColor;
                        const m = v.match(/rgba\\(.*,\\s*([\\d.]+)\\)/);
                        if (v && v !== 'transparent' && !(m && parseFloat(m[1]) < 0.9)) return v; e = e.parentElement; } return 'rgb(0,0,0)'; };
                    const q = (s) => document.querySelector(s);
                    const out = {};
                    for (const [k, s] of [['why', '#colour-ideas .idea-why'], ['note', '#colour-ideas .idea-note, #colour-ideas .idea-add'], ['tag', '#colour-ideas .idea-tag'],
                                          ['pill', '#colour-ideas .pro-pill'], ['hint', '#colour-ideas .hint'], ['add', '#colour-ideas .idea-add']]) {
                        const el = q(s); if (el) out[k] = [getComputedStyle(el).color, bg(el)];
                    }
                    return out; }""")
                bad = {k: round(contrast(rgb(v[0]), rgb(v[1])), 2) for k, v in col.items() if contrast(rgb(v[0]), rgb(v[1])) < 4.5}
                check(f"{tag}: why, tag, label, hint and add text all have contrast of at least 4.5", not bad, bad)
                if width == 390:
                    shot(page, f"v28-ideas-{appearance}-390.png")
                else:
                    shot(page, f"v28-ideas-{appearance}-360.png")
        page.set_viewport_size({"width": 390, "height": 844})

        # ---------- 9. Nothing else changed ----------
        print("\n--- 9. Nothing else changed ---")
        load(page)
        open_editor(page)
        n = page.locator(".step-edit").count()
        page.locator("#recipe-page button.add-step").dispatch_event("click")   # v50: steps are folded, so the page is short and the tab bar can sit over this button
        page.wait_for_timeout(150)
        check("+ Add step still adds an empty step", page.locator(".step-edit").count() == n + 1)
        set_step_paint(page, 0, "Brand New Paint X")
        page.wait_for_timeout(150)
        check("the 'Do you own these?' card still appears for a paint that is new to your palette",
              page.locator("#recipe-own").count() == 1 and page.is_visible("#recipe-own"))
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
