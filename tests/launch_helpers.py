"""U4b (v89): a fresh load of the app shows the start page (the circle), with every section hidden.

Older tests were written when the app opened straight on the last section. Their load / seed helpers call leave_launch(page) once after
the page loads: it taps the segment (or the cog) for the section the app had saved (settings.tab, or the Dashboard), which puts the
page where those tests have always started. Tests of the start page itself skip it (see tests/test_v89_launch.py)."""

SETTINGS_PAGES = ("settings", "help", "updates")

def is_launching(page):
    return page.evaluate("() => document.body.classList.contains('launching')")

# One page.evaluate does it all: it taps the same buttons a person would (a real click event on the segment or the cog), without
# Playwright's actionability waits, and the app switches section in the same call.
_TAP = """() => {
    if (typeof settings !== 'object') return null;                       // the app has not started yet
    if (!document.body.classList.contains('launching')) return false;    // nothing to do
    const tab = settings.tab || 'dashboard';
    const page = ['settings', 'help', 'updates'].includes(tab);
    document.querySelector(page ? '.cog[data-tab="settings"]' : '.tabs button[data-tab="' + tab + '"]').click();
    if (page && tab !== 'settings') document.querySelector('#more-seg button[data-page="' + tab + '"]').click();
    return true;
}"""

def leave_launch(page):
    """Tap through the start page to the saved section. Does nothing when the start page is not showing."""
    if page.evaluate(_TAP) is None:
        page.wait_for_function("() => typeof settings === 'object'")
        page.evaluate(_TAP)
