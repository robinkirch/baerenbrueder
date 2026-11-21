r"""Patch: Launcher-Grafikseite (Dialog-Template #161 in Window.dll) um "Bildrate" erweitern.

Die Seite WFrontEndPageConfigVideo (Game.exe) baut auf Template 161 (DLGTEMPLATEEX, 318x230 DLU) auf.
Aenderungen:
  - Aufloesungsliste (ID 1126) und ihre Beschriftung (ID 1128) schmaler: cx -> 150
  - neu: STATIC "Bildrate" (ID 1200) bei (186,144) 81x12
  - neu: LISTBOX (ID 1201, unsortiert, LBS_NOTIFY) bei (186,156) 60x35
Das vergroesserte Template wird in den freien Platz am Ende von .rsrc geschrieben; der Ressourcen-Dateneintrag
(OffsetToData/Size) und die VirtualSize von .rsrc werden angepasst. Befuellen/Speichern: game_launcher_resolutions.py.

Aufruf: python patches/window_dialog_fps.py [quelle] [ziel]
"""
import hashlib
import shutil
import struct
import sys
from pathlib import Path

import pefile

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "tools"))
from dialogs import parse  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
WINDOW_SHA256 = "f01473b141b6cacc4f412f2869c7c4e6c6d167489df51d8a66a7c52548068291"
DIALOG_ID = 161
RES_LIST_ID = 1126
NEW_RES_CX = 150
FPS_LABEL_ID, FPS_LIST_ID = 1200, 1201


def item_ex(style, x, y, cx, cy, cid, cls_ord, text):
    b = struct.pack("<IIIhhhhI", 0, 0, style, x, y, cx, cy, cid)
    b += struct.pack("<HH", 0xFFFF, cls_ord)
    b += text.encode("utf-16-le") + b"\0\0"
    b += struct.pack("<H", 0)              # keine Extra-Daten
    return b


def main():
    src = Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT / "SETUP" / "Bears" / "system" / "Window.dll"
    dst = Path(sys.argv[2]) if len(sys.argv) > 2 else ROOT / "game" / "system" / "Window.dll"
    data = bytearray(src.read_bytes())
    if hashlib.sha256(data).hexdigest() != WINDOW_SHA256:
        sys.exit(f"{src} ist nicht die Original-Window.dll")
    pe = pefile.PE(data=bytes(data))
    rsrc = next(s for s in pe.sections if s.Name.rstrip(b"\0") == b".rsrc")
    entry = None
    for t in pe.DIRECTORY_ENTRY_RESOURCE.entries:
        if t.id == 5:
            for e in t.directory.entries:
                if e.id == DIALOG_ID:
                    entry = e.directory.entries[0].data.struct
    if entry is None:
        sys.exit("Dialog 161 nicht gefunden")
    tmpl = bytearray(pe.get_data(entry.OffsetToData, entry.Size))
    head, items = parse(bytes(tmpl))
    assert head["ex"] and head["n"] == 9, head

    # Aufloesungsliste verschmaelern (Feld cx im Item: Offset +16 bei DLGTEMPLATEEX-Items)
    res = next(i for i in items if i["id"] == RES_LIST_ID)
    struct.pack_into("<h", tmpl, res["off"] + 16, NEW_RES_CX)
    # Beschriftung "Aufloesung" (ID 1128, 243 breit) wuerde die neue Beschriftung ueberlappen
    lbl = next(i for i in items if i["id"] == 1128)
    struct.pack_into("<h", tmpl, lbl["off"] + 16, NEW_RES_CX)

    # Neue Items anhaengen (DWORD-ausgerichtet)
    while len(tmpl) % 4:
        tmpl += b"\0"
    tmpl += item_ex(0x50020000, 186, 144, 81, 12, FPS_LABEL_ID, 0x82, "Bildrate")
    while len(tmpl) % 4:
        tmpl += b"\0"
    tmpl += item_ex(0x50A10101, 186, 156, 60, 35, FPS_LIST_ID, 0x83, "")
    struct.pack_into("<H", tmpl, 16, head["n"] + 2)       # cDlgItems
    _, new_items = parse(bytes(tmpl))
    assert len(new_items) == 11

    # In den freien Platz von .rsrc schreiben
    new_rva = (rsrc.VirtualAddress + rsrc.Misc_VirtualSize + 3) & ~3
    end_rva = new_rva + len(tmpl)
    if end_rva > rsrc.VirtualAddress + rsrc.SizeOfRawData:
        sys.exit("kein Platz in .rsrc")
    off = rsrc.PointerToRawData + (new_rva - rsrc.VirtualAddress)
    if any(data[off:off + len(tmpl)]):
        sys.exit(".rsrc-Restplatz nicht leer")
    data[off:off + len(tmpl)] = tmpl
    ent_off = entry.get_file_offset()
    struct.pack_into("<II", data, ent_off, new_rva, len(tmpl))                    # OffsetToData, Size
    struct.pack_into("<I", data, rsrc.get_file_offset() + 8, end_rva - rsrc.VirtualAddress)   # VirtualSize
    dd = pe.OPTIONAL_HEADER.DATA_DIRECTORY[2]
    struct.pack_into("<I", data, dd.get_file_offset() + 4, end_rva - dd.VirtualAddress)      # Resource-Dir-Groesse

    orig_copy = dst.with_name(dst.name + ".orig")
    if dst.exists() and not orig_copy.exists():
        shutil.copy2(dst, orig_copy)
    dst.write_bytes(data)
    print(f"Window.dll gepatcht: Dialog 161 um 'Bildrate' erweitert ({len(tmpl)} Bytes @ RVA {new_rva:#x})")


if __name__ == "__main__":
    main()
