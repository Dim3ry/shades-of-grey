"""LC1 tests for Minifolio (licence notices for Leptonica and libtiff inside the pot-label reader's engine). New behaviour only:
1. The two licence files exist, are not empty and carry the expected wording.
2. They are named in ocr/README.md.
3. The Credits page lists both under Pot-label reader, linking to the files, and the links open the files.
4. The rows fit 390 and 360 px with no sideways scroll, links 44 px or taller.
Run all tests with `python3 tests/run_all.py`, or serve the repo folder and run this file on its own."""
import os, sys
from playwright.sync_api import sync_playwright

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import test_v31 as t
from launch_helpers import wait_settled

results = []

def check(name, ok, detail=""):
    results.append(bool(ok))
    print(("PASS " if ok else "FAIL ") + name + ("" if ok else f"  -> {detail}"))

def go(page, w, h):
    page.set_viewport_size({"width": w, "height": h})
    t.load(page, settings={"examplesChecked": True}, launch=True)
    page.click('.tabs button[data-tab="guides"]')
    wait_settled(page)
    page.click('#more-seg button[data-page="about"]')
    wait_settled(page)
    page.evaluate("() => showTab('credits')")   # CR3: the link on About is gone
    wait_settled(page)
    page.evaluate("() => document.querySelectorAll('#view-credits details').forEach(d => d.open = true)")   # CR3: sections start closed

def main():
    errors = []
    lept, tiff = t.read("ocr/LICENSE-leptonica.txt"), t.read("ocr/LICENSE-libtiff.txt")
    print("\n--- 1. The files ---")
    check("Leptonica licence is not empty and starts with its copyright line", len(lept) > 500 and "Copyright (C) 2001-2020 Leptonica" in lept[:200])
    check("Leptonica licence has the redistribution conditions and disclaimer", "Redistributions in binary form must reproduce" in lept and "ANY EXPRESS OR IMPLIED WARRANTIES" in lept)
    check("libtiff licence is not empty and starts with the Sam Leffler copyright", len(tiff) > 500 and tiff.startswith("Copyright (c) 1988-1997 Sam Leffler"))
    check("libtiff licence has the permission notice and the warranty line", "Permission to use, copy, modify, distribute, and sell" in tiff and "PROVIDED \"AS-IS\" AND WITHOUT WARRANTY" in tiff)

    print("\n--- 2. README ---")
    readme = t.read("ocr/README.md")   # the offline file list itself is covered by the plumbing test, not here
    check("ocr/README.md names both libraries and links both files", "LICENSE-leptonica.txt" in readme and "LICENSE-libtiff.txt" in readme and "Leptonica" in readme and "libtiff" in readme)

    print("\n--- 3. Credits ---")
    with sync_playwright() as p:
        browser = p.chromium.launch()
        ctx = browser.new_context(viewport={"width": 390, "height": 844}, service_workers="block", reduced_motion="reduce")
        page = ctx.new_page()
        page.on("pageerror", lambda x: errors.append(str(x)))
        go(page, 390, 844)
        rows = page.evaluate("() => [...document.querySelectorAll('#credits-reader li')].map(li => [li.querySelector('strong').textContent.trim(), li.querySelector('a').getAttribute('href')])")
        names = [r[0] for r in rows]
        check("Pot-label reader lists Tesseract, Leptonica and libtiff in that order", names == ["Tesseract engine and English data", "Leptonica", "libtiff"], rows)
        hrefs = dict(rows)
        check("the new links point at the two licence files", hrefs.get("Leptonica") == "ocr/LICENSE-leptonica.txt" and hrefs.get("libtiff") == "ocr/LICENSE-libtiff.txt", hrefs)
        base = page.url.split("#")[0].rsplit("/", 1)[0] + "/"
        for name, href, word in (("Leptonica", "ocr/LICENSE-leptonica.txt", "Leptonica"), ("libtiff", "ocr/LICENSE-libtiff.txt", "Sam Leffler")):
            r = page.request.get(base + href)
            check(f"the {name} link opens the licence text", r.ok and word in r.text(), r.status)
        check("links open in a new tab safely", page.evaluate("() => [...document.querySelectorAll('#credits-reader a')].every(a => a.target === '_blank' && a.rel.includes('noopener') && a.rel.includes('noreferrer'))"))

        print("\n--- 4. Fit ---")
        for w, h in ((390, 844), (360, 640)):
            go(page, w, h)
            m = page.evaluate("() => ({ side: document.documentElement.scrollWidth > document.documentElement.clientWidth, tall: [...document.querySelectorAll('#credits-reader a')].map(a => a.getBoundingClientRect().height) })")
            check(f"{w} px: no sideways scroll and every reader link is 44 px or taller", not m["side"] and all(x >= 44 for x in m["tall"]), m)
        ctx.close(); browser.close()
    check("no page errors", not errors, errors)
    print(f"\n{sum(results)}/{len(results)} passed")
    sys.exit(0 if all(results) else 1)

if __name__ == "__main__":
    main()
