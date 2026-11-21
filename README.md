# Bärenbrüder – Windows-11-Port

Inoffizielle Fehlerbehebungen, damit das PC-Spiel **„Disneys Bärenbrüder“** (2003, KnowWonder, Unreal Engine 1)
unter Windows 10/11 (x64) stabil läuft. Das Original lief nur unter Windows XP und auch dort nicht fehlerfrei.

> **Dieses Repository enthält keine Spieldateien.** Es enthält nur Patch-Skripte, die eine *eigene* Kopie des
> Originalspiels anpassen, sowie Werkzeuge und Notizen. Das Spiel selbst ist urheberrechtlich geschützt.

## Behobene Probleme

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

Details zu Ursachen und Adressen: [`CLAUDE.md`](CLAUDE.md) und [`notes/`](notes/).

## Anleitung: eigenes Spiel patchen

Du brauchst die **deutsche PC-Version** von „Disneys Bärenbrüder“ (2003), als Original-CD oder als Abbild (ISO)
deiner CD. Andere Sprachversionen werden nicht unterstützt: Die Patches prüfen jede Datei per Prüfsumme und brechen
bei Abweichungen ab, statt etwas kaputt zu machen.

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

Für Entwickler: Der UnrealScript-Dekompiler `tools/udecomp` (.NET 10, UELib) wird nur für neue Bytecode-Patches
gebraucht. Die vorhandenen Patches nutzen die zwischengespeicherten Anweisungsgrenzen in
`patches/hgame_statements.json`.

## Aufbau

| Pfad | Inhalt |
|---|---|
| `patches/` | Reproduzierbare Patches (Offset, Originalbytes, neue Bytes, Begründung) |
| `tools/` | Hilfswerkzeuge: UnrealScript-Dekompiler (`udecomp`, auf Basis von UELib), Paket-Umbau, PE-Analyse, Frida-Skripte, Paketbau |
| `installer/` | Inno-Setup-Skript und Liesmich für das Spielpaket |
| `notes/` | Erkenntnisse aus dem Reverse Engineering und Testsitzungen |

## Lizenz

Die eigenen Skripte und Notizen in diesem Repository: noch festzulegen. Mitgelieferte Lizenztexte für OpenAL Soft
(LGPL) liegen in `patches/thirdparty/`. „Disneys Bärenbrüder“ ist eine Marke der Disney Enterprises, Inc.; dieses
Projekt steht in keiner Verbindung zu Disney oder KnowWonder.
