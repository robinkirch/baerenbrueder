# Disneys Bärenbrüder – Windows-11-Fassung

Inoffizielle Anpassung des PC-Spiels von 2003 an Windows 10/11. Das Originalspiel lief nur unter Windows XP und
auch dort nicht fehlerfrei.

## Starten

`system\Game.exe` starten (bzw. die Verknüpfung im Startmenü). Es öffnet sich zuerst der Launcher mit
Auflösung und Bildrate, danach das Spiel.

Kein DirectX-Setup und kein Original-Installationsprogramm nötig. Einstellungen und Spielstände liegen unter
`%ProgramData%\Disney Interactive\Bärenbrüder\System`.

## Was wurde behoben

- **Bildrate begrenzt** (Standard 60, wählbar 30 / 60 / 144 im Launcher und im Spielmenü) – vorher liefen Dialoge
  und Zwischensequenzen bei hohen Bildraten auseinander
- **Alle Auflösungen inkl. Breitbild** wählbar (Launcher und Spielmenü); Bild bei Breitbild nicht mehr
  „rangezoomt“ (Hor+-Sichtfeld)
- **Menüs und Ladebildschirme** bei Breitbild zentriert und richtig skaliert, keine Mausspuren neben dem Menü,
  Auflösungsliste scrollbar (auch per Mausrad)
- **Ton** bleibt nach Alt+Tab erhalten; moderner Audiotreiber (OpenAL Soft) statt Creative OpenAL von 2003
- **Maus dreht die Figur** (Standardbelegung)
- **Lachswanderung:** Luftblasen platzen nicht mehr sofort
- **Speichersteine** reagieren während Zwischensequenzen nicht mehr auf Linksklick (der Dialog brach ab)
- Tippfehler im Skript des Eisrutschen-Intros behoben (fehlende Animation)

## Einstellungen

Die Bildrate lässt sich auch direkt einstellen: `Game.ini`, Abschnitt `[Engine.GameEngine]`, `MaxFPS=20…240`
(empfohlen 60; über ca. 200 FPS treten Fehler im Original-Spielcode auf).

## Gut zu wissen

- **Honigwaben** öffnen ab 50 Stück den Eingang zu einer geheimen Höhle (Espenwald, Lachswald, Tal des Feuers).
- Wer dort alle **6 Geist-Totems** findet, erhält am Ende ein **Bonuslevel**.
- **Silberne Zapfen** erhöhen das maximale Leben.
- Gespeichert wird automatisch an Speichersteinen und bei Levelwechseln.

## Mitgelieferte Fremdsoftware

- [OpenAL Soft](https://github.com/kcat/openal-soft) 1.25.2 (`system\OpenAL32.dll`), LGPL –
  Lizenz: `Lizenzen\OpenAL-Soft\COPYING`
