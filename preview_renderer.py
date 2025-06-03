import bpy
import os
import sys
import gc

# --- CONFIGURATION ---

TARGET_OBJECT_NAME = "Cube"
overwrite_all_previews = True
IMG_TYPE = "JPEG"
IMG_EXT = "jpg"
RENDER_RES = 128

# --- ARG PARSING ---

argv = sys.argv
if "--" in argv:
    argv = argv[argv.index("--") + 1:]
else:
    argv = []

if len(argv) < 2:
    print("Usage: blender --background --python render_previews_batch.py -- <jpg> <png> -- <True> <False> -- <blend_folder> <blend1.blend> <blend2.blend> ...")
    sys.exit(1)

IMG_EXT = argv[0].lower()
overwrite_all_previews = argv[1].lower() == "true"
BLEND_FOLDER = argv[2]
blend_files = argv[3:]

# --- FUNCTIONS ---
def safe_filename(name):
    return "".join(c if c.isalnum() or c in "-_." else "_" for c in name)

def clear_existing_materials(obj):
    if obj.data.materials:
        obj.data.materials.clear()
        gc.collect()

def assign_material(obj, mat):
    obj.data.materials.append(mat)

def render_preview(output_path):
    bpy.context.scene.render.filepath = output_path
    bpy.ops.render.render(write_still=True)
    print(f"Rendered preview: {output_path}")

def process_blend_file(blend_filename):
    blend_path = os.path.join(BLEND_FOLDER, blend_filename)
    blend_name = os.path.splitext(blend_filename)[0]
    preview_output_path = os.path.join(BLEND_FOLDER, f"{blend_name}_Data", "previews")

    os.makedirs(preview_output_path, exist_ok=True)

    # Load all materials from the blend file
    with bpy.data.libraries.load(blend_path, link=False) as (data_from, _):
        material_names = [name for name in data_from.materials if name]

    # Get the cube object
    cube = bpy.data.objects.get(TARGET_OBJECT_NAME)
    if not cube:
        print(f"Cube object '{TARGET_OBJECT_NAME}' not found!")
        return

    print(f"Processing {blend_filename} with {len(material_names)} materials")

    for i, mat_name in enumerate(material_names, 1):
        output_file = os.path.join(preview_output_path, f"{safe_filename(mat_name)}.{IMG_EXT}")
        alt_ext = "png" if IMG_EXT == "jpg" else "jpg"
        alt_file = os.path.join(preview_output_path, f"{safe_filename(mat_name)}.{alt_ext}")

        # Handle overwrite and cleanup
        # if overwrite_all_previews:
            # Delete opposite format if it exists
        if os.path.exists(alt_file):
            os.remove(alt_file)
            print(f"[{blend_name}] Removed outdated: {os.path.basename(alt_file)}")
        # else:
        #     if os.path.exists(output_file):
        #         print(f"[{blend_name}] Skipping existing: {mat_name}")
        #         continue

        output_file = os.path.join(preview_output_path, f"{safe_filename(mat_name)}.{IMG_EXT}")
        if not overwrite_all_previews and os.path.exists(output_file):
            print(f"[{blend_name}] Skipping existing: {mat_name}")
            continue

        with bpy.data.libraries.load(blend_path, link=False) as (_, data_to):
            data_to.materials = [mat_name]

        mat = bpy.data.materials.get(mat_name)
        if mat is None:
            print(f"⚠️ Failed to load material: {mat_name}")
            continue

        print(f"[{blend_name}] Rendering {mat_name} ({i}/{len(material_names)})")
        clear_existing_materials(cube)
        assign_material(cube, mat)
        render_preview(output_file)
        bpy.data.materials.remove(mat)
        gc.collect()

# --- SETUP RENDER SETTINGS ---

scene = bpy.context.scene
scene.render.engine = 'BLENDER_EEVEE_NEXT'
scene.render.resolution_x = RENDER_RES
scene.render.resolution_y = RENDER_RES
scene.render.resolution_percentage = 100
if IMG_EXT == "jpg":
    scene.render.image_settings.file_format = IMG_TYPE
    IMG_TYPE = "JPEG"
    scene.render.film_transparent = False
    scene.render.image_settings.quality = 90
elif IMG_EXT == "png":
    IMG_TYPE = "PNG"
    scene.render.image_settings.file_format = IMG_TYPE
    scene.render.image_settings.color_mode = 'RGBA'

# scene.render.image_settings.file_format = IMG_TYPE
scene.eevee.taa_render_samples = 8
scene.render.threads_mode = 'FIXED'
scene.render.threads = max(1, os.cpu_count())

# --- MAIN PROCESS ---

print(f"Starting batch rendering for {len(blend_files)} blend files")

for blend_file in blend_files:
    process_blend_file(blend_file)

print("Batch rendering done! 🎉")
