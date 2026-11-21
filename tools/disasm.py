"""Disassembliert eine Funktion aus einer PE-Datei ab einer virtuellen Adresse.

Aufruf: python tools/disasm.py <datei> <va-hex> [max_bytes]
Stoppt nach dem ersten 'ret' (oder max_bytes). Gibt zusaetzlich den Datei-Offset aus.
"""
import sys

import pefile
from capstone import CS_ARCH_X86, CS_MODE_32, Cs

path, va = sys.argv[1], int(sys.argv[2], 16)
max_bytes = int(sys.argv[3]) if len(sys.argv) > 3 else 512
pe = pefile.PE(path)
rva = va - pe.OPTIONAL_HEADER.ImageBase
off = pe.get_offset_from_rva(rva)
code = pe.__data__[off:off + max_bytes]
md = Cs(CS_ARCH_X86, CS_MODE_32)
for ins in md.disasm(code, va):
    foff = off + (ins.address - va)
    print(f"{ins.address:08x} (file {foff:06x})  {ins.bytes.hex():<16} {ins.mnemonic} {ins.op_str}")
    if ins.mnemonic.startswith("ret"):
        break
