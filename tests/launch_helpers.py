"""U4b (v89): a fresh load of the app shows the start page (the circle), with every section hidden.

Older tests were written when the app opened straight on the last section. Their load / seed helpers call leave_launch(page) once after
the page loads: it taps the segment (or the cog) for the section the app had saved (settings.tab, or the Dashboard), which puts the
page where those tests have always started. Tests of the start page itself skip it (see tests/test_v89_launch.py)."""

SETTINGS_PAGES = ("settings", "help", "updates")

def is_launching(page):
    return page.evaluate("() => document.body.classList.contains('launching')")

def leave_launch(page):
    """Tap through the start page to the saved section, as a person would. Does nothing when the start page is not showing."""
    if not is_launching(page):
        return
    tab = page.evaluate("() => settings.tab") or "dashboard"
    if tab in SETTINGS_PAGES:
        page.click('.cog[data-tab="settings"]')
        if tab != "settings":
            page.click(f'#more-seg button[data-page="{tab}"]')
    else:
        page.click(f'.tabs button[data-tab="{tab}"]')
    page.wait_for_timeout(150)
