"""v29 tests for Minifolio (Coach 3): "Smarter tips" in the Colour ideas panel (Pro preview).

Two new things inside the recipe editor's Colour ideas card:
  (1) a hand-written tip for the chosen role (eyes or glow, trim, gems, weapon, cloth, base), and role-specific reasons that
      replace the general reason on an idea where they say it better;
  (2) "Does this scheme hang together?": a button that checks the colours of the recipe being edited (too many strong colours,
      no light and dark, one suggested focus colour), in short plain words, always saying it is only a guide.
The maths for (2) is MinifolioColour.schemeCheck in colour.js (tested in Node by tests/colour_engine_check.js). "Whole model"
still means the main colour of your recipe filed under the Whole model part (Coach 2); the check looks at the recipe being edited.

Checks:
1. Versions, the v29 Updates entry, wiring unchanged (no new file), CSP and data unchanged, no network or storage code, no GW names.
2. Role tips: one per role, 1-2 short sentences, shown when the role is chosen, text from the app (never from paint names).
3. Role-specific reasons are used where they exist (and the general reason still covers the rest).
4. The check: heading, button, closed to start, needs two colours, button toggles, focus stays, state kept across roles.
5. The check's answers on real recipes: good scheme, too many strong colours, flat, both problems; one focus colour; no paint names.
6. It updates live as paints change; paints with no colour are left out and say so.
7. Whole model coexists: ideas still follow the Whole model recipe's colour; the check looks at the recipe being edited.
8. Hostile text (text-injection test): names, brands and recipe names full of HTML never become markup in the tips or the check.
9. Offline: role changes and the check make no network requests at all, and work with the network switched off.
10. An older colour.js without schemeCheck: the card still works, the check section just isn't there.
11. Dark and light at 390 and 360 px: inside the screen, 44 px button, readable (contrast 4.5), no sideways scroll.
12. Nothing else changed: v28 behaviour, Add step, Cancel, no pop-ups, no page errors.
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
    # v50: steps are folded, so the page can be short and the tab bar can sit over this button; send the tap straight to it.
    page.locator("#recipe-page button.add-step").dispatch_event("click")
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

# The real recipes used below (paint ids from PAINTS).
GOOD = rec(101, "Good scheme", "Armour", [1, 1, 2, 4, 8])            # dark blue x2, orange, grey, pale blue
MANY = rec(102, "Too many colours", "Armour", [1, 1, 2, 20, 21, 7, 8])  # five strong colours
FLAT = rec(103, "Flat blues", "Armour", [22, 23, 24])                 # three mid blues of similar lightness
BOTH = rec(104, "Both problems", "Armour", [7, 22, 20, 25, 26])       # five strong colours, all mid lightness
ALL_RECIPES = [GOOD, MANY, FLAT, BOTH]

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
        load(page, recipes=ALL_RECIPES)
        html, app, sw, colour = read("index.html"), read("app.js"), read("sw.js"), read("colour.js")
        version = page.evaluate("APP_VERSION")
        m = re.search(r'const VERSION = "([^"]+)"', sw)
        check("the comment in app.js names the same number", f'e.g. "app.js?v={version[1:]}"' in app)
        entry = page.evaluate("CHANGELOG.find(r => r.version === 'v29')")
        check("the newest Updates entry is the current version", page.evaluate("CHANGELOG[0].version") == version)
        if page.evaluate("['v29'].every(v => CHANGELOG.some(r => r.version === v))"):
            check("the Updates entry mentions Pro preview, 'only a guide' and that nothing leaves the phone",
                  entry and "Pro preview" in entry["changes"][0] and "only a guide" in entry["changes"][1] and "sends nothing anywhere" in entry["changes"][1], entry)
        else:
            print("SKIP (entry no longer in the public Updates list): " + "the Updates entry mentions Pro preview, 'only a guide' and that nothing leaves the phone")
        csp = re.search(r'http-equiv="Content-Security-Policy"\s+content="([^"]+)"', html, re.S)
        policy = " ".join(csp.group(1).split()) if csp else ""
        hosts = set(re.findall(r"https?://[^\s;'\"]+", policy))
        check("script-src and connect-src are untouched, and the only outside address is still the one GoatCounter picture address",
              "script-src 'self' 'wasm-unsafe-eval';" in policy and "connect-src 'self';" in policy and hosts == {"https://dim3ry.goatcounter.com/count"}, (policy, hosts))
        panel_code = app[app.index("v28: \"COLOUR IDEAS\""):app.index('v18c: TIDY BRANDS')]
        check("the panel code (now with tips and the check) has no network code, no storage, no innerHTML with user text",
              not re.search(r"\bfetch\s*\(|XMLHttpRequest|sendBeacon|WebSocket|localStorage|sessionStorage|\beval\s*\(|new Function|insertAdjacentHTML|outerHTML", panel_code)
              and panel_code.count("innerHTML") == 1 and 'body.innerHTML = ""' in panel_code, [m.group(0) for m in re.finditer(r"innerHTML[^\n]*", panel_code)])
        scheme_code = colour[colour.index("does a scheme hang together"):colour.index("const api = {")]
        check("the scheme check in colour.js has no network, storage or page code",
              not re.search(r"fetch\(|XMLHttpRequest|WebSocket|sendBeacon|localStorage|sessionStorage|document\.|window\.|innerHTML|eval\(|new Function|https?://", scheme_code))
        check("colour.js still adds exactly one name to the page", "root.MinifolioColour = api;" in colour and len(re.findall(r"root\.[A-Za-z]+ =", colour)) == 1)
        new_text = page.evaluate("""() => JSON.stringify([COLOUR_ROLES.map(r => [r.tip, r.why]), SCHEME_NEEDS_TWO, SCHEME_ONLY_A_GUIDE,
            ['Does this scheme hang together?', 'Check this recipe', 'Hide the check']])""")
        sample = [schemeWordsText for schemeWordsText in [page.evaluate("""() => JSON.stringify([
            schemeCheckWords(MinifolioColour.schemeCheck([{ colour: '#0d407f', uses: 3 }, { colour: '#f4741c', uses: 1 }, { colour: '#0b0b0b', uses: 1 }])),
            schemeCheckWords(MinifolioColour.schemeCheck([{ colour: '#3b6fb0', uses: 2 }, { colour: '#6b8fc2', uses: 1 }]))])""")]][0]
        check("the new text names no Games Workshop game, faction or product", not GW_WORDS.search(new_text) and not GW_WORDS.search(sample), GW_WORDS.findall(new_text + sample))
        check("the new text has no angle brackets or ampersands (it is plain text, shown with textContent)", not re.search(r"[<>&]", new_text + sample))

        # ---------- 2. Role tips ----------
        print("\n--- 2. Role tips ---")
        load(page)
        open_editor(page)
        set_step_paint(page, 0, "Macragge Blue")
        open_panel(page)
        keys = ["glow", "trim", "gems", "weapon", "cloth", "base"]
        want = page.evaluate("() => COLOUR_ROLES.map(r => [r.key, r.tip])")
        check("every role has a hand-written tip", [k for k, _ in want] == keys and all(t and len(t) > 30 for _, t in want), want)
        check("each tip is one or two short plain sentences (under 140 characters in all)",
              all(1 <= len(sentences(t)) <= 2 and len(t) < 140 for _, t in want), [(k, len(t), len(sentences(t))) for k, t in want])
        check("the tips are all different", len({t for _, t in want}) == 6)
        check("the eyes tip says the brightest, most saturated spot on the model", "brightest, most saturated spot on the model" in dict(want)["glow"])
        shown = {}
        for key, text in want:
            pick_role(page, key)
            shown[key] = tip(page)
        check("choosing a role shows that role's tip, after the label 'Tip:'", all(shown[k] == "Tip: " + t for k, t in want), shown)
        check("the tip sits under the role buttons and above the ideas",
              page.evaluate("""() => { const t = document.getElementById('colour-ideas-tip'), chips = document.querySelector('#colour-ideas [data-role]').parentElement, first = document.querySelector('#colour-ideas button.idea');
                  return !!(chips.compareDocumentPosition(t) & Node.DOCUMENT_POSITION_FOLLOWING) && !!(t.compareDocumentPosition(first) & Node.DOCUMENT_POSITION_FOLLOWING); }"""))
        check("the card still says Pro preview and still has exactly 6 roles", page.inner_text("#colour-ideas .pro-pill") == "Pro preview" and page.locator("#colour-ideas [data-role]").count() == 6)

        # ---------- 3. Role-specific reasons ----------
        print("\n--- 3. Role-specific reasons ---")
        expect = {
            "glow": ["is the opposite of dark blue, so eyes in it stand out the most.", "is almost opposite dark blue. Eyes still stand out, with a softer feel.", "is almost opposite dark blue. Eyes still stand out, with a softer feel."],
            "trim": ["is the opposite of dark blue, so trim in it gives a bold, clear edge.", "sits next to dark blue on the colour wheel, so trim in it looks neat and calm.", "A pale trim lifts the edges of dark blue and makes the shapes easy to read."],
            "gems": ["is spaced evenly round the colour wheel from dark blue, so gems in it are rich but don't clash.", "is spaced evenly round the colour wheel from dark blue, so gems in it are rich but don't clash.", "is the opposite of dark blue, so gems in it pop as small bright spots."],
            "weapon": ["A mid grey keeps the weapon calm next to dark blue, so the eyes and face stay the focus.", "A dark neutral keeps the weapon quiet next to dark blue.", "sits next to dark blue on the colour wheel, so the weapon matches the rest of the model."],
            "cloth": ["cloth sits next to dark blue on the colour wheel, so it looks calm and matches.", "cloth sits next to dark blue on the colour wheel, so it looks calm and matches.", "is spaced evenly round the colour wheel from dark blue: lively cloth that doesn't clash."],
            "base": ["A dark neutral base lets dark blue on the model stand out.", "A mid grey base is neutral, so it won't pull the eye away from dark blue.", "sits next to dark blue on the colour wheel, so the base feels part of the model."],
        }
        for key in keys:
            pick_role(page, key)
            got = ideas(page)
            check(f"{key}: three ideas, each reason uses the role's own wording", len(got) == 3 and all(g["why"].endswith(e) for g, e in zip(got, expect[key])), [g["why"] for g in got])
        every = []
        for key in keys:
            pick_role(page, key)
            every += [g["why"] for g in ideas(page)]
        names = [pnt["name"] for pnt in PAINTS]
        check("no reason has a leftover { } placeholder, an empty word, a paint name, or is more than one or two sentences",
              all("{" not in w and "}" not in w and "  " not in w and not any(n.lower() in w.lower() for n in names) and 1 <= len(sentences(w)) <= 2 and len(w) < 130 for w in every), [w for w in every if len(w) >= 130 or "{" in w])
        check("every reason starts with a capital letter and ends with a full stop", all(w[0].isupper() and w.endswith(".") for w in every), every)
        # Where the role has no better wording, the general sentence is still used (neutral base: accents).
        load(page, paints=[PAINTS[3], PAINTS[1], PAINTS[7], PAINTS[2]])
        open_editor(page)
        set_step_paint(page, 0, "Eshin Grey")
        open_panel(page)
        pick_role(page, "glow")
        grey_glow = ideas(page)
        check("a grey base with eyes: the eyes wording for neutral colours is used", grey_glow and "eyes or glow stand out without clashing" in grey_glow[0]["why"] and grey_glow[0]["why"].startswith("Your colour is neutral"), grey_glow)
        pick_role(page, "weapon")
        grey_weapon = ideas(page)
        check("a grey base with a weapon: mid and dark use the weapon wording, the accent falls back to the general sentence",
              len(grey_weapon) == 3 and "keeps the weapon calm" in grey_weapon[0]["why"] and "keeps the weapon quiet" in grey_weapon[1]["why"]
              and grey_weapon[2]["why"].startswith("Your colour is neutral, so a ") and grey_weapon[2]["why"].endswith("accent stands out without clashing."), grey_weapon)

        # ---------- 4. The check: the controls ----------
        print("\n--- 4. The check: the controls ---")
        load(page, recipes=ALL_RECIPES)
        open_editor(page)
        set_step_paint(page, 0, "Macragge Blue")
        open_panel(page)
        check("the heading says Does this scheme hang together?", page.inner_text("#scheme-check .scheme-title") == "Does this scheme hang together?")
        check("it sits inside the Colour ideas card, below the ideas and above the footnote",
              page.evaluate("""() => { const c = document.getElementById('scheme-check'), card = document.getElementById('colour-ideas'), last = [...card.querySelectorAll('button.idea')].pop();
                  const foot = card.querySelector('.ideas-body').lastElementChild;
                  return card.contains(c) && !!(last.compareDocumentPosition(c) & Node.DOCUMENT_POSITION_FOLLOWING) && !!(c.compareDocumentPosition(foot) & Node.DOCUMENT_POSITION_FOLLOWING) && foot.textContent.includes('Colours on screen are a guide'); }"""))
        check("the button says Check this recipe and nothing is shown yet",
              page.inner_text("#scheme-check-toggle") == "Check this recipe" and page.get_attribute("#scheme-check-toggle", "aria-expanded") == "false" and page.locator("#scheme-result").count() == 0)
        press_check(page)
        check("with one colour it says to add at least two, plus the only-a-guide line",
              "Needs two paints with colours set" in result_text(page) and "guide" in result_text(page) and page.locator("#scheme-result .scheme-list").count() == 0, result_text(page))
        check("the button now says Hide the check and is marked expanded; focus stayed on it",
              page.inner_text("#scheme-check-toggle") == "Hide the check" and page.get_attribute("#scheme-check-toggle", "aria-expanded") == "true"
              and page.evaluate("() => document.activeElement && document.activeElement.id") == "scheme-check-toggle")
        pick_role(page, "gems")
        check("the check stays open when you change role", page.locator("#scheme-result").count() == 1)
        press_check(page)
        check("pressing again hides it", page.locator("#scheme-result").count() == 0 and page.inner_text("#scheme-check-toggle") == "Check this recipe")
        press_check(page)
        page.click("#colour-ideas > summary")
        page.wait_for_timeout(120)
        page.click("#colour-ideas > summary")
        page.wait_for_timeout(200)
        check("closing and reopening the card keeps the check open", page.locator("#scheme-result").count() == 1)

        # ---------- 5. The check's answers ----------
        print("\n--- 5. The check's answers on real recipes ---")
        load(page, recipes=ALL_RECIPES)
        edit_recipe(page, 101)
        open_panel(page)
        press_check(page)
        r = rows(page)
        check("good scheme: the verdict says it hangs together", verdict(page) == "Yes, this looks like it hangs together.", verdict(page))
        check("good scheme: three rows, labelled Strong colours, Light and dark, Focus colour", [x["label"] for x in r] == ["Strong colours: ", "Light and dark: ", "Focus colour: "], r)
        check("good scheme: strong colours are Fine and name dark blue and orange",
              r[0]["tag"] == "Fine" and r[0]["cls"] == "own" and "2 (dark blue and orange)" in r[0]["text"] and "good number" in r[0]["text"], r[0])
        check("good scheme: light and dark is Fine", r[1]["tag"] == "Fine" and "depth" in r[1]["text"], r[1])
        check("good scheme: exactly one focus colour is suggested, the orange, against the main dark blue",
              sum(1 for x in r if x["label"] == "Focus colour: ") == 1 and r[2]["tag"] == "Suggestion" and "Let orange be the star" in r[2]["text"] and "dark blue" in r[2]["text"], r[2])
        shot(page, "v29-check-good-dark-390.png")
        edit_recipe(page, 102)
        open_panel(page)
        r = rows(page)
        check("too many colours: the verdict is 'Nearly. One thing to look at.'", verdict(page) == "Nearly. One thing to look at.", verdict(page))
        check("too many colours: strong colours says Look at this, counts five and names them",
              r[0]["tag"] == "Look at this" and r[0]["cls"] == "near" and r[0]["text"].startswith("You have 5: ") and all(w in r[0]["text"] for w in ["dark blue", "orange", "green", "purple", "red"]) and "fight for attention" in r[0]["text"], r[0])
        check("too many colours: light and dark is still Fine (a pale paint is in the recipe)", r[1]["tag"] == "Fine", r[1])
        check("too many colours: it still suggests one focus colour", sum(1 for x in r if x["label"] == "Focus colour: ") == 1 and "star" in r[2]["text"] and "darker or duller" in r[2]["text"], r[2])
        edit_recipe(page, 103)
        open_panel(page)
        r = rows(page)
        check("flat blues: the verdict is 'Nearly. One thing to look at.'", verdict(page) == "Nearly. One thing to look at.", verdict(page))
        check("flat blues: light and dark says Look at this and suggests a darker shade or lighter highlight",
              r[1]["tag"] == "Look at this" and "same lightness" in r[1]["text"] and "darker shade or a lighter highlight" in r[1]["text"], r[1])
        check("flat blues: one strong blue is already the star", r[0]["tag"] == "Fine" and r[2]["text"].startswith("Blue is your only strong colour, so it is already the star."), r)
        edit_recipe(page, 104)
        open_panel(page)
        r = rows(page)
        check("both problems: the verdict is 'Not quite yet. Two things to look at.'", verdict(page) == "Not quite yet. Two things to look at.", verdict(page))
        check("both problems: both rows say Look at this, and a focus colour is still suggested",
              r[0]["tag"] == "Look at this" and r[1]["tag"] == "Look at this" and r[2]["tag"] == "Suggestion", r)
        shot(page, "v29-check-both-dark-390.png")
        text_all = []
        for rid in (101, 102, 103, 104):
            edit_recipe(page, rid)
            open_panel(page)
            text_all.append(result_text(page))
        check("every answer says plainly that it is only a guide", all("Colours on a screen are only a guide" in t for t in text_all), text_all)   # v59: the guide line is shorter and shared with the Compendium copy text
        check("no answer names a paint or recipe, or leaves a placeholder",
              not any(re.search(r"Macragge|Troll Slayer|Forest Green|Deep Purple|Mid Blue|Burnt|Violet|Scarlet|Ink Sky|Eshin|Good scheme|Too many colours|Flat blues|Both problems|undefined|NaN|\{|\}", t) for t in text_all), text_all)
        check("every row is short: under 190 characters, one or two sentences",
              all(len(x["text"]) < 190 and 1 <= len(sentences(x["text"])) <= 3 for rid in (101, 102, 103, 104) for x in (edit_recipe(page, rid) or open_panel(page) or rows(page))))
        # ...and the wording function on its own for the extra cases
        words = page.evaluate("""() => ({
            calm: schemeCheckWords(MinifolioColour.schemeCheck([{ colour: '#462f30', uses: 2 }, { colour: '#9e915c', uses: 1 }, { colour: '#0b0b0b', uses: 1 }])),
            three: schemeCheckWords(MinifolioColour.schemeCheck([{ colour: '#0d407f', uses: 3 }, { colour: '#f4741c', uses: 2 }, { colour: '#228b22', uses: 2 }, { colour: '#0b0b0b', uses: 1 }])) })""")
        check("calm colours: 'None. Your colours are calm and muted' and a focus hint with no colour named",
              words["calm"]["rows"][0]["text"].startswith("None. Your colours are calm and muted") and words["calm"]["rows"][2]["text"].startswith("Your colours are all calm.") and words["calm"]["verdict"].startswith("Yes"), words["calm"])
        check("exactly three strong colours reads as a good number, not a warning", words["three"]["rows"][0]["tag"] == "Fine" and words["three"]["verdict"].startswith("Yes"), words["three"])

        # ---------- 6. Live updates, unset colours ----------
        print("\n--- 6. It updates as the recipe changes ---")
        load(page)
        open_editor(page)
        set_step_paint(page, 0, "Macragge Blue")
        open_panel(page)
        press_check(page)
        check("one paint: asks for a second colour", "Needs two paints" in result_text(page))
        add_step(page)
        set_step_paint(page, 1, "Troll Slayer Orange")
        page.wait_for_timeout(250)
        check("adding an orange step updates the answer without reopening anything (two colours now: strong colours row appears)",
              page.locator("#scheme-result .scheme-list li").count() == 3 and "2 (dark blue and orange)" in rows(page)[0]["text"], result_text(page))
        add_step(page)
        set_step_paint(page, 2, "Mystery Paint That Has No Colour")
        page.wait_for_timeout(250)
        check("a paint with no colour set is left out and the answer says so",
              "1 paint has no colour set, so it was left out." in result_text(page) and "2 (dark blue and orange)" in rows(page)[0]["text"], result_text(page))
        add_step(page)
        set_step_paint(page, 3, "Another Unknown Paint")
        page.wait_for_timeout(250)
        check("two paints with no colour: 'paints have' and 'they were'", "2 paints have no colour set, so they were left out." in result_text(page), result_text(page))

        # ---------- 7. Whole model still works as before ----------
        print("\n--- 7. Whole model ---")
        whole = rec(201, "Prime and base", "Whole model", [1, 1])
        eyes = rec(202, "Eyes recipe", "Armour", [2, 8])
        load(page, recipes=[whole, eyes])
        edit_recipe(page, 202)
        open_panel(page)
        press_check(page)
        check("the base is still the Whole model recipe's colour: 'Using the main colour of ...' is shown",
              page.evaluate("() => (document.getElementById('colour-ideas-using') || {}).textContent || ''").startswith("Using the main colour of"))
        got = ideas(page)
        check("glow ideas follow the Whole model's dark blue (opposite of dark blue, eyes wording)", got and "opposite of dark blue" in got[0]["why"] and "so eyes in it stand out the most" in got[0]["why"], got)
        r = rows(page)
        check("the check looks at the recipe being edited (orange and pale blue), not the Whole model's blue: one strong colour, orange",
              r and r[0]["text"].startswith("1 (orange)") and r[2]["text"].startswith("Orange is your only strong colour"), r)
        check("the Start from list still starts with Whole model", page.evaluate("() => document.querySelector('#colour-ideas-base option').textContent").startswith("Whole model: Prime and base"))

        # ---------- 8. Hostile text ----------
        print("\n--- 8. Hostile text (text-injection test) ---")
        hostile_paints = [
            {"id": 40, "brand": HOSTILE_BRAND, "name": HOSTILE, "colour": "#0d407f", "status": "owned"},
            {"id": 41, "brand": HOSTILE_BRAND, "name": HOSTILE + " 2", "colour": "#f4741c", "status": "owned"},
            {"id": 42, "brand": "Vallejo", "name": "Plain Grey", "colour": "#4a4d52", "status": "owned"},
        ]
        bad_whole = rec(301, HOSTILE, "Whole model", [40, 40])
        bad_recipe = rec(302, HOSTILE + " recipe", "Armour", [40, 41, 42])
        load(page, paints=hostile_paints, recipes=[bad_whole, bad_recipe])
        page.evaluate("() => { window.__pwned = 0; }")
        edit_recipe(page, 302)
        open_panel(page)
        press_check(page)
        for key in keys:
            pick_role(page, key)
        page.wait_for_timeout(300)
        body_text = page.inner_text("#colour-ideas .ideas-body")
        check("nothing was injected: no pop-ups, no script ran, and no <img> or <script> was made in the card",
              not dialogs and page.evaluate("() => window.__pwned") == 0 and page.locator("#colour-ideas img").count() == 0 and page.locator("#colour-ideas script").count() == 0,
              (dialogs, page.evaluate("() => window.__pwned")))
        check("the tips and the check show none of the hostile words and no angle brackets",
              "Evil" not in page.inner_text("#colour-ideas-tip") and "<" not in page.inner_text("#colour-ideas-tip")
              and "Evil" not in result_text(page) and "<" not in result_text(page) and "onerror" not in result_text(page), result_text(page))
        check("the check still gave a real answer (a verdict and three rows)", verdict(page) != "" and page.locator("#scheme-result .scheme-list li").count() == 3, result_text(page))
        check("the card's own text (tip, check) is the same with hostile paints as with plain ones: no extra elements",
              page.locator("#scheme-result *").evaluate_all("els => els.map(e => e.tagName).filter(t => !['DIV','P','UL','LI','SPAN','STRONG'].includes(t))") == [])

        # ---------- 9. Offline ----------
        print("\n--- 9. Offline ---")
        load(page, recipes=ALL_RECIPES)
        edit_recipe(page, 102)
        open_panel(page)
        page.wait_for_timeout(300)
        page.on("request", lambda rq: requests.append(rq.url))
        ctx.set_offline(True)
        for key in keys:
            pick_role(page, key)
        press_check(page)
        offline_ok = page.locator("#scheme-result .scheme-list li").count() == 3 and verdict(page) == "Nearly. One thing to look at."
        press_check(page)
        press_check(page)
        ctx.set_offline(False)
        check("with the network switched off, tips and the check still work", offline_ok)
        check("changing roles and pressing the check made no network requests at all", requests == [], requests)

        # ---------- 10. An older colour.js without schemeCheck ----------
        print("\n--- 10. colour.js without schemeCheck ---")
        ctx2 = browser.new_context(viewport={"width": 390, "height": 844}, service_workers="block")
        page2 = ctx2.new_page()
        errors2 = []
        page2.on("pageerror", lambda e: errors2.append(str(e)))
        old = colour.replace("isStrongColour, schemeCheck,", "isStrongColour,")
        page2.route("**/colour.js*", lambda route: route.fulfill(status=200, content_type="application/javascript", body=old))
        load(page2)
        open_editor(page2)
        set_step_paint(page2, 0, "Macragge Blue")
        open_panel(page2)
        check("without schemeCheck the card, the tip and three ideas are there; only the check is missing; no errors",
              page2.evaluate("typeof MinifolioColour.schemeCheck") == "undefined" and page2.locator("#colour-ideas-tip").count() == 1
              and page2.locator("#colour-ideas button.idea").count() == 3 and page2.locator("#scheme-check").count() == 0 and not errors2, errors2)
        ctx2.close()

        # ---------- 11. Phone sizes, dark and light ----------
        print("\n--- 11. Dark and light at 390 and 360 px ---")
        for appearance in ["dark", "light"]:
            for width in [390, 360]:
                page.set_viewport_size({"width": width, "height": 844})
                for case, rid in [("both", 104), ("good", 101)]:
                    tag = f"{appearance} {width}px {case}"
                    load(page, recipes=ALL_RECIPES, settings={"appearance": appearance})
                    edit_recipe(page, rid)
                    open_panel(page)
                    press_check(page)
                    page.locator("#scheme-check").scroll_into_view_if_needed()
                    page.wait_for_timeout(200)
                    geo = page.evaluate("""() => { const c = document.getElementById('colour-ideas').getBoundingClientRect();
                        const inside = (el) => { const r = el.getBoundingClientRect(); return r.left >= c.left - 0.5 && r.right <= c.right + 0.5; };
                        const btn = document.getElementById('scheme-check-toggle');
                        const parts = ['#colour-ideas-tip', '#scheme-check', '#scheme-result', '.scheme-verdict', '.scheme-list'].map(s => document.querySelector(s));
                        const whats = [...document.querySelectorAll('.scheme-what')];
                        return { cl: c.left, cr: c.right, w: window.innerWidth, btnH: btn.getBoundingClientRect().height, btnInside: inside(btn),
                                 partsInside: parts.every(inside), whatsInside: whats.every(inside), rowCount: whats.length }; }""")
                    check(f"{tag}: the card is inside the screen and the tip, check, rows and button are inside the card",
                          geo["cl"] >= 0 and geo["cr"] <= geo["w"] + 0.5 and geo["partsInside"] and geo["whatsInside"] and geo["btnInside"], geo)
                    check(f"{tag}: the check button is at least 44 px tall and there are three rows", geo["btnH"] >= 44 and geo["rowCount"] == 3, geo)
                    check(f"{tag}: no sideways scroll", no_sideways(page))
                    col = page.evaluate("""() => { const bg = (el) => { let e = el; while (e) { const v = getComputedStyle(e).backgroundColor;
                            const m = v.match(/rgba\\(.*,\\s*([\\d.]+)\\)/);
                            if (v && v !== 'transparent' && !(m && parseFloat(m[1]) < 0.9)) return v; e = e.parentElement; } return 'rgb(0,0,0)'; };
                        const out = {};
                        const pairs = [['tip', '#colour-ideas-tip'], ['tip label', '#colour-ideas-tip strong'], ['title', '.scheme-title'], ['button', '#scheme-check-toggle'],
                                       ['verdict', '.scheme-verdict'], ['what', '.scheme-what'], ['guide', '#scheme-result .hint']];
                        for (const [k, s] of pairs) { const el = document.querySelector(s); if (el) out[k] = [getComputedStyle(el).color, bg(el)]; }
                        [...document.querySelectorAll('#scheme-result .idea-tag')].forEach((el, i) => { out['pill ' + i + ' ' + el.className] = [getComputedStyle(el).color, bg(el)]; });
                        return out; }""")
                    bad = {k: round(contrast(rgb(v[0]), rgb(v[1])), 2) for k, v in col.items() if contrast(rgb(v[0]), rgb(v[1])) < 4.5}
                    check(f"{tag}: tip, title, button, verdict, rows, pills and the guide line all have contrast of at least 4.5", not bad and len(col) >= 9, (bad, list(col)))
                    shot(page, f"v29-check-{case}-{appearance}-{width}.png")
        page.set_viewport_size({"width": 390, "height": 844})

        # ---------- 12. Nothing else changed ----------
        print("\n--- 12. Nothing else changed ---")
        load(page)
        open_editor(page)
        n = page.locator(".step-edit").count()
        add_step(page)
        set_step_paint(page, 0, "Brand New Paint X")
        page.wait_for_timeout(150)
        check("the Colour ideas card starts closed", page.evaluate("() => document.getElementById('colour-ideas').open") is False)
        add_step(page)
        set_step_paint(page, 1, "Macragge Blue")
        open_panel(page)
        check("the Colour ideas card is still labelled Pro preview and still ends with the v28 footnote",
              page.inner_text("#colour-ideas .pro-pill") == "Pro preview" and "Colours on screen are a guide" in page.inner_text("#colour-ideas .ideas-body"), page.inner_text("#colour-ideas .ideas-body"))
        page.click("#recipe-page button.plain-button:has-text('Cancel')")
        page.wait_for_timeout(250)
        if page.is_visible("#dialog-yes"):
            page.click("#dialog-yes")
            page.wait_for_timeout(250)
        check("no real browser pop-ups appeared", not dialogs, dialogs)
        check("no page errors", not errors, errors[:3])
        browser.close()

    print(f"\n{sum(results)} of {len(results)} checks passed")
    sys.exit(0 if all(results) else 1)

if __name__ == "__main__":
    main()
