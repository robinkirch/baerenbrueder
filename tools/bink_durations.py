"""Vergleicht fuer alle Bink-Sounds in einem .uax-Paket:
  - Dauer laut Engine (FSoundData::GetPeriod): TotalFrames * FrameRateDiv / FrameRate
  - echte Audiodauer: Summe der dekodierten Bytes aller Audio-Pakete / (Rate * Kanaele * 2)

Aufruf: python tools/bink_durations.py <AllDialog.uax> [namensfilter]
Namen werden heuristisch aus dem Text direkt vor dem BIK-Header nicht ermittelt; ausgegeben wird der Offset.
"""
import struct
import sys


def parse_bink(buf, off):
    sig = buf[off:off + 3]
    if sig != b"BIK":
        return None
    size = struct.unpack_from("<I", buf, off + 4)[0] + 8
    frames, _largest, _frames2, width, height, fps_num, fps_den, _flags, ntracks = struct.unpack_from(
        "<9I", buf, off + 8)
    if not (0 < frames < 100000 and fps_num and fps_den and 0 < ntracks <= 8):
        return None
    p = off + 44
    p += 4 * ntracks  # max decoded size pro Spur
    rates = []
    for _ in range(ntracks):
        rate, flags = struct.unpack_from("<HH", buf, p)
        rates.append((rate, flags))
        p += 4
    p += 4 * ntracks  # Track-IDs
    offsets = struct.unpack_from(f"<{frames + 1}I", buf, p)
    total_bytes = 0
    for i in range(frames):
        fo = off + (offsets[i] & ~1)
        if ntracks:
            pkt = struct.unpack_from("<I", buf, fo)[0]
            if pkt >= 4:
                total_bytes += struct.unpack_from("<I", buf, fo + 4)[0]
    rate, flags = rates[0]
    channels = 2 if flags & 0x2000 else 1
    engine = frames * fps_den / fps_num
    audio = total_bytes / (rate * channels * 2) if rate else 0.0
    return dict(off=off, size=size, frames=frames, fps=fps_num / fps_den, rate=rate,
                channels=channels, engine=engine, audio=audio)


def main():
    data = open(sys.argv[1], "rb").read()
    results = []
    pos = 0
    while True:
        pos = data.find(b"BIK", pos)
        if pos < 0:
            break
        try:
            r = parse_bink(data, pos)
        except struct.error:
            r = None
        if r:
            results.append(r)
            pos += r["size"]
        else:
            pos += 3
    diffs = [r["audio"] - r["engine"] for r in results]
    print(f"{len(results)} Bink-Sounds gefunden")
    print(f"Differenz echte Audiodauer - Engine-Dauer: min {min(diffs):+.3f}s  max {max(diffs):+.3f}s  "
          f"Mittel {sum(diffs) / len(diffs):+.3f}s")
    over = [r for r in results if r["audio"] - r["engine"] > 0.5]
    print(f"{len(over)} Sounds laufen > 0.5 s laenger als die Engine annimmt (Cutscene-Puffer ist 0.5 s)")
    rates = {}
    for r in results:
        rates[(r["rate"], r["channels"], round(r["fps"], 3))] = rates.get((r["rate"], r["channels"], round(r["fps"], 3)), 0) + 1
    print("Formate (Rate, Kanaele, FPS): Anzahl", rates)
    for r in sorted(results, key=lambda r: r["audio"] - r["engine"], reverse=True)[:10]:
        print(f"  @{r['off']:9d}  engine {r['engine']:6.2f}s  audio {r['audio']:6.2f}s  "
              f"frames {r['frames']} fps {r['fps']:.3f} rate {r['rate']} ch {r['channels']}")


if __name__ == "__main__":
    main()
