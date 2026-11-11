"""Messi vs Ronaldo — "10 facts: who's better?"  (kylo-3d-shorts pipeline, fact-countdown format)

  blender --background --python build.py -- <workdir> [preview|draft|full]
<workdir> holds beats.json. Messi = light blue (left), Ronaldo = red (right); the score rides on the camera.
"""
import math
import os
import random
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "..", "tools"))
import kit  # noqa: E402

import bpy  # noqa: E402
import human  # noqa: E402
import s3d  # noqa: E402

argv = sys.argv[sys.argv.index("--") + 1:]
WORK = argv[0]
MODE = argv[1] if len(argv) > 1 else "full"
B = s3d.load_beats(os.path.join(WORK, "beats.json"))
kit.setup(B)
W = lambda i, w=None, o=0: s3d.when(B, i, w, o)  # noqa: E731
END = bpy.context.scene.frame_end

LB = (0.45, 0.72, 1.0)
RED = (0.95, 0.07, 0.05)
SIL = s3d.mat("Silhouette", (0.012, 0.012, 0.015), rough=0.45)
SILVER = kit.metal("Silver", (0.86, 0.87, 0.9), rough=0.16)
GOLD = kit.metal("Gold", (1.0, 0.72, 0.28))
INK = s3d.mat("Ink", (0.03, 0.03, 0.035), rough=0.5)
MESSI_KIT = dict(shirt=(0.62, 0.8, 0.98), pants=(0.95, 0.95, 0.97), shoes=(0.9, 0.9, 0.9), hat=None)
RON_KIT = dict(shirt=(0.82, 0.06, 0.05), pants=(0.95, 0.95, 0.95), shoes=(0.1, 0.1, 0.1), hat=None)


def drop_quiet(o, f, height=2.5, dur=12):
    s3d.drop_in(o, f, height=height, dur=dur)
    s3d._markers.pop()


def palm(name, loc, h=4.0, mat=None, leaf=None):
    m = mat or s3d.mat("PalmDark", (0.05, 0.04, 0.03), rough=0.8)
    lm = leaf or m
    x, y, z = loc
    parts = [s3d.cylinder(name + "_trunk", 0.09, h, (x, y, z + h / 2), mat=m, verts=10)]
    for k in range(7):
        a = k * math.tau / 7
        lf = s3d.box(f"{name}_leaf{k}", (1.5, 0.28, 0.03), (x + 0.65 * math.cos(a), y + 0.65 * math.sin(a), z + h - 0.15), lm, bevel=0.01)
        lf.rotation_euler = (0, 0.45, a)
        parts.append(lf)
    return parts


def duel_stage(x, label_l="MESSI", label_r="RONALDO"):
    kit.floor(f"Floor{x}", (x, 2, 0), (14, 10), s3d.mat("Studio", (0.04, 0.04, 0.045), rough=0.75))
    kit.backdrop(f"BDL{x}", (x - 3, 8, 3), w=6, h=14, bottom=(0.22, 0.42, 0.75), top=(0.02, 0.05, 0.13))
    kit.backdrop(f"BDR{x}", (x + 3, 8, 3), w=6, h=14, bottom=(0.62, 0.05, 0.04), top=(0.1, 0.01, 0.02))
    s3d.box(f"PlM{x}", (1.3, 0.8, 0.5), (x - 0.72, 2.2, 0.25), s3d.mat("PlinthBlue", (0.32, 0.58, 0.95), rough=0.35))
    s3d.box(f"PlR{x}", (1.3, 0.8, 0.5), (x + 0.72, 2.2, 0.25), s3d.mat("PlinthRed", (0.72, 0.05, 0.04), rough=0.35))
    dark = s3d.mat("PlinthText", (0.015, 0.015, 0.02), rough=0.5)
    kit.text(f"PlMt{x}", label_l, (x - 0.72, 1.79, 0.38), 0.1, dark)
    kit.text(f"PlRt{x}", label_r, (x + 0.72, 1.79, 0.38), 0.1, kit.emit("PlinthTextW", (1, 1, 1), 1.5))
    kit.light(f"Top{x}", "AREA", (x, 0.8, 4.0), 450, size=4, target=(x, 2.2, 0.5))
    kit.light(f"RimL{x}", "AREA", (x - 2.5, 4.5, 2.5), 250, LB, size=2, target=(x - 0.72, 2.2, 0.8))
    kit.light(f"RimR{x}", "AREA", (x + 2.5, 4.5, 2.5), 250, RED, size=2, target=(x + 0.72, 2.2, 0.8))


def count_text(x, side, n, f, z=1.1):
    """Big tally floating above each side's trophies (the lower frame belongs to the captions)."""
    m = kit.emit("CountM", LB, 2.2) if side == "L" else kit.emit("CountR", (1.0, 0.25, 0.18), 2.6)
    t = kit.text(f"Count{x}{side}", str(n), (x + (-0.72 if side == "L" else 0.72), 2.2, z), 0.32, m, extrude=0.02)
    kit.vis(t, f, pop=8, over=1.4)


cam = kit.Cam(35)
hud = cam.hud(3.0)

# ================================================================ 0 / 10 / 11 — the stage: two silhouettes
kit.backdrop("BD0", (0, 9, 3), w=30, h=20, bottom=(0.04, 0.045, 0.09), top=(0.0, 0.0, 0.01))
s3d.cylinder("StageFloor", 5, 0.1, (0, 2, -0.05), mat=s3d.mat("StageGloss", (0.012, 0.012, 0.016), rough=0.6))
messi = kit.silhouette(human.Human("Messi", loc=(-0.95, 2.0, 0.0), facing=18, seed=1), SIL)
ron = kit.silhouette(human.Human("Ronaldo", loc=(0.95, 2.0, 0.0), facing=-18, seed=0), SIL)
kit.football("BallM", 0.11, (-0.66, 1.72, 0.11))
kit.football("BallR", 0.11, (0.66, 1.72, 0.11))
kit.light("RimM", "AREA", (-1.9, 3.8, 2.4), 320, LB, size=1.5, target=(-0.95, 2, 1.0), cutoff=12)
kit.light("RimRo", "AREA", (1.9, 3.8, 2.4), 320, RED, size=1.5, target=(0.95, 2, 1.0), cutoff=12)
kit.light("PoolM", "SPOT", (-0.95, 1.6, 4.5), 50, LB, target=(-0.95, 2, 0), spot=0.55, cutoff=12)
kit.light("PoolR", "SPOT", (0.95, 1.6, 4.5), 50, RED, target=(0.95, 2, 0), spot=0.55, cutoff=12)
kit.light("StageFill", "AREA", (0, -3, 3), 30, (0.6, 0.65, 0.8), size=4, target=(0, 2, 1), cutoff=12)
f_admit = W(0, "admit")
ron.pose_at(f_admit, "stand"); ron.pose_at(f_admit + 8, "shrug"); ron.hold(f_admit + 8, B[1]["fs"])
messi.hold(1, B[1]["fs"])
f10 = B[10]["fs"]
for h in (messi, ron):
    h.pose_at(f10, "stand"); h.pose_at(f10 + 10, "think"); h.hold(f10 + 10, B[11]["fs"])
    h.pose_at(B[11]["fs"] + 4, "point"); h.hold(B[11]["fs"] + 4, END)

# ================================================================ 1 — fact 10: growth hormone deficiency (b/w in post)
X = 100
kit.floor("Floor1", (X, 1, 0), (10, 8), s3d.mat("Lino", (0.3, 0.3, 0.3), rough=0.7))
s3d.box("Wall1", (8, 0.2, 5), (X, 3.4, 2.5), s3d.mat("WallPaint", (0.5, 0.52, 0.55), rough=0.9), bevel=0.0)
s3d.box("Chart", (0.5, 0.03, 1.9), (X - 0.55, 3.28, 1.15), s3d.mat("ChartPaper", (0.96, 0.96, 0.94), rough=0.8), bevel=0.005)
for cm in range(30, 200, 10):
    s3d.box(f"Tick{cm}", (0.22 if cm % 50 == 0 else 0.1, 0.01, 0.008), (X - 0.67 + (0.06 if cm % 50 else 0.0), 3.26, cm / 100), INK, bevel=0)
    if cm % 20 == 0:
        kit.text(f"TickL{cm}", str(cm), (X - 0.41, 3.255, cm / 100), 0.055, INK)
kid = human.Human("Kid", loc=(X - 0.1, 2.95, 0.0), facing=0, outfit=MESSI_KIT, seed=2, scale=0.62)
kit.football("Ball1", 0.11, (X + 0.3, 2.7, 0.11))
TX = X + 0.75
s3d.box("Table1", (0.6, 0.4, 0.04), (TX, 2.85, 0.75), s3d.mat("TableTop", (0.6, 0.6, 0.6), rough=0.4))
for dx in (-0.25, 0.25):
    for dy in (-0.16, 0.16):
        s3d.box("TableLeg", (0.03, 0.03, 0.73), (TX + dx, 2.85 + dy, 0.365), s3d.mat_steel(), bevel=0.003)
glass = s3d.mat("VialGlass", (0.85, 0.9, 0.95), rough=0.08)
f_treat = W(1, "treatment")
for k, dx in enumerate((-0.18, -0.08, 0.02)):
    v = s3d.cylinder(f"Vial{k}", 0.025, 0.09, (TX + dx, 2.8, 0.815), mat=glass, verts=16)
    s3d.pop_in(v, W(1, "pay") + k * 3, dur=8, sfx="pop" if k == 0 else None)
syr = s3d.cylinder("Syringe", 0.012, 0.16, (TX + 0.17, 2.82, 0.785), rot=(0, math.pi / 2, 0.3), mat=glass, verts=12)
s3d.pop_in(syr, f_treat, dur=8, sfx=None)
s3d.tag("growth hormone deficiency", (X + 0.1, 2.5, 1.62), W(1, "deficiency"), hold=58, size=0.075)
s3d.tag("Barcelona pays", (TX, 2.6, 1.15), W(1, "Barcelona"), hold=50, size=0.075)
kid.pose_at(W(1, "diagnosed"), "stand"); kid.pose_at(W(1, "diagnosed") + 8, "think"); kid.hold(W(1, "diagnosed") + 8, f_treat)
kid.pose_at(f_treat + 6, "thumbs_up"); kid.hold(f_treat + 6, B[2]["fs"])
kit.light("Key1", "AREA", (X - 1.5, -1, 3), 260, (1, 0.96, 0.9), size=3, target=(X, 3, 1))
kit.light("Fill1", "AREA", (X + 2, 0, 1.5), 60, size=2, target=(X, 3, 1))

# ================================================================ 2 — fact 9: Madeira -> Manchester
X = 200
sea = s3d.mat("Sea", (0.015, 0.06, 0.12), rough=0.35)
sea_bsdf = next(n for n in sea.node_tree.nodes if n.type == "BSDF_PRINCIPLED")
if "Specular IOR Level" in sea_bsdf.inputs:
    sea_bsdf.inputs["Specular IOR Level"].default_value = 0.0   # the studio HDRI and backlight otherwise whiten the water
kit.terrain("Ocean", (X, 10, 0), (60, 40), (60, 40), lambda x, y: 0.04 * math.sin(x * 1.3 + y * 0.7) + 0.03 * math.sin(y * 2.1), sea)
kit.sphere("Island", (X - 0.8, 7, -0.3), 1.0, s3d.mat("IslandGreen", (0.1, 0.3, 0.07), rough=0.9, noise=0.4, noise_scale=6), scale=(3.0, 2.0, 1.1))
kit.sphere("Cliffs", (X - 0.8, 7, -0.1), 1.0, s3d.mat("Cliff", (0.28, 0.22, 0.18), rough=0.95, noise=0.5), scale=(3.15, 2.1, 0.45))
kit.cone("Peak", (X - 1.3, 7.4, 1.0), 1.1, 0.05, 1.1, s3d.mat("IslandGreen", (0.1, 0.3, 0.07)))
for k, (dx, dy) in enumerate(((-2.2, 6.6), (0.3, 6.3), (0.9, 7.2), (-0.2, 7.5))):
    kit.cone(f"Tree2_{k}", (X + dx, dy, 0.9), 0.18, 0.0, 0.6, s3d.mat("Pine", (0.04, 0.16, 0.05), rough=0.9))
kit.backdrop("Sky2", (X, 22, 4), w=60, h=30, bottom=(1.0, 0.42, 0.22), top=(0.28, 0.05, 0.09))
kit.sphere("Sun2", (X + 3, 21.5, 2.0), 1.4, kit.emit("SunDisc", (1, 0.72, 0.45), 4.0))
plane = kit.plane_model("Plane", (X + 0.3, 5.2, 0.95))
plane.scale = (0.9, 0.9, 0.9)
f_moved = W(2, "moved")
kit.key_loc(plane, f_moved - 2, (X + 0.3, 5.2, 0.95))
plane.rotation_euler = (0, 0, 0)
plane.keyframe_insert("rotation_euler", frame=f_moved - 2)
kit.key_loc(plane, f_moved + 42, (X + 2.4, 1.6, 2.5))
plane.rotation_euler = (0.25, -0.3, -0.45)
plane.keyframe_insert("rotation_euler", frame=f_moved + 42)
s3d.marker("whoosh", f_moved, prompt="jet airliner takeoff roar passing")
s3d.tag("Madeira", (X - 0.8, 5.2, 1.8), W(2, "Madeira"), hold=60, size=0.16)
s3d.tag("age 18", (X + 1.2, 4.0, 2.4), W(2, "eighteen"), hold=50, size=0.16)
kit.light("Sun2L", "AREA", (X + 4, 14, 6), 2500, (1, 0.6, 0.4), size=6, target=(X, 6, 0))
kit.light("Fill2", "AREA", (X, -4, 4), 160, (0.85, 0.7, 0.8), size=4, target=(X, 6, 0.5))

# ================================================================ 3 — fact 8: the napkin contract
X = 300
s3d.box("Table3", (3.0, 2.0, 0.08), (X, 0.6, 0.86), s3d.mat_wood())
kit.backdrop("BD3", (X, 5, 2), w=14, h=10, bottom=(0.8, 0.86, 0.93), top=(0.95, 0.97, 1.0), strength=0.9)
napkin = s3d.box("Napkin", (1.0, 1.0, 0.006), (X, 0.55, 0.905), s3d.mat("NapkinPaper", (0.97, 0.97, 0.95), rough=0.85, noise=0.15, noise_scale=40), bevel=0.002)
napkin.rotation_euler = (0, 0, 0.12)
f3 = B[3]["fs"]
s3d.drop_in(napkin, f3 + 3, height=1.0, dur=14, sfx="whoosh", prompt="paper napkin flutters down onto a table")
blue_ink = s3d.mat("BlueInk", (0.04, 0.08, 0.4), rough=0.4)
f_con = W(3, "contract")
for r, (y, L) in enumerate(((0.3, 0.62), (0.18, 0.7), (0.06, 0.55), (-0.06, 0.66))):
    ln = kit.mesh_obj(f"InkLine{r}", [(0, -0.008, 0), (L, -0.008, 0), (L, 0.008, 0), (0, 0.008, 0)], [(0, 1, 2, 3)], blue_ink)
    ln.parent = napkin
    ln.location = (-0.38, y, 0.0035)
    ln.scale = (0, 1, 1)
    ln.keyframe_insert("scale", frame=1)
    ln.keyframe_insert("scale", frame=f_con + r * 5)
    ln.scale = (1, 1, 1)
    ln.keyframe_insert("scale", frame=f_con + r * 5 + 8)
cu = bpy.data.curves.new("Signature", "CURVE")
cu.dimensions = "3D"
cu.bevel_depth = 0.004
sp = cu.splines.new("POLY")
pts = [(-0.25 + 0.55 * t / 59, -0.28 + 0.05 * math.sin(t * 0.55) + 0.02 * math.sin(t * 1.7), 0.004) for t in range(60)]
sp.points.add(len(pts) - 1)
for p, c in zip(sp.points, pts):
    p.co = (*c, 1)
sig = kit.link(bpy.data.objects.new("Signature", cu))
cu.materials.append(blue_ink)
sig.parent = napkin
f_sign = W(3, "signed")
cu.bevel_factor_end = 0.0
cu.keyframe_insert("bevel_factor_end", frame=f_sign)
cu.bevel_factor_end = 1.0
cu.keyframe_insert("bevel_factor_end", frame=f_sign + 18)
pen = kit.empty("PenRig", (0, 0, 0))
pen.parent = napkin
pen.rotation_euler = (0.35, 0.5, 0)
body = s3d.cylinder("Pen", 0.012, 0.17, (0, 0, 0), mat=s3d.mat("PenBody", (0.05, 0.1, 0.35), rough=0.3), verts=16)
body.parent = pen
body.location = (0, 0, 0.095)
for k in range(0, 60, 6):
    kit.key_loc(pen, f_sign + int(18 * k / 59), (pts[k][0], pts[k][1], 0.006))
kit.key_loc(pen, f_sign - 6, (pts[0][0] - 0.05, pts[0][1], 0.06))
kit.key_loc(pen, f_sign + 26, (pts[-1][0] + 0.08, pts[-1][1] - 0.04, 0.08))
kit.lathe("Cup3", [(0.035, 0), (0.045, 0.01), (0.055, 0.09), (0.05, 0.095)], (X + 0.62, 1.15, 0.9), s3d.mat("Porcelain", (0.95, 0.95, 0.93), rough=0.2))
kit.lathe("Saucer3", [(0.07, 0), (0.1, 0.012), (0.095, 0.014)], (X + 0.62, 1.15, 0.9), s3d.mat("Porcelain", (0.95, 0.95, 0.93)))
s3d.tag("age 13", (X - 0.55, 0.2, 1.3), W(3, "thirteen"), hold=50, size=0.09)
kit.light("Key3", "AREA", (X - 1.5, -1, 3.2), 300, (1, 0.95, 0.88), size=3, target=(X, 0.6, 0.9))
kit.light("Fill3", "AREA", (X + 1.8, 0, 2), 80, (0.85, 0.9, 1.0), size=2, target=(X, 0.6, 0.9))

# ================================================================ 4 — fact 7: Champions League 5 vs 4
X = 400
duel_stage(X)
f5, f4 = W(4, "five"), W(4, "four")
for i in range(5):
    c = kit.cup(f"CupR{i}", (X + 0.72 + (i - 2) * 0.245, 2.2, 0.5), 0.3, SILVER)
    s3d.pop_in(c, f5 + i * 3, dur=8, sfx="pop" if i == 0 else None)
for i in range(4):
    c = kit.cup(f"CupM{i}", (X - 0.72 + (i - 1.5) * 0.28, 2.2, 0.5), 0.3, SILVER)
    s3d.pop_in(c, f4 + i * 3, dur=8, sfx="pop" if i == 0 else None)
count_text(X, "R", 5, f5 + 12)
count_text(X, "L", 4, f4 + 9)

# ================================================================ 5 — fact 6: Ballon d'Or 8 vs 5
X = 500
duel_stage(X)
f8, f5b = W(5, "eight"), W(5, "five")
for i in range(8):
    row, col = divmod(i, 4)
    g = kit.golden_ball(f"GBM{i}", (X - 0.72 + (col - 1.5) * 0.29, 2.36 - row * 0.3, 0.5), 0.12, GOLD)
    s3d.pop_in(g, f8 + i * 2, dur=8, sfx="pop" if i == 0 else None)
for i, (col, row) in enumerate(((-1, 0), (0, 0), (1, 0), (-0.5, 1), (0.5, 1))):
    g = kit.golden_ball(f"GBR{i}", (X + 0.72 + col * 0.29, 2.36 - row * 0.3, 0.5), 0.12, GOLD)
    s3d.pop_in(g, f5b + i * 2, dur=8, sfx="pop" if i == 0 else None)
count_text(X, "L", 8, f8 + 16, z=1.2)
count_text(X, "R", 5, f5b + 10, z=1.2)

# ================================================================ 6 — fact 5: Euro 2016 + all-time top scorer
X = 600
kit.floor("Floor6", (X, 2, 0), (14, 10), s3d.mat("Studio6", (0.05, 0.025, 0.025), rough=0.75))
kit.backdrop("BD6", (X, 8, 3), w=16, h=14, bottom=(0.55, 0.05, 0.04), top=(0.06, 0.0, 0.01))
s3d.box("Plinth6", (0.6, 0.6, 0.6), (X - 0.7, 2.0, 0.3), s3d.mat("PlinthDark", (0.08, 0.02, 0.02), rough=0.35))
euro = kit.lathe("Euro", [(r * 1.4, z * 1.4) for r, z in ((0.09, 0), (0.09, 0.04), (0.04, 0.07), (0.03, 0.35), (0.06, 0.42),
                                                        (0.09, 0.5), (0.12, 0.6), (0.15, 0.66), (0.145, 0.67))],
                 (X - 0.7, 2.0, 0.6), SILVER)
s3d.pop_in(euro, W(6, "Euro"), dur=10)
kit.goal("Goal6", (X + 0.55, 3.0, 0), w=1.4, h=0.9, d=0.7)
f_sc = W(6, "scorer")
rng = random.Random(4)
for i in range(14):
    b = kit.football(f"Ball6_{i}", 0.11, (X + 0.55 + rng.uniform(-0.5, 0.5), 3.3 + rng.uniform(0, 0.3), 0.11 + 0.18 * (i // 6)))
    if i % 4 == 0:
        s3d.drop_in(b, f_sc + i * 2, height=2.4, dur=12, sfx="thud")
    else:
        drop_quiet(b, f_sc + i * 2, height=2.4, dur=12)
s3d.tag("EURO 2016", (X - 0.7, 1.7, 1.75), W(6, "Euro"), hold=55, size=0.12)
s3d.tag("all-time top scorer", (X + 0.45, 2.6, 1.4), f_sc, hold=60, size=0.1)
kit.light("Key6", "AREA", (X - 1.5, -1, 3), 300, (1, 0.92, 0.85), size=3, target=(X, 2.5, 0.7))
kit.light("Rim6", "AREA", (X + 1.5, 5, 3), 450, RED, size=3, target=(X, 2.5, 0.7))
kit.light("Spot6", "SPOT", (X - 0.7, 1.6, 3.5), 400, target=(X - 0.7, 2.0, 0.9), spot=0.4)

# ================================================================ 7 — fact 4: World Cup 2022
X = 700
kit.floor("Floor7", (X, 2, 0), (14, 10), s3d.mat("Studio7", (0.03, 0.035, 0.05), rough=0.4))
kit.backdrop("BD7", (X, 8, 3), w=16, h=14, bottom=(0.12, 0.28, 0.5), top=(0.0, 0.01, 0.03))
s3d.cylinder("Ped7", 0.42, 0.9, (X + 0.35, 2.6, 0.45), mat=s3d.mat("Marble", (0.05, 0.05, 0.06), rough=0.3))
s = 1.6
wc = kit.lathe("WorldCup", [(r * s, z * s) for r, z in ((0.17, 0), (0.17, 0.05), (0.15, 0.07), (0.12, 0.13), (0.09, 0.25),
                                                      (0.11, 0.4), (0.14, 0.52), (0.1, 0.6), (0.05, 0.62))], (X + 0.35, 2.6, 0.9), GOLD)
kit.sphere("WCGlobe", (X + 0.35, 2.6, 0.9 + 0.75 * s), 0.16 * s, GOLD)
green = s3d.mat("Malachite", (0.02, 0.35, 0.15), rough=0.25)
for z in (0.03, 0.06):
    kit.torus("WCBand", (X + 0.35, 2.6, 0.9 + z * s), 0.165 * s, 0.012 * s, mat=green)
kneel = kit.silhouette(human.Human("Kneel", loc=(X - 0.75, 2.0, 0.0), facing=25, seed=3), SIL)
f_won = W(7, "won")
kneel.pose_at(f_won, "stand")
kneel.place(f_won, (X - 0.75, 2.0, 0.0), 25)
pose_kneel = dict(human.POSES["crouch"])
pose_kneel["head"] = (30, 0, 0)
kneel.pose_at(f_won + 12, pose_kneel)
kneel.place(f_won + 12, (X - 0.75, 2.0, -0.32), 25)
kneel.hold(f_won + 12, B[8]["fs"])
cmats = [s3d.mat("ConfBlue", LB, rough=0.5), s3d.mat("ConfWhite", (0.95, 0.95, 0.95), rough=0.5), GOLD]
kit.flakes("Confetti7", (X, 2.3, 4.8), area=(5, 3), height=12, n=450, size=0.03, mats=cmats, f0=f_won, f1=B[8]["fs"], fall=9, spin=0.6)
s3d.tag("2022", (X + 0.35, 2.1, 2.75), W(7, "2022"), hold=60, size=0.16)
kit.light("Spot7", "SPOT", (X + 0.35, 2.2, 4.5), 900, (1, 0.95, 0.85), target=(X + 0.35, 2.6, 1.3), spot=0.45)
kit.light("Rim7", "AREA", (X - 2, 4, 2.5), 300, LB, size=2, target=(X - 0.75, 2, 0.8))
kit.light("Fill7", "AREA", (X, -3, 2.5), 50, (0.7, 0.8, 1), size=4, target=(X, 2, 1))

# ================================================================ 8 — fact 3: Saudi Arabia, still scoring
X = 800


def dunes(x, y):
    yw = y + 12
    k = min(1.0, max(0.0, (yw - 4) / 6))
    return k * (0.35 * math.sin(x * 0.35 + y * 0.2) + 0.25 * math.sin(y * 0.5 - x * 0.15) + 0.08 * max(0, yw - 8))


kit.terrain("Dunes", (X, 12, 0), (50, 40), (100, 80), dunes, s3d.mat("Sand", (0.85, 0.58, 0.32), rough=0.9, noise=0.2, noise_scale=12))
kit.backdrop("Sky8", (X, 31, 6), w=70, h=30, bottom=(1.0, 0.68, 0.38), top=(0.45, 0.18, 0.08))
kit.sphere("Sun8", (X + 3, 30, 3.5), 1.6, kit.emit("SunDisc8", (1, 0.85, 0.6), 5.0))
kit.goal("Goal8", (X + 0.9, 4.0, 0), w=2.0, h=0.9, d=0.7)
trunk8, leaf8 = s3d.mat("PalmTrunk", (0.3, 0.2, 0.12), rough=0.9), s3d.mat("PalmLeaf", (0.12, 0.3, 0.08), rough=0.7)
palm("Palm8a", (X - 2.2, 6, 0), mat=trunk8, leaf=leaf8)
palm("Palm8b", (X + 2.6, 7.5, 0), h=4.6, mat=trunk8, leaf=leaf8)
striker = human.Human("Striker", loc=(X - 1.0, 2.5, 0.0), facing=50, outfit=RON_KIT, seed=0)
ball8 = kit.football("Ball8", 0.11, (X - 0.62, 2.65, 0.11))
f_kick = W(8, "scoring")
striker.walk(B[8]["fs"] + 4, f_kick - 2, to=(X - 0.78, 2.55), face_end=50)
kit.key_loc(ball8, f_kick, (X - 0.62, 2.65, 0.11))
kit.key_loc(ball8, f_kick + 6, (X + 0.1, 3.4, 0.55))
kit.key_loc(ball8, f_kick + 11, (X + 0.9, 4.45, 0.45))
kit.key_loc(ball8, f_kick + 16, (X + 0.95, 4.5, 0.11))
s3d.marker("thud", f_kick, prompt="football kicked hard")
s3d.marker("whoosh", f_kick + 8, prompt="ball hits the net swish")
striker.act(f_kick + 14, "cheer", cycles=2, period=14)
s3d.tag("Saudi Arabia", (X, 3.0, 1.9), W(8, "Saudi"), hold=50, size=0.14)
kit.light("Sun8L", "AREA", (X + 6, 12, 8), 3000, (1, 0.75, 0.5), size=8, target=(X, 3, 0))
kit.light("Fill8", "AREA", (X, -4, 3), 120, (1, 0.85, 0.7), size=4, target=(X, 3, 0.8))

# ================================================================ 9 — fact 2: Inter Miami, the show
X = 900
kit.floor("Pitch9", (X, 4, 0), (30, 20), s3d.mat("Pitch", (0.05, 0.22, 0.06), rough=0.8, noise=0.25, noise_scale=6))
line_m = kit.emit("PitchLine", (0.9, 0.9, 0.9), 0.6)
s3d.box("Line9", (30, 0.08, 0.005), (X, 5.5, 0.003), line_m, bevel=0)
crowd = s3d.mat("Crowd", (0.04, 0.04, 0.06), rough=0.8)
nt = crowd.node_tree
bsdf = next(n for n in nt.nodes if n.type == "BSDF_PRINCIPLED")
nz = nt.nodes.new("ShaderNodeTexNoise")
nz.inputs["Scale"].default_value = 90
ramp = nt.nodes.new("ShaderNodeValToRGB")
ramp.color_ramp.interpolation = "CONSTANT"
ramp.color_ramp.elements[1].position = 0.68
ramp.color_ramp.elements[1].color = (1.0, 0.75, 0.9, 1)
nt.links.new(nz.outputs["Fac"], ramp.inputs["Fac"])
nt.links.new(ramp.outputs["Color"], bsdf.inputs["Emission Color"])
bsdf.inputs["Emission Strength"].default_value = 3.0
stand = s3d.box("Stands9", (26, 7, 0.3), (X, 13, 3.0), crowd, bevel=0)
stand.rotation_euler = (0.55, 0, 0)
for sx in (-3.5, 3.5):
    s3d.cylinder("Tower9", 0.12, 8, (X + sx, 10, 4), mat=s3d.mat("TowerSteel", (0.2, 0.2, 0.22), rough=0.5), verts=10)
    s3d.box("Flood9", (1.3, 0.2, 0.7), (X + sx, 9.9, 8.1), kit.emit("Floodlight", (1, 0.97, 0.9), 9.0))
kit.backdrop("Sky9", (X, 22, 6), w=60, h=30, bottom=(0.35, 0.08, 0.3), top=(0.02, 0.0, 0.05))
palm("Palm9a", (X - 3.4, 7, 0), h=4.8)
palm("Palm9b", (X + 3.6, 7.5, 0), h=4.2)
leo = human.Human("Leo", loc=(X, 2.6, 0.0), facing=0, outfit=dict(shirt=(0.97, 0.6, 0.75), pants=(0.05, 0.05, 0.05), shoes=(0.9, 0.9, 0.9), hat=None), seed=1)
kit.football("Ball9", 0.11, (X + 0.32, 2.4, 0.11))
f_show = W(9, "show")
leo.act(f_show - 4, "wave", cycles=2, period=14)
for k, (pos, col) in enumerate((((X - 1.5, 15, 7.0), (1.0, 0.45, 0.75)), ((X + 1.8, 15, 8.2), (0.5, 0.85, 1.0)),
                                ((X - 0.2, 16, 9.4), (1.0, 0.95, 0.85)), ((X + 2.8, 16, 6.2), (1.0, 0.45, 0.75)),
                                ((X - 2.8, 16, 8.8), (0.5, 0.85, 1.0)))):
    f = W(9, "Inter") if k == 0 else f_show + (k - 1) * 7
    kit.burst(f"Burst9_{k}", pos, f, col, seed=k)
kit.light("SpotPink", "SPOT", (X - 3, -1, 6), 900, (1, 0.5, 0.8), target=(X, 2.6, 0.9), spot=0.4)
kit.light("SpotCyan", "SPOT", (X + 3, -1, 6), 700, (0.5, 0.85, 1.0), target=(X, 2.6, 0.9), spot=0.4)
kit.light("Fill9", "AREA", (X, -3, 2.5), 60, (0.8, 0.8, 1), size=4, target=(X, 2.6, 1))

# ================================================================ HUD: title, fact number, score
white = kit.emit("HudWhite", (1, 1, 1), 2.2)
yellow = kit.emit("HudYellow", (1, 0.82, 0.25), 2.2)
m_blue = kit.emit("HudBlue", LB, 2.2)
m_red = kit.emit("HudRed", (1.0, 0.18, 0.12), 2.6)
digit_m = kit.emit("DigitM", (1, 1, 1), 2.4)
digit_r = kit.emit("DigitR", (1, 1, 1), 2.4)

t1 = kit.hud_text(hud, "Title", "MESSI vs RONALDO", (0, 1.32, 0), 0.15, white)
t2 = kit.hud_text(hud, "Rule", "10 FACTS  ·  1 POINT EACH", (0, 1.14, 0), 0.075, yellow)
for t in (t1, t2):
    kit.vis(t, 2, B[1]["fs"], pop=0)

score = kit.empty("Score", (0, 0.12, 0), hud)
plate = s3d.box("ScorePlate", (1.62, 0.34, 0.01), (0, 0, 0), kit.emit("PlateDark", (0.02, 0.025, 0.05), 1.0), bevel=0.004)
plate.parent = score
plate.location = (0, 0, -0.01)
name_m = kit.hud_text(score, "NameM", "MESSI", (-0.5, 0, 0), 0.12, m_blue)
name_r = kit.hud_text(score, "NameR", "RONALDO", (0.52, 0, 0), 0.12, m_red)
kit.hud_text(score, "Colon", ":", (0, 0.015, 0), 0.22, white)

points = {"M": [W(1, "treatment"), W(3, "napkin"), W(5, "five"), W(7, "missing"), W(9, "show")],
          "R": [W(2, "United"), W(4, "five", 4), W(6, "matches"), W(8, "scoring", 12), W(10, "history")]}
for side, frames in points.items():
    x = -0.13 if side == "M" else 0.13
    bounds = [1] + frames + [None]
    for v in range(6):
        d = kit.hud_text(score, f"D{side}{v}", str(v), (x, 0, 0), 0.24, digit_m if side == "M" else digit_r)
        kit.vis(d, bounds[v], bounds[v + 1], pop=0 if v == 0 else 6, over=1.6)
    for k, f in enumerate(frames):
        plus = kit.hud_text(hud, f"Plus{side}{k}", "+1", (x * 4, 0.95, 0.05), 0.16, m_blue if side == "M" else m_red)
        kit.vis(plus, f, f + 16, pop=5)
        kit.key_loc(plus, f, (x * 4, 0.92, 0.05))
        kit.key_loc(plus, f + 15, (x * 4, 1.08, 0.05))
        s3d.marker("pop", f, prompt="bright arcade point scored ding")

f_55 = W(10, "5:5")
f_top = B[1]["fs"]
# On the stage only the big digits sit between the silhouettes; plate + names belong to the top-bar layout.
MID = ((0, 0.12, 0), 1.0)
for f, loc, sc_ in ((1, *MID), (f_top - 1, *MID), (f_top + 7, (0, 1.3, 0), 0.85),
                    (f_55 - 6, (0, 1.3, 0), 0.85), (f_55 + 4, *MID), (END, (0, 0.12, 0), 1.05)):
    kit.key_loc(score, f, loc)
    kit.key_scale(score, f, sc_)
for ob in (plate, name_m, name_r):
    kit.vis(ob, f_top + 2, f_55 - 2, pop=0)
f_quiet = int(round(B[10]["words"][-1]["e"] * 24)) + 2
for k, f in enumerate(range(f_quiet, B[11]["fs"], 5)):
    for m in (digit_m, digit_r):
        kit.emit_key(m, f, 0.25 if k % 2 == 0 else 3.5)
for m in (digit_m, digit_r):
    kit.emit_key(m, B[11]["fs"], 2.4)

badge_plate = s3d.box("BadgePlate", (0.5, 0.13, 0.01), (0, 0, 0), kit.emit("PlateDark", (0.02, 0.025, 0.05), 1.0), bevel=0.004)
badge_plate.parent = hud
badge_plate.location = (0, 0.98, -0.01)
kit.vis(badge_plate, B[1]["fs"], B[11]["fs"], pop=0)
for i in range(1, 11):
    badge = kit.hud_text(hud, f"Fact{i}", f"FACT #{11 - i}", (0, 0.98, 0), 0.085, yellow)
    kit.vis(badge, B[i]["fs"], B[i + 1]["fs"], pop=5)
kit.vis(kit.hud_text(hud, "Ask", "WHO'S BETTER?", (0, 1.15, 0), 0.17, white), B[11]["fs"], pop=6)
kit.vis(kit.hud_text(hud, "Vote", "VOTE IN THE COMMENTS", (0, 0.97, 0), 0.08, yellow), W(11, "comments"), pop=6)

# ================================================================ camera: one shot per beat, hard cuts
shots = [((0, -3.8, 1.05), (0, 2, 0.95), (0, -3.3, 1.0), (0, 2, 0.95)),
         ((100.1, -1.3, 0.95), (100.1, 2.9, 0.75), (100.1, -0.8, 0.9), (100.1, 2.9, 0.75)),
         ((200.2, -3.5, 1.7), (200.4, 6, 1.0), (200.5, -2.6, 1.8), (200.5, 6, 1.1)),
         ((300, -1.5, 2.45), (300, 0.5, 0.9), (300, -1.0, 2.0), (300, 0.45, 0.9)),
         ((400, -2.9, 1.1), (400, 2.2, 0.62), (400, -2.4, 1.05), (400, 2.2, 0.62)),
         ((500, -2.9, 1.1), (500, 2.2, 0.62), (500, -2.4, 1.05), (500, 2.2, 0.62)),
         ((600.0, -2.6, 1.1), (600.0, 2.6, 0.7), (600.0, -2.0, 1.05), (600.0, 2.6, 0.7)),
         ((700, -4.0, 1.5), (700.1, 2.4, 1.25), (700.05, -3.0, 1.45), (700.1, 2.4, 1.2)),
         ((800, -3.6, 1.15), (800.1, 3.2, 0.75), (800.1, -2.8, 1.1), (800.1, 3.2, 0.75)),
         ((900, -4.5, 1.4), (900, 3, 2.0), (900, -3.6, 1.35), (900, 3, 1.9)),
         ((0, -3.7, 1.05), (0, 2, 0.95), (0, -3.2, 1.0), (0, 2, 0.95)),
         ((0, -3.3, 1.0), (0, 2, 0.95), (0, -3.9, 1.1), (0, 2, 0.95))]
for i, (e0, l0, e1, l1) in enumerate(shots):
    f0 = 1 if i == 0 else B[i]["fs"]
    f1 = END + 1 if i == len(shots) - 1 else B[i + 1]["fs"]
    cam.shot(f0, f1, e0, l0, e1, l1)
cam.finish()

# ================================================================ output
if MODE == "preview":
    os.makedirs(os.path.join(WORK, "preview"), exist_ok=True)
    for i, b in enumerate(B):
        for tag_, f in (("a", b["fs"] + 6), ("b", b["fe"] - 4)):
            s3d.preview_still(os.path.join(WORK, "preview", f"b{i:02d}{tag_}_f{f:04d}.png"), frame=f, scale=30, samples=4)
    s3d.qa_gate(abort=False)
elif MODE == "time":
    import time
    sc = bpy.context.scene
    f0 = int(os.environ.get("S3D_FRAME", "30"))
    for f in (f0, f0 + 1, f0 + 2):
        sc.frame_set(f)
        sc.render.filepath = f"/tmp/time_{f}.png"
        t = time.time()
        bpy.ops.render.render(write_still=True)
        print("TIME", f, round(time.time() - t, 1), flush=True)
elif MODE == "draft":
    sc = bpy.context.scene
    sc.render.engine = "BLENDER_WORKBENCH"
    sc.display.shading.color_type = "MATERIAL"
    s3d.render_mp4(os.path.join(WORK, "draft.mp4"), scale=30)
else:
    kit.render_frames(WORK)
