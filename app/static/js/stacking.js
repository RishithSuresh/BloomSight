/* Drag-to-stack visual cryptography reveal.
 *
 * The "base" canvas holds share 1. The "drag" canvas (positioned
 * absolutely inside the stage and movable) holds share 2. As share 2
 * overlaps share 1 we compute the per-pixel min of the two RGB(A)
 * buffers in the overlap rect and paint it onto the "reveal" canvas
 * pinned over the base. When the overlap is near-perfect we snap the
 * draggable into place and dispatch a `bs:revealed` event.
 */

window.BS = window.BS || {};

BS.stacking = (function () {
  const SNAP_PX = 14;

  function setup(opts) {
    const stage   = opts.stage;
    const base    = opts.baseCanvas;
    const reveal  = opts.revealCanvas;
    const dragEl  = opts.draggable;
    const dragCv  = opts.dragCanvas;
    const baseImg = opts.baseImage;
    const dragImg = opts.dragImage;
    const onSnap  = opts.onSnap || function () {};

    const w = baseImg.naturalWidth, h = baseImg.naturalHeight;
    base.width = reveal.width = dragCv.width = w;
    base.height = reveal.height = dragCv.height = h;
    stage.style.width  = (w + 240) + "px";
    stage.style.height = (h + 60) + "px";

    const bctx = base.getContext("2d", { willReadFrequently: true });
    const dctx = dragCv.getContext("2d", { willReadFrequently: true });
    const rctx = reveal.getContext("2d", { willReadFrequently: true });
    bctx.drawImage(baseImg, 0, 0);
    dctx.drawImage(dragImg, 0, 0);

    const baseData = bctx.getImageData(0, 0, w, h).data;
    const dragData = dctx.getImageData(0, 0, w, h).data;

    // Start the draggable to the right of the base.
    dragEl.style.left = (w + 60) + "px";
    dragEl.style.top  = "30px";
    reveal.style.left = "0px";
    reveal.style.top  = "0px";

    let dragging = false, snapped = false;
    let startX = 0, startY = 0, originLeft = 0, originTop = 0;

    function paintOverlap() {
      const rect = stage.getBoundingClientRect();
      const baseRect   = base.getBoundingClientRect();
      const dragRect   = dragCv.getBoundingClientRect();
      const dx = Math.round(dragRect.left - baseRect.left);
      const dy = Math.round(dragRect.top  - baseRect.top);

      // Clear reveal canvas
      rctx.clearRect(0, 0, w, h);
      const x0 = Math.max(0, dx),       y0 = Math.max(0, dy);
      const x1 = Math.min(w, dx + w),   y1 = Math.min(h, dy + h);
      if (x1 <= x0 || y1 <= y0) return;

      const ow = x1 - x0, oh = y1 - y0;
      const out = rctx.createImageData(ow, oh);
      const od  = out.data;
      for (let yy = 0; yy < oh; yy++) {
        for (let xx = 0; xx < ow; xx++) {
          const bi = ((y0 + yy) * w + (x0 + xx)) * 4;
          const di = ((y0 + yy - dy) * w + (x0 + xx - dx)) * 4;
          const oi = (yy * ow + xx) * 4;
          od[oi  ] = Math.min(baseData[bi  ], dragData[di  ]);
          od[oi+1] = Math.min(baseData[bi+1], dragData[di+1]);
          od[oi+2] = Math.min(baseData[bi+2], dragData[di+2]);
          od[oi+3] = 255;
        }
      }
      rctx.putImageData(out, x0, y0);

      // Snap detection.
      if (!snapped && Math.abs(dx) < SNAP_PX && Math.abs(dy) < SNAP_PX) {
        snapped = true;
        dragEl.classList.add("snapped");
        const baseLeft = base.offsetLeft;
        const baseTop  = base.offsetTop;
        dragEl.style.left = baseLeft + "px";
        dragEl.style.top  = baseTop  + "px";
        setTimeout(function () {
          rctx.clearRect(0, 0, w, h);
          rctx.fillStyle = "#fff";
          rctx.fillRect(0, 0, w, h);
          // Final composite for the snapped state.
          const out = rctx.createImageData(w, h);
          const od  = out.data;
          for (let i = 0; i < baseData.length; i += 4) {
            od[i  ] = Math.min(baseData[i  ], dragData[i  ]);
            od[i+1] = Math.min(baseData[i+1], dragData[i+1]);
            od[i+2] = Math.min(baseData[i+2], dragData[i+2]);
            od[i+3] = 255;
          }
          rctx.putImageData(out, 0, 0);
          dragEl.style.opacity = "0";
          onSnap();
        }, 380);
      }
    }

    function onPointerDown(e) {
      if (snapped) return;
      dragging = true; dragEl.classList.add("dragging");
      const r = dragEl.getBoundingClientRect();
      startX = e.clientX; startY = e.clientY;
      originLeft = dragEl.offsetLeft; originTop = dragEl.offsetTop;
      dragEl.setPointerCapture(e.pointerId);
    }
    function onPointerMove(e) {
      if (!dragging) return;
      dragEl.style.left = (originLeft + (e.clientX - startX)) + "px";
      dragEl.style.top  = (originTop  + (e.clientY - startY)) + "px";
      paintOverlap();
    }
    function onPointerUp() {
      dragging = false; dragEl.classList.remove("dragging");
    }

    dragEl.addEventListener("pointerdown", onPointerDown);
    dragEl.addEventListener("pointermove", onPointerMove);
    dragEl.addEventListener("pointerup",   onPointerUp);
    dragEl.addEventListener("pointercancel", onPointerUp);

    paintOverlap(); // initial empty paint
    return {
      destroy: function () {
        dragEl.removeEventListener("pointerdown", onPointerDown);
        dragEl.removeEventListener("pointermove", onPointerMove);
        dragEl.removeEventListener("pointerup",   onPointerUp);
        dragEl.removeEventListener("pointercancel", onPointerUp);
      },
    };
  }

  return { setup };
})();
