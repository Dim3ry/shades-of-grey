// ===== early.js: choose the theme and light or dark BEFORE the page is drawn =====
// v21.4: this used to sit inside index.html's <head>. It moved into its own file so the
// security policy can refuse ANY code written inside the page (see the CSP note in index.html).
// It's loaded near the top of the page, before the styles, so the page is marked light (if
// that's your setting) before anything appears. No dark flash. The full version
// (applyAppearance in app.js) takes over once the app starts.
// v47: it also puts your theme on the page (data-t) with the mode (data-m: dark or light), and
// sets the phone's top-bar colour to that theme's page colour, so a theme doesn't flash Classic first.
// The page colours below must match the THEMES section of index.html (a test checks).
try {
  const PAGE_COLOURS = {
    classic: { dark: "#0b1220", light: "#e9eff6" },
    blueprint: { dark: "#0c2c4f", light: "#f1f4f8" },
    parchment: { dark: "#17120e", light: "#d8c59a" },
    forge: { dark: "#0e0e10", light: "#cfcdc6" },
    bench: { dark: "#111815", light: "#cfe0d4" },
    rulebook: { dark: "#181810", light: "#c8c6a9" },
  };
  const saved = JSON.parse(localStorage.getItem("shades-of-grey-settings") || "{}") || {};
  const choice = saved.appearance;
  const light = choice === "light" ||
    (choice === "auto" && window.matchMedia && window.matchMedia("(prefers-color-scheme: light)").matches);
  const root = document.documentElement;
  if (light) root.dataset.appearance = "light";
  const theme = Object.prototype.hasOwnProperty.call(PAGE_COLOURS, saved.theme) ? saved.theme : "classic";
  root.dataset.t = theme;
  root.dataset.m = light ? "light" : "dark";
  const bar = document.querySelector('meta[name="theme-color"]');
  if (bar) bar.setAttribute("content", PAGE_COLOURS[theme][light ? "light" : "dark"]);
} catch (ignored) {}
