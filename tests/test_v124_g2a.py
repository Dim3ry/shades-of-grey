"""G2a tests for Minifolio (Guides topic groups, grouped browse and numbers). New behaviour only:
1. The mapping (guides-groups.js): every guide entry of Colour basics, Techniques, Tools and prep and Problems sits in exactly one
   topic group of its own section, and every key the mapping names exists. This check fails on purpose if an entry is left out or a
   key is wrong, so it gets noticed (the app still shows a left-out entry, under "Not yet grouped").
2. Numbers are worked out from A to Z order each time: renaming one title in a test copy moves its number and the others' with it.
3. "Not yet grouped": an entry the mapping does not place shows in a last group of that name; a mapped key with no entry is skipped.
4. The screen: sections 1 to 6, a section's groups (2.3), a group's entries (2.3.4), the number on an entry page, Back one level at a
   time; openGuide lands on the entry and Back goes to its group.
5. Layout at 390x844, 360x640 and 320 px, dark and light, Classic and two other themes: no sideways scroll, taps 44 px or more, the
   number on one line at the right of the title's first line, no title word split or pushed off.
Run all tests with `python3 tests/run_all.py`, or serve the repo folder and run this file on its own."""
import os, sys, time
from playwright.sync_api import sync_playwright

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import test_v31 as t
from launch_helpers import wait_settled, tap_tab

results = []
GROUPED = ["colour-basics", "techniques", "tools-prep", "problems"]

def check(name, ok, detail=""):
    results.append(bool(ok))
    print(("PASS " if ok else "FAIL ") + name + ("" if ok else f"  -> {str(detail)[:600]}"))

def home(page):
    page.evaluate("() => { knowledgeCache = null; Object.assign(guidesState, { view: 'home', cat: '', group: '', key: '', kind: '', query: '', shownRows: {} }); renderGuides(); }")
    wait_settled(page)

def nums(page, sel):
    return page.evaluate("(s) => [...document.querySelectorAll(s)].map(r => [r.querySelector('.guides-row-title').textContent, (r.querySelector('.guides-num') || {}).textContent || ''])", sel)

# Layout of every visible numbered row and entry header: number on one line, at the right of the title's first line, inside the row,
# not over the title; no title word split across lines (a hyphen may break); no sideways scroll; taps 44 px or more.
LAYOUT = """() => {
    const bad = [];
    const rows = [...document.querySelectorAll('#compendium-body .guides-row, #compendium-body .guides-entry-head')].filter(r => r.offsetParent && r.querySelector('.guides-num'));
    for (const r of rows) {
        const n = r.querySelector('.guides-num').getBoundingClientRect(), ti = r.querySelector('.guides-row-title, .guides-title'), tr = ti.getBoundingClientRect(), rr = r.getBoundingClientRect();
        const first = ti.firstChild ? (() => { const g = document.createRange(); g.setStart(ti.firstChild, 0); g.setEnd(ti.firstChild, 1); return g.getBoundingClientRect(); })() : tr;
        if (n.height > 24 || n.right > rr.right + 0.5 || n.left < tr.right - 1 || n.top > first.bottom || n.bottom < first.top || tr.width < 40) bad.push(['place', ti.textContent, Math.round(n.height), Math.round(n.top - first.top)]);
        const node = ti.firstChild, re = /[^\\s-]+/g; let m;
        while (node && (m = re.exec(node.data))) { const g = document.createRange(); g.setStart(node, m.index); g.setEnd(node, m.index + m[0].length);
            if ([...g.getClientRects()].filter(x => x.width > 0).length > 1) bad.push(['split', m[0]]); }
    }
    const small = [...document.querySelectorAll('#compendium-body button')].filter(b => b.offsetParent && b.getBoundingClientRect().height < 44).map(b => b.textContent);
    return { rows: rows.length, bad, small, sideways: document.documentElement.scrollWidth > innerWidth + 1 };
}"""

def main():
    errors = []
    with sync_playwright() as p:
        browser = p.chromium.launch()
        ctx = browser.new_context(viewport={"width": 390, "height": 844}, service_workers="block")
        page = ctx.new_page()
        page.on("pageerror", lambda x: errors.append(str(x)))
        page.on("dialog", lambda d: (errors.append("dialog: " + d.message), d.dismiss()))
        t.load(page, launch=True, settings={"tab": "guides", "examplesChecked": True})
        page.wait_for_function("() => typeof guideGroupsOf === 'function'")

        print("\n--- 1. The mapping ---")
        r = page.evaluate("""(cats) => { const kn = knowledgeIndex(), out = {}, seen = new Map(), twiceAcross = [];
            for (const c of cats) { const x = guideGroupsOf(c);
                const keys = x.groups.flatMap(g => g.entries.map(e => e.key));
                for (const k of keys) { if (seen.has(k)) twiceAcross.push(k); seen.set(k, c); }
                out[c] = { unplaced: x.unplaced, unknown: x.unknown, twice: x.twice, placed: keys.length, all: kn.list({ category: c, kind: 'guide' }).length,
                           names: x.groups.map(g => g.name) }; }
            return { out, twiceAcross, other: Object.keys(GUIDE_GROUPS.sections).filter(k => !cats.includes(k)),
                     guides: kn.list({ kind: 'guide' }).length, inSections: [...seen.keys()].length }; }""", GROUPED)
        out = r["out"]
        check("every guide entry is in exactly one topic group of its own section (none left for 'Not yet grouped')",
              all(not o["unplaced"] and not o["twice"] and o["placed"] == o["all"] and "Not yet grouped" not in o["names"] for o in out.values())
              and not r["twiceAcross"] and r["inSections"] == r["guides"],
              {c: (o["unplaced"][:5], o["twice"][:5], o["placed"], o["all"]) for c, o in out.items()})
        check("every key the mapping names is a real entry of that section", all(not o["unknown"] for o in out.values()), {c: o["unknown"][:5] for c, o in out.items()})
        check("only the four grouped sections are in the mapping; Detail recipes and Basing keep their own groups", r["other"] == [], r["other"])

        print("\n--- 2. Numbers follow A to Z ---")
        r = page.evaluate("""(cats) => { const bad = [], cmp = (a, b) => a.localeCompare(b, 'en', { sensitivity: 'base' });
            cats.forEach((c, ci) => { const sec = String(GUIDE_CATEGORIES.findIndex(x => x.key === c) + 1), gs = guideGroupsOf(c).groups;
                const names = gs.map(g => g.name); if (names.join('|') !== [...names].sort(cmp).join('|')) bad.push(['groups', c]);
                gs.forEach((g, i) => { if (g.num !== sec + '.' + (i + 1)) bad.push(['gnum', g.name, g.num]);
                    const titles = g.entries.map(e => e.title); if (titles.join('|') !== [...titles].sort(cmp).join('|')) bad.push(['entries', g.name]);
                    g.entries.forEach((e, j) => { if (g.nums.get(e.key) !== g.num + '.' + (j + 1)) bad.push(['enum', e.key]); }); }); });
            return { bad, secs: GUIDE_CATEGORIES.map(c => guideSectionNumber(c.key)).join(' ') }; }""", GROUPED)
        check("sections are 1 to 6 in their fixed order; groups and entries are numbered by their A to Z place", not r["bad"] and r["secs"] == "1 2 3 4 5 6", r)
        # rename the first entry of Techniques 2.1 in a test copy so it sorts last: its number and its neighbours' move, the key does not
        r = page.evaluate("""() => { const g0 = guideGroupsOf('techniques').groups[0], first = g0.entries[0], second = g0.entries[1], n = g0.entries.length;
            const copy = GUIDE_ENTRIES.map(e => e.key === first.key ? Object.assign({}, e, { title: 'Zzz renamed in a test copy' }) : e);
            const kn = makeKnowledgeIndex({ guides: copy, recipes: [], basing: [], tips: [], parts: [], starters: [] });
            const g1 = guideGroupsOf('techniques', kn).groups.find(g => g.name === g0.name);
            return { before: [g0.nums.get(first.key), g0.nums.get(second.key)], after: [g1.nums.get(first.key), g1.nums.get(second.key)], n,
                     still: guidePlace(kn.get(first.key), kn), real: knowledgeIndex().get(first.key).title !== 'Zzz renamed in a test copy' }; }""")
        n = r["n"]
        check("renaming a title in a test copy renumbers by A to Z: it moves to the end, the next one moves up, the group stays",
              r["before"] == ["2.1.1", "2.1.2"] and r["after"] == [f"2.1.{n}", "2.1.1"] and r["still"]["num"] == f"2.1.{n}" and r["real"], r)
        r = page.evaluate("() => JSON.stringify(GUIDE_GROUPS) + JSON.stringify(localStorage) + JSON.stringify(guidesState)")
        check("no number is stored: not in the mapping, not in saved data, not in the screen's state", not __import__("re").search(r"\b[1-6]\.\d+\.\d+\b", r))

        print("\n--- 3. Not yet grouped ---")
        r = page.evaluate("""() => { const extra = { key: 'g2a-test-unmapped', category: 'techniques', title: 'Aardvark test entry', summary: 's', body: ['b'], related: [], keywords: [] };
            const kn = makeKnowledgeIndex({ guides: [...GUIDE_ENTRIES, extra], recipes: [], basing: [], tips: [], parts: [], starters: [] });
            const map = JSON.parse(JSON.stringify(GUIDE_GROUPS.sections)); map.techniques[0].keys.push('no-such-entry-key');
            const x = guideGroupsOf('techniques', kn, map), last = x.groups[x.groups.length - 1];
            return { unplaced: x.unplaced, unknown: x.unknown, last: last.name, num: last.num, n: x.groups.length, keys: last.entries.map(e => e.key),
                     shownAnywhere: x.groups.some(g => g.entries.some(e => e.key === 'no-such-entry-key')) }; }""")
        check("an entry the mapping leaves out shows in a last group 'Not yet grouped' (numbered after the others); a wrong key is skipped and reported",
              r["unplaced"] == ["g2a-test-unmapped"] and r["unknown"] == ["no-such-entry-key"] and r["last"] == "Not yet grouped"
              and r["num"] == f"2.{r['n']}" and r["keys"] == ["g2a-test-unmapped"] and not r["shownAnywhere"], r)
        tap_tab(page, "guides")
        page.click('#more-seg button[data-page="guides"]')
        page.evaluate("""() => { GUIDE_ENTRIES.push({ key: 'g2a-test-unmapped', category: 'techniques', title: 'Aardvark test entry', summary: 's', body: ['b'], related: [], keywords: [] }); }""")
        home(page)
        page.click('.guides-cats [data-cat="techniques"]')
        wait_settled(page)
        last = nums(page, ".guides-main .guides-groups .guides-row")[-1]
        page.click('.guides-main [data-group="Not yet grouped"]')
        wait_settled(page)
        check("on screen: 'Not yet grouped' is the last group of Techniques and lists the left-out entry",
              last[0] == "Not yet grouped" and nums(page, ".guides-main .guides-row") == [["Aardvark test entry", last[1] + ".1"]], (last, nums(page, ".guides-main .guides-row")))
        page.evaluate("() => { GUIDE_ENTRIES.pop(); }")

        print("\n--- 4. The screen ---")
        home(page)
        secs = nums(page, ".guides-cats .guides-row")
        check("home: the six sections show their numbers 1 to 6 at the right end of the row",
              [s[1] for s in secs] == ["1", "2", "3", "4", "5", "6"] and page.evaluate("() => [...document.querySelectorAll('.guides-cats .guides-row')].every(r => r.lastElementChild.classList.contains('guides-num'))"), secs)
        page.click('.guides-cats [data-cat="techniques"]')
        wait_settled(page)
        gs = nums(page, ".guides-main .guides-row")
        want = page.evaluate("() => guideGroupsOf('techniques').groups.map(g => [g.name, g.num])")
        check("a section lists its topic groups A to Z, each with its number (2.1, 2.2 ...), and nothing else", gs == want and len(gs) > 5 and gs[0][1] == "2.1", gs[:4])
        name = want[2][0]
        page.click(f'.guides-main [data-group="{name}"]')
        wait_settled(page)
        es = nums(page, ".guides-main .guides-row")
        want = page.evaluate("(n) => { const g = guideGroupsOf('techniques').groups.find(x => x.name === n); return g.entries.map(e => [e.title, g.nums.get(e.key)]); }", name)
        check("a group shows its heading and its entries A to Z with title, summary and number (2.3.1 ...)",
              es == want and page.inner_text(".guides-main .guides-title") == name and page.locator(".guides-main .guides-row-summary").count() == len(es)
              and page.inner_text("#guides-back") == "Back to Techniques", es[:3])
        page.click(".guides-main .guides-row >> nth=1")
        wait_settled(page)
        check("an entry page shows its number at the top right of its header",
              page.inner_text(".guides-entry .guides-entry-head .guides-num") == es[1][1] and page.inner_text(".guides-entry h3") == es[1][0]
              and page.inner_text("#guides-back") == f"Back to {name}")
        page.click("#guides-back")
        wait_settled(page)
        check("Back from an entry goes to its group, with that entry's row focused",
              page.inner_text(".guides-main .guides-title") == name and page.evaluate("(t) => document.activeElement.querySelector('.guides-row-title').textContent === t", es[1][0]))
        page.click("#guides-back")
        wait_settled(page)
        check("Back from a group goes to the section's groups", page.locator(".guides-main .guides-groups").count() == 1 and page.inner_text("#guides-back") == "Back to Guides")
        page.click("#guides-back")
        wait_settled(page)
        check("Back from a section goes to the home list", page.locator(".guides-cats").count() == 1 and page.locator("#guides-back").count() == 0)
        page.fill("#guides-search", "rust")
        page.wait_for_selector(".guides-lower .guides-row[data-guide]")
        check("search results are left as they were (no numbers in this chunk)", page.locator(".guides-lower .guides-num").count() == 0)
        hit = page.get_attribute(".guides-lower .guides-row[data-guide]", "data-guide")
        page.click(".guides-lower .guides-row[data-guide]")
        page.wait_for_selector(".guides-entry")
        page.click("#guides-back")
        wait_settled(page)
        f = page.evaluate("() => { const a = document.activeElement; return { key: a.dataset.guide || '', tag: a.tagName, shown: !!a.offsetParent, main: !!a.closest('.guides-main') }; }")
        check("Back from a search result on a phone focuses that entry's row in its group (not a hidden search row)", f == {"key": hit, "tag": "BUTTON", "shown": True, "main": True}, f)
        home(page)
        page.click('.guides-cats [data-cat="detail"]')
        page.wait_for_selector(".guides-main .detail-recipes")
        check("Detail recipes keeps its own controls, with no numbers yet", page.locator(".guides-main .guides-num").count() == 0)

        # openGuide from another screen: the entry, its number, Back to its group (Mentor source links call openGuide too; test_v103 checks those)
        key = "preparing-resin-models"
        place = page.evaluate("(k) => guidePlace(knowledgeIndex().get(k))", key)
        tap_tab(page, "dashboard")
        wait_settled(page)
        page.evaluate("(k) => openGuide(k)", key)
        page.wait_for_selector(".guides-entry")
        check("openGuide(key) lands on that entry with its number, and Back goes to its group",
              page.get_attribute(".guides-entry", "id") == "guide-" + key and page.inner_text(".guides-entry .guides-num") == place["num"]
              and page.inner_text("#guides-back") == "Back to " + place["group"] and page.evaluate("() => guidesState.group") == place["group"], place)
        page.evaluate("() => openGuide(GUIDE_STARTERS[0].key, 'starter')")
        wait_settled(page)
        check("an entry with no group (a starter question) shows no number and goes back to Guides",
              page.locator(".guides-entry .guides-num").count() == 0 and page.inner_text("#guides-back") == "Back to Guides")

        # speed: every list is worked out when it is drawn, so drawing must stay quick with every entry loaded
        ms = page.evaluate("""(cats) => { const t0 = performance.now(); let n = 0;
            for (const c of cats) { Object.assign(guidesState, { view: 'category', cat: c, group: '', key: '', kind: '', query: '' }); renderGuides();
                for (const g of guideGroupsOf(c).groups) { Object.assign(guidesState, { view: 'group', group: g.name }); renderGuides(); n++; } }
            return [(performance.now() - t0) / (n + cats.length), n]; }""", GROUPED)
        check("drawing a section or a group takes under 50 ms on average with all entries loaded", ms[0] < 50, ms)

        print("\n--- 5. Phones, light and dark, themes ---")
        long_group = page.evaluate("""() => { let best = null; for (const c of ['techniques', 'tools-prep']) for (const g of guideGroupsOf(c).groups) {
            const w = Math.max(...g.entries.map(e => e.title.length)); if (!best || w > best[2]) best = [c, g.name, w]; } return best; }""")
        configs = [(390, 844, "dark", "classic"), (390, 844, "light", "forge"), (360, 640, "light", "classic"), (360, 640, "dark", "parchment"),
                   (320, 640, "dark", "classic"), (320, 640, "light", "parchment")]
        page.evaluate("() => window.scrollTo(0, 0)")
        for w, h, scheme, theme in configs:
            # one page: the size changes, and the theme and light or dark are set the way the Theme and Appearance buttons set them
            page.set_viewport_size({"width": w, "height": h})
            r = page.evaluate("""([th, lt]) => { settings.theme = th; settings.appearance = lt ? 'light' : 'dark'; applyPalette(settings.palette); render();
                const d = document.documentElement.dataset; return [d.t, d.m]; }""", [theme, scheme == "light"])
            home(page)
            page.evaluate("() => document.fonts.ready.then(() => true)")   # a theme's own font has loaded before anything is measured
            seen = []
            for step in ("home", "groups", "entries", "entry"):
                if step == "groups":
                    page.click(f'.guides-cats [data-cat="{long_group[0]}"]')
                elif step == "entries":
                    page.click(f'.guides-main [data-group="{long_group[1]}"]')
                elif step == "entry":
                    page.click(".guides-main .guides-row >> nth=0")
                    page.evaluate("() => window.scrollTo(0, 0)")
                wait_settled(page)
                seen.append((step, page.evaluate(LAYOUT)))
            check(f"{w}x{h} {scheme} {theme}: numbers on one line at the right of the title's first line, no word split, taps 44 px, no sideways scroll",
                  r == [theme, scheme] and all(m["rows"] >= 1 and not m["bad"] and not m["small"] and not m["sideways"] for _, m in seen), [x for x in seen if x[1]["bad"] or x[1]["small"] or x[1]["sideways"]])

        check("no page errors or pop-ups", errors == [], errors)
        browser.close()
    print(f"\n{sum(results)}/{len(results)} checks passed")
    return 0 if all(results) else 1

if __name__ == "__main__":
    sys.exit(main())
