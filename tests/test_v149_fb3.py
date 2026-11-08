"""FB3 tests for Minifolio (fewer menus). New behaviour only:
1. About and Credits are one page: five sub-tabs, no Credits tab, a Credits section on About with the same content, every old link scrolls to it.
2. Five small Settings texts are gone; "What's sent" stays on purpose (it says when the switch takes effect, which Help does not); the Privacy link is there.
3. Bundles: Appearance and Themes (Theme, Stages, Mentor look, Colours) and Your data (now holding Counting visits and Shop links).
4. Moved controls keep their saved values after a reload and after a restore.
5. No sideways scroll at 390, 360 and 320 px, and the page is shorter.
Run all tests with `python3 tests/run_all.py`, or serve the repo folder and run this file on its own."""
import json, os, sys
from playwright.sync_api import sync_playwright

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import test_v31 as t
from launch_helpers import wait_settled

results = []

def check(name, ok, detail=""):
    results.append(bool(ok))
    print(("PASS " if ok else "FAIL ") + name + ("" if ok else f"  -> {detail}"))

def open_page(page, which, settings=None, w=390, h=844):
    page.set_viewport_size({"width": w, "height": h})
    t.load(page, settings=dict({"examplesChecked": True}, **(settings or {})), launch=True)
    page.click('.tabs button[data-tab="guides"]')
    wait_settled(page)
    page.click(f'#more-seg button[data-page="{which}"]')
    wait_settled(page)

def open_fold(page, key):
    b = page.locator(f"#card-fold-{key}-button")
    if b.get_attribute("aria-expanded") != "true":
        b.click()
    page.wait_for_selector(f"#card-fold-{key}-panel:not([hidden])")

def credits_in_view(page):
    return page.evaluate("""() => { const r = document.querySelector('#view-credits h2').getBoundingClientRect();
        const bar = document.querySelector('.app-bar').getBoundingClientRect().bottom;
        return { top: r.top, bar, vh: innerHeight, about: !document.getElementById('view-about').classList.contains('hidden') }; }""")

def main():
    errors = []
    with sync_playwright() as p:
        browser = p.chromium.launch()
        ctx = browser.new_context(viewport={"width": 390, "height": 844}, service_workers="block", reduced_motion="reduce")
        page = ctx.new_page()
        page.on("pageerror", lambda x: errors.append(str(x)))

        print("\n--- 1. About and Credits ---")
        open_page(page, "about")
        tabs = page.evaluate("() => [...document.querySelectorAll('#more-seg button')].map(b => b.textContent.trim())")
        check("five sub-tabs and no Credits tab", tabs == ["About", "Guides", "Settings", "How it works", "Updates"], tabs)
        check("the Credits section sits inside About, below the About card", page.evaluate(
            "() => { const s = document.getElementById('view-credits'); const a = document.querySelector('.about-card');"
            " return document.getElementById('view-about').contains(s) && s.getBoundingClientRect().top > a.getBoundingClientRect().bottom - 1; }"))
        rows = page.evaluate("() => ({ heads: [...document.querySelectorAll('#view-credits h2, #view-credits h3')].map(h => h.textContent.trim()),"
                             " fonts: document.querySelectorAll('#credits-fonts li').length,"
                             " reader: [...document.querySelectorAll('#credits-reader strong')].map(e => e.textContent.trim()),"
                             " paints: document.querySelectorAll('#credits-paints li').length })")
        check("same content: Credits, Fonts, Pot-label reader, Paint list", rows["heads"] == ["Credits", "Fonts", "Pot-label reader", "Paint list"], rows["heads"])
        check("same rows: 11 fonts, three reader rows (with Leptonica and libtiff), one paint list", rows["fonts"] == 11 and rows["reader"][1:] == ["Leptonica", "libtiff"] and rows["paints"] == 1, rows)
        check("the Thanks section is still hidden while its list is empty", page.evaluate("() => document.getElementById('credits-thanks').classList.contains('hidden')"))
        check("About keeps one Privacy link, opening the page safely in a new tab", page.evaluate(
            "() => { const l = [...document.querySelectorAll('#view-about a.privacy-page-link')]; return l.length === 1 && l[0].getAttribute('href') === 'privacy' && l[0].target === '_blank' && l[0].rel === 'noopener noreferrer'; }"))
        for sel in ("#about-credits-link", "#about-rights-credits"):
            open_page(page, "about")
            page.click(sel)
            wait_settled(page)
            v = credits_in_view(page)
            check(f"{sel} scrolls to the Credits heading, clear of the header", v["about"] and v["top"] >= v["bar"] and v["top"] < v["vh"], v)
        for sel in ("#help-credits-link", "#help-rights-credits"):
            open_page(page, "help")
            page.evaluate("() => { document.querySelectorAll('#view-help details').forEach(d => d.open = true); }")
            page.locator(sel).scroll_into_view_if_needed()
            page.click(sel)
            wait_settled(page)
            v = credits_in_view(page)
            check(f"Help's {sel} opens About and scrolls to Credits", v["about"] and v["top"] >= v["bar"] and v["top"] < v["vh"], v)
        page.evaluate("() => showTab('credits')")
        wait_settled(page)
        v = credits_in_view(page)
        check("showTab('credits') (the old page name) also lands there", v["about"] and v["top"] >= v["bar"] and v["top"] < v["vh"], v)

        print("\n--- 2. Settings texts ---")
        open_page(page, "settings")
        text = page.evaluate("() => document.getElementById('view-settings').textContent")
        for gone in ("Which one?", "About looks", "About light mode", "What can be imported", "Who gets what", "CSV columns", "Save backup leaves out photos"):
            check(f"'{gone}' is gone from Settings", gone not in text)
        check("their elements and Help words that only served them are gone", page.evaluate(
            "() => ['backup-explain','appearance-note','palette-light-note','import-explain','shoplinks-note'].every(i => !document.getElementById(i))"))
        check("'What's sent' stays (stopped on: it says when the switch takes effect, which Help does not)", "What's sent" in text and "Takes effect the next time the app opens" in text)
        check("the Privacy link sits under the Counting visits switch and opens the privacy page in a new tab", page.evaluate(
            "() => { const l = document.getElementById('settings-privacy-link'); const c = document.getElementById('counting-card');"
            " return c.contains(l) && l.getAttribute('href') === 'privacy' && l.target === '_blank' && l.rel === 'noopener noreferrer'; }"))

        print("\n--- 3. Bundles ---")
        tops = page.evaluate("() => [...document.querySelectorAll('#view-settings > .card')].filter(c => c.querySelector(':scope > h2, :scope > .card-fold-button') && getComputedStyle(c).display !== 'none' && c.id !== 'review-card')"
                             ".map(c => (c.querySelector(':scope > h2') || c).textContent.trim())")
        check("seven top-level sections, with Appearance and Themes in the place of eight cards", len(tops) == 7 and "Appearance and Themes" in tops, tops)
        check("the old cards are no longer top-level", not any(n in tops for n in ("Stages", "Appearance", "Theme", "Mentor look", "Counting visits", "Shop links", "Colours")), tops)
        open_fold(page, "appearance-themes")
        parts = page.evaluate("() => [...document.querySelectorAll('#appearance-themes-card > .card-fold-panel > .settings-part > h3')].map(h => h.textContent.trim())")
        check("Appearance and Themes holds Theme, Stages, Mentor look, Colours in that order", parts == ["Theme", "Stages", "Mentor look", "Colours"], parts)
        order = page.evaluate("""() => { const p = document.getElementById('theme-card');
            const chips = [...p.querySelectorAll('[data-appearance-choice]')].map(b => b.textContent.trim());
            const looks = [...p.querySelectorAll('[data-theme-choice]')].map(b => b.textContent.trim());
            const a = p.querySelector('.appearance-chips'), r = p.querySelector('.theme-row');
            return { chips, looks, chipsFirst: !!(a.compareDocumentPosition(r) & Node.DOCUMENT_POSITION_FOLLOWING) }; }""")
        check("Theme is one part: Dark, Light, Match my phone first, then the four looks", order["chips"] == ["Dark", "Light", "Match my phone"] and order["chipsFirst"] and len(order["looks"]) == 4, order)
        check("the looks keep their names", [x.split("\n")[0] for x in order["looks"]] and all(n in " ".join(order["looks"]) for n in ("Classic", "Parchment Codex", "Grim Forge", "Paint Bench")), order["looks"])
        open_fold(page, "your-data")
        yd = page.evaluate("() => [...document.querySelectorAll('#your-data-card .settings-part > h3')].map(h => h.textContent.trim())")
        check("Your data holds Counting visits and Shop links, each as its own headed part", yd == ["Counting visits", "Shop links"], yd)
        check("the controls are all still there", page.evaluate(
            "() => ['count-visits','show-shop-links','palette-select','stage-list','add-stage','save-stages','done-from','delete-all'].every(i => document.getElementById(i))"))
        page.select_option("#palette-select", "greyscale")
        check("Colours still changes the stage colours", page.evaluate("() => JSON.parse(localStorage.getItem('shades-of-grey-settings')).palette") == "greyscale")
        page.click("#add-stage")
        check("the stage list editor still adds a stage row", page.evaluate("() => document.querySelectorAll('#stage-list li').length") > 0)

        print("\n--- 4. Saved values ---")
        saved = {"appearance": "light", "theme": "parchment", "mentorLook": "magical", "countVisits": False, "hideShopLinks": True, "palette": "ice"}
        def values():
            return page.evaluate("""() => ({
                appearance: document.querySelector('[data-appearance-choice][aria-pressed=true]').dataset.appearanceChoice,
                theme: document.querySelector('[data-theme-choice][aria-pressed=true]').dataset.themeChoice,
                mentor: document.querySelector('[data-mentor-look][aria-pressed=true]').dataset.mentorLook,
                count: document.getElementById('count-visits').checked, shop: document.getElementById('show-shop-links').checked,
                palette: document.getElementById('palette-select').value })""")
        want = {"appearance": "light", "theme": "parchment", "mentor": "magical", "count": False, "shop": False, "palette": "ice"}
        open_page(page, "settings", saved)
        check("after a reload every moved control shows its saved value", values() == want, values())
        backup = page.evaluate("backupData()")
        open_page(page, "settings", {"appearance": "dark", "theme": "classic", "mentorLook": "grounded", "countVisits": True, "hideShopLinks": False, "palette": "frost"})
        page.set_input_files("#restore-file", files=[{"name": "b.json", "mimeType": "application/json", "buffer": json.dumps(backup).encode()}])
        page.wait_for_selector("#dialog-yes", state="visible")
        page.click("#dialog-yes")
        page.wait_for_function("() => document.documentElement.dataset.t === 'parchment'", timeout=5000)
        got = values()
        check("a restored backup brings back the looks, light and dark and colours", (got["appearance"], got["theme"], got["palette"]) == ("light", "parchment", "ice"), got)
        check("the Counting visits and Shop links switches are not in backups, so a restore leaves them alone", got["count"] is True and got["shop"] is True, got)
        page.evaluate("() => { document.getElementById('count-visits').click(); document.getElementById('show-shop-links').click(); }")
        s = page.evaluate("() => JSON.parse(localStorage.getItem('shades-of-grey-settings'))")
        check("both switches still save the same keys", s.get("countVisits") is False and s.get("hideShopLinks") is True, s)

        print("\n--- 5. Fit and height ---")
        for w, h in ((390, 844), (360, 640), (320, 568)):
            open_page(page, "settings", None, w, h)
            fit = page.evaluate("() => ({ sideways: document.documentElement.scrollWidth > innerWidth, screens: document.documentElement.scrollHeight / innerHeight })")
            check(f"{w}x{h}: Settings has no sideways scroll", not fit["sideways"], fit)
            if w == 390:
                check("390x844: Settings closed is under two screens tall", fit["screens"] < 2, fit)
        for w, h in ((390, 844), (320, 568)):
            open_page(page, "about", {"appearance": "light", "theme": "forge"}, w, h)
            check(f"{w}x{h}: About with Credits has no sideways scroll (light, Grim Forge)", not page.evaluate("() => document.documentElement.scrollWidth > innerWidth"))
        links = page.evaluate("() => [...document.querySelectorAll('#view-about a, #view-about button.link-button')].map(e => { const r = e.getBoundingClientRect(); return [e.textContent.trim().slice(0, 20), Math.round(r.height)]; })")
        check("About and Credits links are 44 px tall", all(hh >= 44 for _, hh in links), links)
        check("no errors in the page", not errors, errors[:2])
        browser.close()
    print(f"\n{sum(results)}/{len(results)} checks passed")
    sys.exit(0 if all(results) else 1)

if __name__ == "__main__":
    main()
