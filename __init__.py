import bpy
import os
import gc
import re
import threading
import json
import bpy.utils.previews

from bpy.types import Panel, Operator, PropertyGroup, UIList
from bpy.props import StringProperty, CollectionProperty, IntProperty, BoolProperty, PointerProperty

bl_info = {
    "name": "TMG Material Browser",
    "author": "Johnathan Mueller",
    "version": (1, 0),
    "blender": (4, 4, 1),
    "location": "View3D > Sidebar > TMG > Material Browser",
    "description": "Browse and manage materials from blend files",
    "category": "TMG",
}

# ---------- CONFIG ----------
preview_collections = {}

CACHE_SUFFIX = "_Data"
JSON_NAME = "{}.json"
PREVIEW_FOLDER = "previews"

KEYWORD_CATEGORIES = {
    # Core Natural Surfaces
    "Wood": [
        "wood", "wooden", "bark", "oak", "birch", "cedar", "chestnut", "bamboo", "splinter",
        "kumiko", "frame", "board", "chipboard", "cardboard", "paper"
        ],
    "Asphalt": [
        "asphalt", "road"
    ],
    "Concrete": [
        "concrete", "cement", "concerete", "pavement"
    ],
    "Brick": ["brick", "bricks", "masonry", "block", "pave"],
    "Granite": ["granite"],
    "Marble": ["marble"],
    "Stone": [
        "rock", "stone", "pebble", "slate", "limestone", "sandstone", "mountain", "earth", "crystal",
        "slab", "asteroid", "asteriod", "lava", "magma", "volcanic", "volcano"
    ],

    # Metal & Hard Surface
    "Metal": [
        "metal", "steel", "iron", "copper", "brass", "castiron", "aluminum", "nail", "screw", "armor", "rust",
        "foil", "silver"
    ],
    "Plastic": [
        "plastic", "poly", "polimer", "paint", "acrylic", "resin", "terrazzo"
    ],
    "Rubber": ["rubber", "hose", "pipe", "tire", "synthetic", "grip"],
    "Glass": ["glass", "window"],
    "Ceramic": ["ceramic", "clay", "terracotta", "pottery", "tileware", "porcelain"],

    # Organic & Living Matter
    "Fabric": [
        "fabric", "cloth", "leather", "lace", "denim", "jeans", "cotton", "fleece",
        "sofa", "rug", "vest", "shirt", "coat", "boot", "padded", "foam", "textile", "wool",
        "stich", "chair", "upholstery", "carpet", "tatami", "sheet", "bed", "stitches", "brush",
        "leather", "woven", "basket", "tartan"
    ],
    "Plant": ["leaf", "leaves", "tree", "flower", "grass", "root", "moss", "ivy", "bush"],
    "Organic": [
        "skin", "flesh", "blood", "meat", "eye", "mouth", "nose", "ear", "cheek", "face",
        "slime", "saliva", "puss", "zombie", "rotten", "rotting", "feather", "feathers", "scales", "honey", "comb"
    ],

    # Utility / Stylized / Misc
    "Tile": ["tile", "tiles", "tiled", "graph"],
    "Floor": ["floor", "flooring", "ground", "pavement", "tatami"],
    "Wall": ["wall", "walls", "panel", "panels"],
    "Ceiling": ["ceiling"],
    "Roof": ["roof"],
    "Facade": ["facade", "window", "door"],
    "Wicker": ["wicker", "rattan"],
    "Transparent": ["transparent", "clear", "opacity"],

    # Stylized / Thematic
    "Sci-Fi": [
        "sci fi", "scifi", "sci_fi", "sci fy", "scyfy", "scify", "tech", "futuristic", "cyber", "synth", "alien",
        "container"
    ],
    "Stylized": ["stylized", "toon", "cartoon", "handpainted", "painted"],
    "Abstract": ["abstract", "pattern", "geometry", "geometric", "mandala", "mosaic", "disco"],
    "Food": ["candy", "gum", "sweet", "cheese", "beef", "pork", "corn", "grape", "apple", "meat", "soup"],

    # Special
    "Debug": ["wireframe", "uv", "checker", "matcap", "normal", "test", "grid"],
}

# ----------JSON Parsing ---------
def get_category(material_name):
    material_name_lower = material_name.lower()
    for category, keywords in KEYWORD_CATEGORIES.items():
        if any(keyword in material_name_lower for keyword in keywords):
            return category
    return "Uncategorized"

def get_category_items(self, context):
    items = [("All", "All", "Show all materials")]
    categories = sorted(set(item.category for item in context.scene.material_browser_items))
    for cat in categories:
        items.append((cat, cat, f"Category: {cat}"))
    return items

def parse_blend_file(filepath):
    materials = []

    blend_dir = os.path.dirname(filepath)
    blend_name = os.path.splitext(os.path.basename(filepath))[0]
    preview_folder = os.path.join(blend_dir, f"{blend_name}_Data", PREVIEW_FOLDER)

    with bpy.data.libraries.load(filepath, link=False) as (data_from, data_to):
        for mat_name in data_from.materials:
            if not mat_name or mat_name.strip() == "":
                continue

            preview_filename = f"{mat_name}.png"
            preview_path = os.path.join(preview_folder, preview_filename)

            # If the preview image exists, use the filename. If not, fallback to ""
            preview = preview_filename if os.path.exists(preview_path) else ""

            materials.append({
                "name": mat_name.strip(),
                "category": get_category(mat_name),
                "preview": preview
            })

    return materials


def write_json(json_path, data):
    os.makedirs(os.path.dirname(json_path), exist_ok=True)
    try:
        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2)
    except Exception as e:
        print(f"Failed to write JSON file at {json_path}: {e}")


def read_json(json_path):
    if not os.path.exists(json_path):
        return []

    if os.path.getsize(json_path) == 0:
        print(f"Warning: JSON file at {json_path} is empty.")
        return []

    try:
        with open(json_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except json.JSONDecodeError as e:
        print(f"Error decoding JSON file at {json_path}: {e}")
        return []

# ---------- CORE UTILS ----------
def get_dynamic_categories(self, context):
    categories = {"All"}
    for item in context.scene.material_browser_items:
        categories.add(item.category)

    return [(cat, cat, "") for cat in sorted(categories)]

def clear_preview_collection():
    if "material_thumbs" in preview_collections:
        bpy.utils.previews.remove(preview_collections["material_thumbs"])
        del preview_collections["material_thumbs"]
    gc.collect()

def load_all_previews(preview_folder):
    pcoll = preview_collections.get("material_thumbs")
    if not pcoll:
        pcoll = bpy.utils.previews.new()
        preview_collections["material_thumbs"] = pcoll

    pcoll.clear()  # Make sure we’re clean before loading

    for f in os.listdir(preview_folder):
        if f.lower().endswith((".png", ".jpg")):
            path = os.path.join(preview_folder, f)
            key = os.path.splitext(f)[0]  # match material name
            pcoll.load(key, path, 'IMAGE')

def load_all_previews(context):
    # Clear any existing previews to avoid memory bloat
    clear_preview_collection()

    # Create a fresh preview collection
    pcoll = bpy.utils.previews.new()
    preview_collections["material_thumbs"] = pcoll

    folder_path = bpy.path.abspath(context.scene.material_browser_path)
    if not os.path.isdir(folder_path):
        print(f"[MaterialBrowser] Invalid path: {folder_path}")
        return

    blend_files = [f for f in os.listdir(folder_path) if f.lower().endswith(".blend")]

    for blend_file in blend_files:
        # Path to the _data/previews folder for this blend
        preview_folder = os.path.join(
            folder_path,
            blend_file.replace(".blend", CACHE_SUFFIX),
            PREVIEW_FOLDER
        )

        if not os.path.isdir(preview_folder):
            continue

        for fname in os.listdir(preview_folder):
            if fname.lower().endswith(".png"):
                full_path = os.path.join(preview_folder, fname)
                name_key = os.path.splitext(fname)[0]  # Strip .png

                if name_key not in pcoll:
                    try:
                        pcoll.load(name_key, full_path, 'IMAGE')
                    except Exception as e:
                        print(f"[MaterialBrowser] Failed to load preview {full_path}: {e}")

def load_previews(preview_dir, materials):
    for mat in materials:
        name = mat["name"]
        preview = mat.get("preview", "")
        if preview:
            img_path = os.path.join(preview_dir, preview)
            if os.path.exists(img_path):
                preview_images[name] = preview_collection.load(name, img_path, 'IMAGE')

def unload_previews():
    if not preview_collections:
        for key, pcoll in preview_collections.items():
            bpy.utils.previews.remove(pcoll)
        preview_collections.clear()
    gc.collect()

def refresh_material_list(context, material_data_list):
    items = context.scene.material_browser_items
    items.clear()

    for entry in material_data_list:
        item = items.add()
        item.name = entry.get("name", "Unnamed")
        item.category = get_category(item.name)
        # item.category = categorize_material(item.name)
        item.preview_path = os.path.join(
            context.scene.material_browser_path,
            entry["blend_file"].replace(".blend", CACHE_SUFFIX),
            PREVIEW_FOLDER,
            f"{item.name}.png"
        )
        item.blend_file = os.path.join(context.scene.material_browser_path, entry["blend_file"])

    context.scene.material_browser_material_count = f"Materials: {len(context.scene.material_browser_items)}"
    context.scene.material_browser_material_category_count = f"Materials: {len(context.scene.material_browser_filtered_items)}"
    update_material_browser_filter(None, context)

def find_height_texture(mat):
    if not mat or not mat.use_nodes:
        return None
    for node in mat.node_tree.nodes:
        if node.type == 'TEX_IMAGE':
            # crude heuristic: texture node name or image name contains 'height' or 'displacement'
            name = node.name.lower()
            img_name = node.image.name.lower() if node.image else ""
            if "height" in name or "displacement" in name or "height" in img_name or "displacement" in img_name:
                return node.image
    return None

def create_texture_from_image(image):
    # Blender 2.80 needs Texture datablock for modifiers
    tex_name = f"DispTex_{image.name}"
    if tex_name in bpy.data.textures:
        return bpy.data.textures[tex_name]
    tex = bpy.data.textures.new(tex_name, type='IMAGE')
    tex.image = image
    return tex

def setup_displacement_modifier(obj, image, strength=0.1):
    for mod in obj.modifiers:
        if mod.type == 'DISPLACE':
            # Update the texture if it's different
            tex = create_texture_from_image(image)
            if mod.texture != tex:
                mod.texture = tex
            mod.texture_coords = 'UV'
            mod.strength = strength
            return

def disconnect_displacement(mat, context, enable_displacement):
    if enable_displacement:
        height_image = find_height_texture(mat)
        if height_image:
            for obj in context.selected_objects:
                if obj.type == 'MESH':
                    setup_displacement_modifier(obj, height_image, strength=0.1)
    else:
        if mat and mat.use_nodes and mat.node_tree:
            for node in mat.node_tree.nodes:
                if node.type == 'OUTPUT_MATERIAL':
                    disp_input = node.inputs.get('Displacement')
                    if disp_input and disp_input.is_linked:
                        for link in disp_input.links:
                            mat.node_tree.links.remove(link)

def filter_material_browser_items(scn):
    scn.material_browser_filtered_items.clear()
    filter_text = scn.material_browser_filter.lower()
    selected_category = scn.material_browser_category

    for item in scn.material_browser_items:
        if selected_category in {"All", item.category}:
            if filter_text in item.name.lower():
                new_item = scn.material_browser_filtered_items.add()
                new_item.name = item.name
                new_item.category = item.category
                new_item.blend_file = item.blend_file

                # Copy the preview path directly
                new_item.preview_path = item.preview_path if item.preview_path else ""

    scn.material_browser_material_count = f"Materials: {len(scn.material_browser_items)}"
    scn.material_browser_material_category_count = f"Materials: {len(scn.material_browser_filtered_items)}"

    if len(scn.material_browser_filtered_items) > 0:
        scn.material_browser_index = 0


def update_material_browser_filter(self, context):
    filter_material_browser_items(context.scene)


def update_material_browser_category(self, context):
    filter_material_browser_items(context.scene)

def get_category(material_name):
    material_name_lower = material_name.lower()
    for category, keywords in KEYWORD_CATEGORIES.items():
        if any(keyword in material_name_lower for keyword in keywords):
            return category
    return "Uncategorized"

def categorize_material(name):
    name_lower = name.lower()
    for keyword, category in KEYWORD_CATEGORIES.items():
        if keyword in name_lower:
            return category
    return "Uncategorized"

def update_change_file_path(self, context):
    clear_preview_collection()
    folder_path = bpy.path.abspath(context.scene.material_browser_path)

    if not os.path.isdir(folder_path):
        self.report({'ERROR'}, "Invalid folder path")
        return {'CANCELLED'}

    all_materials = []
    context.scene.material_browser_items.clear()

    blend_files = [f for f in os.listdir(folder_path) if f.lower().endswith(".blend")]

    for blend_file in blend_files:
        blend_path = os.path.join(folder_path, blend_file)
        cache_folder = os.path.join(folder_path, blend_file.replace(".blend", CACHE_SUFFIX))
        json_path = os.path.join(cache_folder, JSON_NAME.format(blend_file.replace(".blend", "")))

        # Refresh .json only if it doesn't exist
        if not os.path.exists(json_path):
            material_data = parse_blend_file(blend_path)
            write_json(json_path, material_data)

        json_data = read_json(json_path)
        if json_data:
            for entry in json_data:
                entry["blend_file"] = blend_file  # Tag source file
            all_materials.extend(json_data)

    # Update list with combined material data
    refresh_material_list(context, all_materials)

    # Load all previews after list is populated
    load_all_previews(context)

    # UI stats
    context.scene.material_browser_material_count = f"Materials: {len(context.scene.material_browser_items)}"
    context.scene.material_browser_material_category_count = f"Materials: {len(context.scene.material_browser_filtered_items)}"
    context.scene.material_browser_category = "All"

    # Auto-select first material
    if context.scene.material_browser_filtered_items:
        context.scene.material_browser_index = 0


# ---------- Custom Property Group ----------
class MaterialItem(PropertyGroup):
    name: StringProperty()
    category: StringProperty()
    blend_file: StringProperty()
    preview_path: StringProperty(subtype='FILE_PATH')

class MaterialCache(PropertyGroup):
    blend_file: StringProperty()
    folder_path: StringProperty(subtype="DIR_PATH")
    materials: CollectionProperty(type=MaterialItem)
    preview_path: StringProperty(subtype='FILE_PATH')


# ---------- OPERATORS ----------
class MATERIALBROWSER_OT_SelectMaterial(bpy.types.Operator):
    bl_idname = "materialbrowser.select_material"
    bl_label = "Select Material"

    material_name: bpy.props.StringProperty()

    def execute(self, context):
        context.scene.material_browser_selected_material = self.material_name
        return {'FINISHED'}

class MATERIALBROWSER_OT_RefreshCache(bpy.types.Operator):
    bl_idname = "materialbrowser.refresh_cache"
    bl_label = "Refresh Material Cache"
    directory: StringProperty(subtype="DIR_PATH")

    def execute(self, context):
        folder_path = bpy.path.abspath(context.scene.material_browser_path)

        if not os.path.isdir(folder_path):
            self.report({'ERROR'}, f"Invalid folder path: {folder_path}")
            return {'CANCELLED'}

        context.scene.material_cache.folder_path = folder_path
        context.scene.material_cache.materials.clear()

        blend_files = [f for f in os.listdir(folder_path) if f.lower().endswith(".blend")]


        for blend_file in blend_files:
            blend_path = os.path.join(folder_path, blend_file)
            cache_folder = os.path.join(folder_path, blend_file.replace(".blend", CACHE_SUFFIX))
            preview_folder = os.path.join(cache_folder, PREVIEW_FOLDER)
            context.scene.previews_folder_path = preview_folder

            json_path = os.path.join(cache_folder, JSON_NAME.format(blend_file.replace(".blend", "")))

            # Always reparse and overwrite json cache
            mats = parse_blend_file(blend_path)

            # Ensure cache folder exists
            os.makedirs(cache_folder, exist_ok=True)
            write_json(json_path, mats)

            # Refresh material cache UI list from JSON data
            refresh_material_list(context, mats, blend_file)
        
        if context.scene.material_browser_filtered_items:
            first_item = context.scene.material_browser_filtered_items[0]
            context.scene.material_browser_selected_material = first_item.name
            context.scene.material_browser_index = 0

        self.report({'INFO'}, "Material cache fully refreshed")
        print("Material cache fully refreshed.")
        return {'FINISHED'}
    
    
class MATERIALBROWSER_OT_AppendMaterial(bpy.types.Operator):
    bl_idname = "materialbrowser.append_material"
    bl_label = "Append Material"
    bl_description = "Append selected material to selected objects"

    blend_file: StringProperty()
    material_name: StringProperty()

    def execute(self, context):
        folder_path = bpy.path.abspath(bpy.context.scene.material_browser_path)
        blend_path = os.path.join(folder_path, self.blend_file)
        material_name = self.material_name

        if not os.path.isfile(blend_path):
            self.report({'ERROR'}, f"Blend file not found: {blend_path}")
            return {'CANCELLED'}

        # Check if material already exists in current blend
        mat = bpy.data.materials.get(material_name)
        if not mat:
            # Append material from external blend file
            with bpy.data.libraries.load(blend_path, link=False) as (data_from, data_to):
                if material_name in data_from.materials:
                    data_to.materials = [material_name]
            mat = bpy.data.materials.get(material_name)
            if not mat:
                self.report({'ERROR'}, f"Material {material_name} not found in {blend_path}")
                return {'CANCELLED'}

        disconnect_displacement(mat, context, context.scene.enable_displacement)

        # Assign material to all selected objects
        for obj in context.selected_objects:
            if obj.type == 'MESH':
                # Clear existing materials or just add?
                if obj.data.materials:
                    # Replace first material slot with new mat
                    obj.data.materials[0] = mat
                else:
                    obj.data.materials.append(mat)

        self.report({'INFO'}, f"Appended material '{material_name}' to selected objects")
        return {'FINISHED'}


class MATERIALBROWSER_OT_LinkMaterial(bpy.types.Operator):
    bl_idname = "materialbrowser.link_material"
    bl_label = "Link Material"
    bl_description = "Link selected material to selected objects (linked library)"

    blend_file: StringProperty()
    material_name: StringProperty()

    def execute(self, context):
        folder_path = bpy.path.abspath(bpy.context.scene.material_browser_path)
        blend_path = os.path.join(folder_path, self.blend_file)
        material_name = self.material_name

        if not os.path.isfile(blend_path):
            self.report({'ERROR'}, f"Blend file not found: {blend_path}")
            return {'CANCELLED'}

        # Check if material already linked
        mat = bpy.data.materials.get(material_name)
        if not mat:
            # Link material from external blend file
            with bpy.data.libraries.load(blend_path, link=True) as (data_from, data_to):
                if material_name in data_from.materials:
                    data_to.materials = [material_name]
            mat = bpy.data.materials.get(material_name)
            if not mat:
                self.report({'ERROR'}, f"Material {material_name} not found in {blend_path}")
                return {'CANCELLED'}

        # Assign material to all selected objects
        for obj in context.selected_objects:
            if obj.type == 'MESH':
                if obj.data.materials:
                    obj.data.materials[0] = mat
                else:
                    obj.data.materials.append(mat)

        self.report({'INFO'}, f"Linked material '{material_name}' to selected objects")
        return {'FINISHED'}


class MATERIALBROWSER_OT_Scan(bpy.types.Operator):
    bl_idname = "materialbrowser.scan"
    bl_label = "Scan Materials"
    directory: StringProperty(subtype="DIR_PATH")

    def parse_material_list(self, context):
        self.report({'INFO'}, "Scanning materials...")

        dir_path = bpy.path.abspath(context.scene.material_browser_path)
        if not os.path.isdir(dir_path):
            self.report({'ERROR'}, f"Invalid directory: {dir_path}")
            return

        context.scene.material_cache.folder_path = dir_path
        context.scene.material_cache.materials.clear()

        for fname in os.listdir(dir_path):
            if fname.lower().endswith(".blend"):
                blend_path = os.path.join(dir_path, fname)
                name_wo_ext = os.path.splitext(fname)[0]
                data_dir = os.path.join(dir_path, f"{name_wo_ext}{CACHE_SUFFIX}")
                json_path = os.path.join(data_dir, JSON_NAME.format(name_wo_ext))

                # Always write new JSON for fresh parsing
                mats = parse_blend_file(blend_path)
                write_json(json_path, mats)

                # Load parsed materials from JSON
                for mat in mats:
                    item = context.scene.material_cache.materials.add()
                    item.name = mat.get("name", "Unnamed")
                    item.category = mat.get("category", "Uncategorized")

                    # Combine full preview path safely
                    preview_rel = mat.get("preview", "")
                    item.preview_path = os.path.join(context.scene.previews_folder_path, preview_rel) if preview_rel else ""

        self.report({'INFO'}, "Material scan complete.")
        print("Material scan complete.")


    def load_material_list(self, context):
        folder_path = bpy.path.abspath(context.scene.material_browser_path)

        if not os.path.isdir(folder_path):
            self.report({'ERROR'}, "Invalid folder path")
            return {'CANCELLED'}

        blend_files = [f for f in os.listdir(folder_path) if f.lower().endswith(".blend")]

        for blend_file in blend_files:
            blend_path = os.path.join(folder_path, blend_file)
            cache_folder = os.path.join(folder_path, blend_file.replace(".blend", CACHE_SUFFIX))
            preview_folder = os.path.join(cache_folder, PREVIEW_FOLDER)
            context.scene.previews_folder_path = preview_folder

            json_path = os.path.join(cache_folder, JSON_NAME.format(blend_file.replace(".blend", "")))

            # Regenerate only if missing
            if not os.path.exists(json_path):
                material_data = parse_blend_file(blend_path)
                write_json(json_path, material_data)

            json_data = read_json(json_path)
            refresh_material_list(context, json_data, blend_file)

    def execute(self, context):
        self.report({'INFO'}, "Scanning in background...")

        dir_path = bpy.path.abspath(context.scene.material_browser_path)
        if not os.path.isdir(dir_path):
            print("Invalid directory:", dir_path)
            return {'CANCELLED'}

        self.parse_material_list(context)
        self.load_material_list(context)

        self.report({'INFO'}, "Scan complete")
        print("Scan complete.")
        return {'FINISHED'}


# ---------- UI Lists -----------
class MATERIALBROWSER_UL_items(bpy.types.UIList):
    def draw_item(self, context, layout, data, item, icon, active_data, active_propname, index):
        pcoll = preview_collections.get("material_thumbs")
        icon_id = 0  # fallback

        # Try to get a valid icon from the preview collection
        if pcoll and item.name in pcoll:
            icon_id = pcoll[item.name].icon_id

        # Draw layout depending on type
        if self.layout_type in {'DEFAULT', 'COMPACT'}:
            row = layout.row(align=True)

            if icon_id > 0:
                row.label(text="", icon_value=icon_id)
            elif pcoll:
                row.label(text="", icon='ERROR')  # preview collection exists but icon failed
            else:
                row.label(text="", icon='QUESTION')  # no preview collection at all

            row.label(text=item.name)

            # split = row.split(factor=0.7)
            # split.label(text=item.name)
            # split.label(text=f"[{item.category}]")
            

# ---------- Main Panel ----------
class MATERIALBROWSER_PT_Panel(Panel):
    bl_label = "Material Browser"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "TMG"

    def draw(self, context):
        layout = self.layout
        scn = context.scene

        box = layout.box()
        col = box.column()
        row = col.row()
        row.prop(scn, "material_browser_path", text="")
        row.operator("materialbrowser.refresh_cache", text="", icon="FILE_REFRESH")
        col = box.column()
        col.label(text=scn.material_browser_material_count)

        box = layout.box()
        col = box.column()
        col.prop(scn, "enable_displacement")

        box = layout.box()
        col = box.column()
        col.prop(scn, "material_browser_category", text="Category")
        col.label(text=scn.material_browser_material_category_count)

        # Get active material item
        items = getattr(scn, "material_browser_filtered_items", None)
        index = getattr(scn, "material_browser_index", -1)
        active_item = items[index] if items and 0 <= index < len(items) else None

        # Optional preview display
        if active_item:
            box = layout.box()
            col = box.column()

            pcoll = preview_collections.get("material_thumbs")

            row = col.row(align=True)
            if pcoll and active_item.name in pcoll:
                icon_id = pcoll[active_item.name].icon_id
                row.template_icon(icon_value=icon_id, scale=10.0)
                # if icon_id > 0:
                #     row.label(text="", icon_value=icon_id)
                # else:
                #     row.label(text="", icon='ERROR')
            else:
                row.label(text="", icon='QUESTION')
                row.scale_y = 10.0
                row.alignment = 'CENTER'


            # if active_item:
            # if pcoll and active_item.name in pcoll:
            #     icon_id = pcoll[active_item.name].icon_id
            #     col.template_icon(icon_value=icon_id, scale=5.0)

            # preview_path = getattr(active_item, "preview_path", "")
            # pcoll = preview_collections.get("material_thumbs")

            # if pcoll and preview_path in pcoll:
            #     icon_id = pcoll[preview_path].icon_id
            #     col.template_icon(icon_value=icon_id, scale=5.0)
            # else:
            #     col = col.column()
            #     col.scale_y = 5.0
            #     row = col.row()
            #     row.alignment = 'CENTER'
            #     row.label(icon='ERROR')

            # Append / Link buttons
            col = layout.column()
            row = col.row(align=True)

        if active_item and context.selected_objects:
            if hasattr(active_item, "blend_file") and hasattr(active_item, "name"):
                blend_path = bpy.path.abspath(active_item.blend_file)

                append_op = row.operator("materialbrowser.append_material", text="Append", icon='IMPORT')
                append_op.blend_file = blend_path
                append_op.material_name = active_item.name

                link_op = row.operator("materialbrowser.link_material", text="Link", icon='LINKED')
                link_op.blend_file = blend_path
                link_op.material_name = active_item.name
            else:
                col.label(text="Invalid material entry", icon='ERROR')
        else:
            col.label(text="No materials selected to append / link")

        # Always draw the list
        col.row().template_list(
            "MATERIALBROWSER_UL_items", "materials",
            scn, "material_browser_filtered_items",
            scn, "material_browser_index",
            rows=12
        )


# ---------- Register Properties ----------
classes = (
    MaterialItem,
    MaterialCache,
    MATERIALBROWSER_UL_items,
    MATERIALBROWSER_PT_Panel,
    MATERIALBROWSER_OT_Scan,
    MATERIALBROWSER_OT_RefreshCache,
    MATERIALBROWSER_OT_AppendMaterial,
    MATERIALBROWSER_OT_LinkMaterial,
    MATERIALBROWSER_OT_SelectMaterial,
)

def register():
    for cls in classes:
        bpy.utils.register_class(cls)

    bpy.types.Scene.material_browser_path = StringProperty(
        name="Directory",
        description="Path to blend file directory",
        subtype='DIR_PATH',
        update=update_change_file_path
    )

    bpy.types.Scene.material_browser_filter = StringProperty(
        name="Filter",
        description="Filter material names",
        default="",
        update=update_material_browser_filter
    )

    bpy.types.Scene.enable_displacement = BoolProperty(
        name="Enable Displacement",
        description="Add displacement modifier if height texture found",
        default=False,
    )

    bpy.types.Scene.material_browser_category = bpy.props.EnumProperty(
        name="Category",
        description="Filter by category",
        items=[("All", "All", "")] +
            [(cat, cat, "") for cat in sorted(KEYWORD_CATEGORIES.keys())] +
            [("Uncategorized", "Uncategorized", "")],  # add this line
        default="All",
        update=update_material_browser_category
    )

    bpy.types.Scene.material_browser_material_count = StringProperty(
        name="Material Count",
        description="Displays how many materials are in the list",
        default="Materials: 0"
    )

    bpy.types.Scene.material_browser_material_category_count = StringProperty(
        name="Material Category Count",
        description="Displays how many materials are in the category list",
        default="Materials: 0"
    )

    bpy.types.Scene.material_browser_items = CollectionProperty(type=MaterialItem)
    bpy.types.Scene.material_browser_filtered_items = CollectionProperty(type=MaterialItem)
    bpy.types.Scene.material_browser_index = IntProperty()
    bpy.types.Scene.material_cache = PointerProperty(type=MaterialCache)
    preview_collections["material_thumbs"] = bpy.utils.previews.new()
    bpy.types.Scene.material_browser_selected_material = bpy.props.StringProperty(name="Selected Material")
    
    bpy.types.Scene.previews_folder_path = StringProperty(
        name="Previews Folder",
        description="Path to preview images for materials",
        subtype='DIR_PATH',
        default=""
    )


def unregister():
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)
    
    # Safely remove all previews
    if not preview_collections:
        for name, pcoll in list(preview_collections.items()):
            bpy.utils.previews.remove(pcoll)
        preview_collections.clear()
    
    if "material_thumbs" in preview_collections:
        bpy.utils.previews.remove(preview_collections["material_thumbs"])
        preview_collections.pop("material_thumbs")

    del bpy.types.Scene.material_browser_path
    del bpy.types.Scene.material_browser_filter
    del bpy.types.Scene.material_browser_category
    del bpy.types.Scene.enable_displacement
    del bpy.types.Scene.material_browser_material_count
    del bpy.types.Scene.material_browser_material_category_count
    del bpy.types.Scene.previews_folder_path
    del bpy.types.Scene.material_browser_selected_material
    gc.collect()


if __name__ == "__main__":
    register()
