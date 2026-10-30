"""X2 tests for Minifolio (Tools and Settings). New behaviour only:
1. The fourth bar segment and start-circle segment say Tools; the page heading says Tools and Settings; its switch is Guides, Settings, Help, Updates.
2. The header cog is gone and the basket stays. The segment is lit on all four pages. The Compendium tab is gone.
3. Guides holds Detail recipes and Basing tips, working as before; Show steps from Ideas for this lands there.
4. Old state: a saved tab or address of "compendium" opens Guides; "settings" still opens Settings; an unknown tab falls back; an old backup restores.
5. The start circle glides into the bar for the new label; the section slide runs between sections but not between the four pages.
6. 360 and 390 px, dark and light: no sideways scroll, taps 44 px or more. No new network use; no faction words in the new text.
Run all tests with `python3 tests/run_all.py`, or serve the repo folder and run this file on its own."""
import os, sys, re, json
from playwright.sync_api import sync_playwright

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import test_v31 as t
from launch_helpers import wait_settled, app_ready, leave_launch

results = []
FACTION_WORDS = re.compile(r"tyranid|space marine|ork|necron|eldar|ultramarine|warhammer|citadel|games workshop|chaos|imperial", re.I)

def check(name, ok, detail=""):
    results.append(bool(ok))
    print(("PASS " if ok else "FAIL ") + name + ("" if ok else f"  -> {detail}"))

PAINTS = [{"id": 1, "brand": "Citadel", "name": "Macragge Blue", "colour": "#0d407f", "status": "owned"}]
UNITS = [{"id": 1, "name": "Squad", "hobby": "40K", "stage": 2, "count": 5, "added": "2026-10-01", "log": [["2026-10-01", 2]]}]

def texts(page, sel):
    return page.evaluate("(s) => [...document.querySelectorAll(s)].map(b => b.textContent.trim())", sel)

def lit(page):
    return page.evaluate("() => [...document.querySelectorAll('.arc [aria-current=page]')].map(b => b.dataset.tab)")

def settle(page):
    wait_settled(page)

# the first keyframes of whatever moves on the page in the same call as the tap, so a slow machine cannot finish first
TAP = """(sel) => { const before = document.querySelector('main > section:not(.hidden)');
    document.querySelector(sel).click();
    const moving = [...document.querySelectorAll('main > section')].flatMap(s => s.getAnimations().map(a => { const k = a.effect.getKeyframes()[0]; return k.transform || ('o' + k.opacity); }));
    return { layer: before.classList.contains('mo-out'), moving, orb: document.getElementById('mentor-button').getAnimations().length,
             ghost: !!document.querySelector('.mo-ring, .mo-ghost') }; }"""

def main():
    errors, outside = [], []
    app, html = t.read("app.js"), t.read("index.html")
    with sync_playwright() as p:
        browser = p.chromium.launch()
        ctx = browser.new_context(viewport={"width": 390, "height": 844}, service_workers="block")
        page = ctx.new_page()
        page.on("pageerror", lambda x: errors.append(str(x)))
        page.on("dialog", lambda d: (errors.append("dialog: " + d.message), d.dismiss()))
        page.on("request", lambda r: outside.append(r.url) if not r.url.startswith(("http://localhost", "http://127.0.0.1", "data:", "blob:")) else None)

        print("\n--- 1. Segments, heading, switch ---")
        t.load(page, paints=PAINTS, units=UNITS, launch=True)
        check("the start circle's segments: Dashboard, Models, Painting, Tools",
              texts(page, ".arc [data-tab]") == ["Dashboard", "Models", "Painting", "Tools"], texts(page, ".arc [data-tab]"))   # George renamed the fourth label from Help to Tools
        page.click('.tabs button[data-tab="guides"]')
        settle(page)
        check("the bar's fourth segment says Tools, and its tap name is Tools",
              texts(page, ".arc [data-tab]")[3] == "Tools" and page.get_attribute('.arc [data-tab="guides"]', "aria-label") == "Tools")
        check("the page heading says Tools and Settings", page.inner_text("#more-title").strip() == "Tools and Settings" and page.is_visible("#more-title"))
        check("the switch is Guides, Settings, Help, Updates, with Guides selected first",
              texts(page, "#more-seg button") == ["Guides", "Settings", "Help", "Updates"]
              and page.evaluate("() => [...document.querySelectorAll('#more-seg button')].map(b => b.getAttribute('aria-selected')).join()") == "true,false,false,false")
        check("the cog is gone and the basket is still in the header",
              page.locator(".cog").count() == 0 and page.locator('[data-tab="settings"]').count() == 0 and page.locator(".app-actions #basket-button").count() == 1)
        check("no Compendium tab or view is left", page.locator('[data-tab="compendium"], #view-compendium').count() == 0 and "renderCompendium" not in app)
        for name in ["settings", "help", "updates", "guides"]:
            page.click(f'#more-seg button[data-page="{name}"]')
            settle(page)
            check(f"{name}: its page shows and the Tools segment is lit",
                  page.evaluate("(n) => settings.tab === n && !document.getElementById('view-' + n).classList.contains('hidden')", name) and lit(page) == ["guides"], lit(page))
        check("a page outside the section lights its own segment, not Tools", (page.click('.tabs button[data-tab="units"]'), settle(page), lit(page))[2] == ["units"])
        check("the heading and switch hide outside Tools and Settings", not page.is_visible("#more-title") and not page.is_visible("#more-seg"))

        print("\n--- 2. Guides ---")
        page.click('.tabs button[data-tab="guides"]')
        settle(page)
        check("Guides shows Detail recipes and Basing as categories", [x.rstrip("0123456789") for x in texts(page, ".guides-cats .guides-row")] == ["Detail recipes", "Basing"]   # X3: was fold-outs
              and page.locator("#cmp-wheel, #cmp-fold-mentor, #cmp-fold-ideas").count() == 0, texts(page, ".guides-cats .guides-row"))
        check("the Pro preview label shows in Guides", "Pro preview" in page.inner_text("#view-guides"))
        page.click('.guides-cats [data-cat="detail"]')   # X3: a category now, not a fold-out
        page.wait_for_selector(".guides-main .detail-recipes button")
        check("Detail recipes opens with its controls", page.locator(".guides-main .detail-recipes button").count() >= 1)
        page.click("#guides-back")
        page.click('.guides-cats [data-cat="basing"]')
        page.wait_for_selector(".guides-main .basing-tips button")
        check("Basing opens with its controls", page.locator(".guides-main .basing-tips button").count() >= 1)

        print("\n--- 3. Repointed link ---")
        t.load(page, paints=PAINTS, settings={"tab": "recipes", "recipeView": "palette", "examplesChecked": True})
        page.click('#paint-list .paint-head:has-text("Macragge Blue")')
        page.locator('#paint-list button.ideas-for[data-ideas-for="1"]').click()
        page.wait_for_selector("#cmp-focus button.ideas-open[data-detail]")
        btn = page.locator("#cmp-focus button.ideas-open[data-detail]").first
        key = btn.get_attribute("data-detail")
        btn.click()
        page.wait_for_selector(f'.guides-main [data-detail="{key}"]')
        settle(page)
        check("Show steps lands in Tools and Settings > Guides with that recipe open and in focus",
              page.evaluate("() => settings.tab") == "guides" and lit(page) == ["guides"] and page.get_attribute("#more-seg [data-page=guides]", "aria-selected") == "true"
              and page.evaluate("() => document.activeElement && document.activeElement.dataset.detail") == key)

        print("\n--- 4. Old saved state ---")
        for saved, want in [("compendium", "guides"), ("settings", "settings"), ("help", "help"), ("nonsense", "dashboard")]:
            t.load(page, paints=PAINTS, units=UNITS, settings={"tab": saved, "examplesChecked": True})
            check(f"a saved tab of {saved!r} opens {want} cleanly", page.evaluate("() => settings.tab") == want and not errors, page.evaluate("() => settings.tab"))
        for h, want in [("compendium", "guides"), ("guides", "guides"), ("settings", "settings"), ("nonsense", None)]:
            t.load(page, paints=PAINTS, units=UNITS, launch=True)
            page.goto(t.URL + "#" + h)
            page.reload()
            app_ready(page)
            check(f"the address #{h} " + (f"opens {want}" if want else "falls back to the start page"),
                  page.evaluate("() => settings.tab") == want if want else page.evaluate("() => document.body.classList.contains('launching')"))
        # a backup made before this change: settings still say the old tab; restoring it opens cleanly
        t.load(page, paints=PAINTS, units=UNITS)
        backup = {"app": "minifolio", "version": 1, "units": UNITS, "recipes": t.book(PAINTS, None), "settings": {"tab": "compendium"}}
        page.evaluate("(b) => { localStorage.setItem('shades-of-grey-settings', JSON.stringify(b.settings)); }", backup)
        page.reload()
        app_ready(page)
        leave_launch(page)
        check("an old saved tab from before opens Guides after a reload", page.evaluate("() => settings.tab") == "guides" and lit(page) == ["guides"])

        print("\n--- 5. Motion ---")
        t.load(page, paints=PAINTS, units=UNITS, launch=True)
        r = page.evaluate(TAP, '.tabs button[data-tab="guides"]')
        check("the start circle glides into the bar for Tools (the button moves, a picture of the circle is on top)", r["orb"] >= 1 and r["ghost"], r)
        settle(page)
        check("... and ends tidy with the segment lit", lit(page) == ["guides"] and page.evaluate("() => document.querySelectorAll('.mo-ring, .mo-ghost').length") == 0)
        r = page.evaluate(TAP, '.tabs button[data-tab="units"]')
        check("Tools to Models: the sections slide (the old one is a layer on top, earlier slides right)",
              r["layer"] and any(m.startswith("translateX(") for m in r["moving"]), r)
        settle(page)
        r = page.evaluate(TAP, '.tabs button[data-tab="guides"]')
        check("Models to Tools: the sections slide", r["layer"] and any(m.startswith("translateX(") for m in r["moving"]), r)
        settle(page)
        r = page.evaluate(TAP, '#more-seg button[data-page="settings"]')
        check("Guides to Settings (same section): an instant switch, nothing moves", not r["layer"] and r["moving"] == [], r)

        print("\n--- 6. Sizes and looks ---")
        for width in (390, 360, 320):   # 320 px added with the rename: the short label Tools must still fit
            for mode in ("dark", "light"):
                page.set_viewport_size({"width": width, "height": 844})
                t.load(page, paints=PAINTS, units=UNITS, settings={"mode": mode, "tab": "guides", "examplesChecked": True})
                tag = f"{width} px {mode}"
                small = page.evaluate("""() => [...document.querySelectorAll('#more-seg button, .arc [data-tab]')].map(b => {
                    const cs = getComputedStyle(b); const r = b.getBoundingClientRect(); return [b.textContent.trim(), Math.round(r.width), Math.round(r.height), cs.transform]; })""")
                check(f"{tag}: no sideways scroll", page.evaluate("() => document.documentElement.scrollWidth <= window.innerWidth + 1"))
                check(f"{tag}: the four switch buttons and the bar segments are 44 px or more by the real tap area",
                      all(h >= 44 for _, w, h, _ in small), small)
                check(f"{tag}: the four switch labels and the bar labels fit on one line each",
                      page.evaluate("() => [...document.querySelectorAll('#more-seg button, .arc [data-tab]')].every(b => b.scrollWidth <= b.clientWidth + 1 && (!b.closest('#more-seg') || b.getBoundingClientRect().height < 60))"))
        page.set_viewport_size({"width": 1280, "height": 900})
        t.load(page, paints=PAINTS, units=UNITS, settings={"tab": "guides", "examplesChecked": True})
        check("1280 px: Guides shows with no sideways scroll", page.is_visible("#view-guides") and page.evaluate("() => document.documentElement.scrollWidth <= window.innerWidth + 1"))

        print("\n--- 7. Safety and words ---")
        new_text = " ".join(texts(page, "#more-title, #more-seg button, .arc [data-tab]")) + page.get_attribute('.arc [data-tab="guides"]', "aria-label") + page.inner_text("#help-tabs")
        check("no faction or brand words in the new text", not FACTION_WORDS.search(new_text), FACTION_WORDS.findall(new_text))
        check("no em dashes in the new text", "—" not in new_text)
        check("Mentor is never 'the Mentor' in the Help menu text", "the Mentor" not in page.inner_text("#help-tabs"))
        check("no new network use", outside == [], outside)
        check("no page errors or pop-ups", errors == [], errors)
        browser.close()
    print(f"\n{sum(results)}/{len(results)} checks passed")
    return 0 if all(results) else 1

if __name__ == "__main__":
    sys.exit(main())
