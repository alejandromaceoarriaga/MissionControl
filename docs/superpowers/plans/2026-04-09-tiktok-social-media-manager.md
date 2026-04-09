# TikTok Social Media Manager Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a fully automated TikTok pipeline that generates curiosity videos with Claude, renders them with FFmpeg+gTTS, uploads via TikTok API v2, auto-responds to comments, and displays a quality analytics dashboard — all free tools, triggered by n8n.

**Architecture:** Python modules handle generation, rendering, and upload. A Flask server exposes a webhook so n8n can trigger the pipeline on a cron schedule. Three n8n workflows handle scheduling, comment responses, and analytics. All state persists in a single `state.json` file.

**Tech Stack:** Python 3.14, `anthropic`, `gtts`, `ffmpeg-python`, `flask`, `requests`, `python-dotenv`, `pytest`, FFmpeg 8.x (already installed), n8n (self-hosted via Docker)

---

## File Map

| File | Responsibility |
|------|---------------|
| `tiktok-manager/.env.template` | Credential template (committed) |
| `tiktok-manager/.env` | Actual secrets (gitignored) |
| `tiktok-manager/requirements.txt` | Python dependencies |
| `tiktok-manager/modules/state.py` | Read/write `outputs/state.json` |
| `tiktok-manager/modules/script_generator.py` | Claude API → structured curiosity script |
| `tiktok-manager/modules/tts.py` | gTTS → MP3 audio |
| `tiktok-manager/modules/video_builder.py` | FFmpeg → 1080×1920 MP4 |
| `tiktok-manager/modules/tiktok_auth.py` | OAuth 2.0 flow + token refresh |
| `tiktok-manager/modules/tiktok_uploader.py` | Upload + publish video to TikTok |
| `tiktok-manager/pipeline.py` | Orchestrate all modules end-to-end |
| `tiktok-manager/server.py` | Flask webhook server (n8n trigger + OAuth callback) |
| `tiktok-manager/n8n-workflows/scheduler.json` | n8n Workflow 1: Cron → pipeline |
| `tiktok-manager/n8n-workflows/comment-responder.json` | n8n Workflow 2: Auto-reply comments |
| `tiktok-manager/n8n-workflows/analytics.json` | n8n Workflow 3: Dashboard generator |
| `tiktok-manager/tests/test_state.py` | Tests for state module |
| `tiktok-manager/tests/test_script_generator.py` | Tests for script generator |
| `tiktok-manager/tests/test_tts.py` | Tests for TTS module |
| `tiktok-manager/tests/test_video_builder.py` | Tests for video builder |
| `tiktok-manager/tests/test_tiktok_uploader.py` | Tests for uploader |
| `tiktok-manager/tests/test_pipeline.py` | Integration test for full pipeline |

---

## Task 1: Project Scaffold

**Files:**
- Create: `tiktok-manager/requirements.txt`
- Create: `tiktok-manager/.env.template`
- Create: `tiktok-manager/.gitignore`
- Create: `tiktok-manager/modules/__init__.py`
- Create: `tiktok-manager/tests/__init__.py`
- Create: `tiktok-manager/outputs/.gitkeep`
- Create: `tiktok-manager/outputs/videos/.gitkeep`
- Create: `tiktok-manager/assets/backgrounds/.gitkeep`
- Create: `tiktok-manager/assets/fonts/.gitkeep`
- Create: `tiktok-manager/assets/music/.gitkeep`
- Create: `tiktok-manager/n8n-workflows/.gitkeep`

- [ ] **Step 1: Create directory structure**

```bash
cd tiktok-manager  # run from MissionControl root
mkdir -p tiktok-manager/modules
mkdir -p tiktok-manager/tests
mkdir -p tiktok-manager/outputs/videos
mkdir -p tiktok-manager/assets/backgrounds
mkdir -p tiktok-manager/assets/fonts
mkdir -p tiktok-manager/assets/music
mkdir -p tiktok-manager/n8n-workflows
touch tiktok-manager/modules/__init__.py
touch tiktok-manager/tests/__init__.py
touch tiktok-manager/outputs/.gitkeep
touch tiktok-manager/outputs/videos/.gitkeep
touch tiktok-manager/assets/backgrounds/.gitkeep
touch tiktok-manager/assets/fonts/.gitkeep
touch tiktok-manager/assets/music/.gitkeep
touch tiktok-manager/n8n-workflows/.gitkeep
```

- [ ] **Step 2: Create `tiktok-manager/requirements.txt`**

```
anthropic>=0.40.0
gtts>=2.5.1
ffmpeg-python>=0.2.0
flask>=3.0.0
requests>=2.31.0
python-dotenv>=1.0.0
pytest>=8.0.0
pytest-mock>=3.12.0
```

- [ ] **Step 3: Create `tiktok-manager/.env.template`**

```
ANTHROPIC_API_KEY=sk-ant-...your-key-here...
TIKTOK_CLIENT_ID=your-client-id
TIKTOK_CLIENT_SECRET=your-client-secret-ROTATED
TIKTOK_REDIRECT_URI=http://localhost:8765/callback
PIPELINE_WEBHOOK_PORT=8765
```

- [ ] **Step 4: Create `tiktok-manager/.gitignore`**

```
.env
outputs/videos/*.mp4
outputs/audio_*.mp3
outputs/state.json
outputs/dashboard.html
outputs/errors.log
__pycache__/
*.pyc
.pytest_cache/
```

- [ ] **Step 5: Copy `.env.template` to `.env` and fill in real values**

```bash
cp tiktok-manager/.env.template tiktok-manager/.env
# Edit .env: add your ANTHROPIC_API_KEY and rotated TIKTOK_CLIENT_SECRET
```

- [ ] **Step 6: Install dependencies**

```bash
cd tiktok-manager
pip install -r requirements.txt
```

Expected output: `Successfully installed anthropic-X.X.X gtts-X.X.X ffmpeg-python-X.X.X flask-X.X.X ...`

- [ ] **Step 7: Commit scaffold**

```bash
git add tiktok-manager/
git commit -m "feat: scaffold tiktok-manager project structure"
```

---

## Task 2: State Manager

**Files:**
- Create: `tiktok-manager/modules/state.py`
- Create: `tiktok-manager/tests/test_state.py`

- [ ] **Step 1: Write the failing test**

Create `tiktok-manager/tests/test_state.py`:

```python
import json
import os
import pytest
from unittest.mock import patch, mock_open
from modules.state import load_state, save_state, DEFAULT_STATE


def test_load_state_returns_default_when_file_missing(tmp_path):
    state_path = tmp_path / "state.json"
    state = load_state(str(state_path))
    assert state["videos_published"] == []
    assert state["last_10_topics"] == []
    assert state["comments_replied"] == []
    assert state["daily_count"] == 0
    assert state["last_video_id"] is None
    assert state["tiktok_access_token"] is None
    assert state["tiktok_refresh_token"] is None
    assert state["token_expires_at"] is None


def test_load_state_reads_existing_file(tmp_path):
    state_path = tmp_path / "state.json"
    data = {**DEFAULT_STATE, "daily_count": 3, "last_video_id": "7abc"}
    state_path.write_text(json.dumps(data))
    state = load_state(str(state_path))
    assert state["daily_count"] == 3
    assert state["last_video_id"] == "7abc"


def test_save_state_writes_json(tmp_path):
    state_path = tmp_path / "state.json"
    state = {**DEFAULT_STATE, "daily_count": 5}
    save_state(state, str(state_path))
    saved = json.loads(state_path.read_text())
    assert saved["daily_count"] == 5


def test_save_state_creates_parent_dirs(tmp_path):
    state_path = tmp_path / "nested" / "dir" / "state.json"
    save_state(DEFAULT_STATE, str(state_path))
    assert state_path.exists()
```

- [ ] **Step 2: Run test to verify it fails**

```bash
cd tiktok-manager
python -m pytest tests/test_state.py -v
```

Expected: `ModuleNotFoundError: No module named 'modules.state'`

- [ ] **Step 3: Implement `tiktok-manager/modules/state.py`**

```python
import json
import os
from typing import Any

STATE_PATH = os.path.join(os.path.dirname(__file__), "..", "outputs", "state.json")

DEFAULT_STATE: dict[str, Any] = {
    "last_video_id": None,
    "videos_published": [],
    "last_10_topics": [],
    "comments_replied": [],
    "daily_count": 0,
    "last_upload_ts": None,
    "tiktok_access_token": None,
    "tiktok_refresh_token": None,
    "token_expires_at": None,
}


def load_state(path: str = STATE_PATH) -> dict[str, Any]:
    """Load state from JSON file, returning defaults if file doesn't exist."""
    if not os.path.exists(path):
        return dict(DEFAULT_STATE)
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    return {**DEFAULT_STATE, **data}


def save_state(state: dict[str, Any], path: str = STATE_PATH) -> None:
    """Write state dict to JSON file, creating parent dirs if needed."""
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(state, f, indent=2, ensure_ascii=False)
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
cd tiktok-manager
python -m pytest tests/test_state.py -v
```

Expected: `4 passed`

- [ ] **Step 5: Commit**

```bash
git add tiktok-manager/modules/state.py tiktok-manager/tests/test_state.py
git commit -m "feat: add state manager module"
```

---

## Task 3: Script Generator

**Files:**
- Create: `tiktok-manager/modules/script_generator.py`
- Create: `tiktok-manager/tests/test_script_generator.py`

- [ ] **Step 1: Write the failing test**

Create `tiktok-manager/tests/test_script_generator.py`:

```python
import pytest
from unittest.mock import MagicMock, patch
from modules.script_generator import generate_script, ScriptOutput


def make_mock_anthropic_response(content: str):
    mock_msg = MagicMock()
    mock_msg.content = [MagicMock(text=content)]
    return mock_msg


SAMPLE_JSON = '''{
  "topic": "pulpos",
  "hook": "¿Sabías que los pulpos tienen 3 corazones?",
  "body": "Los pulpos son criaturas fascinantes. Tienen tres corazones: dos bombean sangre a las branquias, mientras el tercero la envía al resto del cuerpo. Su sangre es azul porque contiene hemocianina con cobre, no hemoglobina con hierro.",
  "cta": "Síguenos para más datos ocultos 🔍",
  "caption": "¿Sabías que los pulpos tienen 3 corazones? 🐙 #datoscuriosos #ciencia #eldatocurioso #curiosidades #animales"
}'''


def test_generate_script_returns_script_output(mocker):
    mock_client = mocker.patch("modules.script_generator.anthropic.Anthropic")
    mock_instance = mock_client.return_value
    mock_instance.messages.create.return_value = make_mock_anthropic_response(SAMPLE_JSON)

    result = generate_script(last_topics=["ballenas", "delfines"])

    assert isinstance(result, dict)
    assert result["topic"] == "pulpos"
    assert result["hook"].startswith("¿Sabías")
    assert len(result["body"]) > 50
    assert result["cta"] != ""
    assert "#datoscuriosos" in result["caption"]


def test_generate_script_passes_last_topics_to_claude(mocker):
    mock_client = mocker.patch("modules.script_generator.anthropic.Anthropic")
    mock_instance = mock_client.return_value
    mock_instance.messages.create.return_value = make_mock_anthropic_response(SAMPLE_JSON)

    generate_script(last_topics=["tema1", "tema2"])

    call_kwargs = mock_instance.messages.create.call_args
    prompt_text = call_kwargs.kwargs["messages"][0]["content"]
    assert "tema1" in prompt_text
    assert "tema2" in prompt_text


def test_generate_script_retries_on_invalid_json(mocker):
    mock_client = mocker.patch("modules.script_generator.anthropic.Anthropic")
    mock_instance = mock_client.return_value
    bad_response = make_mock_anthropic_response("not json at all")
    good_response = make_mock_anthropic_response(SAMPLE_JSON)
    mock_instance.messages.create.side_effect = [bad_response, good_response]

    result = generate_script(last_topics=[])
    assert result["topic"] == "pulpos"
```

- [ ] **Step 2: Run test to verify it fails**

```bash
cd tiktok-manager
python -m pytest tests/test_script_generator.py -v
```

Expected: `ModuleNotFoundError: No module named 'modules.script_generator'`

- [ ] **Step 3: Implement `tiktok-manager/modules/script_generator.py`**

```python
import json
import os
import time
from typing import Any, TypedDict

import anthropic
from dotenv import load_dotenv

load_dotenv()

ScriptOutput = TypedDict("ScriptOutput", {
    "topic": str,
    "hook": str,
    "body": str,
    "cta": str,
    "caption": str,
})

SYSTEM_PROMPT = """Eres un creador de contenido viral de TikTok especializado en curiosidades sorprendentes en español.
Generas guiones cortos, impactantes y educativos para videos de 60-90 segundos.
Siempre respondes ÚNICAMENTE con JSON válido, sin texto adicional."""

USER_PROMPT_TEMPLATE = """Genera un guion para un video de TikTok sobre una curiosidad sorprendente.

Temas ya usados (NO repetir): {last_topics}

Devuelve SOLO este JSON (sin markdown, sin texto extra):
{{
  "topic": "nombre corto del tema (1-3 palabras)",
  "hook": "frase de apertura impactante de máximo 15 palabras que empiece con ¿Sabías que...?",
  "body": "3-4 datos curiosos en español, entre 60 y 80 palabras en total, estilo conversacional",
  "cta": "llamada a la acción de máximo 10 palabras para seguir la cuenta",
  "caption": "texto del post en TikTok con emojis y hashtags, máximo 200 chars, incluir #datoscuriosos #eldatocurioso"
}}"""


def generate_script(last_topics: list[str], max_retries: int = 3) -> ScriptOutput:
    """Call Claude API to generate a curiosity video script. Retries on invalid JSON."""
    client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
    prompt = USER_PROMPT_TEMPLATE.format(
        last_topics=", ".join(last_topics) if last_topics else "ninguno"
    )

    for attempt in range(max_retries):
        try:
            response = client.messages.create(
                model="claude-haiku-4-5-20251001",
                max_tokens=512,
                system=SYSTEM_PROMPT,
                messages=[{"role": "user", "content": prompt}],
            )
            raw = response.content[0].text.strip()
            # Strip markdown code fences if present
            if raw.startswith("```"):
                raw = raw.split("```")[1]
                if raw.startswith("json"):
                    raw = raw[4:]
            return json.loads(raw)
        except (json.JSONDecodeError, KeyError, IndexError) as e:
            if attempt == max_retries - 1:
                raise RuntimeError(f"Claude returned invalid JSON after {max_retries} attempts: {e}")
            time.sleep(2 ** attempt)

    raise RuntimeError("generate_script: unreachable")
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
cd tiktok-manager
python -m pytest tests/test_script_generator.py -v
```

Expected: `3 passed`

- [ ] **Step 5: Commit**

```bash
git add tiktok-manager/modules/script_generator.py tiktok-manager/tests/test_script_generator.py
git commit -m "feat: add Claude script generator module"
```

---

## Task 4: TTS Module

**Files:**
- Create: `tiktok-manager/modules/tts.py`
- Create: `tiktok-manager/tests/test_tts.py`

- [ ] **Step 1: Write the failing test**

Create `tiktok-manager/tests/test_tts.py`:

```python
import os
import pytest
from unittest.mock import MagicMock, patch


def test_generate_audio_returns_output_path(tmp_path, mocker):
    mock_gtts = mocker.patch("modules.tts.gTTS")
    mock_instance = MagicMock()
    mock_gtts.return_value = mock_instance

    from modules.tts import generate_audio
    output_path = str(tmp_path / "audio.mp3")
    result = generate_audio("Hola mundo", output_path)

    assert result == output_path
    mock_gtts.assert_called_once_with(text="Hola mundo", lang="es", slow=False)
    mock_instance.save.assert_called_once_with(output_path)


def test_generate_audio_creates_parent_dirs(tmp_path, mocker):
    mock_gtts = mocker.patch("modules.tts.gTTS")
    mock_instance = MagicMock()
    mock_gtts.return_value = mock_instance

    from modules.tts import generate_audio
    output_path = str(tmp_path / "nested" / "dir" / "audio.mp3")
    generate_audio("Test", output_path)

    assert os.path.isdir(str(tmp_path / "nested" / "dir"))


def test_generate_audio_builds_full_script_from_parts(mocker):
    mock_gtts = mocker.patch("modules.tts.gTTS")
    mock_gtts.return_value = MagicMock()

    from modules.tts import generate_audio_from_script
    script = {
        "hook": "¿Sabías que los pulpos tienen 3 corazones?",
        "body": "Cuerpo del guion aquí.",
        "cta": "Síguenos para más datos.",
    }
    generate_audio_from_script(script, "/tmp/test.mp3")

    call_text = mock_gtts.call_args.kwargs["text"]
    assert "pulpos" in call_text
    assert "Cuerpo del guion" in call_text
    assert "Síguenos" in call_text
```

- [ ] **Step 2: Run test to verify it fails**

```bash
cd tiktok-manager
python -m pytest tests/test_tts.py -v
```

Expected: `ModuleNotFoundError: No module named 'modules.tts'`

- [ ] **Step 3: Implement `tiktok-manager/modules/tts.py`**

```python
import os
from gtts import gTTS


def generate_audio(text: str, output_path: str) -> str:
    """Convert text to MP3 using gTTS. Returns output_path."""
    os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
    tts = gTTS(text=text, lang="es", slow=False)
    tts.save(output_path)
    return output_path


def generate_audio_from_script(script: dict, output_path: str) -> str:
    """Build full TTS text from script dict (hook + body + cta) and save to output_path."""
    full_text = f"{script['hook']}. {script['body']}. {script['cta']}"
    return generate_audio(full_text, output_path)
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
cd tiktok-manager
python -m pytest tests/test_tts.py -v
```

Expected: `3 passed`

- [ ] **Step 5: Commit**

```bash
git add tiktok-manager/modules/tts.py tiktok-manager/tests/test_tts.py
git commit -m "feat: add gTTS audio generation module"
```

---

## Task 5: Video Builder

**Files:**
- Create: `tiktok-manager/modules/video_builder.py`
- Create: `tiktok-manager/tests/test_video_builder.py`

- [ ] **Step 1: Write the failing test**

Create `tiktok-manager/tests/test_video_builder.py`:

```python
import os
import pytest
from unittest.mock import MagicMock, patch


def test_build_video_calls_ffmpeg(tmp_path, mocker):
    mock_ffmpeg = mocker.patch("modules.video_builder.ffmpeg")
    mock_input = MagicMock()
    mock_ffmpeg.input.return_value = mock_input
    mock_input.video.return_value = MagicMock()
    mock_input.audio.return_value = MagicMock()
    mock_ffmpeg.filter.return_value = MagicMock()
    mock_ffmpeg.output.return_value = MagicMock()
    mock_ffmpeg.run.return_value = None

    bg_image = tmp_path / "bg.jpg"
    bg_image.write_bytes(b"fake")
    audio_file = tmp_path / "audio.mp3"
    audio_file.write_bytes(b"fake")
    output_path = str(tmp_path / "output.mp4")

    from modules.video_builder import build_video
    script = {"hook": "¿Sabías algo?", "body": "Cuerpo.", "cta": "Síguenos.", "topic": "pulpos"}
    result = build_video(script, str(audio_file), output_path, str(bg_image))

    assert result == output_path
    assert mock_ffmpeg.input.called


def test_select_random_background_returns_file(tmp_path):
    bg_dir = tmp_path / "backgrounds"
    bg_dir.mkdir()
    (bg_dir / "bg1.jpg").write_bytes(b"img")
    (bg_dir / "bg2.jpg").write_bytes(b"img")

    from modules.video_builder import select_random_background
    result = select_random_background(str(bg_dir))
    assert result.endswith(".jpg")
    assert os.path.exists(result)


def test_select_random_background_raises_when_empty(tmp_path):
    bg_dir = tmp_path / "empty"
    bg_dir.mkdir()

    from modules.video_builder import select_random_background
    with pytest.raises(FileNotFoundError, match="No background images"):
        select_random_background(str(bg_dir))
```

- [ ] **Step 2: Run test to verify it fails**

```bash
cd tiktok-manager
python -m pytest tests/test_video_builder.py -v
```

Expected: `ModuleNotFoundError: No module named 'modules.video_builder'`

- [ ] **Step 3: Implement `tiktok-manager/modules/video_builder.py`**

```python
import os
import random
import subprocess
from typing import Optional

import ffmpeg

BACKGROUNDS_DIR = os.path.join(os.path.dirname(__file__), "..", "assets", "backgrounds")
FONTS_DIR = os.path.join(os.path.dirname(__file__), "..", "assets", "fonts")
MUSIC_DIR = os.path.join(os.path.dirname(__file__), "..", "assets", "music")
WATERMARK_TEXT = "@eldatocurioso"


def select_random_background(backgrounds_dir: str = BACKGROUNDS_DIR) -> str:
    """Return path to a random background image/video from the given directory."""
    files = [
        os.path.join(backgrounds_dir, f)
        for f in os.listdir(backgrounds_dir)
        if f.lower().endswith((".jpg", ".jpeg", ".png", ".mp4"))
    ]
    if not files:
        raise FileNotFoundError(f"No background images found in {backgrounds_dir}")
    return random.choice(files)


def build_video(
    script: dict,
    audio_path: str,
    output_path: str,
    background_path: Optional[str] = None,
) -> str:
    """
    Build a 1080x1920 TikTok video using FFmpeg.
    Overlays hook + body text on background, mixes TTS audio.
    Returns output_path.
    """
    os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)

    if background_path is None:
        background_path = select_random_background()

    # Build FFmpeg command via subprocess for full control
    hook_text = script["hook"].replace("'", "\\'").replace(":", "\\:")
    watermark = WATERMARK_TEXT.replace("@", "\\@")

    # Font path (use default if custom font not found)
    font_path = _find_font()
    font_arg = f":fontfile={font_path}" if font_path else ""

    cmd = [
        "ffmpeg", "-y",
        "-loop", "1", "-i", background_path,   # background image as video
        "-i", audio_path,                         # TTS audio
        "-vf", (
            f"scale=1080:1920:force_original_aspect_ratio=increase,"
            f"crop=1080:1920,"
            f"drawtext=text='{hook_text}'"
            f":fontcolor=white:fontsize=52:x=(w-text_w)/2:y=h*0.35"
            f":borderw=3:bordercolor=black{font_arg},"
            f"drawtext=text='{watermark}'"
            f":fontcolor=white:fontsize=32:x=w-tw-20:y=h-th-20"
            f":borderw=2:bordercolor=black{font_arg}"
        ),
        "-c:v", "libx264",
        "-c:a", "aac",
        "-shortest",
        "-pix_fmt", "yuv420p",
        output_path,
    ]

    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(f"FFmpeg failed:\n{result.stderr}")

    return output_path


def _find_font() -> Optional[str]:
    """Return path to first .ttf font found in assets/fonts, or None."""
    if not os.path.isdir(FONTS_DIR):
        return None
    for f in os.listdir(FONTS_DIR):
        if f.lower().endswith(".ttf"):
            return os.path.join(FONTS_DIR, f)
    return None
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
cd tiktok-manager
python -m pytest tests/test_video_builder.py -v
```

Expected: `3 passed`

- [ ] **Step 5: Download a background image for testing**

Go to https://pixabay.com/images/search/space/ and download one free image to `tiktok-manager/assets/backgrounds/bg1.jpg`

Or via curl (space background, license-free):
```bash
curl -L "https://images.pexels.com/photos/998641/pexels-photo-998641.jpeg?w=1080" \
  -o tiktok-manager/assets/backgrounds/bg1.jpg
```

- [ ] **Step 6: Commit**

```bash
git add tiktok-manager/modules/video_builder.py tiktok-manager/tests/test_video_builder.py
git commit -m "feat: add FFmpeg video builder module"
```

---

## Task 6: TikTok Auth

**Files:**
- Create: `tiktok-manager/modules/tiktok_auth.py`
- Create: `tiktok-manager/tests/test_tiktok_auth.py`

- [ ] **Step 1: Write the failing test**

Create `tiktok-manager/tests/test_tiktok_auth.py`:

```python
import pytest
from unittest.mock import MagicMock, patch
from datetime import datetime, timedelta, timezone


def test_is_token_expired_returns_true_when_past(mocker):
    from modules.tiktok_auth import is_token_expired
    past = (datetime.now(timezone.utc) - timedelta(hours=1)).isoformat()
    assert is_token_expired(past) is True


def test_is_token_expired_returns_false_when_future(mocker):
    from modules.tiktok_auth import is_token_expired
    future = (datetime.now(timezone.utc) + timedelta(hours=1)).isoformat()
    assert is_token_expired(future) is False


def test_is_token_expired_returns_true_when_none():
    from modules.tiktok_auth import is_token_expired
    assert is_token_expired(None) is True


def test_refresh_access_token_updates_state(mocker):
    mock_post = mocker.patch("modules.tiktok_auth.requests.post")
    mock_post.return_value.json.return_value = {
        "data": {
            "access_token": "new_access_token",
            "refresh_token": "new_refresh_token",
            "expires_in": 86400,
        }
    }
    mock_post.return_value.raise_for_status = MagicMock()

    from modules.tiktok_auth import refresh_access_token
    state = {
        "tiktok_refresh_token": "old_refresh",
        "tiktok_access_token": None,
        "token_expires_at": None,
    }
    updated = refresh_access_token(state, client_id="cid", client_secret="csec")

    assert updated["tiktok_access_token"] == "new_access_token"
    assert updated["tiktok_refresh_token"] == "new_refresh_token"
    assert updated["token_expires_at"] is not None
```

- [ ] **Step 2: Run test to verify it fails**

```bash
cd tiktok-manager
python -m pytest tests/test_tiktok_auth.py -v
```

Expected: `ModuleNotFoundError: No module named 'modules.tiktok_auth'`

- [ ] **Step 3: Implement `tiktok-manager/modules/tiktok_auth.py`**

```python
import os
from datetime import datetime, timedelta, timezone
from typing import Optional
import requests
from dotenv import load_dotenv

load_dotenv()

TIKTOK_TOKEN_URL = "https://open.tiktokapis.com/v2/oauth/token/"


def is_token_expired(token_expires_at: Optional[str]) -> bool:
    """Return True if token is expired or not set."""
    if not token_expires_at:
        return True
    try:
        expiry = datetime.fromisoformat(token_expires_at)
        if expiry.tzinfo is None:
            expiry = expiry.replace(tzinfo=timezone.utc)
        return datetime.now(timezone.utc) >= expiry
    except (ValueError, TypeError):
        return True


def refresh_access_token(
    state: dict,
    client_id: Optional[str] = None,
    client_secret: Optional[str] = None,
) -> dict:
    """
    Use refresh_token to get a new access_token.
    Updates and returns the state dict with new token values.
    """
    client_id = client_id or os.getenv("TIKTOK_CLIENT_ID")
    client_secret = client_secret or os.getenv("TIKTOK_CLIENT_SECRET")

    response = requests.post(
        TIKTOK_TOKEN_URL,
        data={
            "client_key": client_id,
            "client_secret": client_secret,
            "grant_type": "refresh_token",
            "refresh_token": state["tiktok_refresh_token"],
        },
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    response.raise_for_status()
    data = response.json()["data"]

    expires_at = (
        datetime.now(timezone.utc) + timedelta(seconds=data["expires_in"])
    ).isoformat()

    return {
        **state,
        "tiktok_access_token": data["access_token"],
        "tiktok_refresh_token": data["refresh_token"],
        "token_expires_at": expires_at,
    }


def get_valid_token(state: dict) -> tuple[str, dict]:
    """
    Return (access_token, updated_state).
    Refreshes token automatically if expired.
    """
    if is_token_expired(state.get("token_expires_at")):
        state = refresh_access_token(state)
    return state["tiktok_access_token"], state
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
cd tiktok-manager
python -m pytest tests/test_tiktok_auth.py -v
```

Expected: `4 passed`

- [ ] **Step 5: Commit**

```bash
git add tiktok-manager/modules/tiktok_auth.py tiktok-manager/tests/test_tiktok_auth.py
git commit -m "feat: add TikTok OAuth token manager"
```

---

## Task 7: TikTok Uploader

**Files:**
- Create: `tiktok-manager/modules/tiktok_uploader.py`
- Create: `tiktok-manager/tests/test_tiktok_uploader.py`

- [ ] **Step 1: Write the failing test**

Create `tiktok-manager/tests/test_tiktok_uploader.py`:

```python
import pytest
from unittest.mock import MagicMock, patch, mock_open


def test_upload_video_returns_video_id(tmp_path, mocker):
    video_file = tmp_path / "video.mp4"
    video_file.write_bytes(b"0" * 1000)

    mock_post = mocker.patch("modules.tiktok_uploader.requests.post")
    # init upload response
    mock_post.return_value.json.return_value = {
        "data": {
            "publish_id": "pub_123",
            "upload_url": "https://upload.tiktok.com/fake",
        }
    }
    mock_post.return_value.raise_for_status = MagicMock()

    mock_put = mocker.patch("modules.tiktok_uploader.requests.put")
    mock_put.return_value.raise_for_status = MagicMock()

    mock_get = mocker.patch("modules.tiktok_uploader.requests.get")
    mock_get.return_value.json.return_value = {
        "data": {"status": "PUBLISH_COMPLETE", "video_id": "7abc123"}
    }
    mock_get.return_value.raise_for_status = MagicMock()

    from modules.tiktok_uploader import upload_video
    video_id = upload_video(
        video_path=str(video_file),
        caption="Test #datoscuriosos",
        access_token="fake_token",
    )
    assert video_id == "7abc123"


def test_upload_video_raises_on_quota_exceeded(tmp_path, mocker):
    video_file = tmp_path / "video.mp4"
    video_file.write_bytes(b"0" * 100)

    mock_post = mocker.patch("modules.tiktok_uploader.requests.post")
    mock_response = MagicMock()
    mock_response.json.return_value = {"error": {"code": "quota_exceeded"}}
    mock_response.raise_for_status.side_effect = Exception("429")
    mock_post.return_value = mock_response

    from modules.tiktok_uploader import upload_video
    with pytest.raises(Exception):
        upload_video(str(video_file), "caption", "token")
```

- [ ] **Step 2: Run test to verify it fails**

```bash
cd tiktok-manager
python -m pytest tests/test_tiktok_uploader.py -v
```

Expected: `ModuleNotFoundError: No module named 'modules.tiktok_uploader'`

- [ ] **Step 3: Implement `tiktok-manager/modules/tiktok_uploader.py`**

```python
import os
import time
import requests

TIKTOK_API_BASE = "https://open.tiktokapis.com/v2"
CHUNK_SIZE = 10 * 1024 * 1024  # 10 MB


def upload_video(video_path: str, caption: str, access_token: str) -> str:
    """
    Upload video to TikTok using Content Posting API v2 (FILE_UPLOAD flow).
    Returns the video_id string on success.
    Raises RuntimeError on quota exceeded or publish failure.
    """
    file_size = os.path.getsize(video_path)
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json; charset=UTF-8",
    }

    # Step 1: Initialize upload
    init_resp = requests.post(
        f"{TIKTOK_API_BASE}/post/publish/video/init/",
        headers=headers,
        json={
            "post_info": {
                "title": caption[:150],
                "privacy_level": "PUBLIC_TO_EVERYONE",
                "disable_duet": False,
                "disable_comment": False,
                "disable_stitch": False,
            },
            "source_info": {
                "source": "FILE_UPLOAD",
                "video_size": file_size,
                "chunk_size": min(CHUNK_SIZE, file_size),
                "total_chunk_count": -(-file_size // min(CHUNK_SIZE, file_size)),
            },
        },
    )
    init_resp.raise_for_status()
    init_data = init_resp.json()["data"]
    publish_id = init_data["publish_id"]
    upload_url = init_data["upload_url"]

    # Step 2: Upload file in chunks
    with open(video_path, "rb") as f:
        chunk_index = 0
        offset = 0
        while True:
            chunk = f.read(CHUNK_SIZE)
            if not chunk:
                break
            end = offset + len(chunk) - 1
            put_resp = requests.put(
                upload_url,
                headers={
                    "Content-Range": f"bytes {offset}-{end}/{file_size}",
                    "Content-Length": str(len(chunk)),
                    "Content-Type": "video/mp4",
                },
                data=chunk,
            )
            put_resp.raise_for_status()
            offset += len(chunk)
            chunk_index += 1

    # Step 3: Poll for publish status
    for _ in range(20):
        status_resp = requests.get(
            f"{TIKTOK_API_BASE}/post/publish/status/fetch/",
            headers=headers,
            params={"publish_id": publish_id},
        )
        status_resp.raise_for_status()
        status_data = status_resp.json()["data"]

        if status_data["status"] == "PUBLISH_COMPLETE":
            return status_data["video_id"]
        if status_data["status"] in ("FAILED", "SPAM_RISK_TOO_MANY_POSTS"):
            raise RuntimeError(f"TikTok publish failed: {status_data['status']}")
        time.sleep(3)

    raise RuntimeError("TikTok publish timed out after polling")
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
cd tiktok-manager
python -m pytest tests/test_tiktok_uploader.py -v
```

Expected: `2 passed`

- [ ] **Step 5: Commit**

```bash
git add tiktok-manager/modules/tiktok_uploader.py tiktok-manager/tests/test_tiktok_uploader.py
git commit -m "feat: add TikTok Content Posting API uploader"
```

---

## Task 8: Pipeline Orchestrator

**Files:**
- Create: `tiktok-manager/pipeline.py`
- Create: `tiktok-manager/tests/test_pipeline.py`

- [ ] **Step 1: Write the failing test**

Create `tiktok-manager/tests/test_pipeline.py`:

```python
import pytest
from unittest.mock import MagicMock, patch
from datetime import datetime, timezone


MOCK_SCRIPT = {
    "topic": "pulpos",
    "hook": "¿Sabías que los pulpos tienen 3 corazones?",
    "body": "Los pulpos son fascinantes...",
    "cta": "Síguenos 🔍",
    "caption": "Los pulpos son increíbles #datoscuriosos #eldatocurioso",
}


def test_run_pipeline_calls_all_modules(tmp_path, mocker):
    mocker.patch("pipeline.STATE_PATH", str(tmp_path / "state.json"))
    mocker.patch("pipeline.OUTPUT_DIR", str(tmp_path / "outputs"))
    mocker.patch("pipeline.BACKGROUNDS_DIR", str(tmp_path / "bg"))

    mock_generate_script = mocker.patch("pipeline.generate_script", return_value=MOCK_SCRIPT)
    mock_generate_audio = mocker.patch("pipeline.generate_audio_from_script", return_value=str(tmp_path / "audio.mp3"))
    mock_build_video = mocker.patch("pipeline.build_video", return_value=str(tmp_path / "video.mp4"))
    mock_get_valid_token = mocker.patch("pipeline.get_valid_token", return_value=("fake_token", {}))
    mock_upload = mocker.patch("pipeline.upload_video", return_value="7abc")
    mocker.patch("pipeline.load_state", return_value={
        "videos_published": [],
        "last_10_topics": [],
        "comments_replied": [],
        "daily_count": 0,
        "last_upload_ts": None,
        "tiktok_access_token": "tok",
        "tiktok_refresh_token": "ref",
        "token_expires_at": None,
        "last_video_id": None,
    })
    mock_save = mocker.patch("pipeline.save_state")

    from pipeline import run_pipeline
    result = run_pipeline()

    assert result["video_id"] == "7abc"
    assert result["topic"] == "pulpos"
    assert mock_generate_script.called
    assert mock_generate_audio.called
    assert mock_build_video.called
    assert mock_upload.called
    assert mock_save.called


def test_run_pipeline_updates_state_after_upload(tmp_path, mocker):
    mocker.patch("pipeline.STATE_PATH", str(tmp_path / "state.json"))
    mocker.patch("pipeline.OUTPUT_DIR", str(tmp_path / "outputs"))
    mocker.patch("pipeline.BACKGROUNDS_DIR", str(tmp_path / "bg"))
    mocker.patch("pipeline.generate_script", return_value=MOCK_SCRIPT)
    mocker.patch("pipeline.generate_audio_from_script", return_value="/tmp/a.mp3")
    mocker.patch("pipeline.build_video", return_value="/tmp/v.mp4")
    mocker.patch("pipeline.get_valid_token", return_value=("tok", {"tiktok_access_token": "tok"}))
    mocker.patch("pipeline.upload_video", return_value="7newvideo")
    initial_state = {
        "videos_published": ["7old"],
        "last_10_topics": ["ballenas"],
        "comments_replied": [],
        "daily_count": 1,
        "last_upload_ts": None,
        "tiktok_access_token": "tok",
        "tiktok_refresh_token": "ref",
        "token_expires_at": None,
        "last_video_id": "7old",
    }
    mocker.patch("pipeline.load_state", return_value=initial_state)
    captured_state = {}

    def capture_save(state, *args, **kwargs):
        captured_state.update(state)

    mocker.patch("pipeline.save_state", side_effect=capture_save)

    from pipeline import run_pipeline
    run_pipeline()

    assert "7newvideo" in captured_state["videos_published"]
    assert "pulpos" in captured_state["last_10_topics"]
    assert captured_state["daily_count"] == 2
    assert captured_state["last_video_id"] == "7newvideo"
```

- [ ] **Step 2: Run test to verify it fails**

```bash
cd tiktok-manager
python -m pytest tests/test_pipeline.py -v
```

Expected: `ModuleNotFoundError: No module named 'pipeline'`

- [ ] **Step 3: Implement `tiktok-manager/pipeline.py`**

```python
import os
import logging
from datetime import datetime, timezone

from dotenv import load_dotenv

from modules.state import load_state, save_state, STATE_PATH
from modules.script_generator import generate_script
from modules.tts import generate_audio_from_script
from modules.video_builder import build_video, BACKGROUNDS_DIR
from modules.tiktok_auth import get_valid_token
from modules.tiktok_uploader import upload_video

load_dotenv()

OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "outputs")
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler(os.path.join(OUTPUT_DIR, "errors.log")),
        logging.StreamHandler(),
    ],
)
logger = logging.getLogger(__name__)


def run_pipeline() -> dict:
    """
    Run full video generation and upload pipeline.
    Returns dict with video_id and topic on success.
    Raises on unrecoverable errors.
    """
    state = load_state()

    # 1. Generate script (avoid repeating topics)
    logger.info("Generating script...")
    script = generate_script(last_topics=state.get("last_10_topics", []))
    logger.info(f"Script topic: {script['topic']}")

    # 2. Generate TTS audio
    ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    audio_path = os.path.join(OUTPUT_DIR, f"audio_{ts}.mp3")
    logger.info("Generating TTS audio...")
    generate_audio_from_script(script, audio_path)

    # 3. Build video
    video_path = os.path.join(OUTPUT_DIR, "videos", f"video_{ts}.mp4")
    logger.info("Building video with FFmpeg...")
    build_video(script, audio_path, video_path)

    # 4. Get valid TikTok token (refresh if needed)
    access_token, state = get_valid_token(state)

    # 5. Upload to TikTok
    logger.info("Uploading to TikTok...")
    video_id = upload_video(video_path, script["caption"], access_token)
    logger.info(f"Uploaded! Video ID: {video_id}")

    # 6. Update state
    topics = state.get("last_10_topics", [])
    topics.append(script["topic"])
    state.update({
        "last_video_id": video_id,
        "videos_published": state.get("videos_published", []) + [video_id],
        "last_10_topics": topics[-10:],
        "daily_count": state.get("daily_count", 0) + 1,
        "last_upload_ts": datetime.now(timezone.utc).isoformat(),
    })
    save_state(state)

    return {"video_id": video_id, "topic": script["topic"]}


if __name__ == "__main__":
    result = run_pipeline()
    print(f"Done! Video ID: {result['video_id']} | Topic: {result['topic']}")
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
cd tiktok-manager
python -m pytest tests/test_pipeline.py -v
```

Expected: `2 passed`

- [ ] **Step 5: Run full test suite**

```bash
cd tiktok-manager
python -m pytest tests/ -v
```

Expected: all tests pass.

- [ ] **Step 6: Commit**

```bash
git add tiktok-manager/pipeline.py tiktok-manager/tests/test_pipeline.py
git commit -m "feat: add pipeline orchestrator"
```

---

## Task 9: HTTP Server (n8n Trigger + OAuth)

**Files:**
- Create: `tiktok-manager/server.py`

- [ ] **Step 1: Implement `tiktok-manager/server.py`**

```python
"""
Flask server with two endpoints:
  POST /run-pipeline   — called by n8n cron to trigger video generation
  GET  /callback       — TikTok OAuth redirect (one-time setup)
  GET  /health         — health check
"""
import os
import threading
import logging
import requests

from flask import Flask, request, jsonify
from dotenv import load_dotenv

from modules.state import load_state, save_state
import pipeline as pipe

load_dotenv()

app = Flask(__name__)
logger = logging.getLogger(__name__)

TIKTOK_TOKEN_URL = "https://open.tiktokapis.com/v2/oauth/token/"
_pipeline_lock = threading.Lock()


@app.get("/health")
def health():
    return jsonify({"status": "ok"})


@app.post("/run-pipeline")
def run_pipeline_endpoint():
    """Trigger the video pipeline. Returns immediately if already running."""
    if not _pipeline_lock.acquire(blocking=False):
        return jsonify({"status": "already_running"}), 409

    def run_and_release():
        try:
            result = pipe.run_pipeline()
            logger.info(f"Pipeline complete: {result}")
        except Exception as e:
            logger.error(f"Pipeline failed: {e}")
        finally:
            _pipeline_lock.release()

    thread = threading.Thread(target=run_and_release, daemon=True)
    thread.start()
    return jsonify({"status": "started"})


@app.get("/callback")
def oauth_callback():
    """Handle TikTok OAuth redirect. Stores tokens in state.json."""
    code = request.args.get("code")
    if not code:
        return "Missing code parameter", 400

    client_id = os.getenv("TIKTOK_CLIENT_ID")
    client_secret = os.getenv("TIKTOK_CLIENT_SECRET")
    redirect_uri = os.getenv("TIKTOK_REDIRECT_URI", "http://localhost:8765/callback")

    resp = requests.post(
        TIKTOK_TOKEN_URL,
        data={
            "client_key": client_id,
            "client_secret": client_secret,
            "code": code,
            "grant_type": "authorization_code",
            "redirect_uri": redirect_uri,
        },
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    resp.raise_for_status()
    data = resp.json()["data"]

    from datetime import datetime, timedelta, timezone
    state = load_state()
    state.update({
        "tiktok_access_token": data["access_token"],
        "tiktok_refresh_token": data["refresh_token"],
        "token_expires_at": (
            datetime.now(timezone.utc) + timedelta(seconds=data["expires_in"])
        ).isoformat(),
    })
    save_state(state)
    return "<h1>✅ TikTok connected! Tokens saved. You can close this tab.</h1>"


if __name__ == "__main__":
    port = int(os.getenv("PIPELINE_WEBHOOK_PORT", 8765))
    print(f"Starting pipeline server on port {port}")
    print(f"OAuth URL: http://localhost:{port}/callback")
    app.run(host="0.0.0.0", port=port)
```

- [ ] **Step 2: Verify server starts without errors**

```bash
cd tiktok-manager
python server.py &
curl http://localhost:8765/health
# Expected: {"status": "ok"}
kill %1
```

- [ ] **Step 3: Commit**

```bash
git add tiktok-manager/server.py
git commit -m "feat: add Flask webhook server for n8n trigger and TikTok OAuth"
```

---

## Task 10: TikTok OAuth — One-Time Setup

This task is **manual** and must be done before the first upload.

- [ ] **Step 1: Rotate your TikTok Client Secret**

Go to https://developers.tiktok.com → your app → regenerate Client Secret. Update `tiktok-manager/.env`.

- [ ] **Step 2: Set redirect URI in TikTok Developer Portal**

In your TikTok app settings, add `http://localhost:8765/callback` as an allowed redirect URI. Also ensure scopes `video.upload` and `video.publish` are enabled.

- [ ] **Step 3: Start the server**

```bash
cd tiktok-manager
python server.py
```

- [ ] **Step 4: Open the TikTok authorization URL in your browser**

```
https://www.tiktok.com/v2/auth/authorize/?client_key=aw38x3be74y38fj6&scope=video.upload,video.publish&response_type=code&redirect_uri=http://localhost:8765/callback&state=random123
```

Replace `aw38x3be74y38fj6` with your Client ID if you created a new one.

- [ ] **Step 5: Log in with @eldatocurioso account and authorize**

After authorizing, TikTok redirects to `http://localhost:8765/callback?code=...` and the server saves tokens to `outputs/state.json` automatically. You should see `✅ TikTok connected!`

- [ ] **Step 6: Verify state.json has tokens**

```bash
cat tiktok-manager/outputs/state.json
# Must show: "tiktok_access_token": "..." and "tiktok_refresh_token": "..."
```

---

## Task 11: First Manual Video Run

- [ ] **Step 1: Run the pipeline manually**

```bash
cd tiktok-manager
python pipeline.py
```

Expected output:
```
2026-04-09 ... [INFO] Generating script...
2026-04-09 ... [INFO] Script topic: [some topic]
2026-04-09 ... [INFO] Generating TTS audio...
2026-04-09 ... [INFO] Building video with FFmpeg...
2026-04-09 ... [INFO] Uploading to TikTok...
2026-04-09 ... [INFO] Uploaded! Video ID: 7xxx...
Done! Video ID: 7xxx... | Topic: [topic]
```

- [ ] **Step 2: Check TikTok account**

Log in to https://www.tiktok.com/@eldatocurioso and verify the video was posted.

- [ ] **Step 3: Commit any fixes found during manual run**

```bash
git add -p  # stage only relevant changes
git commit -m "fix: adjust pipeline after first manual run"
```

---

## Task 12: n8n Workflows

**Files:**
- Create: `tiktok-manager/n8n-workflows/scheduler.json`
- Create: `tiktok-manager/n8n-workflows/comment-responder.json`
- Create: `tiktok-manager/n8n-workflows/analytics.json`

- [ ] **Step 1: Create `tiktok-manager/n8n-workflows/scheduler.json`**

```json
{
  "name": "TikTok Pipeline Scheduler",
  "nodes": [
    {
      "parameters": {
        "rule": { "interval": [{ "field": "hours", "hoursInterval": 4 }] }
      },
      "name": "Every 4 Hours",
      "type": "n8n-nodes-base.scheduleTrigger",
      "position": [240, 300]
    },
    {
      "parameters": {
        "url": "http://host.docker.internal:8765/run-pipeline",
        "method": "POST",
        "options": { "timeout": 10000 }
      },
      "name": "Trigger Pipeline",
      "type": "n8n-nodes-base.httpRequest",
      "position": [460, 300]
    },
    {
      "parameters": {
        "conditions": {
          "string": [{ "value1": "={{ $json.status }}", "operation": "notEqual", "value2": "started" }]
        }
      },
      "name": "Check Status",
      "type": "n8n-nodes-base.if",
      "position": [680, 300]
    },
    {
      "parameters": {
        "filePath": "={{ $env.PIPELINE_LOG_PATH || '/data/outputs/errors.log' }}",
        "dataPropertyName": "data",
        "options": {}
      },
      "name": "Log Error",
      "type": "n8n-nodes-base.writeFile",
      "position": [900, 400]
    }
  ],
  "connections": {
    "Every 4 Hours": { "main": [[{ "node": "Trigger Pipeline", "type": "main", "index": 0 }]] },
    "Trigger Pipeline": { "main": [[{ "node": "Check Status", "type": "main", "index": 0 }]] },
    "Check Status": { "main": [[], [{ "node": "Log Error", "type": "main", "index": 0 }]] }
  }
}
```

- [ ] **Step 2: Create `tiktok-manager/n8n-workflows/comment-responder.json`**

```json
{
  "name": "TikTok Comment Auto-Responder",
  "nodes": [
    {
      "parameters": {
        "rule": { "interval": [{ "field": "minutes", "minutesInterval": 30 }] }
      },
      "name": "Every 30 Min",
      "type": "n8n-nodes-base.scheduleTrigger",
      "position": [240, 300]
    },
    {
      "parameters": {
        "url": "https://open.tiktokapis.com/v2/video/list/",
        "method": "GET",
        "sendHeaders": true,
        "headerParameters": {
          "parameters": [{ "name": "Authorization", "value": "Bearer {{ $env.TIKTOK_ACCESS_TOKEN }}" }]
        },
        "sendQuery": true,
        "queryParameters": {
          "parameters": [{ "name": "fields", "value": "id,title" }]
        }
      },
      "name": "Get Video List",
      "type": "n8n-nodes-base.httpRequest",
      "position": [460, 300]
    },
    {
      "parameters": {
        "url": "https://open.tiktokapis.com/v2/video/comment/list/",
        "method": "GET",
        "sendHeaders": true,
        "headerParameters": {
          "parameters": [{ "name": "Authorization", "value": "Bearer {{ $env.TIKTOK_ACCESS_TOKEN }}" }]
        },
        "sendQuery": true,
        "queryParameters": {
          "parameters": [
            { "name": "video_id", "value": "={{ $json.id }}" },
            { "name": "fields", "value": "id,text,username" }
          ]
        }
      },
      "name": "Get Comments",
      "type": "n8n-nodes-base.httpRequest",
      "position": [680, 300]
    },
    {
      "parameters": {
        "model": "claude-haiku-4-5-20251001",
        "messages": {
          "values": [{
            "role": "user",
            "content": "Eres el community manager de @eldatocurioso en TikTok. Responde este comentario de forma amigable, curiosa y en español en máximo 150 caracteres. Comentario: {{ $json.text }}"
          }]
        },
        "options": { "maxTokens": 100 }
      },
      "name": "Generate Reply",
      "type": "@n8n/n8n-nodes-langchain.lmChatAnthropic",
      "position": [900, 300]
    },
    {
      "parameters": {
        "url": "https://open.tiktokapis.com/v2/video/comment/reply/",
        "method": "POST",
        "sendHeaders": true,
        "headerParameters": {
          "parameters": [
            { "name": "Authorization", "value": "Bearer {{ $env.TIKTOK_ACCESS_TOKEN }}" },
            { "name": "Content-Type", "value": "application/json" }
          ]
        },
        "sendBody": true,
        "bodyParameters": {
          "parameters": [
            { "name": "video_id", "value": "={{ $('Get Comments').item.json.video_id }}" },
            { "name": "text", "value": "={{ $json.content[0].text.substring(0,150) }}" },
            { "name": "parent_comment_id", "value": "={{ $('Get Comments').item.json.id }}" }
          ]
        }
      },
      "name": "Post Reply",
      "type": "n8n-nodes-base.httpRequest",
      "position": [1120, 300]
    }
  ],
  "connections": {
    "Every 30 Min": { "main": [[{ "node": "Get Video List", "type": "main", "index": 0 }]] },
    "Get Video List": { "main": [[{ "node": "Get Comments", "type": "main", "index": 0 }]] },
    "Get Comments": { "main": [[{ "node": "Generate Reply", "type": "main", "index": 0 }]] },
    "Generate Reply": { "main": [[{ "node": "Post Reply", "type": "main", "index": 0 }]] }
  }
}
```

- [ ] **Step 3: Create `tiktok-manager/n8n-workflows/analytics.json`**

```json
{
  "name": "TikTok Analytics Dashboard",
  "nodes": [
    {
      "parameters": {
        "rule": { "interval": [{ "field": "hours", "hoursInterval": 6 }] }
      },
      "name": "Every 6 Hours",
      "type": "n8n-nodes-base.scheduleTrigger",
      "position": [240, 300]
    },
    {
      "parameters": {
        "url": "https://open.tiktokapis.com/v2/video/list/",
        "method": "GET",
        "sendHeaders": true,
        "headerParameters": {
          "parameters": [{ "name": "Authorization", "value": "Bearer {{ $env.TIKTOK_ACCESS_TOKEN }}" }]
        },
        "sendQuery": true,
        "queryParameters": {
          "parameters": [{ "name": "fields", "value": "id,title,create_time,statistics" }]
        }
      },
      "name": "Get Video Stats",
      "type": "n8n-nodes-base.httpRequest",
      "position": [460, 300]
    },
    {
      "parameters": {
        "jsCode": "const videos = $input.all().map(item => item.json);\nconst scored = videos.map(v => {\n  const s = v.statistics || {};\n  const views = s.play_count || 1;\n  const engagement = ((s.like_count||0)+(s.comment_count||0)+(s.share_count||0)) / views;\n  const completion = (s.average_time_watched || 0) / (s.duration || 60);\n  const score = Math.min(100, Math.round(\n    completion * 40 + engagement * 3000 + Math.min(s.share_count||0, 10) * 2\n  ));\n  return { ...v, quality_score: score, engagement_rate: (engagement*100).toFixed(2) };\n});\nconst html = `<!DOCTYPE html><html><head><meta charset='utf-8'><title>@eldatocurioso Analytics</title><script src='https://cdn.jsdelivr.net/npm/chart.js'></script><style>body{font-family:sans-serif;background:#0f0f0f;color:#fff;padding:20px}h1{color:#fe2c55}.card{background:#1a1a1a;border-radius:12px;padding:20px;margin:16px 0}.score{font-size:2em;font-weight:bold;color:#fe2c55}</style></head><body><h1>📊 @eldatocurioso — Analytics Dashboard</h1><p>Updated: ${new Date().toLocaleString('es-DO')}</p>${scored.map(v=>`<div class='card'><h3>${v.title||v.id}</h3><p>Quality Score: <span class='score'>${v.quality_score}/100</span></p><p>Views: ${(v.statistics?.play_count||0).toLocaleString()} | Likes: ${(v.statistics?.like_count||0).toLocaleString()} | Shares: ${(v.statistics?.share_count||0).toLocaleString()}</p><p>Engagement: ${v.engagement_rate}%</p></div>`).join('')}<canvas id='chart' width='800' height='300'></canvas><script>new Chart(document.getElementById('chart'),{type:'bar',data:{labels:${JSON.stringify(scored.map(v=>v.title?.substring(0,20)||v.id))},datasets:[{label:'Quality Score',data:${JSON.stringify(scored.map(v=>v.quality_score))},backgroundColor:'#fe2c55'}]},options:{scales:{y:{max:100}}}});</script></body></html>`;\nreturn [{ json: { html, video_count: scored.length, top_video: scored.sort((a,b)=>b.quality_score-a.quality_score)[0]?.title } }];"
      },
      "name": "Compute Scores & Build HTML",
      "type": "n8n-nodes-base.code",
      "position": [680, 300]
    },
    {
      "parameters": {
        "operation": "write",
        "fileName": "outputs/dashboard.html",
        "dataPropertyName": "html"
      },
      "name": "Save Dashboard",
      "type": "n8n-nodes-base.readWriteFile",
      "position": [900, 300]
    }
  ],
  "connections": {
    "Every 6 Hours": { "main": [[{ "node": "Get Video Stats", "type": "main", "index": 0 }]] },
    "Get Video Stats": { "main": [[{ "node": "Compute Scores & Build HTML", "type": "main", "index": 0 }]] },
    "Compute Scores & Build HTML": { "main": [[{ "node": "Save Dashboard", "type": "main", "index": 0 }]] }
  }
}
```

- [ ] **Step 4: Import workflows into n8n**

1. Open n8n at http://localhost:5678
2. Click **Workflows → Import from File**
3. Import each of the 3 JSON files from `n8n-workflows/`
4. In each workflow, set the `TIKTOK_ACCESS_TOKEN` environment variable in n8n settings (Settings → Variables → Add Variable)
5. Activate all 3 workflows

- [ ] **Step 5: Commit workflows**

```bash
git add tiktok-manager/n8n-workflows/
git commit -m "feat: add n8n workflows for scheduler, comment responder, and analytics"
```

---

## Task 13: Final Integration & PR

- [ ] **Step 1: Run complete test suite**

```bash
cd tiktok-manager
python -m pytest tests/ -v --tb=short
```

Expected: all tests pass.

- [ ] **Step 2: Verify server + pipeline work end-to-end**

```bash
# Terminal 1
cd tiktok-manager && python server.py

# Terminal 2
curl -X POST http://localhost:8765/run-pipeline
# Expected: {"status": "started"}

# Check logs
tail -f tiktok-manager/outputs/errors.log
```

- [ ] **Step 3: Commit any remaining files**

```bash
git add tiktok-manager/
git commit -m "feat: complete TikTok social media manager pipeline"
```

- [ ] **Step 4: Push and create PR**

```bash
git push origin claude/sad-elion
gh pr create \
  --title "feat: TikTok social media manager — @eldatocurioso" \
  --body "Automated TikTok pipeline: Claude generates curiosity scripts, FFmpeg renders 9:16 videos, gTTS narrates, TikTok API v2 uploads. n8n handles scheduling, comment auto-replies, and analytics dashboard."
```
