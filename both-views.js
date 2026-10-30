// Developer tool for both-views.html. Not part of the app.
// Both frames are the app on this same site, so they share the same saved data (same browser storage).
// An edit in one frame reaches the other by itself (the app listens for that); "Reload both" is for a clean start.
(function () {
  "use strict";
  var PAGES = [
    ["dashboard", "Dashboard"], ["units", "Units"], ["recipes", "Painting"],
    ["guides", "Guides"], ["settings", "Settings"], ["help", "Help"], ["updates", "Updates"]
  ];
  var MORE = ["guides", "settings", "help", "updates"];   // these four are pages of the Tools and Settings tab (data-tab guides)
  var select = document.getElementById("page");
  var frames = [document.getElementById("phone"), document.getElementById("desktop")];
  var desktop = frames[1];
  var desktopBox = document.getElementById("desktop-box");
  var desktopTitle = document.getElementById("desktop-title");

  PAGES.forEach(function (p) {
    var o = document.createElement("option");
    o.value = p[0]; o.textContent = p[1];
    select.appendChild(o);
  });

  // Open the chosen page inside one frame by pressing the app's own tab button (same site, so this is allowed).
  function openPage(frame) {
    var name = select.value;
    try {
      var doc = frame.contentDocument;
      var btn = MORE.indexOf(name) >= 0
        ? (doc.querySelector('[data-tab="guides"]') && (doc.querySelector('[data-tab="guides"]').click(), doc.querySelector('[data-page="' + name + '"]')))
        : doc.querySelector('[data-tab="' + name + '"]');
      if (btn) btn.click();
    } catch (ignored) { /* frame not ready yet */ }
  }
  frames.forEach(function (f) { f.addEventListener("load", function () { openPage(f); }); });
  select.addEventListener("change", function () { frames.forEach(openPage); });
  document.getElementById("reload").addEventListener("click", function () {
    frames.forEach(function (f) { f.contentWindow.location.reload(); });
  });

  // Shrink the 1280 px frame to fit the space beside the phone, keeping its true 1280 px layout.
  function fit() {
    var room = document.getElementById("desktop-pane").clientWidth;
    var scale = Math.min(1, room / 1280);
    desktop.style.transform = "scale(" + scale + ")";
    desktopBox.style.width = Math.floor(1280 * scale) + "px";
    desktopBox.style.height = Math.floor(800 * scale) + "px";
    desktopTitle.textContent = "Desktop, 1280 px, shown at " + Math.round(scale * 100) + "%";
  }
  window.addEventListener("resize", fit);
  fit();
})();
