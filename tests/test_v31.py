"""v31 tests for Minifolio (Libraries, Lib 1): "More starter schemes" in the Colour ideas card (Pro preview).

What changed: the starter schemes moved out of app.js into their own file (schemes.js, wired into index.html and sw.js),
grew from 6 to 24 generic schemes in four moods (cold, warm, dark, bright, six each), and a row of mood buttons
(All, Cold, Warm, Dark, Bright) sits above the scheme buttons so the list stays short on a phone. All is the default.
Picking a scheme, its summary and reason, the four colour rows, nearest paint (yours first), the ownership tags and
tap-to-add-a-step all behave exactly as in v30 (tests/test_v30.py still checks that).

Checks:
1. Versions, the v31 Updates entry, wiring (schemes.js loads between colour.js and app.js, is saved for offline use),
   CSP and data unchanged, no network or storage code, the scheme data is no longer in app.js.
2. The data: 24 schemes, six per mood, the original six unchanged, four colours each, valid colours, short plain text.
3. The text scan: no Games Workshop game, faction, scheme, paint or product names in any new text (data, mood names, hint,
   Updates entry, and everything shown on screen for every scheme).
4. Mood buttons: where they sit, All is the default, each mood shows its six, All brings back all 24, focus stays put,
   the choice is kept across roles, a picked scheme outside the chosen mood is put away, one inside it is kept.
5. Every scheme behaves like v30: summary, reason, four rows, part and colour word, different paints, honest tags,
   and tapping a paint adds a step with the right note.
6. Honesty on the new schemes: an owned exact paint says You own this, a wishlist paint never does, an empty palette says
   Not in your palette.
7. Hostile text (text-injection test): paint, brand and faction names full of HTML never become markup in the new parts.
8. Offline: no network requests while using the mood buttons and schemes, and it works with the network off.
9. Dark and light at 390 and 360 px: inside the screen, mood buttons wrap, the filtered list is shorter, contrast 4.5.
10. Nothing else changed: faction history, the three ideas, Add step, Cancel, no pop-ups, no page errors.
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


# The six schemes exactly as they were in v30 (they must not change, apart from gaining a mood).
ORIGINAL_SIX = json.loads(r'''[{"key": "blue-gold", "name": "Cold blue and gold", "summary": "Cold blue armour, gold trim, red eyes", "reason": "Blue and gold is a classic pair. One small bright red spot makes the eyes the first thing people see.", "colours": [{"part": "Armour", "look": "a deep blue", "hex": "#1f4287"}, {"part": "Armour highlight", "look": "a lighter blue", "hex": "#6d93d6"}, {"part": "Trim", "look": "gold", "hex": "#c8a02a"}, {"part": "Eyes", "look": "a bright red", "hex": "#d62b2b"}]}, {"key": "green-bone", "name": "Dark green and bone", "summary": "Dark green armour, bone trim, orange glow", "reason": "Dark green is calm and pale bone lifts the edges. Orange glows against green because it sits on the other side of the colour wheel.", "colours": [{"part": "Armour", "look": "a dark green", "hex": "#2e5d3b"}, {"part": "Armour highlight", "look": "a lighter green", "hex": "#5f9a62"}, {"part": "Trim", "look": "a pale bone colour", "hex": "#d9cfb0"}, {"part": "Glow", "look": "a bright orange", "hex": "#ee7d1b"}]}, {"key": "red-grey", "name": "Deep red and dark grey", "summary": "Deep red armour, dark grey cloth, pale gold trim", "reason": "Dark red and dark grey feel serious and tidy. Pale gold gives clean, bright edges.", "colours": [{"part": "Armour", "look": "a deep red", "hex": "#8c1d22"}, {"part": "Armour highlight", "look": "a brighter red", "hex": "#c2383a"}, {"part": "Cloth", "look": "a dark grey", "hex": "#3b3d44"}, {"part": "Trim", "look": "a pale gold", "hex": "#d8bc62"}]}, {"key": "grey-cyan", "name": "Pale grey and cyan", "summary": "Pale grey armour, dark blue trim, cyan glow", "reason": "A light armour makes dark trim easy to read. Cyan glow stands out on cool colours.", "colours": [{"part": "Armour", "look": "a pale grey", "hex": "#b9bdc4"}, {"part": "Trim", "look": "a dark blue", "hex": "#22365c"}, {"part": "Cloth", "look": "a mid grey", "hex": "#6b7078"}, {"part": "Glow", "look": "a bright cyan", "hex": "#3ed3e6"}]}, {"key": "sand-teal", "name": "Sand and teal", "summary": "Sandy armour, brown cloth, teal gems", "reason": "Earth tones are calm and sit well together. Teal is the opposite of warm brown, so small gems in it stand out.", "colours": [{"part": "Armour", "look": "a sandy tan", "hex": "#c4aa78"}, {"part": "Cloth", "look": "a brown", "hex": "#5c4330"}, {"part": "Gems", "look": "a teal", "hex": "#1f9e9a"}, {"part": "Base", "look": "a dark earth brown", "hex": "#3a2f26"}]}, {"key": "dark-bright", "name": "Dark with one bright colour", "summary": "Near-black armour, pale trim, one bright purple", "reason": "Strong light and dark makes the shapes easy to read. One bright colour keeps the eye in one place.", "colours": [{"part": "Armour", "look": "a near-black", "hex": "#1d1e23"}, {"part": "Cloth", "look": "a mid grey", "hex": "#5a5c63"}, {"part": "Trim", "look": "an off-white", "hex": "#e6e3da"}, {"part": "Bright spot", "look": "a bright purple", "hex": "#8a3fd1"}]}]''')

# Words that must never appear in any new text. Games Workshop's games, factions, products and well-known paint and scheme
# names. (The paint tests above use made-up factions; real paint brands are only ever in the user's own palette.)
GW_MORE = re.compile(r"\b(primaris|aeldari|skaven|nurgle|khorne|slaanesh|tzeentch|cadian|ultramar|adepta|sororitas|stormcast|space wolves|"
                     r"grey knights|imperial|hive fleet|waaagh|tau|t'au|kroot|gretchin|dreadnought|bolter|primarch|legion|crusade|"
                     r"macragge|mephiston|abaddon|retributor|leadbelcher|caliban|averland|zandri|rhinox|khemri|nuln|kantor|"
                     r"fists|wolves|ravens|salamanders|iron hands|white scars|imperial fists|raven guard|night lords|word bearers|"
                     r"death guard|thousand sons|world eaters|emperor.?s children|alpha legion|iron warriors|black legion|"
                     r"custodes|mechanicus|skitarii|harlequin|drukhari|ynnari|genestealer|hormagaunt|termagant|carnifex|"
                     r"gloomhaven|lord of the rings|middle.?earth|old world|kill team|necromunda|blood bowl|warcry|"
                     r"games workshop|citadel|warhammer)\b", re.I)

def nodes_text(page):
    """Everything the starter part of the card shows right now."""
    return page.evaluate("() => (document.getElementById('starter-schemes') || {}).innerText || ''")

def mood_chips(page):
    return page.evaluate("() => [...document.querySelectorAll('#starter-moods .chip')].map(c => [c.textContent, c.getAttribute('aria-pressed'), c.dataset.mood])")

def scheme_chips(page):
    return page.evaluate("() => [...document.querySelectorAll('#starter-chips .chip')].map(c => [c.textContent, c.getAttribute('aria-pressed'), c.dataset.scheme])")

def pick_mood(page, key):
    page.click(f'#starter-moods [data-mood="{key}"]')
    page.wait_for_timeout(150)

def focused(page):
    return page.evaluate("() => document.activeElement && (document.activeElement.dataset.mood || document.activeElement.dataset.scheme || document.activeElement.id) || ''")

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
        html, app, sw, colour, sch = read("index.html"), read("app.js"), read("sw.js"), read("colour.js"), read("schemes.js")
        m = re.search(r'const VERSION = "([^"]+)"', sw)
        tags = re.findall(r'<script src="(early|colour|schemes|detail-recipes|app)\.js\?v=([\d.]+)"></script>', html)
        tags = [t for t in tags if t[0] != "detail-recipes"]   # v32 adds detail-recipes.js between schemes.js and app.js (tests/test_v32.py checks it)
        entry = page.evaluate("CHANGELOG.find(r => r.version === 'v31')")
        if page.evaluate("['v31'].every(v => CHANGELOG.some(r => r.version === v))"):
            check("the Updates entry says Pro preview, 24 schemes, the four moods and that nothing leaves the phone",
                  entry and "Pro preview" in entry["changes"][0] and "24" in entry["changes"][0] and all(w in entry["changes"][0] for w in ["cold", "warm", "dark", "bright"])
                  and "sends nothing anywhere" in entry["changes"][1] and "offline" in entry["changes"][1], entry)
        else:
            print("SKIP (entry no longer in the public Updates list): " + 'the Updates entry says Pro preview, 24 schemes, the four moods and that nothing leaves the')
        policy = re.search(r'http-equiv="Content-Security-Policy"\s+content="([^"]+)"', html)
        policy = policy.group(1) if policy else ""
        check("schemes.js is plain data: no network code, no storage, no page code, no HTML, no function calls",
              not re.search(r"\bfetch\s*\(|XMLHttpRequest|sendBeacon|WebSocket|localStorage|sessionStorage|\beval\s*\(|new Function|innerHTML|insertAdjacentHTML|document\.|window\.|import\s*\(", sch), re.findall(r"[a-zA-Z.]+\(", sch)[:5])
        check("schemes.js adds exactly two names to the page (STARTER_MOODS and STARTER_SCHEMES)",
              re.findall(r"^(?:const|let|var|function)\s+(\w+)", sch, re.M) == ["STARTER_MOODS", "STARTER_SCHEMES"], re.findall(r"^(?:const|let|var|function)\s+(\w+)", sch, re.M))
        check("the Pro preview label is still there", "Pro preview" in app and page.evaluate("() => typeof STARTER_SCHEMES") == "object")
        panel_code = app[app.index("v28: \"COLOUR IDEAS\""):app.index('v18c: TIDY BRANDS')]
        check("the panel code still has no network code, no storage, only textContent for new text, and still exactly one innerHTML (the panel's own clear)",
              not re.search(r"\bfetch\s*\(|XMLHttpRequest|sendBeacon|WebSocket|localStorage|sessionStorage|\beval\s*\(|new Function|insertAdjacentHTML|outerHTML", panel_code)
              and panel_code.count("innerHTML") == 1 and 'body.innerHTML = ""' in panel_code, [m.group(0) for m in re.finditer(r"innerHTML[^\n]*", panel_code)])
        check("colour.js was not touched by this chunk", "schemeCheck" in colour and "root.MinifolioColour = api;" in colour and len(re.findall(r"root\.[A-Za-z]+ =", colour)) == 1)

        # ---------- 2. The data ----------
        print("\n--- 2. The scheme data ---")
        schemes = page.evaluate("STARTER_SCHEMES")
        moods = page.evaluate("STARTER_MOODS")
        check("there are exactly 24 schemes", len(schemes) == 24, len(schemes))
        check("four moods, in order: cold, warm, dark, bright, each with a plain name", [m["key"] for m in moods] == ["cold", "warm", "dark", "bright"]
              and [m["name"] for m in moods] == ["Cold", "Warm", "Dark", "Bright"], moods)
        counts = {m["key"]: len([s for s in schemes if s["mood"] == m["key"]]) for m in moods}
        check("six schemes in each mood, and every scheme is in one of them", all(v == 6 for v in counts.values()) and sum(counts.values()) == 24, counts)
        check("keys, names and summaries are all different", len({s["key"] for s in schemes}) == 24 and len({s["name"] for s in schemes}) == 24
              and len({s["summary"] for s in schemes}) == 24)
        by_key = {s["key"]: s for s in schemes}
        same = all(k["key"] in by_key and all(by_key[k["key"]][f] == k[f] for f in ["name", "summary", "reason", "colours"]) for k in ORIGINAL_SIX)
        check("the original six are kept exactly as they were in v30 (key, name, summary, reason and all four colours)", same and len(ORIGINAL_SIX) == 6)
        check("the original six come first, as before", [s["key"] for s in schemes if s["key"] in {k["key"] for k in ORIGINAL_SIX}] != [] and
              all(s["mood"] in {m["key"] for m in moods} for s in schemes))
        check("every scheme has exactly four colours, each with a part, a plain colour word and a valid #rrggbb colour",
              all(len(s["colours"]) == 4 and all(c["part"].strip() and c["look"].strip() and re.fullmatch(r"#[0-9a-f]{6}", c["hex"]) for c in s["colours"]) for s in schemes))
        check("the four colours of a scheme are four different colours and four different parts",
              all(len({c["hex"] for c in s["colours"]}) == 4 and len({c["part"] for c in s["colours"]}) == 4 for s in schemes))
        check("each summary is one short line (no line breaks, 70 characters or fewer)", all("\n" not in s["summary"] and 0 < len(s["summary"]) <= 70 for s in schemes),
              [s["summary"] for s in schemes if len(s["summary"]) > 70])
        check("each reason is one or two sentences and not long (200 characters or fewer)", all(1 <= len(sentences(s["reason"])) <= 2 and len(s["reason"]) <= 200 for s in schemes),
              [(s["key"], len(sentences(s["reason"])), len(s["reason"])) for s in schemes if not (1 <= len(sentences(s["reason"])) <= 2 and len(s["reason"]) <= 200)])
        check("names describe colours only: short, no digits, no brackets", all(re.fullmatch(r"[A-Za-z' -]{5,40}", s["name"]) for s in schemes), [s["name"] for s in schemes if not re.fullmatch(r"[A-Za-z' -]{5,40}", s["name"])])
        check("no angle brackets, ampersands or backticks anywhere in the data (plain text only)", not re.search(r"[<>&`]", json.dumps(schemes) + json.dumps(moods)))

        # ---------- 3. The text scan ----------
        print("\n--- 3. Text scan: no Games Workshop names in any new text ---")
        load(page, recipes=RECIPES, units=UNITS)
        edit_recipe(page, 106)
        open_panel(page)
        all_text = json.dumps(schemes) + json.dumps(moods) + json.dumps(entry) + page.evaluate("() => document.getElementById('starter-schemes').innerText")
        hits = GW_WORDS.findall(all_text) + GW_MORE.findall(all_text)
        check("the scheme data, mood names, Updates entry and starter heading and hint name no Games Workshop game, faction, scheme, paint or product", not hits, hits)
        shown = []
        ours = """() => [...document.querySelectorAll('#starter-schemes > .scheme-title, #starter-schemes > .hint, #starter-schemes .chip, #starter-summary, #starter-reason, #starter-list .idea-why, #starter-list .idea-tag, #starter-list .idea-note, #starter-list .idea-add')].map(e => e.textContent).join('\\n')"""
        for mood in ["all", "cold", "warm", "dark", "bright"]:
            pick_mood(page, mood)
            shown.append(page.evaluate(ours))
            for s in [x for x in schemes if mood in ("all", x["mood"])]:
                pick_scheme(page, s["key"])
                shown.append(page.evaluate(ours))
                pick_scheme(page, s["key"])
        pick_mood(page, "all")
        screen_hits = GW_WORDS.findall("\n".join(shown)) + GW_MORE.findall("\n".join(shown))
        check("everything we wrote that the starter part shows on screen (heading, hint, mood and scheme buttons, summary, reason, row lines, tags, notes), for every mood and every scheme, names no Games Workshop game, faction, scheme or product",
              not screen_hits and len(shown) > 24, screen_hits[:10])
        own_text = " ".join(" ".join([s["name"], s["summary"], s["reason"]] + [c["part"] + " " + c["look"] for c in s["colours"]]) for s in schemes) + " ".join(m["name"] for m in moods)
        check("not even the word Citadel appears in any text we wrote for the schemes", "citadel" not in own_text.lower() and "games workshop" not in own_text.lower())
        check("every word in the new schemes is plain English (letters, spaces, apostrophes, hyphens, commas, full stops only)",
              all(re.fullmatch(r"[A-Za-z0-9 ',.\-]+", t) for s in schemes for t in [s["name"], s["summary"], s["reason"]] + [c["part"] + " " + c["look"] for c in s["colours"]]))

        # ---------- 4. Mood buttons ----------
        print("\n--- 4. Mood buttons ---")
        load(page, recipes=RECIPES, units=UNITS)
        edit_recipe(page, 106)
        open_panel(page)
        mc = mood_chips(page)
        check("five mood buttons: All, Cold, Warm, Dark, Bright, with All pressed to start", [c[0] for c in mc] == ["All", "Cold", "Warm", "Dark", "Bright"]
              and [c[1] for c in mc] == ["true", "false", "false", "false", "false"], mc)
        check("the mood buttons are in a labelled group", page.get_attribute("#starter-moods", "role") == "group" and "mood" in (page.get_attribute("#starter-moods", "aria-label") or "").lower())
        order = page.evaluate("""() => { const m = document.getElementById('starter-moods'), c = document.getElementById('starter-chips'), t = document.querySelector('#starter-schemes .scheme-title');
            const kids = [...document.getElementById('starter-schemes').children]; return [kids.indexOf(t), kids.indexOf(m), kids.indexOf(c)]; }""")
        check("the mood buttons sit above the scheme buttons, below the heading", order[0] < order[1] < order[2] and -1 not in order, order)
        sc = scheme_chips(page)
        check("all 24 scheme buttons show to start, none picked", len(sc) == 24 and all(c[1] == "false" for c in sc) and [c[2] for c in sc] == [s["key"] for s in schemes], len(sc))
        for mood in ["cold", "warm", "dark", "bright"]:
            pick_mood(page, mood)
            sc = scheme_chips(page)
            mc = mood_chips(page)
            expect = [s["key"] for s in schemes if s["mood"] == mood]
            check(f"{mood}: only that mood's six schemes show, in order, and only the {mood} button is pressed",
                  [c[2] for c in sc] == expect and len(sc) == 6 and [c[2] for c in mc if c[1] == "true"] == [mood], (len(sc), mc))
            check(f"{mood}: the button keeps the focus after it is tapped", focused(page) == mood, focused(page))
        pick_mood(page, "all")
        check("All brings back all 24 and is the only one pressed", len(scheme_chips(page)) == 24 and [c[2] for c in mood_chips(page) if c[1] == "true"] == ["all"])
        check("focus is on the All button", focused(page) == "all", focused(page))
        pick_mood(page, "cold")
        pick_mood(page, "cold")
        check("tapping the pressed mood again leaves it as it is (use All to see everything)", len(scheme_chips(page)) == 6 and [c[2] for c in mood_chips(page) if c[1] == "true"] == ["cold"])
        pick_role(page, "trim")
        check("changing the role keeps the mood", len(scheme_chips(page)) == 6 and [c[2] for c in mood_chips(page) if c[1] == "true"] == ["cold"])
        pick_scheme(page, "teal-silver")
        check("a scheme in the chosen mood can be picked: summary, reason and four rows show",
              page.inner_text("#starter-summary") == by_key["teal-silver"]["summary"] and page.inner_text("#starter-reason") == by_key["teal-silver"]["reason"] and len(starter_rows(page)) == 4)
        pick_mood(page, "cold")
        check("tapping the same mood leaves the pick alone", page.locator("#starter-list").count() == 1)
        pick_mood(page, "all")
        check("switching to All keeps the pick (it is inside All)", page.locator("#starter-list").count() == 1 and page.get_attribute('#starter-schemes [data-scheme="teal-silver"]', "aria-pressed") == "true")
        pick_mood(page, "warm")
        check("switching to a mood that does not contain the pick puts it away (no rows, no summary, nothing pressed)",
              page.locator("#starter-list").count() == 0 and page.locator("#starter-summary").count() == 0 and all(c[1] == "false" for c in scheme_chips(page)))
        pick_mood(page, "all")
        check("and it stays put away when coming back to All", page.locator("#starter-list").count() == 0)
        pick_scheme(page, "black-red")
        pick_mood(page, "dark")
        check("switching to the mood that contains the pick keeps it", page.locator("#starter-list").count() == 1 and page.inner_text("#starter-summary") == by_key["black-red"]["summary"])
        pick_scheme(page, "black-red")
        check("tapping the picked scheme again closes it, with the mood kept", page.locator("#starter-list").count() == 0 and len(scheme_chips(page)) == 6)
        blur(page)
        page.click('nav button[data-tab="recipes"]')
        page.wait_for_timeout(150)
        check("the mood and the pick are kept while the app stays open, like the other choices (here: after leaving and coming back)",
              page.evaluate("() => colourIdeasState.mood") == "dark")
        check("an unknown mood value falls back to All (nothing breaks)", page.evaluate("""() => { colourIdeasState.mood = 'nonsense'; return starterSchemesShown().length; }""") == 24)
        page.evaluate("() => { colourIdeasState.mood = ''; colourIdeasState.scheme = ''; }")

        # ---------- 5. Every scheme behaves like v30 ----------
        print("\n--- 5. Every scheme: summary, reason, four rows, notes, tap to add ---")
        load(page, recipes=RECIPES, units=UNITS)
        edit_recipe(page, 106)
        open_panel(page)
        for s in schemes:
            pick_scheme(page, s["key"])
            r = starter_rows(page)
            ok = (page.inner_text("#starter-summary") == s["summary"] and page.inner_text("#starter-reason") == s["reason"] and len(r) == 4
                  and [x["why"] for x in r] == [f"{c['part']}: {c['look']}." for c in s["colours"]] and len({x["name"] for x in r}) == 4
                  and all(x["tag"] in ("You own this", "Yours, poor fit", "Not in your palette") for x in r))
            check(f"{s['name']} ({s['mood']}): summary, reason, four rows with part and colour word, four different paints, honest tags", ok, (r, page.inner_text("#starter-summary")))
            pick_scheme(page, s["key"])
        n0 = len(draft_steps(page))
        pick_mood(page, "bright")
        pick_scheme(page, "orange-blue")
        names = [x["name"] for x in starter_rows(page)]
        page.locator("#starter-list button.idea-pick").nth(2).click()
        page.wait_for_timeout(250)
        steps = draft_steps(page)
        check("tapping a paint of a new scheme adds one new last step (that paint, 100%, 1 coat) with a plain note naming the scheme and part",
              len(steps) == n0 + 1 and steps[-1]["n"] == names[2] and steps[-1]["mix"] == 100 and steps[-1]["note"] == "Starter scheme (Orange and mid blue): trim", steps[-1])
        check("the scheme stays picked and the card stays open", page.locator("#starter-list button.idea-pick").count() == 4 and page.evaluate("() => document.getElementById('colour-ideas').open"))
        pick_scheme(page, "orange-blue")
        pick_mood(page, "all")

        # ---------- 6. Honesty on the new schemes ----------
        print("\n--- 6. Honesty ---")
        navy = [{"id": 1, "brand": "Test", "name": "Exact Navy", "colour": "#17254d", "status": "owned"},
                {"id": 2, "brand": "Test", "name": "Exact Pale Yellow", "colour": "#efe08a", "status": "wishlist"}]
        load(page, paints=navy, recipes=[], units=[])
        open_editor(page)
        open_panel(page)
        pick_scheme(page, "navy-yellow")
        r = {x["name"]: x["tag"] for x in starter_rows(page)}
        check("an owned paint that is exactly the wanted colour says You own this", r.get("Exact Navy") == "You own this", r)
        check("a wishlist paint that is exactly right never says You own this", r.get("Exact Pale Yellow") != "You own this", r)
        check("every row still has one of the three honest tags", all(v in ("You own this", "Yours, poor fit", "Not in your palette") for v in r.values()) and len(r) == 4, r)
        load(page, paints=[], recipes=[], units=[])
        open_editor(page)
        open_panel(page)
        allnone = True
        for s in schemes:
            pick_scheme(page, s["key"])
            allnone = allnone and len(starter_rows(page)) == 4 and all(x["tag"] == "Not in your palette" for x in starter_rows(page))
            pick_scheme(page, s["key"])
        check("with an empty palette every row of every scheme says Not in your palette (the built-in list is used, nothing is claimed as owned)", allnone)

        # ---------- 7. Hostile text ----------
        print("\n--- 7. Hostile text (text-injection test) ---")
        hostile_paints = [{"id": 90, "brand": HOSTILE_BRAND, "name": HOSTILE, "colour": "#17254d", "status": "owned"},
                          {"id": 91, "brand": "Test", "name": "Plain Red", "colour": "#c8262b", "status": "owned"}]
        hostile_units = [unit(1, HOSTILE + " Troop", HOSTILE + " Faction", [140, 106]), unit(2, "Second", HOSTILE + " Faction", [141])]
        hostile_recipes = [rec(140, HOSTILE + " recipe", "Armour", [90]), rec(141, "Second recipe", "Armour", [90, 91]), rec(106, "Mine", "Eyes", [91])]
        load(page, paints=hostile_paints, recipes=hostile_recipes, units=hostile_units)
        edit_recipe(page, 106)
        open_panel(page)
        for mood in ["cold", "bright", "all"]:
            pick_mood(page, mood)
        pick_scheme(page, "navy-yellow")
        texts = nodes_text(page)
        check("a paint and brand full of HTML show as plain text in the new scheme rows", "<img" in texts and "Evil" in texts
              and page.locator("#starter-schemes img, #starter-schemes script, #starter-schemes b").count() == 0, texts[:200])
        check("nothing ran (no onerror, no script) and the whole card has no injected tags",
              page.evaluate("() => window.__pwned") is None and page.locator("#colour-ideas img, #colour-ideas script, #colour-ideas .ideas-body b").count() == 0)
        page.locator("#starter-list button.idea-pick").first.click()
        page.wait_for_timeout(250)
        steps = draft_steps(page)
        check("the new mood buttons and scheme buttons are built from fixed text (no HTML anywhere in them)",
              page.evaluate("() => [...document.querySelectorAll('#starter-moods .chip, #starter-chips .chip')].every(c => c.children.length === 0)"))
        hostile_state = page.evaluate("""() => { colourIdeasState.mood = '<img src=x onerror="window.__pwned=3">'; colourIdeasState.scheme = '<b>x</b>'; return starterSchemesShown().length; }""")
        check("a hostile saved mood or scheme value is ignored (it falls back to All, nothing is built from it)", hostile_state == 24 and page.evaluate("() => window.__pwned") is None)
        page.evaluate("() => { colourIdeasState.mood = ''; colourIdeasState.scheme = ''; }")

        # ---------- 8. Offline ----------
        print("\n--- 8. Offline ---")
        load(page, recipes=RECIPES, units=UNITS)
        edit_recipe(page, 106)
        open_panel(page)
        requests.clear()
        page.on("request", lambda rq: requests.append(rq.url))
        ctx.set_offline(True)
        for mood in ["cold", "warm", "dark", "bright", "all"]:
            pick_mood(page, mood)
        pick_scheme(page, "plum-lime")
        pick_scheme(page, "olive-amber")
        ok_off = len(starter_rows(page)) == 4 and len(scheme_chips(page)) == 24
        page.locator("#starter-list button.idea-pick").first.click()
        page.wait_for_timeout(250)
        ctx.set_offline(False)
        check("with the network switched off, the mood buttons and the schemes still work", ok_off)
        check("using the mood buttons, picking schemes and tapping paints made no network requests at all", requests == [], requests)
        # If schemes.js could not be loaded at all, the rest of the card must still work.
        ctx3 = browser.new_context(viewport={"width": 390, "height": 844}, service_workers="block")
        page3 = ctx3.new_page()
        errors3 = []
        page3.on("pageerror", lambda e: errors3.append(str(e)))
        page3.route("**/schemes.js*", lambda r: r.abort())
        load(page3, recipes=RECIPES, units=UNITS)
        edit_recipe(page3, 106)
        open_panel(page3)
        check("if schemes.js is missing, the recipe editor and the rest of the Colour ideas card still work and the starter part is simply not there",
              page3.evaluate("() => typeof STARTER_SCHEMES") == "undefined" and page3.locator("#colour-ideas").count() == 1 and page3.locator("#starter-schemes").count() == 0
              and page3.locator("#colour-ideas button.idea").count() == 3 and page3.locator("#faction-history").count() == 1 and page3.locator("#scheme-check").count() == 1 and not errors3, errors3[:2])
        ctx3.close()

        # ---------- 9. Phone sizes, dark and light ----------
        print("\n--- 9. Dark and light at 390 and 360 px ---")
        for appearance in ["dark", "light"]:
            for width in [390, 360]:
                page.set_viewport_size({"width": width, "height": 844})
                tag = f"{appearance} {width}px"
                load(page, recipes=RECIPES, units=UNITS, settings={"appearance": appearance})
                edit_recipe(page, 106)
                open_panel(page)
                page.locator("#starter-schemes").scroll_into_view_if_needed()
                page.wait_for_timeout(150)
                def geometry():
                    return page.evaluate("""() => { const c = document.getElementById('colour-ideas').getBoundingClientRect();
                        const inside = (el) => { const r = el.getBoundingClientRect(); return r.left >= c.left - 0.5 && r.right <= c.right + 0.5; };
                        const mood = [...document.querySelectorAll('#starter-moods .chip')], sch = [...document.querySelectorAll('#starter-chips .chip')];
                        const rows = new Set(sch.map(b => Math.round(b.getBoundingClientRect().top)));
                        const mrows = new Set(mood.map(b => Math.round(b.getBoundingClientRect().top)));
                        const box = document.getElementById('starter-chips').getBoundingClientRect();
                        return { cl: c.left, cr: c.right, w: window.innerWidth, moodInside: mood.every(inside), schInside: sch.every(inside), n: sch.length,
                                 moodMinH: Math.min(...mood.map(b => b.getBoundingClientRect().height)), schRows: rows.size, moodRows: mrows.size, listH: box.height }; }""")
                g_all = geometry()
                shot(page, f"v31-moods-all-{appearance}-{width}.png")
                check(f"{tag}: the card is inside the screen, and every mood and scheme button is inside the card",
                      g_all["cl"] >= 0 and g_all["cr"] <= g_all["w"] + 0.5 and g_all["moodInside"] and g_all["schInside"], g_all)
                check(f"{tag}: the five mood buttons fit on one line and are at least 36 px tall, and the 24 scheme buttons wrap onto several lines",
                      g_all["n"] == 24 and g_all["moodRows"] == 1 and g_all["schRows"] >= 3 and g_all["moodMinH"] >= 36, g_all)
                check(f"{tag}: no sideways scroll", no_sideways(page))
                pick_mood(page, "cold")
                g_cold = geometry()
                shot(page, f"v31-moods-cold-{appearance}-{width}.png")
                check(f"{tag}: choosing a mood keeps six buttons and makes the list clearly shorter (under half the height of All)",
                      g_cold["n"] == 6 and g_cold["listH"] < g_all["listH"] * 0.5 and g_cold["schInside"] and no_sideways(page), (g_cold["listH"], g_all["listH"]))
                pick_scheme(page, "teal-silver")
                page.locator("#starter-list").scroll_into_view_if_needed()
                page.wait_for_timeout(150)
                rowsg = page.evaluate("""() => { const c = document.getElementById('colour-ideas').getBoundingClientRect();
                    const b = [...document.querySelectorAll('#starter-list button.idea-pick')];
                    return { n: b.length, minH: Math.min(...b.map(x => x.getBoundingClientRect().height)),
                             inside: b.every(x => { const r = x.getBoundingClientRect(); return r.left >= c.left - 0.5 && r.right <= c.right + 0.5; }) }; }""")
                shot(page, f"v31-scheme-{appearance}-{width}.png")
                check(f"{tag}: the four rows are each at least 44 px tall and inside the card", rowsg["n"] == 4 and rowsg["minH"] >= 44 and rowsg["inside"], rowsg)
                col = page.evaluate("""() => { const bg = (el) => { let e = el; while (e) { const v = getComputedStyle(e).backgroundColor;
                        const m = v.match(/rgba\\(.*,\\s*([\\d.]+)\\)/);
                        if (v && v !== 'transparent' && !(m && parseFloat(m[1]) < 0.9)) return v; e = e.parentElement; } return 'rgb(0,0,0)'; };
                    const out = {};
                    const pairs = [['mood on', '#starter-moods .chip[aria-pressed="true"]'], ['mood off', '#starter-moods .chip[aria-pressed="false"]'],
                                   ['scheme on', '#starter-chips .chip[aria-pressed="true"]'], ['scheme off', '#starter-chips .chip[aria-pressed="false"]'],
                                   ['starter hint', '#starter-schemes > .hint'], ['summary', '#starter-summary'], ['reason', '#starter-reason'],
                                   ['row name', '#starter-list .idea-name'], ['row why', '#starter-list .idea-why'], ['row add', '#starter-list .idea-add']];
                    for (const [k, s] of pairs) { const el = document.querySelector(s); if (el) out[k] = [getComputedStyle(el).color, bg(el)]; }
                    return out; }""")
                bad = {k: round(contrast(rgb(v[0]), rgb(v[1])), 2) for k, v in col.items() if contrast(rgb(v[0]), rgb(v[1])) < 4.5}
                check(f"{tag}: mood buttons (on and off), scheme buttons, hint, summary, reason and rows all have contrast of at least 4.5", not bad and len(col) >= 10, (bad, list(col)))
                pick_mood(page, "all")
        page.set_viewport_size({"width": 390, "height": 844})

        # ---------- 10. Nothing else changed ----------
        print("\n--- 10. Nothing else changed ---")
        load(page, recipes=RECIPES, units=UNITS)
        edit_recipe(page, 106)
        open_panel(page)
        check("the faction history is still there with its rows", page.locator("#faction-history").count() == 1 and len(hist_rows(page)) >= 1)
        check("the main three ideas are still exactly three 'idea' buttons", page.locator("#colour-ideas button.idea").count() == 3)
        order = page.evaluate("""() => { const ids = ['colour-ideas-tip', 'faction-history', 'starter-schemes', 'scheme-check'];
            const body = document.querySelector('#colour-ideas .ideas-body'); return ids.map(i => [...body.children].indexOf(document.getElementById(i))); }""")
        check("order in the card is unchanged: tip, faction history, starter schemes, then the check", order == sorted(order) and -1 not in order, order)
        check("the card is still labelled Pro preview and still ends with the footnote", page.inner_text("#colour-ideas .pro-pill") == "Pro preview"
              and page.evaluate("() => document.querySelector('#colour-ideas .ideas-body').lastElementChild.textContent.includes('Nothing leaves your phone')"))
        load(page)
        open_editor(page)
        n = page.locator(".step-edit").count()
        add_step(page)
        set_step_paint(page, 0, "Brand New Paint X")
        page.wait_for_timeout(150)
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
