"""Background music without ElevenLabs: a small numpy synth, rendered to the video's exact length.

  /opt/tts/bin/python tools/music.py sport|nostalgic out.wav --seconds 66 [--gain T:G ...]
--gain T:G sets a volume breakpoint (seconds:linear gain); the envelope is linear between points.
"""
import argparse

import numpy as np
import soundfile as sf
from scipy.signal import butter, lfilter

SR = 48000
NOTE = {"C": 0, "D": 2, "E": 4, "F": 5, "G": 7, "A": 9, "B": 11}


def hz(name, octave):
    return 440.0 * 2 ** ((NOTE[name] + 12 * (octave + 1) - 69) / 12)


def env(n, a, r):
    e = np.ones(n)
    na, nr = max(1, int(a * SR)), max(1, int(r * SR))
    e[:na] = np.linspace(0, 1, na)
    e[-nr:] *= np.linspace(1, 0, nr)
    return e


def lp(x, cut, order=2):
    b, a = butter(order, cut / (SR / 2))
    return lfilter(b, a, x)


def hp(x, cut, order=2):
    b, a = butter(order, cut / (SR / 2), btype="high")
    return lfilter(b, a, x)


def saw(f, n, detune=0.0):
    t = np.arange(n) / SR
    out = np.zeros(n)
    for d in (-detune, 0, detune):
        ph = (t * f * (1 + d)) % 1.0
        out += 2 * ph - 1
    return out / 3


def sine(f, n):
    return np.sin(2 * np.pi * f * np.arange(n) / SR)


def place(buf, x, t):
    i = int(t * SR)
    if i >= len(buf):
        return
    j = min(len(buf), i + len(x))
    buf[i:j] += x[: j - i]


def sport(total):
    bpm, n = 96, int(total * SR)
    beat = 60 / bpm
    mix = np.zeros(n)
    prog = [("A", ["A", "C", "E"]), ("F", ["F", "A", "C"]), ("C", ["C", "E", "G"]), ("G", ["G", "B", "D"])]
    nk = int(0.35 * SR)
    tk = np.arange(nk) / SR
    kick = np.sin(2 * np.pi * (45 * tk + 75 * (1 - np.exp(-tk * 30)) / 30)) * np.exp(-tk * 9)
    nh = int(0.05 * SR)
    rng = np.random.default_rng(1)
    hat = hp(rng.standard_normal(nh), 7000) * np.exp(-np.arange(nh) / SR * 80)
    ns = int(0.2 * SR)
    snare = lp(hp(rng.standard_normal(ns), 1200), 6000) * np.exp(-np.arange(ns) / SR * 22)
    t, bar = 0.0, 0
    while t < total:
        root, chord = prog[bar % 4]
        for b in range(4):
            place(mix, kick * 0.9, t + b * beat)
            if b in (1, 3):
                place(mix, snare * 0.35, t + b * beat)
            for h in range(2):
                place(mix, hat * 0.12, t + b * beat + h * beat / 2)
            for h in range(2):
                nb = int(beat / 2 * SR * 0.9)
                bass = lp(saw(hz(root, 1), nb, 0.003), 500) * env(nb, 0.005, 0.05)
                place(mix, bass * 0.35, t + b * beat + h * beat / 2)
        npad = int(4 * beat * SR)
        pad = sum(saw(hz(c, 3), npad, 0.006) for c in chord)
        place(mix, lp(pad, 1400) * env(npad, 0.4, 0.4) * 0.12, t)
        t += 4 * beat
        bar += 1
    return mix


def nostalgic(total):
    bpm, n = 72, int(total * SR)
    beat = 60 / bpm
    mix = np.zeros(n)
    prog = [["C", "E", "G"], ["A", "C", "E"], ["F", "A", "C"], ["G", "B", "D"]]
    t, bar = 0.0, 0
    while t < total:
        chord = prog[bar % 4]
        npad = int(4 * beat * SR)
        pad = sum(sine(hz(c, 3), npad) + 0.3 * sine(hz(c, 4), npad) for c in chord)
        place(mix, lp(pad, 1800) * env(npad, 0.8, 0.8) * 0.12, t)
        for k in range(8):
            c = chord[k % 3] if k < 6 else chord[(k + 1) % 3]
            npl = int(1.2 * SR)
            tt = np.arange(npl) / SR
            f = hz(c, 5 if k % 4 == 3 else 4)
            pluck = (np.sin(2 * np.pi * f * tt) + 0.25 * np.sin(4 * np.pi * f * tt)) * np.exp(-tt * 4.5)
            place(mix, pluck * 0.16, t + k * beat / 2)
        t += 4 * beat
        bar += 1
    return lp(mix, 5000)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("style", choices=["sport", "nostalgic"])
    ap.add_argument("out")
    ap.add_argument("--seconds", type=float, required=True)
    ap.add_argument("--gain", action="append", default=[])
    a = ap.parse_args()
    x = sport(a.seconds) if a.style == "sport" else nostalgic(a.seconds)
    pts = sorted((float(p.split(":")[0]), float(p.split(":")[1])) for p in a.gain) or [(0, 1.0)]
    tt = np.arange(len(x)) / SR
    g = np.interp(tt, [p[0] for p in pts], [p[1] for p in pts])
    fade = np.minimum(1, (a.seconds - tt) / 1.5).clip(0, 1)
    x = x * g * fade
    x = x / (np.abs(x).max() + 1e-9) * 0.89
    st = np.stack([x, np.roll(x, int(0.012 * SR))], axis=1)   # cheap stereo width
    sf.write(a.out, st.astype(np.float32), SR)
    print(f"{a.out}: {a.seconds:.1f}s {a.style}")


if __name__ == "__main__":
    main()
