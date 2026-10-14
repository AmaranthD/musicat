import { initStage } from "./stage.js";

const audio = document.getElementById("audio");
const dropzone = document.getElementById("dropzone");
const trackList = document.getElementById("track-list");
const libraryEmpty = document.getElementById("library-empty");
const libraryCount = document.getElementById("library-count");
const searchInput = document.getElementById("search");
const sortSelect = document.getElementById("sort");
const unrecognized = document.getElementById("unrecognized");
const unrecognizedList = document.getElementById("unrecognized-list");
const progress = document.getElementById("progress");
const progressBar = document.getElementById("progress-bar");
const progressLabel = document.getElementById("progress-label");
const playerCover = document.getElementById("player-cover");
const playerTitle = document.getElementById("player-title");
const playerArtist = document.getElementById("player-artist");
const seek = document.getElementById("seek");
const waveform = document.getElementById("waveform");
const waveContext = waveform.getContext("2d");
const timeCurrent = document.getElementById("time-current");
const timeTotal = document.getElementById("time-total");
const playButton = document.getElementById("play");
const prevButton = document.getElementById("prev");
const nextButton = document.getElementById("next");
const volumeInput = document.getElementById("volume");
const shuffleButton = document.getElementById("shuffle");
const repeatButton = document.getElementById("repeat");
const queueList = document.getElementById("queue-list");
const queueEmpty = document.getElementById("queue-empty");
const playlistForm = document.getElementById("playlist-form");
const playlistName = document.getElementById("playlist-name");
const randomForm = document.getElementById("random-form");
const randomSize = document.getElementById("random-size");
const randomArtist = document.getElementById("random-artist");
const randomFormat = document.getElementById("random-format");
const playlistList = document.getElementById("playlist-list");
const playlistTarget = document.getElementById("playlist-target");
const playlistDetail = document.getElementById("playlist-detail");
const playlistDetailName = document.getElementById("playlist-detail-name");
const playlistTracks = document.getElementById("playlist-tracks");
const playlistPlay = document.getElementById("playlist-play");
const playlistRename = document.getElementById("playlist-rename");
const playlistDelete = document.getElementById("playlist-delete");

const state = {
  tracks: [],
  queue: [],
  baseQueue: [],
  currentIndex: -1,
  shuffle: false,
  repeat: "off",
  playlists: [],
  detail: null,
};

let dragDepth = 0;
let editingId = null;
let seeking = false;

let audioContext = null;
let sourceNode = null;

function ensureAudioGraph() {
  if (audioContext) return;
  audioContext = new AudioContext();
  sourceNode = audioContext.createMediaElementSource(audio);
  const analyser = audioContext.createAnalyser();
  analyser.fftSize = 1024;
  analyser.smoothingTimeConstant = 0.75;
  sourceNode.connect(analyser);
  analyser.connect(audioContext.destination);
  window.__musicatAudio = { audioContext, sourceNode, analyser };
}

function formatTime(seconds) {
  if (!seconds && seconds !== 0) return "--:--";
  const total = Math.round(seconds);
  const minutes = Math.floor(total / 60);
  const rest = String(total % 60).padStart(2, "0");
  return `${minutes}:${rest}`;
}

function coverStyle(track) {
  if (track.has_cover) {
    return `background-image: url('/api/tracks/${track.id}/cover'); background-size: cover;`;
  }
  const hue = [...(track.album || track.title || "musicat")].reduce(
    (acc, ch) => (acc * 31 + ch.charCodeAt(0)) % 360,
    7,
  );
  return `background: hsl(${hue} 60% 62%);`;
}

function currentTrack() {
  return state.queue[state.currentIndex] || null;
}

function playQueue(tracks, index) {
  if (!tracks.length) return;
  state.baseQueue = tracks.slice();
  state.queue = tracks.slice();
  state.currentIndex = index ?? 0;
  if (state.shuffle) applyShuffle(state.queue[state.currentIndex]);
  loadCurrent();
}

function loadCurrent() {
  const track = currentTrack();
  if (!track) return;
  ensureAudioGraph();
  if (audioContext.state === "suspended") audioContext.resume();
  audio.src = `/api/tracks/${track.id}/stream`;
  audio.play();
  renderPlayer();
  renderQueue();
  savePlayer();
}

function step(delta) {
  if (!state.queue.length) return;
  let next = state.currentIndex + delta;
  if (next < 0 || next >= state.queue.length) {
    if (state.repeat !== "all") return;
    next = (next + state.queue.length) % state.queue.length;
  }
  state.currentIndex = next;
  loadCurrent();
}

function shuffleArray(items) {
  for (let i = items.length - 1; i > 0; i -= 1) {
    const j = Math.floor(Math.random() * (i + 1));
    [items[i], items[j]] = [items[j], items[i]];
  }
  return items;
}

function applyShuffle(first) {
  const rest = state.queue.filter((track) => track.id !== first.id);
  shuffleArray(rest);
  state.queue = [first, ...rest];
  state.currentIndex = 0;
}

function toggleShuffle() {
  const track = currentTrack();
  state.shuffle = !state.shuffle;
  if (state.shuffle) {
    state.baseQueue = state.queue.length ? state.queue.slice() : state.baseQueue;
    if (track) applyShuffle(track);
  } else {
    state.queue = state.baseQueue.slice();
    state.currentIndex = track
      ? state.queue.findIndex((item) => item.id === track.id)
      : -1;
  }
  renderToggles();
  renderQueue();
}

function toggleRepeat() {
  const order = { off: "all", all: "one", one: "off" };
  state.repeat = order[state.repeat];
  renderToggles();
}

function renderToggles() {
  shuffleButton.classList.toggle("is-on", state.shuffle);
  repeatButton.classList.toggle("is-on", state.repeat !== "off");
  repeatButton.textContent = { off: "🔁", all: "🔁 tudo", one: "🔂 uma" }[state.repeat];
}

function onTrackEnded() {
  if (state.repeat === "one") {
    audio.currentTime = 0;
    audio.play();
    return;
  }
  if (state.currentIndex + 1 < state.queue.length) {
    step(1);
  } else if (state.repeat === "all" && state.queue.length) {
    state.currentIndex = 0;
    loadCurrent();
  }
}

function renderPlayer() {
  const track = currentTrack();
  playButton.textContent = audio.paused ? "▶" : "⏸";
  if (!track) {
    playerTitle.textContent = "Nada tocando";
    playerArtist.textContent = "—";
    playerCover.style = "";
    return;
  }
  playerCover.style = coverStyle(track);
  playerTitle.textContent = track.title || track.filename;
  playerArtist.textContent = [track.artist, track.album].filter(Boolean).join(" • ") || "—";
}

function renderQueue() {
  queueList.innerHTML = "";
  queueEmpty.hidden = state.queue.length > 0;
  state.queue.forEach((track, index) => {
    const item = document.createElement("li");
    item.className = "queue__item" + (index === state.currentIndex ? " is-current" : "");
    item.textContent = track.title || track.filename;
    item.addEventListener("click", () => {
      state.currentIndex = index;
      loadCurrent();
    });
    queueList.appendChild(item);
  });
}

function renderTracks(tracks) {
  trackList.innerHTML = "";
  libraryCount.textContent = tracks.length ? `${tracks.length}` : "";
  libraryEmpty.hidden = tracks.length > 0;

  for (const track of tracks) {
    const item = document.createElement("li");
    item.className = "track";
    item.dataset.id = track.id;

    if (editingId === track.id) {
      item.appendChild(editForm(track));
      trackList.appendChild(item);
      continue;
    }

    item.innerHTML = `
      <button class="track__play" title="Tocar" aria-label="Tocar">▶</button>
      <div class="track__cover" style="${coverStyle(track)}" aria-hidden="true"></div>
      <div class="track__info">
        <span class="track__title"></span>
        <span class="track__sub"></span>
      </div>
      <span class="track__duration"></span>
      <button class="track__add" title="Adicionar à playlist" aria-label="Adicionar à playlist">＋</button>
      <button class="track__edit" title="Editar metadados" aria-label="Editar">✎</button>
    `;
    item.querySelector(".track__title").textContent = track.title || track.filename;
    const sub = [track.artist, track.album].filter(Boolean).join(" • ");
    item.querySelector(".track__sub").textContent = sub || track.filename;
    item.querySelector(".track__duration").textContent = formatTime(track.duration);
    item.querySelector(".track__play").addEventListener("click", () =>
      playQueue(state.tracks, state.tracks.indexOf(track)),
    );
    item.querySelector(".track__add").addEventListener("click", () => addToPlaylist(track.id));
    item.querySelector(".track__edit").addEventListener("click", () => {
      editingId = track.id;
      renderTracks(tracks);
    });
    trackList.appendChild(item);
  }
}

function editForm(track) {
  const form = document.createElement("form");
  form.className = "track track--editing";
  form.innerHTML = `
    <div class="track__cover" style="${coverStyle(track)}" aria-hidden="true"></div>
    <div class="track__fields">
      <input name="title" placeholder="Título" />
      <input name="artist" placeholder="Artista" />
      <input name="album" placeholder="Álbum" />
    </div>
    <div class="track__actions">
      <button type="submit">Salvar</button>
      <button type="button" data-cancel>Cancelar</button>
    </div>
  `;
  form.elements.title.value = track.title || "";
  form.elements.artist.value = track.artist || "";
  form.elements.album.value = track.album || "";
  form.addEventListener("submit", async (event) => {
    event.preventDefault();
    const payload = {};
    for (const key of ["title", "artist", "album"]) payload[key] = form.elements[key].value;
    await fetch(`/api/tracks/${track.id}`, {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    editingId = null;
    loadLibrary();
  });
  form.querySelector("[data-cancel]").addEventListener("click", () => {
    editingId = null;
    loadLibrary();
  });
  return form;
}

function renderUnrecognized(items) {
  unrecognized.hidden = items.length === 0;
  unrecognizedList.innerHTML = "";
  for (const item of items) {
    const entry = document.createElement("li");
    entry.className = "unrecognized__item";
    const label = document.createElement("span");
    label.textContent = `${item.filename} — ${item.reason}`;
    const remove = document.createElement("button");
    remove.textContent = "Remover";
    remove.addEventListener("click", async () => {
      await fetch(`/api/unrecognized/${item.id}`, { method: "DELETE" });
      loadLibrary();
    });
    entry.append(label, remove);
    unrecognizedList.appendChild(entry);
  }
}

async function loadLibrary() {
  const params = new URLSearchParams({ search: searchInput.value, sort: sortSelect.value });
  const response = await fetch(`/api/library?${params}`);
  const data = await response.json();
  state.tracks = data.tracks;
  renderTracks(data.tracks);
  renderUnrecognized(data.unrecognized);
}

async function loadPlaylists() {
  const data = await (await fetch("/api/playlists")).json();
  state.playlists = data.playlists;
  renderPlaylists();
  renderTargetSelect();
  if (state.detail && !state.playlists.some((p) => p.id === state.detail.id)) {
    state.detail = null;
    renderDetail();
  }
}

function renderPlaylists() {
  playlistList.innerHTML = "";
  for (const playlist of state.playlists) {
    const item = document.createElement("li");
    item.className = "playlist-chip" + (state.detail?.id === playlist.id ? " is-current" : "");
    item.textContent = `${playlist.name} (${playlist.track_count})`;
    item.addEventListener("click", () => openPlaylist(playlist.id));
    playlistList.appendChild(item);
  }
}

function renderTargetSelect() {
  const previous = playlistTarget.value;
  playlistTarget.innerHTML = `<option value="">Adicionar a…</option>`;
  for (const playlist of state.playlists) {
    const option = document.createElement("option");
    option.value = String(playlist.id);
    option.textContent = playlist.name;
    playlistTarget.appendChild(option);
  }
  if (previous) playlistTarget.value = previous;
}

async function openPlaylist(id) {
  const response = await fetch(`/api/playlists/${id}`);
  if (!response.ok) return;
  state.detail = await response.json();
  renderDetail();
  renderPlaylists();
}

function renderDetail() {
  const detail = state.detail;
  playlistDetail.hidden = !detail;
  if (!detail) return;
  playlistDetailName.textContent = detail.name;
  playlistTracks.innerHTML = "";
  detail.tracks.forEach((track, index) => {
    const item = document.createElement("li");
    item.className = "playlist-track";
    item.draggable = true;
    const label = document.createElement("span");
    label.textContent = track.title || track.filename;
    label.addEventListener("click", () => playQueue(detail.tracks, index));
    const remove = document.createElement("button");
    remove.textContent = "✕";
    remove.addEventListener("click", async () => {
      await fetch(`/api/playlists/${detail.id}/tracks/${track.id}`, { method: "DELETE" });
      openPlaylist(detail.id);
      loadPlaylists();
    });

    item.addEventListener("dragstart", (event) => {
      event.dataTransfer.setData("text/plain", String(index));
      item.classList.add("is-dragging");
    });
    item.addEventListener("dragend", () => item.classList.remove("is-dragging"));
    item.addEventListener("dragover", (event) => event.preventDefault());
    item.addEventListener("drop", async (event) => {
      event.preventDefault();
      const from = Number(event.dataTransfer.getData("text/plain"));
      if (from === index) return;
      const ids = detail.tracks.map((entry) => entry.id);
      const [moved] = ids.splice(from, 1);
      ids.splice(index, 0, moved);
      await fetch(`/api/playlists/${detail.id}/tracks`, {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ track_ids: ids }),
      });
      openPlaylist(detail.id);
    });

    item.append(label, remove);
    playlistTracks.appendChild(item);
  });
}

async function addToPlaylist(trackId) {
  const targetId = playlistTarget.value;
  if (!targetId) return;
  await fetch(`/api/playlists/${targetId}/tracks`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ track_id: trackId }),
  });
  if (state.detail && String(state.detail.id) === targetId) openPlaylist(state.detail.id);
  loadPlaylists();
}

let saveTimer;
function savePlayer() {
  clearTimeout(saveTimer);
  saveTimer = setTimeout(() => {
    fetch("/api/player", {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      keepalive: true,
      body: JSON.stringify({
        queue: state.queue.map((track) => track.id),
        current_index: state.currentIndex,
        position: audio.currentTime || 0,
        volume: audio.volume,
      }),
    });
  }, 300);
}

async function restorePlayer() {
  const data = await (await fetch("/api/player")).json();
  const volume = data.volume ?? 1;
  volumeInput.value = String(volume);
  audio.volume = volume;
  if (!data.queue || !data.queue.length) return;
  state.baseQueue = data.queue.slice();
  state.queue = data.queue.slice();
  state.currentIndex = data.current_index ?? 0;
  const track = currentTrack();
  if (!track) return;
  audio.src = `/api/tracks/${track.id}/stream`;
  const position = data.position || 0;
  audio.addEventListener(
    "loadedmetadata",
    () => {
      audio.currentTime = position;
    },
    { once: true },
  );
  renderPlayer();
  renderQueue();
}

playlistForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  const name = playlistName.value.trim();
  if (!name) return;
  await fetch("/api/playlists", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ name }),
  });
  playlistName.value = "";
  loadPlaylists();
});

randomForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  const payload = {
    size: randomSize.value ? Number(randomSize.value) : null,
    artist: randomArtist.value.trim(),
    format: randomFormat.value,
  };
  const created = await (
    await fetch("/api/playlists/random", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    })
  ).json();
  randomSize.value = "";
  randomArtist.value = "";
  await loadPlaylists();
  openPlaylist(created.id);
});

playlistPlay.addEventListener("click", () => {
  if (state.detail) playQueue(state.detail.tracks, 0);
});

playlistRename.addEventListener("click", async () => {
  const name = prompt("Novo nome da playlist:", state.detail?.name || "");
  if (!name) return;
  await fetch(`/api/playlists/${state.detail.id}`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ name }),
  });
  openPlaylist(state.detail.id);
  loadPlaylists();
});

playlistDelete.addEventListener("click", async () => {
  if (!state.detail) return;
  await fetch(`/api/playlists/${state.detail.id}`, { method: "DELETE" });
  state.detail = null;
  renderDetail();
  loadPlaylists();
});

function uploadFiles(files) {
  if (!files.length) return;
  const form = new FormData();
  for (const file of files) form.append("files", file);

  const request = new XMLHttpRequest();
  request.open("POST", "/api/import");
  progress.hidden = false;
  progressBar.style.width = "0%";
  progressLabel.textContent = `Importando ${files.length} arquivo(s)…`;

  request.upload.addEventListener("progress", (event) => {
    if (event.lengthComputable) {
      progressBar.style.width = `${(event.loaded / event.total) * 100}%`;
    }
  });
  request.addEventListener("load", () => {
    progress.hidden = true;
    loadLibrary();
  });
  request.addEventListener("error", () => {
    progress.hidden = true;
    progressLabel.textContent = "Falha ao importar";
  });
  request.send(form);
}

function sizeWaveform() {
  waveform.width = waveform.clientWidth;
  waveform.height = waveform.clientHeight;
}

function drawWaveform() {
  const width = waveform.width;
  const height = waveform.height;
  waveContext.clearRect(0, 0, width, height);
  const graph = window.__musicatAudio;
  const accent =
    getComputedStyle(document.documentElement).getPropertyValue("--accent").trim() || "#ffb3d1";
  waveContext.fillStyle = accent;
  const bars = 48;
  const gap = 2;
  const barWidth = (width - gap * (bars - 1)) / bars;
  let data = null;
  if (graph && graph.analyser) {
    data = new Uint8Array(graph.analyser.frequencyBinCount);
    graph.analyser.getByteFrequencyData(data);
  }
  for (let i = 0; i < bars; i += 1) {
    let value = 0.06;
    if (data) {
      const idx = Math.floor((i / bars) * data.length * 0.6);
      value = data[idx] / 255;
    } else {
      value = 0.06 + 0.04 * Math.sin(i / 3 + performance.now() / 600);
    }
    const barHeight = Math.max(2, value * height);
    waveContext.globalAlpha = 0.5 + value * 0.5;
    waveContext.fillRect(i * (barWidth + gap), height - barHeight, barWidth, barHeight);
  }
  waveContext.globalAlpha = 1;
  requestAnimationFrame(drawWaveform);
}

playButton.addEventListener("click", () => {
  if (!currentTrack()) return;
  if (audio.paused) {
    ensureAudioGraph();
    if (audioContext.state === "suspended") audioContext.resume();
    audio.play();
  } else {
    audio.pause();
  }
});

prevButton.addEventListener("click", () => step(-1));
nextButton.addEventListener("click", () => step(1));
shuffleButton.addEventListener("click", toggleShuffle);
repeatButton.addEventListener("click", toggleRepeat);

audio.addEventListener("play", renderPlayer);
audio.addEventListener("pause", () => {
  renderPlayer();
  savePlayer();
});
audio.addEventListener("ended", onTrackEnded);
audio.addEventListener("loadedmetadata", () => {
  timeTotal.textContent = formatTime(audio.duration);
});
audio.addEventListener("timeupdate", () => {
  if (seeking) return;
  timeCurrent.textContent = formatTime(audio.currentTime);
  if (audio.duration) {
    seek.value = String(Math.round((audio.currentTime / audio.duration) * 1000));
  }
});

seek.addEventListener("input", () => {
  seeking = true;
  if (audio.duration) timeCurrent.textContent = formatTime((seek.value / 1000) * audio.duration);
});
seek.addEventListener("change", () => {
  if (audio.duration) audio.currentTime = (seek.value / 1000) * audio.duration;
  seeking = false;
  savePlayer();
});
volumeInput.addEventListener("input", () => {
  audio.volume = Number(volumeInput.value);
  savePlayer();
});

function showDropzone() {
  dropzone.hidden = false;
}
function hideDropzone() {
  dragDepth = 0;
  dropzone.hidden = true;
}

window.addEventListener("dragenter", (event) => {
  event.preventDefault();
  dragDepth += 1;
  showDropzone();
});
window.addEventListener("dragover", (event) => event.preventDefault());
window.addEventListener("dragleave", (event) => {
  event.preventDefault();
  dragDepth -= 1;
  if (dragDepth <= 0) hideDropzone();
});
window.addEventListener("drop", (event) => {
  event.preventDefault();
  hideDropzone();
  if (event.dataTransfer?.files?.length) uploadFiles(event.dataTransfer.files);
});

let searchTimer;
searchInput.addEventListener("input", () => {
  clearTimeout(searchTimer);
  searchTimer = setTimeout(loadLibrary, 200);
});
sortSelect.addEventListener("change", loadLibrary);

window.addEventListener("beforeunload", savePlayer);
window.addEventListener("resize", sizeWaveform);

renderToggles();
initStage();
sizeWaveform();
requestAnimationFrame(drawWaveform);
loadLibrary();
loadPlaylists();
restorePlayer();
