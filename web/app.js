"use strict";
const $ = (s) => document.querySelector(s);
const $$ = (s) => document.querySelectorAll(s);
const api = async (path, body) => {
  const res = await fetch(path, body === undefined ? {} : { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) throw new Error(data.error || `Error ${res.status}`);
  return data;
};

const LENGTH_FALLBACK = [
  "very short (about 1:00)",
  "short (about 1:30)",
  "about 2:00",
  "about 2:30",
  "standard (about 3:00)",
  "about 3:30",
  "about 4:00",
  "long (about 4:30)",
  "about 5:00",
  "very long (about 6:00)",
];

const ARRANGEMENT_FALLBACK = [
  "off",
  "standard",
  "sterile",
  "unplugged",
  "varied",
  "call and response",
  "signature motif",
  "hypnotic",
  "breakdown",
  "dramatic",
  "many instruments",
  "jazz colours",
  "fantasy",
  "key change",
];

const TEMPLATE_FALLBACK = [
  "none",
  "african/afrobeat-classic-instrumental",
  "african/afrobeats-vocal",
  "african/amapiano-instrumental",
  "african/desert-blues-vocal",
  "african/ethio-jazz-instrumental",
  "african/gqom-instrumental",
  "african/highlife-instrumental",
  "african/soukous-instrumental",
  "alternative/alternative-rock-vocal",
  "alternative/britpop-vocal",
  "alternative/new-wave-vocal",
  "alternative/uk-garage-vocal",
  "ambient/ambient-choir-vocalise",
  "ambient/ambient-guitar",
  "ambient/chillout-pads-strings",
  "ambient/dark-ambient-drone",
  "asian/anime-opening-vocal",
  "asian/bollywood-vocal",
  "asian/chinese-traditional-instrumental",
  "asian/city-pop-vocal",
  "asian/enka-vocal",
  "asian/game-jrpg-orchestral",
  "asian/indian-classical-instrumental",
  "asian/kpop-vocal",
  "asian/mandopop-ballad-vocal",
  "blues/blues-ballad-vocal",
  "blues/boogie-woogie-instrumental",
  "blues/chicago-blues-vocal",
  "blues/delta-blues-vocal",
  "blues/electric-blues-instrumental",
  "cinematic/corporate-uplifting-instrumental",
  "cinematic/documentary-underscore-instrumental",
  "cinematic/emotional-piano-underscore",
  "cinematic/epic-trailer-instrumental",
  "cinematic/fantasy-adventure-orchestral",
  "cinematic/horror-suspense-instrumental",
  "cinematic/orchestral-action-instrumental",
  "cinematic/sports-stadium-anthem",
  "classical/baroque-concerto-instrumental",
  "classical/cello-and-piano",
  "classical/choral-sacred-vocal",
  "classical/cinematic-romance",
  "classical/gregorian-chant-vocal",
  "classical/impressionist-piano-instrumental",
  "classical/minimalism-instrumental",
  "classical/mystical-neoclassical",
  "classical/neoclassical-piano",
  "classical/opera-aria-vocal",
  "classical/piano-and-strings",
  "classical/romantic-string-ensemble",
  "classical/string-quartet-instrumental",
  "classical/symphonic-orchestral-instrumental",
  "comedy/comedy-rap-vocal",
  "comedy/english-parody-pop-vocal",
  "comedy/german-absurd-novelty",
  "country/americana-vocal",
  "country/bluegrass-instrumental",
  "country/country-ballad-vocal",
  "country/honky-tonk-vocal",
  "country/modern-country-pop-vocal",
  "country/outlaw-country-vocal",
  "disco/classic-disco-vocal",
  "disco/italo-disco-vocal",
  "edm/big-room-festival-instrumental",
  "edm/breakbeat-instrumental",
  "edm/dance-anthem-instrumental",
  "edm/drum-and-bass-instrumental",
  "edm/dubstep-instrumental",
  "edm/eurodance-vocal",
  "edm/future-bass-vocal",
  "edm/future-rave-sparse-vocals",
  "edm/goa-trance-instrumental",
  "edm/hardgroove-techno-instrumental",
  "edm/hardstyle-instrumental",
  "edm/jungle-instrumental",
  "edm/liquid-drum-and-bass-sparse-vocals",
  "edm/melodic-techno-instrumental",
  "edm/neurofunk-dnb-instrumental",
  "edm/progressive-trance-instrumental",
  "edm/psytrance-instrumental",
  "edm/uplifting-trance-instrumental",
  "electronic/analog-space-electronic",
  "electronic/berlin-school-sequencer",
  "electronic/chiptune-instrumental",
  "electronic/cinematic-electronica",
  "electronic/downtempo-electronica",
  "electronic/ebm-darkwave-vocal",
  "electronic/electro-swing-vocal",
  "electronic/idm-experimental-instrumental",
  "electronic/lofi-hiphop-instrumental",
  "electronic/minimal-electronic-german-vocals",
  "electronic/peak-time-techno-sparse-vocals",
  "electronic/synth-pop-vocal",
  "electronic/synthwave",
  "electronic/trip-hop",
  "electronic/vaporwave-instrumental",
  "european/alpine-volksmusik-instrumental",
  "european/balkan-brass-instrumental",
  "european/chanson-vocal",
  "european/fado-vocal",
  "european/flamenco-instrumental",
  "european/irish-pub-session-instrumental",
  "european/klezmer-instrumental",
  "european/polka-instrumental",
  "european/russian-folk-vocal",
  "european/schlager-vocal",
  "european/viennese-waltz-instrumental",
  "folk/appalachian-folk-instrumental",
  "folk/celtic-folk-vocal",
  "folk/dark-fairytale-folk-vocal",
  "folk/folk-punk-vocal",
  "folk/melancholic-folk-ballad-vocal",
  "folk/mystical-medieval-folk-vocal",
  "folk/nordic-folk-vocal",
  "folk/romantic-solo-guitar",
  "folk/sea-shanty-vocal",
  "funk/classic-funk-instrumental",
  "funk/nu-disco-funk",
  "gospel/contemporary-worship-vocal",
  "gospel/german-worship-vocal",
  "gospel/gospel-choir-vocal",
  "gospel/hymn-choir-vocal",
  "hiphop/boom-bap-hiphop-vocal",
  "hiphop/cloud-rap-vocal",
  "hiphop/drill-instrumental",
  "hiphop/german-rap-vocal",
  "hiphop/old-school-hiphop-vocal",
  "hiphop/phonk-instrumental",
  "hiphop/rnb-vocal",
  "hiphop/trap-instrumental",
  "house/acid-house-instrumental",
  "house/afro-house-vocal",
  "house/bass-house-instrumental",
  "house/deep-house",
  "house/disco-house-vocal",
  "house/electro-house-instrumental",
  "house/french-house-instrumental",
  "house/melodic-house",
  "house/organic-house",
  "house/progressive-house-dreamy-bittersweet",
  "house/progressive-house-melodic-trance",
  "house/progressive-house-sparse-vocals",
  "house/tech-house-instrumental",
  "jazz/bebop-instrumental",
  "jazz/cool-jazz-instrumental",
  "jazz/dixieland-instrumental",
  "jazz/gypsy-jazz-instrumental",
  "jazz/jazz-funk",
  "jazz/smooth-jazz-instrumental",
  "jazz/smooth-jazz-vocal-late-night",
  "jazz/smooth-jazz-vocal-positive-resolution",
  "jazz/swing-big-band-instrumental",
  "jazz/vocal-jazz-crooner",
  "kids/children-song-vocal",
  "kids/kids-adventure-song-vocal",
  "kids/lullaby-vocal",
  "kids/nursery-rhyme-german-vocal",
  "latin/bachata-vocal",
  "latin/bossa-nova-vocal",
  "latin/cumbia-instrumental",
  "latin/merengue-instrumental",
  "latin/norteno-corrido-vocal",
  "latin/reggaeton-vocal",
  "latin/salsa-vocal",
  "latin/samba-instrumental",
  "latin/son-cubano-vocal",
  "latin/tango-instrumental",
  "meditation/focus-study-instrumental",
  "meditation/meditation-healing-instrumental",
  "meditation/nature-soundscape-instrumental",
  "meditation/sleep-music-instrumental",
  "metal/black-metal-instrumental",
  "metal/death-metal-vocal",
  "metal/doom-metal-instrumental",
  "metal/folk-metal-vocal",
  "metal/grunge-vocal",
  "metal/heavy-metal-vocal",
  "metal/industrial-metal-vocal",
  "metal/melodic-metal-instrumental",
  "metal/metalcore-vocal",
  "metal/nu-metal-vocal",
  "metal/power-metal-vocal",
  "metal/progressive-djent-instrumental",
  "metal/sludge-post-metal-instrumental",
  "metal/symphonic-metal-vocal",
  "metal/thrash-metal-vocal",
  "musical/broadway-ballad-vocal",
  "musical/german-musical-vocal",
  "musical/musical-theatre-ensemble-vocal",
  "pop/art-pop-vocal",
  "pop/bedroom-pop-vocal",
  "pop/dance-pop-vocal",
  "pop/dream-pop-electronic-vocal",
  "pop/german-pop-vocal",
  "pop/hyperpop-vocal",
  "pop/indie-pop-vocal",
  "pop/power-ballad-vocal",
  "pop/singer-songwriter-acoustic-vocal",
  "punk/pop-punk-vocal",
  "punk/post-punk-vocal",
  "punk/punk-rock-vocal",
  "punk/ska-punk-vocal",
  "reggae/dancehall-vocal",
  "reggae/dub-instrumental",
  "reggae/rocksteady-vocal",
  "reggae/roots-reggae-vocal",
  "reggae/ska-jamaican-instrumental",
  "rock/blues-rock-instrumental",
  "rock/classic-rock-vocal",
  "rock/garage-rock-vocal",
  "rock/hard-rock-vocal",
  "rock/indie-rock-vocal",
  "rock/post-rock-instrumental",
  "rock/progressive-rock-instrumental",
  "rock/psychedelic-rock-instrumental",
  "rock/rockabilly-vocal",
  "rock/shoegaze-vocal",
  "rock/southern-rock-vocal",
  "rock/stoner-rock-instrumental",
  "rock/surf-rock-instrumental",
  "seasonal/christmas-carol-vocal",
  "seasonal/christmas-pop-vocal",
  "seasonal/german-christmas-vocal",
  "seasonal/wedding-ceremony-instrumental",
  "soul/doo-wop-vocal",
  "soul/motown-soul-vocal",
  "soul/neo-soul-vocal",
  "soul/soul-ballad-vocal",
  "world/andean-folk-instrumental",
  "world/arabic-pop-vocal",
  "world/bhangra-instrumental",
  "world/calypso-soca-vocal",
  "world/gamelan-instrumental",
  "world/gnawa-instrumental",
  "world/hawaiian-slack-key-instrumental",
  "world/mariachi-vocal",
  "world/mongolian-throat-singing-instrumental",
  "world/qawwali-vocal",
  "world/turkish-folk-instrumental",
];

const FIELDS = [
  { k: "template", label: "f_template", fallback: TEMPLATE_FALLBACK, tip: "tip_template" },
  { k: "description", label: "f_description", type: "textarea", rows: 3, tip: "tip_description" },
  { k: "genre", label: "f_genre", tip: "tip_genre" },
  { k: "mood", label: "f_mood", tip: "tip_mood" },
  { k: "tempo", label: "f_tempo", tip: "tip_tempo" },
  { k: "key", label: "f_key", tip: "tip_key" },
  { k: "meter", label: "f_meter", tip: "tip_meter" },
  { k: "length", label: "f_length", fallback: LENGTH_FALLBACK, tip: "tip_length" },
  { k: "vocals", label: "f_vocals", fallback: ["sung", "sparse vocals", "instrumental"], tip: "tip_vocals" },
  { k: "vocals.language", label: "f_language", tip: "tip_language" },
  { k: "vocals.voice", label: "f_voice", tip: "tip_voice" },
  { k: "vocals.theme", label: "f_theme", type: "textarea", rows: 3, tip: "tip_theme" },
  { k: "arrangement", label: "f_arrangement", fallback: ARRANGEMENT_FALLBACK, tip: "tip_arrangement" },
  { k: "genre_closeness", label: "f_closeness", type: "range", tip: "tip_closeness", def: 70 },
  { k: "creativity", label: "f_creativity", type: "range", tip: "tip_creativity", def: 50 },
  { k: "lyrics_fidelity", label: "f_lyrics_fidelity", fallback: ["standard", "high - best of 2 takes", "highest - best of 3 takes"], tip: "tip_lyrics_fidelity", def: "standard" },
  { k: "lines_under_singing", label: "f_lines", type: "checkbox", tip: "tip_lines" },
];

const DOC_INPUTS = { title: "shTitle", style: "shStyle", lyrics: "shLyrics", artwork_prompt: "shArt" };
const DOC_KEYS = Object.keys(DOC_INPUTS);

const S = {
  mode: "review", defaults: null, options: {}, job: null, timer: null, brief: {}, status: null,
  sheetState: { title: "auto", style: "auto", lyrics: "auto", artwork_prompt: "auto" },
  lastDraft: {}, applioAvailable: true, voiceModels: [],
};
const STORE = "tamusicmaker.v1";

function toast(msg, isErr) {
  const tr = $("#toast");
  tr.textContent = msg; tr.className = "toast" + (isErr ? " err" : ""); tr.hidden = false;
  clearTimeout(toast.h); toast.h = setTimeout(() => (tr.hidden = true), isErr ? 9000 : 3500);
}

// ---------------------------------------------------------------- form
function buildForm() {
  const root = $("#briefForm");
  root.innerHTML = "";
  for (const f of FIELDS) {
    const wrap = document.createElement("label");
    wrap.className = f.type === "checkbox" ? "check" : "field";
    const val = S.brief[f.k] != null ? S.brief[f.k] : f.def;
    if (S.brief[f.k] == null && f.def != null) S.brief[f.k] = f.def;
    const lbl = t(f.label);
    let el;
    if (f.type === "textarea") { el = document.createElement("textarea"); el.rows = f.rows || 3; }
    else if (f.type === "checkbox") { el = document.createElement("input"); el.type = "checkbox"; el.checked = !!val; }
    else if (f.type === "range") { el = document.createElement("input"); el.type = "range"; el.min = 0; el.max = 100; }
    else {
      const opts = S.options[f.k] || f.fallback;
      if (opts && opts.length) {
        el = document.createElement("select");
        const all = opts.includes(val) || val == null ? opts : [val, ...opts];
        for (const o of all) { const op = document.createElement("option"); op.value = op.textContent = o; el.appendChild(op); }
      } else el = document.createElement("input");
    }
    el.dataset.key = f.k;
    if (f.type !== "checkbox" && val != null) el.value = val;
    el.addEventListener("input", () => { S.brief[f.k] = f.type === "checkbox" ? el.checked : f.type === "range" ? Number(el.value) : el.value; persist(); if (f.type === "range") span.textContent = el.value; });
    let span = document.createElement("span");
    span.textContent = f.type === "range" ? `${lbl}: ${el.value}` : lbl;

    let tipEl = null;
    if (f.tip) {
      tipEl = document.createElement("span");
      tipEl.className = "tip-icon";
      tipEl.textContent = "?";
      tipEl.dataset.tip = t(f.tip);
      tipEl.dataset.i18nTip = f.tip;
    }

    if (f.type === "range") {
      span.textContent = el.value;
      const lab = document.createElement("span");
      lab.className = "field-head";
      lab.textContent = lbl + ": ";
      lab.appendChild(span);
      if (tipEl) lab.appendChild(tipEl);
      wrap.append(lab, el);
    } else if (f.type === "checkbox") {
      wrap.append(el, span);
      if (tipEl) wrap.append(tipEl);
    } else {
      const head = document.createElement("span");
      head.className = "field-head";
      head.append(span);
      if (tipEl) head.append(tipEl);
      wrap.append(head, el);
    }
    root.appendChild(wrap);
  }
}

function collectMastering() {
  return {
    enabled: $("#mstEnabled")?.checked !== false,
    eq_mode: $("#mstEqMode")?.value || "match preset",
    eq_preset: $("#mstEqPreset")?.value || "Warm - gentle (workflow default)",
    eq_target: $("#mstEqTarget")?.value || "warm",
    eq_strength: parseFloat($("#mstEqStrength")?.value || "0.35"),
    eq_max_gain_db: parseFloat($("#mstEqMaxGain")?.value || "2.0"),
    eq_max_bands: parseInt($("#mstEqMaxBands")?.value || "4", 10),
    loudness_target: $("#mstLoudTarget")?.value || "streaming (-14 LUFS, -1 dBTP)",
    custom_lufs: parseFloat($("#mstCustomLufs")?.value || "-14.0"),
    custom_ceiling: parseFloat($("#mstCustomCeiling")?.value || "-1.0"),
    compression: $("#mstCompression")?.value || "Balanced - gentle glue",
    comp_threshold: parseFloat($("#mstCompThreshold")?.value || "-18.0"),
    comp_ratio: parseFloat($("#mstCompRatio")?.value || "1.5"),
    comp_knee: parseFloat($("#mstCompKnee")?.value || "6.0"),
    comp_attack: parseFloat($("#mstCompAttack")?.value || "20"),
    comp_release: parseFloat($("#mstCompRelease")?.value || "150"),
    comp_sidechain: parseFloat($("#mstCompSidechain")?.value || "80"),
    comp_detector: $("#mstCompDetector")?.value || "RMS",
    sample_rate: $("#mstSampleRate")?.value || "keep",
  };
}

function collectAudioHq() {
  return {
    stereo_enabled: $("#hqStereoEnabled")?.checked !== false,
    stereo_preset: $("#hqStereoPreset")?.value || "auto - from the song's genre",
    stereo_highcut_hz: parseFloat($("#hqStereoHighcut")?.value || "10500"),
    stereo_cleanup: parseFloat($("#hqStereoCleanup")?.value || "0.65"),
    stereo_warmth: parseFloat($("#hqStereoWarmth")?.value || "0.18"),
    regen_enabled: !!$("#hqRegenEnabled")?.checked,
    regen_preset: $("#hqRegenPreset")?.value || "auto - from the song's genre",
    regen_steps: parseInt($("#hqRegenSteps")?.value || "4", 10),
    regen_seed: parseInt($("#hqRegenSeed")?.value || "0", 10),
    regen_from_hz: parseFloat($("#hqRegenFromHz")?.value || "8200"),
    regen_new_share: parseFloat($("#hqRegenNewShare")?.value || "0.85"),
    regen_level_match: parseFloat($("#hqRegenLevelMatch")?.value || "0.90"),
    dereverb_enabled: !!$("#hqDereverbEnabled")?.checked,
    dereverb_preset: $("#hqDereverbPreset")?.value || "auto - from the song's genre",
    dereverb_amount: parseFloat($("#hqDereverbAmount")?.value || "0.35"),
    dereverb_phase_lock: parseFloat($("#hqDereverbPhaseLock")?.value || "0.35"),
  };
}

function collectRefineCfg() {
  return {
    engine: $("#refEngine")?.value || "resample only",
    model: $("#refModel")?.value || "pytorch_model.bin",
    preset: $("#refPreset")?.value || "custom - the three fields below",
    sr_gain: parseFloat($("#refGain")?.value || "1.0"),
    crossover_hz: parseFloat($("#refCrossover")?.value || "0"),
    pre_hz: parseFloat($("#refPreHz")?.value || "0"),
    post_hz: parseFloat($("#refPostHz")?.value || "0"),
    seed: parseInt($("#refSeed")?.value || "0", 10),
  };
}

function updateMasteringUI() {
  if ($("#expSheetBox")) $("#expSheetBox").hidden = !$("#expSheet")?.checked;

  const mstOn = $("#mstEnabled")?.checked !== false;
  if ($("#mstBody")) $("#mstBody").hidden = !mstOn;
  const eqMode = $("#mstEqMode")?.value || "match preset";
  if ($("#mstEqPresetBox")) $("#mstEqPresetBox").hidden = eqMode !== "match preset";
  if ($("#mstEqCustomBox")) $("#mstEqCustomBox").hidden = eqMode !== "custom match";
  const loudTarget = $("#mstLoudTarget")?.value || "streaming (-14 LUFS, -1 dBTP)";
  if ($("#mstLoudCustomBox")) $("#mstLoudCustomBox").hidden = loudTarget !== "custom";
  const comp = $("#mstCompression")?.value || "Balanced - gentle glue";
  if ($("#mstCompCustomBox")) $("#mstCompCustomBox").hidden = comp !== "custom";

  const stOn = $("#hqStereoEnabled")?.checked !== false;
  if ($("#hqStereoBody")) $("#hqStereoBody").hidden = !stOn;
  const stPreset = $("#hqStereoPreset")?.value || "auto - from the song's genre";
  if ($("#hqStereoCustomBox")) $("#hqStereoCustomBox").hidden = !stPreset.startsWith("custom");

  const rgOn = !!$("#hqRegenEnabled")?.checked;
  if ($("#hqRegenBody")) $("#hqRegenBody").hidden = !rgOn;
  const rgPreset = $("#hqRegenPreset")?.value || "auto - from the song's genre";
  if ($("#hqRegenCustomBox")) $("#hqRegenCustomBox").hidden = !rgPreset.startsWith("custom");

  const drOn = !!$("#hqDereverbEnabled")?.checked;
  if ($("#hqDereverbBody")) $("#hqDereverbBody").hidden = !drOn;
  const drPreset = $("#hqDereverbPreset")?.value || "auto - from the song's genre";
  if ($("#hqDereverbCustomBox")) $("#hqDereverbCustomBox").hidden = !drPreset.startsWith("custom");

  const refOn = !!$("#optRefine")?.checked;
  if ($("#refEnabled")) $("#refEnabled").checked = refOn;
  if ($("#refBody")) $("#refBody").hidden = !refOn;
  const refEng = $("#refEngine")?.value || "resample only";
  if ($("#refModelBox")) $("#refModelBox").hidden = refEng !== "model";
  const refPreset = $("#refPreset")?.value || "custom - the three fields below";
  if ($("#refCustomFreqBox")) $("#refCustomFreqBox").hidden = !refPreset.startsWith("custom");
}

function populateSrModels() {
  const sel = $("#refModel");
  if (!sel) return;
  const cur = sel.value || "pytorch_model.bin";
  const models = S.options?._audio_sr_models;
  const list = Array.isArray(models) && models.length ? models : ["pytorch_model.bin"];
  if (!list.includes(cur)) list.unshift(cur);
  sel.innerHTML = "";
  for (const m of list) {
    const opt = document.createElement("option");
    opt.value = opt.textContent = m;
    sel.appendChild(opt);
  }
  sel.value = cur;
}

function resetMasteringDefaults() {
  if ($("#mstEnabled")) $("#mstEnabled").checked = true;
  if ($("#hqStereoEnabled")) $("#hqStereoEnabled").checked = true;
  if ($("#hqStereoPreset")) $("#hqStereoPreset").value = "auto - from the song's genre";
  if ($("#hqStereoHighcut")) $("#hqStereoHighcut").value = "10500";
  if ($("#hqStereoCleanup")) $("#hqStereoCleanup").value = "0.65";
  if ($("#hqStereoWarmth")) $("#hqStereoWarmth").value = "0.18";
  if ($("#hqRegenEnabled")) $("#hqRegenEnabled").checked = false;
  if ($("#hqRegenPreset")) $("#hqRegenPreset").value = "auto - from the song's genre";
  if ($("#hqRegenSteps")) $("#hqRegenSteps").value = "4";
  if ($("#hqRegenSeed")) $("#hqRegenSeed").value = "0";
  if ($("#hqRegenFromHz")) $("#hqRegenFromHz").value = "8200";
  if ($("#hqRegenNewShare")) $("#hqRegenNewShare").value = "0.85";
  if ($("#hqRegenLevelMatch")) $("#hqRegenLevelMatch").value = "0.90";
  if ($("#hqDereverbEnabled")) $("#hqDereverbEnabled").checked = false;
  if ($("#hqDereverbPreset")) $("#hqDereverbPreset").value = "auto - from the song's genre";
  if ($("#hqDereverbAmount")) $("#hqDereverbAmount").value = "0.35";
  if ($("#hqDereverbPhaseLock")) $("#hqDereverbPhaseLock").value = "0.35";
  if ($("#mstEqMode")) $("#mstEqMode").value = "match preset";
  if ($("#mstEqPreset")) $("#mstEqPreset").value = "Warm - gentle (workflow default)";
  if ($("#mstEqTarget")) $("#mstEqTarget").value = "warm";
  if ($("#mstEqStrength")) $("#mstEqStrength").value = "0.35";
  if ($("#mstEqMaxGain")) $("#mstEqMaxGain").value = "2.0";
  if ($("#mstEqMaxBands")) $("#mstEqMaxBands").value = "4";
  if ($("#mstLoudTarget")) $("#mstLoudTarget").value = "streaming (-14 LUFS, -1 dBTP)";
  if ($("#mstCustomLufs")) $("#mstCustomLufs").value = "-14.0";
  if ($("#mstCustomCeiling")) $("#mstCustomCeiling").value = "-1.0";
  if ($("#mstCompression")) $("#mstCompression").value = "Balanced - gentle glue";
  if ($("#mstCompThreshold")) $("#mstCompThreshold").value = "-18.0";
  if ($("#mstCompRatio")) $("#mstCompRatio").value = "1.5";
  if ($("#mstCompKnee")) $("#mstCompKnee").value = "6.0";
  if ($("#mstCompAttack")) $("#mstCompAttack").value = "20";
  if ($("#mstCompRelease")) $("#mstCompRelease").value = "150";
  if ($("#mstCompSidechain")) $("#mstCompSidechain").value = "80";
  if ($("#mstCompDetector")) $("#mstCompDetector").value = "RMS";
  if ($("#mstSampleRate")) $("#mstSampleRate").value = "keep";
  if ($("#optRefine")) $("#optRefine").checked = false;
  if ($("#refEnabled")) $("#refEnabled").checked = false;
  if ($("#refEngine")) $("#refEngine").value = "resample only";
  if ($("#refModel")) $("#refModel").value = "pytorch_model.bin";
  if ($("#refPreset")) $("#refPreset").value = "custom - the three fields below";
  if ($("#refGain")) $("#refGain").value = "1.0";
  if ($("#refCrossover")) $("#refCrossover").value = "0";
  if ($("#refPreHz")) $("#refPreHz").value = "0";
  if ($("#refPostHz")) $("#refPostHz").value = "0";
  if ($("#refSeed")) $("#refSeed").value = "0";
  updateMasteringUI();
  persist();
  toast(t("mstResetDone"));
}

function collectOptions() {
  const sheetOn = !!$("#expSheet")?.checked;
  return {
    cover: $("#optCover").checked, stems: $("#optStems").checked, refine: $("#optRefine").checked,
    voice_swap: (S.applioAvailable && $("#optVoiceSwap")?.checked) || false,
    voice_model: $("#voiceModelSelect")?.value,
    voice_pitch: parseInt($("#voicePitch")?.value || "0", 10),
    voice_index_rate: parseFloat($("#voiceIndexRate")?.value || "0.75"),
    srt_en: $("#expSrtEn")?.checked !== false,
    writer_model: S.defaults?.writer_model || undefined,
    export: {
      flac: $("#expFlac").checked,
      mp3: $("#expMp3").checked,
      wav: $("#expWav").checked,
      lyrics_srt: $("#expSrt").checked,
      sheet_music: sheetOn ? ($("#expSheetFormat")?.value || "PDF (A4)") : "off",
      sheet_music_size: $("#expSheetSize")?.value || "standard",
      folder: $("#expFolder").value || "plenio",
    },
    mastering: collectMastering(),
    audio_hq: collectAudioHq(),
    refine_cfg: collectRefineCfg(),
  };
}
function sheetData() { return { title: $("#shTitle").value.trim(), style: $("#shStyle").value.trim(), lyrics: $("#shLyrics").value.trim(), artwork_prompt: $("#shArt").value.trim() }; }

// ---------------------------------------------------------------- sheet states (auto / manual)
function refreshDocBadges() {
  for (const k of DOC_KEYS) {
    const st = S.sheetState[k] === "manual" ? "manual" : "auto";
    const badge = $("#badge-" + k);
    if (badge) {
      badge.textContent = t(st === "manual" ? "stateManual" : "stateAuto");
      badge.className = "badge" + (st === "manual" ? " manual" : "");
    }
    const btnAuto = $(`[data-doc-auto="${k}"]`);
    const btnMan = $(`[data-doc-manual="${k}"]`);
    if (btnAuto) btnAuto.disabled = st === "auto";
    if (btnMan) btnMan.disabled = st === "manual";
  }
  const labels = { title: "title", style: "style", lyrics: "lyrics", artwork_prompt: "artwork" };
  $("#sheetInfo").textContent = DOC_KEYS.map((k) => `${labels[k]}: ${t(S.sheetState[k] === "manual" ? "stateManual" : "stateAuto")}`).join(" · ");
}

function setDocState(kind, state, fromBackBtn) {
  S.sheetState[kind] = state === "manual" ? "manual" : "auto";
  if (fromBackBtn && S.sheetState[kind] === "auto") {
    const inp = $("#" + DOC_INPUTS[kind]);
    if (inp) inp.value = S.lastDraft[kind] || "";
  }
  refreshDocBadges();
  updateLyricCount();
  persist();
}

function insertSectionTag(tag) {
  const ta = $("#shLyrics");
  const start = ta.selectionStart ?? ta.value.length;
  const end = ta.selectionEnd ?? ta.value.length;
  const before = ta.value.slice(0, start);
  const after = ta.value.slice(end);
  const needPre = before.length > 0 && !before.endsWith("\n") ? "\n\n" : (before.endsWith("\n") && !before.endsWith("\n\n") && before.trim().length > 0 ? "\n" : "");
  const needPost = after.startsWith("\n") ? "" : "\n";
  const insert = `${needPre}${tag}${needPost}`;
  ta.value = before + insert + after;
  const pos = before.length + insert.length;
  ta.focus();
  ta.setSelectionRange(pos, pos);
  setDocState("lyrics", "manual");
}

// YuE2 takes the singer's gender from the style text only; make sure it matches the briefing.
function ensureVoice() {
  if (!["sung", "sparse vocals"].includes(S.brief.vocals || "sung")) return;
  let style = $("#shStyle").value.trim();
  if (!style) return; // empty auto style will be generated by the writer model
  const voice = String(S.brief["vocals.voice"] || "");
  const FEM = /\b(female|woman|women|girl|soprano|mezzo-?soprano|alto|contralto)\b/i, MAL = /\b(male|man|men|boy|baritone|tenor|bass voice)\b/i;
  const want = FEM.test(voice) ? "female" : MAL.test(voice) ? "male" : "";
  if (!want) return;
  const other = want === "male" ? FEM : MAL, own = want === "male" ? MAL : FEM;
  if (own.test(style) && !other.test(style)) return;
  style = style.replace(new RegExp(other.source, "gi"), "").replace(/\s{2,}/g, " ").replace(/\s+,/g, ",").replace(/^[,\s]+/, "");
  $("#shStyle").value = `${want} vocals, ${style}`.trim();
  persist();
  toast(t("styleUpdated", { v: want }));
}

function planSeedValue() { return $("#planSeedRandom").checked ? null : ($("#planSeed").value || null); }
function draftSeedValue() { return $("#draftSeedRandom").checked ? null : ($("#draftSeed").value || null); }

function persist() {
  const data = {
    brief: S.brief, mode: S.mode, sheet: sheetData(), sheetState: S.sheetState, opts: collectOptions(),
    draftSeed: $("#draftSeed").value, rnd: $("#draftSeedRandom").checked,
    planSeed: $("#planSeed").value, planRnd: $("#planSeedRandom").checked,
    count: $("#autoCount").value, lang: LANG,
  };
  localStorage.setItem(STORE, JSON.stringify(data));
}

function restore() {
  let saved = {};
  try { saved = JSON.parse(localStorage.getItem(STORE) || "{}"); } catch {}
  if (saved.lang && I18N[saved.lang]) LANG = saved.lang;
  S.brief = { ...(S.defaults?.brief || {}), ...(saved.brief || {}) };
  const ex = { ...(S.defaults?.export || {}), ...(saved.opts?.export || {}) };
  $("#optCover").checked = !!saved.opts?.cover; $("#optStems").checked = !!saved.opts?.stems; $("#optRefine").checked = !!saved.opts?.refine;
  $("#optVoiceSwap").checked = !!saved.opts?.voice_swap;
  $("#voiceSwapOptions").hidden = !$("#optVoiceSwap").checked;
  if (saved.opts?.voice_pitch !== undefined) $("#voicePitch").value = saved.opts.voice_pitch;
  if (saved.opts?.voice_index_rate !== undefined) $("#voiceIndexRate").value = saved.opts.voice_index_rate;
  $("#expFlac").checked = ex.flac !== false; $("#expMp3").checked = !!ex.mp3; $("#expWav").checked = !!ex.wav; $("#expSrt").checked = ex.lyrics_srt !== false;
  if ($("#expSrtEn")) $("#expSrtEn").checked = saved.opts?.srt_en !== false;
  if ($("#expSheet")) $("#expSheet").checked = !!(ex.sheet_music && ex.sheet_music !== "off");
  if (ex.sheet_music && ex.sheet_music !== "off" && $("#expSheetFormat")) $("#expSheetFormat").value = ex.sheet_music;
  if (ex.sheet_music_size && $("#expSheetSize")) $("#expSheetSize").value = ex.sheet_music_size;
  $("#expFolder").value = ex.folder || "plenio";
  $("#draftSeed").value = saved.draftSeed || S.defaults?.draft_seed || "";
  $("#draftSeedRandom").checked = saved.rnd !== undefined ? saved.rnd : false;
  $("#autoCount").value = saved.count || 3;
  $("#planSeed").value = saved.planSeed || 1; $("#planSeedRandom").checked = !!saved.planRnd;
  const sh = saved.sheet || {};
  $("#shTitle").value = sh.title || ""; $("#shStyle").value = sh.style || ""; $("#shLyrics").value = sh.lyrics || ""; $("#shArt").value = sh.artwork_prompt || "";
  for (const k of DOC_KEYS) {
    S.sheetState[k] = saved.sheetState?.[k] === "manual" ? "manual" : "auto";
  }

  const mst = saved.opts?.mastering || {};
  if ($("#mstEnabled")) $("#mstEnabled").checked = mst.enabled !== false;
  if (mst.eq_mode && $("#mstEqMode")) $("#mstEqMode").value = mst.eq_mode;
  if (mst.eq_preset && $("#mstEqPreset")) $("#mstEqPreset").value = mst.eq_preset;
  if (mst.eq_target && $("#mstEqTarget")) $("#mstEqTarget").value = mst.eq_target;
  if (mst.eq_strength !== undefined && $("#mstEqStrength")) $("#mstEqStrength").value = mst.eq_strength;
  if (mst.eq_max_gain_db !== undefined && $("#mstEqMaxGain")) $("#mstEqMaxGain").value = mst.eq_max_gain_db;
  if (mst.eq_max_bands !== undefined && $("#mstEqMaxBands")) $("#mstEqMaxBands").value = mst.eq_max_bands;
  if (mst.loudness_target && $("#mstLoudTarget")) $("#mstLoudTarget").value = mst.loudness_target;
  if (mst.custom_lufs !== undefined && $("#mstCustomLufs")) $("#mstCustomLufs").value = mst.custom_lufs;
  if (mst.custom_ceiling !== undefined && $("#mstCustomCeiling")) $("#mstCustomCeiling").value = mst.custom_ceiling;
  if (mst.compression && $("#mstCompression")) $("#mstCompression").value = mst.compression;
  if (mst.comp_threshold !== undefined && $("#mstCompThreshold")) $("#mstCompThreshold").value = mst.comp_threshold;
  if (mst.comp_ratio !== undefined && $("#mstCompRatio")) $("#mstCompRatio").value = mst.comp_ratio;
  if (mst.comp_knee !== undefined && $("#mstCompKnee")) $("#mstCompKnee").value = mst.comp_knee;
  if (mst.comp_attack !== undefined && $("#mstCompAttack")) $("#mstCompAttack").value = mst.comp_attack;
  if (mst.comp_release !== undefined && $("#mstCompRelease")) $("#mstCompRelease").value = mst.comp_release;
  if (mst.comp_sidechain !== undefined && $("#mstCompSidechain")) $("#mstCompSidechain").value = mst.comp_sidechain;
  if (mst.comp_detector && $("#mstCompDetector")) $("#mstCompDetector").value = mst.comp_detector;
  if (mst.sample_rate && $("#mstSampleRate")) $("#mstSampleRate").value = mst.sample_rate;

  const hq = saved.opts?.audio_hq || {};
  if ($("#hqStereoEnabled")) $("#hqStereoEnabled").checked = hq.stereo_enabled !== false;
  if (hq.stereo_preset && $("#hqStereoPreset")) $("#hqStereoPreset").value = hq.stereo_preset;
  if (hq.stereo_highcut_hz !== undefined && $("#hqStereoHighcut")) $("#hqStereoHighcut").value = hq.stereo_highcut_hz;
  if (hq.stereo_cleanup !== undefined && $("#hqStereoCleanup")) $("#hqStereoCleanup").value = hq.stereo_cleanup;
  if (hq.stereo_warmth !== undefined && $("#hqStereoWarmth")) $("#hqStereoWarmth").value = hq.stereo_warmth;
  if ($("#hqRegenEnabled")) $("#hqRegenEnabled").checked = !!hq.regen_enabled;
  if (hq.regen_preset && $("#hqRegenPreset")) $("#hqRegenPreset").value = hq.regen_preset;
  if (hq.regen_steps !== undefined && $("#hqRegenSteps")) $("#hqRegenSteps").value = hq.regen_steps;
  if (hq.regen_seed !== undefined && $("#hqRegenSeed")) $("#hqRegenSeed").value = hq.regen_seed;
  if (hq.regen_from_hz !== undefined && $("#hqRegenFromHz")) $("#hqRegenFromHz").value = hq.regen_from_hz;
  if (hq.regen_new_share !== undefined && $("#hqRegenNewShare")) $("#hqRegenNewShare").value = hq.regen_new_share;
  if (hq.regen_level_match !== undefined && $("#hqRegenLevelMatch")) $("#hqRegenLevelMatch").value = hq.regen_level_match;
  if ($("#hqDereverbEnabled")) $("#hqDereverbEnabled").checked = !!hq.dereverb_enabled;
  if (hq.dereverb_preset && $("#hqDereverbPreset")) $("#hqDereverbPreset").value = hq.dereverb_preset;
  if (hq.dereverb_amount !== undefined && $("#hqDereverbAmount")) $("#hqDereverbAmount").value = hq.dereverb_amount;
  if (hq.dereverb_phase_lock !== undefined && $("#hqDereverbPhaseLock")) $("#hqDereverbPhaseLock").value = hq.dereverb_phase_lock;

  const ref = saved.opts?.refine_cfg || {};
  if ($("#refEnabled")) $("#refEnabled").checked = !!saved.opts?.refine;
  if (ref.engine && $("#refEngine")) $("#refEngine").value = ref.engine;
  if (ref.model && $("#refModel")) {
    if (![...$("#refModel").options].some((o) => o.value === ref.model)) {
      const opt = document.createElement("option");
      opt.value = opt.textContent = ref.model;
      $("#refModel").appendChild(opt);
    }
    $("#refModel").value = ref.model;
  }
  if (ref.preset && $("#refPreset")) $("#refPreset").value = ref.preset;
  if (ref.sr_gain !== undefined && $("#refGain")) $("#refGain").value = ref.sr_gain;
  if (ref.crossover_hz !== undefined && $("#refCrossover")) $("#refCrossover").value = ref.crossover_hz;
  if (ref.pre_hz !== undefined && $("#refPreHz")) $("#refPreHz").value = ref.pre_hz;
  if (ref.post_hz !== undefined && $("#refPostHz")) $("#refPostHz").value = ref.post_hz;
  if (ref.seed !== undefined && $("#refSeed")) $("#refSeed").value = ref.seed;

  updateMasteringUI();
  refreshDocBadges();
  setMode(saved.mode || "review");
  updateLyricCount();
}

function setMode(mode) {
  S.mode = mode;
  document.querySelectorAll("#modeSeg button").forEach((b) => b.classList.toggle("active", b.dataset.mode === mode));
  const auto = mode === "auto";
  $("#autoBox").hidden = !auto;
  $("#btnDraft").hidden = auto; $("#btnRender").hidden = auto; $("#btnAuto").hidden = !auto;
  $("#modeHint").textContent = auto ? t("hintAuto") : t("hintReview");
  persist();
}

function updateLyricCount() {
  const txt = $("#shLyrics").value;
  const lines = txt.split("\n").filter((l) => l.trim() && !/^\[.*\]$/.test(l.trim())).length;
  const sections = (txt.match(/^\[.*\]$/gm) || []).length;
  $("#lyricCount").textContent = txt.trim() ? t("linesSections", { l: lines, s: sections }) : "";
  // A manual required field must have text; an auto field can either have a draft or be generated during render.
  const missingManual = ["title", "style", "lyrics"].some((k) => S.sheetState[k] === "manual" && !$("#" + DOC_INPUTS[k]).value.trim());
  $("#btnRender").disabled = missingManual;
}

function setLanguage(lang) {
  if (!I18N[lang]) return;
  LANG = lang;
  applyI18n();
  updateVoiceSwapUI();
  buildForm();
  refreshDocBadges();
  setMode(S.mode);
  updateLyricCount();
  loadHistory();
  refreshStatus();
  persist();
}

// ---------------------------------------------------------------- jobs
function busy(on) {
  ["btnDraft", "btnRender", "btnAuto"].forEach((id) => ($("#" + id).disabled = on || (id === "btnRender" && $("#btnRender").disabled)));
  if (!on) updateLyricCount();
}

async function startJob(path, body) {
  if (path !== "/api/voice_swap" && !S.status?.comfy) return toast(t("comfyDown"), true);
  persist();
  try {
    const job = await api(path, body);
    S.job = job; busy(true);
    $("#progress").hidden = false; $("#pBar").style.width = "0%";
    clearInterval(S.timer); S.timer = setInterval(pollJob, 800); pollJob();
  } catch (e) { toast(e.message, true); }
}

async function pollJob() {
  if (!S.job) return;
  let job;
  try { job = await api("/api/job/" + S.job.id); } catch (e) { return; }
  const ph = t(job.phase);
  $("#pPhase").textContent = job.runs > 1 ? `${ph} (Song ${job.run}/${job.runs})` : ph;
  $("#pDetail").textContent = job.detail || "";
  $("#pBar").style.width = Math.round(job.progress * 100) + "%";
  $("#pTime").textContent = fmtTime(Date.now() / 1000 - job.started);
  if (["done", "error", "cancelled"].includes(job.status)) {
    clearInterval(S.timer); S.job = null; busy(false);
    $("#progress").hidden = true;
    finishJob(job);
  }
}
const fmtTime = (s) => `${Math.floor(s / 60)}:${String(Math.floor(s % 60)).padStart(2, "0")}`;

function finishJob(job) {
  if (job.status !== "done") {
    if (job.kind === "render") { showTab("result"); $("#resultBox").innerHTML = ""; $("#resultBox").append(el("div", "err", job.error || t("cancelled"))); }
    toast(job.status === "cancelled" ? t("cancelled") : job.error, job.status === "error");
    return;
  }
  if (job.kind === "draft") {
    const d = job.draft;
    S.lastDraft = { ...d };
    for (const k of DOC_KEYS) {
      if (S.sheetState[k] !== "manual") {
        $("#" + DOC_INPUTS[k]).value = d[k] || "";
      }
    }
    refreshDocBadges(); updateLyricCount(); persist();
    toast(t("draftReady"));
  } else if (job.kind === "voice_swap") {
    renderResults(job); loadHistory(); showTab("result");
    toast(t("voiceSwapReady"));
  } else {
    renderResults(job); loadHistory(); showTab("result");
  }
}

function el(tag, cls, text) { const e = document.createElement(tag); if (cls) e.className = cls; if (text != null) e.textContent = text; return e; }

function renderResults(job) {
  const box = $("#resultBox"); box.innerHTML = ""; const wrap = el("div", "result");
  job.results.forEach((res) => {
    const item = el("div", "item");
    const songTitle = job.runs > 1 ? `Song ${res.run}` : $("#shTitle").value || t("result");
    item.append(el("h3", "", songTitle));
    mediaInto(item, res.media, { title: songTitle, lyrics: $("#shLyrics").value || "" });
    if (res.texts.length) item.append(el("div", "texts", res.texts.map((x) => x.text).join("\n")));
    wrap.append(item);
  });
  box.append(wrap);
}

function parseSrt(text) {
  if (!text) return [];
  const items = [];
  const blocks = text.trim().replace(/\r\n/g, "\n").replace(/\r/g, "\n").split(/\n\n+/);
  for (const block of blocks) {
    const lines = block.trim().split("\n");
    if (!lines.length) continue;
    let timeLineIdx = 0;
    if (/^\d+$/.test(lines[0].trim())) timeLineIdx = 1;
    const timeLine = lines[timeLineIdx] || "";
    const match = timeLine.match(/(\d{2}):(\d{2}):(\d{2})[,.](\d{3})\s*-->\s*(\d{2}):(\d{2}):(\d{2})[,.](\d{3})/);
    if (match) {
      const start = parseInt(match[1], 10) * 3600 + parseInt(match[2], 10) * 60 + parseInt(match[3], 10) + parseInt(match[4], 10) / 1000;
      const end = parseInt(match[5], 10) * 3600 + parseInt(match[6], 10) * 60 + parseInt(match[7], 10) + parseInt(match[8], 10) / 1000;
      const textContent = lines.slice(timeLineIdx + 1).join(" ").trim();
      if (textContent) items.push({ start, end, text: textContent });
    }
  }
  return items;
}

function formatTime(sec) {
  if (!sec || isNaN(sec) || sec < 0) return "0:00";
  const m = Math.floor(sec / 60);
  const s = Math.floor(sec % 60);
  return `${m}:${s < 10 ? "0" : ""}${s}`;
}

let sharedAudioCtx = null;
const mediaSourceMap = new WeakMap();

function getAudioAnalyser(audioEl) {
  try {
    const AC = window.AudioContext || window.webkitAudioContext;
    if (!AC) return null;
    if (!sharedAudioCtx) sharedAudioCtx = new AC();
    if (sharedAudioCtx.state === "suspended") {
      sharedAudioCtx.resume().catch(() => {});
    }
    let entry = mediaSourceMap.get(audioEl);
    if (!entry) {
      const src = sharedAudioCtx.createMediaElementSource(audioEl);
      const analyser = sharedAudioCtx.createAnalyser();
      analyser.fftSize = 128;
      analyser.smoothingTimeConstant = 0.75;
      src.connect(analyser);
      analyser.connect(sharedAudioCtx.destination);
      entry = { src, analyser };
      mediaSourceMap.set(audioEl, entry);
    }
    return entry.analyser;
  } catch (e) {
    return null;
  }
}

function renderSubtitleLinks(box, subs) {
  box.innerHTML = "";
  subs.forEach((s) => {
    const link = document.createElement("a");
    link.className = "mini srt-link";
    link.href = s.url ? (s.url.includes("?") ? `${s.url}&download=1` : `${s.url}?download=1`) : "#";
    link.download = s.name;
    link.textContent = `⬇ ${s.label || s.name}`;
    link.style.textDecoration = "none";
    link.style.display = "inline-block";
    link.style.marginRight = "6px";
    link.style.marginTop = "6px";
    box.append(link);
  });
}

function createVisualState() {
  const count = 300;
  const starX = new Float32Array(count);
  const starY = new Float32Array(count);
  const starZ = new Float32Array(count);
  for (let i = 0; i < count; i++) {
    starX[i] = Math.random() * 2 - 1;
    starY[i] = Math.random() * 2 - 1;
    starZ[i] = Math.random();
  }
  return {
    caps: new Float32Array(48),
    retroOffset: 0,
    turn: 0,
    stars: { count, x: starX, y: starY, z: starZ },
  };
}

function drawSceneFrame(ctx, style, state, freq, wave, w, h, dt, coverBitmap) {
  let bass = 0, mid = 0, treble = 0;
  if (freq && freq.length) {
    bass = ((freq[1] || 0) + (freq[2] || 0) + (freq[3] || 0) + (freq[4] || 0)) / (4 * 255);
    mid = ((freq[8] || 0) + (freq[12] || 0) + (freq[16] || 0) + (freq[20] || 0)) / (4 * 255);
    treble = ((freq[30] || 0) + (freq[40] || 0) + (freq[50] || 0)) / (3 * 255);
  }

  if (style === "retro") {
    // 1. Retro Synthwave (Sun & Perspective Grid)
    const horizon = h * 0.54;
    const sky = ctx.createLinearGradient(0, 0, 0, horizon);
    sky.addColorStop(0, "#070214");
    sky.addColorStop(1, "#3b1154");
    ctx.fillStyle = sky;
    ctx.fillRect(0, 0, w, horizon);

    const r = Math.min(w, h) * (0.24 + bass * 0.05);
    const sunGrad = ctx.createLinearGradient(0, horizon - r * 1.6, 0, horizon);
    sunGrad.addColorStop(0, "#ffe600");
    sunGrad.addColorStop(1, "#ff007f");
    ctx.save();
    ctx.beginPath();
    ctx.arc(w / 2, horizon - r * 0.35, r, 0, Math.PI * 2);
    ctx.clip();
    ctx.fillStyle = sunGrad;
    ctx.fillRect(w / 2 - r, horizon - r * 1.6, r * 2, r * 2);
    ctx.fillStyle = "#070214";
    for (let k = 0; k < 6; k++) {
      const sy = horizon - r * 0.3 + k * r * 0.14;
      ctx.fillRect(w / 2 - r, sy, r * 2, 2 + k * 1.8);
    }
    ctx.restore();

    if (freq && freq.length) {
      ctx.beginPath();
      ctx.moveTo(0, horizon);
      const points = 48;
      for (let i = 0; i <= points; i++) {
        const k = i <= points / 2 ? (points / 2 - i) : (i - points / 2);
        const idx = Math.min(freq.length - 1, Math.floor(k * 2));
        const val = freq[idx] / 255;
        const hy = horizon - Math.pow(val, 1.4) * h * 0.22;
        ctx.lineTo((i / points) * w, hy);
      }
      ctx.lineTo(w, horizon);
      ctx.fillStyle = "#0c0422";
      ctx.fill();
      ctx.strokeStyle = "#33d6a6";
      ctx.lineWidth = 2;
      ctx.stroke();
    }

    ctx.fillStyle = "#05010f";
    ctx.fillRect(0, horizon, w, h - horizon);
    state.retroOffset = ((state.retroOffset || 0) + dt * (0.4 + bass * 2.0)) % 1;
    ctx.strokeStyle = "rgba(124, 92, 255, 0.85)";
    ctx.lineWidth = 1.5;
    for (let k = 0; k < 12; k++) {
      const z = (k + state.retroOffset) / 12;
      const gy = horizon + Math.pow(z, 2.2) * (h - horizon);
      ctx.globalAlpha = z;
      ctx.beginPath();
      ctx.moveTo(0, gy);
      ctx.lineTo(w, gy);
      ctx.stroke();
    }
    ctx.globalAlpha = 1;
    for (let k = -8; k <= 8; k++) {
      ctx.beginPath();
      ctx.moveTo(w / 2 + k * w * 0.015, horizon);
      ctx.lineTo(w / 2 + k * w * 0.14, h);
      ctx.stroke();
    }
  } else if (style === "stars") {
    // 2. 3D Hyperspace Starfield
    ctx.fillStyle = "rgba(7, 9, 15, 0.35)";
    ctx.fillRect(0, 0, w, h);
    const cx = w / 2, cy = h / 2;
    const speed = (0.15 + bass * 1.5) * dt;
    const s = state.stars;
    ctx.lineCap = "round";
    for (let i = 0; i < s.count; i++) {
      const pz = s.z[i];
      s.z[i] -= speed;
      if (s.z[i] <= 0.02) {
        s.x[i] = Math.random() * 2 - 1;
        s.y[i] = Math.random() * 2 - 1;
        s.z[i] = 1;
        continue;
      }
      const sx = cx + (s.x[i] / s.z[i]) * cx;
      const sy = cy + (s.y[i] / s.z[i]) * cy;
      const px = cx + (s.x[i] / pz) * cx;
      const py = cy + (s.y[i] / pz) * cy;
      const light = 1 - s.z[i];
      ctx.strokeStyle = light > 0.7 ? "#ffffff" : `rgba(51, 214, 166, ${light})`;
      ctx.lineWidth = Math.max(1, light * 3.5);
      ctx.beginPath();
      ctx.moveTo(px, py);
      ctx.lineTo(sx, sy);
      ctx.stroke();
    }
  } else if (style === "radial") {
    // 3. Radial Pulse / Sunburst
    ctx.fillStyle = "rgba(10, 12, 18, 0.4)";
    ctx.fillRect(0, 0, w, h);
    const cx = w / 2, cy = h / 2;
    const size = Math.min(w, h);
    const core = size * (0.18 + bass * 0.08);
    state.turn = (state.turn || 0) + dt * (0.2 + mid * 0.6);
    const n = 64;
    ctx.lineCap = "round";
    for (let i = 0; i < n; i++) {
      const k = i < n / 2 ? i : n - 1 - i;
      const idx = Math.min((freq ? freq.length : 1) - 1, Math.floor(k * 1.5));
      const val = (freq && freq.length) ? (freq[idx] / 255) : 0.2;
      const len = Math.pow(val, 1.3) * size * 0.35;
      const angle = state.turn + (i / n) * Math.PI * 2;
      ctx.strokeStyle = val > 0.6 ? "#33d6a6" : "#7c5cff";
      ctx.lineWidth = Math.max(2, (size / n) * 1.1);
      ctx.beginPath();
      ctx.moveTo(cx + Math.cos(angle) * core, cy + Math.sin(angle) * core);
      ctx.lineTo(cx + Math.cos(angle) * (core + len), cy + Math.sin(angle) * (core + len));
      ctx.stroke();
    }
    const glow = ctx.createRadialGradient(cx, cy, 0, cx, cy, core);
    glow.addColorStop(0, "rgba(51, 214, 166, 0.85)");
    glow.addColorStop(0.6, "rgba(124, 92, 255, 0.5)");
    glow.addColorStop(1, "rgba(124, 92, 255, 0)");
    ctx.fillStyle = glow;
    ctx.beginPath();
    ctx.arc(cx, cy, core, 0, Math.PI * 2);
    ctx.fill();
  } else if (style === "scope") {
    // 4. Oscilloscope (Glowing Wave)
    ctx.fillStyle = "rgba(8, 10, 16, 0.3)";
    ctx.fillRect(0, 0, w, h);
    const midY = h / 2;
    const amp = h * 0.4 * (0.8 + bass * 0.7);
    if (wave && wave.length) {
      ctx.lineJoin = "round";
      for (const [width, color] of [[8, "rgba(124, 92, 255, 0.25)"], [2.5, "#33d6a6"]]) {
        ctx.beginPath();
        const step = Math.max(1, Math.floor(wave.length / w));
        for (let x = 0, i = 0; i < wave.length; i += step, x += w / (wave.length / step)) {
          const y = midY + ((wave[i] - 128) / 128) * amp;
          if (i === 0) ctx.moveTo(x, y);
          else ctx.lineTo(x, y);
        }
        ctx.strokeStyle = color;
        ctx.lineWidth = width;
        ctx.stroke();
      }
    } else {
      ctx.strokeStyle = "rgba(51, 214, 166, 0.4)";
      ctx.lineWidth = 2;
      ctx.beginPath();
      ctx.moveTo(0, midY); ctx.lineTo(w, midY); ctx.stroke();
    }
  } else if (style === "blur") {
    // 5. Cover Atmosphere
    ctx.fillStyle = "#0f1117";
    ctx.fillRect(0, 0, w, h);
    if (coverBitmap) {
      ctx.save();
      ctx.filter = `blur(${Math.max(12, 24 - bass * 12)}px) brightness(${0.5 + bass * 0.4})`;
      ctx.drawImage(coverBitmap, 0, 0, w, h);
      ctx.restore();
    }
    if (wave && wave.length) {
      ctx.beginPath();
      const step = Math.max(1, Math.floor(wave.length / w));
      for (let x = 0, i = 0; i < wave.length; i += step, x += w / (wave.length / step)) {
        const y = (h - 30) + ((wave[i] - 128) / 128) * (25 + bass * 35);
        if (i === 0) ctx.moveTo(x, y);
        else ctx.lineTo(x, y);
      }
      ctx.strokeStyle = "rgba(51, 214, 166, 0.85)";
      ctx.lineWidth = 3;
      ctx.stroke();
    }
  } else if (style === "custom") {
    // 7. Custom User Video Background
    const bgVideo = state.customVideo || window._tamusicmaker_custom_video;
    if (bgVideo && bgVideo.readyState >= 2) {
      const vw = bgVideo.videoWidth || 1920;
      const vh = bgVideo.videoHeight || 1080;
      const scale = Math.max(w / vw, h / vh);
      const dw = vw * scale;
      const dh = vh * scale;
      const dx = (w - dw) / 2;
      const dy = (h - dh) / 2;
      ctx.drawImage(bgVideo, dx, dy, dw, dh);
    } else {
      ctx.fillStyle = "#0a0c13";
      ctx.fillRect(0, 0, w, h);
      ctx.fillStyle = "rgba(255, 255, 255, 0.6)";
      ctx.font = "14px sans-serif";
      ctx.textAlign = "center";
      ctx.fillText(t("customVideoSelectPrompt"), w / 2, h / 2);
    }
  } else if (style === "custom_image") {
    // 8. Custom Static Image Background
    const bgImg = state.customImage || window._tamusicmaker_custom_image;
    if (bgImg && (bgImg.complete || bgImg.width)) {
      const iw = bgImg.naturalWidth || bgImg.width || 1920;
      const ih = bgImg.naturalHeight || bgImg.height || 1080;
      const scale = Math.max(w / iw, h / ih);
      const dw = iw * scale;
      const dh = ih * scale;
      const dx = (w - dw) / 2;
      const dy = (h - dh) / 2;
      ctx.drawImage(bgImg, dx, dy, dw, dh);
    } else {
      ctx.fillStyle = "#0a0c13";
      ctx.fillRect(0, 0, w, h);
      ctx.fillStyle = "rgba(255, 255, 255, 0.6)";
      ctx.font = "14px sans-serif";
      ctx.textAlign = "center";
      ctx.fillText(t("customImageSelectPrompt"), w / 2, h / 2);
    }
  } else {
    // 6. Classic Bars (Winamp Style with falling peak caps & floor reflection)
    ctx.fillStyle = "#0c0e14";
    ctx.fillRect(0, 0, w, h);
    const n = 36;
    const barW = Math.max(3, w / n - 3);
    const floor = h * 0.82;
    state.caps = state.caps || new Float32Array(n);
    const flen = freq ? freq.length : 0;

    for (let i = 0; i < n; i++) {
      let val = 0.08;
      if (flen > 0) {
        const idx = Math.min(flen - 1, Math.floor((i / n) * (flen * 0.88)));
        val = (freq[idx] || 0) / 255;
      }
      const barH = Math.max(3, Math.pow(val, 1.3) * (floor * 0.9));
      state.caps[i] = Math.max((state.caps[i] || 0) - dt * floor * 0.5, barH);
      const x = i * (barW + 3) + 2;

      const grad = ctx.createLinearGradient(0, floor, 0, floor - barH);
      grad.addColorStop(0, "rgba(124, 92, 255, 0.85)");
      grad.addColorStop(0.7, "rgba(51, 214, 166, 0.95)");
      grad.addColorStop(1, "#ffffff");
      ctx.fillStyle = grad;
      ctx.fillRect(x, floor - barH, barW, barH);

      ctx.fillStyle = "#ffffff";
      ctx.fillRect(x, floor - state.caps[i] - 3, barW, 2);

      ctx.globalAlpha = 0.2;
      ctx.fillStyle = "rgba(124, 92, 255, 0.5)";
      ctx.fillRect(x, floor + 2, barW, barH * 0.25);
      ctx.globalAlpha = 1;
    }
  }
}

function mediaInto(parent, media, extra = {}) {
  let audio = media.filter((m) => m.kind === "audio");
  if (audio.some((m) => !m.temp)) audio = audio.filter((m) => !m.temp);
  let subs = media.filter((m) => m.kind === "subtitle");
  const images = media.filter((m) => m.kind === "image");
  const coverImg = images.length ? images[0] : null;

  if (!audio.length) {
    if (subs.length) {
      const subBox = el("div", "srt-box");
      renderSubtitleLinks(subBox, subs);
      parent.append(subBox);
    }
    if (coverImg) {
      const img = document.createElement("img");
      img.className = "cover";
      img.src = coverImg.url;
      parent.append(img);
    }
    return;
  }

  // Plenio Native Player container
  const player = el("div", "ta-player");
  let activeTrack = audio[0];
  let activeSub = subs.length ? subs[0] : null;
  let parsedCues = [];
  let showVisualizer = true;
  let showLyrics = true;
  let speedIdx = 0;
  const speeds = [1.0, 1.25, 1.5, 2.0, 0.75];

  const audioEl = document.createElement("audio");
  audioEl.preload = "metadata";
  audioEl.src = activeTrack.url;

  // Header: Cover + Meta + Version Selector
  const header = el("div", "player-header");
  if (coverImg) {
    const thumb = document.createElement("img");
    thumb.className = "player-thumb";
    thumb.src = coverImg.url;
    thumb.title = t("optCover");
    thumb.onclick = () => window.open(coverImg.url, "_blank");
    header.append(thumb);
  } else {
    header.append(el("div", "player-thumb-placeholder", "♪"));
  }

  const meta = el("div", "player-meta");
  const songTitle = extra.title || activeTrack.name;
  meta.append(el("div", "player-title", songTitle));
  const subTitle = el("div", "player-subtitle", activeTrack.name);
  meta.append(subTitle);

  const verRow = el("div", "player-versions");
  const verBtns = [];
  if (audio.length > 1) {
    audio.forEach((track, idx) => {
      let label = track.name;
      if (track.name.includes("voice_swap") || track.name.startsWith("[")) {
        label = `🎙️ ${t("trackVoiceSwap")}`;
      } else if (track.name.includes("sr") || track.name.includes("refine") || track.name.includes("48k")) {
        label = `✨ ${t("trackRefined")}`;
      } else if (idx === 0) {
        label = `🎵 ${t("trackOriginal")}`;
      }
      const b = el("button", "ver-btn" + (idx === 0 ? " active" : ""), label);
      b.onclick = () => {
        verBtns.forEach((btn) => btn.classList.remove("active"));
        b.classList.add("active");
        const seek = audioEl.currentTime || 0;
        const wasPlaying = !audioEl.paused;
        activeTrack = track;
        subTitle.textContent = track.name;
        audioEl.src = track.url;
        audioEl.currentTime = seek;
        if (wasPlaying) audioEl.play().catch(() => {});
        updateDownloadLinks();
      };
      verBtns.push(b);
      verRow.append(b);
    });
    meta.append(verRow);
  }
  header.append(meta);
  player.append(header);

  // Visualizer Canvas
  let visState = createVisualState();
  let currentVisStyle = S.visStyle || (localStorage.getItem("tamusicmaker.vis_style") || "bars");
  let lastVisTime = performance.now();
  let coverBitmap = null;
  if (coverImg && coverImg.url) {
    const img = new Image();
    img.crossOrigin = "anonymous";
    img.src = coverImg.url;
    img.onload = () => { coverBitmap = img; if (showVisualizer) drawVisualizer(); };
  }

  const visWrap = el("div", "player-visualizer-container");
  const canvas = document.createElement("canvas");
  canvas.className = "player-canvas";
  visWrap.append(canvas);
  player.append(visWrap);

  function drawVisualizer() {
    if (!canvas || !canvas.parentElement || !showVisualizer) return;
    const ctx = canvas.getContext("2d");
    if (!ctx) return;
    const w = (canvas.width = canvas.parentElement.clientWidth || 400);
    const h = (canvas.height = canvas.parentElement.clientHeight || 90);

    const now = performance.now();
    const dt = Math.min(0.1, (now - lastVisTime) / 1000) || 0.016;
    lastVisTime = now;

    const analyser = getAudioAnalyser(audioEl);
    let freqData = null;
    let waveData = null;
    if (analyser && !audioEl.paused) {
      freqData = new Uint8Array(analyser.frequencyBinCount);
      waveData = new Uint8Array(analyser.frequencyBinCount);
      analyser.getByteFrequencyData(freqData);
      analyser.getByteTimeDomainData(waveData);
    }

    try {
      drawSceneFrame(ctx, currentVisStyle, visState, freqData, waveData, w, h, dt, coverBitmap);
    } catch (e) {
      console.warn("Visualizer render error:", e);
    }

    if (!audioEl.paused && showVisualizer) {
      requestAnimationFrame(drawVisualizer);
    }
  }

  // Scrubber Bar
  const scrubber = el("div", "player-scrubber");
  const trackWrap = el("div", "scrubber-track-wrap");
  const trackBar = el("div", "scrubber-track");
  const bufBar = el("div", "scrubber-buffer");
  const fillBar = el("div", "scrubber-fill");
  const handle = el("div", "scrubber-handle");
  const tooltip = el("div", "scrubber-tooltip");
  trackBar.append(bufBar, fillBar, handle);
  trackWrap.append(trackBar, tooltip);

  const timesRow = el("div", "player-times");
  const tElapsed = el("span", "", "0:00");
  const tTotal = el("span", "", "0:00");
  timesRow.append(tElapsed, tTotal);
  scrubber.append(trackWrap, timesRow);
  player.append(scrubber);

  function updateScrubber() {
    const cur = audioEl.currentTime || 0;
    const dur = audioEl.duration || 0;
    tElapsed.textContent = formatTime(cur);
    tTotal.textContent = formatTime(dur);
    const pct = dur > 0 ? (cur / dur) * 100 : 0;
    fillBar.style.width = pct + "%";
    handle.style.left = pct + "%";
    if (audioEl.buffered && audioEl.buffered.length) {
      try {
        const bEnd = audioEl.buffered.end(audioEl.buffered.length - 1);
        bufBar.style.width = dur > 0 ? (bEnd / dur) * 100 + "%" : "0%";
      } catch {}
    }
  }

  trackWrap.onmousemove = (e) => {
    const rect = trackWrap.getBoundingClientRect();
    const pos = Math.max(0, Math.min(1, (e.clientX - rect.left) / rect.width));
    const targetSec = pos * (audioEl.duration || 0);
    tooltip.textContent = formatTime(targetSec);
    tooltip.style.left = pos * 100 + "%";
    tooltip.style.display = "block";
  };
  trackWrap.onmouseleave = () => {
    tooltip.style.display = "none";
  };
  trackWrap.onclick = (e) => {
    const rect = trackWrap.getBoundingClientRect();
    const pos = Math.max(0, Math.min(1, (e.clientX - rect.left) / rect.width));
    audioEl.currentTime = pos * (audioEl.duration || 0);
    updateScrubber();
    updateActiveLyricHighlight(audioEl.currentTime);
  };

  // Controls
  const ctrlRow = el("div", "player-controls");
  const btnBack = el("button", "ctrl-btn", "⏪ 5s");
  btnBack.title = t("playerSeekBack");
  btnBack.onclick = () => {
    audioEl.currentTime = Math.max(0, audioEl.currentTime - 5);
    updateActiveLyricHighlight(audioEl.currentTime);
  };

  const btnPlay = el("button", "play-btn", "▶");
  btnPlay.title = t("playerPlay");
  btnPlay.onclick = () => {
    if (audioEl.paused) {
      document.querySelectorAll("audio").forEach((a) => {
        if (a !== audioEl) a.pause();
      });
      if (sharedAudioCtx && sharedAudioCtx.state === "suspended") {
        sharedAudioCtx.resume().catch(() => {});
      }
      audioEl.play().catch(() => {});
    } else {
      audioEl.pause();
    }
  };

  const btnFwd = el("button", "ctrl-btn", "5s ⏩");
  btnFwd.title = t("playerSeekFwd");
  btnFwd.onclick = () => {
    audioEl.currentTime = Math.min(audioEl.duration || 9999, audioEl.currentTime + 5);
    updateActiveLyricHighlight(audioEl.currentTime);
  };

  const btnLoop = el("button", "ctrl-btn", "🔁");
  btnLoop.title = t("playerLoop");
  btnLoop.onclick = () => {
    audioEl.loop = !audioEl.loop;
    btnLoop.classList.toggle("active", audioEl.loop);
  };

  const btnSpeed = el("button", "ctrl-btn", "1.0x");
  btnSpeed.title = t("playerSpeed");
  btnSpeed.onclick = () => {
    speedIdx = (speedIdx + 1) % speeds.length;
    const spd = speeds[speedIdx];
    audioEl.playbackRate = spd;
    btnSpeed.textContent = spd.toFixed(spd % 1 === 0 ? 1 : 2) + "x";
  };

  const volBox = el("div", "volume-box");
  const btnMute = el("button", "ctrl-btn", "🔊");
  btnMute.style.padding = "5px 8px";
  btnMute.title = t("playerMute");
  const volSlider = document.createElement("input");
  volSlider.type = "range";
  volSlider.className = "volume-slider";
  volSlider.min = "0";
  volSlider.max = "1";
  volSlider.step = "0.05";
  volSlider.value = "1";
  btnMute.onclick = () => {
    audioEl.muted = !audioEl.muted;
    btnMute.textContent = audioEl.muted ? "🔇" : "🔊";
  };
  volSlider.oninput = () => {
    audioEl.volume = parseFloat(volSlider.value);
    audioEl.muted = false;
    btnMute.textContent = audioEl.volume === 0 ? "🔇" : "🔊";
  };
  volBox.append(btnMute, volSlider);

  const btnLyricsToggle = el("button", "ctrl-btn active", "🎤 " + t("playerLyrics"));
  const btnVisToggle = el("button", "ctrl-btn active", "📊 " + t("playerVisualizer"));

  btnLyricsToggle.onclick = () => {
    showLyrics = !showLyrics;
    lyricsPane.hidden = !showLyrics;
    btnLyricsToggle.classList.toggle("active", showLyrics);
    if (showLyrics) {
      updateActiveLyricHighlight(audioEl.currentTime);
    }
  };
  btnVisToggle.onclick = () => {
    showVisualizer = !showVisualizer;
    visWrap.hidden = !showVisualizer;
    btnVisToggle.classList.toggle("active", showVisualizer);
    if (showVisualizer) drawVisualizer();
  };

  const inputPlayerCustomVideo = document.createElement("input");
  inputPlayerCustomVideo.type = "file";
  inputPlayerCustomVideo.accept = "video/mp4,video/webm,video/quicktime,video/x-matroska";
  inputPlayerCustomVideo.style.display = "none";
  inputPlayerCustomVideo.onchange = () => {
    const file = inputPlayerCustomVideo.files && inputPlayerCustomVideo.files[0];
    if (file) {
      window._tamusicmaker_custom_file = file;
      const v = document.createElement("video");
      v.src = URL.createObjectURL(file);
      v.loop = true;
      v.muted = true;
      v.playsInline = true;
      v.onloadeddata = () => {
        window._tamusicmaker_custom_video = v;
        visState.customVideo = v;
        if (!audioEl.paused) v.play().catch(() => {});
        drawVisualizer();
      };
      v.load();
    }
  };
  player.append(inputPlayerCustomVideo);

  const inputPlayerCustomImage = document.createElement("input");
  inputPlayerCustomImage.type = "file";
  inputPlayerCustomImage.accept = "image/png,image/jpeg,image/webp,image/jpg";
  inputPlayerCustomImage.style.display = "none";
  inputPlayerCustomImage.onchange = () => {
    const file = inputPlayerCustomImage.files && inputPlayerCustomImage.files[0];
    if (file) {
      window._tamusicmaker_custom_image_file = file;
      const img = new Image();
      img.src = URL.createObjectURL(file);
      img.onload = () => {
        window._tamusicmaker_custom_image = img;
        visState.customImage = img;
        drawVisualizer();
      };
    }
  };
  player.append(inputPlayerCustomImage);

  const selVisStyle = document.createElement("select");
  selVisStyle.className = "vis-style-select";
  selVisStyle.title = t("visStyle");
  [
    { id: "bars", name: t("visStyleBars") },
    { id: "retro", name: t("visStyleRetro") },
    { id: "stars", name: t("visStyleStars") },
    { id: "radial", name: t("visStyleRadial") },
    { id: "scope", name: t("visStyleScope") },
    { id: "blur", name: t("visStyleBlur") },
    { id: "custom", name: t("visStyleCustom") },
    { id: "custom_image", name: t("visStyleCustomImage") },
  ].forEach((p) => {
    const opt = document.createElement("option");
    opt.value = p.id;
    opt.textContent = p.name;
    selVisStyle.append(opt);
  });
  selVisStyle.value = currentVisStyle;
  selVisStyle.onchange = () => {
    currentVisStyle = selVisStyle.value;
    S.visStyle = currentVisStyle;
    try { localStorage.setItem("tamusicmaker.vis_style", currentVisStyle); } catch {}
    visState = createVisualState();
    if (currentVisStyle === "custom") {
      if (!window._tamusicmaker_custom_video) {
        inputPlayerCustomVideo.click();
      } else {
        visState.customVideo = window._tamusicmaker_custom_video;
        if (!audioEl.paused) window._tamusicmaker_custom_video.play().catch(() => {});
      }
    } else if (currentVisStyle === "custom_image") {
      if (!window._tamusicmaker_custom_image) {
        inputPlayerCustomImage.click();
      } else {
        visState.customImage = window._tamusicmaker_custom_image;
      }
    }
    drawVisualizer();
  };

  ctrlRow.append(btnBack, btnPlay, btnFwd, btnLoop, btnSpeed, volBox, el("span", "spacer"), btnLyricsToggle, selVisStyle, btnVisToggle);
  player.append(ctrlRow);

  // Synced Lyrics Pane
  const lyricsPane = el("div", "lyrics-pane");
  const langBar = el("div", "lyrics-lang-bar");
  const cueBox = el("div", "lyrics-cues");
  lyricsPane.append(langBar, cueBox);
  player.append(lyricsPane);

  function updateActiveLyricHighlight(time) {
    if (!parsedCues || !parsedCues.length || !showLyrics) return;
    const t = Number(time) || 0;
    let activeIdx = -1;

    // Only activate if we reached the start of the first cue (minus lead-in tolerance)
    if (t >= parsedCues[0].start - 0.2) {
      for (let i = 0; i < parsedCues.length; i++) {
        const c = parsedCues[i];
        const nextStart = (i + 1 < parsedCues.length) ? parsedCues[i + 1].start : (audioEl.duration || c.end + 8.0);
        if (t >= c.start - 0.2 && t < nextStart) {
          activeIdx = i;
          break;
        }
      }
      // If we are past the last cue end by more than 6s, clear highlight
      if (activeIdx === parsedCues.length - 1 && t > parsedCues[activeIdx].end + 6.0) {
        activeIdx = -1;
      }
    }

    const cueEls = cueBox.querySelectorAll(".lyric-cue");
    cueEls.forEach((el) => {
      const isCur = (activeIdx >= 0 && Number(el.dataset.idx) === activeIdx);
      if (el.classList.contains("active") !== isCur) {
        el.classList.toggle("active", isCur);
        if (isCur) {
          el.scrollIntoView({ behavior: "smooth", block: "center" });
        }
      }
    });
  }

  async function loadActiveSubtitle() {
    cueBox.innerHTML = "";
    langBar.innerHTML = "";
    if (subs.length > 1) {
      subs.forEach((s) => {
        const btn = el("button", "lyrics-lang-btn" + (s === activeSub ? " active" : ""), s.label || s.name);
        btn.onclick = () => {
          activeSub = s;
          loadActiveSubtitle();
        };
        langBar.append(btn);
      });
      langBar.hidden = false;
    } else {
      langBar.hidden = true;
    }

    if (activeSub) {
      try {
        const resp = await fetch(activeSub.url);
        const txt = await resp.text();
        parsedCues = parseSrt(txt);
      } catch (err) {
        console.warn("Failed to load SRT:", err);
        parsedCues = [];
      }
    } else {
      parsedCues = [];
    }

    if (parsedCues.length) {
      parsedCues.forEach((c, idx) => {
        const cueEl = el("div", "lyric-cue");
        cueEl.dataset.idx = String(idx);
        cueEl.dataset.start = String(c.start);
        cueEl.dataset.end = String(c.end);
        cueEl.append(el("span", "lyric-time", formatTime(c.start)), el("span", "lyric-text", c.text));
        cueEl.onclick = () => {
          audioEl.currentTime = c.start;
          updateActiveLyricHighlight(c.start);
          if (audioEl.paused) audioEl.play().catch(() => {});
        };
        cueBox.append(cueEl);
      });
      updateActiveLyricHighlight(audioEl.currentTime);
    } else if (extra.lyrics) {
      cueBox.append(el("div", "hint", t("playerRawLyrics")));
      cueBox.append(el("div", "texts", extra.lyrics));
    } else {
      cueBox.append(el("p", "hint", t("playerNoLyrics")));
    }
  }

  loadActiveSubtitle();

  // Audio Events
  audioEl.onplay = () => {
    btnPlay.textContent = "⏸";
    btnPlay.title = t("playerPause");
    const cv = window._tamusicmaker_custom_video;
    if (cv) cv.play().catch(() => {});
    if (showVisualizer) drawVisualizer();
    updateActiveLyricHighlight(audioEl.currentTime);
  };
  audioEl.onpause = () => {
    btnPlay.textContent = "▶";
    btnPlay.title = t("playerPlay");
    const cv = window._tamusicmaker_custom_video;
    if (cv) cv.pause();
    updateActiveLyricHighlight(audioEl.currentTime);
  };
  audioEl.onended = () => {
    btnPlay.textContent = "▶";
    btnPlay.title = t("playerPlay");
    const cv = window._tamusicmaker_custom_video;
    if (cv) cv.pause();
    updateActiveLyricHighlight(audioEl.currentTime);
  };
  audioEl.onloadedmetadata = () => {
    updateScrubber();
    drawVisualizer();
    updateActiveLyricHighlight(audioEl.currentTime);
  };
  audioEl.onseeked = () => {
    updateScrubber();
    updateActiveLyricHighlight(audioEl.currentTime);
  };
  audioEl.ontimeupdate = () => {
    updateScrubber();
    const time = audioEl.currentTime;
    const cv = window._tamusicmaker_custom_video;
    if (cv && cv.duration && !cv.paused) {
      const target = time % cv.duration;
      if (Math.abs(cv.currentTime - target) > 0.4) {
        cv.currentTime = target;
      }
    }
    updateActiveLyricHighlight(time);
  };

  // Actions Row: Voice Swap, Translate SRT, Downloads, Plenio Standalone Player
  const actionsRow = el("div", "player-actions-row");

  const btnSwap = el("button", "swap-voice", t("swapVoiceBtn"));
  btnSwap.dataset.role = "voice-swap";
  btnSwap.disabled = !S.applioAvailable;
  if (!S.applioAvailable) btnSwap.title = t("applioMissing");
  btnSwap.onclick = () => openVoiceSwapDialog(activeTrack);
  actionsRow.append(btnSwap);

  const btnSrt = el("button", "swap-voice", t("translateSrtBtn"));
  btnSrt.onclick = async () => {
    btnSrt.disabled = true;
    try {
      const res = await api("/api/translate_srt", { audio_url: activeTrack.url, target_lang: "en" });
      if (res.subtitles && res.subtitles.length) {
        subs = res.subtitles;
        activeSub = subs.find((s) => s.lang === "bilingual" || s.lang === "en") || subs[0];
        loadActiveSubtitle();
        updateDownloadLinks();
      }
      toast(t("srtReady"));
    } catch (e) {
      toast(e.message, true);
    } finally {
      btnSrt.disabled = false;
    }
  };
  actionsRow.append(btnSrt);

  const dlAudio = el("a", "mini srt-link", t("downloadAudio"));
  dlAudio.style.textDecoration = "none";
  dlAudio.target = "_blank";
  actionsRow.append(dlAudio);

  let dlSub = null;
  if (subs.length) {
    dlSub = el("a", "mini srt-link", t("downloadSubs"));
    dlSub.style.textDecoration = "none";
    dlSub.target = "_blank";
    actionsRow.append(dlSub);
  }

  function updateDownloadLinks() {
    dlAudio.href = activeTrack.url ? (activeTrack.url.includes("?") ? `${activeTrack.url}&download=1` : `${activeTrack.url}?download=1`) : "#";
    dlAudio.download = activeTrack.name;
    if (dlSub && activeSub) {
      dlSub.href = activeSub.url ? (activeSub.url.includes("?") ? `${activeSub.url}&download=1` : `${activeSub.url}?download=1`) : "#";
      dlSub.download = activeSub.name;
    }
  }
  updateDownloadLinks();

  if (coverImg) {
    const dlCover = el("a", "mini srt-link", t("downloadCover"));
    dlCover.href = coverImg.url ? (coverImg.url.includes("?") ? `${coverImg.url}&download=1` : `${coverImg.url}?download=1`) : "#";
    dlCover.download = coverImg.name;
    dlCover.style.textDecoration = "none";
    dlCover.target = "_blank";
    actionsRow.append(dlCover);
  }

  const btnVideo = el("button", "btn-video-export", t("videoExportBtn"));
  btnVideo.onclick = () => openVideoExportDialog({
    audioEl,
    activeTrack,
    coverImg,
    activeSub,
    parsedCues,
    title: extra.title || activeTrack.name,
  });
  actionsRow.append(btnVideo);

  const btnEditSong = el("button", "btn-edit-song", "✏️ " + (t("loadEditor") || "In Editor laden"));
  btnEditSong.onclick = () => {
    if (extra.songData) {
      loadSongIntoEditor(extra.songData);
    } else {
      api("/api/history").then((history) => {
        const found = history.find((h) => h.title === extra.title) || history[0];
        if (found) loadSongIntoEditor(found);
      }).catch(() => {});
    }
  };
  actionsRow.append(btnEditSong);

  const btnNewTake = el("button", "btn-new-take", "🎤 " + (t("newTake") || "Neuer Take"));
  btnNewTake.onclick = async () => {
    const songObj = extra.songData;
    const sTitle = extra.title || (songObj && songObj.title) || "";
    const promptMsg = t("newTakePrompt", { title: sTitle }) || `Neuen Take für „${sTitle}“ rendern?`;
    if (!confirm(promptMsg)) return;
    try {
      busy(true);
      $("#progress").hidden = false;
      const res = await api("/api/song/new_take", { id: songObj?.id, audio_url: extra.url });
      S.job = res;
      showTab("result");
      S.timer = setInterval(pollJob, 800);
    } catch (err) {
      busy(false);
      $("#progress").hidden = true;
      toast(err.message || String(err), true);
    }
  };
  actionsRow.append(btnNewTake);

  if (S.status && S.status.plenio_player) {
    const btnPlenio = el("button", "btn-plenio-open", t("playerOpenPlenio"));
    btnPlenio.onclick = async () => {
      try {
        await api("/api/plenio_player/launch");
        toast(t("playerPlenioStarted"));
      } catch (e) {
        toast(e.message, true);
      }
    };
    actionsRow.append(btnPlenio);
  }

  player.append(actionsRow);
  parent.append(player);
}

function openVoiceSwapDialog(mediaItem) {
  if (!S.applioAvailable) return toast(t("applioMissing"), true);
  S.pendingSwap = mediaItem;
  $("#dlgVoiceSwapSongName").textContent = mediaItem.name;
  $("#dlgVoiceSwap").showModal();
}

let currentVideoExport = null;
let activeBrowserVideoAbort = null;

function stopVideoExportPlayback() {
  stopAudioRangePreview();
  const video = $("#videoPreview");
  if (video) {
    try {
      video.pause();
      video.currentTime = 0;
      video.removeAttribute("src");
      video.load();
    } catch (_) {}
  }
  if (activeBrowserVideoAbort) {
    try {
      activeBrowserVideoAbort();
    } catch (_) {}
    activeBrowserVideoAbort = null;
  }
}
const _loadedFontsSet = new Set();

async function ensureFontLoaded(fontName) {
  if (!fontName) return;
  fontName = fontName.trim();
  if (!fontName || _loadedFontsSet.has(fontName)) return;

  try {
    if (document.fonts && document.fonts.check(`16px "${fontName}"`)) {
      _loadedFontsSet.add(fontName);
      return;
    }
  } catch (_) {}

  try {
    const fontUrl = `/api/font_file?name=${encodeURIComponent(fontName)}`;
    const fontFace = new FontFace(fontName, `url(${fontUrl})`);
    const loaded = await fontFace.load();
    document.fonts.add(loaded);
    _loadedFontsSet.add(fontName);
  } catch (err) {
    console.debug(`FontFace load for "${fontName}" skipped/failed:`, err);
  }
}

async function initVideoSubtitleFonts() {
  const inpFont = $("#inpVideoSubtitleFont");
  const datalist = $("#listVideoFonts");
  const preview = $("#videoFontPreview");
  if (!inpFont || !datalist) return;

  function updateFontPreview(fontName) {
    fontName = (fontName || "").trim();
    if (!fontName) fontName = "Impact";
    if (preview) {
      preview.style.fontFamily = `"${fontName}", sans-serif`;
    }
    ensureFontLoaded(fontName);
  }

  if (!window._systemFontsList) {
    try {
      const res = await api("/api/fonts");
      if (res && res.fonts) {
        window._systemFontsList = res.fonts;
        window._defaultFont = res.default || "Impact";
      }
    } catch (e) {
      console.warn("Failed to load /api/fonts:", e);
      window._systemFontsList = ["Impact", "Arial", "Segoe UI", "Tahoma", "Verdana", "Georgia", "Comic Sans MS", "Trebuchet MS", "Times New Roman"];
      window._defaultFont = "Impact";
    }

    datalist.innerHTML = "";
    (window._systemFontsList || []).forEach((name) => {
      const opt = document.createElement("option");
      opt.value = name;
      datalist.appendChild(opt);
    });
  }

  const savedFont = localStorage.getItem("tamusicmaker_video_font") || window._defaultFont || "Impact";
  if (!inpFont.value) {
    inpFont.value = savedFont;
  }
  updateFontPreview(inpFont.value);

  inpFont.oninput = () => {
    const val = inpFont.value.trim();
    if (val) {
      localStorage.setItem("tamusicmaker_video_font", val);
      updateFontPreview(val);
    }
  };

  inpFont.onchange = () => {
    const val = inpFont.value.trim();
    if (val) {
      localStorage.setItem("tamusicmaker_video_font", val);
      updateFontPreview(val);
    }
  };

  inpFont.onfocus = () => {
    inpFont.select();
  };
}

let videoAudioRange = {
  url: null,
  start: 0.0,
  duration: 0.0,
  totalDuration: 0.0,
  peaks: null,
  activePreset: "full",
};

let previewAudioEl = null;
let previewAudioRaf = null;
const _audioPeakCache = new Map();

function formatTimeSec(sec) {
  if (isNaN(sec) || sec < 0) sec = 0;
  const m = Math.floor(sec / 60);
  const s = Math.floor(sec % 60);
  const ms = Math.floor((sec % 1) * 10);
  return `${m}:${s.toString().padStart(2, "0")}.${ms}`;
}

async function loadAudioWaveform(url) {
  if (_audioPeakCache.has(url)) {
    return _audioPeakCache.get(url);
  }
  const resp = await fetch(url);
  const ab = await resp.arrayBuffer();
  const AC = window.AudioContext || window.webkitAudioContext;
  const ctx = new AC();
  const audioBuf = await ctx.decodeAudioData(ab);
  const totalDuration = audioBuf.duration;
  const channelData = audioBuf.getChannelData(0);
  const numBars = 240;
  const blockSize = Math.max(1, Math.floor(channelData.length / numBars));
  const peaks = new Float32Array(numBars);
  let maxPeak = 0.001;
  for (let i = 0; i < numBars; i++) {
    const start = i * blockSize;
    let sum = 0;
    const step = Math.max(1, Math.floor(blockSize / 32));
    for (let j = 0; j < blockSize; j += step) {
      const v = Math.abs(channelData[start + j] || 0);
      if (v > sum) sum = v;
    }
    peaks[i] = sum;
    if (sum > maxPeak) maxPeak = sum;
  }
  for (let i = 0; i < numBars; i++) {
    peaks[i] = Math.min(1.0, peaks[i] / maxPeak);
  }
  try { ctx.close(); } catch (_) {}
  const data = { totalDuration, peaks };
  _audioPeakCache.set(url, data);
  return data;
}

function updateAudioRangeUI() {
  const { totalDuration, start, duration } = videoAudioRange;
  const badge = $("#badgeVideoAudioDuration");
  const infoLbl = $("#lblAudioRangeInfo");
  const inpStart = $("#inpAudioRangeStart");
  const inpDur = $("#inpAudioRangeDuration");

  const isFull = Math.abs(duration - totalDuration) < 0.6 && start < 0.2;
  const endSec = Math.min(totalDuration, start + duration);

  if (badge) {
    if (isFull) {
      badge.textContent = `Full (${formatTimeSec(totalDuration)})`;
      badge.style.color = "var(--accent2)";
      badge.style.background = "rgba(51,214,166,0.15)";
    } else {
      badge.textContent = `${duration.toFixed(1)}s`;
      badge.style.color = "#ff7a45";
      badge.style.background = "rgba(255,106,61,0.18)";
    }
  }

  if (infoLbl) {
    infoLbl.textContent = `${formatTimeSec(start)} - ${formatTimeSec(endSec)} (${isFull ? "Full" : duration.toFixed(1) + "s"})`;
  }

  if (inpStart && document.activeElement !== inpStart) {
    inpStart.value = start.toFixed(1);
    inpStart.max = Math.max(0, totalDuration - 0.5).toFixed(1);
  }
  if (inpDur && document.activeElement !== inpDur) {
    inpDur.value = duration.toFixed(1);
    inpDur.max = totalDuration.toFixed(1);
  }
}

function renderWaveformCanvas() {
  const canvas = $("#videoWaveformCanvas");
  if (!canvas) return;
  const wrap = canvas.parentElement;
  if (!wrap) return;
  const dpr = window.devicePixelRatio || 1;
  const rect = wrap.getBoundingClientRect();
  const w = rect.width || 480;
  const h = rect.height || 78;
  if (canvas.width !== Math.round(w * dpr) || canvas.height !== Math.round(h * dpr)) {
    canvas.width = Math.round(w * dpr);
    canvas.height = Math.round(h * dpr);
  }
  const ctx = canvas.getContext("2d");
  ctx.save();
  ctx.scale(dpr, dpr);

  // Background
  ctx.fillStyle = "#0c0e17";
  ctx.fillRect(0, 0, w, h);

  // Subtle grid lines
  ctx.strokeStyle = "rgba(255, 255, 255, 0.04)";
  ctx.lineWidth = 1;
  for (let x = 0; x < w; x += 60) {
    ctx.beginPath();
    ctx.moveTo(x, 0);
    ctx.lineTo(x, h);
    ctx.stroke();
  }

  const { peaks, totalDuration, start, duration } = videoAudioRange;
  if (!peaks || totalDuration <= 0) {
    ctx.fillStyle = "rgba(144, 151, 173, 0.6)";
    ctx.font = "12px system-ui, sans-serif";
    ctx.textAlign = "center";
    ctx.textBaseline = "middle";
    ctx.fillText("Lade Wellenform…", w / 2, h / 2);
    ctx.restore();
    return;
  }

  const selStartSec = Math.max(0, Math.min(totalDuration, start));
  const selEndSec = Math.max(selStartSec, Math.min(totalDuration, start + duration));
  const startX = (selStartSec / totalDuration) * w;
  const endX = (selEndSec / totalDuration) * w;

  // Waveform bars
  const numBars = peaks.length;
  const barSpacing = w / numBars;
  const barW = Math.max(1.5, barSpacing * 0.72);
  const midY = h / 2;

  for (let i = 0; i < numBars; i++) {
    const x = i * barSpacing;
    const barAmp = peaks[i];
    const barH = Math.max(3, barAmp * (h * 0.76));
    const topY = midY - barH / 2;

    const inSelection = (x + barW >= startX && x <= endX);
    if (inSelection) {
      const grad = ctx.createLinearGradient(0, topY, 0, topY + barH);
      grad.addColorStop(0, "#ff7a45");
      grad.addColorStop(0.5, "#ff5252");
      grad.addColorStop(1, "#ff9800");
      ctx.fillStyle = grad;
    } else {
      ctx.fillStyle = "rgba(120, 130, 160, 0.32)";
    }

    if (ctx.roundRect) {
      ctx.beginPath();
      ctx.roundRect(x, topY, barW, barH, 1.5);
      ctx.fill();
    } else {
      ctx.fillRect(x, topY, barW, barH);
    }
  }

  // Dim outside areas
  ctx.fillStyle = "rgba(5, 7, 12, 0.45)";
  if (startX > 0) ctx.fillRect(0, 0, startX, h);
  if (endX < w) ctx.fillRect(endX, 0, w - endX, h);

  // Selection overlay
  const selWidth = Math.max(1, endX - startX);
  ctx.fillStyle = "rgba(255, 90, 70, 0.08)";
  ctx.fillRect(startX, 0, selWidth, h);

  // Border top and bottom
  ctx.fillStyle = "rgba(255, 120, 80, 0.55)";
  ctx.fillRect(startX, 0, selWidth, 2);
  ctx.fillRect(startX, h - 2, selWidth, 2);

  // Left handle
  ctx.fillStyle = "#ffffff";
  ctx.fillRect(startX - 1, 0, 3, h);
  ctx.fillStyle = "#ff6a3d";
  if (ctx.roundRect) {
    ctx.beginPath();
    ctx.roundRect(startX - 3.5, h / 2 - 12, 7, 24, 3);
    ctx.fill();
  } else {
    ctx.fillRect(startX - 3.5, h / 2 - 12, 7, 24);
  }
  ctx.fillStyle = "#ffffff";
  ctx.fillRect(startX, h / 2 - 6, 1, 12);

  // Right handle
  ctx.fillStyle = "#ffffff";
  ctx.fillRect(endX - 1, 0, 3, h);
  ctx.fillStyle = "#ff6a3d";
  if (ctx.roundRect) {
    ctx.beginPath();
    ctx.roundRect(endX - 3.5, h / 2 - 12, 7, 24, 3);
    ctx.fill();
  } else {
    ctx.fillRect(endX - 3.5, h / 2 - 12, 7, 24);
  }
  ctx.fillStyle = "#ffffff";
  ctx.fillRect(endX, h / 2 - 6, 1, 12);

  // Time tags
  ctx.font = "bold 10px Consolas, monospace";
  ctx.textBaseline = "top";

  const startStr = formatTimeSec(selStartSec);
  const startTagW = ctx.measureText(startStr).width + 6;
  const startTagX = Math.max(2, Math.min(w - startTagW - 2, startX - startTagW / 2));
  ctx.fillStyle = "rgba(0, 0, 0, 0.78)";
  ctx.fillRect(startTagX, 3, startTagW, 13);
  ctx.fillStyle = "#ff9800";
  ctx.fillText(startStr, startTagX + 3, 4);

  const endStr = formatTimeSec(selEndSec);
  const endTagW = ctx.measureText(endStr).width + 6;
  const endTagX = Math.max(2, Math.min(w - endTagW - 2, endX - endTagW / 2));
  ctx.fillStyle = "rgba(0, 0, 0, 0.78)";
  ctx.fillRect(endTagX, h - 16, endTagW, 13);
  ctx.fillStyle = "#ff9800";
  ctx.fillText(endStr, endTagX + 3, h - 15);

  // Playback cursor
  if (previewAudioEl && !previewAudioEl.paused) {
    const curT = previewAudioEl.currentTime;
    const curX = (curT / totalDuration) * w;
    ctx.shadowColor = "#33d6a6";
    ctx.shadowBlur = 8;
    ctx.fillStyle = "#33d6a6";
    ctx.fillRect(curX - 1, 0, 2, h);
    ctx.shadowBlur = 0;
  }

  ctx.restore();
}

let isCanvasDragging = false;
let canvasDragMode = null;
let dragDownT = 0;
let dragInitialStart = 0;
let dragInitialDuration = 0;
let dragMoveOffset = 0;

function setRangePresetActive(preset) {
  videoAudioRange.activePreset = preset;
  $$(".seg-range-btn").forEach(btn => {
    btn.classList.toggle("active", btn.dataset.range === preset);
  });
}

function checkAndSyncPresetBadge() {
  const { totalDuration, duration, start } = videoAudioRange;
  const isFull = Math.abs(duration - totalDuration) < 0.6 && start < 0.2;
  if (isFull) {
    setRangePresetActive("full");
  } else if (Math.abs(duration - 15) < 0.6) {
    setRangePresetActive("15");
  } else if (Math.abs(duration - 30) < 0.6) {
    setRangePresetActive("30");
  } else if (Math.abs(duration - 60) < 0.6) {
    setRangePresetActive("60");
  } else {
    setRangePresetActive("custom");
  }
}

function initWaveformMouseEvents() {
  const canvas = $("#videoWaveformCanvas");
  if (!canvas || canvas._mouseInited) return;
  canvas._mouseInited = true;

  function getTimeFromEvent(e) {
    const rect = canvas.getBoundingClientRect();
    const x = Math.max(0, Math.min(rect.width, e.clientX - rect.left));
    const ratio = rect.width > 0 ? (x / rect.width) : 0;
    return ratio * (videoAudioRange.totalDuration || 1);
  }

  function getXFromTime(t) {
    const rect = canvas.getBoundingClientRect();
    const ratio = videoAudioRange.totalDuration > 0 ? (t / videoAudioRange.totalDuration) : 0;
    return ratio * rect.width;
  }

  canvas.addEventListener("mousedown", (e) => {
    if (e.button !== 0) return;
    const { totalDuration, start, duration } = videoAudioRange;
    if (totalDuration <= 0) return;

    const t = getTimeFromEvent(e);
    const rect = canvas.getBoundingClientRect();
    const mouseX = e.clientX - rect.left;
    const startX = getXFromTime(start);
    const endX = getXFromTime(start + duration);

    isCanvasDragging = true;
    dragDownT = t;
    dragInitialStart = start;
    dragInitialDuration = duration;

    const hitDist = 9;
    if (Math.abs(mouseX - startX) <= hitDist) {
      canvasDragMode = "start";
    } else if (Math.abs(mouseX - endX) <= hitDist) {
      canvasDragMode = "end";
    } else if (mouseX > startX && mouseX < endX) {
      canvasDragMode = "move";
      dragMoveOffset = t - start;
    } else {
      canvasDragMode = "create";
      videoAudioRange.start = t;
      videoAudioRange.duration = 0.5;
    }

    if (previewAudioEl && !previewAudioEl.paused) stopAudioRangePreview();
    setRangePresetActive("custom");
    updateAudioRangeUI();
    renderWaveformCanvas();
  });

  window.addEventListener("mousemove", (e) => {
    if (!canvas.offsetParent) return;
    const { totalDuration, start, duration } = videoAudioRange;
    if (totalDuration <= 0) return;

    if (!isCanvasDragging) {
      const rect = canvas.getBoundingClientRect();
      const mouseX = e.clientX - rect.left;
      const mouseY = e.clientY - rect.top;
      if (mouseX >= 0 && mouseX <= rect.width && mouseY >= 0 && mouseY <= rect.height) {
        const startX = getXFromTime(start);
        const endX = getXFromTime(start + duration);
        const hitDist = 9;
        if (Math.abs(mouseX - startX) <= hitDist || Math.abs(mouseX - endX) <= hitDist) {
          canvas.style.cursor = "ew-resize";
        } else if (mouseX > startX && mouseX < endX) {
          canvas.style.cursor = "grab";
        } else {
          canvas.style.cursor = "crosshair";
        }
      }
      return;
    }

    const t = getTimeFromEvent(e);

    if (canvasDragMode === "start") {
      canvas.style.cursor = "ew-resize";
      const currentEnd = dragInitialStart + dragInitialDuration;
      const newStart = Math.max(0, Math.min(currentEnd - 0.5, t));
      videoAudioRange.start = newStart;
      videoAudioRange.duration = Math.max(0.5, currentEnd - newStart);
    } else if (canvasDragMode === "end") {
      canvas.style.cursor = "ew-resize";
      const newEnd = Math.min(totalDuration, Math.max(videoAudioRange.start + 0.5, t));
      videoAudioRange.duration = Math.max(0.5, newEnd - videoAudioRange.start);
    } else if (canvasDragMode === "move") {
      canvas.style.cursor = "grabbing";
      const dur = dragInitialDuration;
      let newStart = t - dragMoveOffset;
      if (newStart < 0) newStart = 0;
      if (newStart + dur > totalDuration) newStart = totalDuration - dur;
      videoAudioRange.start = Math.max(0, newStart);
      videoAudioRange.duration = dur;
    } else if (canvasDragMode === "create") {
      canvas.style.cursor = "crosshair";
      const s = Math.max(0, Math.min(dragDownT, t));
      const e_pos = Math.min(totalDuration, Math.max(dragDownT, t));
      videoAudioRange.start = s;
      videoAudioRange.duration = Math.max(0.5, e_pos - s);
    }

    updateAudioRangeUI();
    renderWaveformCanvas();
  });

  window.addEventListener("mouseup", () => {
    if (isCanvasDragging) {
      isCanvasDragging = false;
      canvasDragMode = null;
      canvas.style.cursor = "crosshair";
      checkAndSyncPresetBadge();
      updateAudioRangeUI();
      renderWaveformCanvas();
    }
  });

  window.addEventListener("resize", () => {
    if (canvas.offsetParent) renderWaveformCanvas();
  });
}

function initVideoAudioRangeControls() {
  $$(".seg-range-btn").forEach(btn => {
    btn.onclick = () => {
      const val = btn.dataset.range;
      const { totalDuration } = videoAudioRange;
      if (totalDuration <= 0) return;
      if (val === "full") {
        videoAudioRange.start = 0;
        videoAudioRange.duration = totalDuration;
      } else {
        const targetDur = parseFloat(val) || 30;
        const dur = Math.min(targetDur, totalDuration);
        if (videoAudioRange.start + dur > totalDuration) {
          videoAudioRange.start = Math.max(0, totalDuration - dur);
        }
        videoAudioRange.duration = dur;
      }
      setRangePresetActive(val);
      if (previewAudioEl && !previewAudioEl.paused) stopAudioRangePreview();
      updateAudioRangeUI();
      renderWaveformCanvas();
    };
  });

  const inpStart = $("#inpAudioRangeStart");
  if (inpStart) {
    inpStart.oninput = () => {
      const val = parseFloat(inpStart.value) || 0;
      const { totalDuration } = videoAudioRange;
      const clampedStart = Math.max(0, Math.min(totalDuration - 0.5, val));
      videoAudioRange.start = clampedStart;
      if (clampedStart + videoAudioRange.duration > totalDuration) {
        videoAudioRange.duration = Math.max(0.5, totalDuration - clampedStart);
      }
      checkAndSyncPresetBadge();
      updateAudioRangeUI();
      renderWaveformCanvas();
    };
  }

  const inpDur = $("#inpAudioRangeDuration");
  if (inpDur) {
    inpDur.oninput = () => {
      const val = parseFloat(inpDur.value) || 1;
      const { totalDuration } = videoAudioRange;
      const maxDur = Math.max(0.5, totalDuration - videoAudioRange.start);
      videoAudioRange.duration = Math.max(0.5, Math.min(maxDur, val));
      checkAndSyncPresetBadge();
      updateAudioRangeUI();
      renderWaveformCanvas();
    };
  }

  const btnPreview = $("#btnPreviewAudioRange");
  if (btnPreview) {
    btnPreview.onclick = () => toggleAudioRangePreview();
  }
}

function toggleAudioRangePreview() {
  if (previewAudioEl && !previewAudioEl.paused) {
    stopAudioRangePreview();
    return;
  }
  startAudioRangePreview();
}

function startAudioRangePreview() {
  stopAudioRangePreview();
  if (!currentVideoExport || !currentVideoExport.activeTrack || !currentVideoExport.activeTrack.url) return;
  previewAudioEl = new Audio(currentVideoExport.activeTrack.url);
  previewAudioEl.currentTime = videoAudioRange.start;
  const ico = $("#icoPreviewAudio");
  const txt = $("#txtPreviewAudio");
  if (ico) ico.textContent = "⏹";
  if (txt) txt.textContent = t("previewRangeStop");

  previewAudioEl.play().catch(e => console.warn("Audio preview failed:", e));

  const endTime = videoAudioRange.start + videoAudioRange.duration;
  function trackLoop() {
    if (!previewAudioEl || previewAudioEl.paused) return;
    if (previewAudioEl.currentTime >= endTime || previewAudioEl.ended) {
      stopAudioRangePreview();
      return;
    }
    renderWaveformCanvas();
    previewAudioRaf = requestAnimationFrame(trackLoop);
  }
  previewAudioRaf = requestAnimationFrame(trackLoop);
  previewAudioEl.onended = () => stopAudioRangePreview();
}

function stopAudioRangePreview() {
  if (previewAudioRaf) {
    cancelAnimationFrame(previewAudioRaf);
    previewAudioRaf = null;
  }
  if (previewAudioEl) {
    try {
      previewAudioEl.pause();
      previewAudioEl.removeAttribute("src");
      previewAudioEl.load();
    } catch (_) {}
    previewAudioEl = null;
  }
  const ico = $("#icoPreviewAudio");
  const txt = $("#txtPreviewAudio");
  if (ico) ico.textContent = "▶";
  if (txt) txt.textContent = t("previewRangePlay");
  renderWaveformCanvas();
}

function openVideoExportDialog(info) {
  stopVideoExportPlayback();
  currentVideoExport = info;
  const dlg = $("#dlgExportVideo");
  if (!dlg) return;

  initVideoSubtitleFonts();
  initWaveformMouseEvents();
  initVideoAudioRangeControls();

  const trackUrl = info.activeTrack ? info.activeTrack.url : null;
  videoAudioRange.url = trackUrl;
  videoAudioRange.start = 0.0;
  videoAudioRange.duration = 0.0;
  videoAudioRange.totalDuration = 0.0;
  videoAudioRange.peaks = null;
  setRangePresetActive("full");
  updateAudioRangeUI();
  setTimeout(() => renderWaveformCanvas(), 40);

  if (trackUrl) {
    loadAudioWaveform(trackUrl).then(data => {
      if (videoAudioRange.url !== trackUrl) return;
      videoAudioRange.totalDuration = data.totalDuration;
      videoAudioRange.peaks = data.peaks;
      if (videoAudioRange.activePreset === "full" || videoAudioRange.duration <= 0) {
        videoAudioRange.start = 0.0;
        videoAudioRange.duration = data.totalDuration;
      }
      updateAudioRangeUI();
      renderWaveformCanvas();
    }).catch(err => {
      console.warn("Waveform decode error:", err);
      const tempA = new Audio(trackUrl);
      tempA.onloadedmetadata = () => {
        if (videoAudioRange.url !== trackUrl) return;
        videoAudioRange.totalDuration = tempA.duration || 60;
        if (videoAudioRange.activePreset === "full" || videoAudioRange.duration <= 0) {
          videoAudioRange.start = 0.0;
          videoAudioRange.duration = videoAudioRange.totalDuration;
        }
        updateAudioRangeUI();
        renderWaveformCanvas();
      };
    });
  }

  const chkSubs = $("#chkVideoIncludeSubtitles");
  const fieldFont = $("#fieldVideoSubtitleFont");
  const rowTiming = $("#rowVideoSubtitleTiming");
  const hintNoSubs = $("#videoNoSubtitlesHint");
  const isFlac = !!(info.activeTrack && (info.activeTrack.name?.toLowerCase().endsWith(".flac") || info.activeTrack.url?.toLowerCase().includes(".flac")));
  const hasSubs = !!(info.activeSub || (info.parsedCues && info.parsedCues.length > 0) || isFlac);

  const inpOffset = $("#inpVideoSubtitleOffset");
  if (inpOffset) inpOffset.value = "0.0";
  const inpSpeed = $("#inpVideoSubtitleSpeed");
  if (inpSpeed) inpSpeed.value = "100";

  if (!hasSubs) {
    if (chkSubs) {
      chkSubs.checked = false;
      chkSubs.disabled = true;
    }
    if (hintNoSubs) hintNoSubs.hidden = false;
    if (fieldFont) fieldFont.hidden = true;
    if (rowTiming) rowTiming.hidden = true;
  } else {
    if (chkSubs) {
      chkSubs.disabled = false;
      const savedSubsPref = localStorage.getItem("tamusicmaker_video_subtitles");
      chkSubs.checked = savedSubsPref !== "0";
    }
    if (hintNoSubs) hintNoSubs.hidden = true;
    if (fieldFont) fieldFont.hidden = !chkSubs.checked;
    if (rowTiming) rowTiming.hidden = !chkSubs.checked;
  }

  if (chkSubs) {
    chkSubs.onchange = () => {
      localStorage.setItem("tamusicmaker_video_subtitles", chkSubs.checked ? "1" : "0");
      if (fieldFont) fieldFont.hidden = !chkSubs.checked;
      if (rowTiming) rowTiming.hidden = !chkSubs.checked;
    };
  }

  $("#dlgVideoSongTitle").textContent = info.title;
  $("#videoRenderProgress").hidden = true;
  $("#videoResultBox").hidden = true;
  const btnStartInit = $("#btnStartRenderVideo");
  if (btnStartInit) {
    btnStartInit.disabled = false;
    btnStartInit.className = "primary";
  }
  const btnSaveInit = $("#btnSaveVideoAction");
  if (btnSaveInit) btnSaveInit.style.display = "none";

  const hasFfmpeg = !!(S.status && S.status.ffmpeg);
  const selEngine = $("#selVideoEngine");
  const notice = $("#videoEngineNotice");

  if (hasFfmpeg) {
    selEngine.value = "server";
    notice.textContent = t("videoEngineServerHint");
    notice.style.color = "var(--accent2)";
  } else {
    selEngine.value = "browser";
    notice.textContent = t("videoEngineBrowserHint");
    notice.style.color = "var(--mute)";
  }

  selEngine.onchange = () => {
    if (selEngine.value === "server") {
      notice.textContent = t("videoEngineServerHint");
      notice.style.color = "var(--accent2)";
    } else {
      notice.textContent = t("videoEngineBrowserHint");
      notice.style.color = "var(--mute)";
    }
  };

  const selStyle = $("#selVideoStyle");
  const rowCustom = $("#rowExportCustomVideo");
  const fileInput = $("#fileExportCustomVideo");
  const btnChoose = $("#btnChooseExportVideo");
  const txtName = $("#txtExportVideoName");
  const btnClear = $("#btnClearExportVideo");

  const rowCustomImg = $("#rowExportCustomImage");
  const fileInputImg = $("#fileExportCustomImage");
  const btnChooseImg = $("#btnChooseExportImage");
  const txtNameImg = $("#txtExportImageName");
  const btnClearImg = $("#btnClearExportImage");

  function updateCustomVideoRow() {
    const isCustom = selStyle && selStyle.value === "custom";
    if (rowCustom) rowCustom.hidden = !isCustom;
    if (isCustom && !window._exportCustomVideoFile && window._tamusicmaker_custom_file) {
      window._exportCustomVideoFile = window._tamusicmaker_custom_file;
    }
    if (txtName) {
      if (window._exportCustomVideoFile) {
        txtName.textContent = window._exportCustomVideoFile.name;
        if (btnClear) btnClear.style.display = "inline-flex";
      } else {
        txtName.textContent = t("customVideoSelectPrompt");
        if (btnClear) btnClear.style.display = "none";
      }
    }
  }

  function updateCustomImageRow() {
    const isCustomImg = selStyle && selStyle.value === "custom_image";
    if (rowCustomImg) rowCustomImg.hidden = !isCustomImg;
    if (isCustomImg && !window._exportCustomImageFile && window._tamusicmaker_custom_image_file) {
      window._exportCustomImageFile = window._tamusicmaker_custom_image_file;
    }
    if (txtNameImg) {
      if (window._exportCustomImageFile) {
        txtNameImg.textContent = window._exportCustomImageFile.name;
        if (btnClearImg) btnClearImg.style.display = "inline-flex";
      } else {
        txtNameImg.textContent = t("customImageSelectPrompt");
        if (btnClearImg) btnClearImg.style.display = "none";
      }
    }
  }

  function updateMediaRows() {
    updateCustomVideoRow();
    updateCustomImageRow();
  }

  if (selStyle) selStyle.onchange = updateMediaRows;
  if (btnChoose) btnChoose.onclick = () => fileInput && fileInput.click();
  if (fileInput) {
    fileInput.onchange = () => {
      if (fileInput.files && fileInput.files[0]) {
        window._exportCustomVideoFile = fileInput.files[0];
        updateCustomVideoRow();
      }
    };
  }
  if (btnClear) {
    btnClear.onclick = () => {
      window._exportCustomVideoFile = null;
      if (fileInput) fileInput.value = "";
      updateCustomVideoRow();
    };
  }

  if (btnChooseImg) btnChooseImg.onclick = () => fileInputImg && fileInputImg.click();
  if (fileInputImg) {
    fileInputImg.onchange = () => {
      if (fileInputImg.files && fileInputImg.files[0]) {
        window._exportCustomImageFile = fileInputImg.files[0];
        updateCustomImageRow();
      }
    };
  }
  if (btnClearImg) {
    btnClearImg.onclick = () => {
      window._exportCustomImageFile = null;
      if (fileInputImg) fileInputImg.value = "";
      updateCustomImageRow();
    };
  }

  updateMediaRows();

  dlg.showModal();
}

async function startVideoExport() {
  if (!currentVideoExport) return;
  const info = currentVideoExport;
  const progressBox = $("#videoRenderProgress");
  const resultBox = $("#videoResultBox");
  const pStatus = $("#videoRenderStatus");
  const btnStart = $("#btnStartRenderVideo");

  try {
    const aspect = $("#selVideoAspect")?.value || "16:9";
    const style = $("#selVideoStyle")?.value || "retro";
    const durationMode = $("#selVideoDurationMode")?.value || "audio";
    const subtitleFont = $("#inpVideoSubtitleFont")?.value?.trim() || "Impact";
    const subtitleOffset = parseFloat($("#inpVideoSubtitleOffset")?.value || "0.0") || 0.0;
    const subtitleSpeedPct = parseFloat($("#inpVideoSubtitleSpeed")?.value || "100") || 100;
    const subtitleSpeed = subtitleSpeedPct / 100.0;
    const chkSubs = $("#chkVideoIncludeSubtitles");
    const includeSubtitles = chkSubs ? chkSubs.checked : true;
    const engine = $("#selVideoEngine")?.value || "server";

    progressBox.hidden = false;
    resultBox.hidden = true;
    btnStart.disabled = true;
    pStatus.textContent = t("videoRendering");

    let bgVideoUrl = null;
    const customFile = window._exportCustomVideoFile || window._tamusicmaker_custom_file;
    const customImgFile = window._exportCustomImageFile || window._tamusicmaker_custom_image_file;
    const chosenMediaFile = style === "custom_image" ? customImgFile : customFile;

    if (style === "custom" || style === "custom_image") {
      if (!chosenMediaFile) {
        toast(style === "custom_image" ? t("customImageSelectPrompt") : t("customVideoSelectPrompt"), true);
        progressBox.hidden = true;
        btnStart.disabled = false;
        return;
      }
      if (engine === "server" && S.status && S.status.ffmpeg) {
        pStatus.textContent = style === "custom_image" ? t("customImageUploading") : t("customVideoUploading");
        try {
          const ext = chosenMediaFile.name.split(".").pop().toLowerCase() || (style === "custom_image" ? "png" : "mp4");
          const upResp = await fetch("/api/video/upload_bg", {
            method: "POST",
            headers: {
              "Content-Type": chosenMediaFile.type || (style === "custom_image" ? "image/png" : "video/mp4"),
              "X-File-Ext": ext,
            },
            body: chosenMediaFile,
          });
          const upData = await upResp.json();
          if (upData.ok && upData.url) {
            bgVideoUrl = upData.url;
          } else {
            throw new Error(upData.error || "Upload failed");
          }
        } catch (err) {
          console.warn("Background media upload failed:", err);
        }
      }
    }

    pStatus.textContent = t("videoRendering");

    const isFullRange = videoAudioRange.activePreset === "full" ||
      (videoAudioRange.start < 0.2 && Math.abs(videoAudioRange.duration - videoAudioRange.totalDuration) < 0.6);
    const audioStart = isFullRange ? 0.0 : videoAudioRange.start;
    const audioDuration = isFullRange ? 0.0 : videoAudioRange.duration;

    if (engine === "server" && S.status && S.status.ffmpeg) {
      try {
        const payload = {
          audio_url: info.activeTrack.url,
          audio_start: audioStart,
          audio_duration: audioDuration,
          title: info.title,
          aspect: aspect,
          style: style,
          bg_video_url: bgVideoUrl,
          duration_mode: durationMode,
          subtitle_font: subtitleFont,
          include_subtitles: includeSubtitles,
          subtitle_offset: subtitleOffset,
          subtitle_speed: subtitleSpeed,
          cover_url: info.coverImg ? info.coverImg.url : null,
          srt_url: (includeSubtitles && info.activeSub) ? info.activeSub.url : null,
        };
        const res = await api("/api/video/render", payload);
        const dlg = $("#dlgExportVideo");
        if (!dlg || !dlg.open) return;
        if (res.ok && res.url) {
          progressBox.hidden = true;
          resultBox.hidden = false;
          btnStart.disabled = false;
          btnStart.className = "ghost";
          const downloadUrl = res.download_url || (res.url.includes("?") ? `${res.url}&download=1` : `${res.url}?download=1`);
          const video = $("#videoPreview");
          video.src = res.url;
          const dl = $("#btnDownloadVideo");
          dl.href = downloadUrl;
          dl.download = res.name;
          dl.textContent = `💾 ${res.name}`;
          const saveAction = $("#btnSaveVideoAction");
          if (saveAction) {
            saveAction.href = downloadUrl;
            saveAction.download = res.name;
            saveAction.textContent = t("btnSaveVideo");
            saveAction.style.display = "inline-flex";
          }
          toast(t("videoReady"));
        } else {
          throw new Error(res.error || "Unknown error");
        }
      } catch (err) {
        console.warn("Server video render failed, falling back to browser recording:", err);
        pStatus.textContent = "Server-Export fehlgeschlagen, wechsle auf Web-Engine…";
        await runBrowserVideoRecord(info, aspect, style, progressBox, resultBox, pStatus, btnStart, chosenMediaFile, durationMode, subtitleFont, includeSubtitles, subtitleOffset, subtitleSpeed, audioStart, audioDuration);
      }
    } else {
      await runBrowserVideoRecord(info, aspect, style, progressBox, resultBox, pStatus, btnStart, chosenMediaFile, durationMode, subtitleFont, includeSubtitles, subtitleOffset, subtitleSpeed, audioStart, audioDuration);
    }
  } catch (err) {
    console.error("Video export encountered an error:", err);
    toast(t("videoFailed") + ": " + (err.message || err), true);
    if (progressBox) progressBox.hidden = true;
    if (btnStart) {
      btnStart.disabled = false;
      btnStart.className = "primary";
    }
  }
}

async function runBrowserVideoRecord(info, aspect, style, progressBox, resultBox, pStatus, btnStart, customFile = null, durationMode = "audio", subtitleFont = "Impact", includeSubtitles = true, subtitleOffset = 0.0, subtitleSpeed = 1.0, audioStart = 0.0, audioDuration = 0.0) {
  try {
    pStatus.textContent = "Web-Engine nimmt Video auf…";
    await ensureFontLoaded(subtitleFont);
    const isPortrait = aspect === "9:16";
    const width = isPortrait ? 720 : 1280;
    const height = isPortrait ? 1280 : 720;

    let parsedCues = info.parsedCues || [];
    if (includeSubtitles && (!parsedCues || !parsedCues.length) && info.activeSub && info.activeSub.url) {
      try {
        const sResp = await fetch(info.activeSub.url);
        const sTxt = await sResp.text();
        parsedCues = parseSrt(sTxt);
      } catch (_) {}
    }
    if (includeSubtitles && parsedCues && parsedCues.length) {
      if (audioStart > 0.001 || audioDuration > 0.001) {
        const clipEnd = audioDuration > 0.001 ? audioStart + audioDuration : 999999;
        parsedCues = parsedCues
          .filter((c) => c.end > audioStart && c.start < clipEnd)
          .map((c) => ({
            ...c,
            start: Math.max(0, (c.start - audioStart) * subtitleSpeed + subtitleOffset),
            end: Math.max(0.3, (c.end - audioStart) * subtitleSpeed + subtitleOffset),
          }));
      } else if (Math.abs(subtitleOffset) > 0.001 || Math.abs(subtitleSpeed - 1.0) > 0.001) {
        parsedCues = parsedCues.map((c) => ({
          ...c,
          start: Math.max(0, c.start * subtitleSpeed + subtitleOffset),
          end: Math.max(0.3, c.end * subtitleSpeed + subtitleOffset),
        }));
      }
    }

    const offCanvas = document.createElement("canvas");
    offCanvas.width = width;
    offCanvas.height = height;
    const ctx = offCanvas.getContext("2d");

    let customBgVideoEl = null;
    let customBgImageBitmap = null;
    if (style === "custom" && customFile) {
      customBgVideoEl = document.createElement("video");
      customBgVideoEl.src = URL.createObjectURL(customFile);
      customBgVideoEl.loop = durationMode !== "video";
      customBgVideoEl.muted = true;
      customBgVideoEl.playsInline = true;
      await new Promise((resolve) => {
        customBgVideoEl.onloadeddata = resolve;
        customBgVideoEl.onerror = resolve;
        customBgVideoEl.load();
      });
    } else if (style === "custom_image" && customFile) {
      try {
        customBgImageBitmap = await createImageBitmap(customFile);
      } catch (e) {
        console.warn("Failed to create image bitmap:", e);
      }
    }

    const AC = window.AudioContext || window.webkitAudioContext;
    const audioCtx = new AC();
    if (audioCtx.state === "suspended") await audioCtx.resume();

    const audioEl = document.createElement("audio");
    audioEl.crossOrigin = "anonymous";
    audioEl.src = info.activeTrack.url;
    audioEl.preload = "auto";

    const mediaSrc = audioCtx.createMediaElementSource(audioEl);
    const analyser = audioCtx.createAnalyser();
    analyser.fftSize = 128;
    const dest = audioCtx.createMediaStreamDestination();

    mediaSrc.connect(analyser);
    analyser.connect(dest);
    analyser.connect(audioCtx.destination);

    let coverBitmap = null;
    if (info.coverImg && info.coverImg.url) {
      try {
        const resp = await fetch(info.coverImg.url);
        const blob = await resp.blob();
        coverBitmap = await createImageBitmap(blob);
      } catch (e) {}
    }

    const canvasStream = offCanvas.captureStream(30);
    const combined = new MediaStream([
      ...canvasStream.getVideoTracks(),
      ...dest.stream.getAudioTracks(),
    ]);

    const mime = MediaRecorder.isTypeSupported("video/webm;codecs=vp9,opus")
      ? "video/webm;codecs=vp9,opus"
      : MediaRecorder.isTypeSupported("video/webm")
      ? "video/webm"
      : "video/mp4";

    const recorder = new MediaRecorder(combined, { mimeType: mime, videoBitsPerSecond: 4_000_000 });
    const chunks = [];
    recorder.ondataavailable = (e) => {
      if (e.data && e.data.size > 0) chunks.push(e.data);
    };

    let recording = true;
    let aborted = false;

    activeBrowserVideoAbort = () => {
      aborted = true;
      recording = false;
      try {
        audioEl.pause();
        audioEl.currentTime = 0;
        audioEl.removeAttribute("src");
        audioEl.load();
      } catch (_) {}
      if (customBgVideoEl) {
        try {
          customBgVideoEl.pause();
          customBgVideoEl.currentTime = 0;
          customBgVideoEl.removeAttribute("src");
          customBgVideoEl.load();
        } catch (_) {}
      }
      try {
        if (recorder && recorder.state === "recording") {
          recorder.onstop = null;
          recorder.stop();
        }
      } catch (_) {}
      try {
        audioCtx.close();
      } catch (_) {}
    };

    const videoVisState = createVisualState();
    if (customBgVideoEl) videoVisState.customVideo = customBgVideoEl;
    if (customBgImageBitmap) videoVisState.customImage = customBgImageBitmap;
    let lastVideoTime = performance.now();

    function renderFrame() {
      if (!recording) return;
      const now = performance.now();
      const dt = Math.min(0.1, (now - lastVideoTime) / 1000) || 0.016;
      lastVideoTime = now;

      const bufLen = analyser.frequencyBinCount;
      const freqData = new Uint8Array(bufLen);
      const waveData = new Uint8Array(bufLen);
      analyser.getByteFrequencyData(freqData);
      analyser.getByteTimeDomainData(waveData);

      // 1. Draw the chosen Visual Scene as dynamic background
      try {
        drawSceneFrame(ctx, style, videoVisState, freqData, waveData, width, height, dt, coverBitmap);
      } catch (e) {
        console.warn("Video visualizer render error:", e);
      }

      // 2. Draw centered framed Cover Art (if present and not blur, custom video or custom image)
      if (coverBitmap && style !== "blur" && style !== "custom" && style !== "custom_image") {
        const cw = isPortrait ? 480 : 380;
        const ch = cw;
        const cx = (width - cw) / 2;
        const cy = isPortrait ? 160 : (height - ch) / 2 - 30;
        ctx.save();
        ctx.shadowColor = "rgba(0, 0, 0, 0.8)";
        ctx.shadowBlur = 24;
        ctx.drawImage(coverBitmap, cx, cy, cw, ch);
        ctx.strokeStyle = "rgba(255, 255, 255, 0.25)";
        ctx.lineWidth = 2;
        ctx.strokeRect(cx, cy, cw, ch);
        ctx.restore();
      }

      // 3. Draw Song Title (skip on custom media to keep visual completely unobstructed)
      if (style !== "custom" && style !== "custom_image") {
        ctx.save();
        ctx.fillStyle = "#ffffff";
        ctx.font = `bold 26px "${subtitleFont}", sans-serif`;
        ctx.textAlign = "center";
        ctx.shadowColor = "rgba(0,0,0,0.9)";
        ctx.shadowBlur = 10;
        const titleY = isPortrait ? (style === "blur" ? 420 : 120) : (style === "blur" ? 180 : 60);
        ctx.fillText(info.title || "Song", width / 2, titleY);
        ctx.restore();
      }

      // 4. Draw Current Synchronized Lyric Line (if enabled)
      if (includeSubtitles) {
        const curTime = Math.max(0, audioEl.currentTime - audioStart);
        const curCue = parsedCues.find((c) => c.start <= curTime && curTime <= c.end + 0.3);
        if (curCue) {
          ctx.save();
          const cueFontSize = isPortrait ? 28 : 24;
          ctx.font = `bold ${cueFontSize}px "${subtitleFont}", sans-serif`;
          ctx.textAlign = "center";
          const cueY = isPortrait ? height - 120 : height - 50;

          // Clean dark stroke / outline for high contrast over any background (no black box!)
          ctx.lineWidth = 4;
          ctx.strokeStyle = "rgba(0, 0, 0, 0.9)";
          ctx.shadowColor = "rgba(0, 0, 0, 0.85)";
          ctx.shadowBlur = 4;
          ctx.strokeText(curCue.text, width / 2, cueY);

          // White text with subtle accent glow
          ctx.fillStyle = "#ffffff";
          ctx.shadowColor = "rgba(51, 214, 166, 0.7)";
          ctx.shadowBlur = 6;
          ctx.fillText(curCue.text, width / 2, cueY);
          ctx.restore();
        }
      }

      if (audioDuration > 0.001 && audioEl.currentTime >= audioStart + audioDuration) {
        if (recorder.state === "recording") recorder.stop();
        return;
      }

      requestAnimationFrame(renderFrame);
    }

    recorder.onstop = () => {
      if (aborted) return;
      recording = false;
      activeBrowserVideoAbort = null;
      if (customBgVideoEl) customBgVideoEl.pause();
      try { audioCtx.close(); } catch (_) {}
      const dlg = $("#dlgExportVideo");
      if (!dlg || !dlg.open) return;
      const blob = new Blob(chunks, { type: mime });
      const videoUrl = URL.createObjectURL(blob);
      progressBox.hidden = true;
      resultBox.hidden = false;
      const video = $("#videoPreview");
      video.src = videoUrl;
      const ext = mime.includes("mp4") ? "mp4" : "webm";
      const fileName = `${info.title || "song"}.${ext}`;
      const dl = $("#btnDownloadVideo");
      dl.href = videoUrl;
      dl.download = fileName;
      dl.textContent = `💾 ${fileName}`;
      const saveAction = $("#btnSaveVideoAction");
      if (saveAction) {
        saveAction.href = videoUrl;
        saveAction.download = fileName;
        saveAction.textContent = t("btnSaveVideo");
        saveAction.style.display = "inline-flex";
      }
      btnStart.disabled = false;
      btnStart.className = "ghost";
      toast(t("videoReady"));
    };

    recorder.start(100);
    if (audioStart > 0.001) {
      try { audioEl.currentTime = audioStart; } catch (_) {}
    }
    audioEl.play();
    if (customBgVideoEl) customBgVideoEl.play().catch(() => {});
    renderFrame();

    if (durationMode === "video" && customBgVideoEl) {
      customBgVideoEl.onended = () => {
        if (recorder.state === "recording") recorder.stop();
      };
      audioEl.onended = () => {
        audioEl.currentTime = audioStart;
        audioEl.play().catch(() => {});
      };
      customBgVideoEl.ontimeupdate = () => {
        if (customBgVideoEl.duration) {
          const pct = Math.floor((customBgVideoEl.currentTime / customBgVideoEl.duration) * 100);
          pStatus.textContent = `${pct}% (${formatTime(customBgVideoEl.currentTime)} / ${formatTime(customBgVideoEl.duration)})`;
        }
      };
    } else {
      audioEl.onended = () => {
        if (recorder.state === "recording") recorder.stop();
      };
      audioEl.ontimeupdate = () => {
        if (customBgVideoEl && customBgVideoEl.duration && !customBgVideoEl.paused) {
          const target = (audioEl.currentTime - audioStart) % customBgVideoEl.duration;
          if (Math.abs(customBgVideoEl.currentTime - target) > 0.4) {
            customBgVideoEl.currentTime = target;
          }
        }
        const targetDur = (audioDuration > 0.001) ? audioDuration : (audioEl.duration || 60);
        const cur = Math.max(0, audioEl.currentTime - audioStart);
        const pct = Math.min(100, Math.floor((cur / targetDur) * 100));
        pStatus.textContent = `${pct}% (${formatTime(cur)} / ${formatTime(targetDur)})`;
        if (audioDuration > 0.001 && audioEl.currentTime >= audioStart + audioDuration) {
          if (recorder.state === "recording") recorder.stop();
        }
      };
    }
  } catch (err) {
    activeBrowserVideoAbort = null;
    console.error("Browser video recording failed:", err);
    progressBox.hidden = true;
    btnStart.disabled = false;
    toast(t("videoFailed") + err.message, true);
  }
}

async function startVoiceSwapFromDialog() {
  $("#dlgVoiceSwap").close();
  if (!S.pendingSwap) return;
  const payload = {
    audio_url: S.pendingSwap.url,
    filename: S.pendingSwap.name,
    model: $("#dlgVoiceModelSelect").value,
    pitch: parseInt($("#dlgVoicePitch").value || "0", 10),
    index_rate: parseFloat($("#dlgVoiceIndexRate").value || "0.75"),
  };
  startJob("/api/voice_swap", payload);
}

function updateVoiceSwapUI() {
  const chk = $("#optVoiceSwap");
  if (chk) {
    const lbl = chk.closest("label");
    const span = lbl?.querySelector('[data-i18n="optVoiceSwap"]');
    if (!S.applioAvailable) {
      chk.checked = false;
      chk.disabled = true;
      $("#voiceSwapOptions").hidden = true;
      lbl?.classList.add("disabled-check");
      if (span) span.textContent = `${t("optVoiceSwap")} ${t("applioNotInstalledShort")}`;
    } else {
      chk.disabled = false;
      lbl?.classList.remove("disabled-check");
      if (span) span.textContent = t("optVoiceSwap");
    }
  }
  document.querySelectorAll('[data-role="voice-swap"]').forEach((b) => {
    b.disabled = !S.applioAvailable;
    b.title = S.applioAvailable ? "" : t("applioMissing");
  });
}

async function loadVoiceModels() {
  try {
    const res = await api("/api/voice_models");
    S.applioAvailable = !!res.available;
    S.voiceModels = res.models || [];
    updateVoiceSwapUI();
    const sel = $("#voiceModelSelect");
    const dlgSel = $("#dlgVoiceModelSelect");
    if (!sel || !dlgSel) return;
    sel.innerHTML = ""; dlgSel.innerHTML = "";
    if (!S.voiceModels.length) {
      const opt = el("option", "", S.applioAvailable ? t("noVoiceModel") : t("applioNotInstalledShort"));
      sel.append(opt); dlgSel.append(opt.cloneNode(true));
      return;
    }
    S.voiceModels.forEach((m) => {
      const opt = el("option", "", m.display_name);
      opt.value = m.name;
      sel.append(opt);
      dlgSel.append(opt.cloneNode(true));
    });
  } catch (e) {
    console.warn("Failed to load voice models:", e);
  }
}

// ---------------------------------------------------------------- history
async function loadHistory() {
  const list = await api("/api/history").catch(() => []);
  const box = $("#historyBox"); box.innerHTML = "";
  if (!list.length) { box.append(el("p", "empty", t("noHistory"))); return; }
  const wrap = el("div", "hist");
  list.forEach((h) => {
    const item = el("div", "item");
    const title = h.title && h.title !== "(automatisch)" && h.title !== "(automatic)" ? h.title : (h.auto ? t("automatic") : t("untitled"));
    const locale = LANG === "de" ? "de-DE" : "en-US";
    item.append(el("h3", "", title), el("div", "hint", new Date(h.ts * 1000).toLocaleString(locale) + (h.auto ? ` · ${t("batch")}` : "")));
    mediaInto(item, h.media || [], { title, lyrics: (h.sheet && h.sheet.lyrics) || "" });
    const row = el("div", "actions");
    const btnPlayInTab = el("button", "accent", t("openInPlayer"));
    btnPlayInTab.onclick = () => {
      loadSongIntoPlayer(h);
      showTab("player");
    };
    const load = el("button", "", t("loadEditor"));
    load.onclick = () => loadSongIntoEditor(h);
    const btnNewTake = el("button", "btn-new-take", "🎤 " + (t("newTake") || "Neuer Take"));
    btnNewTake.onclick = async () => {
      const promptMsg = t("newTakePrompt", { title }) || `Neuen Take für „${title}“ rendern?`;
      if (!confirm(promptMsg)) return;
      try {
        busy(true);
        $("#progress").hidden = false;
        const res = await api("/api/song/new_take", { id: h.id });
        S.job = res;
        showTab("result");
        S.timer = setInterval(pollJob, 800);
      } catch (err) {
        busy(false);
        $("#progress").hidden = true;
        toast(err.message || String(err), true);
      }
    };
    const del = el("button", "ghost danger", t("del"));
    del.onclick = async () => {
      const msg = t("confirmDeleteSong") || "Diesen Song und alle zugehörigen Audiodateien unwiderruflich von der Festplatte löschen?";
      if (!confirm(msg)) return;
      document.querySelectorAll("audio").forEach((a) => {
        try {
          a.pause();
          a.removeAttribute("src");
          a.load();
        } catch (_) {}
      });
      try {
        await api("/api/history/delete", { id: h.id });
        await loadHistory();
        toast(t("songDeleted") || "Song und Dateien von der Festplatte gelöscht.");
      } catch (err) {
        toast("Fehler beim Löschen: " + (err.message || err), true);
      }
    };
    row.append(btnPlayInTab, load, btnNewTake, del); item.append(row); wrap.append(item);
  });
  box.append(wrap);
}

function loadSongIntoEditor(songData) {
  if (!songData) return;
  if (songData.brief) {
    S.brief = { ...S.brief, ...songData.brief };
    buildForm();
  }
  const s = songData.sheet || {};
  if ($("#shTitle")) $("#shTitle").value = s.title || songData.title || "";
  if ($("#shStyle")) $("#shStyle").value = s.style || "";
  if ($("#shLyrics")) $("#shLyrics").value = s.lyrics || "";
  if ($("#shArt")) $("#shArt").value = s.artwork_prompt || "";
  for (const k of DOC_KEYS) S.sheetState[k] = s[k] ? "manual" : "auto";
  refreshDocBadges();
  setMode("review");
  updateLyricCount();
  showTab("sheet");
  toast(t("songLoadedIntoEditor") || "Song mit allen Einstellungen in den Editor geladen.");
}

async function loadSongIntoPlayer(songData) {
  const box = $("#playerBox");
  box.innerHTML = "";

  const history = await api("/api/history").catch(() => []);
  if (history.length) {
    const pickBar = el("div", "row", null);
    pickBar.style.marginBottom = "14px";
    pickBar.style.gap = "10px";
    pickBar.style.alignItems = "center";
    pickBar.append(el("span", "hint", t("playerPickSong")));
    const sel = document.createElement("select");
    sel.id = "playerSongSelect";
    sel.style.flex = "1";
    history.forEach((h) => {
      const opt = document.createElement("option");
      opt.value = h.id;
      const tStr = h.title && h.title !== "(automatisch)" && h.title !== "(automatic)" ? h.title : (h.auto ? t("automatic") : t("untitled"));
      const d = new Date(h.ts * 1000);
      const isToday = d.toDateString() === new Date().toDateString();
      const dStr = isToday
        ? d.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })
        : `${d.toLocaleDateString([], { day: "2-digit", month: "2-digit" })} ${d.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}`;
      opt.textContent = `${tStr} (${dStr})`;
      if (h.id === songData.id) opt.selected = true;
      sel.append(opt);
    });
    sel.onchange = () => {
      const picked = history.find((h) => h.id === sel.value);
      if (picked) loadSongIntoPlayer(picked);
    };
    pickBar.append(sel);

    const btnLoadEditor = el("button", "btn-player-load-editor", "✏️ " + (t("loadEditor") || "In Editor laden"));
    btnLoadEditor.onclick = () => loadSongIntoEditor(songData);
    pickBar.append(btnLoadEditor);

    box.append(pickBar);
  }

  mediaInto(box, songData.media || [], { title: songData.title, lyrics: (songData.sheet && songData.sheet.lyrics) || "", songData });
}

async function ensurePlayerTabLoaded() {
  const box = $("#playerBox");
  const history = await api("/api/history").catch(() => []);
  if (!history.length) {
    box.innerHTML = `<p class="empty">${t("playerSelectPrompt")}</p>`;
    return;
  }
  const sel = $("#playerSongSelect");
  if (sel && box.querySelector(".ta-player")) {
    const currentVal = sel.value;
    sel.innerHTML = "";
    history.forEach((h) => {
      const opt = document.createElement("option");
      opt.value = h.id;
      const tStr = h.title && h.title !== "(automatisch)" && h.title !== "(automatic)" ? h.title : (h.auto ? t("automatic") : t("untitled"));
      const d = new Date(h.ts * 1000);
      const isToday = d.toDateString() === new Date().toDateString();
      const dStr = isToday
        ? d.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })
        : `${d.toLocaleDateString([], { day: "2-digit", month: "2-digit" })} ${d.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}`;
      opt.textContent = `${tStr} (${dStr})`;
      if (h.id === currentVal) opt.selected = true;
      sel.append(opt);
    });
    return;
  }
  loadSongIntoPlayer(history[0]);
}

function showTab(name) {
  document.querySelectorAll("#tabs button").forEach((b) => b.classList.toggle("active", b.dataset.tab === name));
  ["sheet", "mastering", "player", "result", "history"].forEach((tab) => {
    const el = $("#tab-" + tab);
    if (el) el.hidden = tab !== name;
  });
  if (name === "player") {
    ensurePlayerTabLoaded();
  }
}

// ---------------------------------------------------------------- status / settings
async function refreshStatus() {
  try {
    const st = await api("/api/status"); S.status = st;
    const box = $("#status");
    box.className = "status " + (st.comfy ? "ok" : "bad");
    let text = st.comfy ? t("comfyOk") : t("comfyBad");
    if (st.comfy && st.plenio_api) text += " · Plenio API v1";
    if (st.comfy && st.gpu) text += ` · ${st.gpu.replace(/^cuda:\d+\s*/, "")}` + (st.vram_total ? ` · ${(st.vram_free / 2 ** 30).toFixed(1)}/${(st.vram_total / 2 ** 30).toFixed(0)} ${t("gbFree")}` : "");
    if (!st.workflow) text += ` · ${t("wfMissing")}`;
    $("#statusText").textContent = text;
    $("#btnStartComfy").hidden = st.comfy || !st.can_start;
    if (st.comfy && (!S.options._live || !S.options.length)) {
      S.options = await api("/api/options").catch(() => ({}));
      if (Object.keys(S.options).length) {
        buildForm();
        populateSrModels();
      }
    }
  } catch { $("#statusText").textContent = t("serverDown"); $("#status").className = "status bad"; }
}

function populateLangDropdown() {
  const sel = $("#cfgLang");
  sel.innerHTML = "";
  for (const [code, dict] of Object.entries(I18N)) {
    const opt = document.createElement("option");
    opt.value = code;
    opt.textContent = dict._name || code;
    sel.appendChild(opt);
  }
  sel.value = LANG;
}

function applyTheme(theme) {
  const t = theme === "light" ? "light" : "dark";
  document.documentElement.setAttribute("data-theme", t);
  try { localStorage.setItem("tamusicmaker.theme", t); } catch {}
  if ($("#cfgTheme")) $("#cfgTheme").value = t;
}

async function openSettings() {
  const c = await api("/api/config");
  populateLangDropdown();
  $("#cfgLang").value = c.language || LANG;
  $("#cfgTheme").value = c.theme || "dark";
  $("#cfgUrl").value = c.comfy_url; $("#cfgWorkflow").value = c.workflow; $("#cfgDir").value = c.comfy_dir; $("#cfgCmd").value = c.comfy_start_command;
  $("#cfgVoiceModelsDir").value = c.voice_models_dir || "";
  $("#settings").showModal();
}

function setupTooltips() {
  let box = $("#globalTooltip");
  if (!box) {
    box = document.createElement("div");
    box.id = "globalTooltip";
    box.className = "tooltip-popup";
    box.hidden = true;
    document.body.appendChild(box);
  }

  let activeIcon = null;

  function show(icon) {
    if (!icon) return;
    const text = icon.dataset.tip;
    if (!text) return;
    activeIcon = icon;
    box.textContent = text;
    box.hidden = false;
    box.classList.remove("show");

    const r = icon.getBoundingClientRect();
    const b = box.getBoundingClientRect();
    let top = r.top - b.height - 8;
    if (top < 8) top = r.bottom + 8;
    let left = r.left + r.width / 2 - b.width / 2;
    if (left < 8) left = 8;
    if (left + b.width > window.innerWidth - 8) left = window.innerWidth - b.width - 8;
    box.style.top = `${top}px`;
    box.style.left = `${left}px`;
    requestAnimationFrame(() => box.classList.add("show"));
  }

  function hide() {
    activeIcon = null;
    box.classList.remove("show");
    box.hidden = true;
  }

  document.addEventListener("pointerover", (e) => {
    const icon = e.target.closest(".tip-icon");
    if (icon) show(icon);
  });
  document.addEventListener("pointerout", (e) => {
    if (e.target.closest(".tip-icon")) hide();
  });
  document.addEventListener("click", (e) => {
    const icon = e.target.closest(".tip-icon");
    if (icon) {
      e.preventDefault();
      e.stopPropagation();
      if (activeIcon === icon) hide();
      else show(icon);
    } else if (activeIcon) {
      hide();
    }
  }, true);
  window.addEventListener("scroll", hide, true);
}

// ---------------------------------------------------------------- wiring
async function init() {
  setupTooltips();
  try {
    const savedTheme = localStorage.getItem("tamusicmaker.theme") || "dark";
    applyTheme(savedTheme);
    const c = await api("/api/config");
    if (c.language && I18N[c.language]) LANG = c.language;
    if (c.theme) applyTheme(c.theme);
  } catch {}
  restore();
  applyI18n();
  populateLangDropdown();
  try { S.defaults = await api("/api/defaults"); } catch (e) { toast(t("wfReadErr") + e.message, true); S.defaults = { brief: {}, export: {} }; }
  restore();
  applyI18n();
  refreshDocBadges();
  buildForm();
  document.querySelectorAll("#modeSeg button").forEach((b) => (b.onclick = () => setMode(b.dataset.mode)));
  document.querySelectorAll("#tabs button").forEach((b) => (b.onclick = () => showTab(b.dataset.tab)));

  // Auto / Manual document state buttons & typing detection
  document.querySelectorAll("[data-doc-auto]").forEach((b) => (b.onclick = () => setDocState(b.dataset.docAuto, "auto", true)));
  document.querySelectorAll("[data-doc-manual]").forEach((b) => (b.onclick = () => {
    const k = b.dataset.docManual;
    setDocState(k, "manual", false);
    $("#" + DOC_INPUTS[k])?.focus();
  }));
  for (const [k, id] of Object.entries(DOC_INPUTS)) {
    $("#" + id).addEventListener("input", () => {
      if (S.sheetState[k] !== "manual") S.sheetState[k] = "manual";
      refreshDocBadges(); updateLyricCount(); persist();
    });
  }
  document.querySelectorAll(".tag-btn").forEach((b) => (b.onclick = () => insertSectionTag(b.dataset.tag)));

  ["draftSeed", "draftSeedRandom", "planSeed", "planSeedRandom", "autoCount", "optCover", "optStems", "optRefine", "optVoiceSwap", "voicePitch", "voiceIndexRate", "expFlac", "expMp3", "expWav", "expSrt", "expSrtEn", "expSheet", "expSheetFormat", "expSheetSize", "expFolder",
    "mstEnabled", "mstEqMode", "mstEqPreset", "mstEqTarget", "mstEqStrength", "mstEqMaxGain", "mstEqMaxBands",
    "mstLoudTarget", "mstCustomLufs", "mstCustomCeiling", "mstCompression", "mstCompThreshold", "mstCompRatio", "mstCompKnee", "mstCompAttack", "mstCompRelease", "mstCompSidechain", "mstCompDetector", "mstSampleRate",
    "hqStereoEnabled", "hqStereoPreset", "hqStereoHighcut", "hqStereoCleanup", "hqStereoWarmth",
    "hqRegenEnabled", "hqRegenPreset", "hqRegenSteps", "hqRegenSeed", "hqRegenFromHz", "hqRegenNewShare", "hqRegenLevelMatch",
    "hqDereverbEnabled", "hqDereverbPreset", "hqDereverbAmount", "hqDereverbPhaseLock",
    "refEngine", "refModel", "refPreset", "refGain", "refCrossover", "refPreHz", "refPostHz", "refSeed"]
    .forEach((id) => $("#" + id)?.addEventListener("input", () => { updateMasteringUI(); updateLyricCount(); persist(); }));

  $("#optRefine")?.addEventListener("change", (e) => {
    if ($("#refEnabled")) $("#refEnabled").checked = e.target.checked;
    updateMasteringUI();
    persist();
  });
  $("#refEnabled")?.addEventListener("change", (e) => {
    if ($("#optRefine")) $("#optRefine").checked = e.target.checked;
    updateMasteringUI();
    persist();
  });
  $("#btnResetMastering")?.addEventListener("click", resetMasteringDefaults);
  updateMasteringUI();

  $("#optVoiceSwap")?.addEventListener("change", (e) => {
    $("#voiceSwapOptions").hidden = !e.target.checked;
    persist();
  });
  $("#btnStartVoiceSwap")?.addEventListener("click", (e) => {
    e.preventDefault();
    startVoiceSwapFromDialog();
  });
  $("#btnStartRenderVideo")?.addEventListener("click", (e) => {
    e.preventDefault();
    startVideoExport();
  });
  $("#dlgExportVideo")?.addEventListener("close", () => {
    stopVideoExportPlayback();
  });
  $("#btnCancelVideoDlg")?.addEventListener("click", () => {
    stopVideoExportPlayback();
    $("#dlgExportVideo")?.close();
  });
  loadVoiceModels();

  const base = () => ({ brief: S.brief, draft_seed: draftSeedValue(), plan_seed: planSeedValue(), options: collectOptions() });
  $("#btnDraft").onclick = () => startJob("/api/draft", base());
  $("#btnRender").onclick = () => { ensureVoice(); startJob("/api/render", { ...base(), mode: "review", sheet: sheetData(), sheet_states: { ...S.sheetState } }); };
  $("#btnAuto").onclick = () => { ensureVoice(); startJob("/api/render", { ...base(), mode: "auto", count: Number($("#autoCount").value) || 1, sheet: sheetData(), sheet_states: { ...S.sheetState } }); };
  $("#btnCancel").onclick = () => S.job && api("/api/cancel", { id: S.job.id });
  $("#btnSettings").onclick = openSettings;
  $("#cfgTheme").onchange = () => {
    const theme = $("#cfgTheme").value;
    applyTheme(theme);
    api("/api/config", { theme }).catch(() => {});
  };
  $("#cfgLang").onchange = () => {
    const lang = $("#cfgLang").value;
    setLanguage(lang);
    api("/api/config", { language: lang }).catch(() => {});
  };
  $("#cfgSave").onclick = async () => {
    const lang = $("#cfgLang").value;
    const theme = $("#cfgTheme").value;
    setLanguage(lang);
    applyTheme(theme);
    await api("/api/config", {
      language: lang,
      theme: theme,
      comfy_url: $("#cfgUrl").value.trim(),
      workflow: $("#cfgWorkflow").value.trim(),
      comfy_dir: $("#cfgDir").value.trim(),
      comfy_start_command: $("#cfgCmd").value.trim(),
      voice_models_dir: $("#cfgVoiceModelsDir").value.trim(),
    });
    S.options = {};
    refreshStatus();
    loadVoiceModels();
  };
  $("#btnStartComfy").onclick = async () => { try { await api("/api/comfy/start", {}); toast(t("comfyStarting")); } catch (e) { toast(e.message, true); } };
  loadHistory(); refreshStatus();
  setInterval(refreshStatus, 6000);
  setInterval(() => fetch("/api/ping").catch(() => {}), 5000); fetch("/api/ping");
}
init();
