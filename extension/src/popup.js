document.addEventListener('DOMContentLoaded', () => {
  // Force popup width to 400px — Firefox sometimes sizes based on content
  document.documentElement.style.width = '400px';
  document.documentElement.style.height = '450px';
  document.body.style.maxWidth = '100%';

  const extVersion = document.getElementById('extVersion');
  if (extVersion) {
    extVersion.textContent = `v${chrome.runtime.getManifest().version}`;
  }

  const srcText = document.getElementById('srcText');
  const targetText = document.getElementById('targetText');
  const srcLang = document.getElementById('srcLang');
  const targetLang = document.getElementById('targetLang');
  const swapBtn = document.getElementById('swapBtn');
  const translateBtn = document.getElementById('translateBtn');
  const copyBtn = document.getElementById('copyBtn');
  const charCount = document.getElementById('charCount');
  
  const toggleSettings = document.getElementById('toggleSettings');
  const settingsPanel = document.getElementById('settingsPanel');
  const ollamaUrl = document.getElementById('ollamaUrl');
  const ollamaModel = document.getElementById('ollamaModel');
  const ollamaApiKey = document.getElementById('ollamaApiKey');
  const saveSettings = document.getElementById('saveSettings');
  const testSettings = document.getElementById('testSettings');
  const testStatus = document.getElementById('testStatus');
  const globalStatus = document.getElementById('globalStatus');

  let delayTimer;

  // Font adjustments for accessibility & read support
  function applyPopupFontPreferences(prefs) {
    let size = prefs.extFontSize || 12;
    let family = prefs.extFontFamily || "'Segoe UI', system-ui, sans-serif";
    const isDyslexic = prefs.extDyslexicMode || false;

    if (isDyslexic) {
      size = Math.max(size, 15);
      family = "'Comic Sans MS', 'Chalkboard SE', cursive";
      document.body.classList.add('high-contrast-dyslexic');
    } else {
      document.body.classList.remove('high-contrast-dyslexic');
    }

    srcText.style.fontSize = `${size}px`;
    srcText.style.fontFamily = family;
    targetText.style.fontSize = `${size}px`;
    targetText.style.fontFamily = family;
  }

  // Function to dynamically load Ollama models and populate datalist dropdown suggestions
  function loadOllamaModels(selectedModelValue) {
    const url = ollamaUrl.value.trim().replace(/\/$/, "");
    const key = ollamaApiKey.value.trim();
    const modelsList = document.getElementById("modelsList");
    if (!modelsList) return;

    if (selectedModelValue) {
      ollamaModel.value = selectedModelValue;
    }

    // Call background service worker to fetch models securely (cross-origin bypassed)
    chrome.runtime.sendMessage({
      action: "get-models",
      url: url,
      key: key
    }, (response) => {
      if (chrome.runtime.lastError) {
        console.log("Background error fetching models:", chrome.runtime.lastError.message);
        return;
      }

      if (response && response.success && response.models && response.models.length > 0) {
        modelsList.textContent = "";
        response.models.forEach(modelName => {
          const opt = document.createElement("option");
          opt.value = modelName;
          modelsList.appendChild(opt);
        });

        const activeModel = ollamaModel.value.trim();
        let found = response.models.includes(activeModel);

        // Intelligent auto-detection of the best model (e.g. gemma4, gemma2, etc.)
        if (!found) {
          const gemmaModel = response.models.find(m => m.toLowerCase().includes("gemma"));
          if (gemmaModel) {
            ollamaModel.value = gemmaModel;
            chrome.storage.local.set({ ollamaModel: gemmaModel });
          } else {
            const qwenModel = response.models.find(m => m.toLowerCase().includes("qwen"));
            if (qwenModel) {
              ollamaModel.value = qwenModel;
              chrome.storage.local.set({ ollamaModel: qwenModel });
            }
          }
        }
      }
    });
  }

  // --- Quick-lang mapping (Ctrl+F9 + letter) dynamic list ---
  // value = internal language name (sent as targetLang); label = French display.
  const QUICK_LANGS = [
    ['French', 'Français'], ['English', 'Anglais'], ['Spanish', 'Espagnol'],
    ['German', 'Allemand'], ['Italian', 'Italien'], ['Portuguese', 'Portugais'],
    ['Chinese', 'Chinois'], ['Japanese', 'Japonais'], ['Russian', 'Russe']
  ];
  const quickLangList = document.getElementById('quickLangList');
  const addQuickLangBtn = document.getElementById('addQuickLang');

  function addQuickLangRow(letter, lang) {
    const row = document.createElement('div');
    row.className = 'ql-row';
    row.style.cssText = 'display:flex; gap:4px; align-items:center; margin-bottom:4px;';

    const letterInput = document.createElement('input');
    letterInput.type = 'text';
    letterInput.maxLength = 1;
    letterInput.className = 'ql-letter';
    letterInput.value = (letter || '').toUpperCase();
    letterInput.style.cssText = 'width:34px; min-width:34px; text-align:center; text-transform:uppercase;';
    letterInput.addEventListener('input', () => {
      letterInput.value = letterInput.value.replace(/[^a-zA-Z]/g, '').toUpperCase();
    });

    const arrow = document.createElement('span');
    arrow.textContent = '→';
    arrow.style.color = 'var(--text-muted)';

    const langSelect = document.createElement('select');
    langSelect.className = 'ql-lang';
    langSelect.style.flex = '1';
    QUICK_LANGS.forEach(([val, label]) => {
      const opt = document.createElement('option');
      opt.value = val; opt.textContent = label;
      if (val === lang) opt.selected = true;
      langSelect.appendChild(opt);
    });

    const removeBtn = document.createElement('button');
    removeBtn.type = 'button';
    removeBtn.className = 'secondary';
    removeBtn.textContent = '✕';
    removeBtn.title = 'Retirer cette lettre';
    removeBtn.style.cssText = 'padding:2px 8px; font-size:11px;';
    removeBtn.addEventListener('click', () => row.remove());

    row.appendChild(letterInput);
    row.appendChild(arrow);
    row.appendChild(langSelect);
    row.appendChild(removeBtn);
    quickLangList.appendChild(row);
  }

  // Build rows from the stored "E=English, F=French" string.
  function renderQuickLangRows(rawMap) {
    quickLangList.textContent = '';
    const pairs = [];
    (rawMap || '').split(',').forEach((pair) => {
      const idx = pair.indexOf('=');
      if (idx > 0) {
        const key = pair.slice(0, idx).trim();
        const lang = pair.slice(idx + 1).trim();
        if (key.length === 1 && lang) pairs.push([key, lang]);
      }
    });
    if (pairs.length === 0) {
      // Sensible defaults so the panel isn't empty on first use.
      [['E', 'English'], ['F', 'French'], ['S', 'Spanish']].forEach(([k, l]) => addQuickLangRow(k, l));
    } else {
      pairs.forEach(([k, l]) => addQuickLangRow(k, l));
    }
  }

  // Serialize the rows back to the "E=English, F=French" string.
  function serializeQuickLangRows() {
    const out = [];
    const seen = new Set();
    quickLangList.querySelectorAll('.ql-row').forEach((row) => {
      const key = row.querySelector('.ql-letter').value.trim().toUpperCase();
      const lang = row.querySelector('.ql-lang').value;
      if (key.length === 1 && lang && !seen.has(key)) {
        seen.add(key);
        out.push(`${key}=${lang}`);
      }
    });
    return out.join(', ');
  }

  if (addQuickLangBtn) {
    addQuickLangBtn.addEventListener('click', () => addQuickLangRow('', 'English'));
  }

  // Load saved settings & selections
  chrome.storage.local.get([
    'ollamaUrl', 'ollamaModel', 'ollamaApiKey', 'srcLang', 'targetLang', 'lastQueryText', 'customContextMenuLang', 'maxCharacters', 'extFontSize', 'extFontFamily', 'extDyslexicMode', 'quickLangMap'
  ], (result) => {
    if (result.ollamaUrl) ollamaUrl.value = result.ollamaUrl;
    if (result.ollamaApiKey) ollamaApiKey.value = result.ollamaApiKey;
    if (result.srcLang) srcLang.value = result.srcLang;
    if (result.targetLang) targetLang.value = result.targetLang;
    if (result.customContextMenuLang) {
      document.getElementById('customContextMenuLang').value = result.customContextMenuLang;
    }
    if (result.maxCharacters) {
      document.getElementById('maxCharacters').value = result.maxCharacters;
    }
    if (result.extFontSize) {
      document.getElementById('extFontSize').value = result.extFontSize;
    }
    if (result.extFontFamily) {
      document.getElementById('extFontFamily').value = result.extFontFamily;
    }
    if (result.extDyslexicMode !== undefined) {
      document.getElementById('extDyslexicMode').checked = result.extDyslexicMode;
    }
    renderQuickLangRows(result.quickLangMap);

    // Apply font settings load trigger
    applyPopupFontPreferences(result);
    
    // Load models list
    loadOllamaModels(result.ollamaModel);
    
    // Automatically retrieve browser's active selection first, or fallback to saved last query text
    chrome.tabs.query({ active: true, currentWindow: true }, (tabs) => {
      if (tabs[0]) {
        chrome.scripting.executeScript({
          target: { tabId: tabs[0].id },
          func: () => window.getSelection().toString()
        }, (selectionResult) => {
          if (selectionResult && selectionResult[0] && selectionResult[0].result) {
            srcText.value = selectionResult[0].result;
            updateCharCount();
            translate();
          } else if (result.lastQueryText) {
            srcText.value = result.lastQueryText;
            updateCharCount();
          }
        });
      } else if (result.lastQueryText) {
        srcText.value = result.lastQueryText;
        updateCharCount();
      }
    });
  });

  // Settings visibility toggle — overlay mode, no layout changes
  toggleSettings.addEventListener('click', () => {
    const isVisible = settingsPanel.style.display === 'block';
    settingsPanel.style.display = isVisible ? 'none' : 'block';
    if (!isVisible) {
      loadOllamaModels(ollamaModel.value);
    }
  });

  // Save Config
  saveSettings.addEventListener('click', () => {
    const fontSizeVal = parseInt(document.getElementById('extFontSize').value, 10) || 12;
    const fontFamilyVal = document.getElementById('extFontFamily').value;
    const dyslexicVal = document.getElementById('extDyslexicMode').checked;

    chrome.storage.local.set({
      ollamaUrl: ollamaUrl.value.trim(),
      ollamaModel: ollamaModel.value,
      ollamaApiKey: ollamaApiKey.value.trim(),
      customContextMenuLang: document.getElementById('customContextMenuLang').value.trim(),
      maxCharacters: parseInt(document.getElementById('maxCharacters').value, 10) || 10000,
      extFontSize: fontSizeVal,
      extFontFamily: fontFamilyVal,
      extDyslexicMode: dyslexicVal,
      quickLangMap: serializeQuickLangRows()
    }, () => {
      // Re-apply immediately in popup
      applyPopupFontPreferences({
        extFontSize: fontSizeVal,
        extFontFamily: fontFamilyVal,
        extDyslexicMode: dyslexicVal
      });
      showStatus(testStatus, "Configuration sauvegardée !", "success");
      setTimeout(() => { settingsPanel.style.display = 'none'; }, 1000);
    });
  });

  // Test Ollama server connection and refresh models
  testSettings.addEventListener('click', () => {
    const url = ollamaUrl.value.trim().replace(/\/$/, "");
    const key = ollamaApiKey.value.trim();
    showStatus(testStatus, "Connexion...", "");

    chrome.runtime.sendMessage({
      action: "get-models",
      url: url,
      key: key
    }, (response) => {
      if (chrome.runtime.lastError) {
        showStatus(testStatus, "Erreur d'extension.", "error");
        return;
      }
      if (response && response.success) {
        // Refresh models dropdown
        const currentSelected = ollamaModel.value;
        loadOllamaModels(currentSelected);
        showStatus(testStatus, `Connecté ! ${response.models.length} modèles trouvés et mis à jour.`, "success");
      } else {
        showStatus(testStatus, `Erreur : ${response ? response.error : "Impossible de joindre Ollama"}`, "error");
      }
    });
  });

  // Auto-translate on key up (debounce 600ms)
  srcText.addEventListener('input', () => {
    updateCharCount();
    clearTimeout(delayTimer);
    delayTimer = setTimeout(translate, 600);
  });

  // Copy Translation
  copyBtn.addEventListener('click', () => {
    if (targetText.value) {
      navigator.clipboard.writeText(targetText.value).then(() => {
        showStatus(globalStatus, "Traduction copiée !", "success");
      });
    }
  });

  // Open shortcuts settings page
  const openShortcutsBtn = document.getElementById('openShortcutsBtn');
  if (openShortcutsBtn) {
    openShortcutsBtn.addEventListener('click', () => {
      // Firefox provides a dedicated API to open its "Manage Extension
      // Shortcuts" dialog directly. Chrome has no equivalent; chrome://
      // URLs are illegal to open from extensions in Firefox.
      const commandsApi = (typeof browser !== 'undefined' && browser.commands) || chrome.commands;
      if (commandsApi && commandsApi.openShortcutSettings) {
        commandsApi.openShortcutSettings();
      } else {
        chrome.tabs.create({ url: 'chrome://extensions/shortcuts' });
      }
    });
  }

  // Manual trigger button
  translateBtn.addEventListener('click', () => {
    clearTimeout(delayTimer);
    translate();
  });

  // Swap Source/Target
  swapBtn.addEventListener('click', () => {
    const temp = srcLang.value;
    if (temp === "Auto Detection") {
      srcLang.value = "English";
    } else {
      srcLang.value = targetLang.value;
    }
    targetLang.value = temp === "Auto Detection" ? "French" : temp;
    translate();
  });

  function updateCharCount() {
    charCount.textContent = `${srcText.value.length} caractères`;
  }

  function showStatus(element, msg, type) {
    element.textContent = msg;
    element.className = "status-msg";
    if (type) element.classList.add(type);
    setTimeout(() => {
      element.textContent = "";
    }, 4000);
  }

  function detectIsEnglishHeuristic(txt) {
    if (!txt) return false;
    const words = txt.toLowerCase().match(/\b[a-z]{2,10}\b/g);
    if (!words) return false;
    const englishStopwords = new Set(["the", "and", "of", "to", "is", "that", "it", "for", "on", "was", "with", "as", "at", "by", "an", "be", "this", "are", "you", "from", "have", "not", "or", "but"]);
    let englishCount = 0;
    for (const w of words) {
      if (englishStopwords.has(w)) {
        englishCount++;
      }
    }
    return (englishCount / words.length) > 0.12 || (words.length >= 3 && englishCount >= 1);
  }

  function detectIsFrenchHeuristic(txt) {
    if (!txt) return false;
    const words = txt.toLowerCase().match(/\b[a-z]{2,10}\b/g);
    if (!words) return false;
    const frenchStopwords = new Set(["le", "la", "les", "et", "est", "dans", "pour", "une", "des", "qui", "que", "un", "du", "en", "pour", "par", "sur", "avec", "mais", "ou", "ce", "cette"]);
    let frenchCount = 0;
    for (const w of words) {
      if (frenchStopwords.has(w)) {
        frenchCount++;
      }
    }
    return (frenchCount / words.length) > 0.12 || (words.length >= 3 && frenchCount >= 1);
  }

  async function translate() {
    const text = srcText.value.trim();
    if (!text) {
      targetText.value = "";
      return;
    }

    // Smart automatic target language check
    let tLang = targetLang.value;
    const isEnglish = detectIsEnglishHeuristic(text);
    const isFrench = detectIsFrenchHeuristic(text);
    
    if (isEnglish && tLang === "English") {
      targetLang.value = "French";
    } else if (isFrench && tLang === "French") {
      targetLang.value = "English";
    }

    globalStatus.textContent = "Traduction en cours...";
    globalStatus.className = "status-msg";

    // Save languages and query
    chrome.storage.local.set({
      srcLang: srcLang.value,
      targetLang: targetLang.value,
      lastQueryText: text,
      ollamaUrl: ollamaUrl.value.trim(),
      ollamaModel: ollamaModel.value,
      ollamaApiKey: ollamaApiKey.value.trim()
    }, () => {
      // Execute the request securely via the background worker
      chrome.runtime.sendMessage({
        action: "secure-translate",
        text: text
      }, (response) => {
        if (chrome.runtime.lastError) {
          targetText.value = `❌ Erreur de communication avec l'arrière-plan :\n${chrome.runtime.lastError.message}`;
          globalStatus.textContent = "Échec.";
          globalStatus.className = "status-msg error";
          return;
        }

        if (response && response.success) {
          targetText.value = response.translation;
          globalStatus.textContent = "Traduction réussie.";
          globalStatus.className = "status-msg success";
        } else {
          const localUrl = ollamaUrl.value.trim().replace(/\/$/, "");
          const model = ollamaModel.value;
          targetText.value = `❌ Erreur de traduction :\n${response ? response.error : "Erreur inconnue"}\n\nVeuillez vérifier :\n1. Si Ollama tourne sur ${localUrl}\n2. Si le modèle '${model}' est disponible.\n3. Si vous utilisez Tailscale/Wireguard, vérifiez l'adresse IP et la connexion.`;
          globalStatus.textContent = "Échec.";
          globalStatus.className = "status-msg error";
        }
      });
    });
  }
});
