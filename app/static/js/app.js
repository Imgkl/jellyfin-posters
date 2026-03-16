// ── Motion ──
// Exposed globally so carousel.js can use it too
const { animate } = Motion;
window.animate = animate;

// ── State ──
let movies = [];
let filteredMovies = [];
let currentIndex = 0;
let reviewedCount = 0;
let lastServerUrl = "";
let lastUsername = "";

const grids = {
  Primary: new ImageGrid("Primary"),
  Backdrop: new ImageGrid("Backdrop"),
  Logo: new ImageGrid("Logo"),
};

// ── DOM refs ──
const loginScreen = document.getElementById("login-screen");
const mainScreen = document.getElementById("main-screen");
const loginForm = document.getElementById("login-form");
const loginError = document.getElementById("login-error");
const movieListEl = document.getElementById("movie-list");
const movieTitle = document.getElementById("movie-title");
const progressCounter = document.getElementById("progress-counter");
const sidebarCount = document.getElementById("sidebar-count");
const searchInput = document.getElementById("search-input");
const loadingEl = document.getElementById("loading-indicator");
const btnApply = document.getElementById("btn-apply");
const btnSkip = document.getElementById("btn-skip");
const toastEl = document.getElementById("toast");

// ── Toast ──
let toastTimer = null;
function showToast(msg) {
  toastEl.textContent = msg;
  toastEl.classList.remove("hidden");
  toastEl.classList.add("show");
  clearTimeout(toastTimer);
  toastTimer = setTimeout(() => {
    toastEl.classList.remove("show");
    toastEl.classList.add("hidden");
  }, 2000);
}

// ── Login ──
loginForm.addEventListener("submit", async (e) => {
  e.preventDefault();
  loginError.textContent = "";
  const btn = document.getElementById("login-btn");
  btn.textContent = "connecting...";
  btn.disabled = true;

  try {
    const serverUrl = document.getElementById("server-url").value.trim();
    const username = document.getElementById("username").value.trim();
    const result = await api.post("/api/auth/login", {
      server_url: serverUrl,
      username: username,
      password: document.getElementById("password").value,
    });
    lastServerUrl = serverUrl;
    lastUsername = username;
    await loadMovies();
    loginScreen.classList.add("hidden");
    mainScreen.classList.remove("hidden");
    if (movies.length > 0) {
      navigateTo(firstUnreviewedIndex());
    }
  } catch (err) {
    loginError.textContent = err.message;
  } finally {
    btn.textContent = "login";
    btn.disabled = false;
  }
});

// ── Auto-login (env credentials) ──
async function autoLogin() {
  try {
    await api.post("/api/auth/login", { server_url: "", username: "", password: "" });
    await loadMovies();
    loginScreen.classList.add("hidden");
    mainScreen.classList.remove("hidden");
    if (movies.length > 0) navigateTo(firstUnreviewedIndex());
  } catch {
    // Credentials invalid, show login form
  }
}

// ── Load movies ──
async function loadMovies() {
  const data = await api.get("/api/movies");
  movies = data.items;
  filteredMovies = movies;
  reviewedCount = movies.filter((m) => m.reviewed).length;
  renderSidebar();
  updateProgress();
}

function firstUnreviewedIndex() {
  const idx = movies.findIndex((m) => !m.reviewed);
  return idx >= 0 ? idx : 0;
}

// ── Sidebar ──
function renderSidebar() {
  movieListEl.innerHTML = "";
  filteredMovies.forEach((m, i) => {
    const li = document.createElement("li");
    li.dataset.index = m.index;

    const dot = document.createElement("span");
    dot.className = `status-dot ${m.reviewed ? "reviewed" : "pending"}`;
    dot.textContent = m.reviewed ? "●" : "○";

    const name = document.createElement("span");
    name.className = "movie-name";
    name.textContent = m.name;

    const year = document.createElement("span");
    year.className = "movie-year";
    year.textContent = m.year || "";

    li.appendChild(dot);
    li.appendChild(name);
    li.appendChild(year);

    li.addEventListener("click", () => navigateTo(m.index));
    movieListEl.appendChild(li);
  });
  sidebarCount.textContent = `${reviewedCount}/${movies.length}`;
  highlightActive();
}

function highlightActive() {
  const items = movieListEl.querySelectorAll("li");
  items.forEach((li) => {
    li.classList.toggle("active", parseInt(li.dataset.index) === currentIndex);
  });
  // Scroll active into view
  const active = movieListEl.querySelector("li.active");
  if (active) {
    active.scrollIntoView({ block: "nearest" });
  }
}

function updateProgress() {
  progressCounter.textContent = `${reviewedCount}/${movies.length} reviewed`;
}

// ── Search ──
searchInput.addEventListener("input", () => {
  const q = searchInput.value.toLowerCase().trim();
  if (!q) {
    filteredMovies = movies;
  } else {
    filteredMovies = movies.filter(
      (m) =>
        m.name.toLowerCase().includes(q) ||
        (m.year && String(m.year).includes(q))
    );
  }
  renderSidebar();
});

// ── Navigate to movie ──
async function navigateTo(index) {
  if (index < 0 || index >= movies.length) return;
  currentIndex = index;
  const movie = movies[index];

  movieTitle.textContent = `${movie.name}${movie.year ? ` (${movie.year})` : ""}`;
  highlightActive();

  // Reset scroll positions
  document.querySelector(".content").scrollTop = 0;
  document.querySelectorAll(".thumb-grid").forEach((g) => (g.scrollTop = 0));

  // Show loading, fade out sections
  loadingEl.classList.remove("hidden");
  animate("#image-sections", { opacity: 0 }, { duration: 0.15 });

  // Load current images and remote images in parallel
  try {
    const [currentImages, remoteImages] = await Promise.all([
      api.get(`/api/movies/${movie.id}/images`),
      api.get(`/api/movies/${movie.id}/remote-images`),
    ]);

    // Set current images
    setCurrentImage("Primary", currentImages.Primary);
    setCurrentImage("Backdrop", currentImages.Backdrop);
    setCurrentImage("Logo", currentImages.Logo);

    // Load grids
    grids.Primary.load(remoteImages.Primary);
    grids.Backdrop.load(remoteImages.Backdrop);
    grids.Logo.load(remoteImages.Logo);
  } catch (err) {
    showToast("failed to load images: " + err.message);
  } finally {
    loadingEl.classList.add("hidden");
    animate("#image-sections", { opacity: [0, 1] }, { duration: 0.25 });
  }

  // Prefetch next movie's images
  if (index + 1 < movies.length) {
    api.post(`/api/movies/${movies[index + 1].id}/prefetch`, {}).catch(() => {});
  }
}

function setCurrentImage(type, info) {
  const img = document.getElementById(`current-${type}`);
  const noImg = img.parentElement.querySelector(".no-image");
  const metaEl = document.getElementById(`current-meta-${type}`);
  if (info && info.proxy_url) {
    img.src = info.proxy_url;
    img.style.display = "block";
    noImg.style.display = "none";
    animate(img, { opacity: [0, 1] }, { duration: 0.3 });
    img.onload = () => {
      if (img.naturalWidth && img.naturalHeight) {
        metaEl.textContent = `${img.naturalWidth} × ${img.naturalHeight}`;
      } else {
        metaEl.textContent = "";
      }
    };
  } else {
    img.src = "";
    img.style.display = "none";
    noImg.style.display = "block";
    metaEl.textContent = "";
  }
}


// ── Apply & Next ──
btnApply.addEventListener("click", applyAndNext);

async function applyAndNext() {
  const movie = movies[currentIndex];
  if (!movie) return;

  btnApply.disabled = true;
  btnApply.textContent = "applying...";

  let posterChanged = false;
  let backdropChanged = false;
  let logoChanged = false;

  try {
    const applyTasks = [];

    if (grids.Primary.hasSelection()) {
      applyTasks.push({ type: "Primary", url: grids.Primary.getSelection() });
    }
    if (grids.Backdrop.hasSelection()) {
      applyTasks.push({ type: "Backdrop", url: grids.Backdrop.getSelection() });
    }
    if (grids.Logo.hasSelection()) {
      applyTasks.push({ type: "Logo", url: grids.Logo.getSelection() });
    }

    if (applyTasks.length > 0) {
      const results = await Promise.allSettled(
        applyTasks.map((t) =>
          api.post(`/api/movies/${movie.id}/apply-image`, { type: t.type, url: t.url })
        )
      );

      const failed = [];
      results.forEach((r, i) => {
        if (r.status === "fulfilled") {
          if (applyTasks[i].type === "Primary") posterChanged = true;
          if (applyTasks[i].type === "Backdrop") backdropChanged = true;
          if (applyTasks[i].type === "Logo") logoChanged = true;
        } else {
          failed.push(applyTasks[i].type.toLowerCase());
        }
      });

      if (failed.length > 0) {
        showToast(`failed to apply: ${failed.join(", ")}`);
      }
    }

    // Mark reviewed (include applied URLs for export)
    await api.post(`/api/movies/${movie.id}/mark-reviewed`, {
      poster_changed: posterChanged,
      backdrop_changed: backdropChanged,
      logo_changed: logoChanged,
      poster_url: grids.Primary.hasSelection() ? grids.Primary.getSelection() : "",
      backdrop_url: grids.Backdrop.hasSelection() ? grids.Backdrop.getSelection() : "",
      logo_url: grids.Logo.hasSelection() ? grids.Logo.getSelection() : "",
    });

    // Update local state
    if (!movie.reviewed) {
      movie.reviewed = true;
      reviewedCount++;
      updateProgress();
      renderSidebar();
    }

    const changed = [
      posterChanged && "poster",
      backdropChanged && "backdrop",
      logoChanged && "logo",
    ].filter(Boolean);

    if (changed.length > 0) {
      showToast(`applied ${changed.join(", ")} — moving to next`);
    } else {
      showToast("marked as reviewed — moving to next");
    }

    // Go to next
    if (currentIndex + 1 < movies.length) {
      navigateTo(currentIndex + 1);
    }
  } catch (err) {
    showToast("error: " + err.message);
  } finally {
    btnApply.textContent = "apply & next";
    btnApply.disabled = false;
  }
}

// ── Skip ──
btnSkip.addEventListener("click", () => {
  if (currentIndex + 1 < movies.length) {
    navigateTo(currentIndex + 1);
  }
});

// ── Settings Modal ──
const settingsModal = document.getElementById("settings-modal");
const settingsForm = document.getElementById("settings-form");
const settingsError = document.getElementById("settings-error");
const btnSettings = document.getElementById("btn-settings");
const btnRefresh = document.getElementById("btn-refresh");

function openSettings() {
  document.getElementById("settings-url").value = lastServerUrl;
  document.getElementById("settings-username").value = lastUsername;
  document.getElementById("settings-password").value = "";
  settingsError.textContent = "";
  settingsModal.classList.remove("hidden");
}

function closeSettings() {
  settingsModal.classList.add("hidden");
}

btnSettings.addEventListener("click", openSettings);
document.getElementById("settings-close").addEventListener("click", closeSettings);
settingsModal.addEventListener("click", (e) => {
  if (e.target === settingsModal) closeSettings();
});

settingsForm.addEventListener("submit", async (e) => {
  e.preventDefault();
  settingsError.textContent = "";
  const submitBtn = settingsForm.querySelector('button[type="submit"]');
  submitBtn.textContent = "connecting...";
  submitBtn.disabled = true;

  try {
    const serverUrl = document.getElementById("settings-url").value.trim();
    const username = document.getElementById("settings-username").value.trim();
    await api.post("/api/auth/login", {
      server_url: serverUrl,
      username: username,
      password: document.getElementById("settings-password").value,
    });
    lastServerUrl = serverUrl;
    lastUsername = username;
    await loadMovies();
    if (movies.length > 0) navigateTo(firstUnreviewedIndex());
    closeSettings();
    showToast("reconnected — " + movies.length + " movies loaded");
  } catch (err) {
    settingsError.textContent = err.message;
  } finally {
    submitBtn.textContent = "reconnect";
    submitBtn.disabled = false;
  }
});

document.getElementById("settings-logout").addEventListener("click", async () => {
  try {
    await api.post("/api/auth/logout", {});
  } catch {}
  closeSettings();
  mainScreen.classList.add("hidden");
  loginScreen.classList.remove("hidden");
  movies = [];
  filteredMovies = [];
  reviewedCount = 0;
  showToast("logged out");
});

// ── Refresh ──
async function refreshMovies() {
  btnRefresh.disabled = true;
  btnRefresh.classList.add("loading");
  try {
    const result = await api.post("/api/library/refresh", {});
    await loadMovies();
    if (movies.length > 0) navigateTo(firstUnreviewedIndex());
    const parts = [result.total_movies + " movies"];
    if (result.stale_removed > 0) parts.push(result.stale_removed + " stale removed");
    showToast("refreshed — " + parts.join(", "));
  } catch (err) {
    showToast("refresh failed: " + err.message);
  } finally {
    btnRefresh.disabled = false;
    btnRefresh.classList.remove("loading");
  }
}

btnRefresh.addEventListener("click", refreshMovies);

// ── Cleanup Backdrops ──
const btnCleanup = document.getElementById("btn-cleanup-backdrops");
async function cleanupBackdrops() {
  btnCleanup.disabled = true;
  btnCleanup.classList.add("loading");
  try {
    const result = await api.post("/api/library/cleanup-backdrops", {});
    showToast(`cleaned up ${result.fixed} movies`);
  } catch (err) {
    showToast("cleanup failed: " + err.message);
  } finally {
    btnCleanup.disabled = false;
    btnCleanup.classList.remove("loading");
  }
}
btnCleanup.addEventListener("click", cleanupBackdrops);

// ── Import / Export ──
const btnExport = document.getElementById("btn-export");
btnExport.addEventListener("click", async () => {
  btnExport.disabled = true;
  btnExport.textContent = "exporting…";
  try {
    const data = await api.get("/api/data/export");
    const blob = new Blob([JSON.stringify(data, null, 2)], { type: "application/json" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    const date = new Date().toISOString().slice(0, 10);
    a.href = url;
    a.download = `jellyfin-progress-${date}.json`;
    a.click();
    URL.revokeObjectURL(url);
    showToast(`exported ${data.record_count} records`);
  } catch (err) {
    showToast("export failed: " + err.message);
  } finally {
    btnExport.disabled = false;
    btnExport.textContent = "export progress";
  }
});

const btnImport = document.getElementById("btn-import");
const importFileInput = document.getElementById("import-file");
btnImport.addEventListener("click", () => {
  importFileInput.click();
});

importFileInput.addEventListener("change", async () => {
  const file = importFileInput.files[0];
  if (!file) return;
  btnImport.disabled = true;
  btnImport.textContent = "importing…";
  try {
    const text = await file.text();
    const data = JSON.parse(text);
    const records = data.records || [];
    const result = await api.post("/api/data/import", { mode: "merge", records });
    showToast(`imported ${result.imported} records`);
    await loadMovies();
    if (movies.length > 0) navigateTo(firstUnreviewedIndex());
  } catch (err) {
    showToast("import failed: " + err.message);
  } finally {
    btnImport.disabled = false;
    btnImport.textContent = "import progress";
    importFileInput.value = "";
  }
});

// ── Fullscreen Preview ──
const previewOverlay = document.getElementById("preview-overlay");
const previewImg = document.getElementById("preview-img");
const previewMeta = document.getElementById("preview-meta");

function showPreview() {
  // Use the last-interacted grid, not the first with a selection
  const type = ImageGrid.lastActive;
  if (!type) return;
  const grid = grids[type];
  if (!grid || !grid.hasSelection()) return;

  const img = grid.images[grid.selectedIndex];
  previewImg.src = api.proxyUrl(img.url);
  const parts = [];
  if (img.provider) parts.push(img.provider);
  if (img.width && img.height) parts.push(`${img.width} \u00d7 ${img.height}`);
  if (img.language) parts.push(img.language);
  parts.push(`[${type.toLowerCase()}]`);
  previewMeta.textContent = parts.join(" \u00b7 ");
  previewOverlay.classList.remove("hidden");
  animate(previewOverlay, { opacity: [0, 1] }, { duration: 0.2 });
  animate(previewImg, { scale: [0.92, 1], opacity: [0, 1] }, { duration: 0.25 });
}

function hidePreview() {
  previewOverlay.classList.add("hidden");
  previewImg.src = "";
}

previewOverlay.addEventListener("click", hidePreview);

// ── Keyboard shortcuts ──
document.addEventListener("keydown", (e) => {
  // Close settings modal on escape
  if (!settingsModal.classList.contains("hidden")) {
    if (e.key === "Escape") {
      e.preventDefault();
      closeSettings();
    }
    return;
  }

  // Close preview on escape or space
  if (!previewOverlay.classList.contains("hidden")) {
    if (e.key === "Escape" || e.key === " ") {
      e.preventDefault();
      hidePreview();
    }
    return;
  }

  // Don't capture when typing in inputs
  if (e.target.tagName === "INPUT" || e.target.tagName === "TEXTAREA") {
    if (e.key === "Escape") {
      e.target.blur();
      e.preventDefault();
    }
    return;
  }

  switch (e.key) {
    case " ":
      e.preventDefault();
      showPreview();
      break;
    case "ArrowUp":
      e.preventDefault();
      if (currentIndex > 0) navigateTo(currentIndex - 1);
      break;
    case "ArrowDown":
      e.preventDefault();
      if (currentIndex + 1 < movies.length) navigateTo(currentIndex + 1);
      break;
    case "Enter":
      e.preventDefault();
      applyAndNext();
      break;
    case "s":
    case "S":
      e.preventDefault();
      if (currentIndex + 1 < movies.length) navigateTo(currentIndex + 1);
      break;
    case "/":
      e.preventDefault();
      searchInput.focus();
      break;
  }
});

// ── Check existing auth on load ──
(async () => {
  try {
    const status = await api.get("/api/auth/status");
    if (status.authenticated) {
      await loadMovies();
      loginScreen.classList.add("hidden");
      mainScreen.classList.remove("hidden");
      if (movies.length > 0) navigateTo(firstUnreviewedIndex());
    } else {
      // Auto-fill login form from server defaults
      if (status.default_server_url) {
        document.getElementById("server-url").value = status.default_server_url;
      }
      if (status.default_username) {
        document.getElementById("username").value = status.default_username;
      }
      // Auto-login if both username and password are configured on the server
      if (status.has_default_credentials) {
        await autoLogin();
      }
    }
  } catch {
    // Not authenticated, show login
  }
})();
