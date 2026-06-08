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

// Set up Context Menu item on installation
chrome.runtime.onInstalled.addListener(() => {
  chrome.contextMenus.create({
    id: "shallott-translate-selection",
    title: "Traduire avec ShallotT Local",
    contexts: ["selection"]
  });

  // Setup default values in storage
  chrome.storage.local.get(['ollamaUrl', 'ollamaModel', 'targetLang'], (result) => {
    if (!result.ollamaUrl) chrome.storage.local.set({ ollamaUrl: DEFAULT_URL });
    if (!result.ollamaModel) chrome.storage.local.set({ ollamaModel: DEFAULT_MODEL });
    if (!result.targetLang) chrome.storage.local.set({ targetLang: "French" });
  });
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
    chrome.storage.local.get(['ollamaUrl', 'ollamaModel', 'ollamaApiKey', 'targetLang'], async (stored) => {
      const url = normalizeUrl(stored.ollamaUrl);
      const model = stored.ollamaModel || "gemma:latest";
      const key = stored.ollamaApiKey || "";
      const targetL = stored.targetLang || "French";

      const promptContext = `Translate the following text into ${targetL}.`;
      const fullPrompt = `<start_of_turn>user\nYou are a professional, high-performance translator like DeepL. Translate the text accurately. Preserve the original formatting, paragraph breaks, tone, and style.\nCRITICAL: Do not write any explanations, summaries, preamble, warning, notes, or code blocks. Just output the translation directly.\n\nInstruction: ${promptContext}\n\nText to translate:\n${request.text}\n<start_of_turn>model\n`;

      try {
        const headers = { "Content-Type": "application/json" };
        if (key) headers["Authorization"] = `Bearer ${key}`;

        const response = await fetch(`${url}/api/generate`, {
          method: "POST",
          headers: headers,
          body: JSON.stringify({
            model: model,
            prompt: fullPrompt,
            stream: false,
            options: { temperature: 0.2, top_p: 0.9, num_predict: 2048 }
          })
        });

        if (!response.ok) throw new Error(`HTTP ${response.status}`);
        const result = await response.json();
        const translation = result.response ? result.response.trim() : "Empty response";
        sendResponse({ success: true, translation: translation });
      } catch (err) {
        sendResponse({ success: false, error: err.message });
      }
    });
    return true; // Keep sendResponse channel active
  } else if (request.action === "get-models") {
    const url = normalizeUrl(request.url);
    const key = request.key || "";
    const headers = {};
    if (key) headers["Authorization"] = `Bearer ${key}`;

    fetch(`${url}/api/tags`, { method: "GET", headers: headers })
      .then(response => {
        if (!response.ok) throw new Error(`HTTP ${response.status}`);
        return response.json();
      })
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
  if (info.menuItemId === "shallott-translate-selection" && info.selectionText) {
    const selectedText = info.selectionText;
    
    // Store selected text into local extension memory
    chrome.storage.local.set({ lastQueryText: selectedText }, () => {
      // Direct notification or automatic popup opening if supported,
      // or inject an clean absolute overlay bubble direct in page!
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
  bubble.style.backgroundColor = "#181c24";
  bubble.style.color = "#c9ceef";
  bubble.style.border = "1px solid #ffaa33";
  bubble.style.borderRadius = "8px";
  bubble.style.boxShadow = "0 8px 30px rgba(0,0,0,0.5)";
  bubble.style.padding = "10px";
  bubble.style.zIndex = "999999999";
  bubble.style.fontFamily = "'Segoe UI', system-ui, sans-serif";
  bubble.style.fontSize = "12px";

  // Bubble internal layout
  bubble.innerHTML = `
    <div style="display:flex; justify-content:space-between; align-items:center; border-bottom:1px solid #2e3440; padding-bottom:6px; margin-bottom:8px;">
      <span style="font-weight:bold; color:#ffaa33;">ShallotT Local Translation</span>
      <span id="shallott-close-btn" style="cursor:pointer; padding:2px 6px; font-weight:bold;">✕</span>
    </div>
    <div style="font-style:italic; color:#707a8a; margin-bottom:5px; max-height:40px; overflow:hidden; text-overflow:ellipsis; white-space:nowrap;">"${text}"</div>
    <div id="shallott-bubble-result" style="line-height:1.5; color:#a6e3a1; max-height:180px; overflow-y:auto; word-break:break-word;">Traductions en cours...</div>
    <div style="display:flex; justify-content:flex-end; margin-top:8px; font-size:10px; color:#707a8a;">Gemma local API</div>
  `;

  document.body.appendChild(bubble);

  // Close event listener
  document.getElementById("shallott-close-btn").addEventListener("click", () => bubble.remove());
  
  // Close when clicking outside
  const outerClick = (e) => {
    if (!bubble.contains(e.target)) {
      bubble.remove();
      document.removeEventListener("mousedown", outerClick);
    }
  };
  document.addEventListener("mousedown", outerClick);

  // Send message to background script to perform secure cross-origin fetch
  chrome.runtime.sendMessage({ action: "secure-translate", text: text }, (response) => {
    const resContainer = document.getElementById("shallott-bubble-result");
    if (!resContainer) return;

    if (chrome.runtime.lastError) {
      resContainer.style.color = "#f38ba8";
      resContainer.textContent = `Erreur : ${chrome.runtime.lastError.message}`;
      return;
    }

    if (response && response.success) {
      resContainer.textContent = response.translation;
    } else {
      resContainer.style.color = "#f38ba8";
      resContainer.textContent = `Erreur : ${response ? response.error : "Unknown background error"}`;
    }
  });
}
