class ImageGrid {
  constructor(type) {
    this.type = type;
    this.images = [];
    this.selectedIndex = -1;
    this.loadGeneration = 0;
    this.pendingLoads = 0;
    this.loadStartedAt = 0;

    this.gridEl = document.getElementById(`grid-${type}`);
    this.counterEl = document.getElementById(`counter-${type}`);
    this.metaEl = document.getElementById(`meta-${type}`);
    this.noImageEl = this.gridEl.querySelector(".no-image-grid");
  }

  load(images) {
    this.loadGeneration += 1;
    this.loadStartedAt = performance.now();
    this.images = (images || []).slice().sort((a, b) => {
      const areaA = (a.width || 0) * (a.height || 0);
      const areaB = (b.width || 0) * (b.height || 0);
      return areaB - areaA;
    });
    this.selectedIndex = -1;
    this.pendingLoads = this.images.length;
    jpDiagnostics.log("grid.load.start", {
      type: this.type,
      generation: this.loadGeneration,
      image_count: this.images.length,
    });
    this.render();
  }

  cancelLoads(reason = "cancelled") {
    const cancelled = this.pendingLoads;
    this.loadGeneration += 1;
    this.gridEl.querySelectorAll(".thumb img").forEach((img) => {
      img.removeAttribute("src");
    });
    this.gridEl.querySelectorAll(".thumb").forEach((el) => el.remove());
    this.images = [];
    this.selectedIndex = -1;
    this.pendingLoads = 0;
    this.counterEl.textContent = "";
    this.metaEl.textContent = "";
    this.noImageEl.style.display = "block";
    jpDiagnostics.log("grid.load.cancelled", {
      type: this.type,
      generation: this.loadGeneration,
      cancelled,
      reason,
    });
  }

  render() {
    // Clear existing thumbnails (keep no-image placeholder)
    this.gridEl.querySelectorAll(".thumb").forEach((el) => el.remove());

    if (this.images.length === 0) {
      this.noImageEl.style.display = "block";
      this.counterEl.textContent = "";
      this.metaEl.textContent = "";
      jpDiagnostics.log("grid.load.complete", {
        type: this.type,
        generation: this.loadGeneration,
        image_count: 0,
        elapsed_ms: 0,
      });
      return;
    }

    this.noImageEl.style.display = "none";
    this.counterEl.textContent = `${this.images.length} available`;

    // Add expand/collapse toggle if there are enough images to overflow
    this.gridEl.classList.remove("expanded");
    const existingToggle = this.counterEl.parentElement.querySelector(".grid-toggle");
    if (existingToggle) existingToggle.remove();

    const toggle = document.createElement("button");
    toggle.className = "grid-toggle";
    toggle.textContent = "show all";
    toggle.addEventListener("click", () => {
      const expanded = this.gridEl.classList.toggle("expanded");
      toggle.textContent = expanded ? "collapse" : "show all";
    });
    this.counterEl.parentElement.appendChild(toggle);

    this.images.forEach((img, i) => {
      const thumb = document.createElement("div");
      thumb.className = "thumb";
      thumb.dataset.index = i;

      const imgEl = document.createElement("img");
      const thumbUrl = img.thumbnail_url || img.url;
      imgEl.alt = "";
      imgEl.loading = "lazy";

      const generation = this.loadGeneration;
      const imageStartedAt = performance.now();
      const settle = (outcome) => {
        const stale = generation !== this.loadGeneration;
        if (!stale) this.pendingLoads = Math.max(0, this.pendingLoads - 1);
        jpDiagnostics.log(`grid.image.${outcome}`, {
          type: this.type,
          generation,
          index: i,
          stale,
          pending: stale ? null : this.pendingLoads,
          elapsed_ms: Math.round((performance.now() - imageStartedAt) * 10) / 10,
          width: imgEl.naturalWidth || 0,
          height: imgEl.naturalHeight || 0,
        });
        if (!stale && this.pendingLoads === 0) {
          jpDiagnostics.log("grid.load.complete", {
            type: this.type,
            generation,
            image_count: this.images.length,
            elapsed_ms: Math.round((performance.now() - this.loadStartedAt) * 10) / 10,
          });
        }
      };
      imgEl.addEventListener("load", () => settle("loaded"), { once: true });
      imgEl.addEventListener("error", () => settle("error"), { once: true });
      imgEl.src = api.proxyUrl(thumbUrl);

      thumb.appendChild(imgEl);

      thumb.addEventListener("click", () => this.select(i));
      thumb.addEventListener("mouseenter", () => this.showMeta(i));
      thumb.addEventListener("mouseleave", () => this.showMeta(this.selectedIndex));

      this.gridEl.appendChild(thumb);

      animate(thumb, { opacity: [0, 1], scale: [0.85, 1] }, { delay: i * 0.03, duration: 0.3, ease: "easeOut" });
    });

    this.metaEl.textContent = "";
  }

  select(index) {
    if (index < 0 || index >= this.images.length) return;

    // Toggle off if clicking the already-selected thumbnail
    if (this.selectedIndex === index) {
      this.selectedIndex = -1;
      this.clearSelectionHighlight();
      this.metaEl.textContent = "";
      return;
    }

    this.selectedIndex = index;
    this.clearSelectionHighlight();

    const thumb = this.gridEl.querySelector(`.thumb[data-index="${index}"]`);
    if (thumb) {
      thumb.classList.add("selected");
      animate(thumb, { scale: [1, 1.06, 1] }, { duration: 0.2 });
    }

    // Track this as the last interacted grid for preview
    ImageGrid.lastActive = this.type;

    this.showMeta(index);
  }

  clearSelectionHighlight() {
    this.gridEl.querySelectorAll(".thumb.selected").forEach((el) => {
      el.classList.remove("selected");
    });
  }

  showMeta(index) {
    if (index < 0 || index >= this.images.length) {
      this.metaEl.textContent = "";
      return;
    }
    const img = this.images[index];
    const parts = [];
    if (img.provider) parts.push(img.provider);
    if (img.width && img.height) parts.push(`${img.width}×${img.height}`);
    if (img.language) parts.push(img.language);
    if (img.type === "Thumb") parts.push("[thumb]");
    this.metaEl.textContent = parts.join(" · ");
  }

  hasSelection() {
    return this.selectedIndex >= 0;
  }

  getSelection() {
    if (this.selectedIndex < 0) return null;
    return this.images[this.selectedIndex].url;
  }
}
