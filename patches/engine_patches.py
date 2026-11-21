r"""Patch: konfigurierbares FPS-Limit im Einzelspieler (Engine.dll), Wert aus der INI.

Problem
-------
`UGameEngine::GetMaxTickRate` (0x1035c1c0) liefert im Einzelspieler 0.0 (= unbegrenzt). Die Hauptschleife in
Game.exe (FUN_10905f3a) schlaeft nur, wenn dieser Wert > 0 ist. Auf modernen PCs laeuft das Spiel mit
150-1600 FPS; bei hohen Frameraten melden Cutscene-Befehle (Say/Talk) vorzeitig "fertig" -> Dialoge
ueberlagern sich, Kamerafahrten springen (Messungen: notes\logs\run-06 .. run-09).
Zusaetzlich: appSleep() nutzt Sleep(); ohne timeBeginPeriod(1) hat Sleep unter Windows ~15.6 ms
Aufloesung -> jede Begrenzung landet bei ~64 FPS.

Fix
---
1. Am Funktionsanfang (0x1035c1c0, `push ebp; mov ebp,esp; push -1`) springt ein `jmp` in einen Code-Cave im
   freien Bereich hinter .text. Der Cave laeuft nur beim ersten Aufruf (Flag) und
   - liest `[Engine.GameEngine] MaxFPS` per `GConfig->GetFloat` (vtable +8) aus Game.ini,
   - klemmt den Wert auf 20..240, sonst/fehlend -> 60,
   - ruft `timeBeginPeriod(1)` ueber Core `appGetDllHandle`/`appGetDllExport` (Adressen relativ zum
     Engine-Import `appFailAssert` berechnet -> unabhaengig von der Ladeadresse von Core),
   - fuehrt die ueberschriebenen Original-Bytes aus und springt zurueck.
   Der Cave ist positionsunabhaengig (call/pop), braucht also keine neuen Relocations.
2. Der Einzelspieler-Zweig (0x1035c366, `fld [0x10426c78]` = 0.0) laedt stattdessen den gelesenen Wert.
   Der Operand hat bereits einen DIR32-Relocation-Eintrag, der weiter gueltig ist.
3. Variablen (Wert, Flag) liegen im BSS-Rest von .data (VirtualSize +8), Code/Strings im Rest von .text.

Aufruf: python patches/engine_maxfps.py [quelle] [ziel]
  Standard: quelle=SETUP\Bears\system\Engine.dll, ziel=game\system\Engine.dll
"""
import hashlib
import shutil
import struct
import sys
from pathlib import Path

import pefile

ROOT = Path(__file__).resolve().parent.parent
ENGINE_SHA256 = "0f8b4611ec496f34559414a65ff6874f631b0cf72bd2ede2d94d0f40b8da70b1"
CORE = ROOT / "game" / "system" / "Core.dll"

FUNC_VA = 0x1035C1C0
FUNC_ORIG = bytes.fromhex("558bec6aff")          # push ebp; mov ebp,esp; push -1
EXEC_VA = 0x1035E8B0                   # UGameEngine::Exec (gleicher Prolog wie GetMaxTickRate)

# Hor+-Widescreen: FSceneNode::ComputeRenderSize (0x1034d5b0) berechnet T = tan(FovAngle/2) und daraus die
# Projektion FX/2 / T -> bei Breitbild bleibt das horizontale FOV, vertikal wird abgeschnitten ("Zoom").
# An 0x1034d67e (fstp qword [ebp-0x30]; fld dword [eax+0xb8]) -> call WS_CAVE; nop*4. Der Cave speichert T,
# multipliziert es mit k = max(1, (FX/FY) * 0.75) (FX/FY: [this+0xb8]/[this+0xbc], eax = this) und fuehrt die
# ueberschriebene fld-Anweisung aus. Ergebnis: vertikales Sichtfeld wie in 4:3 bei jeder Breite.
WS_VA = 0x1034D67E
WS_ORIG = bytes.fromhex("dd5dd0d980b8000000")
WS_CAVE = bytes.fromhex(
    "dd5dd0"            # 00 fstp qword [ebp-0x30]      T sichern (Original)
    "d980b8000000"      # 03 fld  dword [eax+0xb8]      FX
    "d8b0bc000000"      # 09 fdiv dword [eax+0xbc]      FX/FY
    "680000403f"        # 0f push 0.75f
    "d80c24"            # 14 fmul dword [esp]           k = Seitenverhaeltnis * 3/4
    "d9e8"              # 17 fld1
    "dff1"              # 19 fcomip st(0), st(1)        1.0 >= k ?
    "7308"              # 1b jae skip
    "dc4dd0"            # 1d fmul qword [ebp-0x30]      k * T
    "dd5dd0"            # 20 fstp qword [ebp-0x30]
    "eb02"              # 23 jmp end
    "ddd8"              # 25 skip: fstp st(0)
    "83c404"            # 27 end: add esp,4
    "d980b8000000"      # 2a fld dword [eax+0xb8]       (Original)
    "c3")               # 30 ret
FLD_VA = 0x1035C366
FLD_ORIG = bytes.fromhex("d905786c4210")         # fld dword ptr [0x10426c78]

SECTION = "Engine.GameEngine"
KEY = "MaxFPS"
F_MIN, F_MAX, F_DEF = 20.0, 240.0, 60.0


def u16z(s):
    return s.encode("utf-16-le") + b"\0\0"


def section(pe, name):
    return next(s for s in pe.sections if s.Name.rstrip(b"\0") == name)


def import_slot(pe, dll, name):
    for e in pe.DIRECTORY_ENTRY_IMPORT:
        if e.dll.decode().lower() == dll.lower():
            for i in e.imports:
                if i.name and i.name.decode() == name:
                    return i.address
    raise KeyError(name)


def export_rva(pe, name):
    for s in pe.DIRECTORY_ENTRY_EXPORT.symbols:
        if s.name and s.name.decode() == name:
            return s.address
    raise KeyError(name)


def build(data):
    pe = pefile.PE(data=bytes(data))
    base = pe.OPTIONAL_HEADER.ImageBase
    text, dsec = section(pe, b".text"), section(pe, b".data")

    # Adressen
    cave_rva = (text.VirtualAddress + text.Misc_VirtualSize + 15) & ~15
    value_rva = (dsec.VirtualAddress + dsec.Misc_VirtualSize + 7) & ~7
    flag_rva = value_rva + 4
    gconfig_slot = import_slot(pe, "Core.dll", "?GConfig@@3PAVFConfigCache@@A")
    assert_slot = import_slot(pe, "Core.dll", "?appFailAssert@@YAXPBD0H@Z")
    core = pefile.PE(str(CORE))
    a = export_rva(core, "?appFailAssert@@YAXPBD0H@Z")
    d_handle = export_rva(core, "?appGetDllHandle@@YAPAXPBG@Z") - a
    d_export = export_rva(core, "?appGetDllExport@@YAPAXPAXPBG@Z") - a

    code_len = 0xA9
    strings = {}
    blob = b""
    for k, s in (("sec", SECTION), ("key", KEY), ("winmm", "winmm.dll"), ("tbp", "timeBeginPeriod")):
        strings[k] = cave_rva + code_len + len(blob)
        blob += u16z(s)

    here = base + cave_rva + 6                       # Adresse nach `call .here`
    d = lambda rva: struct.pack("<i", base + rva - here)
    d_va = lambda va: struct.pack("<i", va - here)
    i32 = lambda v: struct.pack("<i", v)
    f32 = lambda v: struct.pack("<f", v)

    c = b""
    c += b"\x60"                                     # 00 pushad
    c += b"\xe8\x00\x00\x00\x00"                     # 01 call .here
    c += b"\x5b"                                     # 06 pop ebx
    c += b"\x80\xbb" + d(flag_rva) + b"\x00"         # 07 cmp byte [ebx+FLAG],0
    c += b"\x0f\x85" + i32(0x9E - 0x14)              # 0e jne .done
    c += b"\xc6\x83" + d(flag_rva) + b"\x01"         # 14 mov byte [ebx+FLAG],1
    c += b"\x8b\x83" + d_va(gconfig_slot)            # 1b mov eax,[ebx+IAT_GConfig]
    c += b"\x8b\x08"                                 # 21 mov ecx,[eax]
    c += b"\x85\xc9"                                 # 23 test ecx,ecx
    c += b"\x74" + bytes([0x43 - 0x27])              # 25 jz .clamp
    c += b"\x6a\x00"                                 # 27 push 0 (Filename)
    c += b"\x8d\x83" + d(value_rva) + b"\x50"        # 29 lea eax,[VALUE]; push eax
    c += b"\x8d\x83" + d(strings["key"]) + b"\x50"   # 30 lea eax,[KEY]; push eax
    c += b"\x8d\x83" + d(strings["sec"]) + b"\x50"   # 37 lea eax,[SEC]; push eax
    c += b"\x8b\x01"                                 # 3e mov eax,[ecx]
    c += b"\xff\x50\x08"                             # 40 call [eax+8]  (GetFloat, thiscall)
    c += b"\x8b\x83" + d(value_rva)                  # 43 .clamp: mov eax,[VALUE]
    c += b"\x3d" + f32(F_MIN)                        # 49 cmp eax,20.0f
    c += b"\x7c\x07"                                 # 4e jl .bad
    c += b"\x3d" + f32(F_MAX)                        # 50 cmp eax,240.0f
    c += b"\x7e\x0a"                                 # 55 jle .timer
    c += b"\xc7\x83" + d(value_rva) + f32(F_DEF)     # 57 .bad: mov dword [VALUE],60.0f
    c += b"\x8b\x83" + d_va(assert_slot)             # 61 .timer: mov eax,[IAT_appFailAssert]
    c += b"\x05" + i32(d_handle)                     # 67 add eax,appGetDllHandle-appFailAssert
    c += b"\x8d\x8b" + d(strings["winmm"])           # 6c lea ecx,[L"winmm.dll"]
    c += b"\x51\xff\xd0\x83\xc4\x04"                 # 72 push ecx; call eax; add esp,4
    c += b"\x85\xc0\x74" + bytes([0x9E - 0x7C])      # 78 test eax,eax; jz .done
    c += b"\x89\xc6"                                 # 7c mov esi,eax
    c += b"\x8b\x83" + d_va(assert_slot)             # 7e mov eax,[IAT_appFailAssert]
    c += b"\x05" + i32(d_export)                     # 84 add eax,appGetDllExport-appFailAssert
    c += b"\x8d\x8b" + d(strings["tbp"])             # 89 lea ecx,[L"timeBeginPeriod"]
    c += b"\x51\x56\xff\xd0\x83\xc4\x08"             # 8f push ecx; push esi; call eax; add esp,8
    c += b"\x85\xc0\x74\x04"                         # 96 test eax,eax; jz .done
    c += b"\x6a\x01\xff\xd0"                         # 9a push 1; call eax  (timeBeginPeriod, stdcall)
    c += b"\x61"                                     # 9e .done: popad
    c += FUNC_ORIG                                   # 9f Original-Bytes
    c += b"\xe9" + i32((FUNC_VA + 5) - (base + cave_rva + 0xA9))  # a4 jmp zurueck
    assert len(c) == code_len, hex(len(c))
    cave = c + blob

    # --- Zweiter Cave: Konsolenbefehle MAXFPS <n> / GETMAXFPS in UGameEngine::Exec -------------------------
    exec_rva = (cave_rva + len(cave) + 15) & ~15
    exec_cave = build_exec_cave(pe, base, exec_rva, value_rva, gconfig_slot)
    cave += b"\0" * (exec_rva - cave_rva - len(cave)) + exec_cave

    # --- Dritter Cave: Hor+-Widescreen in FSceneNode::ComputeRenderSize ---------------------------------------
    ws_rva = (cave_rva + len(cave) + 15) & ~15
    cave += b"\0" * (ws_rva - cave_rva - len(cave)) + WS_CAVE

    # Platz pruefen
    if cave_rva + len(cave) > text.VirtualAddress + text.SizeOfRawData:
        sys.exit("kein Platz in .text")
    cave_off = text.PointerToRawData + (cave_rva - text.VirtualAddress)
    if any(data[cave_off:cave_off + len(cave)]):
        sys.exit("Cave-Bereich nicht leer")

    # Schreiben
    data[cave_off:cave_off + len(cave)] = cave
    struct.pack_into("<I", data, text.get_file_offset() + 8, cave_rva + len(cave) - text.VirtualAddress)

    w_off = pe.get_offset_from_rva(WS_VA - base)
    if bytes(data[w_off:w_off + len(WS_ORIG)]) != WS_ORIG:
        sys.exit("Original-Bytes in ComputeRenderSize stimmen nicht")
    data[w_off:w_off + len(WS_ORIG)] = b"\xe8" + i32((base + ws_rva) - (WS_VA + 5)) + b"\x90" * (len(WS_ORIG) - 5)

    x_off = pe.get_offset_from_rva(EXEC_VA - base)
    if bytes(data[x_off:x_off + 5]) != FUNC_ORIG:
        sys.exit("Original-Bytes am Anfang von UGameEngine::Exec stimmen nicht")
    data[x_off:x_off + 5] = b"\xe9" + i32((base + exec_rva) - (EXEC_VA + 5))
    struct.pack_into("<I", data, dsec.get_file_offset() + 8, flag_rva + 4 - dsec.VirtualAddress)

    f_off = pe.get_offset_from_rva(FUNC_VA - base)
    if bytes(data[f_off:f_off + 5]) != FUNC_ORIG:
        sys.exit("Original-Bytes am Funktionsanfang stimmen nicht")
    data[f_off:f_off + 5] = b"\xe9" + i32((base + cave_rva) - (FUNC_VA + 5))

    l_off = pe.get_offset_from_rva(FLD_VA - base)
    if bytes(data[l_off:l_off + 6]) != FLD_ORIG:
        sys.exit("Original-Bytes am fld stimmen nicht")
    data[l_off + 2:l_off + 6] = struct.pack("<I", base + value_rva)

    return dict(cave=base + cave_rva, cave_len=len(cave), value=base + value_rva, flag=base + flag_rva)


def build_exec_cave(pe, base, rva, value_rva, gconfig_slot):
    """UGameEngine::Exec-Hook (positionsunabhaengig, thiscall: ecx=this, [esp+4]=Cmd, [esp+8]=Ar):
        if (ParseCommand(&Cmd, "MAXFPS"))    { Wert = Clamp(appAtof(Cmd)); GConfig->SetFloat(SEC, KEY, Wert); return 1; }
        if (ParseCommand(&Cmd, "GETMAXFPS")) { Ar.Logf("%i", (int)Wert); return 1; }
        sonst Original-Prolog ausfuehren und in Exec weiterlaufen."""
    slot = lambda n: import_slot(pe, "Core.dll", n)
    iat_parse = slot("?ParseCommand@@YAHPAPBGPBG@Z")
    iat_atof = slot("?appAtof@@YAMPBG@Z")
    iat_logf = slot("?Logf@FOutputDevice@@QAAXPBGZZ")
    code_len = 0xCC
    strs, blob = {}, b""
    for k, s in (("set", "MAXFPS"), ("get", "GETMAXFPS"), ("fmt", "%i"), ("sec", SECTION), ("key", KEY)):
        strs[k] = rva + code_len + len(blob)
        blob += u16z(s)
    here = base + rva + 7
    d = lambda r: struct.pack("<i", base + r - here)
    d_va = lambda va: struct.pack("<i", va - here)
    f32 = lambda v: struct.pack("<f", v)
    c = b""
    c += b"\x51\x53"                                  # 00 push ecx; push ebx
    c += b"\xe8\x00\x00\x00\x00\x5b"                  # 02 call .h; .h: pop ebx
    c += b"\x8d\x83" + d(strs["set"]) + b"\x50"       # 08 lea eax,"MAXFPS"; push eax
    c += b"\x8d\x44\x24\x10\x50"                      # 0f lea eax,&Cmd; push eax
    c += b"\xff\x93" + d_va(iat_parse)                # 14 call ParseCommand
    c += b"\x83\xc4\x08\x85\xc0"                      # 1a add esp,8; test eax,eax
    c += b"\x75" + bytes([0x46 - 0x21])               # 1f jnz .set
    c += b"\x8d\x83" + d(strs["get"]) + b"\x50"       # 21 lea eax,"GETMAXFPS"; push eax
    c += b"\x8d\x44\x24\x10\x50"                      # 28 lea eax,&Cmd; push eax
    c += b"\xff\x93" + d_va(iat_parse)                # 2d call ParseCommand
    c += b"\x83\xc4\x08\x85\xc0"                      # 33 add esp,8; test eax,eax
    c += b"\x75" + bytes([0xA4 - 0x3A])               # 38 jnz .get
    c += b"\x5b\x59"                                  # 3a pop ebx; pop ecx
    c += FUNC_ORIG                                    # 3c Original-Prolog
    c += b"\xe9" + struct.pack("<i", (EXEC_VA + 5) - (base + rva + 0x46))   # 41 jmp Exec+5
    assert len(c) == 0x46
    c += b"\xff\x74\x24\x0c"                          # 46 .set: push Cmd
    c += b"\xff\x93" + d_va(iat_atof)                 # 4a call appAtof (-> st0)
    c += b"\x83\xc4\x04"                              # 50 add esp,4
    c += b"\xd9\x9b" + d(value_rva)                   # 53 fstp [VALUE]
    c += b"\x8b\x83" + d(value_rva)                   # 59 mov eax,[VALUE]
    c += b"\x3d" + f32(F_MIN) + b"\x7c\x07"           # 5f cmp 20.0; jl .bad
    c += b"\x3d" + f32(F_MAX) + b"\x7e\x0a"           # 66 cmp 240.0; jle .ok
    c += b"\xc7\x83" + d(value_rva) + f32(F_DEF)      # 6d .bad: [VALUE] = 60.0
    c += b"\x6a\x00"                                  # 77 .ok: push NULL (Filename)
    c += b"\xff\xb3" + d(value_rva)                   # 79 push [VALUE]
    c += b"\x8d\x83" + d(strs["key"]) + b"\x50"       # 7f push KEY
    c += b"\x8d\x83" + d(strs["sec"]) + b"\x50"       # 86 push SEC
    c += b"\x8b\x83" + d_va(gconfig_slot)             # 8e mov eax,[IAT_GConfig]
    c += b"\x8b\x08\x8b\x01\xff\x50\x2c"              # 94 mov ecx,[eax]; mov eax,[ecx]; call [eax+0x2c] (SetFloat)
    c += b"\x5b\x59\xb8\x01\x00\x00\x00\xc2\x08\x00"  # 9b pop ebx; pop ecx; mov eax,1; ret 8
    assert len(c) == 0xA4, hex(len(c))
    c += b"\xd9\x83" + d(value_rva)                   # a5 .get: fld [VALUE]
    c += b"\x51\xdb\x1c\x24"                          # ab push ecx; fistp [esp]  (int-Argument)
    c += b"\x8d\x83" + d(strs["fmt"]) + b"\x50"       # af push L"%i"
    c += b"\xff\x74\x24\x18"                          # b6 push Ar
    c += b"\xff\x93" + d_va(iat_logf)                 # ba call FOutputDevice::Logf (cdecl)
    c += b"\x83\xc4\x0c"                              # c0 add esp,12
    c += b"\x5b\x59\xb8\x01\x00\x00\x00\xc2\x08\x00"  # c3 pop ebx; pop ecx; mov eax,1; ret 8
    assert len(c) == code_len, hex(len(c))
    return c + blob


def main():
    src = Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT / "SETUP" / "Bears" / "system" / "Engine.dll"
    dst = Path(sys.argv[2]) if len(sys.argv) > 2 else ROOT / "game" / "system" / "Engine.dll"
    data = bytearray(src.read_bytes())
    if hashlib.sha256(data).hexdigest() != ENGINE_SHA256:
        sys.exit(f"{src} ist nicht die Original-Engine.dll")
    info = build(data)
    orig_copy = dst.with_name(dst.name + ".orig")
    if dst.exists() and not orig_copy.exists():
        shutil.copy2(dst, orig_copy)
    dst.write_bytes(data)
    print(f"Engine.dll gepatcht: MaxFPS aus [{SECTION}] {KEY} (Standard {F_DEF:g}, erlaubt {F_MIN:g}..{F_MAX:g})")
    print(f"  Cave @ {info['cave']:#x} ({info['cave_len']} Bytes), Wert @ {info['value']:#x}, Flag @ {info['flag']:#x}")


if __name__ == "__main__":
    main()
