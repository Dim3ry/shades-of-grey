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
const VERSION = "v146";
const CACHE_NAME = "shades-of-grey-" + VERSION;
// The pot-label reader's big files (the engine and its English data, about 11 MB) are kept in
// their own store that ISN'T cleared on updates, so they're only fetched once.
// v18.3: they now come from the app's own "ocr" folder, not other websites. They're saved the
// first time you scan, and after that scanning works offline. (Not saved at install, so people
// who never scan don't download 11 MB.) ocr/ocr-worker.js itself is small and treated like any
// other app file, so changes to it arrive with updates.
const OCR_CACHE = "shades-of-grey-label-reader";
// DS2: the version of the label-reader engine in the ocr folder (tesseract.js-core, see ocr/README.md). The engine's files keep
// their names when it is updated, so the saved copies are labelled with this. A new number empties that store once (at the next
// update), and the new engine is fetched the next time you scan. Change it whenever the files in the ocr folder are replaced.
const OCR_ENGINE = "5.1.1";
const OCR_ENGINE_LABEL = "./ocr/saved-engine-version";   // not a real file: a note kept in the store, holding OCR_ENGINE
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
// DS2: a font or label-reader file is only saved if it really is one. A weak signal or a wi-fi sign-in page can answer with
// something else (a page of text, a cut-off file), and before DS2 that was saved and used for good. Each kind of file starts
// with its own few letters ("wOF2" for a font, "\0asm" for the engine), and the others are checked for size and for not
// being a web page. Saved copies that fail the check are removed when a new version takes over (see "activate").
function goodSavedFile(url, blob) {
  return blob.slice(0, 4).arrayBuffer().then((buffer) => {
    const head = new Uint8Array(buffer);
    const starts = (...bytes) => bytes.every((b, i) => head[i] === b);
    const path = new URL(url).pathname;
    if (/\.woff2$/.test(path)) return starts(0x77, 0x4f, 0x46, 0x32);                 // wOF2
    if (/\.wasm$/.test(path)) return starts(0x00, 0x61, 0x73, 0x6d);                  // \0asm
    if (/\.js$/.test(path)) return blob.size > 10000 && head[0] !== 0x3c;           // not "<" (a web page)
    if (/eng\.traineddata$/.test(path)) return blob.size > 1000000 && head[0] !== 0x3c;
    return false;
  }, () => false);
}
// The address a font or label-reader file is saved under: without any "?..." on the end, so the store holds one copy per file.
function savedFileKey(url) {
  const key = new URL(url);
  key.search = "";
  key.hash = "";
  return key.href;
}
function keepIfGood(cache, url, response) {
  if (!response.ok) return Promise.resolve();
  return response.clone().blob().then((blob) => goodSavedFile(url, blob).then((good) => good
    ? cache.put(savedFileKey(url), new Response(blob, { status: response.status, statusText: response.statusText, headers: response.headers }))
    : null)).catch(() => {});
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
  "./where-to-buy.js" + CODE_TAG,  // L1: what to buy for some Guides entries (the Where to buy fold-outs)
  "./manifest.json",
  "./icon-192.png",
  "./icon-512.png",
  "./ocr/ocr-worker.js",
  "./fonts/LICENSES.md",  // CR1: the licence texts the Credits page links to, saved so they open offline
  "./ocr/LICENSE-tesseract.txt",
  "./LICENSE-paint-list.txt",
];

// "install": runs once when this version of sw.js is first seen. Save the app files.
// DS2: { cache: "reload" } fetches each file from the web itself, not from the browser's own short-term store, so a new version's
// saved copy can't start with an older index.html (or ./) that the browser happened to be holding.
self.addEventListener("install", (event) => {
  event.waitUntil(caches.open(CACHE_NAME).then((cache) => cache.addAll(APP_FILES.map((url) => new Request(url, { cache: "reload" })))));
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
      .then(() => tidySavedFiles())   // DS2
      .then(() => self.clients.claim())
  );
});

// DS2: when a new version takes over: the label-reader store is emptied if it holds a different engine version (a store with no
// note yet holds this one, 5.1.1, the only engine the app has used from its own folder), and saved fonts and engine files that are
// not what they should be (see goodSavedFile) are removed, so the next use fetches them again.
function tidySavedFiles() {
  const label = new URL(OCR_ENGINE_LABEL, self.location.href).href;
  const ocr = caches.open(OCR_CACHE).then((cache) => cache.match(label)
    .then((note) => (note ? note.text() : OCR_ENGINE))
    .then((saved) => saved === OCR_ENGINE ? null
      : cache.keys().then((requests) => Promise.all(requests.map((request) => cache.delete(request)))))
    .then(() => cache.put(label, new Response(OCR_ENGINE, { headers: { "Content-Type": "text/plain" } })))
    .then(() => checkStore(cache, (url) => url !== label)));
  const fonts = caches.open(FONT_CACHE).then((cache) => checkStore(cache, () => true));
  return Promise.all([ocr, fonts]).catch(() => {});
}
function checkStore(cache, include) {
  return cache.keys().then((requests) => Promise.all(requests.filter((request) => include(request.url)).map((request) =>
    cache.match(request).then((saved) => (saved ? saved.blob() : null))
      .then((blob) => (blob ? goodSavedFile(request.url, blob) : false))
      .then((good) => (good && request.url === savedFileKey(request.url) ? null : cache.delete(request))))));
}

// "fetch": runs every time the app asks for a file. Network first, saved copy if offline.
// Your units are NOT involved here: they live in the browser's storage, not in files.
self.addEventListener("fetch", (event) => {
  if (event.request.method !== "GET") return; // only plain "get a file" requests

  // v27: the visit counter's picture (a tiny image from GoatCounter) is left alone: it goes straight
  // to the network, is never saved, and with no internet it simply fails without anyone noticing.
  if (new URL(event.request.url).hostname.endsWith(".goatcounter.com")) return;

  // Label-reader engine files never change, so use the saved copy first, else fetch and keep it.
  // v47: the same for the theme fonts (a font file never changes; a new font would get a new name).
  // DS2: saved only if the file is what it should be (keepIfGood), and under its address without any "?..." (one copy per file).
  const fileUrl = new URL(event.request.url);
  if (isOcrFile(fileUrl) || isFontFile(fileUrl)) {
    event.respondWith(
      caches.open(isFontFile(fileUrl) ? FONT_CACHE : OCR_CACHE).then((cache) => cache.match(savedFileKey(event.request.url)).then((saved) => saved ||
        fetch(event.request).then((response) => {
          const keeping = keepIfGood(cache, event.request.url, response);
          try { event.waitUntil(keeping); } catch (ignored) {}
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
// DS2: only for an address with no "?..." on the end, or this version's own "?v=" tag. Before DS2 every different "?..." was
// saved as a copy of its own, so the store could grow without end (200 made-up addresses gave 200 more copies).
function keepable(url) {
  const u = new URL(url);
  return u.origin === self.location.origin && (u.search === "" || u.search === CODE_TAG);
}
function fetchAndKeep(request) {
  return fetch(request).then((response) => {
    if (response.ok && keepable(request.url)) {
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
// DS2: the app's page is saved under its plain address ("./" or "./index.html", with any "?..." taken off), so the store keeps one
// copy of it. Before DS2 each different "?..." (index.html?junk=1, ?junk=2...) was saved as a full copy of its own. Other pages
// (null here) are not saved; offline they get the app's page, as before.
// LP1: the privacy page (privacy, or privacy.html on a plain file server) is a page of its own, not the app. It is saved under its own address
// and, offline, only its own saved copy is used: it is never answered with the app's page.
function isPrivacyPage(url) {
  const u = new URL(url);
  const scope = new URL("./", self.location.href);
  return u.origin === scope.origin && (u.pathname === scope.pathname + "privacy" || u.pathname === scope.pathname + "privacy.html");
}
function pageKey(url) {
  const u = new URL(url);
  const scope = new URL("./", self.location.href);
  if (isPrivacyPage(url)) { u.search = ""; u.hash = ""; return u.href; }
  if (u.origin !== scope.origin || (u.pathname !== scope.pathname && u.pathname !== scope.pathname + "index.html")) return null;
  u.search = "";
  u.hash = "";
  return u.href;
}
function savedPage(request) {
  return caches.open(CACHE_NAME).then((cache) => cache.match(request, { ignoreSearch: true })
    .then((saved) => saved || (isPrivacyPage(request.url) ? null : cache.match("./index.html"))));
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
      .then((cache) => { const key = pageKey(request.url); return key ? cache.put(key, response.clone()) : null; })
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
