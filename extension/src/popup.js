document.addEventListener('DOMContentLoaded', () => {
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

  // Function to dynamically load Ollama models and populate select dropdown
  function loadOllamaModels(selectedModelValue) {
    const url = ollamaUrl.value.trim().replace(/\/$/, "");
    const key = ollamaApiKey.value.trim();
    
    // Clear and add a loading/temporary option
    ollamaModel.innerHTML = "";
    const activeModel = selectedModelValue || "gemma:latest";
    const tempOpt = document.createElement("option");
    tempOpt.value = activeModel;
    tempOpt.textContent = activeModel + " (sauvegardé)";
    tempOpt.selected = true;
    ollamaModel.appendChild(tempOpt);

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
        ollamaModel.innerHTML = "";
        let found = false;
        
        let modelToSelect = activeModel;
        if (response.models.includes(activeModel)) {
          found = true;
        }

        // Intelligent auto-detection of the best model (e.g. gemma4, gemma2, etc.)
        if (!found) {
          const gemmaModel = response.models.find(m => m.toLowerCase().includes("gemma"));
          if (gemmaModel) {
            modelToSelect = gemmaModel;
            found = true;
          } else {
            const qwenModel = response.models.find(m => m.toLowerCase().includes("qwen"));
            if (qwenModel) {
              modelToSelect = qwenModel;
              found = true;
            } else {
              modelToSelect = response.models[0];
              found = true;
            }
          }
        }

        response.models.forEach(modelName => {
          const opt = document.createElement("option");
          opt.value = modelName;
          opt.textContent = modelName;
          if (modelName === modelToSelect) {
            opt.selected = true;
          }
          ollamaModel.appendChild(opt);
        });

        // Automatically save the auto-detected model so translated texts work out of the box
        if (modelToSelect !== activeModel) {
          chrome.storage.local.set({ ollamaModel: modelToSelect });
        }
      }
    });
  }

  // Load saved settings & selections
  chrome.storage.local.get([
    'ollamaUrl', 'ollamaModel', 'ollamaApiKey', 'srcLang', 'targetLang', 'lastQueryText'
  ], (result) => {
    if (result.ollamaUrl) ollamaUrl.value = result.ollamaUrl;
    if (result.ollamaApiKey) ollamaApiKey.value = result.ollamaApiKey;
    if (result.srcLang) srcLang.value = result.srcLang;
    if (result.targetLang) targetLang.value = result.targetLang;
    
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

  // Settings visibility toggle
  toggleSettings.addEventListener('click', () => {
    const isVisible = settingsPanel.style.display === 'block';
    settingsPanel.style.display = isVisible ? 'none' : 'block';
    if (!isVisible) {
      // Reload models on opening options panel
      loadOllamaModels(ollamaModel.value);
    }
  });

  // Save Config
  saveSettings.addEventListener('click', () => {
    chrome.storage.local.set({
      ollamaUrl: ollamaUrl.value.trim(),
      ollamaModel: ollamaModel.value,
      ollamaApiKey: ollamaApiKey.value.trim()
    }, () => {
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

  async function translate() {
    const text = srcText.value.trim();
    if (!text) {
      targetText.value = "";
      return;
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
