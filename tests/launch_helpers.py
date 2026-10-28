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

# v93 (Mo3b): leaving the start page also runs a half-second move (the circle turns into the bar, the Mentor button glides down). Older tests
# only want to be on the section, so after the tap this helper jumps that move to its end (the same final state it reaches by itself) and waits
# for the real end condition: no picture of the old shape left and no animation left on the bar. Tests of the move itself (test_v93) do not use it.
_FINISH_BAR = """() => document.getAnimations().filter(a => a.effect && a.effect.target && a.effect.target.closest
    && a.effect.target.closest('.tabs, .mo-ring, .mo-ghost')).forEach(a => a.finish())"""

def leave_launch(page):
    """Tap through the start page to the saved section. Does nothing when the start page is not showing."""
    if page.evaluate(_TAP) is None:
        page.wait_for_function("() => typeof settings === 'object'")
        page.evaluate(_TAP)
    page.evaluate(_FINISH_BAR)
    wait_settled(page)


# v92 (Mo3a): moving between screens takes 240 ms, and while it moves the old section is still drawn on top. Tests that look at a
# section right after a tap wait for the real end of the move (no layer left and no animation on any section), which is as soon
# as it has settled however slow the machine is, instead of a fixed delay.
_SETTLED = """() => !document.querySelector('.mo-out, .mo-box, .mo-ring, .mo-ghost')
    && [...document.querySelectorAll('main > section, #recipe-home, #recipe-page')].every(e => e.getAnimations().length === 0)
    && document.querySelector('.tabs').getAnimations({ subtree: true }).length === 0"""

def wait_settled(page, timeout=15000):
    page.wait_for_function(_SETTLED, timeout=timeout)
