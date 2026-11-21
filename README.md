# Brother Bear (Bärenbrüder) – Windows 11 Port

**[English](#english)** · **[Deutsch](#deutsch)**

These files do not contain any Game files. Please use your one files or serch on https://archive.org/details/barenbruder for legitime files. I do not know if the files in archive.org are legit and legaly fine.
---

## English

Unofficial fixes that make the PC game **Disney's Brother Bear** (German: *Disneys Bärenbrüder*, 2003, KnowWonder,
Unreal Engine 1) run stably on Windows 10/11 (x64). The original only ran on Windows XP, and not without problems.

> **This repository contains no game files.** It only contains patch scripts that modify *your own* copy of the
> original game, plus tools and notes. The game itself is protected by copyright.

### Fixed problems

| Problem in the original | Fix | File |
|---|---|---|
| Dialogue lines overlap, cutscenes drift apart (unlimited frame rate) | FPS limit (default 60, 30/60/144 selectable) + `timeBeginPeriod(1)` | Engine.dll |
| Resolution list empty or only up to 1024×768 | All 32-bit modes, up to 64 entries | D3DDrv.dll, Game.exe (launcher) |
| Menu only offers 640/800/1024; menu too large/unusable on widescreen | Filter removed, scaled by height, centered, scrollable list + mouse wheel | HGame.u |
| Picture "zoomed in" on widescreen | Hor+ field of view | Engine.dll |
| Loading screens shifted/cut off on widescreen | Scaled by height, centered | HGame.u |
| Mouse trails next to the 4:3 menu | Always clear frame + Z buffer | D3DDrv.dll |
| Sound permanently gone after Alt+Tab | NULL viewport handled | WinDrv.dll |
| Creative OpenAL 1.0 (2003) | OpenAL Soft 1.25.2 | OpenAL32.dll |
| Frame rate only configurable via INI | "Bildrate" (frame rate) option in launcher and in-game menu | Window.dll, Game.exe, HGame.u |
| Salmon Run: air bubbles burst immediately at 60+ FPS | Frame-dependent threshold fixed | HGame.u |
| Left click at a save stone saves during cutscenes (dialogue cut off) | Added `OkayToSave()` check | HGame.u |
| Missing Koda animation in the ice slide intro | Typo `Kodz` → `Koda` | CutScenes\IceRun_Intro.int |

Technical details (causes, addresses, structures): [`notes/`](notes/) (German).

### How to patch your own game

You need the PC version of the game (2003), as the original CD or as an image (ISO) of your CD.

**Only the German version has been tested.** The patched program files contain no text (all text lives in the
`.int` language files), so other language versions most likely work as well – provided their program files are
identical. The patches check this themselves: every file is compared against a known checksum before patching. On a
mismatch the script stops instead of damaging anything. If that happens, please open an issue with your language
version and the message. Only visible difference: the new menu entry is labelled "Bildrate" in every language.

1. **Install Python:** [python.org/downloads](https://www.python.org/downloads/). Tick
   **"Add python.exe to PATH"** in the installer.
2. **Download this repository:** on GitHub *Code → Download ZIP*, then extract it, e.g. to
   `C:\Games\BrotherBear-Win11`.
3. **Copy the game files into it:** insert the CD or mount the ISO (double-click) and copy the **entire content** of
   the CD into the extracted folder. Afterwards there must be a folder `SETUP\Bears\` in it.
   Do **not** run the original setup from the CD.
4. **Download OpenAL Soft** (modern audio driver):
   [openal-soft releases](https://github.com/kcat/openal-soft/releases) → `openal-soft-1.25.2-bin.zip`, extract it.
   You need `bin\Win32\soft_oal.dll` from it.
5. **Patch:** in the extracted folder, type `cmd` into the Explorer address bar (opens a command prompt there) and run:

   ```bat
   pip install pefile
   python patches\apply_all.py --openal "C:\path\to\openal-soft-1.25.2-bin\bin\Win32\soft_oal.dll"
   ```

   The script creates the folder `game\` (a copy of `SETUP\Bears\`) and only patches this copy. The original files
   stay untouched.
6. **Play:** start `game\system\Game.exe`. The `game\` folder can be moved anywhere (create a shortcut to
   `Game.exe`). Settings and save games are stored in `%ProgramData%\Disney Interactive\Bärenbrüder\System`.

**Optional: build an installer.** With [Inno Setup 7](https://jrsoftware.org/isdl.php),
`python tools\build_dist.py --installer` creates a cleaned-up game folder `dist\Baerenbrueder\` (without backups and
developer tools) and `dist\Baerenbrueder-Win11-Setup.exe`. These files contain the complete game – please do
**not** share them publicly.

### For developers

- The UnrealScript decompiler `tools/udecomp` (.NET 10, UELib) is only needed for new bytecode patches. The existing
  patches use the cached statement boundaries in `patches/hgame_statements.json`.
- **Ghidra (optional):** reverse engineering was done with Ghidra and the
  [GhidraMCP](https://github.com/LaurieWired/GhidraMCP) bridge. To use it with Claude Code, copy
  `.mcp.json.example` to `.mcp.json` and adjust the paths to your Python installation and `bridge_mcp_ghidra.py`.

### Repository layout

| Path | Content |
|---|---|
| `patches/` | Reproducible patches (offset, original bytes, new bytes, reason) |
| `tools/` | Helper tools: UnrealScript decompiler (`udecomp`, based on UELib), package rebuilding, PE analysis, Frida scripts, packaging |
| `installer/` | Inno Setup script and readme for the game package |
| `notes/` | Reverse engineering findings and test session analyses (German) |

### License

The scripts, tools and notes in this repository are licensed under the
[GNU General Public License v3.0](LICENSE). The license does **not** apply to the game itself: its files are
protected by copyright and not part of this repository.

License texts for the bundled OpenAL Soft (LGPL) are in `patches/thirdparty/`. "Brother Bear" is a trademark of
Disney Enterprises, Inc.; this project is not affiliated with Disney or KnowWonder.

---

## Deutsch

Inoffizielle Fehlerbehebungen, damit das PC-Spiel **„Disneys Bärenbrüder“** (2003, KnowWonder, Unreal Engine 1)
unter Windows 10/11 (x64) stabil läuft. Das Original lief nur unter Windows XP und auch dort nicht fehlerfrei.

> **Dieses Repository enthält keine Spieldateien.** Es enthält nur Patch-Skripte, die eine *eigene* Kopie des
> Originalspiels anpassen, sowie Werkzeuge und Notizen. Das Spiel selbst ist urheberrechtlich geschützt.

### Behobene Probleme

| Problem im Original | Lösung | Datei |
|---|---|---|
| Dialoge überlagern sich, Zwischensequenzen laufen auseinander (unbegrenzte Bildrate) | FPS-Limit (Standard 60, 30/60/144 wählbar) + `timeBeginPeriod(1)` | Engine.dll |
| Auflösungsliste leer bzw. nur bis 1024×768 | Alle 32-Bit-Modi, bis 64 Einträge | D3DDrv.dll, Game.exe (Launcher) |
| Menü filtert auf 640/800/1024, Menü bei Breitbild zu groß/unbedienbar | Filter aus, Skalierung nach Höhe, zentriert, scrollbare Liste + Mausrad | HGame.u |
| Bild bei Breitbild „rangezoomt“ | Hor+-Sichtfeld | Engine.dll |
| Ladebildschirme bei Breitbild verschoben/abgeschnitten | Nach Höhe skaliert, zentriert | HGame.u |
| Mausspuren neben dem 4:3-Menü | Bild + Z-Puffer immer löschen | D3DDrv.dll |
| Ton nach Alt+Tab dauerhaft weg | NULL-Viewport abgefangen | WinDrv.dll |
| Creative OpenAL 1.0 (2003) | OpenAL Soft 1.25.2 | OpenAL32.dll |
| Bildrate nur per INI | Auswahl „Bildrate“ im Launcher und im Spielmenü | Window.dll, Game.exe, HGame.u |
| Lachswanderung: Luftblasen platzen ab 60 FPS sofort | Frame-abhängige Schwelle korrigiert | HGame.u |
| Linksklick am Speicherstein speichert während Zwischensequenzen (Dialog bricht ab) | `OkayToSave()`-Prüfung ergänzt | HGame.u |
| Fehlende Koda-Animation im Eisrutschen-Intro | Tippfehler `Kodz` → `Koda` | CutScenes\IceRun_Intro.int |

Technische Details (Ursachen, Adressen, Strukturen): [`notes/`](notes/).

### Anleitung: eigenes Spiel patchen

Du brauchst die PC-Version von „Disneys Bärenbrüder“ (2003), als Original-CD oder als Abbild (ISO) deiner CD.

**Getestet ist nur die deutsche Version.** Die gepatchten Programmdateien enthalten keine Texte (die stehen in den
`.int`-Sprachdateien), deshalb funktionieren andere Sprachversionen sehr wahrscheinlich auch – sofern ihre
Programmdateien identisch sind. Das prüfen die Patches selbst: Jede Datei wird vor dem Patchen per Prüfsumme mit dem
bekannten Stand verglichen. Bei Abweichung bricht das Skript ab, statt etwas zu beschädigen. In dem Fall freue ich
mich über ein Issue mit Sprachversion und Meldung. Einziger sichtbarer Unterschied: Die neue Menüzeile heißt auch in
anderen Sprachen „Bildrate“.

1. **Python installieren:** [python.org/downloads](https://www.python.org/downloads/). Im Installer
   **„Add python.exe to PATH“** ankreuzen.
2. **Dieses Repository herunterladen:** oben auf GitHub *Code → Download ZIP* und entpacken, z. B. nach
   `C:\Spiele\Baerenbrueder-Win11`.
3. **Spieldateien hineinkopieren:** CD einlegen bzw. die ISO per Doppelklick einbinden und den **gesamten Inhalt**
   der CD in den entpackten Ordner kopieren. Danach muss es dort den Ordner `SETUP\Bears\` geben.
   Das Original-Setup der CD wird **nicht** ausgeführt.
4. **OpenAL Soft herunterladen** (moderner Audiotreiber):
   [openal-soft Releases](https://github.com/kcat/openal-soft/releases) → `openal-soft-1.25.2-bin.zip` und entpacken.
   Benötigt wird daraus `bin\Win32\soft_oal.dll`.
5. **Patchen:** im entpackten Ordner in der Adresszeile des Explorers `cmd` eingeben (öffnet die Eingabeaufforderung
   dort) und ausführen:

   ```bat
   pip install pefile
   python patches\apply_all.py --openal "C:\Pfad\zu\openal-soft-1.25.2-bin\bin\Win32\soft_oal.dll"
   ```

   Das Skript legt den Ordner `game\` an (Kopie von `SETUP\Bears\`) und patcht nur diese Kopie. Die Originaldateien
   bleiben unverändert.
6. **Spielen:** `game\system\Game.exe` starten. Der Ordner `game\` kann beliebig verschoben werden
   (Verknüpfung auf `Game.exe` anlegen). Einstellungen und Spielstände liegen unter
   `%ProgramData%\Disney Interactive\Bärenbrüder\System`.

**Optional: Installer bauen.** Mit [Inno Setup 7](https://jrsoftware.org/isdl.php) erzeugt
`python tools\build_dist.py --installer` einen bereinigten Spielordner `dist\Baerenbrueder\` (ohne
Sicherungskopien und Entwicklerwerkzeuge) und `dist\Baerenbrueder-Win11-Setup.exe`. Diese Dateien enthalten das
komplette Spiel. Bitte **nicht öffentlich** weitergeben.

### Für Entwickler

- Der UnrealScript-Dekompiler `tools/udecomp` (.NET 10, UELib) wird nur für neue Bytecode-Patches gebraucht. Die
  vorhandenen Patches nutzen die zwischengespeicherten Anweisungsgrenzen in `patches/hgame_statements.json`.
- **Ghidra (optional):** Das Reverse Engineering lief mit Ghidra und der
  [GhidraMCP](https://github.com/LaurieWired/GhidraMCP)-Bridge. Für die Nutzung mit Claude Code
  `.mcp.json.example` nach `.mcp.json` kopieren und die Pfade zur eigenen Python-Installation und zu
  `bridge_mcp_ghidra.py` anpassen.

### Aufbau

| Pfad | Inhalt |
|---|---|
| `patches/` | Reproduzierbare Patches (Offset, Originalbytes, neue Bytes, Begründung) |
| `tools/` | Hilfswerkzeuge: UnrealScript-Dekompiler (`udecomp`, auf Basis von UELib), Paket-Umbau, PE-Analyse, Frida-Skripte, Paketbau |
| `installer/` | Inno-Setup-Skript und Liesmich für das Spielpaket |
| `notes/` | Erkenntnisse aus dem Reverse Engineering und Testsitzungen |

### Lizenz

Die Skripte, Werkzeuge und Notizen in diesem Repository stehen unter der
[GNU General Public License v3.0](LICENSE). Die Lizenz gilt **nicht** für das Spiel selbst: Seine Dateien sind
urheberrechtlich geschützt und nicht Teil dieses Repositorys.

Die mitgelieferten Lizenztexte für OpenAL Soft (LGPL) liegen in `patches/thirdparty/`. „Disneys Bärenbrüder“ ist eine
Marke der Disney Enterprises, Inc.; dieses Projekt steht in keiner Verbindung zu Disney oder KnowWonder.


