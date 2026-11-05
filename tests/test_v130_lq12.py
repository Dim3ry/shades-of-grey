"""LQ12 tests for Minifolio (the Models list glides on Delete and Undo; the bar fades back after typing). New behaviour only:
1. Delete (300 units, a card in the middle): a copy of the card fades out where it was (opacity only, in a layer outside the list, inert,
   hidden from screen readers, no data-id), the cards below on the screen glide up (transform only), only cards near the screen move,
   no card is drawn again (MS1), and at rest no copy and no transform is left.
2. Undo: the card comes back and fades in where it lands, the cards below glide back down, only that card is drawn, nothing is left moving.
   The same at the top and at the end of the list.
3. The bar after typing (Models' Unit name box, Guides' search, the Mentor box): its opacity rises over time once the box is left, opacity
   only (it never moves or changes colour), at MO6's slow pace; typing again ends the fade at once.
4. Never while the start circle shows or travels, and a travel starting ends a fade at once. Not from 900 px (the bar never stepped aside).
5. Reduce motion: Delete, Undo and the bar's return happen at once with no animation.
Run all tests with `python3 tests/run_all.py`, or serve the repo folder and run this file on its own."""
import os, sys
from playwright.sync_api import sync_playwright

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import test_v31 as t
from launch_helpers import wait_settled, _FINISH_BAR

results = []

def check(name, ok, detail=""):
    results.append(bool(ok))
    print(("PASS " if ok else "FAIL ") + name + ("" if ok else f"  -> {str(detail)[:400]}"))

def units(n):
    out = []
    for i in range(1, n + 1):
        u = {"id": i, "name": f"Squad {i}", "hobby": "Skirmish", "stage": 1 + i % 5, "count": 3, "added": "2026-10-01", "log": [["2026-10-01", 1 + i % 5]]}
        if i % 2: u["faction"] = "Iron Wolves"
        out.append(u)
    return out

SETTINGS = {"factionColours": {"Iron Wolves": "#3366aa"}, "tab": "units"}

def card(uid):
    return f'#unit-list > li.unit[data-id="{uid}"]'

def load(page, n=300, launch=False, settings=None):
    t.load(page, units=units(n), settings=settings or SETTINGS, launch=launch)
    page.evaluate(_FINISH_BAR)
    if not launch:
        wait_settled(page)

def settle(page):
    page.wait_for_function("""() => !document.querySelector('.lq-ghost') && ![...document.querySelectorAll('#unit-list > li.unit')].some(li => li.getAnimations().length)""")

# Open the card and its Details, put it in the middle of the screen, press Delete in Details (the question box is then up).
ASK = """async (id) => { const sel = `#unit-list > li.unit[data-id="${id}"]`, wait = (ms) => new Promise(r => setTimeout(r, ms));
    let c; for (let i = 0; i < 100 && !(c = document.querySelector(sel)); i++) await wait(30);   // T6: wait for the card to be drawn (the list arrives in pieces), not a guess
    c.scrollIntoView({ block: 'center' });
    if (c.classList.contains('compact')) c.querySelector('.info').click();
    await wait(350); c = document.querySelector(sel);
    const d = c.querySelector('.details-toggle'); if (d.getAttribute('aria-expanded') !== 'true') d.click();
    await wait(350); c = document.querySelector(sel); c.scrollIntoView({ block: 'center' });
    [...c.querySelectorAll('.panel button.danger-button')].filter(b => /Delete/.test(b.textContent)).pop().click();
    await wait(200);
    document.querySelectorAll('#unit-list > li.unit').forEach(li => li.__lq12 = true);
    return !document.getElementById('dialog-backdrop').classList.contains('hidden'); }"""
# Press a button and read, in the same call (before any frame), what moves: the copy, and every card that has an animation
PRESS = """(sel) => { document.querySelector(sel).click();
    const props = (a) => [...new Set(a.effect.getKeyframes().flatMap(f => Object.keys(f).filter(k => !['offset', 'easing', 'composite', 'computedOffset'].includes(k))))];
    const cards = [...document.querySelectorAll('#unit-list > li.unit')];
    const moving = cards.map((li, i) => ({ id: +li.dataset.id, i, anims: li.getAnimations().map(a => ({ props: props(a), first: a.effect.getKeyframes()[0] })) })).filter(c => c.anims.length);
    const layer = document.querySelector('.lq-ghost.card-leaving'), copy = layer && layer.firstElementChild;
    return { moving, fresh: cards.filter(li => !li.__lq12).map(li => +li.dataset.id),
             copy: copy ? { inList: !!copy.closest('#unit-list'), inert: layer.inert, hidden: layer.getAttribute('aria-hidden'), dataId: copy.querySelectorAll('[data-id]').length + (copy.dataset.id ? 1 : 0),
                            ids: copy.querySelectorAll('[id]').length + (copy.id ? 1 : 0), name: (copy.querySelector('.name') || {}).textContent,
                            anims: copy.getAnimations().map(a => ({ props: props(a), first: a.effect.getKeyframes()[0].opacity, last: a.effect.getKeyframes().slice(-1)[0].opacity })) } : null }; }"""
TIDY = """() => !document.querySelector('.lq-ghost') && [...document.querySelectorAll('#unit-list > li.unit')].every(li => getComputedStyle(li).transform === 'none' && getComputedStyle(li).opacity === '1' && !li.getAnimations().length)"""
dy = lambda f: float(f["transform"].split(",")[1].strip(" px)")) if "transform" in f else 0.0

def delete_and_undo(page, uid, where):
    ok = page.evaluate(ASK, uid)
    n = page.evaluate("() => document.querySelectorAll('#unit-list > li.unit').length")
    r = page.evaluate(PRESS, "#dialog-yes")
    c = r["copy"]
    check(f"{where}: Delete: a copy of the card fades out where it was (opacity only, from 1 to 0)",
          ok and c and c["name"] == f"Squad {uid}" and c["anims"] and all(a["props"] == ["opacity"] and a["first"] == "1" and a["last"] == "0" for a in c["anims"]), (ok, c))
    check(f"{where}: …in a layer outside the list, inert and hidden from screen readers, with no ids or data-ids",
          c and not c["inList"] and c["inert"] and c["hidden"] == "true" and c["dataId"] == 0 and c["ids"] == 0, c)
    check(f"{where}: Delete: the unit is gone from the list and no other card was drawn again (MS1)",
          page.locator(card(uid)).count() == 0 and r["fresh"] == [] and page.evaluate("() => document.querySelectorAll('#unit-list > li.unit').length") == n - 1, r["fresh"])
    settle(page)
    check(f"{where}: Delete: at rest no copy is left and no card keeps a transform", page.evaluate(TIDY))
    page.evaluate("() => document.querySelectorAll('#unit-list > li.unit').forEach(li => li.__lq12 = true)")
    u = page.evaluate(PRESS, "#toast-undo")
    back = [m for m in u["moving"] if m["id"] == uid]
    check(f"{where}: Undo: the card comes back and fades in where it lands (opacity only, from 0), and only it is drawn",
          page.locator(card(uid)).count() == 1 and back and back[0]["anims"][0]["props"] == ["opacity"] and back[0]["anims"][0]["first"].get("opacity") == "0"
          and u["fresh"] == [uid], u)
    settle(page)
    check(f"{where}: Undo: nothing is left moving, no transform or fade left, and the card is back open", page.evaluate(TIDY)
          and page.evaluate("(s) => { const c = document.querySelector(s); return !c.classList.contains('compact') && !!c.querySelector(':scope > .panel'); }", card(uid)))
    return r, u

BAR_RISE = """async () => { const bar = document.querySelector('nav.tabs'), raf = () => new Promise(r => requestAnimationFrame(r));
    const segs = () => [...bar.querySelectorAll('.arc > [data-tab]')].map(b => { const r = b.getBoundingClientRect(), cs = getComputedStyle(b);
        return [Math.round(r.left * 10) / 10, Math.round(r.top * 10) / 10, cs.backgroundColor, cs.color]; });
    document.activeElement.blur();
    await new Promise(r => setTimeout(r, 0));
    const anims = bar.getAnimations().filter(a => a.id === 'bar-back').map(a => ({ props: [...new Set(a.effect.getKeyframes().flatMap(f => Object.keys(f).filter(k => !['offset', 'easing', 'composite', 'computedOffset'].includes(k))))],
        ms: a.effect.getTiming().duration, ease: a.effect.getTiming().easing }));
    const out = [], t0 = performance.now(), look = [];
    while (performance.now() - t0 < 4000) { await raf(); out.push(+getComputedStyle(bar).opacity); if (look.length < 2 && out.length > 1) look.push(JSON.stringify(segs()));
        if (out[out.length - 1] === 1 && !bar.getAnimations().some(a => a.id === 'bar-back')) break; }
    look.push(JSON.stringify(segs()));
    return { anims, out, look, flow: parseFloat(getComputedStyle(document.documentElement).getPropertyValue('--motion-flow')),
             flowEase: getComputedStyle(document.documentElement).getPropertyValue('--motion-flow-ease').trim() }; }"""

def rises(r):
    o = r["out"]
    return (len(o) > 2 and o[0] < 0.6 and o[-1] == 1 and all(b >= a - 0.001 for a, b in zip(o, o[1:])) and any(0.05 < v < 0.97 for v in o))

def main():
    errors = []
    with sync_playwright() as p:
        browser = p.chromium.launch()
        ctx = browser.new_context(viewport={"width": 390, "height": 844}, service_workers="block", color_scheme="dark", has_touch=True)
        page = ctx.new_page()
        page.on("pageerror", lambda x: errors.append(str(x)))
        load(page)

        print("--- 1 and 2. Delete and Undo in the middle of 300 units ---")
        r, u = delete_and_undo(page, 150, "middle")
        below = [m for m in r["moving"] if m["id"] > 150]
        check("Delete: the cards below on the screen glide up into the gap (transform only, starting lower)",
              below and all(len(m["anims"]) == 1 and m["anims"][0]["props"] == ["transform"] and dy(m["anims"][0]["first"]) > 0 for m in below), r["moving"])
        idx = [m["i"] for m in r["moving"]]
        check("Delete: only cards on or near the screen move (a few, next to the gap; none far off)",
              0 < len(idx) <= 20 and max(idx) - min(idx) <= 20 and all(abs(m["id"] - 150) <= 20 for m in r["moving"]), idx)
        below = [m for m in u["moving"] if m["id"] > 150]
        check("Undo: the cards below glide back down (transform only, starting higher)",
              below and all(m["anims"][0]["props"] == ["transform"] and dy(m["anims"][0]["first"]) < 0 for m in below), u["moving"])
        check("Undo: only cards near the screen move", 0 < len(u["moving"]) <= 20 and all(abs(m["id"] - 150) <= 20 for m in u["moving"]), [m["id"] for m in u["moving"]])

        print("\n--- 2. The top and the end of the list ---")
        page.evaluate("(s) => document.querySelector(s + ' .info').click()", card(150))   # closed again: one card open at a time anyway
        settle(page)
        delete_and_undo(page, 1, "top")
        page.evaluate("(s) => document.querySelector(s + ' .info').click()", card(1))
        settle(page)
        r, u = delete_and_undo(page, 300, "end")
        # (at the very end the page gets shorter, so the cards above may slide down with the scroll: they glide, by transform only)
        check("end: any card that moves glides by transform only", all(a["props"] == ["transform"] for m in r["moving"] for a in m["anims"]), r["moving"])

        print("\n--- 3. The bar fades back after typing ---")
        load(page, n=4)
        page.click("#toggle-add")
        page.focus("#name-input")
        page.keyboard.type("Wolves")
        check("typing in Models' Unit name box: the bar steps aside", page.evaluate("() => document.body.classList.contains('typing') && getComputedStyle(document.querySelector('nav.tabs')).display === 'none'"))
        rest = page.evaluate("() => [...document.querySelectorAll('nav.tabs .arc > [data-tab]')].map(b => { const cs = getComputedStyle(b); return [cs.backgroundColor, cs.color]; })")
        r = page.evaluate(BAR_RISE)
        check("leaving the box: the bar's opacity rises over time to 1 (not in one frame)", rises(r), r["out"][:12])
        check("…opacity only, at MO6's slow pace (--motion-flow on its ease-out curve)",
              len(r["anims"]) == 1 and r["anims"][0]["props"] == ["opacity"] and r["anims"][0]["ms"] == r["flow"] and r["anims"][0]["ease"].replace(" ", "") == r["flowEase"].replace(" ", ""), r["anims"])
        check("…the bar never moves or changes colour while it fades", len(set(r["look"])) == 1, r["look"])
        check("…its colours at rest are as before typing", page.evaluate("() => [...document.querySelectorAll('nav.tabs .arc > [data-tab]')].map(b => { const cs = getComputedStyle(b); return [cs.backgroundColor, cs.color]; })") == rest)
        page.focus("#name-input")
        page.evaluate("() => document.activeElement.blur()")
        page.wait_for_function("() => document.querySelector('nav.tabs').getAnimations().some(a => a.id === 'bar-back')")
        page.focus("#name-input")
        page.wait_for_function("() => document.body.classList.contains('typing')")
        check("typing again during the fade ends it at once", page.evaluate("() => !document.querySelector('nav.tabs').getAnimations().some(a => a.id === 'bar-back')"))
        page.evaluate("() => { document.activeElement.blur(); }")
        page.evaluate("() => { document.querySelector('nav.tabs').getAnimations().forEach(a => a.finish()); showTab('guides'); }")
        page.wait_for_selector("#guides-search", state="visible")
        page.focus("#guides-search")
        page.keyboard.type("wash")
        r = page.evaluate(BAR_RISE)
        check("Guides' search: leaving it, the bar fades back the same way", rises(r) and len(r["anims"]) == 1, r["out"][:12])
        page.click("#mentor-button")
        page.wait_for_selector(".mentor-input", state="visible")
        page.focus(".mentor-input")
        page.keyboard.type("hello")
        r = page.evaluate(BAR_RISE)
        check("the Mentor box: leaving it, the bar fades back the same way", rises(r) and len(r["anims"]) == 1, r["out"][:12])
        page.keyboard.press("Escape")

        print("\n--- 4. Never while the start circle shows or travels ---")
        load(page, n=4, launch=True)
        n = page.evaluate("() => { document.body.classList.add('typing'); updateTyping(); return document.querySelector('nav.tabs').getAnimations().filter(a => a.id === 'bar-back').length; }")
        check("on the start circle: typing ends with no fade", n == 0 and not page.evaluate("() => document.body.classList.contains('typing')"), n)
        n = page.evaluate("""() => { document.querySelector('.tabs button[data-tab="units"]').click();
            const travelling = document.body.classList.contains('mo-travelling');
            document.body.classList.add('typing'); updateTyping();
            return [travelling, document.querySelector('nav.tabs').getAnimations().filter(a => a.id === 'bar-back').length]; }""")
        check("while the circle travels into the bar: typing ends with no fade", n == [True, 0], n)
        page.evaluate(_FINISH_BAR)
        wait_settled(page)
        n = page.evaluate("""async () => { document.body.classList.add('typing'); updateTyping();
            const bar = document.querySelector('nav.tabs'), fading = bar.getAnimations().some(a => a.id === 'bar-back');
            document.getElementById('home-button').click();
            await Promise.resolve();
            return [fading, document.body.classList.contains('mo-travelling'), bar.getAnimations().filter(a => a.id === 'bar-back').length]; }""")
        check("a fade running when the travel back to the circle starts ends at once", n == [True, True, 0], n)
        page.evaluate(_FINISH_BAR)
        wait_settled(page)

        print("\n--- 5. Reduce motion, and wide screens ---")
        rm = browser.new_context(viewport={"width": 390, "height": 844}, service_workers="block", reduced_motion="reduce", has_touch=True)
        rp = rm.new_page()
        rp.on("pageerror", lambda x: errors.append(str(x)))
        load(rp, n=40)
        rp.evaluate(ASK, 20)
        a = rp.evaluate("() => { document.getElementById('dialog-yes').click(); return [document.querySelectorAll('.card-leaving').length, document.getAnimations().filter(a => a.effect.target && a.effect.target.closest('#unit-list, .card-leaving')).length]; }")
        check("Reduce motion: Delete happens at once, no copy and no animation", a == [0, 0] and rp.locator(card(20)).count() == 0, a)
        a = rp.evaluate("() => { document.getElementById('toast-undo').click(); return document.getAnimations().filter(a => a.effect.target && a.effect.target.closest('#unit-list, .card-leaving')).length; }")
        check("Reduce motion: Undo brings it back at once, no animation", a == 0 and rp.locator(card(20)).count() == 1, a)
        rp.evaluate("() => { document.body.classList.add('typing'); }")
        a = rp.evaluate("() => { updateTyping(); const bar = document.querySelector('nav.tabs'); return [bar.getAnimations().length, getComputedStyle(bar).opacity, getComputedStyle(bar).display]; }")
        check("Reduce motion: the bar is back at once after typing, no animation", a[0] == 0 and a[1] == "1" and a[2] != "none", a)
        rm.close()
        page.set_viewport_size({"width": 360, "height": 640})
        load(page, n=30)
        page.evaluate(ASK, 12)
        top = page.evaluate("(s) => Math.round(document.querySelector(s).getBoundingClientRect().top)", card(12))
        page.click("#dialog-yes")
        settle(page)
        page.click("#toast-undo")
        settle(page)
        now = page.evaluate("(s) => { const r = document.querySelector(s).getBoundingClientRect(); return [Math.round(r.top), r.bottom > 0]; }", card(12))
        check("360x640: Undo of a card taller than the screen puts it back where it was, in sight", top < 0 and now == [top, True], (top, now))
        page.set_viewport_size({"width": 1280, "height": 800})
        load(page, n=4)
        n = page.evaluate("() => { document.body.classList.add('typing'); updateTyping(); return document.querySelector('nav.tabs').getAnimations().filter(a => a.id === 'bar-back').length; }")
        check("from 900 px (the bar never stepped aside): no fade", n == 0, n)
        load(page, n=30)
        page.locator(card(20)).click()
        page.locator("#unit-side button.danger-button", has_text="Delete").last.click()
        r = page.evaluate(PRESS, "#dialog-yes")
        check("from 900 px, Delete in the side pane (the pane closes and the cards take new columns): nothing glides across the page",
              r["moving"] == [] and r["copy"] is None and page.locator(card(20)).count() == 0, r)

        check("no page errors", not errors, errors)
        browser.close()
    print(f"\n{sum(results)}/{len(results)} checks passed")
    sys.exit(0 if all(results) else 1)

if __name__ == "__main__":
    main()
