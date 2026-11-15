# Changelog

All notable changes to **tA-MusicMaker** are documented in this file.  
*Alle nennenswerten Änderungen an **tA-MusicMaker** werden in dieser Datei dokumentiert.*

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and this project adheres to [Semantic Versioning](https://semver.org/).

---

## [1.32] - 2026-11-15

### English (Primary)
- **Vocal-Isolated Forced Lyrics & Subtitle Alignment (`wsl_vocal_align.py`, `srt_translate.py`):**
  - Added `wsl_vocal_align.py` (bundled in `build_app.bat`): WSL GPU vocal isolation (Demucs) combined with Qwen3-ASR and Qwen3-ForcedAligner for precise word- and line-level lyrics timing.
  - Upgraded `srt_translate.py` with monotone Whisper anchor matching, Plenio Qwen3-ASR sung-segment correction (fixing misheard ASR words against written lyrics), embedded audio lyrics tag reading, and smooth cue extension until the next sentence.
- **ComfyUI Launch, GPU Status & ASR Auto-Recovery:**
  - Added live GPU hardware status indicator and a `⚡ Launch ComfyUI` button with Windows Terminal / WSL profile detection and a native file browser (`📁 Browse…`) for the ComfyUI start command.
  - Added automatic fallback to standard fidelity when ComfyUI hits a `Best-Take / ASR` `@strict` dataclass error, plus a one-click **Fix ComfyUI Best-Take / ASR** (`transformers` update) action in Settings.
- **File Saved Dialog & Build Resilience:**
  - Added a `✅ File Saved` dialog with **Open File** and **Show in Folder** actions after exporting files.
  - Hardened `bump_version.py` against temporary file locks on `web/index.html` during builds.

### Deutsch
- **Vokal-isolierte Untertitel- & Songtext-Synchronisation (`wsl_vocal_align.py`, `srt_translate.py`):**
  - Neues Modul `wsl_vocal_align.py` (in `build_app.bat` gebündelt): WSL-GPU-Gesangsisolation (Demucs) kombiniert mit Qwen3-ASR und Qwen3-ForcedAligner für präzises Timing von Songtexten und Untertiteln.
  - Erweiterung von `srt_translate.py` um monotones Whisper-Anker-Matching, Korrektur von Plenio-Qwen3-ASR-Segmenten anhand des geschriebenen Songtexts, Auslesen eingebetteter Lyrics-Tags und fließendes Verlängern der Untertitel-Cues bis zum nächsten Satz.
- **ComfyUI-Start, GPU-Status & ASR-Fehlerbehebung:**
  - Live-GPU-Statusanzeige und `⚡ ComfyUI starten`-Button inklusive Windows-Terminal-/WSL-Profil-Erkennung sowie nativem Dateiauswahl-Dialog (`📁 Durchsuchen…`) für den ComfyUI-Startbefehl.
  - Automatischer Fallback auf Standard-Fidelity bei `Best-Take / ASR` `@strict`-Dataclass-Fehlern in ComfyUI sowie ein 1-Klick-Button **ComfyUI Textprüfung (ASR) reparieren** in den Einstellungen.
- **Datei-gespeichert-Dialog & Build-Stabilität:**
  - Neuer `✅ Datei gespeichert`-Dialog mit den Aktionen **Datei öffnen** und **Im Ordner anzeigen**.
  - `bump_version.py` gegen kurzzeitige Dateisperren auf `web/index.html` beim Build abgesichert.

---

## [1.18] - 2026-11-14

### English (Primary)
- **Centered Styled Confirmation Dialogs:**
  - Replaced all native browser `confirm()` popups (resetting song brief, rendering a new take, deleting a song) with a centered, theme-matched `<dialog id="dlgConfirm">` modal without the browser `127.0.0.1:8765` header.

### Deutsch
- **Zentrierte Bestätigungsdialoge im App-Design:**
  - Alle nativen Browser-`confirm()`-Popups (Briefing zurücksetzen, Neuer Take, Song löschen) wurden durch ein mittig zentriertes Modal-Fenster (`#dlgConfirm`) im **thomo.ART**-Design ersetzt – ohne die störende `127.0.0.1:8765`-Kopfzeile.

---

## [1.17] - 2026-11-14

### English (Primary)
- **Hybrid Plenio 2.0 Studio Tools (`Enhance & Master` + `AI Cover`):**
  - Added a dedicated **Studio Tools** card (automatically shown when connected to Plenio 2.0) while keeping the existing `YuE2 · Song` workflow, all Mastering & Refine controls, RVC Voice Swap, and Video Export 100% untouched.
  - **Enhance & Master (`enhance-master`):** Upload any existing audio file (`.mp3`, `.flac`, `.wav`, `.ogg`, `.m4a`) to master and upscale it via Plenio 2.0's Audio HQ & UniverSR (48 kHz) pipeline with optional stem export.
  - **AI Cover (`yue2-cover`):** Upload a source track and re-imagine it in a new genre, mood, vocals mode, `Original Notes` fidelity (0–100), and optional custom lyrics.
  - Results are automatically saved into the local library and appear directly in the Player, History, and Video Export.
  - Fully backward-compatible: automatically hidden for users on Plenio 1.5/1.6.

### Deutsch
- **Hybride Plenio 2.0 Studio-Werkzeuge (`Enhance & Master` + `AI Cover`):**
  - Neue **Studio-Werkzeuge**-Karte (erscheint automatisch bei erkanntem Plenio 2.0), während der bestehende `YuE2 · Song`-Workflow, alle Mastering- & Refine-Regler, RVC Voice Swap und der Musikvideo-Export zu 100 % unverändert bleiben.
  - **Enhance & Master (`enhance-master`):** Bestehende Audiodateien (`.mp3`, `.flac`, `.wav`, `.ogg`, `.m4a`) hochladen und direkt mit Audio HQ & UniverSR (48 kHz) sowie optionalem Stem-Export veredeln lassen.
  - **AI Cover (`yue2-cover`):** Bestehenden Song hochladen und mit neuem Genre, Stimmung, Gesang/Instrumental, `Original-Noten`-Treue (0–100) und optionalem Text neu interpretieren lassen.
  - Fertige Ergebnisse landen automatisch in der Mediathek (Player, Verlauf & Video-Export).
  - Vollständig abwärtskompatibel: Bei Nutzern mit Plenio 1.5/1.6 wird die Karte automatisch ausgeblendet.

---

## [1.16] - 2026-11-14

### English (Primary)
- **Plenio 2.0 Quick-Presets:**
  - Added 1-click Quick-Preset buttons (`Quick sketch`, `Party - fast`, `Full song`, `Best quality`, `Three takes`, `Instrumental`) above the Song Brief.
  - Automatically fetches presets from Plenio 2.0's Song API v2 (`/plenio/api/v2/presets`) with built-in fallbacks for full compatibility with Plenio 1.5/1.6 installations.
- **Plenio Model Check (Settings):**
  - Added a live **Plenio Model Check** diagnostic in Settings (`/plenio/api/v1/models`) showing installed, missing, or size-mismatched models with sizes and target folders.
  - Safely degrades with a friendly notice when connected to older Plenio versions (< 1.6) or when ComfyUI is offline.
- **Plenio 2.0 API v2 Detection:**
  - Added non-breaking `plenio_v2_info` detection in `comfy_client.py` and `server.py` while keeping all existing 1.x/2.0 song generation, RVC Voice Swap, and video export workflows untouched.

### Deutsch
- **Plenio 2.0 Schnell-Presets:**
  - Neue 1-Klick-Preset-Buttons (*Quick sketch*, *Party - fast*, *Full song*, *Best quality*, *Three takes*, *Instrumental*) direkt im Song-Briefing.
  - Werden bei Plenio 2.0 live über die Song API v2 geladen und funktionieren dank integriertem Fallback auch nahtlos für Nutzer mit Plenio 1.5/1.6.
- **Plenio Modell-Diagnose (Einstellungen):**
  - Neuer Bereich **Plenio Modell-Diagnose** in den Einstellungen, der über ComfyUI live prüft, welche Modelle installiert sind, fehlen oder eine abweichende Größe haben.
  - Vollständig abwärtskompatibel (zeigt bei älteren Plenio-Versionen < 1.6 oder Offline-ComfyUI einen freundlichen Hinweis ohne Fehlermeldung).
- **Plenio 2.0 API-v2-Erkennung:**
  - Sichere Erkennung von Plenio 2.0 (`plenio_api_v2`) bei voller Beibehaltung aller bestehenden Song-, Voice-Swap- und Musikvideo-Funktionen.

---

## [1.15] - 2026-11-11

### English (Primary)
- **Status Bar Version Detection:**
  - Removed outdated legacy `(1.5-ready)` suffix for modern Plenio releases.
  - Correctly displays current Plenio versions (e.g. `Plenio v1.6.0`) directly in the status bar without misleading readiness markers.
- **Plenio 1.6+ Stem Track Integration:**
  - Automatic detection and unified grouping of all stems (`Vocals`, `Drums`, `Bass`, `Other/Rest`, `Instrumental`, and `Take Raw`) under a single song card in the Media/Player library.
  - Individual stem playback switcher in the player with one-click direct stem audio downloading.
  - Prevents redundant duplicate song entries when songs are rendered with stem separation enabled.

### Deutsch
- **Versionsanzeige in der Statusleiste:**
  - Veralteten Zusatz `(1.5-ready)` für moderne Plenio-Versionen entfernt.
  - Erkennt und zeigt installierte Plenio-Versionen (z. B. `Plenio v1.6.0`) nun sauber und ohne irreführende Vorbereitungs-Labels an.
- **Plenio 1.6+ Stem-Spuren Integration:**
  - Automatische Erkennung und saubere Gruppierung aller Einzelspuren (`Vocals`, `Drums`, `Bass`, `Other/Mix`, `Instrumental`, `Take Raw`) unter einer gemeinsamen Song-Karte in der Medien-/Player-Bibliothek.
  - Direkte Spuren-Umschaltung im Player mit 1-Klick-Download für jede einzelne Stem-Audiodatei.
  - Verhindert doppelte Song-Einträge in der Bibliothek, wenn Songs mit aktivierter Stem-Trennung generiert werden.

---

## [1.10] - 2026-11-09

### English (Primary)
- **Plenio 1.5.1 Workflow & Engine Upgrade:**
  - Upgraded `YuE2-Song.json` to the official Plenio v1.5.1 release template.
  - **Gemma 4 12B (auto) Writer:** Default writer choice set to `Gemma 4 12B (auto)`, delivering noticeably superior lyric generation, rhythmic cadence, song titles, and FLUX.2 cover art prompts with automatic fallback to ComfyUI's Gemma 4 text encoder if llama.cpp is absent.
  - **GGUF Model Tracking:** Added model metadata and download tracking for quantized Gemma 4 12B GGUF models (`gemma-4-12B-it-qat-UD-Q4_K_XL.gguf` [6.7 GB] and `gemma-4-12b-it-Q6_K.gguf` [9.8 GB]) in `server.py`.
  - **Vocal Stem Subtitle Alignment:** Default export subtitle timing (`lyrics_timing`) set to `"vocal stem"` for millisecond-exact lyrics alignment against isolated vocals.
  - **Extended Custom Lyrics Tags:** Full support for detailed section tags up to 160 characters (e.g. `[Verse - Female Choir, Call and Response delivery]`), preserving all bracketed directions, repeat markers, and custom line breaks verbatim.
  - **Dynamic Writer Fallback:** Added smart model resolution for `PlenioWriterChoice` ensuring seamless backward compatibility with existing ComfyUI setups on Plenio 1.5.0/1.4.1 (automatically selects `gemma4_e4b_it_fp8_scaled.safetensors` without errors).

### Deutsch
- **Plenio 1.5.1 Workflow & Engine Upgrade:**
  - Aktualisierung von `YuE2-Song.json` auf das offizielle Plenio v1.5.1 Release-Template.
  - **Gemma 4 12B (auto) Writer:** Neuer Standard-Writer `Gemma 4 12B (auto)` für deutlich stilsicherere, lyrisch anspruchsvollere Songtexte, treffendere Titel und stimmigere Cover-Prompts – bei unter 16 GB VRAM mit 6,7 GB sogar kleiner und speichereffizienter als das alte FP8-Modell, inklusive automatischem Fallback.
  - **GGUF Modell-Registrierung:** Erfassung der neuen quantisierten Gemma 4 12B GGUF-Modelle in `server.py` (`UD-Q4_K_XL` und `Q6_K`).
  - **Präzises Untertitel-Timing:** Standardmäßige Untertitelausrichtung (`lyrics_timing`) auf `"vocal stem"` für taktgenaue Textanzeige und Untertitelsynchronisation.
  - **Lange Abschnitts-Tags & Formatierungs-Erhalt:** Unterstützung für ausführliche Abschnittstags bis zu 160 Zeichen sowie 1:1-Erhalt aller Regieanweisungen in Klammern und Zeilenumbrüche bei eigenen Texten.
  - **Dynamische Writer-Abwärtskompatibilität:** Intelligente Modellauflösung für `PlenioWriterChoice`, die volle Abwärtskompatibilität zu bestehenden ComfyUI-Instanzen mit Plenio 1.5.0/1.4.1 garantiert (wählt automatisch `gemma4_e4b_it_fp8_scaled.safetensors` ohne Modellfehler).


---

## [1.08] - 2026-11-02

### English (Primary)
- **Settings Credits Attribution:** Added official reference and direct clickable link to the [Plenio Music Production System](https://github.com/jplenio/Plenio-Music-Production-System) repository in the Settings Copyright & Credits section.

### Deutsch
- **Plenio-Quellenverweis in den Einstellungen:** Hinzufügen des offiziellen Hinweises und anklickbaren Direktlinks auf das [Plenio Music Production System](https://github.com/jplenio/Plenio-Music-Production-System) Repository im Bereich Copyright & Danksagung.

---

## [1.07] - 2026-11-02

### English (Primary)
- **Lantern House Edition Branding:** Renamed app edition branding to *(Lantern House Edition)* across window title, header bar, and about info, while maintaining the credits to CodexMundi for their support and testing in the Settings dialog.
- **Dynamic Plenio Version Detection:** Status bar now dynamically detects the active Plenio version on the ComfyUI instance:
  - Displays Plenio v1.4.1 (1.5-ready) when connected to an existing Plenio v1.4.1 node installation.
  - Automatically displays Plenio v1.5.x once the ComfyUI custom node is updated to Plenio 1.5.0+.

### Deutsch
- **Lantern House Edition Branding:** Umbenennung des Editions-Brandings auf *(Lantern House Edition)* in Fenstertitel, Header und Infozeile, bei uneingeschränkter Beibehaltung der Danksagung an CodexMundi in den Einstellungen.
- **Dynamische Plenio-Versionserkennung:** Die Statusleiste erkennt nun automatisch die auf ComfyUI installierte Plenio-Version:
  - Zeigt Plenio v1.4.1 (1.5-ready) bei einer bestehenden Plenio v1.4.1 Installation an.
  - Schaltet automatisch auf Plenio v1.5.x um, sobald der ComfyUI-Custom-Node auf Plenio 1.5.0+ aktualisiert wird.

---

## [1.06] - 2026-11-01

### English (Primary)
- **Fix Connection Status Display:** Fixed a frontend ReferenceError where `describeRangeVal` was missing in `buildForm()`, preventing `refreshStatus()` from resolving and leaving the top bar in a persistent "Connecting..." state.
- **Immediate Live Status:** Verified immediate live connection detection (`status ok`), showing connected ComfyUI status, Plenio API v1 badge, and active GPU/VRAM statistics on launch.

### Deutsch
- **Verbindungsanzeige-Fehlerbehebung:** Korrektur eines Frontend-ReferenceErrors (`describeRangeVal` in `buildForm()`), der das Ausführen von `refreshStatus()` blockierte und den Statusbalken dauerhaft auf „Verbinde …“ / „Connecting…“ hielt.
- **Sofortige Live-Statuserkennung:** Zuverlässige Erkennung der aktiven ComfyUI-Verbindung (`status ok`) mit grünem Indikator, Plenio-API-Badge und Live-Anzeige von GPU und freiem VRAM direkt beim Start.

---

## [1.05] - 2026-11-01

### English (Primary)
- **Plenio 1.5.0 Integration & Workflow Upgrade:** Upgraded `YuE2-Song.json` to the official Plenio v1.5.0 release with 26 graph nodes and complete brief input dynamic schema.
- **Your Own Lyrics ("Eigene Songtexte"):** Added choice for lyrics source: *Written from idea below* (AI writes lyrics) or *My own, sung as written below* (sings your lyrics verbatim, preserving section tags `[Verse]`, `[Chorus]`, etc.).
- **Extended Creativity Range (0 to 200):** Creativity slider now scales up to 200 with new default set to 100 (*experimental*); includes live descriptive badges (*steady*, *restrained*, *balanced*, *varied*, *experimental*, *adventurous*) and exact sampling interpolation for YuE2 plan, take, and writer stages.
- **Style Template Autofill & 250 Templates:** Bundled all 250 official Plenio templates (`data/plenio_templates.json`), auto-populating brief text and musical parameters upon template selection, accompanied by a new *📋 Refill from Template* button.
- **Cross-Version ComfyUI Compatibility:** Added graceful handling ensuring prompts seamlessly work on ComfyUI setups running Plenio 1.4.1 as well as Plenio 1.5.0+.

### Deutsch
- **Plenio 1.5.0 Integration & Workflow-Upgrade:** Aktualisierung von `YuE2-Song.json` auf das offizielle Plenio v1.5.0 Release mit 26 Graph-Knoten und vollständiger dynamischer Brief-Schnittstelle.
- **Eigene Songtexte ("Your Own Lyrics"):** Neue Auswahlmöglichkeit für die Songtext-Quelle: *Aus der Idee unten schreiben* (KI dichtet den Text) oder *Eigener Text (wird exakt so gesungen)* (Text wird unverändert mit Abschnitten wie `[Verse]`, `[Chorus]` gesungen).
- **Erweiterter Kreativitätsbereich (0 bis 200):** Kreativitäts-Schieberegler bis 200 mit neuem Standardwert 100 (*experimentell*); inklusive interaktiver Stufenanzeige (*beständig*, *zurückhaltend*, *ausgewogen*, *abwechslungsreich*, *experimentell*, *abenteuerlustig*) und exakter Sampling-Interpolation für YuE2 Plan-, Take- und Writer-Phasen.
- **Vorlagen-Autofill & 250 Style-Templates:** Alle 250 offiziellen Plenio-Vorlagen offline gebündelt (`data/plenio_templates.json`) mit sichtbarem Ausfüllen der Briefing-Felder bei Vorlagenauswahl und neuem Button *📋 Vorlage anwenden*.
- **Versionsübergreifende ComfyUI-Kompatibilität:** Robuste Abwärts- und Aufwärtskompatibilität für ComfyUI-Instanzen mit Plenio 1.4.1 sowie 1.5.0+.

---

## [0.99] - 2026-10-31

### English (Primary)
- **Interactive In-App Changelog Viewer:** Added an expandable, collapsible changelog viewer directly inside the Settings dialog, fetching version notes on demand with styled markdown formatting and bilingual badges.
- **Plenio v1.4.1 Workflow Upgrade:** Updated `YuE2-Song.json` to the latest Plenio v1.4.1 template, including the native `PlenioLoras` node (#25) supporting up to 4 YuE2 LoRAs with adjustable strength controls.
- **Fast Export (`lyrics_timing: "the song"`):** Set default subtitle alignment to the mixed song track instead of forcing vocal stem separation, saving ~30 seconds to 2 minutes of render time per take.
- **Exact Timing Option:** Added UI toggle for optional vocal stem separation during subtitle timing (`lyrics_timing: "vocal stem"`).
- **Standalone Song Page (.html):** Added export option to generate a self-contained HTML page in the output folder containing song artwork, embedded player, full lyrics with section tags, score ABC, and generation metadata.
- **Bilingual Interface:** Added English and German localization and tooltips for all new export controls and the changelog viewer.

### Deutsch
- **Interaktiver In-App-Changelog-Viewer:** Ausklappbare Changelog-Ansicht direkt im Einstellungsmenü mit Abruf auf Knopfdruck, sauberer Markdown-Formatierung und zweisprachigen Hervorhebungen.
- **Plenio v1.4.1 Workflow-Upgrade:** Aktualisierung von `YuE2-Song.json` auf Plenio v1.4.1 inklusive nativem `PlenioLoras`-Node (#25) für bis zu 4 YuE2-LoRAs mit individuellen Stärkereglern.
- **Schnellerer Export (`lyrics_timing: "the song"`):** Standardmäßige Ausrichtung der Untertitel direkt am gemixten Song statt erzwungener Stem-Separation; spart 30s bis 2 Minuten Rechenzeit pro Take.
- **Option für exaktes Timing:** Neuer Schalter in den Export-Optionen für Gesangsspurtrennung beim Untertitel-Timing (`lyrics_timing: "vocal stem"`).
- **Autarke Song-Seite (.html):** Neuer Export-Schalter zur automatischen Erstellung einer eigenständigen HTML-Übersicht mit Cover, Player, Songtext mit Abschnitten, Notenblatt und Prompts im Ausgabeordner.
- **Zweisprachige Oberfläche:** Deutsche und englische Übersetzungen sowie Tooltips für alle neuen Export-Optionen und die Changelog-Ansicht.

---

## [0.96] - 2026-10-30

### English (Primary)
- **Advanced Video Export Studio:** Create `.mp4` music videos with 6 visualizer styles (Classic Bars, Retro Synthwave, Starfield Hyperspace, Radial Pulse, Oscilloscope, Cover Atmosphere).
- **Custom Backgrounds:** Added support for uploading and looping custom background videos (`.mp4`, `.webm`) and background images (`.png`, `.jpg`, `.webp`).
- **Aspect Ratios:** Support for 16:9 Landscape (YouTube / Desktop) and 9:16 Portrait (TikTok / YouTube Shorts / Instagram Reels).
- **Audio Clipping & Range Trimmer:** Interactive waveform range selection with draggable start/end handles to trim and loop music for video export.
- **Burn-in Subtitles:** Render synchronized lyrics directly into exported videos with customizable Windows fonts, size, timing offset, and speed adjustments.
- **Dual Video Engines:** Server Engine (ultra-fast FFmpeg) with automatic fallback to Web Engine (browser-native Canvas/WebCodecs).

### Deutsch
- **Erweitertes Video-Export-Studio:** Erstellung von `.mp4`-Musikvideos mit 6 Visualizer-Stilen (Klassische Balken, Retro Synthwave, Sternenfeld-Hyperspace, Radial-Puls, Oszilloskop, Cover-Atmosphäre).
- **Eigene Hintergründe:** Unterstützung für benutzerdefinierte Hintergrundvideos (`.mp4`, `.webm`) und Hintergrundbilder (`.png`, `.jpg`, `.webp`) mit Loop-Funktion.
- **Bildformate:** 16:9 Querformat (YouTube / Desktop) und 9:16 Hochformat (TikTok / YouTube Shorts / Instagram Reels).
- **Audio-Clip-Trimmer:** Interaktive Waveform-Bereichsauswahl mit Ziehpunkten zum flexiblen Zuschneiden von Audio für den Video-Export.
- **Eingebrannte Untertitel:** Synchrone Lyrics direkt ins Video rendern mit installierten Windows-Schriften, Schriftgrößen, Zeitversatz (+/-) und Geschwindigkeitsanpassung.
- **Zwei Video-Engines:** Schnelle Server-Engine (FFmpeg) mit automatischem Fallback auf die Web-Engine (Browser-Canvas/WebCodecs).

---

## [0.93] - 2026-10-27

### English (Primary)
- **DaVinci Resolve Subtitle Optimization:** Generates 100% non-overlapping, frame-exact `.srt` subtitles designed specifically for DaVinci Resolve timelines.
- **Bilingual Subtitle Translation:** One-click translation of generated `.srt` lyrics between English and German (EN ↔ DE).
- **Plenio Standalone Player Launcher:** Direct UI button to launch Plenio's standalone browser player (`Plenio Player.bat`).

### Deutsch
- **DaVinci Resolve Untertitel-Optimierung:** Erzeugung von 100% überlappungsfreien, schnittpräzisen `.srt`-Untertiteln speziell für DaVinci Resolve Timelines.
- **Zweisprachige Untertitel-Übersetzung:** Ein-Klick-Übersetzung generierter `.srt`-Dateien zwischen Englisch und Deutsch (DE ↔ EN).
- **Plenio Standalone Player Launcher:** Direkter Button zum Starten des externen Plenio Web-Players (`Plenio Player.bat`).

---

## [0.90] - 2026-10-26

### English (Primary)
- **Voice Swap Module (RVC / Applio):** Seamless vocal track replacement using trained RVC models via Applio.
- **Pitch & Retrieval Controls:** Adjustable pitch shifting (-24 to +24 semitones) and feature search ratio (index rate).
- **Vocal Recording Guide:** Bundled printable recording guide (`Stimmaufnahme-Vorlage-RVC.pdf`).
- **Audio HQ & 48 kHz Refine:** Integrated UniverSR high-frequency regeneration (HQ 2) and stereo cleanup (HQ 1).

### Deutsch
- **Voice Swap Modul (RVC / Applio):** Gesangsstimmen-Austausch mit trainierten RVC-Modellen über Applio.
- **Tonhöhen- & Merkmal-Steuerung:** Einstellbare Tonhöhenverschiebung (-24 bis +24 Halbtöne) und Merkmalsuchrate (Index-Rate).
- **Vocal-Aufnahmevorlage:** Beigefügter druckbarer Leitfaden (`Stimmaufnahme-Vorlage-RVC.pdf`).
- **Audio HQ & 48 kHz Refine:** Integration von UniverSR-Hochfrequenz-Regeneration (HQ 2) und Stereo-Bereinigung (HQ 1).

---

## [0.87] - 2026-10-24

### English (Primary)
- **Initial Release:** Desktop frontend for Plenio YuE2 music generation workflow.
- **thomo.ART Dark UI:** Clean, responsive studio interface with bilingual support (EN/DE).
- **Direct ComfyUI Integration:** Real-time WebSocket connection to local ComfyUI (`127.0.0.1:8188`).
- **Core Workflow:** Song briefing, lyrics generation (Gemma 4 E4B), seed management, cover art generation (FLUX.2 Klein), and stem separation (BS-RoFormer).

### Deutsch
- **Erstveröffentlichung:** Desktop-Frontend für den Plenio YuE2 Musikproduktions-Workflow.
- **thomo.ART Dark-UI:** Übersichtliche Studio-Oberfläche mit zweisprachiger Unterstützung (DE/EN).
- **Direkte ComfyUI-Anbindung:** Echtzeit-WebSocket-Verbindung zu lokalem ComfyUI (`127.0.0.1:8188`).
- **Kern-Workflow:** Song-Briefing, Textgenerierung (Gemma 4 E4B), Seed-Verwaltung, Cover-Erstellung (FLUX.2 Klein) und Stem-Trennung (BS-RoFormer).
