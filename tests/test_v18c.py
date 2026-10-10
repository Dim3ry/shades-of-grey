"""Test (v18c-1): the "CitadelCitadel" brand fix, and "Do you own these?".

1. Brand doubling (review section 1, item 3). Typing a known paint name filled in the Brand
   box for you, so tapping Brand and typing "Citadel" gave "CitadelCitadel". Now the filled-in
   text is selected when you go into the box, so typing replaces it. A brand typed twice is
   also put back to once whenever a paint is saved or the app loads, and a paint that then
   matches one you already have is joined to it (recipes use the one you had).

2. "Do you own these? All / None / Let me pick" (item 4). Paints new to your palette, from a
   paste import OR typed by hand in a recipe, get this choice. All is picked to start with
   (they're saved as Owned). None saves them as Not owned, so they go on the shopping list.
   Let me pick lets you untap the ones you don't have.

Serve the repo folder first (run_all.py does this for you), then run:
python3 tests/test_v18c.py
The port comes from the SOG_PORT environment variable, or 8765 if it isn't set."""
import json, os, sys
from playwright.sync_api import sync_playwright

PORT = os.environ.get("SOG_PORT", "8765")
BASE = f"http://localhost:{PORT}"
RECIPES_KEY = "shades-of-grey-recipes"

results = []
def check(name, ok, detail=""):
    results.append(bool(ok))
    print(("PASS " if ok else "FAIL ") + name + ("" if ok else f"  -> {detail}"))

def paint(pid, name, brand="Citadel", **extra):
    return {"id": pid, "brand": brand, "name": name, "colour": "#3b5b7a", **extra}

def start(page, book=None):
    """A fresh app: no units, and this recipe book (or an empty one)."""
    page.goto(f"{BASE}/manifest.json")
    page.evaluate("""book => { localStorage.clear(); localStorage.setItem('mini-tracker-models', '[]');
                     if (book) localStorage.setItem('shades-of-grey-recipes', JSON.stringify(book)); }""", book)
    page.goto(f"{BASE}/index.html")
    page.wait_for_timeout(300)

def saved_book(page):
    return json.loads(page.evaluate(f"localStorage.getItem('{RECIPES_KEY}') || '{{}}'"))

def statuses(page):
    """Paint name -> status, from the saved recipe book."""
    return {p["name"]: p.get("status", "") for p in saved_book(page).get("paints", [])}

def paste(page, text):
    page.evaluate("startImport()")
    page.fill("#import-text", text)
    page.click("#import-page button.primary-button")   # "Read notes"
    page.wait_for_timeout(100)

def pressed(page, selector):
    loc = page.locator(selector)
    return loc.count() == 1 and loc.get_attribute("aria-pressed") == "true"

NOTE = "Test scheme\n\nCloak:\nMephiston Red\nAgrax Earthshade"

def main():
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(viewport={"width": 390, "height": 844})
        errors = []
        page.on("pageerror", lambda e: errors.append(str(e)))

        # ---------- 1. Brand doubling ----------
        start(page)
        cases = {"CitadelCitadel": "Citadel", "Citadel Citadel": "Citadel", "CitadelCitadelCitadel": "Citadel",
                 "Army PainterArmy Painter": "Army Painter", "citadelCitadel": "citadel",
                 "Vallejo": "Vallejo", "Pro Acryl": "Pro Acryl", "AK": "AK", "AKAK": "AKAK", "": ""}
        got = page.evaluate("cases => Object.fromEntries(Object.keys(cases).map(k => [k, tidyBrand(k)]))", cases)
        bad = {k: v for k, v in got.items() if v != cases[k]}
        check("tidyBrand: a brand typed twice goes back to once, others are left alone", not bad, bad)

        # Saved doubles are tidied when the app loads, and joined to the paint you already had.
        book = {"paints": [paint(1, "Macragge Blue"),
                           paint(2, "Macragge Blue", brand="CitadelCitadel", status="owned", owned=True),
                           paint(3, "Mephiston Red", brand="CitadelCitadel", status="wishlist")],
                "recipes": [{"id": 1, "name": "Armour", "part": "Armour", "notes": "", "steps": [
                    {"technique": "Base coat", "coats": 1, "paints": [{"paint": 2, "mix": 100}]},
                    {"technique": "Layer", "coats": 1, "paints": [{"paint": 3, "mix": 100}]}]}],
                "schemes": [], "v15": True,
                "shorthand": {"mb": {"brand": "CitadelCitadel", "name": "Macragge Blue"}}}
        start(page, book)
        mem = page.evaluate("book")
        brands = sorted({p["brand"] for p in mem["paints"]})
        check("saved doubles: no 'CitadelCitadel' brand left after loading", brands == ["Citadel"], brands)
        blues = [p for p in mem["paints"] if p["name"] == "Macragge Blue"]
        check("saved doubles: the two Macragge Blues become one paint", len(blues) == 1 and blues[0]["id"] == 1,
              [(b["id"], b["brand"]) for b in blues])
        check("saved doubles: the joined paint keeps the Owned status", blues and blues[0].get("status") == "owned",
              blues)
        step_ids = [sp["paint"] for s in mem["recipes"][0]["steps"] for sp in s["paints"]]
        check("saved doubles: the recipe now uses the paint you already had", step_ids == [1, 3], step_ids)
        red = next((p for p in mem["paints"] if p["name"] == "Mephiston Red"), {})
        check("saved doubles: a double with no twin just gets its brand tidied",
              red.get("brand") == "Citadel" and red.get("status") == "wishlist", red)
        check("saved doubles: remembered shorthand is tidied too", mem["shorthand"]["mb"]["brand"] == "Citadel",
              mem["shorthand"])
        shop_brands = page.evaluate("[...new Set(shoppingItems().map(i => i.paint.brand))]")
        check("saved doubles: the shopping list has no 'CitadelCitadel' group", "CitadelCitadel" not in shop_brands,
              shop_brands)

        # Saving a paint with a doubled brand (by any route) stores it once.
        added = page.evaluate("findOrAddPaint('CitadelCitadel', 'Retributor Armour', '#000000').brand")
        check("findOrAddPaint stores 'CitadelCitadel' as 'Citadel'", added == "Citadel", added)
        edited = page.evaluate("""() => { const p = book.paints.find(x => x.name === 'Mephiston Red');
                                  editPaint(p, 'brand', 'Citadel Citadel'); return p.brand; }""")
        check("Your Palette: editing a brand to 'Citadel Citadel' saves 'Citadel'", edited == "Citadel", edited)

        # The real bug: type a known paint, go to Brand (with Tab or a tap), type "Citadel".
        for how in ["Tab", "tap"]:
            start(page)
            page.evaluate("startNewRecipe(null)")
            page.fill("#recipe-page input.paint-name", "Macragge Blue")
            if how == "Tab":
                page.keyboard.press("Tab")
            else:
                page.click("#recipe-page input.paint-brand")
            page.wait_for_timeout(50)
            filled = page.input_value("#recipe-page input.paint-brand")
            page.keyboard.type("Citadel")
            typed = page.input_value("#recipe-page input.paint-brand")
            check(f"recipe editor ({how}): the brand fills itself in", filled == "Citadel", filled)
            check(f"recipe editor ({how}): typing 'Citadel' over it gives 'Citadel', not 'CitadelCitadel'",
                  typed == "Citadel", typed)

        # Even if a double gets typed by hand, leaving the box and saving tidies it.
        start(page)
        page.evaluate("startNewRecipe(null)")
        page.fill("#recipe-page input", "Brand test")   # the recipe name box comes first
        page.fill("#recipe-page input.paint-name", "Kantor Blue")
        page.fill("#recipe-page input.paint-brand", "CitadelCitadel")
        page.locator("#recipe-page input.paint-brand").blur()
        check("recipe editor: leaving the Brand box tidies 'CitadelCitadel'",
              page.input_value("#recipe-page input.paint-brand") == "Citadel",
              page.input_value("#recipe-page input.paint-brand"))
        page.click("#recipe-page button.primary-button:has-text('Save recipe')")
        page.wait_for_timeout(150)
        kantor = [p for p in saved_book(page).get("paints", []) if p["name"] == "Kantor Blue"]
        check("recipe editor: the saved paint's brand is 'Citadel'", [p["brand"] for p in kantor] == ["Citadel"], kantor)

        # ---------- 2. "Do you own these?" in the paste import ----------
        start(page)
        paste(page, NOTE)
        own = page.locator("#import-own")
        check("paste: the 'Do you own these?' card shows for new paints",
              own.count() == 1 and own.is_visible() and "Do you own these?" in own.inner_text(),
              own.inner_text() if own.count() else "no card")
        check("paste: All is picked to start with", pressed(page, "#import-own [data-own=all]")
              and not pressed(page, "#import-own [data-own=none]") and not pressed(page, "#import-own [data-own=pick]"))
        check("paste: it counts the 2 new paints", "2 paints will be new" in own.inner_text(), own.inner_text())
        page.click("#import-save")
        page.wait_for_timeout(150)
        st = statuses(page)
        check("paste, All: both new paints are saved as Owned",
              st.get("Mephiston Red") == "owned" and st.get("Agrax Earthshade") == "owned", st)

        start(page)
        paste(page, NOTE)
        page.click("#import-own [data-own=none]")
        check("paste: tapping None picks None", pressed(page, "#import-own [data-own=none]")
              and not pressed(page, "#import-own [data-own=all]"))
        page.click("#import-save")
        page.wait_for_timeout(150)
        st = statuses(page)
        check("paste, None: both new paints are saved as Not owned",
              st.get("Mephiston Red") == "notowned" and st.get("Agrax Earthshade") == "notowned", st)
        shop = page.evaluate("shoppingItems().map(i => i.paint.name).sort()")
        check("paste, None: both paints are on the shopping list", shop == ["Agrax Earthshade", "Mephiston Red"], shop)

        start(page)
        paste(page, NOTE)
        page.click("#import-own [data-own=pick]")
        chips = page.locator("#import-own .own-paint")
        check("paste, Let me pick: one chip per new paint, all ticked to start",
              chips.count() == 2 and all(chips.nth(i).get_attribute("aria-pressed") == "true" for i in range(2)),
              chips.count())
        page.click("#import-own .own-paint:has-text('Mephiston Red')")
        check("paste, Let me pick: tapping a paint unticks it",
              page.locator("#import-own .own-paint:has-text('Mephiston Red')").get_attribute("aria-pressed") == "false")
        page.click("#import-save")
        page.wait_for_timeout(150)
        st = statuses(page)
        check("paste, Let me pick: the untapped paint is Not owned, the other Owned",
              st.get("Mephiston Red") == "notowned" and st.get("Agrax Earthshade") == "owned", st)

        # Paints already in your palette aren't asked about, and keep their status.
        start(page, {"paints": [paint(1, "Mephiston Red", status="wishlist")], "recipes": [], "schemes": [], "v15": True})
        paste(page, NOTE)
        text = page.locator("#import-own").inner_text()
        check("paste: a paint you already have isn't listed", "1 paint will be new" in text, text)
        page.click("#import-own [data-own=none]")
        page.click("#import-save")
        page.wait_for_timeout(150)
        st = statuses(page)
        check("paste: a paint you already have keeps its own status",
              st.get("Mephiston Red") == "wishlist" and st.get("Agrax Earthshade") == "notowned", st)

        # Nothing new: no card.
        paste(page, NOTE)
        check("paste: no new paints, no card", not page.locator("#import-own").is_visible())

        # A paint name is shown as plain text, never as HTML.
        start(page)
        paste(page, "Test scheme\n\nCloak:\nMephiston Red\n<img src=x onerror=window.hacked=1>")
        if page.locator("#import-own").is_visible():
            page.click("#import-own [data-own=pick]")   # show the per-paint chips too
        check("paste: paint names in the card are plain text, not HTML",
              page.locator("#import-own img").count() == 0 and not page.evaluate("window.hacked === 1"))

        # ---------- 3. "Do you own these?" for paints added by hand ----------
        start(page)
        page.evaluate("startNewRecipe(null)")
        check("recipe editor: no card before any paint is typed", not page.locator("#recipe-own").is_visible())
        page.fill("#recipe-page input", "Hand test")
        page.fill("#recipe-page input.paint-name", "Mephiston Red")
        own = page.locator("#recipe-own")
        check("recipe editor: the card appears as you type a new paint",
              own.is_visible() and "1 paint will be new" in own.inner_text(),
              own.inner_text() if own.count() else "no card")
        check("recipe editor: typing keeps your place in the paint box",
              page.evaluate("document.activeElement && document.activeElement.classList.contains('paint-name')"))
        check("recipe editor: All is picked to start with", pressed(page, "#recipe-own [data-own=all]"))
        page.click("#recipe-page button.primary-button:has-text('Save recipe')")
        page.wait_for_timeout(150)
        st = statuses(page)
        check("recipe editor, All: the new paint is saved as Owned", st.get("Mephiston Red") == "owned", st)

        start(page)
        page.evaluate("""startRecipeDraft({ id: null, name: 'Pick test', part: '', notes: '', linkUnit: null, steps: [
            { technique: '', coats: 1, ratio: '', note: '', optional: false, paints: [
              { brand: '', name: 'Mephiston Red', colour: '#808080', mix: 50 },
              { brand: '', name: 'Kantor Blue', colour: '#808080', mix: 50 } ] }] }); showTab('recipes');""")
        page.click("#recipe-own [data-own=pick]")
        labels = page.locator("#recipe-own .own-paint").all_inner_texts()
        check("recipe editor, Let me pick: both new paints listed, with the brand filled in",
              any("Citadel Mephiston Red" in t for t in labels) and any("Citadel Kantor Blue" in t for t in labels), labels)
        page.click("#recipe-own .own-paint:has-text('Kantor Blue')")
        page.click("#recipe-page button.primary-button:has-text('Save recipe')")
        page.wait_for_timeout(150)
        st = statuses(page)
        check("recipe editor, Let me pick: the untapped paint is Not owned, the other Owned",
              st.get("Mephiston Red") == "owned" and st.get("Kantor Blue") == "notowned", st)

        start(page)
        page.evaluate("startNewRecipe(null)")
        page.fill("#recipe-page input", "None test")
        page.fill("#recipe-page input.paint-name", "Kantor Blue")
        page.click("#recipe-own [data-own=none]")
        page.click("#recipe-page button.primary-button:has-text('Save recipe')")
        page.wait_for_timeout(150)
        st = statuses(page)
        check("recipe editor, None: the new paint is saved as Not owned", st.get("Kantor Blue") == "notowned", st)

        check("no page errors", not errors, errors)
        browser.close()

    print(f"\n{sum(results)} of {len(results)} checks passed")
    sys.exit(0 if all(results) else 1)

if __name__ == "__main__":
    main()
