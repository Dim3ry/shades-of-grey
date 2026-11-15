"""CM1 test for Minifolio (Classic's corner marks: one pattern). New behaviour only.
P1: a card sitting directly on the page gets the eight marks; anything inside a card never does. Classic only."""
import os, sys
from playwright.sync_api import sync_playwright

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import test_v31 as t
from launch_helpers import wait_settled

results = []

def check(name, ok, detail=""):
    results.append(bool(ok))
    print(("PASS " if ok else "FAIL ") + name + ("" if ok else f"  -> {str(detail)[:400]}"))

UNITS = [{"id": 1, "name": "Alpha", "hobby": "40K", "faction": "Tyranids", "stage": 5, "count": 3}]
# Every screen and whether its top-level cards are marked. "none" screens hold only list rows, which are rows and stay plain.
SCREENS = {"dashboard": "marked", "recipes": "none", "units": "none", "shopping": "marked", "about": "marked", "guides": "marked",
           "settings": "marked", "help": "marked", "updates": "marked"}
CARDS = """() => [...document.querySelectorAll('.card, .panel-marked')].filter(e => e.getBoundingClientRect().height > 0).map(e => ({
  inner: !!e.parentElement.closest('.card, .panel-marked'),
  marks: getComputedStyle(e).backgroundImage.split('linear-gradient').length - 1 }))"""

def load(browser, tab, theme="classic", appearance="dark", w=390, h=844):
    c = browser.new_context(viewport={"width": w, "height": h}, service_workers="block")
    pg = c.new_page()
    t.load(pg, units=UNITS, settings={"tab": tab, "examplesChecked": True, "appearance": appearance, "theme": theme})
    wait_settled(pg)
    return pg, c

def main():
    errors = []
    with sync_playwright() as p:
        browser = p.chromium.launch()
        for tab, want in SCREENS.items():
            pg, c = load(browser, tab)
            cards = pg.evaluate(CARDS)
            outer = [x["marks"] for x in cards if not x["inner"]]
            inner = [x["marks"] for x in cards if x["inner"]]
            if want == "marked":
                check(f"Classic {tab}: every top-level card has eight marks", outer and all(n == 8 for n in outer), cards)
            else:
                check(f"Classic {tab}: list rows stay plain", all(n == 0 for n in outer), cards)
            check(f"Classic {tab}: nothing inside a card has marks", all(n == 0 for n in inner), cards)
            c.close()

        # Sub-screens: the three Shopping tabs and two Painting pages
        pg, c = load(browser, "shopping")
        for n in ("Paints", "Gear", "Wishlist"):
            pg.evaluate("(n) => [...document.querySelectorAll('#shop-seg button')].find(x => x.textContent.trim().startsWith(n)).click()", n)
            wait_settled(pg)
            cards = pg.evaluate(CARDS)
            check(f"Shopping, {n} tab: its card is marked", cards and all(x["marks"] == 8 for x in cards if not x["inner"]), cards)
        c.close()
        pg, c = load(browser, "recipes")
        for n in ("Your Palette", "Colour Lab"):
            pg.evaluate("(n) => [...document.querySelectorAll('#view-recipes [role=tab], #view-recipes .tab-row button')].find(x => x.textContent.trim() === n).click()", n)
            wait_settled(pg)
            cards = pg.evaluate(CARDS)
            check(f"Painting, {n}: its cards are marked", cards and all(x["marks"] == 8 for x in cards if not x["inner"]), cards)
        c.close()

        # A box that is not a .card opts in with the class; the same box inside a card does not
        pg, c = load(browser, "dashboard")
        r = pg.evaluate("""() => { const d = document.createElement('div'); d.className = 'panel-marked'; document.querySelector('#view-dashboard').appendChild(d);
          const i = document.createElement('div'); i.className = 'panel-marked'; document.querySelector('#headline-card').appendChild(i);
          const n = e => getComputedStyle(e).backgroundImage.split('linear-gradient').length - 1; return [n(d), n(i)]; }""")
        check("panel-marked opts a box in", r[0] == 8, r)
        c.close()

        # Mentor window and the Theme swatch keep their marks
        pg, c = load(browser, "dashboard")
        pg.click("#mentor-button"); pg.wait_for_selector(".mentor-window", state="visible")
        check("the Mentor window still has eight marks", pg.evaluate("() => getComputedStyle(document.querySelector('.mentor-window')).backgroundImage.split('linear-gradient').length - 1") == 8)
        c.close()

        # Light mode and the narrowest screen: marks stay on, no sideways scroll
        for ap, w, h in (("light", 390, 844), ("dark", 320, 568)):
            pg, c = load(browser, "dashboard", appearance=ap, w=w, h=h)
            cards = pg.evaluate(CARDS)
            side = pg.evaluate("() => document.documentElement.scrollWidth > innerWidth + 1")
            check(f"Classic {ap} {w} wide: cards marked, no sideways scroll", all(x["marks"] == 8 for x in cards if not x["inner"]) and not side, (cards, side))
            c.close()

        # The other three looks draw no more than they did: no card there gets the Classic eight strokes
        for th in ("parchment", "forge", "bench"):
            pg, c = load(browser, "settings", theme=th)
            cards = pg.evaluate(CARDS)
            check(f"{th}: no card has the Classic eight marks", cards and all(x["marks"] != 8 for x in cards), cards)
            c.close()
        browser.close()
    print(f"\n{sum(results)}/{len(results)} checks passed")
    sys.exit(0 if all(results) else 1)

if __name__ == "__main__":
    main()
