// ShallotT auto-detect content script — declared in manifest content_scripts so
// Firefox injects it reliably on every http/https page load (no fragile
// programmatic executeScript, no stale-after-reload issues).
(function () {
  if (window.__shallottAutoDetectActive) return;
  window.__shallottAutoDetectActive = true;

  var hintBtn = null;
  var currentSelection = '';

  function removeHint() {
    if (hintBtn) { hintBtn.remove(); hintBtn = null; }
    currentSelection = '';
  }

  function showHint(text, x, y) {
    removeHint();
    hintBtn = document.createElement('div');
    hintBtn.id = 'shallott-autodetect-btn';
    hintBtn.style.cssText = 'position:fixed;z-index:999999998;'
      + 'background:rgba(24,28,36,0.92);color:#ffaa33;'
      + 'border:1px solid #ffaa33;'
      + 'padding:4px 10px;border-radius:20px;font-size:11px;font-weight:600;cursor:pointer;'
      + 'font-family:"Segoe UI",system-ui,sans-serif;'
      + 'box-shadow:0 2px 8px rgba(0,0,0,0.4);'
      + 'backdrop-filter:blur(4px);user-select:none;white-space:nowrap;'
      + 'transition:opacity 0.15s;';
    hintBtn.textContent = '🧅 Traduire ?';
    var langNames = { French: 'Français', English: 'Anglais', Spanish: 'Espagnol',
      German: 'Allemand', Italian: 'Italien', Portuguese: 'Portugais',
      Chinese: 'Chinois', Japanese: 'Japonais', Russian: 'Russe' };
    chrome.storage.local.get(['targetLang'], function (res) {
      if (hintBtn) {
        var lang = res.targetLang || 'French';
        var display = langNames[lang] || lang;
        hintBtn.textContent = '🧅 Traduire en ' + display + ' ?';
      }
    });
    hintBtn.style.left = Math.min(Math.max(x + 10, 5), window.innerWidth - 210) + 'px';
    hintBtn.style.top = Math.max(y - 32, 5) + 'px';
    hintBtn.onclick = function (e) {
      e.stopPropagation(); e.preventDefault();
      // 'text' is the selection passed into showHint (guaranteed non-empty);
      // fall back to currentSelection or the live DOM selection just in case.
      var sendText = text || currentSelection ||
        (window.getSelection ? window.getSelection().toString().trim() : '');
      removeHint();
      var rt = (typeof browser !== 'undefined' && browser.runtime) ? browser.runtime : chrome.runtime;
      try {
        rt.sendMessage({ action: 'auto-detect-translate', text: sendText });
      } catch (err) { /* extension context invalidated, ignore */ }
    };
    document.body.appendChild(hintBtn);
    setTimeout(function () {
      if (hintBtn && hintBtn.parentNode) { hintBtn.remove(); hintBtn = null; }
    }, 6000);
  }

  function isForeignLanguage(txt) {
    if (!txt || txt.length < 3) return false;
    var words = txt.match(/\b\w{2,15}\b/g);
    return words && words.length >= 2;
  }

  document.addEventListener('mouseup', function (e) {
    setTimeout(function () {
      var sel = window.getSelection();
      var txt = (sel || '').toString().trim();
      if (txt && txt.length >= 3 && txt !== currentSelection) {
        currentSelection = txt;
        if (isForeignLanguage(txt)) {
          try {
            var rect = sel.getRangeAt(0).getBoundingClientRect();
            showHint(txt, rect.left, rect.bottom);
          } catch (err) { /* selection in input, skip */ }
        } else {
          removeHint();
        }
      } else if (!txt) {
        setTimeout(removeHint, 500);
      }
    }, 350);
  });

  document.addEventListener('click', function (e) {
    if (hintBtn && !hintBtn.contains(e.target)) {
      removeHint();
    }
  });
})();
