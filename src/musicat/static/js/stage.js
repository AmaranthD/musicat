const CAT_COLORS = ["#ffb3d1", "#b8e3ff", "#fff0b3"];
const CAT_NAMES = ["Rebolado", "Cabeçinha", "Pulinho"];

function catSvg(color, index) {
  return `
    <div class="cat-wrapper" data-index="${index}">
      <svg class="cat" viewBox="0 0 120 140" role="img" aria-label="Gatinho ${CAT_NAMES[index]}">
        <g class="cat__tail">
          <path d="M92 118 q30 -10 20 -46" fill="none" stroke="${color}"
                stroke-width="10" stroke-linecap="round" />
        </g>
        <g class="cat__body">
          <ellipse class="cat__torso" cx="60" cy="104" rx="34" ry="32" fill="${color}" />
          <g class="cat__head">
            <polygon points="40,52 32,24 56,42" fill="${color}" />
            <polygon points="80,52 88,24 64,42" fill="${color}" />
            <polygon points="43,48 38,31 54,43" fill="#3a2b44" />
            <polygon points="77,48 82,31 66,43" fill="#3a2b44" />
            <circle cx="60" cy="68" r="30" fill="${color}" />
            <circle class="cat__eye" cx="50" cy="64" r="5" fill="#2a1c28" />
            <circle class="cat__eye" cx="70" cy="64" r="5" fill="#2a1c28" />
            <path d="M60 74 q-6 6 -12 2 M60 74 q6 6 12 2" fill="none"
                  stroke="#2a1c28" stroke-width="2.4" stroke-linecap="round" />
            <path d="M60 76 v6" stroke="#2a1c28" stroke-width="2.4" stroke-linecap="round" />
          </g>
        </g>
      </svg>
    </div>
  `;
}

export function initStage() {
  const stage = document.getElementById("stage");
  if (!stage) return;

  stage.innerHTML =
    `<canvas class="stage__canvas"></canvas>` +
    `<div class="cats">${CAT_COLORS.map(catSvg).join("")}</div>`;

  const canvas = stage.querySelector(".stage__canvas");
  const context = canvas.getContext("2d");
  const wrappers = [...stage.querySelectorAll(".cat-wrapper")];
  let particles = [];

  function resize() {
    canvas.width = stage.clientWidth;
    canvas.height = stage.clientHeight;
  }
  resize();
  window.addEventListener("resize", resize);

  const analyserData = { bass: 0, mid: 0, treble: 0, beat: false };
  let bassAverage = 0;
  let lastBeat = 0;

  function readAudio(now) {
    const graph = window.__musicatAudio;
    if (!graph || !graph.analyser) {
      const sway = (Math.sin(now / 900) + 1) / 2;
      Object.assign(analyserData, { bass: 0.05 * sway, mid: 0.05 * sway, treble: 0.04 * sway, beat: false });
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

    analyserData.bass = band(0, 0.12);
    analyserData.mid = band(0.12, 0.45);
    analyserData.treble = band(0.45, 1);

    bassAverage = bassAverage * 0.92 + analyserData.bass * 0.08;
    analyserData.beat =
      analyserData.bass > 0.22 &&
      analyserData.bass > bassAverage * 1.35 &&
      now - lastBeat > 180;
    if (analyserData.beat) lastBeat = now;
  }

  function spawnParticles() {
    if (!analyserData.beat) return;
    const cx = canvas.width * (0.2 + Math.random() * 0.6);
    const cy = canvas.height * (0.2 + Math.random() * 0.3);
    for (let i = 0; i < 8; i += 1) {
      particles.push({
        x: cx,
        y: cy,
        vx: (Math.random() - 0.5) * 3,
        vy: -1 - Math.random() * 3,
        life: 1,
        color: CAT_COLORS[Math.floor(Math.random() * CAT_COLORS.length)],
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

  const personalities = [
    { bounce: 26, body: 10, head: 4, tail: 12 },
    { bounce: 10, body: 4, head: 16, tail: 6 },
    { bounce: 40, body: 6, head: 8, tail: 20 },
  ];

  function animate(now) {
    readAudio(now);
    spawnParticles();
    drawParticles();

    const beatBoost = analyserData.beat ? 1 : 0;
    wrappers.forEach((wrapper, index) => {
      const p = personalities[index];
      const phase = now / 300 + index;
      const bounce = -(analyserData.bass * p.bounce) - beatBoost * 12;
      const sway = Math.sin(phase) * analyserData.mid * p.body;
      const headTilt = Math.sin(phase * 1.4) * (analyserData.treble * p.head + beatBoost * 6);
      const tailWag = Math.sin(phase * 2.2) * (analyserData.mid * p.tail + beatBoost * 8);

      wrapper.style.transform = `translateY(${bounce}px)`;
      wrapper.querySelector(".cat__body").style.transform = `rotate(${sway}deg)`;
      wrapper.querySelector(".cat__head").style.transform = `rotate(${headTilt}deg)`;
      wrapper.querySelector(".cat__tail").style.transform = `rotate(${tailWag}deg)`;
    });

    requestAnimationFrame(animate);
  }

  requestAnimationFrame(animate);
}
