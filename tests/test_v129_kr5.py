"""KR5 tests for Minifolio (the second gap-fill knowledge base pack and its agreed corrections are imported). New behaviour only:
1. The 46 new guides (knowledge-base/data/k10-kr5-guides.json), 41 detail recipes (k11-kr5-detail-recipes.json) and 12 basing tips
   (k12-kr5-basing-tips.json) are in the app with their own titles, each guide in exactly one topic group of its own section
   (guides-groups.js), and each recipe and tip in a group of its own list.
2. Mentor gives the new entry first for sample questions from the KR5 pack: a guide, a recipe, a basing tip, and salt weathering
   (which needs the salt words taken out of the hairspray chipping synonyms).
3. Two of the applied corrections read as corrected on screen: a guide paragraph (paint the paler colour first in quartered designs)
   and a recipe step (the woodland camo wash is cut with medium, not water).
4. Guides at 390x844 dark and 360x640 light: a group list shows the new entries, rows 44 px or taller, no sideways scroll.
The wording rules are checked by knowledge-base/check_knowledge.py; the older count tests (v32, v33, v37, v104) carry the new totals.
Run all tests with `python3 tests/run_all.py`, or serve the repo folder and run this file on its own."""
import json, os, sys
from playwright.sync_api import sync_playwright

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import test_v31 as t
from launch_helpers import wait_settled, tap_tab

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, "..", "knowledge-base", "data")
results = []

# Two of the 111 "apply" corrections, as the pack wrote them (kr5-pack/corrections/kr5-corrections.json c026 and c013)
QUARTERED_NEW = "Paint the paler colour first. The darker one then covers any slips over the join, while a pale colour like yellow covers dark slips badly."
QUARTERED_OLD = "Paint the darker colour first."
CAMO_NEW = "One part wash to two of medium over the whole pattern, so it tints without rings."
CAMO_OLD = "One part wash to two of water over the whole pattern."

def check(name, ok, detail=""):
    results.append(bool(ok))
    print(("PASS " if ok else "FAIL ") + name + ("" if ok else f"  -> {str(detail)[:600]}"))

def kb(name):
    with open(os.path.join(DATA, name), encoding="utf-8") as f:
        return json.load(f)

def home(page):
    page.evaluate("() => { Object.assign(guidesState, { view: 'home', cat: '', group: '', key: '', kind: '', query: '', shownRows: {} }); renderGuides(); }")
    wait_settled(page)

def main():
    errors = []
    guides = kb("k10-kr5-guides.json")["guides"]
    recipes = kb("k11-kr5-detail-recipes.json")["detail-recipes"]
    tips = kb("k12-kr5-basing-tips.json")["basing-tips"]
    with sync_playwright() as p:
        browser = p.chromium.launch()
        ctx = browser.new_context(viewport={"width": 390, "height": 844}, service_workers="block")
        page = ctx.new_page()
        page.on("pageerror", lambda x: errors.append(str(x)))
        page.on("dialog", lambda d: (errors.append("dialog: " + d.message), d.dismiss()))
        t.load(page, launch=True, settings={"tab": "guides", "examplesChecked": True})
        page.wait_for_function("() => typeof guideGroupsOf === 'function'")

        print("\n--- 1. The new entries and their groups ---")
        r = page.evaluate("""([gs, rs, ts]) => {
            const byKey = new Map(GUIDE_ENTRIES.map(e => [e.key, e]));
            const guides = gs.map(g => { const e = byKey.get(g.key);
                const homes = Object.entries(GUIDE_GROUPS.sections).flatMap(([sec, groups]) => groups.filter(x => x.keys.includes(g.key)).map(x => [sec, x.name]));
                return { key: g.key, ok: !!e && e.title === g.title && e.category === g.category, homes, cat: g.category }; });
            const dg = new Set(DETAIL_GROUPS.map(g => g.key)), bg = new Set(BASING_GROUPS.map(g => g.key));
            const recipes = rs.map(x => { const d = DETAIL_RECIPES.filter(y => y.key === x.key);
                return { key: x.key, ok: d.length === 1 && d[0].name === x.name && d[0].group === x.group && dg.has(d[0].group) && d[0].steps.length === x.steps }; });
            const tips = ts.map(x => { const d = BASING_TIPS.filter(y => y.key === x.key);
                return { key: x.key, ok: d.length === 1 && d[0].name === x.name && d[0].group === x.group && bg.has(d[0].group) }; });
            return { guides, recipes, tips }; }""", [[{"key": g["key"], "title": g["title"], "category": g["category"]} for g in guides],
                                                     [{"key": x["key"], "name": x["name"], "group": x["group"], "steps": len(x["steps"])} for x in recipes],
                                                     [{"key": x["key"], "name": x["name"], "group": x["group"]} for x in tips]])
        check(f"the {len(guides)} new guides are in the app with their titles and sections", len(guides) == 46 and all(g["ok"] for g in r["guides"]), [g for g in r["guides"] if not g["ok"]])
        check("each new guide sits in exactly one topic group, in its own section",
              all(len(g["homes"]) == 1 and g["homes"][0][0] == g["cat"] for g in r["guides"]), [(g["key"], g["homes"]) for g in r["guides"] if len(g["homes"]) != 1 or g["homes"][0][0] != g["cat"]])
        check(f"the {len(recipes)} new detail recipes are in the app once each, in one of the recipe groups, with their steps",
              len(recipes) == 41 and all(x["ok"] for x in r["recipes"]), [x for x in r["recipes"] if not x["ok"]])
        check(f"the {len(tips)} new basing tips are in the app once each, in one of the basing groups",
              len(tips) == 12 and all(x["ok"] for x in r["tips"]), [x for x in r["tips"] if not x["ok"]])

        print("\n--- 2. Mentor finds the new entries ---")
        for q, key in [("how do i paint a hologram", "painting-holograms"), ("how do i paint a wolf", "grey-wolf-fur"),
                       ("how do i make a jungle base", "jungle-floor"), ("how do i do salt weathering", "salt-weathering")]:
            a = page.evaluate("""(q) => { const a = MinifolioMentor.mentorAnswer(q, { index: knowledgeIndex(), paints: [], tips: MENTOR_TIPS });
                return { kind: a.kind, keys: (a.sources || []).map(s => s.key) }; }""", q)
            check(f"Mentor answers '{q}' with {key} first", a["kind"] == "answer" and a["keys"][:1] == [key], a)

        print("\n--- 3. Two applied corrections read as corrected ---")
        tap_tab(page, "guides")
        home(page)
        page.click('.guides-cats [data-cat="techniques"]')
        group = page.evaluate("(k) => guidePlace(knowledgeIndex().get(k)).group", "quartered-designs")
        page.click(f'.guides-main [data-group="{group}"]')
        page.click('.guides-main .guides-row[data-guide="quartered-designs"]')
        page.wait_for_selector(".guides-entry")
        text = page.inner_text(".guides-entry")
        check("Quartered designs now says to paint the paler colour first", QUARTERED_NEW in text and QUARTERED_OLD not in text, text[:500])
        home(page)
        page.click('.guides-cats [data-cat="detail"]')
        page.click('#cmp-detail-groups [data-detail-group="all"]')
        page.click('#cmp-detail-chips [data-detail="woodland-camo"]')
        page.wait_for_selector("#cmp-detail-list")
        step = page.locator("#cmp-detail-list > li").nth(3)   # step 4, the wash: its note sits behind the step's More info
        step.locator(".more-info-button").first.click()
        text = step.inner_text()
        check("the woodland camo recipe now cuts its wash with medium (step 4, under More info)", CAMO_NEW in text and CAMO_OLD not in text, text[:600])

        print("\n--- 4. Guides lists on phones ---")
        for w, h, scheme, cat, group, keys in [
                (390, 844, "dark", "problems", "Paint and wash problems", ["fix-blotchy-one-coat-paints", "fix-dust-and-hairs-in-paint", "fix-metallic-glitter-in-paint", "fix-peeling-paint"]),
                (360, 640, "light", "techniques", "Freehand and markings", ["digital-pixel-camo", "masking-fluid-by-brush", "painting-banners-and-flags"])]:
            page.set_viewport_size({"width": w, "height": h})
            page.evaluate("(lt) => { settings.appearance = lt ? 'light' : 'dark'; applyPalette(settings.palette); render(); }", scheme == "light")
            tap_tab(page, "guides")
            home(page)
            page.click(f'.guides-cats [data-cat="{cat}"]')
            page.click(f'.guides-main [data-group="{group}"]')
            wait_settled(page)
            m = page.evaluate("""(keys) => { const rows = [...document.querySelectorAll('.guides-main .guides-row[data-guide]')];
                return { shown: keys.filter(k => rows.some(r => r.dataset.guide === k && r.offsetParent)), small: rows.filter(r => r.getBoundingClientRect().height < 44).length,
                         sideways: document.documentElement.scrollWidth > window.innerWidth, mode: document.documentElement.dataset.m }; }""", keys)
            check(f"{w}x{h} {scheme}: {group} lists the new entries, rows 44 px or taller, no sideways scroll",
                  m["shown"] == keys and m["small"] == 0 and not m["sideways"] and m["mode"] == scheme, m)

        check("no page errors or pop-ups", errors == [], errors)
        browser.close()
    print(f"\n{sum(results)}/{len(results)} checks passed")
    return 0 if all(results) else 1

if __name__ == "__main__":
    sys.exit(main())
