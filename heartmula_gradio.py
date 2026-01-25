"""HeartMuLa Music Generator - Gradio Edition
Professional web UI for HeartMuLa music generation with comprehensive presets.

Requirements:
    pip install gradio

File Structure (all paths relative to root where this script is located):
    - Settings: presets/setsave/mula_gradio.json
    - Presets: presets/setsave/mulapresets.json
    - Output: output/
    - Models: ckpt/
    - Script: examples/run_music_generation.py

Location: Place this file in root directory (same level as ckpt/, output/, examples/)
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from dataclasses import dataclass, asdict
from datetime import datetime
from pathlib import Path
import re
from typing import Optional

import gradio as gr


# ============================================================================
# Configuration & Utilities
# ============================================================================

def root_dir() -> Path:
    """Get root directory (script is in root)."""
    return Path(__file__).resolve().parent


def settings_path() -> Path:
    """Path to settings JSON."""
    return root_dir() / "presets" / "setsave" / "mula_gradio.json"


def presets_path() -> Path:
    """Path to presets JSON."""
    return root_dir() / "presets" / "setsave" / "mulapresets.json"


def ensure_dirs() -> None:
    """Create required directories."""
    root = root_dir()
    (root / "ckpt").mkdir(parents=True, exist_ok=True)
    (root / "output").mkdir(parents=True, exist_ok=True)
    (root / "presets" / "setsave").mkdir(parents=True, exist_ok=True)
    (root / "examples").mkdir(parents=True, exist_ok=True)


def slugify(text: str, max_len: int = 42) -> str:
    """Convert text to filesystem-safe slug."""
    s = (text or '').strip().lower()
    s = s.replace('–', '-').replace('—', '-')
    s = re.sub(r'[^a-z0-9]+', '_', s)
    s = re.sub(r'_+', '_', s).strip('_')
    if max_len and len(s) > max_len:
        s = s[:max_len].rstrip('_')
    return s


def format_tags_for_file(tags: str) -> str:
    """Format tags as comma-separated with no spaces."""
    if not tags or not tags.strip():
        return ""
    
    # Remove spaces after commas and convert to lowercase
    tags = tags.strip().lower()
    tags = ','.join([t.strip() for t in tags.split(',')])
    
    return tags


# ============================================================================
# Data Classes
# ============================================================================

@dataclass
class MulaSettings:
    """User settings for HeartMuLa."""
    model_path: str = "ckpt"
    version: str = "3B"
    max_audio_length_sec: int = 240  # 4 minutes
    topk: int = 50
    temperature: float = 1.0
    cfg_scale: float = 1.5
    output_dir: str = "output"

    @staticmethod
    def load(path: Path) -> "MulaSettings":
        """Load settings from JSON file."""
        if not path.exists():
            return MulaSettings()
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            
            # Migrate old model paths to new structure
            if "model_path" in data:
                old_path = data["model_path"]
                if "models/HeartMuLa" in old_path or "models/heartmula" in old_path.lower():
                    data["model_path"] = "ckpt"
            
            return MulaSettings(**{k: v for k, v in data.items() if k in MulaSettings.__dataclass_fields__})
        except Exception:
            return MulaSettings()

    def save(self, path: Path) -> None:
        """Save settings to JSON file."""
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(asdict(self), indent=2, ensure_ascii=False), encoding="utf-8")


def default_presets() -> dict:
    """Default preset library."""
    return {
        "version": 1,
        "genres": [
            {
                "name": "EDM",
                "presets": [
                    {"name": "House – Club", "tags": "club house, 128 bpm, four-on-the-floor kick, offbeat open hi-hat, rolling bassline, sidechain compression, bright supersaw, riser, snare build, drop, festival energy, wide stereo"},
                    {"name": "Tech House", "tags": "tech house, 128 bpm, punchy kick and snare, groovy bass, syncopated percussion, shaker loop, minimal vocals, tension build, big drop, club mix"},
                    {"name": "Melodic Techno", "tags": "melodic techno, 126 bpm, driving kick, hypnotic arp, dark atmosphere, long buildup, impact hit, drop, cinematic pads"},
                    {"name": "Big Room", "tags": "big room, 130 bpm, huge kick, snare roll buildup, white noise riser, supersaw lead, massive drop, festival"},
                    {"name": "Drum & Bass – Dancefloor", "tags": "drum and bass, 174 bpm, fast breakbeat, punchy kick and snare, rolling sub bass, reese bass, high energy, tension build, riser, impact hit, big drop, energetic synth stabs, atmospheric pad, DJ friendly, loop-based, minimal vocal chops"},
                    {"name": "Drum & Bass – Neurofunk", "tags": "neurofunk, drum and bass, 172 bpm, tight snare, aggressive reese bass, growl bass, syncopated drums, gritty texture, dark atmosphere, industrial sound design, long buildup, snare roll, heavy drop, bass variation, minimal vocals, club mix, hard hitting"},
                    {"name": "Drum & Bass – Liquid", "tags": "liquid drum and bass, 170 bpm, crisp breakbeat, warm sub bass, airy pads, emotional chords, clean mix, gentle riser, smooth drop, melodic lead, spacious reverb, minimal vocals, DJ friendly intro and outro"},
                    {"name": "Techno – Driving Warehouse", "tags": "techno, 130 bpm, four-on-the-floor kick, rumbling bass, rolling percussion, offbeat hi-hat, hypnotic loop, dark warehouse, minimal vocals, repetitive groove, long buildup, tension, impact hit, drop, DJ friendly"},
                    {"name": "Techno – Peak Time", "tags": "peak time techno, 132 bpm, powerful kick, driving bassline, big synth stab, build-up with snare roll, white noise riser, huge drop, energetic percussion, club mix, loop-based, crowd energy"},
                    {"name": "Techno – Melodic", "tags": "melodic techno, 126 bpm, driving kick, arpeggiated synth, deep bass, cinematic pad, gradual buildup, impact hit, drop, wide stereo, minimal vocal chops, DJ friendly"},
                    {"name": "Hard Techno – Rave", "tags": "hard techno, 150 bpm, hard four-on-the-floor kick, distorted rumble bass, aggressive percussion, rave stabs, intense energy, fast hats, build-up, snare roll, white noise riser, brutal drop, warehouse rave, relentless"},
                    {"name": "Hard Techno – Industrial", "tags": "industrial hard techno, 145 bpm, heavy distorted kick, metallic percussion, dark atmosphere, gritty texture, pounding groove, relentless drive, tension build, impact hit, drop, harsh synth, underground"},
                    {"name": "Hard Techno – Hardgroove", "tags": "hardgroove techno, 145 bpm, hard kick, groovy tom percussion, syncopated loops, fast hats, tribal percussion, hypnotic repetition, long buildup, drop, rave energy, DJ friendly"},
                ]
            },
            {
                "name": "Rock",
                "presets": [
                    {"name": "Rock – Classic", "tags": "classic rock, 120 bpm, live drum kit, steady rock groove, crunchy rhythm guitars, melodic lead guitar, electric bass, verse chorus structure, big chorus, warm analog mix, arena feel"},
                    {"name": "Rock – Hard Rock", "tags": "hard rock, 140 bpm, driving drums, punchy kick and snare, distorted power chords, palm-muted riffs, big chorus, guitar solo, gritty vocals, aggressive energy, modern rock mix, wide guitars"},
                    {"name": "Rock – Metal", "tags": "heavy metal, 160 bpm, double kick, tight snare, fast riffs, palm-muted chugs, aggressive guitar tone, heavy bass, breakdown, solo section, intense vocals, raw power"},
                ]
            },
            {
                "name": "Pop",
                "presets": [
                    {"name": "Pop – Modern", "tags": "modern pop, 118 bpm, clean punchy drums, bright synths, catchy hook, verse chorus structure, big chorus, polished vocal production, radio-ready mix, uplifting mood, wide stereo"},
                    {"name": "Pop – Synthpop", "tags": "synthpop, 112 bpm, retro drum machine, gated snare, warm analog synths, arpeggiator, catchy melody, dreamy chords, smooth vocals, nostalgic 80s vibe, clean mix"},
                    {"name": "Pop – Dance Pop", "tags": "dance pop, 124 bpm, four-on-the-floor kick, offbeat open hat, bright chords, sidechain compression, vocal hook, pre-chorus build, drop-style chorus, club-friendly, glossy mix"},
                ]
            },
            {
                "name": "R&B",
                "presets": [
                    {"name": "R&B – Contemporary", "tags": "contemporary r&b, 92 bpm, smooth drums, deep sub bass, lush chords, soulful vocals, modern vocal layers, relaxed groove, intimate vibe, polished mix"},
                    {"name": "R&B – Neo Soul", "tags": "neo soul, 85 bpm, swung groove, warm electric piano, jazzy chords, live bass feel, crisp snare, intimate vocals, laid-back pocket, organic texture, smooth mix"},
                    {"name": "R&B – Trap Soul", "tags": "trap soul, 70 bpm, trap hats, 808 bass, minimal chords, airy pads, moody vibe, melodic vocals, emotional hook, sparse arrangement, late-night atmosphere"},
                ]
            },
            {
                "name": "Rap",
                "presets": [
                    {"name": "Rap – Boom Bap", "tags": "boom bap rap, 92 bpm, classic hip hop drums, punchy kick, snappy snare, sampled vibe, chopped loop, gritty texture, head-nod groove, rap-focused, raw mix"},
                    {"name": "Rap – Trap", "tags": "trap rap, 140 bpm, rapid hi-hats, 808 bass, hard snare, dark synth melody, aggressive energy, hook section, beat switch, modern mix, rap-focused"},
                    {"name": "Rap – Drill", "tags": "drill rap, 145 bpm, sliding 808, sharp snare, syncopated hi-hats, dark piano or bell melody, tense vibe, aggressive rhythm, rap-forward, hard mix"},
                ]
            },
            {
                "name": "Ballad / Slow",
                "presets": [
                    {"name": "Ballad – Piano", "tags": "piano ballad, 72 bpm, emotional piano chords, soft drums, gentle strings, intimate vocals, big chorus lift, gradual build, heartfelt mood, warm reverb"},
                    {"name": "Ballad – Acoustic", "tags": "acoustic ballad, 78 bpm, acoustic guitar fingerpicking, soft percussion, warm bass, intimate vocal, emotional chorus, natural room sound, organic performance"},
                    {"name": "Ballad – Cinematic", "tags": "cinematic ballad, 68 bpm, orchestral strings, piano, soft drums, emotional swells, dramatic build, big climax, film score feel, lush reverb"},
                ]
            },
            {
                "name": "Instrumental",
                "presets": [
                    {"name": "Instrumental – Ambient", "tags": "ambient instrumental, 70 bpm, evolving pads, soft textures, spacious reverb, slow movement, atmospheric drones, minimal percussion, calming mood, cinematic soundscape, no vocals"},
                    {"name": "Instrumental – Lo-fi", "tags": "lofi instrumental, 82 bpm, dusty drums, vinyl crackle texture, jazzy chords, warm bass, relaxed groove, soft melody, chill mood, loop-based, no vocals"},
                    {"name": "Instrumental – Orchestral", "tags": "orchestral instrumental, 90 bpm, strings brass woodwinds, cinematic percussion, emotional theme, dynamic build, heroic climax, film score style, wide stereo, no vocals"},
                ]
            },
            {
                "name": "Reggae",
                "presets": [
                    {"name": "Reggae – Roots", "tags": "roots reggae, 74 bpm, one drop rhythm, skank guitar on offbeat, warm bassline, live drums, relaxed groove, sunny vibe, soulful vocals, organic mix"},
                    {"name": "Reggae – Dancehall", "tags": "dancehall, 96 bpm, modern drum pattern, heavy bass, syncopated rhythm, energetic vibe, catchy chant hook, club-ready, bright synth accents, punchy mix"},
                    {"name": "Reggae – Dub", "tags": "dub reggae, 72 bpm, deep bass, sparse drums, skank guitar, heavy reverb and delay, echo effects, spacey atmosphere, minimalist groove, instrumental focus"},
                ]
            },
            {"name": "Custom", "presets": []}
        ]
    }


class PresetManager:
    """Manage preset loading/saving."""
    
    def __init__(self, path: Path):
        self.path = path
        self.data: dict = {}
    
    def load(self) -> dict:
        """Load or create preset file."""
        if self.path.exists():
            try:
                self.data = json.loads(self.path.read_text(encoding="utf-8"))
                if isinstance(self.data, dict) and "genres" in self.data:
                    return self.data
            except Exception:
                pass
        self.data = default_presets()
        self.save()
        return self.data
    
    def save(self) -> None:
        """Save presets to file."""
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(json.dumps(self.data, indent=2, ensure_ascii=False), encoding="utf-8")
    
    def get_genre_names(self) -> list[str]:
        """Get list of genre names."""
        return [g["name"] for g in self.data.get("genres", [])]
    
    def get_presets_for_genre(self, genre_name: str) -> list[dict]:
        """Get presets for a specific genre."""
        for genre in self.data.get("genres", []):
            if genre["name"] == genre_name:
                return genre.get("presets", [])
        return []


# ============================================================================
# Generation Logic
# ============================================================================

def validate_installation(model_path: str) -> tuple[bool, str]:
    """Validate HeartMuLa installation."""
    root = root_dir()
    
    # Check model directory
    model_dir = Path(model_path.strip())
    if not model_dir.is_absolute():
        model_dir = root / model_dir
    
    if not model_dir.exists():
        return False, f"Model directory not found: {model_dir}"
    
    # Check required model files
    required = [
        model_dir / "HeartCodec-oss",
        model_dir / "HeartMuLa-oss-3B",
        model_dir / "gen_config.json",
        model_dir / "tokenizer.json",
    ]
    
    missing = [str(p) for p in required if not p.exists()]
    if missing:
        return False, f"Missing model files:\n" + "\n".join(missing)
    
    # Check generation script
    script = root / "examples" / "run_music_generation.py"
    if not script.exists():
        return False, f"Generation script not found: {script}\n\nExpected location: examples/run_music_generation.py"
    
    return True, ""


def generate_music(
    model_path: str,
    version: str,
    tags: str,
    lyrics: str,
    max_length_sec: int,
    topk: int,
    temperature: float,
    cfg_scale: float,
    output_dir: str,
    progress=gr.Progress()
) -> tuple[str, str]:
    """Generate music with HeartMuLa."""
    
    # Validate installation
    ok, error = validate_installation(model_path)
    if not ok:
        return None, f"❌ Installation Error:\n{error}"
    
    progress(0, desc="Preparing generation...")
    
    # Prepare paths
    root = root_dir()
    model_dir = Path(model_path.strip())
    if not model_dir.is_absolute():
        model_dir = root / model_dir
    
    out_dir = Path(output_dir.strip() or "output")
    if not out_dir.is_absolute():
        out_dir = root / out_dir
    out_dir.mkdir(parents=True, exist_ok=True)
    
    # Generate unique output filename
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    counter = 1
    filename = f"heartmula_{timestamp}.mp3"
    output_file = out_dir / filename
    while output_file.exists():
        filename = f"heartmula_{timestamp}_{counter}.mp3"
        output_file = out_dir / filename
        counter += 1
    
    # Create assets directory for CLI usage
    assets_dir = root / "assets"
    assets_dir.mkdir(parents=True, exist_ok=True)
    
    # Format tags as comma-separated with no spaces
    formatted_tags = format_tags_for_file(tags or "")
    
    # Write to assets directory (where run_music_generation.py looks by default)
    (assets_dir / "lyrics.txt").write_text((lyrics or "") + "\n", encoding="utf-8")
    (assets_dir / "tags.txt").write_text(formatted_tags + "\n", encoding="utf-8")
    
    # Build command - use relative paths
    python_exe = sys.executable
    
    # Convert output path to relative
    try:
        relative_output = output_file.relative_to(root)
        output_path_for_cli = f".\\{relative_output}"
    except ValueError:
        # If can't make relative, use the filename in output dir
        output_path_for_cli = f".\\output\\{output_file.name}"
    
    # Use relative paths
    cmd = [
        python_exe,
        r".\examples\run_music_generation.py",
        f"--model_path=.\\ckpt",
        f"--version={version}",
        r"--lyrics=.\assets\lyrics.txt",
        r"--tags=.\assets\tags.txt",
        f"--save_path={output_path_for_cli}",
        f"--max_audio_length_ms={max_length_sec * 1000}",
        f"--topk={topk}",
        f"--temperature={temperature}",
        f"--cfg_scale={cfg_scale}",
    ]
    
    # Format CLI command for display
    cli_command = " ".join(cmd)
    
    progress(0.1, desc="Starting generation process...")
    
    # Run generation
    try:
        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
            cwd=str(root)
        )
        
        output_lines = []
        for line in process.stdout:
            output_lines.append(line.rstrip())
            # Update progress based on output
            if "%" in line:
                try:
                    pct = int(re.search(r'(\d+)%', line).group(1))
                    progress(0.1 + (pct / 100) * 0.8, desc=f"Generating... {pct}%")
                except:
                    pass
        
        process.wait()
        
        if process.returncode == 0:
            progress(1.0, desc="Generation complete!")
            
            if output_file.exists():
                log = "\n".join(output_lines[-20:])  # Last 20 lines
                status_msg = (
                    f"✅ Success!\n\n"
                    f"Saved to: {output_file}\n\n"
                    f"Tags: {tags or '(none)'}\n"
                    f"Written to .\\assets\\tags.txt as: {formatted_tags}\n\n"
                    f"--- Console Output (last 20 lines) ---\n{log}\n\n"
                    f"--- CLI Command ---\n{cli_command}"
                )
                return str(output_file), status_msg
            else:
                status_msg = (
                    f"⚠️ Process completed but output file not found: {output_file}\n\n"
                    f"--- CLI Command ---\n{cli_command}"
                )
                return None, status_msg
        else:
            log = "\n".join(output_lines)
            status_msg = (
                f"❌ Generation failed (exit code {process.returncode})\n\n"
                f"--- Console Output ---\n{log}\n\n"
                f"--- CLI Command ---\n{cli_command}"
            )
            return None, status_msg
    
    except Exception as e:
        status_msg = (
            f"❌ Error during generation:\n{str(e)}\n\n"
            f"--- CLI Command ---\n{cli_command}"
        )
        return None, status_msg


# ============================================================================
# Gradio Interface
# ============================================================================

def create_interface():
    """Create Gradio interface."""
    ensure_dirs()
    
    settings = MulaSettings.load(settings_path())
    preset_manager = PresetManager(presets_path())
    presets_data = preset_manager.load()
    
    # Custom CSS
    css = """
    .gradio-container {
        font-family: 'Segoe UI', Arial, sans-serif;
    }
    .header {
        text-align: center;
        background: linear-gradient(135deg, #1a252f 0%, #2c3e50 50%, #1a252f 100%);
        padding: 30px;
        border-radius: 10px;
        margin-bottom: 20px;
        border-bottom: 3px solid #3498db;
    }
    .header h1 {
        color: #ecf0f1;
        font-size: 2.5em;
        margin: 0;
        font-weight: bold;
    }
    .header p {
        color: #95a5a6;
        font-size: 1.1em;
        margin: 10px 0 0 0;
    }
    .preset-card {
        border: 2px solid #3498db;
        border-radius: 8px;
        padding: 15px;
        background: #f8f9fa;
    }
    """
    
    # Preset selection functions
    def update_presets(genre_name):
        """Update preset dropdown based on genre."""
        presets = preset_manager.get_presets_for_genre(genre_name)
        choices = [p["name"] for p in presets]
        return gr.Dropdown(choices=choices, value=choices[0] if choices else None)
    
    def load_preset_tags(genre_name, preset_name):
        """Load tags from selected preset."""
        presets = preset_manager.get_presets_for_genre(genre_name)
        for preset in presets:
            if preset["name"] == preset_name:
                return preset["tags"]
        return ""
    
    with gr.Blocks(css=css, title="HeartMuLa - Get Going Fast | DJ Grizzly Edition", theme=gr.themes.Soft()) as app:
        
        # Header
        with gr.Row():
            gr.HTML("""
                <div class="header">
                    <h1>🎵 HeartMuLa - Get Going Fast</h1>
                    <p><a href="https://www.youtube.com/@dj__grizzly" target="_blank" style="color: #3498db; text-decoration: none; font-size: 16px;">DJ Grizzly Edition</a></p>
                </div>
            """)
        
        with gr.Row():
            # Left Column - Main Controls
            with gr.Column(scale=2):
                
                # Model Configuration
                with gr.Group():
                    gr.Markdown("### ⚙️ Model Configuration")
                    model_path = gr.Textbox(
                        label="Model Path",
                        value=settings.model_path,
                        placeholder="ckpt",
                        info="Path to HeartMuLa model directory"
                    )
                    version = gr.Dropdown(
                        choices=["3B"],
                        value=settings.version,
                        label="Model Version"
                    )
                
                # Creative Input
                with gr.Group():
                    gr.Markdown("### 🎨 Creative Input")
                    tags = gr.Textbox(
                        label="Style Tags",
                        placeholder="club house, female vocals, angelic, dreamy, 128 bpm, four-on-the-floor kick, offbeat open hi-hat, rolling bassline, sidechain compression, bright supersaw, riser, snare build, drop, festival energy, wide stereo",
                        lines=2,
                        info="Describe the musical style, genre, tempo, and characteristics"
                    )
                    lyrics = gr.Textbox(
                        label="Lyrics (optional)",
                        value=(
                            "[Intro]\n"
                            "Get Going Fast is so super... duper... radiant... kinetic... hyper...\n\n"
                            "[Verse]\n"
                            "turbo... mega... lightning-striker... star-glimmer...\n\n"
                            "super... pulse... shimmer... ultra... hyper... turbo...\n\n"
                            "nebula...\n\n"
                            "[Prechorus]\n"
                            "echo... signal... flicker... spark... drift...\n\n"
                            "[Chorus]\n"
                            "Get Going Fast is so super... duper... vivid... electric... soaring...\n\n"
                            "ultra... hyper... turbo... mega... starlight...\n\n"
                            "[Bridge]\n"
                            "fade... rise... breathe... shine...\n\n"
                            "[Outro]\n"
                            "fade... rise... glow... flow... ever... onward...\n"
                        ),
                        lines=12,
                        info="Leave empty for instrumental"
                    )

                
                # Generation Parameters
                with gr.Group():
                    gr.Markdown("### 🎛️ Generation Parameters")
                    with gr.Row():
                        max_length = gr.Slider(
                            minimum=10,
                            maximum=600,
                            step=10,
                            value=settings.max_audio_length_sec,
                            label="Max Length (seconds)",
                            info="Duration of generated music"
                        )
                        topk = gr.Slider(
                            minimum=1,
                            maximum=200,
                            step=1,
                            value=settings.topk,
                            label="Top-K",
                            info="Sampling parameter"
                        )
                    with gr.Row():
                        temperature = gr.Slider(
                            minimum=0.1,
                            maximum=2.0,
                            step=0.1,
                            value=settings.temperature,
                            label="Temperature",
                            info="Creativity vs consistency"
                        )
                        cfg_scale = gr.Slider(
                            minimum=0.0,
                            maximum=10.0,
                            step=0.1,
                            value=settings.cfg_scale,
                            label="CFG Scale",
                            info="Guidance strength"
                        )
                
                # Output Settings
                with gr.Group():
                    gr.Markdown("### 💾 Output Settings")
                    output_dir = gr.Textbox(
                        label="Output Directory",
                        value=settings.output_dir,
                        placeholder="output"
                    )
                
                # Generate Button
                generate_btn = gr.Button(
                    "🎵 Generate Music",
                    variant="primary",
                    size="lg"
                )
            
            # Right Column - Presets
            with gr.Column(scale=1):
                with gr.Group():
                    gr.Markdown("### 📚 Preset Library")
                    gr.Markdown("*Select a genre and preset to load style tags*")
                    
                    genre_dropdown = gr.Dropdown(
                        choices=preset_manager.get_genre_names(),
                        value=preset_manager.get_genre_names()[0] if preset_manager.get_genre_names() else None,
                        label="Genre",
                        interactive=True
                    )
                    
                    preset_dropdown = gr.Dropdown(
                        choices=[],
                        label="Preset",
                        interactive=True
                    )
                    
                    load_preset_btn = gr.Button("Load Preset Tags", size="sm")
                    
                    # Preset info
                    gr.Markdown("""
                    **Available Genres:**
                    - EDM (House, Techno, D&B, etc.)
                    - Rock (Classic, Hard Rock, Metal)
                    - Pop (Modern, Synthpop, Dance Pop)
                    - R&B (Contemporary, Neo Soul, Trap Soul)
                    - Rap (Boom Bap, Trap, Drill)
                    - Ballad / Slow
                    - Instrumental
                    - Reggae
                    - Custom
                    """)
        
        # Output Section
        with gr.Row():
            with gr.Column():
                gr.Markdown("### 🎧 Output")
                audio_output = gr.Audio(
                    label="Generated Music",
                    type="filepath"
                )
                status_output = gr.Textbox(
                    label="Generation Status",
                    lines=10,
                    max_lines=20
                )
        
        # Event handlers
        genre_dropdown.change(
            fn=update_presets,
            inputs=[genre_dropdown],
            outputs=[preset_dropdown]
        )
        
        load_preset_btn.click(
            fn=load_preset_tags,
            inputs=[genre_dropdown, preset_dropdown],
            outputs=[tags]
        )
        
        generate_btn.click(
            fn=generate_music,
            inputs=[
                model_path,
                version,
                tags,
                lyrics,
                max_length,
                topk,
                temperature,
                cfg_scale,
                output_dir
            ],
            outputs=[audio_output, status_output]
        )
        
        # Load initial presets
        app.load(
            fn=update_presets,
            inputs=[genre_dropdown],
            outputs=[preset_dropdown]
        )
        
        # Footer
        gr.Markdown("""
        ---
        **HeartMuLa - Get Going Fast** | [DJ Grizzly Edition](https://www.youtube.com/@dj__grizzly)  
        Powered by HeartMuLa | Built with Gradio
        """)
    
    return app


# ============================================================================
# Main Entry Point
# ============================================================================

def main():
    """Launch the Gradio app."""
    app = create_interface()
    
    # Allow Gradio to serve files from output directory
    output_path = root_dir() / "output"
    output_path.mkdir(parents=True, exist_ok=True)
    
    app.launch(
        server_name="0.0.0.0",
        server_port=7860,
        share=False,
        inbrowser=True,
        allowed_paths=[str(output_path)]
    )


if __name__ == "__main__":
    main()
