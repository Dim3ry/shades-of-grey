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
    parchment: { dark: "#17120e", light: "#d8c59a" },
    forge: { dark: "#0d0f11", light: "#cdd1d5" },
    bench: { dark: "#20251f", light: "#e0e4d8" },
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

// U6b: THE MENTOR LOOK, also before the page is drawn. mentor-looks.js (loaded just before this file) holds James's drawings: MENTOR_LOOKS[look][state]
// and their styles, MENTOR_LOOKS_CSS. The choice is settings.mentorLook ("magical" or "grounded"; missing means Futuristic, the default). This puts
// data-look on the page (the CSS uses it, see "LR1:" in index.html), the styles in one <style>, and, for a look that is not Futuristic, that look's
// drawing in the round button as soon as the page has the button (index.html holds the Futuristic one). minifolioLook.svg is the one place a
// drawing's text becomes part of the page; app.js uses it too. The drawings are the app's own fixed data, never anything typed or imported.
try {
  const root = document.documentElement;
  const haveLooks = typeof MENTOR_LOOKS === "object" && MENTOR_LOOKS !== null;
  window.minifolioLook = {
    known: (look) => haveLooks && typeof look === "string" && Object.prototype.hasOwnProperty.call(MENTOR_LOOKS, look),
    styles() {
      if (document.getElementById("ml-css") || typeof MENTOR_LOOKS_CSS !== "string") return;
      const style = document.createElement("style");
      style.id = "ml-css";
      style.textContent = MENTOR_LOOKS_CSS;
      (document.head || root).appendChild(style);
    },
    svg(look, state) {
      const box = document.createElement("div");
      box.innerHTML = MENTOR_LOOKS[look][state];
      return box.firstElementChild;
    },
  };
  const saved = JSON.parse(localStorage.getItem("shades-of-grey-settings") || "{}") || {};
  const look = window.minifolioLook.known(saved.mentorLook) ? saved.mentorLook : "futuristic";
  root.dataset.look = look;
  window.minifolioLook.styles();
  if (look !== "futuristic") {
    const swap = () => {
      const button = document.getElementById("mentor-button");
      const old = button && button.querySelector("svg");
      if (!old) return false;
      button.replaceChild(window.minifolioLook.svg(look, "neutral"), old);
      return true;
    };
    const watch = new MutationObserver(() => { if (swap()) watch.disconnect(); });
    watch.observe(root, { childList: true, subtree: true });
    document.addEventListener("DOMContentLoaded", () => watch.disconnect());
  }
} catch (ignored) {}

// LR1: THE LOADING RING. It is in index.html, so it shows from the first frame. This lights it as the script files arrive: each one that has
// loaded lights a little more of the first three fifths (the files are counted in the order index.html loads them; nothing changes that order).
// app.js then takes it over (minifolioRing.app) for Mo4a's three steps, which light the rest. It never goes backwards. While a big file is still on
// its way the ring holds and the CSS sheen keeps moving. Reduced motion: each segment lights only once it is whole (steps, no fading).
// MO6: the ring is now the loading screen, the app icon's ring in the middle of a plain screen (see "MO6:" in the CSS of index.html), with every
// look. Its five segments light (a glow and a bright edge, --l0 to --l4 on .mo6-load) clockwise from 12 o'clock; the segments' own colours never
// change while it loads, so the ring stays the icon the phone showed. The circle's place is still fitted here (the same sum as fitLaunch in app.js), so the
// start circle is ready under the screen when the ring hands over to it.
try {
  const root = document.documentElement;
  const RING_FILES = 10;      // this file and the data files index.html loads after it and before app.js (colour.js to mentor-engine.js)
  const FILES_SHARE = 0.6;    // how much of the ring they light; Mo4a's three steps in app.js light the rest
  const still = () => !!(window.matchMedia && window.matchMedia("(prefers-reduced-motion: reduce)").matches);
  const ring = window.minifolioRing = {
    progress: 0,
    app: false,   // set by app.js when it takes over
    draw(p) {
      ring.progress = Math.max(ring.progress, Math.min(1, p || 0));
      const box = document.querySelector(".mo6-load.mo-load");
      if (!box) return ring.progress;
      const whole = still();
      for (let i = 0; i < 5; i++) {
        const f = Math.min(1, Math.max(0, ring.progress * 5 - i));
        box.style.setProperty("--l" + i, String(whole ? (f > 0.999 ? 1 : 0) : Math.round(f * 1000) / 1000));
      }
      box.setAttribute("aria-valuenow", String(Math.round(ring.progress * 100)));
      return ring.progress;
    },
  };
  // MO6: a safety net. If app.js never takes the screen over (it failed to start), the screen fades away 6 s after the page has loaded, so the
  // page is never left covered.
  window.addEventListener("load", () => setTimeout(() => {
    const box = document.querySelector(".mo6-load");
    if (!box || ring.app) return;
    box.classList.remove("mo-load");
    box.classList.add("mo6-leaving");
    document.body.classList.remove("ring-loading");
    document.querySelectorAll(".ring-hold").forEach((b) => b.classList.remove("ring-hold"));
    box.style.transition = "opacity 240ms linear";
    box.style.opacity = "0";
    setTimeout(() => box.remove(), 300);
  }, 6000));
  const fit = () => {
    const bar = document.querySelector(".app-bar");
    const top = bar ? bar.getBoundingClientRect().bottom : 57;   // 57: the header's height on a phone, until the header is on the page
    const room = window.innerHeight - top;
    const scale = Math.min(1, root.clientWidth / 390, (room - 24) / 340);
    root.style.setProperty("--ring-scale", String(Math.max(0.3, Math.round(scale * 1000) / 1000)));
    root.style.setProperty("--ring-cy", Math.round(top + room / 2) + "px");
  };
  fit();
  let files = 0;
  document.addEventListener("load", (event) => {
    const el = event.target;
    if (!el || el.tagName !== "SCRIPT" || ring.app) return;
    fit();   // the header is measured again each time (its font may have arrived meanwhile)
    files++;
    ring.draw(Math.min(1, files / RING_FILES) * FILES_SHARE);
  }, true);
} catch (ignored) {}
