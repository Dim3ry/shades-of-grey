"""Photo types accepted when restoring a backup (17 Oct 2026 safety tidy-up).

A full backup carries photos as text pictures ("data:image/jpeg;base64,..."). The app only ever
saves JPEG itself, so restore now accepts only JPEG, PNG and WebP. Anything else (an SVG drawing,
a web page, a GIF) is skipped. No version change: this is a small tightening, and it ships with
the next release.

Checks (using the app's own importPhotoFiles, in a real browser):
1. JPEG, PNG and WebP photos are all restored.
2. An SVG, an HTML page, a GIF and a plain-text "photo" are all skipped, and nothing is saved for them.
3. A good photo with an SVG as its thumbnail is still restored, and the saved thumbnail is a
   JPEG made from the full picture, never the SVG.
4. A photo with no thumbnail still works the old way (thumbnail made from the picture).
Run all tests with `python3 tests/run_all.py`, or serve the repo folder and run this file on its own."""
import os, sys
from playwright.sync_api import sync_playwright
from launch_helpers import leave_launch

PORT = os.environ.get("SOG_PORT", "8765")
URL = f"http://localhost:{PORT}/index.html"
results = []

# A real 1x1 picture, so the app can make a thumbnail from it when it has to.
PNG = "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8BQDwAEhQGAhKmMIQAAAABJRU5ErkJggg=="
# Stand-in bytes: the restore code stores these without opening them when a good thumbnail comes with them.
FAKE_JPEG = "data:image/jpeg;base64,AAAA"
FAKE_WEBP = "data:image/webp;base64,AAAA"
SVG = "data:image/svg+xml;base64,PHN2ZyB4bWxucz0naHR0cDovL3d3dy53My5vcmcvMjAwMC9zdmcnPjwvc3ZnPg=="
HTML = "data:text/html;base64,PGgxPmhpPC9oMT4="
GIF = "data:image/gif;base64,R0lGODlhAQABAAAAACw="
TEXT = "data:text/plain;base64,aGVsbG8="


def check(name, ok, detail=""):
    results.append(bool(ok))
    print(("PASS " if ok else "FAIL ") + name + ("" if ok else f"  -> {detail}"))


def main():
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page()
        errors = []
        page.on("pageerror", lambda e: errors.append(str(e)))
        page.goto(URL)
        page.wait_for_function("() => typeof APP_VERSION === 'string' && typeof importPhotoFiles === 'function'")
        leave_launch(page)   # U4b: tap through the start page

        files = {
            "t-jpeg": {"full": FAKE_JPEG, "thumb": FAKE_JPEG},
            "t-png": {"full": PNG, "thumb": PNG},
            "t-webp": {"full": FAKE_WEBP, "thumb": FAKE_WEBP},
            "t-svg": {"full": SVG, "thumb": SVG},
            "t-html": {"full": HTML, "thumb": HTML},
            "t-gif": {"full": GIF, "thumb": GIF},
            "t-text": {"full": TEXT, "thumb": TEXT},
        }
        count = page.evaluate("files => importPhotoFiles(files)", files)
        check("three photos restored (JPEG, PNG, WebP) and four skipped", count == 3, count)
        stored = page.evaluate("""async () => {
            const out = {};
            for (const id of ["t-jpeg", "t-png", "t-webp", "t-svg", "t-html", "t-gif", "t-text"]) {
                const r = await getPhoto(id);
                out[id] = r ? { full: r.full.type, thumb: r.thumb.type } : null;
            }
            return out;
        }""")
        check("JPEG, PNG and WebP are in the photo store, with the right types",
              stored["t-jpeg"] == {"full": "image/jpeg", "thumb": "image/jpeg"}
              and stored["t-png"] == {"full": "image/png", "thumb": "image/png"}
              and stored["t-webp"] == {"full": "image/webp", "thumb": "image/webp"}, stored)
        check("the SVG, HTML page, GIF and text 'photos' left nothing behind",
              all(stored[k] is None for k in ("t-svg", "t-html", "t-gif", "t-text")), stored)

        count = page.evaluate("files => importPhotoFiles(files)",
                              {"t-mixed": {"full": PNG, "thumb": SVG}, "t-nothumb": {"full": PNG}})
        types = page.evaluate("""async () => {
            const out = {};
            for (const id of ["t-mixed", "t-nothumb"]) {
                const r = await getPhoto(id);
                out[id] = r ? { full: r.full.type, thumb: r.thumb.type } : null;
            }
            return out;
        }""")
        check("a good photo with an SVG thumbnail, and one with no thumbnail, are both restored", count == 2, count)
        check("their saved thumbnails are JPEGs made from the picture, never the SVG",
              all(types[k] and types[k]["thumb"] == "image/jpeg" and types[k]["full"] == "image/png"
                  for k in ("t-mixed", "t-nothumb")), types)
        check("no page errors", not errors, errors[:5])
        browser.close()

    print(f"\n{sum(results)} of {len(results)} checks passed")
    sys.exit(0 if all(results) else 1)


if __name__ == "__main__":
    main()
