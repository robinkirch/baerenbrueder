r"""Patch: Launcher (Vorab-Menue, Grafikseite) - alle Aufloesungen, korrektes Speichern, Bildrate (Game.exe).

Seite WFrontEndPageConfigVideo (Template 161 in Window.dll, siehe window_dialog_fps.py).

1. Befuellen (FUN_109027f0, D3D-Zweig ab 0x10902839 -> Cave A):
   Original: feste Liste 640/800/1024 (+1280x1024). Neu: alle 32-bit-Modi ab 640 Breite aus EnumDisplaySettingsW
   (ohne Duplikate). Danach FPS-Liste (ID 1201): Reset, "30 FPS"/"60 FPS"/"144 FPS", aktuellen Wert aus
   [Engine.GameEngine] MaxFPS (GConfig->GetFloat, Standard 60) auswaehlen.
2. Speichern (FUN_1090ae00, D3D-Zweig ab 0x1090af1b -> Cave B):
   Original-FEHLER: Aufloesung wurde ueber den LISTEN-INDEX bestimmt (1=800x600, 2=1024x768, 3=1280x1024,
   sonst 640x480) -> mit der vollstaendigen Liste falsche Aufloesung. Neu: Text des gewaehlten Eintrags lesen,
   am 'x' teilen -> FString X/Y (wie Original weiterverarbeitet). Zusaetzlich gewaehlte Bildrate (Zahl vor dem
   Leerzeichen) per GConfig->SetString in [Engine.GameEngine] MaxFPS schreiben.
Game.exe hat keine Relocations (feste Basis 0x10900000) -> absolute Adressen sind gueltig.

Aufruf: python patches/game_launcher_resolutions.py [quelle] [ziel]
"""
import hashlib
import shutil
import struct
import sys
from pathlib import Path

import pefile

sys.path.insert(0, str(Path(__file__).resolve().parent))
from x86asm import X86  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
GAME_SHA256 = "8179c624560d01eeeec2b8f2614b775fe23eda0fa0752475cab56676eceb5b23"
FILL_SITE, FILL_ORIG, FILL_CONT = 0x10902839, bytes.fromhex("689cb091106a008b4dd081c1e0000000"), 0x1090292E
SAVE_SITE, SAVE_ORIG, SAVE_CONT = 0x1090AF1B, bytes.fromhex("8b4dcc81c1e0000000ff15bca49110"), 0x1090B05C
IAT = dict(appFailAssert=0x1091A0A4, appSprintf=0x1091A148, opHWND=0x1091A700, InsertString=0x1091A6FC,
           SendMessageW=0x1091A458, GetDlgItem=0x1091A44C, GConfig=0x1091A140, FStrAssign=0x1091A108)
FPS_LIST_ID = 1201
FPS_ITEMS = ("30 FPS", "60 FPS", "144 FPS")
LB_ADDSTRING, LB_RESETCONTENT, LB_SETCURSEL, LB_GETCURSEL, LB_GETTEXT, LB_FINDSTRINGEXACT = (
    0x180, 0x184, 0x186, 0x188, 0x189, 0x1A2)


def u32(v):
    return struct.pack("<I", v & 0xFFFFFFFF)


def call_iat(a, name):
    a.emit(b"\xff\x15" + u32(IAT[name]))


def send(a, msg, wparam_bytes, lparam_bytes, hwnd_reg=b"\x53"):
    """SendMessageW(hwnd(ebx), msg, wparam, lparam); Argumente als fertige push-Bytefolgen."""
    a.emit(lparam_bytes + wparam_bytes + b"\x68" + u32(msg) + hwnd_reg)
    call_iat(a, "SendMessageW")


def build_fill_cave(base, d_handle, d_export):
    """Cave A: thiscall-artig, ecx = Seite. Lokale Daten (ebp-Rahmen): DEVMODE @0, buf @0xE0, i @0x160,
    float @0x164, int @0x168."""
    a = X86(base)
    a.emit(b"\x60\x8b\xf1")                                  # pushad; mov esi,ecx
    a.emit(b"\x81\xec" + u32(0x170) + b"\x8b\xec")           # sub esp,0x170; mov ebp,esp
    a.emit(b"\xa1" + u32(IAT["appFailAssert"]) + b"\x05" + u32(d_handle))
    a.push_addr("s_user32")
    a.emit(b"\xff\xd0\x83\xc4\x04\x85\xc0")                  # call eax; add esp,4; test eax,eax
    a.jcc("jz", "fps")
    a.emit(b"\x8b\xf8")                                      # mov edi,eax (user32)
    a.emit(b"\xa1" + u32(IAT["appFailAssert"]) + b"\x05" + u32(d_export))
    a.push_addr("s_eds")
    a.emit(b"\x57\xff\xd0\x83\xc4\x08\x85\xc0")              # push edi; call eax; add esp,8; test
    a.jcc("jz", "fps")
    a.emit(b"\x8b\xf8")                                      # mov edi,EnumDisplaySettingsW
    a.emit(b"\xc7\x85" + u32(0x160) + u32(0))                # i = 0
    a.label("loop")
    a.emit(b"\x66\xc7\x45\x44\xdc\x00\x66\xc7\x45\x46\x00\x00")   # dmSize=220, dmDriverExtra=0
    a.emit(b"\x55\xff\xb5" + u32(0x160) + b"\x6a\x00\xff\xd7")    # EnumDisplaySettingsW(NULL, i, &dm)
    a.emit(b"\x85\xc0")
    a.jcc("jz", "fps")
    a.emit(b"\xff\x85" + u32(0x160))                         # i++
    a.emit(b"\x81\xbd" + u32(0xA8) + u32(32))                # dmBitsPerPel == 32 ?
    a.jcc("jne", "loop")
    a.emit(b"\x81\xbd" + u32(0xAC) + u32(640))               # dmPelsWidth >= 640 ?
    a.jcc("jb", "loop")
    a.emit(b"\xff\xb5" + u32(0xB0) + b"\xff\xb5" + u32(0xAC))   # push h; push w
    a.push_addr("s_resfmt")
    a.emit(b"\x8d\x85" + u32(0xE0) + b"\x50")                # push buf
    call_iat(a, "appSprintf")
    a.emit(b"\x83\xc4\x10")
    a.emit(b"\x8d\x8e" + u32(0xE0))                          # ecx = WListBox (Seite+0xE0)
    call_iat(a, "opHWND")
    a.emit(b"\x8b\xd8")                                      # ebx = hwnd
    send(a, LB_FINDSTRINGEXACT, b"\x6a\xff", b"\x8d\x8d" + u32(0xE0) + b"\x51")
    a.emit(b"\x83\xf8\xff")
    a.jcc("jne", "loop")
    a.emit(b"\x8d\x85" + u32(0xE0) + b"\x50\x6a\xff")        # push buf; push -1
    a.emit(b"\x8d\x8e" + u32(0xE0))
    call_iat(a, "InsertString")
    a.jmp("loop")
    # --- FPS-Liste ---------------------------------------------------------------------------------------
    a.label("fps")
    a.emit(b"\x68" + u32(FPS_LIST_ID) + b"\xff\x76\x04")      # push 1201; push [esi+4] (Seiten-HWND)
    call_iat(a, "GetDlgItem")
    a.emit(b"\x85\xc0")
    a.jcc("jz", "done")
    a.emit(b"\x8b\xd8")                                      # ebx = FPS-Liste
    send(a, LB_RESETCONTENT, b"\x6a\x00", b"\x6a\x00")
    for i in range(len(FPS_ITEMS)):
        a.emit(b"")
        a.parts.append(("abs", (b"\x68", f"s_fps{i}")))      # push s
        a.size += 5
        a.emit(b"\x6a\x00\x68" + u32(LB_ADDSTRING) + b"\x53")
        call_iat(a, "SendMessageW")
    a.emit(b"\xc7\x85" + u32(0x164) + struct.pack("<f", 60.0))   # f = 60.0 (Standard)
    a.emit(b"\x6a\x00\x8d\x85" + u32(0x164) + b"\x50")        # push NULL; push &f
    a.push_addr("s_key")
    a.push_addr("s_sec")
    a.emit(b"\xa1" + u32(IAT["GConfig"]) + b"\x8b\x08\x8b\x01\xff\x50\x08")   # GConfig->GetFloat
    a.emit(b"\xd9\x85" + u32(0x164) + b"\xdb\x9d" + u32(0x168))             # n = (int)f
    a.emit(b"\xff\xb5" + u32(0x168))
    a.push_addr("s_fpsfmt")
    a.emit(b"\x8d\x85" + u32(0xE0) + b"\x50")
    call_iat(a, "appSprintf")
    a.emit(b"\x83\xc4\x0c")
    send(a, LB_FINDSTRINGEXACT, b"\x6a\xff", b"\x8d\x85" + u32(0xE0) + b"\x50")
    a.emit(b"\x83\xf8\xff")
    a.jcc("jne", "sel")
    a.emit(b"\xb8\x01\x00\x00\x00")                          # nicht gefunden -> "60 FPS"
    a.label("sel")
    a.emit(b"\x6a\x00\x50\x68" + u32(LB_SETCURSEL) + b"\x53")
    call_iat(a, "SendMessageW")
    a.label("done")
    a.emit(b"\x81\xc4" + u32(0x170) + b"\x61\xc3")           # add esp,0x170; popad; ret
    a.wstr("s_user32", "user32.dll")
    a.wstr("s_eds", "EnumDisplaySettingsW")
    a.wstr("s_resfmt", "%ix%i")
    a.wstr("s_fpsfmt", "%i FPS")
    a.wstr("s_sec", "Engine.GameEngine")
    a.wstr("s_key", "MaxFPS")
    for i, s in enumerate(FPS_ITEMS):
        a.wstr(f"s_fps{i}", s)
    return a.assemble()


def build_save_cave(base):
    """Cave B: aufgerufen im Rahmen von FUN_1090ae00 (ebp = dessen Rahmen): [ebp-0x34] = Seite,
    [ebp-0x28] = FString X, [ebp-0x1c] = FString Y."""
    a = X86(base)
    a.emit(b"\x60\x81\xec" + u32(0x100) + b"\x8b\xfc")       # pushad; sub esp,0x100; mov edi,esp (buf)
    a.emit(b"\x8b\x75\xcc")                                  # mov esi,[ebp-0x34] (Seite)
    a.emit(b"\x8d\x8e" + u32(0xE0))
    call_iat(a, "opHWND")
    a.emit(b"\x8b\xd8")                                      # ebx = Aufloesungsliste
    send(a, LB_GETCURSEL, b"\x6a\x00", b"\x6a\x00")
    a.emit(b"\x83\xf8\xff")
    a.jcc("je", "def")
    a.emit(b"\x57\x50\x68" + u32(LB_GETTEXT) + b"\x53")      # LB_GETTEXT(idx, buf)
    call_iat(a, "SendMessageW")
    a.emit(b"\x8b\xcf")                                      # ecx = buf
    a.label("scan")
    a.emit(b"\x0f\xb7\x01\x85\xc0")                          # movzx eax,word [ecx]; test
    a.jcc("jz", "def")
    a.emit(b"\x83\xf8\x78")                                  # 'x'
    a.jcc("je", "found")
    a.emit(b"\x83\xc1\x02")
    a.jmp("scan")
    a.label("found")
    a.emit(b"\x66\xc7\x01\x00\x00\x83\xc1\x02")              # *p = 0; p++
    a.emit(b"\x51\x8d\x4d\xe4")                              # push Y; ecx = &FString Y ([ebp-0x1c])
    call_iat(a, "FStrAssign")
    a.emit(b"\x57\x8d\x4d\xd8")                              # push X; ecx = &FString X ([ebp-0x28])
    call_iat(a, "FStrAssign")
    a.jmp("fps")
    a.label("def")
    a.push_addr("s_480")
    a.emit(b"\x8d\x4d\xe4")
    call_iat(a, "FStrAssign")
    a.push_addr("s_640")
    a.emit(b"\x8d\x4d\xd8")
    call_iat(a, "FStrAssign")
    # --- Bildrate speichern -----------------------------------------------------------------------------
    a.label("fps")
    a.emit(b"\x68" + u32(FPS_LIST_ID) + b"\xff\x76\x04")
    call_iat(a, "GetDlgItem")
    a.emit(b"\x85\xc0")
    a.jcc("jz", "done")
    a.emit(b"\x8b\xd8")
    send(a, LB_GETCURSEL, b"\x6a\x00", b"\x6a\x00")
    a.emit(b"\x83\xf8\xff")
    a.jcc("je", "done")
    a.emit(b"\x57\x50\x68" + u32(LB_GETTEXT) + b"\x53")
    call_iat(a, "SendMessageW")
    a.emit(b"\x8b\xcf")
    a.label("scan2")
    a.emit(b"\x0f\xb7\x01\x85\xc0")
    a.jcc("jz", "write")
    a.emit(b"\x83\xf8\x20")                                  # ' '
    a.jcc("je", "cut")
    a.emit(b"\x83\xc1\x02")
    a.jmp("scan2")
    a.label("cut")
    a.emit(b"\x66\xc7\x01\x00\x00")
    a.label("write")
    a.emit(b"\x6a\x00\x57")                                  # push NULL; push buf ("144")
    a.push_addr("s_key")
    a.push_addr("s_sec")
    a.emit(b"\xa1" + u32(IAT["GConfig"]) + b"\x8b\x08\x8b\x01\xff\x50\x30")   # GConfig->SetString
    a.label("done")
    a.emit(b"\x81\xc4" + u32(0x100) + b"\x61\xc3")
    a.wstr("s_640", "640")
    a.wstr("s_480", "480")
    a.wstr("s_sec", "Engine.GameEngine")
    a.wstr("s_key", "MaxFPS")
    return a.assemble()


def main():
    src = Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT / "SETUP" / "Bears" / "system" / "Game.exe"
    dst = Path(sys.argv[2]) if len(sys.argv) > 2 else ROOT / "game" / "system" / "Game.exe"
    data = bytearray(src.read_bytes())
    if hashlib.sha256(data).hexdigest() != GAME_SHA256:
        sys.exit(f"{src} ist nicht die Original-Game.exe")
    pe = pefile.PE(data=bytes(data))
    base = pe.OPTIONAL_HEADER.ImageBase
    if hasattr(pe, "DIRECTORY_ENTRY_BASERELOC"):
        sys.exit("Game.exe hat Relocations - absolute Adressen im Cave waeren ungueltig")
    text = next(s for s in pe.sections if s.Name.rstrip(b"\0") == b".text")
    core = pefile.PE(str(ROOT / "SETUP" / "Bears" / "system" / "Core.dll"))
    exp = {s.name.decode(): s.address for s in core.DIRECTORY_ENTRY_EXPORT.symbols if s.name}
    a = exp["?appFailAssert@@YAXPBD0H@Z"]
    d_handle = exp["?appGetDllHandle@@YAPAXPBG@Z"] - a
    d_export = exp["?appGetDllExport@@YAPAXPAXPBG@Z"] - a

    rva = (text.VirtualAddress + text.Misc_VirtualSize + 15) & ~15
    fill_va = base + rva
    fill = build_fill_cave(fill_va, d_handle, d_export)
    save_rva = (rva + len(fill) + 15) & ~15
    save_va = base + save_rva
    save = build_save_cave(save_va)
    blob = fill + b"\0" * (save_rva - rva - len(fill)) + save
    off = text.PointerToRawData + (rva - text.VirtualAddress)
    if rva + len(blob) > text.VirtualAddress + text.SizeOfRawData or any(data[off:off + len(blob)]):
        sys.exit("kein freier Platz in .text")
    data[off:off + len(blob)] = blob
    struct.pack_into("<I", data, text.get_file_offset() + 8, rva + len(blob) - text.VirtualAddress)

    def patch_site(site, orig, cave_va, cont):
        o = pe.get_offset_from_rva(site - base)
        if bytes(data[o:o + len(orig)]) != orig:
            sys.exit(f"Originalbytes stimmen nicht bei {site:#x}")
        return o

    o = patch_site(FILL_SITE, FILL_ORIG, fill_va, FILL_CONT)
    data[o:o + 13] = b"\x8b\x4d\xd0" + b"\xe8" + struct.pack("<i", fill_va - (FILL_SITE + 8)) \
        + b"\xe9" + struct.pack("<i", FILL_CONT - (FILL_SITE + 13))
    o = patch_site(SAVE_SITE, SAVE_ORIG, save_va, SAVE_CONT)
    data[o:o + 10] = b"\xe8" + struct.pack("<i", save_va - (SAVE_SITE + 5)) \
        + b"\xe9" + struct.pack("<i", SAVE_CONT - (SAVE_SITE + 10))

    orig_copy = dst.with_name(dst.name + ".orig")
    if dst.exists() and not orig_copy.exists():
        shutil.copy2(dst, orig_copy)
    dst.write_bytes(data)
    print(f"Game.exe gepatcht: Launcher-Aufloesungen + Bildrate (Befuellen @ {fill_va:#x}, Speichern @ {save_va:#x})")


if __name__ == "__main__":
    main()
