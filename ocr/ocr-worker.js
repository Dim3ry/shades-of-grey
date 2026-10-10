// ===== ocr/ocr-worker.js: the pot-label reader (v18.3) =====
// Runs in the background (a "web worker") so the screen doesn't freeze while it reads.
// It uses the Tesseract text-reading engine, kept in this same folder (no downloads from
// other websites), so scanning works offline and your photo never leaves the phone.
//
// The app sends it two kinds of message:
//   { id, type: "init" }                    start the engine and load the English data
//   { id, type: "read", image: <PNG bytes> } read the text in a picture
// and it answers { id, text } or { id, error }.

let engine = null;   // the Tesseract engine (a WebAssembly program)
let api = null;      // the engine's "read this picture" tool
let starting = null;

// Can this phone run the faster "SIMD" version of the engine? (A tiny test program.)
function hasSimd() {
  try {
    return WebAssembly.validate(new Uint8Array([0, 97, 115, 109, 1, 0, 0, 0, 1, 5, 1, 96, 0, 1, 123, 3, 2, 1, 0,
      10, 10, 1, 8, 0, 65, 0, 253, 15, 253, 98, 11]));
  } catch (error) {
    return false;
  }
}

async function start() {
  const core = hasSimd() ? "tesseract-core-simd-lstm" : "tesseract-core-lstm";
  importScripts(core + ".js");                      // defines TesseractCore()
  engine = await self.TesseractCore({ locateFile: (file) => file.endsWith(".wasm") ? core + ".wasm" : file });
  const response = await fetch("eng.traineddata");  // the English "how letters look" data
  if (!response.ok) throw new Error("Couldn't load the label reader's English data.");
  engine.FS.writeFile("eng.traineddata", new Uint8Array(await response.arrayBuffer()));
  api = new engine.TessBaseAPI();
  // "1" = the modern (LSTM) reader only, the same as before v18.3.
  if (api.Init(null, "eng", 1) === -1) throw new Error("The label reader couldn't start.");
  api.SetVariable("tessedit_pageseg_mode", "6");     // "one block of text"
}

function read(image) {
  engine.FS.writeFile("/input", image);
  if (api.SetImageFile(1, 0) === 1) throw new Error("Couldn't read that picture.");
  api.Recognize(null);
  return api.GetUTF8Text() || "";
}

self.onmessage = async (event) => {
  const { id, type, image } = event.data || {};
  try {
    if (!starting) starting = start();
    await starting;
    const text = type === "read" ? read(image) : "";
    self.postMessage({ id, text });
  } catch (error) {
    if (!api) starting = null;   // let a later scan try again
    self.postMessage({ id, error: (error && error.message) || "The label reader stopped working." });
  }
};
