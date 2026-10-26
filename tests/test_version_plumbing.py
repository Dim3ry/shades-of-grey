"""Version plumbing for Minifolio: the ONE place that checks the version number and the files around it.

Why: old tests used to each check "the version is vNN or later", the script tags, sw.js, the Updates entry and so on, and a
version bump meant editing them. Now those checks live only here, written so a bump never needs an edit. A chunk's own test
covers only the chunk's new behaviour (see CLAUDE.md).

Checks:
1. The version: APP_VERSION is a plain vN and matches app.js, the heading shows it, sw.js VERSION matches.
2. index.html: every script tag carries ?v= with that number (counted from index.html, not a fixed six), the comments that
   name the number agree.
3. The Updates list: the newest entry is the current version, has a date, at least one line and no em dash; no version is
   listed twice; the list runs newest to oldest.
4. DATA_VERSION: the number in app.js, the one the app uses and the one in a backup all agree; saved settings carry it.
5. Files: every file index.html loads is listed in sw.js, every listed file exists, no outside host is cached.
6. The four storage names exist.
7. Security policy: one policy tag, before the first script, equal to the pinned copy in tests/csp_baseline.txt.
8. The label reader folder, the paint list licence, the CNAME rule and the ZAP workflow are still there.
9. schemes.js, detail-recipes.js and basing-tips.js are unchanged against origin/main (set CONTENT_CHANGE_OK=1 for a chunk
   whose prompt says to change them).
Run all tests with `python3 tests/run_all.py`, or serve the repo folder and run this file on its own."""
import json, os, re, subprocess, sys
from playwright.sync_api import sync_playwright

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import version_helpers as vh
import test_v31 as t   # load

ROOT = vh.ROOT
read = vh.read
results = []

def check(name, ok, detail=""):
    results.append(bool(ok))
    print(("PASS " if ok else "FAIL ") + name + ("" if ok else f"  -> {detail}"))

CONTENT_FILES = ("schemes.js", "detail-recipes.js", "basing-tips.js")


def main():
    app, html, sw = read("app.js"), read("index.html"), read("sw.js")
    version = vh.current()
    with sync_playwright() as p:
        browser = p.chromium.launch()
        ctx = browser.new_context(viewport={"width": 390, "height": 844}, service_workers="block")
        page = ctx.new_page()
        errors = []
        page.on("pageerror", lambda x: errors.append(str(x)))
        t.load(page)

        # ---------- 1. The version ----------
        print("\n--- 1. The version ---")
        check("APP_VERSION is a plain vN (digits and at most one dot)", re.fullmatch(r"v\d+(\.\d+)?", version), version)
        check("the app runs the version written in app.js", page.evaluate("APP_VERSION") == version, page.evaluate("APP_VERSION"))
        check("the version next to the title is that version", page.inner_text("#version-tag").strip() == version, page.inner_text("#version-tag"))
        m = re.search(r'const VERSION = "(v[^"]+)"', sw)
        check("sw.js VERSION matches", m and m.group(1) == version, m and m.group(1))

        # ---------- 2. index.html ----------
        print("\n--- 2. Script tags and comments ---")
        scripts = re.findall(r'<script\b[^>]*\bsrc="([^"]+)"', html)
        local = [s for s in scripts if not re.match(r"https?:", s)]
        check("index.html loads at least one script, all from this site", scripts and len(local) == len(scripts), scripts)
        bad = [s for s in local if not s.endswith("?v=" + version[1:])]
        check("every script tag carries ?v= with the current number", local and not bad, bad)
        check("the comments that name the number agree",
              f'The "?v={version[1:]}" makes' in html and f'e.g. "app.js?v={version[1:]}"' in app)

        # ---------- 3. The Updates list ----------
        print("\n--- 3. The Updates list ---")
        entries = page.evaluate("CHANGELOG")
        names = [e["version"] for e in entries]
        top = entries[0]
        check("the newest Updates entry is the current version", top["version"] == version, top["version"])
        check("the newest entry has a date", bool(re.fullmatch(r"\d{1,2} [A-Z][a-z]{2} \d{4}", top.get("date", ""))), top.get("date"))
        check("the newest entry has at least one line", len(top["changes"]) >= 1, top)
        check("no em dash in the newest entry", "—" not in json.dumps(top, ensure_ascii=False), top)
        check("no version is listed twice", len(names) == len(set(names)), names)
        check("the list runs from newest to oldest", all(vh.parse(a) > vh.parse(b) for a, b in zip(names, names[1:])), names)

        # ---------- 4. DATA_VERSION ----------
        print("\n--- 4. DATA_VERSION ---")
        dv = vh.data_version()
        check("DATA_VERSION in app.js is a whole number of 1 or more", isinstance(dv, int) and dv >= 1, dv)
        check("the app uses that DATA_VERSION", page.evaluate("DATA_VERSION") == dv, page.evaluate("DATA_VERSION"))
        check("a backup carries it", page.evaluate("backupData().dataVersion") == dv)
        check("saved settings carry it",
              page.evaluate("() => JSON.parse(localStorage.getItem('shades-of-grey-settings') || '{}').dataVersion") == dv)

        # ---------- 5. Files ----------
        print("\n--- 5. Files ---")
        files_block = re.search(r"const APP_FILES = \[(.*?)\];", sw, re.S)
        listed = re.findall(r'"\./([^"]*)"', files_block.group(1)) if files_block else []
        loaded = {s.split("?")[0] for s in local}
        for href in re.findall(r'<link\b[^>]*\bhref="([^"#]+)"', html):
            if not re.match(r"https?:|data:", href) and not href.endswith(".css"): loaded.add(href.split("?")[0])
        listed_clean = {x for x in listed if x}
        missing = sorted(f for f in loaded if f not in listed_clean and f != "index.html")
        check("every file index.html loads is listed in sw.js", not missing, missing)
        gone = sorted(f for f in listed_clean if not os.path.exists(os.path.join(ROOT, f)))
        check("every file sw.js lists exists", not gone, gone)
        check("no outside host is cached or named in sw.js", not re.search(r"https?://", sw), re.findall(r"https?://\S+", sw)[:3])
        check("sw.js adds the version tag to the files that carry ?v=",
              all(f'"./{f}" + CODE_TAG' in sw for f in {s.split("?")[0] for s in local}), sorted(loaded))

        # ---------- 6. Storage names ----------
        print("\n--- 6. Storage names ---")
        for const, key in (("STORAGE_KEY", "mini-tracker-models"), ("SETTINGS_KEY", "shades-of-grey-settings"),
                           ("RECIPES_KEY", "shades-of-grey-recipes"), ("DRAFTS_KEY", "shades-of-grey-drafts")):
            check(f"storage name {key} is unchanged", f'{const} = "{key}"' in app)

        # ---------- 7. Security policy ----------
        print("\n--- 7. Security policy ---")
        tags = re.findall(r'<meta http-equiv="Content-Security-Policy" content="([^"]+)"', html)
        check("exactly one security policy tag", len(tags) == 1, len(tags))
        check("it comes before the first script", 0 < html.find('Content-Security-Policy" content') < html.find("<script"))
        pinned = open(os.path.join(vh.HERE, "csp_baseline.txt"), encoding="utf-8").read().strip()
        check("the policy equals the pinned copy in tests/csp_baseline.txt (change both on purpose)", tags == [pinned], tags)

        # ---------- 8. Things that must stay ----------
        print("\n--- 8. Things that must stay ---")
        check("the label reader folder is there", all(os.path.exists(os.path.join(ROOT, "ocr", f)) for f in
              ["ocr-worker.js", "eng.traineddata", "tesseract-core-simd-lstm.wasm", "tesseract-core-lstm.wasm"]))
        check("LICENSE-paint-list.txt is there", os.path.exists(os.path.join(ROOT, "LICENSE-paint-list.txt")))
        cname = os.path.join(ROOT, "CNAME")
        check("CNAME, if there, says minifolio.app (hosting moved to Cloudflare)", not os.path.exists(cname) or open(cname).read().strip() == "minifolio.app")
        zap = os.path.join(ROOT, ".github", "workflows", "zap-scan.yml")
        zap_text = open(zap, encoding="utf-8").read() if os.path.exists(zap) else ""
        check("the ZAP workflow is there, still the passive baseline scan", "action-baseline" in zap_text and "action-full-scan" not in zap_text)

        # ---------- 9. Content files ----------
        print("\n--- 9. Content files ---")
        if os.environ.get("CONTENT_CHANGE_OK") == "1":
            print("SKIP: CONTENT_CHANGE_OK=1, this chunk changes recipe, scheme or tip content on purpose")
        else:
            changed, asked = [], 0
            for base in ("HEAD", "origin/main"):
                out = subprocess.run(["git", "diff", "--name-only", base, "--", *CONTENT_FILES], cwd=ROOT, capture_output=True, text=True)
                if out.returncode == 0:
                    asked += 1
                    changed += out.stdout.split()
            check("schemes.js, detail-recipes.js and basing-tips.js are unchanged", asked and not changed, changed or "git could not be asked")

        check("no page errors", not errors, errors)
        browser.close()

    print(f"\n{sum(results)}/{len(results)} checks passed")
    sys.exit(0 if all(results) else 1)

if __name__ == "__main__":
    main()
