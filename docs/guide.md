<p align="center">English | <a href="guide.fr.md">Français</a></p>

# User guide

This guide explains how to use Bobine Style and exactly what it does to a file. For installing it, see the [README](../README.md#install). The interface is in French: its labels are quoted below in French, with their meaning.

## Contents

1. [Words to know](#words-to-know)
2. [Processing files](#processing-files)
3. [Reading a file's details](#reading-a-files-details)
4. [The house style](#the-house-style)
5. [How roles are found](#how-roles-are-found)
6. [Track names and the default track](#track-names-and-the-default-track)
7. [Fonts](#fonts)
8. [FAQ](#faq)

## Words to know

- **Full track** (*complets*): subtitles for the whole film, every line.
- **Forced track** (*forcés*): only what the audio doesn't say in your language: signs, foreign-language passages. Players show it on their own when the audio is French.
- **Style**: in an ASS subtitle file, a named set of font, size, colours, position. Each line uses one.
- **Role**: what a style is for: dialogue, italics (thoughts, voice-overs), top of the screen, dash lines (two speakers in one subtitle), simultaneous speech, or typesetting (signs, titles, karaoke).
- **House style** (*style maison*): the one style Bobine Style applies, described [below](#the-house-style).

## Processing files

1. **Add files** (*Ajouter* panel, on the left): *Ajouter des MKV…* for files, *Ajouter un dossier…* for a folder, *+ Ajouter* at the top of the list, or drop either on the window (the empty list is a drop zone). With *Inclure les sous-dossiers (saisons)* ticked, a series folder brings all its seasons. `Output` folders and unfinished files are never picked up.
2. **Choose where the results go** (*Sortie*):
   - *À côté* (next to them): an `Output` folder next to each file, under the same name;
   - *Autre dossier* (another folder): one folder for everything, picked then (*Changer…* to pick another); two episodes with the same name from different seasons go into their season's subfolder.

   *Refaire les fichiers déjà traités* processes again files whose result already exists; otherwise they're marked *Déjà traité* (already done) and skipped, so an interrupted series can simply be started again.
3. **Apply** (*Appliquer le style*, bottom left, with the number of files to process): two files at a time, each with its progress bar. *Annuler l'export* stops: the file being written is deleted, the originals are untouched either way.

Each row of the list has a bar on its left saying where it stands: blue while processed, pale blue queued or being read, pale green ready, green done (or already done), red failed. Its state in words: *Lecture…* (reading the tracks), *Prêt* (ready), *Déjà traité* (already done), *Rien à faire* (no French subtitles), *Illisible* (unreadable file), *En attente* (queued), *Terminé* (done), *Échec* (failed: hover for the reason), *Annulé* (cancelled). On its right, its buttons:

- ↻ *Refaire ce fichier*: processes it again on its own, even if it's done;
- 📁: opens the written file's folder;
- ✕: takes it off the list (*Tout retirer* empties the whole list).

Top right, ⚙ *Options*: the theme (*Système*, *Clair* or *Sombre*: system, light or dark) and the update check at startup.

## Reading a file's details

Click a file to see, under the list, in *Ce qui sera fait* (what will be done):

- **The default audio** and the subtitle track that follows from it (see [below](#track-names-and-the-default-track)).
- **Each subtitle track**: what it is now (language, format, title), what it becomes (*Devient*), its flags (*défaut*, *forcés*) and its treatment (*Traitement*):
  - *Style maison*: an ASS track restyled;
  - *SRT converti en ASS*: an SRT track converted, then styled;
  - *Copiée telle quelle*: copied untouched (other languages, image subtitles).

  Under a restyled track, each style's role (*Default : dialogue*, *Pensées : italique*…) and anything worth knowing.
- **The fonts** to attach (*Polices jointes*) and those already in the file (*Déjà dans le MKV*).
- **The output path** (*Sortie*).

## The house style

On a 1080p 16:9 screen:

| | |
|---|---|
| Font | Trebuchet MS bold, 66 px |
| Colour | white, black outline 2.5 px, black shadow 2.5 px |
| Position | centred, 75 px from the bottom of the picture |

Its variants keep all of that and change one thing:

- **Italic**: the same in italics.
- **Top**: at the top of the screen (lines that would cover something at the bottom).
- **Dash lines**: left-aligned so the dashes line up, the block centred under the picture. Its margin is computed from the text's real width in Trebuchet MS.
- **Simultaneous speech** (*Overlap*): in light yellow.
- **Wider margins**: 45 px more on each side.

**Every size follows the video.** The values above are on-screen sizes. A 720p video gets them two thirds as big, a 4K one twice as big, so they look the same on the TV. A scope film (1920×800) or a 4:3 one (1440×1080) keeps exactly the 16:9 size, as it's shown with black bars on a 16:9 screen. An anamorphic DVD is measured at its displayed size.

**Signs never move.** In an ASS file, positions and sizes written in the lines (`\pos`, `\fs`…) are in the script's own grid (its *PlayRes*). When lines carry them, that grid is kept and the house style is converted into it; otherwise the grid takes the video's size. Either way, borders are scaled with the picture (`ScaledBorderAndShadow: yes`).

## How roles are found

From how styles are used, never from their names (except to recognise typesetting: *Sign*, *Title*, *OP*, *Karaoke*…).

- A line is **dialogue** unless its tags place it (`\pos`, `\move`), draw, do karaoke or change its font.
- A style is a **dialogue style** when most of its lines are dialogue, or when it carries a real part of the file's dialogue. That second rule matters for streaming subtitles that typeset signs with the dialogue style: an opening full of signs doesn't make it a sign style.
- The main dialogue style is the upright one with the most lines. The others get their role from their look: italic → *italique*, aligned at the top → *haut*, mostly dash lines → *tirets*, lines running over the main style's → *overlap*, wider side margins → *marges*.
- Anything else is **typesetting** and left exactly as it was.

The CLI's `bobinestyle inspect file.mkv` shows this analysis for each track.

## Track names and the default track

Among the French tracks, the one with the most dialogue is the **full** track. A track is **forced** when it's flagged so, when its title says so (*forc…*, *Signs*, *Panneaux*), or when it has less than half the full track's dialogue.

- Full: titled **Français**, not flagged forced.
- Forced: titled **Français (forcé)**, flagged forced.

**The default subtitle follows the default audio** (the audio track flagged default, or the first one):

| Default audio | Default subtitles |
|---|---|
| French | the forced track (none if there's no forced track) |
| Another language, unknown, or none | the full track (the forced one if there's no full track) |

A subtitle track in another language that was default isn't any more, so that players pick the French one.

## Fonts

Bobine Style ships no subtitle font: Trebuchet MS (a Microsoft font) can't be redistributed. Fonts are taken from your computer and attached to your files, which is what makes the subtitles look the same everywhere:

- the four Trebuchet MS files (regular, bold, italic, bold italic);
- every font the French subtitles use: their styles' and those named in the lines (`\fn`), for signs.

A font already in the MKV isn't attached twice. A font missing from your computer is listed in the file's details; the subtitles then show with a substitute font on players that don't have it either.

## FAQ

**Plex still shows plain white subtitles.** That client converts ASS to plain text (some TV apps do). Try Plex on a computer, or set the client's subtitles to "burn" so the server draws them into the picture with the style.

**A file says *Rien à faire*.** It has no French subtitle track (or only image ones: PGS, VobSub, which can't be restyled).

**Why is my "Signs" track not restyled?** It's only typesetting: restyling it would undo its design. It's still named and flagged forced.

**The subtitles of a scope film sit on the picture, not in the black bars.** Players draw subtitles inside the video. When the bars are part of the video itself (a 1920×1080 file with black bars), 75 px from the bottom usually falls in the bar; with cropped files (1920×800), it can't.

**Can I change the style?** Not from the app: one house style is the point. It's defined in `engine/src/bobinestyle/style.py`.

**Is the original changed?** Never. Outputs are written under a temporary name, checked (same streams, same codecs, same duration, Dolby Vision kept) and only then renamed.
