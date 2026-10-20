"""v51 tests for Minifolio (declutter chunk D4b: tick boxes in the Compendium).

What changed (Compendium tab only; the recipe editor's Colour ideas card is unchanged):
 (a) The paint rows in Starter schemes, Your schemes and Detail recipes have a 44 px tick box at the left, and a "Select all" row sits
     above each list.
 (b) Under the list is the one "Add to shopping list" button. Nothing ticked: the small greyed button with a one-line hint. Something
     ticked: a full-width primary button showing the count. It adds only the ticked paints (one message, one Undo).
 (c) Copy as text and Save into a new recipe stay, equal width, and use the ticked paints when any are ticked, otherwise all of them.
 (d) Paints you own (running low counts) or that are already on the list show their status mark where the tick box would be; the row's
     More info says why. The v42 "Shopping list" fold-out under each scheme is gone (the tick boxes do its job).
 (e) Ticks live only while the app is open. Nothing is saved.

Checks:
1. Versions and the v51 Updates entry.
2. Starter schemes: tick boxes, Select all, the greyed and primary button, Copy and Save with and without ticks.
3. Adding: only the ticked paints, one message, one Undo, nothing else saved, ticks not saved.
4. Owned, running low and already listed paints.
5. Detail recipes and Your schemes.
6. The recipe editor is unchanged.
7. Hostile text, and what the new code is (and is not) allowed to contain.
8. Layout at 360, 390 and 1000 px, dark and light, targets and contrast.
9. No page errors, no browser pop-ups.
Run all tests with `python3 tests/run_all.py`, or serve the repo folder and run this file on its own."""
import os, re, sys
from playwright.sync_api import sync_playwright

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from notice_watch import attach_notices
from combo_helpers import pick_combo
import test_v31 as t
import test_v35 as c
import test_v42 as w   # load, stored, toast, basket, by_name, scheme_paints, P, undo

URL, read = t.URL, t.read
results = []
KEY = w.SCHEME_KEY
BASE = "#cmp-starter-schemes"
LIST = "#cmp-starter-list"
ID = f"cmp-starter-{KEY}"

def check(name, ok, detail=""):
    results.append(bool(ok))
    print(("PASS " if ok else "FAIL ") + name + ("" if ok else f"  -> {detail}"))

def box(loc):
    return loc.bounding_box()

def tap(page, selector, nth=0):
    """Scroll to the middle of the screen first, so the fixed tab bar is never over the thing, then tap it."""
    loc = page.locator(selector).nth(nth)
    loc.evaluate("e => e.scrollIntoView({ block: 'center' })")
    page.wait_for_timeout(60)
    loc.click()
    page.wait_for_timeout(80)

def open_scheme(page, key=KEY):
    c.open_comp(page)
    c.cmp_pick(page, "starter-chips", key)
    page.wait_for_timeout(100)

ROWS_JS = """(s) => [...document.querySelectorAll(s + ' > li')].map(li => {
    const slot = li.querySelector('.pick-slot'), tick = slot && slot.querySelector(':scope > .pick-tick');
    return { name: li.querySelector('.idea-name').childNodes[0].textContent,
             tick: !!tick, checked: tick ? tick.getAttribute('aria-checked') : null,
             marker: slot && slot.querySelector(':scope > .status-marker') ? slot.querySelector(':scope > .status-marker').className : '',
             why: (li.querySelector('.more-info-panel > .hint:last-child') || {}).textContent || '' }; })"""

def rows(page, scope=LIST):
    return page.evaluate(ROWS_JS, scope)

def pick_state(page, pid=ID, base=BASE):
    return page.evaluate("""([pid, base]) => { const all = document.getElementById('cmp-' + pid.replace('cmp-', '') + '-all') || document.getElementById(pid + '-all');
        const add = document.getElementById(pid + '-add'), idle = document.getElementById(pid + '-idle');
        return { all: all ? all.getAttribute('aria-checked') : null, allDisabled: all ? all.getAttribute('aria-disabled') : null,
                 add: add && add.isConnected ? add.textContent : '', idle: !!(idle && idle.isConnected),
                 hint: (document.getElementById(pid + '-idle-hint') || {}).textContent || '' }; }""", [pid, base])

CONTRAST_JS = """([sel, prop, ownBg]) => {
    const el = document.querySelector(sel);
    const parse = (s) => { const m = s.match(/[\\d.]+/g).map(Number); return [m[0], m[1], m[2], m.length > 3 ? m[3] : 1]; };
    const lin = (v) => { v /= 255; return v <= 0.03928 ? v / 12.92 : Math.pow((v + 0.055) / 1.055, 2.4); };
    const L = (c) => 0.2126 * lin(c[0]) + 0.7152 * lin(c[1]) + 0.0722 * lin(c[2]);
    const bgOf = (start) => { let n = start; while (n) { const b = parse(getComputedStyle(n).backgroundColor); if (b[3] > 0.95) return b; n = n.parentElement; } return [255, 255, 255, 1]; };
    const fg = parse(getComputedStyle(el)[prop]);
    const bg = bgOf(ownBg ? el : el.parentElement);
    const a = L(fg), b = L(bg);
    return (Math.max(a, b) + 0.05) / (Math.min(a, b) + 0.05); }"""

def contrast(page, sel, prop="color", own=True):
    return page.evaluate(CONTRAST_JS, [sel, prop, own])

def all_local(page):
    return page.evaluate("() => JSON.stringify(Object.keys(localStorage).sort().map(k => [k, localStorage.getItem(k)]))")

def main():
    errors, dialogs = [], []
    app, html = read("app.js"), read("index.html")
    with sync_playwright() as p:
        browser = p.chromium.launch()
        ctx = browser.new_context(viewport={"width": 390, "height": 844}, service_workers="block")
        page = ctx.new_page()
        page.on("pageerror", lambda e: errors.append(str(e)))
        page.on("dialog", lambda d: (dialogs.append(d.message), d.dismiss()))
        attach_notices(page, dialogs.append)

        # ---------- 1. Versions ----------
        print("\n--- 1. Versions and wording ---")
        w.load(page, paints=[])
        version = page.evaluate("APP_VERSION")
        check("APP_VERSION is v51 or later", float(version[1:]) >= 51, version)
        m = re.search(r'const VERSION = "v([\d.]+)"', read("sw.js"))
        check("sw.js VERSION matches", m and "v" + m.group(1) == version)
        tags = re.findall(r'<script src="[^"]+\?v=(\d+)"', html)
        check("all six script tags carry the version number", len(tags) == 6 and set(tags) == {version[1:]}, tags)
        entry = page.evaluate("CHANGELOG.find(c => c.version === 'v51')")
        check("the v51 Updates entry exists (v52 and v53 may sit above it)", bool(entry) and page.evaluate("CHANGELOG[0].version") in ("v51", "v52", "v53"))
        check("the v51 entry has no em dashes", entry and not any("—" in x for x in entry["changes"]))
        check("the v51 entry mentions tick boxes, Select all and Undo", entry and all(any(word in x for x in entry["changes"]) for word in ("tick box", "Select all", "Undo")))
        check("the v50 and v49 Updates entries are still there", page.evaluate("['v50', 'v49'].every(v => !!CHANGELOG.find(r => r.version === v))"))

        # ---------- 2. Starter schemes ----------
        print("\n--- 2. Starter schemes: tick boxes ---")
        w.load(page, paints=[], settings={"appearance": "dark"})
        c.open_comp(page)
        check("with no scheme picked there is the greyed button and its old hint",
              page.locator(".shop-idle-button").count() == 1 and "Select a scheme to generate a shopping list" in page.locator(".shop-idle .hint").inner_text())
        c.cmp_pick(page, "starter-chips", KEY)
        page.wait_for_timeout(100)
        sp = w.scheme_paints(page)
        scheme_name = page.evaluate("(k) => STARTER_SCHEMES.find(s => s.key === k).name", KEY)
        n = len(sp)
        check("(set-up) the scheme lists four paints", n == 4, n)
        rs = rows(page)
        check("every paint row has a tick box, none ticked", len(rs) == n and all(r["tick"] and r["checked"] == "false" for r in rs), rs)
        ticks = page.locator(f"{LIST} .pick-tick")
        check("each tick box is a real button with role checkbox", page.evaluate(f"() => [...document.querySelectorAll('{LIST} .pick-tick')].every(b => b.tagName === 'BUTTON' && b.type === 'button' && b.getAttribute('role') === 'checkbox')"))
        bb = box(ticks.first)
        check("each tick box is at least 44 by 44 px", all(box(ticks.nth(i))["width"] >= 43.5 and box(ticks.nth(i))["height"] >= 43.5 for i in range(n)), bb)
        check("the tick box is at the left of the row (left of the colour swatch)",
              page.evaluate(f"() => {{ const li = document.querySelector('{LIST} > li'); return li.querySelector('.pick-tick').getBoundingClientRect().right <= li.querySelector('.swatch').getBoundingClientRect().left + 1; }}"))
        check("a tick box is named by the row's own paint name (aria-labelledby), with no aria-label",
              page.evaluate(f"() => [...document.querySelectorAll('{LIST} > li')].every(li => {{ const b = li.querySelector('.pick-tick'); const id = b.getAttribute('aria-labelledby'); const el = id && document.getElementById(id); return !b.hasAttribute('aria-label') && el && el === li.querySelector('.idea-name'); }})"))
        sa = page.locator(f"#{ID}-all")
        check("a Select all row sits above the list, as a real checkbox button",
              sa.count() == 1 and sa.get_attribute("role") == "checkbox" and sa.evaluate("e => e.tagName") == "BUTTON" and sa.get_attribute("aria-checked") == "false" and "Select all" in sa.inner_text())
        check("Select all is above the paint list", page.evaluate(f"() => {{ const a = document.getElementById('{ID}-all'), l = document.querySelector('{LIST}'); return !!(a.compareDocumentPosition(l) & Node.DOCUMENT_POSITION_FOLLOWING); }}"))
        check("Select all is at least 44 px tall", box(sa)["height"] >= 43.5, box(sa))
        ps = pick_state(page)
        check("nothing ticked: the small greyed Add to shopping list button is shown", ps["idle"] and ps["add"] == "")
        idle = page.locator(f"#{ID}-idle")
        check("it is marked disabled for assistive tech and does nothing", idle.get_attribute("aria-disabled") == "true")
        check("its hint now says paints", ps["hint"] == "Select paints to generate a shopping list", ps["hint"])
        check("the old v42 Shopping list fold-out is gone", page.locator("#compendium-body .scheme-shop").count() == 0)
        check("the order is: list, then the Add button, then Copy and Save",
              page.evaluate(f"() => {{ const kids = [...document.querySelector('{BASE}').children]; const i = kids.findIndex(k => k.id === 'cmp-starter-list'), j = kids.findIndex(k => k.classList.contains('pick-actions')), k2 = kids.findIndex(k => k.classList.contains('share-row')); return i >= 0 && j === i + 1 && k2 === j + 1; }}"))
        # Copy and Save with nothing ticked use everything
        c.copy_spy(page)
        tap(page, f"{BASE} .share-row .plain-button", 0)
        txt = c.copied(page) or ""
        check("Copy as text with nothing ticked copies every paint of the scheme", all(x["name"] in txt for x in sp) and scheme_name in txt, txt[:200])
        check("and keeps the footnote", "only a guide" in txt)
        a, b2 = box(page.locator(f"{BASE} .share-row .plain-button").nth(0)), box(page.locator(f"{BASE} .share-row .plain-button").nth(1))
        check("Copy as text and Save into a new recipe are equal width", abs(a["width"] - b2["width"]) <= 2, (a["width"], b2["width"]))
        # tick one
        before_all = all_local(page)
        tap(page, f"{LIST} .pick-tick", 1)
        rs = rows(page)
        check("tapping the second tick box ticks only that row", [r["checked"] for r in rs] == ["false", "true", "false", "false"], rs)
        ps = pick_state(page)
        check("Select all shows the in-between state", ps["all"] == "mixed", ps)
        check("the greyed button is replaced by a primary button showing the count", ps["add"] == "Add to shopping list (1)" and not ps["idle"], ps)
        addb = page.locator(f"#{ID}-add")
        card_w = box(page.locator(f"{BASE} .pick-actions"))["width"]
        check("the primary button is full width and at least 44 px tall", addb.get_attribute("class").find("primary-button") >= 0 and box(addb)["width"] >= card_w - 2 and box(addb)["height"] >= 43.5, (box(addb), card_w))
        check("ticking changed nothing that is saved (storage is identical)", all_local(page) == before_all)
        check("focus stayed on the tick box that was tapped", page.evaluate(f"() => document.activeElement === document.querySelectorAll('{LIST} .pick-tick')[1]"))
        c.copy_spy(page)
        tap(page, f"{BASE} .share-row .plain-button", 0)
        txt = c.copied(page) or ""
        check("Copy as text now copies only the ticked paint", sp[1]["name"] in txt and not any(sp[i]["name"] in txt for i in (0, 2, 3)) and scheme_name in txt, txt[:240])
        # keyboard: a tick box toggles with the space bar and keeps focus
        ticks.nth(2).focus()
        page.keyboard.press("Space")
        rs = rows(page)
        check("the space bar ticks a box, and focus stays on it", rs[2]["checked"] == "true" and page.evaluate(f"() => document.activeElement === document.querySelectorAll('{LIST} .pick-tick')[2]"), rs)
        check("the count follows (2)", pick_state(page)["add"] == "Add to shopping list (2)")
        # Select all
        tap(page, f"#{ID}-all")
        ps = pick_state(page)
        check("Select all ticks every paint, and says so", all(r["checked"] == "true" for r in rows(page)) and ps["all"] == "true" and ps["add"] == f"Add to shopping list ({n})", ps)
        tap(page, f"#{ID}-all")
        ps = pick_state(page)
        check("Select all again clears them, and the greyed button comes back", all(r["checked"] == "false" for r in rows(page)) and ps["all"] == "false" and ps["idle"], ps)
        # ticks are kept while the part is closed and opened again, but only while the app is open
        tap(page, f"{LIST} .pick-tick", 0)
        tap(page, "#cmp-fold-starter-button")
        tap(page, "#cmp-fold-starter-button")
        check("closing and reopening the part keeps the ticks (while the app is open)", [r["checked"] for r in rows(page)] == ["true", "false", "false", "false"], rows(page))
        page.reload(); page.wait_for_function("() => typeof APP_VERSION === 'string'"); page.wait_for_timeout(300)
        open_scheme(page)
        check("after the app is reopened nothing is ticked", all(r["checked"] == "false" for r in rows(page)), rows(page))
        # Save into a new recipe with two ticked
        tap(page, f"{LIST} .pick-tick", 0)
        tap(page, f"{LIST} .pick-tick", 3)
        tap(page, f"{BASE} .share-row .plain-button", 1)
        page.wait_for_timeout(250)
        steps = page.evaluate("() => recipeDraft ? recipeDraft.steps.map(s => s.paints[0].name) : null")
        check("Save into a new recipe starts a recipe with only the two ticked paints", steps == [sp[0]["name"], sp[3]["name"]], steps)

        # ---------- 3. Adding ----------
        print("\n--- 3. Adding the ticked paints ---")
        w.load(page, paints=[])
        open_scheme(page)
        before_json = w.stored_json(page)
        tap(page, f"{LIST} .pick-tick", 0)
        tap(page, f"{LIST} .pick-tick", 2)
        tap(page, f"#{ID}-add")
        page.wait_for_timeout(250)
        tt = w.toast(page)
        st = w.stored(page)
        check("the message says 2 paints were added and there is one Undo", tt["text"] == "Added 2 paints to your shopping list" and tt["undo"] == "Undo", tt)
        added = [w.by_name(st, sp[i]["name"]) for i in (0, 2)]
        check("only the two ticked paints joined the palette, as Wishlist, with the scheme as their source",
              all(r and r.get("status") == "wishlist" and r.get("shopFrom") == [f"Scheme: {scheme_name}"] for r in added) and len(st) == 2, st)
        check("the paints that were not ticked were not added", w.by_name(st, sp[1]["name"]) is None and w.by_name(st, sp[3]["name"]) is None)
        check("the basket says 2", w.basket(page) == "2", w.basket(page))
        check("no tick state or other new key was saved", "ticks" not in w.stored_json(page) and "pick" not in w.stored_json(page).lower().replace("picked", ""))
        rs = rows(page)
        check("the two added rows now show the Wishlist mark instead of a tick box", all((not rs[i]["tick"]) and "s-wishlist" in rs[i]["marker"] for i in (0, 2)), rs)
        check("the other two still have tick boxes, unticked", all(rs[i]["tick"] and rs[i]["checked"] == "false" for i in (1, 3)), rs)
        check("the added rows' More info says why they cannot be ticked", all("already on your shopping list" in rs[i]["why"] for i in (0, 2)), [r["why"] for r in rs])
        ps = pick_state(page)
        check("the ticks were cleared and the greyed button is back", ps["idle"] and ps["all"] == "false", ps)
        check("focus moved to Select all (the button it was on is gone)", page.evaluate(f"() => document.activeElement && document.activeElement.id === '{ID}-all'"))
        w.undo(page)
        tt = w.toast(page)
        check("one Undo puts everything back exactly (the saved palette is identical)", w.stored_json(page) == before_json)
        check("a short message says how many came off, with no second Undo", tt["text"] == "Took 2 paints off your shopping list again." and tt["undo"] is False, tt)
        check("the basket is gone again", w.basket(page) == "", w.basket(page))
        rs = rows(page)
        check("after Undo every row is tickable again, unticked", all(r["tick"] and r["checked"] == "false" and not r["marker"] for r in rs), rs)
        # Select all then Add
        tap(page, f"#{ID}-all")
        tap(page, f"#{ID}-add")
        page.wait_for_timeout(250)
        st = w.stored(page)
        check("Select all then Add puts every paint of the scheme on the list, once each",
              len(st) == n and all(r["status"] == "wishlist" for r in st) and w.toast(page)["text"] == f"Added {n} paints to your shopping list", st)
        check("with nothing left to tick, Select all is disabled and the greyed button shows",
              pick_state(page)["allDisabled"] == "true" and pick_state(page)["idle"])

        # ---------- 4. Owned, running low, already listed ----------
        print("\n--- 4. Paints you own or have listed ---")
        base = [dict(brand=x["brand"], name=x["name"], colour=x["colour"]) for x in sp]
        pal = [w.P(1, base[0]["name"], base[0]["colour"], "owned", brand=base[0]["brand"]),
               w.P(2, base[1]["name"], base[1]["colour"], "low", brand=base[1]["brand"]),
               w.P(3, base[2]["name"], base[2]["colour"], "wishlist", brand=base[2]["brand"], shopFrom=["Recipe: Earlier"])]
        w.load(page, paints=pal)
        open_scheme(page)
        rs = rows(page)
        check("an owned paint shows the Owned mark, not a tick box", not rs[0]["tick"] and "s-owned" in rs[0]["marker"], rs[0])
        check("a running low paint shows the Running low mark, not a tick box", not rs[1]["tick"] and "s-low" in rs[1]["marker"], rs[1])
        check("a paint already on the list shows the Wishlist mark, not a tick box", not rs[2]["tick"] and "s-wishlist" in rs[2]["marker"], rs[2])
        check("the fourth paint can be ticked", rs[3]["tick"] and rs[3]["checked"] == "false", rs[3])
        check("More info says why for an owned paint", "You own this paint" in rs[0]["why"], rs[0]["why"])
        check("More info says why for a running low paint", "running low" in rs[1]["why"], rs[1]["why"])
        check("More info says why for a listed paint", "already on your shopping list" in rs[2]["why"], rs[2]["why"])
        check("the reason is in the row's More info, hidden until it is opened (no new helper text on the page)",
              page.evaluate(f"() => [...document.querySelectorAll('{LIST} > li')].slice(0, 3).every(li => li.querySelector('.more-info-panel').hidden)") and
              page.evaluate(f"() => document.querySelectorAll('#cmp-fold-starter-panel > .pick-actions .hint, {BASE} > .hint').length") <= 1)
        marker_box = page.evaluate(f"() => {{ const m = document.querySelector('{LIST} > li .pick-slot > .status-marker'); return m ? m.parentElement.getBoundingClientRect().width : 0; }}")
        check("the mark sits in the same 44 px slot where the tick box would be", marker_box >= 43.5, marker_box)
        tap(page, f"#{ID}-all")
        ps = pick_state(page)
        check("Select all ticks only the one paint that can be ticked", [r["checked"] for r in rows(page)] == [None, None, None, "true"] and ps["all"] == "true" and ps["add"] == "Add to shopping list (1)", (rows(page), ps))
        c.copy_spy(page)
        tap(page, f"{BASE} .share-row .plain-button", 0)
        txt = c.copied(page) or ""
        check("Copy as text then copies just that paint", base[3]["name"] in txt and not any(base[i]["name"] in txt for i in (0, 1, 2)), txt[:200])
        tap(page, f"#{ID}-add")
        page.wait_for_timeout(250)
        st = w.stored(page)
        check("the message says 1 paint (singular)", w.toast(page)["text"] == "Added 1 paint to your shopping list", w.toast(page))
        check("the owned, running low and listed paints were not touched",
              w.by_name(st, base[0]["name"])["status"] == "owned" and "shopFrom" not in w.by_name(st, base[0]["name"])
              and w.by_name(st, base[1]["name"])["status"] == "low" and "shopFrom" not in w.by_name(st, base[1]["name"])
              and w.by_name(st, base[2]["name"])["shopFrom"] == ["Recipe: Earlier"])
        pal_all = [w.P(i + 1, x["name"], x["colour"], "owned", brand=x["brand"]) for i, x in enumerate(base)]
        w.load(page, paints=pal_all)
        open_scheme(page)
        ps = pick_state(page)
        check("when you own every paint, Select all is disabled, no row has a tick box and the greyed button shows",
              ps["allDisabled"] == "true" and ps["idle"] and not any(r["tick"] for r in rows(page)), (ps, rows(page)))
        before = w.stored_json(page)
        page.locator(f"#{ID}-all").dispatch_event("click")   # Playwright will not click a control marked aria-disabled, so send the tap straight to it
        page.wait_for_timeout(100)
        check("tapping the disabled Select all does nothing", pick_state(page)["idle"] and w.stored_json(page) == before)

        # ---------- 5. Detail recipes and Your schemes ----------
        print("\n--- 5. Detail recipes and Your schemes ---")
        w.load(page, paints=[])
        c.open_comp(page)
        rkey = page.evaluate("DETAIL_RECIPES[0].key")
        rname = page.evaluate("DETAIL_RECIPES[0].name")
        c.cmp_pick(page, "detail-chips", rkey)
        page.wait_for_timeout(100)
        did = f"cmp-detail-{rkey}"
        drs = rows(page, "#cmp-detail-list")
        check("Detail recipes: every step row has a tick box", len(drs) >= 3 and all(r["tick"] and r["checked"] == "false" for r in drs), drs)
        check("Detail recipes: a Select all row and the greyed button are there", page.locator(f"#{did}-all").count() == 1 and page.locator(f"#{did}-idle").count() == 1)
        check("Detail recipes: Copy as text and Save are equal width",
              abs(box(page.locator("#cmp-detail-recipes .share-row .plain-button").nth(0))["width"] - box(page.locator("#cmp-detail-recipes .share-row .plain-button").nth(1))["width"]) <= 2)
        tap(page, "#cmp-detail-list .pick-tick", 1)
        check("Detail recipes: ticking shows the count", pick_state(page, did)["add"] == "Add to shopping list (1)", pick_state(page, did))
        c.copy_spy(page)
        tap(page, "#cmp-detail-recipes .share-row .plain-button", 0)
        txt = c.copied(page) or ""
        check("Detail recipes: Copy as text uses the ticked step only", "Step 2" in txt and "Step 1" not in txt and rname in txt, txt[:240])
        tap(page, f"#{did}-add")
        page.wait_for_timeout(250)
        st = w.stored(page)
        check("Detail recipes: one paint was added, with 'Detail recipe: <name>' as its source",
              len(st) == 1 and st[0]["status"] == "wishlist" and st[0]["shopFrom"] == [("Detail recipe: " + rname)[:60]], st)
        # Your schemes
        pals = [dict(p_) for p_ in t.PAINTS]
        for p_ in pals:
            if p_["id"] in (22, 8):
                p_["status"] = "notowned"
        w.load(page, paints=pals, recipes=t.RECIPES, units=t.UNITS)
        c.open_comp(page)
        pick_combo(page, "#cmp-faction-history-pick", text="Gloom Legion")
        page.wait_for_timeout(150)
        hid = page.evaluate("() => document.querySelector('#cmp-faction-history .pick-all').id.replace('-all', '')")
        hrs = rows(page, "#cmp-faction-history-list")
        free = [r for r in hrs if r["tick"]]
        check("Your schemes: rows have tick boxes where you do not own the paint, status marks where you do", len(hrs) >= 3 and len(free) >= 1 and len(free) < len(hrs), hrs)
        check("Your schemes: the old Shopping list fold-out is gone", page.locator("#cmp-faction-history .scheme-shop").count() == 0)
        tap(page, f"#{hid}-all")
        ps = pick_state(page, hid)
        check("Your schemes: Select all counts only the paints you do not own", ps["add"] == f"Add to shopping list ({len(free)})", (ps, len(free)))
        tap(page, f"#{hid}-add")
        page.wait_for_timeout(250)
        st = w.stored(page)
        newly = [w.by_name(st, r["name"]) for r in free]
        check("Your schemes: they are on the list with the faction's name as the source",
              all(r and r.get("status") == "wishlist" and r.get("shopFrom") == ["Scheme: Gloom Legion colours"] for r in newly), newly)

        # ---------- 6. The recipe editor is unchanged ----------
        print("\n--- 6. The recipe editor ---")
        w.load(page, paints=[dict(p_) for p_ in t.PAINTS], recipes=t.RECIPES, units=t.UNITS)
        t.open_editor(page) if hasattr(t, "open_editor") else None
        page.evaluate("() => { const d = document.querySelector('details.colour-ideas'); if (d) d.open = true; }")
        page.wait_for_timeout(500)
        check("(set-up) the Colour ideas card is open in the recipe editor", page.locator("#colour-ideas .starter-schemes").count() >= 1 or page.locator("details.colour-ideas[open]").count() >= 1)
        check("the recipe editor's Colour ideas has no tick boxes, no Select all and no greyed shopping button",
              page.locator("#colour-ideas .pick-tick, #colour-ideas .pick-all, #colour-ideas .pick-actions, #colour-ideas .shop-idle").count() == 0)

        # ---------- 7. Hostile text and the code ----------
        print("\n--- 7. Hostile text and the code ---")
        pals = [dict(p_) for p_ in t.PAINTS]
        for p_ in pals:
            if p_["id"] == 22:
                p_["name"], p_["brand"], p_["status"] = t.HOSTILE, t.HOSTILE_BRAND, "notowned"
        w.load(page, paints=pals, recipes=t.RECIPES, units=t.UNITS)
        c.open_comp(page)
        pick_combo(page, "#cmp-faction-history-pick", text="Gloom Legion")
        page.wait_for_timeout(150)
        check("a paint named with HTML shows as plain text in its row (no picture, no bold)",
              page.locator("#cmp-faction-history-list img, #cmp-faction-history-list b, #cmp-faction-history-list script").count() == 0 and
              any(t.HOSTILE in (r["name"] + "") or "Evil" in r["name"] for r in rows(page, "#cmp-faction-history-list")))
        hid = page.evaluate("() => document.querySelector('#cmp-faction-history .pick-all').id.replace('-all', '')")
        tap(page, f"#{hid}-all")
        tap(page, f"#{hid}-add")
        page.wait_for_timeout(250)
        check("adding it ran no script and changed no page element", page.evaluate("() => window.__pwned === undefined"))
        check("the tick box of that paint is labelled by its row name element, not by a copy of the text in an attribute",
              page.evaluate("() => [...document.querySelectorAll('#cmp-faction-history-list .pick-tick')].every(b => !b.hasAttribute('aria-label') && !(b.getAttribute('title') || '').includes('Evil'))"))
        # code scans
        a = app.index("function buildPick(")
        end = app.index("function buildIdeaItem(")
        helpers = app[app.index("let pickSeq = 0;"):end]
        check("the new helpers sit before the code the v36 and v37 tests scan",
              a < app.index("v36: THE COLOUR WHEEL") and a < app.index("v37: one folding part"))
        check("the new helpers have no network code, no storage, no innerHTML and no links",
              not re.search(r"\bfetch\s*\(|XMLHttpRequest|sendBeacon|WebSocket|localStorage|sessionStorage|\beval\s*\(|new Function|insertAdjacentHTML|outerHTML|innerHTML|createElement\(['\"]a['\"]\)|href", helpers))
        check("the new helpers set no aria-label (a paint name could end up in one)", not re.search(r"setAttribute\(\s*[\"']aria-label[\"']", helpers))
        check("the new helpers save nothing (no save() call, no settings)", not re.search(r"\bsave\s*\(|saveSettings|settings\.", helpers))
        css = html[html.index("/* v51: tick boxes"):html.index(".pick-add {")]
        check("the new CSS uses theme variables only (no hard-coded colours)", not re.search(r"#[0-9a-fA-F]{3,8}\b|rgba?\(|hsla?\(", css), re.findall(r"#[0-9a-fA-F]{3,8}\b|rgba?\(", css))
        check("the old fold-out is gone from the code and the styles", "buildSchemeShopFoldout" not in app and ".scheme-shop" not in html)

        # ---------- 8. Layout, targets and contrast ----------
        print("\n--- 8. Layout, dark and light ---")
        for mode in ("dark", "light"):
            for width, height in ((360, 780), (390, 844), (1000, 900)):
                page.set_viewport_size({"width": width, "height": height})
                w.load(page, paints=[], settings={"appearance": mode})
                page.set_viewport_size({"width": width, "height": height})
                open_scheme(page)
                tap(page, f"{LIST} .pick-tick", 0)
                tag = f"{mode} {width} px"
                check(f"{tag}: no sideways scrolling", t.no_sideways(page))
                tb = [box(page.locator(f"{LIST} .pick-tick").nth(i)) for i in range(4)]
                check(f"{tag}: tick boxes are at least 44 px and inside the screen", all(b_["width"] >= 43.5 and b_["height"] >= 43.5 and b_["x"] >= 0 and b_["x"] + b_["width"] <= width for b_ in tb), tb[0])
                a_, b_ = box(page.locator(f"{BASE} .share-row .plain-button").nth(0)), box(page.locator(f"{BASE} .share-row .plain-button").nth(1))
                check(f"{tag}: Copy as text and Save are equal width", abs(a_["width"] - b_["width"]) <= 2, (a_["width"], b_["width"]))
                check(f"{tag}: the Add button spans the same width as the two buttons under it",
                      abs(box(page.locator(f"#{ID}-add"))["width"] - (b_["x"] + b_["width"] - a_["x"])) <= 3, (box(page.locator(f"#{ID}-add")), a_, b_))
                if width == 390:
                    check(f"{tag}: Select all text contrast is at least 4.5", contrast(page, f"#{ID}-all > span:last-child", "color", False) >= 4.5, contrast(page, f"#{ID}-all > span:last-child", "color", False))
                    check(f"{tag}: the Add button text contrast is at least 4.5", contrast(page, f"#{ID}-add") >= 4.5, contrast(page, f"#{ID}-add"))
                    check(f"{tag}: the tick box outline stands out from the row (at least 3:1)", contrast(page, f"{LIST} > li:nth-child(2) .pick-box", "borderTopColor", False) >= 3, contrast(page, f"{LIST} > li:nth-child(2) .pick-box", "borderTopColor", False))
                    tap(page, f"#{ID}-all")
                    tap(page, f"#{ID}-all")
                    check(f"{tag}: the greyed button's text and hint contrast is at least 4.5",
                          contrast(page, f"#{ID}-idle", "color", False) >= 4.5 and contrast(page, f"#{ID}-idle-hint", "color", False) >= 4.5,
                          (contrast(page, f"#{ID}-idle", "color", False), contrast(page, f"#{ID}-idle-hint", "color", False)))
                    page.evaluate(f"() => document.querySelector('{BASE}').scrollIntoView()")
                    t.shot(page, f"v51-{mode}-{width}.png")

        # every theme, dark and light: the new text and outlines stay readable
        for theme in page.evaluate("Object.keys(THEMES)"):
            for mode in ("dark", "light"):
                w.load(page, paints=[], settings={"theme": theme, "appearance": mode})
                open_scheme(page)
                tap(page, f"{LIST} .pick-tick", 0)
                lows = {
                    "Select all": contrast(page, f"#{ID}-all > span:last-child", "color", False),
                    "Add button": contrast(page, f"#{ID}-add"),
                    "tick outline": contrast(page, f"{LIST} > li:nth-child(2) .pick-box", "borderTopColor", False),
                }
                need = {"Select all": 4.5, "Add button": 4.5, "tick outline": 3}
                check(f"{theme}, {mode}: Select all and the Add button text are at least 4.5:1, the tick outline at least 3:1",
                      all(lows[k] >= need[k] for k in lows), lows)
                tap(page, f"{LIST} .pick-tick", 0)   # untick, so the greyed button shows
                grey = (contrast(page, f"#{ID}-idle", "color", False), contrast(page, f"#{ID}-idle-hint", "color", False))
                check(f"{theme}, {mode}: the greyed button and its hint are at least 4.5:1", min(grey) >= 4.5, grey)

        # ---------- 9. Clean run ----------
        print("\n--- 9. A clean run ---")
        check("no page errors", not errors, errors[:2])
        other = [d for d in dialogs if not d.startswith(("Took ", "Started a new recipe", "Nothing added"))]   # the app's own plain notices from this test are expected
        check("no browser pop-ups (only this test's own plain notices appeared)", not other, other[:2])
        browser.close()
    failed = results.count(False)
    print(f"\n{len(results) - failed} passed, {failed} failed")
    sys.exit(1 if failed else 0)

if __name__ == "__main__":
    main()
