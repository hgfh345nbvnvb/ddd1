"""Local narration when there is no ElevenLabs key: Kokoro TTS per beat line -> voice.wav, then Whisper word
timestamps mapped back onto the script's own words -> words.json (same format as eleven.py / voice.py).

  /opt/tts/bin/python tools/tts.py script.txt out_dir [--voice am_michael] [--speed 1.0] [--pause 0.4] [--hold 10=1.6]
"""
import argparse, difflib, json, os, re, subprocess
import numpy as np, soundfile as sf

SAY = {"2016": "twenty sixteen", "2022": "twenty twenty-two", "1961": "nineteen sixty-one",
       "157": "a hundred and fifty-seven", "108": "a hundred and eight", "5:5": "Five, five.",
       "d'Or": "dor", "Klushino": "Kloo-shee-no"}


def norm(w):
    return re.sub(r"[^\w]", "", w.lower())


def spoken(line):
    for k, v in SAY.items():
        line = line.replace(k, v)
    return line


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("script"); ap.add_argument("out_dir")
    ap.add_argument("--voice", default="am_michael"); ap.add_argument("--speed", type=float, default=1.0)
    ap.add_argument("--pause", type=float, default=0.4); ap.add_argument("--lead", type=float, default=0.25)
    ap.add_argument("--hold", action="append", default=[], help="LINE=SECONDS extra silence after a beat line (0-based)")
    a = ap.parse_args()
    holds = {int(h.split("=")[0]): float(h.split("=")[1]) for h in a.hold}
    from kokoro_onnx import Kokoro
    k = Kokoro("/opt/tts/kokoro-v1.0.onnx", "/opt/tts/voices-v1.0.bin")
    lines = [l.strip() for l in open(a.script) if l.strip()]
    sr, chunks = 24000, []
    chunks.append(np.zeros(int(a.lead * sr), np.float32))
    for i, line in enumerate(lines):
        x, sr = k.create(spoken(line), voice=a.voice, speed=a.speed, lang="en-us")
        chunks += [x.astype(np.float32), np.zeros(int((a.pause + holds.get(i, 0.0)) * sr), np.float32)]
    raw = os.path.join(a.out_dir, "voice_24k.wav")
    sf.write(raw, np.concatenate(chunks), sr)
    wav = os.path.join(a.out_dir, "voice.wav")
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", raw, "-ar", "48000", "-ac", "1", wav], check=True)

    from faster_whisper import WhisperModel
    m = WhisperModel("small.en", compute_type="int8")
    w16 = os.path.join(a.out_dir, "voice_16k.wav")
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", raw, "-ar", "16000", "-ac", "1", w16], check=True)
    audio, _ = sf.read(w16, dtype="float32")   # array input: faster-whisper's own decoder breaks on newer PyAV
    segs, _ = m.transcribe(audio, word_timestamps=True, initial_prompt=" ".join(lines))
    heard = [{"w": w.word.strip(), "s": round(w.start, 3), "e": round(w.end, 3)} for s in segs for w in s.words]
    toks = [t for l in lines for t in l.split() if norm(t)]
    # captions/beats should use the script's spelling; timings come from what Whisper heard
    sm = difflib.SequenceMatcher(a=[norm(t) for t in toks], b=[norm(h["w"]) for h in heard], autojunk=False)
    out = []
    for op, i0, i1, j0, j1 in sm.get_opcodes():
        if op == "equal":
            out += [{"w": toks[i0 + n], "s": heard[j0 + n]["s"], "e": heard[j0 + n]["e"]} for n in range(i1 - i0)]
        elif i1 > i0:
            if j1 > j0:
                s, e = heard[j0]["s"], heard[j1 - 1]["e"]
            else:  # not heard at all: squeeze between neighbours
                s = out[-1]["e"] if out else 0.0
                e = heard[j0]["s"] if j0 < len(heard) else s + 0.3 * (i1 - i0)
            step = (e - s) / max(1, i1 - i0)
            out += [{"w": toks[i0 + n], "s": round(s + n * step, 3), "e": round(s + (n + 1) * step, 3)} for n in range(i1 - i0)]
    json.dump(out, open(os.path.join(a.out_dir, "words.json"), "w"), indent=0, ensure_ascii=False)
    os.remove(w16)
    miss = sum(i1 - i0 for op, i0, i1, *_ in sm.get_opcodes() if op != "equal")
    print(f"voice {len(np.concatenate(chunks)) / sr:.1f}s, words {len(out)}, re-timed (not heard verbatim) {miss}")


if __name__ == "__main__":
    main()
