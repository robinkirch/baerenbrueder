"""Listet Dialog-Ressourcen (RT_DIALOG) einer PE-Datei mit allen Steuerelementen.

Aufruf: python tools/dialogs.py <exe/dll> [namensfilter]
Unterstuetzt DLGTEMPLATE und DLGTEMPLATEEX.
"""
import struct
import sys

import pefile

CLASSES = {0x80: "BUTTON", 0x81: "EDIT", 0x82: "STATIC", 0x83: "LISTBOX", 0x84: "SCROLLBAR", 0x85: "COMBOBOX"}


def sz_or_ord(b, p):
    if struct.unpack_from("<H", b, p)[0] == 0xFFFF:
        return ("#%d" % struct.unpack_from("<H", b, p + 2)[0]), p + 4
    e = p
    while struct.unpack_from("<H", b, e)[0]:
        e += 2
    return b[p:e].decode("utf-16-le"), e + 2


def parse(b):
    ex = struct.unpack_from("<HH", b, 0) == (1, 0xFFFF)
    if ex:
        _, _, helpid, exstyle, style, n, x, y, cx, cy = struct.unpack_from("<HHIIIHhhhh", b, 0)
        p = 26
    else:
        style, exstyle, n, x, y, cx, cy = struct.unpack_from("<IIHhhhh", b, 0)
        p = 18
    menu, p = sz_or_ord(b, p)
    cls, p = sz_or_ord(b, p)
    title, p = sz_or_ord(b, p)
    font = None
    if style & 0x40:  # DS_SETFONT
        if ex:
            pt, weight, italic, charset = struct.unpack_from("<HHBB", b, p)
            p += 6
        else:
            pt = struct.unpack_from("<H", b, p)[0]
            p += 2
        font, p = sz_or_ord(b, p)
        font = f"{font} {pt}pt"
    head = dict(ex=ex, style=style, x=x, y=y, cx=cx, cy=cy, title=title, font=font, n=n)
    items = []
    for _ in range(n):
        p = (p + 3) & ~3
        start = p
        if ex:
            helpid, exst, st, ix, iy, icx, icy, cid = struct.unpack_from("<IIIhhhhI", b, p)
            p += 24
        else:
            st, exst, ix, iy, icx, icy, cid = struct.unpack_from("<IIhhhhH", b, p)
            p += 18
        c, p = sz_or_ord(b, p)
        if c.startswith("#"):
            c = CLASSES.get(int(c[1:]), c)
        t, p = sz_or_ord(b, p)
        extra = struct.unpack_from("<H", b, p)[0]
        p += 2 + extra
        items.append(dict(cls=c, text=t, id=cid, x=ix, y=iy, cx=icx, cy=icy, style=st, exstyle=exst, off=start))
    return head, items


if __name__ == "__main__":
    pe = pefile.PE(sys.argv[1])
    flt = sys.argv[2] if len(sys.argv) > 2 else ""
    for t in pe.DIRECTORY_ENTRY_RESOURCE.entries:
        if t.id != 5:
            continue
        for e in t.directory.entries:
            name = str(e.name) if e.name else f"#{e.id}"
            if flt.lower() not in name.lower():
                continue
            for lang in e.directory.entries:
                d = lang.data.struct
                b = pe.get_data(d.OffsetToData, d.Size)
                head, items = parse(b)
                print(f"== {name} (lang {lang.id}) RVA {d.OffsetToData:#x} Size {d.Size}  {head}")
                for it in items:
                    print(f"   {it['cls']:10} id={it['id']:5} ({it['x']:4},{it['y']:4}) {it['cx']:4}x{it['cy']:<4} "
                          f"style={it['style']:#010x} '{it['text']}'")
