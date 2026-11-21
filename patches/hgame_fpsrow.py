r"""Neue Zeile "Bildrate" (30/60/144 FPS) im Optionsmenue (HGame.u, Klasse FEOptionsPage).

Technik ("Detour" + Umlagerung):
  - In jeder betroffenen Funktion wird eine vorhandene Anweisung S durch `EX_Jump <Funktionsende>` ersetzt
    (Rest von S: unerreichbares Fuellmaterial mit exakt gleicher Platten- und Speicherlaenge).
  - Am Funktionsende wird neuer Code + Kopie von S + `EX_Jump <hinter S>` angehaengt; ScriptSize waechst.
    Kein vorhandenes Sprungziel verschiebt sich.
  - Die vergroesserten Funktionen werden mit tools/upkg.py hinter die Objektdaten verlagert (Texturen etc.
    mit absoluten Offsets bleiben unberuehrt).
Variablen: MusicVolumeLoText (Beschriftung) und MusicVolumeHiText (Auswahlliste) werden mitbenutzt; sie werden
im Original nur beim Anlegen verwendet. Die Werte laufen ueber die Engine-Konsolenbefehle MAXFPS/GETMAXFPS
(patches/engine_maxfps.py).

  Created:            nach "Helligkeit" Beschriftung "Bildrate" + Auswahlliste anlegen (Kopie der Farbtiefe-Zeile)
  LoadVideoSettings:  Clear; AddItem 30/60/144 FPS; SetValue(GETMAXFPS)
  Notify:             bei Aenderung (E==1) der Liste: ConsoleCommand("MAXFPS " $ GetValue2())
  ResetToDefaults:    ConsoleCommand("MAXFPS 60")
  HideWindow:         Liste zuklappen
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "tools"))
from upkg import Package, parse_function, rebuild_function, write_ci  # noqa: E402
from ustatements import statements  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
ORIG = str(ROOT / "SETUP" / "Bears" / "system" / "HGame.u")

# Referenzen (FCompactIndex, aus Original-Bytecode abgelesen)
LO_TEXT = bytes.fromhex("6e21")      # MusicVolumeLoText (Export 2158) -> Beschriftung
HI_TEXT = bytes.fromhex("6921")      # MusicVolumeHiText (Export 2153) -> Auswahlliste
CD_LABEL = bytes.fromhex("6c22")     # ColorDepthLabel
CD_COMBO = bytes.fromhex("5404")     # ColorDepthCombo
GET_PLAYER = bytes.fromhex("1ccc0116")   # GetPlayerOwner()
N_CONSOLE, N_SETTEXT, N_ADDITEM, N_SETVALUE, N_CLEAR, N_GETVALUE2 = (
    bytes.fromhex(x) for x in ("22", "31", "5504", "5102", "560d", "7b19"))   # Namen als FCompactIndex
L_CURDEPTH = bytes.fromhex("4434")   # LoadVideoSettings: local CurrentDepth
L_C, L_E = bytes.fromhex("7033"), bytes.fromhex("7b33")   # Notify(C, E)
FPS_VALUES = ("30", "60", "144")


def sconst(s):
    b = s.encode("latin-1") + b"\0"
    return b"\x1f" + b, 1 + len(b)


def swap(raw, old, new):
    """Objektreferenz `01 <old>` (InstanceVariable) durch `01 <new>` ersetzen (gleiche Laenge)."""
    assert len(old) == len(new)
    assert raw.count(b"\x01" + old) >= 1, (raw.hex(), old.hex())
    return raw.replace(b"\x01" + old, b"\x01" + new)


def context_call(obj_d, obj_m, name, args_d, args_m, size=0):
    """obj.name(args)  -> (disk, mem). Skip = Speichergroesse des Member-Ausdrucks."""
    member_m = 5 + args_m + 1
    return (b"\x19" + obj_d + member_m.to_bytes(2, "little") + bytes([size]) + b"\x1b" + name + args_d + b"\x16",
            1 + obj_m + 3 + member_m)


def var_call(var, name, args_d=b"", args_m=0):
    return context_call(b"\x01" + var, 5, name, args_d, args_m)


def console(cmd_d, cmd_m):
    """EatString(GetPlayerOwner().ConsoleCommand(cmd))"""
    d, m = context_call(GET_PLAYER, 6, N_CONSOLE, cmd_d, cmd_m)
    return b"\x0e" + d, 1 + m


def filler(disk, diff):
    """Unerreichbares Fuellmaterial mit Plattenlaenge `disk` und Speicher-Mehrbedarf `diff`."""
    units = [(b"\x21\x00", 3), (b"\x20" + write_ci(-101), 2)]     # NameConst None (+3), ObjectConst (+2)
    for n3 in range(disk // 2 + 1):
        for n2 in range(disk // 3 + 1):
            if 3 * n3 + 2 * n2 == diff and 2 * n3 + 3 * n2 <= disk:
                out = units[0][0] * n3 + units[1][0] * n2
                return out + b"\x0b" * (disk - len(out))
    raise ValueError(f"kein Fuellmaterial fuer Platte {disk}, Diff {diff}")


def detour(blob, stmts, s_mem, before, after=(b"", 0), keep=True, resume=None):
    """Anweisung bei Speicher-Offset s_mem umleiten: ersetzt durch Sprung ans Ende; dort before + S + after + Rueck-
    sprung. before/after: (disk, mem) oder Funktion(basis_mem) -> (disk, mem) fuer Code mit absoluten Sprungzielen.
    keep=False: S wird nicht mitkopiert (vollstaendig durch `before` ersetzt)."""
    head, script_mem, s = parse_function(blob)
    last = stmts[-1]
    script_disk = last[1] + last[3]
    script = bytearray(blob[s:s + script_disk])
    st = next(x for x in stmts if x[0] == s_mem)
    mem, disk, msz, dsz = st[0], st[1], st[2], st[3]
    s_bytes = bytes(script[disk:disk + dsz])
    script[disk:disk + dsz] = b"\x06" + script_mem.to_bytes(2, "little") + filler(dsz - 3, (msz - 3) - (dsz - 3))
    base = script_mem
    if not keep:
        s_bytes, msz_copy = b"", 0
    else:
        msz_copy = msz
    b_d, b_m = before(base) if callable(before) else before
    a_d, a_m = after(base + b_m + msz_copy) if callable(after) else after
    back = (mem + msz) if resume is None else resume       # resume: alternativer Ruecksprungpunkt (Speicher-Offset)
    appended = b_d + s_bytes + a_d + b"\x06" + back.to_bytes(2, "little")
    new_mem = script_mem + b_m + msz_copy + a_m + 3
    return rebuild_function(blob, bytes(script) + appended, new_mem, script_disk)


def cat(*parts):
    return b"".join(p[0] for p in parts), sum(p[1] for p in parts)


def raw_stmt(stmts, blob, mem):
    _, _, s = parse_function(blob)
    st = next(x for x in stmts if x[0] == mem)
    return blob[s + st[1]:s + st[1] + st[3]], st[2]


def build(data):
    pk = Package(data)
    return pk.build(collect(pk))


def collect(pk):
    """Gibt {export_index: neue_daten} fuer alle FEOptionsPage-Funktionen zurueck."""
    repl = {}

    # --- Created: neue Zeile vor "ResetToDefaultsButton = ..." (0x0B38) ---------------------------------
    exp, _, _, blob, st = statements(ORIG, "FEOptionsPage", "Created")
    blob = pk.export_data(exp - 1)
    row = []
    lbl_create, m = raw_stmt(st, blob, 0x088C)
    row.append((swap(lbl_create, CD_LABEL, LO_TEXT), m))                         # Label anlegen
    row.append(var_call(LO_TEXT, N_SETTEXT, *sconst("Bildrate")))               # Label.SetText("Bildrate")
    for mm, old, new in ((0x08D3, CD_LABEL, LO_TEXT), (0x08E3, CD_LABEL, LO_TEXT), (0x08F7, CD_COMBO, HI_TEXT),
                         (0x0923, CD_COMBO, HI_TEXT), (0x0933, CD_COMBO, HI_TEXT), (0x0943, CD_COMBO, HI_TEXT),
                         (0x0957, CD_COMBO, HI_TEXT)):
        r, m = raw_stmt(st, blob, mm)
        row.append((swap(r, old, new), m))
    repl[exp - 1] = detour(blob, st, 0x0B38, cat(*row))

    # --- LoadVideoSettings: Eintraege + aktueller Wert vor "bInitialized = true" (0x0611) ------------------
    exp, _, _, blob, st = statements(ORIG, "FEOptionsPage", "LoadVideoSettings")
    blob = pk.export_data(exp - 1)
    code = [var_call(HI_TEXT, N_CLEAR)]
    for v in FPS_VALUES:
        a1, a2 = sconst(f"{v} FPS"), sconst(v)
        code.append(var_call(HI_TEXT, N_ADDITEM, a1[0] + a2[0], a1[1] + a2[1]))
    gd, gm = context_call(GET_PLAYER, 6, N_CONSOLE, *sconst("GETMAXFPS"))
    code.append((b"\x0f\x00" + L_CURDEPTH + gd, 1 + 5 + gm))                    # CurrentDepth = ...GETMAXFPS
    fps = sconst("FPS")
    args_d = b"\xa8\x00" + L_CURDEPTH + fps[0] + b"\x16" + b"\x00" + L_CURDEPTH  # CurrentDepth @ "FPS", CurrentDepth
    code.append(var_call(HI_TEXT, N_SETVALUE, args_d, 1 + 5 + fps[1] + 1 + 5))
    repl[exp - 1] = detour(blob, st, 0x0611, cat(*code))

    # --- Notify: nach super.Notify (0x0000): if (E==1 && C==Liste) ConsoleCommand("MAXFPS " $ GetValue2()) ----
    exp, _, _, blob, st = statements(ORIG, "FEOptionsPage", "Notify")
    blob = pk.export_data(exp - 1)

    def notify_code(base):
        op1_d, op1_m = b"\x9a\x3b\x00" + L_E + b"\x26\x16", 1 + 1 + 5 + 1 + 1          # E == 1
        op2_d, op2_m = b"\x72\x00" + L_C + b"\x01" + HI_TEXT + b"\x16", 1 + 5 + 5 + 1  # C == Liste
        cond_d = b"\x82" + op1_d + b"\x18" + (op2_m + 1).to_bytes(2, "little") + op2_d + b"\x16"
        cond_m = 1 + op1_m + 3 + op2_m + 1
        gv_d, gv_m = var_call(HI_TEXT, N_GETVALUE2)
        pre = sconst("MAXFPS ")
        call_d, call_m = console(b"\x70" + pre[0] + gv_d + b"\x16", 1 + pre[1] + gv_m + 1)
        end = base + 3 + cond_m + call_m                                               # Ziel: hinter dem Aufruf
        return b"\x07" + end.to_bytes(2, "little") + cond_d + call_d, 3 + cond_m + call_m
    repl[exp - 1] = detour(blob, st, 0x0000, (b"", 0), notify_code)

    # --- ResetToDefaults: MAXFPS 60 vor dem SetRes-Aufruf (0x013B) ----------------------------------------
    exp, _, _, blob, st = statements(ORIG, "FEOptionsPage", "ResetToDefaults")
    blob = pk.export_data(exp - 1)
    repl[exp - 1] = detour(blob, st, 0x013B, console(*sconst("MAXFPS 60")))

    # --- HideWindow: Liste zuklappen (nach ColorDepthCombo.CloseUpWithNoSound, 0x0015) --------------------
    exp, _, _, blob, st = statements(ORIG, "FEOptionsPage", "HideWindow")
    blob = pk.export_data(exp - 1)
    close, m = raw_stmt(st, blob, 0x0015)
    repl[exp - 1] = detour(blob, st, 0x0015, (b"", 0), (swap(close, CD_COMBO, HI_TEXT), m))

    return repl
