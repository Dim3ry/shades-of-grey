"""Test helpers for the colour wheel after v43 (the drill-down). Not a test file itself (run_all.py only runs test_*.py).

Before v43, tapping red, orange, yellow, green, blue or purple opened that colour's whole paint list under the wheel, and tapping it again
closed it. Since v43 a tap on one of those colours redraws the picture as its three groups; the paints open when a GROUP is tapped.
The older tests were written around "tap a colour, look at its list", so they use `tap` below, which keeps that meaning:

  tap(page, "blue")   first call: drills into Blue and opens its first group that has paints of the person's (else the middle group);
                      second call: goes back up to the whole wheel (so "tap again closes it" still reads the same);
                      from another drilled-in colour it goes back first, so "switch to another colour" works.
  The grey centre (white, grey, black, metallic) is tapped exactly as before.

The new behaviour itself is tested in test_v43.py."""

HUES = ["red", "orange", "yellow", "green", "blue", "purple"]
SUBS = {
    "red": ["deep", "red", "pink"], "orange": ["brown", "orange", "peach"], "yellow": ["mustard", "yellow", "bone"],
    "green": ["olive", "green", "sea"], "blue": ["navy", "blue", "light"], "purple": ["deep", "violet", "lavender"],
}

def wheel_state(page):
    return page.evaluate("() => ({ zoom: compendiumState.wheelZoom, group: compendiumState.wheelGroup, wheel: compendiumState.wheel })")

def go_back(page):
    page.evaluate("() => document.getElementById('cmp-wheel').scrollIntoView({ block: 'center' })")
    page.click("#cmp-wheel-back")
    page.wait_for_timeout(120)

def zoom_in(page, key):
    if wheel_state(page)["zoom"]:
        go_back(page)   # another colour (or this one) is drilled into: the colour slices are not on show, so go back up first
    page.evaluate("() => document.getElementById('cmp-wheel').scrollIntoView({ block: 'center' })")
    page.click(f'[data-wheel="{key}"]')
    page.wait_for_timeout(120)

def open_group(page, key, sub):
    """Tap one group of the drilled-in colour (its middle ring point, as a finger would)."""
    index = SUBS[key].index(sub)
    page.evaluate("() => document.getElementById('cmp-wheel').scrollIntoView({ block: 'center' })")
    x, y = page.evaluate("""(i) => { const r = document.getElementById('cmp-wheel').getBoundingClientRect(), k = r.width / 320, a = [0, 120, 240][i] * Math.PI / 180;
        return [r.left + (160 + 73 * Math.sin(a)) * k, r.top + (150 - 73 * Math.cos(a)) * k]; }""", index)
    page.mouse.click(x, y)
    page.wait_for_timeout(120)

def default_group(page, key):
    """The first group of this colour with a paint of the person's own (owned, wishlist or empty), else the middle group."""
    sub = page.evaluate("""(k) => { const w = WHEEL.find(x => x.key === k); const items = wheelItems().filter(x => x.at.seg === k && x.origin < 2);
        const hit = w.subs.find(s => items.some(x => x.at.sub === s.key)); return hit ? hit.key : w.subs[1].key; }""", key)
    return sub

def tap(page, key):
    st = wheel_state(page)
    if key not in HUES:
        if st["zoom"]:
            go_back(page)        # a colour is drilled into: the grey centre is not on show, so go back up first
        page.click(f'[data-wheel="{key}"]')
        page.wait_for_timeout(120)
        return
    if st["zoom"] == key:
        go_back(page)            # the second tap: back up, so everything is closed again
        return
    if st["zoom"]:
        go_back(page)            # another colour is drilled into: back up first
    zoom_in(page, key)
    open_group(page, key, default_group(page, key))

def open_each_group(page, key, read):
    """Drill into a colour, open each of its three groups in turn, collect read(page) for each, go back up. Returns a list of three results."""
    out = []
    if wheel_state(page)["zoom"] == key:
        go_back(page)
    zoom_in(page, key)
    for sub in SUBS[key]:
        open_group(page, key, sub)
        out.append(read(page))
        open_group(page, key, sub)   # tap again closes it
    go_back(page)
    return out

def touch_open(tp, key):
    """The same as tap(), for a touch phone page (taps with a finger): drill into a colour and open its default group."""
    tp.evaluate("() => document.getElementById('cmp-wheel').scrollIntoView({ block: 'center' })")
    tp.tap(f'[data-wheel="{key}"]')
    tp.wait_for_timeout(150)
    index = SUBS[key].index(default_group(tp, key))
    x, y = tp.evaluate("""(i) => { const r = document.getElementById('cmp-wheel').getBoundingClientRect(), k = r.width / 320, a = [0, 120, 240][i] * Math.PI / 180;
        return [r.left + (160 + 73 * Math.sin(a)) * k, r.top + (150 - 73 * Math.cos(a)) * k]; }""", index)
    tp.touchscreen.tap(x, y)
    tp.wait_for_timeout(150)

def open_everything(page):
    """With a group open: show its other paints and every 'Show all', then report (nothing scrolls sideways, how many rows are listed)."""
    if page.locator("#cmp-wheel-others").count() and page.get_attribute("#cmp-wheel-others", "aria-expanded") == "false":
        page.click("#cmp-wheel-others")
        page.wait_for_timeout(200)
    for _ in range(6):
        more = page.locator('#cmp-wheel-detail button[id^="cmp-wheel-more-"][aria-expanded="false"]')
        if not more.count():
            break
        more.first.click()
        page.wait_for_timeout(80)
    return (page.evaluate("() => document.documentElement.scrollWidth <= window.innerWidth + 1"), page.locator("#cmp-wheel-detail .idea-static").count())
