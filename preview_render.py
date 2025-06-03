import bpy
import os
import subprocess
import threading
import queue
import multiprocessing

from bpy.app.handlers import persistent
from bpy.types import Panel, Operator, PropertyGroup, UIList
from bpy.props import StringProperty, BoolProperty, PointerProperty, CollectionProperty, IntProperty,EnumProperty


addon_dir = os.path.dirname(__file__)
# render_script_path = os.path.join(addon_dir, "preview_renderer.py")
render_scene_path = os.path.join(addon_dir, "render_previews.blend")

log_queue = queue.Queue()

def redraw_ui():
    try:
        for window in bpy.context.window_manager.windows:
            for area in window.screen.areas:
                if area.type in {'VIEW_3D', 'PROPERTIES', 'OUTLINER', 'TEXT_EDITOR'}:
                    area.tag_redraw()
    except Exception:
        pass

def show_popup(message, title="Notice"):
    def draw(self, context):
        self.layout.label(text=message)
    bpy.context.window_manager.popup_menu(draw, title=title, icon='INFO')
    redraw_ui()

def log_timer():
    updated = False
    props = bpy.context.scene.material_preview_props
    while not log_queue.empty():
        msg = log_queue.get_nowait()
        props.log += msg
        updated = True
    if updated:
        for area in bpy.context.screen.areas:
            if area.type == 'VIEW_3D':
                area.tag_redraw()
    return 0.5

def safe_save_blend_file():
    if bpy.data.filepath:
        bpy.ops.wm.save_mainfile()
        return True
    else:
        bpy.ops.wm.save_as_mainfile('INVOKE_DEFAULT')
        return False

def append_log_line(text):
    props = bpy.context.scene.material_preview_props
    log_items = bpy.context.scene.material_preview_props.log_items
    item = log_items.add()
    item.text = text
    props.active_index = len(log_items) - 1
    redraw_ui()

def clear_log():
    props = bpy.context.scene.material_preview_props
    props.log_items.clear()
    props.active_index = -1
    redraw_ui()

class LogLine(PropertyGroup):
    text: StringProperty()

class MATERIALPREVIEW_UL_log_list(UIList):
    def draw_item(self, context, layout, data, item, icon, active_data, active_propname, index):
        if self.layout_type in {'DEFAULT', 'COMPACT'}:
            layout.label(text=item.text)
        elif self.layout_type == 'GRID':
            layout.label(text="")


class MATERIALPREVIEW_OT_start_render(Operator):
    bl_idname = "material_preview.start_render"
    bl_label = "Start Material Previews Render"

    def execute(self, context):
        clear_log()
        # show_popup("Starting render process")
        append_log_line("Starting render process")
        props = context.scene.material_preview_props

        if props.is_rendering:
            self.report({'WARNING'}, "Render already in progress!")
            return {'CANCELLED'}

        blend_folder = bpy.path.abspath(props.blend_folder)
        render_scene_path = bpy.path.abspath(props.render_scene)

        if not os.path.isdir(blend_folder):
            self.report({'ERROR'}, "Invalid blend folder path")
            return {'CANCELLED'}

        if not os.path.isfile(render_scene_path):
            self.report({'ERROR'}, "Invalid render scene file")
            return {'CANCELLED'}

        # if not safe_save_blend_file():
        #     self.report({'ERROR'}, "Please save the current file before starting the render process.")
        #     return {'CANCELLED'}

        props.is_rendering = True

        threading.Thread(
            target=self.launch_render_processes,
            args=(blend_folder, render_scene_path),
            daemon=True
        ).start()

        bpy.app.timers.register(log_timer)

        return {'FINISHED'}

    def launch_render_processes(self, blend_folder, render_scene_path):
        props = bpy.context.scene.material_preview_props

        overwrite_all_previews = props.overwrite_all_previews
        image_format = props.image_type.lower()  # 'png' or 'jpeg'
        img_ext = "jpg" if image_format == "jpeg" else "png"

        blend_files = [f for f in os.listdir(blend_folder) if f.endswith(".blend")]
        num_cores = multiprocessing.cpu_count()
        chunk_size = max(1, len(blend_files) // num_cores)

        def chunk_list(lst, n):
            for i in range(0, len(lst), n):
                yield lst[i:i + n]

        chunks = list(chunk_list(blend_files, chunk_size))
        blender_executable = bpy.app.binary_path
        addon_dir = os.path.dirname(__file__)
        render_script_path = os.path.join(addon_dir, "preview_renderer.py")

        for i, chunk in enumerate(chunks):
            args = [
                blender_executable,
                "--background",
                render_scene_path,
                "--python",
                render_script_path,
                "--",
                img_ext,
                str(overwrite_all_previews).lower(),
                blend_folder,
            ] + chunk

            append_log_line(f"Launching process {i+1} with {len(chunk)} blend files\n")

            proc = subprocess.Popen(args, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)

            for line in proc.stdout:
                append_log_line(line)

            proc.wait()
            append_log_line(f"Process {i+1} finished\n")

        def finish_render():
            props.is_rendering = False
            append_log_line("All rendering processes completed!\n")
            return None

        bpy.app.timers.register(finish_render)


class MATERIALPREVIEW_PT_panel(Panel):
    bl_label = "Preview Renderer"
    bl_idname = "MATERIALPREVIEW_PT_panel"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = 'TMG'

    def draw(self, context):
        layout = self.layout
        props = context.scene.material_preview_props

        layout.prop(props, "blend_folder")
        layout.prop(props, "render_scene")

        box = layout.box()
        col = box.column()
        row = col.row()
        row.prop(props, "overwrite_all_previews")
        row.prop(props, "image_type")

        row = layout.row()
        row.enabled = not props.is_rendering
        row.operator("material_preview.start_render")

        box = layout.box()
        col = box.column()
        col.label(text="Log:")
        col.template_list("MATERIALPREVIEW_UL_log_list", "", props, "log_items", props, "active_index", rows=10)
