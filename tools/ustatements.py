"""Listet die Anweisungen (Top-Level-Statements) einer UnrealScript-Funktion mit Speicher-/Plattenposition,
Groessen und Rohbytes. Nutzt `udecomp --tokens` (UELib) fuer die Token-Grenzen.

Aufruf: python tools/ustatements.py <paket.u> <Klasse> <Funktion> [von_mem_hex bis_mem_hex]
"""
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from upkg import Package, parse_function  # noqa: E402

UDECOMP = Path(__file__).parent / "udecomp"


def statements(pkg_path, cls, fn):
    out = subprocess.run(["dotnet", "run", "-c", "Release", "--no-build", "--project", str(UDECOMP), "--",
                          "--tokens", pkg_path, cls, fn], capture_output=True, text=True).stdout
    head = next(l for l in out.splitlines() if l.startswith("Export "))
    export = int(head.split()[1])
    toks = []
    for l in out.splitlines():
        parts = l.split("\t")
        if len(parts) == 5:
            toks.append((int(parts[0], 16), int(parts[1], 16), int(parts[2]), int(parts[3]), parts[4]))
    data = open(pkg_path, "rb").read()
    pk = Package(data)
    blob = pk.export_data(export - 1)
    _, script_size, s = parse_function(blob)
    stmts, end = [], -1
    for mem, disk, msz, dsz, name in toks:
        if mem >= end:
            stmts.append([mem, disk, msz, dsz, name])
            end = mem + msz
    # UELib meldet bei erweiterten Native-Aufrufen (Token 0x60..0x6F + Indexbyte) die Plattenposition ein Byte
    # zu spaet. Anweisungen liegen lueckenlos hintereinander -> Start = Ende der vorherigen Anweisung.
    expect = 0
    for st in stmts:
        if st[1] != expect:
            assert st[1] - expect == 1 and 0x60 <= blob[s + expect] <= 0x6F, (st, expect)
            st[3] += st[1] - expect
            st[1] = expect
        expect = st[1] + st[3]
    return export, script_size, s, blob, stmts


if __name__ == "__main__":
    pkg, cls, fn = sys.argv[1:4]
    lo = int(sys.argv[4], 16) if len(sys.argv) > 5 else 0
    hi = int(sys.argv[5], 16) if len(sys.argv) > 5 else 1 << 30
    export, script_size, s, blob, stmts = statements(pkg, cls, fn)
    print(f"Export {export}  ScriptSize(mem) {script_size}  Script-Start im Export {s}")
    for mem, disk, msz, dsz, name in stmts:
        if lo <= mem <= hi:
            raw = blob[s + disk:s + disk + dsz].hex(" ")
            print(f"{mem:04X} d{disk:04X} m{msz:3d} d{dsz:3d} {name:24} {raw}")
