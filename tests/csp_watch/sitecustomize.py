"""v21.2: a "CSP watcher" for the whole test suite.

run_all.py puts this folder first on PYTHONPATH, and Python loads any file called sitecustomize.py
automatically before a test starts. So EVERY test file (old and new) gets this, without changing
any of them.

What it does: every browser page a test opens gets a listener on the browser's console. If the
browser says it blocked something because of the Content Security Policy (the "Refused to ..."
messages), the message is written to the file named in SOG_CSP_LOG. run_all.py reads that file
after each test and counts anything there as a failure.

Deliberate checks (tests that try to load something forbidden on purpose, to prove the policy
works) put "csp-probe" in the address, and those are ignored here."""
import os

LOG = os.environ.get("SOG_CSP_LOG")

if LOG:
    try:
        from playwright.sync_api._generated import Browser, BrowserContext

        def _watch(page):
            def on_console(msg):
                text = msg.text
                # v21.4: a refused INLINE script has no address of its own, so the browser's message
                # can't carry the marker. Those tries run on a page opened as "index.html?csp-probe",
                # so the page's own address is checked too.
                try:
                    where = page.url
                except Exception:
                    where = ""
                if "Content Security Policy" in text and "csp-probe" not in text and "csp-probe" not in where:
                    with open(LOG, "a", encoding="utf-8") as f:
                        f.write(text.replace("\n", " ") + "\n")
            page.on("console", on_console)
            return page

        _browser_new_page = Browser.new_page
        _context_new_page = BrowserContext.new_page

        def browser_new_page(self, *args, **kwargs):
            return _watch(_browser_new_page(self, *args, **kwargs))

        def context_new_page(self, *args, **kwargs):
            return _watch(_context_new_page(self, *args, **kwargs))

        Browser.new_page = browser_new_page
        BrowserContext.new_page = context_new_page

        # T1: a page.goto sometimes fails with net::ERR_ABORTED when the machine is busy (the browser drops the load; nothing is wrong with
        # the app). Try again, up to 3 times in all. Any other error, and any address used for a deliberate probe, is raised straight away.
        from playwright.sync_api import Page

        _goto = Page.goto

        def goto_with_retry(self, url, *args, **kwargs):
            for attempt in range(3):
                try:
                    return _goto(self, url, *args, **kwargs)
                except Exception as error:
                    if "ERR_ABORTED" not in str(error) or "csp-probe" in str(url) or attempt == 2:
                        raise

        Page.goto = goto_with_retry
    except Exception as error:  # never stop a test from running just because the watcher failed
        with open(LOG, "a", encoding="utf-8") as f:
            f.write(f"WATCHER-NOT-LOADED {error}\n")
