// ===== sw.js: the "service worker" =====
// A small helper the browser runs in the background. Its one job here: keep a copy
// of the app on your phone, so it still opens with no internet.
//
// How it decides (called "network first"):
//   1. Online?  Fetch the newest version from the web, and save a fresh copy.
//   2. Offline? Use the saved copy instead.
// So updates show up as soon as you're online, and offline it still works.
//
// WHEN YOU UPLOAD A NEW VERSION: change the number below (v1 -> v2 -> v3...).
// That tells the phone to throw away the old saved copy and start a new one.
const VERSION = "v16.1";
const CACHE_NAME = "shades-of-grey-" + VERSION;
// v16: the pot-label reader (Tesseract.js) is downloaded the first time you scan. It's kept
// in its own store that ISN'T cleared on updates, so scanning keeps working offline.
const OCR_CACHE = "shades-of-grey-label-reader";
const OCR_HOSTS = ["cdn.jsdelivr.net", "tessdata.projectnaptha.com"];

// The files that make up the app. Saved as soon as the app is installed.
const APP_FILES = [
  "./",
  "./index.html",
  "./manifest.json",
  "./icon-192.png",
  "./icon-512.png",
];

// "install": runs once when this version of sw.js is first seen. Save the app files.
self.addEventListener("install", (event) => {
  event.waitUntil(caches.open(CACHE_NAME).then((cache) => cache.addAll(APP_FILES)));
  self.skipWaiting(); // start using this new version straight away
});

// "activate": runs when this version takes over. Delete saved copies from old versions.
self.addEventListener("activate", (event) => {
  event.waitUntil(
    caches.keys()
      .then((names) => Promise.all(
        names.filter((name) => name !== CACHE_NAME && name !== OCR_CACHE).map((name) => caches.delete(name))))
      .then(() => self.clients.claim())
  );
});

// "fetch": runs every time the app asks for a file. Network first, saved copy if offline.
// Your units are NOT involved here: they live in the browser's storage, not in files.
self.addEventListener("fetch", (event) => {
  if (event.request.method !== "GET") return; // only plain "get a file" requests

  // v16: label-reader files never change, so use the saved copy first, else download and keep it.
  if (OCR_HOSTS.includes(new URL(event.request.url).hostname)) {
    event.respondWith(
      caches.open(OCR_CACHE).then((cache) => cache.match(event.request).then((saved) => saved ||
        fetch(event.request).then((response) => {
          if (response.ok) cache.put(event.request, response.clone());
          return response;
        }))));
    return;
  }

  event.respondWith(
    fetch(event.request)
      .then((response) => {
        // Got a good answer from the web: keep a copy for next time we're offline.
        if (response.ok && new URL(event.request.url).origin === self.location.origin) {
          const copy = response.clone();
          caches.open(CACHE_NAME).then((cache) => cache.put(event.request, copy));
        }
        return response;
      })
      .catch(() =>
        // No internet: look for a saved copy. Any page request falls back to the app itself.
        caches.match(event.request, { ignoreSearch: true })
          .then((saved) => saved || caches.match("./index.html")))
  );
});
