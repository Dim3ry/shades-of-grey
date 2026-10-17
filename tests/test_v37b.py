"""v37 part 2 tests for Minifolio (Compendium 2b): search boxes and wheel groups.

What changed in the Compendium tab (Pro preview):
 - "Start from" and "Faction" are boxes you type in (not drop-downs). The list under the box narrows as you type, you can still scroll it and
   pick, and it works with a keyboard and a screen reader (the combobox pattern).
 - Starter schemes, Detail recipes and Basing tips have a search box above their buttons. Typing shows matches even when no group is chosen.
 - Each of the ten wheel parts is split into two or three named groups (headings in the detail), by the paint's colour. Each group runs dark to
   light with yours first, and shows its first few paints with a "Show all N" button for the rest.
 - Reuse: the door flag door.search switches the search on in the Compendium only; one shared builder for each kind of box.

Checks:
1. Versions (still v37, nothing bumped), the Updates entry, Help, wiring, no network, storage, innerHTML or links in the new code.
2. "Start from": built as a combobox, the list, counts, narrowing rules checked against an independent copy of the matching rule, "No matches.",
   keyboard, tap, scrolling to the very last paint, Clear, Escape, outside tap, speed with 1200 paints.
3. "Faction": the same box with a short list, empty and stale states.
4. Search above the button lists: placement, the short-by-default rule, counts for every typed word, every item reachable by its own name, the box
   keeps the focus, groups and the Themes | Combinations switch together with search, a picked item, kept while the app is open, recipe card unchanged.
5. Wheel groups: the headings of all ten parts, where paints land (colour, not name, and the edges), every group has built-in paints,
   dark to light, yours first and marked, short by default with Show all, Copy as text.
6. Hostile text (text-injection test) and a text scan for Games Workshop and brand words.
7. Offline.
8. Phone widths 360, 375, 390 and 400, and a real touch phone.
9. Dark and light at 390 and 360 px: contrast.
10. Nothing else changed (the ring picture, the recipe card).
Run all tests with `python3 tests/run_all.py`, or serve the repo folder and run this file on its own."""
import colorsys, hashlib, os, re, subprocess, sys, unicodedata
from playwright.sync_api import sync_playwright

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from notice_watch import attach_notices
import test_v31 as t   # the helpers (loading the app, the palette, the colours) and the Games Workshop word lists
from combo_helpers import pick_combo

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
KEYS = ["ideas", "history", "starter", "detail", "basing"]
UNITS = [unit(1, "Troop A", "Gloom Legion", [101]), unit(2, "Other", "Other Host", [102]), unit(3, "Third", "gloom legion ", [])]
RECIPES = [rec(101, "Armour blue", "Whole model", [1, 22]), rec(102, "Orange trim", "Armour", [2, 22]), rec(201, "Blue only", "Armour", [1])]

# ---- an independent copy of the matching rule (letters and digits only, any case, accents ignored, every word must be in the text) ----
def norm(text):
    text = "".join(c for c in unicodedata.normalize("NFD", text) if not unicodedata.combining(c)).lower()
    return " ".join(re.findall(r"[^\W_]+", text))

def hit(query, text):
    words = norm(query).split()
    if not words:
        return True
    hay = norm(text)
    compact = hay.replace(" ", "")
    return all(w in hay or w in compact for w in words)

def hx(h, s, l):
    r, g, b = colorsys.hls_to_rgb(h / 360, l, s)
    return "#%02x%02x%02x" % tuple(round(x * 255) for x in (r, g, b))

def P(pid, name, colour, status="owned", brand="Test Paints", **extra):
    return dict({"id": pid, "brand": brand, "name": name, "colour": colour, "status": status}, **extra)

# A made-up palette with a paint in every one of the 30 wheel groups (nothing here names a real paint).
GROUPS = [  # (wheel part, group key, heading, a colour that belongs there)
    ("red", "deep", "Deep reds", "#5a0d14"), ("red", "red", "Reds", "#c1272d"), ("red", "pink", "Pinks", "#f4a6c0"),
    ("orange", "brown", "Browns", "#4a2d12"), ("orange", "orange", "Oranges", "#e8802a"), ("orange", "peach", "Peach and apricot", "#f7b788"),
    ("yellow", "mustard", "Mustard and ochre", "#b8a22e"), ("yellow", "yellow", "Yellows", "#e6c82e"), ("yellow", "bone", "Bone", "#d9cba4"),
    ("green", "olive", "Olive and moss", "#6b7a2a"), ("green", "green", "Greens", "#228b22"), ("green", "sea", "Sea green and mint", "#2e8b6e"),
    ("blue", "navy", "Navy and deep blue", "#0d2a5c"), ("blue", "blue", "Blues", "#3b6fb0"), ("blue", "light", "Sky and pale blue", "#a9c6ec"),
    ("purple", "deep", "Deep purple", "#2a0f4a"), ("purple", "violet", "Violet", "#7b2d8b"), ("purple", "lavender", "Lavender and lilac", "#c3b1e1"),
    ("white", "neutral", "Pure whites", "#ffffff"), ("white", "warm", "Warm whites", "#fef3dd"), ("white", "cool", "Cool whites", "#e8eef2"),
    ("grey", "neutral", "Neutral greys", "#7f7f7f"), ("grey", "warm", "Warm greys", "#8f867a"), ("grey", "cool", "Cool greys", "#7a8794"),
    ("black", "neutral", "True blacks", "#0a0a0a"), ("black", "warm", "Warm blacks", "#2d1e01"), ("black", "cool", "Cool blacks", "#0b1220"),
    ("metallic", "gold", "Gold", "#c9a227"), ("metallic", "silver", "Silver", "#b8bec6"), ("metallic", "bronze", "Bronze", "#b4693a"),
]
PART_ORDER = ["red", "orange", "yellow", "green", "blue", "purple", "white", "grey", "black", "metallic"]
GPAINTS = [P(100 + i, f"Probe {g[2]}", g[3]) for i, g in enumerate(GROUPS)]
# the metallics need a metal word (their one exception), the others must not have one
for i, g in enumerate(GROUPS):
    if g[0] == "metallic":
        GPAINTS[i]["name"] = f"Probe {g[1]} metal"
COLOUR_OF = {p["name"]: p["colour"] for p in GPAINTS}

GROUPS_JS = """() => { const out = []; let cur = null;
    for (const el of document.querySelectorAll('#cmp-wheel-detail > h4.wheel-sub, #cmp-wheel-detail > ul.idea-list')) {
        if (el.tagName === 'H4') { cur = { heading: el.textContent, rows: [] }; out.push(cur); continue; }
        for (const b of el.querySelectorAll('.idea-static')) cur.rows.push({ name: b.querySelector('.idea-name').childNodes[0].textContent,
            tag: b.querySelector('.idea-tag').textContent, why: b.querySelector('.idea-why').textContent,
            colour: b.querySelector('.swatch').style.getPropertyValue('--swatch') }); }
    return out; }"""
CHIPS_JS = "(s) => [...document.querySelectorAll(s)].map(c => c.textContent)"

def open_tab(page):
    blur(page)
    page.click('nav button[data-tab="compendium"]')
    page.wait_for_timeout(200)

def is_open(page, key):
    return page.get_attribute(f"#cmp-fold-{key}-button", "aria-expanded") == "true"

def fold(page, key, want=True):
    if is_open(page, key) != want:
        page.click(f"#cmp-fold-{key}-button")
        page.wait_for_timeout(100)

def open_all(page):
    for key in KEYS:
        fold(page, key, True)

def tap(page, key):
    page.click(f'[data-wheel="{key}"]')
    page.wait_for_timeout(120)

def place(page, colour, name="Plain", ptype=None):
    return page.evaluate("([c, n, ty]) => { const r = wheelPlace({ colour: c, name: n, type: ty || undefined }); return r ? r.seg + '/' + r.sub : null; }", [colour, name, ptype])

def copy_spy(page):
    page.evaluate("""() => { window.__copied = null;
        Object.defineProperty(navigator, 'clipboard', { configurable: true, value: { writeText: (x) => { window.__copied = x; return Promise.resolve(); } } }); }""")

def copied(page):
    page.wait_for_timeout(200)
    return page.evaluate("() => window.__copied")

def type_into(page, sel, text):
    """Type like a person: click the box, clear it, then press the keys one at a time."""
    page.click(sel)
    page.fill(sel, "")
    page.keyboard.type(text)
    page.wait_for_timeout(60)

def option_texts(page, list_sel):
    return page.evaluate("(s) => [...document.querySelectorAll(s + ' [role=option]')].map(o => o.textContent)", list_sel)

def status(page, sel):
    return page.inner_text(sel).strip()

def all_paint_texts(page):
    return page.evaluate("""() => { const c = compendiumBaseChoices(); const all = [...c.own, ...c.other, ...c.brands.flatMap(b => b.list)];
        return all.map(p => p.brand ? `${p.name} (${p.brand})` : p.name); }""")

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
        load(page, paints=PAINTS, recipes=RECIPES, units=UNITS)
        html, sw, app = read("index.html"), read("sw.js"), read("app.js")
        tags = re.findall(r'<script src="([^"]+)\?v=(\d+)"', html)
        check("the version is v37 or later everywhere, and the same everywhere (v38 bumped it later): APP_VERSION, sw.js and the six script tags",
              float(page.evaluate("APP_VERSION")[1:]) >= 37 and page.evaluate("APP_VERSION")[1:] == re.search(r'const VERSION = "v([\d.]+)"', sw).group(1) and len(tags) == 6
              and len({v for _, v in tags}) == 1 and {v for _, v in tags} == {page.evaluate("APP_VERSION")[1:]},
              (page.evaluate("APP_VERSION"), tags))
        files = re.search(r"const APP_FILES = \[(.*?)\];", sw, re.S).group(1)
        check("sw.js still saves the same twelve app files for offline use (nothing new was added to the app)",
              re.findall(r'"\./([^"?]*)', files) == ["", "index.html", "app.js", "early.js", "colour.js", "schemes.js", "detail-recipes.js", "basing-tips.js", "manifest.json", "icon-192.png", "icon-512.png", "ocr/ocr-worker.js"],
              re.findall(r'"\./([^"?]*)', files))
        entry = page.evaluate("CHANGELOG.find(r => r.version === 'v37')")
        joined = " ".join(entry["changes"]) if entry else ""
        check("the v37 Updates entry now also tells about the search boxes (Start from, Faction, No matches) and the wheel groups (Deep purple, Violet, Show all)",
              entry and page.evaluate("CHANGELOG.filter(r => r.version === 'v37').length") == 1
              and all(w in joined for w in ["Search", "Start from", "Faction", "No matches", "Deep purple", "Violet", "Lavender and lilac", "Show all", "neutral, warm or cool"]), joined[-500:])
        check("the v36, v35 and v34 entries are still there", page.evaluate("['v36', 'v35', 'v34'].every(v => !!CHANGELOG.find(r => r.version === v))"))
        help_text = page.evaluate("() => document.getElementById('help-tabs').textContent")
        check("Help says Start from and Faction are boxes you can type in, the lists have a search box, and the wheel is split into groups",
              all(w in help_text for w in ["Start from and Faction are boxes you can type in", "search box", "split into groups"]), help_text[-300:])
        changed = []
        for base in ("HEAD", "origin/main"):
            out = subprocess.run(["git", "diff", "--name-only", base, "--", "colour.js", "schemes.js", "detail-recipes.js", "basing-tips.js", "sw.js"],
                                 cwd=ROOT, capture_output=True, text=True)
            if out.returncode == 0:
                changed += [f for f in out.stdout.split() if f != "sw.js"]
        check("the content data files and colour.js are unchanged", changed == [], changed)
        mark_a, mark_b = app.index("v37 part 2: SEARCH"), app.index("v37: the other way to browse the starter schemes")
        new_code = app[mark_a:mark_b] + app[app.index("const WHEEL_TINT_C"):app.index("function wheelTone(")]
        check("the new code has no network code, no storage, no innerHTML, no links and no shop wording",
              len(new_code) > 6000 and not re.search(r"\bfetch\s*\(|XMLHttpRequest|sendBeacon|WebSocket|localStorage|sessionStorage|\beval\s*\(|new Function|insertAdjacentHTML|outerHTML|innerHTML|createElement\('a'\)|createElement\(\"a\"\)|href|affiliate|\bshop\b", new_code),
              [m.group(0) for m in re.finditer(r"(fetch|innerHTML|href|affiliate)[^\n]*", new_code)][:3])
        check("each shared builder is defined once and used by every box: buildSearchPicker (Start from, Faction), buildListSearch (three lists), wheelSub",
              all(app.count(f"function {n}(") == 1 for n in ["buildSearchPicker", "buildListSearch", "wheelSub", "wheelTint", "searchNorm", "searchMatches", "groupAllowsNow"])
              and app.count("appendChild(buildSearchPicker(door") == 2 and app.count("appendChild(buildListSearch(door") == 3)
        check("the door flag is the switch: the Compendium door has search, the recipe card's door does not, and the door comment names it",
              re.search(r"fold: true, short: true, switcher: true, search: true", app) is not None and "search        (v37 part 2, Compendium only)" in app
              and "door.search" in app and not re.search(r"search:\s*true", app[app.index("function appendLibraryParts"):app.index("function appendRolePicker")]))
        check("Start from and Faction are no longer drop-downs: they are text boxes with role combobox; the recipe card still has its own drop-down",
              page.evaluate("() => { const a = document.getElementById('cmp-colour-ideas-base'); return a === null; }") is True)
        open_tab(page)
        open_all(page)
        info = page.evaluate("""() => ['cmp-colour-ideas-base', 'cmp-faction-history-pick'].map(i => { const e = document.getElementById(i); return { tag: e.tagName, type: e.type, role: e.getAttribute('role') }; })""")
        check("both are <input type=text role=combobox>", info == [{"tag": "INPUT", "type": "text", "role": "combobox"}] * 2, info)

        # ---------- 2. Start from ----------
        print("\n--- 2. Start from: a box you type in ---")
        load(page, paints=PAINTS, recipes=RECIPES, units=UNITS)
        open_tab(page)
        open_all(page)
        BASE, LIST, STAT, TOG, CLR = "#cmp-colour-ideas-base", "#cmp-colour-ideas-base-list", "#cmp-colour-ideas-base-status", "#cmp-colour-ideas-base-toggle", "#cmp-colour-ideas-base-clear"
        texts = all_paint_texts(page)
        check(f"there are 500+ paints to start from ({len(texts)})", len(texts) > 500, len(texts))
        aria = page.evaluate("""() => { const i = document.getElementById('cmp-colour-ideas-base'), l = document.getElementById('cmp-colour-ideas-base-list'), lab = document.querySelector('label[for="cmp-colour-ideas-base"]');
            return { label: lab && lab.textContent, ac: i.getAttribute('aria-autocomplete'), exp: i.getAttribute('aria-expanded'), ctl: i.getAttribute('aria-controls'), listRole: l.getAttribute('role'),
                     listHidden: l.hidden, lab: l.getAttribute('aria-labelledby'), hasPop: i.getAttribute('aria-haspopup'), off: i.getAttribute('autocomplete'), placeholder: i.placeholder,
                     tab: i.tabIndex, value: i.value, status: document.getElementById('cmp-colour-ideas-base-status').getAttribute('role') }; }""")
        check("it has a real label (Start from), role combobox, aria-autocomplete list, aria-haspopup, aria-controls pointing at a listbox, closed at the start, and a status line",
              aria != {} and aria["label"] == "Start from" and aria["ac"] == "list" and aria["exp"] == "false" and aria["ctl"] == "cmp-colour-ideas-base-list" and aria["listRole"] == "listbox"
              and aria["listHidden"] and aria["lab"] == "cmp-colour-ideas-base-label" and aria["hasPop"] == "listbox" and aria["off"] == "off" and aria["status"] == "status"
              and aria["placeholder"] == "Type or choose a paint" and aria["tab"] == 0 and aria["value"] == "", aria)
        check("the closed box makes no list lines (nothing is built until it is opened)", page.locator(f"{LIST} li").count() == 0)
        tog = page.evaluate("""() => { const b = document.getElementById('cmp-colour-ideas-base-toggle'); return { tab: b.tabIndex, label: b.getAttribute('aria-label'), type: b.type, ctl: b.getAttribute('aria-controls') }; }""")
        check("a button next to it opens the list without typing (a finger or a screen reader); it is out of the Tab order (the keyboard uses the arrow keys)",
              tog == {"tab": -1, "label": "Show the list: Start from", "type": "button", "ctl": "cmp-colour-ideas-base-list"}, tog)
        page.click(BASE)
        page.wait_for_timeout(100)
        check("tapping the box opens the list: aria-expanded true, the list shows, and the status says how many paints there are",
              page.get_attribute(BASE, "aria-expanded") == "true" and page.is_visible(LIST) and status(page, STAT) == f"{len(texts)} paints. Type to narrow the list.", status(page, STAT))
        opts = page.evaluate("""() => [...document.querySelectorAll('#cmp-colour-ideas-base-list [role=option]')].map(o => ({ id: o.id, sel: o.getAttribute('aria-selected'),
            pos: o.getAttribute('aria-posinset'), size: o.getAttribute('aria-setsize'), value: o.dataset.value, h: o.getBoundingClientRect().height }))""")
        check("the list starts with only 60 lines so 500+ paints stay quick, each a real option with its place (1 of N) and a unique id",
              len(opts) == 60 and opts[0]["pos"] == "1" and opts[-1]["pos"] == "60" and all(o["size"] == str(len(texts)) for o in opts) and len({o["id"] for o in opts}) == 60 and all(o["sel"] == "false" for o in opts), opts[:2])
        check("every line is at least 44 px tall (a finger)", all(o["h"] >= 44 for o in opts), [o["h"] for o in opts if o["h"] < 44][:3])
        groups = page.evaluate("() => [...document.querySelectorAll('#cmp-colour-ideas-base-list > li.combo-group')].map(e => [e.textContent, e.getAttribute('role')])")
        check("the lines are in groups with headings: your own paints first, then other paints in your palette, then the built-in list by brand",
              groups and groups[0] == ["Paints you own", "presentation"] and any(g[0].startswith("More ") for g in groups), groups[:4])
        check("the first lines are your own paints (owned first)", option_texts(page, LIST)[:3] == sorted(option_texts(page, LIST)[:3]) and "Macragge Blue (Citadel)" in option_texts(page, LIST)[:14])
        page.keyboard.press("Escape")
        page.wait_for_timeout(60)
        check("Escape closes it again (aria-expanded false, list hidden, status empty)", page.get_attribute(BASE, "aria-expanded") == "false" and not page.is_visible(LIST) and status(page, STAT) == "")

        # narrowing: every query is checked against an independent copy of the rule
        queries = ["blue", "BLUE", "macragge", "blue macragge", "macrágge", "citadel", "orange red", "off white", "offwhite", "grey", "x", "a b", "  ", "(citadel)", "ZZ", "troll slayer"]
        bad = []
        for q in queries:
            type_into(page, BASE, q)
            want = [x for x in texts if hit(q, x)]
            n_shown = page.locator(f"{LIST} [role=option]").count()
            stat = status(page, STAT)
            expect_stat = ("No matches." if not want else f"{len(want)} {'match' if len(want) == 1 else 'matches'}.") if norm(q) else f"{len(texts)} paints. Type to narrow the list."
            if not norm(q):
                expect_stat = f"{len(texts)} matches."   # only spaces typed: it is a typed search with no words, so everything matches
            first = option_texts(page, LIST)[:60]
            if stat != expect_stat or n_shown != min(60, len(want)) or first != want[:60]:
                bad.append((q, stat, expect_stat, n_shown, len(want)))
        check(f"typing narrows the list: {len(queries)} queries (capitals, accents, word order, brand, punctuation, only spaces, no match) give exactly the lines an independent copy of the rule gives, in the same order, with the right count", not bad, bad[:3])
        type_into(page, BASE, "zzzzqq")
        check("when nothing fits it says No matches. plainly, and the empty list is not shown", status(page, STAT) == "No matches." and not page.is_visible(LIST) and page.locator(f"{LIST} [role=option]").count() == 0, status(page, STAT))
        check("the No matches. line never repeats what was typed (nothing typed can reach the page as text from the status)", "zzzz" not in page.inner_text("#cmp-fold-ideas-panel"))
        live = page.evaluate("() => { const s = document.getElementById('cmp-colour-ideas-base-status'); return [s.getAttribute('role'), s.getAttribute('aria-live')]; }")
        check("the status line is a polite live region, so a screen reader says the count as you type", live == ["status", "polite"], live)
        type_into(page, BASE, "macragge")
        check("one match is said in the singular", status(page, STAT) == "1 match.", status(page, STAT))
        t0 = page.evaluate("""() => { const i = document.getElementById('cmp-colour-ideas-base'); const t = performance.now(); i.value = 'a'; i.dispatchEvent(new Event('input', { bubbles: true }));
            i.value = 'bl'; i.dispatchEvent(new Event('input', { bubbles: true })); i.value = ''; i.dispatchEvent(new Event('input', { bubbles: true })); return (performance.now() - t) / 3; }""")
        check(f"each keystroke is quick even with {len(texts)} paints (under 150 ms on average: {t0:.1f} ms)", t0 < 150, t0)
        page.keyboard.press("Escape")
        # keyboard
        type_into(page, BASE, "blue")
        check("while typing the list is open and nothing is highlighted yet (no aria-activedescendant)", page.get_attribute(BASE, "aria-expanded") == "true" and page.get_attribute(BASE, "aria-activedescendant") is None)
        page.keyboard.press("ArrowDown")
        a1 = page.get_attribute(BASE, "aria-activedescendant")
        page.keyboard.press("ArrowDown")
        a2 = page.get_attribute(BASE, "aria-activedescendant")
        page.keyboard.press("ArrowUp")
        a3 = page.get_attribute(BASE, "aria-activedescendant")
        check("the down arrow highlights the first line, then the next, the up arrow goes back; aria-activedescendant names the highlighted line and the focus stays in the box",
              a1 == "cmp-colour-ideas-base-list-0" and a2 == "cmp-colour-ideas-base-list-1" and a3 == a1 and page.evaluate("() => document.activeElement.id") == "cmp-colour-ideas-base"
              and page.evaluate("(i) => document.getElementById(i).classList.contains('is-active') && document.getElementById(i).getAttribute('role') === 'option'", a3), (a1, a2, a3))
        page.keyboard.press("PageDown")
        check("Page Down moves eight lines", page.get_attribute(BASE, "aria-activedescendant") == "cmp-colour-ideas-base-list-8", page.get_attribute(BASE, "aria-activedescendant"))
        for _ in range(70):
            page.keyboard.press("ArrowDown")
        deep = page.get_attribute(BASE, "aria-activedescendant")
        check("the down arrow keeps going past the first 60 lines (more are added as you reach the end)", deep == "cmp-colour-ideas-base-list-78" and page.locator(f"{LIST} [role=option]").count() >= 79, (deep, page.locator(f"{LIST} [role=option]").count()))
        check("the highlighted line is scrolled into view inside the list",
              page.evaluate("() => { const l = document.getElementById('cmp-colour-ideas-base-list'), e = document.querySelector('#cmp-colour-ideas-base-list .is-active'); const a = l.getBoundingClientRect(), b = e.getBoundingClientRect(); return b.top >= a.top - 1 && b.bottom <= a.bottom + 1; }"))
        page.keyboard.press("Enter")
        page.wait_for_timeout(200)
        picked = page.evaluate("() => compendiumState.base")
        check("Enter picks the highlighted paint: the box shows its name, the list closes, the Colour ideas below appear, and the focus stays in the box",
              picked != "" and page.get_attribute(BASE, "aria-expanded") == "false" and page.input_value(BASE) in texts and page.locator("#cmp-fold-ideas-panel [data-role]").count() == 6
              and page.evaluate("() => document.activeElement.id") == "cmp-colour-ideas-base", (picked, page.input_value(BASE)))
        check("the chosen paint shows in the list as selected (aria-selected true) the next time it is opened", (lambda: (page.click(TOG), page.wait_for_timeout(80),
              page.locator(f'{LIST} [role=option][aria-selected="true"]').count())[-1])() == 1)
        page.keyboard.press("Escape")
        # the first click selects the whole name so typing replaces it
        page.click(BASE)
        sel = page.evaluate("() => { const i = document.getElementById('cmp-colour-ideas-base'); return [i.selectionStart, i.selectionEnd, i.value.length]; }")
        check("clicking a box that has a paint in it selects the whole name, so typing replaces it", sel[0] == 0 and sel[1] == sel[2] > 0, sel)
        page.keyboard.press("Escape")
        # enter with one match and nothing highlighted
        type_into(page, BASE, "troll slayer")
        one = page.locator(f"{LIST} [role=option]").count()
        page.keyboard.press("Enter")
        page.wait_for_timeout(200)
        check("Enter with exactly one match and nothing highlighted picks that match", one == 1 and page.input_value(BASE).startswith("Troll Slayer Orange") and page.evaluate("() => compendiumState.base") == "citadel|troll slayer orange", (one, page.input_value(BASE)))
        # escape restores
        type_into(page, BASE, "xyz")
        page.keyboard.press("Escape")
        check("Escape puts the chosen paint's name back in the box (typing is thrown away)", page.input_value(BASE).startswith("Troll Slayer Orange") and page.get_attribute(BASE, "aria-expanded") == "false", page.input_value(BASE))
        # a tap on a line (touch and mouse): the list is a pointer thing too
        type_into(page, BASE, "macragge")
        page.click(f'{LIST} [role=option]')
        page.wait_for_timeout(200)
        check("tapping a line picks it, closes the list, and the focus goes to the button next to the box (no keyboard pops up on a phone)",
              page.evaluate("() => compendiumState.base") == "citadel|macragge blue" and page.get_attribute(BASE, "aria-expanded") == "false"
              and page.evaluate("() => document.activeElement.id") == "cmp-colour-ideas-base-toggle")
        # scroll and pick, down to the very last paint
        page.click(TOG)
        page.wait_for_timeout(100)
        for _ in range(40):
            if page.locator(f"{LIST} [role=option]").count() >= len(texts):
                break
            page.hover(LIST)
            page.mouse.wheel(0, 4000)
            page.wait_for_timeout(40)
        n_now = page.locator(f"{LIST} [role=option]").count()
        check(f"scrolling the list with the wheel keeps adding lines until all {len(texts)} are there and nothing is missing or twice", n_now == len(texts) and len(set(option_texts(page, LIST))) == len(set(texts)), (n_now, len(texts)))
        last = page.locator(f'{LIST} [role=option][aria-posinset="{len(texts)}"]')
        last_text = last.inner_text()
        last.click()
        page.wait_for_timeout(200)
        check("you can scroll to the very last paint and pick it: the box shows it and Colour ideas follows", page.input_value(BASE) == last_text == texts[-1] and page.locator("#cmp-fold-ideas-panel .idea-static").count() == 3, (page.input_value(BASE), last_text))
        # clear
        check("a Clear button shows while a paint is chosen", page.is_visible(CLR))
        page.click(CLR)
        page.wait_for_timeout(200)
        check("Clear takes the paint away: the box is empty, the ideas go, the focus goes to the box, and the Clear button hides",
              page.input_value(BASE) == "" and page.evaluate("() => compendiumState.base") == "" and page.locator("#cmp-colour-ideas-none").count() == 1
              and page.evaluate("() => document.activeElement.id") == "cmp-colour-ideas-base" and not page.is_visible(CLR))
        # outside tap and Tab close it
        page.click(BASE)
        page.wait_for_timeout(60)
        page.click("#cmp-wheel-hint")
        page.wait_for_timeout(80)
        check("tapping anywhere outside closes the list", page.get_attribute(BASE, "aria-expanded") == "false" and not page.is_visible(LIST))
        page.click(BASE)
        page.keyboard.press("Tab")
        page.wait_for_timeout(80)
        check("pressing Tab closes the list and moves on (the list never traps the keyboard)", page.get_attribute(BASE, "aria-expanded") == "false" and page.evaluate("() => document.activeElement.id") != "cmp-colour-ideas-base")
        page.click(TOG)
        page.wait_for_timeout(80)
        was_open = page.get_attribute(BASE, "aria-expanded") == "true"
        page.click(TOG)
        page.wait_for_timeout(80)
        check("the button opens the list and closes it again", was_open and page.get_attribute(BASE, "aria-expanded") == "false" and page.get_attribute(TOG, "aria-expanded") == "false")
        check("opening it changes nothing else: no paint is chosen and the page has not redrawn", page.evaluate("() => compendiumState.base") == "")
        # state kept
        pick_combo(page, BASE, text="Macragge Blue (Citadel)")
        blur(page)
        page.click('nav button[data-tab=\"units\"]')
        page.wait_for_timeout(100)
        open_tab(page)
        check("coming back to the Compendium, the paint you chose is still in the box (kept while the app is open)", page.input_value(BASE) == "Macragge Blue (Citadel)")
        # empty palette
        load(page, paints=[], recipes=RECIPES, units=UNITS)
        open_tab(page)
        open_all(page)
        page.click(TOG)
        check("with an empty palette the box still lists the built-in paints (no 'paints you own' heading)", page.locator(f"{LIST} [role=option]").count() == 60
              and not any(g.startswith("Paints you own") for g in page.evaluate("() => [...document.querySelectorAll('#cmp-colour-ideas-base-list > li.combo-group')].map(e => e.textContent)")))
        page.keyboard.press("Escape")
        shot(page, "v37b-start-from-closed-390.png")
        load(page, paints=PAINTS, recipes=RECIPES, units=UNITS)
        open_tab(page)
        open_all(page)
        type_into(page, BASE, "orange")
        shot(page, "v37b-start-from-open-390.png")
        page.keyboard.press("Escape")

        # ---------- 3. Faction ----------
        print("\n--- 3. Faction: the same box with a short list ---")
        FB, FL, FS, FT = "#cmp-faction-history-pick", "#cmp-faction-history-pick-list", "#cmp-faction-history-pick-status", "#cmp-faction-history-pick-toggle"
        load(page, paints=PAINTS, recipes=RECIPES, units=UNITS)
        open_tab(page)
        open_all(page)
        page.click(FT)
        page.wait_for_timeout(80)
        check("the list holds each faction once, sorted (Gloom Legion once, however it was typed), and says how many there are",
              option_texts(page, FL) == ["Gloom Legion", "Other Host"] and status(page, FS) == "2 factions. Type to narrow the list.", (option_texts(page, FL), status(page, FS)))
        check("it has a label, role combobox, and no group headings (there is only one group)", page.evaluate("() => document.querySelector('label[for=\"cmp-faction-history-pick\"]').textContent") == "Faction"
              and page.locator(f"{FL} .combo-group").count() == 0 and page.get_attribute(FB, "role") == "combobox")
        type_into(page, FB, "OTH")
        check("typing narrows it (capitals do not matter)", option_texts(page, FL) == ["Other Host"] and status(page, FS) == "1 match.")
        type_into(page, FB, "zzz")
        check("No matches. when nothing fits", status(page, FS) == "No matches." and not page.is_visible(FL))
        page.keyboard.press("Escape")
        pick_combo(page, FB, text="Gloom Legion")
        hist = page.locator("#cmp-faction-history-list .idea-static").count()
        check("choosing Gloom Legion by keyboard shows its paints (as before) and the focus stays in the box", hist >= 2 and "Gloom Legion" in page.inner_text("#cmp-faction-history-for")
              and page.evaluate("() => document.activeElement.id") == "cmp-faction-history-pick" and page.input_value(FB) == "Gloom Legion", hist)
        page.click(FT)
        page.click(f'{FL} [role=option]:text-is("Other Host")')
        page.wait_for_timeout(200)
        check("tapping a faction in the list works too", page.evaluate("() => compendiumState.faction") == "other host" and page.input_value(FB) == "Other Host")
        page.click("#cmp-faction-history-pick-clear")
        page.wait_for_timeout(150)
        check("Clear takes the faction away and says to choose one", page.evaluate("() => compendiumState.faction") == "" and "Choose a faction above" in page.inner_text("#cmp-faction-history-none"))
        load(page, recipes=RECIPES, units=[unit(1, "Solo", "")])
        open_tab(page)
        open_all(page)
        check("with no faction on any unit the box is switched off and says No factions yet, and the plain line says why",
              page.is_disabled(FB) and page.get_attribute(FB, "placeholder") == "No factions yet" and page.is_disabled(FT) and "None of your units has a faction yet" in page.inner_text("#cmp-faction-history-none"))
        load(page, recipes=RECIPES, units=UNITS)
        page.evaluate("() => { compendiumState.faction = 'gone host'; }")
        open_tab(page)
        open_all(page)
        check("a saved faction that no unit has any more is dropped: the box is empty", page.input_value(FB) == "" and page.evaluate("() => compendiumState.faction") == "")

        # ---------- 4. Search above the choice buttons ----------
        print("\n--- 4. Search above Starter schemes, Detail recipes and Basing tips ---")
        load(page, paints=PAINTS, recipes=RECIPES, units=UNITS)
        open_tab(page)
        open_all(page)
        data = page.evaluate("""() => ({ starter: STARTER_SCHEMES.map(s => ({ key: s.key, text: s.name + ' ' + s.summary, name: s.name, mood: s.mood })),
            detail: DETAIL_RECIPES.map(s => ({ key: s.key, text: s.name + ' ' + s.summary, name: s.name, group: s.group })),
            basing: BASING_TIPS.map(s => ({ key: s.key, text: s.name + ' ' + s.summary, name: s.name, group: s.group })) })""")
        PARTS = [("starter", "Search starter schemes", "starter-chips", "starter-moods", "mood", "starter-none", "schemes"),
                 ("detail", "Search detail recipes", "detail-chips", "detail-groups", "detail-group", "detail-none-group", "recipes"),
                 ("basing", "Search basing tips", "basing-chips", "basing-groups", "basing-group", "basing-none-group", "tips")]
        for key, label, chips_id, groups_id, attr, none_id, what in PARTS:
            S, ST = f"#cmp-{key}-search", f"#cmp-{key}-search-status"
            info = page.evaluate("""([k, g, c]) => { const i = document.getElementById('cmp-' + k + '-search'), part = i.closest('.fold-panel').firstElementChild, kids = [...part.children].map(e => e.id || e.className);
                const lab = document.querySelector('label[for="cmp-' + k + '-search"]'), st = document.getElementById('cmp-' + k + '-search-status');
                return { type: i.type, label: lab && lab.textContent, desc: i.getAttribute('aria-describedby'), role: st.getAttribute('role'), live: st.getAttribute('aria-live'),
                         box: i.closest('.list-search').id, kids, tab: i.tabIndex, value: i.value, ph: i.placeholder }; }""", [key, groups_id, chips_id])
            check(f"{key}: a search box with a real label ({label}), type search, described by a polite live status line, in the tab order, empty at the start",
                  info["type"] == "search" and info["label"] == label and info["desc"] == f"cmp-{key}-search-status" and info["role"] == "status" and info["live"] == "polite" and info["tab"] == 0 and info["value"] == "" and info["ph"] == "Type to search", info)
            order = page.evaluate("""([k, g]) => { const s = document.getElementById('cmp-' + k + '-search-box').getBoundingClientRect(), b = document.getElementById('cmp-' + g).getBoundingClientRect(); return [s.bottom, b.top]; }""", [key, groups_id])
            check(f"{key}: the search box sits above the group buttons (so above every choice button)", order[0] <= order[1] + 0.5, order)
            check(f"{key}: before typing, the short-by-default rule from part 1 still holds: no list, and the plain line says to pick a group or tap All",
                  page.locator(f"#cmp-{chips_id}").count() == 0 and page.inner_text(f"#cmp-{none_id}") == f"Pick a group above to see its {what}, or tap All." and status(page, ST) == "")
            items = data[key]
            bad = []
            for q in ["blue", "red", "grey", "GOLD", "stone", "a", "zzzzz", "water", "two", "steel blue"]:
                type_into(page, S, q)
                want = [x["name"] for x in items if hit(q, x["text"])]
                shown = page.evaluate(CHIPS_JS, f"#cmp-{chips_id} .chip")
                stat = status(page, ST)
                expect = "No matches." if not want else f"{len(want)} {'match' if len(want) == 1 else 'matches'}."
                none_line = page.locator(f"#cmp-{none_id}").count()
                if shown != want or stat != expect or none_line != 0:
                    bad.append((q, shown[:3], want[:3], stat, expect, none_line))
            check(f"{key}: typing shows exactly the matches (name and summary) even though no group is chosen, with the right count, and the plain line is gone", not bad, bad[:2])
            type_into(page, S, "zzzzz")
            check(f"{key}: when nothing fits it says No matches. and shows no buttons (and no empty box)", status(page, ST) == "No matches." and page.locator(f"#cmp-{chips_id}").count() == 0 and page.locator(f"#cmp-{none_id}").count() == 0)
            page.fill(S, "")
            page.dispatch_event(S, "input")
            check(f"{key}: clearing the text puts the short rule back (no list, the plain line returns) and empties the status",
                  page.locator(f"#cmp-{chips_id}").count() == 0 and page.locator(f"#cmp-{none_id}").count() == 1 and status(page, ST) == "")
            # the box keeps the focus and is the very same element while typing
            page.evaluate("() => { document.getElementById('cmp-%s-search').__same = 7; }" % key)
            page.click(S)
            page.keyboard.type("blu")
            page.wait_for_timeout(60)
            check(f"{key}: the box keeps the focus while you type, is never replaced (a half-typed word, a screen reader and a phone keyboard are not interrupted), and keeps what you typed",
                  page.evaluate("() => document.activeElement.id") == f"cmp-{key}-search" and page.evaluate("(k) => document.getElementById('cmp-' + k + '-search').__same", key) == 7 and page.input_value(S) == "blu")
            check(f"{key}: the typed words are kept in the door's state (compendiumState.search.{key})", page.evaluate("(k) => compendiumState.search[k]", key) == "blu")
            # every item can be found by its own name
            missing = page.evaluate("""([k, items]) => { const input = document.getElementById('cmp-' + k + '-search'), out = [];
                for (const it of items) { input.value = it.name; input.dispatchEvent(new Event('input', { bubbles: true }));
                    const names = [...document.querySelectorAll('#cmp-' + (k === 'starter' ? 'starter' : k) + '-chips .chip')].map(c => c.textContent); if (!names.includes(it.name)) out.push(it.name); }
                return out; }""", [key, items])
            check(f"{key}: every one of the {len(items)} can be found by typing its own name", not missing, missing[:3])
            page.fill(S, "")
            page.dispatch_event(S, "input")
        # one deep check with groups, All and the switch
        S, ST = "#cmp-starter-search", "#cmp-starter-search-status"
        type_into(page, S, "blue")
        n_all = len(page.evaluate(CHIPS_JS, "#cmp-starter-chips .chip"))
        page.click('#cmp-starter-moods [data-mood="cold"]')
        page.wait_for_timeout(100)
        cold = page.evaluate(CHIPS_JS, "#cmp-starter-chips .chip")
        want_cold = [x["name"] for x in data["starter"] if x["mood"] == "cold" and hit("blue", x["text"])]
        check("a chosen group still narrows the search: Cold plus 'blue' shows only the cold matches, and the status names the group (N matches in Cold.)",
              cold == want_cold and 0 < len(cold) < n_all and status(page, ST) == f"{len(cold)} {'match' if len(cold) == 1 else 'matches'} in Cold.", (cold, want_cold, status(page, ST)))
        check("the search text is still in the box after the group redrew the page, and the group button stays on", page.input_value(S) == "blue" and page.get_attribute('#cmp-starter-moods [data-mood="cold"]', "aria-pressed") == "true")
        page.click('#cmp-starter-moods [data-mood="cold"]')
        page.wait_for_timeout(100)
        check("tapping the group again puts the group away but the search still shows its matches", len(page.evaluate(CHIPS_JS, "#cmp-starter-chips .chip")) == n_all)
        page.click('#cmp-starter-view [data-view="combos"]')
        page.wait_for_timeout(100)
        combos = page.evaluate(CHIPS_JS, "#cmp-starter-chips .chip")
        check("the Themes | Combinations switch keeps the search: the same matches show in Combinations (and the search box is still above the group buttons)",
              combos == [x["name"] for x in data["starter"] if hit("blue", x["text"])] and page.input_value(S) == "blue" and page.locator("#cmp-starter-combos").count() == 1)
        page.click('#cmp-starter-combos [data-combo="blue"]')
        page.wait_for_timeout(100)
        blues = page.evaluate(CHIPS_JS, "#cmp-starter-chips .chip")
        check("in Combinations a chosen colour group narrows the search too", 0 < len(blues) <= len(combos) and set(blues) <= set(combos) and status(page, ST).endswith("in Blues."), (blues, status(page, ST)))
        page.click('#cmp-starter-view [data-view="themes"]')
        page.wait_for_timeout(100)
        # pick from search results
        page.fill(S, "")
        page.dispatch_event(S, "input")
        page.click('#cmp-starter-moods [data-mood="cold"]')   # cold is off after the switch? make sure no group is on
        page.wait_for_timeout(60)
        if page.get_attribute('#cmp-starter-moods [data-mood="cold"]', "aria-pressed") == "true":
            page.click('#cmp-starter-moods [data-mood="cold"]')
        type_into(page, S, "terracotta")
        chosen = page.evaluate(CHIPS_JS, "#cmp-starter-chips .chip")
        page.click("#cmp-starter-chips .chip")
        page.wait_for_timeout(150)
        check("picking a scheme from the search results shows its summary and its paints, and the search text stays", len(chosen) >= 1 and page.locator("#cmp-starter-list .idea-static").count() == 4 and page.input_value(S) == "terracotta", chosen)
        type_into(page, S, "terracottazzz")
        check("typing on so that the scheme no longer matches hides its paints (and says No matches.)", page.locator("#cmp-starter-list").count() == 0 and status(page, ST) == "No matches.")
        page.fill(S, "")
        page.dispatch_event(S, "input")
        page.wait_for_timeout(100)
        check("emptying the search keeps a scheme you picked in sight (its group is chosen, so it is not lost)", page.locator("#cmp-starter-list .idea-static").count() == 4 and page.locator("#cmp-starter-chips .chip").count() >= 1)
        # escape and clear
        type_into(page, S, "blue")
        page.keyboard.press("Escape")
        page.wait_for_timeout(80)
        check("Escape in a search box empties it and the list follows", page.input_value(S) == "" and page.evaluate("() => compendiumState.search.starter") == "")
        type_into(page, S, "blue")
        check("a Clear button shows while there is text", page.is_visible("#cmp-starter-search-clear"))
        page.click("#cmp-starter-search-clear")
        page.wait_for_timeout(80)
        check("Clear empties the box, puts the focus back in it and hides itself", page.input_value(S) == "" and page.evaluate("() => document.activeElement.id") == "cmp-starter-search" and not page.is_visible("#cmp-starter-search-clear"))
        # kept while the app is open, gone after a reload
        type_into(page, "#cmp-detail-search", "wet")
        blur(page)
        page.click('nav button[data-tab=\"units\"]')
        page.wait_for_timeout(100)
        open_tab(page)
        check("what you typed is kept while the app is open (leave the tab and come back)", page.input_value("#cmp-detail-search") == "wet" and is_open(page, "detail"))
        page.reload()
        page.wait_for_function("() => typeof APP_VERSION === 'string'")
        page.wait_for_timeout(300)
        open_tab(page)
        fold(page, "detail", True)
        check("after the app is closed and opened again the search is empty", page.input_value("#cmp-detail-search") == "")
        # recipe card unchanged
        t.edit_recipe(page, 101)
        t.open_panel(page)
        card_ids = [i for i in ["starter-search", "detail-search", "basing-search", "colour-ideas-base-combo", "faction-history-pick"] if page.locator(f"#colour-ideas #{i}, #colour-ideas #cmp-{i}").count()]
        check("the Colour ideas card in a recipe has no search boxes and still has its own Start from drop-down (it works exactly as before)",
              not card_ids and page.evaluate("() => document.getElementById('colour-ideas-base').tagName") == "SELECT" and page.locator("#colour-ideas .list-search, #colour-ideas .combo").count() == 0, card_ids)
        check("and its lists are still all listed from the start (no short rule, no switch)", page.locator("#colour-ideas #starter-chips .chip").count() == 24 and page.locator("#colour-ideas .view-switch").count() == 0)

        # ---------- 5. Wheel groups ----------
        print("\n--- 5. Wheel groups ---")
        load(page, paints=GPAINTS)
        open_tab(page)
        heads_all = {}
        for part in PART_ORDER:
            tap(page, part)
            heads_all[part] = [g["heading"] for g in page.evaluate(GROUPS_JS)]
        want_heads = {part: [f"{g[2]} (1)" for g in GROUPS if g[0] == part] for part in PART_ORDER}
        check("every one of the ten wheel parts shows its two or three named groups as headings, each with its count, in this order (30 groups in all)", heads_all == want_heads, heads_all)
        check("every part has two or three groups", all(2 <= len([g for g in GROUPS if g[0] == part]) <= 3 for part in PART_ORDER) and len(GROUPS) == 30)
        wh = page.evaluate("() => WHEEL.map(w => [w.key, w.subs.map(s => s.label)])")
        check("the headings come from one list in the code (WHEEL) and match", [[k, labels] for k, labels in wh] == [[part, [g[2] for g in GROUPS if g[0] == part]] for part in PART_ORDER], wh)
        names_by = {}
        for part in PART_ORDER:
            tap(page, part)
            for g in page.evaluate(GROUPS_JS):
                names_by[(part, g["heading"].split(" (")[0])] = [r["name"] for r in g["rows"]]
        bad = [(part, key, label) for part, key, label, colour in GROUPS if names_by.get((part, label)) != [f"Probe {label}" if part != "metallic" else f"Probe {key} metal"]]
        check("each probe paint is in exactly its own group, one paint in each of the 30 groups", not bad, bad[:4])
        everything = [n for v_ in names_by.values() for n in v_]
        check("across the whole wheel every paint appears exactly once", sorted(everything) == sorted(COLOUR_OF), (len(everything), len(COLOUR_OF)))
        # where paints land, from the colour, and the edges
        table = [
            # red: deep under 0.3 lightness, light (0.62+) or a magenta-leaning mid red is pink
            (hx(0, .7, .27), "red/deep"), (hx(0, .7, .33), "red/red"), (hx(0, .7, .58), "red/red"), (hx(0, .7, .66), "red/pink"), (hx(335, .6, .45), "red/pink"),
            (hx(335, .6, .25), "red/deep"), (hx(350, .7, .45), "red/red"), (hx(325, .5, .35), "red/pink"), (hx(10, .6, .75), "red/pink"),
            # orange: browns are dark dull oranges, peach is light (0.66+)
            (hx(30, .6, .3), "orange/brown"), (hx(30, .9, .5), "orange/orange"), (hx(30, .9, .62), "orange/orange"), (hx(25, .9, .72), "orange/peach"), (hx(8, .4, .3), "orange/brown"),
            # yellow: mustard under 0.5 lightness, bone is pale and dull
            (hx(52, .8, .43), "yellow/mustard"), (hx(52, .8, .55), "yellow/yellow"), (hx(52, .8, .66), "yellow/yellow"), (hx(52, .3, .7), "yellow/bone"), (hx(45, .45, .8), "yellow/bone"),
            # green by hue: olive under 90, sea green from 150; dark olive is olive
            (hx(60, .5, .25), "green/olive"), (hx(80, .5, .4), "green/olive"), (hx(88, .5, .4), "green/olive"), (hx(92, .5, .4), "green/green"), (hx(120, .5, .4), "green/green"),
            (hx(148, .5, .4), "green/green"), (hx(152, .5, .4), "green/sea"), (hx(168, .5, .4), "green/sea"), (hx(100, .4, .8), "green/green"),
            # blue: navy under 0.3, light from 0.62
            (hx(220, .6, .2), "blue/navy"), (hx(220, .6, .28), "blue/navy"), (hx(220, .6, .33), "blue/blue"), (hx(220, .6, .6), "blue/blue"), (hx(220, .6, .66), "blue/light"),
            (hx(180, .5, .4), "blue/blue"), (hx(200, .7, .8), "blue/light"),
            # purple: deep under 0.3, lavender from 0.6
            (hx(270, .5, .27), "purple/deep"), (hx(270, .5, .33), "purple/violet"), (hx(270, .5, .57), "purple/violet"), (hx(270, .5, .63), "purple/lavender"), (hx(300, .4, .75), "purple/lavender"),
            # whites, greys, blacks by tint
            ("#ffffff", "white/neutral"), ("#f5f5f5", "white/neutral"), ("#f0eeef", "white/neutral"), ("#fff7cc", "white/warm"), ("#ffe3d8", "white/warm"), ("#e8eef2", "white/cool"), ("#d8f4e8", "white/cool"),
            ("#7f7f7f", "grey/neutral"), ("#5e5e5e", "grey/neutral"), ("#8f867a", "grey/warm"), ("#756566", "grey/warm"), ("#6c6e60", "grey/warm"), ("#7a8794", "grey/cool"), ("#6b707c", "grey/cool"), ("#6d8589", "grey/cool"),
            ("#0a0a0a", "black/neutral"), ("#0b0b0c", "black/neutral"), ("#2d1e01", "black/warm"), ("#24000e", "black/warm"), ("#0b1220", "black/cool"), ("#131e0d", "black/cool"),
            # parts that did not change
            ("#c9a227", "red/red") if False else ("#228b22", "green/green"), ("#2fb5a8", "blue/blue"),
        ]
        wrong = [(c, got, want) for c, want in table if (got := place(page, c)) != want]
        check(f"all {len(table)} test colours land in the right group, including both sides of every edge (lightness 0.3, 0.5, 0.62, 0.66; hue 90, 150; tint)", not wrong, wrong)
        names = [("#228b22", "Deep Purple Thing", "green/green"), ("#3b6fb0", "Violet Dream", "blue/blue"), ("#c1272d", "Pale Pink Paint", "red/red"), ("#7b2d8b", "Deep Purple", "purple/violet"),
                 ("#a9c6ec", "Deep Navy", "blue/light"), ("#0b1220", "Pure Black", "black/cool"), ("#8f867a", "Neutral Grey", "grey/warm"), ("#e8eef2", "Warm White", "white/cool")]
        wrong = [(c, n, got, want) for c, n, want in names if (got := place(page, c, n)) != want]
        check("a paint goes where its colour puts it, not where its name says (Deep Purple is a violet, Pure Black is a cool black, Warm White is a cool white)", not wrong, wrong)
        check("the metallic groups are as before (gold, silver, bronze), from a metal word, else from the colour",
              [place(page, "#c9a227", "Pale Gold"), place(page, "#b8bec6", "Steel Thing"), place(page, "#b4693a", "Copper Pot"), place(page, "#8d9299", "Test Metallic"), place(page, "#c8a06a", "Odd Shine", "metallic")]
              == ["metallic/gold", "metallic/silver", "metallic/bronze", "metallic/silver", "metallic/bronze"])
        check("the same colour always lands in the same group (no hidden state), and unknown colours and basing materials still land nowhere",
              place(page, "#3b6fb0", "A") == place(page, "#3b6fb0", "B") and place(page, "#808080", "Default") is None and place(page, "#888888", "Sand", "material") is None and place(page, "nonsense", "X") is None)
        # every group has built-in paints, nothing is outside the 30, counts add up
        cover = page.evaluate("""() => { const out = {}; let outside = 0; for (const x of wheelItems().filter(i => i.origin === 2)) { const w = WHEEL.find(s => s.key === x.at.seg); if (!w || !w.subs.some(s => s.key === x.at.sub)) outside++;
            out[x.at.seg + '/' + x.at.sub] = (out[x.at.seg + '/' + x.at.sub] || 0) + 1; } return { out, outside, total: wheelItems().filter(i => i.origin === 2).length }; }""")
        missing = [f"{g[0]}/{g[1]}" for g in GROUPS if cover["out"].get(f"{g[0]}/{g[1]}", 0) < 1]
        check(f"all 30 groups have built-in paints in them (none is empty), and no built-in paint falls outside a group ({cover['total']} paints)", not missing and cover["outside"] == 0, (missing, cover["outside"]))
        check("no group is a dump: none has more than 70% of its part", all(max(v for k, v in cover["out"].items() if k.startswith(part + "/")) <= 0.7 * sum(v for k, v in cover["out"].items() if k.startswith(part + "/"))
                                                                          for part in PART_ORDER if part not in ("white", "black")), cover["out"])
        # the description says what the groups are
        tap(page, "purple")
        check("the open part says what its groups are (Split into deep purple, violet and lavender and lilac. Each group runs from dark to light, yours first.)",
              page.inner_text("#cmp-wheel-groups") == "Split into deep purple, violet and lavender and lilac. Each group runs from dark to light, yours first.", page.inner_text("#cmp-wheel-groups"))
        tap(page, "grey")
        check("the neutral parts explain warm and cool in their description", "Warm greys lean brown or yellow, cool greys lean blue or green" in page.inner_text("#cmp-wheel-detail"))
        tap(page, "grey")
        # dark to light, yours first, marked, and short by default
        mine = [P(300 + i, f"Own Blue {i:02d}", hx(220, .6, .35 + (11 - i) * .01)) for i in range(12)]   # 12 owned blues in Blues, lightest first by name
        wish = P(320, "Wish Blue X", hx(220, .6, .36), "wishlist")
        pal = mine + [wish, P(321, "Empty Blue X", hx(220, .6, .37), "empty"), P(322, "Own Navy", hx(220, .6, .2)), P(323, "Own Sky", hx(220, .6, .8))]
        load(page, paints=pal)
        open_tab(page)
        tap(page, "blue")
        groups = page.evaluate(GROUPS_JS)
        by = {g["heading"].split(" (")[0]: g["rows"] for g in groups}
        blues = by["Blues"]
        check("Blues shows all 14 of your own paints in the group (the short limit never hides yours): 12 owned, then the wishlist, then the one that is not owned",
              len(blues) == 14 and [r["tag"] for r in blues] == ["You own this"] * 12 + ["On your wishlist", "In your palette, not owned"], [r["tag"] for r in blues])
        labs = page.evaluate("(cs) => cs.map(c => MinifolioColour.hexToLab(c).L)", [r["colour"] for r in blues[:12]])
        check("yours run dark to light inside the group (the names were made to run the other way, so this is the colour, not the name)", labs == sorted(labs) and [r["name"] for r in blues[:12]] == [f"Own Blue {i:02d}" for i in range(11, -1, -1)], [r["name"] for r in blues[:3]])
        check("the other groups hold their own: Navy has Own Navy and Sky has Own Sky", [r["name"] for r in by["Navy and deep blue"]] == ["Own Navy"] and [r["name"] for r in by["Sky and pale blue"]] == ["Own Sky"])
        check("the heading counts what the group holds (Blues (14))", [g["heading"] for g in groups] == ["Navy and deep blue (1)", "Blues (14)", "Sky and pale blue (1)"], [g["heading"] for g in groups])
        built_in = page.evaluate("() => wheelItems().filter(x => x.at.seg === 'blue' && x.origin === 2).length")
        per = page.evaluate("() => { const o = {}; for (const x of wheelItems().filter(i => i.at.seg === 'blue' && i.origin === 2)) o[x.at.sub] = (o[x.at.sub] || 0) + 1; return o; }")
        page.click("#cmp-wheel-others")
        page.wait_for_timeout(150)
        groups = page.evaluate(GROUPS_JS)
        by = {g["heading"].split(" (")[0]: g for g in groups}
        shown_counts = {k: len(g["rows"]) for k, g in by.items()}
        check("with the other paints on, each group shows only its first few: 8 or all of yours, whichever is more (Navy 8, Blues 14, Sky 8)", shown_counts == {"Navy and deep blue": 8, "Blues": 14, "Sky and pale blue": 8}, shown_counts)
        check("the headings count the whole group, not just what shows (yours + built-in)", {k.split(" (")[0]: int(k.split("(")[1].rstrip(")")) for k in [g["heading"] for g in groups]}
              == {"Navy and deep blue": per["navy"] + 1, "Blues": per["blue"] + 14, "Sky and pale blue": per["light"] + 1}, [g["heading"] for g in groups])
        btns = page.evaluate("""() => [...document.querySelectorAll('#cmp-wheel-detail button[id^="cmp-wheel-more-"]')].map(b => ({ id: b.id, text: b.textContent, label: b.getAttribute('aria-label'), exp: b.getAttribute('aria-expanded'), h: b.getBoundingClientRect().height }))""")
        check("each group with more has one button under its list: Show all N (with a longer spoken name), not expanded, 44 px tall",
              [b["id"] for b in btns] == ["cmp-wheel-more-navy", "cmp-wheel-more-blue", "cmp-wheel-more-light"]
              and btns[0]["text"] == f"Show all {per['navy'] + 1}" and btns[0]["label"] == f"Show all {per['navy'] + 1} navy and deep blue" and all(b["exp"] == "false" and b["h"] >= 44 for b in btns), btns)
        mine_rows = [r["name"] for r in by["Blues"]["rows"][:14]]
        check("in a group, yours always come before the built-in paints", all(r["tag"] != "Not in your palette" for r in by["Blues"]["rows"][:14]) and all(r["tag"] == "Not in your palette" for r in by["Navy and deep blue"]["rows"][1:]), mine_rows[:3])
        page.click("#cmp-wheel-more-blue")
        page.wait_for_timeout(150)
        rows_blue = page.evaluate(GROUPS_JS)[1]["rows"]
        check("Show all opens that group fully (and no other), the button now says Show fewer, is expanded, and keeps the focus",
              len(rows_blue) == per["blue"] + 14 and page.inner_text("#cmp-wheel-more-blue") == "Show fewer" and page.get_attribute("#cmp-wheel-more-blue", "aria-expanded") == "true"
              and page.evaluate("() => document.activeElement.id") == "cmp-wheel-more-blue" and len(page.evaluate(GROUPS_JS)[0]["rows"]) == 8, len(rows_blue))
        lights_built = page.evaluate("(cs) => cs.map(c => MinifolioColour.hexToLab(c).L)", [r["colour"] for r in rows_blue[14:]])
        check("the built-in paints in the group run dark to light too", lights_built == sorted(lights_built) and len(lights_built) == per["blue"], lights_built[:4])
        tap(page, "blue")
        tap(page, "blue")
        check("closing the part and opening it again keeps the group open (kept while the app is open)", page.inner_text("#cmp-wheel-more-blue") == "Show fewer")
        copy_spy(page)
        page.click("#cmp-wheel-detail .share-row button")
        text = copied(page)
        check("Copy as text keeps the headings and the paints that show (not the ones behind Show all)",
              text and "Navy and deep blue (" in text and "Blues (" in text and "Sky and pale blue (" in text and text.count("Not in your palette") == per["blue"] + 7 + 7, (text or "")[:200])
        page.click("#cmp-wheel-more-blue")
        page.wait_for_timeout(100)
        check("Show fewer puts the rest away again", len(page.evaluate(GROUPS_JS)[1]["rows"]) == 14)
        shot(page, "v37b-wheel-blue-390.png")
        # a group with few paints has no button; a group at exactly 8 has none
        load(page, paints=[P(400 + i, f"Eight {i}", hx(220, .6, .35 + i * .01)) for i in range(8)])
        open_tab(page)
        tap(page, "blue")
        check("a group of eight or fewer has no Show all button", page.locator('#cmp-wheel-detail button[id^="cmp-wheel-more-"]').count() == 0 and len(page.evaluate(GROUPS_JS)[0]["rows"]) == 8)
        load(page, paints=[])
        open_tab(page)
        tap(page, "purple")
        check("with an empty palette a part with no paints of yours says so, and the button shows the built-in ones in their groups",
              "You have none of these in your palette yet" in page.inner_text("#cmp-wheel-detail") and page.locator("#cmp-wheel-others").count() == 1)
        page.click("#cmp-wheel-others")
        page.wait_for_timeout(150)
        gs = page.evaluate(GROUPS_JS)
        check("then Purple shows Deep purple, Violet and Lavender and lilac, each with built-in paints", [g["heading"].split(" (")[0] for g in gs] == ["Deep purple", "Violet", "Lavender and lilac"] and all(len(g["rows"]) >= 1 for g in gs), [g["heading"] for g in gs])
        # every part, every group, built-in: heading counts equal the data
        counts_ok = []
        for part in PART_ORDER:
            tap(page, part)
            if page.locator("#cmp-wheel-others").get_attribute("aria-expanded") != "true":
                page.click("#cmp-wheel-others")
                page.wait_for_timeout(100)
            gs = page.evaluate(GROUPS_JS)
            want = page.evaluate("(p) => { const o = {}; for (const x of wheelItems().filter(i => i.at.seg === p)) o[x.at.sub] = (o[x.at.sub] || 0) + 1; return WHEEL.find(w => w.key === p).subs.filter(s => o[s.key]).map(s => s.label + ' (' + o[s.key] + ')'); }", part)
            counts_ok.append((part, [g["heading"] for g in gs] == want, max(len(g["rows"]) for g in gs) <= 8))
        check("for all ten parts, with the other paints on, the headings are the groups that have paints with the right counts, and no group lists more than 8 until Show all", all(a and b for _, a, b in counts_ok), counts_ok)

        # ---------- 6. Hostile text and the text scan ----------
        print("\n--- 6. Hostile text and the text scan ---")
        evil_paints = PAINTS + [P(90, HOSTILE, "#2244aa", brand=HOSTILE_BRAND), P(91, HOSTILE + " Gold", "#c9a227", brand=HOSTILE_BRAND), P(92, "Evil <i>Pink</i>", "#f4a6c0", brand=HOSTILE_BRAND)]
        evil_recipes = [rec(301, HOSTILE, "Armour", [90])]
        evil_units = [unit(1, HOSTILE, HOSTILE + " Host", [301])]
        load(page, paints=evil_paints, recipes=evil_recipes, units=evil_units)
        open_tab(page)
        open_all(page)
        copy_spy(page)
        page.click(BASE)
        page.fill(BASE, "evil")
        page.wait_for_timeout(100)
        evil_opts = option_texts(page, LIST)
        check("hostile paint names and brands in the Start from list are plain text (they show as typed) and no script runs",
              any("<img src=x" in o for o in evil_opts) and page.locator("#cmp-colour-ideas-base-list img, #cmp-colour-ideas-base-list b, #cmp-colour-ideas-base-list i, #cmp-colour-ideas-base-list script").count() == 0
              and page.evaluate("() => window.__pwned") is None, evil_opts[:2])
        pick_combo(page, BASE, value=page.evaluate("() => { const c = compendiumBaseChoices(); return c.key([...c.own, ...c.other].find(p => p.name.includes('Evil Blue') || p.name.includes('<img'))); }"))
        check("choosing it puts the text in the box as text, and the ideas below are plain text too",
              "<img src=x" in page.input_value(BASE) and page.locator("#view-compendium img, #view-compendium script, #view-compendium b, #view-compendium iframe").count() == 0 and page.evaluate("() => window.__pwned") is None)
        page.click(FT)
        check("a hostile faction name is plain text in the Faction list", any("<img src=x" in o for o in option_texts(page, FL)) and page.locator(f"{FL} img, {FL} b").count() == 0)
        page.keyboard.press("Escape")
        for q in [HOSTILE, HOSTILE_BRAND, '"><script>window.__pwned=3</script>', "<b>bold</b>", "&amp;&lt;"]:
            for sel in ("#cmp-starter-search", "#cmp-detail-search", "#cmp-basing-search", BASE, FB):
                page.click(sel)
                page.fill(sel, q)
                page.wait_for_timeout(40)
            page.keyboard.press("Escape")
        check("typing hostile text into every search box never makes markup or runs anything, and the No matches. lines never repeat it",
              page.locator("#view-compendium img, #view-compendium script, #view-compendium b, #view-compendium iframe").count() == 0 and page.evaluate("() => window.__pwned") is None
              and all("<" not in status(page, s) and "script" not in status(page, s).lower() for s in ("#cmp-starter-search-status", "#cmp-detail-search-status", "#cmp-basing-search-status", STAT, FS)))
        check("saved odd search text in the door's state is handled (a number, an empty list, a long string) without an error",
              (lambda: (page.evaluate("() => { compendiumState.search = { starter: 5, detail: null, basing: 'x'.repeat(5000) }; renderCompendium(); }"), page.wait_for_timeout(200), page.locator("#cmp-starter-search").count() == 1)[-1])())
        page.evaluate("() => { compendiumState.search = { starter: '', detail: '', basing: '' }; renderCompendium(); }")
        tap(page, "blue")
        tap(page, "blue")
        page.evaluate("() => { compendiumState.wheel = 'blue'; renderCompendium(); }")
        rows_ = page.evaluate(GROUPS_JS)
        check("hostile paint names in the wheel groups show as plain text and are in a group", any("<img src=x" in r["name"] for g in rows_ for r in g["rows"]) and page.locator("#cmp-wheel-detail img, #cmp-wheel-detail b, #cmp-wheel-detail script").count() == 0)
        check("the Copy as text for a wheel group has the hostile name as plain text too", (lambda: (page.click("#cmp-wheel-detail .share-row button"), "<img src=x" in (copied(page) or ""))[-1])())
        # the text scan over everything we wrote
        load(page, paints=GPAINTS, recipes=RECIPES, units=UNITS)
        open_tab(page)
        open_all(page)
        shown = []
        def grab():
            shown.append(page.evaluate("""() => { const c = document.getElementById('compendium-body').cloneNode(true);
                c.querySelectorAll('.idea-name, .combo-option, #cmp-faction-history-for').forEach(e => e.remove());
                return c.innerText + ' ' + [...c.querySelectorAll('[aria-label], title')].map(e => e.getAttribute('aria-label') || e.textContent).join(' ') + ' ' + [...c.querySelectorAll('input')].map(e => e.placeholder).join(' '); }"""))
        grab()
        for k in PART_ORDER:
            tap(page, k)
            grab()
            tap(page, k)
        page.click(BASE)
        page.fill(BASE, "zzzzqq")
        grab()
        page.fill(BASE, "")
        page.click(TOG)
        grab()
        page.keyboard.press("Escape")
        for key in ("starter", "detail", "basing"):
            page.click(f"#cmp-{key}-search")
            page.fill(f"#cmp-{key}-search", "zzzzz")
            grab()
            page.fill(f"#cmp-{key}-search", "a")
            grab()
        everything = "\n".join(shown)
        hits = GW_WORDS.findall(everything) + GW_MORE.findall(everything)
        check("everything we wrote for the search boxes and wheel groups (labels, placeholders, status lines, headings, descriptions, buttons) names no Games Workshop game, faction, scheme, paint or product",
              not hits and all(w in everything for w in ["Search starter schemes", "Search detail recipes", "Search basing tips", "Type or choose a paint", "Type or choose a faction", "No matches.", "Split into", "Warm blacks", "Lavender and lilac"]), (hits[:10], [w for w in ["Search starter schemes", "Search detail recipes", "Search basing tips", "Type or choose a paint", "Type or choose a faction", "No matches.", "Split into", "Warm blacks", "Lavender and lilac"] if w not in everything]))
        check("and none of it names a brand, a shop or a product", not BRAND_WORDS.findall(everything), BRAND_WORDS.findall(everything)[:10])
        own = "\n".join([joined, help_text, new_code])
        own_hits = GW_WORDS.findall(own) + GW_MORE.findall(own)
        check("the Updates entry, the Help line and the new code's own words are clean too", not own_hits and not BRAND_WORDS.findall(joined + help_text), own_hits[:10])
        check("there are no links at all in the new parts (no shop links, those come later)", page.locator("#compendium-body a, #compendium-body [href]").count() == 0)

        # ---------- 7. Offline ----------
        print("\n--- 7. Offline ---")
        load(page, paints=PAINTS, recipes=RECIPES, units=UNITS)
        mark = len(requests)
        open_tab(page)
        open_all(page)
        pick_combo(page, BASE, text="Macragge Blue (Citadel)")
        pick_combo(page, FB, text="Gloom Legion")
        type_into(page, "#cmp-starter-search", "blue")
        tap(page, "purple")
        outside = [u for u in requests[mark:] if not u.startswith(t.BASE) and not u.startswith("data:") and not u.startswith("blob:")]
        check("using the search boxes and the wheel groups makes no request to any other address", not outside, outside[:5])
        ctx.set_offline(True)
        pick_combo(page, BASE, text="Troll Slayer Orange (Citadel)")
        type_into(page, "#cmp-detail-search", "wet")
        tap(page, "blue")
        page.click("#cmp-wheel-others")
        check("it all works with the network off", page.input_value(BASE).startswith("Troll Slayer Orange") and page.locator("#cmp-detail-chips .chip").count() >= 1 and page.locator("#cmp-wheel-detail .idea-static").count() >= 1)
        ctx.set_offline(False)

        # ---------- 8. Phone widths ----------
        print("\n--- 8. Phone widths 360, 375, 390 and 400 ---")
        for width in (360, 375, 390, 400):
            page.set_viewport_size({"width": width, "height": 800})
            load(page, paints=PAINTS, recipes=RECIPES, units=UNITS)
            open_tab(page)
            open_all(page)
            geo = page.evaluate("""() => { const card = document.querySelector('#view-compendium .card').getBoundingClientRect();
                const rows = ['cmp-colour-ideas-base', 'cmp-faction-history-pick', 'cmp-starter-search', 'cmp-detail-search', 'cmp-basing-search'].map(id => { const i = document.getElementById(id), r = i.getBoundingClientRect(), row = i.parentElement.getBoundingClientRect();
                    const sib = [...i.parentElement.children].map(c => c.getBoundingClientRect()); return { id, h: r.height, w: r.width, inCard: row.left >= card.left - 0.5 && row.right <= card.right + 0.5, fits: sib.every(s => s.right <= row.right + 0.5), font: parseFloat(getComputedStyle(i).fontSize) }; });
                const tog = document.getElementById('cmp-colour-ideas-base-toggle').getBoundingClientRect();
                return { rows, tog: [tog.width, tog.height] }; }""")
            check(f"at {width} px every search box is at least 44 px tall, wider than 150 px, inside the card, with its buttons beside it, and the text is 16 px (so a phone does not zoom in)",
                  all(r["h"] >= 44 and r["w"] > 150 and r["inCard"] and r["fits"] and r["font"] >= 16 for r in geo["rows"]) and geo["tog"][0] >= 44 and geo["tog"][1] >= 44 and no_sideways(page), geo)
            page.click(BASE)
            page.wait_for_timeout(100)
            lst = page.evaluate("""() => { const l = document.getElementById('cmp-colour-ideas-base-list').getBoundingClientRect(), card = document.querySelector('#view-compendium .card').getBoundingClientRect();
                return { h: l.height, in: l.left >= card.left - 0.5 && l.right <= card.right + 0.5, vh: window.innerHeight, scrolls: document.getElementById('cmp-colour-ideas-base-list').scrollHeight > document.getElementById('cmp-colour-ideas-base-list').clientHeight }; }""")
            check(f"at {width} px the open list is inside the card, no taller than 300 px (so it is never most of the screen) and scrolls", lst["in"] and 100 < lst["h"] <= 300 and lst["scrolls"] and no_sideways(page), lst)
            type_into(page, BASE, "orange")
            check(f"at {width} px nothing scrolls sideways while typing in Start from", no_sideways(page))
            page.keyboard.press("Escape")
            page.fill("#cmp-starter-search", "gold")
            page.dispatch_event("#cmp-starter-search", "input")
            check(f"at {width} px nothing scrolls sideways with a search showing", no_sideways(page))
            load(page, paints=GPAINTS)
            open_tab(page)
            wrong = []
            for part in PART_ORDER:
                tap(page, part)
                bad = page.evaluate("""() => { const c = document.querySelector('#view-compendium .card').getBoundingClientRect(); return [...document.querySelectorAll('#cmp-wheel-detail *')].filter(e => { const r = e.getBoundingClientRect();
                    return r.width > 0 && (r.right > c.right + 0.5 || r.left < c.left - 0.5); }).map(e => e.className || e.tagName); }""")
                if bad or not no_sideways(page):
                    wrong.append((part, bad[:3]))
            check(f"at {width} px all ten wheel parts with their group headings fit inside the card and nothing scrolls sideways", not wrong, wrong)
            load(page, paints=pal)
            open_tab(page)
            tap(page, "blue")
            page.click("#cmp-wheel-others")
            page.click("#cmp-wheel-more-blue")
            page.wait_for_timeout(150)
            check(f"at {width} px the group with Show all open fits and nothing scrolls sideways", no_sideways(page) and page.evaluate("() => document.getElementById('cmp-wheel-more-blue').getBoundingClientRect().height") >= 44)
            if width in (360, 400):
                page.evaluate("() => window.scrollTo(0, 0)")
                shot(page, f"v37b-wheel-groups-{width}.png")
                page.evaluate("() => document.getElementById('cmp-wheel-detail').scrollIntoView()")
                shot(page, f"v37b-wheel-detail-{width}.png")
        page.set_viewport_size({"width": 390, "height": 844})
        # a real touch phone
        touch = browser.new_context(viewport={"width": 390, "height": 844}, has_touch=True, is_mobile=True, service_workers="block")
        tp = touch.new_page()
        tp.on("pageerror", lambda e: errors.append(str(e)))
        load(tp, paints=PAINTS, recipes=RECIPES, units=UNITS)
        open_tab(tp)
        open_all(tp)
        tp.tap(TOG)
        tp.wait_for_timeout(120)
        check("on a touch phone, tapping the button next to Start from opens the list without the keyboard (the box is not focused)", tp.get_attribute(BASE, "aria-expanded") == "true" and tp.evaluate("() => document.activeElement.id") != "cmp-colour-ideas-base")
        for _ in range(3):
            tp.evaluate("() => { const l = document.getElementById('cmp-colour-ideas-base-list'); l.scrollTop = l.scrollHeight; }")
            tp.wait_for_timeout(120)
        target = tp.locator(f"{LIST} [role=option]").nth(70)
        target_text = target.inner_text()
        target.scroll_into_view_if_needed()
        box = target.bounding_box()
        tp.touchscreen.tap(box["x"] + box["width"] / 2, box["y"] + box["height"] / 2)
        tp.wait_for_timeout(250)
        check("on a touch phone, scrolling the list and tapping a line far down picks that paint", tp.input_value(BASE) == target_text and tp.get_attribute(BASE, "aria-expanded") == "false", (tp.input_value(BASE), target_text))
        tp.tap("#cmp-starter-search")
        tp.keyboard.type("blue")
        tp.wait_for_timeout(100)
        check("on a touch phone, typing in a list search box shows the matches", tp.locator("#cmp-starter-chips .chip").count() >= 1 and tp.evaluate("() => document.activeElement.id") == "cmp-starter-search")
        tp.tap("#cmp-starter-chips .chip")
        tp.wait_for_timeout(150)
        check("and tapping a match shows the scheme's paints", tp.locator("#cmp-starter-list .idea-static").count() == 4)
        touch.close()

        # ---------- 9. Dark and light ----------
        print("\n--- 9. Dark and light, 390 and 360 px ---")
        for appearance in ("dark", "light"):
            for width in (390, 360):
                page.set_viewport_size({"width": width, "height": 844})
                load(page, paints=PAINTS, recipes=RECIPES, units=UNITS, settings={"appearance": appearance})
                open_tab(page)
                open_all(page)
                pick_combo(page, FB, text="Gloom Legion")
                page.click(BASE)
                page.fill(BASE, "blue")
                page.keyboard.press("ArrowDown")
                page.keyboard.press("ArrowDown")
                page.wait_for_timeout(100)
                type_into(page, "#cmp-starter-search", "blue")
                tag = f"{appearance} {width}px"
                col = page.evaluate("""() => { const bg = (el) => { let e = el; while (e) { const v = getComputedStyle(e).backgroundColor; const m = v.match(/rgba\\(.*,\\s*([\\d.]+)\\)/);
                        if (v && v !== 'transparent' && !(m && parseFloat(m[1]) < 0.9)) return v; e = e.parentElement; } return 'rgb(0,0,0)'; };
                    const out = {};
                    const pairs = [['label', 'label[for="cmp-colour-ideas-base"]'], ['input text', '#cmp-colour-ideas-base'], ['option', '#cmp-colour-ideas-base-list [role=option]:not(.is-active)'],
                                   ['active option', '#cmp-colour-ideas-base-list .is-active'], ['group heading', '#cmp-colour-ideas-base-list .combo-group'], ['status', '#cmp-colour-ideas-base-status'],
                                   ['toggle', '#cmp-colour-ideas-base-toggle'], ['search text', '#cmp-starter-search'], ['search label', 'label[for="cmp-starter-search"]'], ['search status', '#cmp-starter-search-status'],
                                   ['clear', '#cmp-starter-search-clear'], ['faction text', '#cmp-faction-history-pick']];
                    for (const [k, s] of pairs) { const el = document.querySelector(s); if (el) out[k] = [getComputedStyle(el).color, bg(el)]; }
                    const ph = document.getElementById('cmp-starter-search'); ph.value = ''; out['placeholder'] = [getComputedStyle(ph, '::placeholder').color, bg(ph)];
                    return out; }""")
                bad = {k: round(contrast(rgb(v[0]), rgb(v[1])), 2) for k, v in col.items() if contrast(rgb(v[0]), rgb(v[1])) < 4.5}
                check(f"{tag}: the labels, the typed text, the list lines, headings, the highlighted line, the status lines, the placeholder and the buttons all have contrast of at least 4.5", not bad and len(col) >= 12, (bad, len(col)))
                ring = page.evaluate("""() => { const el = document.querySelector('#cmp-colour-ideas-base-list .is-active'); const cs = getComputedStyle(el); const card = getComputedStyle(document.querySelector('#view-compendium .card')).backgroundColor;
                    const listbg = getComputedStyle(document.getElementById('cmp-colour-ideas-base-list')).backgroundColor; return { outline: cs.outlineColor, listbg, card, input: getComputedStyle(document.getElementById('cmp-colour-ideas-base')).borderColor }; }""")
                check(f"{tag}: the highlighted line has an outline you can see (contrast 3 or more against the list)", contrast(rgb(ring["outline"]), rgb(ring["listbg"])) >= 3, ring)
                page.focus("#cmp-starter-search")
                fo = page.evaluate("() => { const cs = getComputedStyle(document.getElementById('cmp-starter-search')); return [cs.borderTopColor, 'solid', 2, cs.boxShadow]; }")
                check(f"{tag}: a box that has the focus shows the accent border like every other box in the app (contrast 3 or more against the card)", fo[1] != "none" and fo[2] >= 2 and contrast(rgb(fo[0]), rgb(ring["card"])) >= 3, fo)
                check(f"{tag}: nothing scrolls sideways", no_sideways(page))
                shot(page, f"v37b-search-{appearance}-{width}.png")
                page.keyboard.press("Escape")
                load(page, paints=GPAINTS, settings={"appearance": appearance})
                open_tab(page)
                tap(page, "purple")
                col2 = page.evaluate("""() => { const bg = (el) => { let e = el; while (e) { const v = getComputedStyle(e).backgroundColor; const m = v.match(/rgba\\(.*,\\s*([\\d.]+)\\)/);
                        if (v && v !== 'transparent' && !(m && parseFloat(m[1]) < 0.9)) return v; e = e.parentElement; } return 'rgb(0,0,0)'; };
                    const out = {}; for (const [k, s] of [['group heading', '#cmp-wheel-detail .wheel-sub'], ['groups line', '#cmp-wheel-groups'], ['row why', '#cmp-wheel-detail .idea-why'], ['tag', '#cmp-wheel-detail .idea-tag']]) {
                        const el = document.querySelector(s); if (el) out[k] = [getComputedStyle(el).color, bg(el)]; } return out; }""")
                bad2 = {k: round(contrast(rgb(v[0]), rgb(v[1])), 2) for k, v in col2.items() if contrast(rgb(v[0]), rgb(v[1])) < 4.5}
                check(f"{tag}: the wheel group headings, the groups line and the rows have contrast of at least 4.5", not bad2 and len(col2) >= 4, (bad2, len(col2)))
                shot(page, f"v37b-wheel-{appearance}-{width}.png")
        page.set_viewport_size({"width": 390, "height": 844})

        # ---------- 10. Nothing else changed ----------
        print("\n--- 10. Nothing else changed ---")
        load(page, paints=PAINTS, recipes=RECIPES, units=UNITS)
        open_tab(page)
        ring = page.evaluate("() => [...document.querySelectorAll('#cmp-wheel path.wheel-seg')].map(e => e.getAttribute('d'))")
        digest = hashlib.sha256("|".join(ring).encode()).hexdigest()[:16]
        check("the ring picture is exactly as before: the same ten slices in the same order with the same shapes", len(ring) == 10 and digest == "566f183642b86302", (digest, len(ring)))
        check("the wheel still has the same hint line, caption and ten slices in the same order",
              page.inner_text("#cmp-wheel-hint") == "Tap a colour to see what's in it" and page.evaluate("() => [...document.querySelectorAll('#cmp-wheel path.wheel-seg')].map(e => e.dataset.wheel)") == PART_ORDER)
        check("the five folding parts and their order are as in part 1", page.evaluate("() => [...document.querySelectorAll('#compendium-body > section.fold .fold-button')].map(b => b.firstElementChild.textContent)") == ["Colour ideas", "Your schemes", "Starter schemes", "Detail recipes", "Basing tips"])
        check("no page id appears twice with everything open and a wheel part showing", (lambda: (open_all(page), tap(page, "orange"), page.click(BASE), page.keyboard.press("Escape"),
              page.evaluate("() => { const ids = [...document.querySelectorAll('[id]')].map(e => e.id); return ids.filter((x, i) => ids.indexOf(x) !== i); }") == [])[-1])())
        check("every id the new boxes add starts with cmp- (so the recipe editor can never clash)", page.evaluate("() => [...document.querySelectorAll('#compendium-body [id]')].every(e => e.id.startsWith('cmp-'))"))
        check("DATA_VERSION is still 1 and the three storage names are unchanged", page.evaluate("DATA_VERSION") == 1
              and all(k in app for k in ['STORAGE_KEY = "mini-tracker-models"', 'SETTINGS_KEY = "shades-of-grey-settings"', 'RECIPES_KEY = "shades-of-grey-recipes"']))
        policy = re.search(r'http-equiv="Content-Security-Policy"\s+content="([^"]+)"', html)
        hosts = set(re.findall(r"https?://[^\s;'\"]+", policy.group(1) if policy else ""))
        check("the security policy is untouched: the only outside address is still the one GoatCounter picture address", len(hosts) == 1 and "goatcounter" in list(hosts)[0], hosts)
        check("no page error and no unexpected dialog during all of this", not errors and not dialogs, (errors[:3], dialogs[:3]))
        browser.close()

    print(f"\n{sum(results)}/{len(results)} checks passed")
    sys.exit(0 if all(results) else 1)

if __name__ == "__main__":
    main()
