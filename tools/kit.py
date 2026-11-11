"""Blender helpers for fact-countdown shorts, layered on the kylo-3d-shorts plugin's s3d/human libraries.

Zones (one per fact) sit 100 m apart on X; a single camera hard-cuts between them with a slow push-in,
and HUD elements (score, fact number) ride on the camera so they stay put across cuts.
"""
import math
import os
import random
import sys

import bmesh
import bpy
from mathutils import Vector

HERE = os.path.dirname(os.path.abspath(__file__))
_font = None


def find_scripts():
    import glob
    c = os.environ.get("KYLO_SCRIPTS", "")
    if c and os.path.exists(os.path.join(c, "s3d.py")):
        return c
    hits = sorted(glob.glob(os.path.expanduser("~/.claude/plugins/cache/*/kylo-3d-shorts/*/skills/3d-short/scripts")))
    if hits:
        return hits[-1]
    raise SystemExit("set KYLO_SCRIPTS=<plugin>/skills/3d-short/scripts")


sys.path.insert(0, find_scripts())
import s3d  # noqa: E402


# ---------------------------------------------------------------- scene
def setup(beats, fps=24, hdri="studio_small_09", tail=14, cam_bg=(0.02, 0.02, 0.03), sun=0.8):
    s3d.new_short(fps=fps, sky=hdri)
    sc = bpy.context.scene
    sc.frame_end = beats[-1]["fe"] + tail
    sc.render.use_motion_blur = False
    ee = sc.eevee
    ee.taa_render_samples = int(os.environ.get("S3D_SAMPLES", "4"))
    for a, v in (("use_raytracing", False), ("use_fast_gi", False)):
        if hasattr(ee, a):
            setattr(ee, a, v)
    for o in sc.objects:
        if o.type == "LIGHT" and o.data.type == "SUN":
            o.data.energy = sun
            if os.environ.get("S3D_FAST", "1") == "1":
                o.data.use_shadow = False   # every zone has its own shadow-casting key light
    if os.environ.get("S3D_FAST", "1") == "1":
        for a, v in (("shadow_ray_count", 1), ("shadow_step_count", 4), ("shadow_resolution_scale", 0.5)):
            if hasattr(ee, a):
                setattr(ee, a, v)
    _camera_sees(cam_bg)
    return sc


def _camera_sees(color):
    """The HDRI lights and reflects; camera rays see a plain colour (each zone brings its own backdrop)."""
    nt = bpy.context.scene.world.node_tree
    out = next(n for n in nt.nodes if n.type == "OUTPUT_WORLD")
    if not out.inputs["Surface"].links:
        return
    src = out.inputs["Surface"].links[0].from_socket
    lp = nt.nodes.new("ShaderNodeLightPath")
    bg = nt.nodes.new("ShaderNodeBackground")
    bg.inputs[0].default_value = (*color, 1)
    mix = nt.nodes.new("ShaderNodeMixShader")
    nt.links.new(lp.outputs["Is Camera Ray"], mix.inputs[0])
    nt.links.new(src, mix.inputs[1])
    nt.links.new(bg.outputs[0], mix.inputs[2])
    nt.links.new(mix.outputs[0], out.inputs["Surface"])


def link(ob):
    bpy.context.scene.collection.objects.link(ob)
    return ob


def empty(name, loc=(0, 0, 0), parent=None):
    e = link(bpy.data.objects.new(name, None))
    e.parent = parent
    e.location = loc
    return e


def mesh_obj(name, verts, faces, mat=None, smooth=False, loc=(0, 0, 0)):
    me = bpy.data.meshes.new(name)
    me.from_pydata([tuple(v) for v in verts], [], [tuple(f) for f in faces])
    me.update()
    bm = bmesh.new()
    bm.from_mesh(me)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    bm.to_mesh(me)
    bm.free()
    if smooth:
        me.shade_smooth()
    if mat:
        me.materials.append(mat)
    ob = link(bpy.data.objects.new(name, me))
    ob.location = loc
    return ob


def emit(name, color, strength=2.0):
    return s3d.mat_emit(name, color, strength)


def metal(name, color, rough=0.22):
    return s3d.mat(name, color, rough=rough, metal=1.0)


def light(name, kind, loc, energy, color=(1, 1, 1), size=1.0, target=None, cutoff=40.0, spot=0.6):
    ld = bpy.data.lights.new(name, kind)
    ld.energy = energy
    ld.color = color
    if kind == "AREA":
        ld.size = size
    elif kind == "SPOT":
        ld.spot_size = spot
        ld.spot_blend = 0.4
    if hasattr(ld, "use_custom_distance"):
        ld.use_custom_distance = True   # lights only cost inside their own zone
        ld.cutoff_distance = cutoff
    if os.environ.get("S3D_FAST", "1") == "1" and kind in ("AREA", "POINT") and energy < 200:
        ld.use_shadow = False           # fills don't need shadow maps
    ob = link(bpy.data.objects.new(name, ld))
    ob.location = loc
    if target is not None:
        ob.rotation_euler = (Vector(target) - Vector(loc)).to_track_quat("-Z", "Y").to_euler()
    return ob


def backdrop(name, center, w=40, h=26, bottom=(0.1, 0.1, 0.1), top=(0.0, 0.0, 0.0), strength=1.0):
    """Big upright plane facing the camera with a vertical emission gradient."""
    m = bpy.data.materials.new(name + "_mat")
    m.use_nodes = True
    nt = m.node_tree
    for n in list(nt.nodes):
        nt.nodes.remove(n)
    tc = nt.nodes.new("ShaderNodeTexCoord")
    sep = nt.nodes.new("ShaderNodeSeparateXYZ")
    mr = nt.nodes.new("ShaderNodeMapRange")
    mr.inputs["From Min"].default_value = -h / 2
    mr.inputs["From Max"].default_value = h / 2
    ramp = nt.nodes.new("ShaderNodeValToRGB")
    ramp.color_ramp.elements[0].color = (*bottom, 1)
    ramp.color_ramp.elements[1].color = (*top, 1)
    ramp.color_ramp.elements[0].position = 0.25
    ramp.color_ramp.elements[1].position = 0.75
    em = nt.nodes.new("ShaderNodeEmission")
    em.inputs["Strength"].default_value = strength
    out = nt.nodes.new("ShaderNodeOutputMaterial")
    nt.links.new(tc.outputs["Object"], sep.inputs[0])
    nt.links.new(sep.outputs["Z"], mr.inputs["Value"])
    nt.links.new(mr.outputs["Result"], ramp.inputs["Fac"])
    nt.links.new(ramp.outputs["Color"], em.inputs["Color"])
    nt.links.new(em.outputs[0], out.inputs["Surface"])
    x, y, z = center
    ob = mesh_obj(name, [(-w / 2, 0, -h / 2), (w / 2, 0, -h / 2), (w / 2, 0, h / 2), (-w / 2, 0, h / 2)], [(0, 1, 2, 3)], m)
    ob.location = (x, y, z)
    ob.visible_shadow = False
    return ob


def floor(name, center, size=(30, 30), mat=None):
    x, y, z = center
    sx, sy = size
    return mesh_obj(name, [(-sx / 2, -sy / 2, 0), (sx / 2, -sy / 2, 0), (sx / 2, sy / 2, 0), (-sx / 2, sy / 2, 0)],
                    [(0, 1, 2, 3)], mat, loc=(x, y, z))


def terrain(name, center, size=(40, 30), res=(90, 70), height=lambda x, y: 0.0, mat=None):
    sx, sy = size
    nx, ny = res
    verts, faces = [], []
    for j in range(ny + 1):
        for i in range(nx + 1):
            x = -sx / 2 + sx * i / nx
            y = -sy / 2 + sy * j / ny
            verts.append((x, y, height(x, y)))
    for j in range(ny):
        for i in range(nx):
            a = j * (nx + 1) + i
            faces.append((a, a + 1, a + nx + 2, a + nx + 1))
    return mesh_obj(name, verts, faces, mat, smooth=True, loc=center)


# ---------------------------------------------------------------- text
def font():
    global _font
    if _font is None:
        p = os.path.join(HERE, "fonts", "Montserrat-ExtraBold.ttf")
        _font = bpy.data.fonts.load(p) if os.path.exists(p) else False
    return _font or None


def text(name, body, loc=(0, 0, 0), size=0.3, mat=None, align="CENTER", extrude=0.0, rot=(math.pi / 2, 0, 0),
         parent=None, spacing=1.0):
    cu = bpy.data.curves.new(name, "FONT")
    cu.body = body
    cu.size = size
    cu.align_x = align
    cu.align_y = "CENTER"
    cu.extrude = extrude
    cu.space_character = spacing
    if font():
        cu.font = font()
    if mat:
        cu.materials.append(mat)
    ob = link(bpy.data.objects.new(name, cu))
    ob.parent = parent
    ob.location = loc
    ob.rotation_euler = rot
    return ob


def hud_text(hud, name, body, loc, size, mat, align="CENTER"):
    """Text in the camera's own plane (HUD children face the lens)."""
    return text(name, body, loc, size, mat, align=align, rot=(0, 0, 0), parent=hud)


# ---------------------------------------------------------------- timing / visibility
def vis(o, f0, f1=None, pop=6, over=1.25):
    """Scale 0 outside [f0, f1); pops in at f0 (pop=0: hard cut)."""
    s = tuple(o.scale)

    def k(f, v):
        o.scale = v
        o.keyframe_insert("scale", frame=max(1, f))
    if f0 > 2:
        k(1, (0, 0, 0))
        k(f0 - 1, (0, 0, 0))
    if pop:
        k(f0, tuple(x * over for x in s))
        k(f0 + pop, s)
    else:
        k(f0, s)
    if f1:
        k(f1 - 1, s)
        k(f1, (0, 0, 0))
    o.scale = s
    return o


def key_loc(o, f, loc):
    o.location = loc
    o.keyframe_insert("location", frame=f)


def key_scale(o, f, s):
    o.scale = (s, s, s) if isinstance(s, (int, float)) else s
    o.keyframe_insert("scale", frame=f)


def emit_key(mat, f, strength):
    for n in mat.node_tree.nodes:
        if "Emission Strength" in n.inputs:
            n.inputs["Emission Strength"].default_value = strength
            n.inputs["Emission Strength"].keyframe_insert("default_value", frame=f)
        elif n.type == "EMISSION":
            n.inputs["Strength"].default_value = strength
            n.inputs["Strength"].keyframe_insert("default_value", frame=f)


def linear(o):
    for fc in s3d.fcurves(o):
        for kp in fc.keyframe_points:
            kp.interpolation = "LINEAR"


def render_frames(work, scale=100):
    """Final render as a PNG sequence: resumable (existing frames are skipped) and patchable per range."""
    s3d.qa_gate()
    sc = bpy.context.scene
    sc.render.resolution_percentage = scale
    s3d.export_markers(os.path.join(work, "render.sfx.json"))
    st = sc.render.image_settings
    try:
        st.media_type = "IMAGE"
    except Exception:
        pass
    st.file_format = "PNG"
    st.color_mode = "RGB"
    st.compression = 15
    sc.render.filepath = os.path.join(os.path.abspath(work), "frames", "f")
    sc.render.use_overwrite = False
    sc.render.use_placeholder = True
    bpy.ops.render.render(animation=True)


# ---------------------------------------------------------------- camera
class Cam:
    def __init__(self, lens=35):
        cd = bpy.data.cameras.new("Cam")
        cd.lens = lens
        cd.sensor_fit = "VERTICAL"
        cd.sensor_height = 36
        cd.clip_end = 400
        self.o = link(bpy.data.objects.new("Cam", cd))
        bpy.context.scene.camera = self.o
        self._prev = None
        self.shots = []

    def _set(self, f, eye, look):
        self.o.location = eye
        e = (Vector(look) - Vector(eye)).to_track_quat("-Z", "Y").to_euler()
        if self._prev is not None:
            e.make_compatible(self._prev)
        self._prev = e.copy()
        self.o.rotation_euler = e
        self.o.keyframe_insert("location", frame=f)
        self.o.keyframe_insert("rotation_euler", frame=f)

    def shot(self, f0, f1, eye0, look0, eye1=None, look1=None):
        """Hold a framing from f0 to f1-1, drifting to eye1/look1; the next shot starts with a hard cut."""
        self._set(f0, eye0, look0)
        self._set(f1 - 1, eye1 or eye0, look1 or look0)
        self.shots.append((f0, f1, round(eye0[0] / ZONE)))

    def finish(self):
        linear(self.o)
        if os.environ.get("S3D_NOCULL") != "1":
            cull_zones(self)

    def hud(self, d=3.0):
        """Empty d metres in front of the lens; at lens 35 the frame spans x ±0.289·d, y ±0.514·d."""
        return empty("HUD", (0, 0, -d), self.o)


ZONE = 100.0


def cull_zones(cam):
    """Hide every zone the camera is not in: EEVEE otherwise updates all lights and shadow maps every frame.
    Objects that already animate hide_render themselves (hide_until, tags) are left alone."""
    bpy.context.view_layer.update()
    shots = sorted(cam.shots)
    rig = set()
    stack = [cam.o]
    while stack:
        o = stack.pop()
        rig.add(o)
        stack += list(o.children)
    n = 0
    for o in bpy.context.scene.objects:
        if o in rig or o.type in ("EMPTY", "ARMATURE", "CAMERA"):
            continue
        if any(fc.data_path == "hide_render" for fc in s3d.fcurves(o)):
            continue
        z = round(o.matrix_world.translation.x / ZONE)
        state = None
        for f0, f1, zone in shots:
            hide = zone != z
            if hide != state:
                o.hide_render = hide
                o.keyframe_insert("hide_render", frame=1 if state is None else f0)
                state = hide
        n += 1
    print(f"kit: zone culling on {n} objects over {len(shots)} shots")


# ---------------------------------------------------------------- props
def lathe(name, prof, loc=(0, 0, 0), mat=None, seg=48, cap=True):
    n = len(prof)
    verts, faces = [], []
    for j in range(seg):
        a = 2 * math.pi * j / seg
        verts += [(r * math.cos(a), r * math.sin(a), z) for r, z in prof]
    for j in range(seg):
        jn = (j + 1) % seg
        faces += [(j * n + i, jn * n + i, jn * n + i + 1, j * n + i + 1) for i in range(n - 1)]
    if cap and prof[0][0] > 0:
        c = len(verts)
        verts.append((0, 0, prof[0][1]))
        faces += [(((j + 1) % seg) * n, j * n, c) for j in range(seg)]
    return mesh_obj(name, verts, faces, mat, smooth=True, loc=loc)


def torus(name, loc, major, minor, rot=(0, 0, 0), mat=None):
    bpy.ops.mesh.primitive_torus_add(major_radius=major, minor_radius=minor, location=loc, rotation=rot,
                                     major_segments=32, minor_segments=12)
    o = bpy.context.object
    o.name = name
    o.data.shade_smooth()
    if mat:
        o.data.materials.append(mat)
    return o


def sphere(name, loc, r, mat=None, seg=32, scale=(1, 1, 1)):
    bpy.ops.mesh.primitive_uv_sphere_add(radius=r, location=loc, segments=seg, ring_count=seg // 2)
    o = bpy.context.object
    o.name = name
    o.scale = scale
    o.data.shade_smooth()
    if mat:
        o.data.materials.append(mat)
    return o


def cone(name, loc, r1, r2, depth, mat=None, rot=(0, 0, 0), verts=32):
    bpy.ops.mesh.primitive_cone_add(radius1=r1, radius2=r2, depth=depth, location=loc, rotation=rot, vertices=verts)
    o = bpy.context.object
    o.name = name
    if mat:
        o.data.materials.append(mat)
    return o


def football(name, r=0.11, loc=(0, 0, 0), white=None, black=None):
    """Truncated icosahedron (12 pentagons, 20 hexagons) smoothed onto a sphere."""
    phi = (1 + 5 ** 0.5) / 2
    pts = set()
    for b in ((0, 1, 3 * phi), (1, 2 + phi, 2 * phi), (phi, 2, 2 * phi + 1)):
        for p in (b, (b[1], b[2], b[0]), (b[2], b[0], b[1])):
            for sx in (1, -1):
                for sy in (1, -1):
                    for sz in (1, -1):
                        pts.add((round(p[0] * sx, 6), round(p[1] * sy, 6), round(p[2] * sz, 6)))
    bm = bmesh.new()
    for p in pts:
        bm.verts.new(Vector(p).normalized() * r)
    bmesh.ops.convex_hull(bm, input=list(bm.verts))
    bmesh.ops.dissolve_limit(bm, angle_limit=math.radians(2), verts=list(bm.verts), edges=list(bm.edges))
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    me.materials.append(white or s3d.mat("BallWhite", (0.92, 0.92, 0.9), rough=0.35))
    me.materials.append(black or s3d.mat("BallBlack", (0.03, 0.03, 0.035), rough=0.35))
    for p in me.polygons:
        p.material_index = 1 if len(p.vertices) == 5 else 0
    me.shade_smooth()
    ob = link(bpy.data.objects.new(name, me))
    ob.location = loc
    sub = ob.modifiers.new("Sub", "SUBSURF")
    sub.levels = sub.render_levels = 2
    cast = ob.modifiers.new("Round", "CAST")
    cast.factor = 1.0
    return ob


def cup(name, loc, h=0.34, mat=None):
    """Big-eared European cup: lathe body + two loop handles."""
    p = [(0.075, 0), (0.07, 0.03), (0.03, 0.05), (0.022, 0.13), (0.05, 0.16), (0.10, 0.24), (0.12, 0.30), (0.115, 0.34), (0.105, 0.335)]
    s = h / 0.34
    body = lathe(name, [(r * s, z * s) for r, z in p], loc, mat)
    for side in (-1, 1):
        hd = torus(name + "_ear", (loc[0] + side * 0.12 * s, loc[1], loc[2] + 0.23 * s), 0.07 * s, 0.012 * s,
                   rot=(math.pi / 2, 0, 0), mat=mat)
        hd.scale = (0.8, 1, 1.25)
        hd.parent = body
        hd.location = (side * 0.12 * s, 0, 0.23 * s)
    return body


def golden_ball(name, loc, r=0.12, gold=None, gold2=None):
    g = gold or metal("Gold", (1.0, 0.72, 0.28))
    g2 = gold2 or metal("Gold2", (0.75, 0.48, 0.12), rough=0.35)
    base = lathe(name + "_base", [(0.07 * r / 0.12, 0), (0.07 * r / 0.12, 0.05 * r / 0.12), (0.03 * r / 0.12, 0.08 * r / 0.12)], loc, g2)
    ball = football(name, r, (0, 0, 0.08 * r / 0.12 + r * 0.95), g, g2)
    ball.parent = base
    return base


def pawn(name, loc, mat, h=1.7):
    """Restroom-sign person: lathe body + head, for crowds and candidate line-ups."""
    s = h / 1.7
    prof = [(0.12, 0), (0.17, 0.02), (0.15, 0.6), (0.17, 0.95), (0.22, 1.25), (0.21, 1.36), (0.12, 1.43), (0.05, 1.46)]
    body = lathe(name, [(r * s, z * s) for r, z in prof], loc, mat, seg=24)
    hd = sphere(name + "_head", (0, 0, 1.6 * s), 0.12 * s, mat, seg=20)
    hd.parent = body
    hd.location = (0, 0, 1.6 * s)
    return body


def silhouette(h, mat):
    for p in h.parts:
        for sl in p.material_slots:
            sl.material = mat
    return h


def flakes(name, center, area=(8, 5), height=14, n=500, size=0.03, mats=(), f0=1, f1=100, fall=6.0, seed=1, spin=0.0):
    """Column of small quads that drifts down over [f0, f1] (snow, confetti, stars with fall=0)."""
    rng = random.Random(seed)
    verts, faces, idx = [], [], []
    for k in range(n):
        c = Vector((rng.uniform(-area[0] / 2, area[0] / 2), rng.uniform(-area[1] / 2, area[1] / 2), rng.uniform(0, height)))
        a, b = rng.uniform(0, math.tau), rng.uniform(0, math.tau)
        u = Vector((math.cos(a), math.sin(a) * math.cos(b), math.sin(b))) * size
        v = u.cross(Vector((rng.random(), rng.random(), rng.random()))).normalized() * size
        base = len(verts)
        verts += [c - u - v, c + u - v, c + u + v, c - u + v]
        faces.append((base, base + 1, base + 2, base + 3))
        idx.append(rng.randrange(max(1, len(mats))))
    me = bpy.data.meshes.new(name)
    me.from_pydata([tuple(p) for p in verts], [], faces)
    for m in mats:
        me.materials.append(m)
    for p, i in zip(me.polygons, idx):
        p.material_index = i
    ob = link(bpy.data.objects.new(name, me))
    ob.location = center
    ob.visible_shadow = False
    if fall:
        key_loc(ob, f0, center)
        key_loc(ob, f1, (center[0], center[1], center[2] - fall))
        if spin:
            ob.rotation_euler = (0, 0, 0)
            ob.keyframe_insert("rotation_euler", frame=f0)
            ob.rotation_euler = (0, 0, spin)
            ob.keyframe_insert("rotation_euler", frame=f1)
        linear(ob)
    return ob


def burst(name, center, f, color, n=70, radius=2.2, dur=22, seed=0):
    """Firework: points fly out from the centre and fade."""
    rng = random.Random(seed)
    m = emit(name + "_m", color, 0.0)
    verts, faces = [], []
    for k in range(n):
        d = Vector((rng.gauss(0, 1), rng.gauss(0, 1), rng.gauss(0, 1))).normalized() * radius * rng.uniform(0.85, 1.0)
        s = 0.035
        b = len(verts)
        verts += [d + Vector((-s, 0, -s)), d + Vector((s, 0, -s)), d + Vector((s, 0, s)), d + Vector((-s, 0, s))]
        faces.append((b, b + 1, b + 2, b + 3))
    me = bpy.data.meshes.new(name)
    me.from_pydata([tuple(p) for p in verts], [], faces)
    me.materials.append(m)
    ob = link(bpy.data.objects.new(name, me))
    ob.location = center
    ob.visible_shadow = False
    key_scale(ob, 1, 0.0)
    key_scale(ob, f - 1, 0.0)
    key_scale(ob, f, 0.08)
    key_scale(ob, f + dur, 1.0)
    key_scale(ob, f + dur + 1, 0.0)
    emit_key(m, f - 1, 0.0)
    emit_key(m, f, 6.0)
    emit_key(m, f + dur, 0.0)
    s3d.marker("pop", f, prompt="distant firework burst crackle")
    return ob


def plane_model(name, loc, body=None, stripe=None):
    """Small airliner pointing +X."""
    bm = body or s3d.mat("PlaneBody", (0.92, 0.92, 0.94), rough=0.3)
    st = stripe or s3d.mat("PlaneStripe", (0.75, 0.08, 0.06), rough=0.4)
    fus = lathe(name, [(0.0, -0.9), (0.08, -0.82), (0.13, -0.6), (0.14, 0.4), (0.10, 0.75), (0.02, 0.95), (0.0, 0.96)], loc, bm, seg=24)
    fus.rotation_euler = (0, math.pi / 2, 0)
    parts = [s3d.box(name + "_wing", (0.5, 1.7, 0.03), (0, 0, 0), bm, bevel=0.01),
             s3d.box(name + "_tail", (0.25, 0.6, 0.02), (0, 0, 0), bm, bevel=0.01),
             s3d.box(name + "_fin", (0.28, 0.02, 0.32), (0, 0, 0), st, bevel=0.01)]
    offs = [(0.05, 0, 0), (-0.78, 0, 0), (-0.78, 0, 0.16)]
    root = empty(name + "_root", loc)
    fus.parent = root
    fus.location = (0, 0, 0)
    for p, o in zip(parts, offs):
        p.parent = root
        p.location = o
    return root


def goal(name, loc, w=2.4, h=1.0, d=0.8, mat=None):
    m = mat or s3d.mat("GoalWhite", (0.95, 0.95, 0.95), rough=0.3)
    x, y, z = loc
    parts = [s3d.cylinder(name + "_pl", 0.04, h, (x - w / 2, y, z + h / 2), mat=m, verts=12),
             s3d.cylinder(name + "_pr", 0.04, h, (x + w / 2, y, z + h / 2), mat=m, verts=12),
             s3d.cylinder(name + "_bar", 0.04, w + 0.08, (x, y, z + h), rot=(0, math.pi / 2, 0), mat=m, verts=12)]
    net = s3d.mat("Net", (0.85, 0.85, 0.85), rough=0.6)
    back = mesh_obj(name + "_net", [(-w / 2, 0, h), (w / 2, 0, h), (w / 2, d, 0), (-w / 2, d, 0)], [(0, 1, 2, 3)], net, loc=(x, y, z))
    sub = back.modifiers.new("Sub", "SUBSURF")
    sub.subdivision_type = "SIMPLE"
    sub.levels = sub.render_levels = 4
    wf = back.modifiers.new("Wire", "WIREFRAME")
    wf.thickness = 0.008
    return parts + [back]
