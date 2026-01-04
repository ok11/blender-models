"""
Grohe adapter for Blender 4.x
"""

import bpy
import bmesh
import math

# ============================================
# Modeling parameters (mm)
# ============================================

# Inner teeth
INNER_D_MIN = 7.0             # Diameter minimum
INNER_D_MAX = 7.5             # Diameter maximumn
INNER_TEETH = 20              # Number of teeth

INNER_HOLE_D = 5.0            # Diameter bottom hole

# Outer teeth (handle)  
OUTER_D_MIN = 11.0            # Diameter minimum
OUTER_D_MAX = 11.8            # Diameter maximum
OUTER_TEETH = 20              # Number of teeth
OUTER_HEIGHT = 14.0           # Outer height

# Top side slots
TOP_SLOT_COUNT = 4            # Number of slots
TOP_SLOT_WIDTH = 1.5          # Slot width
TOP_SLOT_DEPTH = 10.0         # Slot depth

# Flange (handle mounting)
FLANGE_D = 8.9                # Diameter of the flange
FLANGE_H = 2.8                # Height of the flange (overall)
FLANGE_CHAMFER_BOT = 1.7      # Bottom chamfer height (45°)
FLANGE_CHAMFER_TOP = 0.7      # Top chamfer height (45°)

# Body
BODY_D = 8.0                  # Body cylinder diameter

# Taper cone
TAPER_H = 2.0                 # Cone height

# Bottom slots  
BOT_SLOT_COUNT = 4            # Number of slots
BOT_SLOT_WIDTH = 1.8          # Slot width
BOT_SLOT_HEIGHT = 4.0         # Slot height
BOT_SLOT_OFFSET = 45          # Offset relative to the top slots (degrees)

# General
TOTAL_H = 21.0                # Total height

# Tolerance
TOL_INNER = 0.15              # Inner diameter tolerance

# ============================================
MM = 1  # Unit conversion if needed

# ============================================
# Utils
# ============================================

def clear_mesh_objects():
    bpy.ops.object.select_all(action='DESELECT')
    for obj in bpy.data.objects:
        if obj.type == 'MESH':
            obj.select_set(True)
    bpy.ops.object.delete()

def apply_all_modifiers(obj):
    """ Apply all modifiers """
    bpy.context.view_layer.objects.active = obj
    for mod in obj.modifiers[:]:
        try:
            bpy.ops.object.modifier_apply(modifier=mod.name)
        except:
            pass

def boolean_difference(target, cutter, apply=True):
    """ Subtract cutter from the target """
    mod = target.modifiers.new(name="Bool", type='BOOLEAN')
    mod.operation = 'DIFFERENCE'
    mod.object = cutter
    mod.solver = 'EXACT'  # Can also be FAST
    
    if apply:
        bpy.context.view_layer.objects.active = target
        try:
            bpy.ops.object.modifier_apply(modifier=mod.name)
        except Exception as e:
            print(f"Boolean failed: {e}")
            # Try the FAST solver
            mod.solver = 'FAST'
            try:
                bpy.ops.object.modifier_apply(modifier=mod.name)
            except:
                pass

def boolean_union(target, addition, apply=True):
    """ Add addition to the target"""
    mod = target.modifiers.new(name="Bool", type='BOOLEAN')
    mod.operation = 'UNION'
    mod.object = addition
    mod.solver = 'EXACT'
    
    if apply:
        bpy.context.view_layer.objects.active = target
        try:
            bpy.ops.object.modifier_apply(modifier=mod.name)
        except:
            mod.solver = 'FAST'
            try:
                bpy.ops.object.modifier_apply(modifier=mod.name)
            except:
                pass

def delete_object(obj):
    bpy.data.objects.remove(obj, do_unlink=True)

# ============================================
# Splined cylinder
# ============================================

def create_splined_cylinder(name, d_min, d_max, teeth, height, z_offset=0):
    """ Create a splined cylinder """
    r_min = d_min / 2 * MM
    r_max = d_max / 2 * MM
    h = height * MM
    z = z_offset * MM
    
    mesh = bpy.data.meshes.new(name)
    bm = bmesh.new()
    
    # Create vertices for the teeth
    num_verts = teeth * 2
    
    verts_bot = []
    verts_top = []
    
    for i in range(num_verts):
        angle = (i / num_verts) * 2 * math.pi
        # Even = tips of the teeth, odd = roots
        r = r_max if (i % 2 == 0) else r_min
        
        x = r * math.cos(angle)
        y = r * math.sin(angle)
        
        verts_bot.append(bm.verts.new((x, y, z)))
        verts_top.append(bm.verts.new((x, y, z + h)))
    
    bm.verts.ensure_lookup_table()
    
    # Side surfaces
    for i in range(num_verts):
        ni = (i + 1) % num_verts
        bm.faces.new([verts_bot[i], verts_bot[ni], verts_top[ni], verts_top[i]])
    
    # End faces
    bm.faces.new(verts_bot)
    bm.faces.new(verts_top[::-1])
    
    bm.to_mesh(mesh)
    bm.free()
    
    obj = bpy.data.objects.new(name, mesh)
    bpy.context.collection.objects.link(obj)
    return obj

def create_cylinder(name, diameter, height, z_offset=0, segments=64):
    """ A simple cylinder """
    bpy.ops.mesh.primitive_cylinder_add(
        radius=diameter/2 * MM,
        depth=height * MM,
        location=(0, 0, (z_offset + height/2) * MM),
        vertices=segments
    )
    obj = bpy.context.active_object
    obj.name = name
    return obj

def create_cone(name, d_bottom, d_top, height, z_offset=0, segments=64):
    """ A cut cone """
    bpy.ops.mesh.primitive_cone_add(
        radius1=d_bottom/2 * MM,
        radius2=d_top/2 * MM,
        depth=height * MM,
        location=(0, 0, (z_offset + height/2) * MM),
        vertices=segments
    )
    obj = bpy.context.active_object
    obj.name = name
    return obj

def create_slot_cutter(name, width, height, z_start, angle_deg, radial_length=20):
    """ A slot cutter """
    w = width * MM
    h = height * MM
    z = z_start * MM
    length = radial_length * MM
    
    bpy.ops.mesh.primitive_cube_add(
        size=1,
        location=(length/2, 0, z + h/2)
    )
    obj = bpy.context.active_object
    obj.name = name
    obj.scale = (length, w/2, h)
    bpy.ops.object.transform_apply(scale=True)
    
    # Rotate it
    obj.rotation_euler[2] = math.radians(angle_deg)
    bpy.ops.object.transform_apply(rotation=True)
    
    return obj

# ============================================
# Let's start, Dr Frankenstein!
# ============================================

def create_grohe_adapter():
    """ Create the whole adapter mesh """
    print("\n" + "="*60)
    print("Let's go for a Grohe adapter (v4)")
    print("="*60)
    
    clear_mesh_objects()
    
    # Calculate Z-coords for layers (bottom-to-top)
    z_flange_bot = 0
    z_flange_top = FLANGE_H
    
    # Body cylinder
    body_h = TOTAL_H - FLANGE_H - TAPER_H - OUTER_HEIGHT
    z_body_top = z_flange_top + body_h
    
    z_taper_top = z_body_top + TAPER_H
    z_top = TOTAL_H
    
    print(f"Layers: flange 0-{FLANGE_H}, body{FLANGE_H}-{z_body_top}, cone {z_body_top}-{z_taper_top}, taper {z_taper_top}-{z_top}")
    
    # ========== 1. Main parts  ==========
    
    print("\n[1/8] Creating the flange...")
    
    d_flange_bottom = FLANGE_D - 2 * FLANGE_CHAMFER_BOT  # Bottom diameter
    d_flange_chamfer_top = FLANGE_D - 2 * FLANGE_CHAMFER_TOP  # Diameter after the top chamfer
    
    # Bottom chamfer
    flange_chamfer_bot = create_cone(
        "flange_chamfer_bot",
        d_flange_bottom, FLANGE_D,
        FLANGE_CHAMFER_BOT,
        z_offset=0
    )
    
    # Middle part (cylinder)
    flange_mid_h = FLANGE_H - FLANGE_CHAMFER_BOT - FLANGE_CHAMFER_TOP
    if flange_mid_h > 0.01:  # If it is smaller, it is anyway not possible to print
        flange_mid = create_cylinder(
            "flange_mid",
            FLANGE_D,
            flange_mid_h,
            z_offset=FLANGE_CHAMFER_BOT
        )
        boolean_union(flange_chamfer_bot, flange_mid, apply=True)
        delete_object(flange_mid)
    
    # Top chamfer
    flange_chamfer_top = create_cone(
        "flange_chamfer_top",
        FLANGE_D, d_flange_chamfer_top,
        FLANGE_CHAMFER_TOP,
        z_offset=FLANGE_H - FLANGE_CHAMFER_TOP
    )
    boolean_union(flange_chamfer_bot, flange_chamfer_top, apply=True)
    delete_object(flange_chamfer_top)
    
    # Now flange_chamfer_bot contains the whole flange
    flange = flange_chamfer_bot
    flange.name = "flange"
    
    print("[2/8] Creating the body...")
    body = create_cylinder(
        "body",
        BODY_D,
        body_h,
        z_offset=FLANGE_H
    )
    
    print("[3/8] Creating the taper...")
    taper = create_cone(
        "taper",
        BODY_D, OUTER_D_MIN,
        TAPER_H,
        z_offset=z_body_top
    )
    
    print("[4/8] Creating the outer splines...")
    outer_splines = create_splined_cylinder(
        "outer_splines",
        OUTER_D_MIN, OUTER_D_MAX,
        OUTER_TEETH,
        OUTER_HEIGHT,
        z_offset=z_taper_top
    )
    
    # ========== 2. Joining as a whole  ==========
    
    print("[5/8] Joining the parts...")
    
    # Starting with outer_splines
    adapter = outer_splines
    adapter.name = "GroheAdapter"
    
    for part in [taper, body, flange]:
        boolean_union(adapter, part, apply=True)
        delete_object(part)
    
    # ========== 3. Cutting the slots ==========
    
    print("[6/8] Cutting the top side slots...")
    z_top_slots = TOTAL_H - TOP_SLOT_DEPTH
    
    for i in range(TOP_SLOT_COUNT):
        angle = (360 / TOP_SLOT_COUNT) * i
        cutter = create_slot_cutter(
            f"top_slot_{i}",
            TOP_SLOT_WIDTH,
            TOP_SLOT_DEPTH + 1,  # +1 to make sure it cuts through
            z_top_slots - 0.5,
            angle
        )
        boolean_difference(adapter, cutter, apply=True)
        delete_object(cutter)
    
    print("[7/8] Cutting the bottom side slots...")
    for i in range(BOT_SLOT_COUNT):
        angle = (360 / BOT_SLOT_COUNT) * i + BOT_SLOT_OFFSET
        cutter = create_slot_cutter(
            f"bot_slot_{i}",
            BOT_SLOT_WIDTH,
            BOT_SLOT_HEIGHT + 1,
            -0.5,
            angle
        )
        boolean_difference(adapter, cutter, apply=True)
        delete_object(cutter)
    
    # ========== 4. Inner hole and splines ==========
    
    print("[8/8] Cutting the inner hole and splines...")
    
    # Inner splines: 14mm from the top side
    inner_spline_height = 14.0
    z_inner_start = TOTAL_H - inner_spline_height
    
    inner_cutter = create_splined_cylinder(
        "inner_cutter",
        INNER_D_MIN + TOL_INNER * 2,
        INNER_D_MAX + TOL_INNER * 2,
        INNER_TEETH,
        inner_spline_height + 1, 
        z_offset=z_inner_start - 0.5
    )
    boolean_difference(adapter, inner_cutter, apply=True)
    delete_object(inner_cutter)
    
    # Bottom side hole
    hole_height = z_inner_start  # From the bottom face to the teeth
    hole_cutter = create_cylinder(
        "hole_cutter",
        INNER_HOLE_D + TOL_INNER * 2,
        hole_height + 1,
        z_offset=-0.5
    )
    boolean_difference(adapter, hole_cutter, apply=True)
    delete_object(hole_cutter)
    
    # Inner con starts on the same level as the outer one
    inner_cone_cutter = create_cone(
        "inner_cone_cutter",
        INNER_HOLE_D + TOL_INNER * 2,  # Bottom side diameter
        INNER_D_MIN + TOL_INNER * 2,   # Top side diameter
        TAPER_H,                       # Cone height
        z_offset=z_inner_start - 0.5
    )
    boolean_difference(adapter, inner_cone_cutter, apply=True)
    delete_object(inner_cone_cutter)
    
    # ========== 5. Finalization ==========
    
    bpy.context.view_layer.objects.active = adapter
    adapter.select_set(True)
    
    # Recalculation of the normals
    bpy.ops.object.mode_set(mode='EDIT')
    bpy.ops.mesh.select_all(action='SELECT')
    bpy.ops.mesh.normals_make_consistent(inside=False)
    bpy.ops.object.mode_set(mode='OBJECT')
    
    # Smoothing (uncomment if needed)
    # bpy.ops.object.shade_smooth()
    
    print("\n" + "="*60)
    print("Done.")
    print("="*60)

    return adapter

# ============================================
if __name__ == "__main__":

    create_grohe_adapter()
