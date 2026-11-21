"""Minimaler Lese-/Schreibzugriff auf Unreal-1-Pakete (Version 6x-8x) fuer Patches mit Groessenaenderung.

Strategie fuer Groessenaenderungen: Die neuen Objektdaten (z. B. eine vergroesserte Funktion) werden HINTER die
bestehenden Objektdaten und VOR die Import-/Exporttabelle gelegt. Der Exporteintrag zeigt auf die neue Position.
Alle uebrigen Daten bleiben byte-genau an ihrer Stelle (wichtig fuer TLazyArray mit absoluten Offsets in
Texturen/Sounds). Nur Import- und Exporttabelle wandern nach hinten; der Header wird angepasst.

Header (UE1): Tag, FileVersion(u16), LicenseeVersion(u16), PackageFlags, NameCount, NameOffset,
ExportCount, ExportOffset, ImportCount, ImportOffset, (GUID, Generations ...).
Exporteintrag: ClassIndex(ci), SuperIndex(ci), PackageIndex(i32), ObjectName(ci), ObjectFlags(u32),
SerialSize(ci), [SerialOffset(ci) wenn SerialSize > 0].
"""
import struct


def read_ci(b, p):
    """FCompactIndex lesen -> (wert, neue_position)."""
    x = b[p]
    p += 1
    neg = x & 0x80
    v = x & 0x3F
    if x & 0x40:
        shift = 6
        while True:
            y = b[p]
            p += 1
            v |= (y & 0x7F) << shift
            shift += 7
            if not y & 0x80:
                break
    return (-v if neg else v), p


def write_ci(n):
    neg, v = n < 0, abs(n)
    out = [(0x80 if neg else 0) | (v & 0x3F) | (0x40 if v > 0x3F else 0)]
    v >>= 6
    while v:
        out.append((v & 0x7F) | (0x80 if v > 0x7F else 0))
        v >>= 7
    return bytes(out)


class Package:
    def __init__(self, data):
        self.data = bytearray(data)
        (self.tag, self.ver, self.lic, self.flags, self.name_count, self.name_off, self.export_count,
         self.export_off, self.import_count, self.import_off) = struct.unpack_from("<IHHIIIIIII", self.data, 0)
        assert self.tag == 0x9E2A83C1
        self.names = self._read_names()
        self.exports = self._read_exports()
        self._import_end = self._scan_imports_end()

    def _read_names(self):
        p, names = self.name_off, []
        for _ in range(self.name_count):
            if self.ver >= 64:
                n, p = read_ci(self.data, p)
                s = bytes(self.data[p:p + n]).rstrip(b"\0").decode("latin-1")
                p += n
            else:
                e = self.data.index(0, p)
                s = bytes(self.data[p:e]).decode("latin-1")
                p = e + 1
            p += 4  # Flags
            names.append(s)
        return names

    def _read_exports(self):
        p, ex = self.export_off, []
        for _ in range(self.export_count):
            start = p
            cls, p = read_ci(self.data, p)
            sup, p = read_ci(self.data, p)
            pkg = struct.unpack_from("<i", self.data, p)[0]
            p += 4
            name, p = read_ci(self.data, p)
            flags = struct.unpack_from("<I", self.data, p)[0]
            p += 4
            size, p = read_ci(self.data, p)
            off = 0
            if size > 0:
                off, p = read_ci(self.data, p)
            ex.append(dict(cls=cls, sup=sup, pkg=pkg, name=name, flags=flags, size=size, off=off,
                           entry=(start, p)))
        self._export_end = p
        return ex

    def _scan_imports_end(self):
        p = self.import_off
        for _ in range(self.import_count):
            _, p = read_ci(self.data, p)   # ClassPackage (Name)
            _, p = read_ci(self.data, p)   # ClassName (Name)
            p += 4                          # PackageIndex
            _, p = read_ci(self.data, p)   # ObjectName (Name)
        return p

    def export_name(self, i):
        return self.names[self.exports[i]["name"]]

    def export_data(self, i):
        e = self.exports[i]
        return bytes(self.data[e["off"]:e["off"] + e["size"]])

    def build(self, replacements):
        """replacements: {export_index (0-basiert): neue_daten}. Gibt die neue Paketdatei zurueck."""
        assert self.import_off < self.export_off, "erwarte Importtabelle vor Exporttabelle"
        assert self._import_end == self.export_off, "Luecke zwischen Import- und Exporttabelle"
        assert self._export_end == len(self.data), "Daten hinter der Exporttabelle"
        tables_start = self.import_off
        out = bytearray(self.data[:tables_start])
        new_pos = {}
        for i, blob in replacements.items():
            new_pos[i] = (len(out), len(blob))
            out += blob
        new_import_off = len(out)
        out += self.data[self.import_off:self._import_end]
        new_export_off = len(out)
        for i, e in enumerate(self.exports):
            off, size = new_pos.get(i, (e["off"], e["size"]))
            out += write_ci(e["cls"]) + write_ci(e["sup"]) + struct.pack("<i", e["pkg"]) + write_ci(e["name"])
            out += struct.pack("<I", e["flags"]) + write_ci(size)
            if size > 0:
                out += write_ci(off)
        struct.pack_into("<I", out, 24, new_export_off)   # ExportOffset (Header: Tag,Ver,Lic,Flags,NameCnt,NameOff,ExpCnt,ExpOff,...)
        struct.pack_into("<I", out, 32, new_import_off)   # ImportOffset
        return bytes(out)


def parse_function(blob):
    """Zerlegt die Serialisierung einer UFunction (v80): (kopf_bis_vor_ScriptSize, script_size, script, rest).
    Kopf: None(ci) SuperField(ci) Next(ci) ScriptText(ci) Children(ci) FriendlyName(ci) Line(i32) TextPos(i32)."""
    p = 0
    for _ in range(6):
        _, p = read_ci(blob, p)
    p += 8
    head = blob[:p]
    script_size = struct.unpack_from("<I", blob, p)[0]
    return head, script_size, p + 4


def rebuild_function(blob, new_script, new_mem_size, script_disk_len):
    """Ersetzt den Script-Teil (Plattenlaenge script_disk_len ab Script-Start) und setzt ScriptSize."""
    head, _, s = parse_function(blob)
    tail = blob[s + script_disk_len:]
    return head + struct.pack("<I", new_mem_size) + new_script + tail
