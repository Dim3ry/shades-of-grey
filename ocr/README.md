# Pot-label reader files

Minifolio reads paint-pot labels on the phone itself, with the free Tesseract engine.
Since v18.3 these files live here, in the app's own folder, instead of being downloaded
from other websites on the first scan. That means scanning works offline from the start,
and the app talks to no outside website when you scan.

| File | What it is | Where it came from |
|---|---|---|
| `tesseract-core-simd-lstm.js` / `.wasm` | The engine (faster version for most phones) | [tesseract.js-core](https://github.com/naptha/tesseract.js-core) v5.1.1, commit `027867a` |
| `tesseract-core-lstm.js` / `.wasm` | The engine (version for older phones) | same |
| `eng.traineddata` | English letter shapes (the "4.0.0_best_int" set, unzipped) | [naptha/tessdata](https://github.com/naptha/tessdata), `gh-pages` branch, commit `806cd9a` |
| Leptonica and libtiff | Two more open-source libraries that are already built into the engine files above (they are not separate files) | Leptonica from [leptonica.org](http://www.leptonica.org/) and libtiff from [libtiff.gitlab.io](https://libtiff.gitlab.io/libtiff/), as bundled by tesseract.js-core v5.1.1 |
| `ocr-worker.js` | Minifolio's own small script that runs the engine | written for Minifolio |

The engine and the English data are © their authors and licensed under the Apache
License 2.0 (copy in `LICENSE-tesseract.txt`). They are unchanged.

Leptonica and libtiff are inside the engine build and are unchanged. Their licence texts are
in `LICENSE-leptonica.txt` (Leptonica, from the project's `leptonica-license.txt`) and
`LICENSE-libtiff.txt` (libtiff, from its `COPYRIGHT` file).
