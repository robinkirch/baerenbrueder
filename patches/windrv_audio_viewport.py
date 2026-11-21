r"""Patch: Ton bleibt nach Alt-Tab nicht mehr dauerhaft weg (WinDrv.dll).

Problem (UWindowsViewport::ViewportWndProc, 0x11108ab0)
-------------------------------------------------------
WinDrv merkt sich den Audio-Viewport beim Fokusverlust in EINER globalen Variable (0x1111831c):
  - WM_ACTIVATE inaktiv (0x11108e93): saved = Audio->GetViewport(); Audio->Minimize()  (Viewport -> NULL)
  - WM_SIZE "Forced minimization" (0x11108fa7): saved = Audio->GetViewport(); Audio->SetViewport(NULL)
  - Rueckkehr: Restore(saved) bzw. SetViewport(saved) nur wenn saved != NULL.
Unter Windows 11 kommt bei Alt-Tab aus dem Vollbild zuerst WM_ACTIVATE (saved = Viewport, korrekt),
danach WM_SIZE: GetViewport() liefert jetzt NULL und ueberschreibt saved -> bei Rueckkehr wird nichts
wiederhergestellt; ALAudio::Update/PlaySound brechen bei Viewport NULL ab -> dauerhaft kein Ton.
Belegt per Frida (notes\logs\run-18: Minimize, dann SetViewport(NULL), kein Restore).

Fix
---
Beide `call [vtable+0x94]` (GetViewport, 6 Bytes) werden durch `call cave; nop` ersetzt. Der Cave ruft
GetViewport auf und liefert, falls das Ergebnis NULL ist, den bereits gespeicherten Wert zurueck.
So ueberschreibt die zweite Nachricht saved nicht mehr mit NULL. Cave positionsunabhaengig (call/pop),
liegt im freien Bereich hinter .text; keine Relocation betroffen.

Aufruf: python patches/windrv_audio_viewport.py [quelle] [ziel]
  Standard: quelle=SETUP\Bears\system\WinDrv.dll, ziel=game\system\WinDrv.dll
"""
import hashlib
import shutil
import struct
import sys
from pathlib import Path

import pefile

ROOT = Path(__file__).resolve().parent.parent
WINDRV_SHA256 = "702f625358d7b738f863670660be5f43b28ba3f228ca6cbae93f06a1ce9e661c"
SAVED_VA = 0x1111831C
SITES = [
    # (VA, Originalbytes, Register mit vtable)
    (0x11108E93, bytes.fromhex("ff9294000000"), "edx"),   # WM_ACTIVATE inaktiv
    (0x11108FA7, bytes.fromhex("ff9094000000"), "eax"),   # WM_SIZE forced minimization
]
CALL_VT = {"edx": b"\xff\x92\x94\x00\x00\x00", "eax": b"\xff\x90\x94\x00\x00\x00"}


def cave_bytes(cave_va, reg):
    # 00 call [reg+0x94]; 06 test eax,eax; 08 jnz .r; 0a call .h; 0f .h: pop eax;
    # 10 mov eax,[eax+saved-.h]; 16 .r: ret
    h = cave_va + 0x0F
    c = CALL_VT[reg] + b"\x85\xc0" + b"\x75\x0c" + b"\xe8\x00\x00\x00\x00" + b"\x58"
    c += b"\x8b\x80" + struct.pack("<i", SAVED_VA - h) + b"\xc3"
    assert len(c) == 0x17
    return c


def main():
    src = Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT / "SETUP" / "Bears" / "system" / "WinDrv.dll"
    dst = Path(sys.argv[2]) if len(sys.argv) > 2 else ROOT / "game" / "system" / "WinDrv.dll"
    data = bytearray(src.read_bytes())
    if hashlib.sha256(data).hexdigest() != WINDRV_SHA256:
        sys.exit(f"{src} ist nicht die Original-WinDrv.dll")
    pe = pefile.PE(data=bytes(data))
    base = pe.OPTIONAL_HEADER.ImageBase
    text = next(s for s in pe.sections if s.Name.rstrip(b"\0") == b".text")

    rva = (text.VirtualAddress + text.Misc_VirtualSize + 15) & ~15
    for va, orig, reg in SITES:
        cave_va = base + rva
        cave = cave_bytes(cave_va, reg)
        off = text.PointerToRawData + (rva - text.VirtualAddress)
        if rva + len(cave) > text.VirtualAddress + text.SizeOfRawData or any(data[off:off + len(cave)]):
            sys.exit("kein freier Platz in .text")
        data[off:off + len(cave)] = cave
        s_off = pe.get_offset_from_rva(va - base)
        if bytes(data[s_off:s_off + 6]) != orig:
            sys.exit(f"Originalbytes stimmen nicht bei {va:#x}")
        data[s_off:s_off + 6] = b"\xe8" + struct.pack("<i", cave_va - (va + 5)) + b"\x90"
        print(f"  {va:#x}: call [{reg}+0x94] -> call {cave_va:#x}")
        rva = (rva + len(cave) + 15) & ~15
    struct.pack_into("<I", data, text.get_file_offset() + 8, rva - text.VirtualAddress)

    orig_copy = dst.with_name(dst.name + ".orig")
    if dst.exists() and not orig_copy.exists():
        shutil.copy2(dst, orig_copy)
    dst.write_bytes(data)
    print("WinDrv.dll gepatcht: gespeicherter Audio-Viewport wird nicht mehr mit NULL ueberschrieben")


if __name__ == "__main__":
    main()
