"""Chunk D tests for Minifolio: Mentor starts fresh after a while, with a Back button, and a taller window on a phone. New behaviour only.

1. The idle time is one named setting (MENTOR_IDLE_MINUTES) and is 30.
2. Reopening within 30 minutes keeps the exchange; after 30 minutes, or after a reload, the window opens at its start. A window left open is not touched.
3. Back: arrow only, 44 px, named "Back to start", top left, only in the chat view; it clears the exchange, brings the starter questions back, and focus goes to the first thing.
4. Keyboard and press: Tab reaches it, it has a visible focus ring, it ripples on a press, and not with reduced motion.
5. Nothing is stored: no storage writes while chatting, and the question words are not found in any storage.
6. Help and Privacy say the new sentence.
7. Taller window on a phone at 390x844, 360x640 and 320x568: taller than before, clear of the top and the bottom bar, still scrolls, no sideways scroll.
The clock is faked by moving Date.now on; nothing waits 30 real minutes.
Run all tests with `python3 tests/run_all.py`, or serve the repo folder and run this file on its own."""
import os, sys
from playwright.sync_api import sync_playwright

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import test_v24 as t

results = []

def check(name, ok, detail=""):
    results.append(bool(ok))
    print(("PASS " if ok else "FAIL ") + name + ("" if ok else f"  -> {detail}"))

def settle(page):
    page.wait_for_function("() => document.querySelector('.mentor-window').getAnimations().every(a => a.playState === 'finished')")

def open_it(page):
    page.click("#mentor-button")
    page.wait_for_selector(".mentor-window")
    settle(page)

def close_it(page):
    page.keyboard.press("Escape")
    page.wait_for_function("() => !document.querySelector('.mentor-backdrop')")

def ask(page, text):
    page.fill(".mentor-input", text)
    page.keyboard.press("Enter")

def rect(page, sel):
    return page.evaluate("(s) => { const r = document.querySelector(s).getBoundingClientRect(); return [r.left, r.top, r.right, r.bottom, r.width, r.height]; }", sel)

def shown(page, sel):
    return page.evaluate("(s) => { const e = document.querySelector(s); return !!e && e.getClientRects().length > 0 && getComputedStyle(e).visibility !== 'hidden'; }", sel)

def msgs(page):
    return page.locator(".mentor-msg").count()

def jump(page, minutes):
    """Move the app's clock (Date.now) on by this many minutes."""
    page.evaluate("(m) => { window.__skew = (window.__skew || 0) + m * 60000; }", minutes)

CLOCK = """() => { if (window.__skewOn) return; window.__skewOn = true; const real = Date.now.bind(Date); window.__skew = 0;
    Date.now = () => real() + window.__skew; }"""

def main():
    errors = []
    with sync_playwright() as p:
        browser = p.chromium.launch()
        ctx = browser.new_context(viewport={"width": 390, "height": 844}, service_workers="block", reduced_motion="reduce")
        page = ctx.new_page()
        page.on("pageerror", lambda x: errors.append(str(x)))
        t.fresh(page)
        page.evaluate(CLOCK)

        print("\n--- 1. The setting ---")
        check("MENTOR_IDLE_MINUTES is 30", page.evaluate("() => typeof MENTOR_IDLE_MINUTES !== 'undefined' && MENTOR_IDLE_MINUTES") == 30)

        print("\n--- 2. Fresh start after a while ---")
        open_it(page)
        check("the start view has no Back button", not shown(page, ".mentor-back"))
        ask(page, "armour blue")
        check("after a question the exchange is showing", msgs(page) == 2 and page.evaluate("() => document.querySelector('.mentor-window').classList.contains('mentor-chatting')"))
        close_it(page)
        jump(page, 29)
        open_it(page)
        check("reopened 29 minutes later: the exchange is still there", msgs(page) == 2)
        close_it(page)
        jump(page, 2)
        open_it(page)
        check("reopened 31 minutes after the last message: the start view", msgs(page) == 0 and not page.evaluate("() => document.querySelector('.mentor-window').classList.contains('mentor-chatting')"))
        check("the greeting and the starter chips show again", shown(page, ".mentor-greeting") and page.locator(".mentor-col > .mentor-chips .mentor-chip").count() >= 1)
        ask(page, "thin paint")
        jump(page, 60)
        check("a window left open for an hour is not touched", msgs(page) == 2)
        ask(page, "red armour")
        check("a new message is counted from now", msgs(page) == 4)
        close_it(page)
        jump(page, 29)
        open_it(page)
        check("the time counts from the latest message, not the first", msgs(page) == 4)
        close_it(page)

        print("\n--- 3. Reload ---")
        page.reload()
        page.wait_for_function("() => typeof openMentor === 'function'")
        open_it(page)
        check("after a reload the window opens at its start", msgs(page) == 0 and not shown(page, ".mentor-back"))
        close_it(page)
        page.evaluate(CLOCK)

        print("\n--- 4. Back button ---")
        open_it(page)
        starters_before = page.locator(".mentor-col > .mentor-chips .mentor-chip").evaluate_all("els => els.map(e => e.textContent)")
        ask(page, "red armour")
        used = page.locator(".mentor-me").first.inner_text().lower()
        back = page.locator(".mentor-back")
        check("Back shows in the chat view", shown(page, ".mentor-back"))
        r, w = rect(page, ".mentor-back"), rect(page, ".mentor-window")
        check("it is 44 px square and in the top left corner of the window", abs(r[4] - 44) < 1 and abs(r[5] - 44) < 1 and r[0] - w[0] < 16 and r[1] - w[1] < 16, (r, w))
        check("it is named Back to start, is a real button, and has no visible words",
              back.get_attribute("aria-label") == "Back to start" and back.evaluate("e => e.tagName") == "BUTTON" and back.inner_text().strip() == "")
        orb, cl, sc = rect(page, ".mentor-orbbox"), rect(page, ".mentor-close"), rect(page, ".mentor-scroll")
        check("it does not touch the orb or the close X, and no message sits over it", r[2] <= orb[0] and r[2] <= cl[0] and sc[1] >= r[3], (r, orb, cl, sc))
        back.click()
        check("Back clears the exchange and returns to the start view", msgs(page) == 0 and not page.evaluate("() => document.querySelector('.mentor-window').classList.contains('mentor-chatting')"))
        check("the window stays open and Back is gone", page.locator(".mentor-window").count() == 1 and not shown(page, ".mentor-back"))
        again = page.locator(".mentor-col > .mentor-chips .mentor-chip").evaluate_all("els => els.map(e => e.textContent)")
        check("the starter chips are all back", again == starters_before, (again, starters_before))
        check("focus lands on the first thing in the start view", page.evaluate("() => document.activeElement.textContent") == "Paint Picker")
        close_it(page)
        open_it(page)
        check("after Back and a reopen it is still at the start", msgs(page) == 0)
        close_it(page)
        # the phone's own Back, the X, tapping outside and Escape still close the window
        open_it(page); ask(page, "thin paint")
        page.click(".mentor-close")
        page.wait_for_function("() => !document.querySelector('.mentor-backdrop')")
        check("the close X still closes it and keeps the exchange for the next open", True)
        open_it(page)
        check("the exchange was kept", msgs(page) == 2)
        page.mouse.click(5, 5)
        page.wait_for_function("() => !document.querySelector('.mentor-backdrop')")
        check("a tap outside still closes it", page.locator(".mentor-backdrop").count() == 0)

        print("\n--- 5. Keyboard and press ---")
        open_it(page)
        ask(page, "thin paint")
        page.focus(".mentor-chips .mentor-chip, .mentor-form input")
        page.keyboard.down("Shift")
        for _ in range(12):
            if page.evaluate("() => document.activeElement.className") == "mentor-back":
                break
            page.keyboard.press("Tab")
        page.keyboard.up("Shift")
        check("Shift+Tab from inside the window reaches Back (it is in the tab order)", page.evaluate("() => document.activeElement.className") == "mentor-back")
        page.focus(".mentor-back")
        ring = page.evaluate("() => { const e = document.querySelector('.mentor-back'); const c = getComputedStyle(e); return [c.outlineStyle, parseFloat(c.outlineWidth)]; }")
        check("a keyboard focus shows a ring", page.evaluate("() => document.activeElement.className") == "mentor-back" and ring[0] != "none" and ring[1] >= 2, ring)
        check("no resting transform on it", page.evaluate("() => getComputedStyle(document.querySelector('.mentor-back')).transform") == "none")
        check("no ripple with reduced motion", page.evaluate("""() => { const b = document.querySelector('.mentor-back'); const r = b.getBoundingClientRect();
            b.dispatchEvent(new PointerEvent('pointerdown', { bubbles: true, clientX: r.left + 10, clientY: r.top + 10 })); return b.querySelectorAll('.ripple').length; }""") == 0)
        close_it(page)
        page.emulate_media(reduced_motion="no-preference")
        open_it(page); ask(page, "thin paint")
        check("a press ripples when motion is allowed", page.evaluate("""() => { const b = document.querySelector('.mentor-back'); const r = b.getBoundingClientRect();
            b.dispatchEvent(new PointerEvent('pointerdown', { bubbles: true, clientX: r.left + 10, clientY: r.top + 10 })); return b.querySelectorAll('.ripple').length; }""") == 1)
        close_it(page)
        page.emulate_media(reduced_motion="reduce")

        print("\n--- 6. Nothing is stored ---")
        page.evaluate("""() => { window.__sets = 0; const set = Storage.prototype.setItem;
            Storage.prototype.setItem = function (...a) { window.__sets++; return set.apply(this, a); }; }""")
        open_it(page)
        ask(page, "zebra blue unicorn")
        page.locator(".mentor-back").click()
        ask(page, "zebra blue unicorn")
        check("chatting and going back wrote nothing to storage", page.evaluate("() => window.__sets") == 0, page.evaluate("() => window.__sets"))
        stored = page.evaluate("""async () => { let s = JSON.stringify(localStorage) + JSON.stringify(sessionStorage);
            if (indexedDB.databases) { for (const d of await indexedDB.databases()) s += d.name; }
            return s.toLowerCase(); }""")
        check("the words typed are not in any storage", "zebra" not in stored and "unicorn" not in stored)
        close_it(page)

        print("\n--- 7. Help and Privacy ---")
        NEW = "The chat is cleared when the app reloads or after a while without use."
        priv = page.evaluate("() => document.getElementById('privacy-mentor').textContent")
        helpt = page.evaluate("() => document.getElementById('help-mentor').textContent")
        check("Privacy says the new sentence", "the chat is cleared when the app reloads or after a while without use." in priv.lower() or NEW in priv, priv)
        check("Help says the same", "cleared when the app reloads or after a while without use." in helpt, helpt)
        check("the rest of the Privacy line is kept", all(w in priv for w in ["runs on this device", "not sent anywhere", "not stored"]), priv)

        print("\n--- 8. Taller window on a phone ---")
        OLD = 480   # the old height of the chat window
        for w, h in ((390, 844), (360, 640), (320, 568)):
            page.set_viewport_size({"width": w, "height": h})
            open_it(page)
            ask(page, "red armour")
            ask(page, "thin paint")
            wr, fr = rect(page, ".mentor-window"), rect(page, ".mentor-form")
            check(f"{w}x{h}: chat window is taller than {OLD} px or fills the room, and sits inside the screen",
                  (wr[5] > OLD or wr[1] <= 60) and wr[1] >= 56 and wr[3] <= h and wr[0] >= 0 and wr[2] <= w, wr)
            check(f"{w}x{h}: the box and Send are inside the window and on screen", fr[3] <= wr[3] and fr[3] <= h and fr[1] >= wr[1], (fr, wr))
            check(f"{w}x{h}: the chat area still scrolls and nothing scrolls sideways",
                  page.evaluate("""() => { const s = document.querySelector('.mentor-scroll'); return s.scrollHeight > s.clientHeight && getComputedStyle(s).overflowY === 'auto'
                      && document.documentElement.scrollWidth <= innerWidth; }"""))
            page.evaluate("() => document.activeElement.blur()")
            page.locator(".mentor-back").click()
            ask(page, "red armour")
            page.evaluate("() => document.activeElement.blur()")
            wr2 = rect(page, ".mentor-window")
            room = h - page.evaluate("() => parseFloat(getComputedStyle(document.querySelector('.mentor-backdrop')).paddingBottom)")   # the bar's height plus a gap
            check(f"{w}x{h}: with the keyboard away the window stays clear of the bottom bar", room < h - 100 and wr2[3] <= room + 1, (wr2, room))
            ob, cb, bb = rect(page, ".mentor-orbbox"), rect(page, ".mentor-close"), rect(page, ".mentor-back")
            check(f"{w}x{h}: the orb, X and Back keep their place at the top of the window", ob[1] - wr2[1] < 20 and cb[1] - wr2[1] < 10 and bb[1] - wr2[1] < 10, (ob, cb, bb, wr2))
            close_it(page)
        print("\n--- 9. Notice and themes ---")
        page.set_viewport_size({"width": 360, "height": 640})
        for dark in (True, False):
            page.evaluate("(d) => { document.documentElement.setAttribute('data-appearance', d ? 'dark' : 'light'); }", dark)
            open_it(page); ask(page, "red armour")
            page.evaluate("() => { document.activeElement.blur(); showToast('Test notice'); }")
            over = []
            for _ in range(3):
                over.append(page.evaluate("""() => { const t = document.getElementById('toast').getBoundingClientRect();
                    const w = document.querySelector('.mentor-window').getBoundingClientRect();   // a button scrolled out of the chat area is clipped, so it is not counted
                    return [...document.querySelectorAll('.mentor-window button, .mentor-window input')].filter(b => { const r = b.getBoundingClientRect(); if (r.bottom <= w.top) return false;
                        return r.width && r.left < t.right && r.right > t.left && r.top < t.bottom && r.bottom > t.top; }).map(b => b.className + ":" + Math.round(b.getBoundingClientRect().top) + ":" + Math.round(t.bottom)).join(","); }"""))
                page.wait_for_timeout(120)
            check(f"360x640 {'dark' if dark else 'light'}: a notice never sits over a button in the window, even while it appears", over == ["", "", ""], over)
            check(f"360x640 {'dark' if dark else 'light'}: Back is inside the window and nothing scrolls sideways",
                  rect(page, ".mentor-back")[0] >= rect(page, ".mentor-window")[0] and page.evaluate("() => document.documentElement.scrollWidth <= innerWidth"))
            close_it(page)
        page.evaluate("() => document.documentElement.removeAttribute('data-appearance')")
        page.set_viewport_size({"width": 1280, "height": 800})
        open_it(page); ask(page, "red armour")
        wr = rect(page, ".mentor-window")
        check("1280x800: the window stays inside the screen", wr[1] >= 0 and wr[3] <= 800, wr)
        close_it(page)

        check("no page errors", not errors, errors)
        browser.close()
    print(f"\n{sum(results)}/{len(results)} checks passed")
    sys.exit(0 if all(results) else 1)

main()
