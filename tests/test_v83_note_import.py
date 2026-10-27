"""v83 (chunk U2): pasted recipe notes can have sections.

New behaviour only:
1. Notes like the screenshot (Heraldry, Lenses, Guns, Cloth... with paints under each) are guessed as section headings,
   not as paints to identify. A plain list with no headings reads as before.
2. The preview shows the heading as a "Section" line, "Check N paints" does not ask about it, and the guess can be changed
   with "This line is" in the pencil editor (Paint step / Section heading / Ignore). Undo puts the choice back.
3. Saving makes one recipe per section, named after the heading; ignored lines and heading words are never saved as paints.
4. Heading text is shown as plain text (no markup runs).
5. 390 px and 360 px, dark and light, and 1280 px: no sideways scroll; the new controls are 44 px or more."""
import os, sys
from playwright.sync_api import sync_playwright

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import test_v31 as t

load, no_sideways = t.load, t.no_sideways
results = []

def check(name, ok, detail=""):
    results.append(bool(ok))
    print(("PASS " if ok else "FAIL ") + name + ("" if ok else f"  -> {detail}"))

# Real paints and headings from the screenshot notes (headings have no colon).
NOTES = """Tin Knights

Armour:
Mephiston Red

Heraldry
Warplock Bronze
Agrax Earthshade
Runefang Steel

Lenses
Evil Sunz Scarlet
Seraphim Sepia

Guns
Iron Hands Steel
Agrax Earthshade

Glass
Runefang Steel
Terradon Turquoise"""
PLAIN = "Cloak:\nMephiston Red\nAgrax Earthshade\nAbaddon Black"
INJECT = "Cloak:\nMephiston Red\n\n<img src=x onerror=window.__pwned=1>\nWarplock Bronze\nAgrax Earthshade"

READ = "{ const p = parseRecipeText(%s); return p.schemes.flatMap(s => s.parts.map(x => ({ part: x.name, steps: x.steps.map(st => ({ role: stepRole(st), src: st.source, status: st.paints.map(m => m.status) })) }))); }"

def read(page, text):
    return page.evaluate("t => " + READ % "t", text)

def open_preview(page, text):
    page.evaluate("startImport()")
    page.fill("#import-text", text)
    page.click("#import-page button.primary-button")
    page.wait_for_timeout(150)

def main():
    errors, dialogs = [], []
    with sync_playwright() as p:
        browser = p.chromium.launch()
        ctx = browser.new_context(viewport={"width": 390, "height": 844}, service_workers="block")
        page = ctx.new_page()
        page.on("pageerror", lambda x: errors.append(str(x)))
        page.on("dialog", lambda d: (dialogs.append(d.message), d.dismiss()))
        load(page, units=[])

        print("\n--- 1. The guess ---")
        parts = read(page, NOTES)
        steps = [s for part in parts for s in part["steps"]]
        heads = [s["src"] for s in steps if s["role"] == "heading"]
        check("Heraldry, Lenses, Guns and Glass are guessed as section headings", heads == ["Heraldry", "Lenses", "Guns", "Glass"], heads)
        check("real paints stay paint steps", all(s["role"] == "paint" for s in steps if s["src"] in ("Warplock Bronze", "Agrax Earthshade", "Runefang Steel")))
        plain = read(page, PLAIN)
        check("a plain list with no headings has no section headings",
              len(plain) == 1 and len(plain[0]["steps"]) == 3 and all(s["role"] == "paint" for s in plain[0]["steps"]), plain)
        lone = read(page, "Cloak:\nMephiston Red\nBloodied Fur\nAbaddon Black")
        check("a new paint with only one matched line after it is not guessed as a heading",
              all(s["role"] == "paint" for s in lone[0]["steps"]), lone)

        print("\n--- 2. The preview ---")
        open_preview(page, NOTES)
        check("the headings show as Section lines", page.locator("#import-page .import-heading").count() == 4)
        check("Check N paints does not ask about the headings", page.locator("#import-page .import-check").count() == 0)
        check("Save is ready and says how many recipes it will make", "Save 5 recipes" in page.inner_text("#import-save"), page.inner_text("#import-save"))
        first = page.locator("#import-page .import-heading .import-edit").first
        first.click()
        chip = lambda label: page.locator("#import-page .import-step-editor .import-role-chip", has_text=label)
        check("the editor says what the line is", chip("Section heading").get_attribute("aria-pressed") == "true")
        chip("Paint step").click()
        page.wait_for_timeout(120)
        check("changing Heraldry to a paint step makes it a numbered step again (a new paint)",
              page.locator("#import-page .import-heading").count() == 3 and "Heraldry (new)" in page.inner_text("#import-page"))
        page.locator("#toast button, .toast button").first.click()
        page.wait_for_timeout(120)
        check("Undo puts the heading back", page.locator("#import-page .import-heading").count() == 4)
        page.locator("#import-page .import-heading .import-edit").nth(1).click()
        chip("Ignore").click()
        page.wait_for_timeout(120)
        check("Ignore shows the line as Ignored and Save count drops", page.locator("#import-page .import-ignore").count() == 1
              and "Save 4 recipes" in page.inner_text("#import-save"), page.inner_text("#import-save"))

        print("\n--- 3. Saving ---")
        page.click("#import-save")
        page.wait_for_timeout(300)
        names = page.evaluate("() => book.recipes.map(r => r.name)")
        check("one recipe per section, named after its heading", any(n.endswith("Heraldry") for n in names) and any(n.endswith("Guns") for n in names)
              and any(n.endswith("Glass") for n in names), names)
        check("the ignored heading is not a recipe", not any(n.endswith("Lenses") for n in names), names)
        paints = page.evaluate("() => book.paints.map(p => p.name)")
        check("heading words are not saved as paints", not any(n in ("Heraldry", "Guns", "Glass", "Lenses") for n in paints), paints)
        heraldry = page.evaluate("() => book.recipes.find(r => r.name.endsWith('Heraldry')).steps.length")
        check("Ignore drops only the line: Lenses' paints fall under Heraldry above it", heraldry == 5, heraldry)

        print("\n--- 4. Plain text only ---")
        load(page, units=[])
        open_preview(page, INJECT)
        check("pasted markup is shown as text, nothing runs", page.evaluate("() => window.__pwned") is None and page.locator("#import-page img").count() == 0)

        print("\n--- 5. Layout ---")
        load(page, units=[])
        open_preview(page, NOTES)
        for width, scheme in ((390, "dark"), (390, "light"), (360, "dark"), (360, "light"), (1280, "dark")):
            page.set_viewport_size({"width": width, "height": 844})
            page.emulate_media(color_scheme=scheme)
            page.wait_for_timeout(100)
            sizes = page.eval_on_selector_all("#import-page .import-heading .import-edit, #import-page .import-heading .import-remove",
                                               "els => els.map(e => { const r = e.getBoundingClientRect(); return Math.min(r.width, r.height); })")
            check(f"{width} px {scheme}: heading buttons 44 px or more, no sideways scroll", len(sizes) >= 8 and min(sizes) >= 44 and no_sideways(page), sizes)
        page.set_viewport_size({"width": 390, "height": 844})
        page.locator("#import-page .import-heading .import-edit").first.click()
        for width in (390, 360):
            page.set_viewport_size({"width": width, "height": 844})
            h = page.eval_on_selector_all("#import-page .import-role-chip", "els => els.map(e => e.getBoundingClientRect().height)")
            check(f"{width} px: the This line is buttons are 44 px or more, no sideways scroll", len(h) == 3 and min(h) >= 44 and no_sideways(page), h)

        check("no page errors, no browser pop-ups", not errors and not dialogs, (errors, dialogs))
        browser.close()
    print(f"\n{sum(results)} of {len(results)} checks passed")
    return 0 if all(results) else 1

if __name__ == "__main__":
    sys.exit(main())
