# Changelog

All notable changes to **tA-MusicMaker** are documented in this file.  
*Alle nennenswerten Änderungen an **tA-MusicMaker** werden in dieser Datei dokumentiert.*

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and this project adheres to [Semantic Versioning](https://semver.org/).

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
