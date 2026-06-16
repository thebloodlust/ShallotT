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
    chrome.storage.local.get(['ollamaUrl', 'ollamaModel', 'ollamaApiKey', 'targetLang', '_contextLang', 'maxCharacters'], async (stored) => {
      const url = normalizeUrl(stored.ollamaUrl);
      const model = stored.ollamaModel || "gemma:latest";
      const key = stored.ollamaApiKey || "";
      // One-shot context menu override, cleared after use
      const targetL = stored._contextLang || stored.targetLang || "French";
      const maxChars = stored.maxCharacters || 10000;
      // Clear the one-shot override so next translation uses the user's preference
      if (stored._contextLang) {
        chrome.storage.local.remove('_contextLang');
      }

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
  } else if (request.action === "translate-page-batch") {
    // Batch-translate an array of texts for full-page translation
    const texts = request.texts || [];
    if (texts.length === 0) {
      sendResponse({ translations: [] });
      return;
    }

    // Use ||| as delimiter — more likely to be preserved by models
    const DELIM = ' ||| ';
    const combined = texts.join(DELIM);

    chrome.storage.local.get(['ollamaUrl', 'ollamaModel', 'ollamaApiKey', 'targetLang'], (settings) => {
      const url = (settings.ollamaUrl || 'http://localhost:11434').replace(/\/$/, '');
      const model = settings.ollamaModel || 'gemma:latest';
      const apiKey = settings.ollamaApiKey || '';
      const targetLang = settings.targetLang || 'French';

      const headers = { 'Content-Type': 'application/json' };
      if (apiKey) headers['Authorization'] = `Bearer ${apiKey}`;

      const body = JSON.stringify({
        model: model,
        prompt: `Translate each of the following texts to ${targetLang}. Return ONLY the translations, one per line, in the same order. Do NOT add any commentary, numbering, or prefixes. Here are the texts:\n\n${combined}`,
        stream: false,
        options: { temperature: 0.1 }
      });

      fetch(`${url}/api/generate`, { method: 'POST', headers, body })
        .then(r => r.json())
        .then(data => {
          const response = data.response || '';
          // Split by newlines and filter empty lines
          let translations = response.split('\n')
            .map(s => s.trim())
            .filter(s => s.length > 0)
            // Remove common prefixes like "1. ", "- ", etc.
            .map(s => s.replace(/^\d+[\.\)]\s*/, '').replace(/^[-•]\s*/, ''));
          // Pad with originals if we got fewer translations
          while (translations.length < texts.length) {
            translations.push(texts[translations.length] || '');
          }
          sendResponse({ translations: translations.slice(0, texts.length) });
        })
        .catch(err => {
          console.log('[ShallotT] Page translate error:', err.message);
          sendResponse({ error: err.message, translations: texts });
        });
    });
    return true; // async
  } else if (request.action === "translate-big-batch") {
    // Big-batch translation (30 texts at once) — bypasses character limits
    const text = request.text || '';
    const count = request.count || 1;
    if (!text.trim()) { sendResponse({ success: false }); return; }

    chrome.storage.local.get(['ollamaUrl', 'ollamaModel', 'ollamaApiKey', 'targetLang', '_contextLang'], (settings) => {
      const url = (settings.ollamaUrl || 'http://localhost:11434').replace(/\/$/, '');
      const model = settings.ollamaModel || 'gemma:latest';
      const apiKey = settings.ollamaApiKey || '';
      const targetLang = settings._contextLang || settings.targetLang || 'French';
      if (settings._contextLang) chrome.storage.local.remove('_contextLang');
      const headers = { 'Content-Type': 'application/json' };
      if (apiKey) headers['Authorization'] = `Bearer ${apiKey}`;

      // No token limit — use num_predict: -1 for unlimited
      fetch(`${url}/api/generate`, {
        method: 'POST', headers,
        body: JSON.stringify({
          model, stream: false,
          prompt: `Translate each numbered line to ${targetLang}. Keep the [N] prefix on each translation. Output NOTHING else:\n\n${text}`,
          options: { temperature: 0.1, num_predict: 4096 }
        })
      })
      .then(r => r.json())
      .then(data => {
        const raw = data.response || '';
        // Parse: extract [N] prefixed lines
        const translations = [];
        const lines = raw.split('\n');
        for (const line of lines) {
          const m = line.match(/^\[(\d+)\]\s*(.+)/);
          if (m) {
            const idx = parseInt(m[1]);
            translations[idx] = m[2].trim();
          }
        }
        // Fill gaps (filter out undefined)
        const result = [];
        for (let i = 0; i < count; i++) {
          result.push(translations[i] || '');
        }
        sendResponse({ success: true, translations: result });
      })
      .catch(err => {
        console.log('[ShallotT] Big batch failed:', err.message);
        sendResponse({ success: false, error: err.message });
      });
    });
    return true; // async
  } else if (request.action === "secure-translate-page") {
    // Single-text translation for full-page translate (reuses existing pipeline)
    const text = request.text || '';
    if (!text.trim()) {
      sendResponse({ success: false, error: 'Empty text' });
      return;
    }
    chrome.storage.local.get(['ollamaUrl', 'ollamaModel', 'ollamaApiKey', 'targetLang'], (settings) => {
      const url = (settings.ollamaUrl || 'http://localhost:11434').replace(/\/$/, '');
      const model = settings.ollamaModel || 'gemma:latest';
      const apiKey = settings.ollamaApiKey || '';
      const targetLang = settings.targetLang || 'French';
      const headers = { 'Content-Type': 'application/json' };
      if (apiKey) headers['Authorization'] = `Bearer ${apiKey}`;
      fetch(`${url}/api/generate`, {
        method: 'POST', headers,
        body: JSON.stringify({
          model, stream: false,
          prompt: `Translate the following text to ${targetLang}. Return ONLY the translation, no commentary:\n\n${text}`,
          options: { temperature: 0.1 }
        })
      })
      .then(r => r.json())
      .then(data => sendResponse({ success: true, translation: (data.response || text).trim() }))
      .catch(err => sendResponse({ success: false, error: err.message }));
    });
    return true; // async
  } else if (request.action === "capture-tab") {
    // Capture the active tab as a data URL for OCR processing
    chrome.tabs.captureVisibleTab(null, { format: 'png' }, (dataUrl) => {
      sendResponse({ dataUrl: dataUrl || null });
    });
    return true; // async sendResponse
  } else if (request.action === "ocr-result") {
    // OCR content script returned text — translate it
    const text = request.text;
    if (text && text.trim()) {
      chrome.storage.local.set({ lastQueryText: text }, () => {
        chrome.tabs.query({ active: true, currentWindow: true }, (tabs) => {
          if (tabs[0] && tabs[0].id) {
            if (chrome.scripting) {
              chrome.scripting.executeScript({
                target: { tabId: tabs[0].id },
                func: displayInlineTranslationBubble,
                args: [text]
              }).catch(() => {});
            } else {
              chrome.tabs.executeScript(tabs[0].id, {
                code: `(${displayInlineTranslationBubble.toString()})(${JSON.stringify(text)})`
              });
            }
          }
        });
      });
    }
  } else if (request.action === "quick-lang-key") {
    // Received the letter key from the injected quick-lang listener
    const key = request.key;
    if (!key) return; // User pressed Escape or timeout

    chrome.storage.local.get(['quickLangMap', 'quickTransSel'], (res) => {
      const defaultMap = { e: 'English', f: 'French', s: 'Spanish', g: 'German', i: 'Italian', p: 'Portuguese', c: 'Chinese', j: 'Japanese', r: 'Russian' };
      const rawMap = res.quickLangMap || '';
      const userMap = parseQuickLangMap(rawMap) || defaultMap;
      const targetLang = userMap[key.toLowerCase()];
      const selectedText = res.quickTransSel || '';

      if (targetLang && selectedText) {
        chrome.storage.local.set({ targetLang: targetLang, lastQueryText: selectedText }, () => {
          chrome.tabs.query({ active: true, currentWindow: true }, (tabs) => {
            if (tabs[0] && tabs[0].id) {
              if (chrome.scripting) {
                chrome.scripting.executeScript({
                  target: { tabId: tabs[0].id },
                  func: displayInlineTranslationBubble,
                  args: [selectedText]
                }).catch(() => {});
              } else {
                chrome.tabs.executeScript(tabs[0].id, {
                  code: `(${displayInlineTranslationBubble.toString()})(${JSON.stringify(selectedText)})`
                });
              }
            }
          });
        });
      }
    });
  } else if (request.action === "auto-detect-translate") {
    // User clicked the floating "Translate?" button — show the inline translation
    // bubble using the SAME injection path as the right-click context menu.
    const text = request.text;
    if (!text) return;

    const injectBubble = (tabId) => {
      if (tabId == null) return;
      chrome.storage.local.set({ lastQueryText: text }, () => {
        // MV3: must use chrome.scripting (chrome.tabs.executeScript does not exist
        // in a service worker). Injects the same draggable bubble as right-click.
        chrome.scripting.executeScript({
          target: { tabId: tabId },
          func: displayInlineTranslationBubble,
          args: [text]
        }).catch(() => {});
      });
    };

    if (sender && sender.tab && sender.tab.id != null) {
      injectBubble(sender.tab.id);
    } else {
      chrome.tabs.query({ active: true, currentWindow: true }, (tabs) => {
        injectBubble(tabs && tabs[0] ? tabs[0].id : null);
      });
    }
  }
});

// NOTE: the auto-detect "Traduire?" listener is now injected declaratively via
// content_scripts (src/autodetect.js) in the manifest. The old programmatic
// injection was removed (it duplicated the declarative injection).

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
              // Show inline translation bubble (same as right-click)
              chrome.storage.local.set({ lastQueryText: selectedText }, () => {
                chrome.scripting.executeScript({
                  target: { tabId: tabs[0].id },
                  func: displayInlineTranslationBubble,
                  args: [selectedText]
                }).catch(() => {});
              });
            }
          });
        } else {
          // MV2 Fallback for tabs injection
          chrome.tabs.executeScript(tabs[0].id, {
            code: "window.getSelection().toString()"
          }, (res) => {
            if (res && res[0]) {
              const selectedText = res[0];
              chrome.storage.local.set({ lastQueryText: selectedText }, () => {
                chrome.tabs.executeScript(tabs[0].id, {
                  code: `(${displayInlineTranslationBubble.toString()})(${JSON.stringify(selectedText)})`
                });
              });
            }
          });
        }
      }
    });
  } else if (command === "quick-translate") {
    // Two-step shortcut: Ctrl+F9 then a letter for quick language selection
    chrome.tabs.query({ active: true, currentWindow: true }, (tabs) => {
      if (tabs[0] && tabs[0].id) {
        const injectListener = () => {
          if (chrome.scripting) {
            chrome.scripting.executeScript({
              target: { tabId: tabs[0].id },
              func: injectQuickLangListener
            }).catch(() => {});
          } else {
            chrome.tabs.executeScript(tabs[0].id, {
              code: `(${injectQuickLangListener.toString()})()`
            });
          }
        };
        // Get selection text first, store it, then inject the key listener
        if (chrome.scripting) {
          chrome.scripting.executeScript({
            target: { tabId: tabs[0].id },
            func: () => window.getSelection().toString()
          }, (res) => {
            if (res && res[0] && res[0].result) {
              chrome.storage.local.set({ quickTransSel: res[0].result }, injectListener);
            } else {
              injectListener();
            }
          });
        } else {
          // MV2 fallback
          chrome.tabs.executeScript(tabs[0].id, {
            code: "window.getSelection().toString()"
          }, (res) => {
            if (res && res[0]) {
              chrome.storage.local.set({ quickTransSel: res[0] }, injectListener);
            } else {
              injectListener();
            }
          });
        }
      }
    });
  } else if (command === "ocr-screenshot") {
    // Inject Tesseract.js first, then OCR overlay (same isolated world, shared global)
    chrome.tabs.query({ active: true, currentWindow: true }, (tabs) => {
      if (!tabs[0] || !tabs[0].id) return;
      chrome.scripting.executeScript({
        target: { tabId: tabs[0].id },
        files: ['src/lib/tesseract.min.js', 'src/ocr_content.js']
      }).catch(err => {
        console.log("[ShallotT] OCR injection failed:", err.message);
      });
    });
  } else if (command === "translate-page") {
    // Full page translation — inject content script
    chrome.tabs.query({ active: true, currentWindow: true }, (tabs) => {
      if (!tabs[0] || !tabs[0].id) return;
      chrome.scripting.executeScript({
        target: { tabId: tabs[0].id },
        files: ['src/translate_page.js']
      }).catch(err => {
        console.log("[ShallotT] Page translate injection failed:", err.message);
      });
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

    // Use the override for THIS translation only — don't permanently change targetLang
    const configToUpdate = { lastQueryText: selectedText };
    if (targetLangOverride) {
      configToUpdate._contextLang = targetLangOverride; // one-shot, cleared after use
    }

    chrome.storage.local.set(configToUpdate, () => {
      runTranslation();
    });
  }
});

// Parse the user's quick-lang mapping string: "E=English, F=French, ..."
function parseQuickLangMap(raw) {
  if (!raw || typeof raw !== 'string') return null;
  const map = {};
  const pairs = raw.split(',');
  for (const pair of pairs) {
    const trimmed = pair.trim();
    const eqIdx = trimmed.indexOf('=');
    if (eqIdx > 0) {
      const key = trimmed.substring(0, eqIdx).trim().toLowerCase();
      const lang = trimmed.substring(eqIdx + 1).trim();
      if (key.length === 1 && lang) {
        map[key] = lang;
      }
    }
  }
  return Object.keys(map).length > 0 ? map : null;
}

// Injected into the page by the quick-translate command (Ctrl+F9).
// Shows a small indicator and listens for a single letter keypress
// to select the target language.
function injectQuickLangListener() {
  const old = document.getElementById('shallott-quicklang-indicator');
  if (old) old.remove();

  const indicator = document.createElement('div');
  indicator.id = 'shallott-quicklang-indicator';
  indicator.style.cssText = 'position:fixed;top:12px;right:12px;background:#181c24;color:#ffaa33;padding:10px 16px;border:2px solid #ffaa33;border-radius:8px;z-index:999999999;font-size:13px;font-family:"Segoe UI",system-ui,sans-serif;box-shadow:0 4px 20px rgba(0,0,0,0.5);pointer-events:none;';
  indicator.textContent = '🎯 Appuyez sur une lettre pour la langue cible… (Échap pour annuler)';
  document.body.appendChild(indicator);

  const handler = function(e) {
    if (e.target.tagName === 'INPUT' || e.target.tagName === 'TEXTAREA' || e.target.isContentEditable) return;
    var key = e.key.toLowerCase();
    if (key.length === 1 && key >= 'a' && key <= 'z') {
      e.preventDefault();
      e.stopPropagation();
      document.removeEventListener('keydown', handler, true);
      document.removeEventListener('keydown', escHandler, true);
      indicator.remove();
      chrome.runtime.sendMessage({ action: 'quick-lang-key', key: key });
    }
  };

  var escHandler = function(e) {
    if (e.key === 'Escape') {
      document.removeEventListener('keydown', handler, true);
      document.removeEventListener('keydown', escHandler, true);
      indicator.remove();
      chrome.runtime.sendMessage({ action: 'quick-lang-key', key: null });
    }
  };

  document.addEventListener('keydown', handler, true);
  document.addEventListener('keydown', escHandler, true);

  setTimeout(function() {
    document.removeEventListener('keydown', handler, true);
    document.removeEventListener('keydown', escHandler, true);
    if (indicator.parentNode) indicator.remove();
  }, 8000);
}

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
  
  // Place around the selection. The bubble is position:fixed, so coordinates
  // are VIEWPORT-relative — never add scrollX/scrollY (that pushes it off-screen
  // on scrolled pages). getBoundingClientRect() is already viewport-relative.
  // Fall back to a fixed viewport position if the selection is gone.
  let topPos = 90;
  let leftPos = 90;
  try {
    const sel = window.getSelection();
    if (sel && sel.rangeCount > 0) {
      const geom = sel.getRangeAt(0).getBoundingClientRect();
      if (geom && (geom.width || geom.height || geom.top)) {
        topPos = geom.bottom + 8;
        leftPos = geom.left;
      }
    }
  } catch (e) { /* keep fallback position */ }

  bubble.style.top = `${Math.max(8, Math.min(topPos, window.innerHeight - 200))}px`;
  bubble.style.left = `${Math.max(8, Math.min(leftPos, window.innerWidth - 360))}px`;
  bubble.style.boxSizing = "border-box";
  bubble.style.width = "340px";
  bubble.style.height = "auto";
  bubble.style.minWidth = "260px";
  bubble.style.minHeight = "120px";
  bubble.style.maxWidth = "calc(100vw - 20px)";
  bubble.style.maxHeight = "calc(100vh - 20px)";
  bubble.style.backgroundColor = "#181c24";
  bubble.style.color = "#c9ceef";
  bubble.style.border = "1px solid #ffaa33";
  bubble.style.borderRadius = "8px";
  bubble.style.boxShadow = "0 8px 30px rgba(0,0,0,0.5)";
  bubble.style.padding = "10px";
  bubble.style.zIndex = "999999999";
  bubble.style.fontFamily = "'Segoe UI', system-ui, sans-serif";
  bubble.style.fontSize = "12px";

  // Make bubble resizable with CSS property; flex layout lets the
  // translation result grow to fill the extra space on resize while
  // keeping the header and action buttons pinned and visible.
  bubble.style.resize = "both";
  bubble.style.overflow = "hidden";
  bubble.style.display = "flex";
  bubble.style.flexDirection = "column";

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
  resultBox.style.flex = "1";
  resultBox.style.minHeight = "0";
  resultBox.style.minWidth = "0";
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
