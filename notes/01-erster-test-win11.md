# Erster Test unter Windows 11 (2026-11-20)

System: Ryzen (16 Threads, ~3.8 GHz), AMD Radeon RX 7900 XT, Monitor 3440x1440 @ 144 Hz.
Start aus `game\system\Game.exe` ohne Admin → Spiel startet, Intro-Cutscene läuft.

Logs/INIs liegen NICHT im Spielordner, sondern in
`C:\ProgramData\Disney Interactive\Bärenbrüder\System\` (Game.log, Detected.log, Game.ini, User.ini).

## Beobachtete Probleme
1. **Auflösung max. 1024x768** im Optionsmenü.
   - Log: `ScriptLog: Adding to our ResolutionCombo:640x480 / 800x600 / 1024x768`
   - Kommt aus UnrealScript (Optionsseite `FEAdvOptionsPage`, vermutlich `HGame.u`), nicht aus D3DDrv.
   - Start-Modus laut Log: `Best-match display mode: 640x480x32@59`.
2. **Cutscene zu schnell, Audio-Cues überlagern sich.**
   - Log, wiederholt: `CutError: Trying to issue command to:CavePainting1.Rutt1 when previous CutCommand hasnt finished yet`
   - Hypothese: ungebremste Framerate (`UseVSync=False`, kein FPS-Limit in UE1 v433) → Timing/DeltaTime-Probleme.
     Alternative: Zeitmessung über `rdtsc` (`CPU Speed=3792 MHz` wird korrekt gemessen, also eher unwahrscheinlich).

## Weitere Auffälligkeiten
- `Init: Version: 433`, `Detected: Windows NT 6.2` (Windows-Kompatibilitäts-Shim, normal).
- Speicher wird auf 2 GB gekappt angezeigt (kein Fehler).
- `joyGetDevCaps failed` (harmlos).

## Experiment 1 (Game.ini, Original gesichert als Game.ini.orig)
- `[WinDrv.WindowsClient] FullscreenViewportX/Y = 3440x1440`
- `[D3DDrv.D3DRenderDevice] UseVSync=True`
Ergebnis: Spiel startet in 3440x1440@60 (`Best-match display mode: 3440x1440x32@60`).
- Ingame-Menü (ESC) skaliert nicht mit, Buttons (z. B. Exit) nicht klickbar.
- Audio-Überlagerung und CutErrors unverändert → Framerate ist NICHT die Hauptursache.

## Analyse Audio / Cutscenes (Ghidra, Engine.dll)
- `AActor::execGetSoundDuration` (0x103daac0) → `USound::GetDuration` (0x1030ff40, gecacht in `this+0x68`)
  → `FSoundData::GetPeriod` (0x1034b430). Unterscheidet Formate per FName:
  - `BIK`: `BinkOpen(data, 0x4000000)` + `BinkGetSummary` → `FrameRateDiv * TotalFrames / FrameRate`
  - `WAV`: `dataSize * 8 / (rate * bits * channels)`
  - `PS2`: erste 4 Bytes der Daten = Dauer als float
- Dialoge (`sounds\AllDialog.uax`, 35 MB) sind **Bink-Audio** (764 BIK-Einträge). Berechnung sieht korrekt aus.
- `ALAudio.dll` importiert 27 Standard-OpenAL-Funktionen (u. a. `alGetSourcei` für Source-State),
  keine Sonderimporte. Mitgelieferte `OpenAL32.dll` = Creative OpenAL 1.0 (2003, DirectSound3D/EAX).
  DS3D-Hardware gibt es seit Vista nicht mehr → Verdacht: falscher Source-State / Wiedergabe-Status.

## Experiment 2: OpenAL Soft
- `game\system\OpenAL32.dll` ersetzt durch OpenAL Soft 1.25.2 (`bin\Win32\soft_oal.dll`, umbenannt).
  Original als `OpenAL32.dll.orig` gesichert.
Ergebnis: nicht dauerhaft behoben. Überlagerung mal ja, mal nein; Kamera springt teils („spult vor“);
nach Alt-Tab und Rückkehr ist der Sound komplett weg.

## Analyse Cutscene-System (UnrealScript, dekompiliert mit tools\udecomp)
- Dekompilate: `notes\uc\HGame\*.uc`, `notes\uc\Engine\*.uc`. **Engine.u enthält Original-Quelltext**
  (`notes\uc\Engine\*.ScriptText.txt`), HGame.u nur Bytecode.
- Cutscene-Skripte sind INI-artige Dateien: `system\CutScenes\<Name>.int` (Threads, `line_N=`).
- `CutError ... previous CutCommand hasnt finished yet` ist **Design-Rauschen**: Befehle mit `*` laufen
  asynchron weiter (z. B. `Rutt WalkTo ... *RuttDoneWalking`, danach sofort `Rutt Say ...`). Kein Bug.
- `Actor.CutCommand_Say` (Engine.u): spielt Sound und startet `TimedCue` mit `GetSoundDuration + 0.5 s`.
  Erst danach kommt der Cue → nächste Zeile / Kamera-Thread (`WaitFor PaintingN`).
  ⇒ Die Engine wartet NICHT auf das echte Sound-Ende. Läuft die Wiedergabe länger als berechnet
  (Stocken, verzögerter Start, Streaming-Unterlauf), überlappen die Zeilen und Kamera-Flüge werden abgebrochen.
- Verdacht: Streaming in `ALAudio.dll` (`alSourceQueueBuffers`/`alSourceUnqueueBuffers`, `alGetSourcei`)
  ist auf modernem Windows fragil; nach Fokusverlust wird die Wiedergabe nicht wieder aufgenommen.
  → widerlegt für Dialoge: Bink-Dialoge werden in `RegisterSound` komplett dekodiert, nicht gestreamt.

## Alt-Tab: Sound dauerhaft weg (Ursache gefunden, ALAudio.dll)
- `UALAudioSubsystem::Minimize` (0x100024b0) setzt `Viewport (this+0x2c) = NULL`.
- `Restore` (0x100024c0) setzt ihn zurück. `Update` (0x100052f0) und `PlaySound` (0x10006af0) tun nichts,
  solange Viewport NULL ist → ohne Restore-Aufruf bleibt der Ton für immer stumm.
- Offen: Wer ruft Minimize/Restore (WinDrv.dll)? Vermutlich kommt Restore unter Win11 nicht an.

## Messungen mit Frida (tools/frida_logtime.py, Logs in notes\logs\)
- run-04: Dialogstarts vs. echte Dauer (tools/analyze_dialog_timing.py). Stillstehende Dialoge:
  Abstand exakt Dauer+0.5 s (korrekt). Bei Kamerafahrten/Wandmalereien starten Folgezeilen viel zu früh,
  selbst `Sleep 1.0` dauerte < 1 s real. Faktor ca. 1.5 schneller.
- run-05: `GetSoundDuration` liefert korrekte Werte (= Bink-Header). Dateien/Längen sind NICHT die Ursache.
- Bink-Dauern aller 757 Dialoge = echte Audiodauer (tools/bink_durations.py), 22050 Hz mono, 15 fps.
⇒ **Spielzeit läuft zeitweise schneller als Echtzeit.**

## Hypothese Zeitmessung (noch zu beweisen)
- `appSeconds` = rdtsc * `GSecondsPerCycle` (Core.dll exportiert `GSecondsPerCycle` als **float**), Ergebnis `FTime`.
- D3D8 `CreateDevice` ohne `D3DCREATE_FPU_PRESERVE` schaltet x87 auf Single Precision.
- Uptime des Test-PCs 86.5 h (Fast Startup aktiv) → float-Auflösung ~31 ms > Frame (16.7 ms bei 60 Hz).
  Quantisierte Deltas + Mindest-Delta-Clamp in der Engine würden Spielzeit beschleunigen.
- Nächster Test: Tick-Hooks (`UGameEngine::Tick`, `ULevel::Tick`) summieren DeltaSeconds pro Echtzeit-Sekunde.
  → **widerlegt** (run-06): gameSum ≈ 1.00 s pro Echtzeit-Sekunde. Zeitmessung ist korrekt.

## Ursache Dialog-Überlagerung: unbegrenzte Framerate (BEWIESEN)
- run-06: Spiel läuft mit 150–1600 FPS, `UseVSync=True` wirkt nicht.
  Stillstehende Dialoge (~150–190 FPS) korrekt; Wandmalerei-Szenen (950–1600 FPS) massiv zu früh.
- run-07 mit Frida-FPS-Limiter 60: **alle** Dialogzeilen exakt Dauer+0.52 s, keine Überlagerung.
- Game.exe Hauptschleife (FUN_10905f3a): `appSleep` nur wenn `Engine->GetMaxTickRate() > 0`.
- `UGameEngine::GetMaxTickRate` (0x1035c1c0): Server → NetServerMaxTickRate (10..120), Netz-Client →
  NetSpeed/64, **Einzelspieler → 0.0** (`fld [0x10426c78]` bei 0x1035c366) = unbegrenzt.
- Fix: `patches/engine_fps_limit.py` → Einzelspieler-Limit 60 FPS (float in .rdata-Slack, fld umgebogen).
- Offen: Warum genau Say/Talk bei hohen FPS vorzeitig enden (Script-Ebene), und warum VSync wirkungslos ist (D3DDrv).
  VSync wird laut User nicht benötigt.

## FPS-Limit konfigurierbar (patches/engine_maxfps.py, ersetzt engine_fps_limit.py)
- run-08: Engine-Limit 144 ohne Timer-Auflösung → real nur ~64 FPS: `appSleep` → `Sleep()` hat ohne
  `timeBeginPeriod(1)` ~15.6 ms Auflösung. Betraf auch den ersten 60er-Patch (~64 statt 60).
- run-09: echte 144 FPS (Frida mit timeBeginPeriod) → alle Dialogzeilen exakt. 144 ist sicher (für Intro).
- Neuer Patch: jmp am Anfang von GetMaxTickRate → Code-Cave (hinter .text, positionsunabhängig) liest einmalig
  `[Engine.GameEngine] MaxFPS` via `GConfig->GetFloat` (vtable +8, verifiziert über GetStr +0x14 in Game.exe),
  klemmt 20..240 (sonst 60) und ruft `timeBeginPeriod(1)` über Core `appGetDllHandle`/`appGetDllExport`
  (relativ zum Import `appFailAssert`). Wert/Flag im BSS-Rest von .data.
- run-10: MaxFPS=144 → 140 FPS (137–145). run-11: MaxFPS=60 → 59.6 FPS.
