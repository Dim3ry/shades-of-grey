"""Test helper (v21.7): questions used to be the browser's own confirm() and prompt() boxes, which the
tests answered with page.on("dialog", ...). They are now the app's own question box (#dialog-backdrop,
with #dialog-message, #dialog-input, #dialog-yes and #dialog-no).

DialogAnswers(page) watches for that box and answers it by TAPPING ITS BUTTONS (a real click on
#dialog-yes or #dialog-no), the moment it opens, inside the page, so the code that asked has
already carried on by the time the test's own click returns. It replaces:

    page.on("dialog", lambda d: d.accept())            ->  DialogAnswers(page)
    answer = {"accept": True} ... d.dismiss()          ->  answers = DialogAnswers(page); answers.yes = False

    answers.yes = False      # from now on, tap No (or Cancel on a "type a name" box)
    answers.text = "Hull"    # what to type into a "type a name" box before tapping OK
    answers.seen             # a list of (kind, message) for every question shown ("yesno", "text", "show")
    answers.messages         # just the messages
    answers.clear()          # forget what has been seen

`sink`, if given, is called with each question's message (like attach_notices does for notices), so
an old check like `any("Discard" in d for d in dialogs)` still works if sink is `dialogs.append`.
Set the answer BEFORE the page loads or after: it survives reloads of the same page.

Tests of the box itself (test_v21_7) do NOT use this: they tap the buttons with real clicks."""
import json

WATCH_JS = """
(() => {
  const start = () => {
    const back = document.getElementById("dialog-backdrop");
    if (!back) return;
    let handled = false;
    const check = () => {
      const open = !back.classList.contains("hidden");
      if (!open) { handled = false; return; }
      if (handled) return;
      handled = true;
      const cfg = window.__dlgConfig || { yes: true, text: "" };
      const input = document.getElementById("dialog-input");
      const kind = !input.classList.contains("hidden") ? "text"
        : !document.getElementById("dialog-area").classList.contains("hidden") ? "show" : "yesno";
      const message = document.getElementById("dialog-message").textContent;
      window.__dlgSeen = (window.__dlgSeen || []);
      window.__dlgSeen.push([kind, message]);
      if (window.__dialogSeen) window.__dialogSeen(kind, message);
      if (kind === "text") input.value = cfg.text;
      document.getElementById(cfg.yes ? "dialog-yes" : "dialog-no").click();
      // The answer may have opened the next question straight away: look again.
      handled = false;
      check();
    };
    new MutationObserver(check).observe(back, { attributes: true, attributeFilter: ["class"] });
  };
  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", start);
  else start();
})();
"""


class DialogAnswers:
    def __init__(self, page, sink=None, yes=True, text=""):
        self.page = page
        self._yes = yes
        self._text = text
        self._seen = []
        self._sink = sink
        page.expose_function("__dialogSeen", self._on_seen)
        page.add_init_script(WATCH_JS)
        self._push()

    def _on_seen(self, kind, message):
        self._seen.append((kind, message))
        if self._sink:
            self._sink(message)

    def _push(self):
        cfg = json.dumps({"yes": self._yes, "text": self._text})
        self.page.add_init_script(f"window.__dlgConfig = {cfg};")   # later scripts win, so reloads keep the latest
        if self.page.url not in ("", "about:blank"):
            try:
                self.page.evaluate(f"() => {{ window.__dlgConfig = {cfg}; }}")
            except Exception:
                pass

    @property
    def yes(self):
        return self._yes

    @yes.setter
    def yes(self, value):
        self._yes = bool(value)
        self._push()

    @property
    def text(self):
        return self._text

    @text.setter
    def text(self, value):
        self._text = value
        self._push()

    def _flush(self):
        # Let any report from the page that is still on its way arrive before looking.
        try:
            self.page.evaluate("() => 0")
        except Exception:
            pass

    @property
    def seen(self):
        self._flush()
        return self._seen

    @property
    def messages(self):
        return [m for _, m in self.seen]

    def clear(self):
        self._flush()
        self._seen.clear()
