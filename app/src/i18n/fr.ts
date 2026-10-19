/** The French UI text, and the shape every other language must match
 * (see Messages): a key missing from a translation doesn't compile. Text
 * that varies with a number or a name is a function. From Bobine Audio. */
export const fr = {
  common: {
    close: "Fermer",
    retry: "Réessayer",
    help: "Aide",
    httpError: (status: number) => `Erreur ${status}`,
    cancelled: "Annulé",
    cancelExport: "Annuler l'export",
    removeAll: "Tout retirer",
    add: "+ Ajouter",
    change: "Changer…",
    show: "Afficher",
    engineStopped: "Le moteur s'est arrêté pendant la tâche.",
  },

  startup: {
    starting: "Démarrage du moteur…",
    unreachable: "Le moteur d'analyse ne répond pas. Réessaie, ou redémarre l'application.",
    unreachableShort: "Le moteur ne répond pas",
    noAnswer: "Le moteur ne répond pas.",
  },

  options: {
    title: "Options",
    theme: "Thème",
    themes: { system: "Système", light: "Clair", dark: "Sombre" },
    themeHint: "« Système » suit le thème clair ou sombre de ton système.",
    language: "Langue",
    systemLanguage: "Système",
    languageHint: "« Système » suit la langue de ton système : français s'il est en français, anglais sinon.",
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

  add: {
    title: "Ajouter",
    files: "Ajouter des MKV…",
    folder: "Ajouter un dossier…",
    recursive: "Inclure les sous-dossiers (saisons)",
    noMkv: "Aucun fichier MKV là-dedans.",
    mkvFilter: "Vidéos MKV",
    folderDialog: "Ajouter un dossier",
    dropToAdd: "Ajouter à la liste",
    dropRecursive: "Les dossiers sont parcourus avec leurs sous-dossiers",
    dropBlocked: "Attends la fin du traitement",
  },

  output: {
    title: "Sortie",
    where: "Où écrire les fichiers traités",
    nextTo: "À côté",
    otherFolder: "Autre dossier",
    folderDialog: "Dossier de sortie",
    nextToText: "Dans un dossier « Output » à côté des originaux, sous le même nom",
    nextToHint:
      "Chaque fichier traité garde son nom, dans un dossier « Output » à côté de l'original. Les originaux ne sont jamais modifiés.",
    redo: "Refaire les fichiers déjà traités",
    summary: (files: number, toDo: number, done: number) =>
      `${files} fichier${files > 1 ? "s" : ""} · ${toDo} à traiter` + (done > 0 ? ` · ${done} traité${done > 1 ? "s" : ""}` : ""),
    running: (done: number, total: number) => `Traitement… ${done} / ${total}`,
    apply: (n: number) => `Appliquer le style${n > 0 ? ` (${n})` : ""}`,
  },

  list: {
    title: "Fichiers",
    hint: "Chaque MKV ajouté est lu : ses pistes de sous-titres françaises, ce qu'elles deviendront et les polices à joindre. Clique sur une ligne pour voir le détail en dessous, puis lance « Appliquer le style ».",
    file: "Fichier",
    french: "Sous-titres français",
    fonts: "Polices",
    state: "État",
    emptyTitle: "Glisse des fichiers ou des dossiers ici",
    emptyHint: "Des MKV, ou le dossier d'une saison ou d'une série : leurs sous-titres français prendront le style maison.",
    forced: "forcés",
    full: "complets",
    redo: "Refaire ce fichier",
    openFolder: "Ouvrir le dossier du fichier écrit",
    remove: "Retirer de la liste",
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
    title: "Ce qui sera fait",
    readingTracks: "Lecture des pistes…",
    noSubtitles: "Aucune piste de sous-titres : ce fichier ne sera pas traité.",
    noFrench: "Aucune piste de sous-titres française : ce fichier ne sera pas traité.",
    // "Audio par défaut en japonais (VO) : sous-titres complets par défaut."
    defaultAudio: "Audio par défaut en ",
    defaultSubtitles: " : sous-titres ",
    byDefault: " par défaut.",
    forced: "forcés",
    full: "complets",
    noAudio: "Pas d'audio : sous-titres complets par défaut.",
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
    attachedFonts: "Polices jointes : ",
    presentFonts: "Déjà dans le MKV : ",
    output: "Sortie",
  },

  languages: {
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

export type Messages = typeof fr;
