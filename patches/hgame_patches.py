r"""Bytecode-Patches fuer HGame.u (UnrealScript, Spiellogik/Menues).

Alle Patches sind laengenneutral (gleich viele Bytes) und pruefen vorher die Originalbytes.
Objektreferenzen im Bytecode sind FCompactIndex-codiert (Importe negativ), siehe notes\logs\HGame.refs.tsv:
  RealWidth -495 = EF 07, RealHeight -846 = CE 0D, SizeX -65 = C1 01, SizeY -84 = D4 01,
  WinWidth -102 = E6 01, WinHeight -101 = E5 01.

1. Aufloesungsliste (FEOptionsPage.IsSupportedResolution): `return false` -> `return true`
   (EX_Return EX_False 04 28 -> 04 27). Menue uebernimmt alle Modi aus `GetRes`.

2. Menue-Skalierung bei Breitbild (ESC-Menue/Startmenue unbedienbar):
   Die UI rechnet in einem 640x480-Raster; `Root.SetScale(Root.RealWidth / 640)` skaliert nur nach der
   Breite. Bei 3440x1440 -> GUIScale 5.375, Root nur 268 Einheiten hoch: das 480 hohe Menue ragt aus dem
   Bild, die Maus wird auf 268 begrenzt -> untere Buttons (z. B. Beenden) unerreichbar.
   a) HPConsole (Root anlegen) und b) FEBook.Paint (Aufloesungswechsel):
      `Root.RealWidth / 640` -> `Root.RealHeight / 480` (Breitbild: Menue passt in die Hoehe).
   c) HPConsole: FEBook-Position `0.0 * (Root.WinWidth/2 - 320)` -> `1.0 * (...)` = horizontal zentriert
      (die Zentrierung war im Original vorhanden, aber mit Faktor 0 deaktiviert).
   d) baseFEPage.AfterPaint (Rollover-Grafiken): Skalierung `Canvas.SizeX / WinWidth` ->
      `Canvas.SizeY / WinHeight` (= GUIScale, auch wenn die Seite nicht die volle Breite fuellt).
   Hinweis: Auf Bildschirmen schmaler als 4:3 (z. B. 5:4) waere das Menue etwas breiter als das Bild.

Aufruf: python patches/hgame_patches.py [quelle] [ziel]
  Standard: quelle=SETUP\Bears\system\HGame.u, ziel=game\system\HGame.u
"""
import hashlib
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
HGAME_SHA256 = "ad9eb9dfbb48dc2a7326cb7a257dab176199be0da54639d39ddbd81598be6395"

# (Datei-Offset, Kontext-Start, Kontextbytes (Original), Ersatz fuer den Kontext, Beschreibung)
PATCHES = [
    (659345, "161604270428040b", "161604270427040b",
     "IsSupportedResolution: return false -> return true"),
    (496511, "01ef07401d8002000016", "01ce0d401de001000016",
     "HPConsole: SetScale(RealWidth/640) -> SetScale(RealHeight/480)"),
    (597493, "01ef07401d8002000016", "01ce0d401de001000016",
     "FEBook.Paint: SetScale(RealWidth/640) -> SetScale(RealHeight/480)"),
    (496610, "ab1e00000000afac", "ab1e0000803fafac",
     "HPConsole: FEBook horizontal zentrieren (Faktor 0.0 -> 1.0)"),
    (289044, "01c10101e60116", "01d40101e50116",
     "baseFEPage.AfterPaint: Canvas.SizeX/WinWidth -> Canvas.SizeY/WinHeight"),
    # Lachswanderung: BubblePickup.stateReady.Tick zaehlt Frames mit (Location.Z - OldLocation.Z) < 0.5 und laesst
    # die Blase nach 6 solchen Frames platzen ("haengt an der Decke fest"). Die Blase steigt mit 30 Einheiten/s,
    # also 30/FPS pro Frame -> ab 60 FPS (0.5/Frame) zaehlt fast jeder Frame, Blasen platzen ~0.1-0.3 s nach dem
    # Erscheinen (bei 2003er ~30 FPS nie). Schwelle 0.5 -> 0.05: festhaengende Blasen (Delta ~0) platzen weiter,
    # frei steigende erst ab 600 FPS faelschlich.
    (709457, "5f3a161e0000003f16", "5f3a161ecdcc4c3d16",
     "BubblePickup.stateReady.Tick: Festhaeng-Schwelle 0.5 -> 0.05 (Luftblasen platzten bei >= 60 FPS)"),
    # 3. Combo-Liste (Aufloesung) scrollbar: HPMenuOptionComboList.BeforePaint war fuer <= 3 Eintraege gebaut
    #    (feste Hoehe 89, ItemHeight = (WinHeight-7)/Count, Scrollbalken versteckt -> bei 22 Eintraegen 3 Einheiten
    #    pro Zeile). Nach Wahl der Hintergrundgrafik wird jetzt die Elternfunktion aufgerufen:
    #    `ItemHeight = (WinHeight-7)/Count;` -> `super.BeforePaint(C, X, Y); return;` (+1 uebriges Byte EX_EndFunctionParms)
    #    UWindowComboList.BeforePaint: ItemHeight 15, max. 10 sichtbar, Scrollbalken bei mehr Eintraegen.
    #    Refs: UWindowComboList.BeforePaint -1197 = ED 12, C = 2808 (78 2B), X = 12179 (53 BE 01), Y = 12180 (54 BE 01).
    #    Laenge: Platte 18 = 18, Speicher (Objektrefs 4 Byte) 24 = 24 -> ScriptSize bleibt gueltig.
]

# ---------------------------------------------------------------------------------------------------------
# 3. Combo-Liste (Aufloesung): HPMenuOptionComboList.BeforePaint (Export 8084, Script ab Datei-Offset 627059)
#    war fuer <= 3 Eintraege gebaut: feste Hoehe 89, ItemHeight = (WinHeight-7)/Count, Scrollbalken versteckt
#    -> bei 22 Eintraegen 3 UI-Einheiten pro Zeile. Neu (ab Speicher-Offset 0xAB = Datei 627190, bis vor das
#    abschliessende `return` bei 627420; Platte 230 Bytes, Speicher 324 Bytes):
#        ListX = VertSB.Pos;                 // Scrollposition sichern (super setzt sie bei <=10 Eintraegen auf 0)
#        super.BeforePaint(C, X, Y);         // Breite, Position, Scrollbalken der Elternklasse
#        if (Count > 3) {
#            WinHeight = 89; ItemHeight = 27;            // 3 Zeilen passend zur Hintergrundgrafik
#            VertSB.ShowWindow(); VertSB.SetRange(0, Count, 3); VertSB.Pos = ListX;
#            VertSB.WinLeft = WinWidth - 15; VertSB.WinTop = 3; VertSB.WinWidth = 12;
#            VertSB.WinHeight = WinHeight - 6;
#            return;
#        }
#        WinHeight = 61; ItemHeight = (WinHeight - 7) / Count;   // kleine Listen wie im Original
#        return;
#    Rest: unerreichbares Fuellmaterial, so dass Platten- UND Speicherlaenge exakt stimmen (ScriptSize).
# ---------------------------------------------------------------------------------------------------------
COMBO_REGION = (627190, 627420)       # Datei-Offsets [start, ende)
COMBO_MEM = (0xAB, 0x1EF)             # Speicher-Offsets (aus vorhandenen Sprungzielen/ScriptSize abgeleitet)
COMBO_HEAD = bytes.fromhex("0f01f8129145af01e501402c071600702b16")   # Originalanweisung am Regionsanfang
COMBO_TAIL = bytes.fromhex("01d30501f90416040b")                      # Ende WindowToGlobal(...) + return


class Asm:
    """Minimal-Assembler fuer UE1-Bytecode: zaehlt Platten- und Speicherlaenge (Objekt-/Namensrefs = 4 Byte)."""

    def __init__(self, mem_base):
        self.items = []          # (disk_bytes, mem_len) oder ("jump", opcode, label, rest_bytes, rest_mem)
        self.labels = {}
        self.mem = mem_base

    def raw(self, disk, mem=None):
        mem = len(disk) if mem is None else mem
        self.items.append((disk, mem))
        self.mem += mem

    def ref(self, tok, compact):  # Token + Objekt-/Namensreferenz
        self.raw(bytes([tok]) + compact, 1 + 4)

    def label(self, name):
        self.labels[name] = self.mem

    def jump_if_not(self, label, cond_disk, cond_mem):
        self.items.append(("jump", 0x07, label, cond_disk, cond_mem))
        self.mem += 3 + cond_mem

    def bytes(self):
        out, mem = b"", 0
        for it in self.items:
            if it[0] == "jump":
                _, op, label, cd, cm = it
                out += bytes([op]) + self.labels[label].to_bytes(2, "little") + cd
                mem += 3 + cm
            else:
                out += it[0]
                mem += it[1]
        return out, mem


def compact(n):
    neg, v = n < 0, abs(n)
    b = [(0x80 if neg else 0) | (v & 0x3F) | (0x40 if v > 0x3F else 0)]
    v >>= 6
    while v:
        b.append((v & 0x7F) | (0x80 if v > 0x7F else 0))
        v >>= 7
    return bytes(b)


def fs(n):
    return bytes([0x40, 0x2C, n])                   # IntToFloat(IntConstByte n): Platte/Speicher 3


def f32(v):
    import struct
    return b"\x1e" + struct.pack("<f", v)          # EX_FloatConst


def build_combo_region():
    R = dict(VertSB=compact(-575), Pos=bytes.fromhex("e504"), WinHeight=compact(-101), WinWidth=compact(-102),
             WinLeft=bytes.fromhex("d305"), WinTop=bytes.fromhex("f904"), ItemHeight=compact(-1208),
             SuperBP=compact(-1197), C=compact(2808), X=compact(12179), Y=compact(12180),
             Count=compact(2800), ListX=compact(4604), ShowWindow=compact(223), SetRange=compact(340))
    assert R["ListX"] == bytes.fromhex("7c47") and R["Count"] == bytes.fromhex("702b")
    a = Asm(COMBO_MEM[0])
    LET, CTX, INST, LOCAL, END, RET, NOTHING, VFUNC, FFUNC = 0x0F, 0x19, 0x01, 0x00, 0x16, 0x04, 0x0B, 0x1B, 0x1C
    SUBF, GTI, I2F = 0xAF, 0x97, 0x40

    def vsb_member_let(member, rhs_disk, rhs_mem):            # VertSB.<member> = rhs
        a.raw(bytes([LET, CTX, INST]) + R["VertSB"] + b"\x05\x00\x04" + bytes([INST]) + member + rhs_disk,
              1 + 1 + 5 + 3 + 5 + rhs_mem)

    def vsb_call(name, args_disk, args_mem):                  # VertSB.<name>(args)
        member_mem = 5 + args_mem + 1
        a.raw(bytes([CTX, INST]) + R["VertSB"] + member_mem.to_bytes(2, "little") + b"\x00" + bytes([VFUNC]) + name
              + args_disk + bytes([END]), 1 + 5 + 3 + member_mem)

    # ListX = VertSB.Pos
    a.raw(bytes([LET, LOCAL]) + R["ListX"] + bytes([CTX, INST]) + R["VertSB"] + b"\x05\x00\x04" + bytes([INST]) + R["Pos"],
          1 + 5 + 1 + 5 + 3 + 5)
    # super.BeforePaint(C, X, Y)
    a.raw(bytes([FFUNC]) + R["SuperBP"] + bytes([LOCAL]) + R["C"] + bytes([LOCAL]) + R["X"] + bytes([LOCAL]) + R["Y"]
          + bytes([END]), 5 + 5 + 5 + 5 + 1)
    # if (Count > 3)
    a.jump_if_not("small", bytes([GTI, LOCAL]) + R["Count"] + b"\x2c\x03" + bytes([END]), 1 + 5 + 2 + 1)
    a.raw(bytes([LET, INST]) + R["WinHeight"] + fs(89), 1 + 5 + 3)           # WinHeight = 89
    a.raw(bytes([LET, INST]) + R["ItemHeight"] + b"\x2c\x1b", 1 + 5 + 2)        # ItemHeight = 27
    vsb_call(R["ShowWindow"], b"", 0)                                            # VertSB.ShowWindow()
    vsb_call(R["SetRange"], fs(0) + bytes([I2F, LOCAL]) + R["Count"] + fs(3), 3 + 1 + 5 + 3)
    vsb_member_let(R["Pos"], bytes([LOCAL]) + R["ListX"], 5)                    # VertSB.Pos = ListX
    vsb_member_let(R["WinLeft"], bytes([SUBF, INST]) + R["WinWidth"] + fs(15) + bytes([END]), 1 + 5 + 3 + 1)
    vsb_member_let(R["WinTop"], fs(3), 3)
    vsb_member_let(R["WinWidth"], fs(12), 3)
    vsb_member_let(R["WinHeight"], bytes([SUBF, INST]) + R["WinHeight"] + fs(6) + bytes([END]), 1 + 5 + 3 + 1)
    a.raw(bytes([RET, NOTHING]))
    a.label("small")
    a.raw(bytes([LET, INST]) + R["WinHeight"] + fs(61), 1 + 5 + 3)           # WinHeight = 61
    a.raw(COMBO_HEAD, 24)                                                        # ItemHeight = (WinHeight-7)/Count
    a.raw(bytes([RET, NOTHING]))

    code, mem = a.bytes()
    disk_need = COMBO_REGION[1] - COMBO_REGION[0]
    mem_need = COMBO_MEM[1] - COMBO_MEM[0]
    # Unerreichbares Fuellmaterial: Speicher-Mehrbedarf (Speicher - Platte) muss exakt ausgeglichen werden.
    #   "21 00"            EX_NameConst None        Platte 2 / Speicher 5  (+3)
    #   "WinHeight=WinHeight" (2-Byte-Refs)         Platte 7 / Speicher 11 (+4)
    #   "X = X" (3-Byte-Refs)                       Platte 9 / Speicher 11 (+2)
    #   "0B"               EX_Nothing               Platte 1 / Speicher 1  (+0)
    units = [(b"\x21\x00", 5), (bytes([LET, INST]) + R["WinHeight"] + bytes([INST]) + R["WinHeight"], 11),
             (bytes([LET, LOCAL]) + R["X"] + bytes([LOCAL]) + R["X"], 11)]
    need_diff = (mem_need - mem) - (disk_need - len(code))
    best = None
    for n4 in range(0, 4):
        for n2 in range(0, 3):
            rest = need_diff - 4 * n4 - 2 * n2
            if rest < 0 or rest % 3:
                continue
            n3 = rest // 3
            disk = 2 * n3 + 7 * n4 + 9 * n2
            if best is None or disk < best[0]:
                best = (disk, n3, n4, n2)
    if best is None or len(code) + best[0] > disk_need:
        sys.exit(f"Combo-Region passt nicht: Code {len(code)}/{disk_need} Platte, {mem}/{mem_need} Speicher")
    _, n3, n4, n2 = best
    for (u, um), n in zip(units, (n3, n4, n2)):
        code += u * n
        mem += um * n
    code += bytes([NOTHING]) * (disk_need - len(code))
    return code


# ---------------------------------------------------------------------------------------------------------
# 4. Mausrad in der Aufloesungsliste: UWindowComboList hat keine Mausrad-Behandlung (KeyDown 236/237 laeuft
#    ins Leere). Jede Taste erreicht zuerst FEBook.KeyEvent (Export 8182, Script ab Datei-Offset 640133).
#    Dort steht ein Entwickler-Debugschalter (Shift+F7: bDebugMode umschalten), Speicher 0x2A..0xA4,
#    Datei [640163, 640254). Ersetzt durch:
#        if (Action == 1 && Key / 2 == 118)          // nur IK_MouseWheelUp (236) / IK_MouseWheelDown (237)
#            FEOptionsPage(curPage).ResolutionCombo.List.VertSB.Scroll(float(Key * 2 - 473));   // -1 / +1
#    danach ausfuehrbares, harmloses Fuellmaterial; Ablauf faellt in den Originalcode (ab 0xA4) durch.
#    Auf anderen Seiten liefert der Cast None -> Aufruf entfaellt.
# ---------------------------------------------------------------------------------------------------------
WHEEL_REGION = (640163, 640254)
WHEEL_MEM = (0x2A, 0xA4)
WHEEL_HEAD = bytes.fromhex("07a400829a3b00431b2616180b009a3b00461b2c761616")   # if (Action==1 && Key==118)
WHEEL_NEXT = bytes.fromhex("07ba0077")                                        # naechste Anweisung (0xA4)


def build_wheel_region():
    LET, CTX, INST, LOCAL, END, VFUNC = 0x0F, 0x19, 0x01, 0x00, 0x16, 0x1B
    R = dict(Key=compact(1734), Action=compact(1731), curPage=compact(78), FEOptionsPage=compact(2415),
             ResolutionCombo=compact(304), List=compact(-471), VertSB=compact(-575), Scroll=compact(1619),
             WinHeight=compact(-101))
    assert R["Key"] == bytes.fromhex("461b") and R["Action"] == bytes.fromhex("431b")
    assert R["curPage"] == bytes.fromhex("4e01")
    a = Asm(WHEEL_MEM[0])
    # Bedingung: (Action == 1) && (Key / 2 == 118)
    op1_d = bytes([0x9A, 0x3B, LOCAL]) + R["Action"] + b"\x26" + bytes([END])          # Action == 1
    op1_m = 1 + 1 + 5 + 1 + 1
    op2_d = bytes([0x9A, 0x91, 0x3B, LOCAL]) + R["Key"] + b"\x2c\x02" + bytes([END]) + b"\x2c\x76" + bytes([END])
    op2_m = 1 + 1 + 1 + 5 + 2 + 1 + 2 + 1
    cond_d = b"\x82" + op1_d + b"\x18" + (op2_m + 1).to_bytes(2, "little") + op2_d + bytes([END])
    cond_m = 1 + op1_m + 3 + op2_m + 1
    a.jump_if_not("end", cond_d, cond_m)
    # FEOptionsPage(curPage).ResolutionCombo.List.VertSB.Scroll(float(Key*2 - 473))
    obj_d = b"\x2e" + R["FEOptionsPage"] + bytes([INST]) + R["curPage"]
    obj_m = 1 + 4 + 5
    for prop in ("ResolutionCombo", "List", "VertSB"):
        obj_d = bytes([CTX]) + obj_d + b"\x05\x00\x04" + bytes([INST]) + R[prop]
        obj_m = 1 + obj_m + 3 + 5
    arg_d = bytes([0x40, 0x93, 0x90, 0x3B, LOCAL]) + R["Key"] + b"\x2c\x02" + bytes([END]) \
        + b"\x1d" + (473).to_bytes(4, "little") + bytes([END])
    arg_m = 1 + 1 + 1 + 1 + 5 + 2 + 1 + 5 + 1
    member_m = 5 + arg_m + 1
    a.raw(bytes([CTX]) + obj_d + member_m.to_bytes(2, "little") + b"\x00" + bytes([VFUNC]) + R["Scroll"]
          + arg_d + bytes([END]), 1 + obj_m + 3 + member_m)
    a.labels["end"] = WHEEL_MEM[1]          # Sprungziel: Regionsende = naechste Originalanweisung
    code, mem = a.bytes()
    disk_need, mem_need = WHEEL_REGION[1] - WHEEL_REGION[0], WHEEL_MEM[1] - WHEEL_MEM[0]
    # Ausfuehrbares Fuellmaterial: "21 00" (NameConst None, 2/5) und "WinHeight = WinHeight" (7/11), Rest EX_Nothing
    units = [(b"\x21\x00", 2, 5), (bytes([LET, INST]) + R["WinHeight"] + bytes([INST]) + R["WinHeight"], 7, 11)]
    need = (mem_need - mem) - (disk_need - len(code))
    for n4 in range(0, 6):
        rest = need - 4 * n4
        if rest >= 0 and rest % 3 == 0 and len(code) + 2 * (rest // 3) + 7 * n4 <= disk_need:
            code += units[0][0] * (rest // 3) + units[1][0] * n4
            mem += 5 * (rest // 3) + 11 * n4
            break
    else:
        sys.exit(f"Mausrad-Region passt nicht: Code {len(code)}/{disk_need}, {mem}/{mem_need}")
    code += b"\x0b" * (disk_need - len(code))
    return code


def main():
    src = Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT / "SETUP" / "Bears" / "system" / "HGame.u"
    dst = Path(sys.argv[2]) if len(sys.argv) > 2 else ROOT / "game" / "system" / "HGame.u"
    data = bytearray(src.read_bytes())
    if hashlib.sha256(data).hexdigest() != HGAME_SHA256:
        sys.exit(f"{src} ist nicht die Original-HGame.u")
    for off, old, new, desc in PATCHES:
        old_b, new_b = bytes.fromhex(old), bytes.fromhex(new)
        assert len(old_b) == len(new_b), desc
        if bytes(data[off:off + len(old_b)]) != old_b:
            sys.exit(f"Bytecode stimmt nicht bei {off} ({desc})")
        data[off:off + len(new_b)] = new_b
        print(f"  {off}: {desc}")
    # Combo-Liste: ganze Region neu
    s, e = COMBO_REGION
    if bytes(data[s:s + len(COMBO_HEAD)]) != COMBO_HEAD or bytes(data[e - 7:e + 2]) != COMBO_TAIL:
        sys.exit("Combo-Region: Originalbytes stimmen nicht")
    region = build_combo_region()
    assert len(region) == e - s
    data[s:e] = region
    print(f"  {s}: HPMenuOptionComboList.BeforePaint: 3 sichtbare Zeilen + Scrollbalken ({len(region)} Bytes)")
    # Mausrad in der Aufloesungsliste
    s, e = WHEEL_REGION
    if bytes(data[s:s + len(WHEEL_HEAD)]) != WHEEL_HEAD or bytes(data[e:e + len(WHEEL_NEXT)]) != WHEEL_NEXT:
        sys.exit("Mausrad-Region: Originalbytes stimmen nicht")
    region = build_wheel_region()
    assert len(region) == e - s
    data[s:e] = region
    print(f"  {s}: FEBook.KeyEvent: Mausrad scrollt Aufloesungsliste (statt Debug-Schalter Shift+F7)")
    # Neue Zeile "Bildrate" (vergroessert Funktionen -> Paket-Umbau, deshalb zuletzt)
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    import hgame_fpsrow
    import hgame_loadscreen
    from upkg import Package
    pk = Package(bytes(data))
    repl = hgame_fpsrow.collect(pk)
    print("  FEOptionsPage: neue Zeile 'Bildrate' (Created/LoadVideoSettings/Notify/ResetToDefaults/HideWindow)")
    repl.update(hgame_loadscreen.collect(pk))
    print("  Ladebildschirme: baseConsole/CutSceneManager.ScaleAndDraw zentriert und nach Hoehe skaliert")
    import hgame_savefix
    repl.update(hgame_savefix.collect(pk))
    print("  SavePointUnsaved.OnSaveGame: Speichern nur wenn OkayToSave() (nicht in Cutscenes)")
    data = bytearray(pk.build(repl))
    orig_copy = dst.with_name(dst.name + ".orig")
    if dst.exists() and not orig_copy.exists():
        shutil.copy2(dst, orig_copy)
    dst.write_bytes(data)
    print(f"HGame.u gepatcht ({len(PATCHES)} Aenderungen)")


if __name__ == "__main__":
    main()
