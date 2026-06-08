/**
 * ShallotT – Content Script
 *
 * Injected into every page.  Responsibilities:
 *  - Return selected text when the background script asks for it
 *  - Display a floating overlay with loading / result / error states
 */

"use strict";

// ─── Message listener ─────────────────────────────────────────────────────────

chrome.runtime.onMessage.addListener((message, _sender, sendResponse) => {
  switch (message.type) {
    case "GET_SELECTION":
      sendResponse({ text: window.getSelection()?.toString()?.trim() ?? "" });
      break;
    case "SHOW_LOADING":
      overlay.showLoading();
      break;
    case "SHOW_RESULT":
      overlay.showResult(message.translation, message.original);
      break;
    case "SHOW_ERROR":
      overlay.showError(message.error);
      break;
  }
  return false; // synchronous response for GET_SELECTION
});

// ─── Overlay ──────────────────────────────────────────────────────────────────

const overlay = (() => {
  const DURATION_MS = 8000;
  let container = null;
  let timer = null;

  const CSS = `
    #shallott-overlay {
      all: initial;
      position: fixed;
      bottom: 24px;
      right: 24px;
      z-index: 2147483647;
      max-width: 420px;
      min-width: 220px;
      background: #1e1e2e;
      color: #cdd6f4;
      font-family: system-ui, sans-serif;
      font-size: 14px;
      border-radius: 10px;
      padding: 14px 16px 12px;
      box-shadow: 0 8px 32px rgba(0,0,0,0.5);
      border: 1px solid #45475a;
      line-height: 1.5;
      animation: shallott-fadein 0.2s ease;
    }
    @keyframes shallott-fadein {
      from { opacity: 0; transform: translateY(8px); }
      to   { opacity: 1; transform: translateY(0); }
    }
    #shallott-overlay .st-header {
      color: #89b4fa;
      font-weight: bold;
      font-size: 12px;
      margin-bottom: 6px;
      display: flex;
      justify-content: space-between;
      align-items: center;
    }
    #shallott-overlay .st-close {
      cursor: pointer;
      color: #6c7086;
      background: none;
      border: none;
      font-size: 16px;
      line-height: 1;
      padding: 0 0 0 8px;
    }
    #shallott-overlay .st-close:hover { color: #cdd6f4; }
    #shallott-overlay .st-original {
      color: #6c7086;
      font-size: 12px;
      margin-bottom: 6px;
      word-break: break-word;
    }
    #shallott-overlay .st-result {
      word-break: break-word;
    }
    #shallott-overlay.st-error .st-result { color: #f38ba8; }
  `;

  function ensureStyle() {
    if (document.getElementById("shallott-style")) return;
    const style = document.createElement("style");
    style.id = "shallott-style";
    style.textContent = CSS;
    document.head?.appendChild(style) ?? document.documentElement.appendChild(style);
  }

  function build() {
    ensureStyle();
    if (!container) {
      container = document.createElement("div");
      container.id = "shallott-overlay";
      document.documentElement.appendChild(container);
    }
    container.className = "";
    clearAutoClose();
  }

  function render(headerText, bodyHTML, isError = false) {
    build();
    if (isError) container.classList.add("st-error");
    container.innerHTML = `
      <div class="st-header">
        <span>🧅 ShallotT</span>
        <button class="st-close" title="Close">✕</button>
      </div>
      <div class="st-result">${bodyHTML}</div>
    `;
    container.querySelector(".st-close").addEventListener("click", hide);
    scheduleAutoClose();
  }

  function scheduleAutoClose() {
    clearAutoClose();
    timer = setTimeout(hide, DURATION_MS);
  }

  function clearAutoClose() {
    if (timer) { clearTimeout(timer); timer = null; }
  }

  function hide() {
    clearAutoClose();
    container?.remove();
    container = null;
  }

  return {
    showLoading() {
      render("ShallotT", "⏳ Translating…");
    },
    showResult(translation, original) {
      const esc = (s) =>
        s.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
      const snippet = original.length > 100 ? esc(original.slice(0, 100)) + "…" : esc(original);
      render(
        "ShallotT",
        `<div class="st-original">📝 ${snippet}</div>` +
        `<div>➡ ${esc(translation)}</div>`,
      );
    },
    showError(msg) {
      render("ShallotT", `⚠ ${msg}`, true);
    },
  };
})();
