// ===== mentor-looks.js: the Mentor orb's three looks and five states (chunk U6, 2 Nov 2026) =====
// This file is only data. It draws nothing until the app puts a string on screen, talks to nothing and stores nothing.
//
// MENTOR_LOOKS[look][state] is one inline SVG string. Looks: futuristic (the default: the launch ring, as in the app icon), magical, grounded.
// States: neutral (the round button, and the window at rest) and the four moods thinking, pleased, unsure, finished (the window only).
// Every colour comes from --mentor-* variables through MENTOR_LOOKS_CSS. New, optional ones (each falls back to an existing one):
//   --mentor-s0 ... --mentor-s4  the five ring segments, clockwise from 12 o'clock: the stage colour set's own five colours
//   --mentor-dot                 the centre dot: the theme's dark-mode accent, so it stays light blue on the dark badge
//   --mentor-glint               the wet sheen on the grounded paint (white)
// MENTOR_LOOKS_CSS: put it once in a <style>. Motion runs only inside an element with the class ml-live (the Mentor window's orb box),
// so the round button stays still. Motion stops under prefers-reduced-motion and inside an element with the class ml-still.
// Made by tools/build-looks.js from round 6 of tools/rounds.js. Change the drawings there and build again.
const MENTOR_LOOKS = {
  futuristic: {
    neutral: "<svg xmlns='http://www.w3.org/2000/svg' viewBox='16.67 16.67 166.67 166.67' class='ml-orb ml-futuristic ml-neutral' aria-hidden='true' focusable='false'><circle class='ml-lens' cx='100' cy='100' r='70'/><g class='ml-turn'><g transform='translate(100 100) rotate(-90)' fill='none'><g class='ml-glow3'><circle class='ml-k0' r='59.5'/><circle class='ml-k1' r='59.5'/><circle class='ml-k2' r='59.5'/><circle class='ml-k3' r='59.5'/><circle class='ml-k4' r='59.5'/></g><g class='ml-glow2'><circle class='ml-k0' r='59.5'/><circle class='ml-k1' r='59.5'/><circle class='ml-k2' r='59.5'/><circle class='ml-k3' r='59.5'/><circle class='ml-k4' r='59.5'/></g><g class='ml-glow1'><circle class='ml-k0' r='59.5'/><circle class='ml-k1' r='59.5'/><circle class='ml-k2' r='59.5'/><circle class='ml-k3' r='59.5'/><circle class='ml-k4' r='59.5'/></g><circle class='ml-gap' r='59.5'/><g class='ml-segs'><circle class='ml-k0' r='59.5'/><circle class='ml-k1' r='59.5'/><circle class='ml-k2' r='59.5'/><circle class='ml-k3' r='59.5'/><circle class='ml-k4' r='59.5'/></g></g></g><circle class='ml-lens' cx='100' cy='100' r='49.5'/><circle class='ml-dot' cx='100' cy='100' r='13'/></svg>",
    thinking: "<svg xmlns='http://www.w3.org/2000/svg' viewBox='16.67 16.67 166.67 166.67' class='ml-orb ml-futuristic ml-thinking' aria-hidden='true' focusable='false'><circle class='ml-lens' cx='100' cy='100' r='74'/><g class='ml-turn'><g transform='translate(100 100) rotate(-90)' fill='none'><g class='ml-glow3'><circle class='ml-k0' r='59.5' transform='translate(3.23 1.34)'/><circle class='ml-k1' r='59.5' transform='translate(1.34 3.23)'/><circle class='ml-k2' r='59.5' transform='translate(-1.59 3.12)'/><circle class='ml-k3' r='59.5' transform='translate(-3.49 0.27)'/><circle class='ml-k4' r='59.5' transform='translate(0.82 -3.40)'/></g><g class='ml-glow2'><circle class='ml-k0' r='59.5' transform='translate(3.23 1.34)'/><circle class='ml-k1' r='59.5' transform='translate(1.34 3.23)'/><circle class='ml-k2' r='59.5' transform='translate(-1.59 3.12)'/><circle class='ml-k3' r='59.5' transform='translate(-3.49 0.27)'/><circle class='ml-k4' r='59.5' transform='translate(0.82 -3.40)'/></g><g class='ml-glow1'><circle class='ml-k0' r='59.5' transform='translate(3.23 1.34)'/><circle class='ml-k1' r='59.5' transform='translate(1.34 3.23)'/><circle class='ml-k2' r='59.5' transform='translate(-1.59 3.12)'/><circle class='ml-k3' r='59.5' transform='translate(-3.49 0.27)'/><circle class='ml-k4' r='59.5' transform='translate(0.82 -3.40)'/></g><g class='ml-segs'><circle class='ml-k0' r='59.5' transform='translate(3.23 1.34)'/><circle class='ml-k1' r='59.5' transform='translate(1.34 3.23)'/><circle class='ml-k2' r='59.5' transform='translate(-1.59 3.12)'/><circle class='ml-k3' r='59.5' transform='translate(-3.49 0.27)'/><circle class='ml-k4' r='59.5' transform='translate(0.82 -3.40)'/></g></g></g><circle class='ml-lens' cx='100' cy='100' r='49.5'/><circle class='ml-dot ml-core' cx='100' cy='100' r='9'/></svg>",
    pleased: "<svg xmlns='http://www.w3.org/2000/svg' viewBox='16.67 16.67 166.67 166.67' class='ml-orb ml-futuristic ml-pleased' aria-hidden='true' focusable='false'><circle class='ml-lens' cx='100' cy='100' r='70'/><g class='ml-turn'><g transform='translate(100 100) rotate(-90)' fill='none'><g class='ml-glow3'><circle class='ml-k0' r='59.5'/><circle class='ml-k1' r='59.5'/><circle class='ml-k2' r='59.5'/><circle class='ml-k3' r='59.5'/><circle class='ml-k4' r='59.5'/></g><g class='ml-glow2'><circle class='ml-k0' r='59.5'/><circle class='ml-k1' r='59.5'/><circle class='ml-k2' r='59.5'/><circle class='ml-k3' r='59.5'/><circle class='ml-k4' r='59.5'/></g><g class='ml-glow1'><circle class='ml-k0' r='59.5'/><circle class='ml-k1' r='59.5'/><circle class='ml-k2' r='59.5'/><circle class='ml-k3' r='59.5'/><circle class='ml-k4' r='59.5'/></g><circle class='ml-gap' r='59.5'/><g class='ml-segs'><circle class='ml-k0' r='59.5'/><circle class='ml-k1' r='59.5'/><circle class='ml-k2' r='59.5'/><circle class='ml-k3' r='59.5'/><circle class='ml-k4' r='59.5'/></g></g></g><circle class='ml-lens' cx='100' cy='100' r='49.5'/><circle class='ml-dot ml-core' cx='100' cy='100' r='18'/></svg>",
    unsure: "<svg xmlns='http://www.w3.org/2000/svg' viewBox='16.67 16.67 166.67 166.67' class='ml-orb ml-futuristic ml-unsure' aria-hidden='true' focusable='false'><circle class='ml-lens' cx='100' cy='100' r='70'/><g class='ml-turn'><g transform='translate(100 100) rotate(-90)' fill='none'><g class='ml-glow3'><circle class='ml-k0' r='59.5'/><circle class='ml-k1' r='59.5'/><circle class='ml-k2' r='59.5'/><circle class='ml-k3' r='59.5'/><circle class='ml-k4' r='59.5'/></g><g class='ml-glow2'><circle class='ml-k0' r='59.5'/><circle class='ml-k1' r='59.5'/><circle class='ml-k2' r='59.5'/><circle class='ml-k3' r='59.5'/><circle class='ml-k4' r='59.5'/></g><g class='ml-glow1'><circle class='ml-k0' r='59.5'/><circle class='ml-k1' r='59.5'/><circle class='ml-k2' r='59.5'/><circle class='ml-k3' r='59.5'/><circle class='ml-k4' r='59.5'/></g><circle class='ml-gap' r='59.5'/><g class='ml-segs'><circle class='ml-k0' r='59.5'/><circle class='ml-k1' r='59.5'/><circle class='ml-k2' r='59.5'/><circle class='ml-k3' r='59.5'/><circle class='ml-k4' r='59.5'/></g></g></g><circle class='ml-lens' cx='100' cy='100' r='54'/><g class='ml-hover'><circle class='ml-dot' cx='93' cy='108' r='9' opacity='.7'/></g></svg>",
    finished: "<svg xmlns='http://www.w3.org/2000/svg' viewBox='16.67 16.67 166.67 166.67' class='ml-orb ml-futuristic ml-finished' aria-hidden='true' focusable='false'><circle class='ml-lens' cx='100' cy='100' r='70'/><g class='ml-turn'><g transform='translate(100 100) rotate(-90)' fill='none'><g class='ml-glow3'><circle class='ml-k0' r='59.5'/><circle class='ml-k1' r='59.5'/><circle class='ml-k2' r='59.5'/><circle class='ml-k3' r='59.5'/><circle class='ml-k4' r='59.5'/></g><g class='ml-glow2'><circle class='ml-k0' r='59.5'/><circle class='ml-k1' r='59.5'/><circle class='ml-k2' r='59.5'/><circle class='ml-k3' r='59.5'/><circle class='ml-k4' r='59.5'/></g><g class='ml-glow1'><circle class='ml-k0' r='59.5'/><circle class='ml-k1' r='59.5'/><circle class='ml-k2' r='59.5'/><circle class='ml-k3' r='59.5'/><circle class='ml-k4' r='59.5'/></g><circle class='ml-gap' r='59.5'/><g class='ml-segs'><circle class='ml-k0' r='59.5'/><circle class='ml-k1' r='59.5'/><circle class='ml-k2' r='59.5'/><circle class='ml-k3' r='59.5'/><circle class='ml-k4' r='59.5'/></g></g></g><circle class='ml-lens' cx='100' cy='100' r='49.5'/><circle class='ml-dotring' cx='100' cy='100' r='13' stroke-width='6'/></svg>",
  },
  magical: {
    neutral: "<svg xmlns='http://www.w3.org/2000/svg' viewBox='16.67 16.67 166.67 166.67' class='ml-orb ml-magical ml-neutral' aria-hidden='true' focusable='false'><circle class='ml-lens' cx='100' cy='100' r='70'/><g class='ml-turn'><g transform='translate(100 100) rotate(-90)' fill='none'><g class='ml-mist3'><circle class='ml-k0' r='59.5'/><circle class='ml-k1' r='59.5'/><circle class='ml-k2' r='59.5'/><circle class='ml-k3' r='59.5'/><circle class='ml-k4' r='59.5'/></g><g class='ml-mist2'><circle class='ml-k0' r='59.5'/><circle class='ml-k1' r='59.5'/><circle class='ml-k2' r='59.5'/><circle class='ml-k3' r='59.5'/><circle class='ml-k4' r='59.5'/></g><g class='ml-segs'><circle class='ml-k0' r='59.5'/><circle class='ml-k1' r='59.5'/><circle class='ml-k2' r='59.5'/><circle class='ml-k3' r='59.5'/><circle class='ml-k4' r='59.5'/></g></g></g><circle class='ml-lens' cx='100' cy='100' r='49.5'/><g class='ml-swirl' opacity='0.5'><circle cx='100' cy='100' r='24' fill='none'/><path class='ml-dotline' d='M100 82A18 18 0 0 1 118 100M100 124A24 24 0 0 1 76 100' fill='none' stroke-width='3' stroke-linecap='round'/></g><circle class='ml-dot' cx='100' cy='100' r='8'/></svg>",
    thinking: "<svg xmlns='http://www.w3.org/2000/svg' viewBox='16.67 16.67 166.67 166.67' class='ml-orb ml-magical ml-thinking' aria-hidden='true' focusable='false'><circle class='ml-lens' cx='100' cy='100' r='74'/><g class='ml-turn'><g transform='translate(100 100) rotate(-90)' fill='none'><g class='ml-mist3'><circle class='ml-k0' r='59.5' transform='translate(3.23 1.34)'/><circle class='ml-k1' r='59.5' transform='translate(1.34 3.23)'/><circle class='ml-k2' r='59.5' transform='translate(-1.59 3.12)'/><circle class='ml-k3' r='59.5' transform='translate(-3.49 0.27)'/><circle class='ml-k4' r='59.5' transform='translate(0.82 -3.40)'/></g><g class='ml-mist2'><circle class='ml-k0' r='59.5' transform='translate(3.23 1.34)'/><circle class='ml-k1' r='59.5' transform='translate(1.34 3.23)'/><circle class='ml-k2' r='59.5' transform='translate(-1.59 3.12)'/><circle class='ml-k3' r='59.5' transform='translate(-3.49 0.27)'/><circle class='ml-k4' r='59.5' transform='translate(0.82 -3.40)'/></g><g class='ml-segs'><circle class='ml-k0' r='59.5' transform='translate(3.23 1.34)'/><circle class='ml-k1' r='59.5' transform='translate(1.34 3.23)'/><circle class='ml-k2' r='59.5' transform='translate(-1.59 3.12)'/><circle class='ml-k3' r='59.5' transform='translate(-3.49 0.27)'/><circle class='ml-k4' r='59.5' transform='translate(0.82 -3.40)'/></g></g></g><circle class='ml-lens' cx='100' cy='100' r='49.5'/><g class='ml-swirl' opacity='0.7'><circle cx='100' cy='100' r='24' fill='none'/><path class='ml-dotline' d='M100 82A18 18 0 0 1 118 100M100 124A24 24 0 0 1 76 100' fill='none' stroke-width='3' stroke-linecap='round'/></g><circle class='ml-dot ml-core' cx='100' cy='100' r='5'/></svg>",
    pleased: "<svg xmlns='http://www.w3.org/2000/svg' viewBox='16.67 16.67 166.67 166.67' class='ml-orb ml-magical ml-pleased' aria-hidden='true' focusable='false'><circle class='ml-lens' cx='100' cy='100' r='70'/><g class='ml-turn'><g transform='translate(100 100) rotate(-90)' fill='none'><g class='ml-mist3'><circle class='ml-k0' r='59.5'/><circle class='ml-k1' r='59.5'/><circle class='ml-k2' r='59.5'/><circle class='ml-k3' r='59.5'/><circle class='ml-k4' r='59.5'/></g><g class='ml-mist2'><circle class='ml-k0' r='59.5'/><circle class='ml-k1' r='59.5'/><circle class='ml-k2' r='59.5'/><circle class='ml-k3' r='59.5'/><circle class='ml-k4' r='59.5'/></g><g class='ml-segs'><circle class='ml-k0' r='59.5'/><circle class='ml-k1' r='59.5'/><circle class='ml-k2' r='59.5'/><circle class='ml-k3' r='59.5'/><circle class='ml-k4' r='59.5'/></g></g></g><circle class='ml-lens' cx='100' cy='100' r='49.5'/><g class='ml-swirl' opacity='0.8'><circle cx='100' cy='100' r='24' fill='none'/><path class='ml-dotline' d='M100 82A18 18 0 0 1 118 100M100 124A24 24 0 0 1 76 100' fill='none' stroke-width='3' stroke-linecap='round'/></g><circle class='ml-dot ml-core' cx='100' cy='100' r='13'/></svg>",
    unsure: "<svg xmlns='http://www.w3.org/2000/svg' viewBox='16.67 16.67 166.67 166.67' class='ml-orb ml-magical ml-unsure' aria-hidden='true' focusable='false'><circle class='ml-lens' cx='100' cy='100' r='70'/><g class='ml-turn'><g transform='translate(100 100) rotate(-90)' fill='none'><g class='ml-mist3'><circle class='ml-k0' r='59.5'/><circle class='ml-k1' r='59.5'/><circle class='ml-k2' r='59.5'/><circle class='ml-k3' r='59.5'/><circle class='ml-k4' r='59.5'/></g><g class='ml-mist2'><circle class='ml-k0' r='59.5'/><circle class='ml-k1' r='59.5'/><circle class='ml-k2' r='59.5'/><circle class='ml-k3' r='59.5'/><circle class='ml-k4' r='59.5'/></g><g class='ml-segs'><circle class='ml-k0' r='59.5'/><circle class='ml-k1' r='59.5'/><circle class='ml-k2' r='59.5'/><circle class='ml-k3' r='59.5'/><circle class='ml-k4' r='59.5'/></g></g></g><circle class='ml-lens' cx='100' cy='100' r='54'/><g class='ml-swirl' opacity='0.25'><circle cx='100' cy='100' r='24' fill='none'/><path class='ml-dotline' d='M100 82A18 18 0 0 1 118 100M100 124A24 24 0 0 1 76 100' fill='none' stroke-width='3' stroke-linecap='round'/></g><g class='ml-hover'><circle class='ml-dot' cx='93' cy='108' r='6' opacity='.7'/></g></svg>",
    finished: "<svg xmlns='http://www.w3.org/2000/svg' viewBox='16.67 16.67 166.67 166.67' class='ml-orb ml-magical ml-finished' aria-hidden='true' focusable='false'><circle class='ml-lens' cx='100' cy='100' r='70'/><g class='ml-turn'><g transform='translate(100 100) rotate(-90)' fill='none'><g class='ml-mist3'><circle class='ml-k0' r='59.5'/><circle class='ml-k1' r='59.5'/><circle class='ml-k2' r='59.5'/><circle class='ml-k3' r='59.5'/><circle class='ml-k4' r='59.5'/></g><g class='ml-mist2'><circle class='ml-k0' r='59.5'/><circle class='ml-k1' r='59.5'/><circle class='ml-k2' r='59.5'/><circle class='ml-k3' r='59.5'/><circle class='ml-k4' r='59.5'/></g><g class='ml-segs'><circle class='ml-k0' r='59.5'/><circle class='ml-k1' r='59.5'/><circle class='ml-k2' r='59.5'/><circle class='ml-k3' r='59.5'/><circle class='ml-k4' r='59.5'/></g></g></g><circle class='ml-lens' cx='100' cy='100' r='49.5'/><circle class='ml-dotring' cx='100' cy='100' r='8' stroke-width='5'/></svg>",
  },
  grounded: {
    neutral: "<svg xmlns='http://www.w3.org/2000/svg' viewBox='16.67 16.67 166.67 166.67' class='ml-orb ml-grounded ml-neutral' aria-hidden='true' focusable='false'><circle class='ml-lens' cx='100' cy='100' r='70'/><g class='ml-turn'><g transform='translate(100 100) rotate(-90)' fill='none'><g class='ml-segs'><circle class='ml-k0' r='59.5'/><circle class='ml-k1' r='59.5'/><circle class='ml-k2' r='59.5'/><circle class='ml-k3' r='59.5'/><circle class='ml-k4' r='59.5'/></g><g class='ml-wet'><circle class='ml-w0' r='65.5'/><circle class='ml-w1' r='65.5'/><circle class='ml-w2' r='65.5'/><circle class='ml-w3' r='65.5'/><circle class='ml-w4' r='65.5'/></g></g></g><circle class='ml-lens' cx='100' cy='100' r='49.5'/><path class='ml-dot' d='M100 87C104.5 93 109 97.5 109 103A9 9 0 0 1 91 103C91 97.5 95.5 93 100 87Z' transform='translate(100 100) scale(1.15) translate(-100 -100)'/></svg>",
    thinking: "<svg xmlns='http://www.w3.org/2000/svg' viewBox='16.67 16.67 166.67 166.67' class='ml-orb ml-grounded ml-thinking' aria-hidden='true' focusable='false'><circle class='ml-lens' cx='100' cy='100' r='74'/><g class='ml-turn'><g transform='translate(100 100) rotate(-90)' fill='none'><g class='ml-segs'><circle class='ml-k0' r='59.5' transform='translate(3.23 1.34)'/><circle class='ml-k1' r='59.5' transform='translate(1.34 3.23)'/><circle class='ml-k2' r='59.5' transform='translate(-1.59 3.12)'/><circle class='ml-k3' r='59.5' transform='translate(-3.49 0.27)'/><circle class='ml-k4' r='59.5' transform='translate(0.82 -3.40)'/></g><g class='ml-wet'><circle class='ml-w0' r='65.5' transform='translate(3.23 1.34)'/><circle class='ml-w1' r='65.5' transform='translate(1.34 3.23)'/><circle class='ml-w2' r='65.5' transform='translate(-1.59 3.12)'/><circle class='ml-w3' r='65.5' transform='translate(-3.49 0.27)'/><circle class='ml-w4' r='65.5' transform='translate(0.82 -3.40)'/></g></g></g><circle class='ml-lens' cx='100' cy='100' r='49.5'/><g class='ml-core'><path class='ml-dot' d='M100 87C104.5 93 109 97.5 109 103A9 9 0 0 1 91 103C91 97.5 95.5 93 100 87Z' transform='translate(100 100) scale(0.8) translate(-100 -100)'/></g></svg>",
    pleased: "<svg xmlns='http://www.w3.org/2000/svg' viewBox='16.67 16.67 166.67 166.67' class='ml-orb ml-grounded ml-pleased' aria-hidden='true' focusable='false'><circle class='ml-lens' cx='100' cy='100' r='70'/><g class='ml-turn'><g transform='translate(100 100) rotate(-90)' fill='none'><g class='ml-segs'><circle class='ml-k0' r='59.5'/><circle class='ml-k1' r='59.5'/><circle class='ml-k2' r='59.5'/><circle class='ml-k3' r='59.5'/><circle class='ml-k4' r='59.5'/></g><g class='ml-wet'><circle class='ml-w0' r='65.5'/><circle class='ml-w1' r='65.5'/><circle class='ml-w2' r='65.5'/><circle class='ml-w3' r='65.5'/><circle class='ml-w4' r='65.5'/></g></g></g><circle class='ml-lens' cx='100' cy='100' r='49.5'/><g class='ml-core'><path class='ml-dot' d='M100 87C104.5 93 109 97.5 109 103A9 9 0 0 1 91 103C91 97.5 95.5 93 100 87Z' transform='translate(100 100) scale(1.6) translate(-100 -100)'/></g></svg>",
    unsure: "<svg xmlns='http://www.w3.org/2000/svg' viewBox='16.67 16.67 166.67 166.67' class='ml-orb ml-grounded ml-unsure' aria-hidden='true' focusable='false'><circle class='ml-lens' cx='100' cy='100' r='70'/><g class='ml-turn'><g transform='translate(100 100) rotate(-90)' fill='none'><g class='ml-segs'><circle class='ml-k0' r='59.5'/><circle class='ml-k1' r='59.5'/><circle class='ml-k2' r='59.5'/><circle class='ml-k3' r='59.5'/><circle class='ml-k4' r='59.5'/></g><g class='ml-wet'><circle class='ml-w0' r='65.5'/><circle class='ml-w1' r='65.5'/><circle class='ml-w2' r='65.5'/><circle class='ml-w3' r='65.5'/><circle class='ml-w4' r='65.5'/></g></g></g><circle class='ml-lens' cx='100' cy='100' r='54'/><g class='ml-hover'><path class='ml-dot' d='M100 87C104.5 93 109 97.5 109 103A9 9 0 0 1 91 103C91 97.5 95.5 93 100 87Z' transform='translate(93 108) scale(0.85) translate(-100 -100)' opacity='.7'/></g></svg>",
    finished: "<svg xmlns='http://www.w3.org/2000/svg' viewBox='16.67 16.67 166.67 166.67' class='ml-orb ml-grounded ml-finished' aria-hidden='true' focusable='false'><circle class='ml-lens' cx='100' cy='100' r='70'/><g class='ml-turn'><g transform='translate(100 100) rotate(-90)' fill='none'><g class='ml-segs'><circle class='ml-k0' r='59.5'/><circle class='ml-k1' r='59.5'/><circle class='ml-k2' r='59.5'/><circle class='ml-k3' r='59.5'/><circle class='ml-k4' r='59.5'/></g><g class='ml-wet'><circle class='ml-w0' r='65.5'/><circle class='ml-w1' r='65.5'/><circle class='ml-w2' r='65.5'/><circle class='ml-w3' r='65.5'/><circle class='ml-w4' r='65.5'/></g></g></g><circle class='ml-lens' cx='100' cy='100' r='49.5'/><circle class='ml-dotring' cx='100' cy='100' r='12' stroke-width='6'/></svg>",
  },
};
const MENTOR_LOOKS_CSS = ".ml-orb{display:block;overflow:visible}\n" +
  ".ml-bg{fill:var(--mentor-bg)}\n" +
  ".ml-lens{fill:var(--mentor-lens)}\n" +
  ".ml-lensrim{fill:var(--mentor-lens);stroke:var(--mentor-rim)}\n" +
  ".ml-core{fill:var(--mentor-core)}\n" +
  ".ml-corering{fill:none;stroke:var(--mentor-core)}\n" +
  ".ml-dot{fill:var(--mentor-dot,var(--mentor-core))}\n" +
  ".ml-dotring{fill:none;stroke:var(--mentor-dot,var(--mentor-core))}\n" +
  ".ml-track{stroke:var(--mentor-rim)}\n" +
  ".ml-glint{fill:var(--mentor-glint,var(--mentor-core))}\n" +
  ".ml-gap{stroke:color-mix(in srgb,var(--mentor-lens) 78%,var(--mentor-core))}\n" +
  ".ml-k0{stroke:var(--mentor-s0,var(--mentor-dim))}\n" +
  ".ml-k1{stroke:var(--mentor-s1,var(--mentor-b))}\n" +
  ".ml-k2{stroke:var(--mentor-s2,var(--mentor-c))}\n" +
  ".ml-k3{stroke:var(--mentor-s3,var(--mentor-a))}\n" +
  ".ml-k4{stroke:var(--mentor-s4,var(--mentor-a))}\n" +
  ".ml-turn,.ml-core,.ml-hover{transform-box:fill-box;transform-origin:center}\n" +
  ".ml-live .ml-thinking .ml-turn{animation:ml-spin 14s linear infinite}\n" +
  ".ml-live .ml-thinking .ml-core{animation:ml-glow 3s ease-in-out infinite}\n" +
  ".ml-live .ml-pleased .ml-core{animation:ml-in2 1.2s ease-out both}\n" +
  ".ml-live .ml-unsure .ml-turn{animation:ml-tilt 6s ease-in-out infinite}\n" +
  ".ml-live .ml-unsure .ml-hover{animation:ml-drift 6s ease-in-out infinite}\n" +
  ".ml-futuristic .ml-k0{stroke-dasharray:41.54 373.85;stroke-dashoffset:-2.6}\n" +
  ".ml-futuristic .ml-k1{stroke-dasharray:41.54 373.85;stroke-dashoffset:-49.33}\n" +
  ".ml-futuristic .ml-k2{stroke-dasharray:50.89 373.85;stroke-dashoffset:-96.06}\n" +
  ".ml-futuristic .ml-k3{stroke-dasharray:60.23 373.85;stroke-dashoffset:-152.14}\n" +
  ".ml-futuristic .ml-k4{stroke-dasharray:153.69 373.85;stroke-dashoffset:-217.56}\n" +
  ".ml-futuristic.ml-thinking .ml-k0{stroke-dasharray:31.15 373.85;stroke-dashoffset:-7.79}\n" +
  ".ml-futuristic.ml-thinking .ml-k1{stroke-dasharray:31.15 373.85;stroke-dashoffset:-54.52}\n" +
  ".ml-futuristic.ml-thinking .ml-k2{stroke-dasharray:40.5 373.85;stroke-dashoffset:-101.25}\n" +
  ".ml-futuristic.ml-thinking .ml-k3{stroke-dasharray:49.85 373.85;stroke-dashoffset:-157.33}\n" +
  ".ml-futuristic.ml-thinking .ml-k4{stroke-dasharray:143.31 373.85;stroke-dashoffset:-222.75}\n" +
  ".ml-futuristic.ml-pleased .ml-k0{stroke-dasharray:44.65 373.85;stroke-dashoffset:-1.04}\n" +
  ".ml-futuristic.ml-pleased .ml-k1{stroke-dasharray:44.65 373.85;stroke-dashoffset:-47.77}\n" +
  ".ml-futuristic.ml-pleased .ml-k2{stroke-dasharray:54 373.85;stroke-dashoffset:-94.5}\n" +
  ".ml-futuristic.ml-pleased .ml-k3{stroke-dasharray:63.35 373.85;stroke-dashoffset:-150.58}\n" +
  ".ml-futuristic.ml-pleased .ml-k4{stroke-dasharray:156.81 373.85;stroke-dashoffset:-216}\n" +
  ".ml-futuristic.ml-finished .ml-k0{stroke-dasharray:46.73 373.85;stroke-dashoffset:0}\n" +
  ".ml-futuristic.ml-finished .ml-k1{stroke-dasharray:46.73 373.85;stroke-dashoffset:-46.73}\n" +
  ".ml-futuristic.ml-finished .ml-k2{stroke-dasharray:56.6 373.85;stroke-dashoffset:-93.46}\n" +
  ".ml-futuristic.ml-finished .ml-k3{stroke-dasharray:64.9 373.85;stroke-dashoffset:-150.06}\n" +
  ".ml-futuristic.ml-finished .ml-k4{stroke-dasharray:158.89 373.85;stroke-dashoffset:-214.96}\n" +
  ".ml-futuristic .ml-segs circle,.ml-futuristic .ml-gap{stroke-width:21}\n" +
  ".ml-futuristic .ml-glow1 circle{stroke-width:25;opacity:.16}\n" +
  ".ml-futuristic .ml-glow2 circle{stroke-width:29;opacity:.1}\n" +
  ".ml-futuristic .ml-glow3 circle{stroke-width:34;opacity:.06}\n" +
  ".ml-futuristic.ml-pleased .ml-segs circle,.ml-futuristic.ml-pleased .ml-gap{stroke-width:23}\n" +
  ".ml-futuristic.ml-pleased .ml-glow1 circle{opacity:.26}\n" +
  ".ml-futuristic.ml-pleased .ml-glow2 circle{opacity:.16}\n" +
  ".ml-futuristic.ml-pleased .ml-glow3 circle{opacity:.1}\n" +
  ".ml-futuristic.ml-unsure .ml-segs{opacity:.55}\n" +
  ".ml-futuristic.ml-unsure .ml-glow1,.ml-futuristic.ml-unsure .ml-glow2,.ml-futuristic.ml-unsure .ml-glow3{opacity:.35}\n" +
  ".ml-live .ml-futuristic.ml-neutral .ml-glow1,.ml-live .ml-futuristic.ml-neutral .ml-glow2,.ml-live .ml-futuristic.ml-neutral .ml-glow3{animation:ml-glow 6s ease-in-out infinite}\n" +
  ".ml-live .ml-futuristic.ml-pleased .ml-glow1,.ml-live .ml-futuristic.ml-pleased .ml-glow2,.ml-live .ml-futuristic.ml-pleased .ml-glow3{animation:ml-up 1.6s ease-out both}\n" +
  ".ml-live .ml-futuristic.ml-finished .ml-k0{animation:ml-fc0 1.4s ease-out both}\n" +
  ".ml-live .ml-futuristic.ml-finished .ml-k1{animation:ml-fc1 1.4s ease-out both}\n" +
  ".ml-live .ml-futuristic.ml-finished .ml-k2{animation:ml-fc2 1.4s ease-out both}\n" +
  ".ml-live .ml-futuristic.ml-finished .ml-k3{animation:ml-fc3 1.4s ease-out both}\n" +
  ".ml-live .ml-futuristic.ml-finished .ml-k4{animation:ml-fc4 1.4s ease-out both}\n" +
  ".ml-magical .ml-k0{stroke-dasharray:27 373.85;stroke-dashoffset:-9.87}\n" +
  ".ml-magical .ml-k1{stroke-dasharray:27 373.85;stroke-dashoffset:-56.6}\n" +
  ".ml-magical .ml-k2{stroke-dasharray:36.35 373.85;stroke-dashoffset:-103.33}\n" +
  ".ml-magical .ml-k3{stroke-dasharray:45.69 373.85;stroke-dashoffset:-159.41}\n" +
  ".ml-magical .ml-k4{stroke-dasharray:139.16 373.85;stroke-dashoffset:-224.83}\n" +
  ".ml-magical.ml-thinking .ml-k0{stroke-dasharray:16.62 373.85;stroke-dashoffset:-15.06}\n" +
  ".ml-magical.ml-thinking .ml-k1{stroke-dasharray:16.62 373.85;stroke-dashoffset:-61.79}\n" +
  ".ml-magical.ml-thinking .ml-k2{stroke-dasharray:25.96 373.85;stroke-dashoffset:-108.52}\n" +
  ".ml-magical.ml-thinking .ml-k3{stroke-dasharray:35.31 373.85;stroke-dashoffset:-164.6}\n" +
  ".ml-magical.ml-thinking .ml-k4{stroke-dasharray:128.77 373.85;stroke-dashoffset:-230.02}\n" +
  ".ml-magical.ml-pleased .ml-k0{stroke-dasharray:30.12 373.85;stroke-dashoffset:-8.31}\n" +
  ".ml-magical.ml-pleased .ml-k1{stroke-dasharray:30.12 373.85;stroke-dashoffset:-55.04}\n" +
  ".ml-magical.ml-pleased .ml-k2{stroke-dasharray:39.46 373.85;stroke-dashoffset:-101.77}\n" +
  ".ml-magical.ml-pleased .ml-k3{stroke-dasharray:48.81 373.85;stroke-dashoffset:-157.85}\n" +
  ".ml-magical.ml-pleased .ml-k4{stroke-dasharray:142.27 373.85;stroke-dashoffset:-223.27}\n" +
  ".ml-magical.ml-finished .ml-k0{stroke-dasharray:46.73 373.85;stroke-dashoffset:0}\n" +
  ".ml-magical.ml-finished .ml-k1{stroke-dasharray:46.73 373.85;stroke-dashoffset:-46.73}\n" +
  ".ml-magical.ml-finished .ml-k2{stroke-dasharray:56.6 373.85;stroke-dashoffset:-93.46}\n" +
  ".ml-magical.ml-finished .ml-k3{stroke-dasharray:64.9 373.85;stroke-dashoffset:-150.06}\n" +
  ".ml-magical.ml-finished .ml-k4{stroke-dasharray:158.89 373.85;stroke-dashoffset:-214.96}\n" +
  ".ml-magical .ml-segs circle{stroke-width:12;stroke-linecap:round;opacity:.8}\n" +
  ".ml-magical .ml-mist2 circle{stroke-width:22;stroke-linecap:round;opacity:.22}\n" +
  ".ml-magical .ml-mist3 circle{stroke-width:34;stroke-linecap:round;opacity:.09}\n" +
  ".ml-dotline{stroke:var(--mentor-dot,var(--mentor-core))}\n" +
  ".ml-magical.ml-pleased .ml-segs circle{stroke-width:15;opacity:1}\n" +
  ".ml-magical.ml-pleased .ml-mist2 circle{opacity:.32}\n" +
  ".ml-magical.ml-pleased .ml-mist3 circle{opacity:.14}\n" +
  ".ml-magical.ml-unsure .ml-segs circle{stroke-width:7}\n" +
  ".ml-magical.ml-unsure .ml-segs{opacity:.55}\n" +
  ".ml-magical.ml-unsure .ml-mist2,.ml-magical.ml-unsure .ml-mist3{opacity:.4}\n" +
  ".ml-magical.ml-finished .ml-segs circle,.ml-magical.ml-finished .ml-mist2 circle,.ml-magical.ml-finished .ml-mist3 circle{stroke-linecap:butt}\n" +
  ".ml-swirl{transform-box:fill-box;transform-origin:center}\n" +
  ".ml-live .ml-magical.ml-neutral .ml-mist2,.ml-live .ml-magical.ml-neutral .ml-mist3{animation:ml-glow 7s ease-in-out infinite}\n" +
  ".ml-live .ml-magical.ml-neutral .ml-swirl{animation:ml-spin 40s linear infinite}\n" +
  ".ml-live .ml-magical.ml-thinking .ml-swirl{animation:ml-spin 9s linear infinite}\n" +
  ".ml-live .ml-magical.ml-pleased .ml-mist2,.ml-live .ml-magical.ml-pleased .ml-mist3{animation:ml-up 1.6s ease-out both}\n" +
  ".ml-live .ml-magical.ml-finished .ml-k0{animation:ml-mc0 1.4s ease-out both}\n" +
  ".ml-live .ml-magical.ml-finished .ml-k1{animation:ml-mc1 1.4s ease-out both}\n" +
  ".ml-live .ml-magical.ml-finished .ml-k2{animation:ml-mc2 1.4s ease-out both}\n" +
  ".ml-live .ml-magical.ml-finished .ml-k3{animation:ml-mc3 1.4s ease-out both}\n" +
  ".ml-live .ml-magical.ml-finished .ml-k4{animation:ml-mc4 1.4s ease-out both}\n" +
  ".ml-grounded .ml-k0{stroke-dasharray:24.92 373.85;stroke-dashoffset:-10.9}\n" +
  ".ml-grounded .ml-k1{stroke-dasharray:24.92 373.85;stroke-dashoffset:-57.64}\n" +
  ".ml-grounded .ml-k2{stroke-dasharray:34.27 373.85;stroke-dashoffset:-104.37}\n" +
  ".ml-grounded .ml-k3{stroke-dasharray:43.62 373.85;stroke-dashoffset:-160.44}\n" +
  ".ml-grounded .ml-k4{stroke-dasharray:137.08 373.85;stroke-dashoffset:-225.87}\n" +
  ".ml-grounded.ml-thinking .ml-k0{stroke-dasharray:14.54 373.85;stroke-dashoffset:-16.1}\n" +
  ".ml-grounded.ml-thinking .ml-k1{stroke-dasharray:14.54 373.85;stroke-dashoffset:-62.83}\n" +
  ".ml-grounded.ml-thinking .ml-k2{stroke-dasharray:23.88 373.85;stroke-dashoffset:-109.56}\n" +
  ".ml-grounded.ml-thinking .ml-k3{stroke-dasharray:33.23 373.85;stroke-dashoffset:-165.64}\n" +
  ".ml-grounded.ml-thinking .ml-k4{stroke-dasharray:126.69 373.85;stroke-dashoffset:-231.06}\n" +
  ".ml-grounded.ml-pleased .ml-k0{stroke-dasharray:28.04 373.85;stroke-dashoffset:-9.35}\n" +
  ".ml-grounded.ml-pleased .ml-k1{stroke-dasharray:28.04 373.85;stroke-dashoffset:-56.08}\n" +
  ".ml-grounded.ml-pleased .ml-k2{stroke-dasharray:37.38 373.85;stroke-dashoffset:-102.81}\n" +
  ".ml-grounded.ml-pleased .ml-k3{stroke-dasharray:46.73 373.85;stroke-dashoffset:-158.89}\n" +
  ".ml-grounded.ml-pleased .ml-k4{stroke-dasharray:140.19 373.85;stroke-dashoffset:-224.31}\n" +
  ".ml-grounded.ml-finished .ml-k0{stroke-dasharray:46.73 373.85;stroke-dashoffset:0}\n" +
  ".ml-grounded.ml-finished .ml-k1{stroke-dasharray:46.73 373.85;stroke-dashoffset:-46.73}\n" +
  ".ml-grounded.ml-finished .ml-k2{stroke-dasharray:56.6 373.85;stroke-dashoffset:-93.46}\n" +
  ".ml-grounded.ml-finished .ml-k3{stroke-dasharray:64.9 373.85;stroke-dashoffset:-150.06}\n" +
  ".ml-grounded.ml-finished .ml-k4{stroke-dasharray:158.89 373.85;stroke-dashoffset:-214.96}\n" +
  ".ml-grounded .ml-w0{stroke-dasharray:22.86 411.55;stroke-dashoffset:-14.29}\n" +
  ".ml-grounded .ml-w1{stroke-dasharray:22.86 411.55;stroke-dashoffset:-65.73}\n" +
  ".ml-grounded .ml-w2{stroke-dasharray:33.15 411.55;stroke-dashoffset:-117.18}\n" +
  ".ml-grounded .ml-w3{stroke-dasharray:43.44 411.55;stroke-dashoffset:-178.91}\n" +
  ".ml-grounded .ml-w4{stroke-dasharray:146.33 411.55;stroke-dashoffset:-250.93}\n" +
  ".ml-grounded.ml-thinking .ml-w0{stroke-dasharray:11.43 411.55;stroke-dashoffset:-20.01}\n" +
  ".ml-grounded.ml-thinking .ml-w1{stroke-dasharray:11.43 411.55;stroke-dashoffset:-71.45}\n" +
  ".ml-grounded.ml-thinking .ml-w2{stroke-dasharray:21.72 411.55;stroke-dashoffset:-122.89}\n" +
  ".ml-grounded.ml-thinking .ml-w3{stroke-dasharray:32.01 411.55;stroke-dashoffset:-184.63}\n" +
  ".ml-grounded.ml-thinking .ml-w4{stroke-dasharray:134.9 411.55;stroke-dashoffset:-256.65}\n" +
  ".ml-grounded.ml-pleased .ml-w0{stroke-dasharray:26.29 411.55;stroke-dashoffset:-12.58}\n" +
  ".ml-grounded.ml-pleased .ml-w1{stroke-dasharray:26.29 411.55;stroke-dashoffset:-64.02}\n" +
  ".ml-grounded.ml-pleased .ml-w2{stroke-dasharray:36.58 411.55;stroke-dashoffset:-115.46}\n" +
  ".ml-grounded.ml-pleased .ml-w3{stroke-dasharray:46.87 411.55;stroke-dashoffset:-177.19}\n" +
  ".ml-grounded.ml-pleased .ml-w4{stroke-dasharray:149.76 411.55;stroke-dashoffset:-249.22}\n" +
  ".ml-grounded.ml-finished .ml-w0{stroke-dasharray:51.44 411.55;stroke-dashoffset:0}\n" +
  ".ml-grounded.ml-finished .ml-w1{stroke-dasharray:51.44 411.55;stroke-dashoffset:-51.44}\n" +
  ".ml-grounded.ml-finished .ml-w2{stroke-dasharray:62.3 411.55;stroke-dashoffset:-102.89}\n" +
  ".ml-grounded.ml-finished .ml-w3{stroke-dasharray:71.45 411.55;stroke-dashoffset:-165.19}\n" +
  ".ml-grounded.ml-finished .ml-w4{stroke-dasharray:174.91 411.55;stroke-dashoffset:-236.64}\n" +
  ".ml-grounded .ml-segs circle{stroke-width:19;stroke-linecap:round}\n" +
  ".ml-grounded .ml-wet circle{stroke:var(--mentor-glint,var(--mentor-core));stroke-width:2.5;stroke-linecap:round;opacity:.3}\n" +
  ".ml-grounded.ml-pleased .ml-segs circle{stroke-width:22}\n" +
  ".ml-grounded.ml-unsure .ml-segs circle{stroke-width:10}\n" +
  ".ml-grounded.ml-unsure .ml-segs{opacity:.55}\n" +
  ".ml-grounded.ml-unsure .ml-wet{display:none}\n" +
  ".ml-grounded.ml-finished .ml-segs circle{stroke-linecap:butt}\n" +
  ".ml-grounded.ml-finished .ml-wet circle{stroke-linecap:butt}\n" +
  ".ml-live .ml-grounded.ml-pleased .ml-segs circle{animation:ml-g-fill 1.2s ease-out both}\n" +
  ".ml-live .ml-grounded.ml-finished .ml-k0{animation:ml-gc0 1.4s ease-out both}\n" +
  ".ml-live .ml-grounded.ml-finished .ml-k1{animation:ml-gc1 1.4s ease-out both}\n" +
  ".ml-live .ml-grounded.ml-finished .ml-k2{animation:ml-gc2 1.4s ease-out both}\n" +
  ".ml-live .ml-grounded.ml-finished .ml-k3{animation:ml-gc3 1.4s ease-out both}\n" +
  ".ml-live .ml-grounded.ml-finished .ml-k4{animation:ml-gc4 1.4s ease-out both}\n" +
  "@keyframes ml-spin{to{transform:rotate(360deg)}}\n" +
  "@keyframes ml-glow{0%,100%{opacity:1}50%{opacity:.55}}\n" +
  "@keyframes ml-breathe{0%,100%{transform:scale(1)}50%{transform:scale(.94)}}\n" +
  "@keyframes ml-in{from{transform:scale(.88);opacity:.5}}\n" +
  "@keyframes ml-up{from{opacity:.3}}\n" +
  "@keyframes ml-tilt{0%,100%{transform:rotate(0)}50%{transform:rotate(-8deg)}}\n" +
  "@keyframes ml-in2{from{transform:scale(.8)}}\n" +
  "@keyframes ml-drift{0%,100%{transform:translate(0,0)}50%{transform:translate(-3px,2px)}}\n" +
  "@keyframes ml-fc0{from{stroke-dasharray:41.54 373.85;stroke-dashoffset:-2.6}}\n" +
  "@keyframes ml-fc1{from{stroke-dasharray:41.54 373.85;stroke-dashoffset:-49.33}}\n" +
  "@keyframes ml-fc2{from{stroke-dasharray:50.89 373.85;stroke-dashoffset:-96.06}}\n" +
  "@keyframes ml-fc3{from{stroke-dasharray:60.23 373.85;stroke-dashoffset:-152.14}}\n" +
  "@keyframes ml-fc4{from{stroke-dasharray:153.69 373.85;stroke-dashoffset:-217.56}}\n" +
  "@keyframes ml-mc0{from{stroke-dasharray:27 373.85;stroke-dashoffset:-9.87}}\n" +
  "@keyframes ml-mc1{from{stroke-dasharray:27 373.85;stroke-dashoffset:-56.6}}\n" +
  "@keyframes ml-mc2{from{stroke-dasharray:36.35 373.85;stroke-dashoffset:-103.33}}\n" +
  "@keyframes ml-mc3{from{stroke-dasharray:45.69 373.85;stroke-dashoffset:-159.41}}\n" +
  "@keyframes ml-mc4{from{stroke-dasharray:139.16 373.85;stroke-dashoffset:-224.83}}\n" +
  "@keyframes ml-gc0{from{stroke-dasharray:24.92 373.85;stroke-dashoffset:-10.9}}\n" +
  "@keyframes ml-gc1{from{stroke-dasharray:24.92 373.85;stroke-dashoffset:-57.64}}\n" +
  "@keyframes ml-gc2{from{stroke-dasharray:34.27 373.85;stroke-dashoffset:-104.37}}\n" +
  "@keyframes ml-gc3{from{stroke-dasharray:43.62 373.85;stroke-dashoffset:-160.44}}\n" +
  "@keyframes ml-gc4{from{stroke-dasharray:137.08 373.85;stroke-dashoffset:-225.87}}\n" +
  "@keyframes ml-g-fill{from{stroke-width:17}}\n" +
  "@media (prefers-reduced-motion:reduce){.ml-orb,.ml-orb *{animation:none!important;transition:none!important}}\n" +
  ".ml-still .ml-orb,.ml-still .ml-orb *{animation:none!important;transition:none!important}";
