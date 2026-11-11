"""Gagarin — "7 facts that are not in textbooks"  (kylo-3d-shorts pipeline, fact-countdown format)

  blender --background --python build.py -- <workdir> [preview|draft|full]
Warm Soviet palette; black-and-white (fact 7) and the glitch (fact 2) are applied in post (tools/post.sh).
"""
import math
import os
import random
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "..", "tools"))
import kit  # noqa: E402

import bmesh  # noqa: E402
import bpy  # noqa: E402
import human  # noqa: E402
import s3d  # noqa: E402
from mathutils import Vector  # noqa: E402

argv = sys.argv[sys.argv.index("--") + 1:]
WORK = argv[0]
MODE = argv[1] if len(argv) > 1 else "full"
B = s3d.load_beats(os.path.join(WORK, "beats.json"))
kit.setup(B, sun=0.6)
W = lambda i, w=None, o=0: s3d.when(B, i, w, o)  # noqa: E731
END = bpy.context.scene.frame_end

CREAM = (0.98, 0.9, 0.72)
ORANGE_SUIT = dict(shirt=(0.95, 0.36, 0.06), pants=(0.95, 0.36, 0.06), shoes=(0.15, 0.12, 0.1), hat="hardhat", hat_color=(0.97, 0.97, 0.95))
SUIT_NOHAT = dict(ORANGE_SUIT, hat=None)
STEEL = kit.metal("HullSteel", (0.62, 0.63, 0.66), rough=0.3)
DARK_HULL = s3d.mat("Scorched", (0.18, 0.15, 0.13), rough=0.6, metal=0.4, noise=0.4)


def vostok(name, loc, scale=1.0):
    """Descent sphere + biconic instrument module, axis along +X (sphere at the front)."""
    root = kit.empty(name, loc)
    root.scale = (scale,) * 3
    parts = [kit.sphere(name + "_ball", (0, 0, 0), 0.6, s3d.mat("VostokBall", (0.3, 0.3, 0.31), rough=0.4, metal=0.6))]
    a = kit.cone(name + "_c1", (0, 0, 0), 0.25, 0.62, 0.55, STEEL, rot=(0, -math.pi / 2, 0))
    b = kit.cone(name + "_c2", (0, 0, 0), 0.62, 0.32, 0.65, STEEL, rot=(0, -math.pi / 2, 0))
    parts += [a, b]
    offs = [(0, 0, 0), (-0.8, 0, 0), (-1.4, 0, 0)]
    for k in range(3):
        parts.append(s3d.cylinder(f"{name}_ant{k}", 0.012, 0.9, (0, 0, 0), rot=(0, 0.5, k * 2.1), mat=STEEL, verts=8))
        offs.append((0.2, 0, 0))
    for p, o in zip(parts, offs):
        p.parent = root
        p.location = o
    for k in range(3):
        parts[3 + k].rotation_euler = (math.cos(k * 2.1) * 0.9, math.sin(k * 2.1) * 0.9, 0)
    return root


def earth_mat():
    m = bpy.data.materials.new("Earth")
    m.use_nodes = True
    nt = m.node_tree
    bsdf = next(n for n in nt.nodes if n.type == "BSDF_PRINCIPLED")
    tc = nt.nodes.new("ShaderNodeTexCoord")
    nz = nt.nodes.new("ShaderNodeTexNoise")
    nz.inputs["Scale"].default_value = 0.09
    nz.inputs["Detail"].default_value = 8
    nt.links.new(tc.outputs["Object"], nz.inputs["Vector"])
    land = nt.nodes.new("ShaderNodeValToRGB")
    e = land.color_ramp.elements
    e[0].position, e[0].color = 0.5, (0.02, 0.07, 0.2, 1)
    e[1].position, e[1].color = 0.54, (0.18, 0.28, 0.1, 1)
    land.color_ramp.elements.new(0.65).color = (0.42, 0.36, 0.22, 1)
    nt.links.new(nz.outputs["Fac"], land.inputs["Fac"])
    cl = nt.nodes.new("ShaderNodeTexNoise")
    cl.inputs["Scale"].default_value = 0.25
    cl.inputs["Detail"].default_value = 6
    nt.links.new(tc.outputs["Object"], cl.inputs["Vector"])
    clr = nt.nodes.new("ShaderNodeValToRGB")
    clr.color_ramp.elements[0].position = 0.55
    clr.color_ramp.elements[1].position = 0.7
    nt.links.new(cl.outputs["Fac"], clr.inputs["Fac"])
    mix = nt.nodes.new("ShaderNodeMix")
    mix.data_type = "RGBA"
    nt.links.new(clr.outputs["Color"], mix.inputs[0])
    nt.links.new(land.outputs["Color"], mix.inputs[6])
    mix.inputs[7].default_value = (0.95, 0.95, 0.95, 1)
    nt.links.new(mix.outputs[2], bsdf.inputs["Base Color"])
    lw = nt.nodes.new("ShaderNodeLayerWeight")
    lw.inputs["Blend"].default_value = 0.35
    pw = nt.nodes.new("ShaderNodeMath")
    pw.operation = "POWER"
    pw.inputs[1].default_value = 2.5
    nt.links.new(lw.outputs["Facing"], pw.inputs[0])
    bsdf.inputs["Emission Color"].default_value = (0.3, 0.6, 1.0, 1)
    sc = nt.nodes.new("ShaderNodeMath")
    sc.operation = "MULTIPLY"
    sc.inputs[1].default_value = 3.0
    nt.links.new(pw.outputs[0], sc.inputs[0])
    nt.links.new(sc.outputs[0], bsdf.inputs["Emission Strength"])
    bsdf.inputs["Roughness"].default_value = 0.7
    return m


def cut_front(o, open_y):
    bm = bmesh.new()
    bm.from_mesh(o.data)
    bmesh.ops.delete(bm, geom=[f for f in bm.faces if f.calc_center_median().y < open_y], context="FACES")
    bm.to_mesh(o.data)
    bm.free()


def shell(name, loc, r, mat, open_y=-0.3, thick=0.04):
    """Sphere with the camera-facing side cut away (cutaway capsule)."""
    o = kit.sphere(name, loc, r, mat, seg=48)
    cut_front(o, open_y * r)
    so = o.modifiers.new("Thick", "SOLIDIFY")
    so.thickness = thick
    return o


def canopy(name, loc, r, mat, depth=1.1):
    prof = [(r * math.sin(t), r * math.cos(t) * 0.75) for t in [k * depth / 14 for k in range(15)]]
    c = kit.lathe(name, prof, loc, mat, seg=32, cap=False)
    so = c.modifiers.new("Thick", "SOLIDIFY")
    so.thickness = 0.02
    return c, r * math.sin(depth), r * math.cos(depth) * 0.75


def lines(name, top_center, rim_r, rim_z, bottom, mat, n=8):
    out = []
    for k in range(n):
        a = k * math.tau / n
        p0 = (top_center[0] + rim_r * math.cos(a), top_center[1] + rim_r * math.sin(a), top_center[2] + rim_z)
        mid = [(p0[i] + bottom[i]) / 2 for i in range(3)]
        d = [bottom[i] - p0[i] for i in range(3)]
        ln = math.sqrt(sum(x * x for x in d))
        c = s3d.cylinder(f"{name}{k}", 0.006, ln, mid, mat=mat, verts=6)
        c.rotation_euler = Vector(d).to_track_quat("Z", "Y").to_euler()
        out.append(c)
    return out


cam = kit.Cam(35)
hud = cam.hud(3.0)

# ================================================================ 0 / 8 — Vostok-1 above the Earth
kit.backdrop("Space", (0, 40, 0), w=90, h=90, bottom=(0.0, 0.0, 0.0), top=(0.0, 0.0, 0.0), strength=0.0)
kit.flakes("Stars", (0, 36, -20), area=(70, 1), height=60, n=1400, size=0.05, mats=[kit.emit("Star", (1, 0.95, 0.85), 3.0)], fall=0, seed=3)
earth = kit.sphere("EarthBall", (0, 16, -21.5), 20, earth_mat(), seg=96)
earth.rotation_euler = (0.4, 0.2, 0)
earth.keyframe_insert("rotation_euler", frame=1)
earth.rotation_euler = (0.4, 0.2, 0.06)
earth.keyframe_insert("rotation_euler", frame=END)
kit.linear(earth)
ship = vostok("Vostok", (0.3, 3.0, 1.0), 0.8)
kit.key_loc(ship, 1, (0.1, 3.0, 1.05))
kit.key_loc(ship, END, (0.8, 3.0, 1.2))
ship.rotation_euler = (0.1, -0.08, -0.25)
ship.keyframe_insert("rotation_euler", frame=1)
ship.rotation_euler = (0.35, -0.08, -0.05)
ship.keyframe_insert("rotation_euler", frame=END)
kit.linear(ship)
kit.light("SunKey", "AREA", (-7, 0, 5), 2200, (1, 0.95, 0.88), size=3, target=(0, 3, 0.5), cutoff=60)
kit.light("EarthBounce", "AREA", (0, 2, -3), 200, (0.4, 0.6, 1.0), size=4, target=(0, 3, 1), cutoff=12)
s3d.tag("VOSTOK-1", (0.3, 2.4, 2.05), 14, hold=70, size=0.12)

# ================================================================ 1 — #7 Klushino, the dugout (b/w in post)
X = 100
snow = s3d.mat("Snow", (0.9, 0.9, 0.92), rough=0.85, noise=0.15, noise_scale=10)
kit.terrain("SnowField", (X, 8, 0), (30, 24), (60, 48), lambda x, y: 0.12 * math.sin(x * 0.7) * math.sin(y * 0.5 + 1) * min(1, max(0, (y + 6) / 6)), snow)
kit.backdrop("Sky1", (X, 20, 4), w=40, h=24, bottom=(0.78, 0.78, 0.8), top=(0.42, 0.44, 0.48))
earth_m = s3d.mat("FrozenEarth", (0.22, 0.16, 0.11), rough=0.95, noise=0.5)
kit.sphere("Mound", (X + 0.2, 3.3, -0.05), 1.0, earth_m, scale=(1.6, 1.3, 0.62))
kit.sphere("MoundSnow", (X + 0.25, 3.4, 0.03), 1.0, snow, scale=(1.5, 1.2, 0.58))
s3d.box("Doorway", (0.6, 0.1, 0.75), (X + 0.15, 2.08, 0.32), s3d.mat("Dark", (0.01, 0.01, 0.01), rough=1.0), bevel=0.01)
wood = s3d.mat_wood()
for px in (-0.2, 0.5):
    s3d.cylinder("Post", 0.05, 0.85, (X + px, 2.02, 0.4), mat=wood, verts=10)
s3d.cylinder("Lintel", 0.05, 0.85, (X + 0.15, 2.02, 0.8), rot=(0, math.pi / 2, 0), mat=wood, verts=10)
s3d.cylinder("Stovepipe", 0.05, 0.6, (X + 0.6, 3.4, 0.85), mat=s3d.mat("Rust", (0.2, 0.12, 0.08), rough=0.6, metal=0.5), verts=12)
smoke = s3d.mat("Smoke", (0.55, 0.55, 0.56), rough=1.0)
f1a, f1b = B[1]["fs"], B[2]["fs"]
for k in range(10):
    p = kit.sphere(f"Puff{k}", (X + 0.6, 3.4, 1.2), 0.06, smoke, seg=12)
    f = f1a - 40 + k * 14
    kit.key_scale(p, 1, 0.0)
    kit.key_scale(p, max(2, f - 1), 0.0)
    kit.key_loc(p, max(2, f), (X + 0.6, 3.4, 1.2))
    kit.key_scale(p, max(2, f), 0.6)
    kit.key_loc(p, f + 60, (X + 0.9 + 0.1 * (k % 3), 3.6, 2.4))
    kit.key_scale(p, f + 60, 2.2)
    kit.key_scale(p, f + 61, 0.0)
s3d.house(X - 3.2, 9.0, w=4.0, h=3.2, d=4.0, seed=1)
for k, (dx, dy, h) in enumerate(((-1.8, 5.5, 3.2), (2.2, 6.5, 3.8), (3.2, 4.5, 2.8), (-2.6, 7.5, 3.4))):
    s3d.cylinder(f"Birch{k}", 0.07, h, (X + dx, dy, h / 2), mat=s3d.mat("Bark", (0.82, 0.8, 0.76), rough=0.8, noise=0.6, noise_scale=20), verts=10)
kit.flakes("Snowfall", (X, 2.6, 3.0), area=(7, 4), height=14, n=700, size=0.018, mats=[kit.emit("Flake", (1, 1, 1), 1.2)],
           f0=f1a, f1=f1b, fall=5.5, seed=7)
s3d.tag("Klushino", (X - 0.9, 2.5, 1.6), W(1, "Klushino"), hold=55, size=0.12)
s3d.tag("21 months", (X + 0.2, 1.9, 1.25), W(1, "dugout"), hold=50, size=0.11)
kit.light("Overcast1", "AREA", (X, -2, 6), 600, (0.95, 0.97, 1.0), size=8, target=(X, 3, 0))

# ================================================================ 2 — #6 157 cm, the cockpit
X = 200
kit.floor("Floor2", (X, 2, 0), (14, 10), s3d.mat("Floor2m", (0.12, 0.13, 0.15), rough=0.7))
kit.backdrop("BD2", (X, 8, 3), w=16, h=14, bottom=(0.85, 0.72, 0.5), top=(0.5, 0.12, 0.08))
cream = s3d.mat("RulerCream", (0.95, 0.9, 0.78), rough=0.7)
ink = s3d.mat("Ink2", (0.05, 0.04, 0.04), rough=0.5)
s3d.box("Ruler", (0.26, 0.04, 2.0), (X - 1.05, 2.6, 1.0), cream, bevel=0.005)
for cm in range(10, 200, 10):
    s3d.box(f"RTick{cm}", (0.12 if cm % 50 else 0.2, 0.01, 0.008), (X - 1.12 + (0.0 if cm % 50 else 0.04), 2.575, cm / 100), ink, bevel=0)
    if cm % 50 == 0:
        kit.text(f"RLbl{cm}", str(cm), (X - 0.96, 2.57, cm / 100), 0.05, ink)
mark = s3d.box("Mark157", (0.42, 0.012, 0.018), (X - 0.95, 2.56, 1.57), kit.emit("RedMark", (1, 0.15, 0.08), 3.0), bevel=0)
f157 = W(2, "157")
kit.vis(mark, f157, pop=6)
s3d.tag("157 cm", (X - 0.55, 2.4, 1.75), f157, hold=60, size=0.11)
shell("Capsule", (X + 0.55, 3.0, 0.95), 1.0, s3d.mat("CapsuleSkin", (0.35, 0.33, 0.32), rough=0.5, metal=0.5))
inner = kit.sphere("CapsuleInner", (X + 0.55, 3.05, 0.95), 0.94, s3d.mat("CabinCream", (0.85, 0.8, 0.68), rough=0.8), seg=32)
cut_front(inner, -0.25)
seat_m = s3d.mat("Seat", (0.45, 0.3, 0.15), rough=0.6)
s3d.box("Seat", (0.5, 0.45, 0.08), (X + 0.55, 3.1, 0.45), seat_m)
s3d.box("SeatBack", (0.5, 0.08, 0.7), (X + 0.55, 3.38, 0.8), seat_m)
kit.torus("Porthole", (X + 1.48, 3.0, 1.2), 0.14, 0.025, rot=(0, math.pi / 2, 0), mat=STEEL)
for k, z in enumerate((0.25, 0.75, 1.25, 1.75)):
    s3d.box(f"CTick{k}", (0.1, 0.01, 0.01), (X + 1.62, 2.4, z), ink, bevel=0)
    kit.text(f"CLbl{k}", f"{int(z * 100)}", (X + 1.78, 2.4, z), 0.045, ink)
yuri = human.Human("Yuri", loc=(X - 0.6, 2.5, 0.0), facing=10, outfit=SUIT_NOHAT, seed=0, scale=0.85)
f_cut2 = W(2, "fit", -3)
yuri.place(f_cut2 - 1, (X - 0.6, 2.5, 0.0), 10)
yuri.pose_at(f_cut2 - 1, "stand")
yuri.place(f_cut2, (X + 0.55, 3.05, 0.0), 0)
yuri.pose_at(f_cut2, "sit")
yuri.place(f_cut2 + 1, (X + 0.55, 3.05, -0.33), 0)
yuri.hold(f_cut2 + 1, B[3]["fs"])
kit.light("Key2", "AREA", (X - 1.5, -1.5, 3), 320, (1, 0.93, 0.82), size=3, target=(X, 2.8, 1))
kit.light("Fill2", "AREA", (X + 2.5, 0.5, 2), 90, (0.8, 0.9, 1.0), size=2, target=(X + 0.5, 3, 1))
kit.light("CabinLamp", "POINT", (X + 0.55, 2.6, 1.6), 30, (1, 0.85, 0.6), cutoff=6)

# ================================================================ 3 — #5 twenty candidates, 17 votes
X = 300
kit.floor("Floor3", (X, 3, 0), (16, 12), s3d.mat("Floor3m", (0.06, 0.03, 0.03), rough=0.7))
kit.backdrop("BD3", (X, 10, 3), w=18, h=14, bottom=(0.5, 0.06, 0.04), top=(0.08, 0.01, 0.01))
f_twenty, f_voted = W(3, "twenty"), W(3, "voted")
others = []
gag = None
for row in range(4):
    for col in range(5):
        m = s3d.mat(f"Cand{row}{col}", (0.22, 0.22, 0.23), rough=0.5)
        p = kit.pawn(f"Pawn{row}{col}", (X + (col - 2) * 0.6, 2.2 + row * 0.75, 0), m)
        kit.vis(p, f_twenty - 10 + (row * 5 + col), pop=6)
        if (row, col) == (0, 2):
            gag = (p, m)
        else:
            others.append((p, m))
s3d.color_to(gag[1], (1.0, 0.5, 0.1), W(3, "him"), dur=10)
skip = {3, 11}   # 17 of the other 19 light up: "all but three" (he didn't vote for himself)
for k, (p, m) in enumerate(others):
    if k not in skip:
        s3d.color_to(m, CREAM, f_voted + 2 + k, dur=6)
spot3 = kit.light("Spot3", "SPOT", (X, 1.0, 5), 0, (1, 0.8, 0.5), target=(X, 2.2, 1.0), spot=0.35, cutoff=12)
spot3.data.keyframe_insert("energy", frame=W(3, "him") - 1)
spot3.data.energy = 900
spot3.data.keyframe_insert("energy", frame=W(3, "him") + 6)
votes = kit.text("Votes", "17 / 20", (X, 1.6, 2.35), 0.32, kit.emit("VotesTxt", CREAM, 2.0), extrude=0.02)
kit.vis(votes, f_voted + 22, pop=8)
s3d.marker("pop", f_voted + 22, prompt="soft brass stinger")
kit.light("Key3", "AREA", (X - 1.5, -1, 4), 260, (1, 0.9, 0.8), size=4, target=(X, 3, 0.8))

# ================================================================ 4 — #4 the bus wheel
X = 400
kit.floor("Steppe4", (X, 6, 0), (40, 24), s3d.mat("Steppe", (0.55, 0.45, 0.28), rough=0.95, noise=0.3, noise_scale=4))
s3d.box("Road4", (40, 2.4, 0.01), (X, 2.6, 0.005), s3d.mat("Asphalt", (0.08, 0.08, 0.085), rough=0.85, noise=0.2), bevel=0)
for k in range(12):
    s3d.box(f"Dash{k}", (0.6, 0.08, 0.004), (X - 8 + k * 1.5, 1.55, 0.012), kit.emit("DashW", (0.9, 0.9, 0.85), 0.5), bevel=0)
kit.backdrop("BD4", (X, 18, 4), w=50, h=24, bottom=(0.98, 0.78, 0.55), top=(0.4, 0.55, 0.78))
bus = kit.empty("Bus", (X - 0.3, 2.7, 0))
lower = s3d.box("BusLower", (3.2, 1.2, 0.75), (0, 0, 0), s3d.mat("BusRed", (0.72, 0.16, 0.06), rough=0.4), bevel=0.12)
upper = s3d.box("BusUpper", (3.2, 1.2, 0.7), (0, 0, 0), s3d.mat("BusCream", (0.93, 0.86, 0.7), rough=0.4), bevel=0.15)
glass = s3d.mat("BusGlass", (0.05, 0.07, 0.09), rough=0.1)
parts = [(lower, (0, 0, 0.62)), (upper, (0, 0, 1.3))]
for k in range(4):
    parts.append((s3d.box(f"Win{k}", (0.55, 0.02, 0.42), (0, 0, 0), glass, bevel=0.03), (-1.05 + k * 0.62, -0.605, 1.36)))
parts.append((s3d.box("Door", (0.5, 0.02, 1.15), (0, 0, 0), glass, bevel=0.02), (1.25, -0.605, 1.0)))
tire = s3d.mat("Tire", (0.03, 0.03, 0.03), rough=0.8)
for sx in (-1.0, 1.0):
    for sy in (-0.55, 0.55):
        parts.append((s3d.cylinder("Wheel", 0.3, 0.2, (0, 0, 0), rot=(math.pi / 2, 0, 0), mat=tire, verts=24), (sx, sy, 0.3)))
for p, o in parts:
    p.parent = bus
    p.location = o
f_stop = W(4, "stopped")
kit.key_loc(bus, B[4]["fs"], (X - 4.5, 2.7, 0))
kit.key_loc(bus, f_stop + 8, (X - 0.3, 2.7, 0))
s3d.marker("thud", f_stop + 6, prompt="old bus brakes squeal and stop")
rider = human.Human("Rider", loc=(X + 0.95, 1.9, 0.0), facing=0, outfit=ORANGE_SUIT, seed=0, scale=0.85)
f_step = W(4, "stepped")
rider.hide_until(f_step)
rider.place(f_step, (X + 0.95, 1.85, 0.0), 0)
rider.walk(f_step + 2, W(4, "wheel", 4), to=(X - 1.3, 1.8), face_end=180)
rider.pose_at(W(4, "wheel", 6), "stand")
rider.hold(W(4, "wheel", 6), B[5]["fs"])
s3d.tag("a tradition since 1961", (X - 0.6, 1.6, 2.3), W(4, "Cosmonauts"), hold=60, size=0.1)
kit.light("Sun4", "AREA", (X + 5, -2, 6), 1500, (1, 0.85, 0.65), size=5, target=(X, 2.6, 0.5))

# ================================================================ 5 — #3 "Let's go!" launch
X = 500
kit.floor("Steppe5", (X, 8, 0), (60, 40), s3d.mat("Steppe", (0.55, 0.45, 0.28)))
kit.backdrop("BD5", (X, 30, 20), w=90, h=80, bottom=(0.98, 0.66, 0.4), top=(0.22, 0.32, 0.6))
rocket = kit.empty("Rocket", (X, 4, 0.6))
white_r = s3d.mat("RocketWhite", (0.86, 0.87, 0.85), rough=0.45)
band = s3d.mat("RocketBand", (0.25, 0.27, 0.28), rough=0.5)
core = kit.lathe("Core", [(0.28, 0), (0.28, 0.2), (0.34, 2.6), (0.34, 4.6), (0.3, 5.0), (0.3, 5.6), (0.36, 5.7), (0.36, 6.5), (0.2, 7.2), (0.0, 7.5)], (0, 0, 0), white_r, seg=32)
rk_parts = [core]
for k in range(4):
    a = k * math.tau / 4 + math.pi / 4
    bst = kit.lathe(f"Booster{k}", [(0.3, 0), (0.33, 0.3), (0.2, 2.4), (0.05, 3.3), (0.0, 3.35)], (0, 0, 0), white_r, seg=24)
    bst.location = (0.5 * math.cos(a), 0.5 * math.sin(a), 0)
    bst.rotation_euler = (-0.06 * math.sin(a), 0.06 * math.cos(a), 0)
    rk_parts.append(bst)
for z in (4.6, 5.65):
    rk_parts.append(kit.torus("Band", (0, 0, z), 0.34, 0.03, mat=band))
fl_mat = kit.emit("Flame", (1.0, 0.6, 0.2), 8.0)
flames = []
for k in range(5):
    if k < 4:
        a = k * math.tau / 4 + math.pi / 4
        pos = (0.5 * math.cos(a), 0.5 * math.sin(a), -0.6)
    else:
        pos = (0, 0, -0.6)
    fl = kit.cone(f"Flame{k}", pos, 0.24, 0.02, 1.2, fl_mat, rot=(math.pi, 0, 0))
    flames.append(fl)
    rk_parts.append(fl)
for p in rk_parts:
    p.parent = rocket
f_go = W(5, '"Let')
for fl in flames:
    kit.vis(fl, f_go, pop=4, over=1.6)
s3d.marker("whoosh", f_go, prompt="rocket engines ignite and roar", seconds=4)
kit.key_loc(rocket, f_go + 8, (X, 4, 0.6))
kit.key_loc(rocket, f_go + 40, (X, 4, 1.6))
kit.key_loc(rocket, B[6]["fs"], (X, 4, 6.5))
s3d.fcurves(rocket)[0].keyframe_points[0].interpolation = "QUAD"
s3d.box("Pad", (3.0, 3.0, 0.6), (X, 4, 0.3), s3d.mat("PadConcrete", (0.4, 0.39, 0.37), rough=0.9))
for k in range(4):
    a = k * math.tau / 4
    arm = s3d.box(f"Arm{k}", (0.15, 0.15, 2.6), (X + 1.4 * math.cos(a), 4 + 1.4 * math.sin(a), 1.6), s3d.mat("Truss", (0.55, 0.15, 0.08), rough=0.6))
    arm.rotation_euler = (0.35 * math.sin(a), -0.35 * math.cos(a), 0)
smoke5 = s3d.mat("Smoke5", (0.8, 0.78, 0.74), rough=1.0)
rs = random.Random(9)
for k in range(16):
    a = rs.uniform(0, math.tau)
    p = kit.sphere(f"Cloud5_{k}", (X + 1.4 * math.cos(a), 4 + 1.0 * math.sin(a), 0.5), 0.5, smoke5, seg=16)
    f = f_go + 6 + k * 2
    kit.key_scale(p, 1, 0.0)
    kit.key_scale(p, f, 0.2)
    kit.key_scale(p, f + 50, rs.uniform(1.6, 2.6))
    kit.key_loc(p, f, (X + 1.2 * math.cos(a), 4 + 0.8 * math.sin(a), 0.5))
    kit.key_loc(p, f + 50, (X + 3.2 * math.cos(a), 4 + 2.0 * math.sin(a), 0.9))
glow = kit.light("FlameLight", "POINT", (X, 3.2, 0.6), 0, (1, 0.6, 0.25), cutoff=30)
glow.data.keyframe_insert("energy", frame=f_go - 1)
glow.data.energy = 4000
glow.data.keyframe_insert("energy", frame=f_go + 6)
min108 = kit.hud_text(hud, "Min108", "108 MIN", (0, 0.55, 0), 0.26, kit.emit("Min108m", CREAM, 2.4))
kit.vis(min108, W(5, "108"), B[6]["fs"], pop=8)
s3d.tag("12 April 1961", (X - 1.6, 2.6, 1.9), W(5, "1961"), hold=60, size=0.14)
kit.light("Sun5", "AREA", (X + 8, -2, 8), 3500, (1, 0.82, 0.6), size=6, target=(X, 4, 3))

# ================================================================ 6 — #2 two parachutes (glitch in post)
X = 600
kit.backdrop("Sky6", (X, 25, 2), w=60, h=40, bottom=(0.62, 0.78, 0.95), top=(0.12, 0.3, 0.66))
cloud = s3d.mat("Cloud", (0.97, 0.97, 0.98), rough=1.0)
rc = random.Random(11)
f6a, f6b = B[6]["fs"], B[7]["fs"]
for k in range(9):
    cx, cy, cz = X + rc.uniform(-4, 4), rc.uniform(8, 16), rc.uniform(-5, 2)
    grp = [kit.sphere(f"Cl6_{k}_{j}", (cx + rc.uniform(-0.9, 0.9), cy, cz + rc.uniform(-0.2, 0.3)), rc.uniform(0.5, 1.0), cloud, seg=16, scale=(1.4, 1, 0.7))
           for j in range(5)]
    root = kit.empty(f"CloudG{k}", (0, 0, 0))
    for g in grp:
        g.parent = root
    kit.key_loc(root, f6a, (0, 0, 0))
    kit.key_loc(root, f6b, (0, 0, 3.5))
    kit.linear(root)
orange = s3d.mat("ChuteOrange", (0.95, 0.4, 0.08), rough=0.7)
whitec = s3d.mat("ChuteWhite", (0.95, 0.94, 0.9), rough=0.7)
line_m = s3d.mat("Line", (0.9, 0.9, 0.9), rough=0.6)
cap6 = kit.empty("CapsuleRig", (X + 0.85, 4.5, 1.2))
ball6 = kit.sphere("Capsule6", (0, 0, 0), 0.5, DARK_HULL)
big, rim_r, rim_z = canopy("BigChute", (0, 0, 2.3), 1.6, orange)
for p in [ball6, big] + lines("BigLine", (0, 0, 2.3), rim_r, rim_z, (0, 0, 0.45), line_m):
    p.parent = cap6
ball6.location = (0, 0, 0)
big.location = (0, 0, 2.3)
kit.key_loc(cap6, f6a, (X + 0.85, 4.5, 1.6))
kit.key_loc(cap6, f6b, (X + 0.85, 4.5, 0.6))
pilot = human.Human("Pilot", loc=(X + 0.6, 4.4, 1.0), facing=10, outfit=ORANGE_SUIT, seed=0, scale=0.55)
f_ej = W(6, "ejected")
pilot.hide_until(f_ej)
pilot.place(f_ej, (X + 0.7, 4.3, 1.4), 10)
pilot.place(f_ej + 10, (X - 0.7, 3.6, 2.0), 10)
pilot.place(f6b, (X - 0.75, 3.6, 0.2), 25)
pilot.pose_at(f_ej, "cheer")
pilot.hold(f_ej, f6b)
s3d.marker("whoosh", f_ej, prompt="ejection seat bang and rush of wind")
small, srim, sz = canopy("SmallChute", (0, 0, 0), 0.75, whitec)
srig = kit.empty("SmallRig", (X - 0.7, 3.6, 3.1))
small.parent = srig
small.location = (0, 0, 0)
for ln in lines("SmallLine", (0, 0, 0), srim, sz, (0, 0, -1.05), line_m, n=6):
    ln.parent = srig
kit.vis(srig, f_ej + 12, pop=8, over=1.3)
kit.key_loc(srig, f_ej + 12, (X - 0.7, 3.6, 3.1))
kit.key_loc(srig, f6b, (X - 0.75, 3.6, 1.3))
secret = kit.hud_text(hud, "Secret", "TOP SECRET", (0, 0.6, 0.02), 0.2, kit.emit("Stamp", (0.9, 0.08, 0.05), 3.0))
secret.rotation_euler = (0, 0, 0.12)
kit.vis(secret, W(6, "secret"), W(6, "capsule", 10), pop=6, over=1.5)
s3d.marker("thud", W(6, "secret"), prompt="rubber stamp slammed on paper")
s3d.tag("7 km", (X - 1.2, 3.0, 2.6), W(6, "seven"), hold=50, size=0.14)
kit.light("Sun6", "AREA", (X - 5, -2, 7), 2500, (1, 0.95, 0.88), size=5, target=(X, 4, 1.5))
kit.light("Fill6", "AREA", (X + 4, -1, 1), 200, (0.7, 0.8, 1.0), size=4, target=(X, 4, 1.5))

# ================================================================ 7 — #1 the field: a woman, a girl, a man in orange
X = 700
field = s3d.mat("Field", (0.32, 0.4, 0.12), rough=0.9, noise=0.5, noise_scale=6)
kit.terrain("Field7", (X, 8, 0), (40, 30), (60, 45), lambda x, y: 0.15 * math.sin(x * 0.4 + 0.5) * math.sin(y * 0.3) * min(1, max(0, (y + 4) / 6)), field)
kit.backdrop("Sky7", (X, 22, 4), w=50, h=24, bottom=(0.95, 0.86, 0.68), top=(0.42, 0.58, 0.82))
for k in range(9):
    s3d.tree(X - 8 + k * 2.1, 14 + (k % 3), h=4.5 + (k % 2), r=1.6, seed=k)
flat, _, _ = canopy("GroundChute", (X + 1.9, 5.2, 0.02), 1.0, orange, depth=1.4)
flat.scale = (1.6, 1.0, 0.18)
woman = human.Human("Anna", loc=(X - 1.0, 2.9, 0.0), facing=45, outfit=dict(shirt=(0.55, 0.22, 0.28), pants=(0.16, 0.15, 0.24), shoes=(0.2, 0.13, 0.08), hat=None), seed=2)
girl = human.Human("Rita", loc=(X - 0.5, 2.3, 0.0), facing=40, outfit=dict(shirt=(0.9, 0.62, 0.3), pants=(0.25, 0.3, 0.45), shoes=(0.2, 0.13, 0.08), hat=None), seed=3, scale=0.62)
man = human.Human("Cosmonaut", loc=(X + 1.4, 4.2, 0.0), facing=-130, outfit=ORANGE_SUIT, seed=0)
f7a = B[7]["fs"]
man.walk(f7a + 4, W(7, "orange", 6), to=(X + 0.5, 3.2), face_end=-120)
man.act(W(7, "orange", 8), "wave", cycles=2, period=16)
for h in (woman, girl):
    h.act(W(7, "frightened", -2), "scared", cycles=3, period=12)
kit.light("Sun7", "AREA", (X - 4, -2, 6), 1600, (1, 0.9, 0.72), size=5, target=(X, 3, 0.5))
kit.light("Fill7", "AREA", (X + 3, -2, 2), 150, (0.8, 0.85, 1.0), size=3, target=(X, 3, 0.8))

# ================================================================ HUD: title, fact numbers, closing question
cream_e = kit.emit("HudCream", CREAM, 2.2)
plate_m = kit.emit("HudPlate", (0.35, 0.03, 0.02), 1.0)
t_plate = s3d.box("TitlePlate", (1.55, 0.5, 0.01), (0, 0, 0), plate_m, bevel=0.004)
t_plate.parent = hud
t_plate.location = (0, 1.2, -0.01)
kit.vis(t_plate, 2, B[1]["fs"], pop=0)
kit.vis(kit.hud_text(hud, "Title1", "7 FACTS", (0, 1.3, 0), 0.2, cream_e), 2, B[1]["fs"], pop=0)
kit.vis(kit.hud_text(hud, "Title2", "NOT IN TEXTBOOKS", (0, 1.09, 0), 0.095, kit.emit("HudYellow", (1, 0.8, 0.3), 2.2)), 2, B[1]["fs"], pop=0)
b_plate = s3d.box("BadgePlate", (0.42, 0.17, 0.01), (0, 0, 0), plate_m, bevel=0.004)
b_plate.parent = hud
b_plate.location = (0, 1.28, -0.01)
kit.vis(b_plate, B[1]["fs"], B[8]["fs"], pop=0)
for i in range(1, 8):
    kit.vis(kit.hud_text(hud, f"Fact{i}", f"#{8 - i}", (0, 1.28, 0), 0.13, cream_e), B[i]["fs"], B[i + 1]["fs"], pop=5)
q_plate = s3d.box("AskPlate", (1.7, 0.42, 0.01), (0, 0, 0), plate_m, bevel=0.004)
q_plate.parent = hud
q_plate.location = (0, 1.2, -0.01)
kit.vis(q_plate, B[8]["fs"], pop=6)
kit.vis(kit.hud_text(hud, "Ask1", "WHAT DID YOUR FAMILY", (0, 1.28, 0), 0.105, cream_e), B[8]["fs"], pop=6)
kit.vis(kit.hud_text(hud, "Ask2", "TELL YOU ABOUT GAGARIN?", (0, 1.12, 0), 0.105, cream_e), B[8]["fs"], pop=6)

# ================================================================ camera
shots = [(1, B[1]["fs"], (0, -2.6, 1.3), (0, 3, 0.9), (0.1, -1.9, 1.25), (0.1, 3, 0.95)),
         (B[1]["fs"], B[2]["fs"], (100, -3.0, 1.3), (100.1, 3, 0.6), (100, -2.2, 1.2), (100.1, 3, 0.6)),
         (B[2]["fs"], f_cut2, (199.75, -2.3, 1.15), (199.75, 2.6, 0.95), (199.7, -1.8, 1.15), (199.7, 2.6, 0.95)),
         (f_cut2, B[3]["fs"], (200.55, -1.9, 1.0), (200.55, 3.0, 0.8), (200.55, -1.5, 0.98), (200.55, 3.0, 0.8)),
         (B[3]["fs"], B[4]["fs"], (300, -3.2, 2.2), (300, 3.2, 0.8), (300, -2.6, 2.0), (300, 3.2, 0.8)),
         (B[4]["fs"], B[5]["fs"], (400, -4.6, 1.3), (399.7, 2.4, 0.9), (399.4, -3.4, 1.1), (399.1, 2.4, 0.7)),
         (B[5]["fs"], B[6]["fs"], (500, -9.5, 2.5), (500, 4, 3.6), (500, -8.0, 3.0), (500, 4, 6.5)),
         (B[6]["fs"], B[7]["fs"], (600, -5.0, 2.0), (600, 4, 2.0), (600, -4.2, 1.8), (600, 4, 1.8)),
         (B[7]["fs"], B[8]["fs"], (700, -3.6, 1.3), (700.2, 3.2, 0.9), (700.1, -2.8, 1.25), (700.2, 3.2, 0.9)),
         (B[8]["fs"], END + 1, (0.6, -3.2, 1.0), (0.4, 3, 1.4), (0.8, -3.8, 1.1), (0.5, 3, 1.5))]
for f0, f1, e0, l0, e1, l1 in shots:
    cam.shot(f0, f1, e0, l0, e1, l1)
cam.finish()

# ================================================================ output
if MODE == "preview":
    os.makedirs(os.path.join(WORK, "preview"), exist_ok=True)
    frames = sorted({b["fs"] + 6 for b in B} | {b["fe"] - 4 for b in B} | {f_cut2 + 6, f_ej + 16})
    for f in frames:
        s3d.preview_still(os.path.join(WORK, "preview", f"f{f:04d}.png"), frame=f, scale=30, samples=4)
    s3d.qa_gate(abort=False)
elif MODE == "draft":
    sc = bpy.context.scene
    sc.render.engine = "BLENDER_WORKBENCH"
    sc.display.shading.color_type = "MATERIAL"
    s3d.render_mp4(os.path.join(WORK, "draft.mp4"), scale=30)
else:
    kit.render_frames(WORK)
