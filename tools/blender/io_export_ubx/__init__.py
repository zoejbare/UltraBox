#
# Copyright (c) 2023, Zoe J. Bare
#
# Permission is hereby granted, free of charge, to any person obtaining a copy of this software and associated
# documentation files (the "Software"), to deal in the Software without restriction, including without limitation
# the rights to use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of the Software,
# and to permit persons to whom the Software is furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all copies or substantial portions
# of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED
# TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL
# THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF
# CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER
# DEALINGS IN THE SOFTWARE.
#

bl_info = {
	"name": "UltraBox Model Exporter",
	"author": "Zoe Bare",
	"version": (1, 0, 0),
	"blender": (3, 6, 0),
	"location": "File > Import-Export",
	"description": "Model exporter for the UltraBox framework",
	"category": "Import-Export",
}

###################################################################################################

if "bpy" in locals():
	import importlib
	if "export_ubx" in locals():
		importlib.reload(export_ubx)

###################################################################################################

import bpy
import bmesh

from bpy.props import BoolProperty, EnumProperty, FloatProperty, StringProperty
from bpy.types import Operator, TOPBAR_MT_file_export
from bpy.utils import register_class, unregister_class
from bpy_extras.io_utils import ExportHelper, axis_conversion

###################################################################################################

class UbxExporter(Operator, ExportHelper):
	"""Write a UBX file"""
	bl_idname = "export_scene.ubx"
	bl_label = "Export UBX"

	filename_ext = ".ubx"

	filter_glob: StringProperty(
		default = f"*{filename_ext}",
		options = {"HIDDEN"},
		maxlen = 255,
	)

	### Configurable export properties ###

	forwardAxis: EnumProperty(
		name = "Forward Axis",
		description = "Blender axis mapped to an object's forward direction",
		items = (
			("X", "X axis", ""),
			("Y", "Y axis", ""),
			("Z", "Z axis", ""),
			("-X", "-X axis", ""),
			("-Y", "-Y axis", ""),
			("-Z", "-Z axis", ""),
		),
		default = "Y",
	)
	upAxis: EnumProperty(
		name = "Up Axis",
		description = "Blender axis mapped to an object's up direction",
		items = (
			("X", "X axis", ""),
			("Y", "Y axis", ""),
			("Z", "Z axis", ""),
			("-X", "-X axis", ""),
			("-Y", "-Y axis", ""),
			("-Z", "-Z axis", ""),
		),
		default = "Z",
	)
	useSelection: BoolProperty(
		name = "Selected Objects",
		description = "Export selected and visible objects only",
		default = False,
	)
	useVisible: BoolProperty(
		name = "Visible Objects",
		description = "Export visible objects only",
		default = False,
	)
	useActiveCollection: BoolProperty(
		name = "Active Collection",
		description = "Export only objects from the active collection (and its children)",
		default = False,
	)
	useLocalClusters: BoolProperty(
		name = "Local Clusters",
		description = "Do not allow non-adjacent triangles in exported mesh clusters",
		default = False,
	)
	precisionScale: FloatProperty(
		name = "Scale",
		description= "Upscale to increase precision of vertex data at runtime (large values may produce visual artifacts)",
		min = 1.0, max = 1000.0,
		soft_min = 1.0, soft_max = 1000.0,
		default = 100.0,
	)

	def _findObjects(self):
		# Get the list of object from either the active collection for the whole scene.
		objects = bpy.context.collection.objects if self.useActiveCollection else bpy.context.scene.objects

		# Filter the objects by meshes with vertex data.
		objects = [x for x in objects if x.type == "MESH" if x.data.vertices]

		# Filter the mesh objects by which are visible.
		if self.useSelection or self.useVisible:
			objects = [x for x in objects if x.visible_get()]

		# Filter the mesh objects by which are currently selected.
		if self.useSelection:
			objects = [x for x in objects if x.select_get()]

		return objects

	def execute(self, _):
		if self.forwardAxis == self.upAxis:
			self.report({"ERROR"}, "Forward axis and up axis are the same")
			return {"CANCELLED"}

		objects = self._findObjects()
		if not objects:
			self.report({"ERROR"}, "No valid mesh objects to export")
			return {"CANCELLED"}

		from . import export_ubx
		export_ubx.save(
			self.filepath,
			objects,
			self.precisionScale,
			self.useLocalClusters,
			axis_conversion(to_forward = self.forwardAxis, to_up = self.upAxis).to_4x4()
		)

		return {"FINISHED"}

###################################################################################################

class MenuFunc(object):
	@staticmethod
	def export(self, ctx):
		self.layout.operator(UbxExporter.bl_idname, text=f"UltraBox ({UbxExporter.filename_ext})")

###################################################################################################

def register():
	register_class(UbxExporter)
	TOPBAR_MT_file_export.append(MenuFunc.export)


def unregister():
	unregister_class(UbxExporter)
	TOPBAR_MT_file_export.remove(MenuFunc.export)

###################################################################################################


if __name__ == "__main__":
	register()
