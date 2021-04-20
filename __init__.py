# ExportHelper is a helper class, defines filename and
# invoke() function which calls the file selector.
from bpy_extras.io_utils import ExportHelper
from bpy.props import StringProperty, BoolProperty, EnumProperty, FloatProperty, IntProperty
from bpy.types import Operator


def reload_modules():
    print("reloading shits...")
    import importlib
    from . import builder
    importlib.reload(builder)
    from . import exporter
    importlib.reload(exporter)


if "bpy" in locals():
    reload_modules()
else:
    import bpy
    from . import builder
    from . import exporter

# the exporter
bl_info = {
    "name": "Bowie Large Mesh Format Exporter",
    "author": "Bowie",
    "blender": (2, 83, 0),
    "version": (0, 0, 1),
    "location": "File > Import-Export",
    "description": "Export Large Mesh File (LMF) containing mesh data and its kdTree",
    "category": "Import-Export"
}

class LMFExporter(Operator, ExportHelper):
    """Export to Large Mesh Format (LMF)"""
    bl_idname = "lmf_exporter.export"  # important since its how bpy.ops.import_test.some_data is constructed
    bl_label = "EXPORT LARGE MESH!"

    # ExportHelper mixin class uses this
    filename_ext = ".lmf"

    filter_glob: StringProperty(
        default="*.lmf",
        options={'HIDDEN'},
        maxlen=255,  # Max internal buffer length, longer would be clamped.
    )

    # some default vertex format
    vertex_has_pos: BoolProperty(name="Position", description="XYZ vertex data", default=(exporter.VTF_DEFAULT & exporter.VTF_POS)!=0)
    vertex_has_normal: BoolProperty(name="Normal", description="XYZ normal data", default=(exporter.VTF_DEFAULT & exporter.VTF_NORMAL)!=0)
    vertex_has_uv0: BoolProperty(name="UV0", description="primary (first) UV", default=(exporter.VTF_DEFAULT & exporter.VTF_UV0)!=0)
    vertex_has_tangents: BoolProperty(name="Tangent+Bitangent", description="tangent+bitangent 2x(XYZ)", default=(exporter.VTF_DEFAULT & exporter.VTF_TANGENT_BITANGENT)!=0)
    vertex_has_uv1: BoolProperty(name="UV1", description="secondary UV", default=(exporter.VTF_DEFAULT & exporter.VTF_UV1)!=0)
    vertex_has_color: BoolProperty(name="Color", description="(RGB) vertex color", default=(exporter.VTF_DEFAULT & exporter.VTF_COLOR)!=0)
    vertex_has_bone: BoolProperty(name="Bone Weights+IDs", description="Bone Weights + ID for skeletal animation", default=(exporter.VTF_DEFAULT & exporter.VTF_BONE_DATA)!=0)
    vertex_has_tween: BoolProperty(name="Tween", description="XYZ vertex animation data", default=(exporter.VTF_DEFAULT & exporter.VTF_TWEEN)!=0)

    max_depth: IntProperty(name="Max Tree Depth", description="Maximum depth of the KD Tree", default=10, min=4, max=32)
    criterion: EnumProperty(items=(
        ('polycount', 'polycount', 'Triangle Count'),
        ('volume', 'volume', 'AABB Volume'),
        ('area', 'area', 'AABB Surface Area'),
        ('extent', 'extent', 'AABB Longest extent'),
    ), name="Split Criterion", description="Split node based on what?", default="polycount")
    threshold: FloatProperty(name="Criterion Threshold", description="Maximum criterion value before splitting", default=1000, min=1)

    write_mode: EnumProperty(
        items=(
            ('ascii', "ASCII", "Human readable format"),
            ('binary', "Binary", "Compact memory size")
        ),
        name="File Type",
        description="What kind of file output to write",
        default='ascii'
    )

    def execute(self, context):
        # build a vertex format before executing
        format = 0
        if self.vertex_has_pos: format |= exporter.VTF_POS
        if self.vertex_has_normal: format |= exporter.VTF_NORMAL
        if self.vertex_has_uv0: format |= exporter.VTF_UV0
        if self.vertex_has_tangents: format |= exporter.VTF_TANGENT_BITANGENT
        if self.vertex_has_uv1: format |= exporter.VTF_UV1
        if self.vertex_has_color: format |= exporter.VTF_COLOR
        if self.vertex_has_bone: format |= exporter.VTF_BONE_DATA
        if self.vertex_has_tween: format |= exporter.VTF_TWEEN


        # return do_write(context, self.filepath, format, self, self.write_mode)
        return exporter.do_write_tree(context, self.filepath, format, self, self.max_depth, self.criterion, self.threshold, self.write_mode)


# Only needed if you want to add into a dynamic menu
def menu_func_export(self, context):
    self.layout.operator(LMFExporter.bl_idname, text="LMF Export")


def register():
    bpy.utils.register_class(LMFExporter)
    bpy.types.TOPBAR_MT_file_export.append(menu_func_export)
    print("REGISTER_LMF")
    reload_modules()


def unregister():
    bpy.utils.unregister_class(LMFExporter)
    bpy.types.TOPBAR_MT_file_export.remove(menu_func_export)
    print("UNREGISTER_LMF")

if __name__ == "__main__":
    register()

    # test call
    bpy.ops.lmf_exporter.export('INVOKE_DEFAULT')