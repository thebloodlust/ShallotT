# Guide d'aide : Comment enregistrer et installer à vie l'extension ShallotT sur Firefox 🧅

Par défaut, Mozilla Firefox bloque l'installation persistante (définitive) des extensions qui n'ont pas été signées numériquement sur leur portail développeur addons.mozilla.org (AMO). 

Voici deux méthodes simples pour enregistrer et installer de façon permanente l'extension de traduction **ShallotT** sur votre Firefox sans avoir à la recharger à chaque démarrage du navigateur.

---

## Méthode 1 : Signature privée gratuite et rapide via Mozilla (Recommandé) 🔒

Cette méthode vous permet d'obtenir un fichier d'extension officielle `.xpi` signé par Mozilla spécialement pour votre compte. Le module s'installera définitivement et restera à vie dans votre Firefox habituel.

### Étape 1 : Récupérer vos identifiants développeur gratuits
1. Connectez-vous sur votre compte Firefox habituel sur le portail des addons : **[addons.mozilla.org/develop/addons/api/key-credentials](https://addons.mozilla.org/develop/addons/api/key-credentials/)**.
2. Si vous n'avez pas encore de compte utilisateur développeur, créez-le gratuitement en acceptant les conditions d'utilisation.
3. Créez des identifiants d'API, Firefox va vous générer immédiatement deux clés d'authentification :
   * **JWT Issuer** (identifiant utilisateur, commence souvent par `user:...`)
   * **JWT Secret** (mot de passe de signature à double facteur)

### Étape 2 : Signer et compiler l'extension en un instant
Ouvrez un terminal dans le dossier racine du projet `ShallotT`, puis exécutez la commande suivante en remplaçant par vos informations obtenues à l'Étape 1 :

```bash
npx web-ext sign --source-dir extension --api-key="VOTRE_JWT_ISSUER_ICI" --api-secret="VOTRE_JWT_SECRET_ICI"
```

### Étape 3 : Installer l'extension à vie sur votre Firefox
1. Une fois la commande ci-dessus exécutée avec succès, un nouveau sous-dossier contenant votre paquet signé est créé : `web-ext-artifacts/`.
2. Il contient un fichier portant l'extension définitive **`.xpi`** (ex : `shallott-1.0.0.xpi`).
3. Ouvrez votre Firefox personnel et naviguez vers l'onglet : **`about:addons`**.
4. Cliquez sur l'icône d'**engrenage/roue crantée ⚙️** située en haut à droite.
5. Sélectionnez **Installer un module depuis un fichier...** (*Install Add-on From File...*).
6. Choisissez votre fichier **`.xpi`** généré à l'étape précédente.

**Félicitations ! 🎉** Votre extension est installée à vie de façon permanente et sécurisée dans votre navigateur.

---

## Méthode 2 : Installer avec Firefox Developer Edition / Nightly / ESR 🖥️

Sur les versions de développement de Firefox (développeurs, testeurs, entreprises d'administration), l'obligation de signature de Mozilla peut être tout simplement désactivée :

1. Ouvrez d'abord une version compatible de Firefox (*Firefox Developer Edition*, *Firefox Nightly* ou *Firefox ESR*).
2. Saisissez dans votre barre d'adresse : **`about:config`**.
3. Cherchez la clé d'option suivante : **`xpinstall.signatures.required`**.
4. Double-cliquez sur sa valeur pour la passer de `true` à **`false`**.
5. Allez dans vos extensions (`about:addons`).
6. Glissez-deposez simplement le fichier d'archive [web-ext-artifacts/shallott_-_traducteur_ia_local-1.0.0.zip](web-ext-artifacts/shallott_-_traducteur_ia_local-1.0.0.zip) directement sur la page. L'extension restera de façon permanente !

---

*Note : Si vous utilisez Google Chrome, Microsoft Edge ou Brave, l'installation permanente se fait simplement en sélectionnant le dossier `extension` sur la page `chrome://extensions` après avoir activé le "Mode développeur" (aucun besoin de signature !).*
