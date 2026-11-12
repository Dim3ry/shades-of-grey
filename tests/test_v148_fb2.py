"""FB2 tests for Minifolio (small fixes). New behaviour only:
the Dashboard doughnut centre reads "Done"; adding a unit shows a message with an Undo button that lasts UNDO_SECONDS;
Undo removes only that unit (and its photos), keeps other units and the Dashboard numbers as they were, undoes same-name copy numbers,
a second add replaces the first message, Undo removes a whole many-model unit, and the message sits above the bottom menu at three phone sizes."""
import os, sys
from playwright.sync_api import sync_playwright

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import test_v31 as t

results = []

def check(name, ok, detail=""):
    results.append(bool(ok))
    print(("PASS " if ok else "FAIL ") + name + ("" if ok else f"  -> {detail}"))

UNITS = [{"id": 1, "name": "Intercessors", "count": 5, "stage": 0, "hobby": "40k", "faction": "Marines", "added": "2026-01-01", "log": [["2026-01-01", 0]]},
         {"id": 2, "name": "Hellblasters", "count": 3, "stage": 3, "hobby": "40k", "faction": "Marines", "added": "2026-01-01", "log": [["2026-01-01", 3]]}]

TOAST = """() => { const x = document.getElementById('toast'), u = document.getElementById('toast-undo'), r = x.getBoundingClientRect(), tabs = document.querySelector('.tabs').getBoundingClientRect(), ur = u.getBoundingClientRect();
  return { shown: !x.classList.contains('hidden'), text: document.getElementById('toast-text').textContent, undo: !u.classList.contains('hidden'), label: u.textContent,
           life: x.style.getPropertyValue('--toast-life'), bottom: r.bottom, tabsTop: tabs.top, undoH: ur.height, undoW: ur.width,
           sideways: document.documentElement.scrollWidth > document.documentElement.clientWidth }; }"""
STATE = """() => ({ names: models.map(m => m.name + ':' + m.count + ':' + (m.copy || '')), done: document.querySelector('#overall-chart svg text').textContent,   // DB1: the ring's percentage (the big stand-alone one is gone)
                  summary: document.getElementById('done-button').textContent })   // DB1: the models-done tile"""

def add(page, name, count=1, game="40k", faction="Marines"):
    if page.locator("#add-form.hidden").count(): page.click("#toggle-add")
    page.fill("#name-input", name)
    page.fill("#count-input", str(count))
    page.fill("#hobby-input", game)
    page.fill("#faction-input", faction)
    page.press("#name-input", "Enter")
    page.wait_for_function("(n) => document.getElementById('toast-text').textContent.startsWith('Added') && document.getElementById('toast-text').textContent.includes(n)", arg=name)

SETTLE = """async () => { document.activeElement && document.activeElement.blur();
  const x = document.getElementById('toast');
  for (let i = 0; i < 120; i++) { await new Promise(r => requestAnimationFrame(r)); const tb = document.querySelector('.tabs').getBoundingClientRect();
    if (x.getAnimations().every(a => a.playState === 'finished') && tb.height > 0) return; } }"""

def main():
    errors = []
    with sync_playwright() as p:
        browser = p.chromium.launch()
        ctx = browser.new_context(viewport={"width": 390, "height": 844}, service_workers="block", color_scheme="dark")
        page = ctx.new_page()
        page.on("pageerror", lambda x: errors.append(str(x)))
        t.load(page, units=UNITS)

        print("\n--- 1. Done with a capital ---")
        page.evaluate("() => showTab('dashboard')")
        page.wait_for_selector("#overall-chart svg text")
        texts = page.evaluate("() => [...document.querySelectorAll('#overall-chart svg text')].map(x => x.textContent)")
        check("doughnut centre reads the percentage and 'Done'", len(texts) == 2 and texts[1] == "Done" and texts[0].endswith("%"), texts)

        print("\n--- 2. The add message ---")
        before = page.evaluate(STATE)
        page.evaluate("() => showTab('units')")
        life = page.evaluate("() => UNDO_SECONDS")
        add(page, "Zzz Termagants", 4)
        page.evaluate(SETTLE)
        m = page.evaluate(TOAST)
        check("message says Added and has an Undo button", m["shown"] and m["text"] == "Added Zzz Termagants" and m["undo"] and m["label"] == "Undo", m)
        check("it lasts UNDO_SECONDS (the shared constant)", m["life"] == f"{life}s" and life == 10, m)
        check("it sits above the bottom menu, Undo button 44 px or more", m["bottom"] <= m["tabsTop"] + 0.5 and m["undoH"] >= 44, m)
        page.evaluate("() => { const z = models.find(x => x.name === 'Zzz Termagants'); z.photos = [{ id: 'fb2-photo', date: '2026-02-01' }]; }")
        page.evaluate("async () => { await putPhoto({ id: 'fb2-photo', blob: new Blob(['x']) }); }")

        print("\n--- 3. Undo ---")
        page.evaluate("() => { models.find(x => x.name === 'Zzz Termagants').stage = 2; }")   # changed in the meantime
        page.click("#toast-undo")
        page.wait_for_function("() => !models.some(m => m.name === 'Zzz Termagants')")
        after = page.evaluate(STATE)
        check("Undo removes the unit even though it changed, and the list is as before", after["names"] == before["names"], after)
        page.wait_for_function("async () => !(await getPhoto('fb2-photo'))")
        check("its photo file is removed too", True)
        page.evaluate("() => showTab('dashboard')")
        check("the Dashboard numbers are back to the old values", page.evaluate(STATE) == before, page.evaluate(STATE))
        check("Undo makes no safety copy and saves the shorter list",
              page.evaluate("() => JSON.parse(localStorage.getItem('mini-tracker-models')).length") == 2
              and not page.evaluate("() => Object.keys(localStorage).some(k => /safety|backup-copy/i.test(k))"))

        print("\n--- 4. Several adds, copies, many models ---")
        page.evaluate("() => showTab('units')")
        add(page, "Intercessors", 10)   # same name, game and faction as the first unit: gets copy numbers
        copies = page.evaluate("() => models.map(m => m.name + ':' + (m.copy || ''))")
        check("a same-name add numbers the copies", "Intercessors:1" in copies and "Intercessors:2" in copies, copies)
        add(page, "Zzz Second")
        check("a newer add replaces the older message", page.evaluate(TOAST)["text"] == "Added Zzz Second")
        page.click("#toast-undo")
        page.wait_for_function("() => !models.some(m => m.name === 'Zzz Second')")
        check("Undo takes off only the newest unit (the 10-model one stays)", page.evaluate("() => models.some(m => m.name === 'Intercessors' && m.count === 10)"))
        page.evaluate("() => showTab('units')")
        add(page, "Zzz Big", 12)
        page.click("#toast-undo")
        page.wait_for_function("() => !models.some(m => m.name === 'Zzz Big')")
        check("a 12-model unit goes as one unit", page.evaluate("() => models.filter(m => m.name === 'Zzz Big').length") == 0)
        first_id = page.evaluate("() => models.find(m => m.name === 'Intercessors' && m.count === 10).id")
        page.evaluate("(id) => { const m = models.find(x => x.id === id); models = models.filter(x => x !== m); render(); }", first_id)
        add(page, "Intercessors", 2)
        page.click("#toast-undo")
        page.wait_for_function("() => !models.some(m => m.count === 2 && m.name === 'Intercessors')")
        check("same-name copy numbers go back when the add is undone",
              page.evaluate("() => models.filter(m => m.name === 'Intercessors').every(m => m.copy === undefined || m.copy === 1)"))

        print("\n--- 5. Layout: three phone sizes, dark and light, Classic and another look ---")
        for (w, h) in [(390, 844), (360, 640), (320, 568)]:
            for scheme, theme in [("dark", "classic"), ("light", "parchment")]:
                c = browser.new_context(viewport={"width": w, "height": h}, service_workers="block", color_scheme=scheme)
                pg = c.new_page()
                pg.on("pageerror", lambda x: errors.append(str(x)))
                t.load(pg, units=UNITS, settings={"theme": theme, "appearance": scheme})
                pg.evaluate("() => showTab('units')")
                add(pg, "Zzz Layout")
                pg.evaluate(SETTLE)
                g = pg.evaluate(TOAST)
                ok = g["shown"] and g["undo"] and g["bottom"] <= g["tabsTop"] + 0.5 and g["undoH"] >= 44 and not g["sideways"]
                check(f"{w}x{h} {scheme} {theme}: message above the menu, Undo 44 px or more, no sideways scroll", ok, g)
                c.close()

        check("no page errors", not errors, errors)
        browser.close()
    print(f"\n{sum(results)}/{len(results)} checks passed")
    return all(results)

if __name__ == "__main__":
    sys.exit(0 if main() else 1)
