r"""Korrekturen an Fehlern in den Original-Cutscene-Skripten (system\CutScenes\*.int, ASCII).

1. IceRun_Intro.int, line_70: "Kodz Animate iceslideRight" -> "Koda ..." (Tippfehler im Original; Log:
   "CutError: Failed to find Kodz" -> Kodas Rutsch-Animation im Intro des Zeitrennens fehlte).

Aufruf: python patches/cutscene_fixes.py
"""
import hashlib
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "SETUP" / "Bears" / "system" / "CutScenes"
DST = ROOT / "game" / "system" / "CutScenes"

# (Datei, SHA256 des Originals, alter Text, neuer Text)
FIXES = [
    ("IceRun_Intro.int", "ec6e2a79bcfa5c86ba17811a5fc9b3d7f379eb3a3125d27f953295bd56dc2a96",
     b"line_70=Kodz Animate iceslideRight", b"line_70=Koda Animate iceslideRight"),
]


def main():
    for name, sha, old, new in FIXES:
        data = (SRC / name).read_bytes()
        if hashlib.sha256(data).hexdigest() != sha:
            sys.exit(f"{name}: nicht die Originaldatei")
        if data.count(old) != 1:
            sys.exit(f"{name}: Suchtext nicht eindeutig gefunden")
        dst = DST / name
        orig_copy = dst.with_name(dst.name + ".orig")
        if dst.exists() and not orig_copy.exists():
            shutil.copy2(dst, orig_copy)
        dst.write_bytes(data.replace(old, new))
        print(f"  {name}: {old.decode()} -> {new.decode()}")
    print(f"Cutscene-Skripte korrigiert ({len(FIXES)} Aenderung(en))")


if __name__ == "__main__":
    main()
