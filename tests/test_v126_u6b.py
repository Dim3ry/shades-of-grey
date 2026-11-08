"""U6b tests for Minifolio (Mentor looks, moods and script, from James's U6 files). New behaviour only:
1. The looks file: three looks, each with all five states; only the --mentor colour names, ml- class names, no scripts, no fixed colours.
2. The script: every stock line is one short plain sentence (eight words or fewer, no em dash, no exclamation mark, no emoji);
   chunk E's "I do not know that yet." stays the first unsure line; a list never gives the same line twice in a row.
3. The setting: Settings > Mentor look (Futuristic, Magical, Grounded) defaults to Futuristic, saves, is on the page before app.js runs
   after a reload, changes the round button (also the start circle's centre), and an unknown value counts as Futuristic.
   Restoring a backup keeps it (it is not in backups, like Shop links).
4. Moods in the window: Thinking while Mentor gets ready, Pleased for a clear answer, Unsure for "Did you mean" and no answer,
   Finished for thanks or a goodbye (with a thanks or finished line), back to neutral after a pause; the round button never shows a mood;
   the orb's box keeps its size. Returning after a long gap greets with a returning line.
5. Reduce motion: nothing in the orb moves, and the moods still differ in shape.
6. The colour set's five colours are still set, but (since U7) the orb's ring keeps the theme's colours. Sizes: 390, 360 and 320 px, light and dark, three themes besides Classic.
Run all tests with `python3 tests/run_all.py`, or serve the repo folder and run this file on its own."""
import json, os, re, sys
from playwright.sync_api import sync_playwright

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import test_v31 as t

results = []
LOOKS = ["futuristic", "magical", "grounded"]
STATES = ["neutral", "thinking", "pleased", "unsure", "finished"]

def check(name, ok, detail=""):
    results.append(bool(ok))
    print(("PASS " if ok else "FAIL ") + name + ("" if ok else f"  -> {detail}"))

def fresh(page, settings=None):
    t.load(page, paints=[], settings=dict({"examplesChecked": True}, **(settings or {})), launch=True)

def open_window(page):
    page.click("#mentor-button")
    page.wait_for_selector(".mentor-window")
    page.wait_for_function("() => document.querySelector('.mentor-window').getAnimations().every(a => a.playState === 'finished')")   # grown to full size

def ask(page, text):
    page.fill(".mentor-input", text)
    page.keyboard.press("Enter")

MOOD = "() => { const b = document.querySelector('.mentor-orbbox'); return [b.dataset.mood, b.querySelector('svg').getAttribute('class')]; }"
BUTTON = "() => document.querySelector('#mentor-button svg').getAttribute('class')"

def main():
    src = t.read("mentor-looks.js")
    print("--- 1. The looks file ---")
    with sync_playwright() as p:
        browser = p.chromium.launch()
        ctx = browser.new_context(viewport={"width": 390, "height": 844}, service_workers="block")
        page = ctx.new_page()
        errors = []
        page.on("pageerror", lambda x: errors.append(str(x)))
        fresh(page)
        shape = page.evaluate("() => Object.fromEntries(Object.entries(MENTOR_LOOKS).map(([k, v]) => [k, Object.keys(v)]))")
        check("three looks, each with all five states", sorted(shape) == sorted(LOOKS) and all(sorted(v) == sorted(STATES) for v in shape.values()), shape)
        classes = set(c for m in re.findall(r"class='([^']+)'", src) for c in m.split()) | set(re.findall(r"\.([a-zA-Z][\w-]*)", src.split("MENTOR_LOOKS_CSS")[-1]))
        check("every class name starts ml-", classes and all(c.startswith("ml-") for c in classes), sorted(c for c in classes if not c.startswith("ml-")))
        check("colours only from --mentor names: no hex, rgb or hsl", not re.search(r"#[0-9a-fA-F]{3,6}\b|rgba?\(|hsla?\(", src)
              and all(v.startswith("--mentor-") for v in re.findall(r"var\((--[\w-]+)", src)))
        check("no scripts or event attributes inside the drawings", not re.search(r"<script|\son[a-z]+\s*=", src, re.I))
        # James's tweaks (3 Nov, afternoon) were to round 6's drawings. U7 (round 7, James's own drawings) replaced them: Magical has no stars and
        # Grounded no hollow drop, and Finished in every look is a glow at the centre. So these two checks now follow round 7's behaviour.
        swirl = page.evaluate("""() => ['neutral','thinking','pleased','unsure','finished'].map(s => minifolioLook.svg('magical', s).querySelectorAll('.ml-swirl, .ml-dotline').length)""")
        check("Magical: the swirl lines round the dot are still gone", all(n == 0 for n in swirl), swirl)
        glow = page.evaluate("""() => { const box = document.createElement('div'); document.body.appendChild(box);
            const out = ['futuristic', 'magical', 'grounded'].map(l => ['neutral', 'finished'].map(s => { box.replaceChildren(minifolioLook.svg(l, s));
              const g = box.querySelector('.ml-fglow'); return !!g && getComputedStyle(g).display !== 'none'; }));
            box.remove(); return out; }""")
        check("Finished (and only Finished) shows the centre glow, in every look", glow == [[False, True]] * 3, glow)

        print("\n--- 2. The script ---")
        phrases = page.evaluate("() => MENTOR_PHRASES")
        lines = [(k, l) for k, v in phrases.items() for l in v]
        bad = [l for _, l in lines if len(l.split()) > 8 or "—" in l or "!" in l or re.search(r"[\U0001F300-\U0001FAFF☀-➿]", l)
               or re.search(r"\bthe Mentor\b|great question", l, re.I)]
        check("every line: eight words or fewer, no em dash, no exclamation mark, no emoji", lines and not bad, bad)
        check("the lists from James's script are there", all(len(phrases[k]) == n for k, n in
              {"greeting": 8, "picker": 3, "thinking": 4, "answer": 8, "unsure": 6, "didYouMean": 3, "thanks": 5, "returning": 5, "finished": 5}.items()))
        check("the old greetings stay first and E's line is the default unsure line",
              phrases["greeting"][:3] == ["How can I help?", "What are you painting?", "Ready when you are."] and phrases["unsure"][0] == "I do not know that yet.")
        runs = page.evaluate("() => ['greeting', 'thanks', 'finished', 'returning'].map(k => Array.from({ length: 30 }, () => mentorPhrase(MENTOR_PHRASES[k], '')))")
        check("a list never gives the same line twice in a row", all(a != b for run in runs for a, b in zip(run, run[1:])))

        print("\n--- 3. The setting ---")
        check("defaults to Futuristic: page, round button and the pressed choice", page.evaluate("() => document.documentElement.dataset.look") == "futuristic"
              and "ml-futuristic" in page.evaluate(BUTTON) and page.get_attribute('[data-mentor-look="futuristic"]', "aria-pressed") == "true")
        check("the round button is the start circle's centre and shows the neutral drawing", page.evaluate("() => document.body.classList.contains('launching')")
              and "ml-neutral" in page.evaluate(BUTTON))
        page.click('.tabs button[data-tab="guides"]')
        page.click('#more-seg button[data-page="settings"]')
        page.click("#card-fold-appearance-themes-button")   # FB3: Mentor look is a part of the Appearance and Themes fold now
        chips = page.locator("[data-mentor-look]")
        check("Settings has Mentor look with three plain choices, each with its own small orb", page.inner_text("#mentor-look-card h3") == "Mentor look"   # FB3: a part heading (h3) inside Appearance and Themes
              and chips.all_inner_texts() == ["Futuristic", "Magical", "Grounded"] and page.locator("[data-mentor-look] svg.ml-orb").count() == 3
              and all(b["height"] >= 44 for b in [chips.nth(i).bounding_box() for i in range(3)]))
        check("no helper sentence in the card", page.locator("#mentor-look-card p").count() == 0)
        page.click('[data-mentor-look="magical"]')
        saved = page.evaluate("() => JSON.parse(localStorage.getItem('shades-of-grey-settings')).mentorLook")
        check("choosing Magical saves it and changes the round button at once", saved == "magical" and "ml-magical" in page.evaluate(BUTTON)
              and page.get_attribute('[data-mentor-look="magical"]', "aria-pressed") == "true", (saved, page.evaluate(BUTTON)))
        held = []
        page.route("**/app.js*", lambda r: held.append(r))
        page.goto(t.URL, wait_until="commit")
        page.wait_for_function("() => !!document.querySelector('#mentor-button svg')")
        for _ in range(200):
            if held:
                break
            page.wait_for_timeout(50)
        pre = page.evaluate("() => [typeof settings, document.documentElement.dataset.look, document.querySelector('#mentor-button svg').getAttribute('class'), !!document.getElementById('ml-css')]")
        check("after a reload, the look is on the page before app.js runs (button drawing and styles)", pre[0] == "undefined" and pre[1] == "magical" and "ml-magical" in pre[2] and pre[3], pre)
        for r in held:
            r.continue_()
        page.unroute("**/app.js*")
        page.wait_for_function("() => typeof settings === 'object'")
        check("and the app keeps it", page.evaluate("() => currentMentorLook()") == "magical")
        backup = page.evaluate("() => backupData()")
        check("the look is not in backups (like Shop links)", "mentorLook" not in backup)
        page.set_input_files("#restore-file", files=[{"name": "b.json", "mimeType": "application/json", "buffer": json.dumps(dict(backup, theme="parchment")).encode()}])
        page.wait_for_timeout(400)
        if page.query_selector('.dialog button:has-text("Yes")'):
            page.click('.dialog button:has-text("Yes")')
        page.wait_for_function("() => JSON.parse(localStorage.getItem('shades-of-grey-settings')).theme === 'parchment'", timeout=5000)
        check("restoring a backup keeps your look", page.evaluate("() => [settings.mentorLook, document.documentElement.dataset.look]") == ["magical", "magical"])
        page.evaluate("() => { settings.mentorLook = 'sparkly'; applyMentorLook(); }")
        check("an unknown look counts as Futuristic", page.evaluate("() => [currentMentorLook(), document.documentElement.dataset.look]") == ["futuristic", "futuristic"]
              and "ml-futuristic" in page.evaluate(BUTTON))

        print("\n--- 4. Moods in the window ---")
        fresh(page)
        for look in LOOKS:
            # the same page each time: the look is switched and Mentor starts afresh, as on a new load (its notes not yet read)
            page.evaluate("(l) => { settings.mentorLook = l; applyMentorLook(); mentorWarm = false; mentorClear(); }", look)
            # U7: Thinking lasts about 0.4 s from the end of the opening move, and reading it straight after the move left only a few ms to spare
            # (round 7's bigger drawings made it miss often on a busy machine). So the first mood the orb takes after opening is recorded as it happens.
            page.evaluate("""() => { window.__moods = []; window.__moodWatch && window.__moodWatch.disconnect();
                window.__moodWatch = new MutationObserver(() => { const b = document.querySelector('.mentor-orbbox');
                  if (b && b.dataset.mood) window.__moods.push([b.dataset.mood, b.querySelector('svg').getAttribute('class')]); });
                window.__moodWatch.observe(document.body, { subtree: true, attributes: true, attributeFilter: ['data-mood'] }); }""")
            open_window(page)
            page.wait_for_function("() => window.__moods.length > 0", timeout=6000)
            seen = {"open": page.evaluate("() => { window.__moodWatch.disconnect(); return window.__moods[0]; }")}
            page.wait_for_function("() => document.querySelector('.mentor-orbbox').dataset.mood === 'neutral'", timeout=6000)
            seen["ready"] = page.evaluate(MOOD)
            # U7: round 7 has no stars; the window-only motion is checked on the look's own moving parts (Magical: the stone ring and the crystals)
            tw = page.evaluate("""() => { const moving = sel => [...document.querySelectorAll(sel)].some(e => e.getAnimations().some(a => a.playState === 'running'));
                return [!!document.querySelector('#mentor-button .ml-magical'), moving('.mentor-orbbox .ml-orbit, .mentor-orbbox [class*="ml-c"]'),
                        moving('#mentor-button *')]; }""")
            ask(page, "how do I thin paint"); seen["clear"] = page.evaluate(MOOD)
            size0 = page.locator(".mentor-orbbox").bounding_box()
            ask(page, "basecaot tips"); seen["dym"] = page.evaluate(MOOD)
            size1 = page.locator(".mentor-orbbox").bounding_box()
            ask(page, "asdf qwerty"); seen["none"] = page.evaluate(MOOD)
            first_none = page.locator(".mentor-lead").last.inner_text()
            ask(page, "zzqx qwerty"); second_none = page.locator(".mentor-lead").last.inner_text()
            ask(page, "thanks"); seen["thanks"] = page.evaluate(MOOD); thanks_line = page.locator(".mentor-lead").last.inner_text()
            ask(page, "bye"); seen["bye"] = page.evaluate(MOOD); bye_line = page.locator(".mentor-lead").last.inner_text()
            button = page.evaluate(BUTTON)
            want = {"open": "thinking", "ready": "neutral", "clear": "pleased", "dym": "unsure", "none": "unsure", "thanks": "finished", "bye": "finished"}
            check(f"{look}: Thinking while getting ready, then neutral; Pleased, Unsure (Did you mean and no answer) and Finished (thanks, bye)",
                  all(seen[k][0] == v and f"ml-{v}" in seen[k][1] and f"ml-{look}" in seen[k][1] for k, v in want.items()), seen)
            check(f"{look}: the round button never shows a mood", "ml-neutral" in button and f"ml-{look}" in button, button)
            if look == "magical":
                check("Magical: its parts move in the window at rest; the round button never moves", tw == [True, True, False], tw)
            if look == "futuristic":
                check("the orb's box keeps its size when the mood changes", size1 and size0 and abs(size0["width"] - size1["width"]) < 1 and abs(size0["height"] - size1["height"]) < 1, (size0, size1))
                check("no answer twice in a row: E's line first, then a different unsure line", first_none == "I do not know that yet."
                      and second_none != first_none and second_none in phrases["unsure"], (first_none, second_none))
                check("thanks gets a thanks line, a goodbye a finished line", thanks_line in phrases["thanks"] and bye_line in phrases["finished"], (thanks_line, bye_line))
                check("a question that only mentions thanks is still answered", not page.evaluate("() => mentorSignOff('thanks, how do I thin paint')")
                      and page.evaluate("() => [mentorSignOff('Thanks a lot!'), mentorSignOff(\"that's all\"), mentorSignOff('cheers mate'), mentorSignOff('ok')]") == ["thanks", "finished", "thanks", ""])
                page.wait_for_function("() => document.querySelector('.mentor-orbbox').dataset.mood === 'neutral'", timeout=5000)
                check("Finished goes back to neutral after a short pause", "ml-neutral" in page.evaluate(MOOD)[1])
                page.keyboard.press("Escape")
                page.wait_for_function("() => !document.querySelector('.mentor-backdrop')")
                page.evaluate("() => { mentorLastAt = Date.now() - 31 * 60000; }")
                open_window(page)
                greet = page.inner_text(".mentor-greeting")
                check("back after a long gap: a returning line", greet in phrases["returning"], greet)
            page.keyboard.press("Escape")
            page.wait_for_function("() => !document.querySelector('.mentor-backdrop')")
        check("each look's five states are different drawings", page.evaluate(
            "() => Object.values(MENTOR_LOOKS).every(l => new Set(Object.values(l)).size === 5)"))

        print("\n--- 5. Reduce motion ---")
        rm = browser.new_context(viewport={"width": 390, "height": 844}, service_workers="block", reduced_motion="reduce")
        rp = rm.new_page()
        rp.on("pageerror", lambda x: errors.append(str(x)))
        fresh(rp)
        open_window(rp)
        check("the window's orb does not move while Mentor gets ready", rp.evaluate(MOOD)[0] == "thinking"
              and rp.evaluate("() => document.querySelector('.mentor-orbbox').getAnimations({ subtree: true }).length") == 0)
        rp.wait_for_function("() => document.querySelector('.mentor-orbbox').dataset.mood === 'neutral'", timeout=6000)
        # U7: round 7 draws every state from one drawing (the state is a class on it), so the shapes are compared as they look on screen, not as markup
        shapes = []
        for q in ("how do I thin paint", "asdf qwerty", "thanks"):
            ask(rp, q)
            shapes.append([rp.evaluate("() => document.querySelector('.mentor-orbbox').getAnimations({ subtree: true }).length"),
                           rp.locator(".mentor-orbbox").screenshot()])
        check("Pleased, Unsure and Finished: nothing moves, and each looks different", all(a == 0 for a, _ in shapes) and len({s for _, s in shapes}) == 3)
        still = rp.evaluate("""() => { settings.mentorLook = 'magical'; applyMentorLook(); return ['pleased', 'unsure'].map(m => { mentorMood(m);
            const box = document.querySelector('.mentor-orbbox');
            return [box.getAnimations({ subtree: true }).length, +getComputedStyle(box.querySelector('.ml-cg')).opacity]; }); }""")
        check("Magical with reduce motion: still, and its crystals brighter for Pleased than Unsure",
              all(x[0] == 0 for x in still) and still[0][1] > still[1][1] > 0, still)
        rm.close()

        print("\n--- 6. Colours and sizes ---")
        # U7 reversed this (James, 3 Nov): the avatars take the theme's colours only. app.js still sets the colour set's five colours
        # (--mentor-s0 to --mentor-s4, which round 6 in mentor-looks-r6.js reads), but the ring no longer follows them.
        RING = "() => [0, 1, 2, 3, 4].map(i => getComputedStyle(document.querySelector('#mentor-button .ml-segs .ml-k' + i)).stroke)"
        page.evaluate("() => { settings.mentorLook = 'futuristic'; applyMentorLook(); }")
        ring0 = page.evaluate(RING)
        page.evaluate("() => { settings.palette = 'greyscale'; applyPalette('greyscale'); }")
        got = page.evaluate("() => [stageColours('greyscale', 5), [0, 1, 2, 3, 4].map(i => getComputedStyle(document.documentElement).getPropertyValue('--mentor-s' + i).trim())]")
        check("the colour set's five colours are still set, but the ring segments keep the theme's colours", got[0] == got[1] and page.evaluate(RING) == ring0, (got, ring0))
        for (w, h, mode, theme, look) in ((390, 844, "dark", "parchment", "magical"), (360, 640, "light", "forge", "grounded"),
                                          (320, 568, "light", "bench", "futuristic")):
            page.set_viewport_size({"width": w, "height": h})
            # the same page: the theme, mode and look are changed as Settings would, then the title button goes back to the start circle
            page.evaluate("""([th, m, l]) => { Object.assign(settings, { theme: th, appearance: m, mentorLook: l }); applyPalette(settings.palette); applyMentorLook();
                if (!document.body.classList.contains('launching')) document.getElementById('home-button').click(); }""", [theme, mode, look])
            page.wait_for_function("() => document.body.classList.contains('launching') && !document.querySelector('.mo-ring, .mo-ghost, .mo-tr')")
            css_w = "() => parseFloat(getComputedStyle(document.querySelector('#mentor-button svg')).width)"   # its own size, before the circle's scaling
            centre = {"width": page.evaluate(css_w)}
            page.click('.tabs button[data-tab="dashboard"]')
            t.quiet(page)
            bar = {"width": page.evaluate(css_w)}
            open_window(page)
            page.wait_for_function("() => document.querySelector('.mentor-orbbox').dataset.mood === 'neutral'", timeout=6000)
            ask(page, "asdf qwerty")
            orb = page.locator(".mentor-orbbox svg").bounding_box()
            sideways = page.evaluate("() => document.documentElement.scrollWidth > document.documentElement.clientWidth")
            check(f"{w}x{h} {mode} {theme} {look}: start circle orb 64 px, bar orb 50 px, window orb shown, no sideways scroll",
                  round(centre["width"]) == 64 and round(bar["width"]) == 50 and orb and orb["width"] >= 36 and not sideways, (centre, bar, orb, sideways))
            page.keyboard.press("Escape")
        check("no page errors", not errors, errors[:3])
        browser.close()
    print(f"\n{sum(results)}/{len(results)} checks passed")
    return 0 if all(results) else 1

if __name__ == "__main__":
    sys.exit(main())
