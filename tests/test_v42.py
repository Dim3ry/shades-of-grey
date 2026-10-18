"""v42 tests for Minifolio (Shopping 2, part B): the scheme buttons in the Compendium.

What changed:
 - In the Compendium, Starter schemes and Your schemes each get a small, closed "Shopping list" fold-out under their paints.
   Inside is one button, "Add paints to shopping list".
 - It puts every paint of the scheme that you do NOT have on the one shared shopping list, remembering "Scheme: <name>".
   Owned and running-low paints are skipped, paints already on the list are not added twice, and a paint that is only in the built-in
   list is added to your palette as Wishlist (exactly like the single Add).
 - One message says how many were added; one Undo puts everything back (and says how many came off). If nothing needed adding it says so,
   with no Undo. The basket count and the "On your shopping list" markers stay right after every add and Undo.
 - It is not a shop button (it only writes to your own list), so Settings -> Shop links does not hide it.
 - The recipe's Colour ideas card is unchanged.

Checks:
1. Versions, Updates entry, nothing else touched (no new address, no Games Workshop words, shop links and the Pro preview label unchanged).
2. Starter schemes: closed and quiet by default; add, message, sources, Wishlist, basket, markers, Undo, nothing-to-add.
3. Skips: owned, running low and already-listed paints are left alone; nothing is added twice.
4. Your schemes: the same, with the faction's name as the source.
5. Shop links off: the button, the list and the basket stay.
6. The recipe card has no such fold-out.
7. Hostile text (text-injection test): scheme, faction, paint and brand names full of HTML stay plain text; sources are cut to 60 characters.
8. Phones and looks: 360 and 390 px, dark and light, no sideways scroll.
Run all tests with `python3 tests/run_all.py`, or serve the repo folder and run this file on its own."""
import json, os, re, subprocess, sys
from playwright.sync_api import sync_playwright

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from notice_watch import attach_notices
from combo_helpers import pick_combo
import test_v31 as t
import test_v35 as c   # Compendium helpers (open every part)
import wheel_helpers as wh   # v43
import test_v39 as h   # wheel helpers

SHOTS, ROOT = t.SHOTS, t.ROOT
read, load, blur = t.read, t.load, t.blur
shot, no_sideways = t.shot, t.no_sideways
HOSTILE, HOSTILE_BRAND = t.HOSTILE, t.HOSTILE_BRAND
GW_WORDS = t.GW_WORDS
results = []

def check(name, ok, detail=""):
    results.append(bool(ok))
    print(("PASS " if ok else "FAIL ") + name + ("" if ok else f"  -> {detail}"))

LISTED = "On your shopping list"
P = h.P
SCHEME_KEY = "blue-gold"   # a built-in starter scheme (four colours, plain words)

def basket(page):
    return page.evaluate("() => { const b = document.getElementById('basket-button'); return b.classList.contains('hidden') ? '' : b.textContent.trim(); }")

def toast(page):
    return page.evaluate("() => ({ text: document.getElementById('toast-text').textContent, kids: document.getElementById('toast-text').children.length, "
                         "undo: !document.getElementById('toast-undo').classList.contains('hidden') && document.getElementById('toast-undo').textContent, "
                         "shown: !document.getElementById('toast').classList.contains('hidden') })")

def stored(page):
    return page.evaluate("() => JSON.parse(localStorage.getItem('shades-of-grey-recipes')).paints")

def stored_json(page):
    return page.evaluate("() => localStorage.getItem('shades-of-grey-recipes')")

def scheme_paints(page, key=SCHEME_KEY):
    """The paints the scheme shows right now: [{brand, name, colour}] (what the Compendium would list)."""
    return page.evaluate("""(k) => starterSchemePaints(STARTER_SCHEMES.find(s => s.key === k)).map(x => ({ brand: x.hit.paint.brand, name: x.hit.paint.name, colour: x.hit.paint.colour, owned: !!x.hit.owned }))""", key)

def open_scheme(page, key=SCHEME_KEY, **kw):
    c.open_comp(page)
    c.cmp_pick(page, "starter-chips", key)
    page.wait_for_timeout(100)

def fold(page, scope="#cmp-starter-schemes"):
    return page.evaluate("""(s) => { const d = document.querySelector(s + ' details.scheme-shop');
        if (!d) return null;
        const b = d.querySelector('button');
        return { open: d.open, summary: d.querySelector('summary').textContent, say: d.querySelector('.shop-add .hint').textContent, button: b ? b.textContent : '' }; }""", scope)

def centre(page, selector):
    """Scroll the thing to the middle of the screen first, so the fixed tab bar at the bottom is never over it."""
    page.evaluate("(s) => document.querySelector(s).scrollIntoView({ block: 'center' })", selector)
    page.wait_for_timeout(80)

def open_fold(page, scope="#cmp-starter-schemes"):
    if not page.evaluate("(s) => document.querySelector(s + ' details.scheme-shop').open", scope):
        centre(page, f"{scope} details.scheme-shop > summary")
        page.click(f"{scope} details.scheme-shop > summary")
        page.wait_for_timeout(100)

def press_add(page, scope="#cmp-starter-schemes"):
    open_fold(page, scope)
    centre(page, f"{scope} details.scheme-shop button")
    page.click(f"{scope} details.scheme-shop button")
    page.wait_for_timeout(250)

def undo(page):
    page.click("#toast-undo")
    page.wait_for_timeout(300)

def wheel_tags(page):
    """name -> tag for every paint row in the wheel's lists, tapping each of the ten parts in turn (v41 markers)."""
    out = {}
    for key in ["red", "orange", "yellow", "green", "blue", "purple", "white", "grey", "black", "metallic"]:
        h.open_tab(page)
        if key in wh.HUES:   # v43: a colour opens its groups first, so look at each of its three groups in turn
            rows = [r for group in wh.open_each_group(page, key, lambda pg: pg.evaluate("() => [...document.querySelectorAll('#cmp-wheel-detail ul.idea-list > li')].map(li => [li.querySelector('.idea-name').childNodes[0].textContent, li.querySelector('.idea-tag').textContent])")) for r in group]
        else:
            h.tap(page, key)
            rows = page.evaluate("() => [...document.querySelectorAll('#cmp-wheel-detail ul.idea-list > li')].map(li => [li.querySelector('.idea-name').childNodes[0].textContent, li.querySelector('.idea-tag').textContent])")
            h.tap(page, key)   # close it again
        for name, tag in rows:
            out.setdefault(name, tag)
    return out

def by_name(paints, name):
    return next((p for p in paints if p["name"] == name), None)

def main():
    with sync_playwright() as p:
        browser = p.chromium.launch()
        ctx = browser.new_context(viewport={"width": 390, "height": 844}, service_workers="block")
        page = ctx.new_page()
        errors, dialogs = [], []
        page.on("pageerror", lambda e: errors.append(str(e)))
        page.on("dialog", lambda d: (dialogs.append(d.message), d.dismiss()))
        attach_notices(page, dialogs.append)

        # ---------- 1. Versions and what did not change ----------
        print("\n--- 1. Versions and what did not change ---")
        load(page, paints=[])
        html, sw = read("index.html"), read("sw.js")
        tags = re.findall(r'<script src="([^"]+)\?v=(\d+)"', html)
        check("the version is v42 or v43 in APP_VERSION, sw.js and all six script tags",
              page.evaluate("APP_VERSION") in ("v42", "v43", "v44") and re.search(r'const VERSION = "v([\d.]+)"', sw).group(1) in ("42", "43", "44") and len(tags) == 6 and len({v for _, v in tags}) == 1 and tags[0][1] in ("42", "43", "44"),
              (page.evaluate("APP_VERSION"), tags))
        check("the two comments that name the number (in index.html and app.js) carry the same 42, 43 or 44", re.search(r'The "\?v=(42|43|44)" makes', html) and re.search(r'e\.g\. "app\.js\?v=(42|43|44)"', read("app.js")))
        entry = page.evaluate("CHANGELOG.slice(0, 3).find(e => e.version === 'v42')")
        joined = " ".join(entry["changes"]) if entry else ""
        check("the v42 Updates entry (newest, or second newest once v43 is out) tells about the Add paints button, Undo, the same list and Shop links",
              entry and all(w in joined for w in ("Add paints to shopping list", "Undo", "same shopping list", "Shop links")), joined[:120])
        diff = subprocess.run(["git", "diff", "main", "--", "app.js"], cwd=ROOT, capture_output=True, text=True).stdout
        added = [l[1:] for l in diff.splitlines() if l.startswith("+") and not l.startswith("+++")]
        removed = [l[1:] for l in diff.splitlines() if l.startswith("-") and not l.startswith("---")]
        code_added = [re.sub(r"\s//\s.*$", "", l) for l in added if not l.strip().startswith("//")]
        check("no new web address, network call or storage in the new code",
              not any(re.search(r"https?:|fetch\(|XMLHttpRequest|localStorage|indexedDB|WebSocket|sendBeacon", l) for l in code_added if "w3.org/2000/svg" not in l), [l for l in code_added if "http" in l and "w3.org/2000/svg" not in l][:2])
        check("nothing was added that writes page text from variables (no innerHTML, insertAdjacentHTML or outerHTML)",
              not any(re.search(r"innerHTML|insertAdjacentHTML|outerHTML|document\.write|eval\(", l) for l in code_added))
        check("no Games Workshop word in anything added", not [l for l in added if GW_WORDS.search(l)], [l for l in added if GW_WORDS.search(l)][:2])
        check("the shop links, the shop table and the Pro preview label were not touched",
              not any(re.search(r"shopLink\(|SHOPS|shopsFor|SHOP_PLAIN_WORDS|Pro preview|pro-pill", l) for l in added + removed), [l for l in added + removed if re.search(r"shopLink\(|SHOPS|shopsFor|SHOP_PLAIN_WORDS|Pro preview|pro-pill", l)][:2])
        check("buildShopFoldout and addToShoppingList (the single Add) were not changed",
              not any(re.search(r"function buildShopFoldout|function addToShoppingList|add\.addEventListener\(\"click\", \(\) => \{ if \(addToShoppingList", l) for l in removed))
        html_diff = subprocess.run(["git", "diff", "main", "--", "index.html"], cwd=ROOT, capture_output=True, text=True).stdout
        html_changed = [l[1:] for l in html_diff.splitlines() if l[:1] in "+-" and not l.startswith(("+++", "---"))]
        check("index.html only changed the version number (so no security-policy entry was added or changed)",
              all(re.search(r"\?v=\d+|wheel|sr-only|help-tabs|v43|v44|restore|example|^\s*</div>\s*$", l) for l in html_changed) and not any("Content-Security-Policy" in l for l in html_changed), html_changed[:3])   # v43 changed the wheel styles, Help words and the live line on purpose
        check("no new file in the repo", subprocess.run(["git", "status", "--short"], cwd=ROOT, capture_output=True, text=True).stdout.count("??") <= 1)   # only this test file

        # ---------- 2. Starter schemes ----------
        print("\n--- 2. Starter schemes ---")
        load(page, paints=[])   # every paint then comes from the built-in list
        open_scheme(page)
        sp = scheme_paints(page)
        scheme_name = page.evaluate("(k) => STARTER_SCHEMES.find(s => s.key === k).name", SCHEME_KEY)
        f = fold(page)
        check("the scheme has a closed 'Shopping list' fold-out under its paints (quiet by default)", f and f["open"] is False and f["summary"] == "Shopping list", f)
        check("the fold-out sits under the paint list and above Copy as text",
              page.evaluate("""() => { const b = document.getElementById('cmp-starter-schemes'); const kids = [...b.children];
                const i = kids.findIndex(k => k.id === 'cmp-starter-list'), j = kids.findIndex(k => k.classList.contains('scheme-shop')); return j === i + 1; }"""))
        check("closed: its button is not visible until you open it", not page.locator("#cmp-starter-schemes details.scheme-shop button").is_visible())
        check("it says how many paints are not on the list yet", f and f["say"].startswith(f"{len(sp)} paints in this scheme are not on your shopping list yet"), f)
        check("the rows themselves look as before (no extra button or line on a row)",
              page.evaluate("() => [...document.querySelectorAll('#cmp-starter-list > li')].every(li => !li.querySelector('.scheme-shop'))"))
        before_json = stored_json(page)
        check("nothing is on the list to begin with and the basket is hidden", basket(page) == "" and not any(p_.get("status") == "wishlist" for p_ in stored(page)))
        press_add(page)
        tt = toast(page)
        st = stored(page)
        added_rows = [by_name(st, x["name"]) for x in sp]
        check("the message says how many were added (4 paints) and there is an Undo", tt["text"] == f"Added {len(sp)} paints to your shopping list" and tt["undo"] == "Undo", tt)
        check("every paint of the scheme is now in the palette as Wishlist (they were only in the built-in list)",
              all(r and r.get("status") == "wishlist" and r.get("owned") is False for r in added_rows), added_rows)
        check("each remembers 'Scheme: <name>' as its one source", all(r["shopFrom"] == [f"Scheme: {scheme_name}"] for r in added_rows), [r.get("shopFrom") for r in added_rows])
        check("one entry per paint (no duplicates in the palette)", len({(p_["brand"], p_["name"]) for p_ in st}) == len(st) == len(sp), len(st))
        check("the basket count is right", basket(page) == str(len(sp)), basket(page))
        f2 = fold(page)
        check("the fold-out now says there is nothing to add and the button has gone, still in the same place",
              f2 and f2["open"] is True and f2["button"] == "" and f2["say"].startswith("Nothing to add"), f2)
        check("focus moved to the message (the button it was on is gone)", page.evaluate("() => document.activeElement && document.activeElement.classList.contains('hint') && !!document.activeElement.closest('.scheme-shop')"))
        tags = wheel_tags(page)
        listed = [x["name"] for x in sp if x["name"] in tags]
        check("the wheel's lists say On your shopping list for those paints (markers stay right)", listed and all(tags[n_] == LISTED for n_ in listed), {n_: tags.get(n_) for n_ in listed})
        h.open_tab(page)
        page.click("#cmp-fold-starter-button") if page.get_attribute("#cmp-fold-starter-button", "aria-expanded") != "true" else None
        page.click('nav button[data-tab="recipes"]')
        page.wait_for_timeout(200)
        page.click('#recipe-seg [data-view="shopping"]')
        page.wait_for_timeout(150)
        text = page.inner_text("#shop-panel")
        check("the Shopping list shows each paint once, saying from Scheme: <name>",
              all(text.count(x["name"]) == 1 for x in sp) and text.count(f"from Scheme: {scheme_name}") >= 1, text[:240])
        check("Copy as text keeps the words", f"(from Scheme: {scheme_name}" in page.evaluate("() => shoppingText(shoppingItems())"))
        # Undo, straight after an add
        load(page, paints=[])
        open_scheme(page)
        before_json = stored_json(page)
        press_add(page)
        undo(page)
        tt = toast(page)
        check("Undo puts everything back exactly as it was (the saved palette is identical)", stored_json(page) == before_json)
        check("a short message says how many came off, with no second Undo", tt["text"] == f"Took {len(sp)} paints off your shopping list again." and tt["undo"] is False, tt)
        check("the basket is gone again", basket(page) == "", basket(page))
        f3 = fold(page)
        check("after Undo the fold-out offers the button again with the right count", f3 and f3["button"] == "Add paints to shopping list" and f3["say"].startswith(f"{len(sp)} paints"), f3)
        tags = wheel_tags(page)
        check("after Undo the wheel's markers are gone too", all(tags.get(x["name"]) != LISTED for x in sp if x["name"] in tags), {n_: tags.get(n_) for n_ in tags if tags[n_] == LISTED})
        # a second press (add, then add again): nothing twice
        load(page, paints=[])
        open_scheme(page)
        press_add(page)
        n_after = len(stored(page))
        res = page.evaluate("""(k) => addSchemePaintsToShoppingList(starterSchemePaints(STARTER_SCHEMES.find(s => s.key === k)).map(x => x.hit.paint), 'Scheme: again')""", SCHEME_KEY)
        tt = toast(page)
        check("pressing it again adds nothing: it says so plainly and there is no Undo",
              res == 0 and tt["text"].startswith("Nothing added") and tt["undo"] is False, (res, tt))
        st = stored(page)
        check("the paints are still on the list once, and the second name was not added",
              len(st) == n_after and all(r["shopFrom"] == [f"Scheme: {scheme_name}"] for r in st), [r.get("shopFrom") for r in st])
        check("the basket still says 4", basket(page) == str(len(sp)), basket(page))

        # ---------- 3. Skips ----------
        print("\n--- 3. Skips (owned, running low, already listed) ---")
        base = [dict(brand=x["brand"], name=x["name"], colour=x["colour"]) for x in sp]
        pal = [P(1, base[0]["name"], base[0]["colour"], "owned", brand=base[0]["brand"]),
               P(2, base[1]["name"], base[1]["colour"], "low", brand=base[1]["brand"]),
               P(3, base[2]["name"], base[2]["colour"], "wishlist", brand=base[2]["brand"], shopFrom=["Recipe: Earlier"])]
        load(page, paints=pal)
        open_scheme(page)
        sp2 = scheme_paints(page)
        check("(set-up) the scheme still lists the same four paints, with yours first", [x["name"] for x in sp2] == [x["name"] for x in sp], [x["name"] for x in sp2])
        f = fold(page)
        check("only the one paint that is neither owned, running low nor listed is counted", f and f["say"].startswith("1 paint in this scheme is not on your shopping list yet"), f)
        press_add(page)
        tt = toast(page)
        st = stored(page)
        check("the message says 1 paint was added (singular)", tt["text"] == "Added 1 paint to your shopping list" and tt["undo"] == "Undo", tt)
        check("the owned paint is untouched (still owned, no source)", by_name(st, base[0]["name"])["status"] == "owned" and "shopFrom" not in by_name(st, base[0]["name"]))
        check("the running-low paint is untouched (still low, no source)", by_name(st, base[1]["name"])["status"] == "low" and "shopFrom" not in by_name(st, base[1]["name"]))
        check("the paint already on the list is untouched (one entry, its old source kept, no scheme name added)",
              by_name(st, base[2]["name"])["status"] == "wishlist" and by_name(st, base[2]["name"])["shopFrom"] == ["Recipe: Earlier"] and sum(1 for p_ in st if p_["name"] == base[2]["name"]) == 1)
        new = by_name(st, base[3]["name"])
        check("the fourth paint (only in the built-in list) joined the palette as Wishlist with the scheme as its source", new and new["status"] == "wishlist" and new["shopFrom"] == [f"Scheme: {scheme_name}"], new)
        check("the basket counts the three list paints (the running-low one, the old wishlist one and the new one)", basket(page) == "3", basket(page))
        undo(page)
        check("Undo removes only what this button added (the old wishlist paint stays, the basket says 2)",
              by_name(stored(page), base[3]["name"]) is None and by_name(stored(page), base[2]["name"])["status"] == "wishlist" and basket(page) == "2", basket(page))
        # nothing to add at all: everything owned
        pal_all = [P(i + 1, x["name"], x["colour"], "owned", brand=x["brand"]) for i, x in enumerate(base)]
        load(page, paints=pal_all)
        open_scheme(page)
        f = fold(page)
        check("when you own every paint, the fold-out says nothing to add and has no button", f and f["button"] == "" and f["say"].startswith("Nothing to add"), f)
        before_json = stored_json(page)
        res = page.evaluate("""(k) => addSchemePaintsToShoppingList(starterSchemePaints(STARTER_SCHEMES.find(s => s.key === k)).map(x => x.hit.paint), 'Scheme: x')""", SCHEME_KEY)
        tt = toast(page)
        check("asking anyway adds nothing, says so plainly, shows no Undo and saves nothing new",
              res == 0 and tt["text"].startswith("Nothing added") and tt["undo"] is False and stored_json(page) == before_json, (res, tt))

        # ---------- 4. Your schemes ----------
        print("\n--- 4. Your schemes ---")
        pals = [dict(p_) for p_ in t.PAINTS]
        for p_ in pals:
            if p_["id"] in (22, 8):
                p_["status"] = "notowned"   # Mid Blue A and Ink Sky: used by the faction's recipes, but not owned
        load(page, paints=pals, recipes=t.RECIPES, units=t.UNITS)
        c.open_comp(page)
        pick_combo(page, "#cmp-faction-history-pick", text="Gloom Legion")
        page.wait_for_timeout(150)
        hist = page.evaluate("() => [...document.querySelectorAll('#cmp-faction-history-list .idea-static')].map(li => [li.querySelector('.idea-name').childNodes[0].textContent, li.querySelector('.idea-tag').textContent])")
        f = fold(page, "#cmp-faction-history")
        check("Your schemes has the same closed 'Shopping list' fold-out", f and f["open"] is False and f["summary"] == "Shopping list", f)
        names_h = [x[0] for x in hist]
        todo = [n_ for n_ in names_h if (by_name(pals, n_) or {}).get("status") not in ("owned", "low", "wishlist")]
        check("(set-up) the faction list has paints you do not own", len(todo) >= 2, hist)
        check("it counts only those paints", f and f["say"].startswith(f"{len(todo)} paint"), (f, todo))
        before_json_h = stored_json(page)
        press_add(page, "#cmp-faction-history")
        tt = toast(page)
        st = stored(page)
        check("the message says how many were added and there is an Undo", tt["text"] == f"Added {len(todo)} paints to your shopping list" and tt["undo"] == "Undo", tt)
        check("they are on the list as Wishlist with the faction's name as the source",
              all(by_name(st, n_)["status"] == "wishlist" and by_name(st, n_)["shopFrom"] == ["Scheme: Gloom Legion colours"] for n_ in todo), [by_name(st, n_) for n_ in todo])
        check("owned paints of the faction were left alone", all(by_name(st, n_)["status"] == "owned" and "shopFrom" not in by_name(st, n_) for n_ in names_h if n_ not in todo and (by_name(pals, n_) or {}).get("status") == "owned"))
        check("the basket count is right", basket(page) == str(len([p_ for p_ in st if p_.get("status") in ("wishlist", "empty")])), basket(page))
        check("the faction's paints in Your schemes still read as before (rows unchanged)",
              page.evaluate("() => [...document.querySelectorAll('#cmp-faction-history-list > li')].every(li => !li.querySelector('.scheme-shop'))"))
        undo(page)
        check("Undo puts the palette back exactly (the saved palette is the same as before the add)", stored_json(page) == before_json_h, "")
        check("Undo says how many came off", toast(page)["text"] == f"Took {len(todo)} paints off your shopping list again.", toast(page))

        # ---------- 5. Shop links off ----------
        print("\n--- 5. Shop links off ---")
        load(page, paints=[], settings={"hideShopLinks": True})
        open_scheme(page)
        f = fold(page)
        check("with Shop links off the button's fold-out is still there (it only adds to your own list)", f and f["summary"] == "Shopping list" and f["button"] == "Add paints to shopping list", f)
        check("and the 'Shop links' fold-outs on single paints are gone as before", page.locator("#compendium-body .shop-more:not(.scheme-shop)").count() == 0)
        press_add(page)
        check("it still adds, and the basket and list stay", toast(page)["text"] == f"Added {len(sp)} paints to your shopping list" and basket(page) == str(len(sp)), (toast(page), basket(page)))
        page.click('nav button[data-tab="recipes"]')
        page.wait_for_timeout(200)
        page.click('#recipe-seg [data-view="shopping"]')
        page.wait_for_timeout(150)
        check("the Shopping list shows the paints (Buy these bar stays hidden, as before)", all(page.inner_text("#shop-panel").count(x["name"]) == 1 for x in sp) and page.locator("#buy-bar").count() == 0)

        # ---------- 6. The recipe card is unchanged ----------
        print("\n--- 6. The recipe card ---")
        load(page, paints=t.PAINTS, recipes=t.RECIPES, units=t.UNITS)
        t.edit_recipe(page, 101)
        t.open_panel(page)
        page.click("#starter-schemes [data-scheme='" + SCHEME_KEY + "']")
        page.wait_for_timeout(150)
        check("in a recipe, Starter schemes and Your schemes have no Shopping list fold-out", page.locator("#colour-ideas .scheme-shop").count() == 0 and page.locator("#starter-list").count() == 1)

        # ---------- 7. Hostile text ----------
        print("\n--- 7. Hostile text ---")
        hp = [P(1, HOSTILE, "#3355aa", "notowned", brand=HOSTILE_BRAND), P(2, HOSTILE + " B", "#c9a227", "notowned", brand=HOSTILE_BRAND),
              P(3, HOSTILE + " C", "#aa2222", "notowned", brand=HOSTILE_BRAND), P(4, HOSTILE + " D", "#dddddd", "notowned", brand=HOSTILE_BRAND)]
        hostile_units = [t.unit(1, "Troop A", HOSTILE, [101]), t.unit(2, "Troop B", HOSTILE, [101])]
        hostile_recipes = [t.rec(101, HOSTILE + " recipe", "Armour", [1, 2, 3, 4])]
        load(page, paints=hp, recipes=hostile_recipes, units=hostile_units)
        page.evaluate("""([name]) => { STARTER_SCHEMES.push({ key: 'hostile-test', mood: 'cold', name, summary: name, reason: name,
            colours: [ { part: name, look: 'a blue', hex: '#3355aa' }, { part: 'Trim', look: 'a gold', hex: '#c9a227' },
                       { part: 'Eyes', look: 'a red', hex: '#aa2222' }, { part: 'Base', look: 'a light grey', hex: '#dddddd' } ] }); }""", [HOSTILE])
        c.open_comp(page)
        c.cmp_pick(page, "starter-chips", "hostile-test")
        page.wait_for_timeout(150)
        check("(set-up) the made-up hostile scheme lists the hostile paints",
              page.evaluate("() => document.querySelectorAll('#cmp-starter-list > li').length") == 4 and page.locator("#cmp-starter-schemes details.scheme-shop").count() == 1)
        bad = page.evaluate("() => ({ pwned: window.__pwned || 0, bad: document.querySelectorAll('#compendium-body img, #compendium-body script, #compendium-body b').length })")
        check("scheme, paint and brand names in the Compendium and the fold-out are plain text: no picture, script or bold appears and nothing runs", bad["pwned"] == 0 and bad["bad"] == 0, bad)
        press_add(page)
        tt = toast(page)
        check("the message is plain text and counts the paints", tt["text"] == "Added 4 paints to your shopping list" and tt["kids"] == 0, tt)
        st = stored(page)
        want = ("Scheme: " + HOSTILE)[:60]
        check("the saved source is plain text cut to 60 characters", all(r["shopFrom"] == [want] and len(r["shopFrom"][0]) == 60 for r in st), [r.get("shopFrom") for r in st])
        page.click('nav button[data-tab="recipes"]')
        page.wait_for_timeout(200)
        page.click('#recipe-seg [data-view="shopping"]')
        page.wait_for_timeout(150)
        bad2 = page.evaluate("() => ({ pwned: window.__pwned || 0, bad: document.querySelectorAll('#shopping-view img, #shopping-view script, #shopping-view b, #basket-button img').length })")
        check("the Shopping list shows those names and sources as plain text", bad2["pwned"] == 0 and bad2["bad"] == 0 and want[:20] in page.inner_text("#shop-panel"), bad2)
        undo_state = toast(page)
        # Your schemes with a hostile faction name
        page.evaluate("() => { const u = JSON.parse(localStorage.getItem('shades-of-grey-recipes')); }")
        load(page, paints=hp, recipes=hostile_recipes, units=hostile_units)
        c.open_comp(page)
        page.evaluate("() => { compendiumState.faction = factionKey(" + json.dumps(HOSTILE) + "); renderCompendium(); }")
        page.wait_for_timeout(200)
        c.open_comp(page)
        f = fold(page, "#cmp-faction-history")
        check("(set-up) a hostile faction gives Your schemes a fold-out", f is not None, f)
        if f:
            press_add(page, "#cmp-faction-history")
            src = [r.get("shopFrom") for r in stored(page) if r.get("status") == "wishlist"]
            want2 = ("Scheme: " + HOSTILE + " colours")[:60]
            check("the faction-name source is plain text cut to 60 characters", src and all(s == [want2] for s in src), src)
        bad3 = page.evaluate("() => ({ pwned: window.__pwned || 0, bad: document.querySelectorAll('#compendium-body img, #compendium-body script, #compendium-body b').length })")
        check("hostile faction and paint names stay plain text in Your schemes", bad3["pwned"] == 0 and bad3["bad"] == 0, bad3)

        # ---------- 8. Phones and looks ----------
        print("\n--- 8. Phones and looks ---")
        for width in (360, 390):
            for scheme in ("dark", "light"):
                page.set_viewport_size({"width": width, "height": 844})
                load(page, paints=[], settings={"theme": scheme})
                open_scheme(page)
                open_fold(page)
                page.wait_for_timeout(100)
                ok = no_sideways(page) and page.evaluate("""() => { const d = document.querySelector('#cmp-starter-schemes details.scheme-shop'); const r = d.getBoundingClientRect();
                    const b = d.querySelector('button').getBoundingClientRect(); return r.right <= window.innerWidth + 1 && b.height >= 44 && b.right <= window.innerWidth + 1; }""")
                check(f"{width}px, {scheme}: the open fold-out fits, the button is at least 44px tall, nothing slides sideways", ok)
                shot(page, f"v42-scheme-{width}-{scheme}.png")
        page.set_viewport_size({"width": 390, "height": 844})
        other = [d for d in dialogs if not d.startswith(("Took ", "Nothing added"))]   # the app's own plain notices from this test are expected
        check("no page errors and no pop-up boxes (only this release's own plain notices appeared)", not errors and not other, (errors[:2], other[:2]))
        browser.close()

if __name__ == "__main__":
    main()
    passed = sum(results)
    print(f"\n{passed}/{len(results)} passed")
    sys.exit(0 if all(results) else 1)
