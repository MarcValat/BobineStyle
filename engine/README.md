# bobinestyle engine

Python engine of Bobine Style: applies the house style to the subtitles of an MKV in the chosen languages (French by default; ASS restyled, SRT converted), names the full and forced tracks in their own language ("Français", "English (forced)") and flags them, attaches the fonts they use, and remuxes the file with everything else copied untouched.

```
uv sync
uv run pytest
```

## CLI

```
uv run bobinestyle probe Film.mkv              # video size, style scale, subtitle tracks (@0, @1...), attachments
uv run bobinestyle inspect Film.mkv            # each ASS style's role, PlayRes kept or replaced
uv run bobinestyle style Film.mkv -t 0         # track @0 restyled, written as Film.0.bobine.ass
uv run bobinestyle mux Film.mkv --plan         # what processing the file would do
uv run bobinestyle mux Film.mkv                # Output/Film.mkv next to it
uv run bobinestyle batch Series/ -r            # every MKV of a folder and its seasons
uv run bobinestyle serve                       # the app's local HTTP server (docs: /docs)
```

- `mux` and `batch`: `--langues fre,eng` the subtitles' languages (ISO 639-2), `--defaut eng` the one whose track becomes the default (the first otherwise).
- `batch`: `-o` another output folder, `-j` files at a time (2), `--force` redo files already in the output, `--plan` / `--details` show without writing.
- The source file is never modified: outputs are written as `.part.mkv`, checked against the source (streams, codecs, duration, Dolby Vision), then renamed.
- `serve` listens on `127.0.0.1:8758` only, out of other machines' reach, but this machine's other programs and the websites open in its browser could call it. So with `BOBINESTYLE_TOKEN` set, every request must carry it back in the `X-Bobine-Token` header (a WebSocket, which takes no header, in its address's `token` parameter), 401 otherwise; `/health` alone answers without it. The app makes a new one at each launch (`app/src-tauri/src/lib.rs`), `bobine-dev` in dev builds. Only the app's pages may read the answers (CORS): the Tauri window, the dev server (`http://localhost:1420`) and any origin `BOBINESTYLE_ORIGINS` adds (comma-separated). Run by hand without `BOBINESTYLE_TOKEN`, it asks for no token.

## How

- `scale.py`: the house style is in pixels of a 16:9 1080p screen; `k = max(width / 1920, height / 1080)` of the video's display size.
- `roles.py`: a style's role from its lines' usage (plain dialogue or typesetting tags), then its look (italic, top, dashes, overlap, margins).
- `style.py`: the house style written into the script's grid, kept when lines carry positions or sizes of their own; only style lines and a few headers change, plus the margin centring dash blocks that have none.
- `srt.py`: SRT cues to ASS lines with their role; `measure.py` measures text with the real font (Pillow) to centre dash blocks.
- `styles.py`: a style (font, size, colours, outline, shadow, margins, and each variant on or off with what it changes), the house style built in, the user's own in `styles.json` in the app's data folder (`BOBINESTYLE_DATA`, given by the app); `/styles` reads and writes them, `/styles/import` and `/styles/export` a shared file, `/fonts` lists the fonts installed. `/plan` and `/jobs/mux` take the style to apply (the house style when none).
- `languages.py`: language codes made one ("fra" -> "fre"), an untagged track's language from its title, track names in their own language.
- `mux.py`: the plan (the chosen languages' tracks, full/forced per language, default track from the default audio, fonts to attach) and the ffmpeg remux (`-copyts`: extracted tracks keep the container's timestamps).
- `server.py` + `jobs.py`: FastAPI sidecar for the app; remuxes run as cancellable jobs streaming progress over WebSocket.
- `i18n.py`: what the user reads (plan notes, warnings, job logs, errors) in French or English, `tr()` on French templates; the app sets the language through `POST /language`, the CLI stays French.
- `packaging/`: PyInstaller build of the sidecar for the app's installer.
