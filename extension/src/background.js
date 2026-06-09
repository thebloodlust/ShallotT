// Background service worker for Chrome/Firefox Extension

// Intercept and bypass CORS both at Request (Ollama check) and Response (Browser check) levels
if (chrome.webRequest) {
  // 1. Overwrite Origin / Referer of requests going to Ollama to make it believe we are a simple local curl/localhost call
  chrome.webRequest.onBeforeSendHeaders.addListener(
    function(details) {
      let isOllamaMatch = details.url.includes("11434") || details.url.includes("/api/generate") || details.url.includes("/api/tags");
      if (isOllamaMatch) {
        let headers = details.requestHeaders;
        let originIndex = -1;
        let refererIndex = -1;
        for (let i = 0; i < headers.length; i++) {
          let nameLower = headers[i].name.toLowerCase();
          if (nameLower === "origin") originIndex = i;
          if (nameLower === "referer") refererIndex = i;
        }

        // Change or insert the Origin to http://localhost:11434 to make Ollama happy (it passes all checks)
        if (originIndex !== -1) {
          headers[originIndex].value = "http://localhost:11434";
        } else {
          headers.push({ name: "Origin", value: "http://localhost:11434" });
        }

        if (refererIndex !== -1) {
          headers[refererIndex].value = "http://localhost:11434/";
        } else {
          headers.push({ name: "Referer", value: "http://localhost:11434/" });
        }

        return { requestHeaders: headers };
      }
    },
    { urls: ["<all_urls>"] },
    ["blocking", "requestHeaders"]
  );

  // 2. Allow everything at the browser inspection level by injecting wildcard Access-Control-Allow-Origin headers
  chrome.webRequest.onHeadersReceived.addListener(
    function(details) {
      let isOllamaMatch = details.url.includes("11434") || details.url.includes("/api/generate") || details.url.includes("/api/tags");
      if (isOllamaMatch) {
        let headers = details.responseHeaders;
        let hasAcao = false;
        let hasAcah = false;
        
        for (let i = 0; i < headers.length; i++) {
          let nameLower = headers[i].name.toLowerCase();
          if (nameLower === "access-control-allow-origin") {
            headers[i].value = "*";
            hasAcao = true;
          }
          if (nameLower === "access-control-allow-headers") {
            headers[i].value = "Authorization, Content-Type, User-Agent, Accept";
            hasAcah = true;
          }
        }

        if (!hasAcao) {
          headers.push({ name: "Access-Control-Allow-Origin", value: "*" });
        }
        if (!hasAcah) {
          headers.push({ name: "Access-Control-Allow-Headers", value: "Authorization, Content-Type, User-Agent, Accept" });
        }

        return { responseHeaders: headers };
      }
    },
    { urls: ["<all_urls>"] },
    ["blocking", "responseHeaders"]
  );
}

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

    // Read stored language to perform smart target language auto-swap if source text matches target language
    chrome.storage.local.get(['targetLang'], (stored) => {
      const activeTarget = targetLangOverride || stored.targetLang || "French";
      const isEnglish = detectIsEnglishHeuristic(selectedText);
      const isFrench = detectIsFrenchHeuristic(selectedText);
      
      if (isEnglish && activeTarget === "English") {
        configToUpdate.targetLang = "French";
      } else if (isFrench && activeTarget === "French") {
        configToUpdate.targetLang = "English";
      }

      chrome.storage.local.set(configToUpdate, () => {
        runTranslation();
      });
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

    const resultBox = document.getElementById("shallott-bubble-result");
    if (resultBox) {
      resultBox.style.fontSize = `${size}px`;
      resultBox.style.fontFamily = family;
      if (isDyslexic) {
        resultBox.style.color = "#ffff00";
        resultBox.style.fontWeight = "bold";
      }
    }
  });

  bubble.innerHTML = `
    <div id="shallott-bubble-header" style="display:flex; justify-content:space-between; align-items:center; border-bottom:1px solid #2e3440; padding-bottom:6px; margin-bottom:8px; cursor:move; user-select:none;">
      <span style="font-weight:bold; color:#ffaa33; pointer-events:none;">ShallotT Local Translation 🧅</span>
      <span id="shallott-close-btn" style="cursor:pointer; padding:2px 6px; font-weight:bold; user-select:none;">✕</span>
    </div>
    <div style="font-style:italic; color:#707a8a; margin-bottom:5px; max-height:40px; overflow:hidden; text-overflow:ellipsis; white-space:nowrap; pointer-events:none;">"${text}"</div>
    <div id="shallott-bubble-result" style="line-height:1.5; color:#a6e3a1; max-height:180px; overflow-y:auto; word-break:break-word; white-space:pre-wrap;">Traductions en cours...</div>
    <div style="display:flex; justify-content:flex-end; margin-top:8px; font-size:10px; color:#707a8a; pointer-events:none;">Gemma local API</div>
  `;

  document.body.appendChild(bubble);

  // Drag and drop mechanism for the floating widget
  const header = document.getElementById("shallott-bubble-header");
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

  document.getElementById("shallott-close-btn").addEventListener("click", () => {
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
    } else {
      if (response && response.error === "AbortedByUser") return;
      resContainer.style.color = "#f38ba8";
      resContainer.textContent = `Erreur : ${response ? response.error : "Unknown background error"}`;
    }
  });
}
