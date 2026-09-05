# To The Max — Faceless YouTube Shorts Video Generator

A full **video** generator (not just scripts) that produces 9:16 vertical
shorts ready for YouTube Shorts, TikTok, Instagram Reels, etc.

## Features

- **Local/Offline mode** — no API keys required; uses local templates,
  pyttsx3 voice, and stock images.
- **Cloud AI mode** — OpenAI GPT generates the script.
- **Full AI Pipeline** — OpenAI script + OpenAI TTS + DALL-E images.
- **Claude mode** — Anthropic Claude via OpenRouter.
- **Opencode mode** — any model on OpenRouter.
- **Cross-platform** — Windows + Linux, single Python file.
- **GUI** — Tkinter, matches the layout you provided:
  - Mode dropdown
  - API key fields (appear/hide by mode)
  - Topic + sub-topic
  - Select Images / Generate Short / Save Video
  - Script box + video preview pane
- **Video output** — 1080×1920 MP4 with ken-burns motion, burned-in
  captions, AAC audio, faststart for streaming.

## Install

### 1. Python 3.9+ on Windows or Linux

> **Note:** `tkinter` ships with the standard Python installer on
> Windows and macOS. On Linux you may need to install it separately:
> `sudo apt install python3-tk`

### 2. Install ffmpeg (required for video assembly)

- **Windows:** download from https://ffmpeg.org and add `ffmpeg.exe` to PATH
- **Linux (Debian/Ubuntu):** `sudo apt install ffmpeg`
- **Linux (Fedora):** `sudo dnf install ffmpeg`
- **macOS:** `brew install ffmpeg`

### 3. Install Python deps

```bash
pip install -r requirements.txt
```

The app will also auto-install missing optional packages on launch.

### 4. Run

```bash
python ToTheMaxShorts.py
```

## Modes at a glance

| Mode | Script | Voice | Images | Cost |
|------|--------|-------|--------|------|
| Local | local templates | offline TTS | stock/picsum | free |
| Cloud AI (OpenAI) | GPT-4o-mini | offline TTS | stock/picsum | low |
| Full AI Pipeline | GPT-4o-mini | OpenAI TTS (optional) | DALL-E 3 (optional) | medium |
| Claude (OpenRouter) | any Claude model | offline TTS | stock/picsum | low |
| Opencode (OpenRouter) | any OpenRouter model | offline TTS | stock/picsum | varies |

Both Claude and Opencode use the **OpenRouter** API endpoint and a single
OpenRouter key — only the model slug changes.

**Default model slugs (verified against OpenRouter's current catalog):**
- Claude: `anthropic/claude-sonnet-5`
- Opencode: `minimax/minimax-m3:free` (free tier)

**Other working free models you can paste into the model field:**
- `meta-llama/llama-4-scout`
- `mistralai/mistral-small-2603`
- `google/gemini-3.7-flash`
- `liquid/lfm-2.5-2.6b:free`
- `nvidia/nemotron-3-5-lightning:free`
- `google/gemma-4-26b-a4b-it:free`

Browse the full live list at https://openrouter.ai/models.

## Output

Videos are saved under:

- Windows: `C:\Users\<you>\ToTheMaxShorts\short_YYYYMMDD_HHMMSS\short.mp4`
- Linux: `~/ToTheMaxShorts/short_YYYYMMDD_HHMMSS/short.mp4`

## Troubleshooting

- **"ffmpeg not found"** — install ffmpeg and ensure it's on PATH.
- **Pillow not installed** — `pip install Pillow`
- **pyttsx3 voice install (Linux):** `sudo apt install espeak`
- **400 / 404 error from OpenRouter** — verify the model slug exists
  in https://openrouter.ai/models and your key is valid. Some older
  slugs (`claude-3-haiku`, `gemini-2.0-flash-exp`) have been retired.
- **ffmpeg build dump / "able-libvpx"** — this usually means the
  real error is earlier in stderr. The app now auto-detects a system
  font for subtitles and reports the actual error line. If you still
  see a dump, try **disabling subtitles** (uncheck "Add burned-in
  subtitles") to isolate whether drawtext is the cause.
- **Linux subtitle font missing** — `sudo apt install fonts-dejavu`
