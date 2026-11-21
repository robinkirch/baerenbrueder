"""Startet das Spiel direkt (ohne Launcher) unter Frida und schreibt jede Log-Zeile mit
exakter Wanduhrzeit mit. Haengt sich an GLog->Serialize (vtable[0]) in Core.dll.

Aufruf: python tools/frida_logtime.py <ausgabe.txt> [map-und-parameter...]
Standard-Parameter: CavePainting1.unr -SAVESLOT=1 (so startet der Launcher ein neues Spiel)
"""
import os
import sys
import threading
import time

import frida

GAME_DIR = r"Z:\Games\Baerenbrueder\game\system"
out_path = sys.argv[1]
game_args = sys.argv[2:] or ["CavePainting1.unr", "-SAVESLOT=1"]

JS = r"""
let pGLog = null;
const hooked = new Set();
function tryHook() {
    if (pGLog === null) {
        const core = Process.findModuleByName('Core.dll');
        if (core === null) return;   // beim Spawn noch nicht geladen
        pGLog = core.getExportByName('?GLog@@3PAVFOutputDevice@@A');
    }
    const dev = pGLog.readPointer();
    if (dev.isNull()) return;
    const ser = dev.readPointer().readPointer();   // vtable[0] = Serialize(const TCHAR*, EName)
    const key = ser.toString();
    if (hooked.has(key)) return;
    hooked.add(key);
    Interceptor.attach(ser, {
        onEnter(args) {
            // __thiscall: this in ecx, args[0] = Text, args[1] = Event
            let s = '';
            try { s = args[0].readUtf16String(); } catch (e) { s = '<?>'; }
            send({ t: Date.now(), ev: args[1].toInt32(), s: s });
        }
    });
    send({ t: Date.now(), ev: -1, s: '[frida] GLog Serialize gehookt @ ' + key });
}
setInterval(tryHook, 20);

// --- Diagnose: berechnete Sounddauer und Bink-Summary protokollieren ---
let durHooked = false;
function hookDuration() {
    if (durHooked) return;
    const eng = Process.findModuleByName('Engine.dll');
    const bink = Process.findModuleByName('binkw32.dll');
    if (eng === null || bink === null) return;
    durHooked = true;
    const exec = eng.getExportByName('?execGetSoundDuration@AActor@@QAEXAAUFFrame@@QAX@Z');
    Interceptor.attach(exec, {
        onEnter(args) { this.res = args[1]; },
        onLeave() { send({ t: Date.now(), ev: -2, s: '[dur] GetSoundDuration = ' + this.res.readFloat().toFixed(3) }); }
    });
    const summ = bink.getExportByName('_BinkGetSummary@8');
    Interceptor.attach(summ, {
        onEnter(args) { this.p = args[1]; },
        onLeave() {
            const u = i => this.p.add(i * 4).readU32();
            send({ t: Date.now(), ev: -2, s: '[bink] summary W=' + u(0) + ' H=' + u(1) + ' TotalTime=' + u(2) +
                ' FileFR=' + u(3) + '/' + u(4) + ' FR=' + u(5) + '/' + u(6) + ' Frames=' + u(8) + ' Played=' + u(9) });
        }
    });
    send({ t: Date.now(), ev: -1, s: '[frida] Duration/Bink hooks aktiv' });
}
setInterval(hookDuration, 20);

// --- Diagnose: Spielzeit (DeltaSeconds) pro echter Sekunde aufsummieren ---
let tickHooked = false;
const agg = { n: 0, sum: 0, min: 1e9, max: 0, vals: {}, levelSum: 0, levelN: 0 };
function hookTick() {
    if (tickHooked) return;
    const eng = Process.findModuleByName('Engine.dll');
    if (eng === null) return;
    tickHooked = true;
    const ge = eng.getExportByName('?Tick@UGameEngine@@UAEXM@Z');
    // Optionaler FPS-Limiter (nur Test): nach jedem Engine-Tick warten, bis 1/FPSCAP s vergangen sind
    if (FPSCAP > 0) {
        const winmm = Process.getModuleByName('kernel32.dll');
        const qpcF = new NativeFunction(winmm.getExportByName('QueryPerformanceCounter'), 'int', ['pointer']);
        const sleepF = new NativeFunction(winmm.getExportByName('Sleep'), 'void', ['uint32']);
        // Sleep(1) ist ohne timeBeginPeriod auf Win11 ~15.6 ms grob
        const tbp = new NativeFunction(Process.getModuleByName('winmm.dll').getExportByName('timeBeginPeriod'), 'uint', ['uint']);
        tbp(1);
        const buf = Memory.alloc(8);
        const qpcNow = () => { qpcF(buf); return buf.readU64().toNumber() / 1e7; };  // QPC-Frequenz 10 MHz
        let next = 0;
        Interceptor.attach(ge, {
            onLeave() {
                const frame = 1 / FPSCAP;
                let now = qpcNow();
                if (next === 0 || now - next > 0.1) next = now;
                next += frame;
                while (next - now > 0.002) { sleepF(1); now = qpcNow(); }
                while (qpcNow() < next) { }
            }
        });
        send({ t: Date.now(), ev: -1, s: '[frida] FPS-Limiter aktiv: ' + FPSCAP });
    }
    Interceptor.attach(ge, {
        onEnter(args) {
            const d = args[0].toInt32();
            const f = new Float32Array(new Int32Array([d]).buffer)[0];
            agg.n++; agg.sum += f;
            if (f < agg.min) agg.min = f;
            if (f > agg.max) agg.max = f;
            const k = f.toFixed(4);
            agg.vals[k] = (agg.vals[k] || 0) + 1;
        }
    });
    const lv = eng.getExportByName('?Tick@ULevel@@UAEXW4ELevelTick@@M@Z');
    Interceptor.attach(lv, {
        onEnter(args) {
            const f = new Float32Array(new Int32Array([args[1].toInt32()]).buffer)[0];
            agg.levelSum += f; agg.levelN++;
        }
    });
    let last = Date.now();
    setInterval(() => {
        const now = Date.now();
        if (agg.n > 0) {
            const top = Object.entries(agg.vals).sort((a, b) => b[1] - a[1]).slice(0, 6)
                .map(e => e[0] + 'x' + e[1]).join(' ');
            send({ t: now, ev: -3, s: '[tick] real=' + ((now - last) / 1000).toFixed(3) +
                ' frames=' + agg.n + ' gameSum=' + agg.sum.toFixed(3) +
                ' levelSum=' + agg.levelSum.toFixed(3) + '/' + agg.levelN +
                ' min=' + agg.min.toFixed(4) + ' max=' + agg.max.toFixed(4) + ' deltas: ' + top });
        }
        last = now;
        agg.n = 0; agg.sum = 0; agg.min = 1e9; agg.max = 0; agg.vals = {}; agg.levelSum = 0; agg.levelN = 0;
    }, 1000);
    send({ t: Date.now(), ev: -1, s: '[frida] Tick hooks aktiv' });
}
setInterval(hookTick, 20);

// --- Diagnose: Alt-Tab-Pfad der Audio-Engine ---
let audHooked = false;
function hookAudio() {
    if (audHooked) return;
    const al = Process.findModuleByName('ALAudio.dll');
    if (al === null) return;
    audHooked = true;
    const names = {
        '?Minimize@UALAudioSubsystem@@UAEXXZ': 'Minimize',
        '?Restore@UALAudioSubsystem@@UAEXPAVUViewport@@@Z': 'Restore',
        '?SetViewport@UALAudioSubsystem@@UAEXPAVUViewport@@@Z': 'SetViewport',
    };
    for (const [sym, label] of Object.entries(names)) {
        Interceptor.attach(al.getExportByName(sym), {
            onEnter(args) {
                const vp = this.context.ecx.add(0x2c).readPointer();
                const bt = Thread.backtrace(this.context, Backtracer.ACCURATE).slice(0, 8).map(a => {
                    const m = Process.findModuleByAddress(a);
                    return m ? m.name + '+0x' + a.sub(m.base).toString(16) : a.toString();
                }).join(' <- ');
                send({ t: Date.now(), ev: -4, s: '[audio] ' + label + ' arg=' + args[0] + ' viewportVorher=' + vp + ' | ' + bt });
            }
        });
    }
    // OpenAL-Aufrufe zaehlen/loggen (Gain-Aenderungen auf 0, Pause/Play/Stop)
    const oal = Process.findModuleByName('OpenAL32.dll');
    if (oal !== null) {
        const cnt = { play: 0, pause: 0, stop: 0, gain0: 0, gainPos: 0 };
        const fl = p => new Float32Array(new Int32Array([p.toInt32()]).buffer)[0];
        Interceptor.attach(oal.getExportByName('alSourcePlay'), { onEnter() { cnt.play++; } });
        Interceptor.attach(oal.getExportByName('alSourcePause'), { onEnter() { cnt.pause++; } });
        Interceptor.attach(oal.getExportByName('alSourceStop'), { onEnter() { cnt.stop++; } });
        Interceptor.attach(oal.getExportByName('alSourcef'), {
            onEnter(args) {
                if (args[1].toInt32() === 0x100a) { if (fl(args[2]) > 0) cnt.gainPos++; else cnt.gain0++; }
            }
        });
        // Listener-Position/-Geschwindigkeit/-Orientierung und Quell-Pitch auf ungueltige Werte pruefen
        const bad = v => !isFinite(v) || Math.abs(v) > 1e6;
        const lis = { pos: '', vel: '', velMax: 0, bad: 0 };
        const pitch = { min: 1e9, max: -1e9, bad: 0 };
        Interceptor.attach(oal.getExportByName('alListenerfv'), {
            onEnter(args) {
                const p = args[0].toInt32(), a = args[1];
                const n = p === 0x100f ? 6 : 3;
                const v = []; for (let i = 0; i < n; i++) v.push(a.add(i * 4).readFloat());
                if (v.some(bad)) { lis.bad++; send({ t: Date.now(), ev: -4, s: '[oal] UNGUELTIGER Listener-Wert param=' + p.toString(16) + ' ' + v.join(',') }); }
                if (p === 0x1004) lis.pos = v.map(x => x.toFixed(1)).join(',');
                if (p === 0x1006) { lis.vel = v.map(x => x.toFixed(1)).join(','); lis.velMax = Math.max(lis.velMax, Math.hypot(v[0], v[1], v[2])); }
            }
        });
        Interceptor.attach(oal.getExportByName('alSourcef'), {
            onEnter(args) {
                if (args[1].toInt32() === 0x1003) {
                    const f = fl(args[2]);
                    if (bad(f)) pitch.bad++;
                    pitch.min = Math.min(pitch.min, f); pitch.max = Math.max(pitch.max, f);
                }
            }
        });
        setInterval(() => {
            send({ t: Date.now(), ev: -4, s: '[oal] play=' + cnt.play + ' pause=' + cnt.pause + ' stop=' + cnt.stop +
                ' gain>0=' + cnt.gainPos + ' gain=0=' + cnt.gain0 + ' | listener pos=' + lis.pos + ' vel=' + lis.vel +
                ' velMax=' + lis.velMax.toFixed(1) + ' bad=' + lis.bad + ' | pitch ' + pitch.min.toFixed(2) + '..' + pitch.max.toFixed(2) + ' bad=' + pitch.bad });
            cnt.play = cnt.pause = cnt.stop = cnt.gain0 = cnt.gainPos = 0;
            lis.velMax = 0; lis.bad = 0; pitch.min = 1e9; pitch.max = -1e9; pitch.bad = 0;
        }, 1000);
    }
    send({ t: Date.now(), ev: -1, s: '[frida] Audio hooks aktiv' });
}
setInterval(hookAudio, 20);

// --- Diagnose: D3DDrv GetRes (Modusliste und Grenzwerte) ---
let d3dHooked = false;
function hookD3D() {
    if (d3dHooked) return;
    const d3d = Process.findModuleByName('D3DDrv.dll');
    if (d3d === null) return;
    d3dHooked = true;
    Interceptor.attach(d3d.base.add(0x8871), {     // nach erkanntem "GetRes" (0x10008871 bei Basis 0x10000000)
        onEnter() {
            const o = this.context.ebx;
            const n = o.add(0x730).readS32();
            const arr = o.add(0x72c).readPointer();
            const maxW = o.add(0x814).readS32(), maxH = o.add(0x818).readS32();
            const modes = [];
            for (let i = 0; i < n && i < 400; i++) {
                const m = arr.add(i * 16);
                modes.push(m.readS32() + 'x' + m.add(4).readS32() + '@' + m.add(8).readS32() + 'f' + m.add(12).readS32());
            }
            send({ t: Date.now(), ev: -5, s: '[getres] n=' + n + ' maxW=' + maxW + ' maxH=' + maxH + ' modes=' + modes.join(' ') });
        }
    });
    send({ t: Date.now(), ev: -1, s: '[frida] D3D GetRes hook aktiv @ ' + d3d.base });
}
setInterval(hookD3D, 20);
"""


def main():
    t0 = None
    lock = threading.Lock()
    done = threading.Event()
    fo = open(out_path, "w", encoding="utf-8")

    def on_message(msg, _data):
        nonlocal t0
        if msg["type"] != "send":
            fo.write(f"# {msg}\n")
            return
        p = msg["payload"]
        with lock:
            if t0 is None:
                t0 = p["t"]
            fo.write(f"{(p['t'] - t0) / 1000:9.3f}  {p['s']}\n")
            fo.flush()
            if "Log file closed" in p["s"]:
                done.set()

    dev = frida.get_local_device()
    extra_env = {}
    if os.environ.get("BB_ALSOFTLOG"):
        # OpenAL-Soft-Debuglog (nur wirksam mit OpenAL Soft als OpenAL32.dll)
        extra_env = {"ALSOFT_LOGLEVEL": "3", "ALSOFT_LOGFILE": os.environ["BB_ALSOFTLOG"]}
    pid = dev.spawn([os.path.join(GAME_DIR, "Game.exe")] + game_args, cwd=GAME_DIR,
                    env=extra_env or None)
    session = dev.attach(pid)
    session.on("detached", lambda *a: done.set())
    fpscap = float(os.environ.get("BB_FPSCAP", "0"))
    script = session.create_script(f"const FPSCAP = {fpscap};\n" + JS)
    script.on("message", on_message)
    script.load()
    dev.resume(pid)
    print(f"Spiel gestartet (PID {pid}), protokolliere nach {out_path}")

    # Optional: simuliertes Alt+Tab zu den Zeitpunkten in BB_ALTTAB (Sekunden, kommagetrennt)
    alttab = [float(x) for x in os.environ.get("BB_ALTTAB", "").split(",") if x.strip()]
    if alttab:
        import ctypes

        def press_alt_tab():
            ku = ctypes.windll.user32.keybd_event
            ku(0x12, 0, 0, 0)          # Alt down
            ku(0x09, 0, 0, 0)          # Tab down
            ku(0x09, 0, 2, 0)          # Tab up
            time.sleep(0.15)
            ku(0x12, 0, 2, 0)          # Alt up

        def alttab_thread():
            start = time.time()
            for t in alttab:
                time.sleep(max(0, t - (time.time() - start)))
                with lock:
                    fo.write(f"# --- simuliertes Alt+Tab bei {t:.1f}s ---\n")
                press_alt_tab()

        threading.Thread(target=alttab_thread, daemon=True).start()

    # Optional: Spielfenster minimieren/wiederherstellen (BB_MINIMIZE="t_min,t_restore")
    mini = [float(x) for x in os.environ.get("BB_MINIMIZE", "").split(",") if x.strip()]
    if len(mini) == 2:
        import ctypes
        from ctypes import wintypes
        u32 = ctypes.windll.user32

        def game_hwnd():
            found = []
            proc = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)

            def cb(h, _):
                p = wintypes.DWORD()
                u32.GetWindowThreadProcessId(h, ctypes.byref(p))
                if p.value == pid and u32.IsWindowVisible(h):
                    found.append(h)
                return True
            u32.EnumWindows(proc(cb), 0)
            return found[0] if found else None

        def minimize_thread():
            start = time.time()
            time.sleep(max(0, mini[0] - (time.time() - start)))
            h = game_hwnd()
            with lock:
                fo.write(f"# --- Fenster minimieren bei {mini[0]:.1f}s (hwnd={h}) ---\n")
            if h:
                u32.ShowWindow(h, 6)            # SW_MINIMIZE
            time.sleep(max(0, mini[1] - (time.time() - start)))
            with lock:
                fo.write(f"# --- Fenster wiederherstellen bei {mini[1]:.1f}s ---\n")
            if h:
                u32.ShowWindow(h, 9)            # SW_RESTORE
                u32.SetForegroundWindow(h)

        threading.Thread(target=minimize_thread, daemon=True).start()
    max_s = float(os.environ.get("BB_MAXSEC", "1800"))
    if not done.wait(timeout=max_s):
        print(f"{max_s:.0f} s erreicht, beende Spiel")
        try:
            dev.kill(pid)
        except frida.ProcessNotFoundError:
            pass
    time.sleep(0.5)
    fo.close()
    print("fertig")


if __name__ == "__main__":
    main()
