"""Chunk E tests for Minifolio: Mentor matching (typo repair, "Did you mean", a confidence cut-off and "I do not know"). New behaviour only.

1. The brand-free test list, asked of the real engine on the page: ordinary questions, typos (swapped, doubled, missing, joined and
   split words), questions Mentor must not answer, app questions, colour questions and starters. Seven questions on the list need the
   phrase and synonym data of a later chunk (MF1) and are left out here: water, clothes, a small room, photos, a first model, streaky.
2. The bands: a weak match that needed a typo fix is "maybe" with the corrected question; a clear match, or an entry's own title, has no "Did you mean".
   Everyday words are never repaired ("bread" is not "break"); a real slip still is.
3. The window: "Did you mean" and one chip that asks the corrected question; the chip and its line go once it is asked.
4. "I do not know that yet.": one line, the starter chips under it, the window stays open with the box ready; an empty box adds nothing.
5. Layout at 390x844 dark, 360x640 light and 320x568 dark: the line never sits over a chip, chips 44 px or more, no sideways scroll.
6. Nothing typed is stored.
Run all tests with `python3 tests/run_all.py`, or serve the repo folder and run this file on its own."""
import os, sys
from playwright.sync_api import sync_playwright

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import test_v24 as t

results = []

def check(name, ok, detail=""):
    results.append(bool(ok))
    print(("PASS " if ok else "FAIL ") + name + ("" if ok else f"  -> {detail}"))

# question, wanted (keys with |, or none / colour / app:<topic>), how: first = the first source, sources = any source, or the answer kind
LIST = {
    "ordinary": [
        ("how do I thin my paint", "thinning-paint", "first"), ("what is drybrushing", "drybrushing", "first"),
        ("how do I do a wash", "applying-washes|wash-vs-glaze", "first"), ("how do I highlight edges", "edge-highlighting", "first"),
        ("what is a wet palette", "wet-palette", "first"), ("should I buy an airbrush", "is-an-airbrush-worth-it", "first"),
        ("how do I clean my brushes", "brush-care", "first"), ("what varnish should I use", "varnishing", "first"),
        ("how do I paint white without it going chalky", "painting-white|fix-chalky-white-paint", "first"),
        ("how do I fix a mistake after the paint is dry", "fix-dry-paint-mistakes", "first"),
        ("how do I make a base look like grass", "grass", "first"), ("how do I make rust", "painting-rust|rust|heavy-rust|light-rust", "first"),
        ("how do I paint faces and eyes", "painting-eyes|painting-faces", "first"), ("what primer should I use", "choosing-primer-colour", "first"),
        ("do I need to prime my models", "choosing-primer-colour|brush-priming|spray-priming", "first"),
        ("primer or no primer", "choosing-primer-colour", "first"),
        ("how do I paint a glowing sword", "glowing-energy-blades|osl-colour-choice", "sources"),
        ("My paint is lumpy, what do I do?", "reviving-old-paint|fix-rough-paint-texture", "sources"),
        # about painting, not about the app, although they name a price or feedback
        ("how much does an airbrush cost", "is-an-airbrush-worth-it|hobby-on-a-budget|airbrush-basics", "first"),
        ("how do I get feedback on my painting", "asking-for-critique", "first"),
    ],
    "typos": [
        ("undrcoat", "coloured-undercoats|choosing-primer-colour", "first"), ("drybrsuh", "drybrushing", "first"),
        ("highlite", "where-highlights-go|choosing-highlight-colours|edge-highlighting", "first"),
        ("wat is a wet pallette", "wet-palette", "first"), ("how do i thni my paint", "thinning-paint", "first"),
        ("edge hihglighting", "edge-highlighting", "first"), ("wetpalette", "wet-palette", "first"),
        ("how do i varnsh my models", "varnishing", "first"), ("zenithal primming", "zenithal-priming", "first"),
        ("drybrushign metal", "drybrushing-metal", "sources"), ("can i use oil paints on miniatu res", "oil-paints-on-models|acrylic-enamel-and-oil-paints", "first"),
        ("shadign recesses", "recess-shading", "first"), ("basecaot tips", "base-coating", "first"),
    ],
    "no answer": [
        ("what time is it in tokyo", "none", "none"), ("how do I bake sourdough bread", "none", "none"), ("asdf qwerty", "none", "none"),
        ("the of it", "none", "none"), ("best pizza near me", "none", "none"), ("what is the capital of france", "none", "none"),
        ("how do I fix my wifi", "none", "none"), ("", "none", "none"), ("comment peindre une figurine", "none", "none"),
    ],
    "app": [
        ("is minifolio free?", "app:price", "app"), ("how do i back up my data", "app:backup", "app"),
        ("does mentor send my questions anywhere", "app:privacy", "app"), ("do i need an account", "app:privacy", "app"),
        ("does it work offline", "app:install", "app"), ("are you ai", "app:mentor", "app"), ("how do i report a bug", "app:feedback", "app"),
    ],
    "colour and starters": [
        ("best paint for a red cloak", "colour", "colour"), ("what goes with blue", "colour", "colour"), ("green eyes", "colour", "colour"),
        ("I'm new. What do I need to start painting?", "starter-tool-kit|first-model-steps|choosing-brushes|choosing-your-first-paints", "first"),
        ("How thin should my paint be?", "thinning-paint", "first"),
    ],
}

ASK = """(qs) => qs.map((q) => { const a = MinifolioMentor.mentorAnswer(q, { index: knowledgeIndex(), paints: [], tips: MENTOR_TIPS });
    return { kind: a.kind, keys: (a.sources || []).map((s) => s.key), app: a.app || '', band: a.band || '', dym: a.didYouMean || '', fixes: a.fixes || [], lead: a.lead }; })"""

def passes(a, want, how):
    ws = want.split("|")
    if how in ("none", "colour"):
        return a["kind"] == how
    if how == "app":
        return a["kind"] == "app" and a["app"] == want
    if a["kind"] != "answer":
        return False
    return (a["keys"][:1] if how == "first" else a["keys"]) and any(k in ws for k in (a["keys"][:1] if how == "first" else a["keys"]))

def open_it(page):
    page.click("#mentor-button")
    page.wait_for_selector(".mentor-window")
    page.wait_for_function("() => document.querySelector('.mentor-window').getAnimations().every(a => a.playState === 'finished')")

def ask(page, text):
    page.fill(".mentor-input", text)
    page.keyboard.press("Enter")

def last_reply(page):
    return page.locator(".mentor-reply").last

# boxes of the last reply's first line and every chip in the window; true when the line overlaps none of them
OVERLAP = """() => { const box = [...document.querySelectorAll('.mentor-reply')].pop(); const line = box.querySelector('.mentor-dym, .mentor-lead').getBoundingClientRect();
    return [...document.querySelectorAll('.mentor-window .mentor-chip')].filter(c => c.getClientRects().length).some(c => { const r = c.getBoundingClientRect();
      return r.left < line.right && r.right > line.left && r.top < line.bottom && r.bottom > line.top; }); }"""
LAYOUT = """() => { const w = document.querySelector('.mentor-window').getBoundingClientRect();
    const chips = [...document.querySelectorAll('.mentor-reply .mentor-chip')].map(c => c.getBoundingClientRect());
    return { sideways: document.documentElement.scrollWidth > innerWidth, small: chips.filter(r => r.height < 44).length,
             outside: chips.filter(r => r.left < w.left - 0.5 || r.right > w.right + 0.5).length, n: chips.length }; }"""

def main():
    errors, dialogs = [], []
    with sync_playwright() as p:
        browser = p.chromium.launch()
        ctx = browser.new_context(viewport={"width": 390, "height": 844}, service_workers="block", reduced_motion="reduce")
        page = ctx.new_page()
        page.on("pageerror", lambda x: errors.append(str(x)))
        page.on("dialog", lambda d: (dialogs.append(d.message), d.dismiss()))
        t.fresh(page)

        print("\n--- 1. The test list ---")
        for group, rows in LIST.items():
            got = page.evaluate(ASK, [q for q, _, _ in rows])
            bad = [(q, a["kind"], a["app"] or a["keys"][:2]) for (q, want, how), a in zip(rows, got) if not passes(a, want, how)]
            check(f"{group}: {len(rows) - len(bad)}/{len(rows)} give the right answer", not bad, bad)

        print("\n--- 2. Bands and repairs ---")
        weak, clear, none, bread, slip, title = page.evaluate(ASK, ["basecaot tips", "how do I thin my paint", "asdf qwerty", "bread chess website", "shadign recesses", "Base coating"])
        check("a weak match that needed a typo fix is 'maybe', with the corrected question", weak["band"] == "maybe" and weak["dym"] == "Basecoat tips", weak)
        check("a clear match answers straight away, with no 'Did you mean'", clear["band"] == "clear" and not clear["dym"], clear)
        check("no answer: the lead is 'I do not know that yet.' and the starter questions come with it",
              none["kind"] == "none" and none["lead"] == "I do not know that yet.", none)
        check("everyday words are never repaired or split (bread, chess, website)", bread["kind"] == "none" and not bread["fixes"], bread)
        check("a real slip in a hobby word is still repaired", slip["kind"] == "answer" and slip["fixes"] == [["shadign", "shading"]], slip)
        check("asking an entry's own title (a tapped 'Did you mean' chip) is clear", title["band"] == "clear" and title["keys"][:1] == ["base-coating"], title)

        print("\n--- 3. Did you mean ---")
        open_it(page)
        ask(page, "blendign tips")
        r = last_reply(page)
        order = r.evaluate("b => [...b.children].map(c => c.className)")
        check("the reply starts with the line 'Did you mean' and then one chip", r.locator(".mentor-dym").inner_text() == "Did you mean"
              and order[:2] == ["mentor-dym", "mentor-chips mentor-chips-in mentor-dym-chips"] and r.locator(".mentor-dym-chips .mentor-chip").count() == 1, order)
        check("the chip is the corrected question, then the answer and its sources follow",
              r.locator(".mentor-dym-chips .mentor-chip").inner_text() == "Blending tips" and r.locator(".mentor-source").count() >= 1, order)
        check("'Did you mean' never sits over a chip", not page.evaluate(OVERLAP))
        check("the answer is announced with the question it read", page.locator(".mentor-window [role=status]").inner_text().startswith("Did you mean Blending tips? "))
        m = page.locator(".mentor-msg").count()
        r.locator(".mentor-dym-chips .mentor-chip").click()
        check("tapping the chip asks the corrected question", page.locator(".mentor-msg").count() == m + 2 and page.locator(".mentor-me").last.inner_text() == "Blending tips")
        check("the new answer is clear (no 'Did you mean') and the used chip and its line are gone",
              last_reply(page).locator(".mentor-dym").count() == 0 and page.locator(".mentor-dym").count() == 0 and last_reply(page).locator(".mentor-source").count() >= 1)

        print("\n--- 4. I do not know ---")
        ask(page, "asdf qwerty")
        r = last_reply(page)
        check("one short line: 'I do not know that yet.', no sources", r.locator(".mentor-lead").inner_text() == "I do not know that yet." and r.locator(".mentor-source").count() == 0)
        starters = page.evaluate("() => knowledgeIndex().list({ kind: 'starter' }).map(e => e.title)")
        chips = r.locator(".mentor-chips-in .mentor-chip").evaluate_all("els => els.map(e => e.textContent)")
        check("starter question chips sit under the line", chips and all(c in starters for c in chips)
              and r.evaluate("b => b.querySelector('.mentor-lead').getBoundingClientRect().bottom <= b.querySelector('.mentor-chips-in').getBoundingClientRect().top"), chips)
        check("the window stays open with the box empty and ready to type in", page.locator(".mentor-window").count() == 1
              and page.evaluate("() => document.activeElement === document.querySelector('.mentor-input') && !document.activeElement.value"))
        check("the line never sits over a chip", not page.evaluate(OVERLAP))
        page.wait_for_timeout(600)
        check("the window does not close by itself", page.locator(".mentor-window").count() == 1)
        r.locator(".mentor-chips-in .mentor-chip").first.click()
        check("a starter chip under the line asks its question", page.locator(".mentor-me").last.inner_text() == chips[0] and last_reply(page).locator(".mentor-source").count() >= 1)
        m = page.locator(".mentor-msg").count()
        ask(page, "   ")
        check("an empty box adds nothing and the window stays open", page.locator(".mentor-msg").count() == m and page.locator(".mentor-window").count() == 1)

        print("\n--- 5. Layout ---")
        for (w, h, dark), typo in zip(((390, 844, True), (360, 640, False), (320, 568, True)), ("basecaot tips", "shadign tips", "layring tips")):
            page.set_viewport_size({"width": w, "height": h})
            page.evaluate("(d) => document.documentElement.setAttribute('data-appearance', d ? 'dark' : 'light')", dark)
            name = f"{w}x{h} {'dark' if dark else 'light'}"
            ask(page, typo)
            dym = page.evaluate(LAYOUT)
            dym_ok = page.locator(".mentor-reply").last.locator(".mentor-dym").count() == 1 and not page.evaluate(OVERLAP)
            ask(page, "asdf qwerty")
            no = page.evaluate(LAYOUT)
            check(f"{name}: chips wrap inside the window, 44 px or more, nothing scrolls sideways, the line clear of every chip",
                  dym_ok and dym["n"] >= 1 and dym["small"] == 0 and dym["outside"] == 0 and not dym["sideways"] and not no["sideways"] and no["small"] == 0 and no["outside"] == 0 and no["n"] >= 1 and not page.evaluate(OVERLAP), [dym, no])

        print("\n--- 6. Nothing stored ---")
        stored = page.evaluate("() => Object.keys(localStorage).map(k => localStorage.getItem(k)).join(' ')")
        check("nothing typed is stored", "blendign" not in stored and "basecaot" not in stored and "asdf" not in stored)
        check("no page errors", not errors, errors)
        check("no browser pop-ups", not dialogs, dialogs)
        browser.close()
    print(f"\n{sum(results)}/{len(results)} checks passed")
    sys.exit(0 if all(results) else 1)

if __name__ == "__main__":
    main()
