"""KR4 tests for Minifolio (the gap-fill knowledge base entries are imported). New behaviour only:
1. The 12 new guides (knowledge-base/data/k8-kr4-guides.json) and 6 new Body detail recipes (k9-kr4-detail-recipes.json) are in the
   app with their own titles, and each new guide sits in exactly one topic group of its own section (guides-groups.js).
2. Mentor gives the new entry first for two sample questions from the KR4 pack (waiting between coats, painting a horse).
3. Guides at 390x844 dark and 360x640 light: a group list shows the new entries, with no sideways scroll and rows 44 px or taller.
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
    guides = kb("k8-kr4-guides.json")["guides"]
    recipes = kb("k9-kr4-detail-recipes.json")["detail-recipes"]
    with sync_playwright() as p:
        browser = p.chromium.launch()
        ctx = browser.new_context(viewport={"width": 390, "height": 844}, service_workers="block")
        page = ctx.new_page()
        page.on("pageerror", lambda x: errors.append(str(x)))
        page.on("dialog", lambda d: (errors.append("dialog: " + d.message), d.dismiss()))
        t.load(page, launch=True, settings={"tab": "guides", "examplesChecked": True})
        page.wait_for_function("() => typeof guideGroupsOf === 'function'")

        print("\n--- 1. The new entries and their groups ---")
        r = page.evaluate("""([gs, rs]) => {
            const byKey = new Map(GUIDE_ENTRIES.map(e => [e.key, e]));
            const guides = gs.map(g => { const e = byKey.get(g.key);
                const homes = Object.entries(GUIDE_GROUPS.sections).flatMap(([sec, groups]) => groups.filter(x => x.keys.includes(g.key)).map(x => [sec, x.name]));
                return { key: g.key, ok: !!e && e.title === g.title && e.category === g.category, homes, cat: g.category }; });
            const recipes = rs.map(x => { const d = DETAIL_RECIPES.find(y => y.key === x.key); return { key: x.key, ok: !!d && d.name === x.name && d.group === 'body' && d.steps.length === x.steps.length }; });
            return { guides, recipes }; }""", [[{"key": g["key"], "title": g["title"], "category": g["category"]} for g in guides],
                                               [{"key": x["key"], "name": x["name"], "steps": x["steps"]} for x in recipes]])
        check(f"the {len(guides)} new guides are in the app with their titles and sections", len(guides) == 12 and all(g["ok"] for g in r["guides"]), [g for g in r["guides"] if not g["ok"]])
        check(f"the {len(recipes)} new detail recipes are in the app under Body with their steps", len(recipes) == 6 and all(x["ok"] for x in r["recipes"]), [x for x in r["recipes"] if not x["ok"]])
        check("each new guide sits in exactly one topic group, in its own section",
              all(len(g["homes"]) == 1 and g["homes"][0][0] == g["cat"] for g in r["guides"]), [(g["key"], g["homes"]) for g in r["guides"] if len(g["homes"]) != 1 or g["homes"][0][0] != g["cat"]])

        print("\n--- 2. Mentor finds the new entries ---")
        for q, key in [("How long should I wait between coats?", "waiting-between-coats"), ("how do I paint a horse", "horses-and-mounts")]:
            a = page.evaluate("""(q) => { const a = MinifolioMentor.mentorAnswer(q, { index: knowledgeIndex(), paints: [], tips: MENTOR_TIPS });
                return { kind: a.kind, keys: (a.sources || []).map(s => s.key) }; }""", q)
            check(f"Mentor answers '{q}' with {key} first", a["kind"] == "answer" and a["keys"][:1] == [key], a)

        print("\n--- 3. Guides lists on phones ---")
        for w, h, scheme, cat, group, keys in [
                (390, 844, "dark", "colour-basics", "Painting specific colours", ["painting-blue", "painting-brown", "painting-green", "painting-grey"]),
                (360, 640, "light", "tools-prep", "Paints and paint care", ["matching-a-lost-colour", "mixing-paint-ranges", "using-colour-lab"])]:
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
