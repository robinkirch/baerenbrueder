# Menüs bei hohen Auflösungen (2026-11-21)

## UI-Aufbau
- UnrealScript-Menüs: UWindow (UWindow.u) + KnowWonder-Seiten in HGame.u (`FEBook`, `baseFEPage`, `FE*Page`).
- Raster 640x480 UI-Einheiten. `Root.GUIScale` = Pixel pro Einheit; `PaintClients` verschiebt den Ursprung je
  Kindfenster um `WinLeft*GUIScale` → ein zentriertes `FEBook` verschiebt Zeichnen UND Maus-Hit-Test.
- Maus: `HPConsole` rechnet `MouseX = WindowsMouseX / GUIScale`, begrenzt auf `Root.WinWidth/WinHeight`.

## Fehler und Fixes
1. **ESC-Menü unbedienbar bei 21:9**: `Root.SetScale(Root.RealWidth/640)` (HPConsole beim Anlegen und
   `FEBook.Paint` bei Auflösungswechsel) → 3440x1440: GUIScale 5.375, Root nur 268 hoch, Menü 480 hoch.
   Fix: `RealHeight/480`; FEBook-Zentrierung `0.0*(WinWidth/2-320)` → `1.0*(...)` (Original deaktiviert);
   `baseFEPage.AfterPaint` Rollover-Skalierung `SizeX/WinWidth` → `SizeY/WinHeight`.
2. **Mausspuren neben dem Menü**: D3DDrv `Lock()` löscht Bild nur bei angeforderter Bildschirmlöschung
   (Flags 2 statt 3 bei 0x10004ea8). Seitenbereiche wurden nie gelöscht. Fix: immer 3.
3. **Auflösungsliste unbedienbar**: `HPMenuOptionComboList.BeforePaint` feste Höhe 89/61,
   `ItemHeight = (WinHeight-7)/Count`, Scrollbalken versteckt. Fix: Region ab Speicher 0xAB neu
   (Scrollpos sichern, super.BeforePaint, bei > 3: Höhe 89, Zeile 27, ShowWindow, SetRange(0,Count,3),
   Scrollbalken-Geometrie; ≤ 3 wie Original). `super` setzt bei ≤ 10 Einträgen VertSB.Pos = 0 → gesichert in `ListX`.
4. **Mausrad**: UWindowComboList hat keine Mausrad-Behandlung; Mausrad = KeyEvent 236/237.
   Weg: HPConsole(UWindow).KeyEvent → FEBook.KeyEvent → curPage.KeyEvent. In FEBook.KeyEvent den Debug-Block
   (Shift+F7) ersetzt: `if (Action==1 && Key/2==118) FEOptionsPage(curPage).ResolutionCombo.List.VertSB.Scroll(float(Key*2-473))`.
5. **Launcher** (Game.exe `WFrontEndPageConfigVideo`, 0x109027f0): feste Liste 640/800/1024(/1280x1024),
   bei fehlender aktueller Auflösung Eintrag 0. Fix: Code-Cave mit EnumDisplaySettingsW.

Alle Punkte vom User getestet und bestätigt.
