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

let dragDepth = 0;
let editingId = null;

function formatDuration(seconds) {
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
      <div class="track__cover" style="${coverStyle(track)}" aria-hidden="true"></div>
      <div class="track__info">
        <span class="track__title"></span>
        <span class="track__sub"></span>
      </div>
      <span class="track__duration"></span>
      <button class="track__edit" title="Editar metadados" aria-label="Editar">✎</button>
    `;
    item.querySelector(".track__title").textContent = track.title || track.filename;
    const sub = [track.artist, track.album].filter(Boolean).join(" • ");
    item.querySelector(".track__sub").textContent = sub || track.filename;
    item.querySelector(".track__duration").textContent = formatDuration(track.duration);
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
    for (const key of ["title", "artist", "album"]) {
      payload[key] = form.elements[key].value;
    }
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
  const params = new URLSearchParams({
    search: searchInput.value,
    sort: sortSelect.value,
  });
  const response = await fetch(`/api/library?${params}`);
  const data = await response.json();
  renderTracks(data.tracks);
  renderUnrecognized(data.unrecognized);
}

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

window.addEventListener("dragover", (event) => {
  event.preventDefault();
});

window.addEventListener("dragleave", (event) => {
  event.preventDefault();
  dragDepth -= 1;
  if (dragDepth <= 0) hideDropzone();
});

window.addEventListener("drop", (event) => {
  event.preventDefault();
  hideDropzone();
  if (event.dataTransfer?.files?.length) {
    uploadFiles(event.dataTransfer.files);
  }
});

let searchTimer;
searchInput.addEventListener("input", () => {
  clearTimeout(searchTimer);
  searchTimer = setTimeout(loadLibrary, 200);
});

sortSelect.addEventListener("change", loadLibrary);

loadLibrary();
