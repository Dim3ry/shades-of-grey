"""X9 tests for Minifolio (wording sweep). New behaviour only:
1. "the Mentor" and "Ask the Mentor" appear nowhere in what a person can read or hear: Help, the Mentor window, button labels,
   aria-labels, titles and placeholders (internal ids and old Updates entries are not looked at).
2. "Compendium" is not in Help or the Colour Lab / Guides pages.
3. Help describes Mentor and the new menu, and Help > Privacy says Mentor runs on the device, nothing typed is sent or stored,
   and the chat is cleared when the app reloads (and it really is).
Run all tests with `python3 tests/run_all.py`, or serve the repo folder and run this file on its own."""
import os, sys, re
from playwright.sync_api import sync_playwright

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import test_v31 as t
from launch_helpers import wait_settled

results = []

def check(name, ok, detail=""):
    results.append(bool(ok))
    print(("PASS " if ok else "FAIL ") + name + ("" if ok else f"  -> {detail}"))

BAD = re.compile(r"\bthe mentor\b", re.I)

# Every readable string on the page now: text of the sections that are not Updates, plus label-like attributes everywhere.
READABLE = """() => {
  const out = [];
  for (const s of document.querySelectorAll('main > section')) { if (s.id !== 'view-updates') out.push(s.textContent); }
  for (const el of document.querySelectorAll('[aria-label],[title],[placeholder],[alt]')) {
    if (el.closest('#view-updates')) continue;
    for (const a of ['aria-label', 'title', 'placeholder', 'alt']) { const v = el.getAttribute(a); if (v) out.push(v); }
  }
  const w = document.querySelector('.mentor-window'); if (w) out.push(w.textContent);
  return out.join(' | ');
}"""

def main():
    errors = []
    with sync_playwright() as p:
        browser = p.chromium.launch()
        ctx = browser.new_context(viewport={"width": 390, "height": 844}, service_workers="block")
        page = ctx.new_page()
        page.on("pageerror", lambda x: errors.append(str(x)))
        page.on("dialog", lambda d: (errors.append("dialog: " + d.message), d.dismiss()))
        t.load(page, launch=True, settings={"tab": "settings", "examplesChecked": True})
        wait_settled(page)
        check("Ask Mentor button is labelled Ask Mentor", page.get_attribute("#mentor-button", "aria-label") == "Ask Mentor")

        page.click("#mentor-button")
        page.wait_for_selector(".mentor-window")
        page.fill(".mentor-input", "armour blue")
        page.click(".mentor-send")
        page.wait_for_selector(".mentor-reply")
        text = page.evaluate(READABLE)
        check("no 'the Mentor' in any readable string, with the Mentor window open and a reply shown", not BAD.search(text), BAD.findall(text))
        check("the window's labels say Mentor", page.get_attribute(".mentor-window", "aria-label") == "Mentor" and page.get_attribute(".mentor-close", "aria-label") == "Close Mentor")

        page.keyboard.press("Escape")
        page.wait_for_function("() => !document.querySelector('.mentor-backdrop')")
        page.reload()
        wait_settled(page)
        page.click("#mentor-button")
        page.wait_for_selector(".mentor-window")
        check("the chat is cleared when the app reloads", page.locator(".mentor-msg").count() == 0)
        page.keyboard.press("Escape")

        for tab in ("guides", "settings", "dashboard"):
            t.load(page, launch=True, settings={"tab": tab, "examplesChecked": True})
            wait_settled(page)
            text = page.evaluate(READABLE)
            check(f"{tab}: no 'the Mentor' and no Compendium in readable text", not BAD.search(text) and "compendium" not in text.lower(), (BAD.findall(text), "compendium" in text.lower()))

        help_ = page.inner_text("#help-mentor") if page.locator("#help-mentor").count() else ""
        priv = page.evaluate("() => document.getElementById('privacy-mentor') ? document.getElementById('privacy-mentor').textContent : ''")
        check("Help has a short Mentor line that names Ask Mentor and Guides", "Ask Mentor" in help_ and "Guides" in help_, help_)
        check("Help > Privacy says on the device, not sent, not stored, cleared on reload",
              all(w in priv for w in ["on this device", "not sent anywhere", "not stored", "cleared when the app reloads"]), priv)
        check("the old 'kept until you close the app' wording is gone", "until you close the app" not in page.evaluate("() => document.getElementById('view-help').textContent"))
        check("no em dashes in the new Help text", "—" not in help_ + priv + page.inner_text("#help-colour-lab") if page.locator("#help-colour-lab").count() else False)
        check("no page errors or pop-ups", not errors, errors)
        browser.close()
    print(f"\n{sum(results)}/{len(results)} checks passed")
    return 0 if all(results) else 1

if __name__ == "__main__":
    sys.exit(main())
