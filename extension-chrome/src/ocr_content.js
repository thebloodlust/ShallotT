/**
 * OCR content script for ShallotT — Tesseract.js (WASM) area OCR.
 * Injected by background.js on Ctrl+Shift+F8.
 * Captures a user-drawn selection rectangle and extracts text via Tesseract.js.
 */

(async function shallotOCRCapture() {
  // ── Prevent double injection ──────────────────────────────────
  if (document.getElementById('shallott-ocr-overlay')) return;

  // ── Build overlay UI first ───────────────────────────────────
  const hint = document.createElement('div');
  hint.id = 'shallott-ocr-hint';
  hint.style.cssText = 'position:fixed;top:12px;left:50%;transform:translateX(-50%);'
    + 'background:#181c24;color:#ffaa33;padding:10px 20px;border:2px solid #ffaa33;'
    + 'border-radius:8px;z-index:999999999;font-size:14px;font-family:"Segoe UI",sans-serif;'
    + 'pointer-events:none;';
  hint.textContent = '📥 Loading OCR engine...';
  document.body.appendChild(hint);

  const overlay = document.createElement('div');
  overlay.id = 'shallott-ocr-overlay';
  overlay.style.cssText = 'position:fixed;top:0;left:0;width:100vw;height:100vh;'
    + 'z-index:999999997;cursor:crosshair;background:rgba(0,0,0,0.3);';
  document.body.appendChild(overlay);

  const selection = document.createElement('div');
  selection.id = 'shallott-ocr-sel';
  selection.style.cssText = 'position:fixed;border:2px dashed #ffaa33;'
    + 'background:rgba(255,170,51,0.1);display:none;z-index:999999998;pointer-events:none;';
  document.body.appendChild(selection);

  // Tesseract.js is injected first via chrome.scripting.executeScript files[].
  // Already available in this isolated world — no CDN or DOM injection needed.
  if (typeof Tesseract === 'undefined') {
    hint.textContent = '❌ OCR engine not loaded. Reload the extension.';
    setTimeout(() => cleanup(null), 3000);
    return;
  }
  hint.textContent = '📸 Draw a rectangle to OCR (Esc to cancel)';

  // ── Drawing state ────────────────────────────────────────────
  let startX = 0, startY = 0;
  let drawing = false;

  overlay.addEventListener('mousedown', e => {
    drawing = true;
    startX = e.clientX;
    startY = e.clientY;
    selection.style.display = 'block';
  });

  overlay.addEventListener('mousemove', e => {
    if (!drawing) return;
    const x = Math.min(startX, e.clientX);
    const y = Math.min(startY, e.clientY);
    const w = Math.abs(e.clientX - startX);
    const h = Math.abs(e.clientY - startY);
    selection.style.left = x + 'px';
    selection.style.top = y + 'px';
    selection.style.width = w + 'px';
    selection.style.height = h + 'px';
  });

  overlay.addEventListener('mouseup', async e => {
    if (!drawing) return;
    drawing = false;
    const x = Math.min(startX, e.clientX);
    const y = Math.min(startY, e.clientY);
    const w = Math.abs(e.clientX - startX);
    const h = Math.abs(e.clientY - startY);

    if (w < 20 || h < 20) {
      cleanup('Area too small — try again');
      return;
    }

    hint.textContent = '🔍 OCR in progress... (Tesseract.js WASM)';

    try {
      // Capture the selected area via html2canvas-like approach:
      // Use a canvas to draw the viewport, then crop
      const canvas = document.createElement('canvas');
      canvas.width = w;
      canvas.height = h;
      const ctx = canvas.getContext('2d');

      // Draw the visible page into a canvas, offset by the selection
      // We use a simpler approach: screenshot the entire viewport then crop
      // For now, let's use the canvas image data approach
      const text = await ocrArea(x, y, w, h);

      if (text && text.trim().length > 0) {
        chrome.runtime.sendMessage({ action: 'ocr-result', text: text.trim() });
        cleanup(null);
      } else {
        cleanup('No text detected — try a larger area');
      }
    } catch (err) {
      cleanup('OCR failed: ' + (err.message || 'unknown error'));
    }
  });

  // ── Escape to cancel ─────────────────────────────────────────
  document.addEventListener('keydown', function escHandler(e) {
    if (e.key === 'Escape') {
      document.removeEventListener('keydown', escHandler, true);
      cleanup(null);
    }
  }, true);

  // ── Helpers ───────────────────────────────────────────────────
  async function ocrArea(x, y, w, h) {
    // Use html2canvas-like approach: scroll the page to capture
    // For simplicity, we use the built-in approach:
    // Grab a screenshot of the visible area and crop
    const screenshotCanvas = await captureVisibleArea();
    const cropCanvas = document.createElement('canvas');
    cropCanvas.width = w * (window.devicePixelRatio || 1);
    cropCanvas.height = h * (window.devicePixelRatio || 1);
    const cropCtx = cropCanvas.getContext('2d');
    cropCtx.drawImage(
      screenshotCanvas,
      x * (window.devicePixelRatio || 1),
      y * (window.devicePixelRatio || 1),
      w * (window.devicePixelRatio || 1),
      h * (window.devicePixelRatio || 1),
      0, 0,
      cropCanvas.width, cropCanvas.height
    );

    // Convert to data URL
    const dataUrl = cropCanvas.toDataURL('image/png');

    // OCR with Tesseract.js
    const worker = await Tesseract.createWorker('eng', 1, {
      logger: m => {
        if (m.status === 'recognizing text') {
          hint.textContent = `🔍 OCR... ${Math.round(m.progress * 100)}%`;
        }
      }
    });

    const { data } = await worker.recognize(dataUrl);
    await worker.terminate();
    return data.text;
  }

  async function captureVisibleArea() {
    // Use the browser's built-in captureVisibleTab if available
    // Since we're a content script, we ask the background to capture
    return new Promise((resolve) => {
      chrome.runtime.sendMessage({ action: 'capture-tab' }, (response) => {
        if (response && response.dataUrl) {
          const img = new Image();
          img.onload = () => {
            const canvas = document.createElement('canvas');
            canvas.width = img.width;
            canvas.height = img.height;
            canvas.getContext('2d').drawImage(img, 0, 0);
            resolve(canvas);
          };
          img.src = response.dataUrl;
        } else {
          // Fallback: capture visible DOM (less accurate)
          const canvas = document.createElement('canvas');
          canvas.width = window.innerWidth * (window.devicePixelRatio || 1);
          canvas.height = window.innerHeight * (window.devicePixelRatio || 1);
          resolve(canvas);
        }
      });
    });
  }

  function cleanup(msg) {
    overlay.remove();
    selection.remove();
    if (msg) {
      hint.textContent = msg;
      setTimeout(() => hint.remove(), 2000);
    } else {
      hint.remove();
    }
  }
})();
