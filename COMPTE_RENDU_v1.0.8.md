# Compte-rendu technique — ShallotT Extension v1.0.8

## Contexte

ShallotT est une extension Firefox/Chrome qui traduit du texte via Ollama (LLM local, modèle Gemma ou équivalent).
Elle fonctionne en Manifest V2 pour Firefox et Manifest V3 pour Chrome.

Ce document décrit les bugs constatés dans la version précédente (v1.0.7) et les corrections apportées.

---

## Bug 1 — Bouton "Traduire ?" auto-détection : affichait le prompt au lieu de la traduction

### Symptôme
Quand l'utilisateur sélectionne du texte sur une page, un bouton flottant "🌐 Traduire en Français ?" apparaît.
En cliquant dessus, la bulle de traduction s'ouvrait mais affichait le texte du prompt LLM (en espagnol, puis en français après une tentative de fix) plutôt que la traduction du texte sélectionné.

### Cause racine
La fonction `createInlineBubble()` (injectée dans la page via `chrome.tabs.executeScript`) utilisait l'API Promise de Firefox :

```js
var api = (typeof browser !== 'undefined') ? browser.runtime : chrome.runtime;
api.sendMessage({ action: 'secure-translate', text: text }).then(function(rsp) { ... });
```

En Firefox MV2, quand le script background répond via `sendResponse` (en retournant `true` de façon synchrone puis en appelant `sendResponse` depuis un callback asynchrone `chrome.storage.local.get`), la Promise côté content-script peut résoudre avec `undefined` ou ne jamais résoudre. Le canal de message se ferme avant que la réponse arrive.

En comparaison, `displayInlineTranslationBubble()` (la bulle du clic droit, qui **fonctionnait**) utilisait la forme callback :

```js
chrome.runtime.sendMessage({ action: 'secure-translate', text: text, trackingId: id }, (response) => { ... });
```

### Correction appliquée
Remplacer la forme Promise par la forme callback dans `createInlineBubble()` :

```js
// AVANT (bugué en Firefox MV2)
var api = (typeof browser !== 'undefined') ? browser.runtime : chrome.runtime;
api.sendMessage({ action: 'secure-translate', text: text }).then(function(rsp) {
  if (rsp && rsp.success && rsp.translation) {
    res.textContent = rsp.translation;
  } else {
    res.textContent = 'Err: bad response';
  }
}).catch(function(err) {
  res.textContent = 'Err: ' + err.message;
});

// APRÈS (correct, identique au clic droit)
chrome.runtime.sendMessage({ action: 'secure-translate', text: text }, function(rsp) {
  if (chrome.runtime.lastError) {
    res.style.color = '#f38ba8';
    res.textContent = 'Err: ' + chrome.runtime.lastError.message;
    return;
  }
  if (rsp && rsp.success && rsp.translation) {
    res.textContent = rsp.translation;
  } else {
    res.style.color = '#f38ba8';
    res.textContent = 'Err: ' + (rsp ? (rsp.error || 'bad response') : 'no response');
  }
});
```

**Fichier modifié :** `extension/src/background.js` — fonction `createInlineBubble()` dans `injectAutoDetectListener()`

---

## Bug 2 — Page Options dans la popup : deux fois plus large, boutons inaccessibles

### Symptôme
En cliquant sur ⚙️ Options dans la popup de l'extension, le panneau de configuration rendait la popup deux fois plus large avec de l'espace vide à droite, et on ne pouvait plus défiler vers le bas pour atteindre les boutons "Sauvegarder" / "Tester Ollama".

### Cause racine
Deux problèmes combinés :

1. **Débordement horizontal** : le `<select id="extFontFamily">` (choix de police) avait des `<option>` avec du texte long (ex: `"'Comic Sans MS', 'Chalkboard SE', cursive"`). En tant qu'élément enfant d'un conteneur flex (`body { display: flex; flex-direction: column }`), son `min-width` par défaut (`auto` = largeur intrinsèque du contenu) forçait le conteneur à s'élargir au-delà des 400px du popup.

2. **Absence de scroll vertical** : `#settingsPanel` n'avait pas de `overflow-y: auto`, donc son contenu débordait silencieusement hors de la fenêtre sans scrollbar.

### Correction appliquée

```css
/* Tous les enfants directs du flex body ne peuvent pas forcer l'élargissement */
header, .lang-row, .text-areas, .actions-row, #settingsPanel, #globalStatus {
  min-width: 0;
}

/* Le panneau options devient un overlay absolu avec scroll interne */
#settingsPanel {
  display: none;
  position: absolute;
  top: 12px; left: 12px; right: 12px; bottom: 12px;
  background-color: var(--bg-color);
  border: 1px solid var(--border-color);
  border-radius: 6px;
  padding: 10px;
  font-size: 11px;
  box-sizing: border-box;
  z-index: 10;
  overflow-y: auto;
  word-wrap: break-word;
}

/* Les selects dans les form-group ont une largeur contrainte */
.form-group input,
.form-group select {
  width: 100%;
  max-width: 100%;
  box-sizing: border-box;
  overflow: hidden;
  text-overflow: ellipsis;
  /* ... autres styles ... */
}
```

**Fichier modifié :** `extension/src/popup.html`

---

## Amélioration 3 — Style du bouton "Traduire ?"

### Avant
Gros bloc orange vif, peu élégant, trop visible.

### Après
Badge compact en forme de pilule, fond sombre semi-transparent avec bordure orange, effet `backdrop-filter: blur` :

```js
hintBtn.style.cssText = 'position:fixed;z-index:999999998;'
  + 'background:rgba(24,28,36,0.92);color:#ffaa33;'
  + 'border:1px solid #ffaa33;'
  + 'padding:4px 10px;border-radius:20px;font-size:11px;font-weight:600;cursor:pointer;'
  + 'font-family:"Segoe UI",system-ui,sans-serif;'
  + 'box-shadow:0 2px 8px rgba(0,0,0,0.4);'
  + 'backdrop-filter:blur(4px);user-select:none;white-space:nowrap;';
hintBtn.textContent = '🧅 Traduire ?';
```

---

## Amélioration 4 — Bulle de traduction (clic droit) : resize fonctionnel

### Problème
Quand l'utilisateur redimensionnait la bulle du clic droit, elle pouvait dépasser les bords du viewport et les boutons d'action (Copier / Remplacer) devenaient inaccessibles. Le contenu ne s'adaptait pas à la nouvelle taille.

### Correction
- `box-sizing: border-box` sur la bulle pour un calcul de taille prévisible
- `max-width: calc(100vw - 20px)` et `max-height: calc(100vh - 20px)` pour rester dans le viewport
- `display: flex; flex-direction: column` sur la bulle pour que le résultat de traduction (`flex: 1`) s'étire quand on agrandit, et que le pied de page (boutons) reste visible en bas

**Fichier modifié :** `extension/src/background.js` — fonction `displayInlineTranslationBubble()`

---

## Fichiers livrés (v1.0.8)

| Fichier | Usage |
|---|---|
| `shallott_-_traducteur_ia_local-1.0.8.zip` | Soumission Firefox AMO (Manifest V2, gecko.id `{28ca131e-ab92-4713-ab9c-efffcfd19825}`) |
| `shallott_-_chrome_mv3-1.0.8.zip` | Installation Chrome/Brave/Edge (Manifest V3) |

---

## Règle importante à conserver (AMO Firefox)

Le champ `browser_specific_settings.gecko.id` dans `extension/manifest.json` **doit toujours rester** :
```
{28ca131e-ab92-4713-ab9c-efffcfd19825}
```
C'est l'identifiant de la fiche publiée sur AMO. Le changer créerait une nouvelle extension au lieu de soumettre une mise à jour.
