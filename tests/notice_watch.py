"""Test helper (v21.6): notices used to be the browser's own alert() boxes, which the tests caught
with page.on("dialog"). They are now the app's own message (#toast, marked data-kind="notice").
attach_notices(page, sink) calls sink(text) for every notice the app shows, so an old check like
`any("full" in d for d in dialogs)` keeps working when sink is `dialogs.append`.
Only notices are reported: Undo messages and the like are ignored."""

WATCH_JS = """
(() => {
  const start = () => {
    const text = document.getElementById("toast-text");
    const toast = document.getElementById("toast");
    if (!text || !toast) return;
    new MutationObserver(() => {
      if (toast.dataset.kind === "notice" && window.__noticeSeen) window.__noticeSeen(text.textContent);
    }).observe(text, { childList: true, characterData: true, subtree: true });
  };
  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", start);
  else start();
})();
"""

def attach_notices(page, sink):
    page.expose_function("__noticeSeen", lambda text: sink(text))
    page.add_init_script(WATCH_JS)
