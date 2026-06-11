// Background service worker for Chrome (Manifest V3)
//
// Note: Origin/Referer rewriting for Ollama requests (so the local server's
// CORS check accepts the extension) is handled declaratively via
// declarativeNetRequest, see rules.json. Response CORS headers don't need
// rewriting because fetches issued from this background context with
// host_permissions bypass the browser's CORS checks entirely.

// Default host configurations
const DEFAULT_URL = "http://localhost:11434";
const DEFAULT_MODEL = "gemma:latest";

// Heuristic language detection functions for background actions
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

// Rebuild context menus based on user custom list of languages
function rebuildContextMenus(langString) {
  if (!chrome.contextMenus) return;
  
  chrome.contextMenus.removeAll(() => {
    chrome.contextMenus.create({
      id: "shallott-translate-selection",
      title: "Traduire avec ShallotT Local",
      contexts: ["selection"]
    });

    // Default list if empty or invalid
    let list = ["Français", "Anglais", "Espagnol", "Allemand", "Italien", "Portugais", "Chinois", "Japonais", "Russe"];
    if (langString) {
      list = langString.split(",")
        .map(s => s.trim())
        .filter(s => s.length > 0);
    }

    // Map French titles to internal English values
    const langMap = {
      "fransais": "French", "français": "French", "francais": "French", "french": "French",
      "anglais": "English", "english": "English",
      "espagnol": "Spanish", "spanish": "Spanish",
      "allemand": "German", "german": "German",
      "italien": "Italian", "italian": "Italian",
      "portugais": "Portuguese", "portuguese": "Portuguese",
      "chinois": "Chinese", "chinese": "Chinese",
      "japonais": "Japanese", "japanese": "Japanese",
      "russe": "Russian", "russian": "Russian"
    };

    // Flag mapping dictionary based on lowercase names
    const flagMap = {
      "french": "🇫🇷", "français": "🇫🇷", "francais": "🇫🇷",
      "english": "🇬🇧", "anglais": "🇬🇧",
      "spanish": "🇪🇸", "espagnol": "🇪🇸",
      "german": "🇩🇪", "allemand": "🇩🇪",
      "italian": "🇮🇹", "italien": "🇮🇹",
      "portuguese": "🇵🇹", "portugais": "🇵🇹",
      "chinese": "🇨🇳", "chinois": "🇨🇳",
      "japanese": "🇯🇵", "japonais": "🇯🇵",
      "russian": "🇷🇺", "russe": "🇷🇺"
    };

    list.forEach(item => {
      if (!item) return;
      const normalized = item.charAt(0).toUpperCase() + item.slice(1);
      const lookVal = item.toLowerCase();
      const mappedLang = langMap[lookVal] || normalized;
      const flag = flagMap[lookVal] || "";
      const displayTitle = flag ? `Traduire en ${normalized} ${flag}` : `Traduire en ${normalized}`;

      chrome.contextMenus.create({
        id: "shallott-lang-" + mappedLang,
        parentId: "shallott-translate-selection",
        title: displayTitle,
        contexts: ["selection"]
      });
    });
  });
}

// Set up Context Menu item on installation
chrome.runtime.onInstalled.addListener(() => {
  // Setup default values in storage
  chrome.storage.local.get(['ollamaUrl', 'ollamaModel', 'targetLang', 'customContextMenuLang', 'maxCharacters'], (result) => {
    if (!result.ollamaUrl) chrome.storage.local.set({ ollamaUrl: DEFAULT_URL });
    if (!result.ollamaModel) chrome.storage.local.set({ ollamaModel: DEFAULT_MODEL });
    if (!result.targetLang) chrome.storage.local.set({ targetLang: "French" });
    if (!result.maxCharacters) chrome.storage.local.set({ maxCharacters: 10000 });
    
    const initialLangs = result.customContextMenuLang || "Français, Anglais, Espagnol, Allemand, Italien, Portugais, Chinois, Japonais, Russe";
    if (!result.customContextMenuLang) {
      chrome.storage.local.set({ customContextMenuLang: initialLangs });
    }
    rebuildContextMenus(initialLangs);
  });
});

// Rebuild when storage changes
chrome.storage.onChanged.addListener((changes, areaName) => {
  if (areaName === "local" && changes.customContextMenuLang) {
    rebuildContextMenus(changes.customContextMenuLang.newValue);
  }
});

function normalizeUrl(url) {
  let cleaned = (url || "http://localhost:11434").trim();
  if (!cleaned) return "http://localhost:11434";
  
  // Strip common Ollama API paths or trailing slashes in case copy-pasted
  cleaned = cleaned.replace(/\/api\/tags\/?$/i, "");
  cleaned = cleaned.replace(/\/api\/generate\/?$/i, "");
  cleaned = cleaned.replace(/\/api\/?$/i, "");
  cleaned = cleaned.replace(/\/$/, "");
  
  if (!/^https?:\/\//i.test(cleaned)) {
    cleaned = "http://" + cleaned;
  }
  
  try {
    const parse = new URL(cleaned);
    let protocol = parse.protocol || "http:";
    let hostname = parse.hostname;
    let port = parse.port;
    
    if (!port) {
      if (hostname.includes(":")) {
        return `${protocol}//${hostname}`;
      } else {
        return `${protocol}//${hostname}:11434`;
      }
    }
    return `${protocol}//${hostname}:${port}`;
  } catch (e) {
    if (!cleaned.includes(":", 6)) {
      cleaned = cleaned + ":11434";
    }
    return cleaned;
  }
}

// Listener to execute secure extension-level fetch requests to bypass webpage CORS/Mixed-Content limitations
chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {
  if (request.action === "secure-translate") {
    const trackingId = request.trackingId || "none";
    chrome.storage.local.get(['ollamaUrl', 'ollamaModel', 'ollamaApiKey', 'targetLang', 'maxCharacters'], async (stored) => {
      const url = normalizeUrl(stored.ollamaUrl);
      const model = stored.ollamaModel || "gemma:latest";
      const key = stored.ollamaApiKey || "";
      const targetL = stored.targetLang || "French";
      const maxChars = stored.maxCharacters || 10000;

      let textToTranslate = request.text || "";
      let truncatedNote = "";
      if (textToTranslate.length > maxChars) {
        textToTranslate = textToTranslate.substring(0, maxChars);
        truncatedNote = `\n\n--- [Note: Traduction limitée à ${maxChars} caractères pour optimiser la vitesse de traitement] ---`;
      }

      const promptContext = `Translate the following text into ${targetL}.`;
      const fullPrompt = `<start_of_turn>user\nYou are a professional, high-performance translator powered by translation AI. Translate the text accurately. Preserve the original formatting, paragraph breaks, tone, and style.\nCRITICAL: Do not write any explanations, summaries, preamble, warning, notes, or code blocks. Just output the translation directly.\n\nInstruction: ${promptContext}\n\nText to translate:\n${textToTranslate}\n<start_of_turn>model\n`;

      let isAborted = false;
      const abortListener = (msg) => {
        if (msg.action === "abort-translation" && msg.trackingId === trackingId) {
          isAborted = true;
          chrome.runtime.onMessage.removeListener(abortListener);
        }
      };
      chrome.runtime.onMessage.addListener(abortListener);

      try {
        const headers = { "Content-Type": "application/json" };
        if (key) headers["Authorization"] = `Bearer ${key}`;

        // Retry wrapper for translation fetch to bypass transient "fetch resource" failures
        let response;
        let lastErr;
        const maxRetries = 2; // Reduced maximum retries for faster response

        for (let i = 0; i < maxRetries; i++) {
          if (isAborted) {
            throw new Error("AbortedByUser");
          }
          try {
            response = await fetch(`${url}/api/generate`, {
              method: "POST",
              headers: headers,
              body: JSON.stringify({
                model: model,
                prompt: fullPrompt,
                stream: false,
                keep_alive: "60m", // Keep model in memory for 60 minutes
                // Use optimal robust parameters matching PyQt6 app to prevent Empty Response
                options: { temperature: 0.2, top_p: 0.9, num_predict: 2048 }
              })
            });
            if (response.ok) break;
          } catch (err) {
            lastErr = err;
            if (i < maxRetries - 1 && !isAborted) {
              await new Promise(resolve => setTimeout(resolve, 200)); // wait 200ms before retry
            }
          }
        }

        if (isAborted) {
          throw new Error("AbortedByUser");
        }

        if (!response || !response.ok) {
          throw new Error(response ? `HTTP ${response.status}` : (lastErr ? lastErr.message : "Fetch translation failed"));
        }

        const result = await response.json();
        let translation = result.response ? result.response.trim() : "Empty response";
        if (typeof truncatedNote !== "undefined" && truncatedNote) {
          translation += truncatedNote;
        }
        sendResponse({ success: true, translation: translation });
      } catch (err) {
        sendResponse({ success: false, error: err.message });
      } finally {
        chrome.runtime.onMessage.removeListener(abortListener);
      }
    });
    return true; // Keep sendResponse channel active
  } else if (request.action === "get-models") {
    const url = normalizeUrl(request.url);
    const key = request.key || "";
    const headers = {};
    if (key) headers["Authorization"] = `Bearer ${key}`;

    const fetchWithRetry = async (retries = 3, delay = 300) => {
      let lastErr;
      for (let i = 0; i < retries; i++) {
        try {
          const response = await fetch(`${url}/api/tags`, { method: "GET", headers: headers });
          if (response.ok) {
            return await response.json();
          }
          throw new Error(`HTTP ${response.status}`);
        } catch (err) {
          lastErr = err;
          if (i < retries - 1) {
            await new Promise(res => setTimeout(res, delay));
          }
        }
      }
      throw lastErr;
    };

    fetchWithRetry()
      .then(data => {
        const models = data.models ? data.models.map(m => m.name) : [];
        sendResponse({ success: true, models: models });
      })
      .catch(err => {
        sendResponse({ success: false, error: err.message });
      });
    return true; // Keep sendResponse channel active
  }
});

// Listener for keyboard command shortcuts
chrome.commands.onCommand.addListener((command) => {
  if (command === "translate-selection") {
    // Inject scripting to read page selection and pop up browser action / dialog or prompt
    chrome.tabs.query({ active: true, currentWindow: true }, (tabs) => {
      if (tabs[0] && tabs[0].id) {
        if (chrome.scripting) {
          chrome.scripting.executeScript({
            target: { tabId: tabs[0].id },
            func: () => window.getSelection().toString()
          }, (res) => {
            if (res && res[0] && res[0].result) {
              const selectedText = res[0].result;
              // Store selected text and open popup
              chrome.storage.local.set({ lastQueryText: selectedText }, () => {
                const action = chrome.action || chrome.browserAction;
                action.openPopup ? action.openPopup() : alert("Selection capturée, cliquez sur l'icône de l'extension ShallotT pour traduire !");
              });
            }
          });
        } else {
          // MSV2 Fallback for tabs injection
          chrome.tabs.executeScript(tabs[0].id, {
            code: "window.getSelection().toString()"
          }, (res) => {
            if (res && res[0]) {
              const selectedText = res[0];
              chrome.storage.local.set({ lastQueryText: selectedText }, () => {
                const action = chrome.action || chrome.browserAction;
                action.openPopup ? action.openPopup() : alert("Selection capturée, cliquez sur l'icône de l'extension ShallotT pour traduire !");
              });
            }
          });
        }
      }
    });
  }
});

// Context Menu triggering
chrome.contextMenus.onClicked.addListener((info, tab) => {
  const isParentClick = info.menuItemId === "shallott-translate-selection";
  const isSubmenuClick = info.menuItemId && info.menuItemId.startsWith("shallott-lang-");
  
  if ((isParentClick || isSubmenuClick) && info.selectionText) {
    const selectedText = info.selectionText;
    
    // Check if a specific target language was selected via submenu
    let targetLangOverride = null;
    if (isSubmenuClick) {
      targetLangOverride = info.menuItemId.replace("shallott-lang-", "");
    }

    const runTranslation = () => {
      // Direct notification or automatic popup opening if supported,
      // or inject a clean absolute overlay bubble direct in page!
      if (chrome.scripting) {
        chrome.scripting.executeScript({
          target: { tabId: tab.id },
          func: displayInlineTranslationBubble,
          args: [selectedText]
        }).catch(err => {
          const action = chrome.action || chrome.browserAction;
          action.openPopup ? action.openPopup() : console.log("Translation stored, open extension window.");
        });
      } else {
        // MV2 fallback
        chrome.tabs.executeScript(tab.id, {
          code: `(${displayInlineTranslationBubble.toString()})(${JSON.stringify(selectedText)})`
        });
      }
    };

    // Prepare config to update in local storage
    const configToUpdate = { lastQueryText: selectedText };
    if (targetLangOverride) {
      configToUpdate.targetLang = targetLangOverride;
    }

    // Direct translation run after configuration updates
    chrome.storage.local.set(configToUpdate, () => {
      runTranslation();
    });
  }
});

// Content-script runner for injecting inline floating translation widget
function displayInlineTranslationBubble(text) {
  // To avoid duplicate bubbles
  const existingId = "shallott-bubble-widget";
  const oldBubble = document.getElementById(existingId);
  if (oldBubble) oldBubble.remove();

  // Create UI overlay
  const bubble = document.createElement("div");
  bubble.id = existingId;
  bubble.style.position = "fixed";
  
  // Try to place around selection coordinates
  const geom = window.getSelection().getRangeAt(0).getBoundingClientRect();
  const topPos = window.scrollY + geom.bottom + 8;
  const leftPos = window.scrollX + geom.left;

  bubble.style.top = `${Math.min(topPos, window.innerHeight - 200)}px`;
  bubble.style.left = `${Math.min(leftPos, window.innerWidth - 360)}px`;
  bubble.style.width = "340px";
  bubble.style.height = "auto";
  bubble.style.minHeight = "120px";
  bubble.style.backgroundColor = "#181c24";
  bubble.style.color = "#c9ceef";
  bubble.style.border = "1px solid #ffaa33";
  bubble.style.borderRadius = "8px";
  bubble.style.boxShadow = "0 8px 30px rgba(0,0,0,0.5)";
  bubble.style.padding = "10px";
  bubble.style.zIndex = "999999999";
  bubble.style.fontFamily = "'Segoe UI', system-ui, sans-serif";
  bubble.style.fontSize = "12px";

  // Make bubble resizable with CSS property
  bubble.style.resize = "both";
  bubble.style.overflow = "auto";

  // Create header container
  const header = document.createElement("div");
  header.id = "shallott-bubble-header";
  header.style.display = "flex";
  header.style.justifyContent = "space-between";
  header.style.alignItems = "center";
  header.style.borderBottom = "1px solid #2e3440";
  header.style.paddingBottom = "6px";
  header.style.marginBottom = "8px";
  header.style.cursor = "move";
  header.style.userSelect = "none";

  const titleSpan = document.createElement("span");
  titleSpan.style.fontWeight = "bold";
  titleSpan.style.color = "#ffaa33";
  titleSpan.style.pointerEvents = "none";
  titleSpan.textContent = "ShallotT Local Translation 🧅";

  const closeBtn = document.createElement("span");
  closeBtn.id = "shallott-close-btn";
  closeBtn.style.cursor = "pointer";
  closeBtn.style.padding = "2px 6px";
  closeBtn.style.fontWeight = "bold";
  closeBtn.style.userSelect = "none";
  closeBtn.textContent = "✕";

  header.appendChild(titleSpan);
  header.appendChild(closeBtn);
  bubble.appendChild(header);

  // Original text display
  const orgTextDiv = document.createElement("div");
  orgTextDiv.style.fontStyle = "italic";
  orgTextDiv.style.color = "#707a8a";
  orgTextDiv.style.marginBottom = "5px";
  orgTextDiv.style.maxHeight = "40px";
  orgTextDiv.style.overflow = "hidden";
  orgTextDiv.style.textOverflow = "ellipsis";
  orgTextDiv.style.whiteSpace = "nowrap";
  orgTextDiv.style.pointerEvents = "none";
  orgTextDiv.textContent = `"${text}"`;
  bubble.appendChild(orgTextDiv);

  // Translation result container
  const resultBox = document.createElement("div");
  resultBox.id = "shallott-bubble-result";
  resultBox.style.lineHeight = "1.5";
  resultBox.style.color = "#a6e3a1";
  resultBox.style.maxHeight = "180px";
  resultBox.style.overflowY = "auto";
  resultBox.style.wordBreak = "break-word";
  resultBox.style.whiteSpace = "pre-wrap";
  resultBox.textContent = "Traductions en cours...";
  bubble.appendChild(resultBox);

  // Bottom action bar
  const bottomBar = document.createElement("div");
  bottomBar.style.display = "flex";
  bottomBar.style.justifyContent = "space-between";
  bottomBar.style.alignItems = "center";
  bottomBar.style.marginTop = "8px";
  bottomBar.style.borderTop = "1px solid #2e3440";
  bottomBar.style.paddingTop = "6px";

  const btnContainer = document.createElement("div");
  btnContainer.style.display = "flex";
  btnContainer.style.gap = "6px";

  const copyBtn = document.createElement("button");
  copyBtn.id = "shallott-bubble-copy";
  copyBtn.style.background = "#585b70";
  copyBtn.style.color = "#cdd6f4";
  copyBtn.style.border = "none";
  copyBtn.style.borderRadius = "3px";
  copyBtn.style.padding = "3px 8px";
  copyBtn.style.fontSize = "10px";
  copyBtn.style.cursor = "pointer";
  copyBtn.title = "Copier la traduction";
  copyBtn.textContent = "📋 Copier";

  const replaceBtn = document.createElement("button");
  replaceBtn.id = "shallott-bubble-replace";
  replaceBtn.style.background = "#ffaa33";
  replaceBtn.style.color = "#000";
  replaceBtn.style.border = "none";
  replaceBtn.style.borderRadius = "3px";
  replaceBtn.style.padding = "3px 8px";
  replaceBtn.style.fontSize = "10px";
  replaceBtn.style.cursor = "pointer";
  replaceBtn.style.fontWeight = "bold";
  replaceBtn.title = "Remplacer le texte sélectionné par la traduction";
  replaceBtn.textContent = "🔄 Remplacer";

  btnContainer.appendChild(copyBtn);
  btnContainer.appendChild(replaceBtn);

  const apiLabel = document.createElement("div");
  apiLabel.style.fontSize = "9px";
  apiLabel.style.color = "#707a8a";
  apiLabel.style.pointerEvents = "none";
  apiLabel.textContent = "Gemma local API";

  bottomBar.appendChild(btnContainer);
  bottomBar.appendChild(apiLabel);
  bubble.appendChild(bottomBar);

  // Bubble internal layout (including checking storage for custom font settings)
  chrome.storage.local.get(['extFontSize', 'extFontFamily', 'extDyslexicMode'], (storedPrefs) => {
    let size = storedPrefs.extFontSize || 12;
    let family = storedPrefs.extFontFamily || "'Segoe UI', system-ui, sans-serif";
    const isDyslexic = storedPrefs.extDyslexicMode || false;

    if (isDyslexic) {
      size = Math.max(size, 15);
      family = "'Comic Sans MS', 'Chalkboard SE', cursive";
      bubble.style.backgroundColor = "#000000";
      bubble.style.color = "#ffffff";
      bubble.style.border = "3px solid #ffff00";
    }

    bubble.style.fontSize = `${size}px`;
    bubble.style.fontFamily = family;

    resultBox.style.fontSize = `${size}px`;
    resultBox.style.fontFamily = family;
    if (isDyslexic) {
      resultBox.style.color = "#ffff00";
      resultBox.style.fontWeight = "bold";
    }
  });

  document.body.appendChild(bubble);

  // Drag and drop mechanism for the floating widget
  let isDragging = false;
  let startX = 0;
  let startY = 0;
  let initialLeft = 0;
  let initialTop = 0;

  header.addEventListener("mousedown", (e) => {
    if (e.button !== 0 || e.target.id === "shallott-close-btn") return;
    
    // De-trigger drag on bottom-right corner resize handle clicks
    const rect = bubble.getBoundingClientRect();
    const handleThreshold = 18;
    if (e.clientX > rect.right - handleThreshold && e.clientY > rect.bottom - handleThreshold) {
      return; 
    }

    isDragging = true;
    startX = e.clientX;
    startY = e.clientY;
    initialLeft = rect.left;
    initialTop = rect.top;
    
    // Switch styling dynamically to absolute coordinate placement relative to viewport
    bubble.style.position = "fixed";
    bubble.style.margin = "0";
    
    e.preventDefault();
  });

  const onMouseMove = (e) => {
    if (!isDragging) return;
    const dx = e.clientX - startX;
    const dy = e.clientY - startY;
    bubble.style.left = `${initialLeft + dx}px`;
    bubble.style.top = `${initialTop + dy}px`;
  };

  const onMouseUp = () => {
    isDragging = false;
  };

  document.addEventListener("mousemove", onMouseMove);
  document.addEventListener("mouseup", onMouseUp);

  // Close event listener (clears also mouse listeners to avoid memory leak and cancels active translate)
  const currentTrackingId = "track-" + Date.now();

  closeBtn.addEventListener("click", () => {
    chrome.runtime.sendMessage({ action: "abort-translation", trackingId: currentTrackingId });
    document.removeEventListener("mousemove", onMouseMove);
    document.removeEventListener("mouseup", onMouseUp);
    bubble.remove();
  });
  
  // Close when clicking outside
  const outerClick = (e) => {
    if (!bubble.contains(e.target)) {
      chrome.runtime.sendMessage({ action: "abort-translation", trackingId: currentTrackingId });
      document.removeEventListener("mousemove", onMouseMove);
      document.removeEventListener("mouseup", onMouseUp);
      document.removeEventListener("mousedown", outerClick);
      bubble.remove();
    }
  };
  document.addEventListener("mousedown", outerClick);

  // Send message to background script to perform secure cross-origin fetch
  chrome.runtime.sendMessage({ action: "secure-translate", text: text, trackingId: currentTrackingId }, (response) => {
    const resContainer = document.getElementById("shallott-bubble-result");
    if (!resContainer) return;

    if (chrome.runtime.lastError) {
      if (chrome.runtime.lastError.message.includes("AbortedByUser")) return;
      resContainer.style.color = "#f38ba8";
      resContainer.textContent = `Erreur : ${chrome.runtime.lastError.message}`;
      return;
    }

    if (response && response.success) {
      resContainer.textContent = response.translation;

      // Copy Action
      if (copyBtn) {
        copyBtn.addEventListener("click", () => {
          navigator.clipboard.writeText(response.translation).then(() => {
            copyBtn.textContent = "✓ Copié !";
            setTimeout(() => { copyBtn.textContent = "📋 Copier"; }, 2000);
          }).catch(err => {
            alert("Erreur de copie de document : " + err);
          });
        });
      }

      // Replace Action
      if (replaceBtn) {
        replaceBtn.addEventListener("click", () => {
          try {
            const selection = window.getSelection();
            if (selection.rangeCount > 0) {
              const range = selection.getRangeAt(0);
              range.deleteContents();
              range.insertNode(document.createTextNode(response.translation));
              replaceBtn.textContent = "✓ Remplacé !";
              setTimeout(() => { replaceBtn.textContent = "🔄 Remplacer"; }, 2000);
            } else {
              alert("Aucune sélection active trouvée pour effectuer le remplacement.");
            }
          } catch (e) {
            alert("Remplacement non autorisé sur de l'input/champ natif complexe (essayez Ctrl+V à la place).");
          }
        });
      }
    } else {
      if (response && response.error === "AbortedByUser") return;
      resContainer.style.color = "#f38ba8";
      resContainer.textContent = `Erreur : ${response ? response.error : "Unknown background error"}`;
    }
  });
}
