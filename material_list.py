import bpy
import os
import gc
import json
import bpy.utils.previews

from bpy.app.handlers import persistent
from bpy.types import Panel, Operator, PropertyGroup, UIList
from bpy.props import StringProperty, CollectionProperty, IntProperty, BoolProperty, PointerProperty

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

@persistent
def load_previews_on_start(dummy):
    context = bpy.context
    load_all_previews(context)

def parse_blend_file(filepath):
    materials = []

    blend_dir = os.path.dirname(filepath)
    blend_file = os.path.basename(filepath)
    blend_name = os.path.splitext(blend_file)[0]
    preview_folder = os.path.join(blend_dir, f"{blend_name}_Data", PREVIEW_FOLDER)

    with bpy.data.libraries.load(filepath, link=False) as (data_from, data_to):
        for mat_name in data_from.materials:
            if not mat_name or mat_name.strip() == "":
                continue

            preview_filename = f"{mat_name}.png"
            preview_path = os.path.join(preview_folder, preview_filename)
            preview = preview_filename if os.path.exists(preview_path) else ""

            materials.append({
                "name": mat_name.strip(),
                "category": get_category(mat_name),
                "preview": preview,
                "blend_file": blend_file
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
def clear_preview_collection():
    if "material_thumbs" in preview_collections:
        bpy.utils.previews.remove(preview_collections["material_thumbs"])
        del preview_collections["material_thumbs"]
    gc.collect()

def load_all_previews(context):
    path = getattr(context.scene, "material_browser_path", None)
    if not path:
        print("No material path set, skipping preview load.")
        return
    
    clear_preview_collection()
    pcoll = bpy.utils.previews.new()
    preview_collections["material_thumbs"] = pcoll

    folder_path = bpy.path.abspath(context.scene.material_browser_path)
    if not os.path.isdir(folder_path):
        print(f"[MaterialBrowser] Invalid path: {folder_path}")
        return

    blend_files = [f for f in os.listdir(folder_path) if f.lower().endswith(".blend")]

    for blend_file in blend_files:
        preview_folder = os.path.join(
            folder_path,
            blend_file.replace(".blend", CACHE_SUFFIX),
            PREVIEW_FOLDER
        )

        if not os.path.isdir(preview_folder):
            continue

        for fname in os.listdir(preview_folder):
            if fname.lower().endswith(".png") or fname.lower().endswith(".jpg"):
                full_path = os.path.join(preview_folder, fname)
                name_key = os.path.splitext(fname)[0]

                if name_key not in pcoll:
                    try:
                        pcoll.load(name_key, full_path, 'IMAGE')
                    except Exception as e:
                        print(f"[MaterialBrowser] Failed to load preview {full_path}: {e}")

def refresh_material_list(context, material_data_list, blend_file=""):
    items = context.scene.material_browser_items
    items.clear()

    for entry in material_data_list:
        item = items.add()
        item.name = entry.get("name", "Unnamed")
        item.category = get_category(item.name)
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

        if not os.path.exists(json_path):
            material_data = parse_blend_file(blend_path)
            write_json(json_path, material_data)

        json_data = read_json(json_path)
        if json_data:
            for entry in json_data:
                entry["blend_file"] = blend_file
            all_materials.extend(json_data)

    refresh_material_list(context, all_materials)
    load_all_previews(context)

    context.scene.material_browser_material_count = f"Materials: {len(context.scene.material_browser_items)}"
    context.scene.material_browser_material_category_count = f"Materials: {len(context.scene.material_browser_filtered_items)}"
    context.scene.material_browser_category = "All"

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
            mats = parse_blend_file(blend_path)
            os.makedirs(cache_folder, exist_ok=True)
            write_json(json_path, mats)
            refresh_material_list(context, mats, blend_file)
            load_all_previews(context)
        
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
        folder_path = bpy.path.abspath(context.scene.material_browser_path)
        blend_path = os.path.join(folder_path, self.blend_file)
        material_name = self.material_name
        self.report({'INFO'}, f"Appending material '{material_name}' to selected objects")

        # Check if material is already in bpy.data
        mat = bpy.data.materials.get(material_name)
        if not mat:
            # If it's not, try to load it from the specified blend file
            if not os.path.isfile(blend_path):
                self.report({'ERROR'}, f"Blend file not found: {blend_path}")
                return {'CANCELLED'}

            with bpy.data.libraries.load(blend_path, link=False) as (data_from, data_to):
                if material_name in data_from.materials:
                    data_to.materials = [material_name]
                else:
                    self.report({'ERROR'}, f"Material {material_name} not found in {blend_path}")
                    return {'CANCELLED'}

            # Check again after loading
            mat = bpy.data.materials.get(material_name)
            if not mat:
                self.report({'ERROR'}, f"Material {material_name} failed to load.")
                return {'CANCELLED'}

        # Apply displacement cleanup
        disconnect_displacement(mat, context, context.scene.enable_displacement)

        # Assign to selected objects
        for obj in context.selected_objects:
            if obj.type == 'MESH':
                if obj.data.materials:
                    obj.data.materials[0] = mat
                else:
                    obj.data.materials.append(mat)

        for area in context.screen.areas:
            if area.type == 'VIEW_3D':
                area.tag_redraw()

        for obj in context.selected_objects:
            obj.update_tag()

        bpy.context.view_layer.update()

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

        mat = bpy.data.materials.get(material_name)
        if not mat:
            with bpy.data.libraries.load(blend_path, link=True) as (data_from, data_to):
                if material_name in data_from.materials:
                    data_to.materials = [material_name]
            mat = bpy.data.materials.get(material_name)
            if not mat:
                self.report({'ERROR'}, f"Material {material_name} not found in {blend_path}")
                return {'CANCELLED'}

        for obj in context.selected_objects:
            if obj.type == 'MESH':
                if obj.data.materials:
                    obj.data.materials[0] = mat
                else:
                    obj.data.materials.append(mat)

        self.report({'INFO'}, f"Linked material '{material_name}' to selected objects")
        return {'FINISHED'}


# ---------- UI Lists -----------
class MATERIALBROWSER_UL_items(bpy.types.UIList):
    def draw_item(self, context, layout, data, item, icon, active_data, active_propname, index):
        pcoll = preview_collections.get("material_thumbs")
        icon_id = 0

        if pcoll and item.name in pcoll:
            icon_id = pcoll[item.name].icon_id

        in_scene = item.name in bpy.data.materials
        status_icon = 'CHECKMARK' if in_scene else 'IMPORT'

        if self.layout_type in {'DEFAULT', 'COMPACT'}:
            row = layout.row(align=True)

            if icon_id > 0:
                row.label(text="", icon_value=icon_id)
            elif pcoll:
                row.label(text="", icon='ERROR')
            else:
                row.label(text="", icon='QUESTION')

            row.label(text=item.name)
            row.label(text="", icon=status_icon)
            

# ---------- Main Panel ----------
class MATERIALBROWSER_PT_Panel(Panel):
    bl_label = "Material List"
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

        # box = layout.box()
        # col = box.column()
        # col.prop(scn, "material_browser_category", text="Category")
        # col.label(text=scn.material_browser_material_category_count)

        items = getattr(scn, "material_browser_filtered_items", None)
        index = getattr(scn, "material_browser_index", -1)
        active_item = items[index] if items and 0 <= index < len(items) else None

        if active_item:
            box = layout.box()
            col = box.column()

            pcoll = preview_collections.get("material_thumbs")

            row = col.row(align=True)
            if pcoll and active_item.name in pcoll:
                icon_id = pcoll[active_item.name].icon_id
                row.template_icon(icon_value=icon_id, scale=10.0)
            else:
                row.label(text="", icon='QUESTION')
                row.scale_y = 10.0
                row.alignment = 'CENTER'

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

        col.row().template_list(
            "MATERIALBROWSER_UL_items", "materials",
            scn, "material_browser_filtered_items",
            scn, "material_browser_index",
            rows=12
        )
