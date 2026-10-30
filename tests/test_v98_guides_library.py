"""X3 tests for Minifolio (the Guides library). New behaviour only:
1. The loader: one index of every kind, look up, list, search ranking and the duplicate "mud" (on a fixture built from knowledge-base/samples).
2. The Guides screen: categories with counts, empty ones hidden, a category's rows, an entry page, Back, related buttons, search.
3. Detail recipes and Basing keep their controls under their own categories.
4. openGuide with a good and a bad key; each entry page carries its key as its id.
5. Entry text is plain text only; no faction words in the new text.
6. 360 and 390 px, dark and light: no sideways scroll, taps 44 px or more; 1280 px puts the list and the entry side by side.
Run all tests with `python3 tests/run_all.py`, or serve the repo folder and run this file on its own."""
import os, sys, re, json
from playwright.sync_api import sync_playwright

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import test_v31 as t
from launch_helpers import wait_settled, tap_tab

results = []
FACTION_WORDS = re.compile(r"tyranid|space marine|ork|necron|eldar|ultramarine|warhammer|citadel|games workshop|chaos|imperial", re.I)
SAMPLES = json.load(open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "knowledge-base", "samples", "sample-entries.json")))

def check(name, ok, detail=""):
    results.append(bool(ok))
    print(("PASS " if ok else "FAIL ") + name + ("" if ok else f"  -> {detail}"))

def texts(page, sel):
    return page.evaluate("(s) => [...document.querySelectorAll(s)].map(b => b.textContent.trim())", sel)

def put(page, guides=None, starters=None):
    """Give the app small guide and starter lists (what the knowledge base will hold) and rebuild the index."""
    page.evaluate("([g, s]) => { GUIDE_ENTRIES.splice(0, GUIDE_ENTRIES.length, ...g); GUIDE_STARTERS.splice(0, GUIDE_STARTERS.length, ...s); knowledgeCache = null; }", [guides or [], starters or []])

def guides(page):
    tap_tab(page, "guides")
    page.click('#more-seg button[data-page="guides"]')
    wait_settled(page)

def main():
    errors, outside = [], []
    with sync_playwright() as p:
        browser = p.chromium.launch()
        ctx = browser.new_context(viewport={"width": 390, "height": 844}, service_workers="block")
        page = ctx.new_page()
        page.on("pageerror", lambda x: errors.append(str(x)))
        page.on("dialog", lambda d: (errors.append("dialog: " + d.message), d.dismiss()))
        page.on("request", lambda r: outside.append(r.url) if not r.url.startswith(("http://localhost", "http://127.0.0.1", "data:", "blob:")) else None)
        t.load(page, launch=True, settings={"tab": "guides", "examplesChecked": True})
        page.wait_for_function("() => typeof makeKnowledgeIndex === 'function'")

        print("\n--- 1. The loader ---")
        r = page.evaluate("""(s) => { const k = makeKnowledgeIndex({ guides: s.guides, recipes: DETAIL_RECIPES, basing: BASING_TIPS, tips: s['mentor-tips'], parts: MENTOR_PARTS, starters: s.starters });
            const kinds = [...new Set(k.entries.map(e => e.kind))].sort();
            return { kinds, clashes: k.clashes, mud: k.entries.filter(e => e.key === 'mud').map(e => [e.kind, e.id]), first: k.get('mud').kind, second: k.get('mud', 'basing').kind,
                     byCat: k.list({ category: 'colour-basics' }).length, byKind: k.list({ kind: 'detail' }).length === DETAIL_RECIPES.length,
                     hits: k.search('warm cool').map(e => e.key), order: k.search('thinning').map(e => e.key), none: k.search('zzzz qqqq').length, caps: k.search('WARM').length > 0,
                     bad: makeKnowledgeIndex({ guides: [{ title: 'no key' }, { key: 'x' }, null], recipes: [], basing: [] }).entries.length }; }""", SAMPLES)
        check("every kind is indexed: guides, detail recipes, basing, Mentor tips, starters", r["kinds"] == ["basing", "detail", "guide", "starter", "tip"], r["kinds"])
        check("the shared key 'mud' keeps both entries, the first loaded answers a plain look up, the kind gets the other",
              r["clashes"] == ["mud"] and r["first"] == "detail" and r["second"] == "basing" and [x[1] for x in r["mud"]] == ["guide-mud", "guide-mud-basing"], r)
        check("list by category and by kind", r["byCat"] == 1 and r["byKind"], r)
        check("search: every word must match, any case, nothing found gives an empty list", "sample-warm-and-cool" in r["hits"] and r["caps"] and r["none"] == 0, r)
        check("search ranks a title or keyword hit above a summary-only hit", r["order"] and r["order"][0] in ("sample-thinning-paint", "sample-starter-thinning"), r["order"])
        check("entries without a key or title are skipped, nothing throws", r["bad"] == 0, r["bad"])

        print("\n--- 2. The screen ---")
        guides(page)
        check("with no guide entries yet, only Detail recipes and Basing show, with counts",
              [x.rstrip("0123456789") for x in texts(page, ".guides-cats .guides-row")] == ["Detail recipes", "Basing"]
              and all(re.search(r"\d+$", x) for x in texts(page, ".guides-cats .guides-row")), texts(page, ".guides-cats .guides-row"))
        check("no heading or sentence under the search box on the home list", page.locator(".guides-nav h3, .guides-nav p").count() == 0)
        put(page, SAMPLES["guides"], SAMPLES["starters"])
        guides(page)
        cats = texts(page, ".guides-cats .guides-row")
        n = page.evaluate("() => GUIDE_ENTRIES.length")
        shown = {c.rstrip("0123456789"): int(re.sub(r"\D", "", c) or 0) for c in cats}
        have = page.evaluate("() => [...new Set(GUIDE_ENTRIES.map(e => e.category))]")
        names = {"colour-basics": "Colour basics", "techniques": "Techniques", "tools-prep": "Tools and prep", "problems": "Problems"}
        check("a category shows exactly when it has entries, and its number is the count",
              all((names[c] in shown) for c in have) and all(names[c] not in shown for c in names if c not in have) and sum(shown.get(names[c], 0) for c in have) == n, (shown, have))
        first_cat = page.evaluate("() => GUIDE_ENTRIES[0].category")
        page.click(f'.guides-cats [data-cat="{first_cat}"]')
        wait_settled(page)
        rows = texts(page, ".guides-main .guides-row .guides-row-title")
        check("a category lists its entries as rows with title and summary",
              len(rows) >= 1 and page.locator(".guides-main .guides-row-summary").count() == len(rows) and page.is_visible("#guides-back"), rows)
        check("on a phone the category list steps aside while one category shows", not page.is_visible(".guides-nav"))
        page.click(".guides-main .guides-row")
        wait_settled(page)
        key = page.get_attribute(".guides-entry", "data-key")
        check("an entry opens as a page: title, body paragraphs, an id from its key",
              page.locator(".guides-entry h3").count() == 1 and page.locator(".guides-entry p").count() >= 3 and page.get_attribute(".guides-entry", "id") == "guide-" + key, key)
        check("related entries are buttons that open that entry", page.locator(".guides-related button").count() >= 1)
        rel = page.get_attribute(".guides-related button", "data-related")
        page.click(".guides-related button")
        wait_settled(page)
        check("tapping a related button opens it", page.get_attribute(".guides-entry", "data-key") == rel, rel)
        page.click("#guides-back")
        wait_settled(page)
        check("Back goes to the category, then to the home list", page.locator(".guides-main .guides-row").count() >= 1 and page.inner_text("#guides-back").startswith("Back to"))
        page.click("#guides-back")
        wait_settled(page)
        check("the home list is back with the category buttons", page.locator(".guides-cats .guides-row").count() >= 2 and page.locator(".guides-main").inner_text() == "")
        page.fill("#guides-search", "warm")
        page.wait_for_selector(".guides-lower .guides-row[data-guide]")
        found = texts(page, ".guides-lower .guides-row-title")
        check("search matches title, summary and keywords as you type", any("Warm" in f for f in found), found)
        page.fill("#guides-search", "zzzz")
        page.wait_for_function("() => document.querySelector('.guides-lower .hint')")
        check("nothing found is one short line", texts(page, ".guides-lower .hint") == ["Nothing found."])
        page.fill("#guides-search", "")
        check("emptying the search brings the categories back", page.locator(".guides-cats").count() == 1)

        print("\n--- 3. Detail recipes and Basing keep their controls ---")
        page.click('.guides-cats [data-cat="detail"]')
        page.wait_for_selector(".guides-main .detail-recipes")
        page.click(".guides-main #cmp-detail-groups .chip")
        page.click("#cmp-detail-chips .chip")
        page.wait_for_selector("#cmp-detail-list")
        check("Detail recipes: a recipe opens with its paints, Add to shopping list and Save into a new recipe",
              page.locator("#cmp-detail-list li").count() >= 3 and page.get_by_text("Add to shopping list").count() >= 1 and page.get_by_text("Save into a new recipe").count() >= 1)
        page.click("#guides-back")
        page.click('.guides-cats [data-cat="basing"]')
        page.wait_for_selector(".guides-main .basing-tips")
        check("Basing shows its own list under its own heading", page.inner_text(".guides-title") == "Basing")

        print("\n--- 4. openGuide ---")
        page.evaluate("() => { settings.tab = 'dashboard'; } ")
        tap_tab(page, "dashboard")
        wait_settled(page)
        page.evaluate("(k) => openGuide(k)", key)
        page.wait_for_selector(".guides-entry")
        check("openGuide opens Tools > Guides on that entry from another screen",
              page.evaluate("(k) => settings.tab === 'guides' && document.getElementById('view-guides').classList.contains('hidden') === false && document.getElementById('guide-' + k) === document.querySelector('.guides-entry')", key))
        dkey = page.evaluate("() => DETAIL_RECIPES[1].key")
        page.evaluate("(k) => openGuide(k)", dkey)
        page.wait_for_selector(f'#cmp-detail-chips [data-detail="{dkey}"], #cmp-detail-summary')
        check("openGuide on a detail recipe shows that recipe picked, with its element id",
              page.evaluate("(k) => !!document.getElementById('guide-' + k) && document.getElementById('cmp-detail-summary') !== null", dkey))
        page.evaluate("() => openGuide('no-such-guide')")
        page.wait_for_selector("#guides-missing")
        check("an unknown key shows one calm line and the list", page.inner_text("#guides-missing") == "That guide could not be found." and page.locator(".guides-cats").count() == 1)
        page.evaluate("() => openGuide(undefined)")
        check("a missing key does not crash either", errors == [], errors)

        print("\n--- 5. Plain text only ---")
        put(page, [{"key": "bad-html", "category": "techniques", "title": "<img src=x onerror=alert(1)> Title", "summary": "<b>bold</b> summary line here",
                    "body": ["<script>alert(2)</script> one", "<i>two</i> two two two", "three three three three"], "related": [], "keywords": ["x"],
                    "credit": {"name": "<u>Name</u>", "url": "javascript:alert(3)"}}])
        guides(page)
        page.click('.guides-cats [data-cat="techniques"]')
        page.click(".guides-main .guides-row")
        page.wait_for_selector(".guides-entry")
        made = page.evaluate("() => document.querySelectorAll('#compendium-body img, #compendium-body script, #compendium-body b, #compendium-body i, #compendium-body u').length")
        check("entry text with tags shows as plain text and builds no elements", made == 0 and "<img" in page.inner_text(".guides-entry h3") and "<script>" in page.inner_text(".guides-entry"), made)
        check("a credit link that is not https is not made into a link", page.locator(".guides-credit a").count() == 0 and "Credit:" in page.inner_text(".guides-credit"))
        put(page, SAMPLES["guides"], SAMPLES["starters"])

        print("\n--- 6. Phone and wide screens ---")
        for width in (390, 360):
            for scheme in ("dark", "light"):
                page.set_viewport_size({"width": width, "height": 844})
                page.emulate_media(color_scheme=scheme)
                guides(page)
                page.evaluate("() => { Object.assign(guidesState, { view: 'home', cat: '', key: '', kind: '' }); renderGuides(); }")
                m = page.evaluate("""() => ({ x: document.documentElement.scrollWidth <= window.innerWidth + 1,
                    small: [...document.querySelectorAll('#compendium-body button, #compendium-body input')].filter(b => b.offsetParent && b.getBoundingClientRect().height < 44).map(b => b.textContent),
                    tf: [...document.querySelectorAll('.guides-row')].map(b => getComputedStyle(b).transform).filter(x => x !== 'none') })""")
                check(f"{width} px {scheme}: no sideways scroll, taps 44 px or more, nothing transformed at rest", m["x"] and not m["small"] and not m["tf"], m)
        page.set_viewport_size({"width": 390, "height": 844})
        page.emulate_media(color_scheme="dark")
        guides(page)
        page.click(f'.guides-cats [data-cat="{first_cat}"]')
        page.set_viewport_size({"width": 1280, "height": 900})
        wait_settled(page)
        check("1280 px: the category list and the entries sit side by side",
              page.evaluate("() => { const a = document.querySelector('.guides-nav').getBoundingClientRect(), b = document.querySelector('.guides-main').getBoundingClientRect(); return a.width > 0 && b.width > a.width && Math.abs(a.top - b.top) < 4 && a.right <= b.left; }"))

        new_text = " ".join(texts(page, "#compendium-body button, #compendium-body label")) + page.inner_text("#help-guides")
        check("no faction or brand words and no em dashes in the new text", not FACTION_WORDS.search(new_text) and "—" not in new_text, FACTION_WORDS.findall(new_text))
        check("no new network use", outside == [], outside)
        check("no page errors or pop-ups", errors == [], errors)
        browser.close()
    print(f"\n{sum(results)}/{len(results)} checks passed")
    return 0 if all(results) else 1

if __name__ == "__main__":
    sys.exit(main())
