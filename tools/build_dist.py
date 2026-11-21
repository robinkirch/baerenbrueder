r"""Baut das auslieferbare Spielpaket dist\Baerenbrueder\ aus der gepatchten Testinstallation game\.

Ablauf:
  1. patches/apply_all.py (alle Patches frisch aus den Originalen; mit --no-apply ueberspringen)
  2. game\ -> dist\Baerenbrueder\ kopieren, ohne Sicherungen/Logs/Entwickler-Werkzeuge (EXCLUDE)
  3. OpenAL Soft pruefen (SHA256) + Lizenztexte beilegen, README.md (aus installer/README-Paket.md)
  4. dist\Baerenbrueder.files.txt: Dateiliste mit SHA256
  5. mit --installer: Inno Setup (ISCC.exe) -> dist\Baerenbrueder-Win11-Setup.exe

Nicht im Paket (unter Windows 11 unnoetig): InstallShield-Installer (SETUP.EXE, *.cab, setup.inx), DirectX-9.0b-Setup
(D3D8 ist Teil von Windows), Autorun. Das Spiel braucht keine Registry-Eintraege; Benutzerdaten (Game.ini, User.ini,
Spielstaende) legt es selbst unter %ProgramData%\Disney Interactive\Baerenbrueder\System an.

Aufruf: python tools/build_dist.py [--no-apply] [--installer]
"""
import fnmatch
import hashlib
import os
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
GAME = ROOT / "game"
DIST = ROOT / "dist" / "Baerenbrueder"
LIST = ROOT / "dist" / "Baerenbrueder.files.txt"
README = ROOT / "installer" / "README-Paket.md"
ISS = ROOT / "installer" / "Baerenbrueder.iss"
OPENAL_DIR = ROOT / "patches" / "thirdparty" / "openal-soft-1.25.2"
OPENAL_SHA = "606cf8b4c22c7ae00813585279ac045115907bc66d1483eb26355907021ea4b0"   # bin\Win32\soft_oal.dll 1.25.2

# Relativ zu game\, Gross-/Kleinschreibung egal
EXCLUDE = [
    "*.orig",                    # Sicherungen der Originale (apply_all)
    "*.log", "system/Detected.ini",
    "system/*_d.dll",            # Debug-Builds von ogg/vorbis (nur untereinander referenziert)
    "system/System.dsp",         # Visual-C++-Projektdatei
    "system/AutoRun.inf",        # CD-Autostart (verweist auf setup.exe)
    "system/BRIGHT.EXE",         # Epic-Texturwerkzeug (1999), Entwicklerwerkzeug
    "system/sx.exe",             # Sound-Konverter (1997), Entwicklerwerkzeug
    "system/Game.ini", "system/User.ini",   # falls vorhanden: Benutzer-INIs gehoeren nicht ins Paket
]


def excluded(rel):
    r = rel.as_posix().lower()
    return any(fnmatch.fnmatch(r, p.lower()) for p in EXCLUDE)


def sha256(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def find_iscc():
    for base in (os.environ.get("ProgramFiles(x86)"), os.environ.get("ProgramFiles"),
                 os.path.join(os.environ.get("LOCALAPPDATA", ""), "Programs")):
        for ver in ("7", "6"):
            if base:
                p = Path(base) / f"Inno Setup {ver}" / "ISCC.exe"
                if p.exists():
                    return p
    return shutil.which("ISCC")


def main():
    if "--no-apply" not in sys.argv:
        r = subprocess.run([sys.executable, str(ROOT / "patches" / "apply_all.py")])
        if r.returncode != 0:
            sys.exit("apply_all.py fehlgeschlagen")

    oal = GAME / "system" / "OpenAL32.dll"
    if sha256(oal) != OPENAL_SHA:
        sys.exit("game\\system\\OpenAL32.dll ist nicht OpenAL Soft 1.25.2 (siehe patches/apply_all.py)")

    if DIST.exists():
        shutil.rmtree(DIST)
    copied, skipped = 0, []
    for src in sorted(GAME.rglob("*")):
        rel = src.relative_to(GAME)
        if src.is_dir():
            continue
        if excluded(rel):
            skipped.append(rel.as_posix())
            continue
        dst = DIST / rel
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dst)
        copied += 1
    (DIST / "Save").mkdir(exist_ok=True)       # SavePath=../Save (Original-Ordnerstruktur)

    lic = DIST / "Lizenzen" / "OpenAL-Soft"
    lic.mkdir(parents=True, exist_ok=True)
    for f in OPENAL_DIR.iterdir():
        shutil.copy2(f, lic / f.name)
    shutil.copy2(README, DIST / "README.md")

    files = sorted(p for p in DIST.rglob("*") if p.is_file())
    total = sum(p.stat().st_size for p in files)
    with open(LIST, "w", encoding="utf-8", newline="\n") as out:
        for p in files:
            out.write(f"{sha256(p)}  {p.relative_to(DIST).as_posix()}\n")

    print(f"Kopiert: {copied} Dateien aus game\\, ausgelassen: {len(skipped)}")
    for s in skipped:
        print(f"  - {s}")
    print(f"Paket: {DIST}  ({len(files)} Dateien, {total / 1e6:.1f} MB)")
    print(f"Dateiliste: {LIST}")

    if "--installer" in sys.argv:
        iscc = find_iscc()
        if not iscc:
            sys.exit("Inno Setup 7/6 (ISCC.exe) nicht gefunden - https://jrsoftware.org/isdl.php")
        r = subprocess.run([str(iscc), "/Q", str(ISS)])
        if r.returncode != 0:
            sys.exit("ISCC fehlgeschlagen")
        print(f"Installer: {ROOT / 'dist' / 'Baerenbrueder-Win11-Setup.exe'}")


if __name__ == "__main__":
    main()
