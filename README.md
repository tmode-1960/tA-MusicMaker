# tA-MusicMaker (v1.32)

A modern Windows desktop application for AI music production powered by the **Plenio YuE2 — Song** ComfyUI workflow (compatible with Plenio 1.5, 1.6, and 2.0), wrapped in the signature **thomo.ART** dark UI.

Connects directly to your local ComfyUI instance and transforms complex node networks into an intuitive, responsive, and elegant production suite.

---

## 🎵 Features

- **Intuitive Studio UI:** Signature dark/light theme with responsive controls, centered confirmation dialogs, real-time status monitoring, and bilingual support (**Deutsch** / **English**).
- **Direct ComfyUI Integration & Launch:** Automatically connects to your local ComfyUI instance via WebSocket/REST (`http://127.0.0.1:8188`), includes a **Launch ComfyUI** button (with Windows Terminal / WSL profile support and native file browser), live GPU/VRAM statistics, and one-click ASR troubleshooting.
- **Dynamic Plenio Version & Model Detection:** Automatically detects your installed [Plenio Music Production System](https://github.com/jplenio/Plenio-Music-Production-System) version (v1.5 / v1.6 / v2.0), provides a live **Plenio Model Check** diagnostic in Settings, and supports **Quick-Presets** (*Quick sketch*, *Party - fast*, *Full song*, *Best quality*, *Three takes*, *Instrumental*).
- **AI Song Generation (YuE2 3B):**
  - Full song generation with lyrics, extended section tags, and customizable genre styles.
  - Lyrics and prompt assistant powered by **Gemma 4 12B (auto)** GGUF with automatic fallback to *Gemma 4 E4B*.
  - Seed management, batch iterations, and lyrics fidelity controls (with automatic Best-Take/ASR fallback).
- **Plenio 2.0 Studio Tools (when connected to Plenio 2.0):**
  - **Enhance & Master:** Upload existing audio files (`.mp3`, `.flac`, `.wav`, `.ogg`, `.m4a`) for Audio HQ & UniverSR (48 kHz) mastering with optional stem export.
  - **AI Cover:** Re-imagine existing tracks with new genre, mood, vocals mode, `Original Notes` fidelity, and optional custom lyrics.
- **Visual Audio Timeline Ruler:**
  - Clear timeline scale showing song minutes, seconds, and musical bar intervals.
- **Audio Post-Processing & Stem Integration:**
  - **Stem Separation:** Split generated tracks into vocals, drums, bass, instrumental, and other stems (*BS-RoFormer*) with unified stem playback & download in the library.
  - **Audio Refinement (48 kHz):** High-fidelity audio super-resolution (*UniverSR*).
  - **Cover Art Generator:** Create matching song artwork (*FLUX.2 Klein 4B*).
- **Voice Swap (RVC / Applio Integration):**
  - Seamlessly replace or fine-tune vocals using trained RVC models via Applio.
  - Includes a printable vocal recording guide: `Stimmaufnahme-Vorlage-RVC.pdf`.
- **Vocal-Isolated Subtitles, Lyrics Alignment & Video Export:**
  - High-precision lyrics alignment using vocal isolation (Demucs), Qwen3-ASR / ForcedAligner (`wsl_vocal_align.py`), and monotone *faster-whisper* anchor matching.
  - Export synchronized `.srt` subtitle files (with bilingual translation) and `.mp4` music videos.
- **Player & Media Library:**
  - Built-in audio player with waveform preview, stem switcher, playback controls, and quick export.

---

## 🚀 How to Run

### Option 1: Windows Installer or Standalone App (Recommended for Users)
**No Python or Git required!**
1. Go to the [**Releases**](https://github.com/tmode-1960/tA-MusicMaker/releases) section of this repository.
2. Download either:
   - **`tA-MusicMaker-Setup.exe`** (Standard Windows Installer with Start Menu & Desktop shortcuts)
   - **`tA-MusicMaker-v1.32.zip`** (Portable package — extract anywhere and double-click `tA-MusicMaker.exe`)
3. Ensure ComfyUI is running in the background (or configure your start command in Settings and click **Launch ComfyUI**).
4. Launch **tA-MusicMaker**. Once the status indicator turns green (*ComfyUI connected*), you're ready to create!

> **Windows SmartScreen Note:**  
> Because this executable is built independently and not signed with an enterprise certificate, Windows may display *"Windows protected your PC"*.  
> Simply click **"More info"** &rarr; **"Run anyway"**.

---

### Option 2: Running from Source (For Developers)

**Prerequisites:** Python 3.10+

```bash
# Clone the repository
git clone https://github.com/tmode-1960/tA-MusicMaker.git
cd tA-MusicMaker

# Quick start (uses standard library and local server)
start.bat
# or
python server.py
```

Optional desktop window wrapper:
```bash
pip install pywebview
```

---

## ⚙️ Prerequisites (in ComfyUI)

To generate music, ensure your local ComfyUI instance has the following installed:

### 1. Custom Nodes (via ComfyUI Manager)
* **Plenio Music Production System** (search for *"Plenio"* in ComfyUI Manager and install). Reference: [Plenio Repository](https://github.com/jplenio/Plenio-Music-Production-System).

### 2. AI Models (inside ComfyUI)
* **Music Model:** `YuE2 3B int8`
* **Writing Model (Lyrics & Drafts):** `Gemma 4 12B (auto)` GGUF (or `Gemma 4 E4B`)
* *(Optional for add-on modules):*
  * **Stem Separation:** `BS-RoFormer`
  * **Refinement (48 kHz):** `UniverSR`
  * **Cover Art:** `FLUX.2 Klein 4B` *(requires > 8 GB VRAM)*

### 3. Hardware Requirements
* NVIDIA GPU with minimum **8 GB VRAM** (12 GB+ recommended for simultaneous cover art and refinement).

### 4. Optional: Custom Voice (RVC)
* If you want to use custom voice models (*Voice Swap*), install **Applio**. If Applio is not installed, the app automatically disables this optional module while everything else works normally.

---

## 🛠️ Building the Standalone App & Installer

If you wish to compile the application and installer yourself:

1. Ensure **PyInstaller** and **Inno Setup 6** (optional, for Setup.exe) are installed.
2. Run:
   ```cmd
   build_app.bat
   ```
   *(This automatically bumps the build version, packages `tA-MusicMaker.exe`, and builds `tA-MusicMaker-Setup.exe` into the `dist/` directory).*

---

## 📄 Credits & License

- Created by **thomo.ART**.
- Powered by the [Plenio Music Production System](https://github.com/jplenio/Plenio-Music-Production-System) by J. Plenio.
- Special thanks to CodexMundi for inspiration, testing and collaboration.
- Released under the MIT License.
