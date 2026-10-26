"""T1: a faster stand-in for a fixed pause after a layout change.

frames(page) waits until the browser has drawn two more frames. After a scroll or a window resize that is all the
page needs, and it takes about 30 ms instead of a fixed 100 to 150 ms. It waits for the thing itself, so it is no
less strict than the pause was: it only waits as long as the browser needs."""


def frames(page, count=2):
    page.evaluate("""n => new Promise(done => { const tick = () => (--n <= 0 ? done() : requestAnimationFrame(tick));
        requestAnimationFrame(tick); })""", count)
