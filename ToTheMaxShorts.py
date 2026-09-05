"""
To The Max Faceless YouTube Shorts Video Generator
Generates vertical 9:16 short videos with optional AI-powered scripts,
text-to-speech narration, and image-based video synthesis.

Supports:
  - Local/Offline mode (no internet required)
  - Cloud AI services (OpenAI)
  - Claude via OpenRouter
  - Opencode via OpenRouter
  - Full AI pipeline (script + TTS + images + subtitles + video assembly)

Cross-platform: Windows & Linux.
"""

import os
import sys
import json
import math
import random
import subprocess
import platform
import threading
from pathlib import Path
from datetime import datetime
from tkinter import Tk, StringVar, BooleanVar, filedialog, messagebox
from tkinter import ttk
from tkinter.scrolledtext import ScrolledText

# Optional imports - loaded lazily so the GUI still launches
try:
    import requests
except Exception:
    requests = None

try:
    import openai
except Exception:
    openai = None

try:
    from PIL import Image, ImageDraw, ImageFont
except Exception:
    Image = ImageDraw = ImageFont = None

try:
    import pyttsx3
except Exception:
    pyttsx3 = None


APP_TITLE = "To The Max  Faceless YouTube Shorts Generator"
OUTPUT_DIR = Path.home() / "ToTheMaxShorts"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

VIDEO_W, VIDEO_H = 1080, 1920  # 9:16 vertical


# ---------------------------------------------------------------------------
# Utility helpers
# ---------------------------------------------------------------------------
def _check_ffmpeg():
    """Return path to ffmpeg or None if not available."""
    from shutil import which
    return which("ffmpeg")


def _pip_install(package):
    """Best-effort pip install inside the running interpreter."""
    try:
        subprocess.check_call(
            [sys.executable, "-m", "pip", "install", "--quiet", package]
        )
        return True
    except Exception:
        return False


def _install_optional_dependencies():
    """Try to install pillow/pyttsx3/openai/requests so the pipeline works."""
    needed = []
    if Image is None:
        needed.append("Pillow")
    if pyttsx3 is None:
        needed.append("pyttsx3")
    if requests is None:
        needed.append("requests")
    for pkg in needed:
        _pip_install(pkg)


# ---------------------------------------------------------------------------
# Script generators
# ---------------------------------------------------------------------------
class ScriptGenerator:
    """Base interface."""

    def generate(self, topic, style="informative"):
        raise NotImplementedError


class LocalScriptGenerator(ScriptGenerator):
    TEMPLATES = [
        "Did you know? {topic} is one of the most fascinating subjects online. "
        "Here are three quick facts: First, it's more important than most people realize. "
        "Second, it's easier to understand than you think. "
        "Third, mastering {topic} can change the way you see the world. "
        "Follow for more mind-blowing shorts!",

        "Stop scrolling! Here's what nobody tells you about {topic}. "
        "It's simpler than you think, the results are worth it, "
        "and anyone can start today. "
        "Like and save this for later.",

        "Why {topic} matters in 60 seconds: "
        "It changes how we see the world. "
        "It creates new opportunities. "
        "And it's easier to get started than you think. "
        "Hit follow to learn more.",

        "Three secrets about {topic}: "
        "Number one, it's the future. "
        "Number two, most people overlook it. "
        "Number three, you can begin right now. "
        "Drop a comment if you want part two!",
    ]

    def generate(self, topic, style="informative"):
        if not topic.strip():
            topic = "the future of technology"
        tpl = random.choice(self.TEMPLATES)
        return tpl.format(topic=topic.strip())


class OpenAIScriptGenerator(ScriptGenerator):
    def __init__(self, api_key):
        if openai is None:
            raise RuntimeError("openai package not installed. Run: pip install openai")
        self.client = openai.OpenAI(api_key=api_key)

    def generate(self, topic, style="informative"):
        prompt = (
            f"Write a faceless YouTube Shorts script (about 120-150 words) about "
            f"'{topic}' in a {style} style. Hook in the first 3 seconds, "
            f"strong call-to-action at the end, written for TTS narration. "
            f"Output ONLY the script text."
        )
        resp = self.client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=250,
            temperature=0.7,
        )
        return resp.choices[0].message.content.strip()


class OpenRouterScriptGenerator(ScriptGenerator):
    """Used for both Claude and Opencode modes - they share the OpenRouter API."""

    def __init__(self, api_key, model, label="OpenRouter"):
        if requests is None:
            raise RuntimeError("requests not installed. Run: pip install requests")
        self.api_key = api_key
        self.model = model
        self.label = label

    def generate(self, topic, style="informative"):
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "HTTP-Referer": "https://github.com/tothemax-shorts",
            "X-Title": "To The Max Shorts Generator",
            "Content-Type": "application/json",
        }
        prompt = (
            f"Write a faceless YouTube Shorts script (about 120-150 words) about "
            f"'{topic}' in a {style} style. Hook in the first 3 seconds, "
            f"strong call-to-action at the end, written for TTS narration. "
            f"Output ONLY the script text."
        )
        payload = {
            "model": self.model,
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": 250,
            "temperature": 0.7,
        }
        r = requests.post(
            "https://openrouter.ai/api/v1/chat/completions",
            headers=headers,
            json=payload,
            timeout=60,
        )
        r.raise_for_status()
        data = r.json()
        try:
            return data["choices"][0]["message"]["content"].strip()
        except (KeyError, IndexError):
            raise RuntimeError(f"Unexpected {self.label} response: {json.dumps(data)[:300]}")


# ---------------------------------------------------------------------------
# Text-to-speech
# ---------------------------------------------------------------------------
class TTSEngine:
    def synthesize(self, text, out_path: Path):
        raise NotImplementedError


class LocalTTS(TTSEngine):
    """Uses pyttsx3 (offline, system voices)."""

    def __init__(self):
        if pyttsx3 is None:
            raise RuntimeError("pyttsx3 not installed. Run: pip install pyttsx3")
        self.engine = pyttsx3.init()
        # Try a female voice if available
        for voice in self.engine.getProperty("voices"):
            if "female" in voice.name.lower() or "zira" in voice.name.lower():
                self.engine.setProperty("voice", voice.id)
                break
        self.engine.setProperty("rate", 175)

    def synthesize(self, text, out_path: Path):
        self.engine.save_to_file(text, str(out_path))
        self.engine.runAndWait()


class OpenAITTS(TTSEngine):
    def __init__(self, api_key):
        if openai is None:
            raise RuntimeError("openai not installed. Run: pip install openai")
        self.client = openai.OpenAI(api_key=api_key)

    def synthesize(self, text, out_path: Path):
        with self.client.audio.speech.with_streaming_response.create(
            model="tts-1", voice="alloy", input=text
        ) as resp:
            resp.stream_to_file(str(out_path))


# ---------------------------------------------------------------------------
# Image generation
# ---------------------------------------------------------------------------
def make_solid_image(path: Path, color, size=(VIDEO_W, VIDEO_H)):
    if Image is None:
        raise RuntimeError("Pillow not installed. Run: pip install Pillow")
    img = Image.new("RGB", size, color)
    img.save(path)


def make_text_image(path: Path, text, bg=(20, 20, 30), fg=(255, 255, 255)):
    """Fallback visual: a colored background with topic text."""
    if Image is None:
        raise RuntimeError("Pillow not installed")
    img = Image.new("RGB", (VIDEO_W, VIDEO_H), bg)
    draw = ImageDraw.Draw(img)
    try:
        font = ImageFont.truetype("arial.ttf", 90)
    except Exception:
        font = ImageFont.load_default()
    # Word-wrap
    words = text.split()
    lines, line = [], ""
    max_w = VIDEO_W - 160
    for w in words:
        test = (line + " " + w).strip()
        if draw.textlength(test, font=font) <= max_w:
            line = test
        else:
            if line:
                lines.append(line)
            line = w
    if line:
        lines.append(line)
    # Center vertically
    line_h = 110
    total_h = line_h * len(lines)
    y = (VIDEO_H - total_h) // 2
    for ln in lines:
        w = draw.textlength(ln, font=font)
        draw.text(((VIDEO_W - w) / 2, y), ln, fill=fg, font=font)
        y += line_h
    img.save(path)


def download_image(url, out_path: Path):
    if requests is None:
        raise RuntimeError("requests not installed")
    r = requests.get(url, timeout=30)
    r.raise_for_status()
    out_path.write_bytes(r.content)


def generate_local_images(topic, count, out_dir: Path):
    """Generate simple text-card visuals for the topic."""
    out_dir.mkdir(parents=True, exist_ok=True)
    palette = [
        ((20, 25, 60), (255, 255, 255)),
        ((60, 20, 40), (255, 240, 200)),
        ((20, 60, 40), (220, 255, 220)),
        ((60, 50, 20), (255, 230, 200)),
        ((40, 20, 60), (230, 220, 255)),
    ]
    paths = []
    for i in range(count):
        bg, fg = palette[i % len(palette)]
        p = out_dir / f"local_{i:02d}.png"
        make_text_image(p, f"{topic}\nPart {i+1}", bg=bg, fg=fg)
        paths.append(p)
    return paths


def generate_picsum_images(count, out_dir: Path):
    """Use picsum.photos for free stock photos (no key required)."""
    out_dir.mkdir(parents=True, exist_ok=True)
    paths = []
    for i in range(count):
        p = out_dir / f"picsum_{i:02d}.jpg"
        url = f"https://picsum.photos/seed/{random.randint(1, 99999)}/{VIDEO_W}/{VIDEO_H}"
        try:
            download_image(url, p)
        except Exception:
            make_solid_image(p, (random.randint(20, 80),) * 3)
        paths.append(p)
    return paths


def generate_ai_images(api_key, topic, count, out_dir: Path, provider="openai"):
    """OpenAI DALL-E image generation."""
    if openai is None or requests is None:
        raise RuntimeError("openai + requests required")
    out_dir.mkdir(parents=True, exist_ok=True)
    client = openai.OpenAI(api_key=api_key)
    paths = []
    for i in range(count):
        try:
            resp = client.images.generate(
                model="dall-e-3",
                prompt=f"Vertical 9:16 cinematic photo about {topic}, scene {i+1}, no text",
                size="1024x1792",
                n=1,
            )
            url = resp.data[0].url
            p = out_dir / f"ai_{i:02d}.jpg"
            download_image(url, p)
            paths.append(p)
        except Exception as e:
            # Fallback to a solid image
            p = out_dir / f"ai_{i:02d}.jpg"
            make_solid_image(p, (random.randint(30, 80),) * 3)
            paths.append(p)
    return paths


# ---------------------------------------------------------------------------
# Subtitle rendering
# ---------------------------------------------------------------------------
def split_script_for_subtitles(text, max_chars=60):
    """Split the script into chunks for short captions."""
    sentences = [s.strip() for s in text.replace("\n", " ").split(".") if s.strip()]
    chunks, current = [], ""
    for s in sentences:
        s = s + "."
        if len(current) + len(s) <= max_chars:
            current = (current + " " + s).strip()
        else:
            if current:
                chunks.append(current)
            current = s
    if current:
        chunks.append(current)
    return chunks


# ---------------------------------------------------------------------------
# Video assembly (ffmpeg)
# ---------------------------------------------------------------------------
def get_audio_duration(audio_path: Path):
    """Get audio duration in seconds using ffprobe."""
    try:
        out = subprocess.check_output(
            [
                "ffprobe", "-v", "error",
                "-show_entries", "format=duration",
                "-of", "default=noprint_wrappers=1:nokey=1",
                str(audio_path),
            ],
            stderr=subprocess.STDOUT,
        )
        return float(out.decode().strip())
    except Exception:
        return 30.0  # fallback


def find_system_font():
    """Return path to a TTF font that ffmpeg's drawtext can use, or None."""
    candidates = []
    if platform.system() == "Windows":
        win_fonts = Path("C:/Windows/Fonts")
        candidates += [
            win_fonts / "arial.ttf", win_fonts / "segoeui.ttf",
            win_fonts / "verdana.ttf", win_fonts / "tahoma.ttf",
        ]
    else:
        candidates += [
            "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
            "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
            "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
            "/usr/share/fonts/truetype/freefont/FreeSansBold.ttf",
            "/usr/share/fonts/TTF/DejaVuSans-Bold.ttf",
        ]
    for c in candidates:
        if Path(c).exists():
            return str(c)
    return None


def _extract_real_ffmpeg_error(stderr: str) -> str:
    """Pull the meaningful error line out of ffmpeg's stderr dump."""
    if not stderr:
        return "ffmpeg failed with no stderr output"
    keywords = ("error", "Error", "ERROR", "Invalid", "No such", "Unable",
                "not found", "could not", "failed", "Missing")
    for line in stderr.splitlines():
        s = line.strip()
        if not s:
            continue
        if s.startswith("--"):
            continue
        if any(k in s for k in keywords):
            return s
    # Fall back to last non-config line
    for line in reversed(stderr.splitlines()):
        s = line.strip()
        if s and not s.startswith("--"):
            return s
    return stderr[-500:]


def assemble_video(image_paths, audio_path: Path, out_path: Path,
                   subtitle_chunks=None, bg_music_path: Path = None):
    """Concatenate images with ken-burns pan, add audio and optional subtitles.

    For each image we use ffmpeg's zoompan filter to create gentle motion.
    """
    ffmpeg = _check_ffmpeg()
    if ffmpeg is None:
        raise RuntimeError("ffmpeg not found on PATH. Install ffmpeg first.")

    audio_dur = get_audio_duration(audio_path)
    n = len(image_paths)
    if n == 0:
        raise RuntimeError("No images to assemble")
    per_image = audio_dur / n

    font_path = find_system_font() if subtitle_chunks else None

    # Build filter complex
    filter_parts = []
    for i in range(n):
        # Each image: force RGB (drop alpha), force even dims, scale, zoompan
        filter_parts.append(
            f"[{i}:v]format=yuv420p,scale={VIDEO_W*2}:{VIDEO_H*2}:"
            f"force_original_aspect_ratio=increase,crop={VIDEO_W*2}:{VIDEO_H*2},"
            f"zoompan=z='min(zoom+0.0015,1.15)':d={int(per_image*25)}:"
            f"x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':"
            f"s={VIDEO_W}x{VIDEO_H}:fps=25[v{i}];"
        )

    concat = "".join(f"[v{i}]" for i in range(n)) + f"concat=n={n}:v=1:a=0[vout]"

    audio_mix = f"[{n}:a]volume=1.0[audio_main]"
    if bg_music_path:
        audio_mix = (
            f"[{n}:a]volume=1.0[audio_main];"
            f"[{n+1}:a]volume=0.15[audio_bg];"
            f"[audio_main][audio_bg]amix=inputs=2:duration=first[audio_out]"
        )

    if subtitle_chunks:
        # Render each chunk as a drawtext for the proportional slice of time
        drawtext_cmds = []
        chunks = subtitle_chunks
        for i, chunk in enumerate(chunks):
            start = i * (audio_dur / len(chunks))
            end = (i + 1) * (audio_dur / len(chunks))
            # Escape single quotes, colons, percent signs, and backslashes for drawtext
            safe = (chunk.replace("\\", "\\\\")
                        .replace("'", "\\'")
                        .replace(":", "\\:")
                        .replace("%", "\\%"))
            font_part = f"fontfile='{font_path}':" if font_path else ""
            drawtext_cmds.append(
                f"drawtext={font_part}text='{safe}':"
                f"fontcolor=white:fontsize=64:box=1:boxcolor=black@0.6:boxborderw=20:"
                f"x=(w-text_w)/2:y=h-280:"
                f"enable='between(t,{start:.2f},{end:.2f})'"
            )
        subtitle_filter = ",".join(drawtext_cmds)
        concat += f";[vout]{subtitle_filter}[vfinal]"
    else:
        concat = "".join(f"[v{i}]" for i in range(n)) + f"concat=n={n}:v=1:a=0[vout]"

    full_filter = "".join(filter_parts) + audio_mix + ";" + concat

    cmd = [ffmpeg, "-y", "-hide_banner", "-loglevel", "error"]
    # Image inputs need -loop 1 so ffmpeg treats them as video streams
    for p in image_paths:
        cmd += ["-loop", "1", "-t", str(audio_dur + 1), "-framerate", "25", "-i", str(p)]
    # Audio input
    cmd += ["-i", str(audio_path)]
    if bg_music_path:
        cmd += ["-i", str(bg_music_path)]

    cmd += [
        "-filter_complex", full_filter,
        "-map", "[vfinal]" if subtitle_chunks else "[vout]",
        "-map", "[audio_out]" if bg_music_path else f"[{n}:a]",
        "-c:v", "libx264", "-preset", "fast", "-crf", "22",
        "-c:a", "aac", "-b:a", "192k",
        "-pix_fmt", "yuv420p", "-movflags", "+faststart",
        "-shortest", str(out_path),
    ]

    try:
        result = subprocess.run(cmd, check=True, capture_output=True, text=True)
    except subprocess.CalledProcessError as e:
        err = _extract_real_ffmpeg_error(e.stderr or "")
        raise RuntimeError(f"ffmpeg failed: {err}")


# ---------------------------------------------------------------------------
# GUI
# ---------------------------------------------------------------------------
class ToTheMaxApp:
    def __init__(self, root):
        self.root = root
        self.root.title(APP_TITLE)
        self.root.geometry("1100x820")
        self.root.minsize(900, 700)

        # State
        self.mode_var = StringVar(value="Local")
        self.style_var = StringVar(value="informative")
        self.topic_var = StringVar()
        self.subtopic_var = StringVar()
        self.openai_key_var = StringVar()
        self.openrouter_key_var = StringVar()
        self.claude_model_var = StringVar(value="anthropic/claude-sonnet-5")
        self.opencode_model_var = StringVar(value="minimax/minimax-m3:free")
        self.use_ai_images = BooleanVar(value=False)
        self.use_ai_tts = BooleanVar(value=False)
        self.use_subtitles = BooleanVar(value=True)
        self.status_var = StringVar(value="Ready")

        self.selected_images = []
        self.last_video_path = None

        self._build_ui()

    # --- layout -----------------------------------------------------------
    def _build_ui(self):
        pad = {"padx": 10, "pady": 6}

        # Row 0: Mode
        ttk.Label(self.root, text="Generation Mode:").grid(row=0, column=0, sticky="w", **pad)
        mode_cb = ttk.Combobox(
            self.root, textvariable=self.mode_var, state="readonly",
            values=["Local", "Cloud AI (OpenAI)", "Full AI Pipeline",
                    "Claude (OpenRouter)", "Opencode (OpenRouter)"],
            width=50,
        )
        mode_cb.grid(row=0, column=1, columnspan=2, sticky="ew", **pad)
        mode_cb.bind("<<ComboboxSelected>>", lambda e: self._update_visibility())

        # API key rows (hidden by default)
        self.openai_label = ttk.Label(self.root, text="OpenAI API Key:")
        self.openai_entry = ttk.Entry(self.root, textvariable=self.openai_key_var, show="*", width=60)

        self.openrouter_label = ttk.Label(self.root, text="OpenRouter API Key:")
        self.openrouter_entry = ttk.Entry(self.root, textvariable=self.openrouter_key_var, show="*", width=60)

        self.claude_model_label = ttk.Label(self.root, text="Claude Model:")
        self.claude_model_entry = ttk.Entry(self.root, textvariable=self.claude_model_var, width=60)

        self.opencode_model_label = ttk.Label(self.root, text="Opencode Model:")
        self.opencode_model_entry = ttk.Entry(self.root, textvariable=self.opencode_model_var, width=60)

        # Style
        ttk.Label(self.root, text="Style:").grid(row=4, column=0, sticky="w", **pad)
        ttk.Combobox(
            self.root, textvariable=self.style_var, state="readonly",
            values=["informative", "motivational", "funny", "mysterious", "educational"],
            width=20,
        ).grid(row=4, column=1, sticky="w", **pad)

        # Topic
        ttk.Label(self.root, text="Topic/Prompt:").grid(row=5, column=0, sticky="w", **pad)
        ttk.Entry(self.root, textvariable=self.topic_var, width=80).grid(
            row=5, column=1, columnspan=2, sticky="ew", **pad)

        # Subtopic
        ttk.Label(self.root, text="Sub-topic/Notes:").grid(row=6, column=0, sticky="w", **pad)
        ttk.Entry(self.root, textvariable=self.subtopic_var, width=80).grid(
            row=6, column=1, columnspan=2, sticky="ew", **pad)

        # AI options (Full AI Pipeline)
        self.ai_opts_frame = ttk.LabelFrame(self.root, text="Full AI Pipeline Options")
        self.ai_opts_frame.grid(row=7, column=0, columnspan=3, sticky="ew", padx=10, pady=6)
        ttk.Checkbutton(self.ai_opts_frame, text="Use AI image generation (DALL-E)",
                        variable=self.use_ai_images).grid(row=0, column=0, sticky="w", padx=10)
        ttk.Checkbutton(self.ai_opts_frame, text="Use AI text-to-speech (OpenAI TTS)",
                        variable=self.use_ai_tts).grid(row=0, column=1, sticky="w", padx=10)
        ttk.Checkbutton(self.ai_opts_frame, text="Add burned-in subtitles",
                        variable=self.use_subtitles).grid(row=0, column=2, sticky="w", padx=10)

        # Buttons
        btn_frame = ttk.Frame(self.root)
        btn_frame.grid(row=8, column=0, columnspan=3, pady=12)
        ttk.Button(btn_frame, text="Select Images", command=self._select_images).grid(row=0, column=0, padx=6)
        ttk.Button(btn_frame, text="Generate Short", command=self._start_generation).grid(row=0, column=1, padx=6)
        ttk.Button(btn_frame, text="Save Video", command=self._save_video).grid(row=0, column=2, padx=6)

        # Script + Preview
        lower = ttk.Frame(self.root)
        lower.grid(row=9, column=0, columnspan=3, sticky="nsew", padx=10, pady=6)
        self.root.rowconfigure(9, weight=1)
        self.root.columnconfigure(1, weight=1)
        lower.columnconfigure(0, weight=1)
        lower.columnconfigure(1, weight=1)
        lower.rowconfigure(1, weight=1)

        ttk.Label(lower, text="Generated Script:").grid(row=0, column=0, sticky="w")
        ttk.Label(lower, text="Preview Video:").grid(row=0, column=1, sticky="w")

        self.script_box = ScrolledText(lower, wrap="word", height=22)
        self.script_box.grid(row=1, column=0, sticky="nsew", padx=(0, 6))

        self.preview_frame = ttk.Frame(lower, relief="sunken", width=VIDEO_W // 2, height=VIDEO_H // 2)
        self.preview_frame.grid(row=1, column=1, sticky="nsew", padx=(6, 0))
        self.preview_frame.grid_propagate(False)
        self.preview_label = ttk.Label(self.preview_frame, text="(preview appears here)", anchor="center")
        self.preview_label.place(relx=0.5, rely=0.5, anchor="center")

        # Status bar
        status = ttk.Frame(self.root)
        status.grid(row=10, column=0, columnspan=3, sticky="ew", padx=10, pady=4)
        ttk.Label(status, textvariable=self.status_var, foreground="#1a73e8").pack(side="left")
        ttk.Label(status, text=f"Output: {OUTPUT_DIR}", foreground="#666").pack(side="right")

        self._update_visibility()

    def _update_visibility(self):
        mode = self.mode_var.get()
        # Hide all conditional rows first
        for w in (self.openai_label, self.openai_entry,
                  self.openrouter_label, self.openrouter_entry,
                  self.claude_model_label, self.claude_model_entry,
                  self.opencode_model_label, self.opencode_model_entry,
                  self.ai_opts_frame):
            w.grid_remove()

        if mode == "Cloud AI (OpenAI)":
            self.openai_label.grid(row=1, column=0, sticky="w", padx=10, pady=6)
            self.openai_entry.grid(row=1, column=1, columnspan=2, sticky="ew", padx=10, pady=6)
        elif mode == "Full AI Pipeline":
            self.openai_label.grid(row=1, column=0, sticky="w", padx=10, pady=6)
            self.openai_entry.grid(row=1, column=1, columnspan=2, sticky="ew", padx=10, pady=6)
            self.ai_opts_frame.grid(row=2, column=0, columnspan=3, sticky="ew", padx=10, pady=6)
        elif mode == "Claude (OpenRouter)":
            self.openrouter_label.grid(row=1, column=0, sticky="w", padx=10, pady=6)
            self.openrouter_entry.grid(row=1, column=1, columnspan=2, sticky="ew", padx=10, pady=6)
            self.claude_model_label.grid(row=2, column=0, sticky="w", padx=10, pady=6)
            self.claude_model_entry.grid(row=2, column=1, columnspan=2, sticky="ew", padx=10, pady=6)
        elif mode == "Opencode (OpenRouter)":
            self.openrouter_label.grid(row=1, column=0, sticky="w", padx=10, pady=6)
            self.openrouter_entry.grid(row=1, column=1, columnspan=2, sticky="ew", padx=10, pady=6)
            self.opencode_model_label.grid(row=2, column=0, sticky="w", padx=10, pady=6)
            self.opencode_model_entry.grid(row=2, column=1, columnspan=2, sticky="ew", padx=10, pady=6)

    # --- actions ----------------------------------------------------------
    def _select_images(self):
        paths = filedialog.askopenfilenames(
            title="Select images for the short",
            filetypes=[("Images", "*.png *.jpg *.jpeg *.webp *.bmp")],
        )
        if paths:
            self.selected_images = [Path(p) for p in paths]
            self._set_status(f"Selected {len(self.selected_images)} images")

    def _set_status(self, msg):
        self.status_var.set(msg)
        self.root.update_idletasks()

    def _start_generation(self):
        if not self.topic_var.get().strip():
            messagebox.showwarning("Missing topic", "Please enter a topic/prompt.")
            return
        thread = threading.Thread(target=self._run_pipeline, daemon=True)
        thread.start()

    def _save_video(self):
        if not self.last_video_path or not self.last_video_path.exists():
            messagebox.showinfo("No video", "Generate a short first.")
            return
        dest = filedialog.asksaveasfilename(
            defaultextension=".mp4",
            initialfile=self.last_video_path.name,
            filetypes=[("MP4 video", "*.mp4")],
        )
        if dest:
            try:
                from shutil import copyfile
                copyfile(self.last_video_path, dest)
                self._set_status(f"Saved to {dest}")
            except Exception as e:
                messagebox.showerror("Save failed", str(e))

    # --- pipeline ---------------------------------------------------------
    def _run_pipeline(self):
        try:
            self._set_status("Starting generation...")
            topic = self.topic_var.get().strip()
            mode = self.mode_var.get()
            style = self.style_var.get()

            # 1. Script
            self._set_status("Generating script...")
            script = self._generate_script(topic, mode, style)
            self.script_box.delete("1.0", "end")
            self.script_box.insert("end", script)

            # 2. Audio (TTS)
            self._set_status("Synthesizing voice...")
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            work_dir = OUTPUT_DIR / f"short_{timestamp}"
            work_dir.mkdir(parents=True, exist_ok=True)
            audio_path = work_dir / "voice.mp3"
            self._synthesize_speech(script, mode, audio_path)

            # 3. Images
            self._set_status("Preparing visuals...")
            img_count = 5
            if self.selected_images:
                image_paths = self.selected_images
            elif mode == "Full AI Pipeline" and self.use_ai_images.get() and self.openai_key_var.get().strip():
                image_paths = generate_ai_images(
                    self.openai_key_var.get().strip(), topic, img_count,
                    work_dir / "images", provider="openai",
                )
            else:
                image_paths = generate_picsum_images(img_count, work_dir / "images")

            # 4. Video assembly
            self._set_status("Assembling video with ffmpeg...")
            out_path = work_dir / "short.mp4"
            subtitles = split_script_for_subtitles(script) if self.use_subtitles.get() else None
            assemble_video(image_paths, audio_path, out_path, subtitle_chunks=subtitles)

            self.last_video_path = out_path
            self._show_preview(out_path)
            self._set_status(f"Done! Video saved to {out_path}")

            messagebox.showinfo("Success", f"Short generated!\n\n{out_path}")
        except Exception as e:
            self._set_status(f"Error: {e}")
            messagebox.showerror("Generation failed", str(e))

    def _generate_script(self, topic, mode, style):
        if mode == "Local":
            return LocalScriptGenerator().generate(topic, style)
        if mode == "Cloud AI (OpenAI)":
            return OpenAIScriptGenerator(self.openai_key_var.get().strip()).generate(topic, style)
        if mode == "Full AI Pipeline":
            return OpenAIScriptGenerator(self.openai_key_var.get().strip()).generate(topic, style)
        if mode == "Claude (OpenRouter)":
            return OpenRouterScriptGenerator(
                self.openrouter_key_var.get().strip(),
                self.claude_model_var.get().strip(),
                "Claude",
            ).generate(topic, style)
        if mode == "Opencode (OpenRouter)":
            return OpenRouterScriptGenerator(
                self.openrouter_key_var.get().strip(),
                self.opencode_model_var.get().strip(),
                "Opencode",
            ).generate(topic, style)
        raise RuntimeError(f"Unknown mode: {mode}")

    def _synthesize_speech(self, text, mode, out_path: Path):
        # OpenAI TTS for Cloud/Full AI modes if requested
        if mode == "Full AI Pipeline" and self.use_ai_tts.get() and self.openai_key_var.get().strip():
            OpenAITTS(self.openai_key_var.get().strip()).synthesize(text, out_path)
            return
        # Default: offline TTS
        LocalTTS().synthesize(text, out_path)

    def _show_preview(self, video_path: Path):
        """Extract a thumbnail from the video and show it in the preview pane."""
        try:
            from shutil import which
            ffmpeg = which("ffmpeg")
            if ffmpeg is None:
                return
            thumb = video_path.parent / "thumb.jpg"
            subprocess.run(
                [ffmpeg, "-y", "-i", str(video_path), "-ss", "00:00:01",
                 "-vframes", "1", "-q:v", "2", str(thumb)],
                check=True, capture_output=True,
            )
            try:
                from PIL import Image, ImageTk
                img = Image.open(thumb)
                # Fit into preview frame
                w = self.preview_frame.winfo_width() or 400
                h = self.preview_frame.winfo_height() or 700
                img.thumbnail((w, h))
                photo = ImageTk.PhotoImage(img)
                self.preview_label.configure(image=photo, text="")
                self.preview_label.image = photo
            except Exception:
                self.preview_label.configure(text=f"Saved:\n{video_path}")
        except Exception:
            self.preview_label.configure(text=f"Saved:\n{video_path}")


def main():
    # Try to install optional deps silently so the pipeline works
    _install_optional_dependencies()

    # Verify ffmpeg
    if _check_ffmpeg() is None:
        msg = (
            "ffmpeg was not detected on your PATH.\n\n"
            "Install it before generating videos:\n"
            "  Windows: download from https://ffmpeg.org and add to PATH\n"
            "  Linux:   sudo apt install ffmpeg   (or your distro's package manager)\n\n"
            "You can still launch the app to view/generate scripts."
        )
        print("WARNING:", msg)

    root = Tk()
    ToTheMaxApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
