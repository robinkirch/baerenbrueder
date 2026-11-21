r"""Wendet alle Patches auf die Testinstallation game\ an (immer ausgehend von den Originalen in SETUP\Bears).

Aufruf: python patches/apply_all.py

Nicht automatisiert (externe Datei):
  - OpenAL Soft (https://github.com/kcat/openal-soft/releases, LGPL): bin\Win32\soft_oal.dll als
    game\system\OpenAL32.dll ablegen (ersetzt Creative OpenAL 1.0 von 2003). Aktuell eingesetzt: 1.25.2.
"""
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
PATCHES = ["engine_patches.py", "d3ddrv_patches.py", "hgame_patches.py", "windrv_audio_viewport.py",
           "game_launcher_resolutions.py", "window_dialog_fps.py",
           "cutscene_fixes.py", "default_settings.py"]

for p in PATCHES:
    print(f"== {p}")
    r = subprocess.run([sys.executable, str(HERE / p)])
    if r.returncode != 0:
        sys.exit(f"{p} fehlgeschlagen")
print("Alle Patches angewendet.")
