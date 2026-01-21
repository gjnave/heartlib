"""HeartMuLa Music Generator - Standalone Edition
Professional UI for HeartMuLa music generation with comprehensive presets.

Requirements:
    pip install PySide6

File Structure (all paths relative to root where this script is located):
    - Settings: presets/setsave/mula.json
    - Presets: presets/setsave/mulapresets.json
    - Output: output/
    - Models: ckpt/
    - Script: examples/run_music_generation.py
    
Location: Place this file in root directory (same level as ckpt/, output/, examples/)
"""

from __future__ import annotations

import json
import os
import re
import subprocess
import sys
from dataclasses import dataclass, asdict
from datetime import datetime
from pathlib import Path
from typing import Optional

from PySide6.QtCore import Qt, QProcess, QTime, Signal, QTimer, QUrl
from PySide6.QtGui import QFont, QColor, QPalette, QIcon, QDesktopServices
from PySide6.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout, QFormLayout,
    QLineEdit, QPushButton, QComboBox, QSpinBox, QDoubleSpinBox,
    QTextEdit, QLabel, QGroupBox, QFileDialog, QMessageBox,
    QTimeEdit, QProgressBar, QSplitter, QFrame, QScrollArea,
    QListWidget, QListWidgetItem, QCheckBox
)


# ============================================================================
# Configuration & Utilities
# ============================================================================

def root_dir() -> Path:
    """Get root directory (script is in root)."""
    return Path(__file__).resolve().parent


def settings_path() -> Path:
    """Path to settings JSON."""
    return root_dir() / "presets" / "setsave" / "mula.json"


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


def ms_to_time(ms: int) -> QTime:
    """Convert milliseconds to QTime."""
    total_seconds = max(1, int(round(ms / 1000.0)))
    h = total_seconds // 3600
    m = (total_seconds % 3600) // 60
    s = total_seconds % 60
    return QTime(h % 24, m, s)


def time_to_ms(t: QTime) -> int:
    """Convert QTime to milliseconds."""
    return int((t.hour() * 3600 + t.minute() * 60 + t.second()) * 1000)


# ============================================================================
# Data Classes
# ============================================================================

@dataclass
class MulaSettings:
    """User settings for HeartMuLa."""
    model_path: str = "ckpt"
    version: str = "3B"
    max_audio_length_ms: int = 240000  # 4 minutes
    topk: int = 50
    temperature: float = 1.0
    cfg_scale: float = 1.5
    lyrics_text: str = (
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
    "[Verse]\n"
    "halo... prism... glow... flow...\n\n"
    "soft... bright... endless... weightless...\n\n"
    "[Bridge]\n"
    "fade... rise... breathe... shine...\n\n"
    "[Chorus]\n"
    "Get Going Fast is so super... duper... radiant... kinetic... hyper...\n\n"
    "ultra... hyper... turbo... mega... starlight...\n\n"
    "[Outro]\n"
    "fade... rise... glow... flow... ever... onward...\n"
    )

    tags_text: str = "club house, female vocals, angelic, dreamy, 128 bpm, four-on-the-floor kick, offbeat open hi-hat, rolling bassline, sidechain compression, bright supersaw, riser, snare build, drop, festival energy, wide stereo"
    output_dir: str = "output"
    auto_open_output: bool = True

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
            return sMulaSettings()

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


# ============================================================================
# UI Components
# ============================================================================

class StatusBar(QFrame):
    """Custom status bar with modern styling."""
    
    def __init__(self):
        super().__init__()
        self.setFrameStyle(QFrame.StyledPanel)
        self.setStyleSheet("""
            QFrame {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #2c3e50, stop:1 #34495e);
                border-top: 1px solid #1a252f;
                padding: 8px 12px;
                color: #ecf0f1;
            }
        """)
        
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        
        self.label = QLabel("Ready")
        self.label.setStyleSheet("color: #ecf0f1; font-size: 11px;")
        layout.addWidget(self.label)
        
        layout.addStretch()
        
        self.progress = QProgressBar()
        self.progress.setVisible(False)
        self.progress.setMaximumWidth(200)
        self.progress.setStyleSheet("""
            QProgressBar {
                border: 1px solid #1a252f;
                background: #1a252f;
                text-align: center;
                color: white;
                border-radius: 3px;
            }
            QProgressBar::chunk {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #3498db, stop:1 #2980b9);
            }
        """)
        layout.addWidget(self.progress)
    
    def set_status(self, text: str, progress: Optional[int] = None):
        """Update status message and optional progress."""
        self.label.setText(text)
        if progress is not None:
            self.progress.setVisible(True)
            self.progress.setValue(progress)
        else:
            self.progress.setVisible(False)


class PresetBrowser(QGroupBox):
    """Preset browser with genre categories."""
    
    preset_selected = Signal(str)  # Emits tags when preset selected
    
    def __init__(self, preset_manager: PresetManager):
        super().__init__("Preset Library")
        self.preset_manager = preset_manager
        self.presets = preset_manager.load()
        
        self.setStyleSheet("""
            QGroupBox {
                font-weight: bold;
                border: 2px solid #3498db;
                border-radius: 5px;
                margin-top: 12px;
                padding-top: 12px;
                background: #ecf0f1;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px;
                color: #2c3e50;
            }
        """)
        
        layout = QVBoxLayout(self)
        
        # Genre selector
        genre_layout = QHBoxLayout()
        genre_layout.addWidget(QLabel("Genre:"))
        
        self.genre_combo = QComboBox()
        self.genre_combo.setStyleSheet("""
            QComboBox {
                padding: 6px;
                border: 1px solid #bdc3c7;
                border-radius: 3px;
                background: white;
            }
            QComboBox::drop-down {
                border: none;
                width: 20px;
            }
        """)
        for genre in self.presets.get("genres", []):
            self.genre_combo.addItem(genre["name"])
        self.genre_combo.currentTextChanged.connect(self._on_genre_changed)
        genre_layout.addWidget(self.genre_combo, 1)
        
        layout.addLayout(genre_layout)
        
        # Preset list
        self.preset_list = QListWidget()
        self.preset_list.setStyleSheet("""
            QListWidget {
                border: 1px solid #bdc3c7;
                border-radius: 3px;
                background: white;
                padding: 4px;
            }
            QListWidget::item {
                padding: 8px;
                border-radius: 3px;
            }
            QListWidget::item:hover {
                background: #e8f4f8;
            }
            QListWidget::item:selected {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #3498db, stop:1 #2980b9);
                color: white;
            }
        """)
        self.preset_list.itemDoubleClicked.connect(self._on_preset_selected)
        layout.addWidget(self.preset_list)
        
        # Load first genre
        if self.genre_combo.count() > 0:
            self._on_genre_changed(self.genre_combo.currentText())
    
    def _on_genre_changed(self, genre_name: str):
        """Update preset list when genre changes."""
        self.preset_list.clear()
        for genre in self.presets.get("genres", []):
            if genre["name"] == genre_name:
                for preset in genre.get("presets", []):
                    item = QListWidgetItem(preset["name"])
                    item.setData(Qt.UserRole, preset["tags"])
                    self.preset_list.addItem(item)
                break
    
    def _on_preset_selected(self, item: QListWidgetItem):
        """Emit tags when preset is double-clicked."""
        tags = item.data(Qt.UserRole)
        if tags:
            self.preset_selected.emit(tags)


# ============================================================================
# Main Application
# ============================================================================

class HeartMuLaApp(QWidget):
    """Main HeartMuLa application window."""
    
    def __init__(self):
        super().__init__()
        ensure_dirs()
        
        self.settings = MulaSettings.load(settings_path())
        self.preset_manager = PresetManager(presets_path())
        
        self.process: Optional[QProcess] = None
        self.current_output_file: Optional[Path] = None
        
        self.init_ui()
        self.apply_theme()
    
    def init_ui(self):
        """Initialize the user interface."""
        self.setWindowTitle("HeartMuLa - Get Going Fast | DJ Grizzly Edition")
        self.setMinimumSize(1100, 750)
        
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        
        # Header
        header = self.create_header()
        main_layout.addWidget(header)
        
        # Content area with splitter
        splitter = QSplitter(Qt.Horizontal)
        splitter.setChildrenCollapsible(False)
        
        # Left panel - Controls
        left_panel = self.create_controls_panel()
        splitter.addWidget(left_panel)
        
        # Right panel - Presets
        right_panel = PresetBrowser(self.preset_manager)
        right_panel.preset_selected.connect(self.load_preset_tags)
        splitter.addWidget(right_panel)
        
        splitter.setSizes([700, 400])
        main_layout.addWidget(splitter, 1)
        
        # Status bar
        self.status_bar = StatusBar()
        main_layout.addWidget(self.status_bar)
    
    def create_header(self) -> QFrame:
        """Create header section."""
        header = QFrame()
        header.setStyleSheet("""
            QFrame {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #1a252f, stop:0.5 #2c3e50, stop:1 #1a252f);
                border-bottom: 3px solid #3498db;
                padding: 20px;
            }
        """)
        
        layout = QVBoxLayout(header)
        
        title = QLabel("🎵 HeartMuLa - Get Going Fast")
        title.setStyleSheet("""
            font-size: 32px;
            font-weight: bold;
            color: #ecf0f1;
            font-family: 'Segoe UI', sans-serif;
        """)
        layout.addWidget(title)
        
        subtitle = QLabel('<a href="https://www.youtube.com/@dj__grizzly" style="color: #3498db; text-decoration: none; font-size: 16px;">DJ Grizzly Edition</a>')
        subtitle.setOpenExternalLinks(True)
        subtitle.setStyleSheet("font-size: 16px; color: #3498db;")
        layout.addWidget(subtitle)
        
        return header
    
    def create_controls_panel(self) -> QWidget:
        """Create main controls panel."""
        panel = QWidget()
        panel.setStyleSheet("background: #ecf0f1;")
        
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setWidget(panel)
        scroll.setFrameShape(QFrame.NoFrame)
        
        layout = QVBoxLayout(panel)
        layout.setSpacing(15)
        layout.setContentsMargins(15, 15, 15, 15)
        
        # Model Configuration
        model_group = self.create_model_group()
        layout.addWidget(model_group)
        
        # Creative Input
        creative_group = self.create_creative_group()
        layout.addWidget(creative_group)
        
        # Generation Parameters
        params_group = self.create_parameters_group()
        layout.addWidget(params_group)
        
        # Output Settings
        output_group = self.create_output_group()
        layout.addWidget(output_group)
        
        # Action Buttons
        actions = self.create_action_buttons()
        layout.addWidget(actions)
        
        # Console Output
        console_group = self.create_console_group()
        layout.addWidget(console_group, 1)
        
        return scroll
    
    def create_model_group(self) -> QGroupBox:
        """Create model configuration group."""
        group = QGroupBox("Model Configuration")
        group.setStyleSheet(self.group_style())
        
        layout = QFormLayout(group)
        layout.setSpacing(10)
        
        # Model Path
        path_layout = QHBoxLayout()
        self.model_path = QLineEdit(self.settings.model_path)
        self.model_path.setPlaceholderText("ckpt")
        path_layout.addWidget(self.model_path, 1)
        
        browse_btn = QPushButton("Browse")
        browse_btn.setMaximumWidth(80)
        browse_btn.clicked.connect(self.browse_model_path)
        path_layout.addWidget(browse_btn)
        
        layout.addRow("Model Path:", path_layout)
        
        # Version
        self.version = QComboBox()
        self.version.addItems(["3B"])
        self.version.setCurrentText(self.settings.version)
        layout.addRow("Version:", self.version)
        
        return group
    
    def create_creative_group(self) -> QGroupBox:
        """Create creative input group."""
        group = QGroupBox("Creative Input")
        group.setStyleSheet(self.group_style())
        
        layout = QVBoxLayout(group)
        
        # Tags
        layout.addWidget(QLabel("Style Tags:"))
        self.tags = QLineEdit(self.settings.tags_text)
        self.tags.setPlaceholderText("e.g., club house, 128 bpm, four-on-the-floor kick...")
        self.tags.setStyleSheet("""
            QLineEdit {
                padding: 8px;
                border: 2px solid #bdc3c7;
                border-radius: 4px;
                background: white;
                font-size: 12px;
            }
            QLineEdit:focus {
                border: 2px solid #3498db;
            }
        """)
        layout.addWidget(self.tags)
        
        # Lyrics
        layout.addWidget(QLabel("Lyrics:"))
        self.lyrics = QTextEdit()
        self.lyrics.setPlainText(self.settings.lyrics_text)
        self.lyrics.setPlaceholderText(
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
        )

        self.lyrics.setMaximumHeight(150)
        self.lyrics.setStyleSheet("""
            QTextEdit {
                border: 2px solid #bdc3c7;
                border-radius: 4px;
                background: white;
                font-family: 'Consolas', monospace;
                font-size: 11px;
            }
            QTextEdit:focus {
                border: 2px solid #3498db;
            }
        """)
        layout.addWidget(self.lyrics)
        
        return group
    
    def create_parameters_group(self) -> QGroupBox:
        """Create generation parameters group."""
        group = QGroupBox("Generation Parameters")
        group.setStyleSheet(self.group_style())
        
        layout = QFormLayout(group)
        layout.setSpacing(10)
        
        # Max Length
        self.max_length = QTimeEdit()
        self.max_length.setDisplayFormat("mm:ss")
        self.max_length.setTime(ms_to_time(self.settings.max_audio_length_ms))
        layout.addRow("Max Length:", self.max_length)
        
        # Top-K
        self.topk = QSpinBox()
        self.topk.setRange(1, 200)
        self.topk.setValue(self.settings.topk)
        layout.addRow("Top-K:", self.topk)
        
        # Temperature
        self.temperature = QDoubleSpinBox()
        self.temperature.setRange(0.1, 2.0)
        self.temperature.setSingleStep(0.1)
        self.temperature.setValue(self.settings.temperature)
        layout.addRow("Temperature:", self.temperature)
        
        # CFG Scale
        self.cfg_scale = QDoubleSpinBox()
        self.cfg_scale.setRange(0.0, 10.0)
        self.cfg_scale.setSingleStep(0.1)
        self.cfg_scale.setValue(self.settings.cfg_scale)
        layout.addRow("CFG Scale:", self.cfg_scale)
        
        return group
    
    def create_output_group(self) -> QGroupBox:
        """Create output settings group."""
        group = QGroupBox("Output Settings")
        group.setStyleSheet(self.group_style())
        
        layout = QFormLayout(group)
        layout.setSpacing(10)
        
        # Output Directory
        dir_layout = QHBoxLayout()
        self.output_dir = QLineEdit(self.settings.output_dir)
        self.output_dir.setPlaceholderText("output")
        dir_layout.addWidget(self.output_dir, 1)
        
        browse_btn = QPushButton("Browse")
        browse_btn.setMaximumWidth(80)
        browse_btn.clicked.connect(self.browse_output_dir)
        dir_layout.addWidget(browse_btn)
        
        layout.addRow("Output Directory:", dir_layout)
        
        # Auto-open output
        self.auto_open = QCheckBox("Automatically open output folder after generation")
        self.auto_open.setChecked(self.settings.auto_open_output)
        layout.addRow("", self.auto_open)
        
        return group
    
    def create_action_buttons(self) -> QFrame:
        """Create action buttons."""
        frame = QFrame()
        layout = QHBoxLayout(frame)
        layout.setContentsMargins(0, 10, 0, 10)
        
        self.generate_btn = QPushButton("🎵 Generate Music")
        self.generate_btn.setMinimumHeight(45)
        self.generate_btn.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #27ae60, stop:1 #229954);
                color: white;
                font-size: 16px;
                font-weight: bold;
                border: none;
                border-radius: 5px;
                padding: 10px;
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #2ecc71, stop:1 #27ae60);
            }
            QPushButton:pressed {
                background: #229954;
            }
            QPushButton:disabled {
                background: #95a5a6;
            }
        """)
        self.generate_btn.clicked.connect(self.generate_music)
        layout.addWidget(self.generate_btn, 3)
        
        self.stop_btn = QPushButton("⏹ Stop")
        self.stop_btn.setMinimumHeight(45)
        self.stop_btn.setEnabled(False)
        self.stop_btn.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #e74c3c, stop:1 #c0392b);
                color: white;
                font-size: 16px;
                font-weight: bold;
                border: none;
                border-radius: 5px;
                padding: 10px;
            }
            QPushButton:hover:enabled {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #ec7063, stop:1 #e74c3c);
            }
            QPushButton:pressed {
                background: #c0392b;
            }
            QPushButton:disabled {
                background: #95a5a6;
            }
        """)
        self.stop_btn.clicked.connect(self.stop_generation)
        layout.addWidget(self.stop_btn, 1)
        
        self.play_btn = QPushButton("▶ Play")
        self.play_btn.setMinimumHeight(45)
        self.play_btn.setEnabled(False)
        self.play_btn.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #3498db, stop:1 #2980b9);
                color: white;
                font-size: 16px;
                font-weight: bold;
                border: none;
                border-radius: 5px;
                padding: 10px;
            }
            QPushButton:hover:enabled {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #5dade2, stop:1 #3498db);
            }
            QPushButton:pressed {
                background: #2980b9;
            }
            QPushButton:disabled {
                background: #95a5a6;
            }
        """)
        self.play_btn.clicked.connect(self.play_output)
        layout.addWidget(self.play_btn, 1)
        
        return frame
    
    def create_console_group(self) -> QGroupBox:
        """Create console output group."""
        group = QGroupBox("Generation Console")
        group.setStyleSheet(self.group_style())
        
        layout = QVBoxLayout(group)
        
        self.console = QTextEdit()
        self.console.setReadOnly(True)
        self.console.setStyleSheet("""
            QTextEdit {
                background: #1e1e1e;
                color: #d4d4d4;
                border: 1px solid #3e3e42;
                border-radius: 3px;
                font-family: 'Consolas', 'Courier New', monospace;
                font-size: 10px;
                padding: 8px;
            }
        """)
        layout.addWidget(self.console)
        
        # Console controls
        controls = QHBoxLayout()
        
        clear_btn = QPushButton("Clear")
        clear_btn.setMaximumWidth(80)
        clear_btn.clicked.connect(self.console.clear)
        controls.addWidget(clear_btn)
        
        controls.addStretch()
        
        layout.addLayout(controls)
        
        return group
    
    def group_style(self) -> str:
        """Standard group box styling."""
        return """
            QGroupBox {
                font-weight: bold;
                border: 2px solid #bdc3c7;
                border-radius: 5px;
                margin-top: 12px;
                padding-top: 12px;
                background: white;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px;
                color: #2c3e50;
            }
            QLineEdit, QComboBox, QSpinBox, QDoubleSpinBox, QTimeEdit {
                padding: 6px;
                border: 1px solid #bdc3c7;
                border-radius: 3px;
                background: white;
            }
            QLineEdit:focus, QComboBox:focus, QSpinBox:focus, 
            QDoubleSpinBox:focus, QTimeEdit:focus {
                border: 1px solid #3498db;
            }
        """
    
    def apply_theme(self):
        """Apply global application theme."""
        self.setStyleSheet("""
            QWidget {
                font-family: 'Segoe UI', Arial, sans-serif;
                font-size: 12px;
            }
            QPushButton {
                padding: 6px 12px;
                border-radius: 3px;
                border: 1px solid #bdc3c7;
                background: white;
            }
            QPushButton:hover {
                background: #ecf0f1;
                border: 1px solid #95a5a6;
            }
            QPushButton:pressed {
                background: #bdc3c7;
            }
        """)
    
    # ========================================================================
    # Event Handlers
    # ========================================================================
    
    def browse_model_path(self):
        """Browse for model directory."""
        path = QFileDialog.getExistingDirectory(
            self, "Select Model Directory", str(root_dir())
        )
        if path:
            self.model_path.setText(path)
    
    def browse_output_dir(self):
        """Browse for output directory."""
        path = QFileDialog.getExistingDirectory(
            self, "Select Output Directory", str(root_dir() / "output")
        )
        if path:
            self.output_dir.setText(path)
    
    def load_preset_tags(self, tags: str):
        """Load tags from preset."""
        self.tags.setText(tags)
        self.log_message(f"Loaded preset tags: {tags[:60]}...")
    
    def save_settings(self):
        """Save current settings."""
        self.settings.model_path = self.model_path.text().strip()
        self.settings.version = self.version.currentText()
        self.settings.max_audio_length_ms = time_to_ms(self.max_length.time())
        self.settings.topk = self.topk.value()
        self.settings.temperature = self.temperature.value()
        self.settings.cfg_scale = self.cfg_scale.value()
        self.settings.lyrics_text = self.lyrics.toPlainText()
        self.settings.tags_text = self.tags.text()
        self.settings.output_dir = self.output_dir.text().strip()
        self.settings.auto_open_output = self.auto_open.isChecked()
        
        self.settings.save(settings_path())
    
    def validate_installation(self) -> tuple[bool, str]:
        """Validate HeartMuLa installation."""
        root = root_dir()
        
        # Check model directory
        model_path = Path(self.model_path.text().strip())
        if not model_path.is_absolute():
            model_path = root / model_path
        
        if not model_path.exists():
            return False, f"Model directory not found: {model_path}"
        
        # Check required model files
        required = [
            model_path / "HeartCodec-oss",
            model_path / "HeartMuLa-oss-3B",
            model_path / "gen_config.json",
            model_path / "tokenizer.json",
        ]
        
        missing = [str(p) for p in required if not p.exists()]
        if missing:
            return False, f"Missing model files:\n" + "\n".join(missing)
        
        # Check generation script
        script = root / "examples" / "run_music_generation.py"
        if not script.exists():
            return False, f"Generation script not found: {script}\n\nExpected location: examples/run_music_generation.py"
        
        return True, ""
    
    def generate_music(self):
        """Start music generation."""
        # Validate
        ok, error = self.validate_installation()
        if not ok:
            QMessageBox.critical(self, "Installation Error", error)
            return
        
        # Save settings
        self.save_settings()
        
        # Prepare paths
        root = root_dir()
        model_path = Path(self.model_path.text().strip())
        if not model_path.is_absolute():
            model_path = root / model_path
        
        output_dir = Path(self.output_dir.text().strip() or "output")
        if not output_dir.is_absolute():
            output_dir = root / output_dir
        output_dir.mkdir(parents=True, exist_ok=True)
        
        # Generate unique output filename
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        # Use a counter to ensure uniqueness
        counter = 1
        filename = f"heartmula_{timestamp}.mp3"
        output_file = output_dir / filename
        while output_file.exists():
            filename = f"heartmula_{timestamp}_{counter}.mp3"
            output_file = output_dir / filename
            counter += 1
        
        # Create temp files for lyrics and tags
        temp_dir = root / "presets" / "setsave" / "_mula_tmp"
        temp_dir.mkdir(parents=True, exist_ok=True)
        
        lyrics_file = temp_dir / "lyrics.txt"
        tags_file = temp_dir / "tags.txt"
        
        lyrics_file.write_text(self.lyrics.toPlainText() + "\n", encoding="utf-8")
        tags_file.write_text(self.tags.text().strip() + "\n", encoding="utf-8")
        
        # Build command
        python_exe = sys.executable
        script = root / "examples" / "run_music_generation.py"
        
        cmd = [
            python_exe,
            str(script),
            f"--model_path={model_path}",
            f"--version={self.version.currentText()}",
            f"--lyrics={lyrics_file}",
            f"--tags={tags_file}",
            f"--save_path={output_file}",
            f"--max_audio_length_ms={time_to_ms(self.max_length.time())}",
            f"--topk={self.topk.value()}",
            f"--temperature={self.temperature.value()}",
            f"--cfg_scale={self.cfg_scale.value()}",
        ]
        
        # Start process
        self.console.clear()
        self.log_message("="*80)
        self.log_message("HEARTMULA GENERATION STARTED")
        self.log_message("="*80)
        self.log_message(f"Output: {output_file}")
        self.log_message(f"Command: {' '.join(cmd)}")
        self.log_message("="*80)
        
        self.process = QProcess(self)
        self.process.setProcessChannelMode(QProcess.MergedChannels)
        self.process.readyReadStandardOutput.connect(self.on_process_output)
        self.process.finished.connect(self.on_process_finished)
        
        self.current_output_file = output_file
        
        self.process.start(cmd[0], cmd[1:])
        
        # Update UI
        self.generate_btn.setEnabled(False)
        self.stop_btn.setEnabled(True)
        self.status_bar.set_status("Generating music...", 0)
    
    def stop_generation(self):
        """Stop the current generation."""
        if self.process and self.process.state() == QProcess.Running:
            self.process.kill()
            self.log_message("\n[PROCESS TERMINATED BY USER]")
    
    def play_output(self):
        """Play the last generated audio file."""
        if self.current_output_file and self.current_output_file.exists():
            try:
                QDesktopServices.openUrl(QUrl.fromLocalFile(str(self.current_output_file)))
            except Exception as e:
                QMessageBox.warning(self, "Playback Error", f"Could not open audio file:\n{e}")
        else:
            QMessageBox.information(self, "No Audio", "No audio file available to play.")
    
    def on_process_output(self):
        """Handle process output."""
        if self.process:
            data = bytes(self.process.readAllStandardOutput()).decode("utf-8", errors="replace")
            if data:
                for line in data.splitlines():
                    self.log_message(line)
    
    def on_process_finished(self, exit_code: int, exit_status):
        """Handle process completion."""
        self.generate_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)
        
        if exit_code == 0:
            self.log_message("\n" + "="*80)
            self.log_message("GENERATION COMPLETE")
            self.log_message("="*80)
            self.status_bar.set_status("Generation complete!", 100)
            
            # Enable play button
            if self.current_output_file and self.current_output_file.exists():
                self.play_btn.setEnabled(True)
            
            # Auto-open folder
            if self.auto_open.isChecked() and self.current_output_file:
                try:
                    if sys.platform == "win32":
                        os.startfile(self.current_output_file.parent)
                    elif sys.platform == "darwin":
                        subprocess.run(["open", str(self.current_output_file.parent)])
                    else:
                        subprocess.run(["xdg-open", str(self.current_output_file.parent)])
                except Exception as e:
                    self.log_message(f"Could not open folder: {e}")
            
            QMessageBox.information(
                self, 
                "Success", 
                f"Music generation complete!\n\nSaved to:\n{self.current_output_file}\n\nClick 'Play' to listen."
            )
        else:
            self.log_message(f"\n[PROCESS EXITED WITH CODE {exit_code}]")
            self.status_bar.set_status(f"Generation failed (exit code {exit_code})")
            self.current_output_file = None  # Clear on failure
            QMessageBox.warning(
                self,
                "Generation Failed",
                f"Process exited with code {exit_code}\n\nCheck console for details."
            )
    
    def log_message(self, message: str):
        """Append message to console."""
        self.console.append(message)
        self.console.verticalScrollBar().setValue(
            self.console.verticalScrollBar().maximum()
        )


# ============================================================================
# Application Entry Point
# ============================================================================

def main():
    """Run the application."""
    app = QApplication(sys.argv)
    
    # Set application info
    app.setApplicationName("HeartMuLa Generator")
    app.setOrganizationName("GetGoingFast")
    
    # Create and show window
    window = HeartMuLaApp()
    window.show()
    
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
