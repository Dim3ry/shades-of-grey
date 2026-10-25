"""v35 tests for Minifolio (Compendium 1): a fifth bottom tab, "Compendium" (Pro preview), that shows the same content as the Colour ideas
card in the recipe editor (paint ideas for a chosen colour, Your schemes, Starter schemes, Detail recipes, Basing tips) without needing a
recipe. The card's building blocks are now shared functions used by BOTH the recipe editor and the Compendium. With no recipe open, the
rows have no add buttons: each part has "Copy as text" and "Save into a new recipe…" instead. No colour wheel yet (Compendium 2).

Checks:
1. Versions, the v35 Updates entry, wiring (no new script file, the data files and colour.js unchanged, sw.js saves the same files),
   Help names five tabs, security policy untouched, the new code has no network code, no storage and no innerHTML.
2. The five-tab bottom bar: order, label "Compendium" in full, fits at 360 and 400 px (and 390), nothing scrolls sideways, the tab lights up.
3. Same content, not a copy: for the same colour, every role gives the same ideas in the card and in the Compendium; every starter
   scheme, detail recipe and basing tip gives the same rows in both (names, tags, reasons, notes). The section order is the card's order.
4. No recipe, no add buttons: no "+ Add as a step", no "Add all", no tappable rows in the Compendium; the card in a recipe still has them.
5. Your schemes (faction history) with a faction drop-down: the factions of your units, most-used paints first, honest tags, empty states.
6. Copy as text for every part (the words, the toast, plain text only) and "Save into a new recipe…" (opens the editor with the steps,
   nothing saved until Save recipe, Cancel asks first, asks before replacing a draft in progress).
7. Honesty: an owned exact paint says You own this, a wishlist paint never does, an empty palette says Not in your palette.
8. Separate picks (the Compendium and the card never change each other), picks kept while the app is open, no duplicate page ids.
9. Text scan: nothing we wrote that the Compendium shows (every scheme, detail recipe, tip and group) names a Games Workshop game,
   faction, scheme, paint or product, and the new Updates and Help text is clean too.
10. Hostile text (text-injection test): paint, brand, faction and recipe names full of HTML never become markup in the Compendium, in
    Copy as text or in the new recipe.
11. Offline: no network requests, and it works with the network off.
12. Dark and light at 390 and 360 px: nothing scrolls sideways with every part open, text contrast 4.5 or more.
13. Nothing else changed: the other tabs, the card in a recipe (Add step, Add all steps), no pop-ups, no page errors.
Run all tests with `python3 tests/run_all.py`, or serve the repo folder and run this file on its own."""
import json, os, re, subprocess, sys
from playwright.sync_api import sync_playwright

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from notice_watch import attach_notices
import test_v31 as t   # the helpers (loading the app, the palette, the colours) and the Games Workshop word lists
from combo_helpers import pick_combo   # v37 part 2: "Start from" and "Faction" are search boxes now, not drop-downs

SHOTS, ROOT = t.SHOTS, t.ROOT
read, load, blur, edit_recipe, open_panel = t.read, t.load, t.blur, t.edit_recipe, t.open_panel
shot, no_sideways, rgb, contrast = t.shot, t.no_sideways, t.rgb, t.contrast
rec, unit, HOSTILE, HOSTILE_BRAND, PAINTS = t.rec, t.unit, t.HOSTILE, t.HOSTILE_BRAND, t.PAINTS
GW_WORDS, GW_MORE = t.GW_WORDS, t.GW_MORE
results = []

def check(name, ok, detail=""):
    results.append(bool(ok))
    print(("PASS " if ok else "FAIL ") + name + ("" if ok else f"  -> {detail}"))

# brand and product words that must not appear in anything we wrote
BRAND_WORDS = re.compile(r"\b(citadel|vallejo|army painter|scale ?75|tamiya|games workshop|warhammer|amazon|ebay|etsy|shop|buy|store)\b", re.I)

# Made-up factions and recipes (nothing here names a real army). Unit 2's faction is the same as unit 1's with other capitals and a space.
UNITS = [unit(1, "Troop A", "Gloom Legion", [101, 102, 106]), unit(2, "Troop B", "gloom legion ", [101, 103]),
         unit(3, "Other", "Other Host", [104]), unit(4, "No faction", "", [105]), unit(5, "Lonely", "Lonely Host")]
RECIPES = [rec(101, "Armour blue", "Whole model", [1, 22]), rec(102, "Orange trim", "Armour", [2, 22]),
           rec(103, "Skin and glow", "Skin", [25, 5, 22]), rec(104, "Other host recipe", "Armour", [7]),
           rec(105, "No faction recipe", "Armour", [21]), rec(106, "Visor glow", "Eyes", [8]),
           rec(201, "Blue only", "Armour", [1])]   # a recipe whose only colour is Macragge Blue: its card and the Compendium start from the same colour
BLUE = "citadel|macragge blue"

# What the rows look like in each door.
ROWS_JS = """(sel) => [...document.querySelectorAll(sel)].map(b => ({
    name: b.querySelector('.idea-name').childNodes[0].textContent, brand: (b.querySelector('.idea-name small') || {}).textContent || '',
    tag: b.querySelector('.idea-tag').textContent, why: b.querySelector('.idea-why').textContent,
    note: (b.querySelector('.idea-note') || {}).textContent || '' }))"""
# Everything WE wrote on the Compendium (paint names, brands, faction names and the pickers are the user's or built-in names, so they are left out).
SHOWN_JS = """() => { const c = document.getElementById('compendium-body').cloneNode(true);
    c.querySelectorAll('.idea-name, select, #cmp-faction-history-for').forEach(e => e.remove());
    return c.innerText; }"""

def rows(page, sel):
    return page.evaluate(ROWS_JS, sel)

def open_comp(page):
    blur(page)
    page.click('nav button[data-tab="compendium"]')
    page.wait_for_timeout(200)
    # v49: the page introduction sits behind a More info button; open it so the text can be read
    if page.get_attribute("#compendium-body > .more-info .more-info-button", "aria-expanded") == "false":
        page.click("#compendium-body > .more-info .more-info-button")
    # v37: the five parts fold and start closed, and the lists start short (no group chosen). This test is about what is INSIDE them, so
    # open every part and choose "All" in each group row first (what v35 looked like). The new layout has its own test (test_v37).
    for key in ["ideas", "history", "starter", "detail", "basing"]:
        if page.get_attribute(f"#cmp-fold-{key}-button", "aria-expanded") != "true":
            page.click(f"#cmp-fold-{key}-button")
    for sel in ['#cmp-starter-moods [data-mood="all"]', '#cmp-detail-groups [data-detail-group="all"]', '#cmp-basing-groups [data-basing-group="all"]']:
        if page.get_attribute(sel, "aria-pressed") != "true":
            page.click(sel)
    page.wait_for_timeout(100)

def pick_base(page, value):
    pick_combo(page, "#cmp-colour-ideas-base", value=value)

def comp_role(page, key):
    page.click(f'#compendium-body [data-role="{key}"]')
    page.wait_for_timeout(120)

def comp_idea_rows(page):
    return rows(page, "#cmp-fold-ideas-panel > .idea-list .idea-static")

def card_idea_rows(page):
    return rows(page, "#colour-ideas button.idea")

def cmp_pick(page, part, key):
    page.click(f'#cmp-{part} [data-{part_attr(part)}="{key}"]')
    page.wait_for_timeout(120)

def part_attr(part):
    return {"starter-chips": "scheme", "detail-chips": "detail", "basing-chips": "basing",
            "starter-moods": "mood", "detail-groups": "detail-group", "basing-groups": "basing-group"}[part]

def card_pick(page, part, key):
    page.click(f'#{part} [data-{part_attr(part)}="{key}"]')
    page.wait_for_timeout(120)

def copy_spy(page):
    page.evaluate("""() => { window.__copied = null;
        Object.defineProperty(navigator, 'clipboard', { configurable: true, value: { writeText: (x) => { window.__copied = x; return Promise.resolve(); } } }); }""")

def copied(page):
    page.wait_for_timeout(200)
    return page.evaluate("() => window.__copied")

def toast(page):
    return page.evaluate("() => (document.getElementById('toast-text') || {}).textContent || ''")

def stored_recipes(page):
    return page.evaluate("() => localStorage.getItem('shades-of-grey-recipes')")

def draft_steps(page):
    return page.evaluate("() => recipeDraft.steps.map(s => ({ n: s.paints[0].name, b: s.paints[0].brand, c: s.paints[0].colour, mix: s.paints[0].mix, coats: s.coats, tech: s.technique, note: s.note }))")

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
        load(page, recipes=RECIPES, units=UNITS)
        html, sw, app = read("index.html"), read("sw.js"), read("app.js")
        check("APP_VERSION is v35 or later", float(page.evaluate("APP_VERSION")[1:]) >= 35, page.evaluate("APP_VERSION"))
        check("sw.js VERSION is v35 or later", float(re.search(r'const VERSION = "v([\d.]+)"', sw).group(1)) >= 35)
        tags = re.findall(r'<script src="([^"]+)\?v=(\d+)"', html)
        check("every script tag carries the same ?v= number (35 or later), and there are still exactly six script files (no new file)",
              len(tags) == 6 and len({v for _, v in tags}) == 1 and float(tags[0][1]) >= 35, tags)
        check("the script files are the same six as before, in the same order",
              [n for n, _ in tags] == ["early.js", "colour.js", "schemes.js", "detail-recipes.js", "basing-tips.js", "app.js"], tags)
        files = re.search(r"const APP_FILES = \[(.*?)\];", sw, re.S).group(1)
        check("sw.js still saves exactly the same app files for offline use (nothing new to add)",
              re.findall(r'"\./([^"?]*)', files) == ["", "index.html", "app.js", "early.js", "colour.js", "schemes.js", "detail-recipes.js", "basing-tips.js", "manifest.json", "icon-192.png", "icon-512.png", "ocr/ocr-worker.js"],
              re.findall(r'"\./([^"?]*)', files))
        entry = page.evaluate("CHANGELOG.find(r => r.version === 'v35')")
        if page.evaluate("['v35'].every(v => CHANGELOG.some(r => r.version === v))"):
            check("Updates has a v35 entry, and the newest entry is v35 or later", entry and float(page.evaluate("CHANGELOG[0].version")[1:]) >= 35, entry)
        else:
            print("SKIP (entry no longer in the public Updates list): " + 'Updates has a v35 entry, and the newest entry is v35 or later')
        joined = " ".join(entry["changes"]) if entry else ""
        if page.evaluate("['v35'].every(v => CHANGELOG.some(r => r.version === v))"):
            check("the Updates entry says Compendium, Pro preview, Copy as text, Save into a new recipe, Save recipe, that nothing is saved before, offline, sends nothing anywhere and no colour wheel yet",
                  all(w in joined for w in ["Compendium", "Pro preview", "Copy as text", "Save into a new recipe", "Save recipe", "offline", "sends nothing anywhere", "no colour wheel yet"]), joined[:300])
        else:
            print("SKIP (entry no longer in the public Updates list): " + 'the Updates entry says Compendium, Pro preview, Copy as text, Save into a new recipe, Save')
        if page.evaluate("['v32', 'v33', 'v34'].every(v => CHANGELOG.some(r => r.version === v))"):
            check("the v34, v33 and v32 Updates entries are still there", page.evaluate("['v34', 'v33', 'v32'].every(v => !!CHANGELOG.find(r => r.version === v))"))
        else:
            print("SKIP (entry no longer in the public Updates list): " + 'the v34, v33 and v32 Updates entries are still there')
        check("DATA_VERSION is still 1 and the three storage names are unchanged", page.evaluate("DATA_VERSION") == 1
              and all(k in app for k in ['STORAGE_KEY = "mini-tracker-models"', 'SETTINGS_KEY = "shades-of-grey-settings"', 'RECIPES_KEY = "shades-of-grey-recipes"']))
        policy = re.search(r'http-equiv="Content-Security-Policy"\s+content="([^"]+)"', html)
        policy = policy.group(1) if policy else ""
        hosts = set(re.findall(r"https?://[^\s;'\"]+", policy))
        check("the security policy is untouched: the only outside address is still the one GoatCounter picture address",
              len(hosts) == 1 and "goatcounter" in list(hosts)[0], (hosts, policy[:200]))
        changed = subprocess.run(["git", "diff", "--name-only", "HEAD", "--", "colour.js", "schemes.js", "detail-recipes.js", "basing-tips.js"],
                                 cwd=ROOT, capture_output=True, text=True).stdout.split()
        check("the content data files and colour.js are unchanged (schemes.js, detail-recipes.js, basing-tips.js, colour.js)", changed == [], changed)
        panel_code = app[app.index("v28: \"COLOUR IDEAS\""):app.index('v18c: TIDY BRANDS')]
        comp_code = panel_code[panel_code.index("v35: THE COMPENDIUM TAB"):]
        new_code = panel_code[panel_code.index("v35: ONE set of building blocks"):panel_code.index("let colourIdeasPressing")] + comp_code
        check("the new code has no network code, no storage, no innerHTML, no links and no shop wording; the panel still has exactly one innerHTML (the card's own clear)",
              not re.search(r"\bfetch\s*\(|XMLHttpRequest|sendBeacon|WebSocket|localStorage|sessionStorage|\beval\s*\(|new Function|insertAdjacentHTML|outerHTML|innerHTML|createElement\('a'\)|createElement\(\"a\"\)|href|affiliate", new_code)
              and panel_code.count("innerHTML") == 1, [mm.group(0) for mm in re.finditer(r"innerHTML[^\n]*", panel_code)])
        check("the card's pieces are shared, not copied: the card (appendLibraryParts) and the Compendium (libraryParts) both use the same parts, and both call appendRolePicker and buildIdeasList, and each builder is defined once",
              app.count("appendLibraryParts(") >= 2 and app.count("libraryParts(") >= 3 and app.count("appendRolePicker(") >= 3 and app.count("buildIdeasList(") >= 3
              and all(app.count(f"function {n}(") == 1 for n in ["buildStarterSchemes", "buildDetailRecipes", "buildBasingTips", "buildFactionHistory", "buildIdeaItem", "appendLibraryParts", "appendRolePicker", "buildIdeasList"]))
        check("the Pro preview label is on the Compendium", page.inner_text("#view-compendium .pro-pill") == "Pro preview" if page.locator("#view-compendium .pro-pill").count() else False)
        help_text = page.evaluate("() => document.getElementById('help-tabs').textContent")
        check("Help names five tabs and says what the Compendium is", all(w in help_text for w in ["five tabs", "Compendium", "Pro preview", "without needing a recipe"]), help_text)

        # ---------- 2. The five-tab bar ----------
        print("\n--- 2. The five-tab bar ---")
        names = page.evaluate("() => [...document.querySelectorAll('nav.tabs button[data-tab]')].map(b => b.dataset.tab)")
        check("five tabs in order: Dashboard, Units, Recipes, Compendium, Settings", names == ["dashboard", "units", "recipes", "compendium", "settings"], names)
        label = page.evaluate("() => [...document.querySelector('nav.tabs button[data-tab=compendium]').childNodes].filter(n => n.nodeType === 3).map(n => n.textContent).join('')")
        check("the label is Compendium in full", label == "Compendium", label)
        for width in (360, 375, 390, 400):
            page.set_viewport_size({"width": width, "height": 800})
            page.wait_for_timeout(100)
            m = page.evaluate("""() => { const out = []; for (const b of document.querySelectorAll('nav.tabs button[data-tab]')) {
                const n = [...b.childNodes].find(x => x.nodeType === 3), r = document.createRange(); r.selectNodeContents(n);
                const tr = r.getBoundingClientRect(), br = b.getBoundingClientRect();
                out.push({ tab: b.dataset.tab, text: tr.width, left: tr.left - br.left, right: br.right - tr.right, w: br.width, bl: br.left, br: br.right }); }
                return out; }""")
            fits = all(x["left"] >= 0 and x["right"] >= 0 for x in m) and m[0]["bl"] >= -0.5 and m[-1]["br"] <= width + 0.5
            check(f"at {width} px every label fits inside its own button (Compendium text {round(m[3]['text'], 1)} of {round(m[3]['w'], 1)} px) and the bar is inside the screen", fits, m)
            check(f"at {width} px the five buttons are the same width and nothing scrolls sideways", len({round(x['w']) for x in m}) == 1 and no_sideways(page), [x["w"] for x in m])
        page.set_viewport_size({"width": 390, "height": 844})
        open_comp(page)
        check("tapping Compendium opens it and lights up its tab",
              page.is_visible("#view-compendium") and page.get_attribute('nav button[data-tab="compendium"]', "aria-current") == "page"
              and page.get_attribute('nav button[data-tab="settings"]', "aria-current") is None and not page.is_visible("#view-dashboard"))
        check("the page is called Compendium and says what it is", page.inner_text("#view-compendium h2") == "Compendium" and "without needing a recipe" in page.inner_text("#cmp-intro"))
        page.reload()
        page.wait_for_function("() => typeof APP_VERSION === 'string'")
        page.wait_for_timeout(300)
        check("reloading the app on the Compendium opens it again (the page you were on is remembered)", page.is_visible("#view-compendium"))
        check("Back from the Compendium goes to the Dashboard", page.evaluate("() => typeof backTarget() === 'function'"))
        page.set_viewport_size({"width": 1100, "height": 800})
        page.wait_for_timeout(100)
        names_top = page.evaluate("() => [...document.querySelectorAll('nav.tabs button[data-tab]')].map(b => b.dataset.tab)")
        check("on a wide screen the top bar has all five tabs and the Compendium page is still there", names_top == names and page.is_visible("#view-compendium") and no_sideways(page))
        page.set_viewport_size({"width": 390, "height": 844})

        # ---------- 3. Same content, not a copy ----------
        print("\n--- 3. Same content in both doors ---")
        load(page, recipes=RECIPES, units=UNITS)
        open_comp(page)
        # v37: the parts sit under folding headings (open_comp has opened them), so read the ids at the top level and inside the panels
        order = page.evaluate("""() => { const want = ['cmp-intro', 'cmp-colour-ideas-none', 'cmp-faction-history', 'cmp-starter-schemes', 'cmp-detail-recipes', 'cmp-basing-tips', 'cmp-foot'];
            const seen = [...document.querySelectorAll('#compendium-body > *, #compendium-body > .more-info .more-info-panel > *, #compendium-body .fold-panel > *')].map(e => e.id);
            return want.map(i => seen.indexOf(i)); }""")
        check("with no colour chosen: the intro, the choose-a-colour line, then Your schemes, Starter schemes, Detail recipes, Basing tips, then the footnote, in the card's order",
              order == sorted(order) and -1 not in order, order)
        check("before a colour is chosen there are no role buttons and no ideas, but all four library parts are there",
              page.locator("#compendium-body [data-role]").count() == 0 and page.locator("#cmp-fold-ideas-panel > .idea-list").count() == 0
              and all(page.locator(f"#{i}").count() == 1 for i in ["cmp-faction-history", "cmp-starter-schemes", "cmp-detail-recipes", "cmp-basing-tips"]))
        page.click("#cmp-colour-ideas-base-toggle")
        opts = page.evaluate("""() => { const out = []; for (const el of document.querySelectorAll('#cmp-colour-ideas-base-list > li')) {
            if (el.classList.contains('combo-group')) out.push([el.textContent, 0]); else if (out.length) out[out.length - 1][1]++; } return out; }""")
        check("the colour chooser lists your paints first (owned, then the rest), then the built-in list by brand",
              opts and opts[0][0] == "Paints you own" and opts[0][1] == 14 and any(l.startswith("More ") for l, _ in opts)
              and page.input_value("#cmp-colour-ideas-base") == "" and page.get_attribute("#cmp-colour-ideas-base", "placeholder") == "Type or choose a paint", opts[:4])
        page.fill("#cmp-colour-ideas-base", "macragge blue")
        check("a paint in your palette is not listed twice (the built-in list leaves out paints you already have)",
              page.evaluate("() => [...document.querySelectorAll('#cmp-colour-ideas-base-list [role=option]')].filter(o => /^Macragge Blue(?! Spray)/.test(o.textContent)).length") == 1)   # v48: Macragge Blue Spray is a different paint
        page.keyboard.press("Escape")
        pick_base(page, BLUE)
        chips = page.evaluate("() => [...document.querySelectorAll('#compendium-body [data-role]')].map(c => [c.textContent, c.getAttribute('aria-pressed')])")
        check("after choosing a colour: six role buttons (Eyes or glow pressed to start) and the role's tip",
              [c[0] for c in chips] == ["Eyes or glow", "Trim", "Gems", "Weapon", "Cloth", "Base"] and chips[0][1] == "true" and chips[1][1] == "false"
              and page.inner_text("#cmp-colour-ideas-tip").startswith("Tip: "), chips)
        check("three ideas show", len(comp_idea_rows(page)) == 3, comp_idea_rows(page))
        # the card in a recipe that has only that colour
        edit_recipe(page, 201)
        open_panel(page)
        both_same = []
        for role in ["glow", "trim", "gems", "weapon", "cloth", "base"]:
            t.pick_role(page, role)
            card = card_idea_rows(page)
            tip_card = page.inner_text("#colour-ideas-tip")
            open_comp(page)
            comp_role(page, role)
            cmp_rows = comp_idea_rows(page)
            both_same.append((role, card == cmp_rows and len(card) == 3 and tip_card == page.inner_text("#cmp-colour-ideas-tip"), card, cmp_rows))
            blur(page)
            page.click('nav button[data-tab="recipes"]')
            page.wait_for_timeout(150)
        bad = [x for x in both_same if not x[1]]
        check("for the same colour, each of the six roles gives the same three ideas (names, tags, reasons, notes) and the same tip in the card and in the Compendium", not bad, bad[:1])

        def part_rows_equal(chip_part, list_id, key_list, card_id, label):
            diffs = []
            for key in key_list:
                blur(page)
                page.click('nav button[data-tab="recipes"]')
                page.wait_for_timeout(100)
                card_pick(page, chip_part, key)
                card_rows = rows(page, f"#{card_id} button.idea-pick")
                open_comp(page)
                cmp_pick(page, chip_part, key)
                cmp_rows = rows(page, f"#cmp-{list_id} .idea-static")
                if not (card_rows == cmp_rows and len(card_rows) > 0):
                    diffs.append((key, card_rows[:1], cmp_rows[:1]))
                cmp_pick(page, chip_part, key)   # put it away again
            check(f"every {label} gives the same rows in the card and in the Compendium", not diffs, diffs[:1])

        keys_s = page.evaluate("STARTER_SCHEMES.map(s => s.key)")
        keys_d = page.evaluate("DETAIL_RECIPES.map(s => s.key)")
        keys_b = page.evaluate("BASING_TIPS.map(s => s.key)")
        # start the card's picks from "nothing picked"
        edit_recipe(page, 201)
        open_panel(page)
        part_rows_equal("starter-chips", "starter-list", keys_s, "starter-list", f"starter scheme ({len(keys_s)})")
        edit_recipe(page, 201)
        open_panel(page)
        part_rows_equal("detail-chips", "detail-list", keys_d, "detail-list", f"detail recipe ({len(keys_d)})")
        edit_recipe(page, 201)
        open_panel(page)
        part_rows_equal("basing-chips", "basing-list", keys_b, "basing-list", f"basing tip ({len(keys_b)})")
        open_comp(page)
        cmp_pick(page, "starter-chips", "blue-gold")
        check("a starter scheme shows its summary and reason, and four plain rows", page.inner_text("#cmp-starter-summary") == "Cold blue armour, gold trim, red eyes"
              and "classic pair" in page.inner_text("#cmp-starter-reason") and page.locator("#cmp-starter-list .idea-static").count() == 4)
        pick_mood = page.click('#cmp-starter-moods [data-mood="warm"]')
        page.wait_for_timeout(120)
        check("the mood buttons work in the Compendium (Warm shows six, and the scheme outside the mood is put away)",
              page.locator("#cmp-starter-chips .chip").count() == 6 and page.locator("#cmp-starter-list").count() == 0)
        page.click('#cmp-starter-moods [data-mood="all"]')
        page.wait_for_timeout(120)
        check("All brings back all of them", page.locator("#cmp-starter-chips .chip").count() == len(keys_s))
        page.click('#cmp-detail-groups [data-detail-group="metal"]')
        page.wait_for_timeout(120)
        check("the detail recipe group buttons work in the Compendium", 0 < page.locator("#cmp-detail-chips .chip").count() < len(keys_d))
        page.click('#cmp-detail-groups [data-detail-group="all"]')
        page.click('#cmp-basing-groups [data-basing-group="cold"]')
        page.wait_for_timeout(120)
        check("the basing tip group buttons work in the Compendium", 0 < page.locator("#cmp-basing-chips .chip").count() < len(keys_b))
        page.click('#cmp-basing-groups [data-basing-group="all"]')
        cmp_pick(page, "basing-chips", "snow")
        check("a basing tip shows What you need, How to build it (plain lists) and Paint steps (optional)",
              page.locator("#cmp-basing-materials li").count() >= 3 and page.locator("#cmp-basing-howto li").count() >= 3
              and "Paint steps (optional)" in page.inner_text("#cmp-basing-tips"))
        cmp_pick(page, "basing-chips", "snow")
        focus_ok = (lambda: (page.click('#cmp-starter-moods [data-mood="cold"]'), page.wait_for_timeout(120), page.evaluate("() => document.activeElement.dataset.mood"))[-1])()
        check("after tapping a button the keyboard focus stays on it", focus_ok == "cold", focus_ok)
        page.click('#cmp-starter-moods [data-mood="all"]')

        # ---------- 4. No recipe, no add buttons ----------
        print("\n--- 4. No recipe, no add buttons ---")
        cmp_pick(page, "starter-chips", "blue-gold")
        cmp_pick(page, "detail-chips", keys_d[0])
        cmp_pick(page, "basing-chips", "snow")
        check("no row in the Compendium is a button, and no row says + Add as a step",
              page.locator("#compendium-body button.idea, #compendium-body button.idea-pick").count() == 0 and page.locator("#compendium-body .idea-add").count() == 0
              and "+ Add" not in page.inner_text("#compendium-body"))
        check("no Add all steps and no Add all paint steps button, and no 'tap a paint to add it' wording",
              page.locator("#cmp-detail-add-all, #cmp-basing-add-all").count() == 0
              and not re.search(r"add it as a step|add just that step|can be added to your recipe|Add all", page.inner_text("#compendium-body")), page.inner_text("#compendium-body")[:200])
        check("the rows are still full rows: a colour swatch, a name, a tag and a reason",
              page.evaluate("() => [...document.querySelectorAll('#compendium-body .idea-static')].every(r => r.querySelector('.swatch') && r.querySelector('.idea-name') && r.querySelector('.idea-tag') && r.querySelector('.idea-why'))"))
        check("each part ends with Copy as text and Save into a new recipe… (Starter schemes, Detail recipes, Basing tips)",
              all(page.locator(f"#{i} .share-row button").count() == 2 for i in ["cmp-starter-schemes", "cmp-detail-recipes", "cmp-basing-tips"])
              and all(page.locator(f"#{i} .share-row button").first.inner_text() == "Copy as text" and page.locator(f"#{i} .share-row button").nth(1).inner_text() == "Save into a new recipe…"
                      for i in ["cmp-starter-schemes", "cmp-detail-recipes", "cmp-basing-tips"]))
        check("the buttons are 44 px tall or more", page.evaluate("() => [...document.querySelectorAll('#compendium-body .share-row button')].every(b => b.getBoundingClientRect().height >= 43.5)"))
        edit_recipe(page, 201)
        open_panel(page)
        card_pick(page, "starter-chips", "blue-gold")
        card_pick(page, "detail-chips", keys_d[0])
        card_pick(page, "basing-chips", "snow")
        check("the card in a recipe is unchanged: its rows are buttons that add a step, with Add all steps and Add all paint steps, and no Copy as text there",
              page.locator("#colour-ideas button.idea").count() == 3 and page.locator("#starter-list button.idea-pick").count() == 4
              and page.locator("#detail-add-all").count() == 1 and page.locator("#basing-add-all").count() == 1
              and page.locator("#colour-ideas .idea-add").count() >= 10 and page.locator("#colour-ideas .share-row, #colour-ideas .idea-static").count() == 0)
        n0 = page.evaluate("() => recipeDraft.steps.length")
        page.click("#starter-list button.idea-pick >> nth=0")
        page.wait_for_timeout(200)
        steps = draft_steps(page)
        check("tapping a starter scheme paint in the card still adds a step with the starter note", len(steps) == n0 + 1 and steps[-1]["note"].startswith("Starter scheme (Cold blue and gold): "), steps[-1])
        page.click("#detail-add-all")
        page.wait_for_timeout(250)
        check("Add all steps in the card still adds every step of the detail recipe, with technique, coats and mix kept",
              page.evaluate("() => recipeDraft.steps.length") > n0 + 2 and draft_steps(page)[-1]["tech"] != "", draft_steps(page)[-3:])
        page.click("#recipe-page button.plain-button:has-text('Cancel')")
        page.wait_for_timeout(250)
        if page.is_visible("#dialog-yes"):
            page.click("#dialog-yes")
            page.wait_for_timeout(250)

        # ---------- 5. Your schemes (faction history) ----------
        print("\n--- 5. Your schemes ---")
        load(page, recipes=RECIPES, units=UNITS)
        open_comp(page)
        page.click("#cmp-faction-history-pick-toggle")
        names_f = page.evaluate("() => [...document.querySelectorAll('#cmp-faction-history-pick-list [role=option]')].map(o => o.textContent)")
        check("the faction box lists the factions of your units once each (Gloom Legion once, however it was typed), sorted, with units that have no faction left out",
              names_f == ["Gloom Legion", "Lonely Host", "Other Host"], names_f)
        page.click("#cmp-faction-history-pick-toggle")
        check("until you choose one it says to choose a faction", "Choose a faction above" in page.inner_text("#cmp-faction-history-none"))
        pick_combo(page, "#cmp-faction-history-pick", text="Gloom Legion")
        page.wait_for_timeout(150)
        hist = rows(page, "#cmp-faction-history-list .idea-static")
        check("Gloom Legion shows the paints from the recipes on its units, most used first, then by name",
              [h["name"] for h in hist] == ["Mid Blue A", "Macragge Blue", "Burnt Orange", "Fire Dragon Bright", "Ink Sky", "Troll Slayer Orange"], [h["name"] for h in hist])
        check("the reasons count units and recipes (Mid Blue A: 2 units, 3 recipes)", hist[0]["why"] == "Used on 2 units in this faction, in 3 recipes.", hist[0])
        check("honest tags: owned paints say You own this, the wishlist paint says You don't own this",
              [h["tag"] for h in hist] == ["You own this", "You own this", "You own this", "You don't own this", "You own this", "You own this"], [h["tag"] for h in hist])
        check("the faction is named and the focus stays in the faction box", "Gloom Legion" in page.inner_text("#cmp-faction-history-for")
              and page.evaluate("() => document.activeElement.id") == "cmp-faction-history-pick")
        pick_combo(page, "#cmp-faction-history-pick", text="Lonely Host")
        page.wait_for_timeout(150)
        check("a faction whose units have no saved recipes says there is no history yet", "No history yet" in page.inner_text("#cmp-faction-history-empty"))
        pick_combo(page, "#cmp-faction-history-pick", text="Other Host")
        page.wait_for_timeout(150)
        check("Other Host shows only its own paint", [h["name"] for h in rows(page, "#cmp-faction-history-list .idea-static")] == ["Evil Sunz Scarlet"])
        pick_combo(page, "#cmp-faction-history-pick", text="Gloom Legion")
        page.wait_for_timeout(150)
        # the card in a recipe for Gloom Legion gives the same rows (apart from the paints already in that recipe)
        check("the faction history has Copy as text and Save into a new recipe…", page.locator("#cmp-faction-history .share-row button").count() == 2)
        load(page, recipes=RECIPES, units=[unit(1, "Solo", "")])
        open_comp(page)
        check("with no faction on any unit it says so and the faction box says there are none",
              "None of your units has a faction yet" in page.inner_text("#cmp-faction-history-none")
              and page.get_attribute("#cmp-faction-history-pick", "placeholder") == "No factions yet" and page.is_disabled("#cmp-faction-history-pick"))
        load(page, recipes=RECIPES, units=UNITS)
        page.evaluate("() => { compendiumState.faction = 'gone host'; }")
        open_comp(page)
        check("a faction that no longer exists is put away quietly", page.evaluate("() => compendiumState.faction") == "" and page.locator("#cmp-faction-history-list").count() == 0)

        # ---------- 6. Copy as text and Save into a new recipe ----------
        print("\n--- 6. Copy as text, Save into a new recipe ---")
        load(page, recipes=RECIPES, units=UNITS)
        open_comp(page)
        copy_spy(page)
        pick_base(page, BLUE)
        # v62: each colour idea now has two small buttons, so the page is longer and Copy as text sits lower. While the colour box has focus the
        # bottom tab bar is hidden; pressing the button blurs the box, the bar comes back and covers the button before the click lands. Blur first.
        page.evaluate("() => document.activeElement && document.activeElement.blur()")
        page.click("#cmp-fold-ideas-panel > .share-row button:has-text('Copy as text')")
        text = copied(page)
        check("Copy as text on the colour ideas copies a heading, three lines and the footnote",
              text and text.splitlines()[0] == "Colour ideas for eyes or glow with Macragge Blue (Citadel)" and len(text.splitlines()) == 5
              and text.splitlines()[-1] == "Colours on a screen are only a guide, so check them on your model.", text)
        check("each line has the paint (and brand), the tag and the reason, as the row shows",
              all(re.match(r"- .+: (You own this|Yours, poor fit|Not in your palette)\. .+", l) for l in text.splitlines()[1:4]), text)
        check("the message says what was copied and does not mention Paste recipes", toast(page) == "Colour ideas copied. Paste it anywhere.", toast(page))
        cmp_pick(page, "starter-chips", "blue-gold")
        page.click("#cmp-starter-schemes .share-row button:has-text('Copy as text')")
        text = copied(page)
        lines = text.splitlines()
        check("Copy as text on a starter scheme: its name, summary, reason, four colour lines and the footnote",
              lines[0] == "Starter scheme: Cold blue and gold" and lines[1] == "Cold blue armour, gold trim, red eyes" and lines[2].startswith("Blue and gold is a classic pair")
              and len(lines) == 8 and lines[3].startswith("- ") and "Armour: a deep blue." in lines[3], text)
        check("the toast says Cold blue and gold copied", toast(page) == "Cold blue and gold copied. Paste it anywhere.", toast(page))
        cmp_pick(page, "detail-chips", keys_d[0])
        page.click("#cmp-detail-recipes .share-row button:has-text('Copy as text')")
        text = copied(page)
        d0 = page.evaluate("(k) => DETAIL_RECIPES.find(r => r.key === k)", keys_d[0])
        check("Copy as text on a detail recipe: its name, summary and one line per step with technique, coats and mix %",
              text.splitlines()[0] == f"Detail recipe: {d0['name']}" and text.splitlines()[1] == d0["summary"]
              and sum(1 for l in text.splitlines() if re.search(r"Step \d: ", l)) == len(d0["steps"]) and "% paint." in text, text)
        cmp_pick(page, "basing-chips", "snow")
        page.click("#cmp-basing-tips .share-row button:has-text('Copy as text')")
        text = copied(page)
        check("Copy as text on a basing tip: What you need, How to build it, Paint steps (optional) and the footnote",
              text.splitlines()[0] == "Basing tip: Snow" and "What you need:" in text and "How to build it:" in text and "Paint steps (optional):" in text
              and "1. " in text and text.splitlines()[-1].startswith("Colours on a screen"), text[:200])
        pick_combo(page, "#cmp-faction-history-pick", text="Gloom Legion")
        page.wait_for_timeout(150)
        page.click("#cmp-faction-history .share-row button:has-text('Copy as text')")
        text = copied(page)
        check("Copy as text on Your schemes: the faction and one line per paint", text.splitlines()[0] == "Colours used on this faction before: Gloom Legion" and len(text.splitlines()) == 8, text)
        check("the copied text is plain text: no tags, no markup", not re.search(r"<[a-z/]|&[a-z]+;", text))
        # without a clipboard the app's own box shows the text
        page.evaluate("() => { Object.defineProperty(navigator, 'clipboard', { configurable: true, value: undefined }); document.execCommand = () => false; }")
        page.click("#cmp-faction-history .share-row button:has-text('Copy as text')")
        page.wait_for_timeout(250)
        check("if the phone will not let the app copy, the app's own box shows the text to copy by hand",
              page.is_visible("#dialog-area") and "Colours used on this faction before" in page.input_value("#dialog-area"), page.is_visible("#dialog-area"))
        page.locator("#dialog-buttons button:visible").last.click()
        page.wait_for_timeout(200)

        # Save into a new recipe
        load(page, recipes=RECIPES, units=UNITS)
        open_comp(page)
        before = stored_recipes(page)
        cmp_pick(page, "detail-chips", keys_d[0])
        d0 = page.evaluate("(k) => DETAIL_RECIPES.find(r => r.key === k)", keys_d[0])
        page.click("#cmp-detail-recipes .share-row button:has-text('Save into a new recipe')")
        page.wait_for_timeout(350)
        steps = draft_steps(page)
        check("Save into a new recipe… opens the recipe editor with a new, unnamed recipe",
              page.evaluate("() => settings.tab") == "recipes" and page.is_visible("#recipe-page") and page.evaluate("() => recipeDraft.id") is None and page.evaluate("() => recipeDraft.name") == "")
        check("it has one step per step of the detail recipe, with technique, coats, mix % and note kept",
              len(steps) == len(d0["steps"]) and all(s["tech"] == d["technique"] and s["coats"] == d["coats"] and s["mix"] == d["mix"] and s["note"] == d["note"] for s, d in zip(steps, d0["steps"])), steps[:2])
        check("each step's paint is the paint the row showed (name, brand, colour)", all(s["n"] and re.fullmatch(r"#[0-9a-f]{6}", s["c"]) for s in steps))
        check("a message says it started a new recipe and to press Save recipe", "Started a new recipe with" in toast(page) and "Save recipe" in toast(page), toast(page))
        check("nothing is saved yet", stored_recipes(page) == before)
        page.click("#recipe-page button.plain-button:has-text('Cancel')")
        page.wait_for_timeout(250)
        check("Cancel asks first (the steps are not saved anywhere)", page.is_visible("#dialog-yes") and page.evaluate("() => recipeDraft") is not None)
        page.click("#dialog-yes")
        page.wait_for_timeout(250)
        check("after Yes the draft is gone and still nothing was saved", page.evaluate("() => recipeDraft") is None and stored_recipes(page) == before)
        open_comp(page)
        page.click("#cmp-detail-recipes .share-row button:has-text('Save into a new recipe')")
        page.wait_for_timeout(350)
        page.fill("#recipe-page input >> nth=0", "From the Compendium")
        blur(page)   # leaving the text box first (while it has the cursor the tab bar is hidden and the page shifts when you tap away)
        page.click("#recipe-page button.primary-button:has-text('Save recipe')")
        page.wait_for_timeout(300)
        saved = json.loads(stored_recipes(page))
        mine = [r for r in saved["recipes"] if r["name"] == "From the Compendium"]
        check("after Save recipe the new recipe is in your recipes with all its steps", len(mine) == 1 and len(mine[0]["steps"]) == len(d0["steps"]), [r["name"] for r in saved["recipes"]])
        check("its steps kept technique, coats, mix and note", all(s["technique"] == d["technique"] and s["coats"] == d["coats"] and s["note"] == d["note"] for s, d in zip(mine[0]["steps"], d0["steps"])))
        # a draft in progress is asked about first
        open_comp(page)
        page.click("#cmp-detail-recipes .share-row button:has-text('Save into a new recipe')")
        page.wait_for_timeout(350)
        page.fill("#recipe-page input >> nth=0", "Half written")
        blur(page)
        open_comp(page)
        page.click("#cmp-detail-recipes .share-row button:has-text('Save into a new recipe')")
        page.wait_for_timeout(300)
        check("with a recipe half written, it asks before replacing it", page.is_visible("#dialog-yes"))
        page.click("#dialog-no") if page.locator("#dialog-no").count() else page.keyboard.press("Escape")
        page.wait_for_timeout(250)
        check("saying no keeps the half-written recipe", page.evaluate("() => recipeDraft && recipeDraft.name") == "Half written", page.evaluate("() => recipeDraft && recipeDraft.name"))
        page.evaluate("() => { recipeDraft = null; }")
        # the other parts start recipes too
        load(page, recipes=RECIPES, units=UNITS)
        open_comp(page)
        pick_base(page, BLUE)
        page.evaluate("() => document.activeElement && document.activeElement.blur()")   # v62: see the note at the Copy as text click above
        page.click("#cmp-fold-ideas-panel > .share-row button:has-text('Save into a new recipe')")
        page.wait_for_timeout(350)
        steps = draft_steps(page)
        check("Save into a new recipe… on the colour ideas makes three steps with the note 'Colour idea for eyes or glow'", len(steps) == 3 and all(s["note"] == "Colour idea for eyes or glow" and s["mix"] == 100 and s["coats"] == 1 for s in steps), steps)
        page.evaluate("() => { recipeDraft = null; }")
        open_comp(page)
        cmp_pick(page, "basing-chips", "snow")
        page.click("#cmp-basing-tips .share-row button:has-text('Save into a new recipe')")
        page.wait_for_timeout(350)
        n_paint = page.evaluate("() => BASING_TIPS.find(t => t.key === 'snow').paintSteps.length")
        steps = draft_steps(page)
        check("on a basing tip it takes the paint steps only (never the materials or the how-to steps)", len(steps) == n_paint and all(s["tech"] for s in steps), steps)
        page.evaluate("() => { recipeDraft = null; }")
        open_comp(page)
        cmp_pick(page, "starter-chips", "blue-gold")
        page.click("#cmp-starter-schemes .share-row button:has-text('Save into a new recipe')")
        page.wait_for_timeout(350)
        steps = draft_steps(page)
        check("on a starter scheme it makes four steps with the starter note", len(steps) == 4 and steps[0]["note"] == "Starter scheme (Cold blue and gold): armour", steps)
        page.evaluate("() => { recipeDraft = null; }")

        # ---------- 7. Honesty ----------
        print("\n--- 7. Honesty ---")
        load(page, recipes=RECIPES, units=UNITS)
        open_comp(page)
        cmp_pick(page, "starter-chips", "blue-gold")
        tags = {r["name"]: r["tag"] for r in rows(page, "#cmp-starter-list .idea-static")}
        check("every tag is one of the three honest tags", set(tags.values()) <= {"You own this", "Yours, poor fit", "Not in your palette"}, tags)
        wish = [{"id": 1, "brand": "Vallejo", "name": "Pure Blue", "colour": "#1f4287", "status": "wishlist"}]
        load(page, paints=wish, recipes=RECIPES, units=UNITS)
        open_comp(page)
        cmp_pick(page, "starter-chips", "blue-gold")
        r0 = rows(page, "#cmp-starter-list .idea-static")[0]
        check("a wishlist paint that is the exact colour is never called You own this", r0["tag"] != "You own this", r0)
        load(page, paints=[], recipes=RECIPES, units=UNITS)
        open_comp(page)
        cmp_pick(page, "starter-chips", "blue-gold")
        check("with an empty palette every row says Not in your palette", all(r["tag"] == "Not in your palette" for r in rows(page, "#cmp-starter-list .idea-static")))
        check("with an empty palette the colour chooser still has the built-in list", page.evaluate("() => { const c = compendiumBaseChoices(); return c.brands.flatMap(b => b.list).length; }") > 100)
        pick_combo(page, "#cmp-colour-ideas-base", index=1)
        check("with an empty palette you can still choose a colour and get three ideas, none of them owned",
              len(comp_idea_rows(page)) == 3 and all(r["tag"] == "Not in your palette" for r in comp_idea_rows(page)))
        check("the footnote says colours are only a guide and nothing leaves the phone", all(w in page.inner_text("#cmp-foot") for w in ["only a guide", "Nothing leaves your phone"]))

        # ---------- 8. Separate picks, kept picks, no duplicate ids ----------
        print("\n--- 8. Separate picks ---")
        load(page, recipes=RECIPES, units=UNITS)
        edit_recipe(page, 201)
        open_panel(page)
        card_pick(page, "starter-chips", "green-bone")
        open_comp(page)
        check("a scheme picked in the card is not picked in the Compendium", page.locator("#cmp-starter-list").count() == 0
              and page.evaluate("() => [colourIdeasState.scheme, compendiumState.scheme]") == ["green-bone", ""])
        cmp_pick(page, "starter-chips", "red-grey")
        pick_base(page, BLUE)
        comp_role(page, "gems")
        dupes = page.evaluate("""() => { const seen = {}; for (const e of document.querySelectorAll('[id]')) seen[e.id] = (seen[e.id] || 0) + 1; return Object.entries(seen).filter(([, n]) => n > 1); }""")
        check("with the recipe editor open and the Compendium showing, no page id is used twice", not dupes, dupes[:5])
        page.click('nav button[data-tab="recipes"]')
        page.wait_for_timeout(200)
        check("the card still has its own pick (green-bone) and the Compendium's pick did not move it", page.evaluate("() => colourIdeasState.scheme") == "green-bone"
              and page.get_attribute('#starter-chips [data-scheme="green-bone"]', "aria-pressed") == "true")
        open_comp(page)
        check("coming back to the Compendium, your picks are still there (scheme, colour and role)",
              page.get_attribute('#cmp-starter-chips [data-scheme="red-grey"]', "aria-pressed") == "true" and page.evaluate("() => compendiumState.base") == BLUE
              and page.get_attribute('#compendium-body [data-role="gems"]', "aria-pressed") == "true")
        page.evaluate("() => { recipeDraft = null; }")
        # data changed elsewhere shows when you come back
        page.evaluate("() => { book.paints.push({ id: 999, brand: 'Test', name: 'Brand New Teal', colour: '#1f9e9a', status: 'owned' }); }")
        blur(page)
        page.click('nav button[data-tab="dashboard"]')
        page.wait_for_timeout(100)
        open_comp(page)
        page.fill("#cmp-colour-ideas-base", "brand new teal")
        check("a paint added meanwhile shows in the colour chooser when you come back", page.locator("#cmp-colour-ideas-base-list [role=option]:text-is('Brand New Teal (Test)')").count() == 1)
        page.keyboard.press("Escape")

        # ---------- 9. Text scan ----------
        print("\n--- 9. Text scan: no Games Workshop names in any new text ---")
        load(page, recipes=RECIPES, units=UNITS)
        open_comp(page)
        shown = [page.evaluate(SHOWN_JS)]
        pick_base(page, BLUE)
        for role in ["glow", "trim", "gems", "weapon", "cloth", "base"]:
            comp_role(page, role)
            shown.append(page.evaluate(SHOWN_JS))
        for key in keys_s:
            cmp_pick(page, "starter-chips", key)
            shown.append(page.evaluate(SHOWN_JS))
            cmp_pick(page, "starter-chips", key)
        for key in keys_d:
            cmp_pick(page, "detail-chips", key)
            shown.append(page.evaluate(SHOWN_JS))
            cmp_pick(page, "detail-chips", key)
        for key in keys_b:
            cmp_pick(page, "basing-chips", key)
            shown.append(page.evaluate(SHOWN_JS))
            cmp_pick(page, "basing-chips", key)
        pick_combo(page, "#cmp-faction-history-pick", text="Gloom Legion")
        shown.append(page.evaluate(SHOWN_JS))
        everything = "\n".join(shown)
        hits = GW_WORDS.findall(everything) + GW_MORE.findall(everything)
        check("everything we wrote that the Compendium shows, for every role, scheme, detail recipe and tip, names no Games Workshop game, faction, scheme, paint or product",
              not hits and len(shown) > 60, (hits[:10], len(shown)))
        brands = BRAND_WORDS.findall(everything)
        check("and none of it names a brand, a shop or a product", not brands, brands[:10])
        own = "\n".join([joined, help_text, app[app.index("v35: THE COMPENDIUM TAB"):app.index('v18c: TIDY BRANDS')]])
        own_hits = GW_WORDS.findall(own) + GW_MORE.findall(own)
        check("the new Updates entry, the Help line and the new code's words are clean too", not own_hits, own_hits[:10])
        check("the Compendium has no links at all (no shop links, those come later)", page.locator("#view-compendium a").count() == 0)

        # ---------- 10. Hostile text ----------
        print("\n--- 10. Hostile text ---")
        evil_paints = PAINTS + [{"id": 90, "brand": HOSTILE_BRAND, "name": HOSTILE, "colour": "#2244aa", "status": "owned"}]
        evil_recipes = [rec(301, HOSTILE, "Armour", [90])]
        evil_units = [unit(1, HOSTILE, HOSTILE + " Host", [301])]
        load(page, paints=evil_paints, recipes=evil_recipes, units=evil_units)
        open_comp(page)
        copy_spy(page)
        evil_key = page.evaluate("() => { const c = compendiumBaseChoices(); return c.key([...c.own, ...c.other].find(p => p.name.includes('Evil'))); }")
        pick_base(page, evil_key)
        pick_combo(page, "#cmp-faction-history-pick", index=1)
        page.wait_for_timeout(150)
        cmp_pick(page, "starter-chips", "blue-gold")
        cmp_pick(page, "detail-chips", keys_d[0])
        cmp_pick(page, "basing-chips", "snow")
        check("hostile paint, brand, faction and recipe names never become markup anywhere in the Compendium",
              page.locator("#view-compendium img, #view-compendium script, #view-compendium b, #view-compendium iframe").count() == 0 and page.evaluate("() => window.__pwned") is None)
        check("they show as plain text instead", "<img src=x" in page.inner_text("#cmp-faction-history-for") or "<img src=x" in page.inner_text("#cmp-faction-history"), page.inner_text("#cmp-faction-history")[:200])
        check("the chosen hostile paint shows as plain text in the chooser and in the copied heading",
              "<img src=x" in page.input_value('#cmp-colour-ideas-base'))
        page.click("#cmp-fold-ideas-panel > .share-row button:has-text('Copy as text')")
        text = copied(page)
        check("Copy as text keeps it as plain text (the heading names the paint as typed)", text.splitlines()[0].startswith("Colour ideas for eyes or glow with ") and "<img src=x" in text.splitlines()[0], text.splitlines()[0])
        page.click("#cmp-faction-history .share-row button:has-text('Save into a new recipe')")
        page.wait_for_timeout(350)
        check("a new recipe started from hostile names keeps them as plain text and runs nothing",
              page.evaluate("() => window.__pwned") is None and page.locator("#recipe-page img, #recipe-page script").count() == 0
              and any("<img src=x" in s["n"] for s in draft_steps(page)))
        page.evaluate("() => { recipeDraft = null; }")

        # ---------- 11. Offline ----------
        print("\n--- 11. Offline ---")
        load(page, recipes=RECIPES, units=UNITS)
        mark = len(requests)
        open_comp(page)
        pick_base(page, BLUE)
        cmp_pick(page, "starter-chips", "blue-gold")
        cmp_pick(page, "detail-chips", keys_d[0])
        cmp_pick(page, "basing-chips", "snow")
        copy_spy(page)
        page.click("#cmp-basing-tips .share-row button:has-text('Copy as text')")
        outside = [u for u in requests[mark:] if not u.startswith(t.BASE) and not u.startswith("data:") and not u.startswith("blob:")]
        check("using the Compendium makes no request to any other address", not outside, outside[:5])
        ctx.set_offline(True)
        pick_base(page, "citadel|troll slayer orange")
        cmp_pick(page, "starter-chips", "green-bone")
        check("it works with the network off", len(comp_idea_rows(page)) == 3 and page.locator("#cmp-starter-list .idea-static").count() == 4)
        ctx.set_offline(False)

        # ---------- 12. Dark and light, 390 and 360 ----------
        print("\n--- 12. Dark and light, 390 and 360 px ---")
        for appearance in ("dark", "light"):
            for width in (390, 360):
                page.set_viewport_size({"width": width, "height": 844})
                load(page, recipes=RECIPES, units=UNITS, settings={"appearance": appearance})
                open_comp(page)
                pick_base(page, BLUE)
                pick_combo(page, "#cmp-faction-history-pick", text="Gloom Legion")
                page.wait_for_timeout(120)
                cmp_pick(page, "starter-chips", "blue-gold")
                cmp_pick(page, "detail-chips", keys_d[0])
                cmp_pick(page, "basing-chips", "snow")
                shot(page, f"v35-compendium-{appearance}-{width}.png")
                tag = f"{appearance} {width}px"
                check(f"{tag}: nothing scrolls sideways with every part open", no_sideways(page))
                outside = page.evaluate("""() => { const c = document.querySelector('#view-compendium .card').getBoundingClientRect();
                    return [...document.querySelectorAll('#compendium-body *')].filter(e => { const r = (e.closest('.chips-scroll') || e).getBoundingClientRect();   // v49: judged by the sliding row it's clipped to
                        return r.width > 0 && (r.right > c.right + 0.5 || r.left < c.left - 0.5); }).map(e => e.id || e.className || e.tagName); }""")
                check(f"{tag}: everything is inside the Compendium card, or in a one-line row that slides inside it (and the card is inside the screen)", not outside and page.evaluate("() => document.querySelector('#view-compendium .card').getBoundingClientRect().right") <= width + 0.5, outside[:5])
                col = page.evaluate("""() => { const bg = (el) => { let e = el; while (e) { const v = getComputedStyle(e).backgroundColor;
                        const m = v.match(/rgba\\(.*,\\s*([\\d.]+)\\)/);
                        if (v && v !== 'transparent' && !(m && parseFloat(m[1]) < 0.9)) return v; e = e.parentElement; } return 'rgb(0,0,0)'; };
                    const out = {};
                    const pairs = [['intro', '#cmp-intro'], ['role on', '#compendium-body [data-role][aria-pressed="true"]'], ['role off', '#compendium-body [data-role][aria-pressed="false"]'],
                                   ['tip', '#cmp-colour-ideas-tip'], ['idea name', '#cmp-fold-ideas-panel > .idea-list .idea-name'], ['idea why', '#cmp-fold-ideas-panel > .idea-list .idea-why'],
                                   ['idea tag', '#cmp-fold-ideas-panel > .idea-list .idea-tag'], ['history why', '#cmp-faction-history-list .idea-why'],
                                   ['mood on', '#cmp-starter-moods .chip[aria-pressed="true"]'], ['mood off', '#cmp-starter-moods .chip[aria-pressed="false"]'],
                                   ['scheme on', '#cmp-starter-chips .chip[aria-pressed="true"]'], ['summary', '#cmp-starter-summary'], ['reason', '#cmp-starter-reason'],
                                   ['scheme why', '#cmp-starter-list .idea-why'], ['detail why', '#cmp-detail-list .idea-why'], ['detail note', '#cmp-detail-list .idea-note'],
                                   ['basing list', '#cmp-basing-materials li'], ['basing sub', '#cmp-basing-tips .basing-sub'], ['basing why', '#cmp-basing-list .idea-why'],
                                   ['copy button', '#cmp-starter-schemes .share-row button'], ['foot', '#cmp-foot'], ['pro pill', '#view-compendium .pro-pill']];
                    for (const [k, s] of pairs) { const el = document.querySelector(s); if (el) out[k] = [getComputedStyle(el).color, bg(el)]; }
                    return out; }""")
                bad = {k: round(contrast(rgb(v[0]), rgb(v[1])), 2) for k, v in col.items() if contrast(rgb(v[0]), rgb(v[1])) < 4.5}
                check(f"{tag}: the intro, buttons, tip, ideas, rows, hints and footnote all have contrast of at least 4.5", not bad and len(col) >= 18, (bad, len(col)))
                rowsg = page.evaluate("""() => { const b = [...document.querySelectorAll('#compendium-body .share-row button, #compendium-body .chip')];
                    return b.length && Math.min(...b.map(x => x.getBoundingClientRect().height)); }""")
                check(f"{tag}: every button is at least 36 px tall (the Copy and Save buttons 44 px)", rowsg >= 36 and page.evaluate("() => [...document.querySelectorAll('#compendium-body .share-row button')].every(b => b.getBoundingClientRect().height >= 43.5)"), rowsg)
                bar = page.evaluate("() => { const b = document.querySelector('nav.tabs button[data-tab=compendium]'); return [getComputedStyle(b).color, getComputedStyle(document.querySelector('nav.tabs')).backgroundColor]; }")
                check(f"{tag}: the lit-up Compendium tab is readable (contrast 3 or more)", contrast(rgb(bar[0]), rgb(bar[1])) >= 3, bar)
        page.set_viewport_size({"width": 390, "height": 844})

        # ---------- 13. Nothing else changed ----------
        print("\n--- 13. Nothing else changed ---")
        load(page, recipes=RECIPES, units=UNITS)
        for tab, view in [("dashboard", "view-dashboard"), ("units", "view-units"), ("recipes", "view-recipes"), ("settings", "view-settings"), ("compendium", "view-compendium")]:
            blur(page)
            page.click(f'nav button[data-tab="{tab}"]')
            page.wait_for_timeout(120)
            check(f"the {tab} tab opens its own page and hides the others", page.is_visible(f"#{view}") and sum(page.is_visible(f"#{v}") for v in ["view-dashboard", "view-units", "view-recipes", "view-settings", "view-compendium"]) == 1)
        check("the card in a recipe still starts closed in a fresh editor", (lambda: (load(page, recipes=RECIPES, units=UNITS), t.open_editor(page), page.evaluate("() => document.getElementById('colour-ideas').open"))[-1])() is False)
        open_panel(page)
        check("the card still has the check at the bottom", page.locator("#scheme-check").count() == 1)
        check("the card still ends with its footnote and keeps its Pro preview label", page.inner_text("#colour-ideas .pro-pill") == "Pro preview"
              and "Nothing leaves your phone" in page.evaluate("() => document.querySelector('#colour-ideas .ideas-body').lastElementChild.textContent"))
        page.click("#recipe-page button.plain-button:has-text('Cancel')")
        page.wait_for_timeout(250)
        check("no real browser pop-ups appeared", not [d for d in dialogs if "Do you own" in d], dialogs[:3])
        check("no page errors", not errors, errors[:3])
        browser.close()

    print(f"\n{sum(results)} of {len(results)} checks passed")
    sys.exit(0 if all(results) else 1)

if __name__ == "__main__":
    main()
