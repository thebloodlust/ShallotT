/**
 * ShallotT – Popup script
 *
 * Allows the user to type or paste text in the popup and translate it
 * immediately using the configured Ollama endpoint.
 */

"use strict";

const DEFAULT_SETTINGS = {
  ollamaHost: "http://192.168.1.100:11434",
  model: "gemma3:8b-instruct-q4_K_M",
  targetLanguage: "en",
  timeout: 60000,
};

const inputEl = document.getElementById("input");
const btnEl = document.getElementById("btn");
const resultEl = document.getElementById("result");
const settingsLink = document.getElementById("settings-link");

// Pre-fill with current selection on the active tab
chrome.tabs.query({ active: true, currentWindow: true }, ([tab]) => {
  if (!tab?.id) return;
  chrome.tabs.sendMessage(tab.id, { type: "GET_SELECTION" }, (resp) => {
    if (chrome.runtime.lastError) return;
    if (resp?.text) inputEl.value = resp.text;
  });
});

btnEl.addEventListener("click", () => translate());

inputEl.addEventListener("keydown", (e) => {
  if (e.key === "Enter" && (e.ctrlKey || e.metaKey)) translate();
});

settingsLink.addEventListener("click", () => {
  chrome.runtime.openOptionsPage();
});

async function translate() {
  const text = inputEl.value.trim();
  if (!text) return;

  btnEl.disabled = true;
  resultEl.className = "";
  resultEl.textContent = "⏳ Translating…";

  const settings = await loadSettings();

  try {
    const result = await callOllama(text, settings);
    resultEl.textContent = result;
  } catch (err) {
    resultEl.textContent = `⚠ ${err.message}`;
    resultEl.className = "error";
  } finally {
    btnEl.disabled = false;
  }
}

async function callOllama(text, settings) {
  const { ollamaHost, model, targetLanguage, timeout } = settings;
  const url = `${ollamaHost.replace(/\/$/, "")}/api/chat`;

  const system =
    `You are a professional translator. ` +
    `Translate the user's text into ${targetLanguage}. ` +
    `Return ONLY the translated text.`;

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
          { role: "system", content: system },
          { role: "user", content: text },
        ],
        stream: false,
      }),
      signal: controller.signal,
    });
  } finally {
    clearTimeout(timer);
  }

  if (!response.ok) throw new Error(`Ollama error: HTTP ${response.status}`);
  const data = await response.json();
  return data?.message?.content?.trim() ?? "(empty response)";
}

function loadSettings() {
  return new Promise((resolve) => {
    chrome.storage.sync.get(DEFAULT_SETTINGS, (items) => resolve(items));
  });
}
