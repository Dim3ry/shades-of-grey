// ===== changelog.js: the Updates tab's list of versions (SZ1, v173) =====
// This list used to sit inside app.js (about 56 KB of text, of which the Updates screen shows only the newest few). It moved into its
// own file so app.js is smaller. The entries, their order and their wording did not change when it moved. It is loaded just before
// app.js (see index.html), as a plain script, so CHANGELOG is a top-level name the app and the tests can read exactly as before.
// WHEN YOU RELEASE AN UPDATE: add the new entry at the TOP of this list (and bump APP_VERSION in app.js, VERSION in sw.js and the ?v= numbers).

    // ================= THE CHANGELOG (the Updates tab's list: add one entry at the top for each version) =================
    const CHANGELOG = [
      { version: "v174", date: "18 Nov 2026", changes: [
        "Shopping: the models tab is now Wishlist models, each tab says what fills it, Remove no longer removes two items on a double tap, and Add model keeps what you typed. Tick boxes are easier to hit and old Undo messages clear.",
        "Fixes and tidying.",
      ] },
      { version: "v173", date: "17 Nov 2026", changes: [
        "Fixes and tidying.",
        "The app's code file is smaller, so it should start a little quicker.",
      ] },
      { version: "v172", date: "16 Nov 2026", changes: [
        "Fixes and tidying.",
        "Pop-ups share one way of moving focus with Tab, and a warning question stays on No.",
      ] },
      { version: "v171", date: "16 Nov 2026", changes: [
        "New My shops ticks, on Shopping and in Settings, choose which shops show in every shop link. Gear and Wishlist rows now have a Find button.",
        "Fixes and tidying.",
      ] },
      { version: "v170", date: "15 Nov 2026", changes: [
        "Fixes and tidying.",
        "The phone-size checks of the looks are steadier.",
      ] },
      { version: "v169", date: "15 Nov 2026", changes: [
        "Shopping has Add paint, Add gear and Add model buttons, and Add to shopping list now shows in more places. Running low paints can be added from Suggested. In the Classic look the blue corner marks now sit on every main card.",
        "Fixes and tidying.",
      ] },
      { version: "v168", date: "15 Nov 2026", changes: [
        "Shopping is now a screen of its own, with a Shopping button at the top of every screen. Inside are Paints, Gear and Wishlist, with a Show shop links switch at the top.",
        "Fixes and tidying.",
      ] },
      { version: "v167", date: "15 Nov 2026", changes: [
        "The models list is now called Wishlist, the same word as the paint status, and the Really want tick is gone. Stages now rolls down inside the top card on Nexus.",
        "Fixes and tidying.",
      ] },
      { version: "v166", date: "15 Nov 2026", changes: [
        "Gear is now protected if the app is open in an older window: the older window asks you to reload instead of saving over it. Undo after deleting a recipe or updating the Palette no longer removes later edits.",
        "Saving falls back to clearing old drafts when storage is full. Fixes and tidying.",
      ] },
      { version: "v165", date: "15 Nov 2026", changes: [
        "Wanted models are now kept in the safety copy and in Recover, and a backup with only wanted models restores. Clearer messages when a backup file is cut off, a file cannot be read, saving is switched off or the app cannot start.",
        "A New version ready bar with a Reload button appears after an update. Fixes and tidying.",
      ] },
      { version: "v164", date: "14 Nov 2026", changes: [
        "Old Undo messages now go when you tap another tab or menu button, and only one shows at a time. The paste result no longer says Owned when it is not, and Keep them no longer says as your own.",
        "Restoring names your current wanted models in its question, and the empty Shopping list says what fills it.",
      ] },
      { version: "v163", date: "14 Nov 2026", changes: [
        "The basket button is always there on Painting pages, so Shopping is easy to find. The models list is now called Wanted.",
        "Pasting notes no longer ticks Owned for you, trims stray quote marks from paint names and keeps every part. Restoring a backup counts as saved, and old Undo messages clear.",
      ] },
      { version: "v162", date: "14 Nov 2026", changes: [
        "On the Wish list, Got it turns a wish into a model at your first stage, with its note, and Undo puts the wish back.",
        "Fixes and tidying.",
      ] },
      { version: "v161", date: "14 Nov 2026", changes: [
        "Rows of tabs that run off the screen now fade at the edge and show an arrow, so the last tab (such as Shopping) is easy to find.",
        "Models has a new Wish list: note models you want, edit them or delete them with Undo. Wishes are not counted anywhere.",
      ] },
      { version: "v160", date: "13 Nov 2026", changes: [
        "In Filters, changing the Game now keeps your faction when that faction has units in the new game.",
        "If it does not, the faction is cleared and a message says so, with an Undo that puts back both the game and the faction.",
      ] },
      { version: "v159", date: "12 Nov 2026", changes: [
        "The Models page has a Sort button with ready-made orders and a Build my own order choice, and units are grouped by game and faction. The Detailed and Simple switch is gone.",
        "Filters now open as a sheet from the bottom, with a button that shows how many units match.",
      ] },
      { version: "v158", date: "12 Nov 2026", changes: [
        "The Dashboard is now called Nexus. Its top card is one card, with the ring showing the percentage over Done, and the stage list folds into a Stages row that starts shut.",
        "The progress graph is now called Progress timeline, and each army doughnut says Done.",
      ] },
      { version: "v157", date: "12 Nov 2026", changes: [
        "Recipes, basing tips and three guides now show a row of colour dots under their title, dark to light, with a ring on wash and glaze steps.",
        "Help explains what the dots are.",
      ] },
      { version: "v156", date: "12 Nov 2026", changes: [
        "The four menu icons have new drawings: Models, Painting, Dashboard and Tools. Credits sections now fold away and the Thanks line is reworded.",
        "The short safety reminder now shows under seven more guides.",
      ] },
      { version: "v155", date: "11 Nov 2026", changes: [
        "A clearer safety note on the Guides home and in Help, and a short reminder under guides about sprays, glue, resin and heat.",
        "Safer advice on spray booths, filters, glue, acetone, heat and hot water.",
      ] },
      { version: "v154", date: "11 Nov 2026", changes: [
        "Mentor now says plainly that it does not know when you ask about something unrelated to painting. Appearance and Themes in Settings starts folded.",
        "The rights line shows once, on About. The privacy page now says a visit-counting change takes effect the next time the app opens.",
      ] },
      { version: "v153", date: "8 Nov 2026", changes: [
        "Pasting an army list now fills in the game when the list names it. A Thanks list of creators is on the About page, and guide pages no longer show numbers.",
        "The Guides home links to the glossary, and the wash or glaze and eyes guides start with clearer lines.",
      ] },
      { version: "v152", date: "8 Nov 2026", changes: [
        "The version number is back at the top of the start circle. Tap it to open Updates.",
        "Fixes and tidying.",
      ] },
      { version: "v151", date: "8 Nov 2026", changes: [
        "The transfers guide now warns that a hair dryer can blow a wet transfer out of place.",
        "Fixes and tidying.",
      ] },
      { version: "v150", date: "8 Nov 2026", changes: [
        "Paint brands in Settings are now tiles you can see all at once, with a tick on the ones that are on.",
        "Fixes and tidying.",
      ] },
      { version: "v149", date: "8 Nov 2026", changes: [
        "About and Credits are now one page, and Settings has seven sections instead of thirteen.",
        "Appearance, Theme, Stages, Mentor look and Colours sit together, and Counting visits and Shop links are inside Your data.",
      ] },
      { version: "v148", date: "8 Nov 2026", changes: [
        "Adding a unit now shows an Undo for ten seconds, and the progress ring says Done with a capital. More guides link to the brush tip, first sessions and waiting between coats guides.",
        "The label reader's credits now name the two image libraries inside it.",
      ] },
      { version: "v147", date: "8 Nov 2026", changes: [
        "The version number is back at the top of every screen and opens Updates. There is a privacy page, and Mentor answers \"how do I paint black armour\" and similar questions with the right guide.",
        "Guides link to each other more, and use \"it's\" in more places.",
      ] },
      { version: "v146", date: "7 Nov 2026", changes: [
        "When one guide fits, Mentor answers with a few lines from it and a Read the guide link. When it is not sure what you meant, it offers two or three guides to pick from.",
        "Fixes and tidying.",
      ] },
      { version: "v145", date: "7 Nov 2026", changes: [
        "Guides now use contractions such as don't, and spell matte, drybrush and undersuit the same way throughout. Wording in some technique guides is plainer.",
        "Fixes and tidying.",
      ] },
      { version: "v144", date: "7 Nov 2026", changes: [
        "Wording in some colour guides and tools and prep guides is plainer.",
        "Fixes and tidying.",
      ] },
      { version: "v143", date: "7 Nov 2026", changes: [
        "Wording in some problem guides, basing tips and detail recipes is plainer.",
        "Fixes and tidying.",
      ] },
      { version: "v142", date: "7 Nov 2026", changes: [
        "Guides now point to a few more related guides, and some safety and oils advice is clearer.",
      ] },
      { version: "v141", date: "6 Nov 2026", changes: [
        "Folds are named by what they open, such as Which one? and What's in it, and Help topics show only an arrow.",
        "Error messages say what went wrong once and what to do next.",
      ] },
      { version: "v140", date: "6 Nov 2026", changes: [
        "Parchment Codex lays its cards out as a ruled ledger and shows notices as a paper slip. Grim Forge has square tags with one cut corner, square stage lamps and a riveted plate for notices.",
        "Paint Bench has masking-tape tags and buttons, pencil-tick stage marks, a tape label on the headline card and a tape strip for notices.",
      ] },
      { version: "v139", date: "6 Nov 2026", changes: [
        "Examples now sit in one thin strip on Models, with plainer made-up names for the sample armies and paints.",
        "Clear examples keeps anything you've changed, and Undo brings the rest back.",
      ] },
      { version: "v138", date: "6 Nov 2026", changes: [
        "The menu icons are hand-drawn, and the Painting and Tools tabs are a row of words with a line under the chosen one that scrolls sideways instead of wrapping.",
        "Armies on the Dashboard show as rows with a switch back to doughnuts, Classic's colours are re-mixed, the loading ring no longer sweeps, and new installs start at On sprue.",
      ] },
      { version: "v137", date: "6 Nov 2026", changes: [
        "Help is shorter: long answers are trimmed, the top card is now The basics, and Match my phone is named as where the app starts.",
        "Mentor now says it looks things up in the guides on your phone.",
      ] },
      { version: "v136", date: "6 Nov 2026", changes: [
        "Mentor's sources are plain links with the guide's title. The scheme check uses ticks and crosses with plain verdicts, the coloured stripes on Guides rows, chips and stage menus are gone, and the version number lives in Updates only.",
        "A unit that reaches Done gets a short message with Undo, with a special line for your first one and for the last of an army.",
      ] },
      { version: "v135", date: "6 Nov 2026", changes: [
        "Plainer wording: empty lists, Dashboard headings, the Palette tile and the delete question. Paint matches now read Close, Near or Not close.",
      ] },
      { version: "v134", date: "6 Nov 2026", changes: [
        "Corners now follow each look: Forge is square and Parchment is nearly square. Classic's corner marks now sit on the headline card and Mentor only.",
        "Things on screen arrive with a soft landing and leave with a quick start, and the start circle now glides into the bar in about half a second. Tapping the bar while it moves skips to the end.",
        "Buttons no longer ripple or lift when you hover, filter chips switch colour at once, and the basket swells a little less.",
      ] },
      { version: "v133", date: "6 Nov 2026", changes: [
        "New installs follow your phone's light or dark setting. If you have chosen Dark, Light or Match my phone before, your choice stays.",
        "On a phone, the Colour Lab scrolls to the next colours when they appear below the screen.",
        "Unused fonts were removed, so the app is a little smaller to download.",
      ] },
      { version: "v132", date: "6 Nov 2026", changes: [
        "The stage names Battle ready and Parade ready are now Tabletop ready and Display ready. If you had not changed your stages, they are renamed for you and your units stay where they were. Older exported files with the old names still import to the right stages.",
        "The Help page is now called How it works.",
        "The feedback card now asks \"Anything missing or broken?\".",
        "How it works has a small Credits link under About.",
      ] },
      { version: "v131", date: "5 Nov 2026", changes: [
        "A new Credits page, straight after About in Tools and Settings, lists the licences for the fonts, the pot-label reader and the paint list. Each licence name opens its full text, which is kept inside the app so it also opens offline. About has a Credits link.",
      ] },
      { version: "v130", date: "3 Nov 2026", changes: [
        "Model cards are compact: each shows its name, game, army and stage. Tap a card to open it with the stage buttons, recipes and Details, and tap its header to close it. One card is open at a time.",
        "Buttons and chips dim the moment you touch them, change colour smoothly and keep their rounded shape when pressed. The square flash some phones drew on a tap is gone.",
        "Switches on Painting, Tools and Settings, Colour Lab and Guides now empty the old choice and fill the new one with colour.",
        "In Colour Lab, pressing a colour on the wheel or in Start from slides the other colours in behind it, and the next set slides out from it. Back plays it in reverse.",
        "Fold-outs unroll and what is below slides down, the Undo message and questions fade away, and Back from a recipe keeps your place in the list. A deleted unit fades out while the cards below glide up, and Undo glides them back. With Reduce motion on, everything still happens at once.",
        "Opening the app shows the loading ring round the start circle again, filling as the app loads. The app icon is now Mentor.",
        "Tapping the start circle no longer flashes a blue square where the bar will be, and the bar fades back in after typing instead of popping.",
        "Tapping the Grounded Mentor in its window sends its paint drops further, in random directions and colours.",
        "Mentor knows more about insect wings, resin prints, lights in models and jungle bases.",
      ] },
      { version: "v129", date: "3 Nov 2026", changes: [
        "Mentor has new looks. Futuristic is a machined hub with an iris, Magical a cluster of crystals inside a slowly turning ring of stones, and Grounded a pool of paint. Tap Mentor in its window for a little surprise.",
        "Opening the app shows the icon ring filling as it loads, then it becomes the start circle. The start circle and the bar change colour smoothly, the bar never disappears on the way down, and the chosen section's colour slides across.",
        "Mentor's window opens more slowly out of its button, and its starter questions sit inside one Suggestions button.",
        "Each look has its own fonts. Parchment Codex has more ink blots, Grim Forge has bolts, cogs and rust, and Paint Bench has brush strokes, smudges and a few stickers.",
        "Guides has 99 new guides, recipes and basing tips, and many older ones are corrected. Back from a guide returns to the list you came from, in the same place.",
        "On a wide screen the start circle shows on its own, and the back arrow sits beside the bar. Hints and Help use made-up names instead of real army and paint names.",
      ]},
      { version: "v128", date: "3 Nov 2026", changes: [
        "Grim Forge is now blackened steel with brushed grain, soot, brass rivets and a forge orange, and bare steel in light mode.",
        "Paint Bench is a calmer hobby desk: lighter, warmer colours, a quieter cutting mat and paler masking tape.",
        "Easier to read in every theme: hints inside empty boxes, pressed buttons in Parchment Codex dark and the label on the round Mentor button.",
        "Models opens much faster on a long list, and a stage tap, a rename, a delete or an Undo now redraws only the card it changed.",
      ]},
      { version: "v127", date: "3 Nov 2026", changes: [
        "Ask Mentor now opens out of its round button, and Mentor sits larger above the questions. The start circle's four sections match the bar: Models and Painting on top, Dashboard and Tools below.",
        "Guides: entries that need something to buy have a Where to buy fold-out with plain shop searches and Add to shopping list. Gear has its own section on the shopping list.",
        "Colour Lab: Start from shows your own paints first, Done picks the first match as you type, and colour ideas never suggest a primer or an ink.",
        "The scheme form fills in the faction from your recipes, has Search recipes, groups recipes by part with Select all, and says when another scheme already goes onto new units in that faction.",
        "Guides: Detail recipes and Basing have numbers like the other sections, and a Filters button folds their group buttons away.",
      ]},
      { version: "v126", date: "3 Nov 2026", changes: [
        "Mentor has three looks to choose from in Settings: Futuristic, Magical and Grounded. In its window it shows when it is thinking, pleased, unsure or finished.",
        "The app no longer looks frozen while it opens: the start circle and its ring show straight away and fill up as the app loads.",
        "Mentor understands more everyday ways of asking, such as paint water, paint on your clothes, fumes, lumpy or streaky paint, photos and a first model.",
        "CSV import reads files split by semicolons or tabs and a Status column, and its messages stay until you close them. Text follows your phone's text size, labels no longer break on small screens, and Skip to content is the first Tab stop.",
        "Quicker taps: only the section you are looking at is redrawn. The storage line counts everything the app keeps, a full phone offers to remove safety copies, and the offline copy no longer grows or keeps a broken font. \"Last backup\" now counts days correctly around the clock change.",
      ]},
      { version: "v125", date: "3 Nov 2026", changes: [
        "Mentor copes with typing slips, offers Did you mean when it is not sure, says when it does not know, and answers simple questions about the app.",
        "Paste recipes: Check paints shows one card for each paint that needs a look, nothing stops you saving, and a tick box sets whether new paints are marked Owned.",
        "Army lists pasted from list builders read their units, counts and faction properly, and lines that can't be read are listed. A paint typed in the recipe editor that the app does not know gets no status.",
        "The first tap on a button near the bottom bar now works, Not now on a kept recipe opens the new recipe, and the start circle's labels keep their font as they move into the bar.",
      ]},
      { version: "v124", date: "3 Nov 2026", changes: [
        "Safer saving: if your saved units or recipes can't be read, saving pauses instead of replacing them, so you can save them as a file or start again. Recover keeps units and recipes together, a restore stops if there's no room for its safety copy, Undo takes back only its own change, and the offline copy never mixes old and new versions.",
        "Safety fixes: a backup can only bring in JPEG, PNG or WebP photos, other websites can no longer show Minifolio inside their pages, very long names are cut to the usual limit, and a broken web address no longer stops the app starting.",
        "The shopping list has a closed Suggested section with your Empty paints and the Not owned paints your recipes use, each with Add and ✕. In Colour Lab's Colour ideas, Add to shopping list is now on the row of a paint you don't own.",
        "Themes: Classic has a cold sci-fi look with an ice cyan accent, a technical font and thin panel lines. Blueprint and Rulebook are gone; if you used one, the app now shows Classic.",
        "Parchment Codex now looks like red ink on old paper, with grain, ink blots and stained edges. In dark mode it is aged parchment by candlelight.",
        "Help says guides and Mentor give general hobby tips, so always follow the maker's label. Help > About links to the font licences.",
        "Guides: a Topics | A to Z switch shows every guide in one list, search results show each guide's number, and some guides end with links to related guides.",
        "Guides has 12 new entries (such as painting blue, green, brown and grey, horses, drying times and using Colour Lab) and six new hair and horse coat detail recipes, and Mentor can answer questions on them.",
      ]},
      { version: "v123", date: "2 Nov 2026", changes: [
        "+ New recipe now opens a quick form: type or paste lines like Eyes: bright yellow, then pale yellow and check the preview. A paint the app does not know is outlined and kept as typed. More options holds the name, part and each step's technique, coats, brand and note, and a technique you pick there stays when you change the paint. After saving, Do you own these? lets you tick the paints you have.",
        "Import CSV can now read two optional dates for each unit: date_added (when it joined your collection) and date_stage (when it reached its stage), as 2026-11-02 or 02/11/2026. The progress graph then shows your collection's real history instead of starting on the day you imported. Export CSV and the CSV template have the two new columns too.",
        "Guides: Colour basics, Techniques, Tools and prep and Problems now open on topic groups, then the entries in each group, all in A to Z order. Each row has a small number (like 2.3.4) so you can find your place, and Back goes up one level at a time.",
      ]},
      { version: "v122", date: "2 Nov 2026", changes: [
        "New About page in Tools and Settings, with what Minifolio is and what it is for. The start page has a new short line under the name.",
      ] },
      { version: "v121", date: "2 Nov 2026", changes: [
        "Parts and techniques moved to Settings, under Recipe preferences. Removing one now asks first and has Undo. Recipes keep the part or technique they use even if you remove it from the list.",
      ] },
      { version: "v120", date: "2 Nov 2026", changes: [
        "Pasting recipes no longer fills the Part list with near-duplicates. A heading in your notes uses a Part you already have (capitals, spaces and a trailing s are ignored). Only a heading with no match is added as a new Part, once. Quote marks left round a new paint's name are removed.",
      ] },
      { version: "v119", date: "2 Nov 2026", changes: [
        "Duplicate recipe now has its own title and adds \"copy\" to the name. Saving Colour ideas into a new recipe now keeps your starting paint as step 1 and sets the part and a name.",
      ] },
      { version: "v118", date: "2 Nov 2026", changes: [
        "A recipe now has one small Edit button by its name. It opens a short list: edit the steps and paints, duplicate, copy as text or delete. Each step shows its paint and technique, for example Bright yellow, Layer. Used on is folded and shows how many units. A new Add to scheme button, next to Add to shopping list, lets you tick which schemes hold the recipe; changes apply when you press Done.",
      ] },
      { version: "v117", date: "1 Nov 2026", changes: [
        "A grey square no longer flashes over the round Ask Mentor button, or the back arrow, basket and Mentor window buttons, when you tap them. The keyboard focus ring on Ask Mentor is now clearer.",
      ] },
      { version: "v116", date: "1 Nov 2026", changes: [
        "Mentor now starts fresh after 30 minutes without use, and has a Back button (an arrow, top left) that takes you back to the start. Mentor's window is also taller on a phone, so more of the chat shows.",
      ] },
      { version: "v115", date: "1 Nov 2026", changes: [
        "The start page now has a short line under the name and no longer shows the version number (it is still in Updates). Help starts with a card called 5 things to know. The Dashboard says what Done means, and the progress graph and Palette tiles stay out of the way until you have a unit or a paint. The Game and Faction boxes now select their text when you tap them, and have an x to clear them.",
      ] },
      { version: "v114", date: "1 Nov 2026", changes: [
        "A round back arrow now sits at the bottom left of the screen. Tap it to go back to the start page, the same as tapping the Minifolio title. It hides on the start page and while things are moving.",
      ] },
      { version: "v113", date: "1 Nov 2026", changes: [
        "Fixed a handful of small things. One unit now reads \"1 unit\" instead of \"1 units\". A message that has run out of time no longer lingers when the phone wakes up. A kept unfinished unit is offered once, by the card at the top of Models, instead of twice. Unit name, game and faction boxes stop at 80 characters (longer ones you already have still load and show unchanged). Every message with an Undo button now stays for 10 seconds. The four start-circle segments now arrive clockwise: Dashboard, Models, Tools, Painting.",
      ] },
      { version: "v112", date: "1 Nov 2026", changes: [
        "Pro preview labels moved. The Colour Lab page, the colour wheel and everything you track yourself no longer carry one. Guides, Colour ideas, Colour plans and Paint Picker show a small PRO PREVIEW tag at the right of their row, and Guides says it is free while in preview. Nothing is locked and nothing works differently.",
      ] },
      { version: "v111", date: "1 Nov 2026", changes: [
        "Fixes: the Ask Mentor label is no longer cut off at the bottom, the last card scrolls clear of the menu, Mentor questions wrap instead of running off the side, the Guides search box is full width, and leftover sample tips are gone.",
      ] },
      { version: "v110", date: "31 Oct 2026", changes: [
        "Tapping the Minifolio title now sends the bottom bar's four sections and the Ask Mentor button travelling back up into the start circle, the same journey in reverse. With reduced motion on, it fades quickly instead.",
      ] },
      { version: "v109", date: "31 Oct 2026", changes: [
        "Tapping a section on the start circle now sends the four sections and the Ask Mentor button travelling down together into the bottom bar, and the section opens as they land. With reduced motion on, it swaps at once.",
      ] },
      { version: "v108", date: "31 Oct 2026", changes: [
        "When you open the app fresh, a ring of three coloured arcs fills around the Ask Mentor button on the start circle, and the four sections appear one by one as it fills. It takes about a second and a quarter. With reduced motion on, the circle shows at once.",
      ] },
      { version: "v107", date: "31 Oct 2026", changes: [
        "Help now describes the menu, Colour Lab, Guides and Mentor as they are today, and Help > Privacy says Mentor runs on your device: what you type is not sent or stored, and the chat is cleared when the app reloads.",
      ] },
      { version: "v106", date: "31 Oct 2026", changes: [
        "Long lists are shorter on a phone: Guides shows 30 rows at a time with Show more, Detail recipes and Basing open on one group, and the Colour ideas card shows the first few.",
      ] },
      { version: "v105", date: "31 Oct 2026", changes: [
        "Mentor understands far more ways of asking.",
      ] },
      { version: "v104", date: "31 Oct 2026", changes: [
        "Guides now has over 600 entries, plus 119 new detail recipes and 48 new basing tips.",
      ] },
      { version: "v103", date: "30 Oct 2026", changes: [
        "Mentor's sources now take you to the exact guide, recipe, tip or colour on the Colour Lab wheel.",
      ] },
      { version: "v102", date: "30 Oct 2026", changes: [
        "Mentor now answers. Type a question or tap a chip in Mentor's window. Mentor replies from Guides and the colour rules, shows paint ideas with the usual buttons, and lists its sources. What you type is not saved or sent, and the last 30 messages are forgotten when you close the app.",
      ] },
      { version: "v101", date: "30 Oct 2026", changes: [
        "Mentor now has an answer engine behind the scenes. It finds the right guide, recipe or tip for a question, and suggests paints for a colour and a part of the model. You cannot see it yet; the typing box comes next.",
      ] },
      { version: "v100", date: "30 Oct 2026", changes: [
        "Ask Mentor now opens a small Mentor window over whatever you are on, with a Paint Picker chip that takes you to Colour Lab. The Picker is now called Paint Picker.",
      ] },
      { version: "v99", date: "30 Oct 2026", changes: [
        "The Dashboard has a Palette card: a colour strip of the paints you have, which colours are missing (marked Gap), your most used paint and your paint counts. Tap it to open Your Palette. There is also an Achievements card, held for later.",
      ] },
      { version: "v98", date: "30 Oct 2026", changes: [
        "Guides is now a library. Search it, or pick a category (Colour basics, Techniques, Detail recipes, Basing, Tools and prep, Problems) and open an entry. Detail recipes and Basing work as before.",
      ] },
      { version: "v97", date: "30 Oct 2026", changes: [
        "The fourth menu section is now Tools. It opens Tools and Settings, which has four pages: Guides (the detail recipes and basing tips, which moved here), Settings, Help and Updates. The cog at the top is gone; the basket stays.",
      ] },
      { version: "v96", date: "29 Oct 2026", changes: [
        "Painting has a new Colour Lab, with the colour wheel, Colour ideas, Colour plans, Colours you've used and the Picker. The round Ask Mentor button opens the Picker. Detail recipes and Basing tips stay where they were for now.",
      ] },
      { version: "v95", date: "29 Oct 2026", changes: [
        "Example recipes and schemes now say so above their name. A scheme card lists its recipes as rows you can tap, with the part, the steps and the colours. A scheme with more than 3 recipes has Show all.",
      ] },
      { version: "v94", date: "29 Oct 2026", changes: [
        "Starter schemes are now called Colour plans, and Your schemes is now Colours you've used, so scheme only means a bundle of recipes. A new closed box, Recipe or scheme? What's the difference, is at the top of Painting > Recipes and Painting > Schemes, and in Help. Words only: your recipes, schemes and backups are untouched.",
      ] },
      { version: "v93", date: "29 Oct 2026", changes: [
        "Tapping a section on the start circle now glides into the menu bar, and going back to the start page glides the other way. Nothing moves if your phone is set to reduce motion.",
      ] },
      { version: "v92", date: "28 Oct 2026", changes: [
        "Moving between sections now slides in the direction you are going, and opening a recipe slides over the list.",
      ] },
      { version: "v91", date: "28 Oct 2026", changes: [
        "Similar paints can now suggest a paint blend. When none of your paints is close, Your closest may show Try mixing: one or two mixes of two paints you own, with the parts to use, next to the colour you want. It is a rough guess from screen colours, so test it on a palette first. Add to recipe step puts the two paints and the ratio into a recipe step, with an Undo. Metallics, washes, shades, Contrast, glazes and other special paints are never mixed.",
      ] },
      { version: "v90", date: "28 Oct 2026", changes: [
        "The round Ask Mentor button now shows Mentor's orb, matching your theme's colours.",
      ] },
      { version: "v89", date: "28 Oct 2026", changes: [
        "The app now opens on a start page: your four sections in a circle around Ask Mentor. Tap one to go in, and tap the Minifolio title any time to come back to it. Switching to another app and back leaves you exactly where you were.",
      ] },
      { version: "v88", date: "28 Oct 2026", changes: [
        "The menu is now a curved bar at the bottom around a round Ask Mentor button. The Units tab is now called Models. Settings is the cog at the top right, and the shopping basket sits beside it. Ask Mentor opens the Paint Picker.",
      ] },
      { version: "v87", date: "28 Oct 2026", changes: [
        "Unit cards now move a little when you change a stage: the stage name slides, the colours fade across and the card pulses once on the way up. Details opens and closes smoothly and the paint swatches pop in.",
      ] },
      { version: "v86", date: "28 Oct 2026", changes: [
        "Things now move a little when you use the app: buttons lift and ripple, the filter chips fill in, the question box and Undo message slide in, and a new unit drops into the list. If your phone is set to reduce motion, none of it moves.",
      ] },
      { version: "v85", date: "28 Oct 2026", changes: [
        "Each model in a unit you track model by model now has back and up buttons next to its stage name, with a thin progress bar and the date it got there. The stage menu on each row has gone. Use Move all models to stage for big jumps.",
        "New Detailed and Simple switch on the Units tab (it shows once a unit is tracked model by model). Simple leaves out the dates and bars.",
        "Units of more than 8 models group their rows by stage. Tap a stage to open or close it.",
        "Track as one batch has an Undo that puts every model back exactly.",
      ] },
      { version: "v84", date: "28 Oct 2026", changes: [
        "The Recipes tab is now called Painting. Inside it, Recipes and Schemes keep their names. Help and the empty lists now say what each is: a recipe is your own step-by-step for a model; a scheme is a colour plan or idea you can save into a recipe.",
        "The screen reader names are clearer. A unit with models at different stages now says so when you select it, Edit details is announced as a button, and Delete says which unit it will delete. \"1 models\" now reads \"1 model\" everywhere.",
      ] },
      { version: "v83", date: "28 Oct 2026", changes: [
        "Each unit card now has a clear Details button, and a stage bar under the name with a back arrow on the left and an up arrow on the right. Both move the unit one stage and both have an Undo. The old stage button and the small Back a stage button are gone: open Details and use Jump to stage. Details also has a Paints row that opens the unit's full set.",
        "Every paint on the Shopping list now has a Remove button, with Undo. It takes only that paint off the list.",
        "Every recipe now has an Add to shopping list button under its steps. On a recipe with only made-up example paints it is greyed out and says why.",
        "Tick a paint on the Shopping list when you have bought it. It turns grey, then moves to Bought at the bottom, and Your Palette marks it Owned in every recipe. Open Bought to put a paint back with Add back, or tap Clear bought to forget the list. Bought paints are included in backups.",
        "Turning a paint brand on or off no longer sends you back to the start of the row or the top of the page. This is in Your Palette and in Settings, and in other rows of buttons too.",
        "Pasted recipe notes can now have sections. A short line like Heraldry with paints under it is guessed to be a section heading, and its paints become their own recipe. Tap the pencil on any line and choose Paint step, Section heading or Ignore to change the guess.",
        "The progress graph now shows dates like Mar 2025 and leaves out dates that would crowd each other.",
        "Add unit remembers the last game and faction you used.",
        "Settings, Your data says Works offline once the app is ready without internet.",
      ]},
      { version: "v82", date: "28 Oct 2026", changes: [
        "Wide screens: the Dashboard, the recipe page opened from Schemes, Paste recipes, the scheme editor and the colour wheel now use the space better. Show as a table is now an easy-to-tap size on phones too.",
      ]},
      { version: "v81", date: "27 Oct 2026", changes: [
        "On a wide screen, the Shopping list now has the shop links and Copy as text on one side and the paints on the other, and Colour Lab has the colour wheel on the left and its sections on the right. Phones are unchanged.",
      ]},
      { version: "v80", date: "27 Oct 2026", changes: [
        "On a wide screen, Your Palette now opens a paint's details in a pane beside the list. You can keep several open at once and close each one. Phones are unchanged.",
      ]},
      { version: "v79", date: "27 Oct 2026", changes: [
        "On a wide screen, a unit's details now open in a pane beside the list. You can keep several open at once and close each one. Phones are unchanged.",
      ]},
      { version: "v78", date: "27 Oct 2026", changes: [
        "On a wide screen, opening a recipe now shows it beside the list, so you can pick another without going back. Phones are unchanged.",
      ]},
      { version: "v77", date: "27 Oct 2026", changes: [
        "Groundwork for wider screens: pages can now sit side by side from 900 px wide. Phones look and work the same. The Updates page on a wide screen is the first to use it.",
      ]},
      { version: "v76", date: "27 Oct 2026", changes: [
        "Very long recipe and paint names now wrap onto more lines instead of making the page scroll sideways.",
        "If Restore backup lowers any unit's model count to the 999 limit, it now tells you how many were changed.",
      ]},
      { version: "v75", date: "27 Oct 2026", changes: [
        "Less small print. Many hints are shorter or gone: on the Dashboard, shopping list, Colour ideas, Colour Lab, the paint scanner, the paste-recipes preview, Settings (Backups, Import, Counting visits, Shop links) and Help. Nothing you can do has changed.",
        "The notes on Counting visits and Shop links in Settings now just say On or Off. The full explanation is in Help, Privacy, which is split into three shorter points.",
        "The note under the Dashboard graph about units added before dates were recorded is shorter.",
        "The ✕ and ✎ buttons in the paste-recipes preview are now 44 px, big enough to tap easily, and screen readers read them with the step they belong to.",
      ]},
      { version: "v74", date: "27 Oct 2026", changes: [
        "Each unit card has a new stage button (⇅) beside the ▲. Press it and pick a stage to go straight there, for example Parade ready, instead of tapping ▲ again and again.",
        "The ▲ now does the same on every unit: it moves the whole unit up one stage. On a unit tracked model by model, every model moves up one. Both have an Undo.",
      ]},
      { version: "v73", date: "27 Oct 2026", changes: [
        "Each paint pick in the Paint Picker now has Add to shopping list in plain view, next to Use in a recipe, Add to a recipe and Similar paints. Each one says what it did and has an Undo.",
        "Add to shopping list stays there even if you switch Shop links off in Settings. Paints you own and made-up example paints don't get it.",
      ]},
      { version: "v72", date: "27 Oct 2026", changes: [
        "The Paint Picker now shows tips for the part you chose under the paint picks, each with its colours and, where it has one, a link to the creator it credits. A tip about your chosen colour comes first.",
        "The tips there are samples for now. Real tips will replace them later.",
      ]},
      { version: "v71", date: "27 Oct 2026", changes: [
        "Paint Picker (Pro preview): in Colour Lab, choose a base colour, a second colour and a part (armour, eyes, weapon or base). You get paints that go with each colour for that part, with the reason. Your own paints come first, and a poor match you own says Yours, poor fit.",
        "Mentor tips will join these picks in the next update.",
      ]},
      { version: "v70", date: "26 Oct 2026", changes: [
        "Behind the scenes: a place for Mentor tips is ready, with three sample tips that only show the format. Nothing new to see yet.",
      ]},
      { version: "v69", date: "26 Oct 2026", changes: [
        "Ideas for this: open a recipe step or a paint in Your Palette and tap Ideas for this. Colour Lab opens with that paint's ideas at the top: colours that go with it, starter schemes, detail recipes and basing tips with a similar colour, using your paints first.",
        "Show steps or Show tip opens that detail recipe or basing tip in full. Back to recipe or Back to Your Palette takes you to the same place. A paint with no colour set has no button.",
      ]},
      { version: "v68", date: "26 Oct 2026", changes: [
        "The stage Painted with issues is now called Needs touch-ups: painted and on the table, with a few bits to fix before Parade ready. Your units stay where they were.",
        "This happens if you hadn't changed your stages, and also when you restore an older backup with the old list. If you had changed them, your names stay as you set them.",
        "Help explains the stage, under Stages and Done.",
      ]},
      { version: "v67", date: "26 Oct 2026", changes: [
        "The shopping list only holds paints you put there: Wishlist paints and anything you add with an Add to shopping list button. Paints a recipe uses that you don't own, and paints that are empty or running low, are no longer added by themselves. They still show as Missing on the recipe.",
        "A recipe with missing paints has an Add missing paints to shopping list button under its steps. It adds only real paints you don't own, says how many, and has an Undo.",
        "Do you own these? now names the paints it means, and a half-typed paint name no longer brings it up.",
        "Save stops and says which step has a brand but no paint name, instead of dropping it. A step with no paint says No paint on its line.",
        "The empty paint box now just says Paint name.",
      ]},
      { version: "v66", date: "25 Oct 2026", changes: [
        "Similar paints now has a second card, Your closest: the nearest paints you own, with the same fit words. It follows Lighter, Close and Darker too.",
        "If your closest paint is already the best match, only Best match shows. If none of your paints is close, Your closest says so. With no paints of your own, only Best match shows.",
        "On a phone the two cards are tabs, Best and Yours. On a wider screen they sit side by side and the pop-up is wider.",
      ]},
      { version: "v65", date: "25 Oct 2026", changes: [
        "New Similar paints button on a paint in Colour Lab. It opens a pop-up with Best match: up to three paints from different brands, closest first, whether or not you own them, each with its fit.",
        "Lighter, Close and Darker at the top of the pop-up look for a lighter or darker colour. Close is the default.",
        "A paint you do not own can go on your shopping list from the pop-up, with an Undo. Paints that are not colours, such as varnishes, mediums and thinners, are never offered.",
      ]},
      { version: "v64", date: "25 Oct 2026", changes: [
        "Suggested paints now show how well they fit: Good fit, Okay fit or Poor fit. The same rule is used in Colour ideas, starter schemes, detail recipes, basing and the colour wheel panel.",
        "A paint you own comes first only when it is a Good or Okay fit. If your best paint is a poor fit, the closest paint overall comes first and your own paint is second, marked Yours, poor fit.",
        "The Opposite of a dark colour in the colour wheel panel is now a clear orange or gold instead of a brown.",
        "The sentences under suggested paints, such as Closest you own and Similar, not exact, have gone. Only the labels are left.",
      ]},
      { version: "v63", date: "24 Oct 2026", changes: [
        "In the Colour Lab colour wheel, each group now shows 12 paints before Show all (it was 8).",
        "After your own paints, paints from popular ranges come first, so the short list is not filled with brands you may not know. The rest are still there under Show all.",
      ]},
      { version: "v62", date: "24 Oct 2026", changes: [
        "A paint in Colour Lab (a colour idea, or a colour wheel paint once you open it) has two buttons. Use in a recipe starts a new recipe with that paint in step 1. Add to a recipe lets you pick a recipe, then one of its steps or a new step. Both have an Undo.",
        "If the paint is not in Your Palette yet, it is added as Not owned, so it reaches your shopping list once a recipe uses it, and the message says so. Made-up example paints are not offered.",
      ]},
      { version: "v61", date: "24 Oct 2026", changes: [
        "A unit with more than one model has a Track models separately button in its details, under the stage. One tap shows every model with its own stage, each with back and up buttons. Track as one batch goes back. Both have an Undo.",
        "The old tick for this in Edit details has gone, as the button does the same job.",
      ]},
      { version: "v60", date: "24 Oct 2026", changes: [
        "Importing an army list now reads the model count written on a unit's line, such as 10x Goblins, Goblins x10 or Goblins (10 models), so units no longer land as 1 model. A list typed by hand, one unit per line, works too.",
        "In the import check, every unit has its own model count and stage. Set every row to puts them all at one stage in one go, and stays in view on a long list. This works for Import CSV as well as army lists.",
        "A CSV file's stage column is used when it matches one of your stages.",
      ]},
      { version: "v59", date: "24 Oct 2026", changes: [
        "Shorter wording on empty screens, the feedback card and a few hints. Nothing else changed.",
      ]},
      { version: "v58", date: "24 Oct 2026", changes: [
        "The made-up example paints, such as Example deep blue, no longer show on the shopping list or in Copy as text, even after Keep them. No shop sells them.",
        "A recipe that only uses example paints now says Uses example paints instead of Missing.",
        "An example paint's More options on Your Palette has Swap for a real paint: pick a real paint and every recipe using the example uses it instead. Undo puts it back.",
      ]},
      { version: "v57", date: "23 Oct 2026", changes: [
        "Once you have a few units or a recipe of your own, the Dashboard asks, once, whether you'd like to save a backup. Save backup saves the same file as in Settings, and Not now hides the card for two weeks. It asks again when your last backup is a month old and you've changed things since.",
        "Settings \u2192 Backups says when your last backup was, right under Save backup, or Never.",
      ]},
      { version: "v56", date: "23 Oct 2026", changes: [
        "Clear examples now clears all the examples in one go: the example units, recipes, schemes and paints. The message says what was cleared, and Undo brings all of it back.",
        "Keep them now keeps all the examples as your own, so the These are examples card goes away on the Dashboard, Units, Recipes and Your Palette.",
      ]},
      { version: "v55", date: "20 Oct 2026", changes: [
        "The small labels on recipes, Colour ideas and Colour Lab are now plain text instead of rounded pills: the part name on a recipe, Fine, Look at this and Suggestion, and Pro preview. The words are the same.",
        "Screen readers now read a paint's own name on the buttons and boxes that act on it, such as Remove, More options, the colour box, Merge, Shop links and the swatch tiles, instead of a longer label that repeated the name.",
      ]},
      { version: "v54", date: "20 Oct 2026", changes: [
        "On the Updates page, each entry shows its version and date, and its lines are behind More info. The newest entry starts open and the rest start shut.",
        "In Settings, Stages, Import and Your data now fold shut when you open the app, like Faction colours and Paint brands. Tap the heading to open one. Delete all units is still inside Your data.",
        "Buttons that are switched off, such as the reorder arrows at the ends of the stage list and Clean up photo storage when there is nothing to clean, are easier to read.",
      ]},
      { version: "v53", date: "20 Oct 2026", changes: [
        "Buttons, text boxes and menus are now all at least 44 px tall, and the small tap targets are bigger: the stage bars on the Dashboard, link buttons such as + Add part and Back, the Open recipe and Go to unit chips, Unlink, and the basket in the tab bar.",
        "Parts and techniques, Edit details and Colour ideas now look like the Help topics, with More info and Less info. These folds, and the Add unit button, also tell screen readers whether they are open.",
        "Help starts with every topic closed.",
        "Four short notes moved behind More info: the Paste recipes introduction, what a scheme is on an empty Schemes page, the colour wheel caption, and the light mode note in Settings.",
        "On iPhone, the Keep your data safe card keeps its warning and the reason in view. The Add to Home Screen steps are behind More info.",
        "In Settings, Faction colours and Paint brands are folded shut when you open the app. Tap the heading to open one.",
        "The red banner shown when saving fails now follows your theme colours.",
      ]},
      { version: "v52", date: "20 Oct 2026", changes: [
        "The Shopping list is tidier. Your paints, the Copy as text button and the basket count stay in view. The explanations (what the list holds, the no-statuses warning and how the shop buttons work) are behind one More info.",
        "Settings is tidier. Each card keeps its buttons and switches in view, and its explanation sits behind a More info. Backups stay big and easy to reach.",
        "On the Dashboard and Units, the note about the example units is behind More info.",
        "Help topics use the same More info and Less info words and the same arrow. Help also has new lines for the Swatches switch and More options, the folded steps in recipes, and the Colour Lab and Guides tick boxes with Select all and Add to shopping list.",
      ]},
      { version: "v51", date: "20 Oct 2026", changes: [
        "In Colour Lab and Guides, the paints in Starter schemes, Your schemes and Detail recipes now have a tick box on the left, and a Select all row above each list.",
        "Add to shopping list sits under the list. It is small and grey until you tick something, then it turns into a full-width button that shows how many paints it will add. It adds only the ticked paints, and one Undo takes them all off again.",
        "Copy as text and Save into a new recipe use the paints you ticked. If nothing is ticked they use all of them.",
        "Paints you own, or that are already on your shopping list, show their status mark where the tick box would be. Open More info on the row to see why.",
        "The small Shopping list heading under each scheme is gone, because the tick boxes do the same job.",
      ]},
      { version: "v50", date: "20 Oct 2026", changes: [
        "Recipes are less busy. A recipe card shows its name and colour dots, plus a short Have all or Missing line once you have marked your paints. The part, step count and units are behind More info.",
        "Each step in a recipe is one line: its number, technique and small colour dots. Tap it to open the step. Coats, mix ratio, note and optional are under More options inside the open step. Add step and Save recipe stay in view.",
        "Have and Missing now use the same small tick and cross marks as Your Palette, with a one-line key. The What can I paint now? hint, the Parts and techniques note and the other long explanations on the Recipes tab are behind More info.",
      ]},
      { version: "v49", date: "19 Oct 2026", changes: [
        "Less busy: long explanations now sit behind a small More info button. In Colour Lab and Guides, each paint row has its own, and so does each page's introduction.",
        "Your Palette has a List | Swatches switch. Swatches shows every paint as a small colour tile with a mark for its status (tick, half circle, ring, star, cross) and a key above. Tap a tile to open that paint. Name, brand, Merge and Remove are now under More options.",
        "On Units, To do, Done and Repaint are three equal buttons, and the stages open underneath once you pick one (or tap Pick by stage). In Colour Lab and Guides, the shopping list and Copy buttons stretch across the card, and the shopping list button is greyed out until you pick a scheme.",
        "Groups of option buttons (paint status, the stage filters, Paint brands and the rest) now always sit on one row. When a group is too long for the screen, it scrolls sideways: a fade shows there are more, and your choice is always in view.",
        "Scanning a pot label works properly with all the new paints: every Vallejo code number is read (Model Air, Game Air, Mecha and the rest), Tamiya codes like XF-1 are read on Tamiya pots, and a Citadel label gives the same answer as before the new brands arrived.",
      ]},
      { version: "v48", date: "19 Oct 2026", changes: [
        "About 2,800 more paints the app knows by name: Warhammer Tone Pro (all 30 colours in their five tones, 1 to 5), Scale 75, Formula P3, Two Thin Coats, Tamiya and Green Stuff World, plus every range of Citadel, Vallejo, The Army Painter, Pro Acryl and AK Interactive (Speedpaint, Model Air, AK figures and more). They're suggested as you type, matched when you paste recipes or scan a pot, and used in Colour ideas.",
        "New in Settings: Paint brands. Switch off the brands you don't use, and their paints stop being suggested and matched. Your own paints are always included.",
      ]},
      { version: "v47", date: "19 Oct 2026", changes: [
        "New in Settings: Theme. Choose Classic (the usual look), Blueprint, Parchment Codex, Grim Forge, Paint Bench or Rulebook. Each has a dark and a light version, so it works with your Appearance setting, and your choice is saved in backups.",
      ]},
      { version: "v46", date: "18 Oct 2026", changes: [
        "Links can now end in a short tag, like minifolio.app/?from=club, so the visit count can tell where a visit came from. Only that one short word is sent, only when Counting visits is on, and it is never saved.",
        "The Dashboard now shows how many models are under way, so a collection that is built and primed no longer reads like nothing has happened.",
        "The \u25B2 button is now always the same bright blue, so a new unit's button no longer looks switched off.",
        "New in Settings, under Backups: Send full backup with photos to\u2026, which opens your phone's share menu with the full backup, like Send backup to\u2026 does for the small one.",
      ]},
      { version: "v45", date: "18 Oct 2026", changes: [
        "The Updates page now shows only the latest five versions, so it is quicker to read.",
        "Help \u2192 Privacy now names the site's current host, and the Updates part of Help matches the shorter list.",
      ]},
      { version: "v44", date: "18 Oct 2026", changes: [
        "A brand-new start now comes with five example recipes (armour, metal, skin, eyes and a base) and two example schemes that group them, all with plain made-up colour names and linked to the example units. The card on the Recipes tab still has Clear examples (with Undo for 8 seconds) and Keep them, and now covers the example schemes too. Anything you edit, use in your own recipe or give a status is kept as yours, and example paints never go on the shopping list.",
        "New in Settings, under Your data: Restore example recipes. It adds the examples back for anyone, including people who started before, without changing your own recipes, schemes or paints and without adding any twice. The card on the Recipes tab then shows again.",
      ]},
      { version: "v43", date: "18 Oct 2026", changes: [
        "The colour wheel now opens up. Tap red, orange, yellow, green, blue or purple and the picture is redrawn as that colour's three groups (for example Deep reds, Reds and Pinks), each a big labelled segment with its name outside the ring. Tap a group to see its paints below the picture (yours first, dark to light, with Show all and Copy as text), and tap it again to close it.",
        "To go back up, tap the Back button in the middle of the picture, the Back to all colours button under it, or press Escape. The grey middle (whites, greys, blacks and metallics) works as before. Which colour and group are open is kept while the app is open. Everything works with a keyboard and a screen reader, which says when the level changes.",
      ]},
      { version: "v42", date: "18 Oct 2026", changes: [
        "In Colour Lab, Starter schemes and Your schemes each have a small closed Shopping list heading under their paints. Open it and tap Add paints to shopping list to put every paint of that scheme you don't own on your shopping list in one go. Paints you own, or have running low, are left out, and paints already on the list are not added twice.",
        "Each paint remembers the scheme it came from (for example \"Scheme: <name>\"). The message says how many were added, and one Undo puts them all back. If nothing needed adding, it says so. It uses the same shopping list as everything else, and the basket count and \"On your shopping list\" marks stay right. It stays when Shop links is switched off, because it only adds to your own list.",
      ]},
      { version: "v41", date: "18 Oct 2026", changes: [
        "Your shopping list now remembers where a paint came from. Adding a paint from the colour wheel's matching colours says \"Colour Lab: Colour wheel\" and the colour part you were in (for example Blue). Adding from Colour ideas says \"Colour Lab: Colour ideas\". It is the same list the Recipes tab uses, and a paint is still on it once.",
        "A paint that is already on your shopping list now says \"On your shopping list\" on its row in Colour Lab (in the colour wheel's lists and matching colours, and in Colour ideas). It updates when you add a paint or tap Undo.",
      ]},
    ];
