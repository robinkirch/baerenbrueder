r"""Patch: Konsolenbefehl `GetRes` liefert alle modernen 32-bit-Aufloesungen (D3DDrv.dll).

Problem (UD3DRenderDevice::Exec, Zweig "GetRes" ab 0x1000885c)
---------------------------------------------------------------
1. Nur 16-bit-Displaymodi werden gesammelt (Sprungtabelle 0x10008d18: Format 23..26, 29, 30 -> uebernehmen).
   Moderne Treiber melden nur noch 32-bit-Modi (D3DFMT_X8R8G8B8 = 22) -> Liste leer.
2. Es werden hoechstens 16 eindeutige Aufloesungen ausgegeben (`cmp edi,0x10` bei 0x1000897b).
3. Ausgabeformat: erster Eintrag "%ix%i", weitere " %ix%i" -> der letzte Eintrag hat kein folgendes
   Leerzeichen. `FEOptionsPage.LoadVideoSettings` (HGame.u) liest aber nur Tokens, denen ein Leerzeichen
   folgt -> der groesste Modus geht immer verloren.

Fix
---
1. Sprungtabellen-Index fuer Format 22 (Byte 0x10008d1a) 0 -> 1 (= "uebernehmen", Ziel 0x10008928).
2. Limit 16 -> 64 (Immediate bei 0x1000897d).
3. String @0x10037f54 " %ix%i" -> "%ix%i " (gleiche Laenge, UTF-16).
4. `mov ebx, 0x10037f48` (0x100089b1, erster Eintrag) zeigt ebenfalls auf 0x10037f54
   (Operand hat einen DIR32-Relocation-Eintrag, bleibt gueltig).
Ergebnis: "640x480 720x400 ... 3440x1440 " - jeder Eintrag mit folgendem Leerzeichen.
Zusammen mit patches/hgame_resolutions.py erscheinen alle Modi im Optionsmenue.

Aufruf: python patches/d3ddrv_resolutions.py [quelle] [ziel]
  Standard: quelle=SETUP\Bears\system\D3DDrv.dll, ziel=game\system\D3DDrv.dll
"""
import hashlib
import shutil
import sys
from pathlib import Path

import pefile

ROOT = Path(__file__).resolve().parent.parent
D3DDRV_SHA256 = "3475aaf5cded1fe497c000a5b9aa8d38edfc76a08c68e0cfc9e7be28b6c8eb26"

# (VA, Originalbytes, neue Bytes, Beschreibung)
PATCHES = [
    (0x10008D1A, "00", "01", "Format 22 (X8R8G8B8) in GetRes uebernehmen"),
    (0x1000897D, "10", "40", "Ausgabelimit 16 -> 64"),
    (0x10037F54, "2000250069007800250069000000", "2500690078002500690020000000", '" %ix%i" -> "%ix%i "'),
    (0x100089B2, "487f0310", "547f0310", "erster Eintrag nutzt ebenfalls \"%ix%i \""),
    # Lock(): Clear-Flags = 3 (TARGET|ZBUFFER) nur bei angeforderter Bildschirmloeschung, sonst 2 (nur Z).
    # Mit dem zentrierten 4:3-Menue (hgame_patches.py) bleiben die Seitenbereiche sonst ungeloescht
    # -> Mausspuren/Flackern. Fix: immer Bild + Z-Puffer loeschen.
    (0x10004EA8, "02000000", "03000000", "Lock: Bild immer loeschen (keine Mausspuren neben dem Menue)"),
]


def main():
    src = Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT / "SETUP" / "Bears" / "system" / "D3DDrv.dll"
    dst = Path(sys.argv[2]) if len(sys.argv) > 2 else ROOT / "game" / "system" / "D3DDrv.dll"
    data = bytearray(src.read_bytes())
    if hashlib.sha256(data).hexdigest() != D3DDRV_SHA256:
        sys.exit(f"{src} ist nicht die Original-D3DDrv.dll")
    pe = pefile.PE(data=bytes(data))
    base = pe.OPTIONAL_HEADER.ImageBase
    for va, old, new, desc in PATCHES:
        old_b, new_b = bytes.fromhex(old), bytes.fromhex(new)
        off = pe.get_offset_from_rva(va - base)
        if bytes(data[off:off + len(old_b)]) != old_b:
            sys.exit(f"Originalbytes stimmen nicht bei {va:#x} ({desc})")
        data[off:off + len(new_b)] = new_b
        print(f"  {va:#x}: {old} -> {new}  ({desc})")
    orig_copy = dst.with_name(dst.name + ".orig")
    if dst.exists() and not orig_copy.exists():
        shutil.copy2(dst, orig_copy)
    dst.write_bytes(data)
    print("D3DDrv.dll gepatcht: GetRes liefert alle 32-bit-Aufloesungen")


if __name__ == "__main__":
    main()
