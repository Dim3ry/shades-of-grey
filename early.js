// ===== early.js: choose light or dark BEFORE the page is drawn =====
// v21.4: this used to sit inside index.html's <head>. It moved into its own file so the
// security policy can refuse ANY code written inside the page (see the CSP note in index.html).
// It's loaded near the top of the page, before the styles, so the page is marked light (if
// that's your setting) before anything appears. No dark flash. The full version
// (applyAppearance in app.js) takes over once the app starts.
try {
  const saved = JSON.parse(localStorage.getItem("shades-of-grey-settings") || "{}") || {};
  const choice = saved.appearance;
  const light = choice === "light" ||
    (choice === "auto" && window.matchMedia && window.matchMedia("(prefers-color-scheme: light)").matches);
  if (light) document.documentElement.dataset.appearance = "light";
} catch (ignored) {}
