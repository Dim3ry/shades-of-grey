// ===== app.js: all of Minifolio's code (how things BEHAVE) =====
// v21.4: this used to sit inside index.html between <script> tags. It moved into its own file
// so the security policy can refuse ANY code written inside the page: if someone ever slipped
// code into the page, the browser wouldn't run it. Nothing in here changed when it moved.
// It's loaded at the very bottom of index.html, after everything you see, exactly where the
// old <script> block was, so it runs at the same moment as before.

    // ===== JavaScript: this section is how things BEHAVE. =====
    // Lines starting with // are comments.

    // The names we save under in the browser's storage, like file names.
    const STORAGE_KEY = "mini-tracker-models";
    const SETTINGS_KEY = "shades-of-grey-settings";
    // v14: the most models a unit can have. A huge number like 150,000 used to freeze the
    // app. Tracking each model separately draws a row per model, so that's limited to 100.
    // (Up here because units are loaded and checked before the rest of the script runs.)
    const MAX_MODELS = 999;
    const MAX_EACH = 100;

    // ================= SAVING SAFELY (v14) =================
    // Browser storage has no "all or nothing" save, so writeTogether() does it by hand:
    // it notes what each name held before, writes the new values one by one, and if one
    // fails (usually because storage is full) it puts back the ones already written.
    // So units, recipes and settings never get out of step with each other. (Before v14
    // the stage list could be saved without the units, which moved every unit to the
    // first stage the next time the app opened.)
    // entries is a list of [name, text] pairs. Returns false only if storage is FULL.
    let holdSaves = false;   // true while showing changes made in another window (see below)
    let saveFailing = false; // true while saving isn't working, so the red banner stays up

    // ----- Data version number (v18.3) -----
    // A number saved with your data (in the settings, and in backups) that says which "shape"
    // of data this copy of the app writes. Raise it by 1 whenever a future version saves data
    // in a way older copies wouldn't understand. If an OLDER copy of the app (say an installed
    // app that hasn't updated yet, open next to a newer browser tab) finds data saved by a
    // NEWER one, it stops saving and asks you to reload, so it can't damage that newer data.
    const DATA_VERSION = 1;
    let dataTooNew = false;  // true once this copy has seen data from a newer version
    function storedDataVersion() {
      try {
        const saved = JSON.parse(localStorage.getItem(SETTINGS_KEY) || "null");
        const n = saved && typeof saved === "object" ? Number(saved.dataVersion) : 0;
        return Number.isFinite(n) ? n : 0;
      } catch (ignored) { return 0; }
    }
    function checkDataVersion() {
      if (!dataTooNew && storedDataVersion() > DATA_VERSION) dataTooNew = true;
      return !dataTooNew;
    }
    function isStorageFull(error) {
      return !!error && (error.name === "QuotaExceededError" || error.name === "NS_ERROR_DOM_QUOTA_REACHED" ||
                         error.code === 22 || error.code === 1014);
    }
    function writeTogether(entries) {
      if (holdSaves) return true;
      // v18.3: newer data saved by a newer version of the app? Don't overwrite it.
      if (!checkDataVersion()) return false;
      const before = [];
      try {
        for (const [key, text] of entries) {
          before.push([key, localStorage.getItem(key)]);
          localStorage.setItem(key, text);
        }
        return true;
      } catch (error) {
        // Put back everything we'd already changed, newest first.
        for (const [key, old] of before.reverse()) {
          try { if (old === null) localStorage.removeItem(key); else localStorage.setItem(key, old); } catch (ignored) {}
        }
        // Storage switched off altogether (some private windows): nothing we can do, and
        // the app still works until it's closed, as before.
        return !isStorageFull(error);
      }
    }

    // The red banner at the top. It stays up while saving keeps failing, and goes away
    // by itself as soon as a save works again (before v14 you were warned only once).
    const TOO_NEW_MESSAGE = "A newer version of Minifolio has saved your data on this device, so this older copy " +
      "has stopped saving to keep that data safe. Nothing has changed. Please reload to update.";
    function showSaveProblem() {
      saveFailing = true;
      const banner = document.getElementById("save-banner");
      if (!banner) return;
      // v18.3: a different message (and a Reload button) when the cause is newer data, not full storage.
      if (dataTooNew) {
        const text = document.getElementById("save-banner-text");
        if (text) {
          text.textContent = "";
          const strong = document.createElement("strong");
          strong.textContent = "Please reload. ";
          text.append(strong, TOO_NEW_MESSAGE);
        }
        const retry = document.getElementById("banner-retry");
        if (retry) retry.textContent = "Reload";
        const backup = document.getElementById("banner-backup");
        if (backup) backup.classList.add("hidden");
      }
      banner.classList.remove("hidden");
    }
    function hideSaveProblem() {
      saveFailing = false;
      const banner = document.getElementById("save-banner");
      if (banner) banner.classList.add("hidden");
    }

    // ================= SETTINGS AND STAGES =================

    // Each unit stores a NUMBER pointing at a position in the stage list (0 = first).
    // Stages from settings.doneFrom onwards count as "Done"; earlier ones are "To do".
    const DEFAULT_STAGES = ["Unassembled", "Part assembled", "Assembled", "Primed",
                            "Part painted", "Battle ready", "Painted with issues", "Parade ready"];
    // The defaults before v3, so testers on them can be moved to the new set (see below).
    const OLD_DEFAULT_STAGES = ["Unassembled", "Part assembled", "Assembled", "Primed",
                                "Part painted", "Painted with issues", "Battle ready"];
    // The original five, kept for anyone who saved units before stages were editable.
    const ORIGINAL_STAGES = ["Unbuilt", "Built", "Primed", "In progress", "Painted"];

    let settings = { palette: "ice", tab: "dashboard" };
    // v14: if the saved settings can't be read, keep a copy of them under another name
    // (like units and recipes), so nothing is thrown away.
    let settingsUnreadable = false;
    {
      let raw = null;
      try { raw = localStorage.getItem(SETTINGS_KEY); } catch (ignored) {}
      if (raw) {
        try {
          const parsed = JSON.parse(raw);
          if (!parsed || typeof parsed !== "object" || Array.isArray(parsed)) throw new Error("Not settings");
          settings = { ...settings, ...parsed };
        } catch (error) {
          settingsUnreadable = true;
          try { localStorage.setItem(SETTINGS_KEY + "-unreadable", raw); } catch (ignored) {}
        }
      }
      // v18.3: stamp the data version, unless the saved data came from a newer version.
      if (!checkDataVersion()) setTimeout(showSaveProblem, 0);
      else settings.dataVersion = DATA_VERSION;
    }

    // A stage list is usable if it's at least 2 names, all text. (Backups are checked
    // more strictly by goodStageList, further down.)
    const usableStages = (list) => Array.isArray(list) && list.length >= 2 &&
      list.every(s => typeof s === "string" && s.trim());

    // The strict check, for stage lists that come from a FILE (a backup or a safety copy):
    // 2 to 10 names, each real text, no two the same (ignoring capitals). The stage
    // editor has the same rules, so every list the app made itself passes.
    function goodStageList(list) {
      if (!Array.isArray(list) || list.length < 2 || list.length > 10) return false;
      if (!list.every(s => typeof s === "string" && s.trim())) return false;
      const lower = list.map(s => s.trim().toLowerCase());
      return new Set(lower).size === lower.length;
    }

    if (!usableStages(settings.stages)) {
      // No usable stage list. Pick one that FITS the saved units, so no unit is pushed
      // back to the first stage and no diary entry is lost (v14: before, a unit on stage 7
      // was reset when only 5 stages were chosen).
      let savedUnits = null;
      try { savedUnits = JSON.parse(localStorage.getItem(STORAGE_KEY) || "null"); } catch (ignored) {}
      const hasOldData = Array.isArray(savedUnits);
      const highest = hasOldData ? highestStageUsed(savedUnits) : -1;
      // Brand-new users and anyone whose settings were damaged get today's default
      // stages; very old data (from before stages could be edited) gets the original five.
      let list = !settingsUnreadable && hasOldData && highest < ORIGINAL_STAGES.length
        ? ORIGINAL_STAGES.slice() : DEFAULT_STAGES.slice();
      while (list.length <= highest && list.length < 10) list.push(`Stage ${list.length + 1}`);
      settings.stages = list;
      settings.doneFrom = list.join() === ORIGINAL_STAGES.join() ? 4 : 5;
    }

    // The highest stage number any saved unit uses (its stage, each model's stage,
    // its diary and its photos). -1 if there are none.
    function highestStageUsed(units) {
      let top = -1;
      const see = (x) => { if (Number.isInteger(x) && x > top) top = x; };
      for (const u of units) {
        if (!u || typeof u !== "object") continue;
        see(Number(u.stage));
        if (Array.isArray(u.stages)) u.stages.forEach(x => see(Number(x)));
        if (Array.isArray(u.log)) u.log.forEach(e => Array.isArray(e) && see(e[1]));
        if (Array.isArray(u.photos)) u.photos.forEach(p => p && see(p.stage));
      }
      return top;
    }

    let STAGES = settings.stages.map(String);
    // v3 upgrade: anyone still on the old default stages gets the new set.
    // Units keep their stage BY NAME: "Battle ready" and "Painted with issues" swap
    // positions, and "Parade ready" is added at the end. Custom stage lists are left alone.
    let upgradedStages = false;
    {
      const same = (a, b) => a.length === b.length && a.every((x, i) => x === b[i]);
      if (same(STAGES, OLD_DEFAULT_STAGES)) {
        let savedUnits = null;
        try { savedUnits = JSON.parse(localStorage.getItem(STORAGE_KEY) || "null"); } catch (ignored) {}
        if (Array.isArray(savedUnits)) {
          // old position -> new position
          const move = [0, 1, 2, 3, 4, 6, 5];
          for (const u of savedUnits) if (Number.isInteger(u.stage) && move[u.stage] !== undefined) u.stage = move[u.stage];
          try { localStorage.setItem(STORAGE_KEY, JSON.stringify(savedUnits)); } catch (ignored) {}
        }
        settings.stages = STAGES = DEFAULT_STAGES.slice();
        settings.doneFrom = 5;
        upgradedStages = true;
        try { localStorage.setItem(SETTINGS_KEY, JSON.stringify(settings)); } catch (ignored) {}
      }
    }
    // Settings saved before the Done marker existed: use the matching default if the
    // stages are one of the built-in sets, otherwise just the last stage.
    if (settings.doneFrom === undefined) {
      const same = (a, b) => a.length === b.length && a.every((s, i) => s === b[i]);
      settings.doneFrom = same(STAGES, DEFAULT_STAGES) ? 5 : same(STAGES, ORIGINAL_STAGES) ? 4 : STAGES.length - 1;
    }
    fixDoneFrom();

    // "Done" must start somewhere from the 2nd stage to the last, so there's always
    // at least one To do stage and one Done stage.
    function fixDoneFrom() {
      const n = Number(settings.doneFrom);
      settings.doneFrom = Number.isInteger(n) ? Math.min(Math.max(n, 1), STAGES.length - 1) : STAGES.length - 1;
    }

    function isDone(stageIndex) {
      return stageIndex >= settings.doneFrom;
    }

    // The stage numbers in each group, e.g. To do = [0,1,2,3,4], Done = [5,6].
    function todoStages() { return STAGES.map((s, i) => i).filter(i => !isDone(i)); }
    function doneStages() { return STAGES.map((s, i) => i).filter(i => isDone(i)); }

    // Saves just the settings. (Units, recipes AND settings are saved together by
    // saveAll(), further down.) If it fails because storage is full, the red banner shows.
    function saveSettings() {
      if (!writeTogether([[SETTINGS_KEY, JSON.stringify(settings)]])) showSaveProblem();
    }

    // Faction colours (v8): settings.factionColours = { "Ultramarines": "#1e3a8a", ... }.
    // They're looked up by the faction's name. Only proper "#rrggbb" colours are kept,
    // so a broken saved value can never break the screen.
    // v14: the list is made with Object.create(null), an object with NOTHING built in.
    // An ordinary {} already "has" things like constructor and toString, so a faction
    // called "constructor" used to find one of those instead of a colour, and the Units
    // list broke. copyColours() makes a copy of the same safe kind (used for Undo).
    function copyColours(colours) {
      return Object.assign(Object.create(null), colours || {});
    }
    function cleanFactionColours(raw) {
      const clean = Object.create(null);
      if (raw && typeof raw === "object" && !Array.isArray(raw)) {
        for (const [name, colour] of Object.entries(raw)) {
          if (name && typeof colour === "string" && /^#[0-9a-f]{6}$/i.test(colour)) clean[name] = colour.toLowerCase();
        }
      }
      return clean;
    }
    settings.factionColours = cleanFactionColours(settings.factionColours);
    saveSettings();

    // ================= LOADING AND SAVING UNITS =================

    // Example units, only used the very first time (when nothing is saved yet).
    // v21: each carries "example: true", so the "These are examples" card can find them.
    const EXAMPLES = [
      { id: 1, name: "Captain", hobby: "40K", faction: "Ultramarines", stage: 3, count: 1, example: true },
      { id: 2, name: "Boyz", hobby: "40K", faction: "Orks", stage: 0, count: 10, example: true },
      { id: 3, name: "Liberators", hobby: "Age of Sigmar", faction: "Stormcast Eternals", stage: 6, count: 5, example: true },
    ];

    // v24: is this the very first visit (no units and no recipes saved yet)? Only then do the
    // example recipes and paints get added (see seedExampleRecipes). Anyone who already has data,
    // even an empty saved recipe book, is left alone.
    const RECIPES_KEY = "shades-of-grey-recipes";
    const freshStart = (() => {
      try { return !localStorage.getItem(STORAGE_KEY) && !localStorage.getItem(RECIPES_KEY); } catch (e) { return false; }
    })();

    // All units live in this list. Each is a small bundle of facts (an "object").
    let models = load();

    // v21: example units saved BEFORE v21 have no "example" mark. Recognise them once:
    // same id, name, game and faction as an example, and nothing of yours added to them
    // (no photos, recipes, nickname or copy number). "examplesChecked" makes sure this only
    // happens once, so "Keep them" (which removes the marks) isn't undone on the next visit.
    // (Saved by the start-up render(), units and settings together.)
    if (!settings.examplesChecked) {
      for (const m of models) {
        const e = EXAMPLES.find(x => x.id === m.id);
        if (e && m.name === e.name && m.hobby === e.hobby && m.faction === e.faction &&
            !m.photos && !m.photo && !m.recipes && !m.nickname && !m.copy) m.example = true;
      }
      settings.examplesChecked = true;
    }

    // ================= PAINT RECIPES: THE DATA =================
    // Recipes are saved separately from units, under their own name in browser storage.
    // The "recipe book" holds four lists:
    //   parts:      what a recipe is for (Armour, Eyes...). You can add your own.
    //   techniques: how a step is done (Base coat, Wash...). You can add your own.
    //   paints:     every paint used in any recipe, ONCE each: { id, brand, name, colour }.
    //               Steps point at a paint by its id, so each paint's details live in one
    //               place. The "Your Palette" tab (next update) is built from this list.
    //   recipes:    { id, name, part, notes, steps: [{ technique, coats, paints: [{ paint, mix }] }] }
    //               "paint" is a paint's id; "mix" is its share in % (null if not given).
    // A unit lists the recipes it uses in unit.recipes, a list of recipe ids.
    // (RECIPES_KEY is declared higher up, just before freshStart, because that needs it first.)
    // v15: "Whole model" is for steps done all over (prime, base coat, zenithal, all-over dry
    // brush). It is always listed first.
    const WHOLE_MODEL = "Whole model";
    const DEFAULT_PARTS = [WHOLE_MODEL, "Armour", "Cloth", "Skin", "Metal", "Trim", "Eyes", "Lenses",
                           "Weapons", "Leather", "Gems", "Base"];
    const V15_TECHNIQUES = ["Technical", "Texture", "Varnish"];
    const DEFAULT_TECHNIQUES = ["Prime", "Base coat", "Contrast", "Layer", "Wash", "Shade", "Glaze",
                                "Dry brush", "Edge highlight", "Wet blend", "Stipple", "Sponge", "Airbrush",
                                ...V15_TECHNIQUES];
    const COMMON_BRANDS = ["Citadel", "Vallejo", "The Army Painter", "Pro Acryl", "AK Interactive",
                           "Scale75", "Two Thin Coats", "Green Stuff World", "Monument Hobbies"];
    const DEFAULT_PAINT_COLOUR = "#808080";

    // v15: paints the app knows before you've used them, suggested as you type.
    // v16: a much longer list (Citadel's current range, colours approximate), so pasted
    // notes and pot-label scans can be matched to real paint names. Format: "Name|colour".
    const KNOWN_PAINT_TABLE = {
      Citadel: [
        // Base
        "Abaddon Black|#231f20", "Averland Sunset|#fbb81c", "Balor Brown|#8b5910", "Bugman's Glow|#834f44",
        "Caledor Sky|#366699", "Caliban Green|#003d15", "Castellan Green|#314821", "Celestra Grey|#90a8a8",
        "Corax White|#f2f2f2", "Corvus Black|#171314", "Daemonette Hide|#696684", "Death Guard Green|#848a66",
        "Deathworld Forest|#556229", "Dryad Bark|#33312d", "Gal Vorbak Red|#4b213c", "Grey Seer|#a2a5a7",
        "Incubi Darkness|#082e32", "Ionrach Skin|#c2b49a", "Jokaero Orange|#ee3823", "Kantor Blue|#02134e",
        "Khorne Red|#6a0001", "Leadbelcher|#888d8f", "Macragge Blue|#0d407f", "Mechanicus Standard Grey|#3d4b4d",
        "Mephiston Red|#9a1115", "Morghast Bone|#c4b085", "Mournfang Brown|#640909", "Naggaroth Night|#3d3354",
        "Night Lords Blue|#002c53", "Phoenician Purple|#440052", "Rakarth Flesh|#a29e91", "Ratskin Flesh|#ad6b4c",
        "Retributor Armour|#c39e5d", "Rhinox Hide|#462f30", "Screamer Pink|#7c1645", "Screaming Bell|#c16f45",
        "Steel Legion Drab|#5e5134", "Stormvermin Fur|#6d655f", "Thousand Sons Blue|#18abcc", "Waaagh! Flesh|#1f5429",
        "Warplock Bronze|#927d7b", "Wraithbone|#dbd1b2", "Zandri Dust|#9e915c", "Iron Hands Steel|#a1a6a9",
        "Runelord Brass|#b6a37a", "Grey Knights Steel|#8a8d8e", "Gorthor Brown|#5f463f",
        "Lupercal Green|#002c2b", "Orruk Flesh|#879f7e", "Wraithbone Spray|#dbd1b2",
        // Layer
        "Administratum Grey|#949b95", "Ahriman Blue|#1f8c9c", "Alaitoc Blue|#295788", "Altdorf Guard Blue|#1f56a7",
        "Baharroth Blue|#58c1cd", "Baneblade Brown|#937f6d", "Bestigor Flesh|#d38a57", "Blue Horror|#a2bad2",
        "Brass Scorpion|#b7885f", "Cadian Fleshtone|#c47652", "Calgar Blue|#4272b8", "Dawnstone|#70756e",
        "Deathclaw Brown|#af634f", "Dechala Lilac|#b69fcc", "Doombull Brown|#5d0009", "Eldar Flesh|#ecc083",
        "Elysian Green|#6b8c37", "Emperor's Children|#b74073", "Evil Sunz Scarlet|#c01411", "Fenrisian Grey|#6d94b3",
        "Fire Dragon Bright|#f4874e", "Flash Gitz Yellow|#fff300", "Flayed One Flesh|#eec483", "Fulgrim Pink|#f4afcd",
        "Gauss Blaster Green|#84c3aa", "Gehenna's Gold|#dba663", "Genestealer Purple|#7658a5", "Gorthor Brown|#5f463f",
        "Hashut Copper|#b7705a", "Hoeth Blue|#4c78af", "Ironbreaker|#a1a6a9", "Kabalite Green|#038c67",
        "Karak Stone|#bb9662", "Kislev Flesh|#d1a570", "Krieg Khaki|#c0bd81", "Liberator Gold|#d3b587",
        "Lothern Blue|#34a2cf", "Loren Forest|#486c25", "Lugganath Orange|#f69b82", "Moot Green|#52b244",
        "Nurgling Green|#7e975e", "Ogryn Camo|#96a648", "Pallid Wych Flesh|#cdcebe", "Pink Horror|#90305d",
        "Russ Grey|#507085", "Screaming Skull|#d2d29b", "Skarsnik Green|#5f9370", "Skavenblight Dinge|#47413b",
        "Skrag Brown|#8b4806", "Slaanesh Grey|#8b8893", "Sotek Green|#0b6371", "Squig Orange|#aa4f44",
        "Stormhost Silver|#bbc6c9", "Sybarite Green|#17a166", "Tallarn Sand|#a07409", "Taubach Beige|#c6a174",
        "Teclis Blue|#317ec1", "Temple Guard Blue|#239489", "Thunderhawk Blue|#417074", "Troll Slayer Orange|#f36d2d",
        "Tuskgor Fur|#883636", "Ulthuan Grey|#c7e0d9", "Ungor Flesh|#d6a766", "Ushabti Bone|#bbbb7f",
        "Vulkan Green|#284631", "Warboss Green|#3e805d", "Warpfiend Grey|#6b6a74", "Warpstone Glow|#1e7331",
        "White Scar|#ffffff", "Wild Rider Red|#ea2f28", "Word Bearers Red|#640d0a", "Xereus Purple|#47125a",
        "Yriel Yellow|#ffda00", "Zamesi Desert|#ddb21d", "Wazdakka Red|#880804", "Kakophoni Purple|#8869ae",
        "Sigvald Burgundy|#5e1b2a", "Eshin Grey|#484b4e", "Grey Knights Steel|#8a8d8e", "Sycorax Bronze|#cbb394",
        "Auric Armour Gold|#c9a24b", "Canoptek Alloy|#b49d76", "Runefang Steel|#c3cacb", "Fulgurite Copper|#b16e4c",
        "Thondia Brown|#5f4934", "Rhinox Hide|#462f30", "Dorn Yellow|#fff55a",
        "Lahmian Medium|#eeeeee", "Contrast Medium|#e6e6e6", "Mordian Blue|#1b345c", "Necron Compound|#9a9b9c",
        "Dark Reaper|#354d4c", "The Fang|#405a74", "Kislev Flesh|#d1a570", "Stormfang|#80a7c1", "Kislev Flesh|#d1a570", "Knight-Questor Flesh|#a56c5a",
        // Shade
        "Agrax Earthshade|#3b2f22", "Athonian Camoshade|#5c5b2e", "Biel-Tan Green|#1c6b42", "Carroburg Crimson|#6b1a2e",
        "Casandora Yellow|#e7a12c", "Coelia Greenshade|#0e4a4c", "Drakenhof Nightshade|#152a52", "Druchii Violet|#4c2e4f",
        "Fuegan Orange|#c2541d", "Nuln Oil|#151515", "Reikland Fleshshade|#9c5c32", "Seraphim Sepia|#a96d22",
        "Kroak Green|#4e6b37", "Mortarion Grime|#7d7b3b", "Poxwalker|#5d5f45", "Targor Rageshade|#4a3a4f",
        "Berserker Bloodshade|#64131c", "Cryptek Armourshade|#3b3a44", "Soulblight Grey|#69707a",
        // Contrast
        "Aethermatic Blue|#5fa5c2", "Aggaros Dunes|#b7914c", "Akhelian Green|#00757a", "Apothecary White|#c7d0d4",
        "Baal Red|#9e0f17", "Basilicanum Grey|#3b3d40", "Black Legion|#1d1d1f", "Black Templar|#1f2328",
        "Blood Angels Red|#a31a1c", "Creed Camo|#5b6a2e", "Cygor Brown|#4d3324", "Darkoath Flesh|#83553c",
        "Dark Angels Green|#1f4029", "Doomfire Magenta|#a7316a", "Flesh Tearers Red|#7a1416", "Frostheart|#3b9ad4",
        "Fyreslayer Flesh|#a8613f", "Gore-Grunta Fur|#7c3d17", "Guilliman Flesh|#c38672", "Gryph-Charger Grey|#6c8ca1",
        "Gryph-Hound Orange|#d9561f", "Iyanden Yellow|#e8a51b", "Imperial Fist|#f2b80e", "Kroxigor Scales|#2c6e8a",
        "Leviadon Blue|#253c74", "Luxion Purple|#5e2f73", "Magos Purple|#7c4a8c", "Mantis Warriors Green|#4a8d36",
        "Militarum Green|#5b6b3a", "Nazdreg Yellow|#c79a2a", "Ork Flesh|#476b2b", "Plaguebearer Flesh|#a7a76b",
        "Pylar Glacier|#a9c9dc", "Shyish Purple|#4e2a5a", "Skeleton Horde|#b39d6c", "Snakebite Leather|#8c5a2b",
        "Space Wolves Grey|#7a95a6", "Talassar Blue|#1d5bae", "Terradon Turquoise|#0f6f72", "Ultramarines Blue|#20419c",
        "Volupus Pink|#8f2c62", "Warp Lightning|#3b8b3b", "Wyldwood|#4a332a", "Aeldari Emerald|#0d6b4b",
        "Celestium Blue|#336a95", "Gutrippa Flesh|#a1765a", "Karandras Green|#38593b", "Bad Moon Yellow|#e5b42a",
        "Hexwraith Flame|#3fbf6f", 
        // Glaze (v18; colours approximate, picked by eye, not copied from any shop site)
        "Bloodletter|#b0353a", "Lamenters Yellow|#e6cf3a", "Waywatcher Green|#4f8a3c",
        // Technical, Dry and others
        "'Ardcoat|#e8e8e8", "Stormshield|#e8e8e8", "Nurgle's Rot|#9a9b26", "Typhus Corrosion|#3b3626",
        "Ryza Rust|#c4561f", "Blood for the Blood God|#7a0000", "Nihilakh Oxide|#66b39e", "Tesseract Glow|#4fbf3a",
        "Spiritstone Red|#a01116", "Soulstone Blue|#1f6db5", "Waystone Green|#1c8a3a", "Agrellan Earth|#a17f5b",
        "Armageddon Dust|#d2a359", "Astrogranite|#757679", "Martian Ironearth|#c25e3a", "Mordant Earth|#2b2a26",
        "Stirland Mud|#492b00", "Valhallan Blizzard|#f4f6f7", "Lustrian Undergrowth|#3a4f22", "Mourn Mountain Snow|#e8eef2",
        "Necron Compound|#9a9b9c", "Sigmarite|#caad76", "Terminatus Stone|#bdb192", "Chaos Black Spray|#231f20",
        "Corax White Spray|#f2f2f2", "Grey Seer Spray|#a2a5a7", "Leadbelcher Spray|#888d8f",
      ],
      "The Army Painter": ["Matt Black|#1a1a1a", "Matt White|#f5f5f5", "Strong Tone|#4a3520", "Dark Tone|#1d1d1d"],
      "Vallejo": ["Black Primer|#1a1a1a", "White Primer|#f5f5f5"],
    };
    const KNOWN_PAINTS = [];
    for (const [brand, rows] of Object.entries(KNOWN_PAINT_TABLE)) for (const row of rows) {
      const [name, colour] = row.split("|");
      if (!KNOWN_PAINTS.some(k => k.brand === brand && k.name === name)) KNOWN_PAINTS.push({ brand, name, colour });
    }
    // v21.3: more brands, so pot-label scans (and pasted notes) recognise them, not just Citadel.
    // Names, colours and Vallejo code numbers come from the open "miniature-paints" list by Rick Fleuren
    // (github.com/Arcturus5404/miniature-paints, MIT licence; see LICENSE-paint-list.txt). Colours are
    // the list's approximations, not exact matches for the real pots. Format: "Name|colour" or
    // "Name|colour|code code" (a name used in two Vallejo ranges, like Black, has both codes).
    // These are "extra" paints: Citadel and your own paints are always tried first, so they never change
    // how a Citadel name is matched.
    const EXTRA_PAINT_TABLE = {
      // Vallejo Game Color (with washes and special effects), Model Color and Xpress Color, with code numbers: 420
      "Vallejo": [
        "Abyssal Turquoise|#1b3e54|72.120", "Acid|#539e5d|72.607", "Alien Purple|#7161a8|72.076",
        "Amaranth Red|#d14e30|70.829", "Andrea Blue|#0270af|70.841", "Angel Green|#324d2c|72.123",
        "Aquamarine|#007c74|72.119", "Arctic White|#ffffff|72.002", "Armor Green|#1e462b|72.466",
        "Athena Skin|#c85b54|72.107", "Azure|#5b6b9e|70.902", "BC Dark Brown|#76563d|70.768",
        "Bag of Bones|#c1a16e|72.450", "Barbarian Skin|#926641|72.071", "Basalt Grey|#5c5a5d|70.869",
        "Basic Skin Tone|#e9ac8d|70.815", "Battledress Brown|#5d4c32|72.473", "Beasty Brown|#7f5525|72.043",
        "Beige|#dfbe6f|70.917", "Beige Brown|#816041|70.875", "Beige Red|#b06e4b|70.804", "Bile|#a4c600|72.606",
        "Bile Green|#d5d900|72.122", "Black|#000000|72.051 72.094 70.950", "Black Glaze|#383838|70.855",
        "Black Green|#2a342b|70.980 72.090", "Black Grey|#302722|70.862", "Black Lotus|#302627|72.423",
        "Black Red|#552f2c|70.859", "Black Violet|#392a31|70.751", "Black Wash|#0e0d0e|73.301 73.201",
        "Bloody Red|#d41c1c|72.010", "Blue|#00528e|72.088 70.925", "Blue Fluorescent|#0370b1|70.736",
        "Blue Green|#007a89|70.808", "Blue Grey Pale|#808686|70.905", "Blue Violet|#59467e|70.811",
        "Blue Wash|#1a5b9b|73.207", "Bone White|#bea374|72.034", "Brass|#643b1d|70.801",
        "Brassy Brass|#e9d7cb|72.058", "Bright Bronze|#e7d5bf|72.057", "Bright Orange|#e05921|70.851",
        "Bronze|#533c1d|70.998", "Bronze Brown|#b16921|72.036", "Bronze Green|#313a29|70.897", "Brown|#9a632a|72.092",
        "Brown Glaze|#4e403d|70.854", "Brown Rose|#9c6560|70.803", "Brown Sand|#906145|70.876", "Buff|#d7af4d|70.976",
        "Burnt Red|#763c3a|70.814", "Burnt Umber|#513b2e|70.941", "Camouflage Black Brown|#403436|70.822",
        "Camouflage Black Green|#313129|70.741", "Camouflage Dark Green|#263025|70.979",
        "Camouflage Green|#605d32|72.467 72.031", "Camouflage Middle Brown|#513e20|70.740",
        "Camouflage Olive Green|#3c3d2f|70.894", "Canvas|#4d3e1f|70.763", "Cardinal Purple|#c81928|72.408",
        "Caribbean Turquoise|#005961|72.414", "Carmine Red|#97211f|70.908", "Cavalry Brown|#84443a|70.982",
        "Cayman Green|#59542a|72.067", "Chainmail|#e4e5e9|72.053", "Chameleon Orange|#ce652e|72.455",
        "Charcoal|#363638|72.155", "Charred Brown|#422a26|72.045", "Chestnut Brown|#603f36|70.746",
        "Chocolate Brown|#58443d|70.872", "Clear Orange|#cc4527|70.956", "Cold White|#f6f6f8|70.919",
        "Commando Green|#3e4f3c|72.468", "Continental Blue|#25242a|70.754", "Copper|#803427|70.999",
        "Copper Brown|#532c25|72.421", "Cork Brown|#a16f4e|70.843", "Corrosion|#572922|72.608",
        "Cream White|#e3d1c3|70.766", "Dark Blue|#464775|72.017 70.930", "Dark Blue Grey|#6d8589|70.904 70.867",
        "Dark Flesh|#d3933b|70.927", "Dark Fleshtone|#603429|72.044", "Dark Green|#1f3727|72.028",
        "Dark Grey|#312f32|70.994", "Dark Gunmetal|#dadada|72.054", "Dark Prussian Blue|#372741|70.899",
        "Dark Purple|#452733|70.749", "Dark Red|#692f24|70.946", "Dark Rose|#805252|70.745",
        "Dark Rust|#3b2625|70.771", "Dark Sand|#cba868|70.847", "Dark Sea Blue|#262c38|70.898",
        "Dark Sea Green|#4b4545|70.868", "Dark Sea Grey|#6c6b69|70.991", "Dark Turquoise|#01708b|72.084",
        "Dark Vermilion|#b52a27|70.947", "Dark Yellow|#90873a|70.978", "Dead Flesh|#c3aa4d|72.035",
        "Dead White|#ffffff|72.001", "Deck Tan|#aba390|70.986", "Deep Green|#1b4b33|70.970",
        "Deep Magenta|#622640|72.113", "Deep Purple|#6f2b42|72.409", "Deep Sky Blue|#4d95c5|70.844",
        "Deep Yellow|#f1c701|70.915", "Demon Blood|#66477e|72.603", "Demonic Skin|#965c58|72.458",
        "Desert Brown|#ab8556|70.767", "Desert Ochre|#9d6729|72.454", "Desert Yellow|#b6854a|70.977 72.063",
        "Dirty Grey|#675f30|72.145", "Dreadnought Yellow|#d38821|72.477", "Dried Blood|#622a1d|72.133",
        "Dry Rust|#5e332d|72.136", "Dwarf Skin|#d99169|72.041 72.402", "Earth|#775730|72.062",
        "Electric Blue|#4399b2|72.023", "Elf Skin Tone|#ca8854|72.004", "Elfic Blue|#50617d|72.117",
        "Elfic Flesh|#ead7b9|72.098", "Emerald|#00624b|70.838", "English Uniform|#6f532b|70.921",
        "Evil Red|#461e26|72.112", "Extra Dark Green|#282a14|70.896", "Fairy Skin|#ca8774|72.457",
        "Fern Green|#475436|70.833", "Field Blue|#4d5256|70.964", "Filthy Brown|#e99300|72.037",
        "Flat Blue|#3f4873|70.962", "Flat Brown|#703f38|70.984", "Flat Earth|#69442a|70.983",
        "Flat Flesh|#e09959|70.955", "Flat Green|#374b2f|70.968", "Flat Red|#a12b29|70.957",
        "Flat Yellow|#f6ba36|70.953", "Flesh Blood|#f27466|72.601", "Flesh Wash|#b67c78|73.204",
        "Fluid Pink|#c06793|72.459", "Fluorescent Blue|#0082cd|72.160", "Fluorescent Cold Green|#007074|72.161",
        "Fluorescent Green|#74b72c|72.104", "Fluorescent Magenta|#e8348d|72.158", "Fluorescent Orange|#e84e10|72.156",
        "Fluorescent Red|#dd2f52|72.157", "Fluorescent Violet|#6f257a|72.159", "Fluorescent Yellow|#f0e639|72.103",
        "Forest Green|#11662d|72.465", "Foul Green|#00a27d|72.025", "French Mirage Blue|#5f6772|70.900",
        "Fresh Blood|#7e2b19|72.132", "Frost|#8ac9e3|72.604", "Galvanic Corrosion|#eeae76|72.610",
        "German Beige WWII|#796950|70.821", "German Fieldgrey WWII|#58523c|70.830", "German Grey|#2e2e2c|70.995",
        "German Orange|#ba6254|70.805", "German Tank Crew|#544a3e|70.759", "German Uniform|#434d42|70.920",
        "German Yellow|#ceb65e|70.806", "Ghost Green|#83c192|72.121", "Ghost Grey|#c2cbd4|72.046",
        "Glacier Blue|#cdd9f1|72.095", "Gloomy Violet|#402f59|72.410", "Glorious Gold|#f4e3c5|72.056",
        "Gloss White|#f5f3f4|70.842", "Glossy Black|#241e1e|70.861", "Goblin Green|#576033|72.030",
        "Gold|#996728|70.996", "Gold Brown|#bf873c|70.877", "Gold Yellow|#d67419|72.007",
        "Golden Olive|#808145|70.857", "Golden Yellow|#f8a734|70.948", "Gorgon Brown|#5a2e23|72.124",
        "Gory Red|#7d1f1f|72.011", "Greasy Black|#413736|72.476", "Green|#007133|72.089",
        "Green Brown|#816d32|70.879", "Green Fluorescent|#a8c958|70.737", "Green Grey|#b5b6ae|70.971 70.886",
        "Green Ochre|#a17f35|70.914", "Green Rush|#8cc5b2|72.605", "Green Sky|#7a9165|70.974",
        "Green Wash|#72b25b|73.205", "Green Yellow|#6e653c|70.881", "Grey Blue|#596d85|70.943",
        "Grey Brown|#5b4923|70.762", "Grey Green|#41403e|70.866", "Grunge Brown|#864326|72.115",
        "Gunmetal|#352a2e|70.863", "Gunmetal Blue|#282834|70.800", "Gunship Green|#4c5840|70.895",
        "Hammered Copper|#dccfc7|72.059", "Heavy Black Green|#3e4943|72.147", "Heavy Blue|#405b78|72.143",
        "Heavy Bluegrey|#cbcac8|72.144", "Heavy Brown|#7b674e|72.153", "Heavy Gold Brown|#b68644|72.151",
        "Heavy Green|#566637|72.146", "Heavy Kakhi|#b49f50|72.149", "Heavy Ochre|#ae7727|72.150",
        "Heavy Orange|#ea5e0f|72.152", "Heavy Red|#8d363c|72.141", "Heavy Siena|#5e483b|72.154",
        "Heavy Skin Tone|#ad8468|72.140", "Heavy Violet|#484069|72.142", "Heretic Turquoise|#13514b|72.481",
        "Hexed Lichen|#4b2753|72.015", "Hospitallier Black|#252527|72.484", "Hot Orange|#e23922|72.009",
        "Hull Red|#5c383c|70.985", "Ice Yellow|#eecf72|70.858", "Iceberg Grey|#42576c|72.463",
        "Imperial Blue|#262a47|72.020", "Imperial Yellow|#f59f2e|72.403", "Infantry Blue|#25212f|70.752",
        "Intermediate Blue|#646d76|70.903", "Intermediate Green|#506544|70.891", "Iraqi Sand|#b49360|70.819",
        "Ivory|#ebe2d1|70.918", "Jade Green|#007155|72.026", "Japanese Uniform WWII|#9f7f2a|70.923",
        "Khaki|#9a7b4c|72.061 70.988", "Khaki Drill|#c7945b|72.451", "Khaki Grey|#7e6338|70.880",
        "Landser Grey|#524f48|72.469", "Lavender Grey|#7f6f6f|70.774", "Leather Brown|#594335|70.871 72.040",
        "Legacy Blue|#272961|72.480", "Lemon Yellow|#e4d202|70.952", "Light Brown|#a25b31|70.929",
        "Light Flesh|#f3d4b8|70.928", "Light Green|#007943|70.942", "Light Green Blue|#86958e|70.972",
        "Light Grey|#919294|70.990", "Light Mud|#7c745d|70.760", "Light Orange|#ee7228|70.911",
        "Light Sea Grey|#a1b1b1|70.973", "Light Turquoise|#006989|70.840", "Light Violet|#a893bc|70.750",
        "Light Yellow|#f8d347|70.949", "Lime Green|#7f9435|70.827", "Livery Green|#9dc451|72.033",
        "Lizard Green|#223a2c|72.418", "London Grey|#696363|70.836", "Luftwaffe Green|#393f25|70.823",
        "Luftwaffe Uniform WWII|#44404e|70.816", "Lustful Purple|#b78bbc|72.114", "Magenta|#903153|70.945 72.083",
        "Magenta Fluorescent|#e6418d|70.735", "Magic Blue|#0069aa|72.021", "Mahogany|#5a3930|72.472",
        "Mahogany Brown|#79504a|70.846", "Mahogany Ink|#674641|70.828", "Martian Orange|#cd4619|72.405",
        "Medium Blue|#16416c|70.963", "Medium Brown|#5b483a|70.826", "Medium Fleshtone|#b07940|70.860",
        "Medium Grey|#867259|70.987", "Medium Grey Blue|#779d92|70.772", "Medium Olive|#414e32|70.850",
        "Medium Sea Grey|#7d7b7c|70.870", "Medium Xpress|#fffbf8|72.448", "Middle Stone|#937f42|70.882",
        "Midnight Purple|#2d1e33|72.116", "Military Green|#434434|70.975", "Military Yellow|#937626|70.764 72.453",
        "Monastic Green|#004b37|72.482", "Moon Yellow|#eeb800|72.005", "Moss and Lichen|#dad76c|72.611",
        "Muddy Ground|#452e28|72.475", "Mummy White|#cfb496|72.449", "Mustard Brown|#9d714a|70.769",
        "Mutation Green|#4c7650|72.105", "Mystic Blue|#004a87|72.411", "Natural Steel|#535258|70.864",
        "Natural Wood Grain|#eaa432|70.834", "Neutral Grey|#6f6d61|72.050 70.992", "New Wood|#8a633c|70.770",
        "Night Blue|#202430|72.019", "Nocturnal Red|#551c22|72.111", "Nuclear Yellow|#dd9213|72.404",
        "Ochre Brown|#aa793e|70.856", "Off-White|#fef3dd|72.101 70.820", "Oily Steel|#484246|70.865",
        "Old Gold|#55371d|70.878", "Old Rose|#bc6d70|70.944", "Olive Brown|#3f3126|70.889",
        "Olive Green|#526138|70.967", "Olive Grey|#40422d|70.888", "Omega Blue|#3a365b|72.413",
        "Orange Brown|#ad623a|70.981", "Orange Fire|#eb5b1e|72.008", "Orange Fluorescent|#e86016|70.733",
        "Orange Ochre|#ac8035|70.824", "Orange Red|#dc4319|70.910", "Orc Skin|#5e752d|72.415",
        "Oxford Blue|#3e3a53|70.807", "Pale Blue|#90a3a9|70.906", "Pale Brown|#9f8375|70.825",
        "Pale Flesh|#cba37f|72.003", "Pale Grey Blue|#a7b6b3|70.907", "Pale Grey Wash|#cacad2|73.202",
        "Pale Sand|#e3c28f|70.837", "Pale Yellow|#ebce7e|72.097", "Parasite Brown|#a35c1e|72.042",
        "Park Green Flat|#21624a|70.969", "Pastel Blue|#607a93|70.901", "Pastel Green|#939870|70.885",
        "Phoenix Orange|#b1401e|72.478", "Pink|#b04f7c|70.958", "Plague Brown|#ab7131|72.039",
        "Plague Green|#4c4d2e|72.419", "Plasma Red|#a52822|72.406", "Polished Gold|#f8ecc2|72.055",
        "Prussian Blue|#3c405d|70.965", "Purple|#533152|70.959", "Red|#cd1316|72.086 70.926",
        "Red Leather|#95543e|70.818", "Red Wash|#d55e86|73.206", "Refractive Green|#474a35|70.890",
        "Rosy Flesh|#e58a6b|72.100", "Rotten Flesh|#89763b|72.452", "Rotten White|#f0eeef|72.130",
        "Royal Blue|#1a427d|70.809", "Royal Purple|#4d2740|70.810 72.016", "Russian Uniform WWII|#585336|70.924",
        "Rust|#e45314|72.131 72.609", "Saddle Brown|#8c645c|70.940", "Salmon Rose|#e28f7f|70.835",
        "Sand Yellow|#eabf56|70.916", "Scarlet|#c23d2e|70.817", "Scarlet Blood|#c22222|72.106",
        "Scarlet Red|#761e1d|72.012", "Scorpy Green|#4f8436|72.032", "Scrofulous Brown|#a7691c|72.038",
        "Scurvy Green|#1f4d43|72.027", "Sepia|#563d27|72.091", "Sepia Wash|#8b622c|73.200 73.300",
        "Seraph Red|#6b1411|72.479", "Sick Green|#406037|72.029", "Silver|#ebedec|72.052 70.997",
        "Silver Grey|#d8cdc9|70.883", "Skin|#5c2d27|72.093", "Skin Tone|#e5ab85|72.099", "Sky Blue|#74b8cf|70.961",
        "Sky Grey|#aaabad|70.989", "Smoke Ink|#5c4847|70.939", "Smokey Ink|#493632|72.068",
        "Snake Green|#015a46|72.417", "Sombre Grey|#535d69|72.048", "Space Grey|#2d5a5d|72.422",
        "Splinter Green|#456341|70.756", "Squid Pink|#c778a5|72.013", "Starship Steel|#517375|72.462",
        "Steel Grey|#7b92a2|72.102", "Stone Grey|#8c7c63|70.884", "Stonewall Grey|#9c9384|72.049",
        "Storm Blue|#303a7f|72.412", "Stormy Blue|#413f57|72.018", "Succubus Skin|#933d46|72.108",
        "Sun Yellow|#f6a300|72.006", "Sunny Skin Tone|#ed9646|70.845", "Sunrise Blue|#73c9ec|72.118",
        "Sunset Orange|#f4973a|72.110", "Sunset Red|#c02b49|70.802", "Tan|#95604e|72.066", "Tan Earth|#997457|70.874",
        "Tan Glaze|#d59335|70.831", "Tan Yellow|#c19b6e|70.912", "Tanned Skin|#81452d|72.471",
        "Templar White|#cccecd|72.401", "Terracotta|#693e38|72.065", "Thick Blood|#954e43|72.602",
        "Tinny Tin|#d5c7c6|72.060", "Toxic Yellow|#e8d457|72.109", "Transparent Blue|#323d5d|70.938",
        "Transparent Green|#007943|70.936", "Transparent Orange|#ea651a|70.935", "Transparent Red|#b62336|70.934",
        "Transparent Yellow|#f7a501|70.937", "Troll Green|#015e32|72.416", "Turquoise|#0c425a|70.966 72.024",
        "Twilight Rose|#774755|72.460", "US Dark Green|#494b36|70.893", "US Field Drab|#826545|70.873",
        "US Olive Drab|#59513c|70.887", "Ultramarine|#2d559d|70.839", "Ultramarine Blue|#383967|72.022",
        "Umber Wash|#766053|73.203", "Uniform Green|#4b5230|70.922", "Vampiric Purple|#492857|72.461",
        "Velvet Red|#81282e|72.407", "Verdigris|#91cbcc|72.135 72.096", "Verdigris Glaze|#99d0ca|70.832",
        "Vermilion|#c42a28|70.909", "Viking Grey|#45515d|72.483", "Violet|#3c2c49|70.960 72.087",
        "Violet Grey|#5a5957|70.773", "Violet Red|#64353f|70.812", "Violeta Wash|#886ca7|73.209",
        "Vomit|#faac42|72.600 72.134", "Wagram Blue|#014461|72.464", "Warlord Purple|#862351|72.014",
        "Warm Grey|#b29e9d|72.148", "Wasteland Brown|#684527|72.420", "White|#ffffff|70.951 72.082",
        "White Glaze|#f4f4f6|70.853", "White Grey|#e3e2e0|70.993", "Wicked Purple|#756566|72.456",
        "Willow Bark|#392b27|72.474", "Wolf Grey|#c3d1d1|72.047", "Yellow|#eba90c|72.085",
        "Yellow Fluorescent|#efe641|70.730", "Yellow Green|#dede26|70.954", "Yellow Ochre|#deaa47|70.913",
        "Yellow Olive|#1e4f39|72.064 70.892", "Yellow Wash|#e9e85c|73.208", "Zombie Flesh|#856b5a|72.470",
      ],
      // Warpaints Fanatic (with washes): 212
      "The Army Painter": [
        "Abyssal Blue|#00506c", "Aegis Aqua|#32b3d5", "Afterglow|#e4ea8d", "Agate Skin|#d7877b",
        "Alien Purple|#6154a3", "Alpha Blue|#667dc0", "Amber Skin|#c4a083", "Amulet Aqua|#68c5b6",
        "Ancient Stone|#d0c3a3", "Angel Green|#173e31", "Angelic Red|#d42c39", "Aqua Alchemy|#24bba6",
        "Aquamarine|#56c4cd", "Arctic Gem|#1995d4", "Army Green|#5d7554", "Ash Grey|#84878f", "Augur Blue|#acbce2",
        "Autumn Sage|#75ad98", "Barbarian Flesh|#f69b7f", "Baron Blue|#7c95cc", "Barren Dune|#debb72",
        "Basilisk Red|#6c2539", "Blood Chalice|#db4b50", "Blue Tone|#132b47", "Boney Spikes|#e6d4c1",
        "Bootstrap Brown|#5d4d4d", "Brainmatter Beige|#dedbd3", "Brigade Grey|#d0d0d2", "Brigadine Brown|#443a40",
        "Bright Gold|#987b1a", "Bright Sapphire|#84cef0", "Brush-On Primer|#727475", "Buffed Hide|#b3756a",
        "Burning Ore|#f2653e", "Burnt Turf|#be9859", "Camouflage Green|#6e8358", "Carnelian Skin|#5d3e46",
        "Cobalt Metal|#2e4249", "Command Khaki|#b49488", "Company Grey|#bcbec2", "Crystal Blue|#0273bc",
        "Cultist Purple|#6962ab", "Daemonic Yellow|#fece2a", "Dark Blue Tone|#17202e", "Dark Emerald|#3b4a25",
        "Dark Red Tone|#2e131a", "Dark Rust|#290f12", "Dark Skin Shade|#443638", "Dark Tone|#1f1f1f",
        "Data System Glow|#87c866", "Death Metal|#2b2b2b", "Deep Azure|#006b79", "Deep Grey|#4b5164",
        "Deep Ocean Blue|#1b3044", "Demigod Flames|#d17b41", "Desert Yellow|#856d45", "Diabolic Plum|#562d74",
        "Disgusting Slime|#a5c345", "Diviner Light|#d59fc5", "Doomfire Drab|#f9d9e6", "Dorado Skin|#eec79e",
        "Dragon Red|#bf283b", "Dry Blood|#24000e", "Dryad Brown|#613630", "Dusty Skull|#8b7c68",
        "Elder Flower|#a8577b", "Electric Lime|#bdd532", "Emerald Forest|#5bbb4d", "Enchanted Pink|#b66cae",
        "Eternal Hunt|#279a4c", "Evergreen Fog|#396360", "Evil Chrome|#5b3b2f", "Ferocious Green|#75c377",
        "Fiendish Yellow|#ec9a44", "Figgy Pink|#e3afc9", "Flickering Flame|#f58b3d", "Forbidden Fruit|#cd88a9",
        "Forest Faun|#a1c7af", "Fresh Rust|#c25428", "Frost Blue|#9abede", "Fur Brown|#774544",
        "Gargoyle Grey|#a8a292", "Gemstone Red|#821d23", "Glittering Green|#2e794a", "Glowing Inferno|#f79d42",
        "Gothic Blue|#2e3e79", "Great Hall Grey|#bbb4a6", "Greedy Gold|#745218", "Green Tone|#1f3625",
        "Greenskin|#1f7843", "Grey Castle|#929286", "Grotesque Green|#b3c29d", "Guardian Green|#226248",
        "Gun Metal|#4f5053", "Hexed Violet|#8d81be", "Hydra Turquoise|#149398", "Ice Yellow|#ffedad",
        "Imperial Navy|#063565", "Impish Rouge|#d957a0", "Inner Light|#fdcb5f", "Jasper Skin|#ba7372",
        "Kraken Lavender|#d5cae5", "Lava Orange|#f5792c", "Leafy Green|#76c045", "Leather Brown|#7c5b54",
        "Legendary Red|#ef4b3e", "Lens Flare Glow|#fff464", "Leopard Stone Skin|#e7b4b1", "Light Tone|#7f5216",
        "Magecast Magenta|#704099", "Magenta Tone|#590135", "Marine Mist|#94d6d7", "Matt Black|#000000",
        "Matt White|#ffffff", "Medieval Forest|#437c6d", "Military Shade|#23270e", "Mithril|#9e9fa3",
        "Mocca Skin|#81655a", "Moldy Wine|#7d3451", "Molten Lava|#f05a3e", "Moonstone Skin|#c57b74",
        "Mossy Green|#b1dcc0", "Mulled Berry|#623348", "Necrotic Flesh|#9aa984", "Neptune Glow|#75ced4",
        "Night Sky|#304358", "Oak Brown|#39262a", "Obsidian Skin|#4a4046", "Oil Stains|#1d252b", "Olive Drab|#7a905f",
        "Onyx Skin|#664a4d", "Oozing Vomit|#7b5c1d", "Opal Skin|#ffd2c8", "Orange Tone|#64300f", "Pale Sand|#efead3",
        "Paratrooper Tan|#9a776c", "Patagon Pine|#63917f", "Pearl Skin|#ffe3d8", "Phalanx Blue|#048bae",
        "Pharaoh Guard|#0c7c61", "Pink Potion|#f4b9d4", "Pixie Pink|#d96fae", "Plasma Coil Glow|#5ecdf4",
        "Plate Mail Metal|#686a6e", "Power Node Glow|#f286b5", "Prairie Ochre|#696242", "Pure Red|#cd151c",
        "Purple Tone|#241c31", "Quartz Skin|#f0d0b4", "Radiation Glow|#fbb375", "Raging Rose|#e96663",
        "Raging Rouge|#f68f82", "Rainforest|#8bc63e", "Red Copper|#4d2c30", "Red Tone|#531f28", "Regal Blue|#004f88",
        "Resplendent Red|#96272f", "Rough Iron|#352d25", "Royal Blue|#0162af", "Ruby Skin|#fbb99d",
        "Ruddy Umber|#985951", "Runic Cobalt|#7496b4", "Rust Tone|#452a11", "Sacred Scarlet|#f1634c",
        "Scarab Green|#193c44", "Sepia Tone|#734014", "Shieldwall Blue|#08a1cc", "Shining Silver|#86888c",
        "Skeleton Bone|#c2b293", "Soft Tone|#563d2a", "Space Dust|#ffe388", "Spellbound Fuchsia|#ad4da0",
        "Stratos Blue|#33658f", "Strong Skin Shade|#442824", "Strong Tone|#211913", "Tainted Gold|#575235",
        "Talisman Teal|#1fae91", "Temple Gate Teal|#046154", "Terrestial Titan|#303149", "Thunderous Blue|#34577b",
        "Tidal Blue|#026b93", "Tiger's Eye Skin|#904d52", "Tomb King Tan|#a29278", "Topaz Skin|#b25a53",
        "Tourmaline Skin|#e3988b", "Tree Ancient|#513430", "Triumphant Navy|#1a2c53", "True Blood|#8d0422",
        "True Brass|#635d58", "True Copper|#6b4731", "Tundra Taupe|#4b4d3e", "Turquoise Siren|#29b3b9",
        "Ultramarine Blue|#284d8e", "Uniform Grey|#6b707c", "Urban Buff|#dbb9ab", "Verdigris|#61b89b",
        "Violent Vermillion|#f37964", "Violet Coven|#a999c7", "Vivid Volt|#cfdc51", "Warlock Magenta|#834d9f",
        "Warped Yellow|#fed548", "Wash Medium|#b1b3b4", "Wasteland Clay|#a38755", "Weapon Bronze|#955610",
        "Weird Elixir|#e092bf", "Wicked Pink|#ce0886", "Wild Green|#46b758", "Wilted Rose|#ecc5d7",
        "Wolf Grey|#4f78a3", "Woodland Camo|#4b6149", "Worn Stone|#c4bfb1", "Wyvern Fury|#993243",
      ],
      // Pro Acryl (with Signature Series): 117
      "Pro Acryl": [
        "Ben Komets Advanced Flesh Tone|#8f5d4c", "Ben Komets Dark Burgundy|#2e1b1b",
        "Ben Komets Dark Sea Ben|#09202e", "Ben Komets Green Oxide|#296155", "Ben Komets Heavy Warm White|#f1d0a1",
        "Ben Komets Petroleum Brown|#3b2313", "Black Brown|#2c2d28", "Black Green|#3f5f50", "Blue|#0855a3",
        "Blue Black|#517283", "Bold Pyrrole Red|#a90f0f", "Bold Titanium White|#e7e9e4", "Bright Gold|#bc9866",
        "Bright Ivory|#e7e8c8", "Bright Jade|#408c8e", "Bright Neutral Grey|#abaea7", "Bright Pale Green|#d8f4e8",
        "Bright Warm Grey|#bbc0ac", "Bright Yellow Green|#88b423", "Bronze|#78685b", "Burgundy|#733739",
        "Burnt Orange|#802715", "Burnt Red|#631410", "Burnt Sienna|#ad4e32", "Camo Green|#365337",
        "Coal Black|#18191b", "Copper|#ae7849", "Dark Blue|#142038", "Dark Camo Green|#313c2c", "Dark Flesh|#674137",
        "Dark Golden Brown|#a58f56", "Dark Grey Blue|#184366", "Dark Neutral Grey|#2a3235", "Dark Purple|#1d2347",
        "Dark Silver|#25292c", "Dark Umber|#423431", "Dark Warm Grey|#464c4c", "Faded Green|#9aa37f",
        "Faded Plum|#c8b5d5", "Faded Ultramarine|#638ac1", "Flameon Bright Pale Yellow|#fff7cc",
        "Flameon Bright Yellow Ochre|#dda55b", "Flameon Caramel Brown|#805f3e", "Flameon Dark Green Brown|#614529",
        "Flameon Dark Orange Brown|#8d5c25", "Flameon Orange Brown|#805f3e", "Fluorescent Green|#3fb549",
        "Fluorescent Orange|#f04d26", "Fluorescent Pink|#ee387c", "Fluorescent Purple|#a32388",
        "Fluorescent Red|#ef3a37", "Fluorescent Yellow|#f2dd26", "Golden Brown|#be9953", "Golden Yellow|#e9d035",
        "Green|#16864e", "Grey Blue|#bce3f2", "Ivory|#d5d0b3", "Jade|#03535a", "Khaki|#ac9e6b",
        "Light Bronze|#9c8d64", "Light Umber|#5e4433", "Magenta|#a14d6f", "Mahogany|#261410",
        "Matt Cexwish Bone|#8d857e", "Matt Cexwish Brown Grey|#4b4945", "Matt Cexwish Dark Bronze|#3f311f",
        "Matt Cexwish Dark Crimson|#3e1714", "Matt Cexwish Dark Emerald|#194245",
        "Matt Cexwish Heavy Titanium White|#e6e6e6", "Metallic Medium|#d3d4cc", "Neutral Grey|#5e5e5e",
        "Ninjon Dark Ivory|#b7b4a6", "Ninjon Dark Magenta|#80303f", "Ninjon Dark Plum|#4e3b3d",
        "Ninjon Dark Warm Flesh|#c59157", "Ninjon Red Grey|#837876", "Ninjon Warm Brown|#6b4b38",
        "Olive Flesh|#ccc6ae", "Orange|#e56b20", "Pale Pink|#e0cabf", "Pale Yellow|#e8e7d2", "Pink|#eba59f",
        "Plum|#8e5384", "Purple|#63306b", "Rich Gold|#b47a30", "Rogue Hobbies Bismuth Yellow|#f9d967",
        "Rogue Hobbies Bright Green|#12a361", "Rogue Hobbies Dark Hot Pink|#c32c5b",
        "Rogue Hobbies Dark Turquoise|#167d94", "Rogue Hobbies Orange Red|#e53941",
        "Rogue Hobbies Ultramarine|#3d5eab", "Shadow Flesh|#8d5345", "Silver|#9a9e9d", "Sky Blue|#248ccb",
        "Tan Flesh|#c39f85", "Transparent Black|#1d1e22", "Transparent Blue|#09125d", "Transparent Brown|#372525",
        "Transparent Green|#082930", "Transparent Orange|#a22207", "Transparent Purple|#16172b",
        "Transparent Red|#90111c", "Transparent White|#f5f5f5", "Transparent Yellow|#e6b802", "Turquoise|#75f1f1",
        "Vince Venturella Beige Red|#a68e86", "Vince Venturella Dark Jade|#2c4855",
        "Vince Venturella Dark Yellow Green|#6a7546", "Vince Venturella Payne's Grey|#2d3844",
        "Vince Venturella Royal Purple|#3b3053", "Vince Venturella White Blue|#afbdba", "Warm Flesh|#f6c67c",
        "Warm Grey|#54544a", "Warm Yellow|#f6c847", "White Gold|#9e9b8a", "Yellow Green|#879245",
        "Yellow Ochre|#ae7f31",
      ],
      // AK 3rd Gen (standard, metallic, intense, ink): 217
      "AK Interactive": [
        "Alga Green|#555e1b", "Aluminium|#afafaf", "Amaranth Red|#cf4e27", "Amethyst Blue|#332a47",
        "Anodized Violet|#9d8696", "Anthracite Grey|#1c2a2b", "Aquatic Turquoise|#006557",
        "Archaic Turquoise|#003839", "Ash Grey|#42423a", "Astral Beryllium|#799e8d", "Basalt Grey|#5b605a",
        "Basic Skin Tone|#f7b57b", "Beige|#e2b848", "Beige Red|#de935a", "Black|#101207", "Black Green|#131e0d",
        "Black Red|#42271e", "Blood Red|#c52219", "Blue Grey|#c7d0cd", "Blue Violet|#886da4", "Blue-green|#358578",
        "Bordeaux Red|#a13b2f", "Brass|#a55d09", "Brick Red|#9e4429", "British Khaki|#654d1f", "Bronze|#7f5405",
        "Brown Rose|#d78464", "Brownish Green|#57460e", "Buff|#d1ac5c", "Burn Orange|#db5e30", "Burnt Red|#533125",
        "Burnt Tin|#331702", "Burnt Umber|#2d1e01", "Cadmium Red|#e9582c", "Camouflage Green|#4f411c",
        "Carbon Black|#110801", "Carmine|#b83e26", "Chocolate (chipping)|#331e09", "Clear Blue|#0d265c",
        "Clear Green|#029837", "Clear Orange|#eb5d0b", "Clear Red|#c61215", "Clear Smoke|#734c21",
        "Clear Yellow|#f49401", "Cobalt Blue|#012136", "Command Green|#312e0d", "Copper|#bd500b",
        "Dark Aluminium|#787878", "Dark Blue|#1e2d4c", "Dark Blue-grey|#4a5e53", "Dark Brown|#533914",
        "Dark Flesh|#eba43a", "Dark Green|#224618", "Dark Green-grey|#3b4d3d", "Dark Grey|#494a45",
        "Dark Prussian Blue|#0a0c1b", "Dark Rust|#542303", "Dark Sand|#e6bc56", "Dark Sea Blue|#0d1814",
        "Dark Sea Grey|#7b7873", "Dead Red|#f54949", "Deck Tan|#ccc4af", "Decomposed Flesh|#b7a261",
        "Deep Blue|#1a4067", "Deep Brown|#854a2a", "Deep Green|#1c6128", "Deep Orange|#fe5e14", "Deep Purple|#7a4967",
        "Deep Red|#dc211a", "Deep Sky Blue|#69b4c7", "Deep Violet|#74536e", "Deep Yellow|#fdc500",
        "Dirty Red|#7f190d", "Dirty Yellow|#eca71c", "Ducat Blue|#3a889f", "Emerald|#036242",
        "Emerald Metallic Green|#21753a", "English Grey|#6d6d65", "Extra Dark Green|#243128", "Faded Green|#7c8872",
        "Fluorescent Blue|#004064", "Fluorescent Green|#98c31e", "Fluorescent Magenta|#ff4c69",
        "Fluorescent Orange|#fe5102", "Fluorescent Yellow|#f6f101", "Foundry Red|#c53733", "French Blue|#545653",
        "Frog Green|#97b821", "German Field Grey|#423e23", "German Grey|#383830", "Gold|#9e6806",
        "Golden Brown|#ab7602", "Golden Olive|#737b26", "Golden Yellow|#feb449", "Graphite|#6c6e60",
        "Grass Green|#62832c", "Green Ochre|#a68236", "Green Sky|#8bb283", "Green-brown|#705923",
        "Green-grey|#dfe4bc", "Greenish White|#e4eecc", "Grey Green|#808064", "Grey-blue|#5f6772",
        "Grey-brown|#705b3c", "Grim Brown|#211404", "Grimy Grey|#dfc998", "Gun Metal|#4e4e4c",
        "Gunship Green|#485335", "Hull Red|#381a02", "Ice Yellow|#feee8e", "Imperial Blue|#192152",
        "Intense Pink|#e9748f", "Interior Yellow Green|#aca300", "Intermediate Blue|#676966",
        "Intermediate Green|#506e32", "Ivory|#f3eec8", "Japanese Brown|#966d1b", "Laser Magenta|#6b102f",
        "Laser Yellow|#f5ef2b", "Lead Grey|#464741", "Leather Brown|#46311e", "Lemon Yellow|#ffe121",
        "Light Brown|#cf8139", "Light Earth|#d0b580", "Light Flesh|#ffdfb6", "Light Green|#59922b",
        "Light Orange|#f07a3c", "Light Prussian Blue|#132a38", "Light Rust|#db5615", "Lilac|#656074",
        "Lime Green|#819f1d", "Lizard Green|#175a31", "Luminous Flesh|#edc180", "Luminous Green|#73b72c",
        "Luminous Orange|#f18700", "Magenta|#b1325f", "Mahogany Brown|#622a05", "Matt Red|#b5311c",
        "Medium Blue|#163a48", "Medium Flesh Tone|#c98230", "Medium Grey|#b6b8a3", "Medium Olive Green|#3e501c",
        "Medium Orange|#fa682c", "Medium Rust|#9c4b30", "Medium Sand|#cc9b35", "Medium Sea Grey|#a19b81",
        "Metallic Blue|#829c99", "Middle Stone|#8b7029", "Mint Green|#008c5f", "Mud Brown|#705331",
        "Natural Steel|#a7a6a1", "Neutral Grey|#696e68", "Night Blue|#0b1c26", "Ocean Blue|#1e3636",
        "Ocher Orange|#f5a75f", "Ochre|#c7932d", "Offwhite|#ebebe1", "Oily Steel|#a7a491", "Old Gold|#b89402",
        "Old Rose|#fe9679", "Olive Green|#4b5f20", "Orange Brown|#b1581e", "Oxford|#353942", "Pale Blue|#b4c4b7",
        "Pale Grey|#aeafb4", "Pale Sand|#efd581", "Pale Yellow|#fedd58", "Pearl|#f5efd5", "Penetrating Red|#b64026",
        "Pistachio|#dcd225", "Purple|#b47c89", "Purulent Yellow|#ebd03b", "Radiant Flesh|#feb254",
        "Radiant Yellow|#ffd409", "Reddish Grey|#7b6b52", "Reflective Green|#352e11", "Rock Grey|#c1b897",
        "Rubber Black|#29251a", "Ruby|#cf4747", "Russian Green|#292907", "Rusty Brass|#a04d0b", "Rusty Gold|#734b03",
        "Saddle Brown|#683a2b", "Sahara Yellow|#b1930d", "Salmon|#f5a175", "Sand Yellow|#e9bd3a",
        "Scarlet Red|#d03b27", "Sepia|#230d00", "Sickly Pink|#f6af91", "Silver|#a0aaac", "Silver Grey|#e2d7b7",
        "Skin|#943718", "Sky Blue|#88c2cd", "Sky Grey|#bbbab6", "Smoke Black|#2b2b21", "Snow Blue|#cae4e1",
        "Sooty Black|#5f5d48", "Spectrum Blue|#b4bebf", "Star Blue|#014760", "Strong Dark Blue|#04151f",
        "Sunny Skin Tone|#ffa84f", "Tan Earth|#7d5c33", "Tan Yellow|#d19849", "Tenebrous Grey|#302c21",
        "Titanium White|#ffffff", "Turquoise|#005e5e", "Ultramarine|#1e357b", "Us Dark Green|#423910",
        "Vampiric Flesh|#cfbc81", "Vermillion|#c44c33", "Violet Red|#573536", "Volcanic Yellow|#f09218",
        "Warm Grey|#b6a88b", "White|#ffffff", "White Grey|#f5f5ed", "Wine Red|#69140d", "Yellow|#fab711",
      ],
    };
    for (const [brand, rows] of Object.entries(EXTRA_PAINT_TABLE)) for (const row of rows) {
      const [name, colour, codes] = row.split("|");
      if (KNOWN_PAINTS.some(k => k.brand === brand && sameName(k.name, name))) continue;
      const paint = { brand, name, colour, extra: true };
      if (codes) paint.codes = codes.split(" ");
      KNOWN_PAINTS.push(paint);
    }
    // Upper/lower case and curly quotes don't count when spotting a repeat (sameText isn't defined yet here).
    function sameName(a, b) { return String(a).replace(/[\u2018\u2019]/g, "'").toLowerCase() === String(b).replace(/[\u2018\u2019]/g, "'").toLowerCase(); }
    // Every Vallejo code in a bit of text (a label can show more than one number).
    // The camera often reads 0 as the letter O and 1 as l or I ("72.O21"), so those count as digits
    // in the last three places, as long as at least one real digit is there too.
    function vallejoCodes(text) {
      const out = [];
      const re = /(?:^|[^0-9A-Za-z])(7[0-3])\s?[.,·:\-]?\s?([0-9OoIl]{3})(?![0-9A-Za-z])/g;
      let m;
      while ((m = re.exec(String(text || "")))) {
        re.lastIndex = m.index + 1;
        if (!/[0-9]/.test(m[2])) continue;
        const c = m[1] + "." + m[2].replace(/[Oo]/g, "0").replace(/[Il]/g, "1");
        if (!out.includes(c)) out.push(c);
      }
      return out;
    }

    // v15: basing materials (rocks, sand, static grass, snow...) aren't paints, but a step can
    // use one. They're kept in the paint list with type "material", so they can sit in a step,
    // but they stay out of colour sorting. Spotted from the name when first added.
    const MATERIAL_WORDS = /(^|[\s-])(rocks?|stones?|pebbles?|gravel|sand|grit|slate|cork|ballast|flock|static grass|grass tufts?|tufts?|leaf litter|texture paste|paste|snow|basing)($|[\s-])/i;
    function isMaterial(paint) {
      if (!paint) return false;
      if (paint.type) return paint.type === "material";
      return MATERIAL_WORDS.test(String(paint.name || ""));
    }

    // v15: leave a step's technique blank and the app guesses it from the step's paints.
    // Checked top to bottom, first match wins. Each word must start a word in the paint's
    // brand or name ("ink" matches "Sepia Ink" but not "Pink Horror"). Otherwise: Layer.
    const GUESS_RULES = [
      ["Varnish", ["ardcoat", "stormshield", "varnish", "gloss", "anti-shine", "matt spray", "satin"]],
      ["Prime", ["primer", "prime", "spray"]],
      ["Texture", ["agrellan", "astrogranite", "armageddon dust", "stirland", "martian iron", "mordant earth",
                   "valhallan blizzard", "lustrian undergrowth", "texture"]],
      ["Contrast", ["contrast", "speedpaint", "xpress", "express", "templar", "blood angels", "snakebite",
                    "gore-grunta", "leviadon", "iyanden", "skeleton horde", "wyldwood", "apothecary white",
                    "aethermatic", "ultramarines blue", "flesh tearers", "basilicanum", "gryph-", "magos",
                    "space wolves grey", "talassar", "terradon", "volupus", "warp lightning", "militarum green",
                    "guilliman flesh", "darkoath", "cygor", "aggaros", "plaguebearer flesh", "nazdreg",
                    "ork flesh", "dark angels green", "akhelian", "shyish", "creed camo", "frostheart",
                    "baal red", "luxion", "pylar", "mantis warriors", "doomfire", "fyreslayer", "imperial fist",
                    "kroxigor", "black legion", "wraithbone contrast"]],
      ["Wash", ["shade", "wash", "ink", "quickshade", "dip", "nuln", "agrax", "earthshade", "carroburg",
                "drakenhof", "nightshade", "seraphim", "sepia", "druchii", "coelia", "greenshade", "athonian",
                "camoshade", "reikland", "fleshshade", "casandora", "fuegan", "berserker", "bloodshade",
                "cryptek", "armourshade", "targor", "rageshade", "poxwalker"]],
      ["Technical", ["technical", "nurgle", "typhus", "ryza rust", "nihilakh", "blood for the blood god",
                     "tesseract", "spiritstone", "soulstone", "waystone", "hexwraith", "mortarion"]],
    ];
    function guessTechnique(paints) {
      const named = (paints || []).filter(p => p && String(p.name || "").trim());
      if (!named.length) return "";
      if (named.every(isMaterial)) return "Texture";
      const texts = named.map(p => plainQuotes(`${p.brand || ""} ${p.name}`).toLowerCase());
      const starts = (text, word) => new RegExp("(^|[^a-z])" + word.replace(/[.*+?^${}()|[\]\\]/g, "\\$&")).test(text);
      for (const [technique, words] of GUESS_RULES) {
        if (texts.some(t => words.some(w => starts(t, w)))) return technique;
      }
      return "Layer";
    }

    // v15: a mix ratio like "2:1", "1:1:2" or "50/50", kept as typed. "" if it isn't one.
    function cleanRatio(value) {
      const t = String(value ?? "").trim().replace(/\s+/g, "");
      return /^\d+(\.\d+)?([:\/]\d+(\.\d+)?)+$/.test(t) ? t : "";
    }
    // The %s a ratio works out as, for n paints (e.g. "2:1" = 67, 33). Null if it doesn't fit.
    function ratioPercents(ratio, n) {
      const t = cleanRatio(ratio);
      if (!t) return null;
      const nums = t.split(/[:\/]/).map(Number);
      const total = nums.reduce((a, b) => a + b, 0);
      if (nums.length !== n || total <= 0) return null;
      // Round down, then hand the leftover % to the biggest remainders, so they add up to 100.
      const exact = nums.map(x => (x * 100) / total);
      const out = exact.map(Math.floor);
      let left = 100 - out.reduce((a, b) => a + b, 0);
      exact.map((x, i) => [x - Math.floor(x), i]).sort((a, b) => b[0] - a[0])
        .forEach(([, i]) => { if (left > 0) { out[i]++; left--; } });
      return out;
    }

    // ================= v16: THE SHARED PAINT-NAME MATCHER =================
    // Used by Paste recipes AND Scan a pot label. Given some typed (or scanned) text it
    // answers one of:
    //   sure     - one clear paint (exact name, a shorthand you've confirmed, or a name
    //              start only one paint has, like "Nuln" = Nuln Oil)
    //   material - a basing material (rocks, snow...), kept as typed
    //   unsure   - it has ideas but won't pick: you choose (a typo, initials like "CM")
    //   new      - nothing like it is known, so it's kept exactly as typed
    // It never quietly swaps a name for a guess: anything unsure is shown to you first.

    // Brand names as people write them, to their proper name.
    const BRAND_WORDS = [
      ["games workshop", "Citadel"], ["warhammer colour", "Citadel"], ["citadel colour", "Citadel"], ["citadel", "Citadel"],
      ["gw", "Citadel"], ["vallejo xpress color", "Vallejo"], ["vallejo xpress", "Vallejo"], ["vallejo express", "Vallejo"],
      ["vallejo game color", "Vallejo"], ["vallejo model color", "Vallejo"], ["vallejo", "Vallejo"],
      ["the army painter", "The Army Painter"], ["army painter", "The Army Painter"], ["pro acryl", "Pro Acryl"],
      ["ak interactive", "AK Interactive"], ["scale75", "Scale75"], ["scale 75", "Scale75"], ["two thin coats", "Two Thin Coats"],
      ["green stuff world", "Green Stuff World"], ["monument hobbies", "Monument Hobbies"],
    ];
    // Names that always mean one paint.
    const BUILT_IN_SHORTHAND = { "gloss": "'Ardcoat", "ardcoat gloss": "'Ardcoat", "ardcoat": "'Ardcoat", "gloss varnish": "'Ardcoat" };
    // Everyday words that start some paint names ("Ice Yellow", "White Scar"). On their own
    // they're too vague to be sure of.
    const VAGUE_WORDS = new Set(["ice", "snow", "white", "black", "grey", "gray", "red", "blue", "green", "yellow", "purple",
      "orange", "pink", "brown", "dark", "light", "pale", "deep", "rust", "blood", "gold", "silver", "iron", "bone", "flesh",
      "skin", "metal", "steel", "bronze", "brass", "copper", "dirt", "mud", "water", "fire", "night", "death", "the"]);

    // Text cut down for comparing: lower case, no apostrophes or "'s", only letters, numbers, spaces.
    // v18: accents are taken off first ("Marrón" = "marron"), so accented names still match.
    function matchKey(text) {
      return plainQuotes(String(text || "")).normalize("NFD").replace(/[̀-ͯ]/g, "").toLowerCase()
        .replace(/'s\b/g, "").replace(/[^a-z0-9]+/g, " ").trim();
    }
    // How many single-letter changes turn a into b (typo distance). Stops early past "max".
    function typoDistance(a, b, max) {
      if (Math.abs(a.length - b.length) > max) return max + 1;
      let prev = Array.from({ length: b.length + 1 }, (_, i) => i);
      for (let i = 1; i <= a.length; i++) {
        const cur = [i];
        let best = i;
        for (let j = 1; j <= b.length; j++) {
          cur[j] = Math.min(prev[j] + 1, cur[j - 1] + 1, prev[j - 1] + (a[i - 1] === b[j - 1] ? 0 : 1));
          best = Math.min(best, cur[j]);
        }
        if (best > max) return max + 1;
        prev = cur;
      }
      return prev[b.length];
    }
    // The brand a bit of text names ("vallejo express" = Vallejo), or "".
    function brandFromText(text) {
      const key = matchKey(text);
      const hit = BRAND_WORDS.find(([words]) => key === words);
      return hit ? hit[1] : "";
    }
    // Splits a brand off the front: "Vallejo Mystic Blue" = { brand: "Vallejo", rest: "Mystic Blue" }.
    function splitBrand(text) {
      const key = matchKey(text);
      for (const [words, brand] of BRAND_WORDS) {
        if (key.startsWith(words + " ")) {
          const n = words.split(" ").length;
          return { brand, rest: String(text).trim().split(/\s+/).slice(n).join(" ") };
        }
      }
      return { brand: "", rest: String(text).trim() };
    }
    // "mystic blue" = "Mystic Blue" (small joining words stay small, ALL CAPS stays).
    function tidyName(text) {
      return String(text).trim().replace(/\s+/g, " ").split(" ").map((w, i) =>
        (i > 0 && /^(and|of|the|in|for|a)$/.test(w)) || /[A-Z]/.test(w) ? w : w.charAt(0).toUpperCase() + w.slice(1)).join(" ");
    }

    // Every paint the matcher can pick from: yours first, then the ones the app knows.
    // v18: while a paste is read, the list is built once and kept (it was rebuilt on every
    // lookup, 100+ times per note). parseRecipeText fills and clears candidateCache.
    let candidateCache = null;
    function matchCandidates() {
      if (candidateCache) return candidateCache;
      const out =book.paints.map(p => ({ brand: p.brand, name: p.name, colour: p.colour, type: p.type, mine: true }));
      // v21.3: a known paint is left out if one of YOUR paints has its name (as before), or if the app
      // already listed the same brand + name. Different brands may share a name ("Black").
      // (Looked up by key, not by searching the list each time: there are 1,000+ known paints now.)
      const textKey = (t) => plainQuotes(String(t || "")).trim().toLowerCase();
      const mineNames = new Set(out.map(o => textKey(o.name)));
      const seen = new Set();
      for (const k of KNOWN_PAINTS) {
        const both = textKey(k.brand) + "|" + textKey(k.name);
        if (mineNames.has(textKey(k.name)) || seen.has(both)) continue;
        seen.add(both);
        out.push({ ...k });
      }
      for (const c of out) { c.key = matchKey(c.name); c.words = c.key.split(" "); }
      return out;
    }
    function shorthandFor(key) {
      const saved = book.shorthand && book.shorthand[key];
      if (saved) return saved;
      const builtIn = BUILT_IN_SHORTHAND[key];
      return builtIn ? { brand: "Citadel", name: builtIn } : null;
    }

    // The matcher itself. hints: { brand, earlier: [paints already seen in the same text] }.
    // v21.3: two passes. First your paints, Citadel and the app's older short lists (so a Citadel
    // name is matched exactly as before); only if that isn't sure are the extra brands tried, and
    // their suggestions go after the first pass's. A Vallejo code ("72.021") is matched straight away.
    function matchPaint(text, hints) {
      hints = hints || {};
      const typed = String(text || "").trim().replace(/\s+/g, " ");
      const everything = matchCandidates();
      const rest = splitBrand(typed);
      const codes = /^[0-9\s.,·:\-]+$/.test(rest.rest || typed) ? vallejoCodes(rest.rest || typed) : [];
      if (codes.length === 1) {
        const hit = everything.find(c => c.codes && c.codes.includes(codes[0]));
        if (hit) return { status: "sure", typed, paint: { brand: hit.brand, name: hit.name, colour: hit.colour || DEFAULT_PAINT_COLOUR, type: hit.type }, suggestions: [] };
      }
      const first = matchPaintIn(text, hints, everything.filter(c => !c.extra));
      if (first.status === "sure" || first.status === "material" || first.status === "none") return first;
      const second = matchPaintIn(text, hints, everything.filter(c => c.extra || c.mine));
      if (first.status === "unsure") {
        const more = second.status === "sure" ? [second.paint] : second.status === "unsure" ? second.suggestions : [];
        const suggestions = first.suggestions.slice();
        for (const s of more) if (suggestions.length < 4 && !suggestions.some(x => sameText(x.name, s.name) && sameText(x.brand, s.brand))) suggestions.push(s);
        return { ...first, suggestions };
      }
      // Nothing like it in the first pass ("new"): the extra brands decide.
      return second.status === "sure" || second.status === "unsure" ? second : first;
    }
    function matchPaintIn(text, hints, pool) {
      hints = hints || {};
      const typed = String(text || "").trim().replace(/\s+/g, " ");
      const result = (status, paint, suggestions) => ({ status, typed, paint: paint || null, suggestions: suggestions || [] });
      if (!typed) return result("none");
      const split = splitBrand(typed);
      const brand = split.brand || hints.brand || "";
      const key = matchKey(split.rest || typed);
      if (!key) return result("none");
      // v18: if the text names a brand ("Vallejo Ivory"), only that brand's paints (or paints with
      // no brand) can match, so it never picks your AK Ivory instead.
      const all = split.brand ? pool.filter(c => !c.brand || sameText(c.brand, split.brand)) : pool;
      const pick = (c) => {
        const full = all.find(x => sameText(x.name, c.name) && (!c.brand || sameText(x.brand, c.brand))) || c;
        return { brand: full.brand || brand, name: full.name, colour: full.colour || DEFAULT_PAINT_COLOUR, type: full.type };
      };
      const preferBrand = (list) => brand ? list.slice().sort((a, b) => sameText(b.brand, brand) - sameText(a.brand, brand)) : list;
      const ranked = (list) => preferBrand(list).sort((a, b) => (b.mine === true) - (a.mine === true));

      // 1. A shorthand you've confirmed before (or 'Ardcoat's nicknames).
      const remembered = shorthandFor(key);
      if (remembered) return result("sure", pick(remembered));
      // 2. The exact name.
      const exact = ranked(all.filter(c => c.key === key));
      // v21.3: the same name in two brands (Vallejo Black, Army Painter Black) with no brand given,
      // none of them yours: ask which.
      const brandsOf = new Set(exact.map(c => matchKey(c.brand)));
      if (exact.length > 1 && brandsOf.size > 1 && !exact[0].mine && !(brand && sameText(exact[0].brand, brand)))
        return result("unsure", null, exact.slice(0, 4).map(pick));
      if (exact.length) return result("sure", pick(exact[0]));
      // 3. A basing material: kept as you wrote it.
      if (MATERIAL_WORDS.test(typed)) return result("material", { brand: "", name: tidyName(split.rest || typed), colour: DEFAULT_PAINT_COLOUR, type: "material" });

      const words = key.split(" ");
      const suggestions = [];
      const suggest = (c) => { if (!suggestions.some(s => sameText(s.name, c.name) && sameText(s.brand, c.brand))) suggestions.push(pick(c)); };
      // 4. The start of a name, whole words: "nuln" = Nuln Oil, "baal" = Baal Red.
      const starts = ranked(all.filter(c => c.words.length > words.length && words.every((w, i) => c.words[i] === w)));
      const vague = words.length === 1 && (VAGUE_WORDS.has(words[0]) || words[0].length < 3);
      const mineStart = starts.filter(c => c.mine);
      if (!vague && (starts.length === 1 || mineStart.length === 1)) return result("sure", pick(mineStart[0] || starts[0]));
      starts.slice(0, 4).forEach(suggest);
      // 5. Initials like "CM" or "SS": never sure, but paints already in the same notes come first.
      if (/^[a-z]{2,4}$/.test(key) && words.length === 1) {
        const initials = (c) => c.words.map(w => w[0]).join("");
        const earlier = (hints.earlier || []).slice().reverse().filter(p => matchKey(p.name).split(" ").map(w => w[0]).join("") === key);
        earlier.forEach(suggest);
        ranked(all.filter(c => initials(c) === key)).slice(0, 4).forEach(suggest);
      }
      // 6. Small typos ("Khorn Red", "Bleck Templar"), or letters dropped ("blangels red").
      const allowed = Math.max(1, Math.floor(key.length / 6));
      const close = all.map(c => ({ c, d: typoDistance(key, c.key, allowed) })).filter(x => x.d <= allowed)
        .sort((a, b) => a.d - b.d).map(x => x.c);
      close.slice(0, 4).forEach(suggest);
      if (key.length >= 6) {
        const squash = key.replace(/ /g, "");
        const inOrder = (small, big) => { let i = 0; for (const ch of big) if (ch === small[i]) i++; return i === small.length; };
        all.filter(c => c.key[0] === key[0] && squash.length >= c.key.replace(/ /g, "").length * 0.6 &&
                        inOrder(squash, c.key.replace(/ /g, ""))).slice(0, 3).forEach(suggest);
      }
      if (suggestions.length || vague || /^[a-z]{1,4}$/.test(key)) return result("unsure", null, suggestions.slice(0, 4));
      // 7. Nothing like it: a new paint, exactly as typed.
      return result("new", { brand, name: tidyName(split.rest || typed), colour: DEFAULT_PAINT_COLOUR });
    }

    // Remembers that "typed" means this paint, for next time (both import and scan).
    function rememberShorthand(typed, paint) {
      const key = matchKey(typed);
      if (!key || !paint || sameText(key, matchKey(paint.name))) return;
      book.shorthand = { ...(book.shorthand || {}), [key]: { brand: paint.brand || "", name: paint.name } };
    }

    // ================= v17: PAINT STATUS, SEARCH AND SHOPPING =================
    // Each paint can have a status, set with one tap. Blank = not set, so the app works the
    // same for anyone who never sets one. Paints the scan added (owned: true) count as Owned.
    const PAINT_STATUSES = [
      { key: "owned", label: "Owned", colour: "var(--good)" },
      { key: "low", label: "Running low", colour: "var(--warn)" },
      { key: "empty", label: "Empty", colour: "var(--bad)" },
      { key: "wishlist", label: "Wishlist", colour: "var(--wish)" },
      { key: "notowned", label: "Not owned", colour: "var(--grey-status)" },
    ];
    const PAINT_STATUS_KEYS = PAINT_STATUSES.map(s => s.key);
    let recipeCanPaint = false;   // the "What can I paint now?" filter (kept while the app is open)
    let shopOpen = false;
    let importReviewIds = null;   // v17.1: the paints a paste import just added, while you check them

    // A paint's status now: its own status, or Owned if the scan added it. "" = not set.
    function paintStatus(paint) {
      if (PAINT_STATUS_KEYS.includes(paint.status)) return paint.status;
      return paint.owned === true ? "owned" : "";
    }
    const statusLabel = (key) => (PAINT_STATUSES.find(s => s.key === key) || {}).label || "";
    // Do you have it to paint with? Owned and running low both count.
    const haveIt = (paint) => { const s = paintStatus(paint); return s === "owned" || s === "low"; };
    // v17.1: how many you have. Blank means one; only counts above one are stored.
    const paintQty = (paint) => (Number.isInteger(paint.qty) && paint.qty > 1 ? paint.qty : 1);
    // Until someone sets a status, the have/missing badges and the filter stay off.
    const anyStatusSet = () => book.paints.some(p => paintStatus(p) !== "");

    // Sets a status (or clears it, with ""). Keeps the older owned field in step.
    function applyPaintStatus(paint, key) {
      if (key) {
        paint.status = key;
        paint.owned = key === "owned" || key === "low";
        if (key !== "low") delete paint.spare;
        if (!haveIt({ status: key })) delete paint.qty;
      } else {
        delete paint.status;
        delete paint.spare;
        delete paint.qty;
        paint.owned = false;
      }
    }

    // The status buttons in a paint's details. Tap one to set it; tap it again to clear it.
    function buildStatusRow(paint) {
      const wrap = document.createElement("div");
      wrap.className = "status-row";
      const label = document.createElement("div");
      label.className = "panel-field";
      label.textContent = "Status";
      const chips = document.createElement("div");
      chips.className = "chips";
      chips.style.marginTop = "0";
      const current = paintStatus(paint);
      for (const s of PAINT_STATUSES) {
        const chip = makeChip(s.label, current === s.key, () => {
          applyPaintStatus(paint, current === s.key ? "" : s.key);
          render();
        }, s.colour);
        chip.classList.add("status-chip");
        chip.dataset.status = s.key;
        chips.appendChild(chip);
      }
      wrap.append(label, chips);
      if (haveIt(paint)) {   // v17.1: how many you have (default one)
        const qtyRow = document.createElement("div");
        qtyRow.className = "qty-row";
        const howMany = document.createElement("span");
        howMany.textContent = "How many";
        const fewer = document.createElement("button");
        fewer.className = "plain-button qty-step";
        fewer.textContent = "−";
        fewer.setAttribute("aria-label", "One fewer");
        const count = document.createElement("span");
        count.className = "qty-count";
        count.textContent = String(paintQty(paint));
        const more = document.createElement("button");
        more.className = "plain-button qty-step";
        more.textContent = "+";
        more.setAttribute("aria-label", "One more");
        const setQty = (n) => {
          n = Math.max(1, Math.min(99, n));
          if (n > 1) paint.qty = n; else delete paint.qty;
          render();
        };
        fewer.addEventListener("click", () => setQty(paintQty(paint) - 1));
        more.addEventListener("click", () => setQty(paintQty(paint) + 1));
        qtyRow.append(howMany, fewer, count, more);
        wrap.appendChild(qtyRow);
      }
      if (current === "low") {
        const spare = document.createElement("label");
        spare.className = "check-label spare-tick";
        const box = document.createElement("input");
        box.type = "checkbox";
        box.checked = paint.spare === true;
        box.addEventListener("change", () => { paint.spare = box.checked; render(); });
        spare.append(box, " Spare in stock");
        wrap.appendChild(spare);
      }
      const hint = document.createElement("p");
      hint.className = "hint";
      hint.style.margin = "6px 0 0";
      hint.textContent = "Tap a status again to clear it.";
      wrap.appendChild(hint);
      return wrap;
    }

    // A small coloured label showing a paint's status, or nothing if it isn't set.
    function statusPill(paint) {
      const key = paintStatus(paint);
      if (!key) return null;
      const pill = document.createElement("span");
      pill.className = "status-pill s-" + key;
      pill.textContent = statusLabel(key) + (key === "low" && paint.spare ? " · spare" : "");
      return pill;
    }

    // Have / Missing next to each paint in a recipe. Hidden until a status is set.
    function haveBadge(paint) {
      if (!anyStatusSet()) return null;
      const badge = document.createElement("span");
      badge.className = "have-badge " + (haveIt(paint) ? "have" : "missing");
      badge.textContent = haveIt(paint) ? "✓ Have" : "✗ Missing";
      return badge;
    }

    // True if you have every paint a recipe uses.
    function canPaintNow(recipe) {
      const ids = new Set();
      for (const s of recipe.steps) for (const sp of s.paints) ids.add(sp.paint);
      if (!ids.size) return false;
      return [...ids].every(id => { const p = paintById(id); return !!p && haveIt(p); });
    }

    // The "What can I paint now?" button above the recipe list.
    function renderCanPaintBox() {
      const box = document.getElementById("can-paint-box");
      box.innerHTML = "";
      box.appendChild(makeChip("What can I paint now?", recipeCanPaint, () => {
        recipeCanPaint = !recipeCanPaint;
        renderRecipeList();
      }));
      document.getElementById("can-paint-hint").textContent =
        recipeCanPaint && !anyStatusSet() ? "Mark the paints you own on Your Palette first, then this list is useful." : "";
    }

    // ----- Shopping list -----
    // Running low, empty and wishlist paints, plus paints a recipe uses that you don't have.
    function shoppingItems() {
      const recipeCount = new Map();
      for (const r of book.recipes) {
        const ids = new Set();
        for (const s of r.steps) for (const sp of s.paints) ids.add(sp.paint);
        for (const id of ids) recipeCount.set(id, (recipeCount.get(id) || 0) + 1);
      }
      const items = [];
      for (const p of book.paints) {
        if (isExamplePaint(p)) continue;   // v24: example paints never go on the shopping list
        const key = paintStatus(p);
        const used = recipeCount.get(p.id) || 0;
        let reason = "";
        if (key === "low") reason = "running low" + (p.spare ? " (spare in stock)" : "");
        else if (key === "empty") reason = "empty";
        else if (key === "wishlist") reason = "wishlist";
        else if (key !== "owned" && used) reason = `missing, used in ${plural(used, "recipe")}`;
        if (reason) items.push({ paint: p, reason });
      }
      return items.sort((a, b) => (a.paint.brand || "￿").localeCompare(b.paint.brand || "￿") || a.paint.name.localeCompare(b.paint.name));
    }

    // The list as plain text, one brand at a time (for copy as text).
    function shoppingText(items) {
      const groups = new Map();
      for (const i of items) {
        const brand = i.paint.brand || "No brand";
        if (!groups.has(brand)) groups.set(brand, []);
        groups.get(brand).push(i);
      }
      const names = [...groups.keys()].sort((a, b) => (a === "No brand") - (b === "No brand") || a.localeCompare(b));
      const lines = ["Shopping list", ""];
      for (const brand of names) {
        lines.push(brand);
        for (const i of groups.get(brand)) lines.push(`- ${i.paint.name}: ${i.reason}`);
        lines.push("");
      }
      if (!items.length) lines.push("Nothing to buy.");
      return lines.join("\n").trimEnd();
    }

    // ----- v19.1: SHOP LINKS ("Buy these") -----
    // EVERY shop lives in this ONE list, so changing or adding a shop is one edit here.
    //   name:   shown on the button
    //   search: the shop's own search address; {q} is replaced by the paint's name (some shops,
    //           like Wayland, want it twice)
    //   brands: "all", or a list of the only brands the shop sells (its button shows only for those)
    //   extra:  added to the end of every link for that shop. Empty for now (plain links, no
    //           affiliate codes). An affiliate code would go here later, e.g. "&ref=CODE"
    //           (and then: an "Ad" line, a Settings switch and an updated Privacy topic).
    //   checked: when the search address was last tried by hand
    const SHOPS = [
      { id: "firestorm", name: "Firestorm Games", search: "https://www.firestormgames.co.uk/products?q={q}", brands: "all", extra: "", checked: "10 Oct 2026" },
      { id: "wayland", name: "Wayland Games", search: "https://www.waylandgames.co.uk/search?query={q}&q={q}", brands: "all", extra: "", checked: "10 Oct 2026" },
      { id: "element", name: "Element Games", search: "https://elementgames.co.uk/search?q={q}", brands: "all", extra: "", checked: "10 Oct 2026" },
      { id: "armypainter", name: "The Army Painter", search: "https://thearmypainter.com/search?q={q}", brands: ["The Army Painter"], extra: "", checked: "10 Oct 2026" },
    ];
    let shopLinksOpen = null;   // the id of the shop whose links are showing, or null

    const shopSells = (shop, brand) => shop.brands === "all" || shop.brands.some(b => sameText(b, brand || ""));
    // What to type into the shop's search: the paint's name ONLY. Checked by hand on 10 Oct:
    // shops' searches match words in their product titles, and many titles leave the brand out
    // ("Warhammer Base: Macragge Blue", "Warpaints Fanatic: Ivory White"), so "Vallejo Ivory" or
    // "The Army Painter Matt White" found nothing at Firestorm while "Ivory" and "Matt White" did.
    function shopSearchWords(shop, paint) {
      return String(paint.name || "").trim();
    }
    function shopLink(shop, paint) {
      const words = encodeURIComponent(shopSearchWords(shop, paint)).replace(/%20/g, "+");
      return shop.search.split("{q}").join(words) + shop.extra;
    }
    // The shops that sell at least one paint on the list, each with the paints it sells.
    function shopsFor(items) {
      return SHOPS.map(shop => ({ shop, paints: items.map(i => i.paint).filter(p => shopSells(shop, p.brand)) }))
        .filter(x => x.paints.length);
    }
    function buildBuyBar(items) {
      const bar = document.createElement("div");
      bar.className = "buy-bar";
      bar.id = "buy-bar";
      const head = document.createElement("h3");
      head.textContent = "Buy these";
      const row = document.createElement("div");
      row.className = "buy-shops";
      bar.append(head, row);
      const offers = shopsFor(items);
      if (!offers.some(o => o.shop.id === shopLinksOpen)) shopLinksOpen = null;
      for (const { shop, paints } of offers) {
        const b = document.createElement("button");
        b.type = "button";
        b.className = "plain-button";
        b.dataset.shop = shop.id;
        b.textContent = shop.name;
        b.setAttribute("aria-expanded", String(shopLinksOpen === shop.id));
        b.addEventListener("click", () => { shopLinksOpen = shopLinksOpen === shop.id ? null : shop.id; renderShopPanel(); });
        row.appendChild(b);
        if (shopLinksOpen !== shop.id) continue;
        const list = document.createElement("ul");
        list.className = "buy-links";
        list.id = "buy-links";
        for (const p of paints) {
          const li = document.createElement("li");
          const a = document.createElement("a");
          a.href = shopLink(shop, p);
          a.target = "_blank";
          a.rel = "noopener noreferrer";   // the shop isn't told which page sent you
          const name = document.createElement("span");
          name.textContent = p.name;
          const go = document.createElement("span");
          go.textContent = "Search ↗";
          a.append(name, go);
          a.setAttribute("aria-label", `Search ${shop.name} for ${p.name} (opens the shop's website)`);
          li.appendChild(a);
          list.appendChild(li);
        }
        bar.appendChild(list);
      }
      const note = document.createElement("p");
      note.className = "hint";
      note.textContent = shopLinksOpen
        ? "Each link opens the shop's own search for that paint. Plain links: Minifolio isn't paid for them, and only the paint's name goes to the shop."
        : "Tap a shop to see a search link for each paint it sells.";
      bar.appendChild(note);
      return bar;
    }

    function renderShopPanel() {
      const panel = document.getElementById("shop-panel");
      const button = document.getElementById("shop-button");
      panel.classList.toggle("hidden", !shopOpen);
      button.setAttribute("aria-expanded", String(shopOpen));
      if (!shopOpen) return;
      panel.innerHTML = "";
      const items = shoppingItems();
      const card = document.createElement("div");
      card.className = "card";
      const title = document.createElement("h2");
      title.textContent = "Shopping list";
      title.style.fontSize = "18px";
      const sub = document.createElement("p");
      sub.className = "hint";
      sub.style.margin = "0 0 10px";
      sub.textContent = !items.length ? "Nothing to buy. Mark your paints on Your Palette to build this list."
        : `${plural(items.length, "paint")} to get: running low, empty, wishlist, and paints your recipes use that you don't have.`;
      card.append(title, sub);
      if (items.length && !anyStatusSet()) {
        const warn = document.createElement("p");
        warn.className = "hint";
        warn.style.margin = "0 0 10px";
        warn.textContent = "No statuses set yet, so every paint your recipes use is listed as missing. Mark what you own to make it accurate.";
        card.appendChild(warn);
      }
      if (items.length) {
        card.appendChild(buildBuyBar(items));   // v19.1: shop links at the top
        const groups = new Map();
        for (const i of items) {
          const brand = i.paint.brand || "No brand";
          if (!groups.has(brand)) groups.set(brand, []);
          groups.get(brand).push(i);
        }
        const names = [...groups.keys()].sort((a, b) => (a === "No brand") - (b === "No brand") || a.localeCompare(b));
        for (const brand of names) {
          const head = document.createElement("div");
          head.className = "shop-brand";
          head.textContent = brand;
          const list = document.createElement("ul");
          list.className = "shop-list";
          for (const i of groups.get(brand)) {
            const li = document.createElement("li");
            li.textContent = i.paint.name + " ";
            const why = document.createElement("small");
            why.textContent = "· " + i.reason;
            li.appendChild(why);
            list.appendChild(li);
          }
          card.append(head, list);
        }
        const copy = document.createElement("button");
        copy.className = "primary-button";
        copy.style.width = "100%";
        copy.style.marginTop = "12px";
        copy.textContent = "Copy as text";
        copy.addEventListener("click", () => copyText(shoppingText(shoppingItems()), "Shopping list"));
        card.appendChild(copy);
      }
      panel.appendChild(card);
    }
    document.getElementById("shop-button").addEventListener("click", () => { shopOpen = !shopOpen; renderShopPanel(); });

    // ----- v17.1: check the paints a paste import just added -----
    function renderImportReview() {
      const box = document.getElementById("import-review");
      if (!box) return;
      const ids = importReviewIds ? importReviewIds.filter(id => paintById(id)) : [];
      box.classList.toggle("hidden", !ids.length);
      box.innerHTML = "";
      if (!ids.length) return;
      const title = document.createElement("h2");
      title.textContent = "Check your import";
      title.style.fontSize = "18px";
      const hint = document.createElement("p");
      hint.className = "hint";
      hint.style.margin = "0 0 10px";
      hint.textContent = `${plural(ids.length, "paint")} came in as Owned. Change the status or how many you have on any of them below, then press Done.`;
      const done = document.createElement("button");
      done.className = "primary-button";
      done.style.width = "100%";
      done.textContent = "Done";
      done.addEventListener("click", () => { importReviewIds = null; render(); });
      box.append(title, hint, done);
    }

    // ----- Search or add a paint on Your Palette -----
    // Type a name: see whether you own it, it's running low, or you don't have it.
    // Typos and remembered shorthand work, because it uses the shared matcher.
    function paletteResultCard(p) {
      const found = () => book.paints.find(x => sameText(x.name, p.name) && (!p.brand || !x.brand || sameText(x.brand, p.brand)));
      const mine = found();
      const current = mine ? paintStatus(mine) : "";
      const wrap = document.createElement("div");
      wrap.className = "scan-result";
      const head = document.createElement("div");
      head.className = "paint-line";
      head.append(makeSwatch(mine ? mine.colour : p.colour || DEFAULT_PAINT_COLOUR), p.name);
      if (p.brand) {
        const brand = document.createElement("span");
        brand.className = "brand";
        brand.textContent = p.brand;
        head.appendChild(brand);
      }
      const verdict = document.createElement("p");
      verdict.className = "hint";
      verdict.style.margin = "6px 0 10px";
      verdict.textContent = mine
        ? (current ? `In your palette: ${statusLabel(current).toLowerCase()}.` : "In your palette. Status not set yet.")
        : "Not in your palette yet. Tap a status to add it.";
      const chips = document.createElement("div");
      chips.className = "chips";
      for (const s of PAINT_STATUSES) {
        const chip = makeChip(s.label, current === s.key, () => {
          const paint = found() || findOrAddPaint(p.brand || "", p.name, p.colour || DEFAULT_PAINT_COLOUR);
          if (p.type === "material") paint.type = "material";
          applyPaintStatus(paint, current === s.key ? "" : s.key);
          render();
        }, s.colour);
        chip.classList.add("status-chip");
        chip.dataset.status = s.key;
        chips.appendChild(chip);
      }
      wrap.append(head, verdict, chips);
      return wrap;
    }

    function renderPaletteSearch() {
      const input = document.getElementById("palette-search");
      const box = document.getElementById("palette-search-result");
      if (!input || !box) return;
      box.innerHTML = "";
      const typed = input.value.trim();
      if (!typed) return;
      const m = matchPaint(typed);
      if (m.status === "sure" || m.status === "material" || m.status === "new") {
        box.appendChild(paletteResultCard(m.paint));
      } else if (m.suggestions.length) {
        const q = document.createElement("p");
        q.className = "hint";
        q.style.margin = "0 0 8px";
        q.textContent = "Which paint do you mean?";
        const chips = document.createElement("div");
        chips.className = "chips";
        for (const p of m.suggestions) {
          chips.appendChild(makeChip(p.name + (p.brand ? ` · ${p.brand}` : ""), false, () => {
            input.value = p.name;
            renderPaletteSearch();
          }));
        }
        box.append(q, chips);
      } else {
        const none = document.createElement("p");
        none.className = "hint";
        none.style.margin = "0";
        none.textContent = "Not sure which paint that is. Try the full name.";
        box.appendChild(none);
      }
    }
    document.getElementById("palette-search").addEventListener("input", renderPaletteSearch);

    // ================= v16: READING PASTED RECIPE NOTES =================
    // Turns notes like the ones people keep in Google Keep into schemes, parts and steps.
    // The result is a preview: nothing is saved until you confirm it.

    // Technique words people write, to the technique they mean.
    const TECHNIQUE_WORDS = [
      ["edge highlight", "Edge highlight"], ["edge highlights", "Edge highlight"], ["wet blend", "Wet blend"],
      ["dry brush", "Dry brush"], ["dry brushed", "Dry brush"], ["drybrush", "Dry brush"], ["drybrushed", "Dry brush"],
      ["drybrushing", "Dry brush"], ["base coat", "Base coat"], ["basecoat", "Base coat"], ["basecoated", "Base coat"],
      ["base", "Base coat"], ["prime", "Prime"], ["primer", "Prime"], ["primed", "Prime"], ["undercoat", "Prime"],
      ["zenithal", "Airbrush"], ["airbrush", "Airbrush"], ["wash", "Wash"], ["washed", "Wash"], ["shade", "Wash"],
      ["layer", "Layer"], ["highlight", "Edge highlight"], ["highlights", "Edge highlight"], ["glaze", "Glaze"],
      ["stipple", "Stipple"], ["sponge", "Sponge"], ["contrast", "Contrast"], ["varnish", "Varnish"], ["technical", "Technical"],
    ];
    // The technique a few words name (your own techniques count too), or "".
    function techniqueFromWords(text) {
      const key = matchKey(text);
      if (!key) return "";
      const own = book.techniques.find(t => matchKey(t) === key);
      if (own) return own;
      const hit = TECHNIQUE_WORDS.find(([w]) => w === key);
      if (!hit) return "";
      return book.techniques.find(t => sameText(t, hit[1])) || hit[1];
    }
    // Pulls technique words off the start ("drybrush in grey seer") or end ("agrax wash").
    function splitTechnique(text) {
      let words = String(text).trim().split(/\s+/);
      let technique = "";
      for (let n = Math.min(2, words.length - 1); n >= 1 && !technique; n--) {
        const t = techniqueFromWords(words.slice(0, n).join(" "));
        if (t) { technique = t; words = words.slice(n); }
      }
      if (!technique) for (let n = Math.min(2, words.length - 1); n >= 1 && !technique; n--) {
        const t = techniqueFromWords(words.slice(-n).join(" "));
        if (t) { technique = t; words = words.slice(0, -n); }
      }
      while (words.length > 1 && /^(in|with|of|then|and|on|using)$/i.test(words[0])) words.shift();
      return { technique, rest: words.join(" ") };
    }
    const OPTIONAL_WORDS = /\b(optional|if required|if needed|if you want|take it or leave it)\b/i;
    const RATIO_TEXT = /^\d+(?:\.\d+)?(?:\s*[:\/]\s*\d+(?:\.\d+)?)+$/;

    // Splits on commas and semicolons that aren't inside (brackets).
    function splitOutside(text, separators) {
      const out = [];
      let depth = 0, cur = "";
      for (const ch of text) {
        if (ch === "(") depth++;
        if (ch === ")") depth = Math.max(0, depth - 1);
        if (!depth && separators.includes(ch)) { out.push(cur); cur = ""; continue; }
        cur += ch;
      }
      out.push(cur);
      return out;
    }

    // Reads one paint mention with its extras: "Seraphim Sepia (take it or leave it)",
    // "Magical crack brown (Agrellan Earth)", "Sigvald Burgundy in gaps".
    // Returns { technique, paint: matcher result or null, note, optional, ratio, coats }.
    function readMention(raw, hints) {
      let text = String(raw).trim();
      const out = { technique: "", paint: null, note: [], optional: false, ratio: "", coats: 1 };
      // Brackets first: a ratio, a coat count, a real paint name, or a note.
      let bracketPaint = null;
      text = text.replace(/\(([^)]*)\)/g, (_, inner) => {
        const t = inner.trim();
        if (!t) return " ";
        if (RATIO_TEXT.test(t)) { out.ratio = t.replace(/\s+/g, ""); return " "; }
        const coats = t.match(/^(\d+)\s*(?:x|coats?)$/i);
        if (coats) { out.coats = Number(coats[1]); return " "; }
        const asPaint = matchPaint(t, hints);
        if (asPaint.status === "sure") { bracketPaint = asPaint; return " "; }
        if (/^optional$/i.test(t)) { out.optional = true; return " "; }
        out.note.push(t);
        if (OPTIONAL_WORDS.test(t)) out.optional = true;
        // A technique only counts at the start: "(drybrush if required)", not "(…around the base)".
        const first = t.split(/\s+/);
        const tech = techniqueFromWords(first.slice(0, 2).join(" ")) || techniqueFromWords(first[0]);
        if (tech) out.technique = tech;
        return " ";
      }).replace(/\s+/g, " ").trim();
      if (/\boptional\b/i.test(text)) { out.optional = true; text = text.replace(/\boptional\b/i, "").trim(); }

      // Just a technique ("Prime")? Then it's a step with no paint.
      const onlyTechnique = techniqueFromWords(text);
      if (onlyTechnique) { out.technique = onlyTechnique; out.note = out.note.join("; "); return out; }
      // The whole name first, before any words are taken off it ("Contrast Medium" is a paint).
      const whole = text && !bracketPaint ? matchPaint(text, hints) : null;
      // v18: "Texture Sand" is the Texture technique with sand, not a material called "Texture Sand".
      // ("Texture paste" stays a material.)
      if (whole && whole.status === "material" && !/\btexture paste\b/i.test(text)) {
        const t = splitTechnique(text);
        const rest = t.technique && t.rest ? matchPaint(t.rest, hints) : null;
        if (rest && (rest.status === "material" || rest.status === "sure")) {
          out.technique = t.technique; out.paint = rest; out.note = out.note.join("; "); return out;
        }
      }
      if (whole && (whole.status === "sure" || whole.status === "material")) { out.paint = whole; out.note = out.note.join("; "); return out; }
      const split = splitTechnique(text);
      if (split.technique) out.technique = split.technique;
      // "dilute corvus", "thinned nuln": how it's applied goes in the note.
      const how = split.rest.match(/^(dilute|diluted|thinned|thin|watered down|watered|heavily|lightly|sparingly|sparing)\s+(.+)$/i);
      if (how) { out.note.unshift(how[1].toLowerCase()); split.rest = splitTechnique(how[2]).rest; }
      // "Magical crack brown (Agrellan Earth)": the real name wins, the nickname becomes a note.
      if (bracketPaint) {
        const full = matchPaint(text, hints);
        if (full.status !== "sure") {
          if (split.rest) out.note.unshift(`aka ${split.rest}`);
          out.paint = bracketPaint;
          out.note = out.note.join("; ");
          return out;
        }
      }
      let name = split.rest;
      if (!name) { out.note = out.note.join("; "); return out; }
      // The whole thing first; if that isn't sure, the longest start that is ("Sigvald Burgundy in gaps").
      let match = matchPaint(name, hints);
      // v18: nothing to match on (no a–z letters, e.g. "下地は黒"): keep it as a note, not a paint.
      if (match.status === "none") { out.note.unshift(name); out.note = out.note.join("; "); return out; }
      if (match.status !== "sure" && match.status !== "material") {
        const words = name.split(" ");
        for (let n = words.length - 1; n >= 1; n--) {
          const head = matchPaint(words.slice(0, n).join(" "), hints);
          if (head.status === "sure") {
            match = head;
            out.note.unshift(words.slice(n).join(" "));
            break;
          }
        }
      }
      out.paint = match;
      out.note = out.note.join("; ");
      return out;
    }

    // v18: "Ushabti Bone and Wraithbone" is two paints, like "+" (before, Wraithbone ended up in
    // the note). Only split when EVERY piece is a paint the app is sure about (or a basing
    // material), so "Ushabti Bone and a bit of white" or "Mephiston Red and then Agrax" stay
    // one paint with a note, and a name that is itself a paint is never split.
    function splitOnAnd(name, ctx) {
      if (!/\band\b/i.test(name) || /[()]/.test(name)) return [name];
      const pieces = name.split(/\s+and\s+/i).map(s => s.trim());
      if (pieces.length < 2 || pieces.some(s => !s)) return [name];
      const hints = { brand: ctx.brand, earlier: ctx.seen };
      if (matchPaint(name, hints).status === "sure") return [name];
      const ok = pieces.every(s => {
        const m = readMention(s, hints);
        return m.paint && (m.paint.status === "sure" || m.paint.status === "material") && !m.note;
      });
      return ok ? pieces : [name];
    }

    // Reads one "segment" of a line (between commas) into one or more steps.
    function readSegment(segment, ctx) {
      let text = segment.trim().replace(/^(?:\d+[.)]|[-•*])\s+/, "").trim();
      if (!text) return [];
      // "No basecoat", "No varnish": a remark, not a step.
      if (/^(no|skip|don'?t)\b/i.test(text)) return [{ remark: text }];
      // An arrow chain is one step per paint, in order.
      const chain = text.split(/\s*(?:->|→|=>|>)\s*/).filter(Boolean);
      if (chain.length > 1) return chain.flatMap(part => readSegment(part, ctx));

      // A technique before a mix: "Contrast 1:1 Baal Red:Contrast Medium".
      let segTechnique = "";
      const techLead = text.match(/^([a-z' ]+?)\s+(\d.*)$/i);
      if (techLead && techniqueFromWords(techLead[1])) { segTechnique = techniqueFromWords(techLead[1]); text = techLead[2]; }
      // v18: "Seraphim Sepia wash 1:2 with Contrast Medium": a paint, a ratio, then "with" the
      // other paint. Rewritten as "1:2 Seraphim Sepia:Contrast Medium" and read as below.
      const withMix = text.match(/^(.+?)\s+(\d+(?:\.\d+)?\s*[:\/]\s*\d+(?:\.\d+)?)\s+(?:with|and|to|in|\+|&)\s+(.+)$/i);
      if (withMix) {
        const asPaint = matchPaint(withMix[1], { brand: ctx.brand });
        const first = asPaint.status === "sure" ? { technique: "", rest: withMix[1] } : splitTechnique(withMix[1]);
        if (first.technique && !segTechnique) segTechnique = first.technique;
        text = `${withMix[2]} ${first.rest}:${withMix[3]}`;
      }
      // A ratio up front, with names joined by ":" or "/": "2:1 frostheart:CM".
      let ratio = "";
      const lead = text.match(/^(\d+(?:\.\d+)?(?:\s*[:\/]\s*\d+(?:\.\d+)?)+)\s+(.*)$/);
      let names;
      if (lead) {
        ratio = lead[1].replace(/\s+/g, "");
        const n = ratio.split(/[:\/]/).length;
        const byColon = lead[2].split(/\s*[:\/]\s*/);
        names = byColon.length === n ? byColon : lead[2].split(/\s*(?:\+|&|\band\b)\s*/i);
        if (names.length === 1 && n > 1) {
          // "Vallejo express 50/50": a brand and a mix for the next few lines.
          const brand = brandFromText(lead[2]);
          if (brand) { ctx.brand = brand; ctx.pendingMix = { ratio, n, paints: [] }; return []; }
        }
      } else {
        // "50/50" or "2:1" at the end, and "A + B" / "A & B" for a mix.
        const tail = text.match(/^(.*?)\s+(\d+(?:\.\d+)?(?:\s*[:\/]\s*\d+(?:\.\d+)?)+)$/);
        if (tail) { ratio = tail[2].replace(/\s+/g, ""); text = tail[1]; }
        const brandOnly = brandFromText(text);
        if (brandOnly) {
          ctx.brand = brandOnly;
          if (ratio) ctx.pendingMix = { ratio, n: ratio.split(/[:\/]/).length, paints: [] };
          return [];
        }
        names = splitOutside(text, ["+", "&"]).flatMap(n => splitOnAnd(n, ctx));
      }
      const mentions = names.map(n => readMention(n, { brand: ctx.brand, earlier: ctx.seen }));
      for (const m of mentions) if (m.paint && m.paint.paint) ctx.seen.push(m.paint.paint);
      if (!ratio) ratio = mentions.map(m => m.ratio).find(Boolean) || "";

      const step = (ms, r) => ({
        technique: ms.map(m => m.technique).find(Boolean) || segTechnique,
        coats: Math.max(...ms.map(m => m.coats)),
        paints: ms.filter(m => m.paint).map(m => m.paint),
        ratio: r || "",
        note: ms.map(m => m.note).filter(Boolean).join("; "),
        optional: ms.some(m => m.optional),
        source: segment.trim(),
      });
      // "Eshin grey base + nuln" is two steps (a base coat, then a wash), not a mix.
      if (mentions.length > 1 && !ratio) {
        const kinds = mentions.map(m => m.technique || guessTechnique(m.paint && m.paint.paint ? [m.paint.paint] : []));
        if (new Set(kinds).size > 1 || mentions.some(m => m.technique)) return mentions.map(m => step([m], ""));
      }
      return [step(mentions, mentions.length > 1 ? ratio : "")];
    }

    // Is this line a heading? Returns { name, rest, kind } or null.
    //   "Eyes:" / "Chitin;" / "Recipe: Eyes"      -> a part
    //   "Viorla; white prime, dilute corvus"      -> a part with steps on the same line
    //   "Rocks = Eshin grey base + nuln"          -> a sub-part of the part above
    //   "Scheme: Tyranids"                        -> a scheme
    function readHeading(line) {
      const scheme = line.match(/^(?:scheme|army|faction)\s*[:;-]\s*(.+)$/i);
      if (scheme) return { kind: "scheme", name: scheme[1].trim(), rest: "" };
      const recipe = line.match(/^recipe\s*[:;-]\s*(.+)$/i);
      if (recipe) return { kind: "part", name: recipe[1].trim(), rest: "" };
      const eq = line.match(/^([^=,()]+?)\s*=\s*(.*)$/);
      if (eq && !techniqueFromWords(eq[1])) return { kind: "sub", name: eq[1].trim(), rest: eq[2].trim() };
      const colon = line.match(/^([^:;,()]+?)\s*[:;]\s*(.*)$/);
      // v18: the ":" in a ratio isn't a heading ("Wet blend 3:1 Kantor Blue:White").
      const ratioColon = colon && /\d$/.test(colon[1]) && /^\d/.test(colon[2]);
      // v18: a line ending in ":" or ";" is always a heading, even a technique word ("Base;").
      const endsLine = colon && !colon[2];
      if (colon && !ratioColon && !RATIO_TEXT.test(colon[1]) && !/^\d/.test(colon[1]) && (endsLine || !techniqueFromWords(colon[1]))) {
        return { kind: "part", name: colon[1].trim(), rest: colon[2].trim() };
      }
      return null;
    }

    // Faction names the app knows (yours, plus the well-known ones it has colours for).
    function knownFactionNames() {
      const names = new Set(models.map(m => matchKey(m.faction)).filter(Boolean));
      for (const k of Object.keys(USUAL_FACTION_COLOURS)) for (const n of k.split("|")) names.add(matchKey(n));
      return names;
    }

    // v21.1: "Ultramarines armour" / "Death Guard cloak and trim": a known faction name
    // followed only by part or heading words. Returns { faction, part } (part may be "")
    // or null. Without this the line read as the paint "Ultramarines Blue".
    const HEADING_WORDS = new Set(["armor", "armour", "armours", "armors", "cloth", "cloak", "cloaks", "robe", "robes",
      "skin", "flesh", "metal", "metals", "metallics", "trim", "eyes", "eye", "lenses", "lens", "weapon", "weapons",
      "leather", "gems", "gem", "base", "bases", "basing", "scheme", "schemes", "recipe", "recipes", "colours",
      "colors", "colour", "color", "paints", "paint", "army", "notes", "guide"]);
    function factionLead(line, factions) {
      const words = line.trim().split(/\s+/);
      for (let k = words.length - 1; k >= 1; k--) {
        if (!factions.has(matchKey(words.slice(0, k).join(" ")))) continue;
        const rest = words.slice(k);
        const own = new Set((Array.isArray(book.parts) ? book.parts : DEFAULT_PARTS).map(p => matchKey(p)));
        const fits = rest.every(w => ["and", "&", "+"].includes(w.toLowerCase()) || HEADING_WORDS.has(matchKey(w)) || own.has(matchKey(w)));
        if (!fits || !rest.some(w => !["and", "&", "+"].includes(w.toLowerCase()))) return null;
        const restText = rest.join(" ");
        // Only a part if it's a real part word (not "scheme", "recipes", "colours"...).
        const general = rest.every(w => ["scheme", "schemes", "recipe", "recipes", "colours", "colors", "colour", "color", "paints", "paint", "army", "notes", "guide", "and", "&", "+"].includes(w.toLowerCase()));
        return { faction: words.slice(0, k).join(" "), part: general ? "" : restText.charAt(0).toUpperCase() + restText.slice(1) };
      }
      return null;
    }

    // The main reader. Returns { schemes: [{ name, parts: [{ name, notes, steps }] }] }.
    // v18: builds the paint list once for the whole paste (much faster), then lets it go.
    function parseRecipeText(text) {
      candidateCache = null;
      candidateCache = matchCandidates();
      try { return readRecipeText(text); } finally { candidateCache = null; }
    }
    function readRecipeText(text) {
      const lines = plainQuotes(String(text || "")).replace(/\r/g, "").replace(/\t/g, " ").split("\n");
      const factions = knownFactionNames();
      const schemes = [];
      let scheme = null, part = null, parent = null, blanks = 2;
      const ctx = { brand: "", pendingMix: null, seen: [] };
      const startScheme = (name) => { scheme = { name, parts: [] }; schemes.push(scheme); part = null; parent = null; };
      const startPart = (name, sub) => {
        if (!scheme) startScheme("");
        const full = sub && parent ? `${parent.name} – ${name}` : name;
        part = scheme.parts.find(p => sameText(p.name, full));
        if (!part) { part = { name: full, notes: [], steps: [] }; scheme.parts.push(part); }
        if (!sub) parent = part;
        ctx.brand = ""; ctx.pendingMix = null;
      };
      const addSteps = (stepText, sticky) => {
        if (!part) startPart(WHOLE_MODEL, false);
        // Commas and mid-line semicolons split steps. "drybrushed;" makes the rest dry brushed.
        let technique = sticky || "";
        const segments = splitOutside(stepText, [",", ";"]).map(s => s.trim()).filter(Boolean);
        segments.forEach((seg, i) => {
          const alone = techniqueFromWords(seg);
          if (alone && i < segments.length - 1) { technique = alone; return; }
          for (const step of readSegment(seg, ctx)) {
            if (step.remark) { part.notes.push(step.remark); continue; }
            if (!step.technique && technique) step.technique = technique;
            if (!step.paints.length && !step.technique && step.note) { part.notes.push(step.note); continue; }
            if (!step.paints.length && !step.technique) continue;
            // "Vallejo express 50/50" then two paints: they're one mixed step.
            const mix = ctx.pendingMix;
            if (mix && step.paints.length === 1) {
              if (!mix.step) { mix.step = { ...step, ratio: mix.ratio, paints: [] }; part.steps.push(mix.step); }
              else mix.step.source += `\n${step.source}`;
              mix.step.paints.push(step.paints[0]);
              if (mix.step.paints.length >= mix.n) ctx.pendingMix = null;
              continue;
            }
            part.steps.push(step);
          }
        });
      };

      for (let i = 0; i < lines.length; i++) {
        const line = lines[i].trim();
        // v18: a line with no letters or numbers (a divider like "-----" or "***", or just an
        // emoji) is treated like a blank line.
        if (!line || !/[\p{L}\p{N}]/u.test(line)) { blanks++; continue; }
        const afterBlanks = blanks;
        blanks = 0;
        if (/^notes?\s*:/i.test(line) && part) { part.notes.push(line.replace(/^notes?\s*:\s*/i, "")); continue; }

        // An army or scheme name on its own line: the very first line, a known faction, or after
        // a gap of 2+ blank lines. It mustn't read as a step ("Prime", "Leadbelcher").
        const bare = !/[:;=,()]/.test(line) && !/\s[-–]\s/.test(line);
        if (bare && line.split(/\s+/).length <= 5 && (factions.has(matchKey(line)) || (afterBlanks >= 2 && (!scheme || scheme.parts.length)) || !schemes.length)) {
          // v18: a known faction is checked before paints ("Dark Angels" isn't Dark Angels Green).
          if (factions.has(matchKey(line))) { startScheme(line); continue; }
        }
        // v21.1: "Ultramarines armour": the faction is the scheme, "Armour" the part (it used
        // to read as the paint Ultramarines Blue). Checked wherever a bare line could start
        // a section, not only at the top.
        const lead = bare && line.split(/\s+/).length <= 6 ? factionLead(line, factions) : null;
        if (lead) {
          if (!scheme || !sameText(scheme.name, lead.faction)) startScheme(lead.faction);
          if (lead.part) startPart(lead.part, false);
          continue;
        }
        if (bare && line.split(/\s+/).length <= 5 && (factions.has(matchKey(line)) || (afterBlanks >= 2 && (!scheme || scheme.parts.length)) || !schemes.length)) {
          const asStep = readMention(line, {});
          const stepLike = asStep.technique || (asStep.paint && (asStep.paint.status === "sure" || asStep.paint.status === "material"));
          if (!stepLike) { startScheme(line); continue; }
        }

        const heading = readHeading(line);
        if (heading && heading.kind === "scheme") { startScheme(heading.name); continue; }
        if (heading) {
          startPart(heading.name, heading.kind === "sub");
          if (heading.rest) addSteps(heading.rest);
          continue;
        }
        // "Part - steps" or "Paint - a note".
        const dash = line.match(/^(.+?)\s+[-–—]\s+(.+)$/);
        if (dash) {
          const left = readMention(dash[1], { brand: ctx.brand });
          const leftIsPaint = left.technique || (left.paint && ["sure", "material"].includes(left.paint.status));
          const right = readMention(splitOutside(dash[2], [","])[0], { brand: ctx.brand });
          const rightIsPaint = right.paint && right.paint.status !== "new";
          if (!leftIsPaint && rightIsPaint) { startPart(dash[1].trim(), false); addSteps(dash[2]); continue; }
          if (leftIsPaint) {
            const before = part ? part.steps.length : 0;
            addSteps(dash[1]);
            const added = part.steps[part.steps.length - 1];
            if (added && part.steps.length > before) added.note = [added.note, dash[2].trim()].filter(Boolean).join("; ");
            continue;
          }
        }
        addSteps(line);
      }
      // Group labels with nothing under them ("Misc:", "Slapchops:") are dropped.
      for (const s of schemes) s.parts = s.parts.filter(p => p.steps.length || p.notes.length);
      return { schemes: schemes.filter(s => s.parts.length) };
    }

    // Every paint mention that needs your answer, grouped by what was typed ("CM" once, not 3 times).
    function unsureMentions(parsed) {
      const groups = new Map();
      for (const s of parsed.schemes) for (const p of s.parts) for (const step of p.steps) for (const m of step.paints) {
        if (m.status !== "unsure") continue;
        const key = matchKey(m.typed);
        if (!groups.has(key)) groups.set(key, { key, typed: m.typed, suggestions: m.suggestions.slice(), count: 0, choice: null });
        const g = groups.get(key);
        g.count++;
        for (const sug of m.suggestions) if (!g.suggestions.some(x => sameText(x.name, sug.name))) g.suggestions.push(sug);
      }
      return [...groups.values()];
    }

    // ================= v16: COPY AS TEXT =================
    // Writes a recipe (or a whole scheme) in the same format Paste recipes reads, so it can be
    // shared (e.g. on Reddit) and pasted straight back in.
    function stepToText(step) {
      const paints = step.paints.map(sp => ({ sp, p: paintById(sp.paint) })).filter(x => x.p);
      const nameOf = (p) => {
        const known = KNOWN_PAINTS.find(k => sameText(k.name, p.name));
        return p.brand && !(known && sameText(known.brand, p.brand)) && !isMaterial(p) ? `${p.brand} ${p.name}` : p.name;
      };
      let body;
      if (paints.length > 1) {
        let ratio = step.ratio;
        if (!ratio && paints.every(x => x.sp.mix !== null) && !isEvenSplit(paints.map(x => ({ mix: x.sp.mix })))) ratio = paints.map(x => x.sp.mix).join(":");
        // v18: always write the ratio, so a mix pastes back as one step ("A + B" reads as two).
        if (!ratio) ratio = paints.map(() => 1).join(":");
        body = `${ratio} ${paints.map(x => nameOf(x.p)).join(":")}`;
      } else body = paints.length ? nameOf(paints[0].p) : "";
      const extras = [];
      if (step.coats > 1) extras.push(`${step.coats} coats`);
      if (step.note) extras.push(step.note.replace(/[()]/g, ""));
      if (step.optional) extras.push("optional");
      return [step.technique, body].filter(Boolean).join(" ") + extras.map(e => ` (${e})`).join("");
    }
    function recipeToText(recipe, heading) {
      const lines = [`${heading || recipe.name}:`];
      for (const step of recipe.steps) lines.push(stepToText(step));
      if (recipe.notes && recipe.notes.trim()) lines.push(`Notes: ${recipe.notes.trim().replace(/\n+/g, " ")}`);
      return lines.join("\n");
    }
    function schemeToText(scheme) {
      return [`Scheme: ${scheme.name}`, ...schemeRecipes(scheme).map(r => recipeToText(r))].join("\n\n");
    }

    let book = loadRecipes();

    function loadRecipes() {
      let saved = null;
      try {
        saved = localStorage.getItem(RECIPES_KEY);
        return cleanRecipeBook(saved ? JSON.parse(saved) : null);
      } catch (error) {
        // Damaged data: tuck it away under another name so it's never lost.
        try { if (saved) localStorage.setItem(RECIPES_KEY + "-unreadable", saved); } catch (ignored) {}
        return cleanRecipeBook(null);
      }
    }

    // Two bits of text the same, ignoring capitals, spaces at the ends and curly quotes?
    function sameText(a, b) {
      return plainQuotes(String(a || "")).trim().toLowerCase() === plainQuotes(String(b || "")).trim().toLowerCase();
    }

    // A mix %: a whole number from 0 to 100, or null for "not given".
    function cleanMix(value) {
      if (value === null || value === undefined || value === "") return null;
      const n = Math.round(Number(value));
      return Number.isFinite(n) ? Math.min(100, Math.max(0, n)) : null;
    }

    // Checks and repairs a recipe book, like cleanModels does for units.
    // "...p" and "...r" keep any extra facts a later version adds, so nothing is lost.
    function cleanRecipeBook(raw) {
      const src = raw && typeof raw === "object" ? raw : {};
      const textList = (values, fallback) => {
        const out = [];
        if (Array.isArray(values)) for (const v of values) {
          const t = String(v ?? "").trim();
          if (t && !out.some(o => sameText(o, t))) out.push(t);
        }
        return out.length ? out : fallback.slice();
      };
      const isColour = (c) => typeof c === "string" && /^#[0-9a-f]{6}$/i.test(c);

      const paints = [];
      const paintIds = new Set();
      const tidied = new Set();   // v18c: paints whose brand was typed twice ("CitadelCitadel")
      for (const p of Array.isArray(src.paints) ? src.paints : []) {
        const name = p && String(p.name || "").trim();
        if (!name || !Number.isInteger(p.id) || paintIds.has(p.id)) continue;
        paintIds.add(p.id);
        // v17: a status (blank = not set), and the "spare in stock" tick, only for running low.
        const rawBrand = String(p.brand || "").trim();
        const paint = { ...p, brand: tidyBrand(rawBrand), name,
                        colour: isColour(p.colour) ? p.colour.toLowerCase() : DEFAULT_PAINT_COLOUR };
        if (paint.brand !== rawBrand) tidied.add(paint.id);
        if (!PAINT_STATUS_KEYS.includes(paint.status)) delete paint.status;
        if (p.example !== true) delete paint.example;   // v24: only a real true counts
        if (paint.status !== "low" || paint.spare !== true) delete paint.spare;
        // v17.1: quantity, only for paints you have and only above one.
        const haveNow = paint.status === "owned" || paint.status === "low" || (!paint.status && paint.owned === true);
        if (!haveNow || !Number.isInteger(paint.qty) || paint.qty <= 1) delete paint.qty;
        else paint.qty = Math.min(99, paint.qty);
        paints.push(paint);
      }

      // v18c: once a doubled brand is tidied, the paint may now be the same as another one
      // (e.g. "CitadelCitadel Macragge Blue" and "Citadel Macragge Blue"). The two become one:
      // recipes use the one you already had, and its status or colour is filled in if it had none.
      const mergedInto = new Map();   // old paint id → the paint it joined
      for (const paint of paints.filter(p => tidied.has(p.id))) {
        const same = (x) => x !== paint && !mergedInto.has(x.id) && sameText(x.name, paint.name) && sameText(x.brand, paint.brand);
        const twin = paints.find(x => same(x) && !tidied.has(x.id)) || paints.find(same);
        if (!twin) continue;
        if (!paintStatus(twin) && paintStatus(paint)) {
          for (const k of ["status", "owned", "spare", "qty"]) if (k in paint) twin[k] = paint[k];
        }
        if (twin.colour === DEFAULT_PAINT_COLOUR && paint.colour !== DEFAULT_PAINT_COLOUR) twin.colour = paint.colour;
        if (paint.type && !twin.type) twin.type = paint.type;
        mergedInto.set(paint.id, twin.id);
      }
      const keptPaints = paints.filter(p => !mergedInto.has(p.id));

      const recipes = [];
      const recipeIds = new Set();
      for (const r of Array.isArray(src.recipes) ? src.recipes : []) {
        if (!r || typeof r.name !== "string" || !r.name.trim()) continue;
        const id = Number.isInteger(r.id) && !recipeIds.has(r.id) ? r.id : null;
        if (id !== null) recipeIds.add(id);
        const steps = (Array.isArray(r.steps) ? r.steps : []).filter(s => s && typeof s === "object").map(s => ({
          ...s,
          technique: String(s.technique || "").trim(),
          coats: cleanCount(s.coats),
          paints: (Array.isArray(s.paints) ? s.paints : [])
            .filter(sp => sp && paintIds.has(sp.paint))
            .map(sp => ({ paint: mergedInto.get(sp.paint) ?? sp.paint, mix: cleanMix(sp.mix) })),
          ratio: cleanRatio(s.ratio),               // v15
          note: String(s.note || "").trim(),        // v15
          optional: s.optional === true,            // v15
        }));
        const cleanRecipe = { ...r, id, name: r.name.trim(), part: String(r.part || "").trim(),
                              notes: String(r.notes || ""), steps };
        if (r.example !== true) delete cleanRecipe.example;   // v24: only a real true counts
        recipes.push(cleanRecipe);
      }
      let next = Math.max(0, ...recipeIds) + 1;
      for (const r of recipes) if (r.id === null) r.id = next++;

      // Painting schemes (v9): { id, name, faction, auto, recipes: [recipe ids] }.
      // A scheme is a named group of recipes for one faction. "auto" = link its recipes to
      // new units added in that faction. Recipe ids that no longer exist are dropped.
      const allRecipeIds = new Set(recipes.map(r => r.id));
      const schemes = [];
      const schemeIds = new Set();
      for (const s of Array.isArray(src.schemes) ? src.schemes : []) {
        if (!s || typeof s.name !== "string" || !s.name.trim()) continue;
        const id = Number.isInteger(s.id) && !schemeIds.has(s.id) ? s.id : null;
        if (id !== null) schemeIds.add(id);
        const ids = Array.isArray(s.recipes) ? [...new Set(s.recipes.filter(r => allRecipeIds.has(r)))] : [];
        schemes.push({ ...s, id, name: s.name.trim(), faction: String(s.faction || "").trim(),
                       auto: s.auto !== false, recipes: ids });
      }
      let nextScheme = Math.max(0, ...schemeIds) + 1;
      for (const s of schemes) if (s.id === null) s.id = nextScheme++;

      const parts = textList(src.parts, DEFAULT_PARTS);
      const techniques = textList(src.techniques, DEFAULT_TECHNIQUES);
      // v15: a recipe book saved before v15 gets "Whole model" and the new techniques, once.
      // Remove them afterwards and they stay removed ("v15" marks the book as done).
      if (!src.v15) {
        if (!parts.some(p => sameText(p, WHOLE_MODEL))) parts.unshift(WHOLE_MODEL);
        for (const t of V15_TECHNIQUES) if (!techniques.some(x => sameText(x, t))) techniques.push(t);
      }
      // "Whole model" always comes first.
      const whole = parts.findIndex(p => sameText(p, WHOLE_MODEL));
      if (whole > 0) parts.unshift(...parts.splice(whole, 1));
      // v16: shorthand you've confirmed ("cm" = Contrast Medium). Empty for older books.
      const shorthand = {};
      if (src.shorthand && typeof src.shorthand === "object" && !Array.isArray(src.shorthand)) {
        for (const [k, v] of Object.entries(src.shorthand)) {
          if (k && v && typeof v.name === "string" && v.name.trim()) shorthand[k] = { brand: tidyBrand(v.brand), name: v.name.trim() };
        }
      }
      return { parts, techniques, paints: keptPaints, recipes, schemes, shorthand, v15: true };
    }

    // localStorage only holds text, so we turn the list into text (JSON) to save it,
    // and back into a list to load it. "try / catch" means: try this, and if it goes
    // wrong, do the catch part instead of crashing.
    function load() {
      let saved = null;
      try {
        saved = localStorage.getItem(STORAGE_KEY);
        if (!saved) return cleanModels(EXAMPLES);   // first ever visit
        const parsed = JSON.parse(saved);
        if (Array.isArray(parsed)) return cleanModels(parsed);
        throw new Error("Saved data isn't a list");
      } catch (error) {
        // Damaged data: tuck the original away under another name so it's never lost.
        try { if (saved) localStorage.setItem(STORAGE_KEY + "-unreadable", saved); } catch (ignored) {}
        return cleanModels(EXAMPLES);
      }
    }

    // Checks every unit and repairs anything odd before the app uses it. Used for saved
    // data and backups, since both come from outside and could be damaged or out of date.
    function cleanModels(list) {
      const cleaned = [];
      const usedIds = new Set();
      for (const m of list) {
        if (!m || typeof m.name !== "string" || !m.name.trim()) continue;
        const stage = Number(m.stage);
        const model = {
          ...m,
          name: m.name.trim(),
          hobby: String(m.hobby || ""),
          faction: String(m.faction || ""),
          stage: Number.isInteger(stage) && stage >= 0 && stage < STAGES.length ? stage : 0,
          count: cleanCount(m.count),
          repaint: m.repaint === true,
        };
        if (m.example !== true) delete model.example;   // v21: only a real true counts
        // Track-each-model: one valid stage per model, otherwise switch it off.
        const validStage = (x) => Number.isInteger(x) && x >= 0 && x < STAGES.length;
        if (m.each === true && Array.isArray(m.stages) && model.count <= MAX_EACH) {
          const list = m.stages.map(Number).slice(0, model.count);
          while (list.length < model.count) list.push(model.stage);
          model.stages = list.map(x => validStage(x) ? x : 0);
          model.stage = lowest(model.stages);
        } else {
          delete model.each;
          delete model.stages;
        }
        // Dates: keep only ones that look like "2026-10-07".
        const isDate = (d) => typeof d === "string" && /^\d{4}-\d{2}-\d{2}$/.test(d);
        if (!isDate(model.added)) delete model.added;
        model.log = Array.isArray(m.log)
          ? m.log.filter(e => Array.isArray(e) && isDate(e[0]) && validStage(e[1]) &&
                              (e[2] === undefined || (Number.isInteger(e[2]) && e[2] >= 0)))
          : [];
        // Linked recipes: a list of whole numbers (recipe ids), no repeats.
        const recipeIds = Array.isArray(m.recipes) ? [...new Set(m.recipes.filter(Number.isInteger))] : [];
        if (recipeIds.length) model.recipes = recipeIds; else delete model.recipes;
        // Photos (v10, several per unit since v11): notes pointing at pictures in the photo
        // store. Old-style photos (model.photo, a picture written as text) are kept until
        // they've been moved. Repeats of the same id are dropped.
        const seenPhotos = new Set();
        const photos = Array.isArray(m.photos) ? m.photos
          .filter(p => p && typeof p.id === "string" && p.id && !seenPhotos.has(p.id) && seenPhotos.add(p.id))
          .map(p => {
            const note = { ...p };
            if (!isDate(note.date)) delete note.date;
            if (!validStage(note.stage)) delete note.stage;
            // "model": which model of a tracked-each-model unit the photo shows (0 = Model 1).
            if (!(Number.isInteger(note.model) && note.model >= 0 && note.model < model.count)) delete note.model;
            return note;
          }) : [];
        if (photos.length) model.photos = photos; else delete model.photos;
        // The cover photo (shown on the unit's card) must be one of its photos.
        if (!photos.some(p => p.id === m.coverPhoto)) delete model.coverPhoto;
        if (typeof m.photo !== "string" || !m.photo.startsWith("data:image")) delete model.photo;
        if (Number.isInteger(model.id) && !usedIds.has(model.id)) usedIds.add(model.id);
        else model.id = null; // given a fresh one below
        cleaned.push(model);
      }
      let next = Math.max(0, ...usedIds) + 1;
      for (const model of cleaned) if (model.id === null) model.id = next++;
      return cleaned;
    }

    // saveAll() saves units, recipes and settings TOGETHER (all or nothing, see
    // writeTogether at the top). It reports back: true if it worked (or storage is
    // switched off), false if storage is FULL, in which case the red banner shows.
    function saveAll() {
      const ok = writeTogether([
        [STORAGE_KEY, JSON.stringify(models)],
        [RECIPES_KEY, JSON.stringify(book)],
        [SETTINGS_KEY, JSON.stringify(settings)],
      ]);
      if (ok) { if (saveFailing && !holdSaves) hideSaveProblem(); }
      else showSaveProblem();
      return ok;
    }
    // The older name, still used all over the app.
    function save() { return saveAll(); }

    // For BIG changes (new stages, restoring a backup, recovering earlier data): make the
    // change, then save. If the save fails, put everything back exactly as it was, so
    // what's on screen always matches what's saved. Returns true if the change was kept.
    function changeAndSave(change) {
      const before = { models: JSON.stringify(models), book: JSON.stringify(book), settings: JSON.stringify(settings) };
      const wasFailing = saveFailing;
      change();
      if (saveAll()) return true;
      // Put back how things were. Nothing unsaved is left, so the banner can go again
      // (unless saving was already failing before this change).
      if (!wasFailing) hideSaveProblem();
      models = JSON.parse(before.models);
      book = JSON.parse(before.book);
      settings = JSON.parse(before.settings);
      settings.factionColours = cleanFactionColours(settings.factionColours);
      STAGES = settings.stages.map(String);
      applyPalette(settings.palette);
      return false;
    }
    const FULL_MESSAGE = "Storage on this device is full, so that change couldn't be saved and nothing has changed. " +
      "Please save a backup, then free some space (for example delete photos or units you no longer need).";
    // v18.3: the right "not saved" message: newer data from a newer version, or full storage.
    function fullMessage() { return dataTooNew ? TOO_NEW_MESSAGE : FULL_MESSAGE; }

    // ================= SMALL HELPERS =================

    // A unit's proper name with its copy number: "Intercessors 2".
    function fullName(model) { return model.copy ? `${model.name} ${model.copy}` : model.name; }
    // The big name on a card: the nickname if there is one.
    function displayName(model) { return model.nickname || fullName(model); }

    // Models in a unit: a whole number, at least 1.
    // v14: at most MAX_MODELS (999, set at the top). A huge number like 150,000 used to
    // freeze the app and blank the Units list on every open.
    function cleanCount(value) {
      const n = parseInt(value, 10);
      return Number.isInteger(n) && n >= 1 ? Math.min(n, MAX_MODELS) : 1;
    }
    // Adds up MODELS (not units): a 10-model squad counts as 10.
    function modelCount(list) { return list.reduce((total, m) => total + (m.count || 1), 0); }

    // A fresh ID, one higher than the highest in use.
    function nextId() { return models.reduce((highest, m) => Math.max(highest, m.id), 0) + 1; }

    // Blank removed, duplicates removed (that's what a Set does), sorted A-Z.
    function uniqueSorted(values) {
      return [...new Set(values.filter(Boolean))].sort((a, b) => a.localeCompare(b));
    }

    // The ONE place units get added (used by the form and CSV import).
    // Same name + game + faction as an existing unit? Then they're numbered.
    // ================= DATES AND HISTORY =================
    // Today's date in YOUR time zone, written like "2026-10-07".
    function todayISO() {
      const d = new Date();
      return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}-${String(d.getDate()).padStart(2, "0")}`;
    }

    // Every unit keeps a small diary of stage changes, used later for the progress graph.
    //   [date, stage]         = the whole unit moved to that stage
    //   [date, stage, n]      = just model number n (0 = first) moved
    // Several changes on the same day for the same model keep only the last one.
    function logStage(model, stage, index) {
      if (!Array.isArray(model.log)) model.log = [];
      const date = todayISO();
      const entry = index === undefined ? [date, stage] : [date, stage, index];
      const last = model.log[model.log.length - 1];
      if (last && last[0] === date && last[2] === entry[2]) model.log[model.log.length - 1] = entry;
      else model.log.push(entry);
    }

    // ================= TRACKING EACH MODEL =================
    // A unit is either painted as a BATCH (one stage for the whole unit, the default) or
    // has "each" switched on, where model.stages holds one stage per model.
    // model.stage is then the LOWEST of them, so sorting and the CSV still make sense.

    // The stage of every model in a unit, as a list.
    function stagesOf(m) {
      return m.each ? m.stages : new Array(m.count || 1).fill(m.stage);
    }
    function lowest(list) { return Math.min(...list); }

    // Put a unit (or one model, if index is given) at a stage, and note it in the diary.
    function setStage(model, stage, index) {
      if (model.each && index !== undefined) {
        model.stages[index] = stage;
        model.stage = lowest(model.stages);
        logStage(model, stage, index);
      } else {
        model.stage = stage;
        if (model.each) model.stages = model.stages.map(() => stage);
        logStage(model, stage);
      }
    }

    // Switch "track each model" on or off.
    function setEach(model, on) {
      if (on && model.count > MAX_EACH) {
        notify(`Tracking each model works for units of up to ${MAX_EACH} models.`);
        render();
        return;
      }
      if (on) {
        model.each = true;
        model.stages = new Array(model.count || 1).fill(model.stage);
        render();
        return;
      }
      const spread = new Set(model.stages).size > 1;
      const goBack = () => {
        delete model.each;
        delete model.stages;
        if (spread) logStage(model, model.stage);
        render();
      };
      // v21.7: asks in the app's own box, then carries on when you answer. "No" just redraws.
      if (spread) {
        askYesNo(`Go back to painting ${displayName(model)} as a batch? ` +
          `All its models will be set to ${STAGES[model.stage]}, the stage of the furthest-behind model.`,
          goBack, { onNo: render });
      } else {
        goBack();
      }
    }

    // When the number of models changes, add new models at the first stage, or drop the last ones.
    function resizeEach(model) {
      if (!model.each) return;
      // Too many models to track one by one (v14): go back to painting it as a batch.
      if (model.count > MAX_EACH) { delete model.each; delete model.stages; return; }
      const n = model.count || 1;
      while (model.stages.length < n) model.stages.push(0);
      model.stages.length = n;
      model.stage = lowest(model.stages);
    }

    function addModel(fields) {
      // Capitals and curly/straight apostrophes don't matter ("T’au" = "T'au").
      const same = (a, b) => plainQuotes(a || "").toLowerCase() === plainQuotes(b || "").toLowerCase();
      const matches = models.filter(m =>
        same(m.name, fields.name) && same(m.hobby, fields.hobby) && same(m.faction, fields.faction));

      const model = { id: nextId(), stage: 0, count: 1, repaint: false, ...fields };
      model.added = todayISO();
      model.log = [[model.added, model.stage]];

      if (matches.length > 0) {
        let highest = Math.max(0, ...matches.map(m => m.copy || 0));
        for (const m of matches) if (!m.copy) m.copy = ++highest;
        model.copy = highest + 1;
        // Match existing spelling, so "40k" and "40K" don't become two games.
        model.name = matches[0].name;
        model.hobby = matches[0].hobby;
        model.faction = matches[0].faction;
      }
      // Painting schemes: a new unit in a faction with an automatic scheme gets that
      // scheme's recipes linked straight away.
      for (const scheme of schemesFor(model.faction)) {
        if (scheme.auto) for (const id of scheme.recipes) linkRecipe(model, id);
      }
      models.push(model);
      return model;
    }

    // ================= TABS =================

    const views = {
      dashboard: document.getElementById("view-dashboard"),
      units: document.getElementById("view-units"),
      recipes: document.getElementById("view-recipes"),
      settings: document.getElementById("view-settings"),
      updates: document.getElementById("view-updates"),
      help: document.getElementById("view-help"),
    };
    const tabButtons = document.querySelectorAll(".tabs button");

    // v21.9: Settings, Help and Updates are ONE main tab (Settings) with a Settings / Help /
    // Updates switch (#more-seg) at the top. The page names are still "settings", "help" and
    // "updates", so a saved settings.tab of "help" or "updates" (from before v21.9) opens the
    // right page, and nothing about how it's saved has changed.
    const MORE_PAGES = ["settings", "help", "updates"];
    const moreSeg = document.getElementById("more-seg");
    moreSeg.querySelectorAll("button").forEach(b => b.addEventListener("click", () => showTab(b.dataset.page)));

    function showTab(name) {
      if (!views[name]) name = "dashboard";
      if (name !== "units" && selectMode) closeSelect();   // v21.1: leaving Units ends select mode
      for (const [key, view] of Object.entries(views)) view.classList.toggle("hidden", key !== name);
      const mainTab = MORE_PAGES.includes(name) ? "settings" : name;   // the bottom-bar tab to light up
      tabButtons.forEach(b => {
        if (b.dataset.tab === mainTab) b.setAttribute("aria-current", "page");
        else b.removeAttribute("aria-current");
      });
      moreSeg.classList.toggle("hidden", !MORE_PAGES.includes(name));
      moreSeg.querySelectorAll("button").forEach(b => b.setAttribute("aria-selected", String(b.dataset.page === name)));
      settings.tab = name;
      saveSettings();
      if (name === "settings") renderSettings();
      if (name === "dashboard") renderHistory();   // the graph needs to be on screen to measure its width
      window.scrollTo(0, 0);
    }
    tabButtons.forEach(b => b.addEventListener("click", () => {
      // Tapping Recipes while already on it goes back to the list (unless you're mid-edit).
      if (b.dataset.tab === "recipes" && settings.tab === "recipes" && !recipeDraft) {
        openRecipeId = null;
        renderRecipes();
      }
      showTab(b.dataset.tab);
    }));

    // ================= FILTERS =================

    // What the Units list is showing. An empty stages Set means "every stage".
    const filters = { hobby: "", faction: "", stages: new Set(), repaint: false };

    // v21.1: SELECT MODE on the Units tab. selectMode = are the tick boxes showing;
    // ticked = the ids of the ticked units. Neither is saved: it's only for this visit.
    let selectMode = false;
    const ticked = new Set();
    // v21.5: the unit just added (outlined for a moment; see showNewUnit()). Not saved.
    let justAddedId = null;
    let justAddedTimer = null;

    function clearFilters() {
      filters.hobby = "";
      filters.faction = "";
      filters.stages = new Set();
      filters.repaint = false;
    }

    // Jump from the dashboard to the Units tab with some filters already set.
    function goToUnits(newFilters) {
      clearFilters();
      Object.assign(filters, newFilters);
      openIds.clear();
      render();
      showTab("units");
    }

    function inScope(m) {
      return (!filters.hobby || m.hobby === filters.hobby) && (!filters.faction || m.faction === filters.faction);
    }
    function isVisible(m) {
      return inScope(m) &&
             (filters.stages.size === 0 || stagesOf(m).some(st => filters.stages.has(st))) &&
             (!filters.repaint || m.repaint);
    }

    // Do two lists of stage numbers contain exactly the same stages?
    function sameStages(set, list) {
      return set.size === list.length && list.every(i => set.has(i));
    }

    // ================= DRAWING EVERYTHING =================

    // render() redraws the screen from the data. Change the data first, then render().
    // It saves first, so every change is saved from this one place.
    // Saves, then redraws everything. v18c-3: reports back true if the save worked.
    function render() {
      const ok = save();
      renderDashboard();
      renderUnits();
      renderRecipes();
      return ok;
    }

    // ================= v18c-3: HONEST "SAVED" MESSAGES =================
    // commit() is render() plus the message: it saves, redraws, and only THEN says
    // "Saved …" / "Added …" if the save really worked. If storage is full it says so
    // plainly instead, with a Save backup button. The change stays on screen and the red
    // banner stays up, so Retry on the banner can still save it once there's room.
    // (Before v18c-3 every message said "Saved" whatever happened.)
    const NOT_SAVED_MESSAGE = "Not saved: storage on this device is full. It's on screen for now, " +
      "but will be lost when the app closes. Save a backup, then free some space.";
    function showNotSaved(message) {
      if (dataTooNew) { showToast(TOO_NEW_MESSAGE, () => location.reload(), "Reload", 12); return; }
      showToast(message || NOT_SAVED_MESSAGE, () => document.getElementById("export-button").click(), "Save backup", 12);
    }
    function commit(message, undo, buttonLabel, seconds) {
      const ok = render();
      if (ok) showToast(message, undo, buttonLabel, seconds);
      else showNotSaved();
      return ok;
    }

    // ================= FACTION COLOURS =================
    // Each faction can have a colour you pick. It's shown as a tint on unit cards, a bar on
    // the dashboard's faction cards and a mark on the faction filter. The STAGE colour
    // stripe on unit cards stays as it is: stage = left stripe, faction = tint and dot.

    // Give an element its faction colour, plus a see-through "tint" version for the
    // faded background. Dark colours are lightened for the tint only (keeping their hue),
    // otherwise a navy or black faction would vanish against the dark cards.
    // (Worked out here rather than with the newer CSS color-mix(), so older phones show it.)
    // v20: in light mode a very pale faction colour (e.g. white) would vanish on the white
    // cards, so its bar is shown a little deeper. The colour you picked doesn't change.
    function setFactionStyle(element, colour) {
      element.style.setProperty("--faction-colour", isLight() ? deepenForLight(colour, 1.8) : colour);
      element.style.setProperty("--faction-tint", factionTint(colour));
    }
    function factionTint(hex) {
      let [r, g, b] = [1, 3, 5].map(i => parseInt(hex.slice(i, i + 2), 16) / 255);
      // Convert to hue / saturation / lightness, raise the lightness, convert back.
      const max = Math.max(r, g, b), min = Math.min(r, g, b);
      let h = 0, sat = 0, light = (max + min) / 2;
      if (max !== min) {
        const d = max - min;
        sat = light > 0.5 ? d / (2 - max - min) : d / (max + min);
        h = max === r ? (g - b) / d + (g < b ? 6 : 0) : max === g ? (b - r) / d + 2 : (r - g) / d + 4;
        h /= 6;
      }
      // v20: in light mode the tint sits on white, so it's kept as it is (just see-through).
      if (!isLight()) light = Math.max(light, 0.5);
      const hue = (t) => {
        t = (t + 1) % 1;
        const q = light < 0.5 ? light * (1 + sat) : light + sat - light * sat, p = 2 * light - q;
        return t < 1 / 6 ? p + (q - p) * 6 * t : t < 1 / 2 ? q : t < 2 / 3 ? p + (q - p) * (2 / 3 - t) * 6 : p;
      };
      [r, g, b] = sat ? [hue(h + 1 / 3), hue(h), hue(h - 1 / 3)] : [light, light, light];
      return `rgba(${Math.round(r * 255)}, ${Math.round(g * 255)}, ${Math.round(b * 255)}, 0.28)`;
    }

    // The faction's colour, or "" if it hasn't got one.
    function factionColour(faction) {
      // hasOwnProperty: only a colour someone actually set counts (v14, see copyColours).
      return (faction && Object.prototype.hasOwnProperty.call(settings.factionColours, faction) && settings.factionColours[faction]) || "";
    }

    // Set (or, with no colour, remove) a faction's colour, then redraw.
    function setFactionColour(faction, colour) {
      if (!faction) return;
      if (colour) settings.factionColours[faction] = colour.toLowerCase();
      else delete settings.factionColours[faction];
      saveSettings();
      render();
    }

    // ----- Usual faction colours (v12) -----
    // The colour most people know each faction by, used when there are no recipes to go
    // on. These are rough, hand-picked shades, not official paint colours. Names are
    // matched loosely: capitals, accents and apostrophes don't matter, and a longer name
    // that CONTAINS one of these (e.g. "Space Marines - Ultramarines") still matches.
    // Several spellings can share one colour: "eldar|aeldari|craftworlds".
    const USUAL_FACTION_COLOURS = {
      // Warhammer 40,000: Imperium
      "ultramarines|space marines|adeptus astartes": "#1f4fa3",
      "dark angels": "#1f4d2b",
      "blood angels": "#9b1c1c",
      "space wolves": "#6b7f99",
      "imperial fists": "#e0b12a",
      "salamanders": "#2e7d32",
      "raven guard": "#262626",
      "iron hands": "#3a3a3a",
      "white scars": "#e8e6dc",
      "black templars": "#1a1a1a",
      "deathwatch": "#202020",
      "grey knights": "#9ca3af",
      "adeptus custodes|custodes": "#c9a227",
      "adepta sororitas|sisters of battle": "#8b1e2d",
      "astra militarum|imperial guard|cadians": "#6b7a3a",
      "adeptus mechanicus|admech|mechanicus": "#9b2a1f",
      "imperial knights": "#1f3f7a",
      "agents of the imperium|inquisition": "#4b3b2a",
      // Warhammer 40,000: Chaos
      "chaos space marines|black legion|heretic astartes": "#1f1f1f",
      "world eaters": "#8b1a1a",
      "death guard": "#8a9a5b",
      "thousand sons": "#2563a8",
      "emperor's children": "#b04a9c",
      "night lords": "#1f2a5a",
      "word bearers": "#7a1f1f",
      "alpha legion": "#2a6f73",
      "iron warriors": "#8a8d8f",
      "chaos daemons|daemons": "#8b1a1a",
      "chaos knights": "#3d2b2b",
      // Warhammer 40,000: Xenos
      "orks|orkz": "#3a7d2c",
      "necrons": "#5aa469",
      "tyranids|nids": "#6d28d9",
      "genestealer cults|genestealer cult": "#6a3d9a",
      "t'au|tau|t'au empire|tau empire": "#c9a46b",
      "aeldari|eldar|craftworlds|asuryani": "#1e8a7a",
      "ulthwe": "#1a1a1a",
      "biel-tan|biel tan": "#2e7d32",
      "iyanden": "#e0b12a",
      "saim-hann|saim hann": "#a11d1d",
      "alaitoc": "#1f4fa3",
      "drukhari|dark eldar": "#2d5f5a",
      "harlequins": "#b02a6a",
      "leagues of votann|votann|squats": "#b5651d",
      // Age of Sigmar: Order
      "stormcast eternals|stormcast": "#c9a227",
      "cities of sigmar": "#2b4c7e",
      "daughters of khaine": "#8b1a2b",
      "fyreslayers": "#d97706",
      "idoneth deepkin|idoneth": "#2a6f9e",
      "kharadron overlords|kharadron": "#8a6d3b",
      "lumineth realm-lords|lumineth": "#e8e6dc",
      "seraphon": "#2a9d8f",
      "sylvaneth": "#6b8e23",
      // Age of Sigmar: Death
      "nighthaunt": "#4fd1c5",
      "ossiarch bonereapers|ossiarch": "#e5dcc5",
      "flesh-eater courts|flesh eater courts": "#8b1a1a",
      "soulblight gravelords|soulblight": "#3b2d4f",
      // Age of Sigmar: Destruction
      "orruk warclans|ironjawz|kruleboyz|bonesplitterz": "#3a7d2c",
      "gloomspite gitz|gloomspite": "#4b5d2a",
      "ogor mawtribes|ogors": "#a0522d",
      "sons of behemat": "#b07a4a",
      // Age of Sigmar: Chaos
      "skaven": "#7a5c3a",
      "slaves to darkness": "#3a3a3a",
      "blades of khorne|khorne": "#8b1a1a",
      "disciples of tzeentch|tzeentch": "#2563a8",
      "maggotkin of nurgle|nurgle": "#8a9a5b",
      "hedonites of slaanesh|slaanesh": "#b04a9c",
      "beasts of chaos": "#5c4033",
    };
    // Make a name easy to compare: lower case, no accents, straight apostrophes,
    // other punctuation turned into spaces.
    function plainName(text) {
      return plainQuotes(String(text || "")).normalize("NFD").replace(/[\u0300-\u036f]/g, "")
        .toLowerCase().replace(/[^a-z0-9']+/g, " ").trim();
    }
    // Umbrella names, only used when no more specific name matches, so
    // "Space Marines - Blood Angels" is red (Blood Angels), not Space Marines blue.
    const UMBRELLA_FACTIONS = new Set(["space marines", "adeptus astartes", "chaos space marines", "heretic astartes",
      "aeldari", "eldar", "craftworlds", "asuryani", "daemons", "chaos daemons"]);
    // Every known spelling: specific names first, then umbrella names, longest first in each.
    const USUAL_COLOUR_LIST = Object.entries(USUAL_FACTION_COLOURS)
      .flatMap(([names, colour]) => names.split("|").map(name => [plainName(name), colour]))
      .sort((a, b) => (UMBRELLA_FACTIONS.has(a[0]) - UMBRELLA_FACTIONS.has(b[0])) || b[0].length - a[0].length);
    // The usual colour for a faction name, or "" if it isn't one we know.
    function usualFactionColour(faction) {
      const name = plainName(faction);
      if (!name) return "";
      const padded = ` ${name} `;
      for (const [known, colour] of USUAL_COLOUR_LIST) {
        if (name === known || padded.includes(` ${known} `)) return colour;   // whole words only
      }
      return "";
    }

    // The best suggestion for a faction: from its recipes if possible, otherwise its
    // usual colour. Returns { colour, from: "recipes" | "usual" } or null.
    function suggestionFor(faction) {
      const fromRecipes = recipeColourFor(faction);
      if (fromRecipes) return { colour: fromRecipes, from: "recipes" };
      const usual = usualFactionColour(faction);
      return usual ? { colour: usual, from: "usual" } : null;
    }
    function suggestFactionColour(faction) {
      const s = suggestionFor(faction);
      return s ? s.colour : "";
    }

    // Suggest a colour from the recipes linked to that faction's units. A faction's
    // "main" colour is usually its armour, so recipes whose part is Armour are preferred.
    // From each recipe we take its FIRST colour (normally the base coat), and count it
    // once per unit using the recipe. The most-used colour wins. Unset paints (#808080)
    // are skipped. Returns "" if there's nothing to go on.
    function recipeColourFor(faction) {
      const units = models.filter(m => m.faction === faction);
      const uses = new Map();   // recipe -> how many of this faction's units use it
      for (const unit of units) for (const recipe of recipesOf(unit)) uses.set(recipe, (uses.get(recipe) || 0) + 1);
      let recipes = [...uses.keys()];
      const armour = recipes.filter(r => /armou?r/i.test(r.part || ""));
      if (armour.length) recipes = armour;
      const votes = new Map();  // colour -> votes
      for (const recipe of recipes) {
        const first = recipeColours(recipe).find(c => c !== "#808080");
        if (first) votes.set(first, (votes.get(first) || 0) + uses.get(recipe));
      }
      let best = "", bestVotes = 0;
      for (const [colour, count] of votes) if (count > bestVotes) { best = colour; bestVotes = count; }
      return best;
    }

    // After names change, keep "Intercessors 1 / 2" numbering tidy: a unit alone in its
    // group loses its number; a group of several gets unique numbers (existing ones kept).
    function renumberCopies() {
      const key = (m) => [m.name, m.hobby, m.faction].map(v => plainQuotes(v || "").toLowerCase()).join("\u0000");
      const groups = new Map();
      for (const m of models) {
        if (!groups.has(key(m))) groups.set(key(m), []);
        groups.get(key(m)).push(m);
      }
      for (const group of groups.values()) {
        if (group.length === 1) { delete group[0].copy; continue; }
        const taken = new Set();
        const needNumber = [];
        for (const m of group) {
          if (m.copy && !taken.has(m.copy)) taken.add(m.copy); else needNumber.push(m);
        }
        let next = 1;
        for (const m of needNumber) {
          while (taken.has(next)) next++;
          m.copy = next;
          taken.add(next);
        }
      }
    }

    // Rename a faction on EVERY unit in it, carrying its colour across. If you rename it
    // to a faction that already has a colour, that colour is kept (the two are merged).
    function renameFaction(oldName, newName) {
      newName = (newName || "").trim();
      if (!oldName || !newName || newName === oldName) return;
      // Remember how things were, for Undo.
      const before = models.map(m => [m, m.faction, m.copy]);
      const coloursBefore = copyColours(settings.factionColours);
      const movedSchemes = book.schemes.filter(s => s.faction === oldName);

      for (const m of models) if (m.faction === oldName) m.faction = newName;
      for (const s of movedSchemes) s.faction = newName;   // its painting schemes follow
      if (settings.factionColours[oldName] && !settings.factionColours[newName]) {
        settings.factionColours[newName] = settings.factionColours[oldName];
      }
      delete settings.factionColours[oldName];
      renumberCopies();
      if (filters.faction === oldName) filters.faction = newName;
      saveSettings();
      render();
      renderFactionColours();
      showToast(`Renamed to ${newName}`, () => {
        for (const [m, faction, copy] of before) {
          m.faction = faction;
          if (copy) m.copy = copy; else delete m.copy;
        }
        settings.factionColours = coloursBefore;
        for (const s of movedSchemes) s.faction = oldName;
        if (filters.faction === newName) filters.faction = oldName;
        saveSettings();
        render();
        renderFactionColours();
      });
    }

    // The Settings card listing every faction with its colour.
    const factionColourList = document.getElementById("faction-colour-list");
    function renderFactionColours() {
      factionColourList.innerHTML = "";
      const factions = uniqueSorted(models.map(m => m.faction));
      document.getElementById("faction-colour-hint").textContent = factions.length
        ? "Tap a colour circle to pick a faction's colour. Suggest offers one: from the recipes linked to that faction's units if it can, otherwise the colour the faction is usually painted."
        : "Add some units with a faction first, then give each faction a colour here.";
      // One tap for every faction that hasn't got a colour yet.
      const waiting = factions.filter(f => !factionColour(f) && suggestFactionColour(f));
      const useAll = document.getElementById("use-suggested-colours");
      useAll.classList.toggle("hidden", waiting.length === 0);
      useAll.textContent = `Use suggested colours (${waiting.length})`;
      useAll.onclick = () => {
        const before = copyColours(settings.factionColours);
        for (const f of waiting) settings.factionColours[f] = suggestFactionColour(f);
        saveSettings();
        render();
        renderFactionColours();
        showToast(`${plural(waiting.length, "faction")} coloured`, () => {
          settings.factionColours = before;
          saveSettings();
          render();
          renderFactionColours();
        });
      };
      for (const faction of factions) {
        const colour = factionColour(faction);
        const row = document.createElement("li");
        row.className = "faction-colour-row";

        const picker = document.createElement("input");
        picker.type = "color";
        picker.value = colour || "#808080";
        picker.classList.toggle("unset", !colour);
        picker.setAttribute("aria-label", `Colour for ${faction}`);
        // "input" fires while you drag round the colour picker, so the app changes live.
        picker.addEventListener("input", () => {
          picker.classList.remove("unset");
          setFactionColour(faction, picker.value);
          status.textContent = `${plural(units, "unit")} · ${picker.value.toUpperCase()}`;
        });
        picker.addEventListener("change", renderFactionColours);   // updates the buttons once you've chosen

        const text = document.createElement("div");
        text.className = "faction-colour-text";
        const name = document.createElement("strong");
        name.textContent = faction;
        const status = document.createElement("small");
        const units = models.filter(m => m.faction === faction).length;
        status.textContent = `${plural(units, "unit")} · ${colour ? colour.toUpperCase() : "no colour yet"}`;
        text.append(name, status);

        const buttons = document.createElement("div");
        buttons.className = "faction-colour-buttons";
        const suggested = suggestionFor(faction);
        const suggestion = suggested ? suggested.colour : "";
        if (suggestion && suggestion !== colour) {
          const suggest = document.createElement("button");
          suggest.className = "plain-button";
          suggest.append(makeSwatch(suggestion), suggested.from === "recipes" ? "Suggest (from recipes)" : "Suggest");
          suggest.setAttribute("aria-label", `Use suggested colour ${suggestion} for ${faction}`);
          suggest.addEventListener("click", () => {
            const old = colour;
            setFactionColour(faction, suggestion);
            renderFactionColours();
            showToast(suggested.from === "recipes" ? `${faction} colour set from its recipes` : `${faction} set to its usual colour`,
              () => { setFactionColour(faction, old); renderFactionColours(); });
          });
          buttons.appendChild(suggest);
        }
        const rename = document.createElement("button");
        rename.className = "plain-button";
        rename.textContent = "Rename";
        rename.setAttribute("aria-label", `Rename ${faction}`);
        rename.addEventListener("click", () => {
          askText(`Rename "${faction}" on all ${plural(units, "unit")} to:`, faction, (answer) => {
            if (answer !== null) renameFaction(faction, answer);
          });
        });
        buttons.appendChild(rename);
        if (colour) {
          const clear = document.createElement("button");
          clear.className = "plain-button";
          clear.textContent = "Clear";
          clear.setAttribute("aria-label", `Remove the colour from ${faction}`);
          clear.addEventListener("click", () => {
            setFactionColour(faction, "");
            renderFactionColours();
            showToast(`${faction} colour removed`, () => { setFactionColour(faction, colour); renderFactionColours(); });
          });
          buttons.appendChild(clear);
        }
        row.append(picker, text, buttons);
        factionColourList.appendChild(row);
      }
    }

    // ----- Charts -----

    // Draws a doughnut chart as SVG (a picture made of shapes, written as code).
    // Each stage is a slice of a circle's outline. The trick: a dashed line around the
    // circle, where each "dash" is exactly as long as that stage's share.
    const SVG_NS = "http://www.w3.org/2000/svg";
    function donutChart(counts, size, thickness, mainText, subText, label) {
      const svg = document.createElementNS(SVG_NS, "svg");
      svg.setAttribute("viewBox", `0 0 ${size} ${size}`);
      svg.setAttribute("width", size);
      svg.setAttribute("height", size);
      svg.setAttribute("role", "img");
      svg.setAttribute("aria-label", label);

      const centre = size / 2;
      const radius = (size - thickness) / 2;
      const circumference = 2 * Math.PI * radius;
      const total = counts.reduce((a, b) => a + b, 0);

      const ring = (colour, dash, offset) => {
        const c = document.createElementNS(SVG_NS, "circle");
        c.setAttribute("cx", centre);
        c.setAttribute("cy", centre);
        c.setAttribute("r", radius);
        c.setAttribute("fill", "none");
        c.setAttribute("stroke", colour);
        c.setAttribute("stroke-width", thickness);
        if (dash) {
          c.setAttribute("stroke-dasharray", dash);
          c.setAttribute("stroke-dashoffset", offset);
          // Start at 12 o'clock instead of 3 o'clock.
          c.setAttribute("transform", `rotate(-90 ${centre} ${centre})`);
        }
        svg.appendChild(c);
      };

      ring("var(--border)"); // the empty background ring
      const slices = counts.filter(c => c > 0).length;
      const gap = slices > 1 ? 2 : 0; // a thin gap between slices
      let travelled = 0;
      counts.forEach((count, index) => {
        if (!count) return;
        const length = count / total * circumference;
        ring(`var(--stage-${index})`, `${Math.max(length - gap, 0.5)} ${circumference}`, -travelled);
        travelled += length;
      });

      const text = (content, y, sizePx, colour, weight) => {
        const t = document.createElementNS(SVG_NS, "text");
        t.setAttribute("x", centre);
        t.setAttribute("y", y);
        t.setAttribute("text-anchor", "middle");
        t.setAttribute("fill", colour);
        t.setAttribute("font-size", sizePx);
        t.setAttribute("font-weight", weight);
        t.textContent = content;
        svg.appendChild(t);
      };
      text(mainText, centre + (subText ? 2 : 6), size * 0.17, "var(--text)", 700);
      if (subText) text(subText, centre + size * 0.15, size * 0.09, "var(--muted)", 400);
      return svg;
    }

    // ----- Dashboard -----

    const donePercent = document.getElementById("done-percent");
    const doneSummary = document.getElementById("done-summary");
    const todoButton = document.getElementById("todo-button");
    const doneButton = document.getElementById("done-button");
    const repaintLink = document.getElementById("repaint-link");
    const overallChart = document.getElementById("overall-chart");
    const stageLegend = document.getElementById("stage-legend");
    const factionGrid = document.getElementById("faction-grid");

    // Counts MODELS (not units) at each stage. Units tracked model-by-model count each model
    // at its own stage.
    function stageCounts(list) {
      const counts = STAGES.map(() => 0);
      for (const m of list) {
        if (m.each) for (const st of m.stages) counts[st]++;
        else counts[m.stage] += m.count || 1;
      }
      return counts;
    }
    function doneCount(list) {
      return stageCounts(list).reduce((total, c, i) => total + (isDone(i) ? c : 0), 0);
    }

    function renderDashboard() {
      const total = modelCount(models);
      const done = doneCount(models);
      const todo = total - done;
      const percent = total ? Math.round(done / total * 100) : 0;

      donePercent.textContent = total ? `${percent}%` : "–";
      doneSummary.textContent = total
        ? `${done} of ${total} models done · ${models.length} units`
        : "No units yet. Add some on the Units tab: one at a time, or a whole army from a pasted army list or a CSV file.";

      todoButton.innerHTML = "";
      todoButton.append(Object.assign(document.createElement("strong"), { textContent: todo }), "models to do");
      doneButton.innerHTML = "";
      doneButton.append(Object.assign(document.createElement("strong"), { textContent: done }), "models done");

      const repaints = models.filter(m => m.repaint).length;
      repaintLink.classList.toggle("hidden", repaints === 0);
      repaintLink.textContent = `↻ ${repaints} repaint project${repaints === 1 ? "" : "s"}`;

      // The big doughnut, plus a legend you can tap.
      const counts = stageCounts(models);
      overallChart.innerHTML = "";
      overallChart.appendChild(donutChart(counts, 170, 26, `${percent}%`, "done",
        counts.map((c, i) => `${STAGES[i]}: ${c}`).join(", ")));

      stageLegend.innerHTML = "";
      counts.forEach((count, index) => {
        const item = document.createElement("li");
        const button = document.createElement("button");
        const dot = document.createElement("span");
        dot.className = "dot";
        dot.style.setProperty("--dot", `var(--stage-${index})`);
        const num = document.createElement("span");
        num.className = "num";
        num.textContent = count;
        button.append(dot, STAGES[index], num);
        button.addEventListener("click", () => goToUnits({ stages: new Set([index]) }));
        item.appendChild(button);
        stageLegend.appendChild(item);
      });

      // One small doughnut per faction, like pie charts in a spreadsheet.
      factionGrid.innerHTML = "";
      const factions = uniqueSorted(models.map(m => m.faction));
      if (models.some(m => !m.faction)) factions.push(""); // units with no faction
      if (factions.length === 0) {
        factionGrid.innerHTML = '<p class="hint">Factions appear here once you add units.</p>';
      }
      for (const faction of factions) {
        const group = models.filter(m => m.faction === faction);
        const groupTotal = modelCount(group);
        const groupDone = doneCount(group);
        const pct = groupTotal ? Math.round(groupDone / groupTotal * 100) : 0;
        const button = document.createElement("button");
        button.className = "faction-button";
        const name = document.createElement("span");
        name.className = "faction-name";
        name.textContent = faction || "No faction";
        // Its colour, if it has one: a bar across the top and a dot by the name.
        const colour = factionColour(faction);
        if (colour) {
          button.classList.add("has-faction");
          setFactionStyle(button, colour);
          name.prepend(makeSwatch(colour));
        }
        const small = document.createElement("small");
        small.textContent = `${groupDone} of ${groupTotal} done`;
        button.append(
          donutChart(stageCounts(group), 92, 14, `${pct}%`, "", `${faction || "No faction"}: ${pct}% done`),
          name, small);
        button.addEventListener("click", () => goToUnits({ faction }));
        factionGrid.appendChild(button);
      }
      renderHistory();
    }

    // ----- Progress over time (the line graph) -----
    // Every unit keeps a diary of stage changes (see logStage). To find how many models
    // were painted on any past day, we replay each unit's diary up to that day.

    const HISTORY_RANGES = { "30": "1 month", "90": "3 months", "365": "1 year", "all": "All" };
    if (!HISTORY_RANGES[settings.historyRange]) settings.historyRange = "all";
    const DAY_MS = 86400000;
    // Dates as day numbers (days since 1970), so they're easy to compare and space out.
    function dayNumber(iso) {
      const [y, m, d] = iso.split("-").map(Number);
      return Date.UTC(y, m - 1, d) / DAY_MS;
    }
    function dayLabel(day, withYear) {
      return new Date(day * DAY_MS).toLocaleDateString("en-GB",
        withYear ? { month: "short", year: "2-digit", timeZone: "UTC" } : { day: "numeric", month: "short", timeZone: "UTC" });
    }

    // How many of a unit's models were Done at the end of a given day.
    function doneOnDay(unit, day) {
      const st = unit.start.slice();
      for (const e of unit.m.log) {
        if (dayNumber(e[0]) > day) continue;
        if (e[2] === undefined) st.fill(e[1]);
        else if (e[2] < st.length) st[e[2]] = e[1];
      }
      return st.filter(isDone).length;
    }

    function historyData() {
      const today = dayNumber(todayISO());
      let first = today;
      for (const m of models) {
        if (m.added) first = Math.min(first, dayNumber(m.added));
        for (const e of m.log) first = Math.min(first, dayNumber(e[0]));
      }
      const days = new Set([today]);
      const units = models.map(m => {
        // Units from before v4 have no "added" date: they count from the start of the graph.
        const from = m.added ? dayNumber(m.added) : first;
        // Where the diary starts: its first entry, or (with no diary) where the unit is now.
        const start = m.log.length ? new Array(m.count || 1).fill(m.log[0][1]) : stagesOf(m).slice();
        days.add(from);
        for (const e of m.log) days.add(dayNumber(e[0]));
        return { m, from, start, count: m.count || 1 };
      });
      const valuesOn = (day) => {
        let added = 0, done = 0;
        for (const u of units) {
          if (u.from > day) continue;
          added += u.count;
          done += doneOnDay(u, day);
        }
        return { day, added, done };
      };
      return { today, first, valuesOn, undated: models.filter(m => !m.added).length,
               changeDays: [...days].sort((a, b) => a - b) };
    }

    // A tidy gap between grid lines: 1, 2, 5, 10, 20, 50...
    function niceStep(max) {
      const raw = Math.max(max / 4, 1);
      const power = Math.pow(10, Math.floor(Math.log10(raw)));
      return [1, 2, 5, 10].map(s => s * power).find(s => s >= raw);
    }

    function svgEl(tag, attributes, parent) {
      const el = document.createElementNS(SVG_NS, tag);
      for (const [k, v] of Object.entries(attributes)) el.setAttribute(k, v);
      if (parent) parent.appendChild(el);
      return el;
    }

    function renderHistory() {
      const box = document.getElementById("history-chart");
      const note = document.getElementById("history-note");
      const tableBox = document.getElementById("history-table-box");
      const legend = document.getElementById("history-legend");
      const rangeChips = document.getElementById("history-range");
      if (views.dashboard.classList.contains("hidden")) return;   // drawn when the tab opens

      const data = historyData();
      const ready = models.length > 0 && data.first < data.today;
      rangeChips.innerHTML = "";
      for (const [key, label] of Object.entries(HISTORY_RANGES)) {
        rangeChips.appendChild(makeChip(label, settings.historyRange === key, () => {
          settings.historyRange = key;
          saveSettings();
          renderHistory();
        }));
      }
      for (const el of [rangeChips, legend, tableBox]) el.classList.toggle("hidden", !ready);
      box.innerHTML = "";
      if (!ready) {
        note.textContent = models.length
          ? "Your graph starts today. Come back after a few days of adding and painting to watch it grow."
          : "Add some units and your progress will show here over time.";
        return;
      }
      note.textContent = data.undated
        ? `${plural(data.undated, "unit")} added before dates were recorded (v4) ${data.undated === 1 ? "counts" : "count"} from the start of the graph.`
        : "";

      // The points: the start of the chosen range, then every day something changed.
      const span = settings.historyRange === "all" ? Infinity : Number(settings.historyRange);
      const startDay = Math.max(data.first, data.today - span);
      const points = [startDay, ...data.changeDays.filter(d => d > startDay)].map(data.valuesOn);
      const valueAt = (day) => { let p = points[0]; for (const q of points) if (q.day <= day) p = q; return p; };

      // Size: as wide as the card, a little shorter on phones.
      const width = Math.max(260, box.clientWidth);
      const height = width < 500 ? 210 : 270;
      const pad = { left: 38, right: 44, top: 12, bottom: 28 };
      const x0 = startDay, x1 = data.today;
      const step = niceStep(Math.max(...points.map(p => p.added), 1));
      const top = Math.max(step, Math.ceil(Math.max(...points.map(p => p.added)) / step) * step);
      const X = (day) => pad.left + (day - x0) / (x1 - x0) * (width - pad.left - pad.right);
      const Y = (v) => height - pad.bottom - v / top * (height - pad.top - pad.bottom);

      const svg = svgEl("svg", { width, height, viewBox: `0 0 ${width} ${height}`, role: "img",
        "aria-label": `Models added and painted over time. Now ${points[points.length - 1].added} added, ${points[points.length - 1].done} painted.` });

      // Grid lines and numbers up the left (quiet, so the lines stand out).
      for (let v = 0; v <= top; v += step) {
        svgEl("line", { x1: pad.left, x2: width - pad.right, y1: Y(v), y2: Y(v), stroke: "var(--border)", "stroke-width": 1 }, svg);
        const t = svgEl("text", { x: pad.left - 8, y: Y(v) + 4, "text-anchor": "end", fill: "var(--muted)", "font-size": 11 }, svg);
        t.textContent = v;
      }
      // Dates along the bottom.
      const ticks = width < 500 ? 3 : 5;
      const withYear = x1 - x0 > 300;
      for (let i = 0; i < ticks; i++) {
        const day = Math.round(x0 + (x1 - x0) * i / (ticks - 1));
        const t = svgEl("text", { x: X(day), y: height - 8, fill: "var(--muted)", "font-size": 11,
          "text-anchor": i === 0 ? "start" : i === ticks - 1 ? "end" : "middle" }, svg);
        t.textContent = i === ticks - 1 ? "Today" : dayLabel(day, withYear);
      }

      // The two lines, drawn as steps: a total stays flat until the day it changes.
      const stepPath = (key) => {
        let d = `M ${X(points[0].day)} ${Y(points[0][key])}`;
        for (const p of points.slice(1)) d += ` H ${X(p.day)} V ${Y(p[key])}`;
        return d + ` H ${X(x1)}`;
      };
      const series = [["added", "var(--series-added)"], ["done", "var(--series-painted)"]];
      for (const [key, colour] of series) {
        svgEl("path", { d: stepPath(key), fill: "none", stroke: colour, "stroke-width": 2,
                        "stroke-linejoin": "round", "stroke-linecap": "round" }, svg);
      }
      // Today's numbers at the end of each line, nudged apart if they'd overlap.
      const last = points[points.length - 1];
      let yAdded = Y(last.added) + 4, yDone = Y(last.done) + 4;
      if (yDone - yAdded < 14) { const mid = (yAdded + yDone) / 2; yAdded = mid - 7; yDone = mid + 7; }
      for (const [value, y] of [[last.added, yAdded], [last.done, yDone]]) {
        const t = svgEl("text", { x: X(x1) + 6, y, fill: "var(--text)", "font-size": 12, "font-weight": 600 }, svg);
        t.textContent = value;
      }

      // Touch or hover: a line follows your finger, with that day's numbers.
      const cross = svgEl("line", { y1: pad.top, y2: height - pad.bottom, stroke: "var(--muted)",
                                    "stroke-width": 1, "stroke-dasharray": "3 3", visibility: "hidden" }, svg);
      const dots = series.map(([, colour]) => svgEl("circle", { r: 4.5, fill: colour, stroke: "var(--card)",
                                                                "stroke-width": 2, visibility: "hidden" }, svg));
      const hit = svgEl("rect", { x: pad.left, y: 0, width: width - pad.left - pad.right, height, fill: "transparent" }, svg);
      const tip = document.createElement("div");
      tip.className = "chart-tip hidden";
      const show = (event) => {
        const rect = svg.getBoundingClientRect();
        const px = Math.min(Math.max(event.clientX - rect.left, pad.left), width - pad.right);
        const day = Math.round(x0 + (px - pad.left) / (width - pad.left - pad.right) * (x1 - x0));
        const p = valueAt(day);
        const x = X(day);
        cross.setAttribute("x1", x);
        cross.setAttribute("x2", x);
        dots[0].setAttribute("cx", x); dots[0].setAttribute("cy", Y(p.added));
        dots[1].setAttribute("cx", x); dots[1].setAttribute("cy", Y(p.done));
        for (const el of [cross, ...dots]) el.setAttribute("visibility", "visible");
        const pct = p.added ? Math.round(p.done / p.added * 100) : 0;
        tip.innerHTML = `<strong></strong>` +
          `<div class="legend-key"><i style="--key: var(--series-added);"></i>Added<b>${p.added}</b></div>` +
          `<div class="legend-key"><i style="--key: var(--series-painted);"></i>Painted<b>${p.done} (${pct}%)</b></div>`;
        tip.querySelector("strong").textContent = day === x1 ? "Today" : dayLabel(day, false) + (withYear ? " " + new Date(day * DAY_MS).getUTCFullYear() : "");
        tip.classList.remove("hidden");
        // Keep the box beside the line, flipping to the left near the right-hand edge.
        const tipWidth = tip.offsetWidth;
        const left = x + 12 + tipWidth > width ? x - 12 - tipWidth : x + 12;
        tip.style.left = `${Math.max(0, Math.min(left, width - tipWidth))}px`;   // never off the edge
      };
      const hide = () => {
        for (const el of [cross, ...dots]) el.setAttribute("visibility", "hidden");
        tip.classList.add("hidden");
      };
      hit.addEventListener("pointermove", show);
      hit.addEventListener("pointerdown", show);
      hit.addEventListener("pointerleave", hide);
      box.append(svg, tip);

      // The same numbers as a table, newest first.
      const rows = points.slice().reverse().map(p =>
        `<tr><td>${p.day === x1 ? "Today" : dayLabel(p.day, false) + " " + new Date(p.day * DAY_MS).getUTCFullYear()}</td>` +
        `<td>${p.added}</td><td>${p.done}</td><td>${p.added ? Math.round(p.done / p.added * 100) : 0}%</td></tr>`).join("");
      document.getElementById("history-table").innerHTML =
        `<table><thead><tr><th>Date</th><th>Added</th><th>Painted</th><th>Done</th></tr></thead><tbody>${rows}</tbody></table>`;
    }

    // Redraw the graph when the window changes size (e.g. turning a phone sideways).
    let resizeTimer;
    window.addEventListener("resize", () => { clearTimeout(resizeTimer); resizeTimer = setTimeout(renderHistory, 150); });

    todoButton.addEventListener("click", () => goToUnits({ stages: new Set(todoStages()) }));
    doneButton.addEventListener("click", () => goToUnits({ stages: new Set(doneStages()) }));
    repaintLink.addEventListener("click", () => goToUnits({ repaint: true }));
    // "Faction colours" on the dashboard: open Settings at the faction colours card.
    document.getElementById("faction-colours-link").addEventListener("click", () => {
      showTab("settings");
      document.getElementById("faction-colours-card").scrollIntoView({ block: "start" });
    });

    // ----- Units -----

    const list = document.getElementById("unit-list");
    const hobbyFilter = document.getElementById("hobby-filter");
    const factionFilter = document.getElementById("faction-filter");
    const groupChips = document.getElementById("group-chips");
    const stageChips = document.getElementById("stage-chips");
    const filterNote = document.getElementById("filter-note");
    const clearFiltersButton = document.getElementById("clear-filters");
    const selectButton = document.getElementById("toggle-select");      // v21.1
    const selectBar = document.getElementById("select-bar");
    const selectCount = document.getElementById("select-count");
    const selectAllButton = document.getElementById("select-all");
    const selectMoveSlot = document.getElementById("select-move-slot");

    // Which units have their details panel open. Not saved.
    const openIds = new Set();
    // v23: units whose folded "Edit details" section is open. Not saved: only for this visit.
    // Every change redraws the panel, so without this the section would shut after each edit.
    const editOpenIds = new Set();

    function fillSelect(select, label, values, current) {
      select.innerHTML = "";
      select.add(new Option(`All ${label}`, ""));
      for (const value of values) select.add(new Option(value, value));
      select.value = current;
    }

    function makeChip(text, pressed, onClick, colourVar) {
      const chip = document.createElement("button");
      chip.className = "chip";
      chip.textContent = text;
      chip.setAttribute("aria-pressed", pressed);
      if (colourVar) chip.style.setProperty("--chip-colour", colourVar);
      chip.addEventListener("click", onClick);
      return chip;
    }

    function renderUnits() {
      // Dropdowns: the faction list only shows factions from the chosen game.
      const games = uniqueSorted(models.map(m => m.hobby));
      if (!games.includes(filters.hobby)) filters.hobby = "";
      const factions = uniqueSorted(models.filter(m => !filters.hobby || m.hobby === filters.hobby).map(m => m.faction));
      if (!factions.includes(filters.faction)) filters.faction = "";
      fillSelect(hobbyFilter, "games", games, filters.hobby);
      fillSelect(factionFilter, "factions", factions, filters.faction);
      // The chosen faction's colour shows as a stripe on the menu, like the stage chips.
      factionFilter.style.setProperty("--chip-colour", factionColour(filters.faction) || "var(--border)");

      // Group chips: one tap for every To do (or Done) stage at once.
      const todo = todoStages();
      const done = doneStages();
      groupChips.innerHTML = "";
      groupChips.append(
        makeChip("To do", sameStages(filters.stages, todo), () => {
          filters.stages = sameStages(filters.stages, todo) ? new Set() : new Set(todo);
          render();
        }),
        makeChip("Done", sameStages(filters.stages, done), () => {
          filters.stages = sameStages(filters.stages, done) ? new Set() : new Set(done);
          render();
        }),
        makeChip("↻ Repaint", filters.repaint, () => {
          filters.repaint = !filters.repaint;
          render();
        }),
      );

      // Stage chips: tap several to combine them.
      stageChips.innerHTML = "";
      STAGES.forEach((stageName, index) => {
        stageChips.appendChild(makeChip(stageName, filters.stages.has(index), () => {
          if (filters.stages.has(index)) filters.stages.delete(index);
          else filters.stages.add(index);
          render();
        }, `var(--stage-${index})`));
      });

      const visible = models.filter(isVisible);
      const activeCount = (filters.hobby ? 1 : 0) + (filters.faction ? 1 : 0) +
                          (filters.stages.size > 0 ? 1 : 0) + (filters.repaint ? 1 : 0);
      const anyFilter = activeCount > 0;
      clearFiltersButton.classList.toggle("hidden", !anyFilter);
      // The summary line always shows what you're looking at, even with Filters folded away.
      const scope = [filters.faction || filters.hobby].filter(Boolean).join("");
      filterNote.textContent = anyFilter
        ? `${scope ? scope + ": " : ""}${visible.length} of ${models.length} units (${modelCount(visible)} models)`
        : `${models.length} units, ${modelCount(models)} models`;
      toggleFilters.textContent = `Filters${anyFilter ? " (" + activeCount + ")" : ""} ${filtersOpen ? "▴" : "▾"}`;

      // Suggestions for the game/faction boxes in the add form and the edit panel.
      const fillList = (id, values) => {
        const dl = document.getElementById(id);
        dl.innerHTML = "";
        for (const v of values) { const o = document.createElement("option"); o.value = v; dl.appendChild(o); }
      };
      fillList("game-options", games);
      fillList("faction-options", uniqueSorted(models.map(m => m.faction)));
      fillStartStage();
      renderExamplesCards();
      renderFeedbackCard();   // v25
      fillDraftCard("unit", true);   // v26: a kept unfinished unit

      // v21.1: only units you can see can stay ticked (a filter change unticks the rest,
      // so you never move something that's off screen). No units at all: no Select.
      if (models.length === 0 && selectMode) selectMode = false;
      if (!selectMode) ticked.clear();
      const shownIds = new Set(visible.map(m => m.id));
      for (const id of [...ticked]) if (!shownIds.has(id)) ticked.delete(id);
      selectButton.classList.toggle("hidden", models.length === 0);
      refreshSelectBar(visible);

      list.innerHTML = "";
      if (models.length === 0) {
        // v19: a brand-new collection gets the import buttons right here.
        list.innerHTML = '<li class="empty" id="units-empty">No units yet. Press <strong>+ Add unit</strong> to add one, ' +
          'or bring in a whole army at once:<div class="button-grid">' +
          '<button type="button" class="plain-button" id="empty-wh">Paste army list</button>' +
          '<button type="button" class="plain-button" id="empty-csv">Import CSV</button></div></li>';
        document.getElementById("empty-wh").addEventListener("click", startUnitsPaste);
        document.getElementById("empty-csv").addEventListener("click", startUnitsCsv);
        return;
      }
      if (visible.length === 0) {
        list.innerHTML = '<li class="empty">No units match these filters.</li>';
        return;
      }
      for (const model of visible) list.appendChild(buildCard(model));
    }

    function buildCard(model) {
      const item = document.createElement("li");
      item.className = "unit";
      item.dataset.id = model.id;   // so we can scroll to it from a recipe
      if (model.id === justAddedId) item.classList.add("just-added");   // v21.5
      item.style.setProperty("--stage-colour", `var(--stage-${model.stage})`);
      const isOpen = openIds.has(model.id) && !selectMode;

      // v21.1: in select mode each card starts with a tick box.
      if (selectMode) {
        const tickWrap = document.createElement("label");
        tickWrap.className = "unit-tick";
        const tick = document.createElement("input");
        tick.type = "checkbox";
        tick.checked = ticked.has(model.id);
        tick.setAttribute("aria-label", `Tick ${displayName(model)}`);
        tick.addEventListener("change", () => toggleTick(model.id));
        tickWrap.appendChild(tick);
        item.appendChild(tickWrap);
        item.classList.toggle("ticked", tick.checked);
      }

      if (hasPhoto(model)) {
        // The small picture: an old-style photo, or the thumbnail from the photo store
        // (a blank box for a moment while it loads).
        const thumb = document.createElement("img");
        thumb.className = "thumb";
        const src = model.photo || thumbUrls.get(mainPhoto(model).id);
        if (src) thumb.src = src;
        thumb.alt = "";
        item.appendChild(thumb);
      }

      // The text area. Tapping it now OPENS THE DETAILS (it no longer changes the stage).
      const info = document.createElement("div");
      info.className = "info";
      info.setAttribute("role", "button");
      info.tabIndex = 0;
      if (selectMode) {
        info.setAttribute("aria-pressed", ticked.has(model.id));
        info.setAttribute("aria-label", `${displayName(model)}, ${STAGES[model.stage]}. ${ticked.has(model.id) ? "Ticked" : "Tap to tick"}.`);
      } else {
        info.setAttribute("aria-expanded", isOpen);
        info.setAttribute("aria-label", `${displayName(model)}, ${STAGES[model.stage]}. Show details.`);
      }

      const name = document.createElement("div");
      name.className = "name";
      name.textContent = displayName(model); // textContent shows typed text safely, exactly as typed

      const details = document.createElement("div");
      details.className = "details";
      const realName = model.nickname ? fullName(model) : "";
      const size = model.count > 1 ? `${model.count} models` : "";
      details.textContent = [realName, size, model.hobby].filter(Boolean).join(" · ");
      if (model.faction) {
        if (details.textContent) details.append(" · ");
        // The faction's colour: a dot before its name, and a soft tint across the card.
        // (The left stripe stays the STAGE colour.)
        const colour = factionColour(model.faction);
        if (colour) {
          const dot = makeSwatch(colour);
          dot.classList.add("faction-dot");
          details.append(dot);
          item.classList.add("has-faction");
          setFactionStyle(item, colour);
        }
        details.append(model.faction);
      }

      const stage = document.createElement("div");
      stage.className = "stage";
      // Batch: just the stage. Each model: how many are at each stage, furthest first.
      let stageText = STAGES[model.stage];
      if (model.each && new Set(model.stages).size > 1) {
        const counts = stageCounts([model]);
        stageText = counts.map((c, i) => [c, i]).filter(([c]) => c > 0).reverse()
          .map(([c, i]) => `${c} ${STAGES[i]}`).join(" · ");
      }
      stage.textContent = stageText + (model.repaint ? "  ·  ↻ repaint" : "");

      // Pips: solid up to the furthest-behind model, faint up to the furthest-ahead one.
      const furthest = Math.max(...stagesOf(model));
      const pips = document.createElement("div");
      pips.className = "pips";
      for (let i = 0; i < STAGES.length; i++) {
        const pip = document.createElement("div");
        pip.className = i <= model.stage ? "pip filled" : i <= furthest ? "pip part" : "pip";
        pips.appendChild(pip);
      }

      info.append(name, details, stage, pips);
      const toggle = () => {
        if (selectMode) { toggleTick(model.id); return; }   // v21.1: in select mode a tap ticks
        // v23: closing a unit also puts its "Edit details" section away again.
        if (openIds.has(model.id)) { openIds.delete(model.id); editOpenIds.delete(model.id); } else openIds.add(model.id);
        render();
      };
      info.addEventListener("click", toggle);
      info.addEventListener("keydown", (event) => {
        if (event.key === "Enter" || event.key === " ") { event.preventDefault(); toggle(); }
      });

      // The big ▲ button: the ONLY way to move up a stage from the list.
      const up = document.createElement("button");
      up.className = "up-button";
      const atTop = model.stage >= STAGES.length - 1;
      up.textContent = atTop ? "✓" : "▲";
      up.disabled = atTop;
      up.setAttribute("aria-label", atTop
        ? `${displayName(model)} is ${STAGES[model.stage]}`
        : model.each
          ? `Move one model of ${displayName(model)} up to ${STAGES[model.stage + 1]}`
          : `Move ${displayName(model)} up to ${STAGES[model.stage + 1]}`);
      up.addEventListener("click", () => changeStage(model.id, +1));

      // v21.1: while selecting, the ▲ and the recipe buttons step aside so a tap can't
      // change a stage or open something by accident.
      if (selectMode) { item.append(info); return item; }
      item.append(info, up);

      // Its recipes, as buttons that open them.
      const linked = recipesOf(model);
      if (linked.length) {
        const row = document.createElement("div");
        row.className = "recipe-links";
        for (const recipe of linked) row.appendChild(recipeChip(recipe, () => openRecipe(recipe.id)));
        item.appendChild(row);
      }

      if (isOpen) item.appendChild(buildPanel(model));
      return item;
    }

    // ----- The details panel -----

    function buildPanel(model) {
      const panel = document.createElement("div");
      panel.className = "panel";

      // Name, game and faction can be changed here. Saved when you leave each box.
      const makeEdit = (labelText, field, listId) => {
        const label = document.createElement("label");
        label.textContent = labelText;
        const box = document.createElement("input");
        box.value = model[field] || "";
        if (listId) box.setAttribute("list", listId);
        box.addEventListener("change", () => editUnit(model, field, box.value));
        label.appendChild(box);
        return label;
      };
      const nameEdit = makeEdit("Unit name", "name");
      const editRow = document.createElement("div");
      editRow.className = "edit-row";
      editRow.append(makeEdit("Game", "hobby", "game-options"), makeEdit("Faction", "faction", "faction-options"));

      // v21: JUMP TO STAGE. Pick the stage straight from a menu instead of tapping ▲ up
      // to 7 times. For a unit tracked model by model it moves EVERY model (each model
      // also has its own menu further down); while they're at different stages the menu
      // says "Mixed stages".
      const spread = model.each && new Set(model.stages).size > 1;
      const stageLabel = document.createElement("label");
      stageLabel.textContent = model.each ? "Move all models to stage" : "Stage";
      const stageMenu = stagePicker(spread ? null : model.stage,
        model.each ? `Move all models of ${displayName(model)} to stage` : `Stage of ${displayName(model)}`,
        (to) => jumpToStage(model.id, to), spread ? "Mixed stages" : "");
      stageMenu.classList.add("jump-stage");
      stageLabel.appendChild(stageMenu);
      // v23: PANEL ORDER. What people use most comes first: stage, (each model's stage),
      // photos, recipes, notes. The edit boxes are collected in editFields and put away in
      // one closed "Edit details" section further down (see the end of this function).
      panel.append(stageLabel);
      const editFields = [nameEdit, editRow];

      // Nickname: saves as you type ("input"), redraws when you leave the box ("change").
      const nicknameLabel = document.createElement("label");
      nicknameLabel.textContent = "Nickname (optional)";
      const nickname = document.createElement("input");
      nickname.placeholder = "e.g. The Gold Squad";
      nickname.value = model.nickname || "";
      nickname.addEventListener("input", () => { model.nickname = nickname.value.trim(); save(); });
      nickname.addEventListener("change", () => render());
      nicknameLabel.appendChild(nickname);

      // Model count and repaint flag, side by side.
      const extras = document.createElement("div");
      extras.className = "row";
      const countLabel = document.createElement("label");
      countLabel.textContent = "Models in unit";
      const countBox = document.createElement("input");
      countBox.type = "number";
      countBox.min = 1;
      countBox.max = MAX_MODELS;
      countBox.value = model.count || 1;
      countBox.addEventListener("change", () => { model.count = cleanCount(countBox.value); resizeEach(model); render(); });
      countLabel.appendChild(countBox);

      const repaintLabel = document.createElement("label");
      repaintLabel.className = "check-label";
      const repaintBox = document.createElement("input");
      repaintBox.type = "checkbox";
      repaintBox.checked = !!model.repaint;
      repaintBox.addEventListener("change", () => { model.repaint = repaintBox.checked; render(); });
      repaintLabel.append(repaintBox, "Repaint project");
      extras.append(countLabel, repaintLabel);

      // Notes: saves half a second after you stop typing, and when you leave the box.
      const noteLabel = document.createElement("label");
      noteLabel.textContent = "Paint scheme notes";
      const note = document.createElement("textarea");
      note.placeholder = "e.g. blue armour, black wash, gold trim";
      note.value = model.note || "";
      let noteTimer;
      note.addEventListener("input", () => {
        model.note = note.value;
        clearTimeout(noteTimer);
        noteTimer = setTimeout(save, 500);
      });
      note.addEventListener("blur", save);
      noteLabel.appendChild(note);

      editFields.push(nicknameLabel, extras);

      // Track each model separately (only makes sense with 2 or more models).
      if ((model.count || 1) > 1) {
        const eachLabel = document.createElement("label");
        eachLabel.className = "check-label";
        const eachBox = document.createElement("input");
        eachBox.type = "checkbox";
        eachBox.checked = !!model.each;
        eachBox.addEventListener("change", () => setEach(model, eachBox.checked));
        eachLabel.append(eachBox, "Track each model separately (for painting one at a time)");
        editFields.push(eachLabel);
      }

      if (model.each) {
        const list = document.createElement("ol");
        list.className = "each-list";
        list.setAttribute("aria-label", "Each model's stage");
        model.stages.forEach((st, i) => {
          const row = document.createElement("li");
          row.style.setProperty("--stage-colour", `var(--stage-${st})`);
          const label = document.createElement("span");
          label.className = "each-name";
          label.textContent = `Model ${i + 1}`;
          // v21.8: when this model reached its stage, in plain words, under its name.
          const since = modelSince(model, i);
          if (since) {
            const when = document.createElement("small");
            when.className = "each-since";
            when.textContent = sinceWording(since);
            when.title = `Model ${i + 1} reached ${STAGES[st]} on ${shortDate(since)}`;
            label.appendChild(when);
          }
          // v21: the stage is a menu, so one model can jump straight to any stage.
          const stageName = stagePicker(st, `Model ${i + 1} of ${displayName(model)}: stage`,
                                        (to) => jumpToStage(model.id, to, i));
          stageName.classList.add("each-stage");
          const down = document.createElement("button");
          down.className = "plain-button";
          down.textContent = "◀";
          down.disabled = st === 0;
          down.setAttribute("aria-label", `Move model ${i + 1} back a stage`);
          down.addEventListener("click", () => changeStage(model.id, -1, i));
          const upOne = document.createElement("button");
          upOne.className = "plain-button";
          upOne.textContent = "▲";
          upOne.disabled = st >= STAGES.length - 1;
          upOne.setAttribute("aria-label", `Move model ${i + 1} up a stage`);
          upOne.addEventListener("click", () => changeStage(model.id, +1, i));
          row.append(label, stageName, down, upOne);
          list.appendChild(row);
        });
        panel.appendChild(list);
      }

      // Photos come straight after the stage (v23), then recipes, then the scheme notes.
      panel.appendChild(buildGallery(model));

      // Paint recipes: linked ones (tap to open, ✕ to unlink), and a menu to link more.
      const recipeField = document.createElement("div");
      recipeField.className = "panel-field";
      recipeField.append("Paint recipes");
      const linkedRecipes = recipesOf(model);
      if (linkedRecipes.length) {
        const linkedList = document.createElement("div");
        linkedList.className = "linked-list";
        for (const recipe of linkedRecipes) {
          linkedList.appendChild(linkedChip(recipeChip(recipe, () => openRecipe(recipe.id)),
            `Unlink ${recipe.name}`, () => { unlinkRecipe(model, recipe.id); render(); }));
        }
        recipeField.appendChild(linkedList);
      }
      const recipePicker = document.createElement("select");
      recipePicker.setAttribute("aria-label", `Link a recipe to ${displayName(model)}`);
      recipePicker.add(new Option(linkedRecipes.length ? "Link another recipe…" : "Link a recipe…", ""));
      book.recipes.filter(r => !linkedRecipes.includes(r))
        .sort((a, b) => a.name.localeCompare(b.name))
        .forEach(r => recipePicker.add(new Option(r.part ? `${r.name} (${r.part})` : r.name, r.id)));
      // This faction's painting schemes that the unit doesn't fully have yet.
      for (const scheme of schemesFor(model.faction)) {
        if (scheme.recipes.some(id => recipeById(id) && !(model.recipes || []).includes(id))) {
          recipePicker.add(new Option(`Apply scheme: ${scheme.name}`, `scheme:${scheme.id}`));
        }
      }
      recipePicker.add(new Option("＋ New recipe for this unit", "new"));
      recipePicker.addEventListener("change", () => {
        if (recipePicker.value === "new") { recipePicker.value = ""; startNewRecipe(model.id); return; }
        if (recipePicker.value.startsWith("scheme:")) {
          const scheme = book.schemes.find(s => s.id === Number(recipePicker.value.slice(7)));
          recipePicker.value = "";
          if (scheme) applyScheme(scheme, [model]);
          return;
        }
        if (recipePicker.value) { linkRecipe(model, Number(recipePicker.value)); render(); }
      });
      recipeField.appendChild(recipePicker);
      panel.appendChild(recipeField);

      panel.appendChild(noteLabel);

      // v23: the edit boxes live in ONE closed section with a clear label, one tap away.
      // It's a real <details>, so the keyboard and screen readers work without extra code.
      // Whether it is open is remembered per unit (editOpenIds) so a redraw doesn't shut it.
      const editSection = document.createElement("details");
      editSection.className = "edit-details";
      const editSummary = document.createElement("summary");
      editSummary.textContent = "Edit details";
      const editHint = document.createElement("span");
      editHint.className = "edit-details-hint";
      editHint.textContent = "name, game, faction, nickname, models";
      editSummary.appendChild(editHint);
      const editBody = document.createElement("div");
      editBody.className = "edit-details-body";
      editBody.append(...editFields);
      editSection.append(editSummary, editBody);
      editSection.open = editOpenIds.has(model.id);
      editSection.addEventListener("toggle", () => {
        if (editSection.open) editOpenIds.add(model.id); else editOpenIds.delete(model.id);
      });
      panel.appendChild(editSection);

      const buttons = document.createElement("div");
      buttons.className = "panel-buttons";

      const back = document.createElement("button");
      back.className = "plain-button";
      back.textContent = "◀ Back a stage";
      back.disabled = model.stage === 0;
      back.addEventListener("click", () => changeStage(model.id, -1));
      if (!model.each) buttons.append(back);   // each model has its own ◀ above

      const del = document.createElement("button");
      del.className = "danger-button";
      del.textContent = "Delete";
      del.addEventListener("click", () => deleteModel(model.id));
      buttons.appendChild(del);

      panel.append(buttons);
      return panel;
    }

    // ----- The photo gallery and progress timeline (v11) -----
    // Inside a unit's details: every photo as a small picture in a strip you can scroll
    // sideways, oldest on the left, newest on the right. Under each one: a dot in the
    // stage's colour, the stage name and the date, so you can watch the unit go from
    // grey plastic to painted. Tap a picture to see it full size.
    function buildGallery(model) {
      const box = document.createElement("div");
      box.className = "panel-field gallery";
      const list = timeline(model);

      const head = document.createElement("div");
      head.className = "gallery-head";
      const title = document.createElement("span");
      title.textContent = list.length ? `Photos (${list.length}) · oldest → newest` : "Photos";
      head.appendChild(title);
      box.appendChild(head);

      // An old-style photo still waiting to move to the photo store (e.g. a browser with
      // no IndexedDB): shown as before, so it never goes missing.
      if (model.photo) {
        const old = document.createElement("img");
        old.className = "photo";
        old.alt = `Photo of ${displayName(model)}`;
        old.src = model.photo;
        box.appendChild(old);
      }

      if (list.length) {
        const cover = mainPhoto(model);
        const strip = document.createElement("ol");
        strip.className = "photo-strip";
        strip.setAttribute("aria-label", `Photos of ${displayName(model)}, oldest first`);
        list.forEach((p, i) => {
          const item = document.createElement("li");
          const stage = validStageIndex(p.stage) ? p.stage : null;
          item.style.setProperty("--stage-colour", stage === null ? "var(--border)" : `var(--stage-${stage})`);
          const open = document.createElement("button");
          open.className = "photo-tile";
          open.setAttribute("aria-label", `Open photo ${i + 1} of ${list.length}: ${photoCaption(model, p)}`);
          const img = document.createElement("img");
          img.alt = "";
          const src = thumbUrls.get(p.id);
          if (src) img.src = src;
          open.appendChild(img);
          if (cover && cover.id === p.id) {
            const star = document.createElement("span");
            star.className = "cover-badge";
            star.textContent = "★ Cover";
            open.appendChild(star);
          }
          open.addEventListener("click", () => openLightbox(model.id, p.id));
          const caption = document.createElement("div");
          caption.className = "photo-caption";
          const dot = document.createElement("span");
          dot.className = "dot";
          const stageName = document.createElement("span");
          stageName.className = "photo-stage";
          stageName.textContent = stage === null ? "Stage not set" : STAGES[stage];
          const when = document.createElement("small");
          when.textContent = shortDate(p.date) + (photoModel(model, p) !== null ? ` · Model ${p.model + 1}` : "");
          caption.append(dot, stageName, when);
          item.append(open, caption);
          strip.appendChild(item);
        });
        box.appendChild(strip);
        // Start scrolled to the newest photo, on the right.
        requestAnimationFrame(() => { strip.scrollLeft = strip.scrollWidth; });
      } else if (!model.photo) {
        const none = document.createElement("p");
        none.className = "hint";
        none.textContent = "No photos yet. Add one at each stage to build up a progress timeline.";
        box.appendChild(none);
      }

      // A hidden file picker. accept="image/*" means phones offer the camera or gallery.
      // "multiple" lets you pick several photos at once.
      const picker = document.createElement("input");
      picker.type = "file";
      picker.accept = "image/*";
      picker.multiple = true;
      picker.className = "hidden";

      const actions = document.createElement("div");
      actions.className = "panel-buttons";
      // For units tracked model-by-model: which model is in the photo?
      let which = null;
      if (model.each) {
        which = document.createElement("select");
        which.setAttribute("aria-label", "Which model is in the photo?");
        which.add(new Option("Which model? Whole unit", ""));
        model.stages.forEach((st, i) => which.add(new Option(`Model ${i + 1} (${STAGES[st]})`, String(i))));
        actions.appendChild(which);
      }
      picker.addEventListener("change", async () => {
        const files = [...picker.files];
        picker.value = "";
        const modelIndex = which && which.value !== "" ? Number(which.value) : undefined;
        for (const file of files) await addUnitPhoto(model, file, modelIndex);
      });
      const add = document.createElement("button");
      add.className = "plain-button";
      add.textContent = "＋ Add photo";
      add.addEventListener("click", () => picker.click());
      actions.appendChild(add);
      if (list.length >= 2) {
        const compare = document.createElement("button");
        compare.className = "plain-button";
        compare.textContent = "Before / after";
        compare.addEventListener("click", () => openCompare(model.id));
        actions.appendChild(compare);
      }
      box.append(actions, picker);
      return box;
    }
    function validStageIndex(x) { return Number.isInteger(x) && x >= 0 && x < STAGES.length; }
    // "Basecoated · 7 Oct 2026 · Model 2", for screen readers and the photo viewer.
    function photoCaption(model, p) {
      const parts = [validStageIndex(p.stage) ? STAGES[p.stage] : "Stage not set", shortDate(p.date)];
      if (photoModel(model, p) !== null) parts.push(`Model ${p.model + 1}`);
      return parts.join(" · ");
    }
    // Which model a photo shows: only meaningful while the unit is tracked model-by-model
    // and still has that many models. Otherwise null (a photo of the whole unit).
    function photoModel(model, p) {
      return model.each && Number.isInteger(p.model) && p.model < (model.count || 1) ? p.model : null;
    }

    // ----- Changing things -----

    // Change a unit's name, game or faction, keeping the "Intercessors 1 / 2" numbering tidy.
    function editUnit(model, field, value) {
      value = value.trim();
      if (field === "name" && !value) { render(); return; }  // a unit must keep a name
      if ((model[field] || "") === value) return;
      const same = (a, b) => plainQuotes(a || "").toLowerCase() === plainQuotes(b || "").toLowerCase();
      const sameGroup = (a, b) => same(a.name, b.name) && same(a.hobby, b.hobby) && same(a.faction, b.faction);

      const oldGroup = models.filter(m => m !== model && sameGroup(m, model));
      // Changing the faction of the LAST unit in a faction is really a rename, so its
      // colour goes with it (unless the new faction already has one).
      if (field === "faction") {
        const oldFaction = model.faction || "";
        const lastOne = !models.some(m => m !== model && m.faction === oldFaction);
        if (lastOne && settings.factionColours[oldFaction] && value && !settings.factionColours[value]) {
          settings.factionColours[value] = settings.factionColours[oldFaction];
        }
        if (lastOne) delete settings.factionColours[oldFaction];
        // Its painting schemes follow too (they'd otherwise point at a faction with no units).
        if (lastOne && oldFaction && value) for (const s of book.schemes) if (s.faction === oldFaction) s.faction = value;
        saveSettings();
      }
      model[field] = value;
      delete model.example;   // v21: renamed or moved to another army: it's yours now, not an example
      delete model.copy;
      // The group it left: if only one is left, it no longer needs a number.
      if (oldGroup.length === 1) delete oldGroup[0].copy;
      // The group it joined: number everyone, this unit last.
      const newGroup = models.filter(m => m !== model && sameGroup(m, model));
      if (newGroup.length > 0) {
        let highest = Math.max(0, ...newGroup.map(m => m.copy || 0));
        for (const m of newGroup) if (!m.copy) m.copy = ++highest;
        model.copy = highest + 1;
      }
      if (!isVisible(model)) clearFilters();  // so an edited unit never seems to vanish
      commit(`Saved ${displayName(model)}`);   // v18c-3: only says Saved if it was
    }

    // Move a unit up (+1) or back (-1) a stage, then show a message with Undo.
    // index: which model, for units tracked model-by-model. The big ▲ on a card doesn't
    // say, so it moves up the first model that's furthest behind.
    function changeStage(id, direction, index) {
      const model = models.find(m => m.id === id);
      if (!model) return;
      if (model.each && index === undefined) {
        if (direction < 0) return;
        index = model.stages.indexOf(model.stage);
      }
      const before = model.each ? model.stages[index] : model.stage;
      const after = before + direction;
      if (after < 0 || after >= STAGES.length) return;
      // v21.8: remember stage, stages and diary exactly, so Undo puts them back as they were
      // (before, Undo moved the model back but added a new diary entry dated today, which would
      // now show as the wrong date under a model's name).
      const snapshot = JSON.stringify({ stage: model.stage, stages: model.stages, log: model.log });
      setStage(model, after, model.each ? index : undefined);
      render();
      const who = model.each ? `${displayName(model)}, model ${index + 1}` : displayName(model);
      showToast(`${who} → ${STAGES[after]}`, () => {
        const unit = models.find(m => m.id === id);
        if (!unit) return;
        const was = JSON.parse(snapshot);
        unit.stage = was.stage;
        if (Array.isArray(was.stages)) unit.stages = was.stages;
        unit.log = was.log;
        render();
      });
    }

    // ----- v21: "THESE ARE EXAMPLES" -----
    // The app starts with 3 example units so there's something to look at. While any of
    // them are still there, a card on the Dashboard and the Units tab says so, with
    // "Clear examples" (removes ONLY those units, with Undo) and "Keep them" (they become
    // ordinary units and the card goes away). Renaming an example, or changing its game or
    // faction, also makes it yours (see editUnit).
    function exampleUnits() { return models.filter(m => m.example === true); }
    function renderExamplesCards() {
      const examples = exampleUnits();
      for (const id of ["examples-card-dash", "examples-card"]) {
        const card = document.getElementById(id);
        card.classList.toggle("hidden", !examples.length);
        card.innerHTML = "";
        if (!examples.length) continue;
        const text = document.createElement("p");
        const strong = document.createElement("strong");
        strong.textContent = examples.length === 1 ? "This is an example." : "These are examples.";
        const names = examples.map(m => displayName(m)).join(", ");
        text.append(strong, ` The app starts with ${examples.length === 1 ? "an example unit" : plural(examples.length, "example unit")} ` +
          `(${names}) so you can try things out. Clear ${examples.length === 1 ? "it" : "them"} when you're ready to add your own.`);
        const buttons = document.createElement("div");
        buttons.className = "button-grid";
        const clear = document.createElement("button");
        clear.type = "button";
        clear.className = "danger-button clear-examples";
        clear.textContent = "Clear examples";
        clear.addEventListener("click", clearExamples);
        const keep = document.createElement("button");
        keep.type = "button";
        keep.className = "plain-button keep-examples";
        keep.textContent = examples.length === 1 ? "Keep it" : "Keep them";
        keep.addEventListener("click", keepExamples);
        buttons.append(clear, keep);
        card.append(text, buttons);
      }
    }
    function clearExamples() {
      const gone = exampleUnits();
      if (!gone.length) return;
      // Remember where each one was, so Undo puts it back in the same place.
      const spots = gone.map(m => [models.indexOf(m), m]);
      models = models.filter(m => m.example !== true);
      for (const m of gone) openIds.delete(m.id);
      // Their photo files (if you added any) are left in the photo store, so Undo brings
      // them back too. "Clean up photo storage" in Settings removes them later.
      commit(`Cleared ${plural(gone.length, "example unit")}`, () => {
        for (const [spot, m] of spots) {
          if (models.some(x => x.id === m.id)) continue;   // that id is in use again: skip
          models.splice(Math.min(spot, models.length), 0, m);
        }
        render();
      }, "Undo", 8);
    }
    function keepExamples() {
      const kept = exampleUnits();
      if (!kept.length) return;
      for (const m of kept) delete m.example;
      commit(`Kept ${kept.length === 1 ? "the example as your own unit" : "the examples as your own units"}`, () => {
        for (const m of kept) if (models.includes(m)) m.example = true;
        render();
      });
    }

    // ----- v24: EXAMPLE RECIPES AND PAINTS -----
    // A brand-new start (no units saved yet, an empty recipe book) also gets two example recipes,
    // and the Citadel paints they use appear in Your Palette. A card on the Recipes tab says so,
    // with "Clear examples" (Undo for 8 seconds) and "Keep them". Anyone who already had data is
    // left alone. The marks are "example: true" on a recipe or a paint; older versions keep
    // unknown fields, so nothing here changes the shape of saved data (DATA_VERSION stays 1).
    // Rules: Clear removes only the example recipes, and the example paints that nothing of
    // yours uses. A paint you've used in your own recipe, given a status or edited is yours.
    // Example paints never appear on the shopping list. Each example recipe is linked to the
    // example unit it suits (Captain, Boyz), so you can see how recipes and units connect.
    const EXAMPLE_RECIPES = [
      { name: "Ultramarines armour", part: "Armour", unit: 1,
        notes: "An example recipe, to show how they look. Clear it when you're ready to write your own.",
        steps: [
          { technique: "Base coat", coats: 2, paints: [["Citadel", "Macragge Blue"]] },
          { technique: "Shade", coats: 1, paints: [["Citadel", "Nuln Oil"]] },
          { technique: "Layer", coats: 1, paints: [["Citadel", "Calgar Blue"]] },
          { technique: "Edge highlight", coats: 1, paints: [["Citadel", "Fenrisian Grey"]] },
        ] },
      { name: "Ork skin", part: "Skin", unit: 2,
        notes: "An example recipe, to show how they look. Clear it when you're ready to write your own.",
        steps: [
          { technique: "Base coat", coats: 2, paints: [["Citadel", "Waaagh! Flesh"]] },
          { technique: "Shade", coats: 1, paints: [["Citadel", "Agrax Earthshade"]] },
          { technique: "Layer", coats: 1, paints: [["Citadel", "Warboss Green"]] },
          { technique: "Edge highlight", coats: 1, paints: [["Citadel", "Skarsnik Green"]] },
        ] },
    ];
    function seedExampleRecipes() {
      if (!freshStart || settings.recipeExamplesChecked) return;
      settings.recipeExamplesChecked = true;   // saved by the start-up render()
      if (book.recipes.length || book.paints.length || book.schemes.length) return;
      for (const ex of EXAMPLE_RECIPES) {
        const steps = ex.steps.map(s => ({
          technique: s.technique, coats: s.coats,
          paints: s.paints.map(([brand, name]) => {
            const paint = findOrAddPaint(brand, name, "");
            paint.example = true;
            return { paint: paint.id, mix: null };
          }),
          ratio: "", note: "", optional: false,
        }));
        const recipe = { id: Math.max(0, ...book.recipes.map(r => r.id)) + 1, name: ex.name, part: ex.part,
                         notes: ex.notes, steps, example: true };
        book.recipes.push(recipe);
        const unit = models.find(m => m.id === ex.unit && m.example === true);
        if (unit) linkRecipe(unit, recipe.id);
      }
    }
    function exampleRecipes() { return book.recipes.filter(r => r.example === true); }
    // An example paint that is still only an example: nothing of yours uses it, it has no status.
    function usedByYourRecipe(paintId) {
      return book.recipes.some(r => r.example !== true && r.steps.some(s => s.paints.some(sp => sp.paint === paintId)));
    }
    function isExamplePaint(paint) {
      return paint.example === true && paintStatus(paint) === "" && !usedByYourRecipe(paint.id);
    }
    function examplePaints() { return book.paints.filter(isExamplePaint); }
    function exampleRecipeWords(recipes, paints) {
      const parts = [];
      if (recipes) parts.push(plural(recipes, "example recipe"));
      if (paints) parts.push(plural(paints, "example paint"));
      return parts.join(" and ");
    }
    function renderRecipeExamplesCard(show) {
      const card = document.getElementById("examples-card-recipes");
      const recipes = exampleRecipes(), paints = examplePaints();
      const any = show && (recipes.length || paints.length);
      card.classList.toggle("hidden", !any);
      card.innerHTML = "";
      if (!any) return;
      const text = document.createElement("p");
      const strong = document.createElement("strong");
      const many = recipes.length + paints.length > 1;
      strong.textContent = many ? "These are examples." : "This is an example.";
      const names = recipes.map(r => r.name).join(", ");
      text.append(strong, ` The app starts with ${exampleRecipeWords(recipes.length, paints.length)}` +
        (names ? ` (${names})` : "") + `, so you can see how recipes and your palette work. ` +
        `Clear ${many ? "them" : "it"} when you're ready to add your own. ` +
        `Paints you've used in your own recipes, or given a status, are kept.`);
      const buttons = document.createElement("div");
      buttons.className = "button-grid";
      const clear = document.createElement("button");
      clear.type = "button";
      clear.className = "danger-button clear-recipe-examples";
      clear.textContent = "Clear examples";
      clear.addEventListener("click", clearRecipeExamples);
      const keep = document.createElement("button");
      keep.type = "button";
      keep.className = "plain-button keep-recipe-examples";
      keep.textContent = many ? "Keep them" : "Keep it";
      keep.addEventListener("click", keepRecipeExamples);
      buttons.append(clear, keep);
      card.append(text, buttons);
    }
    function clearRecipeExamples() {
      const goneRecipes = exampleRecipes();
      const gonePaints = examplePaints();
      if (!goneRecipes.length && !gonePaints.length) return;
      // Remember where everything was, and which units were linked, so Undo can put it all back.
      const recipeSpots = goneRecipes.map(r => [book.recipes.indexOf(r), r]);
      const paintSpots = gonePaints.map(p => [book.paints.indexOf(p), p]);
      const links = [];
      for (const m of models) {
        const ids = (m.recipes || []).filter(id => goneRecipes.some(r => r.id === id));
        if (ids.length) links.push([m, ids.map(id => goneRecipes.find(r => r.id === id))]);
      }
      for (const [m, rs] of links) for (const r of rs) unlinkRecipe(m, r.id);
      book.recipes = book.recipes.filter(r => !goneRecipes.includes(r));
      book.paints = book.paints.filter(p => !gonePaints.includes(p));
      const message = `Cleared ${exampleRecipeWords(goneRecipes.length, gonePaints.length)}`;
      commit(message, () => {
        // Put each back in its old place. If its number has been taken since, it gets a new one
        // (and the steps and links that point at it follow).
        const paintIdMap = new Map();
        for (const [spot, p] of paintSpots) {
          if (book.paints.some(x => x.id === p.id)) {
            const fresh = Math.max(0, ...book.paints.map(x => x.id)) + 1;
            paintIdMap.set(p.id, fresh);
            p.id = fresh;
          }
          book.paints.splice(Math.min(spot, book.paints.length), 0, p);
        }
        for (const [spot, r] of recipeSpots) {
          for (const s of r.steps) for (const sp of s.paints) if (paintIdMap.has(sp.paint)) sp.paint = paintIdMap.get(sp.paint);
          if (book.recipes.some(x => x.id === r.id)) r.id = Math.max(0, ...book.recipes.map(x => x.id)) + 1;
          book.recipes.splice(Math.min(spot, book.recipes.length), 0, r);
          for (const [m, rs] of links) if (rs.includes(r) && models.includes(m)) linkRecipe(m, r.id);
        }
        render();
      }, "Undo", 8);
    }
    function keepRecipeExamples() {
      const recipes = book.recipes.filter(r => r.example === true);
      const paints = book.paints.filter(p => p.example === true);
      if (!recipes.length && !paints.length) return;
      for (const r of recipes) delete r.example;
      for (const p of paints) delete p.example;
      commit(`Kept the examples as your own`, () => {
        for (const r of recipes) if (book.recipes.includes(r)) r.example = true;
        for (const p of paints) if (book.paints.includes(p)) p.example = true;
        render();
      });
    }

    // ----- v21: JUMP TO STAGE -----
    // A menu listing every stage. current = the stage it shows (null = none, then
    // "placeholder" is shown as a first line you can't pick). onPick(stage) runs when
    // you choose a different stage. A phone shows its own big, easy picker for a menu.
    function stagePicker(current, label, onPick, placeholder) {
      const menu = document.createElement("select");
      menu.className = "stage-pick";
      menu.setAttribute("aria-label", label);
      if (current === null || current === undefined) {
        const first = new Option(placeholder || "Pick a stage…", "");
        first.disabled = true;
        menu.add(first);
      }
      STAGES.forEach((name, i) => menu.add(new Option(name, String(i))));
      menu.value = current === null || current === undefined ? "" : String(current);
      if (current !== null && current !== undefined) menu.style.setProperty("--stage-colour", `var(--stage-${current})`);
      menu.addEventListener("change", () => {
        if (menu.value === "") return;
        onPick(Number(menu.value));
      });
      return menu;
    }

    // Put a unit (or one model, if index is given) straight at a stage, with Undo.
    // Without an index, a unit tracked model by model has ALL its models moved.
    // Undo puts back exactly how it was, diary included.
    function jumpToStage(id, stage, index) {
      const model = models.find(m => m.id === id);
      if (!model || !Number.isInteger(stage) || stage < 0 || stage >= STAGES.length) return;
      if (!model.each) index = undefined;
      if (model.each && index !== undefined && !(index >= 0 && index < model.stages.length)) return;
      const already = index !== undefined ? model.stages[index] === stage
        : model.each ? model.stages.every(s => s === stage) : model.stage === stage;
      if (already) { render(); return; }
      const before = JSON.stringify({ stage: model.stage, stages: model.stages, log: model.log });
      setStage(model, stage, index);
      const who = index !== undefined ? `${displayName(model)}, model ${index + 1}`
        : model.each ? `All of ${displayName(model)}` : displayName(model);
      commit(`${who} → ${STAGES[stage]}`, () => {
        const unit = models.find(m => m.id === id);
        if (!unit) return;
        const was = JSON.parse(before);
        unit.stage = was.stage;
        if (Array.isArray(was.stages)) unit.stages = was.stages;
        unit.log = was.log;
        render();
      });
    }

    // ----- v21.1: SELECT MODE AND BULK "MOVE TO STAGE" -----
    // "Select" on the Units tab puts a tick box on every card you can see. The bar at the
    // bottom counts the ticks and has a "Move N to stage…" menu; picking a stage moves them
    // all at once, and ONE Undo puts every unit back exactly (diary included).
    function openSelect() {
      if (!models.length) return;
      selectMode = true;
      ticked.clear();
      closeAddForm();
      renderUnits();
    }
    function closeSelect() {
      selectMode = false;
      ticked.clear();
      renderUnits();
    }
    function toggleTick(id) {
      if (!selectMode) return;
      if (ticked.has(id)) ticked.delete(id); else ticked.add(id);
      renderUnits();
    }
    // Draws the bar to match the ticks. visible = the units the filters are showing.
    function refreshSelectBar(visible) {
      selectBar.classList.toggle("hidden", !selectMode);
      document.body.classList.toggle("selecting", selectMode);
      selectButton.setAttribute("aria-pressed", selectMode);
      if (!selectMode) { selectMoveSlot.innerHTML = ""; return; }
      const n = ticked.size;
      selectCount.textContent = `${n} of ${plural(visible.length, "unit")} ticked`;
      const allTicked = visible.length > 0 && visible.every(m => ticked.has(m.id));
      selectAllButton.textContent = allTicked ? "Untick all" : "Select all shown";
      selectAllButton.classList.toggle("hidden", visible.length === 0);
      const menu = stagePicker(null, `Move ${n} ticked to stage`, moveTicked,
        n ? `Move ${n} to stage…` : "Tick units to move them");
      menu.id = "select-move";
      menu.disabled = n === 0;
      selectMoveSlot.innerHTML = "";
      selectMoveSlot.appendChild(menu);
    }
    function selectAllShown() {
      const visible = models.filter(isVisible);
      if (visible.every(m => ticked.has(m.id))) ticked.clear();
      else for (const m of visible) ticked.add(m.id);
      renderUnits();
    }
    // Move every ticked unit (all models of a model-by-model unit) to one stage.
    function moveTicked(stage) {
      if (!Number.isInteger(stage) || stage < 0 || stage >= STAGES.length) return;
      const chosen = models.filter(m => ticked.has(m.id) && isVisible(m));
      const moving = chosen.filter(m => m.each ? !m.stages.every(s => s === stage) : m.stage !== stage);
      selectMode = false;     // select mode closes after a move
      ticked.clear();
      if (!moving.length) {
        render();
        showToast(chosen.length === 1 ? `${displayName(chosen[0])} is already ${STAGES[stage]}`
          : `All ${chosen.length} are already ${STAGES[stage]}`);
        return;
      }
      // A snapshot of each unit as it was, so Undo can put it back exactly.
      const before = moving.map(m => ({ id: m.id, was: JSON.stringify({ stage: m.stage, stages: m.stages, log: m.log }) }));
      for (const m of moving) setStage(m, stage);
      const skipped = chosen.length - moving.length;
      const who = moving.length === 1 ? displayName(moving[0]) : `${moving.length} units`;
      const message = `${who} → ${STAGES[stage]}` + (skipped ? ` (${skipped} already there)` : "");
      commit(message, () => {
        for (const b of before) {
          const unit = models.find(m => m.id === b.id);
          if (!unit) continue;
          const was = JSON.parse(b.was);
          unit.stage = was.stage;
          if (Array.isArray(was.stages)) unit.stages = was.stages;
          unit.log = was.log;
        }
        render();
      }, "Undo", 8);
    }

    // v21.5: deleting a unit still asks first, then offers Undo (8 seconds), like
    // deleting a photo. Undo puts the unit back exactly as it was, in the same place in
    // the list, details open if they were. Its photo FILES are only deleted once the Undo
    // message has gone (and only if no unit uses them again), so Undo brings photos back.
    // If the save fails (storage full), the files are left alone: the unit would come
    // back from the old saved copy next time, and it should still have its photos.
    // "Clean up photo storage" in Settings can tidy any left behind.
    const DELETE_UNIT_SECONDS = 8;
    function deleteModel(id) {
      const asked = models.find(m => m.id === id);
      if (!asked) return;
      // v21.7: the question is asked in the app's own box; the delete (and its Undo) happen when you say yes.
      askYesNo(`Delete "${displayName(asked)}"?`, () => deleteModelNow(id), { danger: true });
    }
    function deleteModelNow(id) {
      const model = models.find(m => m.id === id);   // looked up again: the list could have changed while the question was showing
      if (!model) return;
      const spot = models.indexOf(model);
      const wasOpen = openIds.has(id);
      const files = photoIds(model);
      models = models.filter(m => m !== model);
      openIds.delete(id);
      for (const f of files) pendingPhotoDeletes.add(f);
      const photosText = files.length ? ` and ${files.length === 1 ? "its photo" : "its " + files.length + " photos"}` : "";
      const saved = commit(`Deleted ${displayName(model)}${photosText}`, () => {
        if (!models.includes(model)) {
          // Very rare: a unit added since took this id number. Give this one a new number.
          if (models.some(m => m.id === model.id)) model.id = nextId();
          models.splice(Math.min(spot, models.length), 0, model);
        }
        for (const f of files) pendingPhotoDeletes.delete(f);
        if (wasOpen) openIds.add(model.id);
        commit(`${displayName(model)} is back`);
      }, "Undo", DELETE_UNIT_SECONDS);
      if (!saved) { for (const f of files) pendingPhotoDeletes.delete(f); return; }
      setTimeout(() => {
        for (const f of files) {
          if (!pendingPhotoDeletes.has(f)) continue;     // Undo was pressed
          pendingPhotoDeletes.delete(f);
          if (models.some(m => photoIds(m).includes(f))) continue;
          forgetUrls(f);
          deletePhotoFile(f);
        }
      }, DELETE_UNIT_SECONDS * 1000 + 500);
    }

    // ================= THE PHOTO STORE (v10) =================
    // Photos used to live inside the units list in localStorage, which only holds about
    // 5 MB in total. Now each photo is saved as a file ("blob") in IndexedDB, the browser's
    // bigger built-in database (usually hundreds of MB or more).
    //   In IndexedDB, keyed by id:  { id, full: ~1200px JPEG, thumb: ~240px JPEG }
    //   On the unit, just a note:    unit.photos = [{ id, date: "YYYY-MM-DD", stage }]
    // For now a unit has one photo (photos[0]). A gallery of several is planned next.
    // Old photos (unit.photo, a picture written out as text) are moved across on start up.

    const PHOTO_DB = "shades-of-grey-photos";
    let photoDbPromise = null;
    // Open the database once, creating its "photos" table the first time.
    function photoDb() {
      if (!photoDbPromise) photoDbPromise = new Promise((resolve, reject) => {
        if (!window.indexedDB) { reject(new Error("This browser has no IndexedDB")); return; }
        const request = indexedDB.open(PHOTO_DB, 1);
        request.onupgradeneeded = () => request.result.createObjectStore("photos", { keyPath: "id" });
        request.onsuccess = () => resolve(request.result);
        request.onerror = () => reject(request.error);
      });
      return photoDbPromise;
    }
    // Do one thing with the photos table and wait until it's really finished ("complete").
    // async/await: "await" pauses this function until the slow job is done, without
    // freezing the screen.
    async function photoStore(mode, action) {
      const db = await photoDb();
      return new Promise((resolve, reject) => {
        const tx = db.transaction("photos", mode);
        const request = action(tx.objectStore("photos"));
        tx.oncomplete = () => resolve(request ? request.result : undefined);
        tx.onerror = () => reject(tx.error);
        tx.onabort = () => reject(tx.error || new Error("Photo save cancelled"));
      });
    }
    const putPhoto = (record) => photoStore("readwrite", store => store.put(record));
    const getPhoto = (id) => photoStore("readonly", store => store.get(id));
    const deletePhotoFile = (id) => photoStore("readwrite", store => store.delete(id)).catch(() => {});

    // Pictures on screen need a web address. URL.createObjectURL gives one for a blob.
    // We keep them here so each photo is only read from the database once.
    const thumbUrls = new Map();   // photo id -> address of its thumbnail
    const fullUrls = new Map();    // photo id -> address of its full-size picture

    function newPhotoId() { return "p" + Date.now().toString(36) + Math.random().toString(36).slice(2, 7); }
    function photoIds(model) { return (model.photos || []).map(p => p.id); }
    function hasPhoto(model) { return !!model.photo || !!(model.photos && model.photos.length); }

    // A unit's photos in time order, oldest first: by date, and photos taken on the same
    // day stay in the order they were added. This is the progress timeline order.
    function timeline(model) {
      return (model.photos || [])
        .map((p, i) => ({ p, i }))
        .sort((a, b) => (a.p.date || "").localeCompare(b.p.date || "") || a.i - b.i)
        .map(x => x.p);
    }
    // The cover photo (the one on the unit's card): the one you chose, or else the newest.
    function mainPhoto(model) {
      const list = timeline(model);
      if (!list.length) return null;
      return list.find(p => p.id === model.coverPhoto) || list[list.length - 1];
    }
    // A short, friendly date: "2026-10-07" -> "7 Oct 2026".
    function shortDate(iso) {
      if (!iso) return "No date";
      const [y, mo, d] = iso.split("-").map(Number);
      return `${d} ${["Jan","Feb","Mar","Apr","May","Jun","Jul","Aug","Sep","Oct","Nov","Dec"][mo - 1]} ${y}`;
    }

    // v21.8: plain wording for "how long ago", used under each model's name:
    // "Today", "Yesterday", "Since 7 Oct" (this year) or "Since 7 Oct 2025" (earlier years).
    function sinceWording(iso) {
      if (typeof iso !== "string" || !/^\d{4}-\d{2}-\d{2}$/.test(iso)) return "";
      const days = Math.floor(daysSince(iso));
      if (days === 0) return "Today";
      if (days === 1) return "Yesterday";
      const [y, mo, d] = iso.split("-").map(Number);
      const month = ["Jan","Feb","Mar","Apr","May","Jun","Jul","Aug","Sep","Oct","Nov","Dec"][mo - 1];
      return y === new Date().getFullYear() ? `Since ${d} ${month}` : `Since ${d} ${month} ${y}`;
    }
    // When did model number `index` (0 = Model 1) of a track-each-model unit reach the stage
    // it's at now? The unit's diary has it: an entry [date, stage, n] is that one model
    // moving, an entry [date, stage] is the whole unit moving. The newest entry that
    // concerns this model wins. If that entry disagrees with where the model is now (the
    // diary can't say), or there's no entry, the answer is null and no date is shown.
    function modelSince(model, index) {
      const log = Array.isArray(model.log) ? model.log : [];
      for (let k = log.length - 1; k >= 0; k--) {
        const entry = log[k];
        if (entry[2] === undefined || entry[2] === index) return entry[1] === model.stages[index] ? entry[0] : null;
      }
      return null;
    }

    // Ask the browser to keep our data even when the device is short of space.
    // (It may say no; that's fine. iPhones also need the app added to the home screen.)
    function askToKeepStorage() {
      try {
        if (navigator.storage && navigator.storage.persist) {
          navigator.storage.persisted().then(kept => kept || navigator.storage.persist()).catch(() => {});
        }
      } catch (ignored) {}
    }

    // Open an image file (or blob) as a picture we can draw.
    function loadImage(file) {
      return new Promise((resolve, reject) => {
        const url = URL.createObjectURL(file);
        const img = new Image();
        img.onload = () => { URL.revokeObjectURL(url); resolve(img); };
        img.onerror = () => { URL.revokeObjectURL(url); reject(new Error("Unreadable image")); };
        img.src = url;
      });
    }
    // Shrink a picture to at most maxSize pixels across, as a compressed JPEG blob.
    function resizeToBlob(img, maxSize, quality) {
      return new Promise((resolve, reject) => {
        const scale = Math.min(1, maxSize / Math.max(img.width, img.height));
        const canvas = document.createElement("canvas");
        canvas.width = Math.max(1, Math.round(img.width * scale));
        canvas.height = Math.max(1, Math.round(img.height * scale));
        canvas.getContext("2d").drawImage(img, 0, 0, canvas.width, canvas.height);
        canvas.toBlob(blob => blob ? resolve(blob) : reject(new Error("Couldn't shrink image")), "image/jpeg", quality);
      });
    }
    // Text pictures ("data:image/jpeg;base64,...") <-> blobs, for old photos and full backups.
    function dataUrlToBlob(dataUrl) {
      const [head, data] = dataUrl.split(",");
      const type = (head.match(/^data:([^;,]+)/) || [])[1] || "image/jpeg";
      const binary = atob(data);
      const bytes = new Uint8Array(binary.length);
      for (let i = 0; i < binary.length; i++) bytes[i] = binary.charCodeAt(i);
      return new Blob([bytes], { type });
    }
    function blobToDataUrl(blob) {
      return new Promise((resolve, reject) => {
        const reader = new FileReader();
        reader.onload = () => resolve(reader.result);
        reader.onerror = () => reject(reader.error);
        reader.readAsDataURL(blob);
      });
    }

    // Load the thumbnails of every unit's photo that isn't on screen yet, then redraw once.
    // A photo note whose picture isn't in the database (e.g. after restoring a backup
    // saved WITHOUT photos on another device) is removed, so no empty boxes are left.
    async function loadThumbs() {
      let changed = false;
      for (const m of models) {
        for (const p of (m.photos || []).slice()) {
          if (thumbUrls.has(p.id)) continue;
          const record = await getPhoto(p.id);
          if (record && record.thumb) {
            thumbUrls.set(p.id, URL.createObjectURL(record.thumb));
          } else {
            m.photos = m.photos.filter(x => x.id !== p.id);
            if (!m.photos.length) delete m.photos;
          }
          changed = true;
        }
      }
      if (changed) render();
    }
    // The full-size picture, loaded when a unit's details are opened.
    async function fullPhotoUrl(id) {
      if (fullUrls.has(id)) return fullUrls.get(id);
      const record = await getPhoto(id);
      if (!record || !record.full) return "";
      fullUrls.set(id, URL.createObjectURL(record.full));
      return fullUrls.get(id);
    }
    function forgetUrls(id) {
      for (const map of [thumbUrls, fullUrls]) {
        if (map.has(id)) { URL.revokeObjectURL(map.get(id)); map.delete(id); }
      }
    }

    // Add a photo to a unit from a picked file. Since v11 this ADDS to the unit's photos
    // (it used to replace the only one). The photo remembers the unit's stage and today's
    // date, so it lands in the right place on the progress timeline.
    // modelIndex: for units tracked model-by-model, which model it shows (or undefined).
    async function addUnitPhoto(model, file, modelIndex) {
      let record;
      try {
        const img = await loadImage(file);
        record = { id: newPhotoId(), full: await resizeToBlob(img, 1200, 0.82), thumb: await resizeToBlob(img, 240, 0.75) };
      } catch (error) {
        notify("Sorry, that image couldn't be read.");
        return;
      }
      try {
        await putPhoto(record);
      } catch (error) {
        notify("The photo couldn't be saved. The device may be out of space, or this browser may block storage (e.g. a private window).");
        return;
      }
      // A photo of one model records that model's own stage; otherwise the unit's.
      const one = model.each && Number.isInteger(modelIndex) && modelIndex >= 0 && modelIndex < model.stages.length;
      const note = { id: record.id, date: todayISO(), stage: one ? model.stages[modelIndex] : model.stage };
      if (one) note.model = modelIndex;
      model.photos = [...(model.photos || []), note];
      thumbUrls.set(record.id, URL.createObjectURL(record.thumb));
      fullUrls.set(record.id, URL.createObjectURL(record.full));
      commit(`Photo added to ${displayName(model)} (${plural(model.photos.length, "photo")})`);   // v18c-3
      askToKeepStorage();
    }

    // Delete one photo, with Undo. The note comes off the unit straight away, but the
    // picture file itself is only deleted once the Undo message has gone. If Undo is
    // pressed, the note goes back in exactly the same place (and as cover, if it was).
    const pendingPhotoDeletes = new Set();   // ids waiting for their Undo to time out
    function deleteUnitPhoto(model, id) {
      const index = (model.photos || []).findIndex(p => p.id === id);
      if (index < 0) return;
      const note = model.photos[index];
      const wasCover = model.coverPhoto === id;
      model.photos.splice(index, 1);
      if (!model.photos.length) delete model.photos;
      if (wasCover) delete model.coverPhoto;
      pendingPhotoDeletes.add(id);
      render();
      const seconds = 6;
      showToast("Photo deleted", () => {
        model.photos = model.photos || [];
        model.photos.splice(Math.min(index, model.photos.length), 0, note);
        if (wasCover) model.coverPhoto = id;
        pendingPhotoDeletes.delete(id);
        render();
      }, null, seconds);
      // A little after the message goes, delete the file, unless Undo put it back on a unit.
      setTimeout(() => {
        if (!pendingPhotoDeletes.has(id)) return;
        pendingPhotoDeletes.delete(id);
        if (models.some(m => photoIds(m).includes(id))) return;
        forgetUrls(id);
        deletePhotoFile(id);
      }, seconds * 1000 + 500);
    }

    // Make a photo the unit's cover (the picture on its card).
    function setCoverPhoto(model, id) {
      model.coverPhoto = id;
      render();
      showToast("Cover photo set");
    }

    // Change a photo's stage, date or model afterwards (from the photo viewer).
    function editPhotoNote(model, id, field, value) {
      const note = (model.photos || []).find(p => p.id === id);
      if (!note) return;
      if (value === "" || value === null || value === undefined) delete note[field];
      else note[field] = value;
      render();
    }

    // Move old-style photos (saved as text on the unit) into the photo store. Each one is
    // only removed from the unit AFTER reading it back from the store and checking it's
    // all there. Anything that fails stays where it was, to be tried again next time.
    async function migrateOldPhotos() {
      let moved = 0;
      for (const m of models.filter(m => typeof m.photo === "string")) {
        try {
          const full = dataUrlToBlob(m.photo);
          const thumb = await resizeToBlob(await loadImage(full), 240, 0.75);
          const record = { id: newPhotoId(), full, thumb };
          await putPhoto(record);
          const check = await getPhoto(record.id);
          if (!check || !check.full || check.full.size !== full.size) continue;
          m.photos = [{ id: record.id, date: m.added || todayISO(), stage: m.stage }, ...(m.photos || [])];
          delete m.photo;
          moved++;
        } catch (error) { /* left as it was */ }
      }
      if (moved) save();
      return moved;
    }

    // Started once the screen has been drawn: move old photos, then show thumbnails.
    async function startPhotos() {
      try {
        const moved = await migrateOldPhotos();
        await loadThumbs();
        if (models.some(hasPhoto)) askToKeepStorage();
        if (moved) showToast(`Moved ${plural(moved, "photo")} to the app's bigger photo storage`, null, null, 6);
      } catch (error) {
        // No IndexedDB (some private windows): old photos still show; new ones can't be added.
      }
    }

    // ================= THE PHOTO VIEWER (v11) =================
    // A full-screen layer on top of the app, with two modes:
    //   "photo":   one photo at full size. ‹ › buttons, swiping, or the ← → keys move
    //              along the timeline. Below it you can change the photo's stage, date
    //              and model, make it the cover, or delete it.
    //   "compare": "Before / after". Two photos side by side (one above the other on a
    //              phone), or on top of each other with a slider to wipe between them.
    const viewerBox = document.getElementById("viewer");
    const viewerBody = document.getElementById("viewer-body");
    const viewerTitle = document.getElementById("viewer-title");
    let viewer = null;          // what the viewer is showing, or null when it's closed
    let focusBeforeViewer = null;

    function openLightbox(modelId, photoId) {
      viewer = { mode: "photo", modelId, photoId };
      showViewer();
    }
    function openCompare(modelId) {
      const model = models.find(m => m.id === modelId);
      const list = model ? timeline(model) : [];
      if (list.length < 2) return;
      // Start with the first and last photos: grey plastic vs. how it looks now.
      viewer = { mode: "compare", modelId, beforeId: list[0].id, afterId: list[list.length - 1].id, style: "side", slider: 50 };
      showViewer();
    }
    function showViewer() {
      focusBeforeViewer = document.activeElement;
      viewerBox.classList.remove("hidden");
      document.body.style.overflow = "hidden";   // stop the page behind from scrolling
      drawViewer();
      document.getElementById("viewer-close").focus();
    }
    function closeViewer() {
      viewer = null;
      viewerBox.classList.add("hidden");
      viewerBody.replaceChildren();
      document.body.style.overflow = "";
      if (focusBeforeViewer && focusBeforeViewer.isConnected) focusBeforeViewer.focus();
    }
    document.getElementById("viewer-close").addEventListener("click", closeViewer);
    document.addEventListener("keydown", (event) => {
      if (!viewer) return;
      if (event.key === "Escape") { closeViewer(); return; }
      // Arrow keys move between photos, unless you're typing in a box.
      const typing = /^(INPUT|SELECT|TEXTAREA)$/.test(document.activeElement.tagName);
      if (viewer.mode === "photo" && !typing) {
        if (event.key === "ArrowLeft") moveViewer(-1);
        if (event.key === "ArrowRight") moveViewer(+1);
      }
    });

    // Show the full-size picture in an <img>. Shows the small one first if the big one
    // still has to be read from the photo store, so there's never a blank gap.
    function setFullSrc(img, id) {
      if (fullUrls.has(id)) { img.src = fullUrls.get(id); return; }
      if (thumbUrls.has(id)) img.src = thumbUrls.get(id);
      fullPhotoUrl(id).then(url => { if (url && img.isConnected) img.src = url; }).catch(() => {});
    }

    function drawViewer() {
      if (!viewer) return;
      const model = models.find(m => m.id === viewer.modelId);
      const list = model ? timeline(model) : [];
      if (!list.length) { closeViewer(); return; }
      viewerBody.replaceChildren();
      if (viewer.mode === "photo") drawPhotoView(model, list);
      else drawCompareView(model, list);
    }

    function moveViewer(step) {
      const model = models.find(m => m.id === viewer.modelId);
      const list = model ? timeline(model) : [];
      const index = list.findIndex(p => p.id === viewer.photoId);
      const next = list[index + step];
      if (!next) return;
      viewer.photoId = next.id;
      drawViewer();
    }

    function drawPhotoView(model, list) {
      let index = list.findIndex(p => p.id === viewer.photoId);
      if (index < 0) { index = 0; viewer.photoId = list[0].id; }
      const p = list[index];
      viewerTitle.textContent = `${displayName(model)} · photo ${index + 1} of ${list.length}`;

      // The picture, with ‹ › on top.
      const stageBox = document.createElement("div");
      stageBox.className = "viewer-stage";
      const img = document.createElement("img");
      img.alt = `${displayName(model)}: ${photoCaption(model, p)}`;
      img.draggable = false;
      setFullSrc(img, p.id);
      stageBox.appendChild(img);
      const arrow = (label, cls, step, disabled) => {
        const b = document.createElement("button");
        b.className = `viewer-arrow ${cls}`;
        b.textContent = label;
        b.disabled = disabled;
        b.setAttribute("aria-label", step < 0 ? "Older photo" : "Newer photo");
        b.addEventListener("click", () => moveViewer(step));
        stageBox.appendChild(b);
      };
      arrow("‹", "prev", -1, index === 0);
      arrow("›", "next", +1, index === list.length - 1);
      // Swiping: remember where the finger went down; a sideways move of 50px or more
      // when it lifts counts as a swipe (left = newer, right = older).
      let startX = null;
      stageBox.addEventListener("pointerdown", e => { startX = e.clientX; });
      stageBox.addEventListener("pointerup", e => {
        if (startX === null) return;
        const moved = e.clientX - startX;
        startX = null;
        if (Math.abs(moved) >= 50) moveViewer(moved < 0 ? +1 : -1);
      });

      // The caption: stage colour dot, stage, date, model, and whether it's the cover.
      const caption = document.createElement("div");
      caption.className = "viewer-caption";
      caption.style.setProperty("--stage-colour", validStageIndex(p.stage) ? `var(--stage-${p.stage})` : "var(--border)");
      const dot = document.createElement("span");
      dot.className = "dot";
      const text = document.createElement("span");
      text.textContent = photoCaption(model, p);
      caption.append(dot, text);
      const isCover = mainPhoto(model).id === p.id;
      if (isCover) {
        const star = document.createElement("span");
        star.className = "cover-badge";
        star.style.position = "static";
        star.textContent = "★ Cover photo";
        caption.appendChild(star);
      }

      // Change this photo's details. Each change is saved straight away.
      const form = document.createElement("div");
      form.className = "viewer-form";
      const stageLabel = document.createElement("label");
      stageLabel.textContent = "Stage in this photo";
      const stageSelect = document.createElement("select");
      stageSelect.add(new Option("Not set", ""));
      STAGES.forEach((s, i) => stageSelect.add(new Option(s, String(i))));
      stageSelect.value = validStageIndex(p.stage) ? String(p.stage) : "";
      stageSelect.addEventListener("change", () => {
        editPhotoNote(model, p.id, "stage", stageSelect.value === "" ? null : Number(stageSelect.value));
        drawViewer();
      });
      stageLabel.appendChild(stageSelect);
      const dateLabel = document.createElement("label");
      dateLabel.textContent = "Date taken";
      const dateBox = document.createElement("input");
      dateBox.type = "date";
      dateBox.value = p.date || "";
      dateBox.addEventListener("change", () => {
        // Changing the date can move the photo along the timeline; it stays on screen.
        editPhotoNote(model, p.id, "date", /^\d{4}-\d{2}-\d{2}$/.test(dateBox.value) ? dateBox.value : null);
        drawViewer();
      });
      dateLabel.appendChild(dateBox);
      form.append(stageLabel, dateLabel);
      if (model.each) {
        const modelLabel = document.createElement("label");
        modelLabel.className = "wide";
        modelLabel.textContent = "Which model?";
        const modelSelect = document.createElement("select");
        modelSelect.add(new Option("Whole unit", ""));
        model.stages.forEach((st, i) => modelSelect.add(new Option(`Model ${i + 1}`, String(i))));
        modelSelect.value = photoModel(model, p) !== null ? String(p.model) : "";
        modelSelect.addEventListener("change", () => {
          editPhotoNote(model, p.id, "model", modelSelect.value === "" ? null : Number(modelSelect.value));
          drawViewer();
        });
        modelLabel.appendChild(modelSelect);
        form.appendChild(modelLabel);
      }

      const buttons = document.createElement("div");
      buttons.className = "panel-buttons";
      const cover = document.createElement("button");
      cover.className = "plain-button";
      cover.textContent = isCover ? "★ This is the cover" : "☆ Use as cover";
      cover.disabled = isCover;
      cover.addEventListener("click", () => { setCoverPhoto(model, p.id); drawViewer(); });
      const compare = document.createElement("button");
      compare.className = "plain-button";
      compare.textContent = "Before / after";
      compare.disabled = list.length < 2;
      compare.addEventListener("click", () => openCompare(model.id));
      const del = document.createElement("button");
      del.className = "danger-button";
      del.textContent = "Delete photo";
      del.addEventListener("click", () => {
        // Stay in the viewer on the next photo along (or the one before), if there is one.
        const next = list[index + 1] || list[index - 1];
        deleteUnitPhoto(model, p.id);
        if (next) { viewer.photoId = next.id; drawViewer(); } else closeViewer();
      });
      buttons.append(cover, compare, del);

      viewerBody.append(stageBox, caption, form, buttons);
    }

    function drawCompareView(model, list) {
      viewerTitle.textContent = `${displayName(model)} · before / after`;
      // If a chosen photo was deleted meanwhile, fall back to the first / last.
      if (!list.some(p => p.id === viewer.beforeId)) viewer.beforeId = list[0].id;
      if (!list.some(p => p.id === viewer.afterId)) viewer.afterId = list[list.length - 1].id;

      // Side by side, or slider?
      const switchRow = document.createElement("div");
      switchRow.className = "switch-row";
      for (const [style, label] of [["side", "Side by side"], ["slider", "Slider"]]) {
        const b = document.createElement("button");
        b.className = "plain-button";
        b.textContent = label;
        b.setAttribute("aria-pressed", viewer.style === style);
        b.addEventListener("click", () => { viewer.style = style; drawViewer(); });
        switchRow.appendChild(b);
      }

      // Pick which two photos to compare.
      const picker = (labelText, key) => {
        const label = document.createElement("label");
        label.textContent = labelText;
        const select = document.createElement("select");
        list.forEach((p, i) => select.add(new Option(`${i + 1}. ${photoCaption(model, p)}`, p.id)));
        select.value = viewer[key];
        select.addEventListener("change", () => { viewer[key] = select.value; drawViewer(); });
        label.appendChild(select);
        return label;
      };
      const pickers = document.createElement("div");
      pickers.className = "viewer-form";
      pickers.append(picker("Before", "beforeId"), picker("After", "afterId"));

      const before = list.find(p => p.id === viewer.beforeId);
      const after = list.find(p => p.id === viewer.afterId);
      let pictures;
      if (viewer.style === "side") {
        pictures = document.createElement("div");
        pictures.className = "compare-pair";
        for (const [word, p] of [["Before", before], ["After", after]]) {
          const side = document.createElement("div");
          side.className = "compare-side";
          const label = document.createElement("div");
          label.className = "compare-label";
          label.textContent = `${word}: ${photoCaption(model, p)}`;
          const frame = document.createElement("div");
          frame.className = "frame";
          const img = document.createElement("img");
          img.alt = `${word}: ${photoCaption(model, p)}`;
          setFullSrc(img, p.id);
          frame.appendChild(img);
          side.append(label, frame);
          pictures.appendChild(side);
        }
      } else {
        // The "after" picture is laid exactly over "before", and only the part to the
        // right of the line is shown (clip-path cuts the rest off). Drag the slider to move it.
        pictures = document.createElement("div");
        pictures.className = "compare-side";
        const frame = document.createElement("div");
        frame.className = "slider-frame";
        const beforeImg = document.createElement("img");
        beforeImg.alt = `Before: ${photoCaption(model, before)}`;
        setFullSrc(beforeImg, before.id);
        const afterImg = document.createElement("img");
        afterImg.alt = `After: ${photoCaption(model, after)}`;
        setFullSrc(afterImg, after.id);
        const line = document.createElement("div");
        line.className = "slider-line";
        const tagBefore = document.createElement("span");
        tagBefore.className = "slider-tag";
        tagBefore.style.left = "8px";
        tagBefore.textContent = "Before";
        const tagAfter = document.createElement("span");
        tagAfter.className = "slider-tag";
        tagAfter.style.right = "8px";
        tagAfter.textContent = "After";
        frame.append(beforeImg, afterImg, line, tagBefore, tagAfter);
        const slider = document.createElement("input");
        slider.type = "range";
        slider.min = 0;
        slider.max = 100;
        slider.value = viewer.slider;
        slider.setAttribute("aria-label", "Slide between before and after");
        const place = () => {
          viewer.slider = Number(slider.value);
          afterImg.style.clipPath = `inset(0 0 0 ${viewer.slider}%)`;
          line.style.left = `calc(${viewer.slider}% - 1px)`;
        };
        slider.addEventListener("input", place);
        place();
        pictures.append(frame, slider);
      }
      viewerBody.append(switchRow, pickers, pictures);
    }

    // ----- The pop-up message with Undo -----

    const toast = document.getElementById("toast");
    const toastText = document.getElementById("toast-text");
    const toastUndo = document.getElementById("toast-undo");
    let toastTimer;
    let undoAction = null;

    // The button usually says "Undo", but can say something else (e.g. "Back up").
    function showToast(message, undo, buttonLabel, seconds) {
      delete toast.dataset.kind;   // v21.6: notify() marks a plain notice below; every other message is unmarked
      toastText.textContent = message;
      undoAction = undo || null;
      toastUndo.textContent = buttonLabel || "Undo";
      toastUndo.classList.toggle("hidden", !undo);
      toast.classList.remove("hidden");
      clearTimeout(toastTimer);
      toastTimer = setTimeout(() => toast.classList.add("hidden"), (seconds || 4) * 1000);
    }
    toastUndo.addEventListener("click", () => {
      // Hide first, THEN run the action, so the action can show a new message of its own
      // (e.g. "Apply to 3 units" shows "Applied…" with its own Undo).
      const action = undoAction;
      undoAction = null;
      toast.classList.add("hidden");
      if (action) action();
    });

    // v21.6: NOTICES. These used to be the browser's own pop-up boxes (alert). Now they use the
    // same little message as everything else: no box to dismiss, nothing blocks the page.
    // Longer messages stay up longer (about 1 second per 14 letters, between 6 and 20 seconds),
    // and a tap on a notice hides it. (Questions that need a yes or no are still pop-ups for now:
    // confirm and prompt move to an in-app dialog in v21.7.)
    function notify(message, seconds) {
      showToast(message, null, null, seconds || Math.min(20, Math.max(6, Math.ceil(message.length / 14))));
      toast.dataset.kind = "notice";
    }
    toast.addEventListener("click", (event) => {
      if (undoAction || event.target === toastUndo) return;   // a message with a button isn't hidden by a stray tap
      clearTimeout(toastTimer);
      toast.classList.add("hidden");
    });

    // ================= v21.7: THE IN-APP QUESTION BOX =================
    // Before v21.7, the app asked questions ("Delete this unit?", "Name of the new part:")
    // with the browser's own pop-up boxes. Those look different on every phone, can't be
    // styled, and stop the whole page while they're up. Now the app has its own small box:
    //   askYesNo(message, onYes, { onNo, danger, yes, no })  - a yes/no question
    //   askText(message, start, onDone)                       - "type a name": onDone(text), or null if cancelled
    //   showTextToCopy(message, text)                         - shows some text to copy by hand
    // IMPORTANT difference: the old pop-ups stopped the code until you answered, so a line
    // an "ask, and give up if the answer is no" line worked. The new box can't do that. The code asks,
    // then carries on LATER, from the function handed in (onYes / onDone), when you answer.
    // Cancel, the Escape key and the phone's Back button all count as "no".
    // The box lives in index.html (markup and styles only); this is the code that runs it.
    const dialogBackdrop = document.getElementById("dialog-backdrop");
    const dialogBox = document.getElementById("dialog");
    const dialogMessage = document.getElementById("dialog-message");
    const dialogInput = document.getElementById("dialog-input");
    const dialogArea = document.getElementById("dialog-area");
    const dialogButtons = document.getElementById("dialog-buttons");
    const dialogYes = document.getElementById("dialog-yes");
    const dialogNo = document.getElementById("dialog-no");
    let dialogState = null;   // null, or { cfg, opener } while a question is showing

    function showDialog(cfg) {
      if (dialogState) finishDialog(dialogState.cfg.mode === "text" ? null : false);   // a new question replaces the old one, which counts as "no"
      const text = cfg.mode === "text", show = cfg.mode === "show";
      dialogMessage.textContent = cfg.message;
      dialogInput.classList.toggle("hidden", !text);
      dialogArea.classList.toggle("hidden", !show);
      dialogInput.value = text ? (cfg.initial || "") : "";
      dialogArea.value = show ? (cfg.initial || "") : "";
      dialogYes.textContent = cfg.yes || (text ? "OK" : show ? "Close" : "Yes");
      dialogNo.textContent = cfg.no || (text ? "Cancel" : "No");
      // A question about something destructive makes the safe answer the bold one.
      dialogYes.className = cfg.danger ? "danger-button" : "primary-button";
      dialogNo.className = cfg.danger ? "primary-button" : "plain-button";
      dialogNo.classList.toggle("hidden", show);   // (after the line above, which sets the whole class)
      dialogButtons.classList.toggle("single", show);
      dialogState = { cfg, opener: document.activeElement };
      dialogBackdrop.classList.remove("hidden");
      const first = text ? dialogInput : show ? dialogArea : dialogYes;
      first.focus();
      if (text || show) first.select();
      queueBackCheck();   // so the phone's Back button can close it
    }

    // Close the box and hand back the answer (true/false, the typed text, or null).
    function finishDialog(answer) {
      const state = dialogState;
      if (!state) return;
      dialogState = null;
      dialogBackdrop.classList.add("hidden");
      dialogInput.value = "";
      dialogArea.value = "";
      const opener = state.opener;
      if (opener && opener.isConnected && typeof opener.focus === "function") {
        try { opener.focus({ preventScroll: true }); } catch (ignored) {}
      }
      queueBackCheck();
      state.cfg.onDone(answer);
    }
    // What Back, Escape and the "No" / "Cancel" button do.
    function cancelDialog() {
      if (dialogState) finishDialog(dialogState.cfg.mode === "text" ? null : false);
    }
    function acceptDialog() {
      if (!dialogState) return;
      const mode = dialogState.cfg.mode;
      finishDialog(mode === "text" ? dialogInput.value : true);
    }
    dialogYes.addEventListener("click", acceptDialog);
    dialogNo.addEventListener("click", cancelDialog);
    // Escape = no. Enter = yes (unless a button has the focus: then Enter presses that button).
    // Tab stays inside the box. Written to run first, so nothing else sees these keys.
    document.addEventListener("keydown", (event) => {
      if (!dialogState || event.isComposing) return;
      if (event.key === "Escape") {
        event.preventDefault(); event.stopPropagation();
        cancelDialog();
      } else if (event.key === "Enter" && !(event.target instanceof HTMLButtonElement)) {
        event.preventDefault(); event.stopPropagation();
        acceptDialog();
      } else if (event.key === "Tab") {
        const stops = [dialogInput, dialogArea, dialogNo, dialogYes].filter(el => !el.classList.contains("hidden"));
        const at = stops.indexOf(document.activeElement);
        const next = event.shiftKey ? (at <= 0 ? stops.length - 1 : at - 1) : (at < 0 || at === stops.length - 1 ? 0 : at + 1);
        event.preventDefault();
        stops[next].focus();
      }
    }, true);
    // If focus somehow lands outside the box (a screen reader's own keys, say), pull it back in.
    document.addEventListener("focusin", (event) => {
      if (dialogState && !dialogBox.contains(event.target)) {
        const first = !dialogInput.classList.contains("hidden") ? dialogInput : !dialogArea.classList.contains("hidden") ? dialogArea : dialogYes;
        first.focus();
      }
    });

    function askYesNo(message, onYes, options) {
      const opts = options || {};
      showDialog({
        mode: "yesno", message, yes: opts.yes, no: opts.no, danger: !!opts.danger,
        onDone: (ok) => { if (ok) onYes(); else if (opts.onNo) opts.onNo(); },
      });
    }
    function askText(message, initial, onDone, options) {
      const opts = options || {};
      showDialog({ mode: "text", message, initial, yes: opts.yes, no: opts.no, onDone });
    }
    function showTextToCopy(message, text) {
      showDialog({ mode: "show", message, initial: text, onDone: () => {} });
    }

    // ----- Filters and the add form -----

    hobbyFilter.addEventListener("change", () => {
      filters.hobby = hobbyFilter.value;
      filters.faction = "";
      render();
    });
    factionFilter.addEventListener("change", () => { filters.faction = factionFilter.value; render(); });
    clearFiltersButton.addEventListener("click", () => { clearFilters(); render(); });

    // Fold the filter card open or shut. Starts open only on wide screens.
    const toggleFilters = document.getElementById("toggle-filters");
    const filterCard = document.getElementById("filter-card");
    let filtersOpen = window.matchMedia("(min-width: 900px)").matches;
    function setFiltersOpen(open) {
      filtersOpen = open;
      filterCard.classList.toggle("hidden", !open);
      toggleFilters.setAttribute("aria-expanded", open);
      render();
    }
    toggleFilters.addEventListener("click", () => setFiltersOpen(!filtersOpen));
    filterCard.classList.toggle("hidden", !filtersOpen);

    const form = document.getElementById("add-form");
    const toggleAdd = document.getElementById("toggle-add");
    const nameInput = document.getElementById("name-input");
    const countInput = document.getElementById("count-input");
    const hobbyInput = document.getElementById("hobby-input");
    const factionInput = document.getElementById("faction-input");

    // v21: the Add form's "Starting stage" menu. Rebuilt with every redraw (stages can be
    // renamed or added in Settings), keeping your choice while that stage still exists.
    const stageInput = document.getElementById("stage-input");
    function fillStartStage() {
      const keep = Number(stageInput.value);
      stageInput.innerHTML = "";
      STAGES.forEach((name, i) => stageInput.add(new Option(name, String(i))));
      stageInput.value = Number.isInteger(keep) && keep >= 0 && keep < STAGES.length ? String(keep) : "0";
      stageInput.style.setProperty("--stage-colour", `var(--stage-${stageInput.value})`);
    }
    function startStage() {
      const n = Number(stageInput.value);
      return Number.isInteger(n) && n >= 0 && n < STAGES.length ? n : 0;
    }
    stageInput.addEventListener("change", () =>
      stageInput.style.setProperty("--stage-colour", `var(--stage-${stageInput.value})`));

    toggleAdd.addEventListener("click", () => {
      const opening = form.classList.contains("hidden");
      if (opening && draftWaiting("unit")) return;   // v26: a kept unfinished unit is offered first
      form.classList.toggle("hidden", !opening);
      toggleAdd.textContent = opening ? "Close" : "+ Add unit";
      if (opening && selectMode) closeSelect();   // v21.1: one thing at a time
      if (opening) nameInput.focus();
    });

    // v21.1: Select (tap again to stop), Select all shown, Cancel.
    selectButton.addEventListener("click", () => { if (selectMode) closeSelect(); else openSelect(); });
    selectAllButton.addEventListener("click", selectAllShown);
    document.getElementById("select-cancel").addEventListener("click", closeSelect);

    form.addEventListener("submit", (event) => {
      event.preventDefault();                   // stop the browser reloading the page
      if (!nameInput.value.trim()) return;      // ignore names that are only spaces
      const newModel = addModel({
        name: nameInput.value.trim(),
        count: cleanCount(countInput.value),
        hobby: hobbyInput.value.trim(),
        faction: factionInput.value.trim(),
        stage: startStage(),   // v21: the stage picked in "Starting stage"
      });
      if (!isVisible(newModel)) clearFilters();  // so a new unit never seems to vanish
      nameInput.value = "";
      countInput.value = 1;
      // preventScroll: keep the box ready for the next name without jumping back up to it.
      nameInput.focus({ preventScroll: true });
      // Game, faction and starting stage stay filled in, since you'll often add several
      // from one army.
      justAddedId = newModel.id;   // v21.5: highlighted when the list is drawn
      if (commit(`Added ${displayName(newModel)}`)) showNewUnit(newModel.id);   // v18c-3
    });

    // v21.5: a newly added unit is brought into view and briefly outlined, instead of
    // appearing somewhere off-screen. It scrolls only as far as needed (not at all if the
    // card is already on screen), and stops ABOVE the tab bar and the "Added…" message at
    // the bottom, which would otherwise cover it. Smooth unless the phone asks for less motion.
    const JUST_ADDED_MS = 2500;
    function showNewUnit(id) {
      const card = list.querySelector(`li.unit[data-id="${id}"]`);
      if (card) {
        const gap = 12;
        let bottom = window.innerHeight - gap;
        for (const el of [document.querySelector(".tabs"), toast]) {
          if (!el || el.classList.contains("hidden")) continue;
          const r = el.getBoundingClientRect();
          if (r.height && r.top > window.innerHeight / 2) bottom = Math.min(bottom, r.top - gap);   // only bars along the bottom
        }
        const box = card.getBoundingClientRect();
        let by = 0;
        if (box.bottom > bottom) by = box.bottom - bottom;     // below the clear area: scroll down
        if (box.top - by < gap) by = box.top - gap;            // taller than the gap, or above: show its top
        if (Math.abs(by) > 1) {
          const calm = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
          window.scrollBy({ top: by, behavior: calm ? "auto" : "smooth" });
        }
      }
      clearTimeout(justAddedTimer);
      justAddedTimer = setTimeout(() => {
        justAddedId = null;
        list.querySelectorAll("li.unit.just-added").forEach(li => li.classList.remove("just-added"));
      }, JUST_ADDED_MS);
    }

    // ================= RECIPES TAB =================

    // ----- Small helpers -----
    function recipeById(id) { return book.recipes.find(r => r.id === id); }
    function paintById(id) { return book.paints.find(p => p.id === id); }
    // A unit's recipes (skipping any that have since been deleted).
    function recipesOf(model) { return (model.recipes || []).map(recipeById).filter(Boolean); }
    function unitsUsing(recipeId) { return models.filter(m => (m.recipes || []).includes(recipeId)); }
    function linkRecipe(model, recipeId) {
      if (!(model.recipes || []).includes(recipeId)) model.recipes = [...(model.recipes || []), recipeId];
    }
    function unlinkRecipe(model, recipeId) {
      model.recipes = (model.recipes || []).filter(id => id !== recipeId);
      if (!model.recipes.length) delete model.recipes;
    }
    function coatsText(n) { return `${n} coat${n === 1 ? "" : "s"}`; }

    // Every colour used in a recipe, in order, each once.
    function recipeColours(recipe) {
      const colours = [];
      for (const step of recipe.steps) for (const sp of step.paints) {
        const paint = paintById(sp.paint);
        if (paint && !colours.includes(paint.colour)) colours.push(paint.colour);
      }
      return colours;
    }

    function makeSwatch(colour) {
      const s = document.createElement("span");
      s.className = "swatch";
      s.style.setProperty("--swatch", colour);
      return s;
    }

    // A rounded button showing a recipe's name, with a dot of its first colour.
    function recipeChip(recipe, onClick) {
      const chip = document.createElement("button");
      chip.className = "recipe-chip";
      const colours = recipeColours(recipe);
      if (colours.length) chip.appendChild(makeSwatch(colours[0]));
      chip.append(recipe.name);
      chip.setAttribute("aria-label", `Open recipe: ${recipe.name}`);
      chip.addEventListener("click", onClick);
      return chip;
    }

    // Wraps a chip with an ✕ button beside it, for unlinking.
    function linkedChip(chip, removeLabel, onRemove) {
      const wrap = document.createElement("span");
      wrap.className = "linked";
      const x = document.createElement("button");
      x.className = "unlink";
      x.textContent = "✕";
      x.setAttribute("aria-label", removeLabel);
      x.addEventListener("click", onRemove);
      wrap.append(chip, x);
      return wrap;
    }

    // Paints no recipe uses any more are tidied away, so the palette only shows real ones.
    function pruneUnusedPaints() {
      const used = new Set();
      for (const r of book.recipes) for (const s of r.steps) for (const sp of s.paints) used.add(sp.paint);
      book.paints = book.paints.filter(p => used.has(p.id) || paintStatus(p) !== "");   // v16: scanned paints stay; v17: so do paints with a status
    }

    // Finds a paint by brand and name (ignoring capitals), or adds it. Its colour is updated.
    function findOrAddPaint(brand, name, colour) {
      brand = tidyBrand(brand);   // v18c: "CitadelCitadel" → "Citadel"
      name = name.trim();
      // No brand typed? Then any paint with that name counts as the same paint.
      let paint = book.paints.find(p => sameText(p.name, name) && (!brand || sameText(p.brand, brand)));
      if (!paint) {
        const known = KNOWN_PAINTS.find(k => sameText(k.name, name) && (!brand || sameText(k.brand, brand)));
        paint = { id: Math.max(0, ...book.paints.map(p => p.id)) + 1, brand: brand || (known ? known.brand : ""),
                  name, colour: known ? known.colour : DEFAULT_PAINT_COLOUR };
        if (MATERIAL_WORDS.test(name)) paint.type = "material";   // v15
        book.paints.push(paint);
      }
      // The untouched grey never overwrites a colour you've already picked.
      if (/^#[0-9a-f]{6}$/i.test(colour) && colour.toLowerCase() !== DEFAULT_PAINT_COLOUR) paint.colour = colour.toLowerCase();
      return paint;
    }

    // Mix %: an even split for n paints, e.g. 3 paints = 34, 33, 33.
    function evenSplit(n) {
      const base = Math.floor(100 / n);
      const parts = new Array(n).fill(base);
      parts[0] += 100 - base * n;
      return parts;
    }
    // True if a step's mixes are still the automatic even split (or all blank), so it's
    // safe to re-split them when a paint is added or removed.
    function isEvenSplit(paints) {
      if (!paints.length || paints.every(p => p.mix === null)) return true;
      const even = evenSplit(paints.length);
      return paints.every((p, i) => p.mix === even[i]);
    }
    function resplit(paints) { evenSplit(paints.length).forEach((mix, i) => { paints[i].mix = mix; }); }

    // A warning if a step's mix doesn't add up to 100%.
    function mixWarning(paints) {
      const named = paints.filter(p => p.name.trim());
      if (named.length < 2 || named.some(p => p.mix === null)) return "";
      const total = named.reduce((sum, p) => sum + p.mix, 0);
      return total === 100 ? "" : `The mix adds up to ${total}%, not 100%.`;
    }

    // ----- Which page is showing -----
    const recipeHome = document.getElementById("recipe-home");
    const recipePage = document.getElementById("recipe-page");
    const recipeList = document.getElementById("recipe-list");
    const partFilter = document.getElementById("part-filter");
    let recipePartFilter = "";
    let openRecipeId = null;   // the recipe being read, or null for the list
    let recipeDraft = null;    // the recipe being edited (a copy), or null
    const schemeView = document.getElementById("scheme-view");
    let schemeDraft = null;    // the painting scheme being edited (a copy), or null

    function renderRecipes() {
      if (openRecipeId !== null && !recipeById(openRecipeId)) openRecipeId = null;
      // v16: Paste recipes fills the screen while it's open.
      importPage.classList.toggle("hidden", !importDraft);
      if (importDraft) {
        renderRecipeExamplesCard(false);
        fillDraftCard("recipe", false); fillDraftCard("paste", false);   // v26
        for (const el of [recipeSeg, recipeHome, paletteView, schemeView, recipePage]) el.classList.add("hidden");
        renderImport();
        return;
      }
      const onPage = !!recipeDraft || openRecipeId !== null;
      const onPalette = !onPage && settings.recipeView === "palette";
      const onSchemes = !onPage && settings.recipeView === "schemes";
      const current = onPalette ? "palette" : onSchemes ? "schemes" : "recipes";
      // The switch hides while a recipe or a scheme being edited fills the screen.
      recipeSeg.classList.toggle("hidden", onPage || (onSchemes && !!schemeDraft));
      renderRecipeExamplesCard(!onPage && !(onSchemes && !!schemeDraft));   // v24
      fillDraftCard("recipe", !onPage && !(onSchemes && !!schemeDraft));    // v26: kept unfinished work
      fillDraftCard("paste", !onPage && !(onSchemes && !!schemeDraft));
      recipeSeg.querySelectorAll("button").forEach(b => b.setAttribute("aria-selected", b.dataset.view === current));
      recipeHome.classList.toggle("hidden", onPage || onPalette || onSchemes);
      paletteView.classList.toggle("hidden", !onPalette);
      schemeView.classList.toggle("hidden", !onSchemes);
      recipePage.classList.toggle("hidden", !onPage);
      if (recipeDraft) renderRecipeEditor();
      else if (openRecipeId !== null) renderRecipeView(recipeById(openRecipeId));
      else if (onPalette) renderPalette();
      else if (onSchemes) renderSchemes();
      else renderRecipeList();
    }

    const recipeSeg = document.getElementById("recipe-seg");
    recipeSeg.querySelectorAll("button").forEach(b => b.addEventListener("click", () => {
      settings.recipeView = b.dataset.view;
      saveSettings();
      renderRecipes();
    }));

    // Leaving the editor with unsaved changes? Check first. v21.7: it can't answer instantly
    // any more (the question is in the app's own box), so it works like this: nothing to lose,
    // carries on straight away; otherwise it asks, and carries on only if you say yes.
    function whenOkToLeaveDraft(carryOn) {
      if (!recipeDraft || draftSnapshot(recipeDraft) === recipeDraft.original) { carryOn(); return; }
      askYesNo("Discard the changes to the recipe you're writing?", carryOn, { danger: true });
    }
    function draftSnapshot(d) { return JSON.stringify({ n: d.name, p: d.part, o: d.notes, s: d.steps }); }

    function openRecipe(id) {
      whenOkToLeaveDraft(() => {
        recipeDraft = null;
        openRecipeId = id;
        renderRecipes();
        showTab("recipes");
      });
    }

    // Jump to one unit on the Units tab, with its details open.
    function goToUnit(id) {
      clearFilters();
      openIds.clear();
      openIds.add(id);
      render();
      showTab("units");
      const card = list.querySelector(`li.unit[data-id="${id}"]`);
      if (card) card.scrollIntoView({ block: "center" });
    }

    // ----- The list of recipes -----
    function renderRecipeList() {
      const partsUsed = uniqueSorted(book.recipes.map(r => r.part));
      if (!partsUsed.includes(recipePartFilter)) recipePartFilter = "";
      fillSelect(partFilter, "parts", partsUsed, recipePartFilter);
      partFilter.classList.toggle("hidden", partsUsed.length < 2);

      renderCanPaintBox();
      recipeList.innerHTML = "";
      if (!book.recipes.length) {
        recipeList.innerHTML = '<li class="empty">No recipes yet. Press + New recipe to write down how you paint something, step by step.</li>';
      }
      const shown = book.recipes
        .filter(r => (!recipePartFilter || r.part === recipePartFilter) && (!recipeCanPaint || canPaintNow(r)))
        .sort((a, b) => a.name.localeCompare(b.name));
      for (const recipe of shown) {
        const item = document.createElement("li");
        const button = document.createElement("button");
        button.className = "recipe-item";
        const name = document.createElement("div");
        name.className = "name";
        name.textContent = recipe.name;
        const users = unitsUsing(recipe.id).length;
        const meta = document.createElement("div");
        meta.className = "meta";
        meta.textContent = [recipe.part, plural(recipe.steps.length, "step"),
                            users ? `used on ${plural(users, "unit")}` : ""].filter(Boolean).join(" · ");
        const swatches = document.createElement("div");
        swatches.className = "swatches";
        recipeColours(recipe).slice(0, 12).forEach(c => swatches.appendChild(makeSwatch(c)));
        button.append(name, meta, swatches);
        button.addEventListener("click", () => { openRecipeId = recipe.id; renderRecipes(); window.scrollTo(0, 0); });
        item.appendChild(button);
        recipeList.appendChild(item);
      }

      if (recipeCanPaint && !shown.length) {
        recipeList.insertAdjacentHTML("beforeend", '<li class="empty">No recipe where you own every paint yet. Mark your paints on Your Palette to see what you can paint now.</li>');
      }
      renderListChips("part-chips", "parts", "part");
      renderListChips("technique-chips", "techniques", "technique");
    }

    partFilter.addEventListener("change", () => { recipePartFilter = partFilter.value; renderRecipeList(); });
    document.getElementById("new-recipe").addEventListener("click", () => startNewRecipe(null));

    // The parts and techniques lists: ✕ to remove one, + to add one.
    function renderListChips(boxId, key, word) {
      const box = document.getElementById(boxId);
      box.innerHTML = "";
      for (const value of book[key]) {
        box.appendChild(makeChip(`${value}  ✕`, false, () => {
          if (book[key].length <= 1) { notify(`Keep at least one ${word}.`); return; }
          book[key] = book[key].filter(v => v !== value);
          render();
        }));
        box.lastChild.setAttribute("aria-label", `Remove ${value}`);
      }
      const add = document.createElement("button");
      add.className = "link-button";
      add.textContent = `+ Add ${word}`;
      add.addEventListener("click", () => {
        askText(`Name of the new ${word}:`, "", (answer) => {
          const typed = (answer || "").trim();
          if (typed && !book[key].some(v => sameText(v, typed))) { book[key].push(typed); render(); }
        });
      });
      box.appendChild(add);
    }

    // ----- Reading one recipe -----
    function renderRecipeView(recipe) {
      recipePage.innerHTML = "";
      const back = document.createElement("button");
      back.className = "link-button";
      back.textContent = settings.recipeView === "palette" ? "← Your Palette"
                       : settings.recipeView === "schemes" ? "← Schemes" : "← All recipes";
      back.addEventListener("click", () => { openRecipeId = null; renderRecipes(); });
      recipePage.appendChild(back);

      // Name, part and notes.
      const top = document.createElement("div");
      top.className = "card";
      const title = document.createElement("h2");
      title.textContent = recipe.name;
      title.style.fontSize = "20px";
      top.appendChild(title);
      if (recipe.part) {
        const tag = document.createElement("span");
        tag.className = "part-tag";
        tag.textContent = recipe.part;
        top.appendChild(tag);
      }
      if (recipe.notes.trim()) {
        const notes = document.createElement("p");
        notes.className = "recipe-notes";
        notes.textContent = recipe.notes;
        top.appendChild(notes);
      }
      recipePage.appendChild(top);

      // The steps, in order.
      const stepsCard = document.createElement("div");
      stepsCard.className = "card";
      stepsCard.innerHTML = "<h2>Steps</h2>";
      if (!recipe.steps.length) stepsCard.insertAdjacentHTML("beforeend", '<p class="hint" style="margin: 0;">No steps yet. Press Edit to add some.</p>');
      const steps = document.createElement("ol");
      steps.className = "recipe-steps";
      recipe.steps.forEach((step, i) => {
        const li = document.createElement("li");
        const head = document.createElement("div");
        head.className = "step-title";
        // v15: a blank technique shows the app's guess from the paints.
        const technique = step.technique || guessTechnique(step.paints.map(sp => paintById(sp.paint))) || "Step";
        head.textContent = `${i + 1}. ${technique} `;
        const coats = document.createElement("small");
        coats.textContent = `· ${coatsText(step.coats)}` + (step.ratio ? ` · mix ${step.ratio}` : "") +
                            (step.optional ? " · (optional)" : "");
        head.appendChild(coats);
        if (step.optional) li.classList.add("optional-step");
        li.appendChild(head);
        const mixed = step.paints.length > 1;
        for (const sp of step.paints) {
          const paint = paintById(sp.paint);
          if (!paint) continue;
          const line = document.createElement("div");
          line.className = "paint-line";
          const brand = document.createElement("span");
          brand.className = "brand";
          brand.textContent = paint.brand;
          line.append(makeSwatch(paint.colour), paint.name, brand);
          const badge = haveBadge(paint);   // v17
          if (badge) line.appendChild(badge);
          // Show the mix % when paints are mixed, or a single paint isn't 100% (e.g. thinned).
          if (sp.mix !== null && (mixed || sp.mix !== 100)) {
            const mix = document.createElement("span");
            mix.className = "mix";
            mix.textContent = `${sp.mix}%`;
            line.appendChild(mix);
          }
          li.appendChild(line);
        }
        if (step.note) {
          const note = document.createElement("p");
          note.className = "step-note";
          note.textContent = step.note;
          li.appendChild(note);
        }
        steps.appendChild(li);
      });
      stepsCard.appendChild(steps);
      recipePage.appendChild(stepsCard);

      // Used on: linked units, plus a menu to link more.
      const usedCard = document.createElement("div");
      usedCard.className = "card";
      usedCard.innerHTML = "<h2>Used on</h2>";
      const users = unitsUsing(recipe.id);
      if (users.length) {
        const linkedList = document.createElement("div");
        linkedList.className = "linked-list";
        linkedList.style.marginBottom = "10px";
        for (const unit of users) {
          const chip = document.createElement("button");
          chip.className = "recipe-chip";
          chip.append(displayName(unit));
          if (unit.faction) {
            const small = document.createElement("small");
            small.textContent = unit.faction;
            chip.appendChild(small);
          }
          chip.setAttribute("aria-label", `Go to ${displayName(unit)}`);
          chip.addEventListener("click", () => goToUnit(unit.id));
          linkedList.appendChild(linkedChip(chip, `Unlink ${displayName(unit)}`,
            () => { unlinkRecipe(unit, recipe.id); render(); }));
        }
        usedCard.appendChild(linkedList);
      } else {
        usedCard.insertAdjacentHTML("beforeend", '<p class="hint">Not linked to any units yet.</p>');
      }
      const others = models.filter(m => !users.includes(m)).sort((a, b) =>
        (a.faction || "").localeCompare(b.faction || "") || displayName(a).localeCompare(displayName(b)));
      if (others.length) {
        const picker = document.createElement("select");
        picker.style.width = "100%";
        picker.setAttribute("aria-label", "Link this recipe to a unit");
        picker.add(new Option("Add to a unit…", ""));
        for (const m of others) picker.add(new Option(m.faction ? `${displayName(m)} (${m.faction})` : displayName(m), m.id));
        picker.addEventListener("change", () => {
          const unit = models.find(m => m.id === Number(picker.value));
          if (unit) { linkRecipe(unit, recipe.id); render(); }
        });
        usedCard.appendChild(picker);
      }
      recipePage.appendChild(usedCard);

      // Edit, duplicate, delete.
      const buttons = document.createElement("div");
      buttons.className = "panel-buttons";
      const edit = document.createElement("button");
      edit.className = "primary-button";
      edit.style.padding = "11px 20px";
      edit.textContent = "Edit";
      edit.addEventListener("click", () => { startRecipeDraft(draftFrom(recipe)); });
      const copy = document.createElement("button");
      copy.className = "plain-button";
      copy.textContent = "Duplicate";
      copy.addEventListener("click", () => {
        const d = draftFrom(recipe);
        d.id = null;
        d.name = `${recipe.name} (copy)`;
        startRecipeDraft(d);
      });
      const del = document.createElement("button");
      del.className = "danger-button";
      del.textContent = "Delete";
      del.addEventListener("click", () => deleteRecipe(recipe.id));
      // v16: the recipe as text, in the format Paste recipes reads back.
      const asText = document.createElement("button");
      asText.className = "plain-button";
      asText.textContent = "Copy as text";
      asText.addEventListener("click", () => copyText(recipeToText(recipe), "Recipe"));
      buttons.append(edit, copy, asText, del);
      recipePage.appendChild(buttons);
    }

    function deleteRecipe(id) {
      const asked = recipeById(id);
      if (!asked) return;
      const usersNow = unitsUsing(id).length;
      const schemesNow = book.schemes.filter(s => s.recipes.includes(id)).length;
      const unlinkFrom = [usersNow ? plural(usersNow, "unit") : "",
                          schemesNow ? plural(schemesNow, "scheme") : ""].filter(Boolean).join(" and ");
      askYesNo(`Delete the recipe "${asked.name}"?` + (unlinkFrom ? ` It will be removed from ${unlinkFrom}.` : ""),
        () => deleteRecipeNow(id), { danger: true });
    }
    function deleteRecipeNow(id) {
      const recipe = recipeById(id);   // looked up again, in case it changed while the question was showing
      if (!recipe) return;
      const users = unitsUsing(id);
      const inSchemes = book.schemes.filter(s => s.recipes.includes(id));
      const before = JSON.parse(JSON.stringify(book));   // a copy, for Undo (schemes included)
      book.recipes = book.recipes.filter(r => r.id !== id);
      for (const s of inSchemes) s.recipes = s.recipes.filter(r => r !== id);
      users.forEach(m => unlinkRecipe(m, id));
      pruneUnusedPaints();
      openRecipeId = null;
      render();
      showToast(`Deleted ${recipe.name}`, () => {
        book = before;
        users.forEach(m => linkRecipe(m, id));
        render();
      });
    }

    // ----- Painting schemes -----
    // A scheme is a named group of recipes for one faction, e.g. "My Ultramarines" =
    // armour + trim + lenses + base. You can apply it to every unit in the faction at once,
    // and (if "auto" is on) new units added in that faction get its recipes automatically.
    // Schemes live in the recipe book (book.schemes), so they're saved and backed up with it.

    // The schemes for a faction (ignoring capitals and curly quotes).
    function schemesFor(faction) {
      return faction ? book.schemes.filter(s => sameText(s.faction, faction)) : [];
    }
    function schemeRecipes(scheme) { return scheme.recipes.map(recipeById).filter(Boolean); }
    function schemeUnits(scheme) {
      return scheme.faction ? models.filter(m => sameText(m.faction, scheme.faction)) : [];
    }
    // Units in the faction that are missing at least one of the scheme's recipes.
    function unitsMissing(scheme) {
      return schemeUnits(scheme).filter(m => scheme.recipes.some(id => !(m.recipes || []).includes(id)));
    }

    // Link a scheme's recipes to some units, with Undo. Recipes they already have stay.
    function applyScheme(scheme, units) {
      if (!units.length || !scheme.recipes.length) return;
      const before = units.map(m => [m, m.recipes ? m.recipes.slice() : null]);
      for (const m of units) for (const id of scheme.recipes) linkRecipe(m, id);
      render();
      showToast(`${scheme.name} applied to ${plural(units.length, "unit")}`, () => {
        for (const [m, recipes] of before) { if (recipes) m.recipes = recipes; else delete m.recipes; }
        render();
      });
    }

    const schemeHome = document.getElementById("scheme-home");
    const schemePage = document.getElementById("scheme-page");
    const schemeListEl = document.getElementById("scheme-list");

    function renderSchemes() {
      schemeHome.classList.toggle("hidden", !!schemeDraft);
      schemePage.classList.toggle("hidden", !schemeDraft);
      if (schemeDraft) { renderSchemeEditor(); return; }

      schemeListEl.innerHTML = "";
      if (!book.schemes.length) {
        const empty = document.createElement("li");
        empty.className = "empty";
        empty.textContent = "No schemes yet. A scheme groups the recipes you use for one faction " +
          "(armour, trim, lenses, base…). Apply it to the whole faction at once, and new units in that faction get it automatically.";
        schemeListEl.appendChild(empty);
        return;
      }
      const sorted = book.schemes.slice().sort((a, b) => a.faction.localeCompare(b.faction) || a.name.localeCompare(b.name));
      for (const scheme of sorted) {
        const item = document.createElement("li");
        const card = document.createElement("div");
        card.className = "recipe-item scheme-item";
        const colour = factionColour(scheme.faction);
        if (colour) { card.classList.add("has-faction"); setFactionStyle(card, colour); }

        const name = document.createElement("div");
        name.className = "name";
        name.textContent = scheme.name;

        const meta = document.createElement("div");
        meta.className = "meta";
        if (colour) { const dot = makeSwatch(colour); dot.classList.add("faction-dot"); meta.appendChild(dot); }
        const recipes = schemeRecipes(scheme);
        meta.append([scheme.faction, plural(recipes.length, "recipe"), scheme.auto ? "new units get it" : ""]
          .filter(Boolean).join(" · "));

        const chips = document.createElement("div");
        chips.className = "recipe-links";
        for (const recipe of recipes) chips.appendChild(recipeChip(recipe, () => openRecipe(recipe.id)));

        // How many of the faction's units have the whole scheme.
        const units = schemeUnits(scheme);
        const missing = unitsMissing(scheme);
        const status = document.createElement("div");
        status.className = "meta";
        status.textContent = !units.length ? `No ${scheme.faction} units yet.`
          : !recipes.length ? "Add some recipes to this scheme."
          : !missing.length ? (units.length === 1 ? `The 1 unit in ${scheme.faction} has it.` : `All ${units.length} units in ${scheme.faction} have it.`)
          : `${units.length - missing.length} of ${plural(units.length, "unit")} in ${scheme.faction} have it.`;

        const buttons = document.createElement("div");
        buttons.className = "scheme-buttons";
        if (missing.length && recipes.length) {
          const apply = document.createElement("button");
          apply.className = "primary-button";
          apply.textContent = `Apply to ${plural(missing.length, "unit")}`;
          apply.setAttribute("aria-label", `Apply ${scheme.name} to ${plural(missing.length, "unit")} in ${scheme.faction}`);
          apply.addEventListener("click", () => applyScheme(scheme, missing));
          buttons.appendChild(apply);
        }
        const edit = document.createElement("button");
        edit.className = "plain-button";
        edit.textContent = "Edit";
        edit.setAttribute("aria-label", `Edit ${scheme.name}`);
        edit.addEventListener("click", () => startScheme(scheme));
        buttons.appendChild(edit);
        if (recipes.length) {   // v16
          const asText = document.createElement("button");
          asText.className = "plain-button";
          asText.textContent = "Copy as text";
          asText.setAttribute("aria-label", `Copy ${scheme.name} as text`);
          asText.addEventListener("click", () => copyText(schemeToText(scheme), "Scheme"));
          buttons.appendChild(asText);
        }

        card.append(name, meta, chips, status, buttons);
        item.appendChild(card);
        schemeListEl.appendChild(item);
      }
    }

    // Open the scheme editor: a COPY is edited, and nothing changes until Save.
    function startScheme(scheme, faction) {
      schemeDraft = scheme
        ? { id: scheme.id, name: scheme.name, faction: scheme.faction, auto: scheme.auto, recipes: scheme.recipes.slice() }
        : { id: null, name: "", faction: faction || "", auto: true, recipes: [] };
      schemeDraft.original = schemeSnapshot(schemeDraft);
      settings.recipeView = "schemes";
      saveSettings();
      openRecipeId = null;
      renderRecipes();
      showTab("recipes");
    }
    function schemeSnapshot(d) { return JSON.stringify([d.name, d.faction, d.auto, d.recipes]); }
    function closeScheme(askFirst) {
      const leave = () => {
        schemeDraft = null;
        renderRecipes();
        window.scrollTo(0, 0);
      };
      if (askFirst && schemeDraft && schemeSnapshot(schemeDraft) !== schemeDraft.original) {
        askYesNo("Discard the changes to this scheme?", leave, { danger: true });
        return;
      }
      leave();
    }
    document.getElementById("new-scheme").addEventListener("click", () => startScheme(null));

    function renderSchemeEditor() {
      const d = schemeDraft;
      schemePage.innerHTML = "";
      const back = document.createElement("button");
      back.className = "link-button";
      back.textContent = "← Schemes";
      back.addEventListener("click", () => closeScheme(true));
      schemePage.appendChild(back);

      // Name, faction and the "new units get it" switch.
      const top = document.createElement("div");
      top.className = "card scheme-form";
      const title = document.createElement("h2");
      title.textContent = d.id === null ? "New scheme" : "Edit scheme";
      const nameLabel = document.createElement("label");
      nameLabel.textContent = "Scheme name";
      const nameBox = document.createElement("input");
      nameBox.placeholder = "e.g. My Ultramarines";
      nameBox.value = d.name;
      nameBox.addEventListener("input", () => { d.name = nameBox.value; });
      nameLabel.appendChild(nameBox);

      const factionLabel = document.createElement("label");
      factionLabel.textContent = "Faction";
      const factionBox = document.createElement("input");
      factionBox.placeholder = "e.g. Ultramarines";
      factionBox.setAttribute("list", "faction-options");   // suggests your existing factions
      factionBox.value = d.faction;
      const factionNote = document.createElement("p");
      factionNote.className = "hint";
      const updateNote = () => {
        const n = d.faction.trim() ? models.filter(m => sameText(m.faction, d.faction)).length : 0;
        factionNote.textContent = !d.faction.trim() ? "Which faction is this scheme for?"
          : n ? `${plural(n, "unit")} in this faction.` : "No units in this faction yet. New ones can get this scheme.";
      };
      factionBox.addEventListener("input", () => { d.faction = factionBox.value; updateNote(); });
      updateNote();
      factionLabel.appendChild(factionBox);

      const autoLabel = document.createElement("label");
      autoLabel.className = "check-label";
      const autoBox = document.createElement("input");
      autoBox.type = "checkbox";
      autoBox.checked = d.auto;
      autoBox.addEventListener("change", () => { d.auto = autoBox.checked; });
      autoLabel.append(autoBox, "New units added in this faction get these recipes automatically");

      top.append(title, nameLabel, factionLabel, factionNote, autoLabel);
      schemePage.appendChild(top);

      // The recipes: tick the ones in this scheme.
      const pick = document.createElement("div");
      pick.className = "card";
      const pickTitle = document.createElement("h2");
      pickTitle.textContent = "Recipes in this scheme";
      pick.appendChild(pickTitle);
      if (!book.recipes.length) {
        const none = document.createElement("p");
        none.className = "hint";
        none.textContent = "You haven't written any recipes yet. Save this scheme, write some recipes, then come back and tick them.";
        pick.appendChild(none);
      } else {
        const listEl = document.createElement("ul");
        listEl.className = "scheme-recipe-list";
        const byPart = book.recipes.slice().sort((a, b) =>
          (a.part || "~").localeCompare(b.part || "~") || a.name.localeCompare(b.name));
        for (const recipe of byPart) {
          const row = document.createElement("li");
          const label = document.createElement("label");
          label.className = "check-label";
          const box = document.createElement("input");
          box.type = "checkbox";
          box.checked = d.recipes.includes(recipe.id);
          box.addEventListener("change", () => {
            d.recipes = box.checked ? [...d.recipes, recipe.id] : d.recipes.filter(id => id !== recipe.id);
          });
          const colours = recipeColours(recipe);
          label.append(box);
          if (colours.length) label.append(makeSwatch(colours[0]));
          const text = document.createElement("span");
          text.className = "scheme-recipe-name";
          text.textContent = recipe.name;
          label.append(text);
          if (recipe.part) {
            const part = document.createElement("small");
            part.textContent = recipe.part;
            label.append(part);
          }
          row.appendChild(label);
          listEl.appendChild(row);
        }
        pick.appendChild(listEl);
      }
      schemePage.appendChild(pick);

      const buttons = document.createElement("div");
      buttons.className = "settings-actions";
      const saveButton = document.createElement("button");
      saveButton.className = "primary-button";
      saveButton.style.flex = "1";
      saveButton.textContent = "Save scheme";
      saveButton.addEventListener("click", saveScheme);
      const cancel = document.createElement("button");
      cancel.className = "plain-button";
      cancel.textContent = "Cancel";
      cancel.addEventListener("click", () => closeScheme(true));
      buttons.append(saveButton, cancel);
      if (d.id !== null) {
        const del = document.createElement("button");
        del.className = "danger-button";
        del.textContent = "Delete";
        del.addEventListener("click", () => deleteScheme(d.id));
        buttons.appendChild(del);
      }
      schemePage.appendChild(buttons);
    }

    function saveScheme() {
      const d = schemeDraft;
      const name = d.name.trim();
      let faction = d.faction.trim();
      if (!name) { notify("Give the scheme a name."); return; }
      if (!faction) { notify("Pick the faction this scheme is for."); return; }
      // Match the spelling your units already use, so "ultramarines" finds "Ultramarines".
      const existing = models.find(m => sameText(m.faction, faction));
      if (existing) faction = existing.faction;
      let scheme = d.id === null ? null : book.schemes.find(s => s.id === d.id);
      if (!scheme) {
        scheme = { id: Math.max(0, ...book.schemes.map(s => s.id)) + 1 };
        book.schemes.push(scheme);
      }
      Object.assign(scheme, { name, faction, auto: d.auto, recipes: d.recipes.filter(id => recipeById(id)) });
      schemeDraft = null;
      // Offer to apply it straight away to units that don't have it all yet.
      // v18c-3: commit() only says Saved (and offers Apply) if the save worked.
      const missing = unitsMissing(scheme);
      if (missing.length && scheme.recipes.length) {
        commit(`Saved ${name}`, () => applyScheme(scheme, missing), `Apply to ${plural(missing.length, "unit")}`, 8);
      } else {
        commit(`Saved ${name}`);
      }
      window.scrollTo(0, 0);
    }

    // Deleting a scheme doesn't touch the recipes or the units' links: those stay.
    function deleteScheme(id) {
      const asked = book.schemes.find(s => s.id === id);
      if (!asked) return;
      askYesNo(`Delete the scheme "${asked.name}"? Its recipes, and the units they're linked to, stay as they are.`,
        () => deleteSchemeNow(id), { danger: true });
    }
    function deleteSchemeNow(id) {
      const scheme = book.schemes.find(s => s.id === id);   // looked up again, in case the book changed meanwhile
      if (!scheme) return;
      const index = book.schemes.indexOf(scheme);
      book.schemes.splice(index, 1);
      schemeDraft = null;
      render();
      showToast(`Deleted ${scheme.name}`, () => { book.schemes.splice(index, 0, scheme); render(); });
    }

    // ----- Your Palette -----
    // Every paint used in your recipes, once each. Built automatically: there's nothing to
    // add by hand. Editing a paint here changes it in every recipe, because recipes point
    // at the paint rather than keeping their own copy.

    const paletteView = document.getElementById("palette-view");
    const paintListEl = document.getElementById("paint-list");
    const paintSort = document.getElementById("paint-sort");
    const brandChips = document.getElementById("brand-chips");
    const paletteSummary = document.getElementById("palette-summary");
    let paletteBrand = null;           // null = all brands, "" = paints with no brand
    const openPaintIds = new Set();    // paints with their details open
    if (!["colour", "name", "brand"].includes(settings.paintSort)) settings.paintSort = "colour";

    // Turns "#1e3a8a" into hue (0-360, round the colour wheel), saturation and lightness (0-1).
    function hexToHsl(hex) {
      const [r, g, b] = [1, 3, 5].map(i => parseInt(hex.slice(i, i + 2), 16) / 255);
      const max = Math.max(r, g, b), min = Math.min(r, g, b);
      const l = (max + min) / 2;
      if (max === min) return { h: 0, s: 0, l };
      const d = max - min;
      const s = l > 0.5 ? d / (2 - max - min) : d / (max + min);
      let h = max === r ? (g - b) / d + (g < b ? 6 : 0) : max === g ? (b - r) / d + 2 : (r - g) / d + 4;
      return { h: h * 60, s, l };
    }

    // Sorting by colour: round the colour wheel (reds, oranges, yellows, greens, blues,
    // purples), light to dark within each band. Then greys, blacks and whites, light to dark.
    // Paints still on the untouched grey go last, since their colour isn't known yet.
    function colourOrder(a, b) {
      const key = (paint) => {
        if (paint.colour === DEFAULT_PAINT_COLOUR) return [2, 0, 0];
        const { h, s, l } = hexToHsl(paint.colour);
        if (s < 0.15 || l < 0.08 || l > 0.95) return [1, -l, 0];   // greys and metallics-ish
        return [0, Math.floor(((h + 10) % 360) / 25), -l];            // 25° bands, reds first
      };
      const ka = key(a), kb = key(b);
      for (let i = 0; i < 3; i++) if (ka[i] !== kb[i]) return ka[i] - kb[i];
      return a.name.localeCompare(b.name);
    }

    function recipesUsingPaint(paintId) {
      return book.recipes.filter(r => r.steps.some(s => s.paints.some(sp => sp.paint === paintId)));
    }

    function renderPalette() {
      const paints = book.paints;
      paintSort.value = settings.paintSort;
      renderPaletteSearch();   // v17
      renderImportReview();    // v17.1
      renderShopPanel();

      // Brand chips: one for each brand, tap again to show all.
      const brands = uniqueSorted(paints.map(p => p.brand));
      const noBrand = paints.some(p => !p.brand);
      if (paletteBrand !== null && !(brands.includes(paletteBrand) || (paletteBrand === "" && noBrand))) paletteBrand = null;
      brandChips.innerHTML = "";
      brandChips.classList.toggle("hidden", brands.length + (noBrand ? 1 : 0) < 2);
      brandChips.appendChild(makeChip("All brands", paletteBrand === null, () => { paletteBrand = null; renderPalette(); }));
      for (const brand of [...brands, ...(noBrand ? [""] : [])]) {
        brandChips.appendChild(makeChip(brand || "No brand", paletteBrand === brand,
          () => { paletteBrand = paletteBrand === brand ? null : brand; renderPalette(); }));
      }

      const shown = paints.filter(p => (paletteBrand === null || p.brand === paletteBrand) &&
                                       (!importReviewIds || importReviewIds.includes(p.id)));
      const sorters = {
        colour: (a, b) => (isMaterial(a) - isMaterial(b)) || colourOrder(a, b),   // v15: materials last
        name: (a, b) => a.name.localeCompare(b.name),
        brand: (a, b) => (a.brand || "￿").localeCompare(b.brand || "￿") || a.name.localeCompare(b.name),
      };
      shown.sort(sorters[settings.paintSort]);

      const unset = paints.filter(p => p.colour === DEFAULT_PAINT_COLOUR && !isMaterial(p)).length;
      paletteSummary.textContent = paints.length
        ? `${plural(paints.length, "paint")} from ${plural(brands.length, "brand")}` +
          (paletteBrand !== null ? ` · showing ${shown.length}` : "") +
          (unset ? ` · ${unset} still need${unset === 1 ? "s" : ""} a colour (tap to set it)` : "")
        : "";

      paintListEl.innerHTML = "";
      if (!paints.length) {
        paintListEl.innerHTML = '<li class="empty">Your palette fills itself in from your recipes. Add paints to a recipe and they appear here.</li>';
        return;
      }
      for (const paint of shown) paintListEl.appendChild(buildPaintItem(paint));
    }

    function buildPaintItem(paint) {
      const item = document.createElement("li");
      item.className = "paint-item";
      const isOpen = openPaintIds.has(paint.id);
      const usedIn = recipesUsingPaint(paint.id);

      const head = document.createElement("button");
      head.className = "paint-head";
      head.setAttribute("aria-expanded", isOpen);
      const swatch = makeSwatch(paint.colour);
      swatch.classList.add("big");
      const text = document.createElement("span");
      text.className = "paint-text";
      const name = document.createElement("span");
      name.className = "name";
      name.textContent = paint.name;
      const meta = document.createElement("span");
      meta.className = "details";
      meta.textContent = [paint.brand || "No brand", `in ${plural(usedIn.length, "recipe")}`,
                          paintQty(paint) > 1 ? `× ${paintQty(paint)} in stock` : "",
                          isMaterial(paint) ? "basing material" :
                          paint.colour === DEFAULT_PAINT_COLOUR ? "colour not set" : ""].filter(Boolean).join(" · ");
      text.append(name, meta);
      const pill = statusPill(paint);   // v17
      if (pill) text.appendChild(pill);
      head.append(swatch, text);
      head.addEventListener("click", () => {
        if (openPaintIds.has(paint.id)) openPaintIds.delete(paint.id); else openPaintIds.add(paint.id);
        renderPalette();
      });
      item.appendChild(head);
      if (!isOpen) return item;

      // Details: change the colour, name or brand (everywhere), and the recipes it's in.
      const panel = document.createElement("div");
      panel.className = "panel";
      const row = document.createElement("div");
      row.className = "paint-edit-row";
      const colour = document.createElement("input");
      colour.type = "color";
      colour.value = paint.colour;
      colour.setAttribute("aria-label", `Colour of ${paint.name}`);
      colour.addEventListener("input", () => swatch.style.setProperty("--swatch", colour.value));
      colour.addEventListener("change", () => { paint.colour = colour.value.toLowerCase(); render(); });
      const nameBox = document.createElement("input");
      nameBox.value = paint.name;
      nameBox.setAttribute("aria-label", "Paint name");
      nameBox.addEventListener("change", () => editPaint(paint, "name", nameBox.value));
      const brandBox = document.createElement("input");
      brandBox.value = paint.brand;
      brandBox.placeholder = "Brand";
      brandBox.setAttribute("aria-label", "Brand");
      brandBox.setAttribute("list", "palette-brand-options");
      brandBox.addEventListener("change", () => editPaint(paint, "brand", brandBox.value));
      const brandList = document.createElement("datalist");
      brandList.id = "palette-brand-options";
      for (const b of uniqueSorted([...COMMON_BRANDS, ...book.paints.map(p => p.brand)])) brandList.appendChild(new Option(b));
      row.append(colour, nameBox, brandBox, brandList);
      panel.appendChild(row);
      panel.insertAdjacentHTML("beforeend", '<p class="hint" style="margin: 0;">Changes here apply in every recipe that uses this paint.</p>');
      panel.appendChild(buildStatusRow(paint));   // v17

      const field = document.createElement("div");
      field.className = "panel-field";
      field.append("Used in");
      const chips = document.createElement("div");
      chips.className = "linked-list";
      for (const r of usedIn) chips.appendChild(recipeChip(r, () => openRecipe(r.id)));
      field.appendChild(chips);
      panel.appendChild(field);
      panel.appendChild(buildPaintActions(paint, usedIn));   // v18c-2
      item.appendChild(panel);
      return item;
    }

    // Rename a paint or change its brand. If that makes it the same as another paint
    // you have, offer to merge the two, so it's only in your palette once.
    function editPaint(paint, field, value) {
      value = field === "brand" ? tidyBrand(value) : value.trim();   // v18c
      if (field === "name" && !value) { renderPalette(); return; }
      if (paint[field] === value) return;
      const old = paint[field];
      paint[field] = value;
      const wasExample = paint.example === true;
      delete paint.example;   // v24: you've changed it, so it's yours now (put back below if a merge question is refused)
      const twin = book.paints.find(p => p !== paint && sameText(p.name, paint.name) && sameText(p.brand, paint.brand));
      if (twin) {
        // v21.7: the paint goes back to how it was while the question is showing (a typo you
        // merge away is remembered as shorthand, and "No" leaves it untouched). Then it asks.
        paint[field] = old;
        if (wasExample) paint.example = true;
        askYesNo(`You already have ${twin.brand ? twin.brand + " " : ""}${twin.name}. Merge the two into one paint?`, () => {
          if (!book.paints.includes(paint) || !book.paints.includes(twin)) { renderPalette(); return; }   // changed meanwhile
          joinPaints(paint, twin);
          commit(`Merged into ${twin.name}`);   // v18c-3
        }, { onNo: renderPalette });
        return;
      }
      commit(`Saved ${paint.name}`);   // v18c-3
    }

    // ================= v18c-2: REMOVE AND MERGE PAINTS =================
    // Folds paint "from" into paint "into": every recipe step that used "from" uses "into",
    // and "from" leaves your palette. "into" keeps its own details; it only takes the status,
    // colour or material type from "from" where it had none. The old name is remembered, so
    // pasting it again finds "into" straight away.
    function joinPaints(from, into) {
      for (const r of book.recipes) for (const s of r.steps) for (const sp of s.paints) if (sp.paint === from.id) sp.paint = into.id;
      if (!paintStatus(into) && paintStatus(from)) {
        for (const k of ["status", "owned", "spare", "qty"]) if (k in from) into[k] = from[k];
      }
      if (into.colour === DEFAULT_PAINT_COLOUR && from.colour !== DEFAULT_PAINT_COLOUR) into.colour = from.colour;
      if (from.type && !into.type) into.type = from.type;
      repointShorthand(from, into);
      rememberShorthand(from.name, into);
      book.paints = book.paints.filter(p => p !== from);
      openPaintIds.delete(from.id);
      openPaintIds.add(into.id);
      if (importReviewIds) importReviewIds = importReviewIds.filter(id => id !== from.id);
    }

    // Remembered shorthand that pointed at "from" now points at "into" (or is forgotten, with no "into").
    function repointShorthand(from, into) {
      const out = {};
      for (const [k, v] of Object.entries(book.shorthand || {})) {
        if (!(sameText(v.name, from.name) && sameText(v.brand, from.brand))) out[k] = v;
        else if (into) out[k] = { brand: into.brand || "", name: into.name };
      }
      book.shorthand = out;
    }

    // "Merge into…": pick the paint this one is a copy of. Undo puts everything back.
    function mergePaintInto(from, into) {
      if (!from || !into || from === into) return;
      const before = JSON.stringify(book);
      joinPaints(from, into);
      commit(`Merged ${from.name} into ${into.name}`, () => { book = cleanRecipeBook(JSON.parse(before)); render(); });   // v18c-3
    }

    // "Remove": only for a paint no recipe uses. Undo puts it back.
    function removePaint(paint) {
      if (!paint || recipesUsingPaint(paint.id).length) return;
      const before = JSON.stringify(book);
      book.paints = book.paints.filter(p => p !== paint);
      repointShorthand(paint, null);
      openPaintIds.delete(paint.id);
      if (importReviewIds) importReviewIds = importReviewIds.filter(id => id !== paint.id);
      commit(`Removed ${paint.name}`, () => { book = cleanRecipeBook(JSON.parse(before)); render(); });   // v18c-3
    }

    // The Remove and Merge into… buttons at the bottom of an open paint.
    function buildPaintActions(paint, usedIn) {
      const wrap = document.createElement("div");
      wrap.className = "panel-field paint-actions";
      const buttons = document.createElement("div");
      buttons.className = "panel-buttons";

      const others = book.paints.filter(p => p !== paint)
        .sort((a, b) => a.name.localeCompare(b.name) || (a.brand || "").localeCompare(b.brand || ""));
      const mergeBox = document.createElement("div");
      mergeBox.className = "merge-box hidden";
      if (others.length) {
        const merge = document.createElement("button");
        merge.className = "plain-button";
        merge.textContent = "Merge into…";
        buttons.appendChild(merge);

        const label = document.createElement("label");
        label.textContent = `A misspelt copy? Pick the right paint. Recipes using ${paint.name} will use that one instead.`;
        const pick = document.createElement("select");
        pick.className = "merge-pick";
        pick.setAttribute("aria-label", `Merge ${paint.name} into`);
        pick.appendChild(new Option("Choose a paint…", ""));
        label.appendChild(pick);
        // The list of paints is only built when you tap Merge into… (a paste import opens
        // every new paint at once, and each one carrying the whole list would be a lot).
        merge.addEventListener("click", () => {
          if (pick.options.length === 1) {
            for (const p of others) pick.appendChild(new Option(p.brand ? `${p.name} (${p.brand})` : p.name, String(p.id)));
          }
          mergeBox.classList.toggle("hidden");
          if (!mergeBox.classList.contains("hidden")) pick.focus();
        });
        const go = document.createElement("button");
        go.className = "primary-button merge-go";
        go.textContent = "Merge";
        go.disabled = true;
        pick.addEventListener("change", () => { go.disabled = !pick.value; });
        go.addEventListener("click", () => mergePaintInto(paint, paintById(Number(pick.value))));
        mergeBox.append(label, go);
      }

      if (!usedIn.length) {
        const remove = document.createElement("button");
        remove.className = "danger-button";
        remove.textContent = "Remove";
        remove.setAttribute("aria-label", `Remove ${paint.name} from your palette`);
        remove.addEventListener("click", () => removePaint(paint));
        buttons.appendChild(remove);
      }
      wrap.appendChild(buttons);
      if (usedIn.length) {
        const hint = document.createElement("p");
        hint.className = "hint";
        hint.style.margin = "0";
        hint.textContent = "Only paints in no recipes can be removed.";
        wrap.appendChild(hint);
      }
      wrap.appendChild(mergeBox);
      return wrap;
    }

    paintSort.addEventListener("change", () => { settings.paintSort = paintSort.value; saveSettings(); renderPalette(); });

    // ----- Writing or editing a recipe -----
    // You edit a DRAFT copy, where each paint is written out in full (brand, name, colour).
    // Nothing changes until Save, which turns the paints back into ids in the paint list.
    function blankPaint(mix) { return { brand: "", name: "", colour: DEFAULT_PAINT_COLOUR, mix }; }
    // v15: a new step's technique starts blank, meaning "guess it from the paints".
    function blankStep() { return { technique: "", coats: 1, paints: [blankPaint(100)], ratio: "", note: "", optional: false }; }

    function draftFrom(recipe) {
      return {
        id: recipe.id, name: recipe.name, part: recipe.part, notes: recipe.notes, linkUnit: null,
        steps: recipe.steps.map(s => ({
          technique: s.technique, coats: s.coats, ratio: s.ratio || "", note: s.note || "", optional: !!s.optional,
          paints: s.paints.map(sp => {
            const p = paintById(sp.paint) || { brand: "", name: "", colour: DEFAULT_PAINT_COLOUR };
            return { brand: p.brand, name: p.name, colour: p.colour, mix: sp.mix, type: p.type };
          }),
        })),
      };
    }

    function startRecipeDraft(draft) {
      if (draftWaiting("recipe")) return;   // v26: a kept unfinished recipe is offered first
      // (a recipe brought back by Keep going already knows what "unchanged" means)
      if (typeof draft.original !== "string") draft.original = draftSnapshot(draft);
      recipeDraft = draft;
      renderRecipes();
      window.scrollTo(0, 0);
    }

    // linkUnit: the unit to link it to when saved (when started from a unit), or null.
    function startNewRecipe(linkUnit) {
      whenOkToLeaveDraft(() => {
        openRecipeId = null;
        startRecipeDraft({ id: null, name: "", part: recipePartFilter, notes: "", linkUnit, steps: [blankStep()] });
        showTab("recipes");
        const nameBox = recipePage.querySelector("input");
        if (nameBox) nameBox.focus();
      });
    }

    // A dropdown of a list (parts or techniques) with "＋ Add a new…" at the bottom.
    function pickOrAdd(key, word, current, placeholder, onPick) {
      const select = document.createElement("select");
      if (placeholder) select.add(new Option(placeholder, ""));
      const values = book[key].slice();
      if (current && !values.includes(current)) values.push(current);   // e.g. one you've since removed
      for (const v of values) select.add(new Option(v, v));
      select.add(new Option(`＋ Add a new ${word}…`, "\u0000new"));
      select.value = current || "";
      select.addEventListener("change", () => {
        if (select.value !== "\u0000new") { onPick(select.value); return; }
        askText(`Name of the new ${word}:`, "", (answer) => {
          const typed = (answer || "").trim();
          if (typed) {
            const existing = book[key].find(v => sameText(v, typed));
            if (!existing) { book[key].push(typed); save(); }
            onPick(existing || typed);
          }
          renderRecipeEditor();   // also on Cancel: puts the menu back to what it was
        });
      });
      return select;
    }

    // Puts the cursor in a box after the editor is redrawn (e.g. a newly added paint).
    let focusAfterRender = null;

    function renderRecipeEditor() {
      const d = recipeDraft;
      recipePage.innerHTML = "";

      // Suggestions for the brand and paint boxes.
      const brands = document.createElement("datalist");
      brands.id = "brand-options";
      for (const b of uniqueSorted([...COMMON_BRANDS, ...book.paints.map(p => p.brand)])) brands.appendChild(new Option(b));
      const paintNames = document.createElement("datalist");
      paintNames.id = "paint-options";
      const suggest = [...book.paints, ...KNOWN_PAINTS.filter(k => !book.paints.some(p => sameText(p.name, k.name)))];
      for (const p of suggest.sort((a, b) => a.name.localeCompare(b.name))) {
        const o = document.createElement("option");
        o.value = p.name;
        o.label = p.brand;
        paintNames.appendChild(o);
      }
      recipePage.append(brands, paintNames);

      const card = document.createElement("div");
      card.className = "card form-grid";
      const heading = document.createElement("h2");
      heading.style.margin = "0";
      heading.textContent = d.id === null ? "New recipe" : "Edit recipe";
      card.appendChild(heading);

      const field = (text, control) => {
        const label = document.createElement("label");
        label.append(text, control);
        return label;
      };
      const nameBox = document.createElement("input");
      nameBox.placeholder = "e.g. Ultramarine blue armour";
      nameBox.value = d.name;
      nameBox.addEventListener("input", () => { d.name = nameBox.value; });
      card.appendChild(field("Recipe name", nameBox));
      card.appendChild(field("Part it's for", pickOrAdd("parts", "part", d.part, "Choose a part…", v => { d.part = v; })));
      const notes = document.createElement("textarea");
      notes.placeholder = "Optional: tips, brushes, what to watch out for";
      notes.value = d.notes;
      notes.addEventListener("input", () => { d.notes = notes.value; });
      card.appendChild(field("Notes", notes));
      if (d.linkUnit) {
        const unit = models.find(m => m.id === d.linkUnit);
        if (unit) {
          const note = document.createElement("p");
          note.className = "hint";
          note.style.margin = "0";
          note.textContent = `Will be linked to ${displayName(unit)} when saved.`;
          card.appendChild(note);
        }
      }
      recipePage.appendChild(card);

      // The steps.
      const stepsCard = document.createElement("div");
      stepsCard.className = "card form-grid";
      stepsCard.innerHTML = '<h2 style="margin: 0;">Steps</h2>';
      const stepList = document.createElement("ol");
      stepList.className = "step-edits";
      d.steps.forEach((step, si) => stepList.appendChild(buildStepEditor(d, step, si)));
      stepsCard.appendChild(stepList);
      const addStep = document.createElement("button");
      addStep.className = "plain-button";
      addStep.textContent = "+ Add step";
      addStep.addEventListener("click", () => {
        d.steps.push(blankStep());
        focusAfterRender = `step-${d.steps.length - 1}-paint-0`;
        renderRecipeEditor();
      });
      stepsCard.appendChild(addStep);
      recipePage.appendChild(stepsCard);

      // v28: "Colour ideas" (Pro preview): 3 paint ideas that go with a colour in this recipe.
      recipeIdeasCard = (typeof MinifolioColour !== "undefined") ? buildColourIdeasCard(d) : null;
      if (recipeIdeasCard) recipePage.appendChild(recipeIdeasCard);

      // v18c: paints that are new to your palette: "Do you own these?" (All to start with).
      d.own = d.own || newOwnChoice();
      recipeOwnCard = buildOwnCard(d.own, () => draftNewPaints(d));
      recipeOwnCard.id = "recipe-own";
      recipePage.appendChild(recipeOwnCard);

      const actions = document.createElement("div");
      actions.className = "settings-actions";
      actions.style.marginTop = "0";
      const saveButton = document.createElement("button");
      saveButton.className = "primary-button";
      saveButton.style.flex = "1";
      saveButton.textContent = "Save recipe";
      saveButton.addEventListener("click", saveRecipeDraft);
      const cancel = document.createElement("button");
      cancel.className = "plain-button";
      cancel.textContent = "Cancel";
      cancel.addEventListener("click", () => {
        whenOkToLeaveDraft(() => {
          if (d.id !== null) openRecipeId = d.id;
          recipeDraft = null;
          renderRecipes();
          window.scrollTo(0, 0);
        });
      });
      actions.append(saveButton, cancel);
      recipePage.appendChild(actions);

      if (focusAfterRender) {
        const box = recipePage.querySelector(`[data-key="${focusAfterRender}"]`);
        if (box) box.focus();
        focusAfterRender = null;
      }
    }

    function buildStepEditor(d, step, si) {
      const li = document.createElement("li");
      li.className = "step-edit";

      const iconButton = (text, label, disabled, onClick, extraClass) => {
        const b = document.createElement("button");
        b.className = "icon-button" + (extraClass ? " " + extraClass : "");
        b.textContent = text;
        b.setAttribute("aria-label", label);
        b.disabled = disabled;
        b.addEventListener("click", onClick);
        return b;
      };
      const move = (offset) => {
        [d.steps[si], d.steps[si + offset]] = [d.steps[si + offset], d.steps[si]];
        renderRecipeEditor();
      };
      const head = document.createElement("div");
      head.className = "step-head";
      const label = document.createElement("strong");
      label.textContent = `Step ${si + 1}`;
      head.append(label,
        iconButton("↑", `Move step ${si + 1} up`, si === 0, () => move(-1)),
        iconButton("↓", `Move step ${si + 1} down`, si === d.steps.length - 1, () => move(+1)),
        iconButton("✕", `Remove step ${si + 1}`, false, () => {
          const hasPaints = step.paints.some(p => p.name.trim());
          const remove = () => { d.steps.splice(si, 1); renderRecipeEditor(); };
          if (hasPaints) askYesNo(`Remove step ${si + 1}?`, remove, { danger: true });
          else remove();
        }, "remove"));
      li.appendChild(head);

      // Technique and number of coats.
      const row = document.createElement("div");
      row.className = "row";
      const techLabel = document.createElement("label");
      // v15: the blank choice is "Auto", which shows the guess from this step's paints.
      const autoText = () => { const g = guessTechnique(step.paints); return g ? `Auto: ${g}` : "Auto (from the paints)"; };
      const techSelect = pickOrAdd("techniques", "technique", step.technique, autoText(), v => { step.technique = v; });
      const refreshAuto = () => { techSelect.options[0].text = autoText(); };
      techLabel.append("Technique", techSelect);
      const coatsLabel = document.createElement("label");
      const coats = document.createElement("input");
      coats.type = "number";
      coats.min = 1;
      coats.value = step.coats;
      coats.addEventListener("input", () => { step.coats = cleanCount(coats.value); });
      coatsLabel.append("Coats", coats);
      row.append(techLabel, coatsLabel);
      li.appendChild(row);

      // v15: a short note on how to do the step, and an "optional" tick.
      const extra = document.createElement("div");
      extra.className = "row step-extra";
      const noteLabel = document.createElement("label");
      const note = document.createElement("input");
      note.placeholder = "e.g. heavier on the top";
      note.value = step.note || "";
      note.addEventListener("input", () => { step.note = note.value; });
      noteLabel.append("Note (if any)", note);
      const optLabel = document.createElement("label");
      optLabel.className = "check-label";
      const opt = document.createElement("input");
      opt.type = "checkbox";
      opt.checked = !!step.optional;
      opt.addEventListener("change", () => { step.optional = opt.checked; });
      optLabel.append(opt, "Optional");
      extra.append(noteLabel, optLabel);
      li.appendChild(extra);

      // The paints in this step.
      const warning = document.createElement("p");
      warning.className = "mix-warning";
      const updateWarning = () => {
        const n = step.paints.length;
        const badRatio = n > 1 && step.ratio && step.ratio.trim() && !ratioPercents(step.ratio, n);
        warning.textContent = badRatio
          ? `The ratio needs ${n} numbers, one per paint, like ${Array(n).fill(1).join(":")}.`
          : mixWarning(step.paints);
        warning.classList.toggle("hidden", !warning.textContent);
        refreshAuto();
      };
      const mixInputs = [];
      let ratioBox = null;
      const mixTyped = () => { step.ratio = ""; if (ratioBox) ratioBox.value = ""; };
      step.paints.forEach((paint, pi) => li.appendChild(buildPaintEditor(step, paint, si, pi, updateWarning, mixInputs, mixTyped)));

      // v15: mixing? Type a ratio like 2:1 and the %s are worked out for you.
      if (step.paints.length > 1) {
        const ratioLabel = document.createElement("label");
        ratioBox = document.createElement("input");
        ratioBox.placeholder = `e.g. ${step.paints.length === 2 ? "2:1" : "1:1:2"}`;
        ratioBox.setAttribute("aria-label", "Mix ratio");
        ratioBox.value = step.ratio || "";
        ratioBox.addEventListener("input", () => {
          step.ratio = ratioBox.value;
          const pcs = ratioPercents(ratioBox.value, step.paints.length);
          if (pcs) pcs.forEach((v, i) => { step.paints[i].mix = v; if (mixInputs[i]) mixInputs[i].value = v; });
          updateWarning();
        });
        ratioLabel.append("Mix ratio, paints in the order above (or set each %)", ratioBox);
        li.appendChild(ratioLabel);
      }
      updateWarning();
      li.appendChild(warning);

      const addPaint = document.createElement("button");
      addPaint.className = "link-button";
      addPaint.style.justifySelf = "start";
      addPaint.style.padding = "4px 0";
      addPaint.style.minHeight = "44px";   // v21: was 25 px tall, too small for a fingertip
      addPaint.textContent = step.paints.length ? "+ Mix in another paint" : "+ Add paint";
      addPaint.addEventListener("click", () => {
        const even = isEvenSplit(step.paints);
        step.paints.push(blankPaint(null));
        if (even) resplit(step.paints);
        focusAfterRender = `step-${si}-paint-${step.paints.length - 1}`;
        renderRecipeEditor();
      });
      li.appendChild(addPaint);
      return li;
    }

    function buildPaintEditor(step, paint, si, pi, updateWarning, mixInputs, mixTyped) {
      const box = document.createElement("div");
      box.className = "paint-edit";

      const colour = document.createElement("input");
      colour.type = "color";
      colour.value = paint.colour;
      colour.setAttribute("aria-label", "Paint colour");
      colour.title = "Tap to pick roughly what this paint looks like";
      colour.addEventListener("input", () => { paint.colour = colour.value; });

      const name = document.createElement("input");
      name.className = "paint-name";
      name.placeholder = "Paint, e.g. Macragge Blue";
      name.setAttribute("aria-label", "Paint name");
      name.setAttribute("list", "paint-options");
      name.dataset.key = `step-${si}-paint-${pi}`;
      name.value = paint.name;

      const brand = document.createElement("input");
      brand.className = "paint-brand";
      brand.placeholder = "Brand";
      brand.setAttribute("aria-label", "Brand");
      brand.setAttribute("list", "brand-options");
      brand.value = paint.brand;
      // v18c: when the app fills in the brand for you, tapping the box selects that text,
      // so typing "Citadel" replaces it instead of making "CitadelCitadel".
      let autoBrand = "";      // the brand the app filled in, until you type in the box
      let selectOnTap = false;
      const selectAutoBrand = () => {
        if (!autoBrand || brand.value !== autoBrand) return;
        brand.select();
        selectOnTap = true;
      };
      brand.addEventListener("focus", () => setTimeout(() => { if (document.activeElement === brand) selectAutoBrand(); }, 0));
      // A tap would otherwise move the cursor and undo the selection.
      brand.addEventListener("mouseup", (e) => { if (selectOnTap) { e.preventDefault(); selectOnTap = false; } });
      brand.addEventListener("input", () => { autoBrand = ""; selectOnTap = false; paint.brand = brand.value; updateWarning(); refreshRecipeOwn(); });
      // Leaving the box: a brand typed twice is put back to once.
      brand.addEventListener("change", () => {
        const tidy = tidyBrand(brand.value);
        if (tidy !== brand.value) { brand.value = tidy; paint.brand = tidy; updateWarning(); refreshRecipeOwn(); }
      });

      name.addEventListener("input", () => { paint.name = name.value; updateWarning(); refreshRecipeOwn(); });
      // A paint you've used before: fill in its brand and colour for you.
      name.addEventListener("change", () => {
        const known = book.paints.find(p => sameText(p.name, paint.name) && (!paint.brand.trim() || sameText(p.brand, paint.brand)))
                   || KNOWN_PAINTS.find(p => sameText(p.name, paint.name));
        if (!known) return;
        if (!paint.brand.trim() && known.brand) {
          paint.brand = known.brand;
          brand.value = known.brand;
          autoBrand = known.brand;
          if (document.activeElement === brand) selectAutoBrand();
        }
        if (paint.colour === DEFAULT_PAINT_COLOUR) { paint.colour = known.colour; colour.value = known.colour; }
        refreshRecipeOwn();
      });

      const mixBox = document.createElement("span");
      mixBox.className = "mix-box";
      const mix = document.createElement("input");
      mix.type = "number";
      mix.min = 0;
      mix.max = 100;
      mix.placeholder = "Mix";
      mix.setAttribute("aria-label", "Mix %");
      mix.value = paint.mix === null ? "" : paint.mix;
      mix.addEventListener("input", () => { paint.mix = cleanMix(mix.value); if (mixTyped) mixTyped(); updateWarning(); });
      if (mixInputs) mixInputs[pi] = mix;
      mixBox.append(mix, "%");

      const remove = document.createElement("button");
      remove.className = "icon-button remove";
      remove.textContent = "✕";
      remove.setAttribute("aria-label", `Remove ${paint.name || "this paint"}`);
      remove.addEventListener("click", () => {
        const even = isEvenSplit(step.paints);
        step.paints.splice(pi, 1);
        if (even && step.paints.length) resplit(step.paints);
        renderRecipeEditor();
      });

      box.append(colour, name, brand, mixBox, remove);
      return box;
    }

    function saveRecipeDraft() {
      const d = recipeDraft;
      const name = d.name.trim();
      if (!name) { notify("Give the recipe a name first."); return; }
      // Paints with no name are skipped. Each named paint is found (or added) in the paint list.
      // v18c: a paint new to your palette gets your "Do you own these?" answer (Owned to start with).
      const steps = d.steps.map(s => {
        const paints = s.paints.filter(p => p.name.trim())
          .map(p => {
            const fresh = { brand: tidyBrand(p.brand), name: p.name.trim() };
            const known = isInPalette(fresh);
            const paint = findOrAddPaint(p.brand, p.name, p.colour);
            if (!known && paintStatus(paint) === "") applyPaintStatus(paint, ownsNewPaint(d.own, fresh) ? "owned" : "notowned");
            return { paint: paint.id, mix: cleanMix(p.mix) };
          });
        return {
          technique: s.technique.trim(),
          coats: cleanCount(s.coats),
          paints,
          ratio: paints.length > 1 && ratioPercents(s.ratio, paints.length) ? cleanRatio(s.ratio) : "",   // v15
          note: String(s.note || "").trim(),   // v15
          optional: !!s.optional,              // v15
        };
      });
      let recipe = d.id !== null ? recipeById(d.id) : null;
      if (recipe) {
        Object.assign(recipe, { name, part: d.part.trim(), notes: d.notes, steps });
        delete recipe.example;   // v24: you've changed it, so it's yours now
      } else {
        recipe = { id: Math.max(0, ...book.recipes.map(r => r.id)) + 1, name, part: d.part.trim(), notes: d.notes, steps };
        book.recipes.push(recipe);
      }
      if (d.linkUnit) {
        const unit = models.find(m => m.id === d.linkUnit);
        if (unit) linkRecipe(unit, recipe.id);
      }
      pruneUnusedPaints();
      recipeDraft = null;
      openRecipeId = recipe.id;
      commit(`Saved ${name}`);   // v18c-3: only says Saved if it was
      window.scrollTo(0, 0);
    }


    // ================= v28: "COLOUR IDEAS" (Pro preview) =================
    // In the recipe editor: pick a colour from the recipe (or "Whole model", the recipe's main colour), say what
    // you're painting, and see 3 paint ideas, each with a plain-English reason. Tap one to add it as a new step.
    // All the colour maths lives in colour.js (MinifolioColour). This part only decides which ideas to ask for and
    // draws them. It works offline and sends nothing anywhere. Paint names and brands are always shown as plain
    // text (never as HTML), because they can be anything the user typed or pasted.
    let recipeIdeasCard = null;   // the card in the recipe editor, if it's open
    let colourIdeasState = { open: false, base: "whole", role: "glow", check: false };   // kept while the app is open
    // Is a finger (or mouse button) down right now? The panel never redraws itself under a press: typing a paint
    // name and then tapping a chip makes the paint box "change" (it fills in the colour) in the middle of that tap,
    // and a redraw there would replace the chip before the tap finished, so the tap would be lost.
    let colourIdeasPressing = false;
    for (const [name, down] of [["pointerdown", true], ["pointerup", false], ["pointercancel", false]]) {
      document.addEventListener(name, () => { colourIdeasPressing = down; }, true);
    }

    // What each role asks for. "boost" lifts a too-dull idea (dark blue armour's opposite is a muddy brown,
    // which makes poor eyes): s = least colour strength, l = lightest and darkest allowed.
    // v29: "tip" is hand-written advice for the role, shown when the role is chosen. "why" holds role-specific reasons
    // that replace the generic reason on an idea where they say it better (the key is the idea's relation to the colour:
    // complementary, split, analogous, triad, accent, dark, mid, light). {Fam} / {fam} is the idea's colour word and {base}
    // the chosen colour's word, both from colourFamily. Paint and recipe names never go into a reason.
    const COLOUR_ROLES = [
      { key: "glow",   label: "Eyes or glow", note: "eyes or glow", boost: { s: 0.85, l: [0.55, 0.65] }, picks: ["complementary", "split0", "split1"],
        tip: "Keep eyes and glow the brightest, most saturated spot on the model. A small bright spot pulls the eye straight to it.",
        why: { complementary: "{Fam} is the opposite of {base}, so eyes in it stand out the most.",
               split: "{Fam} is almost opposite {base}. Eyes still stand out, with a softer feel.",
               accent: "Your colour is neutral, so {fam} eyes or glow stand out without clashing." } },
      { key: "trim",   label: "Trim",         note: "trim",         boost: { s: 0.5,  l: [0.5, 0.7] },   picks: ["complementary", "analogous0", "light"],
        tip: "Use one trim colour all over the model so it looks planned. Trim looks best a little lighter or brighter than the armour next to it.",
        why: { complementary: "{Fam} is the opposite of {base}, so trim in it gives a bold, clear edge.",
               analogous: "{Fam} sits next to {base} on the colour wheel, so trim in it looks neat and calm.",
               light: "A pale trim lifts the edges of {base} and makes the shapes easy to read.",
               accent: "Your colour is neutral, so {fam} trim adds interest without clashing." } },
      { key: "gems",   label: "Gems",         note: "gems",         boost: { s: 0.75, l: [0.4, 0.55] },  picks: ["triad0", "triad1", "complementary"],
        tip: "Gems are small, so make them bold. A tiny light dot on one side makes them look shiny.",
        why: { triad: "{Fam} is spaced evenly round the colour wheel from {base}, so gems in it are rich but don't clash.",
               complementary: "{Fam} is the opposite of {base}, so gems in it pop as small bright spots.",
               accent: "Your colour is neutral, so {fam} gems stand out without clashing." } },
      { key: "weapon", label: "Weapon",       note: "weapon",       boost: { s: 0.3,  l: [0.35, 0.6] },  picks: ["mid", "dark", "analogous1"],
        tip: "Keep the weapon calmer than the eyes and face, so the eye goes to them first. Dark or mid tones work well.",
        why: { mid: "A mid grey keeps the weapon calm next to {base}, so the eyes and face stay the focus.",
               dark: "A dark neutral keeps the weapon quiet next to {base}.",
               analogous: "{Fam} sits next to {base} on the colour wheel, so the weapon matches the rest of the model." } },
      { key: "cloth",  label: "Cloth",        note: "cloth",        boost: { s: 0.35, l: [0.25, 0.5] },  picks: ["analogous0", "analogous1", "triad0"],
        tip: "Cloth looks best in a colour next to your main one. Keep it a little darker or duller than the armour so it doesn't compete.",
        why: { analogous: "{Fam} cloth sits next to {base} on the colour wheel, so it looks calm and matches.",
               triad: "{Fam} is spaced evenly round the colour wheel from {base}: lively cloth that doesn't clash." } },
      { key: "base",   label: "Base",         note: "base",         boost: { s: 0.2,  l: [0.2, 0.4] },   picks: ["dark", "mid", "analogous0"],
        tip: "Keep the base darker and duller than the model, so the model stands out. Earth and grey tones rarely clash.",
        why: { dark: "A dark neutral base lets {base} on the model stand out.",
               mid: "A mid grey base is neutral, so it won't pull the eye away from {base}.",
               analogous: "{Fam} sits next to {base} on the colour wheel, so the base feels part of the model." } },
    ];
    // If the chosen colour is grey, black or white, "opposite" means nothing, so these accents are offered instead.
    const NEUTRAL_ACCENT_HUES = [25, 195, 330];   // orange, cyan, pink

    function colourIdeaIsReal(hex) {
      return MinifolioColour.isHex(hex) && String(hex).toLowerCase() !== DEFAULT_PAINT_COLOUR;
    }

    // The distinct paints written in the recipe being edited, with how many steps use each.
    function colourIdeaBases(d) {
      const seen = new Map();
      for (const s of d.steps) for (const p of s.paints) {
        const name = String(p.name || "").trim();
        if (!name) continue;
        const brand = tidyBrand(p.brand);   // "CitadelCitadel" (typed over the filled-in brand) shows as "Citadel"
        const key = sameKey(brand) + "|" + sameKey(name);
        const entry = seen.get(key) || { key, name, brand, colour: p.colour, uses: 0 };
        entry.uses++;
        if (!colourIdeaIsReal(entry.colour) && colourIdeaIsReal(p.colour)) entry.colour = p.colour;
        seen.set(key, entry);
      }
      return [...seen.values()];
    }

    // The main colour of a list of { colour, uses }: the one used in the most steps (the first on a tie). Colourful paints
    // win over black, white and grey ones, so a black primer doesn't make the main colour "black".
    function colourIdeaMainColour(entries) {
      let best = null, bestColourful = null;
      for (const e of entries) {
        if (!colourIdeaIsReal(e.colour)) continue;
        const h = MinifolioColour.harmonies(e.colour);
        if (h && h.hueMeaningful && (!bestColourful || e.uses > bestColourful.uses)) bestColourful = e;
        if (!best || e.uses > best.uses) best = e;
      }
      return bestColourful || best;
    }

    // "Whole model": your recipes filed under the Whole model part (priming, base coats, all-over steps), each with its
    // main colour. Recipes linked to the same unit as the one being edited come first. The recipe being edited is left out.
    function colourIdeaWholeRecipes(d) {
      const mine = new Set([...(d.linkUnit ? [d.linkUnit] : []), ...(d.id !== null ? unitsUsing(d.id).map(m => m.id) : [])]);
      const out = [];
      for (const r of book.recipes) {
        if (!sameText(r.part, WHOLE_MODEL) || (d.id !== null && r.id === d.id)) continue;
        const counts = new Map();
        for (const st of r.steps) for (const sp of st.paints) {
          const paint = paintById(sp.paint);
          if (!paint) continue;
          const e = counts.get(paint.id) || { colour: paint.colour, uses: 0 };
          e.uses++;
          counts.set(paint.id, e);
        }
        const main = colourIdeaMainColour([...counts.values()]);
        if (main) out.push({ id: r.id, name: r.name, colour: main.colour, linked: unitsUsing(r.id).some(m => mine.has(m.id)) });
      }
      return out.sort((a, b) => (b.linked ? 1 : 0) - (a.linked ? 1 : 0));   // stable: otherwise your own order
    }

    // Every paint we may suggest: your palette first, then the built-in list for paints you don't have yet.
    function colourIdeaPool() {
      const have = new Set(book.paints.map(p => sameKey(p.name)));
      return [...book.paints, ...KNOWN_PAINTS.filter(k => !have.has(sameKey(k.name)))];
    }

    // The colour an idea is aiming for, before we look for the nearest paint.
    function colourIdeaWanted(harmony, role, pick, hueSlot) {
      const C = MinifolioColour;
      if (pick === "dark" || pick === "mid" || pick === "light") {
        return { hex: harmony.neutrals[{ dark: 0, mid: 1, light: 2 }[pick]], relation: pick };
      }
      let hex, relation;
      if (!harmony.hueMeaningful) {
        hex = C.hslToHex(NEUTRAL_ACCENT_HUES[hueSlot % NEUTRAL_ACCENT_HUES.length], 0.8, 0.5);
        relation = "accent";
      } else {
        hex = { complementary: harmony.complementary, split0: harmony.split[0], split1: harmony.split[1],
                triad0: harmony.triad[0], triad1: harmony.triad[1],
                analogous0: harmony.analogous[0], analogous1: harmony.analogous[1] }[pick];
        relation = pick.replace(/\d$/, "");
      }
      const hsl = C.hexToHsl(hex);
      const s = Math.max(hsl.s, role.boost.s);
      const l = Math.min(role.boost.l[1], Math.max(role.boost.l[0], hsl.l));
      return { hex: C.hslToHex(hsl.h, s, l), relation };
    }

    // One short, plain sentence saying why the idea works. v29: where the role has its own wording for this
    // relation (COLOUR_ROLES[].why) that is used; otherwise the general sentence below.
    function colourIdeaReason(relation, wantedHex, baseHex, role) {
      const C = MinifolioColour;
      const cap = (t) => t.charAt(0).toUpperCase() + t.slice(1);
      const fam = C.colourFamily(wantedHex) || "this colour";
      const baseFam = C.colourFamily(baseHex) || "your colour";
      const own = role && role.why && role.why[relation];
      if (own) return own.replace(/\{(Fam|fam|base)\}/g, (m, key) => key === "Fam" ? cap(fam) : key === "fam" ? fam : baseFam);
      switch (relation) {
        case "complementary": return `${cap(fam)} is the opposite of ${baseFam} on the colour wheel, so it stands out the most.`;
        case "split": return `${cap(fam)} is nearly opposite ${baseFam}. It still stands out, but looks less harsh than the straight opposite.`;
        case "analogous": return `${cap(fam)} sits right next to ${baseFam} on the colour wheel, so it blends in calmly.`;
        case "triad": return `${cap(fam)} is spaced evenly round the colour wheel from ${baseFam}: lively, but it doesn't clash.`;
        case "accent": return `Your colour is neutral, so a ${fam} accent stands out without clashing.`;
        case "dark": return `A dark neutral stays quietly in the background next to ${baseFam}.`;
        case "mid": return `A mid grey sits comfortably beside ${baseFam} without competing with it.`;
        default: return `A pale neutral gives ${baseFam} a clean, light edge.`;
      }
    }

    // Up to 3 ideas for a base colour and a role. Each is { wanted, relation, hit } where hit is a nearestPaints result.
    function colourIdeas(d, baseHex, role) {
      const C = MinifolioColour;
      const harmony = C.harmonies(baseHex);
      if (!harmony) return [];
      const pool = colourIdeaPool();
      const skip = [baseHex];
      for (const s of d.steps) for (const p of s.paints) if (MinifolioColour.isHex(p.colour)) skip.push(p.colour);
      const out = [];
      let slot = 0;
      for (const pick of role.picks) {
        const wanted = colourIdeaWanted(harmony, role, pick, slot);
        if (!["dark", "mid", "light"].includes(pick)) slot++;
        // Paints you own come first, and the same paint is never suggested twice.
        const hit = C.nearestPaints(wanted.hex, pool, { limit: 1, ownedFirst: true, exclude: [...skip, ...out.map(o => o.hit.paint.colour)] })[0];
        if (hit) out.push({ wanted: wanted.hex, relation: wanted.relation, hit });
      }
      return out;
    }

    // The words under a suggestion that say how far to trust the match.
    function colourIdeaTag(hit) {
      if (!hit.owned) return { cls: "none", text: "Not in your palette" };
      return hit.quality === "good" ? { cls: "own", text: "You own this" } : { cls: "near", text: "Closest you own" };
    }
    function colourIdeaNote(hit) {
      if (hit.quality === "poor") return "Not very close. It is the nearest we found.";
      if (hit.quality === "close") return "Similar, not exact.";
      if (hit.approximate) return "Close enough. This kind of paint looks different on the model than in the pot.";
      return "";
    }

    // Adds the idea to the recipe being edited as a new last step.
    function addColourIdeaStep(d, paint, role) {
      d.steps.push({
        technique: "", coats: 1, ratio: "", optional: false, note: `Colour idea for ${role.note}`,
        paints: [{ brand: String(paint.brand || ""), name: String(paint.name || ""), colour: paint.colour, mix: 100 }],
      });
      colourIdeasState.open = true;
      renderRecipeEditor();
      notify(`Added step ${d.steps.length}: ${paint.name}`);
    }

    // ---- v29: "Does this scheme hang together?" ----
    // A rule-of-thumb check of the colours in the recipe being edited. The maths is MinifolioColour.schemeCheck; this
    // part only turns its answer into short, plain sentences. They are fixed sentences filled in with colour words
    // only (never paint or recipe names), and they always say it is only a guide.
    function colourWordList(words) {
      return words.length < 2 ? (words[0] || "") : words.slice(0, -1).join(", ") + " and " + words[words.length - 1];
    }
    const SCHEME_NEEDS_TWO = "Add at least two paints with different colours set (the round colour button in a step), then this check can run.";
    const SCHEME_ONLY_A_GUIDE = "This is only a guide, not a rule. Plenty of good schemes break these tips, and colours on a screen look different from real paint.";

    // The answer as { verdict, rows: [{ cls, tag, label, text }] }. cls matches the idea tags: own (fine), near (look at this), none (suggestion).
    function schemeCheckWords(r) {
      const cap = (t) => t.charAt(0).toUpperCase() + t.slice(1);
      const rows = [];
      const n = r.strong.length;
      const names = colourWordList(r.strong.map(s => s.family));
      if (r.tooManyStrong) {
        rows.push({ cls: "near", tag: "Look at this", label: "Strong colours", text: `You have ${n}: ${names}. That many strong colours fight for attention, so the eye has nowhere to rest.` });
      } else if (n === 0) {
        rows.push({ cls: "own", tag: "Fine", label: "Strong colours", text: "None. Your colours are calm and muted, which keeps things tidy." });
      } else {
        rows.push({ cls: "own", tag: "Fine", label: "Strong colours", text: `${n} (${names}). That is a good number.` });
      }
      rows.push(r.flat
        ? { cls: "near", tag: "Look at this", label: "Light and dark", text: "Your colours are all about the same lightness, so the model may look flat. Add a darker shade or a lighter highlight." }
        : { cls: "own", tag: "Fine", label: "Light and dark", text: "Your darkest and lightest colours are far enough apart for the model to have depth." });
      if (r.focus && r.focusKind === "only") {
        rows.push({ cls: "none", tag: "Suggestion", label: "Focus colour", text: `${cap(r.focus.family)} is your only strong colour, so it is already the star. Keep the rest calmer.` });
      } else if (r.focus) {
        rows.push({ cls: "none", tag: "Suggestion", label: "Focus colour", text: `Let ${r.focus.family} be the star. It stands out most against your main colour, ${r.dominant.family}. Use it in small areas and keep the other strong colours darker or duller.` });
      } else {
        rows.push({ cls: "none", tag: "Suggestion", label: "Focus colour", text: "Your colours are all calm. For one spot to stand out, make a small area (like the eyes) a stronger colour. The ideas above can suggest one." });
      }
      const problems = (r.tooManyStrong ? 1 : 0) + (r.flat ? 1 : 0);
      const verdict = problems === 0 ? "Yes, this looks like it hangs together."
        : problems === 1 ? "Nearly. One thing to look at." : "Not quite yet. Two things to look at.";
      return { verdict, rows };
    }

    // The check's part of the panel: a title, a button, and (once the button is pressed) the answer.
    function buildSchemeCheck(bases, onToggle) {
      const box = document.createElement("div");
      box.className = "scheme-check";
      box.id = "scheme-check";
      const title = document.createElement("h3");
      title.className = "scheme-title";
      title.textContent = "Does this scheme hang together?";
      const toggle = document.createElement("button");
      toggle.type = "button";
      toggle.className = "plain-button";
      toggle.id = "scheme-check-toggle";
      toggle.textContent = colourIdeasState.check ? "Hide the check" : "Check this recipe";
      toggle.setAttribute("aria-expanded", colourIdeasState.check ? "true" : "false");
      toggle.setAttribute("aria-controls", "scheme-result");
      toggle.addEventListener("click", onToggle);
      box.append(title, toggle);
      if (!colourIdeasState.check) return box;

      const result = document.createElement("div");
      result.className = "scheme-result";
      result.id = "scheme-result";
      const entries = bases.filter(b => colourIdeaIsReal(b.colour)).map(b => ({ colour: b.colour, uses: b.uses }));
      const answer = MinifolioColour.schemeCheck(entries);
      if (!answer.enough) {
        const need = document.createElement("p");
        need.className = "hint";
        need.textContent = SCHEME_NEEDS_TWO;
        result.appendChild(need);
      } else {
        const words = schemeCheckWords(answer);
        const verdict = document.createElement("p");
        verdict.className = "scheme-verdict";
        verdict.textContent = words.verdict;
        const list = document.createElement("ul");
        list.className = "scheme-list";
        for (const row of words.rows) {
          const li = document.createElement("li");
          const tag = document.createElement("span");
          tag.className = "idea-tag " + row.cls;
          tag.textContent = row.tag;
          const what = document.createElement("span");
          what.className = "scheme-what";
          const label = document.createElement("strong");
          label.textContent = row.label + ": ";
          what.append(label, row.text);
          li.append(tag, what);
          list.appendChild(li);
        }
        result.append(verdict, list);
        const left = bases.length - entries.length;
        if (left > 0) {
          const skipped = document.createElement("p");
          skipped.className = "hint";
          skipped.textContent = `${left} ${left === 1 ? "paint has" : "paints have"} no colour set, so ${left === 1 ? "it was" : "they were"} left out.`;
          result.appendChild(skipped);
        }
      }
      const guide = document.createElement("p");
      guide.className = "hint";
      guide.textContent = SCHEME_ONLY_A_GUIDE;
      result.appendChild(guide);
      box.appendChild(result);
      return box;
    }

    function buildColourIdeasCard(d) {
      const card = document.createElement("details");
      card.className = "card colour-ideas";
      card.id = "colour-ideas";
      card.open = colourIdeasState.open;
      const summary = document.createElement("summary");
      const title = document.createElement("h2");
      title.textContent = "Colour ideas";
      const pill = document.createElement("span");
      pill.className = "pro-pill";
      pill.textContent = "Pro preview";
      summary.append(title, pill);
      const body = document.createElement("div");
      body.className = "ideas-body";
      card.append(summary, body);

      let lastLook = "";
      let focusNext = "";
      const draw = () => {
        const bases = colourIdeaBases(d);
        const ownMain = colourIdeaMainColour(bases);
        const ownIsWhole = sameText(d.part, WHOLE_MODEL);   // writing the Whole model recipe itself: use its own colours
        const wholeRecipes = ownIsWhole ? [] : colourIdeaWholeRecipes(d);
        const auto = wholeRecipes[0] || null;               // what "Whole model" means right now
        const choice = colourIdeasState.base;
        let base = null, baseHint = "";
        if (choice.startsWith("wm:")) base = wholeRecipes.find(r => "wm:" + r.id === choice) || null;
        else if (choice !== "whole") base = bases.find(b => b.key === choice) || null;
        if (!base) {
          colourIdeasState.base = "whole";
          base = auto || ownMain;
        }
        if (wholeRecipes.includes(base)) baseHint = `Using the main colour of \u201c${base.name}\u201d.`;
        if (colourIdeasState.base === "whole" && wholeRecipes.length > 1 && !wholeRecipes[0].linked) {
          baseHint += " You have several Whole model recipes: pick the one for this model.";
        }
        const role = COLOUR_ROLES.find(r => r.key === colourIdeasState.role) || COLOUR_ROLES[0];
        const look = JSON.stringify([colourIdeasState.base, role.key, bases.map(b => [b.key, b.colour, b.uses]),
                                     wholeRecipes.map(r => [r.id, r.name, r.colour, r.linked]), ownIsWhole, colourIdeasState.check]);
        if (look === lastLook && !focusNext) return;   // nothing changed: leave it alone
        lastLook = look;
        body.innerHTML = "";

        const hint = document.createElement("p");
        hint.className = "hint";
        hint.textContent = "Pick a colour from this recipe and what you are painting. You get 3 paints that go with it. Tap one to add it as a new step.";
        body.appendChild(hint);

        if (!base) {
          const empty = document.createElement("p");
          empty.className = "hint";
          empty.textContent = bases.length
            ? "Set a colour on one of the paints first (the round colour button in a step), then ideas show here."
            : "Add a paint to a step first (or write a Whole model recipe). Ideas show here once there is a colour to start from.";
          body.appendChild(empty);
          return;
        }

        const pick = document.createElement("label");
        pick.append("Start from");
        const select = document.createElement("select");
        select.style.width = "100%";
        select.id = "colour-ideas-base";
        select.add(new Option(auto ? `Whole model: ${auto.name}` : "Whole model: none yet, using this recipe", "whole"));
        if (wholeRecipes.length > 1) {
          const group = document.createElement("optgroup");
          group.label = "Other Whole model recipes";
          for (const r of wholeRecipes.slice(1)) group.appendChild(new Option(r.name, "wm:" + r.id));
          select.appendChild(group);
        }
        if (bases.length) {
          const group = document.createElement("optgroup");
          group.label = "Paints in this recipe";
          for (const b of bases) group.appendChild(new Option(b.brand ? `${b.name} (${b.brand})` : b.name, b.key));
          select.appendChild(group);
        }
        select.value = colourIdeasState.base;
        select.addEventListener("change", () => { colourIdeasState.base = select.value; focusNext = "#colour-ideas-base"; draw(); });
        pick.appendChild(select);
        body.appendChild(pick);

        const roleLabel = document.createElement("p");
        roleLabel.className = "idea-label";
        roleLabel.textContent = "What are you painting?";
        const chips = document.createElement("div");
        chips.className = "chips";
        chips.style.marginTop = "0";
        for (const r of COLOUR_ROLES) {
          const chip = makeChip(r.label, r.key === role.key, () => { colourIdeasState.role = r.key; focusNext = `[data-role="${r.key}"]`; draw(); });
          chip.dataset.role = r.key;
          chips.appendChild(chip);
        }
        body.append(roleLabel, chips);

        // v29: hand-written advice for the chosen role
        const tip = document.createElement("p");
        tip.className = "role-tip";
        tip.id = "colour-ideas-tip";
        const tipLabel = document.createElement("strong");
        tipLabel.textContent = "Tip: ";
        tip.append(tipLabel, role.tip);
        body.appendChild(tip);

        const baseHex = base.colour;
        if (baseHint) {
          const using = document.createElement("p");
          using.className = "hint";
          using.id = "colour-ideas-using";
          using.textContent = baseHint;
          body.appendChild(using);
        }
        if (!colourIdeaIsReal(baseHex)) {
          const unset = document.createElement("p");
          unset.className = "hint";
          unset.textContent = "This paint's colour isn't set yet, so it counts as neutral. Tap its round colour button in the step to set it.";
          body.appendChild(unset);
        }

        const ideas = colourIdeas(d, baseHex, role);
        if (!ideas.length) {
          const none = document.createElement("p");
          none.className = "hint";
          none.textContent = "No paints with a known colour to suggest yet. Add paints on Your Palette first.";
          body.appendChild(none);
        }
        const list = document.createElement("ul");
        list.className = "idea-list";
        for (const idea of ideas) {
          const paint = idea.hit.paint;
          const tag = colourIdeaTag(idea.hit);
          const reason = colourIdeaReason(idea.relation, idea.wanted, baseHex, role);
          const note = colourIdeaNote(idea.hit);
          const li = document.createElement("li");
          const button = document.createElement("button");
          button.type = "button";
          button.className = "idea";
          button.setAttribute("aria-label", `Add ${paint.name} as a new step. ${tag.text}. ${reason}`);
          const text = document.createElement("span");
          text.className = "idea-text";
          const name = document.createElement("span");
          name.className = "idea-name";
          name.append(paint.name);
          if (paint.brand) {
            const brand = document.createElement("small");
            brand.textContent = paint.brand;
            name.appendChild(brand);
          }
          const tagEl = document.createElement("span");
          tagEl.className = "idea-tag " + tag.cls;
          tagEl.textContent = tag.text;
          const why = document.createElement("span");
          why.className = "idea-why";
          why.textContent = reason;
          text.append(name, tagEl, why);
          if (note) {
            const noteEl = document.createElement("span");
            noteEl.className = "idea-note";
            noteEl.textContent = note;
            text.appendChild(noteEl);
          }
          const add = document.createElement("span");
          add.className = "idea-add";
          add.textContent = "+ Add as a step";
          text.appendChild(add);
          button.append(makeSwatch(paint.colour), text);
          button.addEventListener("click", () => addColourIdeaStep(d, paint, role));
          li.appendChild(button);
          list.appendChild(li);
        }
        body.appendChild(list);

        // v29: "Does this scheme hang together?" (skipped if an older colour.js without schemeCheck is somehow loaded)
        if (typeof MinifolioColour.schemeCheck === "function") {
          body.appendChild(buildSchemeCheck(bases, () => {
            colourIdeasState.check = !colourIdeasState.check;
            focusNext = "#scheme-check-toggle";
            draw();
          }));
        }

        const foot = document.createElement("p");
        foot.className = "hint";
        foot.textContent = "Ideas use paints you own first. Colours on a screen are only a guide, so check them on your model. Nothing leaves your phone.";
        body.appendChild(foot);

        if (focusNext) {
          const target = body.querySelector(focusNext);
          if (target) target.focus();
          focusNext = "";
        }
      };

      card.addEventListener("toggle", () => { colourIdeasState.open = card.open; if (card.open) draw(); });
      // Typing in a paint box asks for a refresh on every key. Wait a moment (and for any press to finish), then redraw once.
      let refreshTimer = null;
      card.refresh = () => {
        if (!card.open) return;
        clearTimeout(refreshTimer);
        const later = () => {
          if (!card.isConnected) return;
          if (colourIdeasPressing) { refreshTimer = setTimeout(later, 120); return; }
          draw();
        };
        refreshTimer = setTimeout(later, 200);
      };
      if (card.open) draw();
      return card;
    }

    // ================= v18c: TIDY BRANDS AND "DO YOU OWN THESE?" =================
    // The brand box used to fill itself in, so typing "Citadel" gave "CitadelCitadel".
    // This puts a brand typed twice (or more) back to once: "CitadelCitadel" or "Citadel citadel" → "Citadel".
    // Only repeats of 3 letters or more count, so short brands are left alone.
    function tidyBrand(brand) {
      const b = String(brand || "").trim().replace(/\s+/g, " ");
      const twice = b.match(/^(.{3,}?)(?:\s*\1)+$/i);
      return twice ? twice[1].trim() : b;
    }

    // Is this paint ({ brand, name }) already in your palette? No brand = any brand counts.
    function isInPalette(p) {
      const brand = tidyBrand(p.brand);
      return book.paints.some(x => sameText(x.name, p.name) && (!brand || sameText(x.brand, brand)));
    }

    // Your answer to "Do you own these?" for the paints about to be added.
    // mode: "all" (picked to start with), "none" or "pick". With "pick", notOwned holds the ones you untapped.
    function newOwnChoice() { return { mode: "all", notOwned: new Set() }; }
    // By name only, so a brand filled in later doesn't undo your tap.
    function ownKey(p) { return sameKey(p.name); }
    function sameKey(text) { return plainQuotes(String(text || "")).trim().toLowerCase(); }
    function ownsNewPaint(choice, p) {
      if (!choice || choice.mode === "all") return true;
      if (choice.mode === "none") return false;
      return !choice.notOwned.has(ownKey(p));
    }

    // Adds p to a list of new paints, unless the same paint is already in it.
    function addNewPaint(list, p) {
      const brand = tidyBrand(p.brand);
      const name = String(p.name || "").trim();
      if (!name || isInPalette({ brand, name })) return;
      if (list.some(o => sameText(o.name, name) && (!o.brand || !brand || sameText(o.brand, brand)))) return;
      const known = brand ? null : KNOWN_PAINTS.find(k => sameText(k.name, name));
      list.push({ brand, name, label: `${brand || (known && known.brand) ? (brand || known.brand) + " " : ""}${name}` });
    }
    // The paints a paste import would add to your palette (paints you've answered count too).
    function importNewPaints(d) {
      const list = [];
      if (d && d.parsed) for (const s of d.parsed.schemes) for (const part of s.parts) for (const step of part.steps)
        for (const m of step.paints) { const p = importPaintFor(m); if (p) addNewPaint(list, p); }
      return list;
    }
    // The paints a recipe you're writing would add to your palette.
    function draftNewPaints(d) {
      const list = [];
      for (const s of d.steps) for (const p of s.paints) addNewPaint(list, p);
      return list;
    }

    // The card: "Do you own these? All / None / Let me pick". getPaints() lists the new paints now.
    // It only redraws itself, so the boxes you're typing in elsewhere on the page aren't disturbed.
    let recipeOwnCard = null;   // the card in the recipe editor, if it's open
    function refreshRecipeOwn() {
      if (recipeOwnCard && recipeOwnCard.isConnected) recipeOwnCard.refresh();
      if (recipeIdeasCard && recipeIdeasCard.isConnected) recipeIdeasCard.refresh();   // v28
    }
    function buildOwnCard(choice, getPaints) {
      const card = document.createElement("div");
      card.className = "card own-check";
      const draw = () => {
        const paints = getPaints();
        // Nothing changed? Leave it alone. (Redrawing as you tap a chip would lose the tap.)
        const look = JSON.stringify([choice.mode, paints.map(p => [p.label, ownsNewPaint(choice, p)])]);
        if (look === card.dataset.look) return;
        card.dataset.look = look;
        card.innerHTML = "";
        card.hidden = !paints.length;
        if (!paints.length) return;
        const head = document.createElement("h2");
        head.textContent = "Do you own these?";
        const hint = document.createElement("p");
        hint.className = "hint";
        hint.textContent = `${plural(paints.length, "paint")} will be new to your palette. Ones you own stay off the shopping list; `
          + "ones you don't go on it. You can change any of them later on Your Palette.";
        const modes = document.createElement("div");
        modes.className = "chips";
        for (const [key, label] of [["all", "All"], ["none", "None"], ["pick", "Let me pick"]]) {
          const chip = makeChip(label, choice.mode === key, () => { choice.mode = key; draw(); });
          chip.dataset.own = key;
          modes.appendChild(chip);
        }
        card.append(head, hint, modes);
        if (choice.mode === "pick") {
          const pickHint = document.createElement("p");
          pickHint.className = "hint";
          pickHint.style.margin = "10px 0 0";
          pickHint.textContent = "Tap the ones you don't have.";
          const list = document.createElement("div");
          list.className = "chips";
          for (const p of paints) {
            const owned = ownsNewPaint(choice, p);
            const chip = makeChip(`${owned ? "✓ " : ""}${p.label}`, owned, () => {
              const k = ownKey(p);
              if (choice.notOwned.has(k)) choice.notOwned.delete(k); else choice.notOwned.add(k);
              draw();
            });
            chip.classList.add("own-paint");
            chip.setAttribute("aria-label", `${p.label}: ${owned ? "owned" : "not owned"}`);
            list.appendChild(chip);
          }
          card.append(pickHint, list);
        }
      };
      card.refresh = draw;
      draw();
      return card;
    }

    // ================= v16: PASTE RECIPES (the preview and saving) =================
    // importDraft: null, or { text, parsed, groups, names } while Paste recipes is open.
    const importPage = document.getElementById("import-page");
    let importDraft = null;

    function startImport() {
      if (draftWaiting("paste")) return;   // v26: kept pasted notes are offered first
      whenOkToLeaveDraft(() => {
        recipeDraft = null;
        openRecipeId = null;
        importDraft = { text: "", parsed: null, groups: [], names: [] };
        renderRecipes();
        showTab("recipes");
        window.scrollTo(0, 0);
      });
    }
    function closeImport(askFirst) {
      const leave = () => {
        importDraft = null;
        renderRecipes();
        window.scrollTo(0, 0);
      };
      if (askFirst && importDraft && importDraft.text.trim()) {
        askYesNo("Leave without saving these recipes?", leave, { danger: true });
        return;
      }
      leave();
    }
    document.getElementById("paste-recipes").addEventListener("click", startImport);
    document.getElementById("paste-recipes-schemes").addEventListener("click", startImport);

    // v18: very long pastes are cut to this many characters, so the page never freezes.
    const PASTE_LIMIT = 20000;
    function readImportText() {
      const d = importDraft;
      d.cut = d.text.length > PASTE_LIMIT;
      d.parsed = parseRecipeText(d.text.slice(0, PASTE_LIMIT));
      d.trimmed = false;   // v18d-1: no steps left out yet
      d.editing = null;    // v18d-2a: no step's editor open
      d.swapAt = -1;       // v18d-2b: no paint's Change… box open
      d.groups = unsureMentions(d.parsed);
      d.names = d.parsed.schemes.map(s => s.name || "Imported recipes");
      renderImport();
    }

    // What a mention ends up as: the matched paint, or your answer for an unsure one.
    function importPaintFor(mention) {
      if (mention.status !== "unsure") return mention.paint;
      const g = importDraft.groups.find(x => x.key === matchKey(mention.typed));
      return g && g.choice ? g.choice.paint : null;
    }
    const importCount = (d) => d.parsed ? d.parsed.schemes.reduce((n, s) => n + s.parts.length, 0) : 0;

    function renderImport() {
      const d = importDraft;
      importPage.innerHTML = "";
      const back = document.createElement("button");
      back.className = "link-button";
      back.textContent = "← Back";
      back.addEventListener("click", () => closeImport(true));
      importPage.appendChild(back);

      const card = document.createElement("div");
      card.className = "card";
      card.innerHTML = `<h2>Paste recipes</h2>
        <p class="hint">Paste your notes (from Google Keep, Reddit, anywhere). Put each part on its own line ending in a colon,
        like <b>Eyes:</b>, then one step per line, or several split by commas. Mixes like <b>2:1 Baal:CM</b> or <b>50/50</b> work too.
        You'll see a preview before anything is saved.</p>`;
      const box = document.createElement("textarea");
      box.id = "import-text";
      box.rows = 8;
      box.style.width = "100%";
      box.placeholder = "Tyranids\n\nChitin:\nLuxion purple\nGenestealer purple (drybrush)\n\nTeeth:\nWraithbone, Agrax";
      box.setAttribute("aria-label", "Recipe notes to paste");
      box.value = d.text;
      box.addEventListener("input", () => { d.text = box.value; });
      const read = document.createElement("button");
      read.className = "primary-button";
      read.style.width = "100%";
      read.style.marginTop = "10px";
      read.textContent = d.parsed ? "Read again" : "Read notes";
      read.addEventListener("click", readImportText);
      card.append(box, read);
      importPage.appendChild(card);
      if (!d.parsed) return;
      if (d.cut) {
        card.insertAdjacentHTML("beforeend", `<p class="hint" style="margin: 12px 0 0;">That's a very long note, so only the first
          ${PASTE_LIMIT.toLocaleString("en-GB")} characters were read. Paste the rest separately.</p>`);
      }
      if (!d.parsed.schemes.length) {
        card.insertAdjacentHTML("beforeend", d.trimmed
          ? '<p class="hint" style="margin: 12px 0 0;">You\'ve left every step out, so there\'s nothing to save. Tap Read again to bring them all back.</p>'
          : '<p class="hint" style="margin: 12px 0 0;">No recipes found in that text.</p>');
        return;
      }
      // v18d-1
      // v18d-2a: ✎ to change a step, ✕ on a part's name or a note too.
      card.insertAdjacentHTML("beforeend", '<p class="hint import-remove-hint" style="margin: 12px 0 0;">Something read wrong? ' +
        'Tap ✎ on a step to change its technique, mix ratio or paints. Tap ✕ on a step to leave it out, or ✕ on a part\'s name ' +
        'or a note to leave that out. This only changes the preview, not your notes, so Read again brings everything back as pasted.</p>');

      // 1. The paints it wasn't sure about. Nothing is picked for you.
      const left = d.groups.filter(g => !g.choice).length;
      if (d.groups.length) {
        const check = document.createElement("div");
        check.className = "card import-check";
        check.innerHTML = `<h2>Check ${plural(d.groups.length, "paint")}</h2>
          <p class="hint">Not sure what these are, so it's asking rather than guessing. Pick one each.
          Your answers are remembered, so next time they're matched straight away.</p>`;
        for (const g of d.groups) {
          const row = document.createElement("div");
          row.className = "import-ask" + (g.choice ? " answered" : "");
          const label = document.createElement("div");
          label.className = "import-typed";
          label.textContent = `“${g.typed}”` + (g.count > 1 ? ` (${g.count} times)` : "");
          const chips = document.createElement("div");
          chips.className = "chips";
          chips.style.marginTop = "6px";
          const choose = (kind, paint) => { g.choice = { kind, paint }; renderImport(); };
          const pressed = (kind, name) => !!g.choice && g.choice.kind === kind && (!name || sameText(g.choice.paint.name, name));
          for (const s of g.suggestions) chips.appendChild(makeChip(s.name, pressed("pick", s.name), () => choose("pick", s)));
          chips.appendChild(makeChip(`Keep “${tidyName(g.typed)}”`, pressed("keep"), () => choose("keep", { brand: "", name: tidyName(g.typed), colour: DEFAULT_PAINT_COLOUR })));
          chips.appendChild(makeChip("Basing material", pressed("material"), () => choose("material", { brand: "", name: tidyName(g.typed), colour: DEFAULT_PAINT_COLOUR, type: "material" })));
          const other = makeChip(g.choice && g.choice.kind === "other" ? `Other: ${g.choice.paint.name}` : "Other…", pressed("other"), () => {
            askText(`What is “${g.typed}”? Type the paint's name:`, "", (answer) => {
              const typed = (answer || "").trim();
              if (!typed) return;
              const m = matchPaint(typed);
              const paint = m.paint || (m.suggestions[0] && sameText(matchKey(m.suggestions[0].name), matchKey(typed)) ? m.suggestions[0] : null)
                            || { brand: "", name: tidyName(typed), colour: DEFAULT_PAINT_COLOUR };
              choose("other", paint);
            });
          });
          chips.appendChild(other);
          row.append(label, chips);
          check.appendChild(row);
        }
        importPage.appendChild(check);
      }

      // 2. The preview: each scheme, its parts and their steps.
      d.parsed.schemes.forEach((scheme, si) => {
        const sc = document.createElement("div");
        sc.className = "card";
        const nameLabel = document.createElement("label");
        nameLabel.className = "hint";
        nameLabel.style.display = "grid";
        nameLabel.style.gap = "4px";
        nameLabel.textContent = "Scheme name";
        const nameBox = document.createElement("input");
        nameBox.value = d.names[si];
        nameBox.style.width = "100%";
        nameBox.setAttribute("aria-label", `Scheme ${si + 1} name`);
        nameBox.addEventListener("input", () => { d.names[si] = nameBox.value; });
        nameLabel.appendChild(nameBox);
        sc.appendChild(nameLabel);
        for (const [pi, part] of scheme.parts.entries()) {
          // v18d-2a: the part's name with a ✕ to leave the whole part out.
          const headLine = document.createElement("div");
          headLine.className = "import-part-line";
          const head = document.createElement("div");
          head.className = "import-part";
          head.textContent = part.name;
          const dropPart = importIconButton("✕", "icon-button remove import-drop-part", "Leave this whole part out",
            `Leave out the whole ${part.name} part`, () => removeImportPart(si, pi));
          headLine.append(head, dropPart);
          sc.appendChild(headLine);
          // v18d-2a: each part note on its own line, with a ✕ to leave that note out.
          for (const [ni, text] of part.notes.entries()) {
            const noteLine = document.createElement("div");
            noteLine.className = "import-note-line";
            const n = document.createElement("p");
            n.className = "step-note";
            n.textContent = text;
            const dropNote = importIconButton("✕", "icon-button remove import-drop-note", "Leave this note out",
              `Leave out the note “${importShort(text)}” from ${part.name}`, () => removeImportNote(si, pi, ni));
            noteLine.append(n, dropNote);
            sc.appendChild(noteLine);
          }
          const ol = document.createElement("ol");
          ol.className = "import-steps";
          for (const [ti, step] of part.steps.entries()) {
            const li = document.createElement("li");
            if (step.optional) li.classList.add("optional-step");
            // v18d-1: the step's words on the left, a ✕ to leave it out on the right.
            const line = document.createElement("div");
            line.className = "import-line";
            const body = document.createElement("div");
            body.className = "import-line-body";
            const remove = document.createElement("button");
            remove.type = "button";
            remove.className = "icon-button remove import-remove";
            remove.textContent = "✕";
            remove.title = "Leave this step out";
            remove.setAttribute("aria-label", `Leave out ${importStepLabel(step)} from ${part.name}`);
            remove.addEventListener("click", () => removeImportStep(si, pi, ti));
            // v18d-2a: ✎ opens a small editor under the line (technique and mix ratio).
            const editing = d.editing === step;
            const edit = importIconButton("✎", "icon-button import-edit", editing ? "Close" : "Change this step",
              `Change ${importStepLabel(step)} in ${part.name}`, () => toggleImportEdit(step));
            edit.setAttribute("aria-expanded", editing ? "true" : "false");
            line.append(body, edit, remove);
            li.appendChild(line);
            if (editing) li.appendChild(buildImportStepEditor(step, part));
            const paints = step.paints.map(importPaintFor);
            const tech = document.createElement("span");
            tech.className = "import-tech";
            tech.textContent = step.technique || `${guessTechnique(paints.filter(Boolean)) || "Step"} (auto)`;
            body.appendChild(tech);
            step.paints.forEach((m, i) => {
              if (i) body.append(" + ");
              const span = document.createElement("span");
              const paint = paints[i];
              if (m.fromTyped !== undefined) {
                // v18d-2b: a paint you changed with ✎ shows what was pasted → what it is now.
                span.className = "import-paint swapped";
                span.textContent = `${m.fromTyped} → ${paint.name}` + (m.status === "new" ? " (new)" : "");
              } else if (m.status === "unsure") {
                span.className = paint ? "import-paint resolved" : "import-paint unsure";
                span.textContent = paint ? `${m.typed} → ${paint.name}` : `${m.typed}?`;
              } else {
                span.className = "import-paint" + (m.status === "new" ? " is-new" : "");
                // v18: never read .name of nothing (that stopped the whole preview).
                span.textContent = (paint ? paint.name : m.typed) + (m.status === "new" ? " (new)" : "");
              }
              body.appendChild(span);
            });
            const extra = [step.ratio ? `mix ${step.ratio}` : "", step.coats > 1 ? coatsText(step.coats) : "",
                           step.optional ? "(optional)" : ""].filter(Boolean).join(" · ");
            if (extra) { const s = document.createElement("small"); s.textContent = ` · ${extra}`; body.appendChild(s); }
            if (step.note) { const n = document.createElement("div"); n.className = "step-note"; n.textContent = step.note; body.appendChild(n); }
            ol.appendChild(li);
          }
          sc.appendChild(ol);
        }
        importPage.appendChild(sc);
      });

      // 3. v18c: "Do you own these?" for the paints new to your palette. All is picked to start with.
      d.own = d.own || newOwnChoice();
      const ownCard = buildOwnCard(d.own, () => importNewPaints(d));
      ownCard.id = "import-own";
      importPage.appendChild(ownCard);

      const save = document.createElement("button");
      save.className = "primary-button";
      save.id = "import-save";
      save.style.width = "100%";
      save.disabled = left > 0;
      save.textContent = left ? `Pick ${plural(left, "more paint")} first` : `Save ${plural(importCount(d), "recipe")}`;
      save.addEventListener("click", saveImport);
      importPage.appendChild(save);
    }

    // ================= v18d-1: LEAVE A STEP OUT OF THE PASTE PREVIEW =================
    // Each step line in the preview has a ✕. It takes that step out of what will be saved
    // (your pasted notes in the box stay as they were, so Read again brings it back).
    // A part with no steps left goes too, and a scheme with no parts left. Undo puts it back.

    // A short name for a step, for the ✕ button's label and the message: its paints, or else
    // its technique, or else its note.
    function importStepLabel(step) {
      const names = step.paints.map(m => { const p = importPaintFor(m); return p ? p.name : m.typed; }).filter(Boolean);
      const text = names.length ? names.join(" + ") : (step.technique || step.note || "this step");
      return text.length > 60 ? text.slice(0, 57) + "…" : text;
    }
    // The preview's shape (which schemes, parts, steps and part notes), so Undo can put it back exactly.
    // v18d-2a: part notes are kept too, now they can be left out.
    function importSnapshot(d) {
      return { names: d.names.slice(), groups: d.groups, trimmed: d.trimmed,
               schemes: d.parsed.schemes.map(s => [s, s.parts.map(p => [p, p.steps.slice(), p.notes.slice()])]) };
    }
    // Puts a snapshot back (Undo). Scheme names typed since are kept; a scheme that had gone
    // gets its old name back. Steps are the same objects, so changes made with ✎ since stay.
    function restoreImport(d, before) {
      const now = d.groups;
      const names = before.schemes.map(([s], i) => {
        const j = d.parsed.schemes.indexOf(s);
        return j >= 0 ? d.names[j] : before.names[i];
      });
      d.parsed.schemes = before.schemes.map(([s, parts]) => {
        s.parts = parts.map(([p, steps, notes]) => { p.steps = steps; p.notes = notes; return p; });
        return s;
      });
      d.names = names;
      d.trimmed = before.trimmed;
      regroupImport(d, now, before.groups);
      renderImport();
    }
    // Rebuilds the "Check N paints" list after steps are left out or put back, so a paint that
    // was only in a removed step stops holding up Save. Answers you'd already given are kept.
    function regroupImport(d, ...older) {
      d.groups = unsureMentions(d.parsed);
      for (const g of d.groups) for (const list of older) {
        const had = list.find(x => x.key === g.key && x.choice);
        if (had) { g.choice = had.choice; break; }
      }
    }
    // Takes out schemes left with no parts (and their names).
    function dropEmptySchemes(d) {
      for (let i = d.parsed.schemes.length - 1; i >= 0; i--) {
        if (!d.parsed.schemes[i].parts.length) { d.parsed.schemes.splice(i, 1); d.names.splice(i, 1); }
      }
    }
    // Runs a change to the preview, redraws it, and if one of these buttons had focus, moves
    // focus to the next button of the same kind (or the notes box if there are none left).
    function changeImport(selector, change) {
      const all = [...importPage.querySelectorAll(selector)];
      const at = all.indexOf(document.activeElement);
      change();
      renderImport();
      if (at >= 0) {
        const next = [...importPage.querySelectorAll(selector)];
        const el = next[Math.min(at, next.length - 1)] || document.getElementById("import-text");
        if (el) el.focus();
      }
    }
    function removeImportStep(si, pi, ti) {
      const d = importDraft;
      const scheme = d && d.parsed && d.parsed.schemes[si];
      const part = scheme && scheme.parts[pi];
      if (!part || !part.steps[ti]) return;
      const label = importStepLabel(part.steps[ti]);
      const before = importSnapshot(d);
      let message = `Left out “${label}” from ${part.name}`;
      changeImport(".import-remove", () => {
        const [step] = part.steps.splice(ti, 1);
        if (d.editing === step) d.editing = null;
        if (!part.steps.length) {
          scheme.parts.splice(pi, 1);
          message = `Left out “${label}”. ${part.name} had no steps left, so it's left out too`;
        }
        dropEmptySchemes(d);
        d.trimmed = true;
        regroupImport(d, before.groups);
      });
      showToast(message, () => { if (importDraft === d) restoreImport(d, before); });
    }

    // ================= v18d-2a: LEAVE A PART OR NOTE OUT, AND CHANGE A STEP =================
    // ✕ on a part's name leaves the whole part out; ✕ on a part note leaves that note out.
    // ✎ on a step opens a small editor under it to change its technique, or change or clear
    // its mix ratio. Like v18d-1, all of this only changes the preview: your pasted notes stay
    // as they were, so Read again brings back exactly what you pasted. Each change has Undo.

    // A small square button (✕ or ✎) with a tooltip and a screen-reader label.
    function importIconButton(text, className, title, label, onClick) {
      const b = document.createElement("button");
      b.type = "button";
      b.className = className;
      b.textContent = text;
      b.title = title;
      b.setAttribute("aria-label", label);
      b.addEventListener("click", onClick);
      return b;
    }
    const importShort = (text) => { const t = String(text || ""); return t.length > 40 ? t.slice(0, 37) + "…" : t; };

    function removeImportPart(si, pi) {
      const d = importDraft;
      const scheme = d && d.parsed && d.parsed.schemes[si];
      const part = scheme && scheme.parts[pi];
      if (!part) return;
      const before = importSnapshot(d);
      changeImport(".import-drop-part", () => {
        scheme.parts.splice(pi, 1);
        if (part.steps.includes(d.editing)) d.editing = null;
        dropEmptySchemes(d);
        d.trimmed = true;
        regroupImport(d, before.groups);
      });
      showToast(`Left out ${part.name} (${plural(part.steps.length, "step")})`,
                () => { if (importDraft === d) restoreImport(d, before); });
    }

    function removeImportNote(si, pi, ni) {
      const d = importDraft;
      const part = d && d.parsed && d.parsed.schemes[si] && d.parsed.schemes[si].parts[pi];
      if (!part || part.notes[ni] === undefined) return;
      const text = part.notes[ni];
      const before = importSnapshot(d);
      changeImport(".import-drop-note", () => {
        part.notes.splice(ni, 1);
        d.trimmed = true;
      });
      showToast(`Left out the note “${importShort(text)}” from ${part.name}`,
                () => { if (importDraft === d) restoreImport(d, before); });
    }

    // Opens or closes the ✎ editor for a step (only one is open at a time).
    function toggleImportEdit(step) {
      const d = importDraft;
      if (!d) return;
      d.editing = d.editing === step ? null : step;
      d.swapAt = -1;   // v18d-2b: a fresh editor has no Change… box open
      renderImport();
      const at = findImportStep(step);
      if (!at) return;
      // Focus goes into the editor when it opens, and back to the ✎ when it closes.
      const el = d.editing ? at.li.querySelector(".import-step-editor select") : at.li.querySelector(".import-edit");
      if (el) el.focus();
    }
    // The <li> on screen for a step object.
    function findImportStep(step) {
      const d = importDraft;
      let n = 0;
      for (const s of d.parsed.schemes) for (const p of s.parts) for (const t of p.steps) {
        if (t === step) return { li: importPage.querySelectorAll(".import-steps li")[n] };
        n++;
      }
      return null;
    }

    // Changes a step's technique and/or ratio, redraws, keeps focus where it was in the editor,
    // and shows a message with Undo (which puts back the old values).
    function changeImportStep(step, changes, message) {
      const d = importDraft;
      const old = {};
      for (const k of Object.keys(changes)) old[k] = step[k];
      const focusKey = document.activeElement && document.activeElement.dataset ? document.activeElement.dataset.importFocus : "";
      Object.assign(step, changes);
      renderImport();
      if (focusKey && d.editing === step) {
        const at = findImportStep(step);
        const el = at && at.li.querySelector(`[data-import-focus="${focusKey}"]`);
        if (el) el.focus();
      }
      showToast(message, () => {
        if (importDraft !== d) return;
        Object.assign(step, old);
        renderImport();
      });
    }

    // ================= v18d-2b: SWAP A PAINT IN A STEP OF THE PASTE PREVIEW =================
    // In the ✎ editor, each paint in the step has a Change… button. You type the paint it should
    // be, and it's matched the same way as "Other…" under "Check N paints": a paint it knows,
    // or a near-exact suggestion, or else a new paint named as you typed it. Only this one step
    // changes (a paint it wasn't sure about stays a question in other steps), "Check N paints",
    // "Do you own these?" and the Save button update to match, and the mix ratio is unchanged
    // (the step has the same number of paints). Your pasted notes aren't touched, so Read again
    // brings back the original. Undo puts the old paint back.

    // After a redraw, puts focus on a control in the open editor (by its data-import-focus).
    function focusImportEditor(step, key) {
      const d = importDraft;
      if (!d || d.editing !== step) return;
      const at = findImportStep(step);
      const el = at && at.li.querySelector(`[data-import-focus="${key}"]`);
      if (el) el.focus();
    }

    // What "typed" would be, matched like "Other…" does. Returns a mention for a preview step.
    function importSwapMention(typed, old) {
      const m = matchPaint(typed);
      const top = m.suggestions[0];
      const near = !m.paint && top && sameText(matchKey(top.name), matchKey(typed)) ? top : null;
      const paint = m.paint || near || { brand: "", name: tidyName(typed), colour: DEFAULT_PAINT_COLOUR };
      const status = m.status === "material" ? "material" : (m.paint && m.status !== "new") || near ? "sure" : "new";
      // fromTyped keeps what was first pasted, so the preview can show "pasted → now".
      return { status, typed, paint, suggestions: [], fromTyped: old.fromTyped !== undefined ? old.fromTyped : old.typed };
    }

    // Swaps paint number i of a step for what you typed. quiet = don't move focus (Done does that).
    function swapImportPaint(step, i, typed, quiet) {
      const d = importDraft;
      const old = step && step.paints[i];
      typed = String(typed || "").trim().replace(/\s+/g, " ");
      if (!d || !old || !typed) return;
      const label = importStepLabel(step);
      const was = importPaintFor(old);
      const wasName = was ? was.name : old.typed;
      const mention = importSwapMention(typed, old);
      d.swapAt = -1;
      // The same paint as before? Nothing to change.
      if (was && sameText(was.name, mention.paint.name) && sameText(tidyBrand(was.brand), tidyBrand(mention.paint.brand))) {
        renderImport();
        if (!quiet) focusImportEditor(step, `swap-${i}`);
        showToast(`${wasName} is already that paint`);
        return;
      }
      const groupsBefore = d.groups;
      step.paints[i] = mention;
      regroupImport(d, groupsBefore);
      renderImport();
      if (!quiet) focusImportEditor(step, `swap-${i}`);
      showToast(`${label}: ${wasName} changed to ${mention.paint.name}${mention.status === "new" ? " (new)" : ""}`, () => {
        if (importDraft !== d) return;
        const at = step.paints.indexOf(mention);
        if (at < 0) return;
        const now = d.groups;
        step.paints[at] = old;
        // Answers given since are kept; one that only the old paint needed comes back too.
        regroupImport(d, now, groupsBefore);
        renderImport();
      });
    }

    function buildImportStepEditor(step, part) {
      const box = document.createElement("div");
      box.className = "import-step-editor";
      const label = importStepLabel(step);
      const paints = step.paints.map(importPaintFor).filter(Boolean);

      // Technique: "Auto" (guess from the paints) or one from your list.
      const techLabel = document.createElement("label");
      techLabel.textContent = "Technique";
      const select = document.createElement("select");
      select.dataset.importFocus = "technique";
      const guess = guessTechnique(paints);
      select.add(new Option(guess ? `Auto: ${guess}` : "Auto (from the paints)", ""));
      const values = book.techniques.slice();
      if (step.technique && !values.some(v => sameText(v, step.technique))) values.push(step.technique);
      for (const v of values) select.add(new Option(v, v));
      select.value = values.find(v => sameText(v, step.technique)) || "";
      select.addEventListener("change", () => {
        const technique = select.value;
        changeImportStep(step, { technique },
          technique ? `${label}: technique changed to ${technique}` : `${label}: technique set to Auto`);
      });
      techLabel.appendChild(select);
      box.appendChild(techLabel);

      // v18d-2b: Paints: one row per paint (its name and Change…). Change… opens a box under it
      // to type the paint it should be. Only one box is open at a time.
      const d = importDraft;
      let swapTyped = () => "";   // what's typed in the open box, so Done can use it
      if (step.paints.length) {
        const list = document.createElement("div");
        list.className = "import-swap-list";
        const title = document.createElement("div");
        title.className = "import-swap-title";
        title.textContent = step.paints.length > 1 ? "Paints" : "Paint";
        list.appendChild(title);
        step.paints.forEach((m, i) => {
          const p = importPaintFor(m);
          const name = p ? p.name : `${m.typed}?`;
          const row = document.createElement("div");
          row.className = "import-swap-row";
          const nameEl = document.createElement("div");
          nameEl.className = "import-swap-name";
          nameEl.textContent = name;
          if (m.fromTyped !== undefined) {
            const was = document.createElement("small");
            was.textContent = ` (pasted as “${m.fromTyped}”)`;
            nameEl.appendChild(was);
          }
          const change = document.createElement("button");
          change.type = "button";
          change.className = "plain-button import-swap";
          change.textContent = "Change…";
          change.dataset.importFocus = `swap-${i}`;
          change.setAttribute("aria-label", `Change ${name} to a different paint`);
          change.setAttribute("aria-expanded", d.swapAt === i ? "true" : "false");
          // Don't take the ratio box out of focus first (that redraws the editor and loses the tap).
          change.addEventListener("mousedown", (e) => e.preventDefault());
          change.addEventListener("click", () => {
            d.swapAt = d.swapAt === i ? -1 : i;
            renderImport();
            focusImportEditor(step, d.swapAt === i ? "swap-input" : `swap-${i}`);
          });
          row.append(nameEl, change);
          list.appendChild(row);
          if (d.swapAt !== i) return;

          // The box: type a name, then Use (or Enter). Cancel (or Esc) closes it.
          const swapBox = document.createElement("div");
          swapBox.className = "import-swap-box";
          const swapLabel = document.createElement("label");
          swapLabel.textContent = `Change ${name} to:`;
          const input = document.createElement("input");
          input.className = "import-swap-input";
          input.dataset.importFocus = "swap-input";
          input.placeholder = "Type the paint's name";
          input.autocomplete = "off";
          input.setAttribute("aria-label", `New paint instead of ${name}`);
          swapLabel.appendChild(input);
          const buttons = document.createElement("div");
          buttons.className = "import-swap-buttons";
          const use = document.createElement("button");
          use.type = "button";
          use.className = "plain-button import-swap-use";
          use.textContent = "Use";
          const cancel = document.createElement("button");
          cancel.type = "button";
          cancel.className = "plain-button import-swap-cancel";
          cancel.textContent = "Cancel";
          const useIt = () => { if (input.value.trim()) swapImportPaint(step, i, input.value); else input.focus(); };
          const close = () => { d.swapAt = -1; renderImport(); focusImportEditor(step, `swap-${i}`); };
          use.addEventListener("mousedown", (e) => e.preventDefault());
          cancel.addEventListener("mousedown", (e) => e.preventDefault());
          use.addEventListener("click", useIt);
          cancel.addEventListener("click", close);
          input.addEventListener("keydown", (e) => {
            if (e.key === "Enter") { e.preventDefault(); useIt(); }
            // Esc closes only this box, not the whole editor.
            if (e.key === "Escape") { e.preventDefault(); e.stopPropagation(); close(); }
          });
          swapTyped = () => input.value.trim();
          buttons.append(use, cancel);
          swapBox.append(swapLabel, buttons);
          list.appendChild(swapBox);
        });
        box.appendChild(list);
      }

      // Mix ratio: only for a step with 2 or more paints.
      const n = step.paints.length;
      let applyRatio = null;   // reads the ratio box; false if what's typed doesn't fit
      if (n > 1) {
        const row = document.createElement("div");
        row.className = "import-ratio-row";
        const ratioLabel = document.createElement("label");
        ratioLabel.textContent = "Mix ratio (blank = even mix)";
        const input = document.createElement("input");
        input.dataset.importFocus = "ratio";
        input.inputMode = "decimal";
        input.placeholder = Array(n).fill(1).join(":");
        input.value = step.ratio || "";
        input.setAttribute("aria-label", `Mix ratio for ${label}`);
        const warning = document.createElement("p");
        warning.className = "import-ratio-warning";
        warning.hidden = true;
        const apply = () => {
          const typed = input.value.trim();
          if (!typed) {
            if (step.ratio) changeImportStep(step, { ratio: "" }, `${label}: mix ratio cleared (even mix)`);
            return true;
          }
          if (!ratioPercents(typed, n)) {
            warning.textContent = `The ratio needs ${n} numbers, one per paint, like ${Array(n).fill(1).join(":")}. Not changed.`;
            warning.hidden = false;
            return false;
          }
          const ratio = cleanRatio(typed);
          if (ratio !== step.ratio) changeImportStep(step, { ratio }, `${label}: mix ratio set to ${ratio}`);
          return true;
        };
        applyRatio = apply;
        input.addEventListener("change", apply);
        input.addEventListener("keydown", (e) => { if (e.key === "Enter") { e.preventDefault(); apply(); } });
        ratioLabel.appendChild(input);
        const clear = document.createElement("button");
        clear.type = "button";
        clear.className = "plain-button import-ratio-clear";
        clear.textContent = "Clear";
        clear.dataset.importFocus = "clear";
        clear.disabled = !step.ratio;
        // Pressing Clear mustn't first take the box out of focus (that would save what's typed).
        clear.addEventListener("mousedown", (e) => e.preventDefault());
        clear.addEventListener("click", () => changeImportStep(step, { ratio: "" }, `${label}: mix ratio cleared (even mix)`));
        row.append(ratioLabel, clear);
        box.append(row, warning);
      }

      const done = document.createElement("button");
      done.type = "button";
      done.className = "plain-button import-edit-done";
      done.textContent = "Done";
      // Done keeps a ratio you've typed but not yet confirmed (unless it doesn't fit), then closes.
      done.addEventListener("mousedown", (e) => e.preventDefault());
      done.addEventListener("click", () => {
        // v18d-2b: a paint name typed in an open Change… box is used too.
        const typed = swapTyped();
        const at = d.swapAt;
        if (applyRatio && applyRatio() === false) return;
        if (typed && at >= 0) swapImportPaint(step, at, typed, true);
        if (d.editing === step) toggleImportEdit(step);
      });
      box.appendChild(done);
      box.addEventListener("keydown", (e) => { if (e.key === "Escape") { e.preventDefault(); toggleImportEdit(step); } });
      return box;
    }

    function saveImport() {
      const d = importDraft;
      if (!d || !d.parsed || d.groups.some(g => !g.choice)) return;
      const before = JSON.stringify(book);
      let recipeCount = 0;
      const made = [];
      const importNewIds = [];   // v17.1
      // v18c-3: every change goes inside changeAndSave(). If the save fails (storage full),
      // the recipe book is put back exactly as it was and the preview stays open with your
      // notes, so nothing is lost and you can try again. Before, the notes were thrown away
      // and it still said "Saved".
      const kept = changeAndSave(() => {
        for (const g of d.groups) if (g.choice.kind === "pick" || g.choice.kind === "other") rememberShorthand(g.typed, g.choice.paint);
        d.parsed.schemes.forEach((s, si) => {
          const schemeName = (d.names[si] || "").trim() || "Imported recipes";
          const ids = [];
          for (const part of s.parts) {
            const steps = part.steps.map(step => {
              const paints = step.paints.map(importPaintFor).filter(Boolean).map(p => {
                // v17.1: a paint new to your palette comes in as Owned (you're bringing your own list).
                // v18c: unless you answered None, or untapped it, under "Do you own these?".
                const known = isInPalette(p);
                const paint = findOrAddPaint(p.brand || "", p.name, p.colour || DEFAULT_PAINT_COLOUR);
                if (!known && paintStatus(paint) === "") applyPaintStatus(paint, ownsNewPaint(d.own, p) ? "owned" : "notowned");
                if (!known) importNewIds.push(paint.id);
                if (p.type === "material") paint.type = "material";
                return paint;
              });
              const ratio = paints.length > 1 && ratioPercents(step.ratio, paints.length) ? cleanRatio(step.ratio) : "";
              const mixes = paints.length > 1 ? (ratioPercents(ratio, paints.length) || evenSplit(paints.length)) : [100];
              return { technique: step.technique, coats: cleanCount(step.coats), ratio, note: step.note || "", optional: !!step.optional,
                       paints: paints.map((p, i) => ({ paint: p.id, mix: mixes[i] })) };
            });
            const existingPart = book.parts.find(p => sameText(p, part.name) || sameText(p + "s", part.name) || sameText(p, part.name + "s"));
            let name = part.name;
            if (book.recipes.some(r => sameText(r.name, name))) name = `${part.name} (${schemeName})`;
            const recipe = { id: Math.max(0, ...book.recipes.map(r => r.id)) + 1, name, part: existingPart || part.name,
                             notes: part.notes.join("\n"), steps };
            book.recipes.push(recipe);
            ids.push(recipe.id);
            recipeCount++;
          }
          const faction = (models.find(m => sameText(m.faction, schemeName)) || {}).faction || schemeName;
          book.schemes.push({ id: Math.max(0, ...book.schemes.map(x => x.id)) + 1, name: schemeName, faction, auto: true, recipes: ids });
          made.push(schemeName);
        });
        settings.recipeView = importNewIds.length ? "palette" : "schemes";
      });
      if (!kept) {
        renderRecipes();   // the preview, still open, with your notes and answers
        showNotSaved("Not saved: storage on this device is full. Your pasted notes are still here. " +
                     "Save a backup, free some space, then tap Save again.");
        return;
      }
      importDraft = null;
      // v17.1: new paints open on Your Palette for a quick check, with every row expanded.
      importReviewIds = importNewIds.length ? importNewIds.slice() : null;
      importNewIds.forEach(id => openPaintIds.add(id));
      render();
      window.scrollTo(0, 0);
      showToast(`Saved ${plural(made.length, "scheme")} with ${plural(recipeCount, "recipe")}`, () => {
        book = cleanRecipeBook(JSON.parse(before));
        render();
      });
    }

    // ================= v16: COPY AS TEXT (the button) =================
    function copyText(text, what) {
      const done = () => showToast(`${what} copied. Paste it anywhere, or back into Paste recipes.`);
      const fallback = () => {
        const area = document.createElement("textarea");
        area.value = text;
        area.style.position = "fixed";
        area.style.opacity = "0";
        document.body.appendChild(area);
        area.select();
        let ok = false;
        try { ok = document.execCommand("copy"); } catch (ignored) {}
        area.remove();
        if (ok) done(); else showTextToCopy("Copy this text:", text);   // v21.7: the app's own box, text already selected
      };
      if (navigator.clipboard && navigator.clipboard.writeText) navigator.clipboard.writeText(text).then(done, fallback);
      else fallback();
    }

    // ================= v16: "LAST BACKED UP" =================
    function renderBackupAge() {
      const el = document.getElementById("backup-age");
      if (!el) return;
      const last = settings.lastBackup;
      const days = last ? daysSince(last) : Infinity;
      el.textContent = !last ? "Last backed up: never. Save a backup now and then, in case your phone clears the app's data."
        : `Last backed up: ${days < 1 ? "today" : days < 2 ? "yesterday" : `${Math.floor(days)} days ago`} (${shortDate(last)}).`;
      el.classList.toggle("backup-old", days >= 7);
    }

    // ================= v16: SCAN A PAINT POT =================
    // Reads the label on the phone itself with the Tesseract engine (free, no AI service).
    // The matcher then SUGGESTS paints and you pick one. Nothing is added until you say so.
    // v16.1: reading the whole photo failed (the background drowned the label out). Now the
    // camera shows a box: line the paint's NAME up in it, and only that strip is read, after
    // a local contrast boost (it makes shiny, curved labels readable).
    // v18.3: the engine and its English data are kept in the app's own "ocr" folder (see
    // ocr/README.md), not downloaded from other websites on the first scan. So scanning works
    // offline from the start, and nothing goes to an outside website. ocr/ocr-worker.js runs
    // the engine in the background; this little "client" sends it pictures and gets text back.
    const OCR_WORKER_URL = "ocr/ocr-worker.js";
    let ocrWorker = null;
    function startOcrWorker() {
      const worker = new Worker(OCR_WORKER_URL);
      const waiting = new Map();
      let nextId = 1;
      const failAll = (message) => {
        for (const w of waiting.values()) w.reject(new Error(message));
        waiting.clear();
      };
      worker.onmessage = (event) => {
        const { id, text, error } = event.data || {};
        const w = waiting.get(id);
        if (!w) return;
        waiting.delete(id);
        if (error) w.reject(new Error(error)); else w.resolve(text || "");
      };
      worker.onerror = () => {
        ocrWorker = null;   // start afresh next time
        failAll("The label reader stopped working. Please try again.");
      };
      const send = (message, transfer) => new Promise((resolve, reject) => {
        const id = nextId++;
        waiting.set(id, { resolve, reject });
        worker.postMessage({ id, ...message }, transfer || []);
      });
      const client = {
        ready: send({ type: "init" }),
        // Same shape as the old library's answer: { data: { text } }.
        async recognize(canvas) {
          const blob = await new Promise((resolve) => canvas.toBlob(resolve, "image/png"));
          if (!blob) throw new Error("Couldn't read that picture.");
          const image = new Uint8Array(await blob.arrayBuffer());
          return { data: { text: await send({ type: "read", image }, [image.buffer]) } };
        },
      };
      client.ready.catch(() => { if (ocrWorker === client) ocrWorker = null; worker.terminate(); });
      return client;
    }
    async function getOcrWorker() {
      if (!ocrWorker) ocrWorker = startOcrWorker();
      await ocrWorker.ready;
      return ocrWorker;
    }

    // Local contrast boost ("CLAHE"): each small patch of the picture gets its own contrast
    // stretch, blended smoothly. Text on a shiny or shadowed label stands out evenly.
    function boostContrast(grey, w, h, clip, tiles) {
      const tw = Math.ceil(w / tiles), th = Math.ceil(h / tiles);
      const maps = [];
      for (let ty = 0; ty < tiles; ty++) for (let tx = 0; tx < tiles; tx++) {
        const hist = new Array(256).fill(0);
        let n = 0;
        for (let y = ty * th; y < Math.min(h, (ty + 1) * th); y++)
          for (let x = tx * tw; x < Math.min(w, (tx + 1) * tw); x++) { hist[grey[y * w + x]]++; n++; }
        const limit = Math.max(1, Math.floor(clip * n / 256));
        let excess = 0;
        for (let i = 0; i < 256; i++) if (hist[i] > limit) { excess += hist[i] - limit; hist[i] = limit; }
        const add = excess / 256;
        const map = new Uint8Array(256);
        let sum = 0;
        for (let i = 0; i < 256; i++) { sum += hist[i] + add; map[i] = n ? Math.min(255, Math.round(sum * 255 / n)) : i; }
        maps.push(map);
      }
      const out = new Uint8Array(w * h);
      for (let y = 0; y < h; y++) {
        const fy = Math.min(tiles - 1, Math.max(0, (y - th / 2) / th));
        const y0 = Math.floor(fy), y1 = Math.min(tiles - 1, y0 + 1), ay = fy - y0;
        for (let x = 0; x < w; x++) {
          const fx = Math.min(tiles - 1, Math.max(0, (x - tw / 2) / tw));
          const x0 = Math.floor(fx), x1 = Math.min(tiles - 1, x0 + 1), ax = fx - x0;
          const v = grey[y * w + x];
          const top = maps[y0 * tiles + x0][v] * (1 - ax) + maps[y0 * tiles + x1][v] * ax;
          const bottom = maps[y1 * tiles + x0][v] * (1 - ax) + maps[y1 * tiles + x1][v] * ax;
          out[y * w + x] = Math.round(top * (1 - ay) + bottom * ay);
        }
      }
      return out;
    }
    // One strip of a picture, shrunk to "width" pixels wide, in grey with the contrast boost.
    function labelStrip(source, sx, sy, sw, sh, width, clip, tiles) {
      const h = Math.max(8, Math.round(sh * width / sw));
      const canvas = document.createElement("canvas");
      canvas.width = width;
      canvas.height = h;
      const g = canvas.getContext("2d");
      g.drawImage(source, sx, sy, sw, sh, 0, 0, width, h);
      const img = g.getImageData(0, 0, width, h);
      const grey = new Uint8Array(width * h);
      for (let i = 0; i < grey.length; i++) grey[i] = Math.round(img.data[i * 4] * 0.299 + img.data[i * 4 + 1] * 0.587 + img.data[i * 4 + 2] * 0.114);
      const boosted = boostContrast(grey, width, h, clip, tiles);
      for (let i = 0; i < grey.length; i++) { img.data[i * 4] = img.data[i * 4 + 1] = img.data[i * 4 + 2] = boosted[i]; img.data[i * 4 + 3] = 255; }
      g.putImageData(img, 0, 0);
      return canvas;
    }
    // The strips to read. From the camera box: that box, at two sizes and two contrast
    // strengths. From a photo: horizontal strips across the middle, where the name usually is.
    function labelStrips(source, box) {
      if (box) return [[260, 2, 8], [350, 2, 8], [260, 3, 4], [350, 3, 4]]
        .map(([w, c, t]) => labelStrip(source, box.x, box.y, box.w, box.h, w, c, t));
      const W = source.width, H = source.height, strips = [];
      for (let top = 0.34; top <= 0.68; top += 0.04) strips.push(labelStrip(source, W * 0.25, H * top, W * 0.5, H * 0.08, 340, 2, 8));
      return strips;
    }
    async function readLabel(source, box, onStatus) {
      onStatus("Getting the label reader ready…");
      const worker = await getOcrWorker();
      const strips = labelStrips(source, box);
      const texts = [];
      for (let i = 0; i < strips.length; i++) {
        onStatus(`Reading the label… (${i + 1} of ${strips.length})`);
        const { data } = await worker.recognize(strips[i]);
        texts.push(data.text || "");
      }
      return texts.join("\n");
    }

    // Label text to paint suggestions. Each word of each paint's name is compared with the
    // words read, allowing misread letters ("waite SCAR" = White Scar) and cut-off words
    // ("STORMHOSBIELS" = Stormhost). Words printed on every pot (CITADEL, LAYER...) are ignored.
    const LABEL_NOISE = new Set(["citadel", "colour", "color", "games", "workshop", "warhammer", "base", "layer", "shade",
      "contrast", "technical", "dry", "air", "spray", "acrylic", "paint", "non", "toxic", "made", "vallejo", "xpress",
      "game", "model", "army", "painter", "speedpaint", "warpaints", "fanatic",
      // v21.3: words on Army Painter, AK and Pro Acryl pots that aren't part of a paint's name
      "acrylics", "interactive", "generation", "gen", "pro", "acryl", "monument", "premium", "series", "signature"]);
    // v21.3: the brand a label names, if it names one. Its paints go first when the name could fit several brands.
    const LABEL_BRANDS = [
      [/citadel|games\s*workshop/, "Citadel"], [/vallejo|game\s*colou?r|model\s*colou?r/, "Vallejo"],
      [/army\s*painter|warpaints|fanatic/, "The Army Painter"], [/pro\s*acryl|monument/, "Pro Acryl"],
      [/\bak\b.{0,3}interactive|ak\s*interactive|3rd\s*gen/, "AK Interactive"],
    ];
    function brandOnLabel(text) {
      const t = String(text || "").toLowerCase();
      const hit = LABEL_BRANDS.find(([re]) => re.test(t));
      return hit ? hit[1] : "";
    }
    function wordLikeness(word, token) {
      const d = typoDistance(word, token, word.length);
      let same = 0;
      while (same < Math.min(word.length, token.length) && word[same] === token[same]) same++;
      return Math.max(1 - d / Math.max(word.length, token.length), same >= 4 ? same / Math.max(word.length, token.length) : 0);
    }
    function suggestFromLabel(text) {
      const tokens = [...new Set(plainQuotes(String(text)).toLowerCase().replace(/[^a-z\s]+/g, " ").split(/\s+/)
        .filter(t => t.length >= 3 && !LABEL_NOISE.has(t)))];
      // v21.3: some extra-brand names use a word that's also label print ("Dry Rust", "Army Green", "Toxic
      // Yellow"), so those paints may use the label words too, as long as another word of the name matched.
      const allTokens = [...new Set(plainQuotes(String(text)).toLowerCase().replace(/[^a-z\s]+/g, " ").split(/\s+/)
        .filter(t => t.length >= 3))];
      // v21.3: Vallejo pots print a code number (72.021). A code that matches a known paint wins outright.
      const codes = vallejoCodes(text);
      const brand = brandOnLabel(text);
      const labelKey = " " + matchKey(text) + " ";
      const scored = [];
      for (const c of matchCandidates()) {
        if (c.codes && codes.some(code => c.codes.includes(code))) { scored.push({ c, score: 2, got: 1e6, rank: 1e6, phrase: 0 }); continue; }
        // A label that names its brand: the extra lists' OTHER brands are left out (your own paints never are).
        if (brand && c.extra && !sameText(c.brand, brand)) continue;
        const words = c.words.filter(w => w.length >= 3);
        if (!words.length) continue;
        let got = 0, letters = 0, special = false, strongWord = false, allClear = true, realWord = false, clearGot = 0;
        for (const w of words) {
          letters += w.length;
          const fromNoise = c.extra && LABEL_NOISE.has(w);
          const best = Math.max(0, ...(fromNoise ? allTokens : tokens).map(t => wordLikeness(w, t)));
          if (best < 0.85) allClear = false; else clearGot += w.length * best;
          if (best >= 0.7 && !fromNoise) realWord = true;
          if (best >= 0.7) { got += w.length * best; if (!VAGUE_WORDS.has(w) && !fromNoise) special = true; }
          // A long, unusual word read well ("STORMHO" for Stormhost) is enough on its own.
          if (best >= 0.75 && w.length >= 6 && !VAGUE_WORDS.has(w)) strongWord = true;
        }
        const score = got / letters;
        if (!realWord) continue;
        // v21.3: extra-brand paints are ranked by the words read CLEARLY, plus whether the whole name is
        // on the label word for word, so "GREY GREEN" picks Grey Green over Green Grey and "GOLD" picks
        // Gold over Old Gold. (Citadel and your own paints rank exactly as before.)
        const rank = c.extra ? clearGot : got;
        const phrase = c.extra && labelKey.includes(" " + c.key + " ") ? c.key.length : 0;
        if (special && (score >= 0.5 || strongWord)) scored.push({ c, score, got, rank, phrase });
        // v21.3: many Vallejo, AK and Pro Acryl names are only everyday words ("Dark Blue", "Bone White").
        // Those extra paints count when EVERY word of the name was read clearly. (Citadel's rule is unchanged.)
        else if (c.extra && allClear) scored.push({ c, score, got, rank, phrase });
      }
      // Most letters matched first (so "STORMHO" picks Stormhost over Storm Blue), then closeness.
      // v21.3: a code match first, then the brand the label names. When letters matched are equal,
      // your own paints, Citadel and the older lists go before the extra brands (so a Citadel label
      // reads exactly as it did before).
      const onBrand = (c) => brand && sameText(c.brand, brand) ? 1 : 0;
      scored.sort((a, b) => (b.got >= 1e6) - (a.got >= 1e6) || onBrand(b.c) - onBrand(a.c) || b.rank - a.rank
        || (a.c.extra === true) - (b.c.extra === true) || b.phrase - a.phrase || b.score - a.score || (b.c.mine === true) - (a.c.mine === true));
      const out = [];
      for (const { c } of scored) if (!out.some(o => sameText(o.name, c.name) && sameText(o.brand, c.brand)))
        out.push({ brand: c.brand, name: c.name, colour: c.colour || DEFAULT_PAINT_COLOUR, type: c.type, extra: c.extra === true });
      // v21.3: the top 4 that aren't extra-brand paints always stay in (so a Citadel label offers what it
      // did before); extra brands fill the spare places, in the same order.
      // (Not when the label names one of the extra brands: then that brand's paints come first.)
      const keep = new Set(!brand || brand === "Citadel" ? out.filter(o => !o.extra).slice(0, 4) : []);
      for (const o of out) { if (keep.size >= 4) break; keep.add(o); }
      return { tokens, suggestions: out.filter(o => keep.has(o)).map(({ extra, ...o }) => o) };
    }

    // ----- The camera, with the box to line the name up in -----
    // v18.3: only ONE camera at a time. A second tap while the camera is opening (or open)
    // is ignored, and the camera is switched off when you leave the app or it's hidden,
    // so the camera light never stays on in the background.
    let cameraStream = null;
    let cameraOpening = false;   // true while the phone is still asking for / starting the camera
    let cameraCancelled = false; // set if the camera was closed while it was still starting
    function closeCamera() {
      if (cameraOpening) cameraCancelled = true;
      if (cameraStream) cameraStream.getTracks().forEach(t => t.stop());
      cameraStream = null;
      document.querySelectorAll("#scan-camera").forEach(view => view.remove());
    }
    async function openCamera() {
      if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) { document.getElementById("scan-photo").click(); return; }
      if (cameraOpening || cameraStream || document.getElementById("scan-camera")) return; // already opening or open
      cameraOpening = true;
      cameraCancelled = false;
      let stream;
      try {
        stream = await navigator.mediaDevices.getUserMedia({ video: { facingMode: "environment", width: { ideal: 1920 }, height: { ideal: 1080 } }, audio: false });
      } catch (error) {
        cameraOpening = false;
        if (cameraCancelled || !scanState) return;
        scanState.status = "Couldn't open the camera (it may need permission). Choose a photo instead, or type the name.";
        renderScan();
        return;
      }
      cameraOpening = false;
      // Closed (or the app was hidden) while it was starting? Switch it straight off.
      if (cameraCancelled || document.hidden || !scanState) { stream.getTracks().forEach(t => t.stop()); return; }
      cameraStream = stream;
      const view = document.createElement("div");
      view.id = "scan-camera";
      view.innerHTML = `<div class="cam-frame"><video playsinline muted autoplay></video><div class="cam-box"></div></div>
        <p class="cam-tip">Line up the paint's <b>name</b> inside the box, close up and straight on. Hold still, then tap Read.</p>
        <div class="cam-buttons"><button class="plain-button" id="cam-cancel">Cancel</button><button class="primary-button" id="cam-read">Read label</button></div>`;
      document.body.appendChild(view);
      const video = view.querySelector("video");
      video.srcObject = cameraStream;
      view.querySelector("#cam-cancel").addEventListener("click", closeCamera);
      view.querySelector("#cam-read").addEventListener("click", () => {
        if (!video.videoWidth) return;
        // Work out which part of the camera picture is inside the box on screen.
        const frame = view.querySelector(".cam-frame").getBoundingClientRect();
        const boxRect = view.querySelector(".cam-box").getBoundingClientRect();
        const scale = Math.max(frame.width / video.videoWidth, frame.height / video.videoHeight);
        const offX = (frame.width - video.videoWidth * scale) / 2, offY = (frame.height - video.videoHeight * scale) / 2;
        const box = { x: (boxRect.left - frame.left - offX) / scale, y: (boxRect.top - frame.top - offY) / scale,
                      w: boxRect.width / scale, h: boxRect.height / scale };
        const still = document.createElement("canvas");
        still.width = video.videoWidth;
        still.height = video.videoHeight;
        still.getContext("2d").drawImage(video, 0, 0);
        closeCamera();
        scanLabel(still, box);
      });
    }

    // v18.3: leaving the app (switching apps, locking the phone, closing the tab) turns the camera off.
    document.addEventListener("visibilitychange", () => { if (document.hidden) closeCamera(); });
    window.addEventListener("pagehide", closeCamera);

    async function scanLabel(source, box) {
      const st = scanState;
      st.chosen = null;
      st.suggestions = [];
      try {
        const text = await readLabel(source, box, (msg) => { st.status = msg; renderScan(); });
        const found = suggestFromLabel(text);
        st.suggestions = found.suggestions;
        st.status = found.suggestions.length ? "Is it one of these?"
          : "Couldn't read the name. Try again with the name filling the box and no glare on it, or type the name below.";
      } catch (error) {
        st.status = error.message || "Couldn't read the label.";
      }
      renderScan();
    }

    // scanState: { status, suggestions, chosen, typed } while the scan panel is open.
    let scanState = null;
    const scanPanel = document.getElementById("scan-panel");
    document.getElementById("scan-button").addEventListener("click", () => {
      scanState = scanState ? null : { status: "", read: "", suggestions: [], chosen: null, typed: "" };
      if (!scanState) closeCamera(); // v18.3: closing the scan panel also switches the camera off
      renderScan();
    });

    function renderScan() {
      scanPanel.classList.toggle("hidden", !scanState);
      scanPanel.innerHTML = "";
      if (!scanState) return;
      const st = scanState;
      const intro = document.createElement("p");
      intro.className = "hint";
      intro.textContent = "Point the camera at the pot and line the paint's name up in the box. The app suggests a paint and you pick it. You can also just type the name.";
      const photo = document.createElement("input");
      photo.type = "file";
      photo.accept = "image/*";
      photo.id = "scan-photo";
      photo.className = "hidden";
      const take = document.createElement("button");
      take.className = "primary-button";
      take.style.width = "100%";
      take.textContent = "📷 Scan a label";
      take.addEventListener("click", openCamera);
      const fromPhoto = document.createElement("button");
      fromPhoto.className = "link-button";
      fromPhoto.textContent = "Use a photo instead";
      fromPhoto.addEventListener("click", () => photo.click());
      photo.addEventListener("change", async () => {
        const file = photo.files && photo.files[0];
        if (!file) return;
        try {
          const bitmap = await createImageBitmap(file);
          scanLabel(bitmap, null);
        } catch (error) {
          st.status = "Couldn't open that photo.";
          renderScan();
        }
      });

      const typed = document.createElement("input");
      typed.placeholder = "Or type a paint name, e.g. Macragge Blue";
      typed.setAttribute("aria-label", "Paint name");
      typed.id = "scan-typed";
      typed.value = st.typed;
      typed.style.marginTop = "10px";
      typed.style.width = "100%";
      typed.addEventListener("change", () => {
        st.typed = typed.value;
        const m = matchPaint(typed.value);
        st.chosen = null;
        st.read = "";
        st.suggestions = m.status === "sure" || m.status === "material" ? [m.paint] : m.suggestions.slice();
        if (m.status === "new") st.suggestions = [m.paint];
        st.status = !typed.value.trim() ? "" : st.suggestions.length ? "Is it one of these?" : "No match. Check the spelling.";
        renderScan();
      });
      scanPanel.append(intro, take, fromPhoto, photo, typed);

      if (st.status) {
        const s = document.createElement("p");
        s.className = "hint";
        s.id = "scan-status";
        s.style.margin = "10px 0 0";
        s.textContent = st.status;
        scanPanel.appendChild(s);
      }
      if (st.suggestions.length) {
        const chips = document.createElement("div");
        chips.className = "chips";
        for (const p of st.suggestions) {
          chips.appendChild(makeChip(p.name + (p.brand ? ` · ${p.brand}` : ""), !!st.chosen && sameText(st.chosen.name, p.name) && sameText(st.chosen.brand, p.brand), () => {
            st.chosen = p;
            if (st.typed && st.typed.trim() && !sameText(st.typed, p.name)) rememberShorthand(st.typed, p);
            renderScan();
          }));
        }
        scanPanel.appendChild(chips);
      }
      if (st.chosen) {
        const p = st.chosen;
        const mine = book.paints.find(x => sameText(x.name, p.name) && (!p.brand || !x.brand || sameText(x.brand, p.brand)));
        const box = document.createElement("div");
        box.className = "scan-result";
        box.id = "scan-result";
        const head = document.createElement("div");
        head.className = "paint-line";
        head.append(makeSwatch(mine ? mine.colour : p.colour || DEFAULT_PAINT_COLOUR), p.name + (p.brand ? ` · ${p.brand}` : ""));
        const verdict = document.createElement("p");
        verdict.className = "hint";
        verdict.style.margin = "6px 0 10px";
        const used = mine ? recipesUsingPaint(mine.id).length : 0;
        const mineStatus = mine ? paintStatus(mine) : "";   // v17
        verdict.textContent = mine
          ? `✓ Already in your palette${mineStatus ? ` · ${statusLabel(mineStatus).toLowerCase()}` : ""}${used ? `, used in ${plural(used, "recipe")}` : ""}.`
          : "Not in your palette yet.";
        box.append(head, verdict);
        if (mine) box.appendChild(buildStatusRow(mine));   // v17
        if (!mine) {
          const add = document.createElement("button");
          add.className = "primary-button";
          add.style.width = "100%";
          add.textContent = "Add to my palette";
          add.addEventListener("click", () => {
            // v18c-3: added and saved together. If storage is full the paint is taken back
            // out (so the palette shows what's really saved) and the message says so.
            const kept = changeAndSave(() => {
              const paint = findOrAddPaint(p.brand || "", p.name, p.colour || DEFAULT_PAINT_COLOUR);
              applyPaintStatus(paint, "owned");   // v17: scanned paints are Owned
              if (p.type === "material") paint.type = "material";
            });
            st.chosen = { ...p };
            renderPalette();
            renderScan();
            if (kept) showToast(`Added ${p.name} to your palette`);
            else showNotSaved(`Not added: storage on this device is full, so ${p.name} isn't in your palette. ` +
                              "Save a backup, free some space, then try again.");
          });
          box.appendChild(add);
        }
        scanPanel.appendChild(box);
      }
    }

    // ================= SETTINGS TAB =================

    // ----- Stage editor -----
    // You edit a DRAFT copy; nothing changes until you press Save.
    // Each draft row remembers which stage it started as ("from"), so when you reorder,
    // units move along with their stage instead of staying at the same position.

    const stageList = document.getElementById("stage-list");
    const doneFromSelect = document.getElementById("done-from");
    let draft = [];          // e.g. [{ name: "Primed", from: 3 }, { name: "New stage", from: null }]
    let draftDoneItem = null; // the draft row where Done starts

    function startDraft() {
      draft = STAGES.map((name, i) => ({ name, from: i }));
      draftDoneItem = draft[settings.doneFrom];
    }

    // v20.1: the colour each draft row will have once saved. With Custom on, a stage keeps
    // its own colour wherever it moves; a new stage gets the colour your starting set gives
    // that spot. Without Custom, colours are spread along the set as before.
    function draftColours() {
      if (!usingCustom()) return stageColours(settings.palette, draft.length);
      const mine = customColoursFor(STAGES.length);
      const fresh = stageColours(settings.palette, draft.length);
      return draft.map((item, i) => item.from !== null && mine[item.from] ? mine[item.from] : fresh[i]);
    }

    function renderStageEditor() {
      const colours = forShow(draftColours());
      stageList.innerHTML = "";
      draft.forEach((item, index) => {
        if (item === draftDoneItem) {
          const divider = document.createElement("li");
          divider.className = "done-divider";
          divider.textContent = "Done from here";
          stageList.appendChild(divider);
        }
        const row = document.createElement("li");
        row.className = "stage-row";

        const dot = document.createElement("span");
        dot.className = "dot";
        dot.style.setProperty("--dot", colours[index]);

        const input = document.createElement("input");
        input.value = item.name;
        input.setAttribute("aria-label", `Stage ${index + 1} name`);
        input.addEventListener("input", () => { item.name = input.value; refreshDoneOptions(); });

        const iconButton = (text, label, disabled, onClick, extraClass) => {
          const b = document.createElement("button");
          b.className = "icon-button" + (extraClass ? " " + extraClass : "");
          b.textContent = text;
          b.setAttribute("aria-label", label);
          b.disabled = disabled;
          b.addEventListener("click", onClick);
          return b;
        };

        // Swapping two neighbours in the list moves a stage up or down.
        const move = (offset) => {
          const target = index + offset;
          [draft[index], draft[target]] = [draft[target], draft[index]];
          renderStageEditor();
        };

        row.append(
          dot, input,
          iconButton("↑", `Move ${item.name} up`, index === 0, () => move(-1)),
          iconButton("↓", `Move ${item.name} down`, index === draft.length - 1, () => move(+1)),
          iconButton("✕", `Remove ${item.name}`, draft.length <= 2, () => {
            draft.splice(index, 1);
            if (!draft.includes(draftDoneItem)) draftDoneItem = draft[draft.length - 1];
            renderStageEditor();
          }, "remove"),
        );
        stageList.appendChild(row);
      });
      refreshDoneOptions();
    }

    // The "Done starts at" dropdown: any stage except the first.
    function refreshDoneOptions() {
      doneFromSelect.innerHTML = "";
      draft.forEach((item, index) => {
        if (index === 0) return;
        doneFromSelect.add(new Option(item.name.trim() || `Stage ${index + 1}`, index));
      });
      let doneIndex = draft.indexOf(draftDoneItem);
      if (doneIndex < 1) { doneIndex = Math.max(1, draft.length - 1); draftDoneItem = draft[doneIndex]; }
      doneFromSelect.value = doneIndex;
    }

    doneFromSelect.addEventListener("change", () => {
      draftDoneItem = draft[Number(doneFromSelect.value)];
      renderStageEditor();
    });

    document.getElementById("add-stage").addEventListener("click", () => {
      if (draft.length >= 10) { notify("You can have up to 10 stages."); return; }
      draft.push({ name: "New stage", from: null });
      renderStageEditor();
      const inputs = stageList.querySelectorAll("input");
      const last = inputs[inputs.length - 1];
      last.focus();
      last.select();
    });

    document.getElementById("reset-stages").addEventListener("click", () => {
      startDraft();
      renderStageEditor();
    });

    document.getElementById("save-stages").addEventListener("click", () => {
      const names = draft.map(item => item.name.trim());
      if (names.some(n => !n)) { notify("Every stage needs a name."); return; }
      const lower = names.map(n => n.toLowerCase());
      if (new Set(lower).size !== lower.length) { notify("Each stage needs a different name."); return; }

      // Work out where each OLD stage now sits. "map[old] = new".
      const map = new Array(STAGES.length);
      draft.forEach((item, newIndex) => { if (item.from !== null) map[item.from] = newIndex; });
      // A removed stage: its units drop to the nearest earlier stage that still exists.
      const removed = [];
      for (let old = 0; old < STAGES.length; old++) {
        if (map[old] !== undefined) continue;
        removed.push(old);
        let k = old - 1;
        while (k >= 0 && map[k] === undefined) k--;
        map[old] = k >= 0 ? map[k] : 0;
      }
      const affected = models.filter(m => stagesOf(m).some(st => removed.includes(st)));
      // v21.7: if some units are in a removed stage it asks in the app's own box first, and the
      // saving below runs when you say yes (or straight away when nobody is affected).
      const saveNow = () => {
        // v14: the units and the new stage list are saved TOGETHER. If there's no room,
        // everything goes back to how it was (before, the stages could be saved without
        // the units, which reset every unit to the first stage on the next open).
        const doneIndex = draft.indexOf(draftDoneItem);
        // v20.1: your Custom colours move with their stages (worked out before STAGES changes).
        const hadCustom = usingCustom() || (Array.isArray(settings.customColours) && settings.customColours.length > 0);
        const newCustom = hadCustom ? (() => {
          const mine = customColoursFor(STAGES.length);
          const fresh = stageColours(settings.palette, draft.length);
          return draft.map((item, i) => item.from !== null ? mine[item.from] : fresh[i]);
        })() : null;
        const kept = changeAndSave(() => {
          if (newCustom) settings.customColours = newCustom;
          models.forEach(m => {
            m.stage = map[m.stage];
            if (m.each) m.stages = m.stages.map(st => map[st]);
            if (Array.isArray(m.log)) m.log.forEach(e => { e[1] = map[e[1]]; });
            // v14: each photo's stage label moves with its stage too.
            if (Array.isArray(m.photos)) m.photos.forEach(p => { if (Number.isInteger(p.stage)) p.stage = map[p.stage]; });
          });
          settings.doneFrom = doneIndex;
          settings.stages = STAGES = names;
          fixDoneFrom();
        });
        if (!kept) { notify(fullMessage()); renderSettings(); return; }
        applyPalette(settings.palette);
        filters.stages = new Set();
        render();
        renderSettings();
        showToast("Stages saved");
      };
      if (affected.length) {
        askYesNo(`${affected.length} unit(s) are in a stage you've removed. They'll move to the nearest earlier stage. Continue?`,
          saveNow, { danger: true });
      } else {
        saveNow();
      }
    });

    // ----- Colours -----

    // Each palette runs from "not started" to "finished". You can have any number of
    // stages, so the app BLENDS between these colours to give each stage its own shade.
    const PALETTES = {
      ice:        { label: "Ice (original)",          colours: ["#64748b", "#6366f1", "#38bdf8", "#22d3ee", "#a7f3d0"] },
      frost:      { label: "Frost (higher contrast)", colours: ["#64748b", "#6366f1", "#38bdf8", "#2dd4bf", "#a7f3d0"] },
      greyscale:  { label: "Greyscale",               colours: ["#6b7280", "#8f96a3", "#b4bac4", "#d9dde3", "#ffffff"] },
      // Based on the Okabe-Ito colours, designed to stay distinct for common colour blindness.
      colourblind:{ label: "Colour-blind friendly",   colours: ["#8b95a5", "#56b4e9", "#cc79a7", "#e69f00", "#f0e442"] },
      // v20.1: the one warm set: ember red → orange → amber → gold → warm cream.
      forge:      { label: "Forge (warm)",            colours: ["#e0452b", "#f2701c", "#f59e0b", "#facc15", "#fde9c0"] },
    };

    // Mixes two colours: amount 0 = colour a, 1 = colour b, 0.5 = halfway.
    // "#38bdf8" is three pairs of hex digits (red 38, green bd, blue f8); we blend each pair.
    function mixColours(a, b, amount) {
      const partsA = [1, 3, 5].map(i => parseInt(a.slice(i, i + 2), 16));
      const partsB = [1, 3, 5].map(i => parseInt(b.slice(i, i + 2), 16));
      return "#" + partsA.map((value, k) =>
        Math.round(value + (partsB[k] - value) * amount).toString(16).padStart(2, "0")).join("");
    }

    // A list of n colours spread evenly along a palette.
    function stageColours(paletteName, n) {
      const colours = (PALETTES[paletteName] || PALETTES.ice).colours;
      const steps = colours.length - 1;
      return Array.from({ length: n }, (unused, index) => {
        const position = n === 1 ? 0 : index / (n - 1) * steps;
        const low = Math.floor(position);
        const high = Math.min(low + 1, steps);
        return mixColours(colours[low], colours[high], position - low);
      });
    }

    // ----- v20.1: Custom stage colours -----
    // settings.useCustom = true means "use my own colours". settings.customColours holds one
    // "#rrggbb" per stage, in the same order as the stages. settings.palette still names a
    // REAL set (the one Custom started from, and what Reset goes back to). That way an older
    // version of the app, which doesn't know Custom, simply shows that set and changes
    // nothing it doesn't understand (it keeps settings it doesn't know about).
    const goodHex = (value) => typeof value === "string" && /^#[0-9a-f]{6}$/i.test(value);
    const usingCustom = () => settings.useCustom === true;
    // A tidy copy of a saved list: at most 10 entries, anything that isn't a colour becomes "".
    function cleanCustomColours(raw) {
      return Array.isArray(raw) ? raw.slice(0, 10).map(c => goodHex(c) ? c.toLowerCase() : "") : [];
    }
    // Your colours for n stages. A missing or broken entry uses the colour your starting
    // set gives that stage, so there's always a sensible colour.
    function customColoursFor(n) {
      const saved = Array.isArray(settings.customColours) ? settings.customColours : [];
      return stageColours(settings.palette, n).map((fallback, i) => goodHex(saved[i]) ? saved[i].toLowerCase() : fallback);
    }
    // The colours in use now (before light mode deepens them): yours, or the set's.
    function chosenStageColours(n) {
      return usingCustom() ? customColoursFor(n) : stageColours(settings.palette, n);
    }
    // How a colour reads on the dark cards. Under 3 is too faint for a stage's name to be
    // read easily. (Light mode deepens pale colours by itself, so light cards are fine.)
    const DARK_CARD = "#141d2f";
    const FAINT_BELOW = 3;
    const tooFaintOnDark = (hex) => contrastRatio(hex, DARK_CARD) < FAINT_BELOW;

    // ----- v20: Appearance (Dark / Light / Match my phone) -----
    // settings.appearance is "dark" (the default), "light" or "auto" (follow the phone).
    const APPEARANCES = { dark: "Dark", light: "Light", auto: "Match my phone" };
    const phoneLight = window.matchMedia ? window.matchMedia("(prefers-color-scheme: light)") : null;
    const goodAppearance = (value) => Object.prototype.hasOwnProperty.call(APPEARANCES, value);
    // true when the app should be light right now.
    function isLight() {
      const choice = goodAppearance(settings.appearance) ? settings.appearance : "dark";
      return choice === "light" || (choice === "auto" && !!phoneLight && phoneLight.matches);
    }
    // Puts data-appearance="light" on the page (or takes it off), which swaps the colour
    // set at the top of the CSS. Also tells the phone what colour its top bar should be.
    function setAppearanceMark() {
      const light = isLight();
      if (light) document.documentElement.dataset.appearance = "light";
      else delete document.documentElement.dataset.appearance;
      const bar = document.querySelector('meta[name="theme-color"]');
      if (bar) bar.setAttribute("content", light ? "#e9eff6" : "#0b1220");
      return light;
    }
    // When the phone switches its own dark mode, follow it (only if "Match my phone" is on).
    if (phoneLight) {
      const follow = () => { if (settings.appearance === "auto") { applyPalette(settings.palette); render(); showAppearanceChoice(); renderCustomColours(); } };
      if (phoneLight.addEventListener) phoneLight.addEventListener("change", follow);
      else if (phoneLight.addListener) phoneLight.addListener(follow);   // older iPhones
    }

    // How easy a colour is to read against another, as a "contrast ratio": 1 = invisible,
    // 21 = black on white. Normal text needs at least 4.5. (The standard web formula.)
    function brightnessOf(hex) {
      const [r, g, b] = [1, 3, 5].map(i => {
        const c = parseInt(hex.slice(i, i + 2), 16) / 255;
        return c <= 0.03928 ? c / 12.92 : Math.pow((c + 0.055) / 1.055, 2.4);
      });
      return 0.2126 * r + 0.7152 * g + 0.0722 * b;
    }
    function contrastRatio(a, b) {
      const [x, y] = [brightnessOf(a), brightnessOf(b)].sort((p, q) => q - p);
      return (x + 0.05) / (y + 0.05);
    }
    // Hue / saturation / lightness back to "#rrggbb" (the opposite of hexToHsl).
    function hslToHex(h, sat, light) {
      const k = (n) => (n + h / 30) % 12;
      const a = sat * Math.min(light, 1 - light);
      const f = (n) => light - a * Math.max(-1, Math.min(k(n) - 3, Math.min(9 - k(n), 1)));
      return "#" + [0, 8, 4].map(n => Math.round(f(n) * 255).toString(16).padStart(2, "0")).join("");
    }
    // The lightest version of a colour (same hue and saturation) that still reads at
    // the given contrast on the light cards.
    const LIGHT_CARD = "#f8fafc";
    // v21.8: the light PAGE colour (a little darker than the cards). Some stage names sit
    // straight on the page (the big ▲ button, the Custom colour rows), so stage colours
    // are made readable against this one, which also covers the cards.
    const LIGHT_PAGE = "#e9eff6";
    function lightnessCap(h, sat, target, surface = LIGHT_CARD) {
      let low = 0, high = 1;
      for (let i = 0; i < 20; i++) {
        const mid = (low + high) / 2;
        if (contrastRatio(hslToHex(h, sat, mid), surface) >= target) low = mid; else high = mid;
      }
      return low;
    }
    // Light mode: pale stage colours are made deeper, so they stay readable on white.
    // Colours that already read well are left alone. A colour that was very pale goes a
    // little DEEPER than one that was only slightly too pale, so stages stay different
    // from each other (e.g. Greyscale's light greys and white become steps of darker grey).
    function deepenForLight(hex, target = 4.5, surface = LIGHT_CARD) {
      if (contrastRatio(hex, surface) >= target) return hex;
      const { h, s: sat, l } = hexToHsl(hex);
      const cap = lightnessCap(h, sat, target, surface);
      const over = cap < 1 ? Math.min(1, Math.max(0, (l - cap) / (1 - cap))) : 0;
      return hslToHex(h, sat, cap * (1 - 0.35 * over));
    }

    // ----- v21.8: dark mode readability -----
    // The mirror of deepenForLight. Some stage colours are too dark to read easily as text
    // on the dark cards (Ice, Frost, Greyscale and Forge had names at 3.5 to 4.5; the
    // target is 4.5). Only the colours that fall short are lightened, and only as far as
    // needed (same hue and saturation). The STORED colours never change; this is only how
    // they're shown. Greyscale needs one more step: its lightened greys would bunch up
    // against each other, so the whole run is spread out again between the lightened first
    // grey and the last (see readableOnDark).
    const READABLE = 4.5;
    // The smallest lightness (same hue and saturation) that reads at the target on the dark card.
    function lightnessFloor(h, sat, target) {
      let low = 0, high = 1;
      for (let i = 0; i < 20; i++) {
        const mid = (low + high) / 2;
        if (contrastRatio(hslToHex(h, sat, mid), DARK_CARD) >= target) high = mid; else low = mid;
      }
      return high;
    }
    function brightenForDark(hex, target = READABLE) {
      if (contrastRatio(hex, DARK_CARD) >= target) return hex;
      const { h, s: sat } = hexToHsl(hex);
      return hslToHex(h, sat, lightnessFloor(h, sat, target));
    }
    // How far apart the closest two neighbours in a list of colours are (plain colour distance).
    function closestNeighbours(list) {
      let least = Infinity;
      for (let i = 1; i < list.length; i++) {
        const a = list[i - 1], b = list[i];
        const gap = Math.hypot(...[1, 3, 5].map(k => parseInt(a.slice(k, k + 2), 16) - parseInt(b.slice(k, k + 2), 16)));
        if (gap < least) least = gap;
      }
      return least;
    }
    function readableOnDark(list, target = READABLE) {
      const lifted = list.map(c => brightenForDark(c, target));
      if (lifted.every((c, i) => c === list[i])) return list;           // nothing was too dark
      // Lightening should keep the stages apart. If it did, we're done.
      if (closestNeighbours(lifted) >= Math.min(closestNeighbours(list) * 0.6, 12)) return lifted;
      // Otherwise (a run of greys, getting lighter and lighter): spread the run out again.
      const lights = list.map(c => hexToHsl(c).l);
      for (let i = 1; i < lights.length; i++) if (lights[i] < lights[i - 1]) return lifted;
      const lowest = lights[0], highest = lights[lights.length - 1], span = highest - lowest || 1;
      return list.map((c, i) => {
        const { h, s: sat } = hexToHsl(c);
        const floor = lightnessFloor(h, sat, target);
        const placed = floor + (lights[i] - lowest) / span * (highest - floor);
        return hslToHex(h, sat, Math.max(placed, lights[i]));
      });
    }

    // The stage colours as they're SHOWN: lightened where needed in dark mode, deepened
    // ones in light mode.
    function shownStageColours(paletteName, n) {
      return forShow(stageColours(paletteName, n));
    }
    // v20.1: the same for any list of colours (e.g. your Custom ones).
    // v21.8: dark mode now lightens the ones that were too dark to read; light mode checks
    // against the page colour as well as the cards.
    function forShow(colours) {
      return isLight() ? colours.map(c => deepenForLight(c, READABLE, LIGHT_PAGE)) : readableOnDark(colours);
    }

    // Sets --stage-0, --stage-1 ... so everything using them updates instantly.
    // v20: also sets light or dark first, because that changes the stage colours.
    function applyPalette(name) {
      setAppearanceMark();
      // v20.1: your own colours when Custom is on.
      const colours = forShow(usingCustom() ? customColoursFor(STAGES.length) : stageColours(name, STAGES.length));
      colours.forEach((colour, index) => document.documentElement.style.setProperty(`--stage-${index}`, colour));
      document.documentElement.style.setProperty("--done-colour", colours[colours.length - 1]);
    }

    // v20: the Appearance buttons in Settings.
    const appearanceButtons = [...document.querySelectorAll("[data-appearance-choice]")];
    function showAppearanceChoice() {
      const choice = goodAppearance(settings.appearance) ? settings.appearance : "dark";
      for (const button of document.querySelectorAll("[data-appearance-choice]")) button.setAttribute("aria-pressed", String(button.dataset.appearanceChoice === choice));
      document.getElementById("appearance-note").textContent = choice === "auto"
        ? `Follows your phone's own dark mode setting. Right now: ${isLight() ? "light" : "dark"}.`
        : "";
      document.getElementById("palette-light-note").hidden = !isLight();
    }
    for (const button of appearanceButtons) {
      button.addEventListener("click", () => {
        settings.appearance = button.dataset.appearanceChoice;
        saveSettings();
        applyPalette(settings.palette);
        render();
        showAppearanceChoice();
        renderCustomColours();
      });
    }
    if (!goodAppearance(settings.appearance)) settings.appearance = "dark";
    showAppearanceChoice();

    const paletteSelect = document.getElementById("palette-select");
    for (const [key, palette] of Object.entries(PALETTES)) paletteSelect.add(new Option(palette.label, key));
    // v20.1: the 6th choice. "custom" is never stored as settings.palette (see usingCustom).
    paletteSelect.add(new Option("Custom (pick your own)", "custom"));
    if (!Object.prototype.hasOwnProperty.call(PALETTES, settings.palette)) settings.palette = "ice";
    if (settings.useCustom !== undefined && typeof settings.useCustom !== "boolean") settings.useCustom = false;
    if (settings.customColours !== undefined) settings.customColours = cleanCustomColours(settings.customColours);
    paletteSelect.value = usingCustom() ? "custom" : settings.palette;
    paletteSelect.addEventListener("change", () => {
      if (paletteSelect.value === "custom") {
        // Start from the set you had (or keep the colours you picked last time).
        settings.useCustom = true;
        if (!Array.isArray(settings.customColours) || !settings.customColours.some(goodHex)) {
          settings.customColours = stageColours(settings.palette, STAGES.length);
        }
      } else {
        settings.palette = paletteSelect.value;
        settings.useCustom = false;
      }
      saveSettings();
      applyPalette(settings.palette);
      renderStageEditor();
      renderCustomColours();
    });

    // ----- v20.1: the Custom colour list -----
    const customBox = document.getElementById("custom-colours");
    const customList = document.getElementById("custom-colour-list");
    const customReset = document.getElementById("custom-reset");
    // What a row says under the stage name: a warning if the colour is too faint on the
    // dark cards; in light mode, a note if it's shown deeper there.
    function customColourNote(hex, note) {
      const faint = tooFaintOnDark(hex);
      note.classList.toggle("faint", faint);
      note.textContent = faint
        ? "⚠ Too faint to read on dark cards. Try a brighter colour."
        : isLight() && contrastRatio(hex, LIGHT_PAGE) < READABLE
          ? "Shown a little deeper in light mode, so it's easy to read."
          : !isLight() && contrastRatio(hex, DARK_CARD) < READABLE
            ? "Shown a little brighter in dark mode, so it's easy to read."
            : "";
      note.hidden = !note.textContent;
    }
    function renderCustomColours() {
      customBox.hidden = !usingCustom();
      customList.innerHTML = "";
      if (!usingCustom()) return;
      const colours = customColoursFor(STAGES.length);
      const shown = forShow(colours);
      STAGES.forEach((name, index) => {
        const row = document.createElement("li");
        row.className = "custom-colour-row";
        row.style.setProperty("--stage-colour", shown[index]);
        const picker = document.createElement("input");
        picker.type = "color";
        picker.value = colours[index];
        picker.setAttribute("aria-label", `Colour for ${name}`);
        const text = document.createElement("span");
        text.className = "custom-colour-text";
        const title = document.createElement("strong");
        title.textContent = name;
        const note = document.createElement("small");
        text.append(title, note);
        customColourNote(colours[index], note);
        // While you drag, the whole app updates; it's saved when you let go.
        const use = (save) => {
          if (!goodHex(picker.value)) return;
          const list = customColoursFor(STAGES.length);
          list[index] = picker.value.toLowerCase();
          settings.customColours = list;
          applyPalette(settings.palette);
          row.style.setProperty("--stage-colour", forShow([list[index]])[0]);
          customColourNote(list[index], note);
          if (save) { saveSettings(); renderStageEditor(); }
        };
        picker.addEventListener("input", () => use(false));
        picker.addEventListener("change", () => use(true));
        row.append(picker, text);
        customList.appendChild(row);
      });
      const from = PALETTES[settings.palette] || PALETTES.ice;
      customReset.textContent = `Reset to ${from.label} colours`;
    }
    customReset.addEventListener("click", () => {
      const before = customColoursFor(STAGES.length);
      settings.customColours = stageColours(settings.palette, STAGES.length);
      saveSettings();
      applyPalette(settings.palette);
      renderStageEditor();
      renderCustomColours();
      showToast("Colours reset", () => {
        settings.customColours = before;
        saveSettings();
        applyPalette(settings.palette);
        renderStageEditor();
        renderCustomColours();
      });
    });
    renderCustomColours();

    // ----- Data summary and delete all -----

    const dataSummary = document.getElementById("data-summary");
    const storageNote = document.getElementById("storage-note");

    function renderSettings() {
      // v20: after a restore or a change in another window, show the right choices.
      showAppearanceChoice();
      showCountingChoice();   // v27
      if (usingCustom()) document.getElementById("palette-select").value = "custom";
      else if (PALETTES[settings.palette]) document.getElementById("palette-select").value = settings.palette;
      renderCustomColours();
      startDraft();
      renderStageEditor();
      renderFactionColours();
      let used = 0;
      try { used = (localStorage.getItem(STORAGE_KEY) || "").length + (localStorage.getItem(RECIPES_KEY) || "").length; } catch (ignored) {}
      const photos = models.reduce((sum, m) => sum + (m.photos || []).length + (m.photo ? 1 : 0), 0);
      const summary =
        `${models.length} units, ${modelCount(models)} models, ${plural(photos, "photo")}, ` +
        `${plural(book.recipes.length, "recipe")}. ` +
        `Units and recipes use about ${Math.max(1, Math.round(used / 1024))} KB of roughly 5,000 KB. ` +
        (settings.lastBackup ? `Last backup: ${shortDate(settings.lastBackup)}.` : "No backup saved yet.") +
        (photos ? (settings.lastFullBackup ? ` Last backup with photos: ${shortDate(settings.lastFullBackup)}.` : " Your photos haven't been backed up yet.") : "");
      dataSummary.textContent = summary;
      renderBackupAge();   // v16
      // v14: say whether the browser has promised to keep the data.
      if (navigator.storage && navigator.storage.persisted) {
        navigator.storage.persisted().then(kept => {
          storageNote.textContent = kept
            ? "This browser has agreed to keep the app's data, even if the device runs low on space."
            : "This browser hasn't promised to keep the app's data, so it could be cleared if the device runs low on space. Regular backups are your safety net.";
        }).catch(() => {});
      }
      // Photos are kept separately, with much more room. Ask the browser how much is used.
      if (navigator.storage && navigator.storage.estimate) {
        navigator.storage.estimate().then(({ usage, quota }) => {
          if (!usage || !quota) return;
          const mb = (bytes) => bytes >= 1e9 ? `${(bytes / 1e9).toFixed(1)} GB` : `${Math.max(1, Math.round(bytes / 1e6))} MB`;
          dataSummary.textContent = summary + ` Altogether (photos included) the app uses about ${mb(usage)} of ${mb(quota)} available.`;
        }).catch(() => {});
      }
      renderPhotoSummary();
      renderRecover();
    }

    // ----- Photo storage summary and clean-up (v11) -----
    // "Orphan" photos are files in the photo store that no unit points at any more, e.g.
    // after "Delete all units" or "Replace my collection". They just take up space.
    // Files still listed in one of the device's safety copies (kept by Delete all, Replace
    // and Restore) are NOT counted as orphans, so those copies keep their photos.
    const photoSummary = document.getElementById("photo-summary");
    const cleanPhotosButton = document.getElementById("clean-photos");
    const SAFETY_COPIES = ["-before-delete-all", "-before-replace", "-before-restore", "-before-recover"];
    const SAFETY_LABELS = {
      "-before-delete-all": "Before Delete all units",
      "-before-replace": "Before Replace my collection",
      "-before-restore": "Before Restore backup",
      "-before-recover": "Before your last Recover",
    };
    const SAFETY_DAYS = 30;

    // ----- Safety copies (v14) -----
    // Saved under the units' storage name + a suffix, e.g. "mini-tracker-models-before-delete-all".
    // Since v14 each one also holds the date and the stage list it was made with:
    //   { date: "2026-10-08", stages: [...], doneFrom, models: [...] }
    // Copies made before v14 are just the list of units; readSafetyCopy() reads both kinds.
    // keepSafetyCopy() returns false if there wasn't room, so the caller can STOP.
    function keepSafetyCopy(suffix) {
      const copy = { date: todayISO(), stages: STAGES, doneFrom: settings.doneFrom, models };
      try {
        localStorage.setItem(STORAGE_KEY + suffix, JSON.stringify(copy));
        return true;
      } catch (error) {
        return false;   // no room (or storage switched off): the old copy, if any, is left as it was
      }
    }
    function readSafetyCopy(suffix) {
      try {
        const raw = JSON.parse(localStorage.getItem(STORAGE_KEY + suffix) || "null");
        if (Array.isArray(raw)) return { date: null, stages: null, doneFrom: undefined, models: raw };
        if (raw && typeof raw === "object" && Array.isArray(raw.models)) return raw;
      } catch (ignored) {}
      return null;
    }
    // v18.3: a restore that replaces ONLY recipes keeps its own copy of your recipes, under
    // "shades-of-grey-recipes-before-recipes-restore" as { date, book }. It's separate from the
    // units copies, so it never mixes with (or overwrites) a copy kept by a full restore.
    const RECIPES_ONLY_COPY = "-before-recipes-restore";
    function keepRecipesCopy() {
      try {
        localStorage.setItem(RECIPES_KEY + RECIPES_ONLY_COPY, JSON.stringify({ date: todayISO(), book }));
        return true;
      } catch (error) { return false; }
    }
    function readRecipesCopy() {
      try {
        const raw = JSON.parse(localStorage.getItem(RECIPES_KEY + RECIPES_ONLY_COPY) || "null");
        if (raw && typeof raw === "object" && raw.book && typeof raw.book === "object") return raw;
      } catch (ignored) {}
      return null;
    }
    function forgetRecipesCopy() {
      try { localStorage.removeItem(RECIPES_KEY + RECIPES_ONLY_COPY); } catch (ignored) {}
    }
    function forgetSafetyCopy(suffix) {
      try { localStorage.removeItem(STORAGE_KEY + suffix); localStorage.removeItem(RECIPES_KEY + suffix); } catch (ignored) {}
    }
    // Run at start-up: copies older than 30 days are removed. Pre-v14 copies have no date,
    // so they're given today's date now (and are removed 30 days from now).
    function expireSafetyCopies() {
      for (const suffix of SAFETY_COPIES) {
        const copy = readSafetyCopy(suffix);
        if (!copy) continue;
        if (!copy.date) {
          copy.date = todayISO();
          try { localStorage.setItem(STORAGE_KEY + suffix, JSON.stringify(copy)); } catch (ignored) {}
        } else if (daysSince(copy.date) > SAFETY_DAYS) {
          forgetSafetyCopy(suffix);
        }
      }
      const recipesCopy = readRecipesCopy();
      if (recipesCopy && (!recipesCopy.date || daysSince(recipesCopy.date) > SAFETY_DAYS)) forgetRecipesCopy();
    }

    // The "Recover earlier data" list in Settings → Your data.
    function renderRecover() {
      const list = document.getElementById("recover-list");
      list.innerHTML = "";
      let any = false;
      for (const suffix of SAFETY_COPIES) {
        const copy = readSafetyCopy(suffix);
        if (!copy || !copy.models.length) continue;
        any = true;
        const li = document.createElement("li");
        const text = document.createElement("span");
        text.textContent = `${SAFETY_LABELS[suffix]}: ${plural(copy.models.length, "unit")}` +
          (copy.date ? `, saved ${shortDate(copy.date)}` : "");
        const button = document.createElement("button");
        button.className = "plain-button";
        button.textContent = "Recover";
        button.setAttribute("aria-label", `Recover: ${SAFETY_LABELS[suffix]}`);
        button.addEventListener("click", () => recoverSafetyCopy(suffix));
        li.append(text, button);
        list.appendChild(li);
      }
      // v18.3: the copy kept by a recipes-only restore is listed too.
      const recipesCopy = readRecipesCopy();
      if (recipesCopy) {
        any = true;
        const count = Array.isArray(recipesCopy.book.recipes) ? recipesCopy.book.recipes.length : 0;
        const li = document.createElement("li");
        const text = document.createElement("span");
        text.textContent = `Before Restore backup (recipes only): ${plural(count, "recipe")}` +
          (recipesCopy.date ? `, saved ${shortDate(recipesCopy.date)}` : "");
        const button = document.createElement("button");
        button.className = "plain-button";
        button.textContent = "Recover";
        button.setAttribute("aria-label", "Recover: Before Restore backup (recipes only)");
        button.addEventListener("click", recoverRecipesCopy);
        li.append(text, button);
        list.appendChild(li);
      }
      document.getElementById("recover-card").classList.toggle("hidden", !any);
    }

    // v18.3: put back the recipes kept by a recipes-only restore. Units aren't touched.
    function recoverRecipesCopy() {
      const copy = readRecipesCopy();
      if (!copy) { renderRecover(); return; }
      const restored = cleanRecipeBook(copy.book);
      askYesNo(`Replace your current ${plural(book.recipes.length, "recipe")} with the ${plural(restored.recipes.length, "recipe")} in this copy? (Your units stay as they are.)`, () => {
        const before = JSON.stringify(book);
        if (!changeAndSave(() => { book = restored; })) { notify(fullMessage()); return; }
        afterBigChange();
        showToast(`Recovered ${plural(book.recipes.length, "recipe")}`, () => {
          if (!changeAndSave(() => { book = cleanRecipeBook(JSON.parse(before)); })) { notify(fullMessage()); return; }
          afterBigChange();
        }, "Undo", 10);
      }, { danger: true });
    }

    // Swap your current units for a safety copy. Your current units are kept as a copy
    // themselves first ("Before your last Recover"), and Undo puts them straight back.
    function recoverSafetyCopy(suffix) {
      const copy = readSafetyCopy(suffix);
      if (!copy) { renderRecover(); return; }
      const copyStages = goodStageList(copy.stages) ? copy.stages.map(String) : null;
      // Clean the copy's units against its own stages, like a backup.
      const currentStages = STAGES;
      if (copyStages) STAGES = copyStages;
      const units = cleanModels(copy.models);
      STAGES = currentStages;
      const recipesCopy = (() => { try { return JSON.parse(localStorage.getItem(RECIPES_KEY + suffix) || "null"); } catch (e) { return null; } })();
      // v21.7: asks in the app's own box; the swap (and its Undo) happen when you say yes.
      askYesNo(`Replace your current ${plural(models.length, "unit")} with the ${plural(units.length, "unit")} in this copy` +
          (recipesCopy ? " (and its recipes)" : "") + "?", () => {
        if (models.length && suffix !== "-before-recover" && !keepSafetyCopy("-before-recover")) {
          notify("There isn't room on this device to keep a copy of your current units first, so nothing has changed. Please save a backup first.");
          return;
        }
        const undoState = { models: JSON.stringify(models), book: JSON.stringify(book), stages: STAGES.slice(), doneFrom: settings.doneFrom };
        const kept = changeAndSave(() => {
          models = units;
          if (recipesCopy) book = cleanRecipeBook(recipesCopy);
          if (copyStages) {
            settings.stages = STAGES = copyStages;
            if (copy.doneFrom !== undefined) settings.doneFrom = copy.doneFrom;
            fixDoneFrom();
          }
        });
        if (!kept) { notify(fullMessage()); return; }
        afterBigChange();
        showToast(`Recovered ${plural(units.length, "unit")}`, () => {
          const back = changeAndSave(() => {
            models = JSON.parse(undoState.models);
            book = JSON.parse(undoState.book);
            settings.stages = STAGES = undoState.stages;
            settings.doneFrom = undoState.doneFrom;
            fixDoneFrom();
          });
          if (!back) { notify(fullMessage()); return; }
          afterBigChange();
        }, "Undo", 10);
      }, { danger: true });
    }

    // Redraw everything after units, recipes or stages were swapped wholesale.
    function afterBigChange() {
      recipeDraft = null;
      openRecipeId = null;
      openIds.clear();
      clearFilters();
      applyPalette(settings.palette);
      render();
      renderSettings();
      loadThumbs().catch(() => {});
    }

    function sizeText(bytes) {
      if (bytes >= 1e9) return `${(bytes / 1e9).toFixed(1)} GB`;
      if (bytes >= 1e6) return `${(bytes / 1e6).toFixed(1)} MB`;
      return `${Math.max(1, Math.round(bytes / 1e3))} KB`;
    }
    // Look through every file in the photo store and sort them into in-use / spare.
    async function photoStoreReport() {
      const records = await photoStore("readonly", store => store.getAll());
      const inUse = new Set(pendingPhotoDeletes);   // waiting for Undo: not spare yet
      for (const m of models) for (const id of photoIds(m)) inUse.add(id);
      const safety = new Set();
      for (const suffix of SAFETY_COPIES) {
        const copy = readSafetyCopy(suffix);
        if (copy) for (const m of copy.models) for (const p of (m && m.photos) || []) if (p && p.id) safety.add(p.id);
      }
      // v14: also read the units list as SAVED right now, in case the app is open in
      // another window that has just added a photo this window hasn't heard about yet.
      try {
        const saved = JSON.parse(localStorage.getItem(STORAGE_KEY) || "[]");
        if (Array.isArray(saved)) for (const m of saved) for (const p of (m && m.photos) || []) if (p && p.id) inUse.add(p.id);
      } catch (ignored) {}
      const report = { count: 0, bytes: 0, orphans: [], orphanBytes: 0, safetyCount: 0 };
      for (const r of records || []) {
        const size = (r.full ? r.full.size : 0) + (r.thumb ? r.thumb.size : 0);
        if (inUse.has(r.id)) { report.count++; report.bytes += size; }
        else if (safety.has(r.id)) report.safetyCount++;
        else { report.orphans.push(r.id); report.orphanBytes += size; }
      }
      return report;
    }
    async function renderPhotoSummary() {
      try {
        const r = await photoStoreReport();
        let text = `Photo storage: ${plural(r.count, "photo")} using ${r.count ? sizeText(r.bytes) : "nothing"}.`;
        if (r.orphans.length) text += ` ${plural(r.orphans.length, "spare photo file")} (${sizeText(r.orphanBytes)}) no unit uses any more; Clean up photo storage removes ${r.orphans.length === 1 ? "it" : "them"}.`;
        if (r.safetyCount) text += ` ${plural(r.safetyCount, "more file")} belong to the safety copy kept by Delete all / Replace / Restore, and are kept.`;
        photoSummary.textContent = text;
        cleanPhotosButton.disabled = !r.orphans.length;
      } catch (error) {
        photoSummary.textContent = "Photo storage isn't available in this browser (for example in a private window).";
        cleanPhotosButton.disabled = true;
      }
    }
    cleanPhotosButton.addEventListener("click", async () => {
      const r = await photoStoreReport();
      if (!r.orphans.length) { renderPhotoSummary(); return; }
      askYesNo(`Delete ${plural(r.orphans.length, "photo file")} that no unit uses? This frees about ${sizeText(r.orphanBytes)}.`, async () => {
        for (const id of r.orphans) { forgetUrls(id); await deletePhotoFile(id); }
        showToast(`Cleaned up: ${plural(r.orphans.length, "photo file")} removed, about ${sizeText(r.orphanBytes)} freed`, null, null, 6);
        renderPhotoSummary();
      }, { danger: true });
    });

    document.getElementById("delete-all").addEventListener("click", () => {
      if (!models.length) return;
      // v21.7: asks in the app's own box; everything below runs when you say yes.
      askYesNo(`Delete all ${models.length} units? A copy is kept on this device for ${SAFETY_DAYS} days ` +
          `(Settings → Recover earlier data), but please save a backup first.`, () => {
        if (!models.length) return;
        // v14: STOP if the safety copy can't be kept, rather than delete with no safety net.
        if (!keepSafetyCopy("-before-delete-all")) {
          notify("There isn't room on this device to keep a safety copy of your units, so nothing has been deleted. " +
                "Please press Save backup first, then delete some photos or units you no longer need.");
          return;
        }
        const before = models;
        models = [];
        openIds.clear();
        clearFilters();
        render();
        renderSettings();
        showToast(`Deleted ${plural(before.length, "unit")}`, () => {
          models = before;
          render();
          renderSettings();
        }, "Undo", 10);
      }, { danger: true });
    });

    // ================= BACKUPS AND CSV =================

    // Hands the browser some text and asks it to download it as a file.
    function downloadFile(filename, text, type) {
      const blob = new Blob([text], { type });
      const link = document.createElement("a");
      link.href = URL.createObjectURL(blob);
      link.download = filename;
      link.click();
      setTimeout(() => URL.revokeObjectURL(link.href), 1000); // instantly can cancel it on some phones
    }

    function readFile(file, whenRead) {
      const reader = new FileReader();
      reader.onload = () => whenRead(reader.result);
      reader.readAsText(file);
    }

    // ----- v19.1: check a file BEFORE reading it -----
    // A very large file can freeze or crash a phone while it's read, and a picture picked by
    // mistake used to turn into nonsense units. So: a size limit for each kind of file, and
    // pictures, videos and other non-text files are refused straight away.
    const MAX_CSV_BYTES = 2 * 1024 * 1024;        // 2 MB: thousands of units (600 units is about 40 KB)
    const MAX_BACKUP_BYTES = 300 * 1024 * 1024;   // 300 MB: room for a full backup with hundreds of photos
    const NOT_TEXT_ENDINGS = /\.(jpe?g|png|gif|webp|heic|heif|bmp|tiff?|svg|mp4|mov|avi|mkv|mp3|m4a|wav|pdf|zip|rar|7z|gz|docx?|xlsx?|xlsm|pptx?|numbers|pages|key|exe|apk)$/i;
    function sizeText(bytes) { return bytes >= 1024 * 1024 ? Math.round(bytes / 1024 / 1024) + " MB" : Math.max(1, Math.round(bytes / 1024)) + " KB"; }
    function fileProblem(file, kind) {
      const what = kind === "csv" ? "a CSV file" : "a Minifolio backup";
      const type = String(file.type || "");
      if (/^(image|video|audio)\//.test(type) || NOT_TEXT_ENDINGS.test(file.name || "")) {
        return /\.(xlsx?|xlsm|numbers)$/i.test(file.name || "") && kind === "csv"
          ? `"${file.name}" is a spreadsheet file, not a CSV. In your spreadsheet app, use Save as (or Download) → CSV, then import that. Nothing has changed.`
          : `"${file.name}" isn't ${what} (it looks like a picture or another kind of file). Nothing has changed.`;
      }
      const limit = kind === "csv" ? MAX_CSV_BYTES : MAX_BACKUP_BYTES;
      if (file.size > limit) {
        return `"${file.name}" is too big (${sizeText(file.size)}; the limit for ${what} is ${sizeText(limit)}). It may not be the right file. Nothing has changed.`;
      }
      return "";
    }
    // After reading: a file that isn't really text (e.g. a picture renamed to .csv) is full of
    // "can't read this" marks or zero bytes.
    function looksLikeText(text) {
      const sample = String(text).slice(0, 20000);
      if (sample.includes("\u0000")) return false;
      const odd = (sample.match(/\uFFFD/g) || []).length;
      return odd <= Math.max(3, sample.length / 200);
    }

    // Backups include your stages, since a unit's stage is a position in that list.
    // Units carry notes about their photos (ids), but the pictures themselves are only in
    // the FULL backup, as text pictures in "photoFiles": { id: { full, thumb } }.
    function backupData() {
      return { app: "Minifolio", version: 6, dataVersion: DATA_VERSION, stages: STAGES, doneFrom: settings.doneFrom, models, recipes: book,
               factionColours: settings.factionColours,
               // v20: the look travels with the backup too. Older versions ignore these.
               palette: settings.palette, appearance: settings.appearance,
               // v20.1: Custom stage colours (on or off, and one colour per stage).
               useCustom: usingCustom(), customColours: Array.isArray(settings.customColours) && settings.customColours.length ? customColoursFor(STAGES.length) : [] };
    }

    document.getElementById("full-export-button").addEventListener("click", async (event) => {
      const button = event.currentTarget;
      button.disabled = true;
      button.textContent = "Preparing backup…";
      try {
        const backup = backupData();
        backup.photoFiles = {};
        let missing = 0;
        for (const m of models) for (const id of photoIds(m)) {
          const record = await getPhoto(id);
          if (!record) { missing++; continue; }
          backup.photoFiles[id] = { full: await blobToDataUrl(record.full), thumb: await blobToDataUrl(record.thumb) };
        }
        const today = todayISO();
        // No neat line breaks here: the file is big enough already.
        downloadFile(`minifolio-full-backup-${today}.json`, JSON.stringify(backup), "application/json");
        settings.lastBackup = today;
        settings.lastFullBackup = today;   // v14: photo backups are tracked separately
        saveSettings();
        renderSettings();
        const count = Object.keys(backup.photoFiles).length;
        showToast(`Full backup saved with ${plural(count, "photo")}` + (missing ? ` (${missing} couldn't be read)` : ""));
      } catch (error) {
        notify("Sorry, the full backup couldn't be made. Try Save backup (without photos) instead.");
      }
      button.disabled = false;
      button.textContent = "Save full backup with photos";
    });

    // Put the pictures from a full backup into the photo store. Returns how many worked.
    async function importPhotoFiles(files) {
      let done = 0;
      for (const [id, pair] of Object.entries(files || {})) {
        try {
          if (!pair || typeof pair.full !== "string" || !pair.full.startsWith("data:image")) continue;
          const full = dataUrlToBlob(pair.full);
          const thumb = typeof pair.thumb === "string" && pair.thumb.startsWith("data:image")
            ? dataUrlToBlob(pair.thumb) : await resizeToBlob(await loadImage(full), 240, 0.75);
          await putPhoto({ id, full, thumb });
          forgetUrls(id);   // in case an older copy of this photo was on screen
          done++;
        } catch (error) { /* skip that one */ }
      }
      return done;
    }

    // v22: the small backup's name and contents, shared by Save backup and Send backup to…
    // so the file is exactly the same either way.
    function smallBackupName(today) { return `minifolio-backup-${today}.json`; }
    function smallBackupText() { return JSON.stringify(backupData(), null, 2); }
    function noteBackupDone() {
      settings.lastBackup = todayISO();   // remembered so the app knows when to remind you
      saveSettings();
      renderSettings();
    }

    // Save backup (a download). `note` replaces the usual message (v22: Send backup to… uses
    // it to explain why it saved the file instead of sending it).
    function saveSmallBackup(note) {
      downloadFile(smallBackupName(todayISO()), smallBackupText(), "application/json");
      noteBackupDone();
      // v14: always say it worked, and that photos aren't in this one.
      const photos = models.reduce((sum, m) => sum + photoIds(m).length, 0);
      const photoWords = photos ? ` Your ${plural(photos, "photo")} aren't in it: use Save full backup with photos for those.` : "";
      showToast(note
        ? note + photoWords
        : photos
          ? `Backup saved, without your ${plural(photos, "photo")}. Use Save full backup with photos for those.`
          : "Backup saved. Keep the file somewhere safe, like OneDrive or email.", null, null, note ? 10 : 6);
    }
    document.getElementById("export-button").addEventListener("click", () => saveSmallBackup());

    // v22: Send backup to… hands the same file to the phone's share menu. The app sends nothing
    // itself: the share menu only goes where the person picks. If the browser can't share files,
    // or the share fails (not if the person closes the menu), the backup is saved instead.
    document.getElementById("share-button").addEventListener("click", async () => {
      const file = new File([smallBackupText()], smallBackupName(todayISO()), { type: "application/json" });
      let canShare = false;
      try { canShare = typeof navigator.share === "function" && typeof navigator.canShare === "function" && navigator.canShare({ files: [file] }); } catch (error) { canShare = false; }
      if (!canShare) {
        saveSmallBackup("This browser can't send files to other apps, so the backup was saved to your device instead.");
        return;
      }
      try {
        await navigator.share({ files: [file], title: "Minifolio backup" });
        noteBackupDone();
        showToast("Backup sent. Keep it somewhere safe, like OneDrive or email.", null, null, 6);
      } catch (error) {
        if (error && error.name === "AbortError") return;   // the person closed the menu: nothing happened
        saveSmallBackup("The share menu couldn't send the backup, so it was saved to your device instead.");
      }
    });

    // The red banner's buttons (v14).
    document.getElementById("banner-backup").addEventListener("click", () => document.getElementById("export-button").click());
    document.getElementById("banner-retry").addEventListener("click", () => {
      if (dataTooNew) { location.reload(); return; }
      if (saveAll()) showToast("Saved. Everything is up to date.");
      else notify("Still full. Please save a backup, then free some space (delete photos or units you no longer need).");
    });

    const restoreFile = document.getElementById("restore-file");
    document.getElementById("restore-button").addEventListener("click", () => restoreFile.click());
    restoreFile.addEventListener("change", () => {
      const file = restoreFile.files[0];
      if (!file) return;
      // v19.1: refuse pictures and very large files before reading anything.
      const problem = fileProblem(file, "backup");
      if (problem) { restoreFile.value = ""; notify(problem); return; }
      readFile(file, (text) => {
        restoreFile.value = "";
        let parsed;
        try { parsed = JSON.parse(text); } catch (error) { parsed = null; }
        const isList = Array.isArray(parsed);   // the oldest backups are just a list of units
        if (!parsed || (!isList && typeof parsed !== "object")) {
          notify("That file doesn't look like a Minifolio backup.");
          return;
        }
        // v19.1: each main part must be the right kind of thing (a list of units, a recipe
        // book, a set of photos), or the file is refused before anything changes.
        const wrongShape = !isList && (
          (parsed.models !== undefined && !Array.isArray(parsed.models)) ||
          (parsed.recipes !== undefined && (parsed.recipes === null || typeof parsed.recipes !== "object" || Array.isArray(parsed.recipes))) ||
          (parsed.photoFiles !== undefined && (parsed.photoFiles === null || typeof parsed.photoFiles !== "object" || Array.isArray(parsed.photoFiles))));
        if (wrongShape) {
          notify("This backup is damaged (part of it isn't laid out the way Minifolio saves it), so it can't be restored safely. Nothing has changed.");
          return;
        }
        // v18.3: a backup saved by a NEWER version of the app might hold things this copy
        // doesn't understand (and would drop), so it asks you to update first.
        if (!isList && Number(parsed.dataVersion) > DATA_VERSION) {
          notify("This backup was saved by a newer version of Minifolio. Please reload the app to update it, then restore again. Nothing has changed.");
          return;
        }
        // v14: a damaged stage list (blank or repeated names, or more than 10) is refused,
        // because every unit's stage is a position in that list.
        if (!isList && parsed.stages !== undefined && !goodStageList(parsed.stages)) {
          notify("This backup's list of stages is damaged (blank or repeated names, or more than 10), so it can't be restored safely. Nothing has changed.");
          return;
        }
        const backupStages = !isList && parsed.stages ? parsed.stages.map(String) : null;
        const backupModels = isList ? parsed : (Array.isArray(parsed.models) ? parsed.models : []);

        // Clean the units against the backup's own stages, BEFORE touching your data.
        const currentStages = STAGES;
        if (backupStages) STAGES = backupStages;
        const restored = cleanModels(backupModels);
        STAGES = currentStages;
        // Backups from v5 onwards also hold recipes. Older ones don't, so your recipes stay.
        const backupBook = !isList && parsed.recipes && typeof parsed.recipes === "object" ? cleanRecipeBook(parsed.recipes) : null;
        const hasRecipes = !!backupBook && (backupBook.recipes.length > 0 || backupBook.paints.length > 0 || backupBook.schemes.length > 0);
        // v14: a backup with recipes but no units is fine too: it replaces only your recipes.
        const unitsToo = restored.length > 0;
        if (!unitsToo && !hasRecipes) {
          notify("That file doesn't look like a Minifolio backup: it has no units or recipes in it.");
          return;
        }
        const photoFiles = !isList && parsed.photoFiles && typeof parsed.photoFiles === "object" ? parsed.photoFiles : null;
        const photoCount = photoFiles ? Object.keys(photoFiles).length : 0;
        const question = (!unitsToo
            ? `Replace your ${plural(book.recipes.length, "recipe")} with ${plural(backupBook.recipes.length, "recipe")} from the backup? (Your units stay as they are.)`
            : backupBook
            ? `Replace your current ${plural(models.length, "unit")} and ${plural(book.recipes.length, "recipe")} with ` +
              `${plural(restored.length, "unit")} and ${plural(backupBook.recipes.length, "recipe")} from the backup?`
            : `Replace your current ${models.length} units with ${restored.length} from the backup? (Your recipes stay as they are.)`)
          + (photoCount ? ` It includes ${plural(photoCount, "photo")}.` : "");
        // v21.7: asks in the app's own box; the restore runs when you say yes.
        askYesNo(question, () => {
          (photoFiles ? importPhotoFiles(photoFiles) : Promise.resolve(0)).then(async (imported) => {
            // Safety copies of what you had (best effort), listed under Recover earlier data.
            if (unitsToo) keepSafetyCopy("-before-restore");
            if (unitsToo && backupBook) { try { localStorage.setItem(RECIPES_KEY + "-before-restore", JSON.stringify(book)); } catch (ignored) {} }
            // v18.3: a recipes-only restore keeps its own copy (listed under Recover earlier data)
            // and gets an Undo button.
            if (!unitsToo) keepRecipesCopy();
            const recipesBefore = unitsToo ? null : JSON.stringify(book);

            // v14: units, recipes, stages and colours are saved TOGETHER, or not at all.
            const kept = changeAndSave(() => {
              if (unitsToo) models = restored;
              if (backupBook) book = backupBook;
              if (unitsToo && backupStages) {
                settings.stages = STAGES = backupStages;
                settings.doneFrom = parsed.doneFrom;
                fixDoneFrom();
              }
              // Backups from v8 onwards hold faction colours. Older ones don't, so yours stay.
              if (unitsToo && !isList && parsed.factionColours) settings.factionColours = cleanFactionColours(parsed.factionColours);
              // v20: backups from v20 onwards hold the stage colour set and Appearance.
              // Anything unknown is ignored, so older backups leave yours as they are.
              if (unitsToo && !isList && typeof parsed.palette === "string" && Object.prototype.hasOwnProperty.call(PALETTES, parsed.palette)) settings.palette = parsed.palette;
              if (unitsToo && !isList && goodAppearance(parsed.appearance)) settings.appearance = parsed.appearance;
              // v20.1: Custom colours. Backups from before v20.1 don't have them, so yours stay.
              if (unitsToo && !isList && Array.isArray(parsed.customColours)) settings.customColours = cleanCustomColours(parsed.customColours);
              if (unitsToo && !isList && typeof parsed.useCustom === "boolean") settings.useCustom = parsed.useCustom;
            });
            if (!kept) { notify(fullMessage()); return; }
            recipeDraft = null;
            openRecipeId = null;
            openIds.clear();
            clearFilters();
            applyPalette(settings.palette);
            render();
            renderSettings();

            // v14: check every photo the restored units need is really on this device. If
            // some couldn't be loaded, say so clearly (they're removed from the units next).
            let missing = 0, needed = 0;
            if (unitsToo) {
              for (const m of models) for (const id of photoIds(m)) {
                needed++;
                try { if (!(await getPhoto(id))) missing++; } catch (error) { missing++; }
              }
            }
            if (missing) {
              notify(photoFiles
                ? `Backup restored, but ${missing} of ${plural(needed, "photo")} couldn't be loaded on this device (${imported} of ${photoCount} in the file worked), so they won't show. Keep the backup file safe: you can restore it again later, for example after freeing some space.`
                : `Backup restored, but this backup was saved without photos, so ${plural(missing, "photo")} won't show on this device. Keep the backup file safe. To bring photos across, use Save full backup with photos on the other device.`);
            } else {
              if (unitsToo) showToast("Backup restored");
              else showToast(`Recipes restored (${plural(book.recipes.length, "recipe")})`, () => {
                if (!changeAndSave(() => { book = cleanRecipeBook(JSON.parse(recipesBefore)); })) { notify(fullMessage()); return; }
                afterBigChange();
                showToast("Your recipes are back as they were");
              }, "Undo", 10);
            }
            // Old backups may hold old-style photos: move them. Then load the thumbnails.
            startPhotos();
          });
        }, { danger: true });
      });
    });

    // Turns CSV text into rows of cells. A value can contain a comma if it's wrapped in
    // quotes, e.g. "Boyz, mob 2", so we read one character at a time.
    function parseCSV(text) {
      const rows = [];
      let row = [];
      let cell = "";
      let insideQuotes = false;
      for (let i = 0; i < text.length; i++) {
        const char = text[i];
        if (insideQuotes) {
          if (char === '"' && text[i + 1] === '"') { cell += '"'; i++; } // "" means a real quote mark
          else if (char === '"') insideQuotes = false;
          else cell += char;
        } else if (char === '"' && cell === "") {
          insideQuotes = true;       // a quote only opens a quoted value at the start of a cell
        } else if (char === ",") {
          row.push(cell); cell = "";
        } else if (char === "\n") {
          row.push(cell); rows.push(row); row = []; cell = "";
        } else if (char !== "\r") {
          cell += char;
        }
      }
      row.push(cell);
      rows.push(row);
      return rows.filter(r => r.some(c => c.trim() !== ""));
    }

    // A stage number from a stage name (any capitals) or a number. Unknown = first stage.
    function stageFromText(text) {
      const cleaned = (text || "").trim().toLowerCase();
      const byName = STAGES.findIndex(s => s.toLowerCase() === cleaned);
      if (byName !== -1) return byName;
      const asNumber = Number(cleaned);
      if (cleaned !== "" && Number.isInteger(asNumber) && asNumber >= 0 && asNumber < STAGES.length) return asNumber;
      return 0;
    }

    // v19.1: CSV rows to units. The FIRST line must be the column titles and include "name";
    // the other columns are found by their titles, so they can be in any order (or missing).
    // Without a "name" title the file is refused, so a random file can't become units.
    const CSV_COLUMNS = { name: ["name", "unit", "unit name"], game: ["game", "hobby"], faction: ["faction", "army"],
      stage: ["stage"], nickname: ["nickname"], count: ["count", "models", "number"], repaint: ["repaint"], notes: ["notes", "note"] };
    function csvToUnits(rows) {
      rows = rows.filter(cells => cells.some(c => String(c).trim()));
      const noName = 'This file has no "name" column, so Minifolio can\'t tell which column holds your unit names. ' +
        'The first line should be the column titles: name, game, faction, stage, nickname, count, repaint, notes ' +
        '(only "name" is needed). CSV template in Settings gives you an example. Nothing has changed.';
      if (!rows.length) return { problem: "That file is empty. Nothing has changed." };
      const titles = rows[0].map(c => plainQuotes(String(c)).trim().toLowerCase());
      const col = {};
      for (const [key, words] of Object.entries(CSV_COLUMNS)) col[key] = titles.findIndex(t => words.includes(t));
      if (col.name < 0) return { problem: noName };
      const cell = (cells, key) => col[key] < 0 ? "" : String(cells[col[key]] || "").trim();
      const unknownStages = new Set();
      const units = [];
      for (const cells of rows.slice(1)) {
        const name = plainQuotes(cell(cells, "name"));
        if (!name) continue;
        const stageText = cell(cells, "stage");
        const n = Number(stageText);
        const validNumber = stageText !== "" && Number.isInteger(n) && n >= 0 && n < STAGES.length;
        if (stageText && !STAGES.some(s => s.toLowerCase() === stageText.toLowerCase()) && !validNumber) {
          unknownStages.add(stageText);
        }
        units.push({
          name,
          hobby: cell(cells, "game"),
          faction: plainQuotes(cell(cells, "faction")),
          stage: stageFromText(stageText),
          nickname: cell(cells, "nickname"),
          count: cleanCount(cell(cells, "count")),
          repaint: ["yes", "y", "true", "1"].includes(cell(cells, "repaint").toLowerCase()),
          note: cell(cells, "notes"),
        });
      }
      return { units, unknownStages };
    }

    // Import CSV reads the file, then shows the review so you can choose Add or Replace.
    const csvFile = document.getElementById("csv-file");
    document.getElementById("csv-button").addEventListener("click", () => {
      placeImportArea("settings");   // v19: the check shows here, under the Settings buttons
      csvFile.click();
    });
    csvFile.addEventListener("change", () => {
      const file = csvFile.files[0];
      if (!file) return;
      // v19.1: refuse pictures and very large files before reading anything.
      const problem = fileProblem(file, "csv");
      if (problem) { csvFile.value = ""; notify(problem); return; }
      readFile(file, (text) => {
        csvFile.value = "";
        if (!looksLikeText(text)) { notify(`"${file.name}" isn't a CSV file (it isn't plain text). Nothing has changed.`); return; }
        const read = csvToUnits(parseCSV(text.replace(/^﻿/, "")));   // ﻿: an invisible mark Excel adds
        if (read.problem) { notify(read.problem); return; }
        const { units, unknownStages } = read;
        if (!units.length) { notify("No units found in that file."); return; }
        whPanel.classList.add("hidden");
        openReview({ source: "csv", title: `"${file.name}"`, rows: units, unknownStages: [...unknownStages] });
      });
    });

    document.getElementById("template-button").addEventListener("click", () => {
      const last = STAGES[STAGES.length - 1];
      const template =
        "name,game,faction,stage,nickname,count,repaint,notes\n" +
        `Intercessors,40K,Ultramarines,${STAGES[0]},,5,no,\n` +
        `Intercessors,40K,Ultramarines,${STAGES[Math.min(3, STAGES.length - 1)]},The Gold Squad,5,no,\n` +
        `Redemptor Dreadnought,40K,Ultramarines,${last},,1,yes,"Magnetised, so can swap guns"\n`;
      downloadFile("minifolio-template.csv", template, "text/csv");
    });


    // ================= EXPORT CSV =================
    // The same columns Import CSV reads, so a file can go out to Excel and back in again.
    // A value with a comma, quote or new line is wrapped in quotes ("" means a real quote).
    function csvCell(value) {
      const text = String(value === undefined || value === null ? "" : value);
      return /[",\n\r]/.test(text) ? '"' + text.replace(/"/g, '""') + '"' : text;
    }
    document.getElementById("csv-export-button").addEventListener("click", () => {
      if (!models.length) { notify("There are no units to export yet."); return; }
      const header = "name,game,faction,stage,nickname,count,repaint,notes";
      const rows = models.map(m => [m.name, m.hobby, m.faction, STAGES[m.stage], m.nickname || "",
        m.count || 1, m.repaint ? "yes" : "no", m.note || ""].map(csvCell).join(","));
      const today = todayISO();
      // "﻿" at the start helps Excel read accents and curly quotes properly.
      downloadFile(`minifolio-${today}.csv`, "﻿" + [header, ...rows].join("\r\n") + "\r\n", "text/csv");
    });

    // ================= IMPORT FROM THE WARHAMMER APP =================
    // The Warhammer app's "export as text" looks like this:
    //   Monty murder (1995 points)        <- the list's own name
    //                                     <- blank line
    //   T’au Empire                       <- the faction
    //   ...detachment and size lines...
    //   Riptide Battlesuit (215 points)   <- a UNIT: a name followed by its points
    //     • 1x Ion accelerator            <- wargear
    //   Pathfinder Team (100 points)
    //     • 1x Pathfinder Shas’ui         <- a MODEL line: it has deeper bullets under it
    //       • 1x Close combat weapon
    //     • 9x Pathfinder                 <- another model line, so this unit has 10 models
    // A bullet with more-indented bullets under it is a model; one without is wargear.
    // A unit with no model lines is a single model (characters, vehicles).

    // Curly quotes (’ “ ”) become plain ones, so "T’au" matches "T'au".
    function plainQuotes(text) {
      return text.replace(/[‘’ʼ]/g, "'").replace(/[“”]/g, '"');
    }

    function parseWarhammerList(text) {
      const lines = plainQuotes(text).replace(/\r/g, "").split("\n");
      const unitPattern = /^\s*(.+?)\s*\((\d+)\s*(?:points?|pts)\)\s*$/i;
      const bulletPattern = /^(\s*)•\s*(.*)$/;
      const nonEmpty = lines.map((l, i) => i).filter(i => lines[i].trim() !== "");
      if (!nonEmpty.length) return null;

      // The first line is the list's name; the next non-empty line is the faction.
      const first = nonEmpty[0];
      const listName = (lines[first].match(unitPattern) || [])[1] || lines[first].trim();
      const factionLine = nonEmpty[1] !== undefined ? lines[nonEmpty[1]].trim() : "";
      const faction = unitPattern.test(factionLine) ? "" : factionLine;
      const startAt = faction ? 2 : 1;   // no faction line? then line 2 may already be a unit

      const units = [];
      let current = null;
      for (let n = startAt; n < nonEmpty.length; n++) {
        const line = lines[nonEmpty[n]];
        if (/^exported with/i.test(line.trim())) break;
        const unitMatch = line.match(unitPattern);
        // A real unit always has bullet lines under it. This skips lines like
        // "Strike Force (2000 points)", which also end in points.
        const followedByBullet = n + 1 < nonEmpty.length && bulletPattern.test(lines[nonEmpty[n + 1]]);
        if (unitMatch && !bulletPattern.test(line) && followedByBullet) {
          // Only the NAME is kept. The points are deliberately thrown away (v14): the app
          // never stores points, as they're Games Workshop's data.
          current = { name: unitMatch[1].trim(), models: 0 };
          units.push(current);
          continue;
        }
        const bullet = line.match(bulletPattern);
        if (!current || !bullet) continue;
        const countMatch = bullet[2].match(/^(\d+)x\s+/);
        if (!countMatch) continue;
        // Look at the next line: is it a bullet indented further than this one?
        const nextLine = n + 1 < nonEmpty.length ? lines[nonEmpty[n + 1]] : "";
        const nextBullet = nextLine.match(bulletPattern);
        if (nextBullet && nextBullet[1].length > bullet[1].length) current.models += Number(countMatch[1]);
      }
      for (const u of units) u.count = u.models || 1;
      return units.length ? { listName, faction, units } : null;
    }

    // Names compared loosely: capitals, hyphens, quotes and spaces don't matter,
    // so "Screamer-Killer" matches "Screamer Killer" and "Breacher Team" matches "Breacher team".
    function looseName(text) {
      return plainQuotes(text || "").toLowerCase().replace(/[^a-z0-9]/g, "");
    }

    // ================= THE IMPORT REVIEW =================
    // Import CSV and Warhammer app list both end up here. You choose:
    //   1. Add to your collection, or Replace it.
    //   2. Which units to bring in (tick boxes).
    //   3. For name clashes (a unit you have under a different name), which name to keep.
    //      Warhammer app names are the default; for a CSV file, your current name is.
    // Nothing changes until you press the button at the bottom, and Undo puts it all back.

    // Matching names, used to spot units you already have.
    //   - the same name, ignoring capitals, spaces and hyphens ("Screamer Killer"), or
    //   - every key word of your name appears in the incoming name. Filler words like
    //     "team", "squad" and "battlesuit" don't count, and plurals are ignored. So your
    //     "Pathfinder squad" matches "Pathfinder Team", and "Enforcer commander" matches
    //     "Commander in Enforcer Battlesuit". But "Hyperadapted Raveners" does NOT match
    //     plain "Raveners", because "hyperadapted" isn't in that name.
    const FILLER_WORDS = new Set(["team", "squad", "unit", "battlesuit", "in", "the", "of", "and", "with", "mob", "pack", "brood"]);
    function keyWords(name) {
      return plainQuotes(name).toLowerCase().split(/[^a-z0-9]+/)
        .map(w => w.length > 3 ? w.replace(/s$/, "") : w)   // "raveners" -> "ravener"
        .filter(w => w && !FILLER_WORDS.has(w) && !/^\d+$/.test(w));   // "Squad 1": the 1 doesn't count
    }
    function namesMatch(yourName, theirName) {
      if (looseName(yourName) === looseName(theirName)) return "exact";
      const mine = keyWords(yourName);
      const theirs = new Set(keyWords(theirName));
      return mine.length && mine.every(w => theirs.has(w)) ? "close" : "";
    }

    const reviewBox = document.getElementById("review");
    const reviewTitle = document.getElementById("review-title");
    const reviewSummary = document.getElementById("review-summary");
    const reviewModeBox = document.getElementById("review-mode");
    const modeButtons = reviewBox.querySelectorAll(".mode-button");
    const reviewWhFields = document.getElementById("review-wh-fields");
    const reviewStageLabel = document.getElementById("review-stage-label");
    const reviewClashNote = document.getElementById("review-clash-note");
    const reviewList = document.getElementById("review-list");
    const reviewGo = document.getElementById("review-go");
    const whPanel = document.getElementById("wh-panel");
    const whText = document.getElementById("wh-text");
    const whGame = document.getElementById("wh-game");
    const whFaction = document.getElementById("wh-faction");
    const whStage = document.getElementById("wh-stage");

    let incoming = null;     // { source: "csv" or "wh", title, rows: [...], unknownStages: [...] }
    let reviewMode = "add";  // "add" or "replace"
    let choices = [];        // one per row: { tick: true/false, keep: "theirs" or "yours" }

    // The incoming rows with game/faction filled in (Warhammer lists take them from the boxes).
    function incomingRows() {
      if (incoming.source !== "wh") return incoming.rows;
      return incoming.rows.map(r => ({ ...r, hobby: whGame.value.trim(), faction: whFaction.value.trim() }));
    }

    // Pairs each incoming unit with one you already have, if any. Each of your units is
    // only used once, so owning 2 Lictors covers 2 Lictors in the list, not 3.
    // Two passes: exact names first for EVERY row, then close matches for what's left.
    // (Otherwise "Winged Hive Tyrant" could grab your "Hive Tyrant" before the list's
    // own "Hive Tyrant" row gets to it.)
    // kind: "exact" (same name), "spelling" (only capitals/hyphens/spaces differ),
    //       "close" (a possible match, e.g. "Pathfinder squad" vs "Pathfinder Team").
    function matchRows() {
      const unused = models.slice();
      const rows = incomingRows();
      const result = rows.map(row => ({ row, match: null, kind: null }));
      const sameFaction = (m, row) => looseName(m.faction) === looseName(row.faction);
      for (const r of result) {
        const i = unused.findIndex(m => sameFaction(m, r.row) && namesMatch(m.name, r.row.name) === "exact");
        if (i !== -1) {
          r.match = unused.splice(i, 1)[0];
          r.kind = r.match.name === r.row.name ? "exact" : "spelling";
        }
      }
      for (const r of result) {
        if (r.match) continue;
        const i = unused.findIndex(m => sameFaction(m, r.row) && namesMatch(m.name, r.row.name) === "close");
        if (i !== -1) { r.match = unused.splice(i, 1)[0]; r.kind = "close"; }
      }
      return result;
    }

    // What each row will do by default.
    //   keep: "theirs" = use the incoming name, "yours" = keep your name,
    //         "different" = not the same unit after all, so add it as new.
    function defaultChoice(m) {
      const fromApp = incoming.source === "wh";
      if (reviewMode === "replace") return { tick: true, keep: "theirs" };
      if (!m.match) return { tick: true, keep: "theirs" };
      return { tick: false, keep: m.kind === "exact" ? "yours" : (fromApp ? "theirs" : "yours") };
    }

    function setDefaultChoices() {
      choices = matchRows().map(defaultChoice);
    }

    // After the faction box changes, only reset rows whose match actually changed,
    // so your ticks and name choices aren't thrown away.
    function refreshChoices() {
      const before = lastMatches;
      choices = matchRows().map((m, i) => {
        const old = before && before[i];
        const same = old && old.kind === m.kind && (old.match && old.match.id) === (m.match && m.match.id);
        return same && choices[i] ? choices[i] : defaultChoice(m);
      });
    }
    let lastMatches = null;

    function openReview(data) {
      incoming = data;
      reviewMode = "add";
      const isWh = data.source === "wh";
      reviewTitle.textContent = isWh ? "Check your army list" : "Check your CSV import";
      reviewWhFields.classList.toggle("hidden", !isWh);
      reviewStageLabel.classList.toggle("hidden", !isWh);
      whStage.innerHTML = "";
      STAGES.forEach((s, i) => whStage.add(new Option(s, i)));
      setDefaultChoices();
      renderReview();
      reviewBox.classList.remove("hidden");
      refreshUnitsImport();
      reviewBox.scrollIntoView({ behavior: "smooth", block: "start" });
    }

    function closeReview() {
      incoming = null;
      reviewBox.classList.add("hidden");
      refreshUnitsImport();
    }

    function plural(n, word) { return `${n} ${word}${n === 1 ? "" : "s"}`; }

    // Renames to make: one per matched unit (by id), only where you chose the incoming name.
    function renamesToMake(matched) {
      if (reviewMode !== "add") return [];
      return matched
        .filter((m, i) => m.match && m.kind !== "exact" && choices[i].keep === "theirs")
        .map(m => ({ id: m.match.id, from: m.match.name, to: m.row.name, faction: m.match.faction }));
    }

    function renderReview() {
      const matched = matchRows();
      lastMatches = matched;
      const rows = matched.map(m => m.row);
      const fromApp = incoming.source === "wh";
      const adding = reviewMode === "add";
      // With nothing in your collection, Add and Replace are the same, so hide the choice.
      reviewModeBox.classList.toggle("hidden", models.length === 0);
      modeButtons.forEach(b => b.setAttribute("aria-checked", String(b.dataset.mode === reviewMode)));

      let summary = `${incoming.title}: ${plural(rows.length, "unit")}, ${plural(modelCount(rows), "model")}.`;
      if (incoming.unknownStages && incoming.unknownStages.length) {
        summary += ` These stages don't match yours, so those units will start at "${STAGES[0]}": ` +
          incoming.unknownStages.join(", ") + ".";
      }
      if (!adding && models.length) {
        summary += ` Your current ${plural(models.length, "unit")} will be removed first. You can Undo straight after.`;
      }
      reviewSummary.textContent = summary;

      const have = matched.filter(m => m.match && m.kind !== "close").length;
      const possible = matched.filter(m => m.kind === "close").length;
      const spelling = matched.filter(m => m.kind === "spelling").length;
      const notes = [];
      if (adding && have) notes.push(`${plural(have, "unit")} already in your collection, so ${have === 1 ? "it starts" : "they start"} unticked.`);
      if (adding && spelling) notes.push(fromApp
        ? `${spelling} will have ${spelling === 1 ? "its" : "their"} spelling updated to match the Warhammer app (e.g. capitals).`
        : `${spelling} differ only in capitals or hyphens; your spelling is kept.`);
      if (adding && possible) notes.push(`${possible} possible match${possible === 1 ? "" : "es"} highlighted in amber: check each one is really the same unit.`);
      reviewClashNote.textContent = notes.join(" ");

      reviewList.innerHTML = "";
      matched.forEach((m, i) => {
        const c = choices[i];
        const li = document.createElement("li");
        const isClose = adding && m.kind === "close";
        const willRename = adding && m.match && m.kind !== "exact" && c.keep === "theirs";
        const doesNothing = !c.tick && !willRename;
        li.className = "review-row" + (isClose ? " clash" : "") + (doesNothing ? " off" : "");

        const label = document.createElement("label");
        const box = document.createElement("input");
        box.type = "checkbox";
        box.checked = c.tick;
        box.setAttribute("aria-label", c.tick ? `Import ${m.row.name}` : `Don't import ${m.row.name}`);
        box.addEventListener("change", () => { c.tick = box.checked; renderReview(); });
        const text = document.createElement("span");
        text.append(m.row.name);
        const meta = document.createElement("div");
        meta.className = "meta";
        const stageText = fromApp ? "" : ` · ${STAGES[m.row.stage]}`;
        meta.textContent = plural(m.row.count || 1, "model") + stageText + (m.row.faction ? ` · ${m.row.faction}` : "");
        text.appendChild(meta);
        if (adding && m.match && m.kind !== "exact") {
          const yours = document.createElement("div");
          yours.className = "meta";
          yours.textContent = `You have: "${m.match.name}"` + (willRename ? " (will be renamed)" : "");
          text.appendChild(yours);
        }
        const tag = document.createElement("span");
        tag.className = "tag";
        tag.textContent = !adding ? "" : isClose ? "possible match" : m.match ? "already have" : "new";
        label.append(box, text);
        if (tag.textContent) label.appendChild(tag);
        li.appendChild(label);

        if (isClose) {
          const pick = document.createElement("select");
          pick.setAttribute("aria-label", `Is ${m.row.name} the same as your ${m.match.name}?`);
          pick.add(new Option(fromApp ? "Same unit: use app name" : "Same unit: use file's name", "theirs"));
          pick.add(new Option("Same unit: keep my name", "yours"));
          pick.add(new Option("Different unit: add as new", "different"));
          pick.value = c.keep;
          pick.addEventListener("change", () => {
            c.keep = pick.value;
            if (pick.value === "different") c.tick = true;
            renderReview();
          });
          li.appendChild(pick);
        }
        reviewList.appendChild(li);
      });

      const ticked = choices.filter(c => c.tick).length;
      const renames = renamesToMake(matched).length;
      if (!adding) {
        reviewGo.textContent = ticked ? `Replace with ${plural(ticked, "unit")}` : "Nothing ticked";
        reviewGo.className = "danger-button";
        reviewGo.disabled = !ticked;
      } else {
        reviewGo.className = "primary-button";
        reviewGo.textContent = ticked ? `Add ${plural(ticked, "unit")}` + (renames ? `, rename ${renames}` : "")
          : renames ? `Rename ${plural(renames, "unit")}` : "Nothing to do";
        reviewGo.disabled = !ticked && !renames;
      }
    }

    // Copy numbers ("Lictor 1", "Lictor 2") for one name in one faction: keeps numbers
    // that are already fine, and only gives new numbers where needed.
    function fixCopies(name, faction) {
      const same = (a, b) => plainQuotes(a || "").toLowerCase() === plainQuotes(b || "").toLowerCase();
      const group = models.filter(m => same(m.name, name) && same(m.faction, faction));
      if (group.length <= 1) { group.forEach(m => { delete m.copy; }); return; }
      const used = new Set();
      const needNumber = [];
      for (const m of group) {
        if (Number.isInteger(m.copy) && m.copy > 0 && !used.has(m.copy)) used.add(m.copy);
        else needNumber.push(m);
      }
      let next = 1;
      for (const m of needNumber) {
        while (used.has(next)) next++;
        m.copy = next;
        used.add(next);
      }
    }

    modeButtons.forEach(b => b.addEventListener("click", () => {
      reviewMode = b.dataset.mode;
      setDefaultChoices();
      renderReview();
    }));
    document.getElementById("review-all").addEventListener("click", () => { choices.forEach(c => { c.tick = true; }); renderReview(); });
    document.getElementById("review-none").addEventListener("click", () => { choices.forEach(c => { c.tick = false; }); renderReview(); });
    document.getElementById("review-cancel").addEventListener("click", closeReview);
    whFaction.addEventListener("input", () => { if (incoming) { refreshChoices(); renderReview(); } });
    whGame.addEventListener("input", () => { if (incoming) renderReview(); });

    reviewGo.addEventListener("click", () => {
      const matched = matchRows();
      const toAdd = matched.filter((m, i) => choices[i].tick);
      const renames = renamesToMake(matched);
      // v21.7: the "replace everything" question is asked in the app's own box; the rest runs
      // when you say yes (straight away for "add", or when there's nothing to replace).
      const run = () => {
        if (reviewMode === "replace" && models.length) {
          // Keep a safety copy on the device. If there isn't room (photos take a lot of
          // space), stop rather than carry on with no safety net.
          // (v14: kept for 30 days, with the stage list, and listed under Recover earlier data.)
          if (!keepSafetyCopy("-before-replace")) {
            notify("There isn't room on this device to keep a safety copy of your current units, so nothing has been changed. Please press Save backup first, then try again.");
            return;
          }
        }

        const before = models.map(m => ({ ...m }));   // a copy, so Undo can put everything back
        if (reviewMode === "replace") {
          models = [];
          openIds.clear();
        } else {
          // Rename first, so new copies are numbered alongside them.
          for (const r of renames) {
            const unit = models.find(m => m.id === r.id);
            if (unit) unit.name = r.to;
          }
          for (const r of renames) { fixCopies(r.from, r.faction); fixCopies(r.to, r.faction); }
        }
        const whStageNumber = Number(whStage.value) || 0;
        matched.forEach((m, i) => {
          const c = choices[i];
          if (!c.tick) return;
          // Extra copies of a unit you have, where you chose to keep your name, use your name.
          const useYours = reviewMode === "add" && m.match && c.keep === "yours";
          addModel({
            ...m.row,
            name: useYours ? m.match.name : m.row.name,
            stage: incoming.source === "wh" ? whStageNumber : m.row.stage,
          });
        });

        const parts = [];
        if (reviewMode === "replace") parts.push(`Replaced with ${plural(toAdd.length, "unit")}`);
        else {
          if (toAdd.length) parts.push(`Added ${plural(toAdd.length, "unit")}`);
          if (renames.length) parts.push(`${toAdd.length ? "renamed" : "Renamed"} ${plural(renames.length, "unit")}`);
        }
        closeReview();
        whText.value = "";
        whPanel.classList.add("hidden");
        refreshUnitsImport();
        closeAddForm();      // v19: so the new units have the screen
        clearFilters();
        render();
        renderSettings();
        showTab("units");    // v19: after an import, show the units it brought in
        showToast(parts.join(", "), () => {
          models = before;
          render();
          renderSettings();
        }, "Undo", 10);
      };
      if (reviewMode === "replace" && models.length) {
        askYesNo(`Remove your ${plural(models.length, "unit")} and replace them with ${plural(toAdd.length, "unit")}?`, run, { danger: true });
      } else {
        run();
      }
    });

    // ----- Starting an import from the Warhammer app -----
    document.getElementById("wh-button").addEventListener("click", () => {
      if (importWhere !== "settings") { placeImportArea("settings"); whPanel.classList.add("hidden"); closeReview(); }
      const opening = whPanel.classList.contains("hidden");
      whPanel.classList.toggle("hidden", !opening);
      if (opening) { closeReview(); whText.focus(); }
    });

    document.getElementById("wh-read").addEventListener("click", () => {
      const list = parseWarhammerList(whText.value);
      if (!list) {
        notify("That doesn't look like a list exported from the Warhammer app. Each unit should be a name followed by its points, e.g. \"Lictor (60 points)\".");
        return;
      }
      // Use the spelling of a faction you already have, and its game.
      const knownFaction = models.find(m => looseName(m.faction) === looseName(list.faction));
      whFaction.value = knownFaction ? knownFaction.faction : list.faction;
      whGame.value = knownFaction ? knownFaction.hobby
        : (models.find(m => looseName(m.hobby) === "40k") || { hobby: "40K" }).hobby;
      openReview({
        source: "wh",
        title: `"${list.listName}"`,
        rows: list.units.map(u => ({ name: u.name, count: u.count })),
      });
    });

    // ================= v19: IMPORT FROM THE UNITS TAB =================
    // "Paste army list" and "Import CSV" sit on the Add unit panel (and on an empty Units
    // list), so nobody has to find them in Settings. Rather than a second copy of the paste
    // box and the import check, the SAME boxes (#import-area) are moved to the Units tab
    // while an import started there is open, and moved back when one starts in Settings.
    const importArea = document.getElementById("import-area");
    const unitsImport = document.getElementById("units-import");
    let importWhere = "settings";   // where #import-area is right now: "settings" or "units"

    function placeImportArea(where) {
      const slot = document.getElementById(where === "units" ? "units-import-slot" : "settings-import-slot");
      if (importArea.parentNode !== slot) slot.appendChild(importArea);
      importWhere = where;
      refreshUnitsImport();
    }
    // The Units tab's import card shows only while something is open in it.
    function refreshUnitsImport() {
      const open = importWhere === "units" &&
        (!whPanel.classList.contains("hidden") || !reviewBox.classList.contains("hidden"));
      unitsImport.classList.toggle("hidden", !open);
    }
    function closeUnitsImport() {
      whPanel.classList.add("hidden");
      closeReview();
    }
    function closeAddForm() {
      form.classList.add("hidden");
      toggleAdd.textContent = "+ Add unit";
    }

    function startUnitsPaste() {
      placeImportArea("units");
      closeReview();
      whPanel.classList.remove("hidden");
      refreshUnitsImport();
      showTab("units");
      unitsImport.scrollIntoView({ block: "start" });
      whText.focus();
    }
    function startUnitsCsv() {
      placeImportArea("units");
      whPanel.classList.add("hidden");
      closeReview();
      csvFile.click();   // the check opens on the Units tab once a file is picked
    }
    document.getElementById("add-wh").addEventListener("click", startUnitsPaste);
    document.getElementById("add-csv").addEventListener("click", startUnitsCsv);
    document.getElementById("units-import-close").addEventListener("click", closeUnitsImport);

    // ================= "TIME TO BACK UP" REMINDER =================
    // Your data only lives on this device, so a backup is the safety net.
    // If you have real units and no backup in 14 days, the app nudges you, at most every 3 days.
    // v18.3: a plain "2026-10-10" date is read as midnight in YOUR time zone (not world time),
    // so "a day since" and "a week since" line up with the dates the app writes.
    function daysSince(isoDate) {
      if (!isoDate) return Infinity;
      const when = /^\d{4}-\d{2}-\d{2}$/.test(isoDate) ? new Date(isoDate + "T00:00:00") : new Date(isoDate);
      return (Date.now() - when.getTime()) / 86400000;
    }
    function maybeRemindToBackUp() {
      const onlyExamples = models.length <= EXAMPLES.length &&
        models.every(m => EXAMPLES.some(e => e.name === m.name && e.faction === m.faction));
      if (!models.length || onlyExamples) return;
      // Don't nag brand-new users: wait for 10+ units and a day since first real use.
      if (!settings.firstRealUse) { settings.firstRealUse = todayISO(); saveSettings(); }
      if (models.length < 10 || daysSince(settings.firstRealUse) < 1) return;
      // v14: after a WEEK, not two (an iPhone can clear a website's data after 7 days
      // unused). If you have photos, the reminder is about a backup WITH photos, and its
      // button makes one, because a plain backup leaves them out.
      const withPhotos = models.some(hasPhoto);
      const last = withPhotos ? settings.lastFullBackup : settings.lastBackup;
      if (daysSince(last) < 7 || daysSince(settings.lastReminder) < 3) return;
      settings.lastReminder = todayISO();
      saveSettings();
      const message = !last
        ? (withPhotos ? "Your photos haven't been backed up yet" : "You haven't saved a backup yet")
        : `It's been over a week since your last backup${withPhotos ? " with photos" : ""}`;
      showToast(message, () => document.getElementById(withPhotos ? "full-export-button" : "export-button").click(), "Back up", 10);
    }

    // ----- iPhone warning (v14) -----
    // Safari on an iPhone or iPad can delete a website's saved data (units AND photos) if
    // it isn't opened for 7 days. Apps added to the Home Screen are safe. So if the app is
    // open in Safari itself, show a card on the dashboard saying so. "Got it" hides it
    // for 30 days.
    function isAppleMobile() {
      return /iPhone|iPad|iPod/.test(navigator.userAgent) ||
             (navigator.platform === "MacIntel" && navigator.maxTouchPoints > 1);   // newer iPads say "Mac"
    }
    function openedFromHomeScreen() {
      return navigator.standalone === true || window.matchMedia("(display-mode: standalone)").matches;
    }
    function showIphoneWarning() {
      const card = document.getElementById("iphone-warning");
      const show = isAppleMobile() && !openedFromHomeScreen() && daysSince(settings.iphoneWarningHidden) > 30;
      card.classList.toggle("hidden", !show);
    }
    document.getElementById("iphone-warning-ok").addEventListener("click", () => {
      settings.iphoneWarningHidden = todayISO();
      saveSettings();
      showIphoneWarning();
    });


    // ================= UPDATES TAB: CHANGE HISTORY AND FEEDBACK =================
    // WHEN YOU RELEASE AN UPDATE: add a new entry at the TOP of this list, and change
    // APP_VERSION to match. (Also bump VERSION in sw.js, so phones fetch the new copy, and the
    // "?v=" number on app.js and early.js in index.html, e.g. "app.js?v=29". v21.4 test checks.)
    const APP_VERSION = "v29";
    // Paste the Microsoft Forms share link between the quotes. Empty = "coming soon".
    const FEEDBACK_URL = "https://tally.so/r/Y5Lka6";

    // ================= v25: ONE GENTLE "SEND FEEDBACK?" CARD =================
    // About a week after someone starts using the app, ONE small card on the Dashboard asks if they
    // would like to send feedback. Nothing is tracked or sent: the app only saves, in the settings
    // on this device, the day it was first opened and what the person chose:
    //   settings.feedbackFirstSeen  "2026-10-12"  first day this device opened v25 or later
    //   settings.feedbackHidden     "done" (opened the form) | "never" (Don't ask again) | unset
    //   settings.feedbackNextAfter  "2026-11-11"  after "Not now": not before this day
    //   settings.feedbackShownOn    "2026-10-19"  the day the card was put up (it stays that day)
    // People who already used the app get TODAY as their first day (they are asked a week after
    // they update, not at once). If the card is not answered, the next visit counts it as
    // "Not now", so it can never show on two days running. Saved settings, so DATA_VERSION stays 1
    // (older versions keep settings they don't know).
    const FEEDBACK_AFTER_DAYS = 7;
    const FEEDBACK_WAIT_DAYS = 30;
    const ISO_DAY = /^\d{4}-\d{2}-\d{2}$/;
    // The same address the Give feedback button under Settings -> Updates uses.
    function feedbackAddress() {
      return FEEDBACK_URL ? `${FEEDBACK_URL}?version=${encodeURIComponent(APP_VERSION)}` : "";
    }
    function dayFromToday(days) {
      const d = new Date();
      d.setDate(d.getDate() + days);
      return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}-${String(d.getDate()).padStart(2, "0")}`;
    }
    // Runs once at start-up (before the first render(), which saves the settings).
    function planFeedbackPrompt() {
      const today = todayISO();
      if (!ISO_DAY.test(settings.feedbackFirstSeen || "")) settings.feedbackFirstSeen = today;
      if (settings.feedbackHidden === "done" || settings.feedbackHidden === "never") return;
      const shown = settings.feedbackShownOn;
      if (ISO_DAY.test(shown || "")) {
        if (shown === today) return;   // put up earlier today: it stays up
        // Put up on an earlier day and never answered: treat it as "Not now".
        settings.feedbackShownOn = "";
        settings.feedbackNextAfter = dayFromToday(FEEDBACK_WAIT_DAYS);
        return;
      }
      if (!FEEDBACK_URL) return;
      if (daysSince(settings.feedbackFirstSeen) < FEEDBACK_AFTER_DAYS) return;
      const next = settings.feedbackNextAfter;
      if (ISO_DAY.test(next || "") && today < next) return;
      settings.feedbackShownOn = today;
    }
    function feedbackCardWanted() {
      return !!FEEDBACK_URL && settings.feedbackHidden !== "done" && settings.feedbackHidden !== "never" &&
        ISO_DAY.test(settings.feedbackShownOn || "") && settings.feedbackShownOn === todayISO();
    }
    function answerFeedback(choice) {
      settings.feedbackShownOn = "";
      if (choice === "later") settings.feedbackNextAfter = dayFromToday(FEEDBACK_WAIT_DAYS);
      else settings.feedbackHidden = choice;   // "done" or "never"
      saveSettings();
      // Redraw after the tap has finished, so the Give feedback link isn't taken off the page
      // before the browser has opened it.
      setTimeout(renderFeedbackCard, 0);
      if (choice === "never") notify("OK, we won't ask again. You can still give feedback under Settings \u2192 Updates.");
    }
    function renderFeedbackCard() {
      const card = document.getElementById("feedback-card");
      if (!card) return;
      const show = feedbackCardWanted();
      card.classList.toggle("hidden", !show);
      card.innerHTML = "";
      if (!show) return;
      const text = document.createElement("p");
      const strong = document.createElement("strong");
      strong.textContent = "Enjoying Minifolio?";
      text.append(strong, " Would you like to tell us what you think? It's a short form, about 2 minutes, and every reply is read.");
      const give = document.createElement("a");
      give.className = "primary-button feedback-give";
      give.href = feedbackAddress();
      give.target = "_blank";
      give.rel = "noopener noreferrer";
      give.textContent = "Give feedback";
      give.addEventListener("click", () => answerFeedback("done"));   // no preventDefault: the link opens
      const buttons = document.createElement("div");
      buttons.className = "button-grid";
      const later = document.createElement("button");
      later.type = "button";
      later.className = "plain-button feedback-later";
      later.textContent = "Not now";
      later.addEventListener("click", () => answerFeedback("later"));
      const never = document.createElement("button");
      never.type = "button";
      never.className = "plain-button feedback-never";
      never.textContent = "Don't ask again";
      never.addEventListener("click", () => answerFeedback("never"));
      buttons.append(later, never);
      card.append(text, give, buttons);
    }
    // ================= v26: UNFINISHED WORK SURVIVES A RELOAD =================
    // Before v26, a half-filled Add unit form, a recipe you were writing and the text in Paste
    // recipes were only held in memory, so reloading the page (or the phone closing the app in
    // the background) lost them. Now the app keeps a DRAFT of each, on this device only:
    //   "unit"   the Add unit boxes (name, number of models, game, faction, starting stage),
    //            kept while the name box has something in it
    //   "recipe" a recipe being written or edited, kept while it has unsaved changes
    //   "paste"  the text in Paste recipes, kept while the box has something in it
    // They live in ONE separate storage entry (DRAFTS_KEY), not in the units, recipes or settings,
    // so they never travel in a backup, never trigger the other-window reload, and a save that
    // fails can never roll them back. Older versions simply ignore an entry they don't know, so
    // DATA_VERSION stays 1. Nothing is sent anywhere.
    //
    // How it works. syncDrafts() looks at what's on screen and writes it down. It runs a moment after
    // every tap, key press or change, when the page is hidden or closed, and every few seconds as a
    // safety net. When the app starts it finds the kept drafts and shows a small card for each
    // (Keep going / Discard); nothing opens by itself. THE RULE THAT KEEPS DRAFTS SAFE: while a kept
    // draft is waiting for an answer, you can't start a new one of the same kind (the app first asks
    // whether to keep going with the old one), and syncDrafts() never touches a waiting draft. So a new
    // draft can never quietly replace an old one. A draft is removed when it's finished (Add, Save, an
    // import, Cancel and "yes, discard") or when you tap Discard and say yes. A discarded draft is gone
    // for good: there is no Undo and nothing brings it back.
    const DRAFTS_KEY = "shades-of-grey-drafts";
    const DRAFT_KINDS = ["unit", "recipe", "paste"];
    const DRAFT_SYNC_MS = 300;        // how long after the last change a draft is written
    const DRAFT_SAFETY_MS = 4000;     // the safety net
    const DRAFT_TEXT_LIMIT = 500000;  // longest piece of text a draft keeps
    let draftOffers = { unit: null, recipe: null, paste: null };    // kept drafts waiting for an answer
    const draftWritten = { unit: null, recipe: null, paste: null }; // what THIS window last wrote (null = nothing)
    let draftSyncTimer = null;

    function readDraftStore() {
      try {
        const parsed = JSON.parse(localStorage.getItem(DRAFTS_KEY) || "null");
        return parsed && typeof parsed === "object" && !Array.isArray(parsed) ? parsed : {};
      } catch (ignored) { return {}; }
    }
    function writeDraftStore(store) {
      try {
        if (Object.keys(store).length) localStorage.setItem(DRAFTS_KEY, JSON.stringify(store));
        else localStorage.removeItem(DRAFTS_KEY);
        return true;
      } catch (ignored) { return false; }   // storage full or off: the draft just isn't kept this time
    }

    // ----- What's on screen, as something that can be saved -----
    const draftText = (value, limit) => typeof value === "string" ? value.slice(0, limit || DRAFT_TEXT_LIMIT) : "";
    function liveUnitDraft() {
      if (!nameInput.value.trim()) return null;
      return {
        name: draftText(nameInput.value, 300), count: draftText(countInput.value, 8),
        game: draftText(hobbyInput.value, 300), faction: draftText(factionInput.value, 300),
        stage: STAGES[startStage()] || "",
      };
    }
    function liveRecipeDraft() {
      const d = recipeDraft;
      if (!d || draftSnapshot(d) === d.original) return null;   // nothing changed yet: nothing to keep
      return {
        id: Number.isInteger(d.id) ? d.id : null, name: draftText(d.name), part: draftText(d.part, 300),
        notes: draftText(d.notes), linkUnit: Number.isInteger(d.linkUnit) ? d.linkUnit : null,
        steps: d.steps.map(s => ({
          technique: draftText(s.technique, 300), coats: s.coats, ratio: draftText(s.ratio, 300),
          note: draftText(s.note), optional: !!s.optional,
          paints: s.paints.map(p => ({
            brand: draftText(p.brand, 300), name: draftText(p.name, 300), colour: p.colour,
            mix: p.mix === undefined ? null : p.mix, type: typeof p.type === "string" ? p.type : undefined,
          })),
        })),
        own: d.own ? { mode: d.own.mode, notOwned: [...d.own.notOwned].map(String) } : null,
      };
    }
    function livePasteDraft() {
      return importDraft && importDraft.text.trim() ? { text: draftText(importDraft.text) } : null;
    }
    const LIVE_DRAFTS = { unit: liveUnitDraft, recipe: liveRecipeDraft, paste: livePasteDraft };

    // ----- Checking what was kept (it came from storage, so it is checked like any saved data) -----
    const goodDraftColour = (c) => typeof c === "string" && /^#[0-9a-f]{6}$/i.test(c) ? c.toLowerCase() : DEFAULT_PAINT_COLOUR;
    function cleanUnitDraft(raw) {
      if (!raw || typeof raw !== "object" || typeof raw.name !== "string" || !raw.name.trim()) return null;
      return {
        name: draftText(raw.name, 300), count: draftText(raw.count, 8) || "1",
        game: draftText(raw.game, 300), faction: draftText(raw.faction, 300), stage: draftText(raw.stage, 300),
      };
    }
    function cleanRecipeDraft(raw) {
      if (!raw || typeof raw !== "object" || !Array.isArray(raw.steps)) return null;
      const steps = raw.steps.slice(0, 60).filter(s => s && typeof s === "object" && Array.isArray(s.paints)).map(s => ({
        technique: draftText(s.technique, 300), coats: cleanCount(s.coats), ratio: draftText(s.ratio, 300),
        note: draftText(s.note), optional: s.optional === true,
        paints: s.paints.slice(0, 12).filter(p => p && typeof p === "object").map(p => {
          const paint = { brand: draftText(p.brand, 300), name: draftText(p.name, 300), colour: goodDraftColour(p.colour), mix: cleanMix(p.mix) };
          if (typeof p.type === "string") paint.type = p.type.slice(0, 100);
          return paint;
        }),
      })).map(s => ({ ...s, paints: s.paints.length ? s.paints : [blankPaint(100)] }));
      const own = raw.own && typeof raw.own === "object" && ["all", "none", "pick"].includes(raw.own.mode)
        ? { mode: raw.own.mode, notOwned: new Set(Array.isArray(raw.own.notOwned) ? raw.own.notOwned.filter(x => typeof x === "string") : []) }
        : newOwnChoice();
      return {
        id: Number.isInteger(raw.id) ? raw.id : null, name: draftText(raw.name), part: draftText(raw.part, 300),
        notes: draftText(raw.notes), linkUnit: Number.isInteger(raw.linkUnit) ? raw.linkUnit : null,
        steps: steps.length ? steps : [blankStep()], own,
      };
    }
    function cleanPasteDraft(raw) {
      return raw && typeof raw === "object" && typeof raw.text === "string" && raw.text.trim() ? { text: draftText(raw.text) } : null;
    }
    const CLEAN_DRAFTS = { unit: cleanUnitDraft, recipe: cleanRecipeDraft, paste: cleanPasteDraft };

    // ----- Writing drafts down -----
    function syncDrafts() {
      clearTimeout(draftSyncTimer);
      draftSyncTimer = null;
      if (dataTooNew) return;   // like the units: a newer version has taken over, so this copy stops saving
      let store = null;
      const changes = [];
      for (const kind of DRAFT_KINDS) {
        if (draftOffers[kind]) continue;   // an old kept draft is waiting for an answer: leave it exactly as it is
        const live = LIVE_DRAFTS[kind]();
        const text = live ? JSON.stringify(live) : null;
        if (text === draftWritten[kind]) continue;   // nothing new (and a window that never wrote one never removes one)
        if (!store) store = readDraftStore();   // read just before writing, so another window's drafts are kept
        if (live) store[kind] = live; else delete store[kind];
        changes.push([kind, text]);
      }
      if (!changes.length) return;
      if (writeDraftStore(store)) for (const [kind, text] of changes) draftWritten[kind] = text;
    }
    function queueDraftSync() {
      clearTimeout(draftSyncTimer);
      draftSyncTimer = setTimeout(syncDrafts, DRAFT_SYNC_MS);
    }
    for (const type of ["input", "change", "click", "keyup"]) document.addEventListener(type, queueDraftSync, true);
    window.addEventListener("pagehide", syncDrafts);
    document.addEventListener("visibilitychange", () => { if (document.visibilityState === "hidden") syncDrafts(); });
    setInterval(syncDrafts, DRAFT_SAFETY_MS);

    // ----- At start-up: find what was kept -----
    function loadKeptDrafts() {
      const store = readDraftStore();
      let tidy = false;
      for (const kind of DRAFT_KINDS) {
        if (!(kind in store)) continue;
        const kept = CLEAN_DRAFTS[kind](store[kind]);
        if (kept) draftOffers[kind] = kept;
        else { delete store[kind]; tidy = true; }   // unreadable or empty: nothing worth offering
      }
      if (tidy) writeDraftStore(store);
    }

    // ----- The cards and what their buttons do -----
    const DRAFT_NAMES = { unit: "unit", recipe: "recipe", paste: "pasted recipe notes" };
    function draftCardLine(kind, kept) {
      const short = (t) => { const s = String(t).trim().replace(/\s+/g, " "); return s.length > 60 ? s.slice(0, 57) + "…" : s; };
      if (kind === "unit") return `You hadn't finished adding “${short(kept.name)}”.`;
      if (kind === "recipe") {
        const name = kept.name.trim();
        const was = kept.id !== null && recipeById(kept.id) ? "changes to" : "";
        return name ? `You hadn't saved ${was ? was + " " : ""}“${short(name)}”.` : "You hadn't saved the recipe you were writing.";
      }
      const n = kept.text.length;
      return `You hadn't saved these recipes (${n.toLocaleString("en-GB")} character${n === 1 ? "" : "s"}).`;
    }
    function fillDraftCard(kind, show) {
      const card = document.getElementById(`draft-card-${kind}`);
      if (!card) return;
      const kept = draftOffers[kind];
      const on = !!(show && kept);
      card.classList.toggle("hidden", !on);
      card.innerHTML = "";
      if (!on) return;
      const text = document.createElement("p");
      const strong = document.createElement("strong");
      strong.textContent = kind === "paste" ? "We kept your pasted recipe notes." : `We kept your unfinished ${DRAFT_NAMES[kind]}.`;
      text.append(strong, " " + draftCardLine(kind, kept) + " It's saved on this device only.");
      const buttons = document.createElement("div");
      buttons.className = "button-grid";
      const go = document.createElement("button");
      go.type = "button";
      go.className = "primary-button draft-keep";
      go.textContent = "Keep going";
      go.addEventListener("click", () => keepDraft(kind));
      const bin = document.createElement("button");
      bin.type = "button";
      bin.className = "danger-button draft-discard";
      bin.textContent = "Discard";
      bin.addEventListener("click", () => discardDraft(kind));
      buttons.append(go, bin);
      card.append(text, buttons);
    }

    // Bring a kept draft back to life.
    function keepDraft(kind) {
      const kept = draftOffers[kind];
      if (!kept) return;
      draftOffers[kind] = null;
      draftWritten[kind] = "kept";   // so that finishing or cancelling it later removes it
      if (kind === "unit") {
        if (selectMode) closeSelect();
        showTab("units");
        form.classList.remove("hidden");
        toggleAdd.textContent = "Close";
        nameInput.value = kept.name;
        countInput.value = kept.count;
        hobbyInput.value = kept.game;
        factionInput.value = kept.faction;
        const at = STAGES.indexOf(kept.stage);
        stageInput.value = String(at >= 0 ? at : startStage());
        stageInput.style.setProperty("--stage-colour", `var(--stage-${stageInput.value})`);
        renderUnits();
        form.scrollIntoView({ block: "start" });
        nameInput.focus({ preventScroll: true });
      } else if (kind === "recipe") {
        const d = kept;
        const existing = d.id !== null ? recipeById(d.id) : null;
        if (!existing) d.id = null;   // the recipe it was changing has gone since: it comes back as a new one
        if (d.linkUnit !== null && !models.some(m => m.id === d.linkUnit)) d.linkUnit = null;
        // What "unchanged" means for the Cancel question: the saved recipe, or nothing for a new one.
        d.original = existing ? draftSnapshot(draftFrom(existing)) : "";
        importDraft = null;
        openRecipeId = null;
        startRecipeDraft(d);
        showTab("recipes");
      } else {
        recipeDraft = null;
        openRecipeId = null;
        importDraft = { text: kept.text, parsed: null, groups: [], names: [] };
        renderRecipes();
        showTab("recipes");
        window.scrollTo(0, 0);
      }
      queueDraftSync();
    }
    // Throw a kept draft away for good. It asks first (No is the bold button), and there is no Undo.
    function discardDraft(kind) {
      if (!draftOffers[kind]) return;
      const what = kind === "paste" ? "pasted recipe notes" : `unfinished ${DRAFT_NAMES[kind]}`;
      askYesNo(`Throw away your ${what}? This can't be undone.`, () => {
        if (!draftOffers[kind]) return;   // already dealt with (say, from another card)
        draftOffers[kind] = null;
        draftWritten[kind] = null;
        const store = readDraftStore();
        delete store[kind];
        writeDraftStore(store);
        renderUnits();
        renderRecipes();
      }, { danger: true, yes: "Discard", no: "Keep it" });
    }
    // Starting a new draft while an old one waits would quietly replace it, so the app asks first.
    // Returns true if the new thing must wait.
    function draftWaiting(kind) {
      if (!draftOffers[kind]) return false;
      askYesNo(`You have an unfinished ${DRAFT_NAMES[kind]} kept from earlier. Keep going with it first?`,
        () => keepDraft(kind), { yes: "Keep going", no: "Not now" });
      return true;
    }
    loadKeptDrafts();

    // ================= v27: COUNTING VISITS (anonymous, no cookies) =================
    // To learn roughly how many people open Minifolio, each time the app starts it asks GoatCounter
    // (goatcounter.com, a small privacy-friendly counting service) for ONE tiny 1x1 picture, the
    // "tracking pixel" way of counting. That request is all that is sent: no cookies, nothing saved
    // on the device, no account or ID, and nothing from the person's units, recipes, photos or settings.
    // It is a picture and not a script, so the Content Security Policy only had to allow that one
    // picture address (img-src); script-src and connect-src are unchanged.
    //   - Only counts when the app runs from minifolio.app (never on a test or local copy).
    //   - The picture is asked for without telling GoatCounter which page it came from (no referrer).
    //   - One count per start-up, never from the other-window sync or a redraw.
    //   - No internet: the request just fails and nothing else happens (sw.js leaves it alone).
    //   - Settings -> Counting visits switches it off. The choice is settings.countVisits: only an
    //     explicit false means off (saved settings, so DATA_VERSION stays 1; older versions keep it).
    //     It is not in backups, like the feedback card's dates.
    const COUNTER_CODE = "dim3ry";
    const COUNTER_URL = "https://" + COUNTER_CODE + ".goatcounter.com/count";
    const COUNTED_HOSTS = ["minifolio.app"];
    let visitCounted = false;
    function countingIsOn() { return settings.countVisits !== false; }
    function countingHere() { return COUNTED_HOSTS.includes(location.hostname); }
    // Runs once at start-up. Returns true if it asked for the picture.
    function countThisVisit() {
      if (visitCounted || !countingIsOn() || !countingHere()) return false;
      visitCounted = true;
      try {
        const pixel = new Image();
        pixel.referrerPolicy = "no-referrer";
        pixel.onload = pixel.onerror = () => {};
        pixel.src = COUNTER_URL + "?p=" + encodeURIComponent("/") + "&rnd=" + Math.random().toString(36).slice(2, 10);
      } catch (ignored) {}
      return true;
    }
    // The tick box in Settings -> Counting visits.
    const countingBox = document.getElementById("count-visits");
    function showCountingChoice() {
      countingBox.checked = countingIsOn();
      document.getElementById("counting-note").textContent = countingIsOn()
        ? "On. When the app opens, it asks GoatCounter for one tiny picture so we can count visits. It sets no cookies, stores nothing on your device and sends nothing from your collection."
        : "Off. The app won't ask GoatCounter for anything, so you aren't counted.";
    }
    countingBox.addEventListener("change", () => {
      settings.countVisits = countingBox.checked;
      saveSettings();
      showCountingChoice();
    });
    if (settings.countVisits !== undefined && typeof settings.countVisits !== "boolean") delete settings.countVisits;
    showCountingChoice();

    const CHANGELOG = [
      { version: "v29", date: "15 Oct 2026", changes: [
        "Pro preview, Colour ideas: each thing you can paint now comes with a short tip written by hand (for example: keep eyes the brightest, most saturated spot on the model), and the reasons under the ideas use that advice where it says it better.",
        "New check at the bottom of Colour ideas: Does this scheme hang together? It looks at the colours in your recipe and says if there are too many strong colours or no light and dark, and suggests one colour to be the star. It is only a guide. It all runs on your phone, works offline and sends nothing anywhere.",
      ]},
      { version: "v28", date: "15 Oct 2026", changes: [
        "New Pro preview: Colour ideas, inside a recipe you are writing or editing. Pick a colour from the recipe (or Whole model, the main colour of your Whole model recipe, so ideas go with the whole model and not just this recipe), say what you are painting (eyes or glow, trim, gems, weapon, cloth or base) and you get 3 paint ideas, each with a short reason such as \u201corange is the opposite of blue, so it stands out\u201d.",
        "Each idea says You own this or Closest you own, so paints you already have come first. Tap one to add it to the recipe as a new step. It is free while it is a preview. The colour maths runs on your phone, works offline and sends nothing anywhere.",
      ]},
      { version: "v27", date: "12 Oct 2026", changes: [
        "Minifolio now counts roughly how many people open it, so we can tell whether it is being used. Each time the app opens it asks GoatCounter, a small privacy-friendly service, for one tiny picture. There are no cookies and no account, nothing is stored on your device, and nothing from your collection is sent.",
        "You can switch it off under Settings \u2192 Counting visits. Help \u2192 Privacy now says exactly what is counted and who receives it. The app's security rules were widened for that one picture address only.",
      ]},
      { version: "v26", date: "12 Oct 2026", changes: [
        "Your unfinished work now survives a reload. If you are part-way through adding a unit, writing a recipe or pasting notes into Paste recipes and the page reloads (or your phone closes the app), a card says \u201cWe kept your unfinished\u2026\u201d with Keep going and Discard. Nothing opens by itself.",
        "What you were typing is kept on this device only (nothing is sent anywhere, and it is not in your backups). It goes when you finish it, or when you discard it. A kept draft is never replaced by accident, and one you discarded never comes back.",
      ]},
      { version: "v25", date: "12 Oct 2026", changes: [
        "About a week after you start using the app, one small \u201cEnjoying Minifolio?\u201d card on the Dashboard asks if you'd like to send feedback. Give feedback opens the same form, Not now asks again in 30 days, and Don't ask again stops it for good. It never shows two days running.",
        "The app only remembers the day you started and your choice, on this device. Nothing is sent anywhere. If you already use the app, the week starts when you update.",
      ]},
      { version: "v24", date: "11 Oct 2026", changes: [
        "A new start now comes with two example recipes (Ultramarines armour and Ork skin), and the paints they use appear in Your Palette. They are linked to the example units Captain and Boyz, so you can see how recipes and units connect.",
        "A \u201cThese are examples\u201d card on the Recipes tab has Clear examples (with Undo) and Keep them. Clearing removes only the examples: a paint you've used in your own recipe or given a status is kept, and example paints never go on your shopping list. If you already had recipes, nothing is added.",
      ]},
      { version: "v23", date: "11 Oct 2026", changes: [
        "A unit's details now start with what you use most: its stage, then photos, recipes and paint notes.",
        "The boxes for changing the unit (name, game, faction, nickname, number of models, repaint and tracking each model) are folded away under one \u201cEdit details\u201d heading. Tap it to open them; it stays open while you make changes.",
      ]},
      { version: "v22", date: "11 Oct 2026", changes: [
        "Backups now come first on the Settings page, in their own Backups card, so they're easy to find.",
        "New Send backup to… button. It opens your phone's share menu, so you can put the backup straight into OneDrive, an email or a message. It sends the same small backup as Save backup (no photos), and the app itself still sends nothing anywhere. If your phone can't send files from here, or sending fails, the backup is saved to your device instead and the app tells you.",
      ]},
      { version: "v21.9", date: "11 Oct 2026", changes: [
        "Fewer tabs: Help and Updates now live inside the Settings tab, so there are four tabs along the bottom (Dashboard, Units, Recipes, Settings). At the top of Settings, a Settings / Help / Updates switch moves between the three.",
        "The app still remembers the page you were on, and the phone's Back button works as before.",
        "Friendlier wording: \"Tell us what you think\" on the Updates page.",
      ]},
      { version: "v21.8", date: "11 Oct 2026", changes: [
        "Stage names are easier to read in dark mode. A few stage colours (some in Ice, Frost, Greyscale and Forge) were a bit too dark to read as text on the dark cards, so they're now shown a little brighter. The colours you picked aren't changed, only how they're shown. Light mode is checked against the page colour as well as the cards.",
        "On a phone, the first photo in a unit's photo strip is no longer cut off at the edge. Two photos now fill the strip, and the strip still starts at the newest one.",
        "While you're typing in a text box, the tab bar steps out of the way so it can't sit on top of your keyboard and cover what you're typing. It comes back as soon as you tap somewhere else.",
        "When you track each model separately, each model now says when it reached its stage (\"Today\", \"Yesterday\" or \"Since 7 Oct\"), under its name. The dates were being saved all along; now you can see them. (Undo on a model's ▲ button now puts its date back exactly too.)",
      ]},
      { version: "v21.7", date: "11 Oct 2026", changes: [
        "Questions like \"Delete this unit?\" and \"Discard the changes?\" no longer use your browser's plain pop-up. The app asks in its own small box, in the same dark or light colours as the rest of the app, with big Yes and No buttons. The questions say the same things and do the same things as before. No, Cancel, the Escape key and the phone's Back button all mean no.",
        "Asking for a name (a new part or technique, renaming a faction, naming a paint the scanner wasn't sure of) uses the same box, with a text box to type in. That finishes the move away from the browser's own pop-ups.",
      ]},
      { version: "v21.6", date: "11 Oct 2026", changes: [
        "Notices no longer pop up as a plain browser box that you have to dismiss. \"That file doesn't look like a Minifolio backup\", \"Every stage needs a name\" and the rest now appear as the app's own message at the bottom of the screen. The words are the same, longer ones stay up longer, and a tap hides one.",
        "Questions that need a yes or no (like \"Are you sure?\") still use the browser's box for now. They move into the app in the next update.",
      ]},
      { version: "v21.5", date: "11 Oct 2026", changes: [
        "Deleted a unit by mistake? Press Undo on the message that appears: it comes back exactly as it was, photos included. (The app still asks \"Are you sure?\" first.)",
        "A unit you've just added is scrolled into view and outlined for a moment, instead of landing somewhere off-screen.",
      ]},
      { version: "v21.4", date: "11 Oct 2026", changes: [
        "Safety: the app's code now lives in its own files, so your browser can refuse any code that isn't one of them, including code someone tried to slip into the page itself. Nothing you see or do has changed.",
      ]},
      { version: "v21.3", date: "11 Oct 2026", changes: [
        "Scan a paint pot now knows more brands: Vallejo Game Color, Model Color and Xpress Color, The Army Painter's Warpaints Fanatic, Pro Acryl and AK 3rd Gen, about 950 more paints, not just Citadel.",
        "On a Vallejo pot the scanner also reads the code number (like 72.021), so it finds the exact paint even when the name is hard to read. Typing a Vallejo code in your notes works too.",
        "Pasting recipes from your notes recognises these brands too. Where two brands share a name, like \"Black\", the app asks which one. Citadel names are matched exactly as before.",
      ]},
      { version: "v21.2", date: "11 Oct 2026", changes: [
        "Safety: the app now tells your browser exactly what it's allowed to load and run (a Content Security Policy). Code from other websites can't run inside Minifolio, even if something tried to sneak it in.",
        "The Give feedback link no longer tells the form's website which page you came from.",
      ]},
      { version: "v21.1", date: "11 Oct 2026", changes: [
        "New: move several units to a stage at once. On the Units tab press Select, tick the units (or Select all shown), then pick a stage from Move to stage at the bottom. One Undo puts them all back.",
        "Pasted notes that start with a faction and a part, like \"Ultramarines armour\", are now read as that faction's armour recipe, not as the paint Ultramarines Blue.",
        "Tidier Your Palette: the status labels (Owned, Low, Wishlist…) are now only as wide as their words.",
      ]},
      { version: "v21", date: "11 Oct 2026", changes: [
        "New: the three example units the app starts with now say so, on the Dashboard and the Units tab. Clear examples removes only those (with Undo); Keep them turns them into your own units.",
        "New: jump straight to a stage. Open a unit and pick its stage from the Stage menu, instead of tapping ▲ up to 7 times. Units tracked model by model have a menu for each model too, and one to move them all.",
        "New: Starting stage when adding a unit, so a unit that's already primed or painted starts at the right stage.",
        "Easier to tap: the per-model ◀ ▲ buttons, the stage editor's ↑ ↓ ✕ buttons, + Mix in another paint and the Help topic titles are now at least 44 pixels, the size a fingertip needs.",
      ]},
      { version: "v20.1", date: "10 Oct 2026", changes: [
        "New warm stage colours: Forge, from ember red through amber and gold to warm cream. Find it in Settings → Colours.",
        "New: Custom stage colours. Pick Custom in Settings → Colours and choose a colour for each stage. It starts from your current set, warns you if a colour is too faint to read, and has a Reset button.",
        "Custom colours stay with their stages when you rename, reorder, add or remove stages, and they're saved in backups.",
      ]},
      { version: "v20", date: "10 Oct 2026", changes: [
        "New: a light look. Settings → Appearance has Dark (still the usual look), Light, and Match my phone, which follows your phone's own dark mode setting.",
        "Light mode keeps the cool blues and greys, and every screen has been checked for easy reading. Pale stage colours are shown a little deeper in light mode so stage names stay readable on white. Photos and the camera stay dark.",
        "Backups now include your Appearance and your stage colour set, so restoring brings them back too.",
      ]},
      { version: "v19.1", date: "10 Oct 2026", changes: [
        "The shopping list has a Buy these bar at the top: a button for each shop that sells your paints (Firestorm Games, Wayland Games, Element Games, and The Army Painter for its own paints). Tap a shop for a search link for each paint. Plain links: Minifolio isn't paid for them, and only the paint's name goes to the shop.",
        "Import CSV checks the file first: it needs a name column (the other columns can be in any order), and pictures, Excel files and files over 2 MB are refused with a message instead of turning into odd units.",
        "Restore backup checks the file first too: pictures, files over 300 MB and damaged backups are refused, and nothing changes.",
      ]},
      { version: "v19", date: "10 Oct 2026", changes: [
        "The phone's Back button no longer leaves the app by mistake. It closes what's open first (a photo, the camera, a recipe, the paste box), then goes to the Dashboard. Only on the Dashboard does it leave the app.",
        "Paste army list and Import CSV are now on the Units tab: tap + Add unit (or use the buttons on an empty Units list). They're still in Settings too. After an import, the Units tab opens on your units.",
        "Help has a new Privacy topic: what stays on your phone, what goes out (only the feedback form, if you use it) and no tracking.",
      ]},
      { version: "v18.3", date: "10 Oct 2026", changes: [
        "The camera can't be left on by accident any more: tapping Scan a label twice opens only one camera, and leaving the app or closing the scan panel switches it off.",
        "Scanning a paint pot now works offline: the label reader is part of Minifolio itself instead of being downloaded from other websites. After the first scan it works with no internet.",
        "Restoring a backup that only has recipes now has an Undo button, and your old recipes are kept for 30 days under Recover earlier data.",
        "Backup file names and backup reminders use your own time zone, so a backup made just after midnight is no longer dated the day before.",
        "Safety: your data now carries a version number. An older copy of the app left open (for example an installed app that hasn't updated) stops saving and asks you to reload, instead of saving over newer data.",
      ]},
      { version: "v18.2", date: "10 Oct 2026", changes: [
        "Shades of Grey is now called Minifolio, with its own web address: minifolio.app. Each web address keeps its own copy of your data, so if you used the old address, save a backup there and restore it here. Backups saved under the old name still restore, and new backup and export files are named minifolio-…",
        "The grey stage colour set is now called Greyscale. The colours are the same.",
      ]},
      { version: "v18.1", date: "10 Oct 2026", changes: [
        "Clearer wording: the app is unofficial and fan-made, and isn't linked to Games Workshop or any paint maker. This now shows on the Updates tab as well as in Help → About, which also says other paint brand names belong to their makers.",
      ]},
      { version: "v18", date: "10 Oct 2026", changes: [
        "Paste recipes reads far more notes correctly: mixes like 'Seraphim Sepia 1:2 with Contrast Medium', headings like 'Base;', a faction name on the first line, 'Texture Sand', accented letters, a brand named in the note ('Vallejo Ivory'), and 'Ushabti Bone and Wraithbone' as two paints. Divider lines and emoji-only lines are skipped. Long notes read much faster, up to 20,000 characters at once.",
        "In the paste preview, ✕ leaves a step, a whole part or a note out, and ✎ changes a step's technique, mix ratio or paints before you save. Every change has Undo, and Read again brings back what you pasted.",
        "'Do you own these?' asks about paints new to your palette when you paste recipes or type a new paint into a recipe: All, None (they go on the shopping list) or Let me pick.",
        "Your Palette: Remove a paint no recipe uses, or Merge into… another paint (handy for typo twins). Both have Undo. Brands typed twice ('CitadelCitadel') are tidied, and paints that turn out to be the same are joined.",
        "Copy as text always writes a mix's ratio (an even mix as 1:1), so a copied recipe pastes back the same.",
        "'Saved' only shows when your change really was saved. If the phone's storage is full, you'll see 'Not saved' with a Save backup button, and a paste import stays open so nothing is lost.",
        "Help has a new 'Pasting recipes from your notes' topic, and covers all of the above.",
      ]},
      { version: "v17.1", date: "9 Oct 2026", changes: [
        "Paints brought in by Paste recipes now start as Owned, not missing. After an import, Your Palette opens on those paints with every one expanded, so you can change any status or quantity, then press Done.",
        "Quantity: a paint you have counts as one. Tap + to say you have more (e.g. two Nuln Oil pots), and − to go back. Shown as '× 2 in stock' on the palette.",
      ]},
      { version: "v17", date: "9 Oct 2026", changes: [
        "Paint status: on any paint, tap Owned, Running low, Empty, Wishlist or Not owned. It's blank until you set one, so nothing changes if you never do. Running low paints have a 'spare in stock' tick.",
        "Search or add a paint on Your Palette: type a name (typos and your shorthand work) to see if you own it, it's running low, or you don't have it. Tap a status to add it.",
        "Paints added by scan count as Owned. The scan's 'Do I own this?' result shows the status too, and you can change it there.",
        "In recipes, each paint shows Have or Missing once you've set a status. 'What can I paint now?' on the Recipes list shows only the recipes where you own every paint.",
        "Shopping list (on Your Palette): running low, empty, wishlist, and paints your recipes use that you don't have, grouped by brand. Copy as text. A spot for shop links is there for later; none are added yet.",
      ]},
      { version: "v16.1", date: "9 Oct 2026", changes: [
        "Pot scanning fixed: it now opens the camera with a box. Line the paint's name up in the box and tap Read label. Only the name is read, with a contrast boost for shiny or metallic labels, so it works far better (tested on white, blue and silver pots).",
        "No more jumbled text when a scan fails: it just says it couldn't read the name. Use a photo instead is still there if the camera won't open.",
      ]},
      { version: "v16", date: "9 Oct 2026", changes: [
        "Paste recipes: paste your painting notes (e.g. from Google Keep) and the app turns them into a scheme, with one recipe per part. You see a preview first, and nothing is saved until you press Save.",
        "It reads parts ending in : or ; , steps one per line or split by commas, arrows (A -> B), numbered lists, mixes like 2:1 Baal:CM or 50/50, and notes in (brackets).",
        "Paint names are matched for you, ignoring capitals and small typos. If it isn't sure (like \"CM\"), it asks you instead of guessing, and remembers your answer for next time.",
        "Copy as text: on a recipe or a scheme. It copies in the same format, so you can share it (e.g. on Reddit) and paste it straight back in.",
        "Scan a paint pot (Your Palette): take a photo of the label and the app suggests the paint, then tells you if you already have it, or adds it. It reads the label on your phone, free. The first scan downloads the reader; after that it works offline.",
        "Settings shows when you last saved a backup. The app now knows the names and colours of the Citadel range, so they're suggested as you type.",
      ]},
      { version: "v15", date: "9 Oct 2026", changes: [
        "Technique can be left on Auto: the app guesses it from the step's paints (shade = Wash, Contrast = Contrast, 'Ardcoat = Varnish, otherwise Layer). Pick one yourself any time.",
        "New \"Whole model\" part, always listed first, for priming, base coats and all-over dry brushes. New techniques: Technical, Texture and Varnish.",
        "Mixes: type a ratio like 2:1 or 1:1:2 and the %s are worked out for you. Contrast Medium and Lahmian Medium are suggested as you type.",
        "Each step can have a short note and an Optional tick. Optional steps show faded.",
        "Basing materials (rocks, sand, snow, static grass…) can go in a step. Your Palette lists them as basing materials, at the end of the colour sort.",
      ]},
      { version: "v14", date: "8 Oct 2026", changes: [
        "Safer saving: units, recipes and settings are now saved together. If storage is full, a big change (like editing your stages or restoring a backup) isn't made at all, instead of being half-saved.",
        "If storage is full, a red banner now stays at the top until saving works again, with a Save backup button. (Before, you were warned once and later changes were quietly lost.)",
        "Open in two places at once? Changes made in one window now appear in the other, instead of one saving over the other.",
        "Delete all units now stops if it can't keep a safety copy, and has an Undo button.",
        "New: Settings → Your data → Recover earlier data. Copies kept by Delete all, Replace and Restore are listed for 30 days, and you can bring one back.",
        "Restoring a backup now tells you if some photos couldn't be loaded, accepts backups that only hold recipes, and refuses backups with a damaged stage list.",
        "Fixed: a faction called \"constructor\" (and a few other special words) could stop the Units list showing. Units are now limited to 999 models.",
        "If your settings ever can't be read, a copy is kept and your units keep their stages.",
        "Editing your stages now keeps each photo's stage label right.",
        "Save backup now shows a message. The backup reminder comes after a week, and reminds you about photos separately. iPhone users opening the app in Safari see a tip to add it to the Home Screen, so their data isn't wiped.",
        "The Warhammer app import button is now called Paste an army list. Only unit names and model counts are kept; points are thrown away.",
        "Help has a new About section: this is an unofficial fan-made tool, not affiliated with Games Workshop.",
      ] },
      { version: "v13", date: "7 Oct 2026", changes: [
        "Several photos per unit. Add photo now adds another photo instead of replacing the old one, and you can pick several at once.",
        "Progress timeline: a unit's photos sit in a strip from oldest to newest, each labelled with its stage (and coloured dot) and date.",
        "Tap a photo to see it full size. Swipe or use ‹ › to move between photos.",
        "In the full-size view, change a photo's stage or date, choose it as the unit's cover photo (shown on its card), or delete it, with Undo.",
        "New Before / after view: two photos side by side, or a slider to wipe between them.",
        "Units tracked model-by-model can label a photo with which model it shows.",
        "Settings → Your data shows how many photos you have and the space they use, and a new Clean up photo storage button removes leftover photo files no unit uses.",
      ] },
      { version: "v12", date: "7 Oct 2026", changes: [
        "Suggested faction colours now work straight away: the app knows the colours well-known factions are usually painted (Ultramarines blue, Orks green, Blood Angels red, Stormcast gold and many more).",
        "If a faction's units have recipes linked, Suggest still prefers a colour from those recipes, and says so.",
        "New Use suggested colours button in Settings → Faction colours: colours every faction that hasn't got one yet, in one tap, with Undo.",
      ]},
      { version: "v11", date: "7 Oct 2026", changes: [
        "Faction colours show more clearly on cards: the faded tint is stronger, dark colours (like deep blue or black) are lightened for the tint so they don't disappear, and it now works on older phones too.",
      ]},
      { version: "v10", date: "7 Oct 2026", changes: [
        "Photos now have far more room. They're kept in the browser's bigger photo storage instead of sharing the small 5 MB space with your units, so you can add many more.",
        "New photos are saved sharper (twice the size as before), with a small copy for the unit list so it stays quick.",
        "Photos you already had are moved across automatically the first time you open this version. Each one is checked before the old copy is removed.",
        "New Save full backup with photos button in Settings. Save backup is still there for a small, quick backup without photos. Restore backup reads both.",
        "Settings now shows roughly how much space the app is using altogether.",
      ]},
      { version: "v9", date: "7 Oct 2026", changes: [
        "Painting schemes: a new Schemes view at the top of the Recipes tab. A scheme is a named group of recipes for one faction, e.g. \"My Ultramarines\" = armour, trim, lenses and base.",
        "Apply a scheme to every unit in its faction with one tap (with Undo). It shows how many of the faction's units already have it.",
        "New units added in that faction (by hand, CSV or Warhammer app import) get the scheme's recipes linked automatically. You can switch this off per scheme.",
        "In a unit's details, the \"Link a recipe\" menu now offers its faction's schemes too.",
        "Renaming a faction moves its schemes with it. Deleting a recipe removes it from schemes (with Undo). Backups include your schemes.",
      ]},
      { version: "v8", date: "7 Oct 2026", changes: [
        "Faction colours: give each faction its own colour in Settings → Faction colours, or tap Faction colours on the dashboard.",
        "Not sure which colour? Press Suggest to pick one from the recipes linked to that faction's units (armour recipes first).",
        "The colour shows as a bar on the dashboard's faction cards, a soft tint and a dot on unit cards, and a stripe on the faction filter. The stage stripe on unit cards stays as it was.",
        "Rename a faction on all its units at once (Settings → Faction colours → Rename). Its colour goes with it.",
        "Backups now include your faction colours.",
      ]},
      { version: "v7", date: "7 Oct 2026", changes: [
        "Progress over time: a new graph on the dashboard showing the models you've added and how many are painted, day by day.",
        "Choose 1 month, 3 months, 1 year or all time. Touch or hover over the graph to read any day's numbers, or open it as a table.",
      ]},
      { version: "v6", date: "7 Oct 2026", changes: [
        "Your Palette: switch to it at the top of the Recipes tab. It lists every paint in your recipes, once each, and fills itself in as you write recipes.",
        "Sort your palette by colour (round the colour wheel, then greys), by name or by brand, and tap a brand to show only its paints.",
        "Tap a paint to change its colour, name or brand everywhere at once, and see which recipes use it. Paints whose colour you haven't set yet are flagged.",
      ]},
      { version: "v5", date: "7 Oct 2026", changes: [
        "New Recipes tab: write down how you paint each part (armour, eyes, trim…) as ordered steps. Each step has a technique, the number of coats, and one or more paints with brand, colour and mix %.",
        "Reorder steps with ↑ ↓, and duplicate a recipe to make a variation.",
        "Link recipes to units. A unit's card shows its recipes as buttons that open them, and each recipe lists the units it's used on.",
        "Add your own parts and techniques to the lists.",
        "Backups now include your recipes.",
      ]},
      { version: "v4", date: "7 Oct 2026", changes: [
        "Paint one model at a time: open a unit with 2 or more models and tick \"Track each model separately\". Each model gets its own stage and ◀ ▲ buttons. The big ▲ on the card moves up whichever model is furthest behind.",
        "The dashboard counts each of those models at its own stage.",
        "The app now quietly notes the date you add a unit and when it changes stage. This is getting ready for a progress-over-time graph.",
      ]},
      { version: "v3", date: "7 Oct 2026", changes: [
        "New final stage: Parade ready. The default order now ends Battle ready → Painted with issues → Parade ready, and all three count as Done. If you were on the old default stages, your units have been moved over automatically.",
        "Edit a unit: open its details to change its name, game or faction.",
        "Units page is tidier on phones: the filters fold away behind a Filters button, so you see more units at once.",
        "Game and faction boxes now suggest names you've already used.",
      ]},
      { version: "v2", date: "6 Oct 2026", changes: [
        "Import a list from the Warhammer app: paste it in Settings and its units are added. Units you already own are skipped and renamed to the app's names.",
        "Export CSV: save your collection as a spreadsheet.",
        "A reminder if you haven't saved a backup in two weeks.",
        "Bigger layout on laptops and desktops, with the tabs along the top.",
        "Bigger tab buttons.",
        "Every import now asks: add to your collection, or replace it? Untick units you don't want, and choose which name to keep when names clash.",
        "This Updates tab, with a link to send feedback, and the version number beside the title.",
        "A Help tab explaining how everything works.",
      ]},
      { version: "v1", date: "5 Oct 2026", changes: [
        "First version: dashboard, units, editable stages, photos and notes.",
        "Backups and CSV import.",
        "Installs on your phone and works offline.",
      ]},
    ];

    function renderUpdates() {
      const link = document.getElementById("feedback-link");
      link.classList.toggle("hidden", !FEEDBACK_URL);
      document.getElementById("feedback-soon").classList.toggle("hidden", !!FEEDBACK_URL);
      // "?version=v2" tells the form which version the tester is on, so they don't have to.
      if (FEEDBACK_URL) link.href = feedbackAddress();
      document.getElementById("version-note").textContent = `You're on version ${APP_VERSION}.`;
      document.getElementById("version-tag").textContent = APP_VERSION;
      const box = document.getElementById("changelog");
      box.innerHTML = "";
      for (const release of CHANGELOG) {
        const div = document.createElement("div");
        div.className = "release";
        const h3 = document.createElement("h3");
        h3.textContent = release.version;
        const date = document.createElement("span");
        date.className = "date";
        date.textContent = release.date;
        h3.appendChild(date);
        const ul = document.createElement("ul");
        for (const change of release.changes) {
          const li = document.createElement("li");
          li.textContent = change;
          ul.appendChild(li);
        }
        div.append(h3, ul);
        box.appendChild(div);
      }
    }

    // ================= START UP =================
    applyPalette(settings.palette);
    seedExampleRecipes();   // v24: only on a brand-new start
    planFeedbackPrompt();   // v25: decides whether the feedback card shows today (saved by the render below)
    render();
    countThisVisit();   // v27: one anonymous visit count (only from minifolio.app, and only if switched on)
    startPhotos();   // moves any old photos across, then loads thumbnails (in the background)
    // Safety copies (Delete all, Replace, Restore, Recover) are kept for 30 days.
    // (Before v14 only Replace's copy expired, after 7 days, using settings.replaceCopyDate.)
    if (settings.replaceCopyDate) { delete settings.replaceCopyDate; saveSettings(); }
    expireSafetyCopies();
    showIphoneWarning();
    renderUpdates();
    showTab(settings.tab);
    if (upgradedStages) showToast("Stages updated: Parade ready added as the final stage", null, null, 8);
    else if (settingsUnreadable) showToast("Your settings couldn't be read, so they were reset. Your units kept their stages, and a copy of the old settings was kept.", null, null, 10);
    else maybeRemindToBackUp();

    // ================= TWO WINDOWS AT ONCE (v14) =================
    // The installed app and a browser tab share the same storage. Before v14 each kept its
    // own copy in memory and saved over the other's changes. Now, when the OTHER window
    // saves, the browser tells this one (the "storage" event) and we load its changes.
    // Screen choices (which tab is open, sort order...) stay this window's own.
    const VIEW_ONLY_SETTINGS = ["tab", "recipeView", "historyRange", "paintSort"];
    const withoutViewSettings = (s) => {
      const copy = { ...s };
      for (const key of VIEW_ONLY_SETTINGS) delete copy[key];
      return JSON.stringify(copy);
    };
    let otherWindowTimer = null;
    window.addEventListener("storage", (event) => {
      if (event.storageArea !== localStorage) return;
      if (event.key !== null && ![STORAGE_KEY, RECIPES_KEY, SETTINGS_KEY].includes(event.key)) return;
      // The other window writes units, recipes and settings one after another: wait a
      // moment so they're all read together.
      clearTimeout(otherWindowTimer);
      otherWindowTimer = setTimeout(loadFromOtherWindow, 150);
    });
    function loadFromOtherWindow() {
      let fresh = null;
      try { fresh = JSON.parse(localStorage.getItem(SETTINGS_KEY) || "null"); } catch (ignored) {}
      const unitsText = (() => { try { return localStorage.getItem(STORAGE_KEY); } catch (e) { return null; } })();
      const recipesText = (() => { try { return localStorage.getItem(RECIPES_KEY); } catch (e) { return null; } })();
      // Nothing that matters changed (e.g. the other window only switched tabs)? Do nothing.
      const sameSettings = !fresh || withoutViewSettings(fresh) === withoutViewSettings(settings);
      if (sameSettings && unitsText === JSON.stringify(models) && recipesText === JSON.stringify(book)) return;

      // v18.3: the other window is a NEWER version that saved newer data: stop saving here.
      if (fresh && Number(fresh.dataVersion) > DATA_VERSION) {
        dataTooNew = true;
        showSaveProblem();
        return;
      }
      if (fresh && typeof fresh === "object" && !Array.isArray(fresh) && usableStages(fresh.stages)) {
        const mine = {};
        for (const key of VIEW_ONLY_SETTINGS) if (key in settings) mine[key] = settings[key];
        settings = { ...settings, ...fresh, ...mine };
        settings.factionColours = cleanFactionColours(settings.factionColours);
        STAGES = settings.stages.map(String);
        fixDoneFrom();
        applyPalette(settings.palette);
      }
      if (unitsText) models = load();
      book = loadRecipes();
      // Drop anything open that no longer exists.
      for (const id of [...openIds]) if (!models.some(m => m.id === id)) openIds.delete(id);
      if (openRecipeId !== null && !book.recipes.some(r => r.id === openRecipeId)) openRecipeId = null;
      // Redraw WITHOUT saving: saving here would just write the same data back and make
      // the other window reload too.
      holdSaves = true;
      try {
        render();
        renderSettings();
      } finally {
        holdSaves = false;
      }
      loadThumbs().catch(() => {});   // new photos added in the other window
      showToast("Updated with changes from another window", null, null, 4);
    }

    // ================= v19: THE PHONE'S BACK BUTTON =================
    // Before v19, the phone's Back button (or a swipe back) left the app from anywhere,
    // even with a photo open. Now Back closes what's open first, one thing per press:
    //   0. (v21.7) a question box ("Delete this unit?"): Back answers No / Cancel
    //   1. the photo viewer           2. the camera, then the scan panel
    //   3. a page on the Recipes tab (paste recipes, a recipe being written or read, a scheme)
    //   4. the import box on the Units tab
    //   4b. (v21.1) select mode on the Units tab (the tick boxes and the Move bar)
    //   5. any tab other than the Dashboard goes back to the Dashboard
    // and only on the Dashboard, with nothing open, does Back leave the app as normal.
    //
    // How: the browser keeps a list of "pages" for its Back button (the history). While
    // something can be closed, the app adds ONE extra step to that list (a "back step").
    // Pressing Back uses it up: the browser tells us ("popstate"), we close the top thing,
    // and add a new step if something else is still open. When nothing is left open (say
    // you pressed ✕ yourself), the spare step is taken away again, so Back never seems to
    // do nothing. The web address never changes.

    // What Back would close right now, as a function that closes it, or null if nothing.
    function backTarget() {
      if (dialogState) return cancelDialog;   // v21.7: a question box sits over everything; Back = No / Cancel
      if (viewer) return closeViewer;
      const tab = settings.tab;
      if (tab === "recipes") {
        if (document.getElementById("scan-camera") || cameraOpening) return closeCamera;
        if (scanState && settings.recipeView === "palette" && !importDraft && !recipeDraft && openRecipeId === null) {
          return () => { scanState = null; closeCamera(); renderScan(); };
        }
        if (importDraft) return () => closeImport(true);
        if (recipeDraft) return () => {
          whenOkToLeaveDraft(() => {   // asks first if there are unsaved changes (v21.7: in the app's own box)
            if (!recipeDraft) return;
            if (recipeDraft.id !== null) openRecipeId = recipeDraft.id;
            recipeDraft = null;
            renderRecipes();
            window.scrollTo(0, 0);
          });
        };
        if (openRecipeId !== null) return () => { openRecipeId = null; renderRecipes(); window.scrollTo(0, 0); };
        if (schemeDraft && settings.recipeView === "schemes") return () => closeScheme(true);
      }
      if (tab === "units" && !unitsImport.classList.contains("hidden")) return closeUnitsImport;
      if (tab === "units" && selectMode) return closeSelect;   // v21.1: select mode's tick boxes
      if (tab && tab !== "dashboard") return () => showTab("dashboard");
      return null;
    }

    let backStep = false;        // true while our extra back step is the current history entry
    // Reloaded (or reopened) while sitting on an old back step? Turn it into a plain entry:
    // the page below it belongs to the page before the reload, so we can't use it.
    if (history.state && history.state.minifolio === "back") {
      try { history.replaceState(null, ""); } catch (e) { /* not allowed: harmless */ }
    }
    let ignoreNextPop = false;   // true while WE asked the browser to go back (to remove a spare step)
    function syncBackStep() {
      const wanted = !!backTarget();
      if (wanted && !backStep) {
        try { history.pushState({ minifolio: "back" }, ""); backStep = true; } catch (e) { /* history blocked: Back works as before */ }
      } else if (!wanted && backStep) {
        backStep = false;
        ignoreNextPop = true;
        history.back();
      }
    }
    window.addEventListener("popstate", () => {
      if (ignoreNextPop) { ignoreNextPop = false; return; }
      backStep = false;            // the browser has just used our step
      const close = backTarget();
      if (close) close();
      syncBackStep();              // something else still open? add a step for it
    });
    // Check after every tap, menu choice or key press. (Not at start-up: a browser ignores
    // back steps added before you've touched the page.) setTimeout lets the tap finish first.
    let backCheckQueued = false;
    function queueBackCheck() {
      if (backCheckQueued) return;
      backCheckQueued = true;
      setTimeout(() => { backCheckQueued = false; syncBackStep(); }, 0);
    }
    for (const type of ["click", "change", "keyup"]) document.addEventListener(type, queueBackCheck, true);

    // ================= v21.8: THE TAB BAR GETS OUT OF THE WAY WHILE YOU TYPE =================
    // On a phone the tab bar is fixed to the bottom of the screen, so when the keyboard
    // opens it can sit right on top of the keyboard and cover what you're typing. While a
    // text box has the cursor, the page gets the mark class "typing" (on <body>); the CSS
    // hides the tab bar for as long as it's there and lowers the message and the Select bar
    // to the bottom edge. When the cursor leaves the text box, the mark goes and the bar
    // is back. (On a wide screen the tabs are a bar at the TOP, which is never in the way,
    // so the CSS only does this on narrower screens.)
    // Boxes that don't open a keyboard (ticks, round buttons, colour pickers, file pickers,
    // sliders, read-only boxes) don't count.
    const KEYBOARD_INPUT_TYPES = new Set(["text", "search", "email", "url", "tel", "password", "number"]);
    function isTextBox(element) {
      if (!element || element.disabled || element.readOnly) return false;
      if (element.tagName === "TEXTAREA") return true;
      if (element.tagName === "INPUT") return KEYBOARD_INPUT_TYPES.has((element.type || "text").toLowerCase());
      return element.isContentEditable === true;
    }
    function updateTyping() {
      document.body.classList.toggle("typing", isTextBox(document.activeElement));
    }
    // Focus moves in and out of boxes; "focusout" is checked a moment later, once we can see
    // where the cursor went (so tapping from one text box to another doesn't flicker the bar).
    // A tap, a key or a menu choice is checked too, in case the box that had the cursor was
    // taken away when the screen was redrawn (the browser doesn't always say so).
    document.addEventListener("focusin", updateTyping, true);
    document.addEventListener("focusout", () => setTimeout(updateTyping, 0), true);
    for (const type of ["click", "change", "keyup"]) document.addEventListener(type, () => setTimeout(updateTyping, 0), true);
    // Pressing a button on the message (Undo) or the Select bar must not take the cursor out
    // of a text box: that would end "typing", the message would jump back up, and the press
    // could miss its button. So a press on those buttons leaves the cursor where it is.
    // (Only buttons: the Select bar's stage menu still needs its normal press to open.)
    for (const id of ["toast", "select-bar"]) {
      const bar = document.getElementById(id);
      if (bar) bar.addEventListener("mousedown", (event) => { if (event.target.closest("button")) event.preventDefault(); });
    }

    // ================= PHASE 6: WORK OFFLINE =================
    // A "service worker" is a small helper script (sw.js) that the browser runs in the
    // background. It keeps a copy of the app on your phone so it opens without internet.
    // "if" checks the browser supports it first, so older browsers just skip this.
    // It only works from a web address (https://...), not from a file opened on your PC.
    if ("serviceWorker" in navigator && location.protocol.startsWith("http")) {
      navigator.serviceWorker.register("sw.js").catch(() => {});
    }
