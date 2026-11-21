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

## Selbst bauen

Voraussetzungen: Windows, Python 3 mit `pefile` (`pip install pefile`), eine Original-CD/ISO des Spiels,
[OpenAL Soft 1.25.2](https://github.com/kcat/openal-soft/releases) (`bin\Win32\soft_oal.dll`) und für den
Installer [Inno Setup 6](https://jrsoftware.org/isdl.php).

1. Inhalt der Original-CD in das Repository-Verzeichnis kopieren (es muss `SETUP\Bears\` geben).
2. `SETUP\Bears\` nach `game\` kopieren und `soft_oal.dll` als `game\system\OpenAL32.dll` ablegen.
3. Patches anwenden: `python patches/apply_all.py` (prüft die Originaldateien, arbeitet immer von `SETUP\Bears\` aus).
4. Paket bauen: `python tools/build_dist.py --installer`
   → `dist\Baerenbrueder\` (spielbarer Ordner) und `dist\Baerenbrueder-Win11-Setup.exe`.

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
