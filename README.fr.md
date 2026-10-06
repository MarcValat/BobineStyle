<p align="center"><a href="README.md">English</a> | Français</p>

<p align="center">
  <img src="app/src-tauri/icons/128x128@2x.png" width="112" alt="Icône de Bobine Style">
</p>

<h1 align="center">Bobine Style</h1>

<p align="center">
  <b>Un style propre et lisible pour les sous-titres français de tes MKV</b>, à la bonne taille sur chaque vidéo.
</p>

<p align="center">
  <a href="https://github.com/MarcValat/BobineStyle/releases/latest"><img src="https://img.shields.io/github/v/release/MarcValat/BobineStyle?label=version" alt="Dernière version"></a>
  <img src="https://img.shields.io/badge/Windows-10%20%7C%2011%20(x64)-0078D6?logo=windows" alt="Windows 10 | 11 (x64)">
  <img src="https://img.shields.io/badge/Linux-Debian%20%7C%20Ubuntu%20(.deb)-E95420?logo=linux&logoColor=white" alt="Linux : Debian | Ubuntu (.deb)">
  <img src="https://img.shields.io/badge/interface-Fran%C3%A7ais-555" alt="Interface : français">
  <a href="LICENSE"><img src="https://img.shields.io/badge/licence-GPL%20v3-blue" alt="Licence GPL v3"></a>
</p>

<p align="center">
  <a href="https://github.com/MarcValat/BobineStyle/releases/latest"><img src="https://img.shields.io/badge/T%C3%A9l%C3%A9charger-Windows%20%7C%20Linux-2ea44f?style=for-the-badge" alt="Télécharger pour Windows ou Linux"></a>
</p>

<picture>
  <source media="(prefers-color-scheme: dark)" srcset="docs/screenshots/main-dark.png">
  <img src="docs/screenshots/main-light.png" alt="Bobine Style : les épisodes d'une saison traités, et ce qui a été fait aux pistes de sous-titres du premier">
</picture>

## Pourquoi

Les sous-titres français arrivent dans tous les styles : un Arial fin d'un côté, une police énorme de l'autre, une piste difficile à lire sur une scène claire. Sur toute une vidéothèque, c'est un patchwork. Les restyler à la main, c'est ouvrir chaque fichier dans un éditeur de sous-titres, trouver quel style sert aux dialogues, lequel aux italiques, ne pas toucher aux panneaux, puis remuxer.

Bobine Style fait tout ça en une passe, pour un fichier ou une série entière, et nomme les pistes pour que Plex (ou n'importe quel lecteur) choisisse la bonne tout seul.

Il fait partie de **Bobine**, une petite suite d'outils pour vidéothèque, avec [SyncAudio](https://github.com/MarcValat/SyncAudio) et [SyncSubtitles](https://github.com/MarcValat/SyncSubtitles).

<img src="docs/screenshots/before-after.png" alt="Avant et après : des sous-titres en Arial fin deviennent du Trebuchet MS gras avec contour et ombre ; le panneau du haut reste tel quel ; une réplique à deux voix est centrée">

## Fonctionnalités

- 🎨 **Un style maison** : Trebuchet MS gras, blanc avec contour et ombre noirs, et ses variantes : italique, haut de l'écran, répliques à tirets (centrées, tirets alignés), paroles simultanées en jaune.
- 📐 **La bonne taille sur chaque vidéo** : le style est défini pour un écran 1080p et adapté à chaque vidéo : même taille en 720p qu'en 4K, et un film scope (2,39:1) ou 4:3 garde la même taille à l'écran qu'un 16:9.
- 🔍 **Des rôles trouvés à l'usage, pas au nom** : quel style sert aux dialogues, aux italiques, au haut de l'écran… est déduit de la façon dont chaque style est utilisé, quel que soit son nom. Les panneaux et la typo restent exactement comme ils étaient.
- 🏷️ **Pistes complètes et forcées nommées et marquées** : *Français* et *Français (forcé)*. Les sous-titres par défaut suivent l'audio par défaut : forcés avec un audio français, complets sinon.
- 🔤 **Polices jointes** : Trebuchet MS et les polices des panneaux sont jointes au MKV, pour que les sous-titres s'affichent pareil sur tous les lecteurs.
- 📝 **Les SRT aussi** : les SRT français sont convertis en ASS dans le même style (italiques, `{\an8}`, répliques à tirets…).
- 🗂️ **Une série entière en une passe** : glisse un dossier, ses saisons sont incluses ; les fichiers déjà faits sont sautés.
- 🛡️ **Rien de perdu** : vidéo, audio, sous-titres des autres langues et chapitres sont copiés tels quels, rien n'est réencodé, le fichier d'origine n'est jamais modifié, et chaque sortie est vérifiée avant d'être gardée.

## Installation

**Windows 10 et 11 :**

1. Télécharge `Bobine Style_x.y.z_x64-setup.exe` depuis la [dernière version](https://github.com/MarcValat/BobineStyle/releases/latest).
2. Lance-le. L'installateur n'est pas signé par un certificat, Windows SmartScreen peut donc afficher *« Windows a protégé votre ordinateur »* : clique sur **Informations complémentaires**, puis **Exécuter quand même**.

**Linux** (Ubuntu 22.04 ou plus récent, Debian et leurs dérivées) :

1. Télécharge `Bobine Style_x.y.z_amd64.deb` depuis la [dernière version](https://github.com/MarcValat/BobineStyle/releases/latest).
2. Installe-le depuis son dossier avec `sudo apt install "./Bobine Style_x.y.z_amd64.deb"`, puis lance-le depuis le menu des applications.
3. Trebuchet MS n'est pas fournie avec Linux : installe-la (`sudo apt install ttf-mscorefonts-installer`) pour qu'elle puisse être jointe aux fichiers.

Le moteur et ffmpeg sont fournis avec l'application. Quand une nouvelle version sort, l'application la propose et l'installe en un clic.

## Comment ça marche

1. **Ajoute des MKV**, ou un dossier entier (une saison, une série), avec les boutons ou en les glissant sur la fenêtre.
2. **Vérifie** ce qui sera fait : clique sur un fichier pour voir le sort de chaque piste de sous-titres, la piste par défaut et les polices à joindre.
3. **Applique le style** : les nouveaux fichiers vont dans un dossier `Output` à côté des originaux (ou dans le dossier de ton choix), sous le même nom.

📖 Le [guide d'utilisation](docs/guide.fr.md) explique tout en détail : le style maison, la détection des rôles, la piste par défaut, FAQ.

## Bon à savoir

- Seules les pistes **françaises** sont restylées (`fre`, ou une piste de langue indéterminée quand le fichier n'en a pas de française). Les autres langues restent telles quelles.
- Les pistes faites uniquement de panneaux (une piste « Signs ») sont marquées forcées mais pas restylées : leur typo est gardée telle qu'elle a été conçue.
- Certaines applications TV (Plex sur certaines TV connectées, par exemple) transforment les sous-titres ASS en texte simple et ignorent tout style : un fichier n'y peut rien. Le style s'affiche sur les lecteurs qui rendent l'ASS (Plex sur ordinateur, Infuse, VLC, mpv, Kodi), et quand le serveur Plex incruste les sous-titres dans l'image.

## Pour les développeurs

- [`engine/`](engine/README.md) : le moteur Python (lecture des pistes, détection des rôles, style, conversion SRT, remux, serveur HTTP local) ; utilisable seul en ligne de commande.
- [`app/`](app/README.md) : l'application (Tauri + React/TypeScript), qui pilote le moteur ; build, empaquetage et publication d'une version.

## Licence

Copyright © 2026 Marc Valat. Bobine Style est un logiciel libre, publié sous la [licence publique générale GNU v3](LICENSE) : tu peux l'utiliser, l'étudier, le partager et le modifier, et toute version que tu distribues, modifiée ou non, doit rester sous la même licence avec son code source disponible.

L'installateur fournit aussi [FFmpeg](https://ffmpeg.org/) (une build [gyan.dev](https://www.gyan.dev/ffmpeg/builds/), via [imageio-ffmpeg](https://github.com/imageio/imageio-ffmpeg)), que Bobine Style lance comme programme séparé. Cette build est aussi sous GPL v3 ; son code source est disponible auprès de FFmpeg et de gyan.dev.

Aucune police n'est fournie : Trebuchet MS et les autres sont prises sur ton ordinateur et jointes à tes propres fichiers.
