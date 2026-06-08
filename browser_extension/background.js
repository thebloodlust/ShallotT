/**
 * ShallotT – Background Service Worker (Manifest V3)
 *
 * Responsibilities:
 *  - Create the right-click "Translate with ShallotT" context menu
 *  - Handle the keyboard shortcut command
 *  - Query the remote Ollama API and relay results to the content script
 */

"use strict";

// ─── Defaults ────────────────────────────────────────────────────────────────

const DEFAULT_SETTINGS = {
  ollamaHost: "http://192.168.1.100:11434",
  model: "gemma3:8b-instruct-q4_K_M",
  targetLanguage: "en",
  timeout: 60000,
};

// ─── Initialisation ───────────────────────────────────────────────────────────

chrome.runtime.onInstalled.addListener(() => {
  chrome.contextMenus.create({
    id: "shallott-translate",
    title: "Translate with ShallotT",
    contexts: ["selection"],
  });
});

// ─── Context-menu click ───────────────────────────────────────────────────────

chrome.contextMenus.onClicked.addListener((info, tab) => {
  if (info.menuItemId === "shallott-translate" && info.selectionText) {
    handleTranslate(info.selectionText, tab.id);
  }
});

// ─── Keyboard shortcut ────────────────────────────────────────────────────────

chrome.commands.onCommand.addListener(async (command) => {
  if (command !== "translate-selection") return;

  const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
  if (!tab?.id) return;

  // Retrieve the current selection from the content script
  chrome.tabs.sendMessage(tab.id, { type: "GET_SELECTION" }, (response) => {
    if (chrome.runtime.lastError || !response?.text) return;
    handleTranslate(response.text, tab.id);
  });
});

// ─── Core translation flow ────────────────────────────────────────────────────

async function handleTranslate(text, tabId) {
  const settings = await loadSettings();

  // Tell the content script to show a loading indicator
  safeSendMessage(tabId, { type: "SHOW_LOADING" });

  let translation;
  try {
    translation = await translateWithOllama(text, settings);
  } catch (err) {
    safeSendMessage(tabId, {
      type: "SHOW_ERROR",
      error: err.message || String(err),
    });
    return;
  }

  safeSendMessage(tabId, {
    type: "SHOW_RESULT",
    original: text,
    translation,
  });
}

// ─── Ollama API call ──────────────────────────────────────────────────────────

async function translateWithOllama(text, settings) {
  const { ollamaHost, model, targetLanguage, timeout } = settings;
  const url = `${ollamaHost.replace(/\/$/, "")}/api/chat`;

  const systemPrompt =
    `You are a professional translator. ` +
    `Translate the user's text into ${targetLanguage}. ` +
    `Return ONLY the translated text – no explanations, no labels.`;

  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), timeout);

  let response;
  try {
    response = await fetch(url, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        model,
        messages: [
          { role: "system", content: systemPrompt },
          { role: "user", content: text },
        ],
        stream: false,
      }),
      signal: controller.signal,
    });
  } finally {
    clearTimeout(timer);
  }

  if (!response.ok) {
    throw new Error(`Ollama responded with HTTP ${response.status}`);
  }

  const data = await response.json();
  return data?.message?.content?.trim() ?? "";
}

// ─── Helpers ──────────────────────────────────────────────────────────────────

async function loadSettings() {
  return new Promise((resolve) => {
    chrome.storage.sync.get(DEFAULT_SETTINGS, (items) => resolve(items));
  });
}

function safeSendMessage(tabId, message) {
  chrome.tabs.sendMessage(tabId, message, () => {
    // Silently swallow "no listener" errors
    void chrome.runtime.lastError;
  });
}
