r"""Wendet alle Patches auf die Testinstallation game\ an (immer ausgehend von den Originalen in SETUP\Bears).

Aufruf: python patches/apply_all.py [--openal <pfad>\soft_oal.dll]

  - Fehlt game\, wird es als Kopie von SETUP\Bears angelegt.
  - --openal: OpenAL Soft (https://github.com/kcat/openal-soft/releases, LGPL, bin\Win32\soft_oal.dll) wird als
    game\system\OpenAL32.dll uebernommen (ersetzt Creative OpenAL 1.0 von 2003). Getestet: 1.25.2.
    Ohne die Option bleibt eine vorhandene OpenAL32.dll unveraendert (Hinweis, falls noch die alte).
"""
import hashlib
import shutil
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
SRC = ROOT / "SETUP" / "Bears"
GAME = ROOT / "game"
PATCHES = ["engine_patches.py", "d3ddrv_patches.py", "hgame_patches.py", "windrv_audio_viewport.py",
           "game_launcher_resolutions.py", "window_dialog_fps.py",
           "cutscene_fixes.py", "default_settings.py"]


def sha256(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def main():
    if not (SRC / "system" / "Game.exe").exists():
        sys.exit(f"Originalspiel nicht gefunden: {SRC}\\system\\Game.exe\n"
                 "-> Inhalt der Original-CD/ISO in das Projektverzeichnis kopieren (es muss SETUP\\Bears\\ geben).")
    if not GAME.exists():
        print(f"== Lege {GAME} als Kopie von {SRC} an")
        shutil.copytree(SRC, GAME)

    for p in PATCHES:
        print(f"== {p}")
        r = subprocess.run([sys.executable, str(HERE / p)])
        if r.returncode != 0:
            sys.exit(f"{p} fehlgeschlagen")

    oal = GAME / "system" / "OpenAL32.dll"
    if "--openal" in sys.argv:
        src = Path(sys.argv[sys.argv.index("--openal") + 1])
        orig_copy = oal.with_name(oal.name + ".orig")
        if oal.exists() and not orig_copy.exists():
            shutil.copy2(SRC / "system" / "OpenAL32.dll", orig_copy)
        shutil.copy2(src, oal)
        print(f"== OpenAL Soft uebernommen: {src}")
    elif sha256(oal) == sha256(SRC / "system" / "OpenAL32.dll"):
        print("HINWEIS: game\\system\\OpenAL32.dll ist noch Creative OpenAL von 2003. Empfohlen: OpenAL Soft\n"
              "         (bin\\Win32\\soft_oal.dll) mit --openal <pfad> uebernehmen.")
    print("Alle Patches angewendet. Start: game\\system\\Game.exe")


if __name__ == "__main__":
    main()
