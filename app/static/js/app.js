/* BloomSight - app glue. */

(function () {
  const $ = function (id) { return document.getElementById(id); };
  const state = { dataURL: null, fileName: null, lastShares: null, stacking: null };
  const panels = Array.prototype.slice.call(document.querySelectorAll(".workflow-panel"));
  const panelButtons = Array.prototype.slice.call(document.querySelectorAll("[data-panel-target]"));
  const sidebar = $("sidebar");
  const sidebarToggle = $("sidebar-toggle");
  const sidebarFab = $("sidebar-fab");
  const MAX_SEED_VALUE = 1_000_000_000;
  const DOWNLOAD_DELAY_MS = 140; // Stagger downloads so browsers are less likely to block bursts.
  let activePanel = "input";

  function setSidebarCollapsed(collapsed) {
    sidebar.classList.toggle("is-collapsed", collapsed);
    if (sidebarFab) sidebarFab.hidden = !collapsed;
    const toggleLabel = sidebarToggle.querySelector(".sidebar-toggle-label");
    const toggleIcon = sidebarToggle.querySelector(".sidebar-toggle-icon");
    if (toggleLabel) toggleLabel.textContent = collapsed ? "Expand" : "Collapse";
    if (toggleIcon) toggleIcon.textContent = collapsed ? "▶" : "◀";
    sidebarToggle.setAttribute("aria-expanded", String(!collapsed));
  }

  function syncPanelButtons() {
    panelButtons.forEach(function (button) {
      const target = button.getAttribute("data-panel-target");
      const isActive = target === activePanel;
      button.classList.toggle("is-active", isActive);
      button.setAttribute("aria-selected", String(isActive));
    });
  }

  function setPanel(name) {
    activePanel = name;
    panels.forEach(function (panel) {
      panel.hidden = panel.getAttribute("data-panel") !== name;
    });
    syncPanelButtons();
  }

  panelButtons.forEach(function (button) {
    button.addEventListener("click", function () {
      const target = button.getAttribute("data-panel-target");
      if (!target || button.disabled) return;
      setPanel(target);
    });
  });

  sidebarToggle.addEventListener("click", function () {
    setSidebarCollapsed(!sidebar.classList.contains("is-collapsed"));
  });

  if (sidebarFab) {
    sidebarFab.addEventListener("click", function () {
      setSidebarCollapsed(false);
    });
  }

  /* ---- Date / footer ----------------------------------------------- */
  const fmt = new Intl.DateTimeFormat("en", {
    day: "2-digit", month: "long", year: "numeric"
  });
  $("folio-date").textContent = fmt.format(new Date());
  $("footer-year").textContent = new Date().getFullYear();

  /* ---- Method selector --------------------------------------------- */
  const methodEl = $("method");
  function syncMethod() {
    $("shares-field").hidden = methodEl.value !== "xor";
    updateRunMeta();
  }
  methodEl.addEventListener("change", syncMethod);
  syncMethod();

  const useSeedEl = $("use-seed");
  const seedEl = $("seed");
  function syncSeedField() {
    $("seed-field").hidden = !useSeedEl.checked;
    updateRunMeta();
  }
  useSeedEl.addEventListener("change", syncSeedField);
  syncSeedField();

  function readSeed() {
    if (!useSeedEl.checked) return null;
    if (seedEl.value.trim() === "") return null;
    const parsed = parseInt(seedEl.value, 10);
    return Number.isFinite(parsed) ? parsed : null;
  }

  function updateRunMeta(msg) {
    if (msg) {
      $("run-meta").textContent = msg;
      return;
    }
    if (!state.dataURL) {
      $("run-meta").textContent = "Choose an image to start. Tip: press Ctrl/Cmd + Enter to generate.";
      return;
    }
    if (useSeedEl.checked) {
      const seed = readSeed();
      if (seed === null) {
        $("run-meta").textContent = "Input ready: " + (state.fileName || "selected image") + ". Enter a numeric deterministic seed.";
        return;
      }
      $("run-meta").textContent = "Input ready: " + (state.fileName || "selected image") + ". Deterministic seed " + seed + " is active.";
      return;
    }
    $("run-meta").textContent = "Input ready: " + (state.fileName || "selected image") + ". Random seed is active.";
  }

  /* ---- Drop zone --------------------------------------------------- */
  const dz = $("dropzone"), fileInput = $("file"), preview = $("preview");
  function acceptFile(file) {
    if (!file || !file.type.startsWith("image/")) return;
    BS.api.fileToDataURL(file).then(function (url) {
      state.dataURL = url;
      state.fileName = file.name || "input-image";
      preview.src = url; preview.hidden = false;
      $("encrypt-btn").disabled = false;
      updateRunMeta();
    });
  }
  dz.addEventListener("dragover",  function (e) { e.preventDefault(); dz.classList.add("is-hover"); });
  dz.addEventListener("dragleave", function ()  { dz.classList.remove("is-hover"); });
  dz.addEventListener("drop", function (e) {
    e.preventDefault(); dz.classList.remove("is-hover");
    if (e.dataTransfer.files[0]) acceptFile(e.dataTransfer.files[0]);
  });
  fileInput.addEventListener("change", function (e) { acceptFile(e.target.files[0]); });
  function createSeedValue() {
    if (window.crypto && window.crypto.getRandomValues) {
      const buf = new Uint32Array(1);
      window.crypto.getRandomValues(buf);
      return String(buf[0]);
    }
    console.warn("crypto.getRandomValues unavailable; falling back to Math.random for seed generation.");
    return String(Math.floor(Math.random() * MAX_SEED_VALUE));
  }
  $("seed-random-btn").addEventListener("click", function () {
    seedEl.value = createSeedValue();
    useSeedEl.checked = true;
    syncSeedField();
  });
  seedEl.addEventListener("change", updateRunMeta);

  /* ---- Toast / errors ---------------------------------------------- */
  const toast = $("toast");
  function showToast(msg) {
    toast.textContent = msg; toast.classList.add("shown");
    setTimeout(function () { toast.classList.remove("shown"); }, 3200);
  }

  /* ---- Procedural specimen ornament -------------------------------- */
  function ornamentFor(seedStr) {
    let h = 0; for (let i = 0; i < seedStr.length; i++) h = (h * 31 + seedStr.charCodeAt(i)) >>> 0;
    function rng() { h = (h * 1664525 + 1013904223) >>> 0; return (h & 0xffff) / 0xffff; }
    let d = "M30 60 C30 50 30 40 30 10";
    for (let i = 0; i < 6; i++) {
      const y = 14 + i * 7, side = i % 2 === 0 ? -1 : 1;
      const len = 12 + rng() * 8;
      d += " M30 " + y + " q " + (side * len * 0.5) + " " + (-3 - rng() * 4)
        + " " + (side * len) + " " + (-1 - rng() * 4);
    }
    return '<svg class="ornament-svg" viewBox="0 0 60 70" aria-hidden="true">'
         + '<path d="' + d + '" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"/>'
         + '</svg>';
  }

  /* ---- Render specimens -------------------------------------------- */
  function renderSpecimens(payload) {
    const host = $("specimens"); host.innerHTML = "";
    const today = fmt.format(new Date());
    payload.shares.forEach(function (sh, i) {
      const card = document.createElement("article");
      card.className = "specimen mounted";
      card.style.animationDelay = (i * 0.18) + "s";
      const title = "Share " + (i + 1) + " / " + payload.shares.length;
      card.innerHTML =
        '<span class="pin tl"></span><span class="pin tr"></span>' +
        '<span class="pin bl"></span><span class="pin br"></span>' +
        '<div class="frame"><img alt="Share ' + (i + 1) + '" src="' + sh.image + '"/></div>' +
        '<div class="label">' +
        '  <div><span class="latin">' + title + '</span><br/>Method: ' + payload.method + '</div>' +
        '  <div class="meta">' + sh.width + ' &times; ' + sh.height + ' px<br/>' + today + '<br/>themed: ' + payload.themed + '</div>' +
        '  <div class="specimen-actions">' +
        '    <a class="btn ghost" href="' + sh.image + '" download="share-' + (i + 1) + '-themed.png">Download themed</a>' +
        '    <a class="btn ghost" href="' + sh.raw + '" download="share-' + (i + 1) + '-raw.png">Download raw</a>' +
        "  </div>" +
        '</div>' + ornamentFor(sh.image.slice(-32) + i);
      host.appendChild(card);
    });
    $("download-all-btn").disabled = payload.shares.length === 0;
    panelButtons.forEach(function (button) {
      if (button.getAttribute("data-panel-target") === "shares") button.disabled = false;
      if (button.getAttribute("data-panel-target") === "reveal") button.disabled = false;
    });
  }

  $("download-all-btn").addEventListener("click", function () {
    if (!state.lastShares || !state.lastShares.shares) return;
    const files = [];
    state.lastShares.shares.forEach(function (share, index) {
      files.push({ href: share.image, name: "share-" + (index + 1) + "-themed.png" });
      files.push({ href: share.raw, name: "share-" + (index + 1) + "-raw.png" });
    });
    files.forEach(function (file, idx) {
      setTimeout(function () {
        const link = document.createElement("a");
        link.href = file.href;
        link.download = file.name;
        document.body.appendChild(link);
        link.click();
        link.remove();
      }, idx * DOWNLOAD_DELAY_MS);
    });
    showToast("Downloading themed and raw versions of all shares.");
  });

  /* ---- Mount the stacking plate (Naor-Shamir only) ----------------- */
  async function mountPlate(payload) {
    const plate = $("plate");
    if (payload.method !== "naor-shamir") { plate.hidden = true; return; }
    plate.hidden = false;
    if (state.stacking) state.stacking.destroy();

    const baseImg = await BS.api.loadImage(payload.shares[0].image);
    const dragImg = await BS.api.loadImage(payload.shares[1].image);
    state.stacking = BS.stacking.setup({
      stage: $("stage"),
      baseCanvas: $("base-canvas"),
      revealCanvas: $("reveal-canvas"),
      draggable: $("draggable"),
      dragCanvas: $("drag-canvas"),
      baseImage: baseImg, dragImage: dragImg,
      onSnap: function () { showRecovered(payload); },
    });
  }

  async function showRecovered(payload) {
    try {
      setPanel("reveal");
      const res = await BS.api.decrypt({
        method: payload.method,
        shares: payload.shares.map(function (s) { return s.image; }),
        downsample: $("downsample").checked,
      });
      $("reveal-img").src = res.image;
      $("download-link").href = res.image;
      $("reveal-card").classList.add("shown");
      $("plate-instructions").textContent = "Shares aligned. Image recovered.";
    } catch (e) { showToast(e.message); }
  }

  /* ---- Encrypt button --------------------------------------------- */
  $("encrypt-btn").addEventListener("click", async function () {
    if (!state.dataURL) return;
    const vine = $("vine");
    vine.classList.remove("is-growing"); void vine.offsetWidth; vine.classList.add("is-growing");
    $("encrypt-btn").disabled = true;
    try {
      const seed = readSeed();
      if (useSeedEl.checked && seed === null) {
        throw new Error("Please enter a numeric seed value.");
      }
      const payload = await BS.api.encrypt({
        image: state.dataURL,
        method: methodEl.value,
        n_shares: parseInt($("shares").value, 10) || 2,
        themed: $("themed").checked,
        seed: seed,
      });
      state.lastShares = payload;
      renderSpecimens(payload);
      setPanel("shares");
      $("reveal-card").classList.remove("shown");
      await mountPlate(payload);
      if (payload.method === "xor") showRecovered(payload);
      updateRunMeta("Generated " + payload.shares.length + " share(s).");
    } catch (e) {
      showToast(e.message);
      updateRunMeta("Could not generate shares: " + e.message);
    } finally {
      $("encrypt-btn").disabled = false;
    }
  });

  /* ---- Reset ------------------------------------------------------- */
  $("reset-btn").addEventListener("click", function () {
    state.dataURL = null; state.fileName = null; state.lastShares = null;
    preview.hidden = true; preview.src = ""; fileInput.value = "";
    $("specimens").innerHTML = "";
    $("plate").hidden = true;
    $("reveal-card").classList.remove("shown");
    $("encrypt-btn").disabled = true;
    $("download-all-btn").disabled = true;
    useSeedEl.checked = false;
    seedEl.value = "";
    syncSeedField();
    panelButtons.forEach(function (button) {
      const target = button.getAttribute("data-panel-target");
      button.disabled = target !== "input";
    });
    setPanel("input");
    updateRunMeta();
  });

  document.addEventListener("keydown", function (event) {
    if ((event.ctrlKey || event.metaKey) && event.key === "Enter" && !$("encrypt-btn").disabled) {
      event.preventDefault();
      $("encrypt-btn").click();
    }
  });

  setPanel("input");
  setSidebarCollapsed(false);
  updateRunMeta();
})();
