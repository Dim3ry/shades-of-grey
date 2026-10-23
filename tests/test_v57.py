"""v57 tests for Minifolio (chunk 1.2: the "Save a backup?" card).

What changed:
 Testers added units, recipes and photos and never saved a backup: they didn't know Save backup existed until they went looking in
 Settings. Everything lives only on the device. Now the Dashboard shows one calm "Save a backup?" card once there is something worth
 keeping (5 of your own units, or 1 of your own recipe; examples don't count), and again when the last backup is 30 days old and the
 units or recipes changed since. Save backup on it saves the same file as Settings; Not now hides it for 14 days. Its explanation is
 behind More info. It never shows with the feedback card or the iPhone warning. Settings says "Last backup: <date>" (or "Never")
 under Save backup. The v14 reminder toast is gone (the card replaces it).

Checks:
1. Versions, the v57 Updates entry.
2. When it shows: not with examples only, not with 4 of your own units, yes with 5, yes with 1 own recipe.
3. What the card is: the heading, More info (shut at first), Save backup and Not now, 44 px buttons, fits a phone.
4. Save backup on the card downloads the same backup as Settings, remembers the day, and the card goes (also after a reload).
5. Not now hides it for 14 days; after that it comes back.
6. 30 days later: only when something changed since that backup.
7. Only one notice at a time: the feedback card and the iPhone warning go first.
8. Settings says Last backup: <date> or Never, under Save backup.
9. Help and the code: the old toast is gone.
10. No page errors, no browser pop-ups.
Run all tests with `python3 tests/run_all.py`, or serve the repo folder and run this file on its own."""
import datetime, json, os, re, sys
from playwright.sync_api import sync_playwright

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from notice_watch import attach_notices
import fold_opener   # Settings cards fold shut since v54
import test_v31 as t
import test_v44 as e   # fresh, existing, main_tab, sub_tab, toast, saved_settings, own_recipe

URL, read = t.URL, t.read
results = []

def check(name, ok, detail=""):
    results.append(bool(ok))
    print(("PASS " if ok else "FAIL ") + name + ("" if ok else f"  -> {detail}"))

def day(n):
    """A date in YOUR time zone, written like the app writes it: today plus n days."""
    return (datetime.date.today() + datetime.timedelta(days=n)).isoformat()

def short(iso):
    y, m, d = map(int, iso.split("-"))
    return f"{d} {['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec'][m - 1]} {y}"

def units(n):
    return [{"id": i + 1, "name": f"Squad {i + 1}", "hobby": "40K", "faction": "Ultramarines", "stage": 2, "count": 5} for i in range(n)]

def add_own_units(page, n):
    page.evaluate("""(n) => { for (let i = 0; i < n; i++) models.push({ id: Math.max(0, ...models.map(m => m.id)) + 1,
        name: 'Mine ' + (i + 1), hobby: '40K', faction: 'Ultramarines', stage: 1, count: 5, log: [] }); save(); render(); }""", n)

def nudge(page):
    e.main_tab(page, "dashboard")
    return page.locator("#backup-nudge").is_visible()

def tap(page, selector):
    page.locator(selector).scroll_into_view_if_needed()
    page.click(selector)
    page.wait_for_timeout(300)

def main():
    errors, dialogs = [], []
    app, html = read("app.js"), read("index.html")
    with sync_playwright() as p:
        browser = p.chromium.launch()
        ctx = browser.new_context(viewport={"width": 390, "height": 844}, service_workers="block", accept_downloads=True)
        page = ctx.new_page()
        page.on("pageerror", lambda x: errors.append(str(x)))
        page.on("dialog", lambda d: (dialogs.append(d.message), d.dismiss()))
        attach_notices(page, dialogs.append)
        fold_opener.open_cards_on_load(page)

        # ---------- 1. Versions ----------
        print("\n--- 1. Versions and the Updates entry ---")
        e.fresh(page)
        version = page.evaluate("APP_VERSION")
        check("APP_VERSION is v57 or later", float(version[1:]) >= 57, version)
        m = re.search(r'const VERSION = "v([\d.]+)"', read("sw.js"))
        check("sw.js VERSION matches", m and "v" + m.group(1) == version, m and m.group(1))
        tags = re.findall(r'<script src="[^"]+\?v=(\d+)"', html)
        check("all six script tags carry the version number", len(tags) == 6 and set(tags) == {version[1:]}, tags)
        check("the comments that name the number agree", f'The "?v={version[1:]}" makes' in html and f'e.g. "app.js?v={version[1:]}"' in app)
        entry = page.evaluate("CHANGELOG.find(c => c.version === 'v57')")
        check("the v57 Updates entry exists and is the newest while v57 is current", bool(entry) and (version != "v57" or page.evaluate("CHANGELOG[0].version") == "v57"))
        joined = " ".join(entry["changes"]) if entry else ""
        check("the entry names the card, Save backup, Not now and the Settings line",
              all(w in joined for w in ("save a backup", "Save backup", "Not now", "last backup", "Never")), joined)
        check("no em dash in the v57 Updates entry", "—" not in app[app.index('{ version: "v57"'):app.index('{ version: "v56"')])
        check("DATA_VERSION is still 1", page.evaluate("DATA_VERSION") == 1)

        # ---------- 2. When it shows ----------
        print("\n--- 2. When it shows ---")
        check("a brand-new start (examples only): no card", not nudge(page))
        add_own_units(page, 4)
        check("4 of your own units: still no card", not nudge(page))
        add_own_units(page, 1)
        check("the 5th of your own units: the card shows", nudge(page))
        e.fresh(page)
        page.evaluate("() => { for (const m of models) delete m.example; save(); render(); }")   # Keep them: 3 units become yours
        check("3 kept example units (yours now) are not enough", not nudge(page))
        e.fresh(page)
        e.own_recipe(page)
        check("one recipe of your own: the card shows", nudge(page))
        e.existing(page, units(12))
        check("someone who already uses the app and never saved a backup gets the card", nudge(page))

        # ---------- 3. What the card is ----------
        print("\n--- 3. What the card is ---")
        text = page.text_content("#backup-nudge")
        check("it asks 'Save a backup?'", text.strip().startswith("Save a backup?"), text)
        more = page.locator("#backup-nudge .more-info-button")
        check("its explanation is behind More info, shut at first",
              more.count() == 1 and more.inner_text().strip() == "More info" and not page.locator("#more-backup-nudge").is_visible())
        tap(page, "#backup-nudge .more-info-button")
        why = page.inner_text("#more-backup-nudge")
        check("More info says why, in plain words",
              all(w in why for w in ("only kept on this device", "7 days", "Restore backup", "Save full backup with photos")), why)
        tap(page, "#backup-nudge .more-info-button")
        buttons = page.evaluate("""() => [...document.querySelectorAll('#backup-nudge .button-grid button')]
            .map(b => ({ text: b.textContent, h: b.getBoundingClientRect().height }))""")
        check("two buttons, Save backup then Not now", [b["text"] for b in buttons] == ["Save backup", "Not now"], buttons)
        check("both buttons are at least 44 px tall", all(b["h"] >= 44 for b in buttons), buttons)
        check("the card fits a phone (no sideways scroll)", page.evaluate("document.documentElement.scrollWidth <= window.innerWidth"))
        check("it is a note, like the other notice cards", page.get_attribute("#backup-nudge", "role") == "note" and "notice-card" in page.get_attribute("#backup-nudge", "class"))

        # ---------- 4. Save backup on the card ----------
        print("\n--- 4. Save backup on the card ---")
        with page.expect_download() as dl:
            tap(page, "#backup-nudge .backup-nudge-save")
        download = dl.value
        check("it downloads the same file as Save backup in Settings", download.suggested_filename == f"minifolio-backup-{day(0)}.json", download.suggested_filename)
        body = json.loads(open(download.path(), encoding="utf-8").read())
        check("the file holds the units", len(body.get("models", [])) == 12, len(body.get("models", [])))
        check("the usual message says it was saved", "Backup saved" in e.toast(page)["text"], e.toast(page))
        s = e.saved_settings(page)
        check("the day and what was saved are remembered", s.get("lastBackup") == day(0) and s.get("lastBackupPrint") == page.evaluate("dataPrint()"), s)
        check("the card goes", not nudge(page))
        e.reload(page)
        check("and stays gone after a reload", not nudge(page))
        add_own_units(page, 1)
        check("a change the same day does not bring it back", not nudge(page))

        # ---------- 5. Not now ----------
        print("\n--- 5. Not now ---")
        e.existing(page, units(6))
        check("(the card is up)", nudge(page))
        tap(page, "#backup-nudge .backup-nudge-later")
        check("Not now hides the card", not nudge(page))
        s = e.saved_settings(page)
        check("for 14 days", s.get("backupNudgeNextAfter") == day(14), s.get("backupNudgeNextAfter"))
        check("Not now saves nothing as a backup", not s.get("lastBackup"), s.get("lastBackup"))
        page.reload(); page.wait_for_timeout(300)
        check("still hidden after a reload", not nudge(page))
        e.existing(page, units(6), settings={"backupNudgeNextAfter": day(3)})
        check("still hidden 11 days later", not nudge(page))
        e.existing(page, units(6), settings={"backupNudgeNextAfter": day(0)})
        check("back on the 14th day", nudge(page))

        # ---------- 6. A month later ----------
        print("\n--- 6. A month later ---")
        e.existing(page, units(8))
        print_now = page.evaluate("dataPrint()")
        e.existing(page, units(8), settings={"lastBackup": day(-31), "lastBackupPrint": print_now})
        check("31 days, nothing changed: no card", not nudge(page))
        add_own_units(page, 1)
        check("31 days and a change since: the card shows", nudge(page))
        check("it says when the last one was", f"Your last one was on {short(day(-31))}" in page.text_content("#backup-nudge"), page.text_content("#backup-nudge"))
        e.existing(page, units(8), settings={"lastBackup": day(-10), "lastBackupPrint": "kdifferent"})
        check("10 days and a change since: no card yet", not nudge(page))
        e.existing(page, units(8), settings={"lastBackup": day(-40)})
        check("a backup from before v57 (nothing remembered about it), 40 days ago: the card shows", nudge(page))

        # ---------- 7. One notice at a time ----------
        print("\n--- 7. One notice at a time ---")
        e.existing(page, units(8), settings={"feedbackFirstSeen": day(-10), "feedbackShownOn": day(0)})
        check("the feedback card already up today: it stays, and the backup card waits",
              page.locator("#feedback-card").is_visible() and not nudge(page))
        tap(page, "#feedback-card .feedback-later")
        page.wait_for_timeout(200)
        check("after the feedback card is answered, the backup card shows", nudge(page) and not page.locator("#feedback-card").is_visible())
        e.existing(page, units(8), settings={"feedbackFirstSeen": day(-10)})
        s = e.saved_settings(page)
        check("a day the feedback card would go up: the backup card goes first, feedback asks another day",
              nudge(page) and not page.locator("#feedback-card").is_visible() and not s.get("feedbackShownOn"), s)
        e.existing(page, units(2), settings={"feedbackFirstSeen": day(-10)})
        check("with nothing to back up, the feedback card shows as before", page.locator("#feedback-card").is_visible() and not nudge(page))

        iphone = browser.new_context(viewport={"width": 390, "height": 844}, service_workers="block",
                                     user_agent="Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1")
        ip = iphone.new_page()
        ip.on("pageerror", lambda x: errors.append(str(x)))
        ip.on("dialog", lambda d: (dialogs.append(d.message), d.dismiss()))
        e.existing(ip, units(8))
        check("on an iPhone in Safari, the iPhone warning shows and the backup card waits",
              ip.locator("#iphone-warning").is_visible() and not nudge(ip))
        tap(ip, "#iphone-warning-ok")
        check("after Got it, the backup card shows", nudge(ip) and not ip.locator("#iphone-warning").is_visible())
        iphone.close()

        # ---------- 8. Settings ----------
        print("\n--- 8. Settings: Last backup ---")
        e.existing(page, units(8))
        e.main_tab(page, "settings")
        age = page.inner_text("#backup-age")
        check("before any backup it says 'Last backup: Never'", age.startswith("Last backup: Never"), age)
        place = page.evaluate("""() => { const a = document.getElementById('backup-age'), grid = document.getElementById('export-button').parentElement;
            return a.previousElementSibling === grid && a.closest('#backup-card') !== null; }""")
        check("it sits right under the backup buttons (Save backup first)", place)
        with page.expect_download():
            page.click("#export-button")
        page.wait_for_timeout(200)
        age = page.inner_text("#backup-age")
        check("after Save backup it says the date", age == f"Last backup: {short(day(0))} (today).", age)
        page.evaluate(f"settings.lastBackup = '{day(-10)}'; renderSettings()")
        age = page.inner_text("#backup-age")
        check("an older one says the date and how long ago", age == f"Last backup: {short(day(-10))} (10 days ago).", age)

        # ---------- 9. Help and code ----------
        print("\n--- 9. Help and the code ---")
        check("the old reminder toast is gone", "function maybeRemindToBackUp(" not in app and page.evaluate("typeof maybeRemindToBackUp") == "undefined")
        help_text = page.evaluate("() => document.getElementById('help-backup-nudge').textContent")
        check("Help describes the card, Not now and the Settings line",
              all(w in help_text for w in ("Save a backup?", "Not now", "two weeks", "30 days", "Never")) and "reminds you after a week" not in help_text, help_text)
        snippet = app[app.index("function renderBackupNudge("):app.index("// ----- iPhone warning (v14) -----")]
        check("the card is built from text, not HTML", "textContent" in snippet and not re.search(r"innerHTML\s*=\s*[^\"\s]", snippet) and 'innerHTML = ""' in snippet)
        check("Save backup on the card presses the Settings button (one backup code path)", 'getElementById("export-button").click()' in snippet)

        # ---------- 10. No errors ----------
        print("\n--- 10. No errors ---")
        check("no page errors", not errors, errors[:3])
        check("no browser pop-ups were shown", not dialogs, dialogs[:3])
        browser.close()

    ok = all(results)
    print(f"\n{sum(results)} of {len(results)} checks passed")
    sys.exit(0 if ok else 1)

if __name__ == "__main__":
    main()
