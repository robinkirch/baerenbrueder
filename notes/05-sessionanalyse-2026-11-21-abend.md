# Analyse Spielsitzung 2026-11-21 19:00–19:55 (Game.log, 9710 Zeilen)

Spielstand geladen → CavePainting3, ValleyOfFire (2× Neustart), VOF_Combat1/2, SalmonForest, SAL_Combat1/2,
Salmon_Run (2 Versuche). Sauberes Beenden, kein Absturz. MaxFPS=60.

## 1. Speichern per Linksklick während einer Cutscene (vom User gefunden) – behoben
- Weg: `BearHero.PlayerInput` → `HandleActionButton` → `SwipeTestSavePoint` → `SavePointUnsaved.OnSaveGame`
  (Speichersteine im Umkreis 150). `SaveBearsGame` stoppt alle Sound-Slots → Cutscene-Dialog bricht ab.
- `Touch` und `ReChecking.Tick` prüfen vorher `BearHero(Level.PlayerHeroActor).OkayToSave()`
  (PlayerWalking, PHYS_Walking, Health > 0 …), der Linksklick-Weg nicht. In Cutscenes ist der Held in `stateCutIdle`.
- Fix `patches/hgame_savefix.py`: am Anfang von `OnSaveGame` `if (!OkayToSave()) return;` (Detour; Bedingung 1:1 aus
  `Touch` kopiert). Andere Aufrufer von `OnSaveGame` gibt es nicht.
- Nebenbei: `tools/ustatements.py` korrigiert die von UELib um 1 Byte zu spät gemeldete Plattenposition bei
  erweiterten Native-Aufrufen (`61 xx`). Bestehende Patches bauen bitgleich.

## 2. Lachswanderung: dritte Luftblase nie erreicht – Ursache: FPS-abhängiges Platzen der Blasen, behoben
- Luftvorrat selbst ist korrekt zeitbasiert (`ScoreManagerSalmonRun.CountingDown.Tick`: `fCountdownTime -= fDelta`,
  jede Blase +5 s). Seitwärts-/Auf-ab-Steuerung (`AttachedToTargetController.SetOffsetAndSpeed`) ist mit DeltaTime skaliert.
- **Fehler:** `BubblePickup.stateReady.Tick` zählt Frames, in denen die Blase weniger als **0.5 Einheiten pro Frame**
  steigt (`locationCheck++`, nie zurückgesetzt), und lässt sie nach > 5 solchen Frames platzen (gedacht für Blasen, die an
  einem Hindernis hängen). Die Blase steigt mit 30 Einheiten/**s** (`BubblePickup.DoBob`: Z = 30·BubbleTime)
  → 30/FPS pro Frame: 30 FPS = 1.0 (ok), 60 FPS = 0.5 (jeder etwas kürzere Frame zählt), 144 FPS = 0.21 (jeder Frame).
  Folge: Blasen platzen 0.1–0.3 s nach Ablauf der 0.3-s-Kollisionswartezeit, statt aufzusteigen. Nur Blasen direkt
  vor Kenai sind erreichbar.
- Log: in beiden Versuchen jeweils 2 Blasengruppen eingesammelt (4 bzw. 9 Blasen, immer mehrere gleichzeitig), dann
  `SalR_Bubbles` (Luft aus). Die Blasen-Indizes reichen bis `BubblePickup535`, es entstehen und platzen also laufend Blasen.
- Fix (`patches/hgame_patches.py`, In-place, Datei-Offset 709457): Schwelle 0.5 → 0.05. Festhängende Blasen
  (Z-Delta ≈ 0) platzen weiterhin, frei steigende Blasen erst ab 600 FPS fälschlich.
- Steuerung/Maus: `AttachedToTargetController` würde seitlich `aBaseX` lesen (auch Maus-Drehung), das gilt aber nur bei
  `bLeftRight`. Laut User geht es im Lachslauf nur hoch/runter → die Mausbindung stört dort nicht.

## 3. Sammelobjekte (Frage des Users)
- **Honigwaben** (`HoneyComb` → `StatusItemHoneycomb`): Währung pro Gebiet. `CaveTrigger` (in AspenForest,
  SalmonForest, ValleyOfFire) öffnet bei ≥ 50 Waben (`NumHoneycombsNeeded=50`) eine Bonus-Höhle und zieht die 50 Waben ab,
  sonst Warnung (`BearsDialogManager.HoneyCombWarning`). Zähler wird zu Beginn von Lachswald und Tal des Feuers per
  Cutscene-Befehl `Kenai ResetHoneycombs` auf 0 gesetzt.
- **Silberne Zapfen** (`PineCone` → `StatusItemPineCone.IncrementCount`): erhöhen das **maximale Leben**
  (`HealthStatusItem.IncrementCountPotential(nUnitsPerIcon)`, ein zusätzliches Lebenssymbol). Vorkommen in denselben drei Gebieten.

## Sonstiges im Log
Keine neuen Meldungstypen gegenüber notes/04 (bekanntes Rauschen: `TriggerKodaPath bCountDown is true`, SpawnActor-
Fehlversuche, leere Texturreferenzen, CutErrors aus Original-Skripten).

## Nachtrag: Sitzung 2026-11-21 ~20:17–20:25 (Spiel durchgespielt)
- Game.log wurde von einem späteren 11-s-Start (20:28, nur Launcher) überschrieben → Analyse über Spielstand/Dateien.
  (Tipp: Game.log nach einer Sitzung sichern, bevor das Spiel erneut gestartet wird.)
- Luftblasen-Fix vom User bestätigt; Salmon_Run geschafft → `Final_Battle.unr`; `Save0.usa` ist die Level-Speicherung
  von Final_Battle (GSTATE060).
- **Story-Reihenfolge** (aus den Levelverweisen der .unr-Dateien, linear, nichts überspringbar):
  CavePainting1 → AvalancheRun → AspenForest → ASP_Combat1 → IceRun → CavePainting2 → ValleyOfFire (↔ VOF_Combat1)
  → VOF_Combat2 → CavePainting3 → SalmonForest (↔ SAL_Combat1/2) → Salmon_Run → Final_Battle.
  Alle Level kamen in den Sitzungen vor (AvalancheRun nur indirekt belegt: einziger Weg von CavePainting1 nach AspenForest).
- **Zwei Enden** (`CutScenes\FinalBattle.int` Zeilen 211/212): `If HasAllSecretCaveTotems` → `LevelLoadKodaBonus`
  (Bonuslevel, Cutscene `CS5` in CavePainting1, danach QuitGame); sonst `Kenai QuitGame` (normales Ende, Spiel wird beendet;
  kein Abspann, `RunCredits` nutzt kein Skript). Bedingung: alle **6 Geist-Totems** (`StatusItemSpiritTotems`, Hirsch,
  Streifenhörnchen, Mammut, Elch, Biber, Otter) aus der geheimen Höhle `SecretTotemCave.unr`, erreichbar über die
  `CaveTrigger` (je 50 Honigwaben) in AspenForest, SalmonForest und ValleyOfFire. Nie besucht → nicht gespielt.
