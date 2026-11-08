"""TD2 tests for Minifolio. New behaviour only: a pasted army list that names its game puts that game in the Game box.
The Warhammer app ends a list with "Created with Warhammer <game name>: The App"; "General's Handbook" is a second sign.
A list that names no game, or a game the app does not know, keeps the 40K default. The box can still be changed by hand.
All sample lists here are short and invented."""
import os, sys
from playwright.sync_api import sync_playwright

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import test_v31 as t

results = []

def check(name, ok, detail=""):
    results.append(bool(ok))
    print(("PASS " if ok else "FAIL ") + name + ("" if ok else f"  -> {detail}"))

BODY = "Test list (100 points)\r\nSome Faction\r\n\r\nUnit One (50 points)\r\n  • 5x Warrior\r\n\r\nUnit Two (50 points)\r\n  • 5x Archer\r\n\r\n"
AOS = BODY + "Created with Warhammer Age of Sigmar: The App\r\nApp: 1.0.0 | Data: 1\r\n"
AOS_CURLY = "General’s Handbook 2026-27\r\n" + BODY
FORTY = BODY + "Exported with App Version: v1.0.0 (1), Data Version: v1\r\n"
NO_FOOTER = BODY
UNKNOWN = BODY + "Created with Warhammer Imaginary Game: The App\r\n"
UNKNOWN_WITH_HANDBOOK = "General's Handbook 2026-27\r\n" + UNKNOWN

def game_for(page, text):
    """Paste the text, read it, return the Game box, close the check screen."""
    page.click("#wh-button") if page.locator("#wh-panel.hidden").count() else None
    page.fill("#wh-text", text)
    page.click("#wh-read")
    page.wait_for_selector("#review:not(.hidden)")
    got = page.input_value("#wh-game")
    page.click("#review-cancel")
    return got

def main():
    errors, dialogs = [], []
    with sync_playwright() as p:
        browser = p.chromium.launch()
        for w, h, scheme in [(390, 844, "dark"), (360, 640, "light")]:
            ctx = browser.new_context(viewport={"width": w, "height": h}, service_workers="block",
                                      reduced_motion="reduce", color_scheme=scheme)
            page = ctx.new_page()
            page.on("pageerror", lambda x: errors.append(str(x)))
            page.on("dialog", lambda d: (dialogs.append(d.message), d.dismiss()))
            t.load(page, units=[])
            page.click('nav button[data-tab="units"]')
            page.wait_for_timeout(200)
            page.click("#toggle-add")
            page.click("#add-wh")
            tag = f"{w} px {scheme}: "

            check(tag + "an Age of Sigmar footer puts Age of Sigmar in the Game box", game_for(page, AOS) == "Age of Sigmar")
            check(tag + "the 40K layout (no game named) keeps 40K", game_for(page, FORTY) == "40K")
            check(tag + "a list with no footer keeps 40K", game_for(page, NO_FOOTER) == "40K")
            check(tag + "a footer naming an unknown game keeps 40K, and does not invent that game",
                  game_for(page, UNKNOWN) == "40K")
            if w == 390:
                check("General's Handbook alone (curly apostrophe) gives Age of Sigmar", game_for(page, AOS_CURLY) == "Age of Sigmar")
                check("an unknown footer beats the Handbook line, so it stays 40K", game_for(page, UNKNOWN_WITH_HANDBOOK) == "40K")
                check("the footer is read in lower case too",
                      game_for(page, BODY + "created with warhammer age of sigmar: the app\r\n") == "Age of Sigmar")
                # By hand: change the box on the check screen, and the units carry the new game.
                page.fill("#wh-text", AOS)
                page.click("#wh-read")
                page.wait_for_selector("#review:not(.hidden)")
                page.fill("#wh-game", "Kill Team")
                check("the Game box can still be changed by hand", page.input_value("#wh-game") == "Kill Team")
                page.click("#review-cancel")
            check(tag + "no sideways scroll",
                  page.evaluate("document.documentElement.scrollWidth <= document.documentElement.clientWidth"))
            ctx.close()

        # Spelling you already use is kept.
        ctx = browser.new_context(viewport={"width": 390, "height": 844}, service_workers="block", reduced_motion="reduce")
        page = ctx.new_page()
        page.on("pageerror", lambda x: errors.append(str(x)))
        page.on("dialog", lambda d: (dialogs.append(d.message), d.dismiss()))
        t.load(page, units=[{"id": 1, "name": "Liberators", "hobby": "age of sigmar", "faction": "Other", "stage": 0, "count": 1}])
        page.click('nav button[data-tab="units"]')
        page.wait_for_timeout(200)
        page.click("#toggle-add")
        page.click("#add-wh")
        check("a game you already have keeps your spelling", game_for(page, AOS) == "age of sigmar")
        ctx.close()
        browser.close()

    check("no page errors", not errors, errors)
    check("no browser pop-ups", not dialogs, dialogs)
    print(f"\n{sum(results)}/{len(results)} checks passed")
    sys.exit(0 if all(results) else 1)

if __name__ == "__main__":
    main()
