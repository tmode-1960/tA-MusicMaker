# tA-MusicMaker (v0.87)

A modern Windows desktop application for AI music production powered by the **Plenio YuE2 — Song** ComfyUI workflow, wrapped in the signature **thomo.ART** dark UI.

Connects to your local ComfyUI instance and replaces complex node networks with a clean, intuitive, and responsive interface.

---

## 🎵 Features

- **Intuitive Studio UI:** Clean dark theme with responsive controls, real-time status monitoring, and bilingual support (**Deutsch** / **English**).
- **Direct ComfyUI Integration:** Automatically connects to your local ComfyUI instance via WebSocket/REST (`http://127.0.0.1:8188`).
- **AI Song Generation (YuE2 3B):**
  - Full song generation with lyrics and customizable genre styles.
  - Lyrics and prompt assistant powered by LLM (*Gemma 4 E4B*).
  - Seed management, batch iterations, and lyrics fidelity controls.
- **Audio Post-Processing & Add-ons:**
  - **Stem Separation:** Split generated tracks into vocals and instrumental stems (*BS-RoFormer*).
  - **Audio Refinement (48 kHz):** High-fidelity audio super-resolution (*UniverSR*).
  - **Cover Art Generator:** Create matching song artwork (*FLUX.2 Klein 4B*).
- **Voice Swap (RVC / Applio Integration):**
  - Seamlessly replace or fine-tune vocals using trained RVC models via Applio.
  - Includes a printable vocal recording guide: `Stimmaufnahme-Vorlage-RVC.pdf`.
- **Subtitles & Lyrics Alignment:**
  - Automatic vocal transcription, alignment, and bilingual translation (*faster-whisper*).
  - Export synchronized `.srt` subtitle files.
- **Player & Media Library:**
  - Built-in audio player with waveform preview, playback controls, and quick export.

---

## 🚀 How to Run

### Option 1: Windows Installer or Standalone App (Recommended for Users)
**No Python or Git required!**
1. Go to the [**Releases**](https://github.com/tmode-1960/tA-MusicMaker/releases) section of this repository.
2. Download either:
   - **`tA-MusicMaker-Setup.exe`** (Standard Windows Installer with Start Menu & Desktop shortcuts)
   - **`tA-MusicMaker.exe`** (Portable single-file executable)
3. Ensure ComfyUI is running in the background.
4. Launch **tA-MusicMaker**. Once the status indicator turns green (*ComfyUI connected*), you're ready to create!

> **Windows SmartScreen Note:**  
> Because this executable is built independently and not signed with an expensive enterprise certificate, Windows may display *"Windows protected your PC"*.  
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
* **Plenio Music Production System** (search for *"Plenio"* in ComfyUI Manager and install).

### 2. AI Models (inside ComfyUI)
* **Music Model:** `YuE2 3B int8`
* **Writing Model (Lyrics & Drafts):** `Gemma 4 E4B`
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

Created by **thomo.ART**.  
Released under the MIT License.
