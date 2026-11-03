"""MF1: Mentor finds the entries it missed. New behaviour only.

MF1 changed only the knowledge base's extras (asked-as phrases and synonyms) and rebuilt mentor-data.js from them.
1. The questions chunk E left for MF1 (water, clothes, a small room with no window, photos, a first model, streaky, and "wter"):
   each now finds its entry.
2. Fresh wordings: 23 or 24 ways of asking for each of the seven entries, written for MF1 and kept out of the data (slang, typos,
   short forms such as "hoodie", "lungs", "clumps"). Each entry is found first or second on at least the number it reached when
   MF1 was measured, none of them gets a colour or an app answer, and none of them is in the data.
3. Words read the right way: painting water is not rinse water (but paint water down the sink still is); mineral or odourless
   spirits are a solvent, not a ghost; clothes worn on a model, clump foliage, rust streaks, a gas mask or a camera lens on a model
   stay painting questions; choosing a model finds the guide on picking one.
4. Everyday questions that use MF1's new words ("lake district walks", "where can i buy a hoodie") still get no answer.
5. mentor-data.js is exactly what build_mentor_data.py --no-quick makes from the extras (never edited by hand).
6. In the Mentor window, "How do I paint water?" answers with the water entry. No page errors, no browser pop-ups.
Run all tests with `python3 tests/run_all.py`, or serve the repo folder and run this file on its own."""
import os, re, subprocess, sys, tempfile
from playwright.sync_api import sync_playwright

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import test_v24 as t

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.join(HERE, "..")
results = []

def check(name, ok, detail=""):
    results.append(bool(ok))
    print(("PASS " if ok else "FAIL ") + name + ("" if ok else f"  -> {detail}"))

# 1. the questions E's test list left for MF1: (question, right keys, how) - first: the first source; sources: any of them
LEFT_FOR_MF1 = [
    ("How do I paint water?", "puddles-and-water|sea-waves|swamp-and-bog|resin-water-effects|glowing-water", "first"),
    ("How do I stop getting paint on my clothes?", "paint-on-clothes", "sources"),
    ("Is it ok to paint in a small room with no window?", "hobby-safety|airbrush-safety", "sources"),
    ("How do I take good photos of my models?", "photographing-models", "first"),
    ("What is a good first model to buy?", "picking-models-to-paint", "first"),
    ("Why is my paint streaky?", "poor-coverage-paints|base-coating", "sources"),
    ("how do i paint wter", "puddles-and-water|sea-waves|resin-water-effects", "first"),
]

# 2. fresh wordings for the seven entries, never put in the extras. The first 10 of each were written before MF1 changed anything,
# the rest before the last rounds of changes (only their totals were looked at while tuning). "at least" is how many were found
# first or second when MF1 was measured (v125 found fewer: water 16, clothes 9, safety 14, lumpy 13, photos 16, first model 8, streaky 5).
SEVEN = {
    "water": ("puddles-and-water|sea-waves|swamp-and-bog|resin-water-effects|glowing-water", 18, [
        "how do i make a river on my base", "painting a lake on a diorama", "best way to do water on a base", "how to paint the sea",
        "water effect for a stream", "make a pond look wet", "how 2 paint watr", "realistic looking water", "how do i paint a puddle",
        "how do you do ocean waves on a base", "how do i do water on a display base", "river base tutorial", "how to make a stream on a base",
        "make a lake for my terrain", "pond effect for a base", "how do i make realistic puddles", "what to use for water on bases",
        "how to paint deep water", "water efects", "how can i make water look shiny on a base", "making water for terrain", "paint swamp water",
        "how to make a river look real", "watter effects on a base"]),
    "clothes": ("paint-on-clothes", 18, [
        "got paint on my hoodie", "acrylic on my jeans how do i get it out", "how to get paint off a t-shirt", "paint stain on my trousers",
        "will acrylic wash out of clothes", "spilt paint on my jumper", "does paint come out in the wash", "keep my clothes clean when i paint",
        "should i wear an apron to paint", "paint on my sleeve", "got acrylic on my favourite shirt", "how to clean paint off jeans",
        "paint on my trousers wont come out", "will hobby paint stain my clothes", "accidentally got paint on my jumper",
        "best way to remove paint from a hoodie", "paint stains on clothing", "how to get dried acrylic out of fabric", "spilled a wash on my trousers",
        "clothes covered in paint", "dropped a pot of paint on my shirt", "how to wash paint out of a top", "is hobby paint permanent on clothes",
        "paint all over my sweatshirt"]),
    "safety": ("hobby-safety|airbrush-safety", 17, [
        "is paint bad for my lungs", "do i need a mask", "painting in my bedroom with the window shut", "are the fumes dangerous",
        "is it safe to spray indoors", "can i paint in a room with no air", "is breathing in primer bad", "headache from painting",
        "is model paint toxic", "do i need an open window to paint", "is it safe to paint in a bedroom", "do i need to open a window when painting",
        "can paint fumes make you ill", "are acrylic paints safe to breathe", "is spray primer dangerous indoors", "do i need a respirator for painting minis",
        "is it unhealthy to paint every day", "paint smell gives me a headache", "is resin dust bad for you", "painting in a room with no ventilation",
        "is it ok to use spray cans in a flat", "stuffy room painting safe?", "is it bad to breathe paint smell", "safety gear for painting minis"]),
    "lumpy": ("reviving-old-paint|fix-rough-paint-texture", 16, [
        "my paint has clumps", "paint gone gloopy", "bits in my paint pot", "paint is chunky", "lumpy paint fix", "why does my paint have lumps",
        "paint gone all thick and clumpy", "grainy paint", "my paint is like cottage cheese", "paint pot full of lumps", "my paint has lumps",
        "lumps in the paint", "paint is full of bits", "my paint went clumpy", "paint gone thick and lumpy", "how to fix lumpy paint",
        "old paint with lumps in it", "paint has chunks in it", "paint is grainy and lumpy", "lumpy paint pot", "clumpy paint", "paint gone gritty",
        "my old paint has chunks in it", "lumpey paint"]),
    # (one more wording was measured, which names a photo-sharing site: it is left out of this public file)
    "photos": ("photographing-models", 20, [
        "how to take pics of my minis", "my pictures of models look rubbish", "photographing miniatures with a phone",
        "best light for taking photos of models", "my photos come out blurry", "camera settings for miniatures", "how to photograph minis",
        "why are my mini photos so dark", "fotos of my models", "how to photograph miniatures", "tips for taking photos of models",
        "my photos make my models look bad", "how to light minis for photos", "how to get sharp photos of minis", "phone pics of my models are blurry",
        "lightbox for model photos", "photography for miniature painters", "how to take photos of minis for online", "pictures of my painted army",
        "taking pictures of painted minis", "how do people get such nice photos of models", "phone camera tips for models", "background for photos of minis"]),
    # ("what to paint first" was measured too, but it is already an asked-as phrase of the guide on the order of painting, so it is left out here)
    "first model": ("picking-models-to-paint", 15, [
        "what mini should i start with", "best model for a first timer", "which miniature to paint first", "good beginner model",
        "what model should a noob buy", "easy mini to practice on", "first miniature to get", "what's a good starter mini",
        "recommend a model for a newbie", "which figure should i paint first", "what model should i paint first", "best first miniature",
        "which mini is good for a beginner", "what is an easy model to paint", "beginner friendly miniatures", "good model to start painting",
        "what to buy for my first model", "is this model too hard for a beginner", "choosing my first mini", "starter model for a new painter",
        "good first mini","simple miniature for a beginner", "whats an easy model to start painting"]),
    "streaky": ("poor-coverage-paints|base-coating", 11, [
        "paint looks streaky", "streaks on my model", "my base coat is all streaky", "paint going on patchy", "why is my coverage so bad",
        "streeky paint", "brush streaks everywhere", "my yellow is streaky", "uneven paint coverage", "paint dries streaky",
        "my base coat looks streaky", "why does my paint look streaky", "paint streaky on armour", "patchy paint", "how to stop paint going streaky",
        "streaky white paint", "my paint never covers evenly", "streaky layers", "see through streaky paint", "paint looks blotchy and streaky",
        "streaky coat of paint", "how to stop streaks", "my paint wont go on smooth", "stripey paint"]),
}

# 3. (question, keys, how): first / sources as above; notfirst: the first source is none of these (or there is no answer); notin: none of the sources
READ_RIGHT = [
    ("can i pour paint water down the sink", "disposing-of-paint-water", "sources"),
    ("how often should i change my rinse water", "rinse-water-habits", "first"),
    ("odourless spirits wash", "ghostly-ethereal-spirits", "notin"),
    ("thin oil paint with mineral spirits", "ghostly-ethereal-spirits", "notin"),
    ("how do i paint a ghost", "ghostly-ethereal-spirits", "first"),
    ("sprue goo", "sprue-goo", "first"),
    ("how do i paint jeans", "paint-on-clothes", "notfirst"),
    ("how do i paint clothes on my model", "paint-on-clothes", "notfirst"),
    ("how do i shade the folds on clothes", "paint-on-clothes", "notfirst"),
    ("how to paint a knitted jumper", "paint-on-clothes", "notfirst"),
    ("clump foliage on a base", "reviving-old-paint|fix-rough-paint-texture", "notfirst"),
    ("rust streaks on a tank", "poor-coverage-paints|base-coating", "notfirst"),
    ("how do i paint a gas mask", "hobby-safety|airbrush-safety", "notfirst"),
    ("how do i paint breathing tubes", "hobby-safety|airbrush-safety", "notfirst"),
    ("how do i paint a camera lens", "photographing-models", "notfirst"),
    ("Picking a model that is good to paint", "picking-models-to-paint", "first"),
]

# 4. everyday questions with MF1's new words (lake, river, hoodie, window, fan, lungs, starter, choosing a mini, tumble dryer): no answer
EVERYDAY = ["best river cruise in europe", "lake district walks", "where can i buy a hoodie", "what to wear to a wedding", "how to open a stuck window",
            "best extractor fan for a bathroom", "how deep is the river thames", "fishing in a lake", "what model should i buy for a laptop",
            "choosing a mini fridge", "how to pick a good watermelon", "starter for dinner party", "does chlorine affect my lungs",
            "how do i ventilate a loft", "tumble dryer not heating", "how do i wash a hoodie"]

ASK = """(qs) => { const ix = knowledgeIndex(); return qs.map((q) => { const a = MinifolioMentor.mentorAnswer(q, { index: ix, paints: [], tips: MENTOR_TIPS });
    return { kind: a.kind, keys: (a.sources || []).map((s) => s.key) }; }); }"""

def fits(a, want, how):
    ws = want.split("|")
    if how == "notfirst":
        return not (a["kind"] == "answer" and a["keys"][:1] and a["keys"][0] in ws)
    if how == "notin":
        return not any(k in ws for k in a["keys"])
    if a["kind"] != "answer":
        return False
    return any(k in ws for k in (a["keys"][:1] if how == "first" else a["keys"]))

def main():
    errors, dialogs = [], []
    with sync_playwright() as p:
        browser = p.chromium.launch()
        ctx = browser.new_context(viewport={"width": 390, "height": 844}, service_workers="block", reduced_motion="reduce")
        page = ctx.new_page()
        page.on("pageerror", lambda x: errors.append(str(x)))
        page.on("dialog", lambda d: (dialogs.append(d.message), d.dismiss()))
        t.fresh(page)

        print("\n--- 1. The questions left for MF1 ---")
        got = page.evaluate(ASK, [q for q, _, _ in LEFT_FOR_MF1])
        for (q, want, how), a in zip(LEFT_FOR_MF1, got):
            check(f"'{q}' finds its entry ({how})", fits(a, want, how), a)

        print("\n--- 2. Fresh wordings, kept out of the data ---")
        odd = []
        for name, (want, least, qs) in SEVEN.items():
            got = page.evaluate(ASK, qs)
            top2 = sum(1 for a in got if a["kind"] == "answer" and any(k in want.split("|") for k in a["keys"][:2]))
            odd += [(q, a["kind"]) for q, a in zip(qs, got) if a["kind"] in ("colour", "app")]
            check(f"{name}: found first or second on {top2} of {len(qs)} fresh wordings (at least {least})", top2 >= least,
                  [(q, a["keys"][:2]) for q, a in zip(qs, got) if not any(k in want.split("|") for k in a["keys"][:2])])
        check("no fresh wording gets a colour answer or the app's answer", not odd, odd)
        phrases = page.evaluate("() => Object.values(MENTOR_DATA.phrases).flat().map((p) => p.toLowerCase().replace(/[^a-z0-9]+/g, ' ').trim())")
        norm = lambda s: re.sub(r"[^a-z0-9]+", " ", s.lower()).strip()
        inside = [q for _, _, qs in SEVEN.values() for q in qs if norm(q) in set(phrases)]
        check("none of the fresh wordings is an asked-as phrase in the data", not inside, inside)

        print("\n--- 3. Words read the right way ---")
        got = page.evaluate(ASK, [q for q, _, _ in READ_RIGHT])
        bad = [(q, how, a["keys"][:2] or a["kind"]) for (q, want, how), a in zip(READ_RIGHT, got) if not fits(a, want, how)]
        check(f"water, solvents, clothes on a model and other painting words: {len(READ_RIGHT) - len(bad)}/{len(READ_RIGHT)} read the right way", not bad, bad)

        print("\n--- 4. Everyday questions ---")
        got = page.evaluate(ASK, EVERYDAY)
        check("everyday questions that use MF1's new words get no answer", all(a["kind"] == "none" for a in got),
              [(q, a["keys"][:1]) for q, a in zip(EVERYDAY, got) if a["kind"] != "none"])

        print("\n--- 5. The data file ---")
        with tempfile.TemporaryDirectory() as tmp:
            out = os.path.join(tmp, "mentor-data.js")
            run = subprocess.run([sys.executable, "-I", os.path.join(ROOT, "knowledge-base", "tools", "build_mentor_data.py"), "--no-quick", "--out", out],
                                 capture_output=True, text=True)
            same = run.returncode == 0 and open(out, "rb").read() == open(os.path.join(ROOT, "mentor-data.js"), "rb").read()
        check("mentor-data.js is exactly the build of the extras (build_mentor_data.py --no-quick)", same, run.stderr[-300:])

        print("\n--- 6. In the Mentor window ---")
        page.click("#mentor-button")
        page.wait_for_selector(".mentor-window")
        page.fill(".mentor-input", "How do I paint water?")
        page.keyboard.press("Enter")
        reply = page.locator(".mentor-reply").last
        reply.locator(".mentor-source").first.wait_for()
        first = reply.locator(".mentor-source").first.inner_text()
        check("'How do I paint water?' answers with the water entry first, not the rinse water guide", "Puddles and water" in first, first)
        check("the window stays open", page.locator(".mentor-window").count() == 1)
        check("no page errors", not errors, errors)
        check("no browser pop-ups", not dialogs, dialogs)
        browser.close()
    print(f"\n{sum(results)}/{len(results)} checks passed")
    sys.exit(0 if all(results) else 1)

if __name__ == "__main__":
    main()
