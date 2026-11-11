"""Frames -> graded render.mp4 for assemble.py: per-beat black-and-white, warm grade, glitch bursts.

  /opt/tts/bin/python tools/post.py <workdir> [--bw BEAT ...] [--glitch BEAT] [--warm]
Times come from beats.json, so the looks land exactly on the beats they belong to.
"""
import argparse
import json
import os
import subprocess


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("work")
    ap.add_argument("--bw", type=int, action="append", default=[])
    ap.add_argument("--glitch", type=int, default=None)
    ap.add_argument("--warm", action="store_true")
    ap.add_argument("--fps", type=int, default=24)
    a = ap.parse_args()
    beats = json.load(open(os.path.join(a.work, "beats.json")))
    span = lambda i: (beats[i]["fs"] - 1) / a.fps, ((beats[i + 1]["fs"] - 1) / a.fps if i + 1 < len(beats) else 1e4)  # noqa: E731
    vf = []
    if a.warm:   # warm Soviet print: lifted reds/yellows, slightly muted, a touch of contrast
        vf.append("colorbalance=rs=0.05:gs=0.01:bs=-0.07:rm=0.04:gm=0.0:bm=-0.05:rh=0.02:bh=-0.03,eq=saturation=0.88:contrast=1.04")
    for i in a.bw:
        s, e = span(i)
        vf.append(f"hue=s=0:enable='between(t,{s:.3f},{e:.3f})'")
    if a.glitch is not None:
        s, e = span(a.glitch)
        # short RGB-split + noise bursts, densest at the start of the beat
        bursts = [(s, s + 0.35)] + [(s + k * 0.9 + 0.5, s + k * 0.9 + 0.62) for k in range(int((e - s - 0.6) / 0.9))]
        cond = "+".join(f"between(t,{x:.3f},{y:.3f})" for x, y in bursts)
        vf.append(f"rgbashift=rh=-14:bh=14:gv=4:enable='{cond}'")
        vf.append(f"noise=alls=45:allf=t:enable='{cond}'")
        vf.append(f"hue=s=0.3:enable='{cond}'")
    out = os.path.join(a.work, "graded.mp4")
    cmd = ["ffmpeg", "-v", "error", "-y", "-framerate", str(a.fps), "-i", os.path.join(a.work, "frames", "f%04d.png")]
    if vf:
        cmd += ["-vf", ",".join(vf)]
    cmd += ["-c:v", "libx264", "-crf", "15", "-preset", "medium", "-pix_fmt", "yuv420p", out]
    subprocess.run(cmd, check=True)
    print(out)


if __name__ == "__main__":
    main()
