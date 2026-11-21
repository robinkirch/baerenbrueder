"""Wertet ein Frida-Zeitprotokoll (tools/frida_logtime.py) fuer Dialogzeilen aus.

Aufruf: python tools/analyze_dialog_timing.py <run.txt> <AllDialog.uax> <AllDialog.exports.tsv>
Gibt pro Dialogzeile Start, echte Dauer, Ende, Unregister-Zeitpunkt und Ueberlappung mit der naechsten Zeile aus.
"""
import re
import sys

sys.path.insert(0, __file__.rsplit("\\", 1)[0])
from bink_durations import parse_bink  # noqa: E402

run, uax, tsv = sys.argv[1:4]
data = open(uax, "rb").read()
dur = {}
for line in open(tsv, encoding="utf-8", errors="replace"):
    name, off, size = line.rstrip("\n").split("\t")
    off, size = int(off), int(size)
    pos = data.find(b"BIK", off, off + size)
    if pos >= 0:
        r = parse_bink(data, pos)
        if r:
            dur[name.lower()] = r["engine"]

plays, unreg = [], {}
pat = re.compile(r"^\s*([\d.]+)\s+(.*)$")
for line in open(run, encoding="utf-8"):
    m = pat.match(line)
    if not m:
        continue
    t, msg = float(m.group(1)), m.group(2)
    if msg.startswith("Playing sound ") and msg[14:].lower() in dur:
        plays.append((t, msg[14:]))
    elif msg.startswith("UnregisterSound(): "):
        n = msg[19:].lower()
        if n in dur:
            unreg.setdefault(n, []).append(t)

print(f"{'Start':>8} {'Dauer':>6} {'Ende':>8} {'Unreg':>8}  {'Abstand->naechste':>17}  Name")
for i, (t, n) in enumerate(plays):
    d = dur[n.lower()]
    u = next((x for x in unreg.get(n.lower(), []) if x >= t), None)
    nxt = plays[i + 1][0] if i + 1 < len(plays) else None
    gap = f"{nxt - (t + d):+7.2f}s" if nxt else ""
    flag = "  <-- UEBERLAPPUNG" if nxt and nxt < t + d - 0.05 else ""
    cut = "  <-- ENTLADEN VOR ENDE" if u and u < t + d - 0.05 else ""
    print(f"{t:8.3f} {d:6.2f} {t + d:8.3f} {u if u else 0:8.3f}  {gap:>17}  {n}{flag}{cut}")
