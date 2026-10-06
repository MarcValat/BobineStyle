# bobinestyle engine

Python engine of Bobine Style: applies the house style to the French subtitles of an MKV (ASS restyled, SRT converted), names and flags the full and forced tracks, attaches the fonts they use, and remuxes the file with everything else copied untouched.

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

- `batch`: `-o` another output folder, `-j` files at a time (2), `--force` redo files already in the output, `--plan` / `--details` show without writing.
- The source file is never modified: outputs are written as `.part.mkv`, checked against the source (streams, codecs, duration, Dolby Vision), then renamed.

## How

- `scale.py`: the house style is in pixels of a 16:9 1080p screen; `k = max(width / 1920, height / 1080)` of the video's display size.
- `roles.py`: a style's role from its lines' usage (plain dialogue or typesetting tags), then its look (italic, top, dashes, overlap, margins).
- `style.py`: the house style written into the script's grid, kept when lines carry positions or sizes of their own; only style lines and a few headers change, plus the margin centring dash blocks that have none.
- `srt.py`: SRT cues to ASS lines with their role; `measure.py` measures text with the real font (Pillow) to centre dash blocks.
- `mux.py`: the plan (French tracks, full/forced, default track from the default audio, fonts to attach) and the ffmpeg remux (`-copyts`: extracted tracks keep the container's timestamps).
- `server.py` + `jobs.py`: FastAPI sidecar for the app; remuxes run as cancellable jobs streaming progress over WebSocket.
- `packaging/`: PyInstaller build of the sidecar for the app's installer.
