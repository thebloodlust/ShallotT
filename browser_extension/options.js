/**
 * ShallotT – Options / settings page script
 */

"use strict";

const FIELDS = ["ollamaHost", "model", "targetLanguage", "timeout"];

const DEFAULT_SETTINGS = {
  ollamaHost: "http://192.168.1.100:11434",
  model: "gemma3:8b-instruct-q4_K_M",
  targetLanguage: "en",
  timeout: 60000,
};

// Load saved settings into form fields
chrome.storage.sync.get(DEFAULT_SETTINGS, (items) => {
  for (const key of FIELDS) {
    const el = document.getElementById(key);
    if (el) el.value = items[key] ?? "";
  }
});

document.getElementById("save").addEventListener("click", () => {
  const values = {};
  for (const key of FIELDS) {
    const el = document.getElementById(key);
    if (!el) continue;
    values[key] = key === "timeout" ? Number(el.value) : el.value.trim();
  }
  chrome.storage.sync.set(values, () => {
    const status = document.getElementById("status");
    status.textContent = "✓ Saved!";
    setTimeout(() => { status.textContent = ""; }, 2000);
  });
});
