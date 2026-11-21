r"""Speichern am Speicherstein nur noch, wenn der Held wirklich speichern darf (HGame.u, SavePointUnsaved.OnSaveGame).

Fehler (vom User gefunden): Steht Kenai waehrend einer Cutscene neben einem Speicherstein, loest Linksklick
(BearHero.HandleActionButton -> SwipeTestSavePoint -> SavePointUnsaved.OnSaveGame) das Speichern aus. Dabei stoppt
SaveBearsGame alle Sound-Slots -> der Cutscene-Dialog bricht ab. Touch() prueft vor dem Speichern
BearHero(Level.PlayerHeroActor).OkayToSave() (PlayerWalking, PHYS_Walking, Health > 0, ...), der Linksklick-Weg
nicht. In Cutscenes ist der Held in 'stateCutIdle' -> OkayToSave() == false.

Fix: am Anfang von OnSaveGame (Detour der ersten Anweisung PlaySound(OnSaveSound)):
    if (!BearHero(Level.PlayerHeroActor).OkayToSave()) return;
Der Bedingungsausdruck wird 1:1 aus SavePointUnsaved.Touch (Anweisung 0x0018) uebernommen.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "tools"))
sys.path.insert(0, str(Path(__file__).resolve().parent))
from ustatements import statements  # noqa: E402
from hgame_fpsrow import ORIG, detour  # noqa: E402

# BearHero(Level.PlayerHeroActor).OkayToSave()  -- aus Touch, Anweisung 0x0018 (JumpIfNot-Bedingung)
OKAY_TO_SAVE = bytes.fromhex("19 2e 02 19 01 a0 05 00 04 01 a9 06 00 04 1b 42 14 16")
OKAY_TO_SAVE_MEM = 29


def collect(pk):
    repl = {}

    # Bedingung gegen das Original pruefen
    _, _, s, tblob, tst = statements(ORIG, "SavePointUnsaved", "Touch")
    t = next(x for x in tst if x[0] == 0x0018)
    raw = tblob[s + t[1]:s + t[1] + t[3]]
    assert raw[0] == 0x07 and raw[3:] == OKAY_TO_SAVE, raw.hex(" ")
    assert t[2] == 3 + OKAY_TO_SAVE_MEM

    exp, _, s, blob, st = statements(ORIG, "SavePointUnsaved", "OnSaveGame")
    blob = pk.export_data(exp - 1)
    first = st[0]
    assert first[:4] == [0, 0, 8, 6] and blob[s:s + 6] == bytes.fromhex("6108016f7016"), (first, blob[s:s + 6].hex())

    def guard(base):
        cond_d = b"\x81" + OKAY_TO_SAVE + b"\x16"           # !OkayToSave()
        cond_m = 1 + OKAY_TO_SAVE_MEM + 1
        cont = base + 3 + cond_m + 2                         # hinter "return"
        return b"\x07" + cont.to_bytes(2, "little") + cond_d + b"\x04\x0b", 3 + cond_m + 2

    repl[exp - 1] = detour(blob, st, 0x0000, guard)
    return repl
