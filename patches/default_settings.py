r"""Standardwerte fuer neue Benutzer (system\default.ini, system\DefUser.ini).

Beim ersten Start legt das Spiel Game.ini/User.ini unter ProgramData\Disney Interactive\Baerenbrueder\System aus
diesen Vorlagen an. Bestehende Benutzer-INIs werden nicht angefasst.

1. default.ini  [Engine.GameEngine] MaxFPS=60   (FPS-Limit, siehe engine_patches.py; fehlt -> Engine nimmt auch 60)
2. DefUser.ini  MouseX: zusaetzlich "Axis aBaseX Speed=5.0" -> Maus dreht die Figur (vom User getestet, 5.0 = halbe
   Geschwindigkeit des ersten Versuchs). Im Lachslauf ohne Wirkung (dort nur hoch/runter).

Aufruf: python patches/default_settings.py
"""
import hashlib
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "SETUP" / "Bears" / "system"
DST = ROOT / "game" / "system"

# (Datei, SHA256 des Originals, alter Text, neuer Text)
FIXES = [
    ("default.ini", "a2218619daf934580c172f02bca61b4f2a3e49ff5e6ddbaa762e8be10f12c4e5",
     b"[Engine.GameEngine]\r\n", b"[Engine.GameEngine]\r\nMaxFPS=60\r\n"),
    ("DefUser.ini", "3b79e81d4991662501292c91ce74af268146e0971ce629f33a93ec373158651c",
     b"MouseX=Axis aMouseX Speed=4.0", b"MouseX=Axis aBaseX Speed=5.0 | Axis aMouseX Speed=4.0"),
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
            shutil.copy2(SRC / name, orig_copy)
        dst.write_bytes(data.replace(old, new))
        print(f"  {name}: {new.decode().strip()}")
    print(f"Standardwerte gesetzt ({len(FIXES)} Datei(en))")


if __name__ == "__main__":
    main()
