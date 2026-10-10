"""v17.1 tests for Shades of Grey (paste import defaults to Owned, quantity stepper).
Serve the repo folder with `python3 -m http.server 8765`, then run: python3 tests/test_v17_1.py <folder for screenshots>."""
import os, sys
from playwright.sync_api import sync_playwright
import os as _os
PORT = _os.environ.get("SOG_PORT", "8765")

URL = f"http://localhost:{PORT}/index.html"
SHOTS = sys.argv[1] if len(sys.argv) > 1 else "."
KEEP_NOTE = open(os.path.join(os.path.dirname(__file__), "keep_note.txt")).read()
results = []
def check(name, ok, detail=""):
    results.append(bool(ok))
    print(("PASS " if ok else "FAIL ") + name + ("" if ok else f"  -> {detail}"))

ANSWERS = {"Bleck Templar": "Black Templar", "CM": "Contrast Medium", "Ice": "Basing material", "SS": "Screaming Skull",
           "Khorn red": "Khorne Red", "gothor brown": "Gorthor Brown", "white": "White Primer",
           "blangels red": "Blood Angels Red", "ultramarine blue": "Ultramarines Blue"}
V17_1_BOOK = {
    "v15": True, "parts": ["Whole model"], "techniques": ["Layer"],
    "paints": [{"id": 1, "brand": "Citadel", "name": "Nuln Oil", "colour": "#222222", "status": "owned", "owned": True}],
    "recipes": [], "schemes": [],
}

def load(page, book):
    page.goto(URL)
    page.evaluate("b => { localStorage.clear(); localStorage.setItem('shades-of-grey-recipes', JSON.stringify(b)); }", book)
    page.reload()
    page.wait_for_timeout(300)

with sync_playwright() as pw:
    browser = pw.chromium.launch()
    page = browser.new_page(viewport={"width": 390, "height": 844})
    errors = []
    page.on("pageerror", lambda e: errors.append(str(e)))

    page.goto(URL)
    check("version is v17.1 or later", float(page.evaluate("APP_VERSION")[1:]) >= 17.1)
    load(page, V17_1_BOOK)

    # Paste import: paints new to the palette default to Owned.
    page.evaluate("showTab('recipes')")
    page.click("#paste-recipes")
    page.fill("#import-text", KEEP_NOTE)
    page.click("text=Read notes")
    page.wait_for_timeout(200)
    for typed, answer in ANSWERS.items():
        row = page.locator(".import-ask", has=page.locator(".import-typed", has_text=f"“{typed}”"))
        row.locator("button.chip", has_text=answer).first.click()
    page.click("#import-save")
    page.wait_for_timeout(300)
    check("import: opens on Your Palette to check", page.evaluate("settings.recipeView") == "palette")
    check("import: review card shown", page.locator("#import-review").is_visible())
    new_count = page.evaluate("book.paints.filter(p => p.name !== 'Nuln Oil').length")
    check("import: every new paint is listed, expanded", page.locator("#paint-list .paint-item").count() == new_count and page.locator("#paint-list .status-row").count() == new_count, (page.locator("#paint-list .paint-item").count(), new_count))
    page.locator("#paint-list .paint-item", has_text="Ice").locator('.status-chip[data-status="empty"]').first.click()
    check("import: can change a status in the review", page.evaluate("paintStatus(book.paints.find(p => p.name === 'Ice'))") == "empty")
    statuses = page.evaluate("book.paints.filter(p => !['Nuln Oil', 'Ice'].includes(p.name)).map(p => paintStatus(p))")
    check("paste import: new paints all start Owned", statuses and all(s == "owned" for s in statuses), set(statuses))
    page.locator("#import-review button", has_text="Done").click()
    check("import: Done closes the review", page.locator("#import-review").is_hidden())
    check("paste import: existing paint keeps its own status", page.evaluate("paintStatus(book.paints.find(p => p.name === 'Nuln Oil'))") == "owned")
    page.screenshot(path=f"{SHOTS}/v17-1-import-owned.png", full_page=False)

    # Quantity: default one, tap + to mark duplicates, − to go back.
    load(page, V17_1_BOOK)
    page.evaluate("showTab('recipes')")
    page.click("#recipe-seg button[data-view='palette']")
    page.locator(".paint-item", has_text="Nuln Oil").locator("button.paint-head").click()
    item = page.locator(".paint-item", has_text="Nuln Oil")
    check("quantity shows one by default", item.locator(".qty-count").text_content() == "1")
    item.locator("button[aria-label='One more']").click()
    item = page.locator(".paint-item", has_text="Nuln Oil")
    check("tap + makes it two", item.locator(".qty-count").text_content() == "2")
    check("two saved on the paint", page.evaluate("book.paints.find(p => p.name === 'Nuln Oil').qty") == 2)
    check("palette shows × 2 in stock", "× 2 in stock" in page.locator(".paint-item", has_text="Nuln Oil").text_content())
    page.screenshot(path=f"{SHOTS}/v17-1-quantity.png", full_page=False)
    page.locator(".paint-item", has_text="Nuln Oil").locator("button[aria-label='One fewer']").click()
    page.locator(".paint-item", has_text="Nuln Oil").locator("button[aria-label='One fewer']").click()
    check("minus stops at one and clears the stored count", page.evaluate("'qty' in book.paints.find(p => p.name === 'Nuln Oil')") is False)
    page.locator(".paint-item", has_text="Nuln Oil").locator("button[aria-label='One more']").click()
    page.locator(".paint-item", has_text="Nuln Oil").locator('.status-chip[data-status="empty"]').click()
    check("quantity goes when you no longer have the paint", page.evaluate("'qty' in book.paints.find(p => p.name === 'Nuln Oil')") is False)

    # Saved data: a stored count survives a reload; nonsense counts are dropped.
    load(page, {**V17_1_BOOK, "paints": [{"id": 1, "brand": "Citadel", "name": "Nuln Oil", "colour": "#222222", "status": "owned", "qty": 3},
                                         {"id": 2, "brand": "Citadel", "name": "Abaddon Black", "colour": "#111111", "status": "empty", "qty": 4},
                                         {"id": 3, "brand": "Citadel", "name": "Leadbelcher", "colour": "#888888", "qty": "lots"}]})
    check("saved count of 3 kept", page.evaluate("book.paints.find(p => p.id === 1).qty") == 3)
    check("count dropped when paint is empty", page.evaluate("'qty' in book.paints.find(p => p.id === 2)") is False)
    check("non-number count dropped", page.evaluate("'qty' in book.paints.find(p => p.id === 3)") is False)

    check("no page errors", not errors, errors)
    page.close(); browser.close()

print()
print(f"{sum(results)} of {len(results)} checks passed")
sys.exit(0 if all(results) else 1)
