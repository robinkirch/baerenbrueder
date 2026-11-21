# Alt-Tab-Ton und Auflösungsliste (2026-11-20)

## Alt-Tab: Ton weg
Ausgangslage: User meldete nach Alt-Tab kompletten Tonverlust (Test mit OpenAL Soft, ohne FPS-Limit).

Statische Analyse (ALAudio.dll):
- `Minimize` (0x100024b0) setzt Viewport (this+0x2c) = NULL, `Restore` setzt ihn zurück.
  `Update`/`PlaySound` tun nichts bei Viewport NULL → Kandidat für dauerhaften Tonverlust.

Laufzeit-Messungen (tools/frida_logtime.py, `BB_ALTTAB` simuliert Alt+Tab per keybd_event):
- run-12: `Minimize`/`Restore` werden beim Alt-Tab **gar nicht aufgerufen**; nur `WM_DisplayChange`
  (Vollbild ↔ Desktop-Modus). Viewport bleibt gültig.
- run-13 (`BB_ALSOFTLOG`): OpenAL Soft nutzt WASAPI auf „Kopfhörer (Arctis Nova 7)“ (USB), kein
  Device-Verlust beim Moduswechsel. HRTF automatisch aktiv (Kopfhörer).
- run-14: OpenAL-Aufrufe pro Sekunde vor/nach Alt-Tab: weiterhin `alSourcePlay`, Gain > 0, keine Pause.
⇒ Engine-seitig kein Tonverlust mehr reproduzierbar. Vermutung: Ursprünglicher Fehler kam von der alten
  Creative-OpenAL-DLL oder einem anderen Wechselweg (Taskleiste/Minimieren). Manueller Test steht aus.
- **2026-11-21: User-Test manuell → Ton nach Alt-Tab weiterhin weg.** Game.log identisch zum automatischen
  Lauf (WM_DisplayChange, D3D-Gerät wird bei Rückkehr neu erstellt). Engine ruft weiter alSourcePlay mit
  Gain > 0 auf → Problem liegt nach den OpenAL-Aufrufen (Ausgabe stumm), nicht im Aufrufpfad.
- Neue Hypothese: Listener-Velocity/-Position oder Pitch wird nach dem Moduswechsel ungültig (NaN/Inf,
  z. B. Positionssprung / DeltaTime) → Doppler macht alle Quellen dauerhaft stumm.
  `frida_logtime.py` prüft jetzt alListenerfv und AL_PITCH auf ungültige Werte.
- run-18: Listener/Pitch-Werte immer gültig (Hypothese NaN **widerlegt**). Simuliertes Alt+Tab (keybd_event)
  minimiert das Fenster NICHT → kein Fehler. **Manuelles Alt-Tab des Users (18.76 s):**
  `Minimize` (Viewport → NULL) und danach `SetViewport(NULL)`, **kein Restore** → ab da keine einzige
  OpenAL-Aktivität mehr (Update/PlaySound brechen bei Viewport NULL ab). Ursprüngliche Analyse war richtig.
- Nächster Schritt: Backtraces der Aufrufer (Minimize/SetViewport/Restore) bei echtem Minimieren
  (`BB_MINIMIZE="t_min,t_restore"`, ShowWindow SW_MINIMIZE/SW_RESTORE).
- run-19 (`BB_MINIMIZE`, ShowWindow): Backtraces → Aufrufer ist `UWindowsViewport::ViewportWndProc`
  (WinDrv 0x11108ab0). Hier Reihenfolge SetViewport(NULL) → Restore(vp), Ton blieb.

### Ursache (WinDrv.dll, ViewportWndProc) – GEFUNDEN
Globale Variable `saved` @0x1111831c, Audio = Client->Engine->Audio (`[[local_18+0x28]+0x5c]`):
- WM_ACTIVATE inaktiv (0x11108e93): `saved = Audio->GetViewport()` (vt+0x94), `Audio->Minimize()` (vt+0x68)
- WM_ACTIVATE aktiv: wenn saved: `Audio->Restore(saved)` (vt+0x64), saved = 0
- WM_SIZE SIZE_MINIMIZED mit 0x0 („Forced minimization“, 0x11108fa7): `saved = Audio->GetViewport()`,
  `Audio->SetViewport(NULL)` (vt+0x60)
- WM_SIZE sonst: wenn saved: `Audio->SetViewport(saved)`, saved = 0
Win11 Alt-Tab: WM_ACTIVATE(inaktiv) speichert vp, dann WM_SIZE überschreibt saved mit NULL
(GetViewport ist nach Minimize schon NULL) → keine Wiederherstellung → dauerhaft stumm.
Fix: `patches/windrv_audio_viewport.py` – GetViewport-Aufrufe an beiden Stellen über Cave, der bei NULL
den bereits gespeicherten Wert zurückgibt. **Vom User manuell getestet: Ton bleibt nach Alt-Tab (2026-11-21).**
- `this+0x5c` im ALAudio-Subsystem wirkt wie Stumm-Schalter (Gain 0), ist aber eine Config-Property
  (kein Schreibzugriff zur Laufzeit gefunden).

## Auflösungsliste
- Menü: `FEOptionsPage.LoadVideoSettings` (HGame.u) → `ConsoleCommand("GetRes")` → Tokens bis Leerzeichen →
  Filter `IsSupportedResolution` (nur 640x480/800x600/1024x768; Software: 512x384).
- Seit FullscreenViewport 3440x1440 kam **gar kein** Eintrag mehr an (alle Logs run-04..run-15).
- D3DDrv `GetRes` (Exec-Zweig ab 0x1000885c), Laufzeit-Dump (run-16): 140 Modi, alle Format 22
  (X8R8G8B8), Grenzwerte this+0x814/0x818 = INT_MAX.
  - Sprungtabelle 0x10008d10/0x10008d18: nur Formate 23–26, 29, 30 (16 bit) werden übernommen → leer.
  - Ausgabe max. 16 eindeutige Modi (`cmp edi,0x10`).
  - Format "%ix%i" + " %ix%i" → letzter Token ohne folgendes Leerzeichen, Menü verwirft ihn.
- Fix: `patches/d3ddrv_resolutions.py` + `patches/hgame_resolutions.py`.
- run-17: Menü erhält 22 Auflösungen 640x480 … 3440x1440. Nur HGame.u nutzt `GetRes`.
- D3DDrv wird relocated geladen (teilt Wunschbasis 0x10000000 mit ALAudio) → Frida-Hooks relativ zur Basis.
