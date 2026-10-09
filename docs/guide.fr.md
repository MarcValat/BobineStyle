<p align="center"><a href="guide.md">English</a> | Français</p>

# Guide d'utilisation

Ce guide explique comment utiliser Bobine Style et ce qu'il fait exactement à un fichier. Pour l'installer, voir le [README](../README.fr.md#installation).

## Sommaire

1. [Les mots à connaître](#les-mots-à-connaître)
2. [Traiter des fichiers](#traiter-des-fichiers)
3. [Lire le détail d'un fichier](#lire-le-détail-dun-fichier)
4. [Le style maison](#le-style-maison)
5. [Comment les rôles sont trouvés](#comment-les-rôles-sont-trouvés)
6. [Noms des pistes et piste par défaut](#noms-des-pistes-et-piste-par-défaut)
7. [Les polices](#les-polices)
8. [FAQ](#faq)

## Les mots à connaître

- **Piste complète** (*complets*) : les sous-titres de tout le film, chaque réplique.
- **Piste forcée** (*forcés*) : seulement ce que l'audio ne dit pas dans ta langue : panneaux, passages en langue étrangère. Les lecteurs l'affichent d'eux-mêmes quand l'audio est en français.
- **Style** : dans un fichier de sous-titres ASS, un ensemble nommé de police, taille, couleurs, position. Chaque ligne en utilise un.
- **Rôle** : ce à quoi sert un style : dialogue, italique (pensées, voix off), haut de l'écran, répliques à tirets (deux personnages dans un même sous-titre), paroles simultanées, ou typo (panneaux, titres, karaoké).
- **Style maison** : le style unique qu'applique Bobine Style, décrit [plus bas](#le-style-maison).

## Traiter des fichiers

1. **Ajoute des fichiers** (panneau *Ajouter*, à gauche) : *Ajouter des MKV…* pour des fichiers, *Ajouter un dossier…* pour un dossier, *+ Ajouter* en tête de la liste, ou glisse-les sur la fenêtre (la liste vide est une zone de dépôt). Avec *Inclure les sous-dossiers (saisons)* coché, le dossier d'une série apporte toutes ses saisons. Les dossiers `Output` et les fichiers inachevés ne sont jamais repris.
2. **Choisis où vont les résultats** (*Sortie*) :
   - *À côté* : un dossier `Output` à côté de chaque fichier, sous le même nom ;
   - *Autre dossier* : un seul dossier pour tout, choisi à ce moment-là (*Changer…* pour en prendre un autre) ; deux épisodes de même nom venant de saisons différentes vont dans le sous-dossier de leur saison.

   *Refaire les fichiers déjà traités* retraite les fichiers dont le résultat existe déjà ; sinon ils sont marqués *Déjà traité* et sautés : une série interrompue se relance simplement.
3. **Applique** (*Appliquer le style*, en bas à gauche, avec le nombre de fichiers à traiter) : deux fichiers à la fois, chacun avec sa barre de progression. *Annuler l'export* arrête : le fichier en cours d'écriture est supprimé, les originaux ne sont de toute façon jamais touchés.

Chaque ligne de la liste a une barre à sa gauche qui dit où elle en est : bleue pendant le traitement, bleu pâle en attente ou en lecture, vert pâle prête, verte terminée (ou déjà traitée), rouge en échec. Son état en toutes lettres : *Lecture…*, *Prêt*, *Déjà traité*, *Rien à faire* (pas de sous-titres français), *Illisible*, *En attente*, *Terminé*, *Échec* (survole pour la raison), *Annulé*. À droite, ses boutons :

- ↻ *Refaire ce fichier* : le retraite seul, même s'il est déjà fait ;
- 📁 : ouvre le dossier du fichier écrit ;
- ✕ : le retire de la liste (*Tout retirer* vide la liste entière).

En haut à droite, ⚙ *Options* : le thème (*Système*, *Clair* ou *Sombre*) et la vérification des mises à jour au démarrage.

## Lire le détail d'un fichier

Clique sur un fichier pour voir, sous la liste, dans *Ce qui sera fait* :

- **L'audio par défaut** et la piste de sous-titres qui en découle (voir [plus bas](#noms-des-pistes-et-piste-par-défaut)).
- **Chaque piste de sous-titres** : ce qu'elle est (langue, format, titre), ce qu'elle devient (*Devient*), son marquage (*défaut*, *forcés*) et son traitement :
  - *Style maison* : une piste ASS restylée ;
  - *SRT converti en ASS* : une piste SRT convertie, puis stylée ;
  - *Copiée telle quelle* : copiée sans changement (autres langues, sous-titres image).

  Sous une piste restylée, le rôle de chaque style (*Default : dialogue*, *Pensées : italique*…) et ce qui mérite d'être su.
- **Les polices** à joindre (*Polices jointes*) et celles déjà présentes (*Déjà dans le MKV*).
- **Le chemin de sortie** (*Sortie*).

## Le style maison

Sur un écran 1080p 16:9 :

| | |
|---|---|
| Police | Trebuchet MS gras, 66 px |
| Couleur | blanc, contour noir 2,5 px, ombre noire 2,5 px |
| Position | centré, à 75 px du bas de l'image |

Ses variantes gardent tout ça et changent une seule chose :

- **Italique** : la même chose en italique.
- **Haut** : en haut de l'écran (répliques qui cacheraient quelque chose en bas).
- **Répliques à tirets** : alignées à gauche pour que les tirets soient les uns sous les autres, le bloc centré sous l'image. Sa marge est calculée d'après la largeur réelle du texte en Trebuchet MS.
- **Paroles simultanées** (*Overlap*) : en jaune pâle.
- **Marges larges** : 45 px de plus de chaque côté.

**Toutes les tailles suivent la vidéo.** Les valeurs ci-dessus sont des tailles à l'écran. Une vidéo 720p les reçoit aux deux tiers, une vidéo 4K au double : à l'écran, c'est pareil. Un film scope (1920×800) ou 4:3 (1440×1080) garde exactement la taille du 16:9, puisqu'il s'affiche avec des bandes noires sur un écran 16:9. Un DVD anamorphique est mesuré à sa taille d'affichage.

**Les panneaux ne bougent jamais.** Dans un fichier ASS, les positions et tailles écrites dans les lignes (`\pos`, `\fs`…) sont dans la grille du script (son *PlayRes*). Quand des lignes en contiennent, cette grille est gardée et le style maison y est converti ; sinon la grille prend la taille de la vidéo. Dans les deux cas, les contours suivent l'image (`ScaledBorderAndShadow: yes`).

## Comment les rôles sont trouvés

D'après l'usage des styles, jamais d'après leur nom (sauf pour reconnaître la typo : *Sign*, *Title*, *OP*, *Karaoke*…).

- Une ligne est du **dialogue** sauf si ses balises la positionnent (`\pos`, `\move`), dessinent, font du karaoké ou changent sa police.
- Un style est un **style de dialogue** quand la plupart de ses lignes sont du dialogue, ou quand il porte une vraie part du dialogue du fichier. Cette seconde règle compte pour les sous-titres des plateformes de streaming, qui font leurs panneaux avec le style de dialogue : un générique plein de panneaux n'en fait pas un style de typo.
- Le style de dialogue principal est le style droit qui a le plus de répliques. Les autres tirent leur rôle de leur apparence : italique → *italique*, aligné en haut → *haut*, surtout des répliques à tirets → *tirets*, lignes en même temps que le style principal → *overlap*, marges latérales plus larges → *marges*.
- Tout le reste est de la **typo**, laissée exactement comme elle était.

En ligne de commande, `bobinestyle inspect fichier.mkv` montre cette analyse pour chaque piste.

## Noms des pistes et piste par défaut

Parmi les pistes françaises, celle qui a le plus de répliques est la piste **complète**. Une piste est **forcée** quand elle est marquée comme telle, quand son titre le dit (*forc…*, *Signs*, *Panneaux*), ou quand elle a moins de la moitié des répliques de la piste complète.

- Complète : titrée **Français**, non marquée forcée.
- Forcée : titrée **Français (forcé)**, marquée forcée.

**Les sous-titres par défaut suivent l'audio par défaut** (la piste audio marquée par défaut, ou la première) :

| Audio par défaut | Sous-titres par défaut |
|---|---|
| Français | la piste forcée (aucune s'il n'y en a pas) |
| Une autre langue, inconnue, ou pas d'audio | la piste complète (la forcée s'il n'y a pas de complète) |

Une piste de sous-titres d'une autre langue qui était par défaut ne l'est plus, pour que les lecteurs choisissent la française.

## Les polices

Bobine Style ne fournit aucune police de sous-titres : Trebuchet MS (une police Microsoft) ne peut pas être redistribuée. Les polices sont prises sur ton ordinateur et jointes à tes fichiers, ce qui permet aux sous-titres de s'afficher pareil partout :

- les quatre fichiers de Trebuchet MS (normal, gras, italique, gras italique) ;
- chaque police utilisée par les sous-titres français : celles de leurs styles et celles nommées dans les lignes (`\fn`), pour les panneaux.

Une police déjà présente dans le MKV n'est pas jointe deux fois. Une police absente de ton ordinateur est signalée dans le détail du fichier ; les sous-titres s'affichent alors avec une police de remplacement sur les lecteurs qui ne l'ont pas non plus.

## FAQ

**Plex affiche toujours des sous-titres blancs simples.** Ce client convertit l'ASS en texte simple (certaines applications TV le font). Essaie Plex sur ordinateur, ou règle les sous-titres du client sur « incruster » pour que le serveur les dessine dans l'image avec le style.

**Un fichier indique *Rien à faire*.** Il n'a pas de piste de sous-titres française (ou seulement des sous-titres image : PGS, VobSub, qui ne peuvent pas être restylés).

**Pourquoi ma piste « Signs » n'est-elle pas restylée ?** Elle n'est faite que de typo : la restyler défairait sa mise en page. Elle est quand même nommée et marquée forcée.

**Les sous-titres d'un film scope sont sur l'image, pas dans les bandes noires.** Les lecteurs dessinent les sous-titres dans la vidéo. Quand les bandes font partie de la vidéo (un fichier 1920×1080 avec bandes noires), 75 px depuis le bas tombent en général dans la bande ; avec un fichier recadré (1920×800), c'est impossible.

**Puis-je changer le style ?** Pas depuis l'application : l'intérêt est d'avoir un seul style maison. Il est défini dans `engine/src/bobinestyle/style.py`.

**L'original est-il modifié ?** Jamais. Les sorties sont écrites sous un nom temporaire, vérifiées (mêmes flux, mêmes codecs, même durée, Dolby Vision conservé), et seulement ensuite renommées.
