# Bobine Style (app)

L'application de [Bobine Style](../README.fr.md) (Tauri v2 + React/TypeScript) : ajouter des MKV ou des dossiers, voir ce qui sera fait à chaque fichier, appliquer le style.

Elle ne contient aucune logique de style ni de remux : elle pilote le moteur Python (`../engine/`), lancé au démarrage comme processus séparé exposant une API HTTP + WebSocket locale sur `127.0.0.1`. Le moteur prend son port habituel (8758) quand il est libre, un autre port libre sinon (`src-tauri/src/lib.rs`, commande `engine_port`) : aucun conflit possible avec Bobine Audio, Bobine Subs ou un autre programme. Une seule copie de l'application tourne à la fois : la relancer ramène la fenêtre ouverte.

## Prérequis

- [Node.js](https://nodejs.org/) (npm).
- [Rust](https://www.rust-lang.org/tools/install) (via [rustup](https://rustup.rs/)).
- [uv](https://docs.astral.sh/uv/) dans le PATH, avec les dépendances du moteur synchronisées (`uv sync` dans `../engine/`) : en dev, le moteur est lancé par `uv run bobinestyle serve` contre les sources.

## Développement

```
npm install
npm run tauri dev
```

Rechargement à chaud de l'interface ; le moteur démarre et s'arrête avec la fenêtre, mais ne se recharge pas : après une modification du moteur, relancer l'application.

`npm run dev` lance l'interface seule dans un navigateur. Avec un moteur lancé à part (`uv run bobinestyle serve` dans `../engine/`, port 8758 par défaut), tout fonctionne sauf les dialogues natifs ; en dev, `window.__test.add(chemins)` ajoute des fichiers sans dialogue, un évènement `bobinestyle:dragdrop` simule un glisser-déposer, et `?update=1` affiche une fausse mise à jour (vérifications automatiques avec Playwright).

## Empaqueter (`tauri build`)

```
npm run tauri build
```

`beforeBuildCommand` construit l'interface, puis fige le moteur avec PyInstaller (`../engine/packaging/build_sidecar.py`, sauté si rien n'a changé depuis le dernier build) dans `src-tauri/binaries/bobinestyle-engine/`, embarqué comme `engine/` à côté de l'exe. L'installateur Windows (NSIS, anglais et français) est écrit dans `src-tauri/target/release/bundle/nsis/`.

Un build local n'est pas signé pour les mises à jour sans la clé : définir `TAURI_SIGNING_PRIVATE_KEY` (contenu de `.tauri-keys/bobinestyle.key`) et `TAURI_SIGNING_PRIVATE_KEY_PASSWORD` (vide).

## Publier une release

Le workflow `.github/workflows/release.yml` (repris de Bobine Subs) :

- **sur un tag `vX.Y.Z`** : tests du moteur sous Windows et Linux, puis une release **brouillon** avec l'installateur `.exe`, le `.deb` et `latest.json` (mises à jour automatiques), signés ;
- **lancé à la main** (Actions > Release > Run workflow, sur n'importe quelle branche) : construit les deux installateurs sans rien publier, en artefacts du run.

Secrets requis (Settings > Secrets and variables > Actions) :

- `TAURI_SIGNING_PRIVATE_KEY` : le contenu de `app/.tauri-keys/bobinestyle.key` (jamais commité) ;
- `TAURI_SIGNING_PRIVATE_KEY_PASSWORD` : vide (clé générée sans mot de passe).

Pour une nouvelle version : changer la version dans `package.json`, `src-tauri/tauri.conf.json`, `src-tauri/Cargo.toml`, `../engine/pyproject.toml` et `../engine/src/bobinestyle/__init__.py`, merger, pousser le tag `vX.Y.Z`, relire puis publier le brouillon.
