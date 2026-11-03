// ===== sw.js: the "service worker" =====
// A small helper the browser runs in the background. Its one job here: keep a copy
// of the app on your phone, so it still opens with no internet.
//
// How it decides (called "network first"):
//   1. Online?  Fetch the newest version from the web, and save a fresh copy.
//   2. Offline? Use the saved copy instead.
// So updates show up as soon as you're online, and offline it still works.
// DS1: one version at a time. The app's code files (named with "?v=" and the version) come from the saved copy first, and a
// new page is only used once its own code files are saved. An error from the web, or a page that takes more than about
// 4 seconds, gets the saved copy instead (see pageResponse at the bottom).
//
// WHEN YOU UPLOAD A NEW VERSION: change the number below (v1 -> v2 -> v3...).
// That tells the phone to throw away the old saved copy and start a new one.
const VERSION = "v125";
const CACHE_NAME = "shades-of-grey-" + VERSION;
// The pot-label reader's big files (the engine and its English data, about 11 MB) are kept in
// their own store that ISN'T cleared on updates, so they're only fetched once.
// v18.3: they now come from the app's own "ocr" folder, not other websites. They're saved the
// first time you scan, and after that scanning works offline. (Not saved at install, so people
// who never scan don't download 11 MB.) ocr/ocr-worker.js itself is small and treated like any
// other app file, so changes to it arrive with updates.
const OCR_CACHE = "shades-of-grey-label-reader";
function isOcrFile(url) {
  return url.origin === self.location.origin && /\/ocr\/(tesseract-core[^/]*|eng\.traineddata)$/.test(url.pathname);
}
// v47: the theme fonts (fonts/*.woff2) are kept in their own store too, also NOT cleared on updates. A font is
// saved the first time the app uses it (when you choose a theme, or see its name on the Theme buttons), and after
// that it comes from the saved copy, so a chosen theme looks right offline. Nothing is saved at install.
// (TH1: Classic uses one small font too, so it is saved the first time the app opens.)
const FONT_CACHE = "shades-of-grey-fonts";
function isFontFile(url) {
  return url.origin === self.location.origin && /\/fonts\/[a-z0-9-]+\.woff2$/.test(url.pathname);
}

// The files that make up the app. Saved as soon as the app is installed.
// v21.4: the app's code moved out of index.html into app.js and early.js. index.html asks for them
// with "?v=" and the version number on the end (e.g. "app.js?v=21.4"), so after an update the phone
// fetches the new files rather than an old saved copy. The same addresses are saved here, built
// from VERSION, so they always match (a test checks index.html uses the same number).
const CODE_TAG = "?v=" + VERSION.slice(1); // "v21.4" -> "?v=21.4"
const APP_FILES = [
  "./",
  "./index.html",
  "./app.js" + CODE_TAG,
  "./early.js" + CODE_TAG,
  "./mentor-looks.js" + CODE_TAG,  // U6b: the Mentor orb's three looks and five states
  "./colour.js" + CODE_TAG,   // v28: the colour maths for Colour ideas
  "./schemes.js" + CODE_TAG,  // v31: the starter colour schemes for Colour ideas
  "./detail-recipes.js" + CODE_TAG,  // v32: the detail recipes for Colour ideas
  "./basing-tips.js" + CODE_TAG,  // v33: the basing tips for Colour ideas
  "./mentor-tips.js" + CODE_TAG,  // v70: the Mentor tips library
  "./guides-data.js" + CODE_TAG,  // X3: the Guides library's guide entries and starter questions
  "./guides-groups.js" + CODE_TAG,  // G2a: the Guides topic groups and See also links
  "./mentor-data.js" + CODE_TAG,  // X8b: Mentor matching data (synonyms, extra keywords, asked-as phrases)
  "./mentor-engine.js" + CODE_TAG,  // X6a: the Mentor answer engine (no screen yet)
  "./manifest.json",
  "./icon-192.png",
  "./icon-512.png",
  "./ocr/ocr-worker.js",
];

// "install": runs once when this version of sw.js is first seen. Save the app files.
self.addEventListener("install", (event) => {
  event.waitUntil(caches.open(CACHE_NAME).then((cache) => cache.addAll(APP_FILES)));
  self.skipWaiting(); // start using this new version straight away
});

// "activate": runs when this version takes over. Delete saved copies from old versions.
// v18.3: also clear out the label-reader files that used to come from other websites.
self.addEventListener("activate", (event) => {
  event.waitUntil(
    caches.keys()
      .then((names) => Promise.all(
        names.filter((name) => name !== CACHE_NAME && name !== OCR_CACHE && name !== FONT_CACHE).map((name) => caches.delete(name))))
      .then(() => caches.open(OCR_CACHE))
      .then((cache) => cache.keys().then((requests) => Promise.all(requests
        .filter((request) => new URL(request.url).origin !== self.location.origin)
        .map((request) => cache.delete(request)))))
      .then(() => self.clients.claim())
  );
});

// "fetch": runs every time the app asks for a file. Network first, saved copy if offline.
// Your units are NOT involved here: they live in the browser's storage, not in files.
self.addEventListener("fetch", (event) => {
  if (event.request.method !== "GET") return; // only plain "get a file" requests

  // v27: the visit counter's picture (a tiny image from GoatCounter) is left alone: it goes straight
  // to the network, is never saved, and with no internet it simply fails without anyone noticing.
  if (new URL(event.request.url).hostname.endsWith(".goatcounter.com")) return;

  // Label-reader engine files never change, so use the saved copy first, else fetch and keep it.
  // v47: the same for the theme fonts (a font file never changes; a new font would get a new name).
  const fileUrl = new URL(event.request.url);
  if (isOcrFile(fileUrl) || isFontFile(fileUrl)) {
    event.respondWith(
      caches.open(isFontFile(fileUrl) ? FONT_CACHE : OCR_CACHE).then((cache) => cache.match(event.request).then((saved) => saved ||
        fetch(event.request).then((response) => {
          if (response.ok) cache.put(event.request, response.clone());
          return response;
        }))));
    return;
  }

  // DS1: page loads have their own rules (see pageResponse below). The app's code files (their addresses end in "?v=" and the
  // version) never change under the same address, so a saved copy is used first, matched EXACTLY: before DS1 a missing
  // "app.js?v=123" could be answered with the saved "app.js?v=122", and a new page ran with old code.
  if (event.request.mode === "navigate") {
    const answer = pageResponse(event.request);
    event.respondWith(answer.response);
    event.waitUntil(answer.done);
    return;
  }
  const versioned = fileUrl.origin === self.location.origin && fileUrl.searchParams.has("v");
  event.respondWith(versioned
    ? caches.match(event.request).then((saved) => saved || fetchAndKeep(event.request))
    : fetchAndKeep(event.request).then(
        // DS1: the web answered with an error (404, 500, 503...) and there is a saved copy? Use the saved copy.
        (response) => response.ok || response.type === "opaqueredirect" ? response
          : caches.match(event.request).then((saved) => saved || response),
        // No internet: the saved copy of exactly this file, if there is one. (v21.4: a missing script or picture just
        // fails, rather than being handed the page by mistake.)
        () => caches.match(event.request).then((saved) => saved || Response.error())));
});

// Fetch from the web; a good answer from the app's own site is saved for next time (offline).
function fetchAndKeep(request) {
  return fetch(request).then((response) => {
    if (response.ok && new URL(request.url).origin === self.location.origin) {
      const copy = response.clone();
      caches.open(CACHE_NAME).then((cache) => cache.put(request, copy));
    }
    return response;
  });
}

// ----- DS1: page loads (the "navigate" requests) -----
// The page from the web is used only if every code file it names is saved too (they're fetched and saved first if not), so
// the page and its code are always the same version. If that fails, if the web answers with an error, or if nothing has
// come after PAGE_WAIT_MS on a slow connection, the saved page is used instead (and the code files saved with it).
// With nothing saved yet (the very first visit) it waits for the web, whatever it says.
// Offline after the first visit it works as before: the saved copy of the page (any "?..." on the address is ignored),
// or the app itself.
const PAGE_WAIT_MS = 4000;
function savedPage(request) {
  return caches.open(CACHE_NAME).then((cache) => cache.match(request, { ignoreSearch: true })
    .then((saved) => saved || cache.match("./index.html")));
}
function codeFilesSaved(pageText, pageUrl) {
  const files = [...pageText.matchAll(/<script[^>]*\ssrc="([^"]+)"/g)]
    .map((m) => new URL(m[1], pageUrl))
    .filter((url) => url.origin === self.location.origin && url.searchParams.has("v"));
  return caches.open(CACHE_NAME).then((cache) => Promise.all(files.map((url) => caches.match(url.href).then((saved) => saved ||
    fetch(url.href).then((response) => {
      if (!response.ok) throw new Error("not saved");
      return cache.put(url.href, response);
    })))));
}
function pageResponse(request) {
  const fromWeb = fetch(request).then((response) => {
    // A redirect (a page load gets it as an "opaqueredirect" answer) is fine: the browser follows it. Not saved.
    if (response.type === "opaqueredirect") return { response, good: true };
    if (!response.ok) return { response, good: false };
    return response.clone().text()
      .then((text) => codeFilesSaved(text, request.url))
      .then(() => caches.open(CACHE_NAME))
      .then((cache) => cache.put(request, response.clone()))
      .then(() => ({ response, good: true }), () => ({ response, good: false }));
  });
  const done = fromWeb.catch(() => null);
  const timer = new Promise((resolve) => setTimeout(() => resolve(null), PAGE_WAIT_MS));
  const response = Promise.race([done, timer]).then((result) => {
    if (result && result.good) return result.response;
    return savedPage(request).then((saved) => saved ||
      done.then((late) => (late ? late.response : Response.error())));
  });
  return { response, done };
}
