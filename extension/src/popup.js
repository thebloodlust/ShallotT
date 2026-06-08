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

  // Load saved settings & selections
  chrome.storage.local.get([
    'ollamaUrl', 'ollamaModel', 'ollamaApiKey', 'srcLang', 'targetLang', 'lastQueryText'
  ], (result) => {
    if (result.ollamaUrl) ollamaUrl.value = result.ollamaUrl;
    if (result.ollamaModel) ollamaModel.value = result.ollamaModel;
    if (result.ollamaApiKey) ollamaApiKey.value = result.ollamaApiKey;
    if (result.srcLang) srcLang.value = result.srcLang;
    if (result.targetLang) targetLang.value = result.targetLang;
    
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
    settingsPanel.style.display = settingsPanel.style.display === 'block' ? 'none' : 'block';
  });

  // Save Config
  saveSettings.addEventListener('click', () => {
    chrome.storage.local.set({
      ollamaUrl: ollamaUrl.value.trim(),
      ollamaModel: ollamaModel.value.trim(),
      ollamaApiKey: ollamaApiKey.value.trim()
    }, () => {
      showStatus(testStatus, "Configuration sauvegardée !", "success");
      setTimeout(() => { settingsPanel.style.display = 'none'; }, 1000);
    });
  });

  // Test Ollama server connection
  testSettings.addEventListener('click', async () => {
    const url = ollamaUrl.value.trim().replace(/\/$/, "");
    const key = ollamaApiKey.value.trim();
    showStatus(testStatus, "Connexion...", "");
    try {
      const headers = {};
      if (key) headers["Authorization"] = `Bearer ${key}`;
      const response = await fetch(`${url}/api/tags`, { method: 'GET', headers: headers });
      if (response.ok) {
        const data = await response.json();
        const models = data.models ? data.models.map(m => m.name) : [];
        showStatus(testStatus, `Connecté ! ${models.length} modèles trouvés.`, "success");
      } else {
        showStatus(testStatus, `Erreur serveur (Code: ${response.status})`, "error");
      }
    } catch (err) {
      showStatus(testStatus, "Impossible de joindre Ollama. Vérifiez l'URL ou le VPN.", "error");
    }
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

    // Save state
    chrome.storage.local.set({
      srcLang: srcLang.value,
      targetLang: targetLang.value,
      lastQueryText: text
    });

    globalStatus.textContent = "Traduction en cours par Gemma 2...";
    globalStatus.className = "status-msg";

    const localUrl = ollamaUrl.value.trim().replace(/\/$/, "");
    const model = ollamaModel.value.trim();
    const key = ollamaApiKey.value.trim();

    const fromL = srcLang.value;
    const toL = targetLang.value;
    
    let promptContext = `Translate the following text into ${toL}.`;
    if (fromL !== "Auto Detection") {
      promptContext = `Translate the following text from ${fromL} to ${toL}.`;
    }

    const fullPrompt = `<start_of_turn>user\nYou are a professional, high-performance translator like DeepL. Translate the text accurately. Preserve the original formatting, paragraph breaks, tone, and style.\nCRITICAL: Do not write any explanations, summaries, preamble, warning, notes, or code blocks. Just output the translation directly.\n\nInstruction: ${promptContext}\n\nText to translate:\n${text}\n<start_of_turn>model\n`;

    try {
      const headers = { 'Content-Type': 'application/json' };
      if (key) headers['Authorization'] = `Bearer ${key}`;

      const response = await fetch(`${localUrl}/api/generate`, {
        method: 'POST',
        headers: headers,
        body: JSON.stringify({
          model: model,
          prompt: fullPrompt,
          stream: false,
          options: {
            temperature: 0.2,
            top_p: 0.9,
            num_predict: 2048
          }
        })
      });

      if (!response.ok) {
        throw new Error(`Erreur serveur (${response.status})`);
      }

      const result = await response.json();
      targetText.value = result.response ? result.response.trim() : "";
      globalStatus.textContent = "Traduction réussie.";
      globalStatus.className = "status-msg success";
    } catch (err) {
      targetText.value = `❌ Erreur de traduction :\n${err.message}\n\nVeuillez vérifier :\n1. Si Ollama tourne sur ${localUrl}\n2. Si le modèle '${model}' est disponible.\n3. Si vous utilisez Tailscale/Wireguard, vérifiez l'adresse IP et la connexion.`;
      globalStatus.textContent = "Échec.";
      globalStatus.className = "status-msg error";
    }
  }
});
