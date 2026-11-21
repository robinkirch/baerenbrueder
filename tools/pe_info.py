"""PE-Infos fuer die Spiel-Binaries: Imports (optional gefiltert nach DLL) und Exports.

Aufruf:
  python tools/pe_info.py imports <datei> [dll-filter]
  python tools/pe_info.py exports <datei> [namens-filter]
"""
import sys

import pefile


def imports(path, flt=None):
    pe = pefile.PE(path)
    for entry in getattr(pe, "DIRECTORY_ENTRY_IMPORT", []):
        dll = entry.dll.decode(errors="replace")
        if flt and flt.lower() not in dll.lower():
            continue
        names = [i.name.decode() if i.name else f"#{i.ordinal}" for i in entry.imports]
        print(f"{dll} ({len(names)}):")
        for n in names:
            print(f"  {n}")


def exports(path, flt=None):
    pe = pefile.PE(path)
    if not hasattr(pe, "DIRECTORY_ENTRY_EXPORT"):
        print("keine Exports")
        return
    base = pe.OPTIONAL_HEADER.ImageBase
    for s in pe.DIRECTORY_ENTRY_EXPORT.symbols:
        name = s.name.decode() if s.name else f"#{s.ordinal}"
        if flt and flt.lower() not in name.lower():
            continue
        print(f"{base + s.address:08x}  {name}")


if __name__ == "__main__":
    mode, path = sys.argv[1], sys.argv[2]
    flt = sys.argv[3] if len(sys.argv) > 3 else None
    {"imports": imports, "exports": exports}[mode](path, flt)
