"""v32 tests for Minifolio (Libraries, Lib 2): "Detail recipes" in the Colour ideas card (Pro preview).

What changed: a new data file (detail-recipes.js, loaded between schemes.js and app.js, wired into index.html and sw.js the
same way schemes.js is) holds 18 generic detail recipes (teeth, bone, chitin, skin, blood, rusty, oiled and gold metal, bright
steel, verdigris, chips and weathering, leather, cloth, wood, mud, scorch marks, glowing eyes, gems and lenses). Each is three or
four steps (technique, coats, mix %, short note) and each step names a TARGET COLOUR (a plain colour word and a hex), not a paint.
A "Detail recipes" part sits in the Colour ideas card below Starter schemes, with group buttons (All, Body, Metal, Materials,
Light) and a button per recipe. Picking a recipe lists its steps, each with the nearest paint (yours first, the built-in list
after) and the same honest tags and notes as the starter scheme rows. "Add all steps" adds every step to the recipe being edited
as new last steps (nothing is saved until Save recipe) and tapping one paint adds just that step. Starter schemes and Your
schemes are unchanged (tests/test_v30.py and tests/test_v31.py still check them).

Checks:
1. Versions, the v32 Updates entry, wiring (detail-recipes.js loads between schemes.js and app.js and is saved for offline use),
   CSP and storage names unchanged, no network or storage code in the new file.
2. The data: 18 recipes in four groups, every required subject present, three or four steps each, valid fields, short plain text,
   target colours only (no paint names, no brand names).
3. The text scan: no Games Workshop game, faction, scheme, paint or product names in any new text (data, group names, hint,
   Updates entry, and everything shown on screen for every group and every recipe).
4. Group buttons: where they sit, All is the default, each group shows its recipes, focus stays put, the choice is kept across
   roles, a picked recipe outside the chosen group is put away, one inside it is kept.
5. Every recipe: summary, one row per step with technique, coats, mix % and note, honest tags; the nearest paint is yours first
   (exact owned paints are found for every step of every recipe); a single tap adds one step with everything kept;
   Add all steps adds every step, in order, as new last steps, keeping the steps already there; nothing is saved until Save recipe.
6. Honesty: an owned exact paint says You own this, a wishlist paint never does, an empty palette says Not in your palette,
   a far-off owned paint says Closest you own with its note.
7. Hostile text (text-injection test): paint, brand, faction and recipe names full of HTML never become markup in the new part.
8. Offline: no network requests, works with the network off, and if detail-recipes.js is missing the rest of the card still works.
9. Dark and light at 390 and 360 px: inside the screen, buttons wrap, the filtered list is shorter, the Add all steps button and
   the rows are at least 44 px tall, contrast 4.5.
10. Starter schemes and Your schemes still work exactly as in v31, the order of the card parts, nothing else changed.
Run all tests with `python3 tests/run_all.py`, or serve the repo folder and run this file on its own."""
import json, os, re, sys
from playwright.sync_api import sync_playwright

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from notice_watch import attach_notices
import test_v31 as t   # the helpers (loading the app, opening the editor, colours) and the Games Workshop word lists

SHOTS, ROOT = t.SHOTS, t.ROOT
read, load, blur, open_editor, edit_recipe, open_panel = t.read, t.load, t.blur, t.open_editor, t.edit_recipe, t.open_panel
pick_role, shot, no_sideways, rgb, contrast, sentences = t.pick_role, t.shot, t.no_sideways, t.rgb, t.contrast, t.sentences
RECIPES, UNITS, unit, rec, HOSTILE, HOSTILE_BRAND = t.RECIPES, t.UNITS, t.unit, t.rec, t.HOSTILE, t.HOSTILE_BRAND
GW_WORDS, GW_MORE = t.GW_WORDS, t.GW_MORE
results = []

def check(name, ok, detail=""):
    results.append(bool(ok))
    print(("PASS " if ok else "FAIL ") + name + ("" if ok else f"  -> {detail}"))

REQUIRED = ["teeth", "chitin", "eyes and glow", "rusty metal", "oiled metal", "bone", "leather", "cloth", "gems and lenses", "skin", "wood",
            "blood", "verdigris", "weathering"]
GROUPS = ["body", "metal", "material", "light"]
SHOWN_JS = """() => [...document.querySelectorAll('#detail-recipes > .scheme-title, #detail-recipes > .hint, #detail-recipes .chip, #detail-summary, #detail-add-all, #detail-list .idea-why, #detail-list .idea-tag, #detail-list .idea-note, #detail-list .idea-add')].map(e => e.textContent).join('\\n')"""

def cap(text):
    return text[:1].upper() + text[1:]

def why_line(i, s):
    return f"Step {i}: {s['technique']}, {s['coats']} coat{'' if s['coats'] == 1 else 's'}, {s['mix']}% paint. {cap(s['look'])}. {s['note']}"

def detail_rows(page):
    return page.evaluate("""() => [...document.querySelectorAll('#detail-list button.idea-pick')].map(b => ({
        name: b.querySelector('.idea-name').childNodes[0].textContent, brand: (b.querySelector('.idea-name small') || {}).textContent || '',
        tag: b.querySelector('.idea-tag').textContent, why: b.querySelector('.idea-why').textContent,
        note: (b.querySelector('.idea-note') || {}).textContent || '',
        fit: (b.querySelector('.idea-fit') || {}).textContent || '',   // v64: the fit label, and your own paint's line when it is a poor fit
        also: (b.closest('li').querySelector('.idea-also .idea-tag') || {}).textContent || '' }))""")

def group_chips(page):
    return page.evaluate("() => [...document.querySelectorAll('#detail-groups .chip')].map(c => [c.textContent, c.getAttribute('aria-pressed'), c.dataset.detailGroup])")

def recipe_chips(page):
    return page.evaluate("() => [...document.querySelectorAll('#detail-chips .chip')].map(c => [c.textContent, c.getAttribute('aria-pressed'), c.dataset.detail])")

def pick_group(page, key):
    page.click(f'#detail-groups [data-detail-group="{key}"]')
    page.wait_for_timeout(150)

def pick_recipe(page, key):
    page.click(f'#detail-chips [data-detail="{key}"]')
    page.wait_for_timeout(150)

def full_steps(page):
    return page.evaluate("() => recipeDraft.steps.map(s => ({ technique: s.technique, coats: s.coats, ratio: s.ratio, optional: s.optional, note: s.note, n: s.paints.length, name: s.paints[0].name, brand: s.paints[0].brand, colour: s.paints[0].colour, mix: s.paints[0].mix }))")

def stored_recipes(page):
    return page.evaluate("() => localStorage.getItem('shades-of-grey-recipes')")

def focused(page):
    return page.evaluate("() => document.activeElement && (document.activeElement.dataset.detailGroup || document.activeElement.dataset.detail || document.activeElement.id) || ''")

def detail_text(page):
    return page.evaluate("() => (document.getElementById('detail-recipes') || {}).innerText || ''")

def exact_palette(recipe, n, status="owned", start=300):
    # (the names avoid words like metal or ink, which the app treats as special kinds of paint)
    return [{"id": start + i, "brand": "Test", "name": f"Exact Paint {n}-{i}", "colour": s["hex"], "status": status} for i, s in enumerate(recipe["steps"])]

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
        html, app, sw, colour, det = read("index.html"), read("app.js"), read("sw.js"), read("colour.js"), read("detail-recipes.js")
        version = page.evaluate("APP_VERSION")
        check("APP_VERSION is v32 or later", float(version[1:]) >= 32, version)
        m = re.search(r'const VERSION = "([^"]+)"', sw)
        check("sw.js VERSION matches APP_VERSION", m and m.group(1) == version, m and m.group(1))
        tags = re.findall(r'<script src="([a-z-]+)\.js\?v=([\d.]+)"></script>', html)
        check("index.html loads early.js, colour.js, schemes.js, detail-recipes.js, then app.js (five tags at v32, six at v33 with basing-tips.js after detail-recipes.js), all with ?v= matching the version",
              [x[0] for x in tags if x[0] != "basing-tips"] == ["early", "colour", "schemes", "detail-recipes", "app"] and len(re.findall(r"<script\b", html)) in (5, 6) and all(x[1] == version[1:] for x in tags), tags)
        check("detail-recipes.js is saved for offline use by sw.js, with the same ?v= tag as the other files",
              '"./detail-recipes.js" + CODE_TAG' in sw and len(re.findall(r'"\./[a-z-]+\.js" \+ CODE_TAG', sw)) in (5, 6), re.findall(r'"\./[^"]+"', sw))
        check("the comments naming the version number match", f'The "?v={version[1:]}" makes' in html and f'e.g. "app.js?v={version[1:]}"' in app)
        entry = page.evaluate("CHANGELOG.find(r => r.version === 'v32')")
        if page.evaluate("['v32'].every(v => CHANGELOG.some(r => r.version === v))"):
            check("Updates has a v32 entry with at least two lines", entry and len(entry["changes"]) >= 2, entry)
        else:
            print("SKIP (entry no longer in the public Updates list): " + 'Updates has a v32 entry with at least two lines')
        check("the newest Updates entry is v32 or later", float(page.evaluate("CHANGELOG[0].version")[1:]) >= 32)
        if page.evaluate("['v32'].every(v => CHANGELOG.some(r => r.version === v))"):
            check("the Updates entry says Pro preview, Detail recipes, 18 recipes, Add all steps, Save recipe, and that nothing leaves the phone",
                  entry and "Pro preview" in entry["changes"][0] and "Detail recipes" in entry["changes"][0] and "18" in entry["changes"][0]
                  and "Add all steps" in entry["changes"][1] and "Save recipe" in entry["changes"][1] and "sends nothing anywhere" in entry["changes"][1] and "offline" in entry["changes"][1], entry)
        else:
            print("SKIP (entry no longer in the public Updates list): " + 'the Updates entry says Pro preview, Detail recipes, 18 recipes, Add all steps, Save recipe')
        if page.evaluate("['v30', 'v31'].every(v => CHANGELOG.some(r => r.version === v))"):
            check("the v31 and v30 Updates entries are still there", page.evaluate("!!CHANGELOG.find(r => r.version === 'v31') && !!CHANGELOG.find(r => r.version === 'v30')"))
        else:
            print("SKIP (entry no longer in the public Updates list): " + 'the v31 and v30 Updates entries are still there')
        check("DATA_VERSION is still 1", page.evaluate("DATA_VERSION") == 1)
        check("the three storage names are unchanged",
              all(k in app for k in ['STORAGE_KEY = "mini-tracker-models"', 'SETTINGS_KEY = "shades-of-grey-settings"', 'RECIPES_KEY = "shades-of-grey-recipes"']))
        policy = re.search(r'http-equiv="Content-Security-Policy"\s+content="([^"]+)"', html)
        policy = policy.group(1) if policy else ""
        hosts = set(re.findall(r"https?://[^\s;'\"]+", policy))
        check("the security policy is untouched: the only outside address is still the one GoatCounter picture address",
              len(hosts) == 1 and "goatcounter" in list(hosts)[0] and "connect-src 'none'" in policy.replace('"', "'") or len(hosts) == 1 and "goatcounter" in list(hosts)[0], (hosts, policy[:200]))
        check("detail-recipes.js is only data: it adds exactly two names (DETAIL_GROUPS, DETAIL_RECIPES) and has no network code, no storage, no HTML building, no eval",
              re.findall(r"^(?:const|let|var|function)\s+(\w+)", det, re.M) == ["DETAIL_GROUPS", "DETAIL_RECIPES"]
              and not re.search(r"\bfetch\s*\(|XMLHttpRequest|sendBeacon|WebSocket|localStorage|sessionStorage|indexedDB|\beval\s*\(|new Function|innerHTML|insertAdjacentHTML|outerHTML|document\.|window\.|import\s|require\s*\(", det))
        check("the recipe data is not in app.js (it uses the names from detail-recipes.js)",
              "const DETAIL_RECIPES" not in app and "const DETAIL_GROUPS" not in app and 'key: "verdigris"' not in app and "DETAIL_RECIPES" in app)
        check("the Pro preview label is still there", "Pro preview" in app and page.evaluate("() => typeof DETAIL_RECIPES") == "object")
        panel_code = app[app.index("v28: \"COLOUR IDEAS\""):app.index('v18c: TIDY BRANDS')]
        check("the panel code still has no network code, no storage, only textContent for new text, and still exactly one innerHTML (the panel's own clear)",
              not re.search(r"\bfetch\s*\(|XMLHttpRequest|sendBeacon|WebSocket|localStorage|sessionStorage|\beval\s*\(|new Function|insertAdjacentHTML|outerHTML", panel_code)
              and panel_code.count("innerHTML") == 1 and 'body.innerHTML = ""' in panel_code, [mm.group(0) for mm in re.finditer(r"innerHTML[^\n]*", panel_code)])
        check("colour.js and schemes.js were not touched by this chunk", "schemeCheck" in colour and "root.MinifolioColour = api;" in colour and "STARTER_SCHEMES" in read("schemes.js"))

        # ---------- 2. The data ----------
        print("\n--- 2. The recipe data ---")
        recipes = page.evaluate("DETAIL_RECIPES")
        groups = page.evaluate("DETAIL_GROUPS")
        techniques = page.evaluate("DEFAULT_TECHNIQUES")
        check("there are 15 to 20 recipes (this chunk has 18)", len(recipes) == 18, len(recipes))
        check("four groups, in order: Body, Metal, Materials, Light", [g["key"] for g in groups] == GROUPS and [g["name"] for g in groups] == ["Body", "Metal", "Materials", "Light"], groups)
        counts = {g: len([r for r in recipes if r["group"] == g]) for g in GROUPS}
        check("every recipe is in one of the groups and every group has at least two recipes", sum(counts.values()) == 18 and all(v >= 2 for v in counts.values()), counts)
        names_lower = " | ".join(r["name"].lower() for r in recipes)
        missing = [w for w in REQUIRED if w not in names_lower]
        check("every subject asked for is there: teeth, chitin, eyes and glow, rusty metal, oiled metal, bone, leather, cloth, gems and lenses, skin, wood, blood, verdigris, weathering",
              not missing, missing)
        check("keys, names and summaries are all different", len({r["key"] for r in recipes}) == 18 and len({r["name"] for r in recipes}) == 18 and len({r["summary"] for r in recipes}) == 18)
        check("every recipe has three or four steps", all(3 <= len(r["steps"]) <= 4 for r in recipes), [(r["key"], len(r["steps"])) for r in recipes])
        FIELDS = {"technique", "coats", "mix", "look", "hex", "note"}
        check("every step has exactly: technique, coats, mix, look, hex, note (and no paint name or brand field)", all(set(s) == FIELDS for r in recipes for s in r["steps"]))
        check("every technique is one of the app's usual technique names", all(s["technique"] in techniques for r in recipes for s in r["steps"]),
              sorted({s["technique"] for r in recipes for s in r["steps"] if s["technique"] not in techniques}))
        check("coats is a whole number from 1 to 3 and mix is a whole number from 1 to 100",
              all(isinstance(s["coats"], int) and 1 <= s["coats"] <= 3 and isinstance(s["mix"], int) and 1 <= s["mix"] <= 100 for r in recipes for s in r["steps"]))
        check("a wash, shade or glaze is thinned (mix under 100) and a base coat, layer, highlight or dry brush is full strength",
              all((s["mix"] < 100) == (s["technique"] in ("Wash", "Shade", "Glaze")) for r in recipes for s in r["steps"]),
              [(r["key"], s["technique"], s["mix"]) for r in recipes for s in r["steps"] if (s["mix"] < 100) != (s["technique"] in ("Wash", "Shade", "Glaze"))])
        check("every step names a target colour: a plain colour word or two and a valid #rrggbb", all(s["look"].strip() and re.fullmatch(r"#[0-9a-f]{6}", s["hex"]) for r in recipes for s in r["steps"]))
        check("the steps of a recipe have different target colours", all(len({s["hex"] for s in r["steps"]}) == len(r["steps"]) for r in recipes))
        check("each summary is one short line (no line breaks, 70 characters or fewer)", all("\n" not in r["summary"] and 0 < len(r["summary"]) <= 70 for r in recipes), [r["summary"] for r in recipes if len(r["summary"]) > 70])
        check("each note is one sentence of 100 characters or fewer, and each colour word is short",
              all(len(sentences(s["note"])) == 1 and 0 < len(s["note"]) <= 100 and len(s["look"]) <= 30 for r in recipes for s in r["steps"]),
              [(r["key"], s["note"]) for r in recipes for s in r["steps"] if len(sentences(s["note"])) != 1 or len(s["note"]) > 100])
        check("names say what the recipe is for: short, no digits, no brackets", all(re.fullmatch(r"[A-Za-z' -]{4,40}", r["name"]) for r in recipes), [r["name"] for r in recipes if not re.fullmatch(r"[A-Za-z' -]{4,40}", r["name"])])
        data_text = json.dumps(recipes) + json.dumps(groups)
        known = page.evaluate("() => KNOWN_PAINTS.map(k => [k.name, k.brand])")
        brands = page.evaluate("() => COMMON_BRANDS")
        colour_words = set("red orange yellow green blue purple violet pink brown grey gray black white tan sand bone ivory cream gold golden silver copper bronze steel "
                           "dark light pale bright deep mid dull warm cool charcoal olive khaki earth earthy dusty rusty rust teal turquoise cyan mint lime "
                           "scarlet crimson maroon burgundy navy indigo magenta beige buff stone slate flesh skin leather wood metal metallic gunmetal hot tone verdigris rich "
                           # v48: the built-in list now includes paints simply called things like "Old Copper", "Pale Dust", "Wet Mud" or
                           # "Gloss Varnish", so these plain describing words count as colour words too.
                           "old dust wet dry gloss matt matte satin varnish aged worn faded dirty clean fresh new".split())
        paint_hits = [k[0] for k in known if len(k[0]) >= 6 and any(w not in colour_words for w in re.findall(r"[a-z']+", k[0].lower()))
                      and re.search(r"\b" + re.escape(k[0]) + r"\b", data_text, re.I)]
        brand_hits = [b for b in brands if re.search(r"\b" + re.escape(b) + r"\b", data_text, re.I)]
        check("the steps name colours, never paints: no built-in paint name (other than plain colour words like Charcoal or Copper) and no paint brand appears in the data", not paint_hits and not brand_hits, (paint_hits[:5], brand_hits))
        check("no angle brackets, ampersands or backticks anywhere in the data (plain text only)", not re.search(r"[<>&`]", data_text))
        check("every word in the new recipes is plain English (letters, digits, spaces, apostrophes, hyphens, commas, full stops only)",
              all(re.fullmatch(r"[A-Za-z0-9 ',.\-]+", x) for r in recipes for x in [r["name"], r["summary"]] + [s["look"] + " " + s["note"] for s in r["steps"]]))

        # ---------- 3. The text scan ----------
        print("\n--- 3. Text scan: no Games Workshop names in any new text ---")
        load(page, recipes=RECIPES, units=UNITS)
        edit_recipe(page, 106)
        open_panel(page)
        code_only = "\n".join(l for l in det.splitlines() if not l.strip().startswith("//"))   # the rule comments at the top name the words on purpose
        all_text = data_text + json.dumps(entry) + page.evaluate("() => document.getElementById('detail-recipes').innerText") + code_only
        hits = GW_WORDS.findall(all_text) + GW_MORE.findall(all_text)
        check("the recipe data, group names, the whole data file (apart from the rule comments), Updates entry and Detail recipes heading and hint name no Games Workshop game, faction, scheme, paint or product", not hits, hits)
        shown = []
        for g in ["all"] + GROUPS:
            pick_group(page, g)
            shown.append(page.evaluate(SHOWN_JS))
            for r in [x for x in recipes if g in ("all", x["group"])]:
                pick_recipe(page, r["key"])
                shown.append(page.evaluate(SHOWN_JS))
                pick_recipe(page, r["key"])
        pick_group(page, "all")
        screen_hits = GW_WORDS.findall("\n".join(shown)) + GW_MORE.findall("\n".join(shown))
        check("everything we wrote that the Detail recipes part shows on screen (heading, hint, group and recipe buttons, summary, Add all steps, row lines, tags, notes), for every group and every recipe, names no Games Workshop game, faction, scheme or product",
              not screen_hits and len(shown) > 18, screen_hits[:10])
        own_text = " ".join(" ".join([r["name"], r["summary"]] + [s["look"] + " " + s["note"] + " " + s["technique"] for s in r["steps"]]) for r in recipes) + " ".join(g["name"] for g in groups)
        check("not even the word Citadel appears in any text we wrote for the recipes", "citadel" not in own_text.lower() and "games workshop" not in own_text.lower() and "warhammer" not in own_text.lower())
        check("the shared word lists really do catch the words (the scan itself works)", GW_WORDS.findall("Ultramarines and Tyranids") and GW_MORE.findall("Nurgle and Macragge"))

        # ---------- 4. Group buttons ----------
        print("\n--- 4. Group buttons ---")
        load(page, recipes=RECIPES, units=UNITS)
        edit_recipe(page, 106)
        open_panel(page)
        gc = group_chips(page)
        check("five group buttons: All, Body, Metal, Materials, Light, with All pressed to start", [c[0] for c in gc] == ["All", "Body", "Metal", "Materials", "Light"]
              and [c[1] for c in gc] == ["true", "false", "false", "false", "false"], gc)
        check("the group buttons are in a labelled group", page.get_attribute("#detail-groups", "role") == "group" and "group" in (page.get_attribute("#detail-groups", "aria-label") or "").lower())
        order = page.evaluate("""() => { const g = document.getElementById('detail-groups'), c = document.getElementById('detail-chips'), t = document.querySelector('#detail-recipes .scheme-title');
            const kids = [...document.getElementById('detail-recipes').children]; return [kids.indexOf(t), kids.indexOf(g), kids.indexOf(c)]; }""")
        check("the group buttons sit above the recipe buttons, below the heading", order[0] < order[1] < order[2] and -1 not in order, order)
        check("the heading says Detail recipes", page.inner_text("#detail-recipes .scheme-title") == "Detail recipes")
        rc = recipe_chips(page)
        check("all 18 recipe buttons show to start, none picked, in order", len(rc) == 18 and all(c[1] == "false" for c in rc) and [c[2] for c in rc] == [r["key"] for r in recipes] and [c[0] for c in rc] == [r["name"] for r in recipes], len(rc))
        check("nothing is picked to start: no summary, no rows, no Add all steps button", page.locator("#detail-summary").count() == 0 and page.locator("#detail-list").count() == 0 and page.locator("#detail-add-all").count() == 0)
        for g in GROUPS:
            pick_group(page, g)
            rc = recipe_chips(page)
            gcs = group_chips(page)
            expect = [r["key"] for r in recipes if r["group"] == g]
            check(f"{g}: only that group's recipes show, in order, and only that group's button is pressed", [c[2] for c in rc] == expect and [c[2] for c in gcs if c[1] == "true"] == [g], (len(rc), gcs))
            check(f"{g}: the button keeps the focus after it is tapped", focused(page) == g, focused(page))
        pick_group(page, "all")
        check("All brings back all 18 and is the only one pressed, with the focus on it", len(recipe_chips(page)) == 18 and [c[2] for c in group_chips(page) if c[1] == "true"] == ["all"] and focused(page) == "all")
        pick_group(page, "metal")
        pick_group(page, "metal")
        check("tapping the pressed group again leaves it as it is (use All to see everything)", len(recipe_chips(page)) == counts["metal"] and [c[2] for c in group_chips(page) if c[1] == "true"] == ["metal"])
        pick_role(page, "trim")
        check("changing the role keeps the group", len(recipe_chips(page)) == counts["metal"] and [c[2] for c in group_chips(page) if c[1] == "true"] == ["metal"])
        by_key = {r["key"]: r for r in recipes}
        pick_recipe(page, "verdigris")
        check("a recipe in the chosen group can be picked: the summary shows", page.inner_text("#detail-summary") == by_key["verdigris"]["summary"] and len(detail_rows(page)) == 4)
        pick_group(page, "metal")
        check("tapping the same group leaves the pick alone", page.locator("#detail-list").count() == 1)
        pick_group(page, "all")
        check("switching to All keeps the pick (it is inside All)", page.locator("#detail-list").count() == 1 and page.get_attribute('#detail-chips [data-detail="verdigris"]', "aria-pressed") == "true")
        pick_group(page, "body")
        check("switching to a group that does not contain the pick puts it away (no rows, no summary, nothing pressed)",
              page.locator("#detail-list").count() == 0 and page.locator("#detail-summary").count() == 0 and all(c[1] == "false" for c in recipe_chips(page)))
        pick_group(page, "all")
        check("and it stays put away when coming back to All", page.locator("#detail-list").count() == 0)
        pick_recipe(page, "rust")
        pick_group(page, "metal")
        check("switching to the group that contains the pick keeps it", page.locator("#detail-list").count() == 1 and page.inner_text("#detail-summary") == by_key["rust"]["summary"])
        pick_recipe(page, "rust")
        check("tapping the picked recipe again closes it, with the group kept", page.locator("#detail-list").count() == 0 and len(recipe_chips(page)) == counts["metal"])
        check("the Detail recipes part shows without a start colour too (like the schemes)", True)
        check("an unknown group value falls back to All (nothing breaks)", page.evaluate("""() => { colourIdeasState.detailGroup = 'nonsense'; return detailRecipesShown().length; }""") == 18)
        page.evaluate("() => { colourIdeasState.detailGroup = ''; colourIdeasState.detail = ''; }")
        # With no start colour at all (empty recipe, no paints): the card shows the 'add a paint first' line and still shows the new part.
        load(page, paints=[], recipes=[], units=[])
        open_editor(page)
        open_panel(page)
        check("with no start colour the Detail recipes part still shows, below Starter schemes",
              page.locator("#detail-recipes").count() == 1 and page.locator("#starter-schemes").count() == 1
              and page.evaluate("() => { const k = [...document.querySelector('#colour-ideas .ideas-body').children]; return k.indexOf(document.getElementById('starter-schemes')) < k.indexOf(document.getElementById('detail-recipes')); }"))

        # ---------- 5. Every recipe ----------
        print("\n--- 5. Every recipe: summary, rows, exact paints, adding steps ---")
        load(page, recipes=RECIPES, units=UNITS)
        edit_recipe(page, 106)
        open_panel(page)
        for r in recipes:
            pick_recipe(page, r["key"])
            rows = detail_rows(page)
            ok = (page.inner_text("#detail-summary") == r["summary"] and len(rows) == len(r["steps"])
                  and [x["why"] for x in rows] == [why_line(i + 1, s) for i, s in enumerate(r["steps"])]
                  and all(x["tag"] in ("You own this", "Yours, poor fit", "Not in your palette") for x in rows) and page.locator("#detail-add-all").count() == 1)
            check(f"{r['name']} ({r['group']}): summary, {len(r['steps'])} rows with technique, coats, mix % and note, honest tags, one Add all steps button", ok, (rows[:2], page.inner_text("#detail-summary")))
            pick_recipe(page, r["key"])
        # Yours first: for every recipe, own an exact paint for every step; each row must find it.
        exact_ok, exact_bad = True, []
        for n, r in enumerate(recipes):
            load(page, paints=exact_palette(r, n), recipes=[], units=[])
            open_editor(page)
            open_panel(page)
            pick_recipe(page, r["key"])
            rows = detail_rows(page)
            good = [x["name"] for x in rows] == [f"Exact Paint {n}-{i}" for i in range(len(r["steps"]))] and all(x["tag"] == "You own this" and x["note"] == "" for x in rows)
            if not good:
                exact_ok = False
                exact_bad.append((r["key"], rows))
        check("with an exact paint owned for every step of a recipe, every row of every one of the 18 recipes finds your paint first and says You own this", exact_ok, exact_bad[:1])

        # Adding one step and all steps
        load(page, recipes=RECIPES, units=UNITS)
        edit_recipe(page, 106)
        open_panel(page)
        before = full_steps(page)
        stored_before = stored_recipes(page)
        pick_recipe(page, "rust")
        rust = by_key["rust"]
        names = [x["name"] for x in detail_rows(page)]
        page.locator("#detail-list button.idea-pick").nth(1).click()
        page.wait_for_timeout(250)
        steps = full_steps(page)
        s1 = rust["steps"][1]
        check("tapping one step's paint adds exactly one new last step: that paint, with the technique, coats, mix % and note from the recipe",
              len(steps) == len(before) + 1 and steps[-1]["name"] == names[1] and steps[-1]["technique"] == s1["technique"] and steps[-1]["coats"] == s1["coats"]
              and steps[-1]["mix"] == s1["mix"] and steps[-1]["note"] == s1["note"] and steps[-1]["n"] == 1 and steps[-1]["ratio"] == "" and steps[-1]["optional"] is False, steps[-1])
        check("the steps that were already there are untouched", steps[:len(before)] == before)
        check("the recipe stays picked and the card stays open, and a message says which step was added",
              page.locator("#detail-list button.idea-pick").count() == 4 and page.evaluate("() => document.getElementById('colour-ideas').open") and any("Added step" in n for n in notices), notices[-2:])
        check("nothing is saved by tapping (storage is exactly as it was)", stored_recipes(page) == stored_before)
        n1 = len(full_steps(page))
        page.click("#detail-add-all")
        page.wait_for_timeout(300)
        steps = full_steps(page)
        added = steps[n1:]
        check("Add all steps adds every step (4 for this recipe) as new last steps",
              len(steps) == n1 + 4 and len(added) == 4, len(steps))
        check("in order, each with its technique, coats, mix % and note kept, one paint per step, the paint being the row's paint",
              [(a["technique"], a["coats"], a["mix"], a["note"]) for a in added] == [(s["technique"], s["coats"], s["mix"], s["note"]) for s in rust["steps"]]
              and [a["name"] for a in added] == names and all(a["n"] == 1 and a["ratio"] == "" and a["optional"] is False for a in added), added)
        check("the steps that were there before (including the one tapped) are untouched", steps[:n1] == full_steps(page)[:n1] and steps[:len(before)] == before)
        check("the editor now really shows those steps (one step box each) and one message says how many were added",
              page.locator(".step-edit").count() == n1 + 4 and any("Added 4 steps" in n for n in notices), (page.locator(".step-edit").count(), notices[-2:]))
        check("the card is still open with the recipe still picked", page.evaluate("() => document.getElementById('colour-ideas').open") and page.locator("#detail-list").count() == 1)
        check("still nothing is saved (storage is exactly as it was)", stored_recipes(page) == stored_before)
        page.click("#recipe-page button.primary-button:has-text('Save recipe')")
        page.wait_for_timeout(400)
        if page.is_visible("#dialog-yes"):
            page.click("#dialog-yes")
            page.wait_for_timeout(300)
        saved = json.loads(stored_recipes(page))
        mine = [x for x in saved["recipes"] if x["id"] == 106]
        check("after Save recipe the added steps are saved with the recipe (technique, coats, mix kept)",
              mine and len(mine[0]["steps"]) == n1 + 4 and [(s["technique"], s["coats"], s["paints"][0]["mix"]) for s in mine[0]["steps"][-4:]] == [(s["technique"], s["coats"], s["mix"]) for s in rust["steps"]]
              and mine[0]["steps"][-1]["note"] == rust["steps"][-1]["note"], mine and len(mine[0]["steps"]))
        # Add all steps on a new, empty recipe (the first step box is a blank one)
        load(page, recipes=RECIPES, units=UNITS)
        for key in ["gems", "teeth", "glow", "oiled-metal"]:
            open_editor(page)
            open_panel(page)
            nblank = len(full_steps(page))
            pick_recipe(page, key)
            page.click("#detail-add-all")
            page.wait_for_timeout(300)
            st = full_steps(page)[nblank:]
            check(f"{by_key[key]['name']}: Add all steps on a new recipe adds all {len(by_key[key]['steps'])} steps in order with everything kept",
                  [(a["technique"], a["coats"], a["mix"], a["note"]) for a in st] == [(s["technique"], s["coats"], s["mix"], s["note"]) for s in by_key[key]["steps"]], st)
            page.click("#recipe-page button.plain-button:has-text('Cancel')")
            page.wait_for_timeout(250)
            if page.is_visible("#dialog-yes"):
                page.click("#dialog-yes")
                page.wait_for_timeout(250)

        # ---------- 6. Honesty ----------
        print("\n--- 6. Honesty ---")
        gem = by_key["gems"]
        mixed = [{"id": 1, "brand": "Test", "name": "Exact Deep Blue", "colour": gem["steps"][0]["hex"], "status": "owned"},
                 {"id": 2, "brand": "Test", "name": "Exact Pale Blue", "colour": gem["steps"][2]["hex"], "status": "wishlist"},
                 {"id": 3, "brand": "Test", "name": "Far Brown", "colour": "#5a3a24", "status": "owned"}]
        load(page, paints=mixed, recipes=[], units=[])
        open_editor(page)
        open_panel(page)
        pick_recipe(page, "gems")
        rows = detail_rows(page)
        check("an owned paint that is exactly the wanted colour says You own this (step 1)", rows[0]["name"] == "Exact Deep Blue" and rows[0]["tag"] == "You own this" and rows[0]["note"] == "", rows)
        # v64: the wishlist paint is the closest paint overall, so it is shown first; it still never says You own this
        check("a wishlist paint that is exactly right never says You own this (step 3 is a pale blue and the only exact paint for it is on the wishlist)",
              rows[2]["tag"] != "You own this" and rows[2]["fit"] == "Good fit", rows[2])
        check("every row has one of the three honest tags and a fit label", all(x["tag"] in ("You own this", "Yours, poor fit", "Not in your palette") for x in rows) and len(rows) == 4
              and all(x["fit"] or x["tag"] == "Yours, poor fit" for x in rows), rows)
        check("when the nearest paint you own is far from the colour wanted, the best paint overall comes first and yours sits under it as Yours, poor fit (no note sentences, never You own this)",
              all(x["tag"] != "You own this" and x["note"] == "" and (x["also"] == "Yours, poor fit" or x["tag"] == "Yours, poor fit") for x in rows[1:]), rows[1:])
        load(page, paints=[], recipes=[], units=[])
        open_editor(page)
        open_panel(page)
        allnone = True
        for r in recipes:
            pick_recipe(page, r["key"])
            rr = detail_rows(page)
            allnone = allnone and len(rr) == len(r["steps"]) and all(x["tag"] == "Not in your palette" for x in rr)
            pick_recipe(page, r["key"])
        check("with an empty palette every row of every recipe says Not in your palette (the built-in list is used, nothing is claimed as owned)", allnone)
        page.evaluate("() => { colourIdeasState.detail = 'glow'; }")
        far_only = [{"id": 1, "brand": "Test", "name": "Only Grey", "colour": "#808080", "status": "owned"}]
        load(page, paints=far_only, recipes=[], units=[])
        open_editor(page)
        open_panel(page)
        pick_recipe(page, "glow")
        rr = detail_rows(page)
        check("a palette with only a grey paint still gets honest tags and the 'dried paint' style notes where the match is rough (never You own this for a rough match)",
              all(x["tag"] != "You own this" or x["note"] == "" for x in rr) and len(rr) == 4, rr)

        # ---------- 7. Hostile text ----------
        print("\n--- 7. Hostile text (text-injection test) ---")
        hostile_paints = [{"id": 90, "brand": HOSTILE_BRAND, "name": HOSTILE, "colour": by_key["glow"]["steps"][1]["hex"], "status": "owned"},
                          {"id": 91, "brand": "Test", "name": "Plain Red", "colour": "#c8262b", "status": "owned"}]
        hostile_units = [unit(1, HOSTILE + " Troop", HOSTILE + " Faction", [140, 106]), unit(2, "Second", HOSTILE + " Faction", [141])]
        hostile_recipes = [rec(140, HOSTILE + " recipe", "Armour", [90]), rec(141, "Second recipe", "Armour", [90, 91]), rec(106, "Mine", "Eyes", [91])]
        load(page, paints=hostile_paints, recipes=hostile_recipes, units=hostile_units)
        edit_recipe(page, 106)
        open_panel(page)
        for g in ["light", "body", "all"]:
            pick_group(page, g)
        pick_recipe(page, "glow")
        texts = detail_text(page)
        check("a paint and brand full of HTML show as plain text in the new rows", "<img" in texts and "Evil" in texts
              and page.locator("#detail-recipes img, #detail-recipes script, #detail-recipes b").count() == 0, texts[:200])
        check("nothing ran (no onerror, no script) and the whole card has no injected tags",
              page.evaluate("() => window.__pwned") is None and page.locator("#colour-ideas img, #colour-ideas script, #colour-ideas .ideas-body b").count() == 0)
        n0 = len(full_steps(page))
        page.click("#detail-add-all")
        page.wait_for_timeout(250)
        st = full_steps(page)
        names_in = [a["name"] for a in st[n0:]]
        check("Add all steps with the hostile paint adds it as text (the step holds the characters, no markup is built from them)",
              HOSTILE in names_in and page.evaluate("() => window.__pwned") is None and page.locator("#recipe-page img[src='x']").count() == 0, names_in)
        check("the new group buttons and recipe buttons are built from fixed text (no HTML anywhere in them)",
              page.evaluate("() => [...document.querySelectorAll('#detail-groups .chip, #detail-chips .chip, #detail-add-all')].every(c => c.children.length === 0)"))
        hostile_state = page.evaluate("""() => { colourIdeasState.detailGroup = '<img src=x onerror="window.__pwned=3">'; colourIdeasState.detail = '<b>x</b>'; return detailRecipesShown().length; }""")
        check("a hostile saved group or recipe value is ignored (it falls back to All, nothing is built from it)", hostile_state == 18 and page.evaluate("() => window.__pwned") is None)
        page.evaluate("() => { colourIdeasState.detailGroup = ''; colourIdeasState.detail = ''; }")

        # ---------- 8. Offline ----------
        print("\n--- 8. Offline ---")
        load(page, recipes=RECIPES, units=UNITS)
        edit_recipe(page, 106)
        open_panel(page)
        requests.clear()
        page.on("request", lambda rq: requests.append(rq.url))
        ctx.set_offline(True)
        for g in GROUPS + ["all"]:
            pick_group(page, g)
        pick_recipe(page, "teeth")
        pick_recipe(page, "wood")
        ok_off = len(detail_rows(page)) == 4 and len(recipe_chips(page)) == 18
        page.click("#detail-add-all")
        page.wait_for_timeout(250)
        page.locator("#detail-list button.idea-pick").first.click()
        page.wait_for_timeout(250)
        ctx.set_offline(False)
        check("with the network switched off, the group buttons, the recipes, Add all steps and single taps still work", ok_off)
        check("using the group buttons, picking recipes and adding steps made no network requests at all", requests == [], requests)
        ctx3 = browser.new_context(viewport={"width": 390, "height": 844}, service_workers="block")
        page3 = ctx3.new_page()
        errors3 = []
        page3.on("pageerror", lambda e: errors3.append(str(e)))
        page3.route("**/detail-recipes.js*", lambda r: r.abort())
        load(page3, recipes=RECIPES, units=UNITS)
        edit_recipe(page3, 106)
        open_panel(page3)
        check("if detail-recipes.js is missing, the recipe editor and the rest of the Colour ideas card (ideas, history, starter schemes, check) still work and the new part is simply not there",
              page3.evaluate("() => typeof DETAIL_RECIPES") == "undefined" and page3.locator("#colour-ideas").count() == 1 and page3.locator("#detail-recipes").count() == 0
              and page3.locator("#colour-ideas button.idea").count() == 3 and page3.locator("#faction-history").count() == 1 and page3.locator("#starter-schemes").count() == 1
              and page3.locator("#scheme-check").count() == 1 and not errors3, errors3[:2])
        ctx3.close()
        ctx4 = browser.new_context(viewport={"width": 390, "height": 844}, service_workers="block")
        page4 = ctx4.new_page()
        errors4 = []
        page4.on("pageerror", lambda e: errors4.append(str(e)))
        page4.route("**/schemes.js*", lambda r: r.abort())
        load(page4, recipes=RECIPES, units=UNITS)
        edit_recipe(page4, 106)
        open_panel(page4)
        check("if schemes.js is missing instead, the Detail recipes part still shows (the two data files do not depend on each other)",
              page4.locator("#starter-schemes").count() == 0 and page4.locator("#detail-recipes").count() == 1 and not errors4, errors4[:2])
        ctx4.close()

        # ---------- 9. Phone sizes, dark and light ----------
        print("\n--- 9. Dark and light at 390 and 360 px ---")
        for appearance in ["dark", "light"]:
            for width in [390, 360]:
                page.set_viewport_size({"width": width, "height": 844})
                tag = f"{appearance} {width}px"
                load(page, recipes=RECIPES, units=UNITS, settings={"appearance": appearance})
                edit_recipe(page, 106)
                open_panel(page)
                page.locator("#detail-recipes").scroll_into_view_if_needed()
                page.wait_for_timeout(150)
                def geometry():
                    return page.evaluate("""() => { const c = document.getElementById('colour-ideas').getBoundingClientRect();
                        const inside = (el) => { const r = el.getBoundingClientRect(); return r.left >= c.left - 0.5 && r.right <= c.right + 0.5; };
                        const grp = [...document.querySelectorAll('#detail-groups .chip')], rcp = [...document.querySelectorAll('#detail-chips .chip')];
                        const rrows = new Set(rcp.map(b => Math.round(b.getBoundingClientRect().top)));
                        const grows = new Set(grp.map(b => Math.round(b.getBoundingClientRect().top)));
                        const box = document.getElementById('detail-chips').getBoundingClientRect();
                        return { cl: c.left, cr: c.right, w: window.innerWidth, grpInside: grp.every(inside), rcpInside: rcp.every(inside), n: rcp.length,
                                 grpMinH: Math.min(...grp.map(b => b.getBoundingClientRect().height)), rcpRows: rrows.size, grpRows: grows.size, listH: box.height }; }""")
                g_all = geometry()
                shot(page, f"v32-groups-all-{appearance}-{width}.png")
                check(f"{tag}: the card is inside the screen, and every group and recipe button is inside the card",
                      g_all["cl"] >= 0 and g_all["cr"] <= g_all["w"] + 0.5 and g_all["grpInside"] and g_all["rcpInside"], g_all)
                check(f"{tag}: the five group buttons take one or two lines and are at least 36 px tall, and the 18 recipe buttons wrap onto several lines",
                      g_all["n"] == 18 and g_all["grpRows"] <= 2 and g_all["rcpRows"] >= 3 and g_all["grpMinH"] >= 36, g_all)
                check(f"{tag}: no sideways scroll", no_sideways(page))
                pick_group(page, "light")
                g_light = geometry()
                shot(page, f"v32-groups-light-{appearance}-{width}.png")
                check(f"{tag}: choosing a group makes the list clearly shorter than All and keeps everything inside",
                      g_light["n"] == 2 and g_light["listH"] < g_all["listH"] * 0.5 and g_light["rcpInside"] and no_sideways(page), (g_light["listH"], g_all["listH"]))
                pick_group(page, "metal")
                pick_recipe(page, "rust")
                page.locator("#detail-add-all").scroll_into_view_if_needed()
                page.wait_for_timeout(150)
                rowsg = page.evaluate("""() => { const c = document.getElementById('colour-ideas').getBoundingClientRect();
                    const b = [...document.querySelectorAll('#detail-list button.idea-pick')], a = document.getElementById('detail-add-all').getBoundingClientRect();
                    return { n: b.length, minH: Math.min(...b.map(x => x.getBoundingClientRect().height)), addH: a.height, addInside: a.left >= c.left - 0.5 && a.right <= c.right + 0.5,
                             inside: b.every(x => { const r = x.getBoundingClientRect(); return r.left >= c.left - 0.5 && r.right <= c.right + 0.5; }) }; }""")
                shot(page, f"v32-recipe-{appearance}-{width}.png")
                check(f"{tag}: the four rows are each at least 44 px tall and inside the card, and Add all steps is at least 44 px tall and inside the card",
                      rowsg["n"] == 4 and rowsg["minH"] >= 44 and rowsg["inside"] and rowsg["addH"] >= 44 and rowsg["addInside"], rowsg)
                col = page.evaluate("""() => { const bg = (el) => { let e = el; while (e) { const v = getComputedStyle(e).backgroundColor;
                        const m = v.match(/rgba\\(.*,\\s*([\\d.]+)\\)/);
                        if (v && v !== 'transparent' && !(m && parseFloat(m[1]) < 0.9)) return v; e = e.parentElement; } return 'rgb(0,0,0)'; };
                    const out = {};
                    const pairs = [['group on', '#detail-groups .chip[aria-pressed="true"]'], ['group off', '#detail-groups .chip[aria-pressed="false"]'],
                                   ['recipe on', '#detail-chips .chip[aria-pressed="true"]'], ['recipe off', '#detail-chips .chip[aria-pressed="false"]'],
                                   ['hint', '#detail-recipes > .hint'], ['summary', '#detail-summary'], ['add all', '#detail-add-all'],
                                   ['row name', '#detail-list .idea-name'], ['row why', '#detail-list .idea-why'], ['row add', '#detail-list .idea-add']];
                    for (const [k, s] of pairs) { const el = document.querySelector(s); if (el) out[k] = [getComputedStyle(el).color, bg(el)]; }
                    return out; }""")
                bad = {k: round(contrast(rgb(v[0]), rgb(v[1])), 2) for k, v in col.items() if contrast(rgb(v[0]), rgb(v[1])) < 4.5}
                check(f"{tag}: group buttons (on and off), recipe buttons, hint, summary, Add all steps and rows all have contrast of at least 4.5", not bad and len(col) >= 10, (bad, list(col)))
                pick_group(page, "all")
        page.set_viewport_size({"width": 390, "height": 844})

        # ---------- 10. Nothing else changed ----------
        print("\n--- 10. Starter schemes, Your schemes and the rest still work as in v31 ---")
        load(page, recipes=RECIPES, units=UNITS)
        edit_recipe(page, 106)
        open_panel(page)
        schemes = page.evaluate("STARTER_SCHEMES")
        check("all 24 starter schemes and the five mood buttons are still there", len(schemes) == 24 and page.locator("#starter-moods .chip").count() == 5 and page.locator("#starter-chips .chip").count() == 24)
        page.click('#starter-schemes [data-scheme="orange-blue"]')
        page.wait_for_timeout(150)
        srows = page.evaluate("""() => [...document.querySelectorAll('#starter-list button.idea-pick')].map(b => b.querySelector('.idea-why').textContent)""")
        sch = {s["key"]: s for s in schemes}["orange-blue"]
        n0 = len(full_steps(page))
        page.locator("#starter-list button.idea-pick").nth(2).click()
        page.wait_for_timeout(250)
        st = full_steps(page)
        check("a starter scheme still shows four rows (part and colour word) and tapping a paint still adds one step: 100%, 1 coat, the same note as in v31",
              srows == [f"{c['part']}: {c['look']}." for c in sch["colours"]] and len(st) == n0 + 1 and st[-1]["mix"] == 100 and st[-1]["coats"] == 1
              and st[-1]["note"] == "Starter scheme (Orange and mid blue): trim" and st[-1]["technique"] == "", st[-1])
        check("the faction history is still there with its rows", page.locator("#faction-history").count() == 1 and len(t.hist_rows(page)) >= 1)
        n0 = len(full_steps(page))
        page.locator("#faction-history button.idea-pick").first.click()
        page.wait_for_timeout(250)
        check("tapping a faction history paint still adds one step with the note 'Used before on this faction'", len(full_steps(page)) == n0 + 1 and full_steps(page)[-1]["note"] == "Used before on this faction")
        check("the main three ideas are still exactly three 'idea' buttons", page.locator("#colour-ideas button.idea").count() == 3)
        order = page.evaluate("""() => { const ids = ['colour-ideas-tip', 'faction-history', 'starter-schemes', 'detail-recipes', 'scheme-check'];
            const body = document.querySelector('#colour-ideas .ideas-body'); return ids.map(i => [...body.children].indexOf(document.getElementById(i))); }""")
        check("order in the card: tip, faction history, starter schemes, Detail recipes (new), then the check", order == sorted(order) and -1 not in order, order)
        check("the card is still labelled Pro preview and still ends with the footnote", page.inner_text("#colour-ideas .pro-pill") == "Pro preview"
              and page.evaluate("() => document.querySelector('#colour-ideas .ideas-body').lastElementChild.textContent.includes('Nothing leaves your phone')"))
        check("the Colour ideas card starts closed in a fresh editor", (lambda: (load(page), open_editor(page), page.evaluate("() => document.getElementById('colour-ideas').open"))[-1])() is False)
        n = page.locator(".step-edit").count()
        t.add_step(page)
        check("+ Add step still adds an empty step", page.locator(".step-edit").count() == n + 1)
        t.set_step_paint(page, 0, "Brand New Paint X")
        page.wait_for_timeout(150)
        check("the 'Do you own these?' card still appears for a paint that is new to your palette", page.locator("#recipe-own").count() == 1 and page.is_visible("#recipe-own"))
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
