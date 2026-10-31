"""X8 tests for Minifolio (the knowledge base is imported). New behaviour only:
1. The Guides home list shows every category with its real count (602 guides in four categories, 137 detail recipes, 60 basing tips),
   and there are 20 starter questions.
2. Three sample guides (one each from Colour basics, Techniques and Problems) open from Guides: title, body, related buttons.
3. One new detail recipe and one new basing tip (from knowledge-base/data) open under Detail recipes and Basing with their steps.
The data rules (wording, keys, links) are checked by knowledge-base/check_knowledge.py and tests/test_v32.py and test_v33.py.
Run all tests with `python3 tests/run_all.py`, or serve the repo folder and run this file on its own."""
import json, os, sys
from playwright.sync_api import sync_playwright

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import test_v31 as t
from launch_helpers import wait_settled, tap_tab

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, "..", "knowledge-base", "data")
COUNTS = {"Colour basics": 81, "Techniques": 316, "Detail recipes": 137, "Basing": 60, "Tools and prep": 155, "Problems": 50}
results = []

def check(name, ok, detail=""):
    results.append(bool(ok))
    print(("PASS " if ok else "FAIL ") + name + ("" if ok else f"  -> {detail}"))

def kb(name):
    with open(os.path.join(DATA, name), encoding="utf-8") as f:
        return json.load(f)

def home(page):
    page.evaluate("() => { settings.tab = 'dashboard'; }")
    tap_tab(page, "guides")
    page.click('#more-seg button[data-page="guides"]')
    page.evaluate("() => { Object.assign(guidesState, { view: 'home', cat: '', key: '', kind: '', query: '' }); renderGuides(); }")
    wait_settled(page)

def main():
    errors = []
    guides = kb("k1-colour-basics.json")["guides"][:1] + kb("k2-techniques.json")["guides"][150:151] + \
        [g for g in kb("k5-tools-prep-problems.json")["guides"] if g["category"] == "problems"][-1:]
    recipe = kb("k3-detail-recipes.json")["detail-recipes"][-1]
    tip = kb("k4-basing-tips.json")["basing-tips"][0]
    with sync_playwright() as p:
        browser = p.chromium.launch()
        ctx = browser.new_context(viewport={"width": 390, "height": 844}, service_workers="block")
        page = ctx.new_page()
        page.on("pageerror", lambda x: errors.append(str(x)))
        page.on("dialog", lambda d: (errors.append("dialog: " + d.message), d.dismiss()))
        t.load(page, launch=True, settings={"tab": "guides", "examplesChecked": True})

        print("\n--- 1. Counts ---")
        home(page)
        rows = page.evaluate("() => [...document.querySelectorAll('.guides-cats .guides-row')].map(b => [b.querySelector('.guides-row-title').textContent, +b.querySelector('.guides-count').textContent])")
        check("the Guides home list shows every category with its count", dict(rows) == COUNTS and len(rows) == 6, rows)
        check("there are 20 starter questions", page.evaluate("() => GUIDE_STARTERS.length") == 20)

        print("\n--- 2. Three sample guides open ---")
        names = {"colour-basics": "Colour basics", "techniques": "Techniques", "problems": "Problems"}
        for g in guides:
            home(page)
            page.click(f'.guides-cats [data-cat="{g["category"]}"]')
            # v106 (X8d): a category list now shows 30 rows first, so open the whole list before looking for the sample row
            page.evaluate("() => { guidesState.shownRows = { ['cat:' + guidesState.cat]: 9999 }; renderGuides(); }")
            page.click(f'.guides-main .guides-row[data-guide="{g["key"]}"]')
            page.wait_for_selector(".guides-entry")
            got = page.evaluate("() => { const e = document.querySelector('.guides-entry'); return { key: e.dataset.key, title: e.querySelector('h3').textContent, text: e.innerText, related: [...e.querySelectorAll('.guides-related button')].map(b => b.dataset.related) }; }")
            check(f"{names[g['category']]}: '{g['title']}' opens with its title, every body paragraph and one button per related entry",
                  got["key"] == g["key"] and got["title"] == g["title"] and all(x in got["text"] for x in g["body"]) and got["related"] == g["related"], got)

        print("\n--- 3. A new detail recipe and a new basing tip open ---")
        home(page)
        page.click('.guides-cats [data-cat="detail"]')
        page.click('#cmp-detail-groups [data-detail-group="all"]')
        page.click(f'#cmp-detail-chips [data-detail="{recipe["key"]}"]')
        page.wait_for_selector("#cmp-detail-list")
        check(f"Detail recipes: '{recipe['name']}' opens with its summary and one row per step",
              page.inner_text("#cmp-detail-summary") == recipe["summary"] and page.locator("#cmp-detail-list li").count() == len(recipe["steps"]))
        home(page)
        page.click('.guides-cats [data-cat="basing"]')
        page.click('#cmp-basing-groups [data-basing-group="all"]')
        page.click(f'#cmp-basing-chips [data-basing="{tip["key"]}"]')
        page.wait_for_selector("#cmp-basing-summary")
        check(f"Basing: '{tip['name']}' opens with its summary and its how-to steps",
              page.inner_text("#cmp-basing-summary") == tip["summary"] and all(h in page.inner_text(".guides-main") for h in tip["howto"]))

        check("no page errors or pop-ups", errors == [], errors)
        browser.close()
    print(f"\n{sum(results)}/{len(results)} checks passed")
    return 0 if all(results) else 1

if __name__ == "__main__":
    sys.exit(main())
