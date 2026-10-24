const DIRS = [
  "south",
  "south-east",
  "east",
  "north-east",
  "north",
  "north-west",
  "west",
  "south-west",
];

const CATS = [
  { color: "tuxedo_0", scale: 2, swayPair: [0, 1], spinStep: 1, phaseOffset: 0, seqOffset: 0 },
  { color: "dress_purple_0", scale: 2, swayPair: [0, 7], spinStep: -1, phaseOffset: 0.5, seqOffset: 2 },
  { color: "formal_kitten_0", scale: 2, swayPair: [0, 1], spinStep: -1, phaseOffset: 0.25, seqOffset: 1 },
];

const DANCE_FRAMES = 9;
const CLIP_BEATS = 6;
const MIN_BEAT_MS = 250;
const MAX_BEAT_MS = 1000;
const SPIN_ON = 0.38;
const SPIN_OFF = 0.26;

const VERSE_MOVES = ["sway", "step", "sway", "bob"];
const CHORUS_MOVES = ["spin", "step", "hop", "squash"];

const THEMES = { palco: "Palco", festa: "Festa", quintal: "Quintal" };
const THEME_KEY = "musicat:theme";
const AUTO_KEY = "musicat:auto";

function initialTheme() {
  const fromUrl = new URLSearchParams(window.location.search).get("theme");
  if (THEMES[fromUrl]) return fromUrl;
  try {
    const saved = localStorage.getItem(THEME_KEY);
    if (THEMES[saved]) return saved;
  } catch (error) {
    /* localStorage indisponível */
  }
  return "palco";
}

let meta = { cell: 84, colors: {} };
const strips = {};

function preload() {
  for (const cat of CATS) {
    strips[cat.color] = {};
    for (const dir of DIRS) {
      const img = new Image();
      img.src = `/static/cats/${cat.color}_dance_${dir}.png`;
      strips[cat.color][dir] = img;
    }
  }
}

function median(values) {
  const sorted = [...values].sort((a, b) => a - b);
  const middle = Math.floor(sorted.length / 2);
  return sorted.length % 2 ? sorted[middle] : (sorted[middle - 1] + sorted[middle]) / 2;
}

export async function initStage() {
  const stage = document.getElementById("stage");
  if (!stage) return;

  try {
    meta = await (await fetch("/static/cats/cats.json")).json();
  } catch (error) {
    meta = { cell: 84, colors: {} };
  }
  preload();

  stage.innerHTML =
    `<div class="stage__backdrop"></div>` +
    `<div class="stage__backdrop"></div>` +
    `<div class="stage__scrim"></div>` +
    `<canvas class="stage__canvas"></canvas>` +
    `<div class="cats">${CATS.map(() => `<div class="cat-wrapper"><div class="cat-sprite"></div></div>`).join("")}</div>` +
    `<div class="stage__themes"><button type="button" class="stage__theme stage__theme--auto">Auto</button>${Object.entries(THEMES)
      .map(([id, label]) => `<button type="button" class="stage__theme" data-theme="${id}">${label}</button>`)
      .join("")}</div>`;

  const backdrops = [...stage.querySelectorAll(".stage__backdrop")];
  const themeButtons = [...stage.querySelectorAll(".stage__theme[data-theme]")];
  const autoButton = stage.querySelector(".stage__theme--auto");
  const audio = document.getElementById("audio");

  let auto = readAuto();
  let activeBackdrop = 0;
  let currentTheme = null;
  let bag = [];
  let lastSwitchAt = 0;
  let lastReason = "inicial";

  function readAuto() {
    if (new URLSearchParams(window.location.search).has("theme")) return false;
    try {
      const saved = localStorage.getItem(AUTO_KEY);
      if (saved !== null) return saved === "1";
    } catch (error) {
      /* localStorage indisponível */
    }
    return true;
  }

  function saveAuto() {
    try {
      localStorage.setItem(AUTO_KEY, auto ? "1" : "0");
    } catch (error) {
      /* localStorage indisponível */
    }
  }

  function shuffle(list) {
    const copy = [...list];
    for (let i = copy.length - 1; i > 0; i -= 1) {
      const j = Math.floor(Math.random() * (i + 1));
      [copy[i], copy[j]] = [copy[j], copy[i]];
    }
    return copy;
  }

  function pickTheme() {
    if (!bag.length) bag = shuffle(Object.keys(THEMES));
    let id = bag.pop();
    if (id === currentTheme && bag.length) {
      bag.push(id);
      id = bag.pop();
    }
    return id;
  }

  function paintTheme(id, animate) {
    const next = backdrops[1 - activeBackdrop];
    next.style.transition = animate ? "opacity 700ms ease" : "none";
    next.style.backgroundImage = `url(/static/backgrounds/${id}.png)`;
    void next.offsetWidth;
    next.classList.add("is-visible");
    backdrops[activeBackdrop].classList.remove("is-visible");
    activeBackdrop = 1 - activeBackdrop;
    currentTheme = id;
  }

  function syncButtons() {
    for (const button of themeButtons) {
      button.classList.toggle("is-active", !auto && button.dataset.theme === currentTheme);
    }
    autoButton.classList.toggle("is-active", auto);
  }

  function changeTheme(reason) {
    paintTheme(pickTheme(), true);
    lastSwitchAt = performance.now();
    lastReason = reason;
    syncButtons();
  }

  function selectTheme(id) {
    auto = false;
    saveAuto();
    paintTheme(id, true);
    lastSwitchAt = performance.now();
    lastReason = "manual";
    syncButtons();
    try {
      localStorage.setItem(THEME_KEY, id);
    } catch (error) {
      /* localStorage indisponível */
    }
  }

  for (const button of themeButtons) {
    button.addEventListener("click", () => selectTheme(button.dataset.theme));
  }

  autoButton.addEventListener("click", () => {
    auto = !auto;
    saveAuto();
    if (auto) changeTheme("auto ligado");
    else syncButtons();
  });

  if (audio) {
    audio.addEventListener("loadedmetadata", () => {
      if (auto) changeTheme("faixa nova");
    });
  }

  paintTheme(initialTheme(), false);
  syncButtons();

  const canvas = stage.querySelector(".stage__canvas");
  const context = canvas.getContext("2d");
  const wrappers = [...stage.querySelectorAll(".cat-wrapper")];
  const sprites = [...stage.querySelectorAll(".cat-sprite")];

  const cats = CATS.map((cat, index) => {
    const cell = meta.colors?.[cat.color]?.cell ?? meta.cell ?? 84;
    const display = cell * cat.scale;
    const el = sprites[index];
    el.style.width = `${display}px`;
    el.style.height = `${display}px`;
    const layers = [document.createElement("div"), document.createElement("div")];
    for (const layer of layers) {
      layer.className = "cat-layer";
      el.appendChild(layer);
    }
    return {
      ...cat,
      cell,
      display,
      el,
      wrapper: wrappers[index],
      layers,
      activeLayer: 0,
      frame: 0,
      dir: null,
      dirIndex: 0,
      barIndex: null,
      moveIndex: -1,
      move: "sway",
      flip: false,
      cuts: 0,
    };
  });

  function resize() {
    canvas.width = stage.clientWidth;
    canvas.height = stage.clientHeight;
  }
  resize();
  window.addEventListener("resize", resize);

  const energy = { bass: 0, mid: 0, treble: 0, beat: false, level: 0, bpm: 0, hasBeat: false };
  let beatAnchor = 0;
  let beatInterval = 500;
  let lastBeatAt = 0;
  let levelSmooth = 0;
  let bassSmooth = 0;
  let pulse = 0;
  let spinning = false;
  let bassAverage = 0;
  const intervals = [];
  let frequencyData = null;
  let particles = [];

  function bandAverage(data, lowHz, highHz, nyquist) {
    const bins = data.length;
    const from = Math.max(1, Math.round((lowHz / nyquist) * bins));
    const to = Math.max(from + 1, Math.round((highHz / nyquist) * bins));
    let sum = 0;
    for (let i = from; i < to; i += 1) sum += data[i];
    return sum / ((to - from) * 255);
  }

  function readAudio(now) {
    const graph = window.__musicatAudio;
    if (!graph || !graph.analyser) {
      const sway = (Math.sin(now / 900) + 1) / 2;
      Object.assign(energy, { bass: 0.05 * sway, mid: 0.05 * sway, treble: 0.04 * sway, beat: false, hasBeat: false });
      levelSmooth = 0.06;
      return;
    }

    const analyser = graph.analyser;
    if (!frequencyData || frequencyData.length !== analyser.frequencyBinCount) {
      frequencyData = new Uint8Array(analyser.frequencyBinCount);
    }
    analyser.getByteFrequencyData(frequencyData);

    const nyquist = (graph.audioContext?.sampleRate ?? 48000) / 2;
    energy.bass = bandAverage(frequencyData, 30, 140, nyquist);
    energy.mid = bandAverage(frequencyData, 300, 2000, nyquist);
    energy.treble = bandAverage(frequencyData, 4000, 12000, nyquist);
    energy.level = energy.bass * 0.5 + energy.mid * 0.35 + energy.treble * 0.15;
    levelSmooth = levelSmooth * 0.9 + energy.level * 0.1;

    bassAverage = bassAverage * 0.92 + energy.bass * 0.08;
    const loud = energy.bass > bassAverage * 1.35 + 0.03;
    energy.beat = loud && now - lastBeatAt > MIN_BEAT_MS;

    if (energy.beat) {
      if (lastBeatAt > 0) {
        const delta = now - lastBeatAt;
        if (delta >= MIN_BEAT_MS && delta <= MAX_BEAT_MS) {
          intervals.push(delta);
          if (intervals.length > 12) intervals.shift();
          beatInterval = median(intervals);
        }
      }
      const predicted = beatAnchor + beatInterval;
      if (beatAnchor && Math.abs(now - predicted) < beatInterval * 0.5) {
        beatAnchor = predicted + (now - predicted) * 0.35;
      } else {
        beatAnchor = now;
      }
      lastBeatAt = now;
      energy.hasBeat = true;
    } else if (lastBeatAt && now - lastBeatAt > beatInterval * 3) {
      energy.hasBeat = false;
      beatAnchor = 0;
      intervals.length = 0;
    }

    energy.bpm = energy.hasBeat ? Math.round(60000 / beatInterval) : 0;
  }

  function setSprite(cat, dir, frame) {
    if (cat.dir !== dir) {
      const previous = cat.layers[cat.activeLayer];
      const next = cat.layers[1 - cat.activeLayer];
      next.style.backgroundImage = `url(${strips[cat.color][dir].src})`;
      next.style.backgroundSize = `${DANCE_FRAMES * cat.display}px ${cat.display}px`;
      next.style.backgroundPosition = `-${frame * cat.display}px 0`;
      next.classList.add("is-active");
      previous.classList.remove("is-active");
      cat.activeLayer = 1 - cat.activeLayer;
      cat.dir = dir;
      cat.frame = frame;
      return;
    }
    if (cat.frame !== frame) {
      const layer = cat.layers[cat.activeLayer];
      layer.style.backgroundPosition = `-${frame * cat.display}px 0`;
      cat.frame = frame;
    }
  }

  function applyMove(cat, t) {
    let x = 0;
    let y = 0;
    let tilt = 0;
    let sx = 1;
    let sy = 1;

    switch (cat.move) {
      case "hop": {
        const step = ((t * 3) % 1 + 1) % 1;
        const arc = Math.sin(Math.PI * step);
        const land = Math.max(0, 1 - step * 5);
        y = -arc * (10 + bassSmooth * 22);
        sy = 1 + arc * 0.05 - land * 0.07;
        sx = 1 - (sy - 1) * 0.8;
        break;
      }
      case "step": {
        const swing = Math.sin(t * Math.PI * 4);
        x = swing * 14;
        tilt = -swing * 4;
        sy = 1 - Math.abs(swing) * 0.03;
        sx = 1 + Math.abs(swing) * 0.03;
        break;
      }
      case "spin": {
        tilt = Math.sin(t * Math.PI * 2) * 5;
        y = -pulse * 6;
        sx = 1 + pulse * 0.03;
        sy = 1 + pulse * 0.03;
        break;
      }
      case "bob": {
        const bob = Math.abs(Math.sin(t * Math.PI * 6));
        y = -bob * 7;
        sy = 1 - bob * 0.02;
        break;
      }
      case "squash": {
        const q = ((t * 6) % 1 + 1) % 1;
        sy = 1 - 0.12 * (1 - q);
        sx = 1 + 0.10 * (1 - q);
        y = -pulse * 2;
        break;
      }
      case "sway":
      default: {
        const swing = Math.sin(t * Math.PI * 4);
        x = swing * 7;
        tilt = swing * 7;
        y = -pulse * 3;
        break;
      }
    }

    cat.wrapper.style.transform =
      `translate3d(${x.toFixed(2)}px, ${y.toFixed(2)}px, 0) rotate(${tilt.toFixed(2)}deg)`;
    const flip = cat.flip ? -1 : 1;
    cat.el.style.transform = `scale(${(sx * flip).toFixed(3)}, ${sy.toFixed(3)})`;
  }

  function updateDance(cat, now) {
    if (!energy.hasBeat) {
      const dir = DIRS[cat.swayPair[Math.floor(now / 1600) % 2]];
      const frame = Math.floor(now / 220) % DANCE_FRAMES;
      cat.barIndex = null;
      cat.move = "sway";
      setSprite(cat, dir, frame);
      applyMove(cat, now / 3000);
      return;
    }

    const position = (now - beatAnchor) / beatInterval + cat.phaseOffset;
    const barIndex = Math.floor(position / CLIP_BEATS);
    const barPosition = ((position % CLIP_BEATS) + CLIP_BEATS) % CLIP_BEATS;
    let frame = Math.min(DANCE_FRAMES - 1, Math.floor((barPosition / CLIP_BEATS) * DANCE_FRAMES));

    if (cat.barIndex !== barIndex) {
      if (cat.frame < DANCE_FRAMES - 1) cat.cuts += 1;
      cat.barIndex = barIndex;

      const sequence = spinning ? CHORUS_MOVES : VERSE_MOVES;
      cat.moveIndex += 1;
      cat.move = sequence[(cat.moveIndex + cat.seqOffset) % sequence.length];
      cat.flip = cat.move !== "spin" && (((barIndex % 4) + 4) % 4) >= 2;

      if (cat.move === "spin") {
        cat.dirIndex = (((cat.dirIndex + cat.spinStep) % 8) + 8) % 8;
      } else {
        cat.dirIndex = barIndex % 2 === 0 ? cat.swayPair[0] : cat.swayPair[1];
      }
    } else if (frame < cat.frame) {
      frame = cat.frame;
    }

    setSprite(cat, DIRS[((cat.dirIndex % 8) + 8) % 8], frame);
    applyMove(cat, barPosition / CLIP_BEATS);
  }

  function spawnParticles() {
    if (!energy.beat) return;
    const cx = canvas.width * (0.2 + Math.random() * 0.6);
    const cy = canvas.height * (0.2 + Math.random() * 0.3);
    for (let i = 0; i < 6; i += 1) {
      particles.push({
        x: cx,
        y: cy,
        vx: (Math.random() - 0.5) * 2.4,
        vy: -1 - Math.random() * 2.4,
        life: 1,
        color: ["#ffb3d1", "#b8e3ff", "#fff0b3"][Math.floor(Math.random() * 3)],
      });
    }
  }

  function drawParticles() {
    context.clearRect(0, 0, canvas.width, canvas.height);
    particles = particles.filter((p) => p.life > 0);
    for (const p of particles) {
      p.x += p.vx;
      p.y += p.vy;
      p.vy += 0.05;
      p.life -= 0.02;
      context.globalAlpha = Math.max(p.life, 0);
      context.fillStyle = p.color;
      context.beginPath();
      context.arc(p.x, p.y, 3 + p.life * 3, 0, Math.PI * 2);
      context.fill();
    }
    context.globalAlpha = 1;
  }

  let debug = null;
  if (new URLSearchParams(window.location.search).has("debug")) {
    debug = document.createElement("div");
    debug.style.cssText =
      "position:absolute;left:8px;top:8px;z-index:5;font:11px monospace;color:#fff;background:#0008;padding:4px 6px;border-radius:4px;white-space:pre;pointer-events:none";
    stage.appendChild(debug);
  }

  function animate(now) {
    readAudio(now);
    spawnParticles();
    drawParticles();

    const wasSpinning = spinning;
    if (levelSmooth > SPIN_ON) spinning = true;
    else if (levelSmooth < SPIN_OFF) spinning = false;

    if (auto && energy.hasBeat && wasSpinning !== spinning) {
      const dwell = Math.max(8000, 32 * beatInterval);
      if (now - lastSwitchAt > dwell) changeTheme(spinning ? "refrão" : "verso");
    }

    bassSmooth += (energy.bass - bassSmooth) * 0.18;
    pulse = Math.max(pulse * 0.88, energy.beat ? 1 : 0);

    cats.forEach((cat) => updateDance(cat, now));

    if (debug) {
      debug.textContent =
        `bpm ${energy.bpm}  beat ${energy.hasBeat ? "on" : "off"}  spin ${spinning ? "on" : "off"}\n` +
        `lvl ${levelSmooth.toFixed(2)}  bass ${energy.bass.toFixed(2)}\n` +
        `bar ${cats[0].barIndex ?? "-"}  dir ${DIRS[cats[0].dirIndex]}  frame ${cats[0].frame}\n` +
        `mov ${cats.map((cat) => `${cat.move}${cat.flip ? "*" : ""}`).join(" ")}\n` +
        `cortes ${cats.map((cat) => cat.cuts).join("/")}\n` +
        `tema ${currentTheme}  auto ${auto ? "on" : "off"}  ${lastReason}`;
    }

    requestAnimationFrame(animate);
  }

  requestAnimationFrame(animate);
}
