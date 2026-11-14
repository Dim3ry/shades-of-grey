"""FX1 test for Minifolio (Shopping is easy to find; the Models "Wish list" option is now "Wanted"). New behaviour only:
the basket on every Painting page even when empty, no number then, the Models | Wanted wording."""
import os, sys
from playwright.sync_api import sync_playwright

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import test_v31 as t
from launch_helpers import quiet

results = []

def check(name, ok, detail=""):
    results.append(bool(ok))
    print(("PASS " if ok else "FAIL ") + name + ("" if ok else f"  -> {str(detail)[:400]}"))

OWNED = {"id": 1, "brand": "Test Paints", "name": "Owned One", "colour": "#3366aa", "status": "owned"}   # nothing on the shopping list
STAGES = ["Boxed", "Built", "Primed", "Painted"]
def wish(i, name, count=1, faction="Moss Court"):
    return {"id": i, "name": name, "count": count, "game": "Fantasy", "faction": faction, "really": False, "note": "", "added": "2026-10-01"}
WISHES = [wish(1, "Moss Knights", 4), wish(2, "Archers", 2), wish(3, "Single")]

BASKET = """() => { const b = document.getElementById('basket-button'), r = b.getBoundingClientRect(), a = getComputedStyle(b, '::after');
  const h1 = document.querySelector('.app-bar h1').getBoundingClientRect();
  return { shown: !b.classList.contains('hidden') && r.width > 0, kids: [...b.children].map(c => c.tagName).join(), label: b.getAttribute('aria-label'),
    tapH: r.height + 2 * Math.abs(parseFloat(a.top)), tapW: r.width + 2 * Math.abs(parseFloat(a.left)),
    inside: r.left >= 0 && r.right <= window.innerWidth, clear: r.left >= h1.left, scrollX: document.documentElement.scrollWidth > document.documentElement.clientWidth }; }"""

def basket(page): return page.evaluate(BASKET)

def main():
    errors = []
    with sync_playwright() as p:
        browser = p.chromium.launch()
        for w, h in ((390, 844), (360, 640), (320, 568)):
            for mode in ("dark", "light"):
                ctx = browser.new_context(viewport={"width": w, "height": h}, service_workers="block", color_scheme=mode)
                page = ctx.new_page()
                page.on("pageerror", lambda x: errors.append(str(x)))
                t.load(page, paints=[OWNED], units=[], settings={"examplesChecked": True, "stages": STAGES, "appearance": mode})
                tag = f"{w}px {mode}"
                page.click('nav button[data-tab="recipes"]'); quiet(page)
                d = basket(page)
                check(f"{tag}: the basket shows on Painting with an empty list, a picture and no number",
                      d["shown"] and d["kids"] == "svg" and d["label"] == "Shopping list, empty. Tap to open it.", d)
                check(f"{tag}: it is a 44 px tap area, inside the screen, not over the title, no sideways scroll",
                      d["tapH"] >= 44 and d["inside"] and d["clear"] and not d["scrollX"], d)
                if (w, mode) == (390, "dark"):
                    for view in ("recipes", "palette", "schemes", "shopping", "colourlab"):
                        page.click(f'#recipe-seg button[data-view="{view}"]'); page.wait_for_timeout(300)
                        check(f"the basket shows on the Painting {view} page when empty", basket(page)["shown"] and basket(page)["kids"] == "svg", basket(page))
                    page.click('#basket-button'); page.wait_for_timeout(300)
                    check("tapping the empty basket opens Shopping", page.is_visible("#shop-panel"))
                    for tab in ("units", "dashboard"):
                        page.click(f'nav button[data-tab="{tab}"]'); quiet(page)
                        check(f"the basket is not on {tab} while the list is empty", not basket(page)["shown"], basket(page))
                    page.click('nav button[data-tab="recipes"]'); quiet(page)
                    check("coming back to Painting shows it again", basket(page)["shown"])
                    page.evaluate("() => { addToShoppingList({ brand: 'B', name: 'New Paint' }, 'Recipe: Test'); }")
                    d = basket(page)
                    check("with one item it shows the number 1", d["shown"] and d["kids"] == "svg,SPAN" and page.inner_text("#basket-button").strip() == "1", d)
                    page.click('nav button[data-tab="units"]'); quiet(page)
                    check("with an item the basket also shows on Models", basket(page)["shown"])
                ctx.close()

        print("\n--- Models | Wanted ---")
        ctx = browser.new_context(viewport={"width": 390, "height": 844}, service_workers="block")
        page = ctx.new_page()
        page.on("pageerror", lambda x: errors.append(str(x)))
        t.load(page, units=[], settings={"examplesChecked": True, "stages": STAGES, "modelWishes": WISHES})
        page.click('nav button[data-tab="units"]'); quiet(page)
        labels = page.evaluate("[...document.querySelectorAll('#models-seg button')].map(b => b.textContent.trim())")
        check("the Models switch reads Models | Wanted", labels == ["Models", "Wanted"], labels)
        check("Models is still the first control on the page", page.evaluate("document.querySelector('#view-units button, #view-units [tabindex]').dataset.mview") == "models")
        page.click('#models-seg button[data-mview="wishes"]'); page.wait_for_selector("#wish-view:not(.hidden)")
        check("the add button says Add model and is 44 px tall", page.inner_text("#wish-add").strip() == "+ Add model" and page.locator("#wish-add").bounding_box()["height"] >= 44)
        check("the count line says 7 wanted models", page.inner_text("#wish-count").strip() == "7 wanted models", page.inner_text("#wish-count"))
        page.click("#wish-add")
        check("the form is named Add model", page.get_attribute(".wish-form", "aria-label") == "Add model")
        page.click(".w-cancel")
        page.click(".wish-info")
        check("an existing one is named Edit model", page.get_attribute(".wish-form", "aria-label") == "Edit model")
        page.click(".w-cancel")
        txt = page.inner_text("#view-units")
        check("no 'wish' wording is shown on the Wanted view", "wish" not in txt.lower(), txt[:300])
        page.click('#models-seg button[data-mview="models"]')
        help_text = page.evaluate("document.getElementById('help-wish-list').textContent + '|' + document.getElementById('help-tabs').textContent")
        check("Help names Wanted and the basket on Painting", "Wanted" in help_text and "Wish list" not in help_text and "always at the top right on Painting" in help_text, help_text)
        ctx.close()
        browser.close()
    check("no page errors", not errors, errors)
    print(f"\n{sum(results)}/{len(results)} passed")
    sys.exit(0 if all(results) else 1)

if __name__ == "__main__":
    main()
