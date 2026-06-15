# ShallotT 🧅 — Traducteur local alimenté avec l'IA (Bureau Multi-OS & Extension Navigateur)

**ShallotT** est une suite de traduction légère, moderne et ultra-rapide conçue comme un traducteur de premier choix alimenté avec l'IA (IA locale / VPN / distant), tout en fonctionnant à 100% en local grâce à la puissance d'**Ollama** et du modèle **Gemma 2 (8b, 9b, q4_k_m ou autre)**.

Aucun abonnement requis, aucune donnée ne quitte votre machine ou vos réseaux sécurisés (idéal avec Tailscale / Wireguard). Les traductions se font sans streaming, délivrant un résultat immédiat en un clin d'œil.

Cette suite comprend :
1. 🖥️ **Une application de bureau multiplateforme (Linux & Windows)** développée en Python avec PyQt6, supportant l'OCR de zone et les raccourcis système de n'importe où.
2. 🌐 **Une extension de navigateur web universelle (Chrome, Firefox, Brave, Edge)** pour traduire des pages web ou du texte sélectionné en un clic via une bulle flottante de traduction directe sans quitter votre navigation.

---

## ✨ Fonctionnalités phares

*   🎹 **Raccourci Global de Bureau `Double Ctrl+C`** : Sélectionnez n'importe quel texte sur votre ordinateur (navigateur, terminal, éditeur de code, PDF...), appuyez deux fois rapidement sur `Ctrl+C`. Une fenêtre pop-up élégante apparaît au premier plan avec la traduction instantanée (Multi-OS Linux/Windows).
*   📸 **Raccourci Global OCR `Ctrl+F8`** : Vous souhaitez traduire du texte présent sur une image, une vidéo ou une interface non sélectionnable ? Appuyez sur `Ctrl+F8`, dessinez un rectangle autour de la zone avec votre souris : ShallotT extrait le texte par OCR et le traduit immédiatement.
*   🌐 **Extension Navigateur Intégrée** : Faites un clic droit sur n'importe quel texte sélectionné dans votre navigateur pour faire apparaître une élégante bulle de traduction contextuelle. Vous pouvez également utiliser le raccourci `Alt+Shift+T` ou le bouton d'extension pour traduire en direct.
*   🚀 **Zéro Latence & Sans Stream** : L'API Ollama est interrogée de façon synchrone directe pour afficher le bloc de texte de manière instantanée, optimisée pour des textes allant de quelques mots à plusieurs milliers de caractères.
*   🎨 **Interface Moderne Sombre** : Design épuré, asynchrone (l'interface ne freeze jamais pendant la traduction), avec un bouton de copie rapide et un mode réduction dans la barre des tâches (System Tray).
*   🔒 **Sécurisé & Privé** : Se connecte à votre instance Ollama locale, distante, ou à travers un VPN comme Tailscale ou Wireguard.

---

## 🖥️ Application de bureau Python (Linux & Windows)

### 🛠️ Configuration requise

Pour faire fonctionner ShallotT sur votre système, vous avez besoin de :

1.  **Python 3.8+**
2.  **Tesseract OCR** (uniquement requis pour la fonctionnalité de capture d'écran OCR `Ctrl+F8`) :
    *   **Sur Linux (Debian/Ubuntu)** :
        ```bash
        sudo apt update
        sudo apt install tesseract-ocr tesseract-ocr-eng tesseract-ocr-fra -y
        ```
    *   **Sur Windows** :
        *   Téléchargez et installez l'installeur Tesseract depuis [GitHub UB-Mannheim](https://github.com/UB-Mannheim/tesseract/wiki).
        *   Installez-le dans le dossier recommandé (`C:\Program Files\Tesseract-OCR`). L'application ShallotT le détectera automatiquement !
3.  **Ollama** : configuré et lancé avec le modèle Gemma (ex. `gemma2:9b`).
    ```bash
    ollama run gemma2:9b
    ```

### 🚀 Installation & Lancement (Bureau)

1. Placez-vous dans le dossier du projet, créez un environnement virtuel Python et installez les paquets requis :

   **Sur Linux** :
   ```bash
   python3 -m venv .venv
   source .venv/bin/activate
   pip install -r requirements.txt
   python3 main.py
   ```

   **Sur Windows (PowerShell/CMD)** :
   ```powershell
   python -m venv .venv
   .venv\Scripts\activate
   pip install -r requirements.txt
   python main.py
   ```

L'application autonome s'ouvre. Par défaut, elle cherche un Ollama actif sur `http://localhost:11434`. Si votre Ollama tourne sur une IP VPN Tailscale ou à distance (par exemple sur un serveur de calcul), modifiez l'URL de votre serveur dans l'onglet **Settings** puis cliquez sur **Save Settings**.

---

## 🌐 Extension de navigateur Web (Chrome, Firefox, Brave, Edge...)

L'extension navigateur est codée en pure **Javascript Manifest V3**. Elle bypass CORS de façon native via les autorisations d'hôtes sécuritaires et permet d'utiliser votre Ollama local/VPN sans encombre.

### 🚀 Comment l'installer dans votre navigateur

#### Pour les navigateurs basés sur Chromium (Google Chrome, Brave, Opera, Microsoft Edge) :
1. Ouvrez votre navigateur et accédez à la page des extensions (`chrome://extensions/`).
2. Activez le **Mode développeur** (interrupteur en haut à droite).
3. Cliquez sur **Charger l'extension non empaquetée** (Load unpacked) en haut à gauche.
4. Sélectionnez le sous-dossier `extension/` de ce dépôt. C'est tout ! L'extension ShallotT apparaît dans votre barre d'outils.

#### Pour Mozilla Firefox :
1. Ouvrez Firefox et saisissez `about:debugging#/runtime/this-firefox` dans la barre d'adresse.
2. Cliquez sur **Charger un module temporaire** (Load Temporary Add-on).
3. Sélectionnez le fichier `manifest.json` présent dans le sous-dossier `extension/` du projet.

### ⌨️ Raccourcis complémentaires de l'extension :
*   **Traduction contextuelle** : Sélectionnez du texte sur n'importe quel site web -> Clic-droit -> `Traduire avec ShallotT Local`. Une magnifique bulle flottante contenant la traduction apparaît sur la page immédiatement !
*   **Raccourci clavier de sélection** (`Alt+Shift+T`) : Sélectionnez du texte, puis appuyez sur `Alt+Shift+T` pour stocker et traduire directement dans la popup d'extension.

### 💾 Comment installer l'extension de façon permanente et stable (à vie) :
Pour vous assurer de garder l'extension même après le redémarrage complet de Firefox sans avoir à la recharger temporairement à chaque fois, veuillez consulter notre guide pas à pas complet d'enregistrement : 
👉 [GUIDE_INSTALLATION_EXTENSION.md](GUIDE_INSTALLATION_EXTENSION.md).


---

## ⌨️ Raccourcis et Modes Avancés sous Linux (Wayland)

Sous certains compositeurs Wayland hautement sécurisés (comme sur GNOME ou KDE modernes), la surveillance globale des touches du clavier par des scripts Python tiers en arrière-plan peut être restreinte par le système d'exploitation.

Pour contourner cela avec une élégance absolue, ShallotT intègre des arguments CLI. Vous pouvez configurer des **raccourcis système natifs** dans les paramètres de votre environnement de bureau (ex. GNOME Settings -> Keyboard -> View and Customize Shortcuts) reliés aux commandes suivantes :

*   **Raccourci de traduction du presse-papiers** (associez par exemple un double-clic de raccourci personnalisé) :
    ```bash
    /chemin/vers/.venv/bin/python /chemin/vers/main.py --translate
    ```
*   **Raccourci de capture d'écran OCR** (associez par exemple `Ctrl+F8` natif à cette commande) :
    ```bash
    /chemin/vers/.venv/bin/python /chemin/vers/main.py --ocr
    ```

Cette méthode est **100% robuste**, fonctionne partout sous Wayland, X11 ou Windows, et évite les soucis de permissions de clavier.

---

## 🎨 Personnalisation du Prompt Gemma 2

L'intégration de Gemma est codée dans `src/ollama_client.py` (pour le bureau) et `extension/src/background.js` / `popup.js` (pour l'extension). Elle utilise un prompt spécifiquement conçu pour guider le modèle à agir de manière extrêmement précise pour la traduction par IA, en évitant le bavardage (pas d'introductions du type *"Voici votre traduction :"* ou *"J'espère que cela vous aide"*), garantissant ainsi un temps de réponse minimal. Vous pouvez ajuster la température (par défaut `0.2` pour plus de fidélité) dans les paramètres du payload.

## 🗂️ Structure du Projet

```
ShallotT/
├── main.py              # Point d'entrée de l'application et routage CLI
├── requirements.txt     # Dépendances Python (PyQt6, Pillow, pytesseract, pynput, pyperclip, requests)
├── README.md            # Ce fichier explicatif
├── src/                 # Code source de l'application de bureau
│   ├── config.py         # Gestionnaire de configuration JSON cross-platform
│   ├── ocr.py            # Overlay de capture et extraction Tesseract OCR (chemins Windows gérés)
│   ├── ollama_client.py  # Connecteur API Ollama optimisé non-streamé
│   ├── shortcuts.py      # Écouteur de touches physiques global de secours (pynput)
│   └── ui.py             # Interface graphique PyQt6 (Dual-panel, Thème sombre, Multi-thread)
└── extension/           # Code source de l'extension de navigateur universelle
    ├── manifest.json     # Manifest V3 pour Chrome, Firefox, Brave, Edge
    ├── icons/            # Icônes de l'extension
    └── src/
        ├── popup.html    # Interface utilisateur popup aux couleurs de ShallotT
        ├── popup.js      # Script de popup avec traduction automatique dédoublée
        └── background.js # Crée les menus contextuels, gère les raccourcis et injecte la bulle flottante

---

## 🔒 Configuration du Serveur Ollama Distant et Sécurisation

Si vous ne possédez pas de GPU puissant localement, vous pouvez héberger Ollama sur un serveur distant (ex. machine d'entreprise, serveur dédié cloud) et vous y connecter de façon ultra-sécurisée. 

Voici comment configurer la connexion distante selon vos besoins :

### Méthode A : Connexion via VPN (Tailscale ou Wireguard) - *Recommandé*
C'est la solution la plus simple, la plus rapide et la plus sécurisée.
1. Installez Tailscale ou Wireguard sur votre PC de bureau et sur votre serveur Ollama distant.
2. Notez l'adresse IP privée de votre serveur dans le VPN (ex. `100.81.120.45` pour Tailscale).
3. Sur votre serveur, configurez Ollama pour qu'il écoute sur toutes les interfaces réseau en ajoutant la variable d'environnement `OLLAMA_HOST=0.0.0.0` (sous Linux, modifiez le service Systemd avec `systemctl edit ollama.service`).
4. Dans les paramètres de ShallotT (application de bureau ou extension), saisissez l'URL d'Ollama sous la forme : `http://OLLAMA_SERVER_VPN_IP:11434` (ex. `http://100.81.120.45:11434`).

### Méthode B : Reverse Proxy avec authentification par Clé API (Caddy / Nginx)
Si vous souhaitez exposer votre serveur à distance de manière sécurisée sans VPN, configurez un reverse proxy comme Caddy avec une clé d'authentification API (Bearer token) :
1. Configurez votre proxy pour rediriger les requêtes vers le port `11434` local et configurer le protocole HTTPS.
2. Ajoutez une règle de validation de l'en-tête `Authorization: Bearer <votre_cle_api_secrete>`.
3. Dans l'onglet **Settings** de ShallotT, saisissez l'URL HTTPS externe (ex. `https://votre-ollama.mon-site.com`).
4. Saisissez votre **clé d'API** secrète dans le champ dédié. ShallotT l'ajoutera automatiquement à toutes ses requêtes pour passer l'authentification de votre proxy.

### Méthode C : Tunneling SSH - *Rapide & sans configuration d'infrastructure*
1. Lancez un tunnel SSH mappant le port local vers votre serveur :
   ```bash
   ssh -L 11434:localhost:11434 nom_utilisateur@ip_du_serveur_distant
   ```
2. Laissez ce terminal ouvert en arrière-plan.
3. Configurez ShallotT pour interroger `http://localhost:11434`, le trafic passera de façon chiffrée par SSH !

---

## 🛠️ Compilation sous Windows en `.exe` Autonome

Vous pouvez compiler l'application Python sous Windows afin d'en faire un exécutable autonome. Cela vous permet de l'utiliser ou de le distribuer sans avoir besoin d'installer Python sur les machines cibles.

### 1. Générer l'exécutable

Pour faciliter cela, un script d'automatisation [build_exe.py](build_exe.py) est inclus. Ouvrez votre terminal PowerShell et exécutez :

**Mode recommandé (one-folder, compatible antivirus) :**
```powershell
python build_exe.py
```
Ce mode produit un dossier `dist\ShallotT\` contenant l'exécutable et toutes ses dépendances.
✅ **Faible risque de faux-positif antivirus** — pas de compression UPX, pas d'auto-extraction.

**Mode fichier unique (si vous avez vraiment besoin d'un seul `.exe`) :**
```powershell
python build_exe.py --onefile
```
⚠️ Le mode `--onefile` peut déclencher des faux-positifs antivirus (Windows Defender, Kaspersky, etc.) car l'auto-extraction PyInstaller ressemble à un comportement de malware. Si votre antivirus bloque le `.exe`, utilisez le mode par défaut sans `--onefile`.

**Options avancées :**
```powershell
python build_exe.py --console        # Affiche la console (débug)
python build_exe.py --onefile --upx  # Fichier unique + compression UPX (risque AV maximal)
```

### 2. Réduire les faux-positifs antivirus

Les exécutables PyInstaller sont parfois signalés à tort par les antivirus. Voici les bonnes pratiques appliquées par défaut :

| Pratique | Effet |
|---|---|
| Mode **one-folder** (`--onedir`) par défaut | Les fichiers sont visibles, pas d'auto-extraction suspecte |
| **UPX désactivé** par défaut | La compression UPX est un marqueur commun de malware |
| **Métadonnées Windows** intégrées | CompanyName, ProductName, FileDescription, version — l'exécutable paraît légitime |
| **Code signing** (à faire manuellement) | Un certificat EV supprime quasi tous les faux-positifs |

Si votre antivirus bloque quand même l'exécutable :
1. Soumettez le fichier pour analyse sur le [portail Microsoft Defender](https://www.microsoft.com/en-us/wdsi/filesubmission)
2. Ajoutez une exclusion dans votre antivirus pour le dossier `dist\ShallotT\`
3. Signez l'exécutable avec un certificat de signature de code (Extended Validation)

### 3. Créer un installeur d'application Windows (`.msi` ou `.exe` d'installation)
Pour distribuer ShallotT sous forme d'installateur classique de type setup ou MSI, nous vous conseillons d'utiliser des outils de packaging standard et extrêmement robustes :

*   **Inno Setup (Recommandé - .exe d'installation)** :
    1. Téléchargez et installez gratuitement [Inno Setup](https://jrsoftware.org/isinfo.php).
    2. Lancez le *Inno Setup Script Wizard*.
    3. Sélectionnez le dossier `dist\ShallotT\` (mode one-folder) ou `dist\ShallotT.exe` (mode onefile).
    4. Indiquez au Wizard d'ajouter également d'autres raccourcis, une icône de bureau ou de configurer le démarrage automatique au boot de Windows.
    5. Compilez le script : vous obtiendrez un installateur professionnel `setup.exe` léger et prêt pour l'installation d'une simple pression sur "Suivant".
*   **WiX Toolset (Pour générer un fichier `.msi`)** :
    1. Si votre d'infrastructure informatique d'entreprise impose le format `.msi` pour le déploiement de masse (Active Directory/GPO/Intune), téléchargez [WiX Toolset](https://wixtoolset.org/).
    2. Créez un fichier de description de package `.wxs` pointant sur le contenu de `dist\ShallotT\` (mode one-folder).
    3. Compilez-le à l'aide des outils `candle` et `light` pour obtenir votre fichier `.msi`.

