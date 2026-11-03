"""v126 tests: "Last backup ... N days ago" counts calendar days, so a 23- or 25-hour day at a clock change does not move the count
(found by T6; daysSince() used to divide the hours since the backup day's midnight by 24).
Run all tests with `python3 tests/run_all.py`, or serve the repo folder and run this file on its own."""
import datetime, os, sys
from playwright.sync_api import sync_playwright
from launch_helpers import leave_launch

PORT = os.environ.get("SOG_PORT", "8765")
URL = f"http://localhost:{PORT}/index.html"
results = []
def check(name, ok, detail=""):
    results.append(bool(ok))
    print(("PASS " if ok else "FAIL ") + name + ("" if ok else f"  -> {detail}"))

UTC = datetime.timezone.utc
# (UK wall clock as UTC, backup day, whole days the app must count, wording it must show)
CASES = [
    (datetime.datetime(2026, 11, 3, 23, 30, tzinfo=UTC), "2026-10-24", 10, "10 days ago"),   # 23:30 GMT, 25 Oct had 25 hours
    (datetime.datetime(2026, 11, 3, 12, 0, tzinfo=UTC), "2026-10-24", 10, "10 days ago"),    # the same day at noon
    (datetime.datetime(2027, 3, 28, 23, 30, tzinfo=UTC), "2027-03-28", 1, "yesterday"),      # 00:30 BST on 29 Mar, 28 Mar had 23 hours
    (datetime.datetime(2027, 3, 28, 23, 30, tzinfo=UTC), "2027-03-19", 10, "10 days ago"),
    (datetime.datetime(2026, 7, 1, 11, 0, tzinfo=UTC), "2026-07-01", 0, "today"),            # no clock change
]

with sync_playwright() as pw:
    browser = pw.chromium.launch()
    page = browser.new_page(viewport={"width": 390, "height": 844}, timezone_id="Europe/London")
    errors = []
    page.on("pageerror", lambda e: errors.append(str(e)))
    page.clock.set_fixed_time(CASES[0][0])
    page.goto(URL)
    page.evaluate("() => localStorage.clear()")
    page.reload()
    leave_launch(page)
    for now, day, want, words in CASES:
        page.clock.set_fixed_time(now)
        got = page.evaluate("d => Math.floor(daysSince(d))", day)
        text = page.evaluate("d => { settings.lastBackup = d; renderBackupAge(); const el = document.getElementById('backup-age'); return el ? el.textContent : ''; }", day)
        label = now.strftime("%d %b %Y %H:%M UTC")
        check(f"{label}, backup {day}: counts {want} whole days", got == want, got)
        check(f"{label}, backup {day}: says '{words}'", f"({words})" in text, text)
    check("a full timestamp still counts real time (36 hours = 1.5 days)",
          abs(page.evaluate("() => daysSince(new Date(Date.now() - 36 * 3600000).toISOString())") - 1.5) < 0.01)
    check("no page errors", not errors, errors)
    browser.close()

passed = sum(results)
print(f"\n{passed} passed, {len(results) - passed} failed")
sys.exit(0 if all(results) else 1)
