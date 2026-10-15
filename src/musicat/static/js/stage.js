const CATS = [
  { color: "orange_0", high: "running", idle: "sitting", bounce: 26, sway: 8, wag: 0.9 },
  { color: "grey_0", high: "walking", idle: "looking", bounce: 12, sway: 5, wag: 0.6 },
  { color: "calico_0", high: "running2", idle: "laying", bounce: 34, sway: 10, wag: 1.2 },
];
const ANIMS = ["sitting", "looking", "laying", "walking", "running", "running2"];
const DISPLAY = 120;

let meta = { cell: 40, colors: {} };
const strips = {};

function preload() {
  for (const cat of CATS) {
    strips[cat.color] = {};
    for (const anim of ANIMS) {
      const img = new Image();
      img.src = `/static/cats/${cat.color}_${anim}.png`;
      strips[cat.color][anim] = img;
    }
  }
}

export async function initStage() {
  const stage = document.getElementById("stage");
  if (!stage) return;

  try {
    meta = await (await fetch("/static/cats/cats.json")).json();
  } catch (error) {
    meta = { cell: 40, colors: {} };
  }
  preload();

  stage.innerHTML =
    `<canvas class="stage__canvas"></canvas>` +
    `<div class="cats">${CATS.map(() => `<div class="cat-wrapper"><div class="cat-sprite"></div></div>`).join("")}</div>`;

  const canvas = stage.querySelector(".stage__canvas");
  const context = canvas.getContext("2d");
  const wrappers = [...stage.querySelectorAll(".cat-wrapper")];
  const sprites = [...stage.querySelectorAll(".cat-sprite")];

  const cats = CATS.map((cat, index) => ({
    ...cat,
    el: sprites[index],
    wrapper: wrappers[index],
    anim: cat.idle,
    frame: 0,
    acc: 0,
    lastAnim: null,
  }));

  function resize() {
    canvas.width = stage.clientWidth;
    canvas.height = stage.clientHeight;
  }
  resize();
  window.addEventListener("resize", resize);

  const energy = { bass: 0, mid: 0, treble: 0, beat: false, level: 0 };
  let bassAverage = 0;
  let lastBeat = 0;
  let particles = [];

  function readAudio(now) {
    const graph = window.__musicatAudio;
    if (!graph || !graph.analyser) {
      const sway = (Math.sin(now / 900) + 1) / 2;
      Object.assign(energy, { bass: 0.05 * sway, mid: 0.05 * sway, treble: 0.04 * sway, beat: false, level: 0.06 });
      return;
    }
    const analyser = graph.analyser;
    const data = new Uint8Array(analyser.frequencyBinCount);
    analyser.getByteFrequencyData(data);
    const bins = data.length;
    const band = (start, end) => {
      let sum = 0;
      const from = Math.floor(bins * start);
      const to = Math.floor(bins * end);
      for (let i = from; i < to; i += 1) sum += data[i];
      return sum / ((to - from) * 255);
    };
    energy.bass = band(0, 0.12);
    energy.mid = band(0.12, 0.45);
    energy.treble = band(0.45, 1);
    energy.level = energy.bass * 0.55 + energy.mid * 0.3 + energy.treble * 0.15;

    bassAverage = bassAverage * 0.92 + energy.bass * 0.08;
    energy.beat =
      energy.bass > 0.22 && energy.bass > bassAverage * 1.35 && now - lastBeat > 170;
    if (energy.beat) lastBeat = now;
  }

  function pickAnim(cat) {
    if (energy.level > 0.5 || energy.beat) return cat.high;
    if (energy.level > 0.28) return cat.high === "walking" ? "running" : "walking";
    return cat.idle;
  }

  function setAnim(cat, anim) {
    if (cat.lastAnim === anim) return;
    const frames = meta.colors[cat.color]?.[anim] ?? 1;
    cat.el.style.backgroundImage = `url(${strips[cat.color][anim].src})`;
    cat.el.style.backgroundSize = `${frames * DISPLAY}px ${DISPLAY}px`;
    cat.anim = anim;
    cat.lastAnim = anim;
    cat.frame = 0;
    cat.acc = 0;
    cat.frames = frames;
  }

  function stepSprite(cat, dt) {
    const fps = 4 + energy.level * 16 + (energy.beat ? 6 : 0);
    cat.acc += dt;
    const frameTime = 1 / fps;
    while (cat.acc >= frameTime) {
      cat.acc -= frameTime;
      cat.frame = (cat.frame + 1) % cat.frames;
    }
    cat.el.style.backgroundPosition = `-${cat.frame * DISPLAY}px 0`;
  }

  function spawnParticles() {
    if (!energy.beat) return;
    const cx = canvas.width * (0.2 + Math.random() * 0.6);
    const cy = canvas.height * (0.2 + Math.random() * 0.3);
    for (let i = 0; i < 8; i += 1) {
      particles.push({
        x: cx,
        y: cy,
        vx: (Math.random() - 0.5) * 3,
        vy: -1 - Math.random() * 3,
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

  let last = performance.now();
  function animate(now) {
    const dt = Math.min((now - last) / 1000, 0.1);
    last = now;
    readAudio(now);
    spawnParticles();
    drawParticles();

    const beatBoost = energy.beat ? 1 : 0;
    cats.forEach((cat, index) => {
      setAnim(cat, pickAnim(cat));
      stepSprite(cat, dt);

      const phase = now / 300 + index * 2.1;
      const bounce = -(energy.bass * cat.bounce) - beatBoost * 14;
      const sway = Math.sin(phase) * energy.mid * cat.sway;
      const scale = 1 + beatBoost * 0.06;
      cat.wrapper.style.transform = `translateY(${bounce}px)`;
      cat.el.style.transform = `rotate(${sway}deg) scale(${scale})`;
    });

    requestAnimationFrame(animate);
  }

  requestAnimationFrame(animate);
}
