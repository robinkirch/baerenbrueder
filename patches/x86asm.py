"""Winziger x86-Hilfsassembler fuer Code-Caves: Bytefolgen + Sprungmarken (alle Spruenge rel32).

    a = X86(base_va)
    a.emit(b"\x60")                 # rohe Bytes
    a.label("loop")
    a.jcc("jz", "done")             # 0F 84 rel32
    a.jmp("loop")                   # E9 rel32
    a.call_va(0x10901234)           # E8 rel32 auf absolute Adresse
    a.addr("str_x")                 # 4-Byte absolute Adresse einer Marke (fuer push imm32 etc.)
    code = a.assemble()
"""
import struct

JCC = {"jo": 0x80, "jno": 0x81, "jb": 0x82, "jae": 0x83, "jz": 0x84, "je": 0x84, "jnz": 0x85, "jne": 0x85,
       "jbe": 0x86, "ja": 0x87, "js": 0x88, "jns": 0x89, "jl": 0x8C, "jge": 0x8D, "jle": 0x8E, "jg": 0x8F}


class X86:
    def __init__(self, base):
        self.base = base
        self.parts = []      # (art, daten)
        self.labels = {}
        self.size = 0

    def emit(self, b):
        self.parts.append(("raw", bytes(b)))
        self.size += len(b)

    def label(self, name):
        self.labels[name] = self.base + self.size

    def jcc(self, cc, label):
        self.parts.append(("rel", (bytes([0x0F, JCC[cc]]), label)))
        self.size += 6

    def jmp(self, label):
        self.parts.append(("rel", (b"\xe9", label)))
        self.size += 5

    def jmp_va(self, va):
        self.parts.append(("relva", (b"\xe9", va)))
        self.size += 5

    def call_va(self, va):
        self.parts.append(("relva", (b"\xe8", va)))
        self.size += 5

    def push_addr(self, label):
        self.parts.append(("abs", (b"\x68", label)))
        self.size += 5

    def wstr(self, label, s):
        self.label(label)
        self.emit(s.encode("utf-16-le") + b"\0\0")

    def assemble(self):
        out = bytearray()
        for kind, d in self.parts:
            pos = self.base + len(out)
            if kind == "raw":
                out += d
            elif kind == "rel":
                op, lab = d
                nxt = pos + len(op) + 4
                out += op + struct.pack("<i", self.labels[lab] - nxt)
            elif kind == "relva":
                op, va = d
                nxt = pos + len(op) + 4
                out += op + struct.pack("<i", va - nxt)
            elif kind == "abs":
                op, lab = d
                out += op + struct.pack("<I", self.labels[lab])
        assert len(out) == self.size
        return bytes(out)
