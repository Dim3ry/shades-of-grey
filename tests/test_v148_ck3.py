"""Chunk CK3 tests for Minifolio: See also links and Mentor phrases for the three CK2 gaps. New behaviour only.

1. The ten new See also links exist (and the one that already existed is still there); no guide has more than 3.
2. A new link opens the right guide from the entry page.
3. Mentor puts the right guide first for the new phrases and small variations.
4. The starter question list is unchanged in size.
Run all tests with `python3 tests/run_all.py`, or serve the repo folder and run this file on its own."""
import os, sys
from playwright.sync_api import sync_playwright

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import test_v31 as t
from launch_helpers import wait_settled, tap_tab

STARTERS = 20   # unchanged by CK3
results = []

def check(name, ok, detail=""):
    results.append(bool(ok))
    print(("PASS " if ok else "FAIL ") + name + ("" if ok else f"  -> {str(detail)[:600]}"))

LINKS = [
    ("brush-care", "split-or-hooked-brush-tips"), ("choosing-brushes", "split-or-hooked-brush-tips"),
    ("first-model-steps", "first-sessions-path"), ("starter-tool-kit", "first-sessions-path"), ("skill-roadmap", "first-sessions-path"),
    ("base-coating", "waiting-between-coats"), ("two-thin-coats", "waiting-between-coats"),
]
PHRASES = {
    "split-or-hooked-brush-tips": ["hook at the end of my brush", "my brush has a hook at the end", "hook on the end of my brush", "bent brush", "how do I fix a bent brush"],
    "waiting-between-coats": ["can I paint over wet paint", "can I paint over wet paint straight away", "is it ok to paint over wet paint", "can you paint on top of wet paint"],
}
ASK = """(qs) => qs.map((q) => { const a = MinifolioMentor.mentorAnswer(q, { index: knowledgeIndex(), paints: [], tips: MENTOR_TIPS });
    return { q, keys: (a.sources || []).map(s => s.key) }; })"""

def main():
    errors = []
    with sync_playwright() as p:
        browser = p.chromium.launch()
        ctx = browser.new_context(viewport={"width": 390, "height": 844}, service_workers="block", reduced_motion="reduce")
        page = ctx.new_page()
        page.on("pageerror", lambda x: errors.append(str(x)))
        t.load(page, settings={"tab": "guides", "examplesChecked": True})
        tap_tab(page, "guides")
        page.click('#more-seg button[data-page="guides"]')
        page.wait_for_function("() => typeof guideSeeAlso === 'function'")
        wait_settled(page)

        print("\n--- 1. Links ---")
        sa = page.evaluate("GUIDE_GROUPS.seeAlso")
        check("the seven guides link to their target", all(b in sa.get(a, []) for a, b in LINKS), [(a, sa.get(a)) for a, b in LINKS if b not in sa.get(a, [])])
        check("existing links on those guides are kept", "choosing-brushes" in sa["brush-care"] and "brush-size" in sa["choosing-brushes"] and "selective-base-coat" in sa["base-coating"] and "building-your-first-kit" in sa["first-model-steps"])
        check("no guide has more than 3 See also links", max(len(v) for v in sa.values()) <= 3, max(sa.items(), key=lambda kv: len(kv[1])))
        keys = set(page.evaluate("GUIDE_ENTRIES.map(g => g.key)"))
        check("every new target is a real guide", all(a in keys and b in keys for a, b in LINKS))

        print("\n--- 2. A link opens the right guide ---")
        for frm, to in [("brush-care", "split-or-hooked-brush-tips"), ("skill-roadmap", "first-sessions-path"), ("two-thin-coats", "waiting-between-coats")]:
            page.evaluate("(k) => { Object.assign(guidesState, { view: 'entry', key: k, kind: 'guide', query: '' }); renderGuides(); }", frm)
            wait_settled(page)
            link = page.locator('.guides-seealso-link[data-see-also="%s"]' % to)
            check(f"{frm} shows a See also link to {to}", link.count() == 1)
            if link.count() == 1:
                link.scroll_into_view_if_needed()
                link.click()
                wait_settled(page)
                check(f"the link opens {to}", page.evaluate("() => guidesState.key") == to, page.evaluate("() => guidesState.key"))

        print("\n--- 3. Mentor phrases ---")
        for key, qs in PHRASES.items():
            res = page.evaluate(ASK, qs)
            for r in res:
                check(f"'{r['q']}' puts {key} first", r["keys"][:1] == [key], r["keys"][:3])

        print("\n--- 4. Starters ---")
        n = page.evaluate("GUIDE_STARTERS.length")
        first = page.evaluate("GUIDE_STARTERS[0].text")
        check("the starter list still has 20 questions", n == STARTERS, n)
        check("the 'I'm new' starter is unchanged", first == "I'm new. What do I need to start painting?" and page.evaluate("GUIDE_STARTERS[0].targets.slice(0, 2)") == ["starter-tool-kit", "first-model-steps"], first)
        check("no page errors", not errors, errors)
        browser.close()
    print(f"\n{sum(results)}/{len(results)} checks passed")
    return all(results)

if __name__ == "__main__":
    sys.exit(0 if main() else 1)
