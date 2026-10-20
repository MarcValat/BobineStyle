/** The French UI text, and the shape every other language must match
 * (see Messages): a key missing from a translation doesn't compile. Text
 * that varies with a number or a name is a function. From Bobine Audio. */
export const fr = {
  common: {
    close: "Fermer",
    retry: "Réessayer",
    help: "Aide",
    error: "Erreur",
    httpError: (status: number) => `Erreur ${status}`,
    cancelled: "Annulé",
    cancelExport: "Annuler l'export",
    remove: "Retirer",
    removeAll: "Tout retirer",
    removeAllQuestion: "Retirer tous les fichiers ?",
    keep: "Garder",
    foldList: "Replier la liste",
    unfoldList: "Déplier la liste",
    change: "Changer…",
    log: (n: number) => `Journal (${n})`,
    connectionLost: "Connexion interrompue avant la fin du traitement (le moteur a-t-il planté ?).",
    websocketLost: "Connexion WebSocket perdue.",
  },

  window: {
    minimize: "Réduire",
    maximize: "Agrandir",
    restore: "Restaurer",
    close: "Fermer",
  },

  startup: {
    ready: "Moteur prêt",
    starting: "Démarrage du moteur…",
    unreachable: "Le moteur ne répond pas. Réessaie, ou redémarre l'application.",
    unreachableShort: "Le moteur ne répond pas",
    noAnswer: "Le moteur ne répond pas.",
  },

  options: {
    title: "Paramètres",
    version: (version: string) => `Version actuelle : ${version}.`,
    theme: "Thème",
    themes: { system: "Système", light: "Clair", dark: "Sombre" },
    themeHint: "« Système » suit le thème clair ou sombre de ton système.",
    language: "Langue",
    systemLanguage: "Système",
    languageHint: "« Système » suit la langue de ton système : français s'il est en français, anglais sinon.",
    uiScale: "Taille de l'interface",
    uiScaleHint: "Agrandit ou réduit toute l'interface : textes, boutons et listes.",
    uiScaleLimited: (percent: number) => `Réduite à ${percent} % : l'écran n'a pas la place pour plus.`,
    updates: "Mises à jour",
    checkUpdates: "Vérifier au démarrage",
    updatesHint: "Au lancement, l'application demande à GitHub si une nouvelle version existe ; rien n'est installé sans ton accord.",
  },

  update: {
    downloadingTitle: (percent: number | null) => `Téléchargement de la mise à jour${percent !== null ? ` : ${percent} %` : "…"}`,
    failedTitle: "La mise à jour a échoué",
    availableTitle: (version: string) => `Mise à jour disponible : v${version}`,
    failedHeading: "Échec de la mise à jour",
    availableHeading: (version: string) => `Bobine Style v${version} est disponible`,
    restartNote: "L'application redémarre une fois la mise à jour téléchargée : un traitement en cours sera interrompu.",
    install: "Installer et redémarrer",
    downloading: (percent: number | null) => `Téléchargement… ${percent !== null ? `${percent} %` : ""}`,
    installing: "Installation, redémarrage…",
    downloadFailed: (error: string) => `Échec du téléchargement : ${error}`,
    installFailed: (error: string) => `Échec de l'installation : ${error}`,
    restart: "Redémarrer l'application",
  },

  batch: {
    moveUp: "Monter",
    moveDown: "Descendre",
  },

  empty: {
    title: "Un style propre et lisible pour les sous-titres de tes MKV",
    hint: "Dans les langues de ton choix, un fichier ou toute une série : Bobine Style restyle les sous-titres et nomme les pistes, sans rien réencoder.",
    drop: "Glisse des MKV ou un dossier ici, ou clique pour parcourir",
    dropHint: "Une saison, une série entière : les fichiers déjà faits sont sautés.",
    styleTitle: "Le style maison",
    styleHint:
      "Trebuchet MS gras, contour et ombre, et une variante pour chaque cas : italique, haut de l'écran, répliques à tirets, paroles simultanées.",
    sizeTitle: "La bonne taille partout",
    sizeHint: "Même taille à l'écran en 720p qu'en 4K, en 16:9, en scope ou en 4:3. Les panneaux ne bougent pas.",
    tracksTitle: "Des pistes bien nommées",
    tracksHint: "« Français », « English (forced) »… dans chaque langue, la bonne par défaut selon l'audio, et les polices jointes au MKV.",
  },

  add: {
    files: "Ajouter des MKV",
    folder: "Ajouter un dossier…",
    recursive: "Inclure les sous-dossiers (saisons)",
    noMkv: "Aucun fichier MKV là-dedans.",
    mkvFilter: "Vidéos MKV",
    folderDialog: "Ajouter un dossier",
    dropToAdd: "Déposer pour ajouter à la liste",
    dropRecursive: "Un dossier ajoute ses MKV, ceux de ses sous-dossiers aussi",
    dropBlocked: "Ajout impossible pendant un traitement : attends sa fin.",
    addMore: "+ Ajouter des MKV",
    dropMore: "ou glisse-les, ou un dossier, sur la fenêtre",
    addHint: "Ajouter des MKV à la liste",
  },

  output: {
    title: "Sortie",
    label: "Sortie :",
    edit: "Modifier…",
    where: "Où écrire les fichiers traités",
    nextTo: "À côté",
    otherFolder: "Autre dossier",
    folderDialog: "Dossier de sortie",
    nextToShort: "dossier « Output » à côté des originaux",
    nextToText: "Dans un dossier « Output » à côté des originaux, sous le même nom",
    nextToHint:
      "Chaque fichier traité garde son nom, dans un dossier « Output » à côté de l'original, ou dans le dossier choisi. Les originaux ne sont jamais modifiés.",
    redo: "Refaire les fichiers déjà traités",
    summary: ({ files, toDo, done, already, nothing, failed }: Counts) =>
      [
        `${files} fichier${files > 1 ? "s" : ""}`,
        `${toDo} à traiter`,
        done > 0 && `${done} terminé${done > 1 ? "s" : ""}`,
        already > 0 && `${already} déjà traité${already > 1 ? "s" : ""}`,
        nothing > 0 && `${nothing} sans sous-titres dans ces langues`,
        failed > 0 && `${failed} échec${failed > 1 ? "s" : ""}`,
      ]
        .filter(Boolean)
        .join(" · "),
    running: (done: number, total: number) => `Application · ${done}/${total}`,
    apply: (n: number) => (n > 0 ? `Appliquer le style · ${n} fichier${n > 1 ? "s" : ""}` : "Appliquer le style"),
  },

  list: {
    count: (n: number) => `Fichiers · ${n}`,
    forced: "forcés",
    full: "complets",
    noChosen: "aucun sous-titre dans ces langues",
    fonts: (n: number) => `${n} police${n > 1 ? "s" : ""}`,
    redo: "Refaire ce fichier",
    openFolder: "Ouvrir le dossier du fichier écrit",
  },

  status: {
    reading: "Lecture…",
    nothingToDo: "Rien à faire",
    failed: "Échec",
    unreadable: "Illisible",
    waiting: "En attente",
    done: "Terminé",
    alreadyDone: "Déjà traité",
    ready: "Prêt",
    percent: (n: number) => `${n} %`,
  },

  detail: {
    readingTracks: "Lecture des pistes…",
    subtitles: (list: string) => `sous-titres : ${list}`,
    noSubtitlesShort: "aucun sous-titre",
    noSubtitles: "Aucune piste de sous-titres : ce fichier ne sera pas traité.",
    noChosen: "Aucune piste de sous-titres dans les langues choisies : ce fichier ne sera pas traité.",
    openFolder: "Ouvrir le dossier",
    applyFile: "Appliquer à ce fichier",
    running: (percent: number) => `Application en cours · ${percent} %`,
    doneRun: "Terminé · écrit et vérifié",
    failedRun: (error: string) => `Échec : ${error} L'original n'a pas été touché.`,
    cancelledRun: "Annulé : rien n'a été écrit.",
    // "Audio par défaut en japonais (VO) : sous-titres complets par défaut."
    defaultAudio: "Audio par défaut en ",
    defaultSubtitles: " : sous-titres ",
    byDefault: " par défaut.",
    // "les sous-titres français complets" / "forcés"
    defaultKind: (forced: boolean, language: string) => `${language} ${forced ? "forcés" : "complets"}`,
    noAudio: (language: string) => `Pas d'audio : sous-titres ${language} complets par défaut.`,
    noDefaultTrack: (language: string) => `Aucune piste de sous-titres en ${language} : la piste par défaut ne change pas.`,
    notChosen: "langue non choisie",
    style: "Style appliqué",
    houseStyle: "Style maison",
    houseStyleSummary: "Trebuchet MS gras 66 px · blanc, contour et ombre noirs · 75 px du bas",
    scaled: (width: number, height: number) => `Tailles pour un écran 1080p, adaptées à cette vidéo (${width}×${height})`,
    track: "Piste",
    becomes: "Devient",
    flags: "Marquage",
    processing: "Traitement",
    unchanged: "inchangée",
    flagDefault: "défaut",
    flagForced: "forcés",
    actions: { restyle: "Style maison", convert: "SRT converti en ASS", copy: "Copiée telle quelle" },
    lines: (n: number) => `${n} réplique${n > 1 ? "s" : ""}`,
    titled: (title: string) => `« ${title} »`,
    attachedFonts: "Polices jointes",
    presentFonts: "Déjà dans le MKV",
    output: "Sortie",
    written: "Écrit",
  },

  languages: {
    label: "Langues :",
    defaultLabel: "Sous-titres par défaut :",
    none: "aucune",
    hint: "Langues : les sous-titres restylés et renommés dans leur langue (« Français », « English (forced) ») ; les autres sont copiés tels quels. Sous-titres par défaut : la langue dont une piste devient celle par défaut, la forcée si l'audio par défaut est dans cette langue, la complète sinon.",
    unknown: "langue inconnue",
    /** A language's name inside a sentence ("Audio par défaut en japonais"). */
    inSentence: (name: string) => name.toLowerCase(),
    names: {
      fre: "Français",
      fra: "Français",
      eng: "Anglais",
      jpn: "Japonais",
      spa: "Espagnol",
      ger: "Allemand",
      deu: "Allemand",
      ita: "Italien",
      por: "Portugais",
      kor: "Coréen",
      chi: "Chinois",
      zho: "Chinois",
    } as Record<string, string>,
  },
};

/** The footer's counts (output.summary). */
interface Counts {
  files: number;
  toDo: number;
  done: number;
  already: number;
  nothing: number;
  failed: number;
}

export type Messages = typeof fr;
