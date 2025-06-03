bl_info = {
    "name": "TMG Material Browser",
    "author": "Johnathan @ TnT Gamez LLC",
    "version": (1, 0, 0),
    "blender": (4, 4, 3),
    "location": "View3D > Sidebar > TMG",
    "description": "Material Browser and Preview Renderer tools",
    "category": "Material",
}

import bpy
import os
import bpy.utils.previews

from bpy.types import Panel, Operator, PropertyGroup, UIList
from bpy.props import (
    StringProperty, BoolProperty, IntProperty, CollectionProperty,
    PointerProperty, EnumProperty
)
from bpy.app.handlers import persistent

# Import your module components
from .material_list import (
    MaterialItem, MaterialCache,
    MATERIALBROWSER_UL_items, MATERIALBROWSER_PT_Panel,
    MATERIALBROWSER_OT_RefreshCache, MATERIALBROWSER_OT_AppendMaterial,
    MATERIALBROWSER_OT_LinkMaterial, MATERIALBROWSER_OT_SelectMaterial,
    update_material_browser_filter, update_change_file_path,
    update_material_browser_category, preview_collections,
    KEYWORD_CATEGORIES, load_previews_on_start,
)

from .preview_render import (
    MATERIALPREVIEW_UL_log_list,
    MATERIALPREVIEW_OT_start_render,
    MATERIALPREVIEW_PT_panel,
)

addon_dir = os.path.dirname(__file__)
# render_script_path = os.path.join(addon_dir, "preview_renderer.py")
render_scene_path = os.path.join(addon_dir, "render_previews.blend")

class LogLine(PropertyGroup):
    text: StringProperty()

class MaterialPreviewProps(PropertyGroup):
    blend_folder: StringProperty(
        name="Material Library Path",
        subtype='DIR_PATH',
        description="Path containing blend files with materials to parse to preview folders"
    )
    render_scene: StringProperty(
        name="Render Scene File",
        subtype='FILE_PATH',
        default=render_scene_path
    )
    is_rendering: BoolProperty(
        name="Is Rendering",
        default=False
    )
    overwrite_all_previews: BoolProperty(
        name="Overwrite All Previews",
        default=True,
        description="Overwrite all preview images, or skip already rendered images"
    )
    image_type: EnumProperty(
        name="Image Type",
        description="File format for saved previews",
        items=[
            ("PNG", "PNG", "Save as .png"),
            ("JPEG", "JPG", "Save as .jpg")
        ],
        default="PNG"
    )
    active_index: IntProperty(default=0)
    log_items: CollectionProperty(type=LogLine)

classes = (
    # Variables
    LogLine,
    MaterialPreviewProps,

    # Browser
    MaterialItem,
    MaterialCache,
    MATERIALBROWSER_UL_items,
    MATERIALBROWSER_PT_Panel,
    MATERIALBROWSER_OT_RefreshCache,
    MATERIALBROWSER_OT_AppendMaterial,
    MATERIALBROWSER_OT_LinkMaterial,
    MATERIALBROWSER_OT_SelectMaterial,

    # Renderer
    MATERIALPREVIEW_UL_log_list,
    MATERIALPREVIEW_OT_start_render,
    MATERIALPREVIEW_PT_panel,
)

def register():
    for cls in classes:
        bpy.utils.register_class(cls)

    # Browser Props
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

    bpy.types.Scene.material_browser_category = EnumProperty(
        name="Category",
        description="Filter by category",
        items=[("All", "All", "")] +
              [(cat, cat, "") for cat in sorted(KEYWORD_CATEGORIES.keys())] +
              [("Uncategorized", "Uncategorized", "")],
        default="All",
        update=update_material_browser_category
    )

    bpy.types.Scene.material_browser_material_count = StringProperty(
        name="Material Count",
        default="Materials: 0"
    )

    bpy.types.Scene.material_browser_material_category_count = StringProperty(
        name="Material Category Count",
        default="Materials: 0"
    )

    bpy.types.Scene.material_browser_items = CollectionProperty(type=MaterialItem)
    bpy.types.Scene.material_browser_filtered_items = CollectionProperty(type=MaterialItem)
    bpy.types.Scene.material_browser_index = IntProperty()
    bpy.types.Scene.material_cache = PointerProperty(type=MaterialCache)

    bpy.types.Scene.material_browser_selected_material = StringProperty(
        name="Selected Material"
    )

    bpy.types.Scene.previews_folder_path = StringProperty(
        name="Previews Folder",
        description="Path to preview images for materials",
        subtype='DIR_PATH',
        default=""
    )

    # Thumbnail previews
    preview_collections["material_thumbs"] = bpy.utils.previews.new()

    # Safe loading after .blend load
    if load_previews_on_start not in bpy.app.handlers.load_post:
        bpy.app.handlers.load_post.append(load_previews_on_start)
    
    bpy.types.Scene.material_preview_props = PointerProperty(type=MaterialPreviewProps)
    bpy.types.Scene.material_preview_log_text = bpy.props.PointerProperty(type=bpy.types.Text)


def unregister():
    # Remove handler
    if load_previews_on_start in bpy.app.handlers.load_post:
        bpy.app.handlers.load_post.remove(load_previews_on_start)

    # Free thumbnails
    pcoll = preview_collections.get("material_thumbs")
    if pcoll:
        bpy.utils.previews.remove(pcoll)
        preview_collections.clear()

    # Remove properties
    props = [
        "material_preview_props", "material_preview_log_text",
        "material_browser_path", "material_browser_filter",
        "enable_displacement", "material_browser_category",
        "material_browser_material_count", "material_browser_material_category_count",
        "material_browser_items", "material_browser_filtered_items",
        "material_browser_index", "material_cache",
        "material_browser_selected_material", "previews_folder_path"
    ]
    for prop in props:
        if hasattr(bpy.types.Scene, prop):
            delattr(bpy.types.Scene, prop)

    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)


if __name__ == "__main__":
    register()
