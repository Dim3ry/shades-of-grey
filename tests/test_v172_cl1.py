"""CL1 tests for Minifolio: clean-up. New behaviour only.
1. One shared Tab loop (wrapTab) for the pop-ups: Tab on the last stop goes to the first, Shift+Tab on the first goes to the last.
2. A question box wraps Tab and Shift+Tab inside itself.
3. A warning (danger) question starts on No, and a stray focus pulled back into the box lands on No, never Yes.
4. A plain question still starts on Yes and pulls back to Yes.
5. The unused helpers are gone from app.js; the ones tests still use are kept.
Run all tests with `python3 tests/run_all.py`, or serve the repo folder and run this file on its own."""
import os, sys
from playwright.sync_api import sync_playwright

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import test_v31 as t

ROOT = t.ROOT
results = []

def check(name, ok, detail=""):
    results.append(bool(ok))
    print(("PASS " if ok else "FAIL ") + name + ("" if ok else f"  -> {detail}"))

ACTIVE = "() => document.activeElement && document.activeElement.id"

def main():
    errors = []
    print("\n--- 5. Dead code ---")
    app = open(os.path.join(ROOT, "app.js"), encoding="utf-8").read()
    gone = ["function sameName(", "function stageFromText(", "const DARK_CARD", "const LIGHT_PAGE"]
    check("unused helpers are gone", not any(g in app for g in gone), [g for g in gone if g in app])
    kept = ["function unsureMentions(", "function foldSection(", "function shownStageColours(", "const LIGHT_CARD"]
    check("helpers that tests still use are kept", all(k in app for k in kept), [k for k in kept if k not in app])
    check("one Tab loop: the wrap sum appears once", app.count("at < 0 || at === stops.length - 1 ? 0 : at + 1") == 1)

    with sync_playwright() as p:
        browser = p.chromium.launch()
        ctx = browser.new_context(viewport={"width": 390, "height": 844}, service_workers="block", reduced_motion="reduce")
        page = ctx.new_page()
        page.on("pageerror", lambda x: errors.append(str(x)))
        page.on("dialog", lambda d: (errors.append("dialog: " + d.message), d.dismiss()))
        t.load(page, settings={"tab": "dashboard", "examplesChecked": True})

        print("\n--- 1. The shared Tab loop ---")
        page.evaluate("""() => { const mk = id => { const b = document.createElement('button'); b.id = id; document.body.appendChild(b); return b; };
            window.__s = ['t1', 't2', 't3'].map(mk); }""")
        def tab(shift, start):
            return page.evaluate("""([shift, start]) => { __s[start].focus();
                const e = new KeyboardEvent('keydown', { key: 'Tab', shiftKey: shift, cancelable: true });
                wrapTab(e, __s); return [document.activeElement.id, e.defaultPrevented]; }""", [shift, start])
        check("Tab on the last goes to the first", tab(False, 2) == ["t1", True], tab(False, 2))
        check("Shift+Tab on the first goes to the last", tab(True, 0) == ["t3", True], tab(True, 0))
        check("Tab in the middle goes to the next", tab(False, 0) == ["t2", True])
        check("an empty list does nothing", page.evaluate("""() => { const e = new KeyboardEvent('keydown', { key: 'Tab', cancelable: true });
            wrapTab(e, []); return e.defaultPrevented; }""") is False)
        page.evaluate("() => __s.forEach(b => b.remove())")

        print("\n--- 2 and 3. A danger question ---")
        page.evaluate("() => askYesNo('Delete it?', () => {}, { danger: true })")
        page.wait_for_function("() => !document.getElementById('dialog-backdrop').classList.contains('hidden')")
        no_id, yes_id = page.evaluate("() => [dialogNo.id, dialogYes.id]")
        check("a danger question starts on No", page.evaluate(ACTIVE) == no_id, page.evaluate(ACTIVE))
        page.evaluate("() => { document.activeElement.blur(); document.body.focus(); }")
        page.evaluate("() => { const b = document.createElement('button'); b.id = 'outside'; document.body.appendChild(b); b.focus(); }")
        check("stray focus is pulled back to No, not Yes", page.evaluate(ACTIVE) == no_id, page.evaluate(ACTIVE))
        page.keyboard.press("Tab")
        check("Tab goes to Yes", page.evaluate(ACTIVE) == yes_id, page.evaluate(ACTIVE))
        page.keyboard.press("Tab")
        check("Tab on the last button wraps to the first", page.evaluate(ACTIVE) == no_id, page.evaluate(ACTIVE))
        page.keyboard.press("Shift+Tab")
        check("Shift+Tab on the first wraps to the last", page.evaluate(ACTIVE) == yes_id, page.evaluate(ACTIVE))
        page.keyboard.press("Escape")
        page.wait_for_function("() => document.getElementById('dialog-backdrop').classList.contains('hidden')")

        print("\n--- 4. A plain question ---")
        page.evaluate("() => askYesNo('Go on?', () => {})")
        page.wait_for_function("() => !document.getElementById('dialog-backdrop').classList.contains('hidden')")
        check("a plain question starts on Yes", page.evaluate(ACTIVE) == yes_id, page.evaluate(ACTIVE))
        page.evaluate("() => document.getElementById('outside').focus()")
        check("stray focus is pulled back to Yes", page.evaluate(ACTIVE) == yes_id, page.evaluate(ACTIVE))
        page.keyboard.press("Escape")

        check("no page errors and no pop-ups", not errors, errors)
        browser.close()
    print(f"\n{sum(results)}/{len(results)} checks passed")
    sys.exit(0 if all(results) else 1)

if __name__ == "__main__":
    main()
