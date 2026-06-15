/**
 * Full-page translation content script for ShallotT.
 * Walks text nodes, translates them via the background Ollama bridge,
 * and swaps them in-place preserving layout/events/styles.
 * Toggle: first call translates, second call reverts to original.
 */

(function shallotPageTranslate() {

  // ── State ──────────────────────────────────────────────────────
  // Toggle: translated → revert to original; original → translate (cached or API)
  if (window.__shallotPageTranslated) {
    revertAll();
    return;
  }

  // If we have cached translations from a previous run, apply them instantly
  if (window.__shallotPageTranslations && window.__shallotPageOriginals) {
    applyCached();
    return;
  }

  const MAX_TEXT_LEN = 400;  // truncate very long texts

  // ── Collect visible text nodes ────────────────────────────────
  function collectTextNodes() {
    const nodes = [];
    const walker = document.createTreeWalker(
      document.body,
      NodeFilter.SHOW_TEXT,
      {
        acceptNode: function(node) {
          const parent = node.parentElement;
          if (!parent) return NodeFilter.FILTER_REJECT;
          const tag = parent.tagName;
          if (tag === 'SCRIPT' || tag === 'STYLE' || tag === 'NOSCRIPT' || tag === 'TEXTAREA'
              || tag === 'CODE' || tag === 'PRE') return NodeFilter.FILTER_REJECT;
          try {
            const style = window.getComputedStyle(parent);
            if (style.display === 'none' || style.visibility === 'hidden') return NodeFilter.FILTER_REJECT;
          } catch(e) {}
          const text = node.textContent.trim();
          if (text.length < 3) return NodeFilter.FILTER_REJECT;
          return NodeFilter.FILTER_ACCEPT;
        }
      }
    );
    while (walker.nextNode()) {
      nodes.push(walker.currentNode);
    }
    return nodes;
  }

  // ── Show / update progress bar ─────────────────────────────────
  let progressBar, progressText;
  function showProgress(current, total) {
    if (!progressBar) {
      const bar = document.createElement('div');
      bar.id = 'shallott-page-progress';
      bar.style.cssText = 'position:fixed;top:0;left:0;width:100%;height:4px;z-index:999999999;'
        + 'background:#181c24;';
      const inner = document.createElement('div');
      inner.id = 'shallott-page-progress-inner';
      inner.style.cssText = 'height:100%;background:#ffaa33;transition:width 0.3s;width:0%;';
      bar.appendChild(inner);
      document.body.appendChild(bar);
      progressBar = inner;

      const txt = document.createElement('div');
      txt.id = 'shallott-page-progress-text';
      txt.style.cssText = 'position:fixed;top:8px;right:12px;z-index:999999999;'
        + 'background:#181c24;color:#ffaa33;padding:4px 10px;border-radius:4px;'
        + 'font-size:11px;font-family:"Segoe UI",sans-serif;';
      document.body.appendChild(txt);
      progressText = txt;
    }
    const pct = total > 0 ? Math.round((current / total) * 100) : 0;
    progressBar.style.width = pct + '%';
    progressText.textContent = `🌐 Translating page... ${pct}% (${current}/${total})`;
  }

  function hideProgress() {
    if (progressBar) { progressBar.parentElement.remove(); progressBar = null; }
    if (progressText) { progressText.remove(); progressText = null; }
  }

  // ── Translate ALL texts in ONE big batch ──────────────────────
  function translateBigBatch(texts) {
    return new Promise((resolve) => {
      // Maximum texts per big batch (Ollama can handle ~2000 chars of prompt)
      const BIG_BATCH_SIZE = 30;
      const chunk = texts.slice(0, BIG_BATCH_SIZE);
      const rest = texts.slice(BIG_BATCH_SIZE);

      // Use [SEP] as a clear delimiter the model can reproduce
      const combined = chunk.map((t, i) => `[${i}] ${t}`).join('\n[SEP]\n');

      chrome.runtime.sendMessage({
        action: 'translate-big-batch',
        text: combined,
        count: chunk.length
      }, (response) => {
        if (chrome.runtime.lastError || !response || !response.success) {
          resolve({ translations: chunk, rest: rest }); // keep originals
        } else {
          const translations = response.translations || chunk;
          resolve({ translations: translations, rest: rest });
        }
      });
    });
  }

  // Translate items in big batches (30 texts each = 2-5 API calls per page)
  async function translateAllTexts(items) {
    const texts = items.map(i => i.text);
    let allTranslations = [];
    let remaining = texts;
    let round = 0;

    while (remaining.length > 0) {
      round++;
      showProgress(round, Math.ceil(texts.length / 30));
      const { translations, rest } = await translateBigBatch(remaining);
      allTranslations = allTranslations.concat(translations);
      remaining = rest;
    }

    // Map back to items
    return items.map((item, idx) => ({
      node: item.node,
      translation: allTranslations[idx] || item.text
    }));
  }

  // ── Main flow ──────────────────────────────────────────────────
  async function translateAll() {
    const nodes = collectTextNodes();
    if (nodes.length === 0) {
      alert('[ShallotT] No visible text found on this page.');
      return;
    }

    window.__shallotPageTranslated = true;
    window.__shallotPageOriginals = new Map();
    window.__shallotPageTranslations = new Map();

    // Save originals
    nodes.forEach(n => {
      window.__shallotPageOriginals.set(n, n.textContent);
    });

    // Build items to translate (truncate long texts)
    const items = [];
    for (const node of nodes) {
      let text = node.textContent.trim();
      if (text.length > MAX_TEXT_LEN) {
        text = text.substring(0, MAX_TEXT_LEN) + '…';
      }
      items.push({ node: node, text: text });
    }

    showProgress(0, 1);
    const allResults = await translateAllTexts(items);

    // Replace text nodes with translations AND save to cache
    let replacedCount = 0;
    for (const item of allResults) {
      if (item.translation && item.translation !== item.node.textContent && item.translation.length > 1) {
        item.node.textContent = item.translation;
        window.__shallotPageTranslations.set(item.node, item.translation);
        replacedCount++;
      }
    }

    hideProgress();
    const flash = document.createElement('div');
    flash.style.cssText = 'position:fixed;top:8px;right:12px;z-index:999999999;'
      + 'background:#a6e3a1;color:#000;padding:4px 10px;border-radius:4px;'
      + 'font-size:11px;font-family:"Segoe UI",sans-serif;';
    flash.textContent = '✅ ' + replacedCount + '/' + nodes.length + ' texts translated (Ctrl+Shift+F10 to revert)';
    document.body.appendChild(flash);
    setTimeout(() => flash.remove(), 4000);
  }

  function applyCached() {
    // Re-apply cached translations instantly (no API calls)
    const translations = window.__shallotPageTranslations;
    if (!translations) return;
    let count = 0;
    translations.forEach((translation, node) => {
      try {
        if (node.parentElement && translation.length > 1) {
          node.textContent = translation;
          count++;
        }
      } catch(e) {}
    });
    window.__shallotPageTranslated = true;
    const flash = document.createElement('div');
    flash.style.cssText = 'position:fixed;top:8px;right:12px;z-index:999999999;'
      + 'background:#a6e3a1;color:#000;padding:4px 10px;border-radius:4px;'
      + 'font-size:11px;font-family:"Segoe UI",sans-serif;';
    flash.textContent = '⚡ ' + count + ' texts restored from cache (Ctrl+Shift+F10 to revert)';
    document.body.appendChild(flash);
    setTimeout(() => flash.remove(), 3000);
  }

  function revertAll() {
    const originals = window.__shallotPageOriginals;
    if (!originals) return;

    originals.forEach((original, node) => {
      try {
        if (node.parentElement) {
          node.textContent = original;
        }
      } catch(e) {}
    });

    window.__shallotPageTranslated = false;
    // Keep originals + translations in cache for instant re-translate
    hideProgress();

    const flash = document.createElement('div');
    flash.style.cssText = 'position:fixed;top:8px;right:12px;z-index:999999999;'
      + 'background:#ffaa33;color:#000;padding:4px 10px;border-radius:4px;'
      + 'font-size:11px;font-family:"Segoe UI",sans-serif;';
    flash.textContent = '↩ Original text restored';
    document.body.appendChild(flash);
    setTimeout(() => flash.remove(), 3000);
  }

  // ── Start ──────────────────────────────────────────────────────
  translateAll().catch(err => {
    console.error('[ShallotT] Page translation failed:', err);
    hideProgress();
  });

})();
