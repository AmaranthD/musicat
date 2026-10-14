const dropzone = document.getElementById("dropzone");
const trackList = document.getElementById("track-list");
const libraryEmpty = document.getElementById("library-empty");
const libraryCount = document.getElementById("library-count");
const unrecognized = document.getElementById("unrecognized");
const unrecognizedList = document.getElementById("unrecognized-list");
const progress = document.getElementById("progress");
const progressBar = document.getElementById("progress-bar");
const progressLabel = document.getElementById("progress-label");

let dragDepth = 0;

function formatDuration(seconds) {
  if (!seconds && seconds !== 0) return "--:--";
  const total = Math.round(seconds);
  const minutes = Math.floor(total / 60);
  const rest = String(total % 60).padStart(2, "0");
  return `${minutes}:${rest}`;
}

function renderTracks(tracks) {
  trackList.innerHTML = "";
  libraryCount.textContent = tracks.length ? `${tracks.length}` : "";
  libraryEmpty.hidden = tracks.length > 0;

  for (const track of tracks) {
    const item = document.createElement("li");
    item.className = "track";
    item.innerHTML = `
      <div class="track__cover" aria-hidden="true"></div>
      <div class="track__info">
        <span class="track__title"></span>
        <span class="track__sub"></span>
      </div>
      <span class="track__duration"></span>
    `;
    item.querySelector(".track__title").textContent = track.title || track.filename;
    const sub = [track.artist, track.album].filter(Boolean).join(" • ");
    item.querySelector(".track__sub").textContent = sub || track.filename;
    item.querySelector(".track__duration").textContent = formatDuration(track.duration);
    trackList.appendChild(item);
  }
}

function renderUnrecognized(items) {
  unrecognized.hidden = items.length === 0;
  unrecognizedList.innerHTML = "";
  for (const item of items) {
    const entry = document.createElement("li");
    entry.className = "unrecognized__item";
    entry.textContent = `${item.filename} — ${item.reason}`;
    unrecognizedList.appendChild(entry);
  }
}

async function loadLibrary() {
  const response = await fetch("/api/library");
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

loadLibrary();
