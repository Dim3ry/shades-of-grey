"""G2b tests for Minifolio (Guides A to Z view, numbers in search, See also links). New behaviour only:
1. See also data: every key in GUIDE_GROUPS.seeAlso is a real entry, never the entry itself, at most 3, none twice; a wrong key is skipped.
2. A to Z: a Topics | A to Z switch on the Guides home list; A to Z lists every entry of every section once, alphabetically, and each
   guide entry carries the same number as in the grouped browse (detail recipes and basing tips have none yet); a row opens its entry.
3. Search results show the same numbers, in the order search already gave (matching and ranking are unchanged).
4. See also row on an entry page: a small heading and up to 3 links, each opening the right entry; no row when an entry has none.
5. Layout at 390x844, 360x640 and 320 px, dark and light: no sideways scroll, taps 44 px or more, the search box wide, the number on the
   title's first line inside the row, and the switch and the See also links reachable (not under the bottom band).
Run all tests with `python3 tests/run_all.py`, or serve the repo folder and run this file on its own."""
import os, sys
from playwright.sync_api import sync_playwright

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import test_v31 as t
from launch_helpers import wait_settled, tap_tab

results = []

def check(name, ok, detail=""):
    results.append(bool(ok))
    print(("PASS " if ok else "FAIL ") + name + ("" if ok else f"  -> {str(detail)[:600]}"))

def home(page, order="topics"):
    page.evaluate("(o) => { Object.assign(guidesState, { view: 'home', cat: '', group: '', key: '', kind: '', query: '', order: o, shownRows: {} }); renderGuides(); }", order)
    wait_settled(page)

# every entry's grouped number, worked out here from the grouped browse itself (section by section), so A to Z and search are compared to it
GROUPED_NUMS = """() => { const m = {}; for (const c of GUIDE_CATEGORIES) for (const g of guideGroupsOf(c.key).groups) for (const [k, n] of g.nums) m[k] = n; return m; }"""
ROWS = """(sel) => [...document.querySelectorAll(sel)].map(r => [r.dataset.guide, r.dataset.kind, r.querySelector('.guides-row-title').textContent, (r.querySelector('.guides-num') || {}).textContent || ''])"""

# visible numbered rows: number on one line, on the title's first line, inside the row; no sideways scroll; taps 44 px or more;
# the chosen elements reachable: scrolled to the middle of the screen, the element itself is what a tap there hits (not the bottom band)
LAYOUT = """(reach) => {
    const bad = [];
    for (const r of [...document.querySelectorAll('#compendium-body .guides-row-numbered')].filter(r => r.offsetParent)) {
        const n = r.querySelector('.guides-num').getBoundingClientRect(), ti = r.querySelector('.guides-row-title'), rr = r.getBoundingClientRect();
        const g = document.createRange(); g.setStart(ti.firstChild, 0); g.setEnd(ti.firstChild, 1); const first = g.getBoundingClientRect();
        if (n.height > 24 || n.right > rr.right + 0.5 || n.left < ti.getBoundingClientRect().right - 1 || n.top > first.bottom || n.bottom < first.top) bad.push(ti.textContent);
    }
    const small = [...document.querySelectorAll('#compendium-body button')].filter(b => b.offsetParent && b.getBoundingClientRect().height < 44).map(b => b.textContent);
    const hidden = [];
    for (const el of [...document.querySelectorAll(reach)].filter(e => e.offsetParent)) {
        el.scrollIntoView({ block: 'center' }); const b = el.getBoundingClientRect(), hit = document.elementFromPoint(b.left + b.width / 2, b.top + b.height / 2);
        if (!hit || !el.contains(hit)) hidden.push(el.textContent);
    }
    const s = document.getElementById('guides-search');
    return { bad, small, hidden, search: s && s.offsetParent ? Math.round(s.getBoundingClientRect().width) : -1, sideways: document.documentElement.scrollWidth > innerWidth + 1 };
}"""

def main():
    errors = []
    with sync_playwright() as p:
        browser = p.chromium.launch()
        ctx = browser.new_context(viewport={"width": 390, "height": 844}, service_workers="block")
        page = ctx.new_page()
        page.on("pageerror", lambda x: errors.append(str(x)))
        page.on("dialog", lambda d: (errors.append("dialog: " + d.message), d.dismiss()))
        t.load(page, settings={"tab": "guides", "examplesChecked": True})
        tap_tab(page, "guides")
        page.click('#more-seg button[data-page="guides"]')
        page.wait_for_function("() => typeof guideSeeAlso === 'function'")
        wait_settled(page)

        print("\n--- 1. See also data ---")
        r = page.evaluate("""() => { const kn = knowledgeIndex(), bad = [];
            for (const [from, keys] of Object.entries(GUIDE_GROUPS.seeAlso)) {
                if (!kn.get(from)) bad.push(['no entry', from]);
                if (!Array.isArray(keys) || !keys.length || keys.length > 3 || new Set(keys).size !== keys.length) bad.push(['list', from]);
                for (const k of keys || []) { if (!kn.get(k)) bad.push(['unknown', from, k]); if (k === from) bad.push(['self', from]); } }
            return { bad, n: Object.keys(GUIDE_GROUPS.seeAlso).length }; }""")
        check("every See also key is a real entry and not the entry itself; each list has 1 to 3 keys, none twice", not r["bad"] and r["n"] > 0, r)
        r = page.evaluate("""() => { const keep = GUIDE_GROUPS.seeAlso, e = knowledgeIndex().get('layering');
            GUIDE_GROUPS.seeAlso = { layering: ['no-such-key', 'layering', 'glazing', 'glazing', 'drybrushing', 'edge-highlighting', 'wet-blending'] };
            const out = guideSeeAlso(e).map(x => x.key); GUIDE_GROUPS.seeAlso = keep; return out; }""")
        check("a wrong key, the entry's own key and a repeat are skipped, and at most 3 show", r == ["glazing", "drybrushing", "edge-highlighting"], r)

        print("\n--- 2. A to Z ---")
        home(page)
        seg = page.evaluate("() => [...document.querySelectorAll('.guides-lower .guides-order [data-order]')].map(b => [b.textContent, b.getAttribute('aria-selected')])")
        check("the home list has a Topics | A to Z switch above the sections, Topics chosen", seg == [["Topics", "true"], ["A to Z", "false"]]
              and page.locator(".guides-lower .guides-order + .guides-cats").count() == 1, seg)
        page.click('.guides-order [data-order="az"]')
        wait_settled(page)
        check("A to Z replaces the sections with one list and keeps focus on the switch",
              page.locator(".guides-lower .guides-cats").count() == 0 and page.locator(".guides-lower .guides-az .guides-row").count() == 30
              and page.evaluate("() => document.activeElement.dataset.order === 'az' && document.activeElement.getAttribute('aria-selected') === 'true'"))
        page.evaluate("() => { guidesState.shownRows = { az: 100000 }; renderGuides(); }")
        rows = page.evaluate(ROWS, ".guides-lower .guides-az .guides-row")
        want = page.evaluate("""() => { const kn = knowledgeIndex(), cats = GUIDE_CATEGORIES.map(c => c.key);
            return kn.entries.filter(e => cats.includes(e.category) && ['guide', 'detail', 'basing'].includes(e.kind)).map(e => e.kind + ':' + e.key).sort(); }""")
        got = sorted(f"{k}:{g}" for g, k, _, _ in rows)
        check("A to Z lists every entry of every section exactly once (guides, detail recipes and basing tips)", got == want and len(rows) > 600, (len(got), len(want)))
        titles = [x[2] for x in rows]
        okorder = page.evaluate("(ts) => ts.every((x, i) => i === 0 || ts[i - 1].localeCompare(x, 'en', { sensitivity: 'base' }) <= 0)", titles)
        check("A to Z is alphabetical by title", okorder, titles[:5])
        nums = page.evaluate(GROUPED_NUMS)
        wrong = [x for x in rows if x[1] == "guide" and x[3] != nums.get(x[0])]
        check("every guide entry's number in A to Z is its number in the grouped browse", not wrong and sum(1 for x in rows if x[3]) == len(nums), wrong[:5])
        check("detail recipes and basing tips show no number yet", all(x[3] == "" for x in rows if x[1] != "guide"))
        # one entry: open it from A to Z, then the same entry through the grouped browse shows the same number
        key = "painting-rust"
        n_az = next(x[3] for x in rows if x[0] == key)
        page.click(f'.guides-az [data-guide="{key}"]')
        page.wait_for_selector(f"#guide-{key}")
        n_page = page.inner_text(".guides-entry .guides-num")
        cat, grp = page.evaluate("(k) => { const e = knowledgeIndex().get(k); return [e.category, guidePlace(e).group]; }", key)
        home(page)
        page.click(f'.guides-cats [data-cat="{cat}"]')
        page.click(f'.guides-main [data-group="{grp}"]')
        wait_settled(page)
        n_grp = page.inner_text(f'.guides-main [data-guide="{key}"] .guides-num')
        check("an A to Z row opens its entry, and its number matches the entry page and the grouped list", n_az == n_page == n_grp and n_az, (n_az, n_page, n_grp))
        home(page, "az")
        page.click('.guides-order [data-order="topics"]')
        wait_settled(page)
        check("Topics brings the sections back", page.locator(".guides-lower .guides-cats").count() == 1 and page.locator(".guides-az").count() == 0)

        print("\n--- 3. Search ---")
        for order in ("topics", "az"):
            home(page, order)
            page.fill("#guides-search", "rust")
            page.wait_for_selector(".guides-lower .guides-row[data-guide]")
            rows = page.evaluate(ROWS, ".guides-lower .guides-row")
            same = page.evaluate("(q) => knowledgeIndex().search(q).slice(0, 30).map(e => e.kind + ':' + e.key)", "rust") == [f"{k}:{g}" for g, k, _, _ in rows]
            wrong = [x for x in rows if x[3] != (nums.get(x[0], "") if x[1] == "guide" else "")]
            check(f"search ({order}): results keep search's own order and show the grouped number on each guide row, none on others",
                  same and not wrong and any(x[3] for x in rows) and page.locator(".guides-lower .guides-order").count() == 0, (same, wrong[:3]))

        print("\n--- 4. See also ---")
        src = page.evaluate("() => Object.keys(GUIDE_GROUPS.seeAlso).find(k => GUIDE_GROUPS.seeAlso[k].length >= 2)")
        targets = page.evaluate("(k) => GUIDE_GROUPS.seeAlso[k]", src)
        page.evaluate("(k) => openGuide(k)", src)
        page.wait_for_selector(f"#guide-{src}")
        wait_settled(page)
        r = page.evaluate("""() => { const box = document.querySelector('.guides-entry .guides-seealso'); if (!box) return null;
            const h = box.querySelector('.similar-label'), links = [...box.querySelectorAll('.guides-seealso-link')], cs = getComputedStyle(h), ls = links.map(l => getComputedStyle(l));
            const muted = getComputedStyle(document.documentElement).getPropertyValue('--muted').trim(), probe = document.createElement('span');
            probe.style.color = 'var(--accent)'; document.body.appendChild(probe); const accent = getComputedStyle(probe).color; probe.style.color = muted; const mutedRgb = getComputedStyle(probe).color; probe.remove();
            const tops = links.map(l => l.getBoundingClientRect().top), lastP = [...document.querySelectorAll('.guides-entry > p')].pop();
            return { head: h.textContent, upper: cs.textTransform, headMuted: cs.color === mutedRgb, keys: links.map(l => l.dataset.seeAlso), titles: links.map(l => l.textContent),
                     accent: ls.every(s => s.color === accent), ownLine: tops.every((y, i) => i === 0 || y >= tops[i - 1] + 43), tall: links.every(l => l.getBoundingClientRect().height >= 44),
                     underText: !!lastP && box.getBoundingClientRect().top >= lastP.getBoundingClientRect().bottom }; }""")
        want_titles = page.evaluate("(ks) => ks.map(k => knowledgeIndex().get(k).title)", targets)
        check("an entry with See also keys shows the row: a small muted upper-case 'See also' heading and its entries' titles, in order",
              r and r["head"] == "See also" and r["upper"] == "uppercase" and r["headMuted"] and r["keys"] == targets and r["titles"] == want_titles, r)
        check("the See also links are accent-coloured, one per line, 44 px tall, under the entry's text",
              r and r["accent"] and r["ownLine"] and r["tall"] and r["underText"], r)
        page.click(f'.guides-seealso-link[data-see-also="{targets[1]}"]')
        page.wait_for_selector(f"#guide-{targets[1]}")
        wait_settled(page)
        place = page.evaluate("(k) => guidePlace(knowledgeIndex().get(k))", targets[1])
        check("a See also link opens that entry (with its number and Back to its group), as openGuide does",
              page.evaluate("() => guidesState.view === 'entry' && guidesState.key") == targets[1] and page.inner_text(".guides-entry .guides-num") == place["num"]
              and page.inner_text("#guides-back") == "Back to " + place["group"], place)
        none = page.evaluate("() => GUIDE_ENTRIES.find(e => !GUIDE_GROUPS.seeAlso[e.key]).key")
        page.evaluate("(k) => openGuide(k)", none)
        page.wait_for_selector(f"#guide-{none}")
        check("an entry with no See also keys shows no See also row", page.locator(".guides-seealso").count() == 0 and page.locator("text=See also").count() == 0)

        print("\n--- 5. Phones, light and dark ---")
        configs = [(390, 844, "dark"), (360, 640, "light"), (320, 640, "dark"), (320, 640, "light")]
        for w, h, scheme in configs:
            page.set_viewport_size({"width": w, "height": h})
            page.evaluate("(lt) => { settings.appearance = lt ? 'light' : 'dark'; applyPalette(settings.palette); render(); }", scheme == "light")
            seen = []
            home(page)
            seen.append(("topics", page.evaluate(LAYOUT, ".guides-order button")))
            home(page, "az")
            seen.append(("az", page.evaluate(LAYOUT, ".guides-order button, .guides-more")))
            page.fill("#guides-search", "highlight")
            page.wait_for_selector(".guides-lower .guides-row-numbered")
            seen.append(("search", page.evaluate(LAYOUT, ".guides-more")))
            page.evaluate("(k) => openGuide(k)", src)
            page.wait_for_selector(".guides-seealso")
            wait_settled(page)
            seen.append(("entry", page.evaluate(LAYOUT, ".guides-seealso-link")))
            badness = [x for x in seen if x[1]["bad"] or x[1]["small"] or x[1]["hidden"] or x[1]["sideways"] or (x[0] != "entry" and x[1]["search"] < 200)]
            check(f"{w}x{h} {scheme}: no sideways scroll, taps 44 px, search box wide, numbers on the first line, switch and links reachable",
                  page.evaluate("() => document.documentElement.dataset.m") == scheme and not badness, badness)

        check("no page errors or pop-ups", errors == [], errors)
        browser.close()
    print(f"\n{sum(results)}/{len(results)} checks passed")
    return 0 if all(results) else 1

if __name__ == "__main__":
    sys.exit(main())
