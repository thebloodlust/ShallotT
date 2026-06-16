# Compte-rendu — Bouton auto-détection "🧅 Traduire ?" (v1.1.3)

Résolution complète du bug "la bulle ne s'ouvre pas" quand on clique sur le bouton
flottant d'auto-détection. Plusieurs causes empilées, trouvées une par une via les
logs console de Firefox.

## Causes successives (toutes corrigées)

### 1. Deux bulles différentes
Le clic droit utilisait `displayInlineTranslationBubble` (OK), le bouton utilisait une
copie divergente `createInlineBubble` (cassée). → Supprimé `createInlineBubble`, le
bouton réutilise la bulle du clic droit.

### 2. Injection programmatique fragile + erreur Firefox MV2
L'écouteur d'auto-détection était injecté par `chrome.tabs/scripting.executeScript`
au chargement, ce qui :
- ne réinjectait pas le nouveau code après reload (content script obsolète) ;
- plantait en Firefox MV2 (`chrome.scripting.executeScript(...) is undefined`).

→ **Remplacé par un content script déclaratif** `src/autodetect.js` listé dans
`manifest.content_scripts` (matches http/https). Firefox l'injecte nativement et de
façon fiable à chaque chargement de page. Suppression de toute l'injection
programmatique de l'écouteur.

### 3. Texte vide envoyé (`text len= 0`)
Le `onclick` lisait `currentSelection`, qui pouvait être réinitialisé. → Utilise le
paramètre `text` passé à `showHint` (garanti non-vide) + fallback sélection live.

### 4. `chrome.scripting` truthy mais inutilisable en Firefox MV2 (cause majeure)
En Firefox MV2, `chrome.scripting` **existe** (donc `if (chrome.scripting)` est vrai)
mais `chrome.scripting.executeScript()` **ne renvoie pas de Promise** → `.then`/`.catch`
lèvent `TypeError: ... is undefined`. Tous les sites d'injection étaient touchés
(auto-détection, clic droit, OCR, traduction de page).

→ Détection corrigée **partout** :
```js
if (chrome.scripting && !(chrome.tabs && chrome.tabs.executeScript)) {
  // Chrome MV3 : API Promise
  chrome.scripting.executeScript({ target, func, args }).catch(...);
} else {
  // Firefox MV2 : API callback, fiable
  chrome.tabs.executeScript(tabId, { code: `(${fn.toString()})(${JSON.stringify(arg)})` }, cb);
}
```
Comme Firefox MV2 possède `chrome.tabs.executeScript`, il prend toujours la branche
qui marche ; Chrome MV3 (sans `chrome.tabs.executeScript`) prend `chrome.scripting`.
Helper `injectFiles()` ajouté pour l'OCR / la traduction de page (injection de fichiers
séquentielle en MV2).

### 5. Bulle positionnée hors écran sur les pages défilées (cause finale)
La bulle est en `position: fixed` (coordonnées **viewport**), mais le code **ajoutait
`window.scrollY` / `window.scrollX`**. Sur une page défilée, la bulle se retrouvait
des milliers de pixels plus bas → invisible. (Sur example.com, non défilée, ça
marchait — d'où le diagnostic.)

→ Corrigé : coordonnées viewport pures (sans scroll), avec clamp dans l'écran :
```js
let topPos = 90, leftPos = 90;            // fallback viewport
const geom = sel.getRangeAt(0).getBoundingClientRect();   // déjà viewport-relative
topPos = geom.bottom + 8; leftPos = geom.left;
bubble.style.top  = Math.max(8, Math.min(topPos,  window.innerHeight - 200)) + 'px';
bubble.style.left = Math.max(8, Math.min(leftPos, window.innerWidth  - 360)) + 'px';
```

## Vérifié
- Le modèle traduit correctement (curl direct sur `/api/generate`).
- Confirmé en conditions réelles : la bulle s'ouvre sur example.com ; le correctif #5
  étend ce fonctionnement aux pages défilées.
- `node --check` OK sur les 4 fichiers (background + autodetect, FF + Chrome).

## Architecture finale de l'auto-détection
1. `src/autodetect.js` (content script déclaratif) : détecte la sélection, affiche le
   badge 🧅, envoie `auto-detect-translate` au background avec le texte.
2. `background.js` handler `auto-detect-translate` : injecte
   `displayInlineTranslationBubble` dans l'onglet (même bulle que le clic droit), via
   `chrome.tabs.executeScript` (FF) ou `chrome.scripting` (Chrome).
3. `displayInlineTranslationBubble` : crée la bulle (position viewport), demande la
   traduction via `secure-translate`, affiche le résultat.

## Rappel AMO
`browser_specific_settings.gecko.id` doit rester `{28ca131e-ab92-4713-ab9c-efffcfd19825}`.

## Fichiers livrés (v1.1.3)
- `shallott_-_traducteur_ia_local-1.1.3.zip` (Firefox MV2)
- `shallott_-_chrome_mv3-1.1.3.zip` (Chrome MV3)
