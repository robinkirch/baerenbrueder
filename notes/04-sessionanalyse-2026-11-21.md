# Analyse Spielsitzung 2026-11-21 13:42–14:07 (Game.log, 2991 Zeilen)

Ein Kapitel + Zeitrennen (IceRun), Levels: CavePainting1/2, Asp_combat1, Icerun, ValleyOfFire.
Sauberes Beenden, kein Absturz. Ladezeiten 0.2–0.7 s.

## Ergebnis: keine Portierungsfehler gefunden
Alle Meldungen stammen aus Original-Daten/-Skripten (würden auch unter XP auftreten):

| Anzahl | Meldung | Bewertung |
|---|---|---|
| 159 | `SpawnActor failed because Koda will not fit in location` | Normal: FancySpawn probiert Positionen durch, bis Koda passt |
| 33+33 | `Failed to load 'NULL'` / `Texture None.None` | Leere Texturreferenzen in Leveldaten, harmlos |
| 5+5 | Paket `HPN_Menu` / `HPNBeanCounter` fehlt | Überbleibsel der Harry-Potter-Engine, nicht benötigt |
| 5 | Sound `AllDialog.pc_ken_KenaiEmotes_8` fehlt | Fehlende Sprachdatei im Original (ein Kenai-Ausruf bleibt stumm) |
| ~150 | `CutError ... hasnt finished yet` | Design-Rauschen (asynchrone `*`-Befehle), siehe notes/01 |
| 19 | `CutError: Error blank cue` | Skript-Unsauberkeit im Original, ohne sichtbare Folgen |
| 6 | `Error getting tiger golden totem status item` | Abfrage ohne Tiger-Totem, harmlos |
| 2 | `CS2AfterIce`: `Failed to find Rutt` | Rutt ist in dieser Szene nicht im Level; Original |
| 1 | **`IceRun_Intro`: `Failed to find Kodz`** | **Tippfehler im Original-Skript** (`CutScenes\IceRun_Intro.int` Zeile 72: `Kodz Animate iceslideRight` statt `Koda`) → eine Rutsch-Animation von Koda im Intro des Zeitrennens fehlt. Behoben: `patches/cutscene_fixes.py`. |
| 3+2 | `missing bone/animation link for lWingTip/lWing` | Modell-Daten (Vogel/Adler), Original |
| je 1 | `Could not load Persistent Actor file ..._pa.usa` | Normal beim ersten Betreten eines Levels |
| je 2 | `Failed to find SmartStart from:...` | Normal, Fallback auf Standard-Startpunkt |

## Nachtrag: Sitzung 2026-11-21 17:01–17:09 (850 Zeilen)
Spielstand geladen (Slot 1, GSTATE020) → Valley of Fire, Cutscenes VOF_KodaWarning, VOF_SteamJetFlyOver,
VOF_RockFall, VOF_CamShake1, VOF_CutToDenahi1, VOF_RockPillarFall, VOF_CrowTotem1. Sauberes Beenden.
- Keine neuen Meldungstypen. Warnungen nur bekannte (KenaiEmotes_8, leere Texturreferenzen).
- 11x `CutError: Trying to issue command to BearsCam when actor is captured by: None` aus einer namenlosen
  Level-Cutscene (`Save0.CutSceneN`): Skript spricht die Kamera an, ohne sie vorher zu „capturen“; der Befehl wird
  trotzdem ausgeführt. Bereits in der ersten Sitzung (1x, ValleyOfFire) aufgetreten → Original-Skript, kein Port-Fehler.
- VOF_CrowTotem1 nutzt `BaseCam FOV Angle=110` → läuft über die Hor+-Korrektur, keine Auffälligkeiten im Log.
- IceRun-Intro (Kodz-Fix) und Ladebildschirm beim Levelwechsel kamen in dieser Sitzung nicht vor.
