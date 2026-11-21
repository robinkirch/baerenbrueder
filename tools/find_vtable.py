"""Findet die vtable einer Klasse in einer UE1-DLL anhand der guard-Strings ihrer Methoden.

Aufruf: python tools/find_vtable.py <dll> <Klassenpraefix, z. B. FConfigCacheIni::>
Jede Methode mit guard(Klasse::Methode) referenziert ihren Namen als UTF-16-String; die vtable ist die
Zeigerfolge in .rdata, die solche Funktionen enthaelt.
"""
import bisect
import re
import struct
import sys

import pefile
from capstone import CS_ARCH_X86, CS_MODE_32, Cs

dll, prefix = sys.argv[1], sys.argv[2]
pe = pefile.PE(dll)
base = pe.OPTIONAL_HEADER.ImageBase
data = pe.__data__
strs = {}
for m in re.finditer(rb"(?:[\x20-\x7e]\x00){6,}", data):
    s = m.group().decode("utf-16-le")
    if s.startswith(prefix):
        strs[base + pe.get_rva_from_offset(m.start())] = s
text = next(s for s in pe.sections if s.Name.startswith(b".text"))
tlo, thi = base + text.VirtualAddress, base + text.VirtualAddress + text.Misc_VirtualSize
ins = list(Cs(CS_ARCH_X86, CS_MODE_32).disasm(text.get_data(), tlo))
starts = [i.address for i in ins if i.mnemonic == "push" and i.op_str == "ebp"]
fn = {}
for i in ins:
    for a, s in strs.items():
        if hex(a) in i.op_str:
            k = bisect.bisect_right(starts, i.address) - 1
            fn[starts[k]] = s
rdata = next(s for s in pe.sections if s.Name.startswith(b".rdata"))
rd = rdata.get_data()
seen = set()
for off in range(0, len(rd) - 4, 4):
    v = struct.unpack_from("<I", rd, off)[0]
    if v not in fn:
        continue
    st = off
    while st >= 4 and tlo <= struct.unpack_from("<I", rd, st - 4)[0] < thi:
        st -= 4
    if st in seen:
        continue
    seen.add(st)
    print(f"vtable @ {base + rdata.VirtualAddress + st:#x}")
    for k in range(40):
        e = struct.unpack_from("<I", rd, st + 4 * k)[0]
        if not tlo <= e < thi:
            break
        print(f"  [{k:2d}] +0x{4 * k:02x} {e:#x} {fn.get(e, '')}")
