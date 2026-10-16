"""v33 tests for Minifolio (Libraries, Lib 3): "Basing tips" in the Colour ideas card (Pro preview).

What changed: a new data file (basing-tips.js, loaded between detail-recipes.js and app.js, wired into index.html and sw.js the
same way detail-recipes.js is) holds 12 generic basing how-tos (sand, gravel, cracked earth, ash and soot, mud, snow, ice, grass,
moss, rock, rubble, lava). Each has a plain name, a one-line summary, a short list of materials in plain words, a few how-to steps
and optional paint steps. A paint step names a TARGET COLOUR (a plain colour word and a hex), never a paint. A "Basing tips" part
sits in the Colour ideas card below Detail recipes, with group buttons (All, Dry ground, Wet and cold, Plants, Stone and fire) and
a button per tip. Picking a tip shows the materials, the how-to steps as plain text, and then the optional paint steps, each with
the nearest paint (yours first, the built-in list after) and the same honest tags and notes as the detail recipe rows. Tapping
one paint adds just that step; "Add all paint steps" adds every paint step to the recipe being edited as new last steps (nothing
is saved until Save recipe). The materials and how-to steps are only shown, never added. No shop links anywhere.
Starter schemes, Your schemes and Detail recipes are unchanged (tests/test_v30.py, test_v31.py and test_v32.py still check them).

Checks:
1. Versions, the v33 Updates entry, wiring (basing-tips.js loads between detail-recipes.js and app.js and is saved for offline
   use), CSP and storage names unchanged, no network or storage code in the new file, no links or shop words.
2. The data: 12 tips in four groups, every required subject present, valid fields, short plain text, target colours only (no paint
   names, no brand names, no product names).
3. The text scan: no Games Workshop game, faction, scheme, paint or product names in any new text (data, group names, hint,
   Updates entry, and everything shown on screen for every group and every tip).
4. Group buttons: where they sit, All is the default, each group shows its tips, focus stays put, the choice is kept across roles,
   a picked tip outside the chosen group is put away, one inside it is kept.
5. Every tip: summary, materials list, how-to steps, one paint row per paint step with honest tags; yours first (exact owned
   paints are found for every paint step of every tip); a single tap adds one step with everything kept; Add all paint steps adds
   every paint step, in order, as new last steps; materials and how-to steps are never added; nothing is saved until Save recipe;
   a tip with no paint steps shows no buttons and says so.
6. Honesty: an owned exact paint says You own this, a wishlist paint never does, an empty palette says Not in your palette, a
   far-off owned paint says Closest you own with its note.
7. Hostile text (text-injection test): paint, brand, faction and recipe names, and a tip whose every text field is full of HTML,
   never become markup in the new part.
8. Offline: no network requests, works with the network off, and if basing-tips.js is missing the rest of the card still works.
9. Dark and light at 390 and 360 px: inside the screen, buttons wrap, the filtered list is shorter, lists and rows are inside the
   card, the Add all paint steps button and the rows are at least 44 px tall, contrast 4.5.
10. Starter schemes, Your schemes and Detail recipes still work exactly as in v32, the order of the card parts, nothing else changed.
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

REQUIRED = ["sand", "snow", "grass", "mud", "rock", "cracked earth", "rubble", "lava", "gravel", "moss", "ash", "ice"]
GROUPS = ["ground", "cold", "plants", "stone"]
SHOWN_JS = """() => [...document.querySelectorAll('#basing-tips > .scheme-title, #basing-tips > .hint, #basing-tips .chip, #basing-summary, #basing-tips .basing-sub, #basing-tips .basing-list li, #basing-no-paint, #basing-none, #basing-add-all, #basing-list .idea-why, #basing-list .idea-tag, #basing-list .idea-note, #basing-list .idea-add')].map(e => e.textContent).join('\\n')"""
# brand and product words that must not appear in anything we wrote for the tips
BRAND_WORDS = re.compile(r"\b(citadel|vallejo|army painter|scale ?75|tamiya|ak interactive|woodland scenics|gale force|green stuff|milliput|vaseline|polyfilla|"
                         r"mod podge|games workshop|warhammer|agrax|nuln|stirland|reikland|typhus|badab|lahmian|nihilakh|seraphim|ultra ?marine|"
                         r"pva|vinyl|flock|static grass|amazon|ebay|etsy|shop|buy|store|ad)\b", re.I)

def cap(text):
    return text[:1].upper() + text[1:]

def why_line(i, s):
    return f"Paint step {i}: {s['technique']}, {s['coats']} coat{'' if s['coats'] == 1 else 's'}, {s['mix']}% paint. {cap(s['look'])}. {s['note']}"

def basing_rows(page):
    return page.evaluate("""() => [...document.querySelectorAll('#basing-list button.idea-pick')].map(b => ({
        name: b.querySelector('.idea-name').childNodes[0].textContent, brand: (b.querySelector('.idea-name small') || {}).textContent || '',
        tag: b.querySelector('.idea-tag').textContent, why: b.querySelector('.idea-why').textContent,
        note: (b.querySelector('.idea-note') || {}).textContent || '' }))""")

def group_chips(page):
    return page.evaluate("() => [...document.querySelectorAll('#basing-groups .chip')].map(c => [c.textContent, c.getAttribute('aria-pressed'), c.dataset.basingGroup])")

def tip_chips(page):
    return page.evaluate("() => [...document.querySelectorAll('#basing-chips .chip')].map(c => [c.textContent, c.getAttribute('aria-pressed'), c.dataset.basing])")

def pick_group(page, key):
    page.click(f'#basing-groups [data-basing-group="{key}"]')
    page.wait_for_timeout(150)

def pick_tip(page, key):
    page.click(f'#basing-chips [data-basing="{key}"]')
    page.wait_for_timeout(150)

def list_texts(page, sel):
    return page.evaluate("(s) => [...document.querySelectorAll(s)].map(e => e.textContent)", sel)

def full_steps(page):
    return page.evaluate("() => recipeDraft.steps.map(s => ({ technique: s.technique, coats: s.coats, ratio: s.ratio, optional: s.optional, note: s.note, n: s.paints.length, name: s.paints[0].name, brand: s.paints[0].brand, colour: s.paints[0].colour, mix: s.paints[0].mix }))")

def stored_recipes(page):
    return page.evaluate("() => localStorage.getItem('shades-of-grey-recipes')")

def focused(page):
    return page.evaluate("() => document.activeElement && (document.activeElement.dataset.basingGroup || document.activeElement.dataset.basing || document.activeElement.id) || ''")

def basing_text(page):
    return page.evaluate("() => (document.getElementById('basing-tips') || {}).innerText || ''")

def exact_palette(tip, n, status="owned", start=300):
    # (the names avoid words like metal or ink, which the app treats as special kinds of paint)
    return [{"id": start + i, "brand": "Test", "name": f"Exact Paint {n}-{i}", "colour": s["hex"], "status": status} for i, s in enumerate(tip["paintSteps"])]

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
        html, app, sw, colour, bas = read("index.html"), read("app.js"), read("sw.js"), read("colour.js"), read("basing-tips.js")
        version = page.evaluate("APP_VERSION")
        check("APP_VERSION is v33 or later", float(version[1:]) >= 33, version)
        m = re.search(r'const VERSION = "([^"]+)"', sw)
        check("sw.js VERSION matches APP_VERSION", m and m.group(1) == version, m and m.group(1))
        tags = re.findall(r'<script src="([a-z-]+)\.js\?v=([\d.]+)"></script>', html)
        check("index.html loads early.js, colour.js, schemes.js, detail-recipes.js, basing-tips.js, then app.js (six tags), all with ?v= matching the version",
              [x[0] for x in tags] == ["early", "colour", "schemes", "detail-recipes", "basing-tips", "app"] and len(re.findall(r"<script\b", html)) == 6 and all(x[1] == version[1:] for x in tags), tags)
        check("basing-tips.js is saved for offline use by sw.js, with the same ?v= tag as the other files",
              '"./basing-tips.js" + CODE_TAG' in sw and len(re.findall(r'"\./[a-z-]+\.js" \+ CODE_TAG', sw)) == 6, re.findall(r'"\./[^"]+"', sw))
        check("the comments naming the version number match", f'The "?v={version[1:]}" makes' in html and f'e.g. "app.js?v={version[1:]}"' in app)
        entry = page.evaluate("CHANGELOG.find(r => r.version === 'v33')")
        check("Updates has a v33 entry with at least two lines", entry and len(entry["changes"]) >= 2, entry)
        check("the newest Updates entry is v33 or later", float(page.evaluate("CHANGELOG[0].version")[1:]) >= 33)
        check("the Updates entry says Pro preview, Basing tips, 12, Add all paint steps, Save recipe, that materials are only shown, and that nothing leaves the phone",
              entry and "Pro preview" in entry["changes"][0] and "Basing tips" in entry["changes"][0] and "12" in entry["changes"][0]
              and "Add all paint steps" in entry["changes"][1] and "Save recipe" in entry["changes"][1] and "only shown" in entry["changes"][1]
              and "sends nothing anywhere" in entry["changes"][1] and "offline" in entry["changes"][1], entry)
        check("the v32, v31 and v30 Updates entries are still there", page.evaluate("['v32', 'v31', 'v30'].every(v => !!CHANGELOG.find(r => r.version === v))"))
        check("DATA_VERSION is still 1", page.evaluate("DATA_VERSION") == 1)
        check("the three storage names are unchanged",
              all(k in app for k in ['STORAGE_KEY = "mini-tracker-models"', 'SETTINGS_KEY = "shades-of-grey-settings"', 'RECIPES_KEY = "shades-of-grey-recipes"']))
        policy = re.search(r'http-equiv="Content-Security-Policy"\s+content="([^"]+)"', html)
        policy = policy.group(1) if policy else ""
        hosts = set(re.findall(r"https?://[^\s;'\"]+", policy))
        check("the security policy is untouched: the only outside address is still the one GoatCounter picture address",
              len(hosts) == 1 and "goatcounter" in list(hosts)[0], (hosts, policy[:200]))
        check("basing-tips.js is only data: it adds exactly two names (BASING_GROUPS, BASING_TIPS) and has no network code, no storage, no HTML building, no eval",
              re.findall(r"^(?:const|let|var|function)\s+(\w+)", bas, re.M) == ["BASING_GROUPS", "BASING_TIPS"]
              and not re.search(r"\bfetch\s*\(|XMLHttpRequest|sendBeacon|WebSocket|localStorage|sessionStorage|indexedDB|\beval\s*\(|new Function|innerHTML|insertAdjacentHTML|outerHTML|document\.|window\.|import\s|require\s*\(", bas))
        check("no web address, link or shop wording anywhere in the new data file (no shop links in this chunk)",
              not re.search(r"https?:|www\.|\.com\b|\.co\.uk|href", bas, re.I) and not BRAND_WORDS.search("\n".join(l for l in bas.splitlines() if not l.strip().startswith("//"))))
        check("the tip data is not in app.js (it uses the names from basing-tips.js)",
              "const BASING_TIPS" not in app and "const BASING_GROUPS" not in app and 'key: "lava"' not in app and "BASING_TIPS" in app)
        panel_code = app[app.index("v28: \"COLOUR IDEAS\""):app.index('v18c: TIDY BRANDS')]
        new_code = panel_code[panel_code.index("(4) v33: Basing tips"):panel_code.index("function buildColourIdeasCard")]
        check("the new code has no network code, no storage, no innerHTML, no links and no shop wording; the panel still has exactly one innerHTML (its own clear)",
              not re.search(r"\bfetch\s*\(|XMLHttpRequest|sendBeacon|WebSocket|localStorage|sessionStorage|\beval\s*\(|new Function|insertAdjacentHTML|outerHTML|innerHTML|createElement\('a'\)|href|affiliate", new_code)
              and panel_code.count("innerHTML") == 1 and 'body.innerHTML = ""' in panel_code, [mm.group(0) for mm in re.finditer(r"innerHTML[^\n]*", panel_code)])
        check("colour.js, schemes.js and detail-recipes.js were not touched by this chunk", "schemeCheck" in colour and "root.MinifolioColour = api;" in colour
              and "STARTER_SCHEMES" in read("schemes.js") and "DETAIL_RECIPES" in read("detail-recipes.js"))
        check("the Pro preview label is still there", "Pro preview" in app and page.evaluate("() => typeof BASING_TIPS") == "object")

        # ---------- 2. The data ----------
        print("\n--- 2. The tip data ---")
        tips = page.evaluate("BASING_TIPS")
        groups = page.evaluate("BASING_GROUPS")
        techniques = page.evaluate("DEFAULT_TECHNIQUES")
        check("there are 12 tips (10 to 12 asked for)", len(tips) == 12, len(tips))
        check("four groups, in order: Dry ground, Wet and cold, Plants, Stone and fire",
              [g["key"] for g in groups] == GROUPS and [g["name"] for g in groups] == ["Dry ground", "Wet and cold", "Plants", "Stone and fire"], groups)
        counts = {g: len([x for x in tips if x["group"] == g]) for g in GROUPS}
        check("every tip is in one of the groups and every group has at least two tips", sum(counts.values()) == 12 and all(v >= 2 for v in counts.values()), counts)
        names_lower = " | ".join(x["name"].lower() for x in tips)
        missing = [w for w in REQUIRED if w not in names_lower]
        check("every subject asked for is there: sand, snow, grass, mud, rock, cracked earth, rubble, lava (and gravel, moss, ash, ice)", not missing, missing)
        check("keys, names and summaries are all different", len({x["key"] for x in tips}) == 12 and len({x["name"] for x in tips}) == 12 and len({x["summary"] for x in tips}) == 12)
        check("every tip has exactly: key, group, name, summary, materials, howto, paintSteps", all(set(x) == {"key", "group", "name", "summary", "materials", "howto", "paintSteps"} for x in tips))
        check("every tip has 3 to 6 materials, 3 to 5 how-to steps and 0 to 5 paint steps", all(3 <= len(x["materials"]) <= 6 and 3 <= len(x["howto"]) <= 5 and 0 <= len(x["paintSteps"]) <= 5 for x in tips),
              [(x["key"], len(x["materials"]), len(x["howto"]), len(x["paintSteps"])) for x in tips])
        check("most tips have paint steps (paint steps are optional, but at least 10 of the 12 give some)", len([x for x in tips if x["paintSteps"]]) >= 10)
        check("each materials line is a plain thing: short, one line, no full stop, and the materials of a tip are all different",
              all(0 < len(m_) <= 70 and "\n" not in m_ and not m_.endswith(".") for x in tips for m_ in x["materials"]) and all(len(set(x["materials"])) == len(x["materials"]) for x in tips),
              [m_ for x in tips for m_ in x["materials"] if len(m_) > 70 or m_.endswith(".")])
        check("each how-to step is one sentence of 120 characters or fewer, ending with a full stop",
              all(len(sentences(h)) == 1 and 0 < len(h) <= 120 and h.endswith(".") for x in tips for h in x["howto"]),
              [h for x in tips for h in x["howto"] if len(sentences(h)) != 1 or len(h) > 120 or not h.endswith(".")])
        FIELDS = {"technique", "coats", "mix", "look", "hex", "note"}
        steps_all = [s for x in tips for s in x["paintSteps"]]
        check("every paint step has exactly: technique, coats, mix, look, hex, note (and no paint name or brand field)", all(set(s) == FIELDS for s in steps_all))
        check("every technique is one of the app's usual technique names", all(s["technique"] in techniques for s in steps_all), sorted({s["technique"] for s in steps_all if s["technique"] not in techniques}))
        check("coats is a whole number from 1 to 3 and mix is a whole number from 1 to 100",
              all(isinstance(s["coats"], int) and 1 <= s["coats"] <= 3 and isinstance(s["mix"], int) and 1 <= s["mix"] <= 100 for s in steps_all))
        check("a wash, shade or glaze is thinned (mix under 100) and a base coat, layer, highlight, stipple or dry brush is full strength",
              all((s["mix"] < 100) == (s["technique"] in ("Wash", "Shade", "Glaze")) for s in steps_all),
              [(s["technique"], s["mix"]) for s in steps_all if (s["mix"] < 100) != (s["technique"] in ("Wash", "Shade", "Glaze"))])
        check("every paint step names a target colour: a plain colour word or two and a valid #rrggbb", all(s["look"].strip() and re.fullmatch(r"#[0-9a-f]{6}", s["hex"]) for s in steps_all))
        check("the paint steps of a tip have different target colours", all(len({s["hex"] for s in x["paintSteps"]}) == len(x["paintSteps"]) for x in tips))
        check("each summary is one short line (no line breaks, 70 characters or fewer)", all("\n" not in x["summary"] and 0 < len(x["summary"]) <= 70 for x in tips), [x["summary"] for x in tips if len(x["summary"]) > 70])
        check("each note is one sentence of 100 characters or fewer, and each colour word is short",
              all(len(sentences(s["note"])) == 1 and 0 < len(s["note"]) <= 100 and len(s["look"]) <= 30 for s in steps_all),
              [s["note"] for s in steps_all if len(sentences(s["note"])) != 1 or len(s["note"]) > 100])
        check("names say what the base is: short, no digits, no brackets", all(re.fullmatch(r"[A-Za-z' -]{3,40}", x["name"]) for x in tips), [x["name"] for x in tips if not re.fullmatch(r"[A-Za-z' -]{3,40}", x["name"])])
        data_text = json.dumps(tips) + json.dumps(groups)
        known = page.evaluate("() => KNOWN_PAINTS.map(k => [k.name, k.brand])")
        brands = page.evaluate("() => COMMON_BRANDS")
        colour_words = set("red orange yellow green blue purple violet pink brown grey gray black white tan sand bone ivory cream gold golden silver copper bronze steel "
                           "dark light pale bright deep mid dull warm cool charcoal olive khaki earth earthy dusty rusty rust teal turquoise cyan mint lime "
                           "scarlet crimson maroon burgundy navy indigo magenta beige buff stone slate flesh skin leather wood metal metallic gunmetal hot tone verdigris rich "
                           "mud snow ice grass moss rock lava ash soot gravel rubble straw".split())
        paint_hits = [k[0] for k in known if len(k[0]) >= 6 and any(w not in colour_words for w in re.findall(r"[a-z']+", k[0].lower()))
                      and re.search(r"\b" + re.escape(k[0]) + r"\b", data_text, re.I)]
        brand_hits = [b for b in brands if re.search(r"\b" + re.escape(b) + r"\b", data_text, re.I)]
        check("the paint steps name colours, never paints: no built-in paint name (other than plain colour words) and no paint brand appears in the data", not paint_hits and not brand_hits, (paint_hits[:5], brand_hits))
        check("no brand names and no product names anywhere in the data (a word list of brands, shops and product words)", not BRAND_WORDS.search(data_text), BRAND_WORDS.findall(data_text))
        check("no angle brackets, ampersands or backticks anywhere in the data (plain text only)", not re.search(r"[<>&`]", data_text))
        every_text = [x["name"] for x in tips] + [x["summary"] for x in tips] + [g["name"] for g in groups] + [m_ for x in tips for m_ in x["materials"]] + [h for x in tips for h in x["howto"]] \
                     + [s["look"] + " " + s["note"] for s in steps_all]
        check("every word in the new text is plain English (letters, digits, spaces, apostrophes, hyphens, commas, full stops only)", all(re.fullmatch(r"[A-Za-z0-9 ',.\-]+", x) for x in every_text),
              [x for x in every_text if not re.fullmatch(r"[A-Za-z0-9 ',.\-]+", x)][:3])
        check("the shared word lists really do catch the words (the scan itself works)", GW_WORDS.findall("Ultramarines and Tyranids") and GW_MORE.findall("Nurgle and Macragge")
              and BRAND_WORDS.findall("Citadel and Vallejo, Polyfilla, flock"))

        # ---------- 3. The text scan ----------
        print("\n--- 3. Text scan: no Games Workshop names in any new text ---")
        load(page, recipes=RECIPES, units=UNITS)
        edit_recipe(page, 106)
        open_panel(page)
        code_only = "\n".join(l for l in bas.splitlines() if not l.strip().startswith("//"))   # the rule comments at the top name the words on purpose
        all_text = data_text + json.dumps(entry) + page.evaluate("() => document.getElementById('basing-tips').innerText") + code_only
        hits = GW_WORDS.findall(all_text) + GW_MORE.findall(all_text)
        check("the tip data, group names, the whole data file (apart from the rule comments), Updates entry and the Basing tips heading and hint name no Games Workshop game, faction, scheme, paint or product", not hits, hits)
        shown = []
        for g in ["all"] + GROUPS:
            pick_group(page, g)
            shown.append(page.evaluate(SHOWN_JS))
            for x in [y for y in tips if g in ("all", y["group"])]:
                pick_tip(page, x["key"])
                shown.append(page.evaluate(SHOWN_JS))
                pick_tip(page, x["key"])
        pick_group(page, "all")
        screen_hits = GW_WORDS.findall("\n".join(shown)) + GW_MORE.findall("\n".join(shown))
        check("everything we wrote that the Basing tips part shows on screen (heading, hint, group and tip buttons, summary, materials, how-to steps, paint step lines, tags, notes), for every group and every tip, names no Games Workshop game, faction, scheme or product",
              not screen_hits and len(shown) > 12, screen_hits[:10])
        screen_brand = BRAND_WORDS.findall("\n".join(shown))
        check("and none of it names a brand, a shop or a product", not screen_brand, screen_brand[:10])
        own_text = " ".join(every_text) + " " + " ".join(s["technique"] for s in steps_all)
        check("not even the word Citadel appears in any text we wrote for the tips", "citadel" not in own_text.lower() and "games workshop" not in own_text.lower() and "warhammer" not in own_text.lower())

        # ---------- 4. Group buttons ----------
        print("\n--- 4. Group buttons ---")
        load(page, recipes=RECIPES, units=UNITS)
        edit_recipe(page, 106)
        open_panel(page)
        gc = group_chips(page)
        check("five group buttons: All, Dry ground, Wet and cold, Plants, Stone and fire, with All pressed to start",
              [c[0] for c in gc] == ["All", "Dry ground", "Wet and cold", "Plants", "Stone and fire"] and [c[1] for c in gc] == ["true", "false", "false", "false", "false"], gc)
        check("the group buttons are in a labelled group", page.get_attribute("#basing-groups", "role") == "group" and "group" in (page.get_attribute("#basing-groups", "aria-label") or "").lower())
        order = page.evaluate("""() => { const g = document.getElementById('basing-groups'), c = document.getElementById('basing-chips'), t = document.querySelector('#basing-tips .scheme-title');
            const kids = [...document.getElementById('basing-tips').children]; return [kids.indexOf(t), kids.indexOf(g), kids.indexOf(c)]; }""")
        check("the group buttons sit above the tip buttons, below the heading", order[0] < order[1] < order[2] and -1 not in order, order)
        check("the heading says Basing tips", page.inner_text("#basing-tips .scheme-title") == "Basing tips")
        rc = tip_chips(page)
        check("all 12 tip buttons show to start, none picked, in order", len(rc) == 12 and all(c[1] == "false" for c in rc) and [c[2] for c in rc] == [x["key"] for x in tips] and [c[0] for c in rc] == [x["name"] for x in tips], len(rc))
        check("nothing is picked to start: no summary, no materials, no how-to, no rows, no Add all paint steps button",
              all(page.locator(s).count() == 0 for s in ["#basing-summary", "#basing-materials", "#basing-howto", "#basing-list", "#basing-add-all"]))
        for g in GROUPS:
            pick_group(page, g)
            rc = tip_chips(page)
            gcs = group_chips(page)
            expect = [x["key"] for x in tips if x["group"] == g]
            check(f"{g}: only that group's tips show, in order, and only that group's button is pressed", [c[2] for c in rc] == expect and [c[2] for c in gcs if c[1] == "true"] == [g], (len(rc), gcs))
            check(f"{g}: the button keeps the focus after it is tapped", focused(page) == g, focused(page))
        pick_group(page, "all")
        check("All brings back all 12 and is the only one pressed, with the focus on it", len(tip_chips(page)) == 12 and [c[2] for c in group_chips(page) if c[1] == "true"] == ["all"] and focused(page) == "all")
        pick_group(page, "stone")
        pick_group(page, "stone")
        check("tapping the pressed group again leaves it as it is (use All to see everything)", len(tip_chips(page)) == counts["stone"] and [c[2] for c in group_chips(page) if c[1] == "true"] == ["stone"])
        pick_role(page, "trim")
        check("changing the role keeps the group", len(tip_chips(page)) == counts["stone"] and [c[2] for c in group_chips(page) if c[1] == "true"] == ["stone"])
        by_key = {x["key"]: x for x in tips}
        pick_tip(page, "lava")
        check("a tip in the chosen group can be picked: the summary shows", page.inner_text("#basing-summary") == by_key["lava"]["summary"] and len(basing_rows(page)) == 5)
        check("picking a tip keeps the focus on its button", focused(page) == "lava", focused(page))
        pick_group(page, "stone")
        check("tapping the same group leaves the pick alone", page.locator("#basing-list").count() == 1)
        pick_group(page, "all")
        check("switching to All keeps the pick (it is inside All)", page.locator("#basing-list").count() == 1 and page.get_attribute('#basing-chips [data-basing="lava"]', "aria-pressed") == "true")
        pick_group(page, "plants")
        check("switching to a group that does not contain the pick puts it away (no lists, no summary, nothing pressed)",
              all(page.locator(s).count() == 0 for s in ["#basing-list", "#basing-summary", "#basing-materials", "#basing-howto"]) and all(c[1] == "false" for c in tip_chips(page)))
        pick_group(page, "all")
        check("and it stays put away when coming back to All", page.locator("#basing-list").count() == 0)
        pick_tip(page, "rock")
        pick_group(page, "stone")
        check("switching to the group that contains the pick keeps it", page.locator("#basing-list").count() == 1 and page.inner_text("#basing-summary") == by_key["rock"]["summary"])
        pick_tip(page, "rock")
        check("tapping the picked tip again closes it, with the group kept", page.locator("#basing-list").count() == 0 and len(tip_chips(page)) == counts["stone"])
        check("an unknown group value falls back to All (nothing breaks)", page.evaluate("""() => { colourIdeasState.basingGroup = 'nonsense'; return basingTipsShown().length; }""") == 12)
        page.evaluate("() => { colourIdeasState.basingGroup = ''; colourIdeasState.basing = ''; }")
        load(page, paints=[], recipes=[], units=[])
        open_editor(page)
        open_panel(page)
        check("with no start colour the Basing tips part still shows, below Detail recipes",
              page.locator("#basing-tips").count() == 1 and page.locator("#detail-recipes").count() == 1
              and page.evaluate("() => { const k = [...document.querySelector('#colour-ideas .ideas-body').children]; return k.indexOf(document.getElementById('detail-recipes')) < k.indexOf(document.getElementById('basing-tips')); }"))

        # ---------- 5. Every tip ----------
        print("\n--- 5. Every tip: summary, materials, how-to, rows, exact paints, adding steps ---")
        load(page, recipes=RECIPES, units=UNITS)
        edit_recipe(page, 106)
        open_panel(page)
        for x in tips:
            pick_tip(page, x["key"])
            rows = basing_rows(page)
            subs = list_texts(page, "#basing-tips .basing-sub")
            kinds = page.evaluate("() => [document.getElementById('basing-materials').tagName, document.getElementById('basing-howto').tagName]")
            ok = (page.inner_text("#basing-summary") == x["summary"]
                  and list_texts(page, "#basing-materials li") == x["materials"] and list_texts(page, "#basing-howto li") == x["howto"] and kinds == ["UL", "OL"]
                  and subs[:2] == ["What you need", "How to build it"] and (subs[2:] == ["Paint steps (optional)"] if x["paintSteps"] else subs[2:] == [])
                  and len(rows) == len(x["paintSteps"]) and [r["why"] for r in rows] == [why_line(i + 1, s) for i, s in enumerate(x["paintSteps"])]
                  and all(r["tag"] in ("You own this", "Closest you own", "Not in your palette") for r in rows)
                  and page.locator("#basing-add-all").count() == (1 if x["paintSteps"] else 0))
            check(f"{x['name']} ({x['group']}): summary, {len(x['materials'])} materials, {len(x['howto'])} how-to steps as plain text, {len(x['paintSteps'])} paint rows with technique, coats, mix % and note, honest tags, one Add all paint steps button",
                  ok, (rows[:2], subs, page.inner_text("#basing-summary")))
            pick_tip(page, x["key"])
        # Yours first: for every tip, own an exact paint for every paint step; each row must find it.
        exact_ok, exact_bad = True, []
        for n, x in enumerate(tips):
            load(page, paints=exact_palette(x, n), recipes=[], units=[])
            open_editor(page)
            open_panel(page)
            pick_tip(page, x["key"])
            rows = basing_rows(page)
            good = [r["name"] for r in rows] == [f"Exact Paint {n}-{i}" for i in range(len(x["paintSteps"]))] and all(r["tag"] == "You own this" and r["note"] == "" for r in rows)
            if not good:
                exact_ok = False
                exact_bad.append((x["key"], rows))
        check("with an exact paint owned for every paint step of a tip, every row of every one of the 12 tips finds your paint first and says You own this", exact_ok, exact_bad[:1])

        # Adding one step and all paint steps
        load(page, recipes=RECIPES, units=UNITS)
        edit_recipe(page, 106)
        open_panel(page)
        before = full_steps(page)
        stored_before = stored_recipes(page)
        pick_tip(page, "mud")
        mud = by_key["mud"]
        names = [r["name"] for r in basing_rows(page)]
        page.locator("#basing-list button.idea-pick").nth(1).click()
        page.wait_for_timeout(250)
        steps = full_steps(page)
        s1 = mud["paintSteps"][1]
        check("tapping one paint adds exactly one new last step: that paint, with the technique, coats, mix % and note from the paint step",
              len(steps) == len(before) + 1 and steps[-1]["name"] == names[1] and steps[-1]["technique"] == s1["technique"] and steps[-1]["coats"] == s1["coats"]
              and steps[-1]["mix"] == s1["mix"] and steps[-1]["note"] == s1["note"] and steps[-1]["n"] == 1 and steps[-1]["ratio"] == "" and steps[-1]["optional"] is False, steps[-1])
        check("the steps that were already there are untouched", steps[:len(before)] == before)
        check("the tip stays picked and the card stays open, and a message says which step was added",
              page.locator("#basing-list button.idea-pick").count() == 4 and page.evaluate("() => document.getElementById('colour-ideas').open") and any("Added step" in n for n in notices), notices[-2:])
        check("nothing is saved by tapping (storage is exactly as it was)", stored_recipes(page) == stored_before)
        n1 = len(full_steps(page))
        page.click("#basing-add-all")
        page.wait_for_timeout(300)
        steps = full_steps(page)
        added = steps[n1:]
        check("Add all paint steps adds every paint step (4 for this tip) as new last steps", len(steps) == n1 + 4 and len(added) == 4, len(steps))
        check("in order, each with its technique, coats, mix % and note kept, one paint per step, the paint being the row's paint",
              [(a["technique"], a["coats"], a["mix"], a["note"]) for a in added] == [(s["technique"], s["coats"], s["mix"], s["note"]) for s in mud["paintSteps"]]
              and [a["name"] for a in added] == names and all(a["n"] == 1 and a["ratio"] == "" and a["optional"] is False for a in added), added)
        check("the steps that were there before (including the one tapped) are untouched", steps[:len(before)] == before)
        check("the materials and the how-to steps were NOT added: no new step has any material or how-to text in its note, and no extra steps appeared",
              not any(a["note"] in mud["materials"] + mud["howto"] for a in steps[len(before):]) and len(steps) == len(before) + 1 + len(mud["paintSteps"]),
              [a["note"] for a in steps[len(before):]])
        check("the editor now really shows those steps (one step box each) and one message says how many were added",
              page.locator(".step-edit").count() == n1 + 4 and any("Added 4 steps" in n for n in notices), (page.locator(".step-edit").count(), notices[-2:]))
        check("the card is still open with the tip still picked", page.evaluate("() => document.getElementById('colour-ideas').open") and page.locator("#basing-list").count() == 1)
        check("still nothing is saved (storage is exactly as it was)", stored_recipes(page) == stored_before)
        page.click("#recipe-page button.primary-button:has-text('Save recipe')")
        page.wait_for_timeout(400)
        if page.is_visible("#dialog-yes"):
            page.click("#dialog-yes")
            page.wait_for_timeout(300)
        saved = json.loads(stored_recipes(page))
        mine = [r for r in saved["recipes"] if r["id"] == 106]
        check("after Save recipe the added steps are saved with the recipe (technique, coats, mix kept)",
              mine and len(mine[0]["steps"]) == n1 + 4 and [(s["technique"], s["coats"], s["paints"][0]["mix"]) for s in mine[0]["steps"][-4:]] == [(s["technique"], s["coats"], s["mix"]) for s in mud["paintSteps"]]
              and mine[0]["steps"][-1]["note"] == mud["paintSteps"][-1]["note"], mine and len(mine[0]["steps"]))
        # Add all paint steps on a new, empty recipe (the first step box is a blank one)
        load(page, recipes=RECIPES, units=UNITS)
        for key in ["lava", "snow", "sand", "ice"]:
            open_editor(page)
            open_panel(page)
            nblank = len(full_steps(page))
            pick_tip(page, key)
            page.click("#basing-add-all")
            page.wait_for_timeout(300)
            st = full_steps(page)[nblank:]
            check(f"{by_key[key]['name']}: Add all paint steps on a new recipe adds all {len(by_key[key]['paintSteps'])} steps in order with everything kept",
                  [(a["technique"], a["coats"], a["mix"], a["note"]) for a in st] == [(s["technique"], s["coats"], s["mix"], s["note"]) for s in by_key[key]["paintSteps"]], st)
            page.click("#recipe-page button.plain-button:has-text('Cancel')")
            page.wait_for_timeout(250)
            if page.is_visible("#dialog-yes"):
                page.click("#dialog-yes")
                page.wait_for_timeout(250)
        # A tip with no paint steps (none of the shipped tips is like that, so one is added for the test)
        load(page, recipes=RECIPES, units=UNITS)
        edit_recipe(page, 106)
        open_panel(page)
        page.evaluate("() => BASING_TIPS.push({ key: 'plain', group: 'stone', name: 'Plain test tip', summary: 'No paint here', materials: ['A thing', 'Another thing', 'A third thing'], howto: ['Do one.', 'Do two.', 'Do three.'], paintSteps: [] })")
        pick_group(page, "all")
        nb = len(full_steps(page))
        pick_tip(page, "plain")
        check("a tip with no paint steps shows its summary, materials and how-to steps, then a plain line saying there are no paint steps, and no Add all button and no rows",
              page.inner_text("#basing-summary") == "No paint here" and list_texts(page, "#basing-materials li") == ["A thing", "Another thing", "A third thing"]
              and list_texts(page, "#basing-howto li") == ["Do one.", "Do two.", "Do three."] and page.inner_text("#basing-no-paint") == "There are no paint steps for this one."
              and page.locator("#basing-add-all").count() == 0 and page.locator("#basing-list").count() == 0 and len(full_steps(page)) == nb)
        page.evaluate("() => { BASING_TIPS.pop(); colourIdeasState.basing = ''; }")

        # ---------- 6. Honesty ----------
        print("\n--- 6. Honesty ---")
        ice = by_key["ice"]
        mixed = [{"id": 1, "brand": "Test", "name": "Exact Deep Blue", "colour": ice["paintSteps"][0]["hex"], "status": "owned"},
                 {"id": 2, "brand": "Test", "name": "Exact Pale Blue", "colour": ice["paintSteps"][1]["hex"], "status": "wishlist"},
                 {"id": 3, "brand": "Test", "name": "Far Brown", "colour": "#5a3a24", "status": "owned"}]
        load(page, paints=mixed, recipes=[], units=[])
        open_editor(page)
        open_panel(page)
        pick_tip(page, "ice")
        rows = basing_rows(page)
        check("an owned paint that is exactly the wanted colour says You own this (paint step 1)", rows[0]["name"] == "Exact Deep Blue" and rows[0]["tag"] == "You own this" and rows[0]["note"] == "", rows)
        check("a wishlist paint that is exactly right never says You own this (paint step 2 is a pale blue and the only exact paint for it is on the wishlist)",
              rows[1]["name"] != "Exact Pale Blue" and rows[1]["tag"] != "You own this", rows[1])
        check("every row has one of the three honest tags", all(r["tag"] in ("You own this", "Closest you own", "Not in your palette") for r in rows) and len(rows) == 3, rows)
        check("when the nearest paint you own is far from the colour wanted, the row says Closest you own and says it is not very close or similar, not exact (never You own this)",
              all(r["tag"] == "Closest you own" and ("Not very close" in r["note"] or "Similar, not exact" in r["note"]) for r in rows[1:]), rows[1:])
        load(page, paints=[], recipes=[], units=[])
        open_editor(page)
        open_panel(page)
        allnone = True
        for x in tips:
            pick_tip(page, x["key"])
            rr = basing_rows(page)
            allnone = allnone and len(rr) == len(x["paintSteps"]) and all(r["tag"] == "Not in your palette" for r in rr)
            pick_tip(page, x["key"])
        check("with an empty palette every row of every tip says Not in your palette (the built-in list is used, nothing is claimed as owned)", allnone)
        far_only = [{"id": 1, "brand": "Test", "name": "Only Grey", "colour": "#808080", "status": "owned"}]
        load(page, paints=far_only, recipes=[], units=[])
        open_editor(page)
        open_panel(page)
        pick_tip(page, "lava")
        rr = basing_rows(page)
        check("a palette with only a grey paint still gets honest tags and the style notes where the match is rough (never You own this for a rough match)",
              all(r["tag"] != "You own this" or r["note"] == "" for r in rr) and len(rr) == 5, rr)

        # ---------- 7. Hostile text ----------
        print("\n--- 7. Hostile text (text-injection test) ---")
        hostile_paints = [{"id": 90, "brand": HOSTILE_BRAND, "name": HOSTILE, "colour": by_key["lava"]["paintSteps"][1]["hex"], "status": "owned"},
                          {"id": 91, "brand": "Test", "name": "Plain Red", "colour": "#c8262b", "status": "owned"}]
        hostile_units = [unit(1, HOSTILE + " Troop", HOSTILE + " Faction", [140, 106]), unit(2, "Second", HOSTILE + " Faction", [141])]
        hostile_recipes = [rec(140, HOSTILE + " recipe", "Armour", [90]), rec(141, "Second recipe", "Armour", [90, 91]), rec(106, "Mine", "Eyes", [91])]
        load(page, paints=hostile_paints, recipes=hostile_recipes, units=hostile_units)
        edit_recipe(page, 106)
        open_panel(page)
        for g in ["stone", "cold", "all"]:
            pick_group(page, g)
        pick_tip(page, "lava")
        texts = basing_text(page)
        check("a paint and brand full of HTML show as plain text in the new rows", "<img" in texts and "Evil" in texts
              and page.locator("#basing-tips img, #basing-tips script, #basing-tips b").count() == 0, texts[:200])
        check("nothing ran (no onerror, no script) and the whole card has no injected tags",
              page.evaluate("() => window.__pwned") is None and page.locator("#colour-ideas img, #colour-ideas script, #colour-ideas .ideas-body b").count() == 0)
        n0 = len(full_steps(page))
        page.click("#basing-add-all")
        page.wait_for_timeout(250)
        st = full_steps(page)
        names_in = [a["name"] for a in st[n0:]]
        check("Add all paint steps with the hostile paint adds it as text (the step holds the characters, no markup is built from them)",
              HOSTILE in names_in and page.evaluate("() => window.__pwned") is None and page.locator("#recipe-page img[src='x']").count() == 0, names_in)
        check("the new group buttons, tip buttons and Add all button are built from fixed text (no HTML anywhere in them)",
              page.evaluate("() => [...document.querySelectorAll('#basing-groups .chip, #basing-chips .chip, #basing-add-all')].every(c => c.children.length === 0)"))
        hostile_state = page.evaluate("""() => { colourIdeasState.basingGroup = '<img src=x onerror="window.__pwned=3">'; colourIdeasState.basing = '<b>x</b>'; return basingTipsShown().length; }""")
        check("a hostile saved group or tip value is ignored (it falls back to All, nothing is built from it)", hostile_state == 12 and page.evaluate("() => window.__pwned") is None)
        page.evaluate("() => { colourIdeasState.basingGroup = ''; colourIdeasState.basing = ''; }")
        # A tip whose every text field is HTML: all of it must show as characters (the injection test on every kind of new text)
        page.evaluate("""(h) => BASING_TIPS.push({ key: 'evil', group: 'stone', name: h, summary: h, materials: [h, h + '2', h + '3'], howto: [h, h + '2', h + '3'],
            paintSteps: [{ technique: 'Base coat', coats: 1, mix: 100, look: h, hex: '#123456', note: h }] })""", HOSTILE)
        pick_group(page, "all")
        pick_tip(page, "evil")
        etext = basing_text(page)
        check("a tip whose name, summary, materials, how-to steps, colour word and note are all full of HTML shows every one as plain characters",
              etext.count("<img") >= 9 and page.locator("#basing-tips img, #basing-tips script, #basing-tips b, #basing-tips i").count() == 0
              and page.evaluate("() => window.__pwned") is None, (etext.count("<img"), etext[:120]))
        check("the hostile text sits inside plain list items and text nodes only (no element was created from it)",
              page.evaluate("() => [...document.querySelectorAll('#basing-materials li, #basing-howto li, #basing-summary, #basing-chips .chip[data-basing=\"evil\"]')].every(e => e.children.length === 0)"))
        page.evaluate("() => { BASING_TIPS.pop(); colourIdeasState.basing = ''; }")

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
        pick_tip(page, "sand")
        pick_tip(page, "grass")
        ok_off = len(basing_rows(page)) == 4 and len(tip_chips(page)) == 12 and len(list_texts(page, "#basing-howto li")) == 5
        page.click("#basing-add-all")
        page.wait_for_timeout(250)
        page.locator("#basing-list button.idea-pick").first.click()
        page.wait_for_timeout(250)
        ctx.set_offline(False)
        check("with the network switched off, the group buttons, the tips, Add all paint steps and single taps still work", ok_off)
        check("using the group buttons, picking tips and adding steps made no network requests at all", requests == [], requests)
        ctx3 = browser.new_context(viewport={"width": 390, "height": 844}, service_workers="block")
        page3 = ctx3.new_page()
        errors3 = []
        page3.on("pageerror", lambda e: errors3.append(str(e)))
        page3.route("**/basing-tips.js*", lambda r: r.abort())
        load(page3, recipes=RECIPES, units=UNITS)
        edit_recipe(page3, 106)
        open_panel(page3)
        check("if basing-tips.js is missing, the recipe editor and the rest of the Colour ideas card (ideas, history, starter schemes, detail recipes, check) still work and the new part is simply not there",
              page3.evaluate("() => typeof BASING_TIPS") == "undefined" and page3.locator("#colour-ideas").count() == 1 and page3.locator("#basing-tips").count() == 0
              and page3.locator("#colour-ideas button.idea").count() == 3 and page3.locator("#faction-history").count() == 1 and page3.locator("#starter-schemes").count() == 1
              and page3.locator("#detail-recipes").count() == 1 and page3.locator("#scheme-check").count() == 1 and not errors3, errors3[:2])
        ctx3.close()
        ctx4 = browser.new_context(viewport={"width": 390, "height": 844}, service_workers="block")
        page4 = ctx4.new_page()
        errors4 = []
        page4.on("pageerror", lambda e: errors4.append(str(e)))
        page4.route("**/detail-recipes.js*", lambda r: r.abort())
        load(page4, recipes=RECIPES, units=UNITS)
        edit_recipe(page4, 106)
        open_panel(page4)
        check("if detail-recipes.js is missing instead, the Basing tips part still shows (the data files do not depend on each other)",
              page4.locator("#detail-recipes").count() == 0 and page4.locator("#basing-tips").count() == 1 and not errors4, errors4[:2])
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
                page.locator("#basing-tips").scroll_into_view_if_needed()
                page.wait_for_timeout(150)
                def geometry():
                    return page.evaluate("""() => { const c = document.getElementById('colour-ideas').getBoundingClientRect();
                        const inside = (el) => { const r = el.getBoundingClientRect(); return r.left >= c.left - 0.5 && r.right <= c.right + 0.5; };
                        const grp = [...document.querySelectorAll('#basing-groups .chip')], rcp = [...document.querySelectorAll('#basing-chips .chip')];
                        const rrows = new Set(rcp.map(b => Math.round(b.getBoundingClientRect().top)));
                        const grows = new Set(grp.map(b => Math.round(b.getBoundingClientRect().top)));
                        const box = document.getElementById('basing-chips').getBoundingClientRect();
                        return { cl: c.left, cr: c.right, w: window.innerWidth, grpInside: grp.every(inside), rcpInside: rcp.every(inside), n: rcp.length,
                                 grpMinH: Math.min(...grp.map(b => b.getBoundingClientRect().height)), rcpRows: rrows.size, grpRows: grows.size, listH: box.height }; }""")
                g_all = geometry()
                shot(page, f"v33-groups-all-{appearance}-{width}.png")
                check(f"{tag}: the card is inside the screen, and every group and tip button is inside the card",
                      g_all["cl"] >= 0 and g_all["cr"] <= g_all["w"] + 0.5 and g_all["grpInside"] and g_all["rcpInside"], g_all)
                check(f"{tag}: the five group buttons take one or two lines and are at least 36 px tall, and the 12 tip buttons wrap onto several lines",
                      g_all["n"] == 12 and g_all["grpRows"] <= 2 and g_all["rcpRows"] >= 2 and g_all["grpMinH"] >= 36, g_all)
                check(f"{tag}: no sideways scroll", no_sideways(page))
                pick_group(page, "plants")
                g_pl = geometry()
                shot(page, f"v33-groups-plants-{appearance}-{width}.png")
                check(f"{tag}: choosing a group makes the list clearly shorter than All and keeps everything inside",
                      g_pl["n"] == 2 and g_pl["listH"] < g_all["listH"] * 0.6 and g_pl["rcpInside"] and no_sideways(page), (g_pl["listH"], g_all["listH"]))
                pick_group(page, "stone")
                pick_tip(page, "lava")
                page.locator("#basing-summary").scroll_into_view_if_needed()
                page.wait_for_timeout(150)
                shot(page, f"v33-tip-top-{appearance}-{width}.png")
                lists = page.evaluate("""() => { const c = document.getElementById('colour-ideas').getBoundingClientRect();
                    const li = [...document.querySelectorAll('#basing-materials li, #basing-howto li')];
                    const inside = (r) => r.left >= c.left - 0.5 && r.right <= c.right + 0.5;
                    return { n: li.length, inside: li.every(x => inside(x.getBoundingClientRect())), listsInside: ['basing-materials', 'basing-howto'].every(i => inside(document.getElementById(i).getBoundingClientRect())),
                             sideways: document.documentElement.scrollWidth > window.innerWidth + 1 }; }""")
                check(f"{tag}: the materials and how-to lines are all inside the card, wrap instead of running off, and the page does not scroll sideways",
                      lists["n"] == len(by_key["lava"]["materials"]) + len(by_key["lava"]["howto"]) and lists["inside"] and lists["listsInside"] and not lists["sideways"], lists)
                page.locator("#basing-add-all").scroll_into_view_if_needed()
                page.wait_for_timeout(150)
                rowsg = page.evaluate("""() => { const c = document.getElementById('colour-ideas').getBoundingClientRect();
                    const b = [...document.querySelectorAll('#basing-list button.idea-pick')], a = document.getElementById('basing-add-all').getBoundingClientRect();
                    return { n: b.length, minH: Math.min(...b.map(x => x.getBoundingClientRect().height)), addH: a.height, addInside: a.left >= c.left - 0.5 && a.right <= c.right + 0.5,
                             inside: b.every(x => { const r = x.getBoundingClientRect(); return r.left >= c.left - 0.5 && r.right <= c.right + 0.5; }) }; }""")
                shot(page, f"v33-tip-paint-{appearance}-{width}.png")
                check(f"{tag}: the five paint rows are each at least 44 px tall and inside the card, and Add all paint steps is at least 44 px tall and inside the card",
                      rowsg["n"] == 5 and rowsg["minH"] >= 44 and rowsg["inside"] and rowsg["addH"] >= 44 and rowsg["addInside"], rowsg)
                col = page.evaluate("""() => { const bg = (el) => { let e = el; while (e) { const v = getComputedStyle(e).backgroundColor;
                        const m = v.match(/rgba\\(.*,\\s*([\\d.]+)\\)/);
                        if (v && v !== 'transparent' && !(m && parseFloat(m[1]) < 0.9)) return v; e = e.parentElement; } return 'rgb(0,0,0)'; };
                    const out = {};
                    const pairs = [['group on', '#basing-groups .chip[aria-pressed="true"]'], ['group off', '#basing-groups .chip[aria-pressed="false"]'],
                                   ['tip on', '#basing-chips .chip[aria-pressed="true"]'], ['tip off', '#basing-chips .chip[aria-pressed="false"]'],
                                   ['hint', '#basing-tips > .hint'], ['summary', '#basing-summary'], ['sub heading', '#basing-tips .basing-sub'],
                                   ['material', '#basing-materials li'], ['how-to', '#basing-howto li'], ['add all', '#basing-add-all'],
                                   ['row name', '#basing-list .idea-name'], ['row why', '#basing-list .idea-why'], ['row add', '#basing-list .idea-add']];
                    for (const [k, s] of pairs) { const el = document.querySelector(s); if (el) out[k] = [getComputedStyle(el).color, bg(el)]; }
                    return out; }""")
                bad = {k: round(contrast(rgb(v[0]), rgb(v[1])), 2) for k, v in col.items() if contrast(rgb(v[0]), rgb(v[1])) < 4.5}
                check(f"{tag}: group buttons (on and off), tip buttons, hint, summary, sub headings, materials, how-to lines, Add all paint steps and rows all have contrast of at least 4.5", not bad and len(col) >= 13, (bad, list(col)))
                pick_group(page, "all")
        page.set_viewport_size({"width": 390, "height": 844})

        # ---------- 10. Nothing else changed ----------
        print("\n--- 10. Starter schemes, Your schemes and Detail recipes still work as in v32 ---")
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
        # Detail recipes exactly as in v32
        dr = page.evaluate("DETAIL_RECIPES")
        check("Detail recipes still has all 18 recipes and its five group buttons", len(dr) == 18 and page.locator("#detail-groups .chip").count() == 5 and page.locator("#detail-chips .chip").count() == 18)
        page.click('#detail-chips [data-detail="rust"]')
        page.wait_for_timeout(150)
        rust = {r["key"]: r for r in dr}["rust"]
        drows = page.evaluate("""() => [...document.querySelectorAll('#detail-list button.idea-pick .idea-why')].map(e => e.textContent)""")
        check("a detail recipe still shows its steps as 'Step 1: ...' (not 'Paint step')", len(drows) == 4 and drows[0].startswith("Step 1: " + rust["steps"][0]["technique"]) and not any("Paint step" in x for x in drows), drows[:1])
        n0 = len(full_steps(page))
        page.click("#detail-add-all")
        page.wait_for_timeout(300)
        st = full_steps(page)
        check("Add all steps in Detail recipes still adds all 4 steps with technique, coats, mix % and note kept",
              len(st) == n0 + 4 and [(a["technique"], a["coats"], a["mix"], a["note"]) for a in st[n0:]] == [(s["technique"], s["coats"], s["mix"], s["note"]) for s in rust["steps"]])
        check("picking a detail recipe does not pick a basing tip, and picking a basing tip does not pick a detail recipe (separate choices)",
              page.locator("#basing-list").count() == 0 and (lambda: (pick_tip(page, "snow"), page.locator("#detail-list").count() == 1 and page.locator("#basing-list").count() == 1)[-1])())
        check("the main three ideas are still exactly three 'idea' buttons", page.locator("#colour-ideas button.idea").count() == 3)
        order = page.evaluate("""() => { const ids = ['colour-ideas-tip', 'faction-history', 'starter-schemes', 'detail-recipes', 'basing-tips', 'scheme-check'];
            const body = document.querySelector('#colour-ideas .ideas-body'); return ids.map(i => [...body.children].indexOf(document.getElementById(i))); }""")
        check("order in the card: tip, faction history, starter schemes, Detail recipes, Basing tips (new), then the check", order == sorted(order) and -1 not in order, order)
        check("the card is still labelled Pro preview and still ends with the footnote", page.inner_text("#colour-ideas .pro-pill") == "Pro preview"
              and page.evaluate("() => document.querySelector('#colour-ideas .ideas-body').lastElementChild.textContent.includes('Nothing leaves your phone')"))
        check("the whole Colour ideas card has no links at all (no shop links, Coach 5 is not merged)", page.locator("#colour-ideas a").count() == 0)
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
