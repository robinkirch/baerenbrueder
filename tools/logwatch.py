"""Liest Game.log live mit und schreibt jede neue Zeile mit Wanduhrzeit (Sekunden seit Start) in eine Datei.

Aufruf: python tools/logwatch.py <Game.log> <ausgabe.txt> [max_sekunden]
Wartet, bis die Log-Datei neu angelegt/geleert wird (Spielstart), und liest dann fortlaufend.
"""
import os
import sys
import time

log, out = sys.argv[1], sys.argv[2]
max_s = float(sys.argv[3]) if len(sys.argv) > 3 else 900

start_wait = time.time()
old_mtime = os.path.getmtime(log) if os.path.exists(log) else 0
# Auf Neustart des Spiels warten: Datei wird neu geschrieben (mtime aendert sich und Groesse klein)
while time.time() - start_wait < max_s:
    if os.path.exists(log) and os.path.getmtime(log) != old_mtime and os.path.getsize(log) < 4096:
        break
    time.sleep(0.05)

t0 = time.perf_counter()
pos = 0
buf = b""
with open(out, "w", encoding="utf-8") as fo:
    fo.write(f"# Start {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
    last_data = time.perf_counter()
    while time.perf_counter() - t0 < max_s:
        try:
            with open(log, "rb") as fi:
                fi.seek(pos)
                chunk = fi.read()
        except OSError:
            chunk = b""
        if chunk:
            pos += len(chunk)
            buf += chunk
            now = time.perf_counter() - t0
            *lines, buf = buf.split(b"\n")
            for ln in lines:
                fo.write(f"{now:9.3f}  {ln.decode('cp1252', 'replace').rstrip()}\n")
            fo.flush()
            last_data = time.perf_counter()
            if b"Log file closed" in chunk:
                break
        time.sleep(0.02)
