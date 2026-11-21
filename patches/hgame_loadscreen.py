r"""Ladebildschirme bei Breitbild zentriert und korrekt skaliert (HGame.u).

1. baseConsole.ScaleAndDraw (Ladebildschirm beim Levelwechsel): zeichnet die 640x480-Kacheln ueber
   Root.DrawStretchedTexture (GUIScale = Hoehe/480 seit hgame_patches.py) -> richtige Groesse, aber links.
   Neu:  FX = (Root.WinWidth - 640) * 0.5;  Root.DrawStretchedTexture(C, X + FX, Y*fy, USize*fy, VSize*fy, Tex)
   (statt FX = 1.0 und X*FX / USize*FX).
2. CutSceneManager.ScaleAndDraw (Bild beim Ueberspringen von Cutscenes): fScale = GetScaleFactor() = SizeX/640
   -> bei 21:9 riesig und unten abgeschnitten. Neu:
       fScale = float(C.SizeY) / 480;
       C.SetPos(X*fScale + (float(C.SizeX) - 640*fScale) * 0.5, Y*fScale)
Technik wie hgame_fpsrow.py (Detour + Umlagerung mit tools/upkg.py).
"""
import struct
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "tools"))
from hgame_fpsrow import ORIG, detour, raw_stmt  # noqa: E402
from upkg import parse_function  # noqa: E402
from ustatements import statements  # noqa: E402

# --- Ausdrucks-Baukasten: jedes Element = (Plattenbytes, Speichergroesse) --------------------------------------
END = (b"\x16", 1)


def L(ref):            # lokale Variable / Parameter
    return b"\x00" + bytes.fromhex(ref), 5


def I(ref):            # Instanzvariable
    return b"\x01" + bytes.fromhex(ref), 5


def F(v):              # FloatConst
    return b"\x1e" + struct.pack("<f", v), 5


def seq(*parts):
    return b"".join(p[0] for p in parts), sum(p[1] for p in parts)


def nat(op, *args):    # native Operator/Funktion mit Parametern
    return seq((bytes([op]), 1), *args, END)


def i2f(e):            # int -> float
    return seq((b"\x40", 1), e)


def ctx(obj, member, size):
    return seq((b"\x19", 1), obj, (member[1].to_bytes(2, "little") + bytes([size]), 3), member)


def let(lhs, rhs):
    return seq((b"\x0f", 1), lhs, rhs)


MUL, ADD, SUB, DIV = 0xAB, 0xAE, 0xAF, 0xAC


def collect(pk):
    repl = {}

    # --- 1. baseConsole.ScaleAndDraw ---------------------------------------------------------------------
    exp, _, _, _, st = statements(ORIG, "baseConsole", "ScaleAndDraw")
    blob = bytearray(pk.export_data(exp - 1))
    _, _, s = parse_function(bytes(blob))
    call_old, _ = raw_stmt(st, bytes(blob), 0x0023)
    fx, fy = "4c33", "7f32"
    call_new = call_old.replace(bytes.fromhex("ab004958004c3316"), bytes.fromhex("ae004958004c3316"), 1)   # X*FX -> X+FX
    usize_old = bytes.fromhex("ab4019007426050004" "01fb02" "004c3316")
    assert call_new.count(usize_old) == 1
    call_new = call_new.replace(usize_old, usize_old[:-3] + bytes.fromhex(fy) + b"\x16")                 # USize*FX -> *fy
    assert len(call_new) == len(call_old) and call_new != call_old
    d = next(x for x in st if x[0] == 0x0023)[1]
    blob[s + d:s + d + len(call_new)] = call_new
    root, winwidth = I("d101"), I("e601")                      # Root (WindowConsole), WinWidth
    new_fx = let(L(fx), nat(MUL, nat(SUB, ctx(root, winwidth, 4), F(640.0)), F(0.5)))
    repl[exp - 1] = detour(bytes(blob), st, 0x000D, new_fx, keep=False)

    # --- 2. CutSceneManager.ScaleAndDraw -----------------------------------------------------------------
    exp, _, _, _, st = statements(ORIG, "CutSceneManager", "ScaleAndDraw")
    blob = pk.export_data(exp - 1)
    C, X, Y, fscale = L("452b"), L("7c6f"), L("7b6f"), L("7417")
    sizex, sizey = I("c101"), I("d401")                        # Canvas.SizeX (-65), Canvas.SizeY (-84)
    stmt1 = let(fscale, nat(DIV, i2f(ctx(C, sizey, 4)), F(480.0)))
    x_arg = nat(ADD, nat(MUL, X, fscale),
                nat(MUL, nat(SUB, i2f(ctx(C, sizex, 4)), nat(MUL, F(640.0), fscale)), F(0.5)))
    y_arg = nat(MUL, Y, fscale)
    setpos = seq((b"\x1c" + bytes.fromhex("c501"), 5), x_arg, y_arg, END)    # FinalFunction SetPos(...)
    stmt2 = ctx(C, setpos, 0)
    # fScale-Zuweisung (0x0000) umleiten: neue Zuweisung + neues SetPos, Ruecksprung hinter das alte SetPos (0x0038)
    repl[exp - 1] = detour(blob, st, 0x0000, seq(stmt1, stmt2), keep=False, resume=0x0038)
    return repl
