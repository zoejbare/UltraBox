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

import bmesh
import enum
import json
import math
import mathutils

###################################################################################################

class UbxMeshVertex(object):
	def __init__(self, position, normal, texCoord, color):
		self._position = mathutils.Vector(position[:]).freeze() # type: mathutils.Vector
		self._normal = mathutils.Vector(normal[:]).freeze() # type: mathutils.Vector
		self._texCoord = mathutils.Vector(texCoord[:]).freeze() # type: mathutils.Vector
		self._color = mathutils.Vector(color[:]).freeze() # type: mathutils.Vector

		self._hash = hash(self._position) \
					^ hash(self._normal) \
					^ hash(self._texCoord) \
					^ hash(self._color)

	def __eq__(self, other):
		return self._hash == hash(other)

	def __ne__(self, other):
		return not self.__eq__(other)

	def __hash__(self):
		return self._hash

	def transform(self, worldMatrix, rotationMatrix):
		self._position = worldMatrix @ self._position
		self._normal = rotationMatrix @ self._normal

	@property
	def position(self):
		return self._position

	@property
	def normal(self):
		return self._normal

	@property
	def texCoord(self):
		return self._texCoord

	@property
	def color(self):
		return self._color

###################################################################################################

class UbxMeshFace(object):
	def __init__(self, bmeshFace, bmeshLayers):
		vertices = set()
		uvLayer = bmeshLayers.uv.active
		colorLayer = bmeshLayers.color.active

		# Create objects to represent each vertex in the face, adding them to the local set.
		for loop in bmeshFace.loops:
			vertex = UbxMeshVertex(
				loop.vert.co,
				loop.vert.normal,
				loop[uvLayer].uv,
				loop[colorLayer])
			vertices.add(vertex)

		self._vertices = frozenset(vertices) # type: frozenset[UbxMeshVertex]
		self._index = bmeshFace.index # type: int

	def __hash__(self):
		return hash(self._index)

	@property
	def vertices(self):
		return self._vertices

	@property
	def sortedVertices(self):
		return sorted(
			self._vertices,
			key=lambda v: (v.position.x * v.position.x) + (v.position.y * v.position.y) + (v.position.z * v.position.z)
		)

	@property
	def index(self):
		return self._index

###################################################################################################

class UbxMeshCluster(object):
	def __init__(self, worldMatrix, rotationMatrix, faces):
		self._vertices = [] # type: list[UbxMeshVertex]
		self._indices = [] # type: list[int]

		for face in sorted(faces, key=lambda f: f.index):
			for vertex in face.sortedVertices:
				try:
					# This vertex data already exists; all we need to do is update the
					# index array with the cluster local index for this vertex.
					localIndex = self._vertices.index(vertex)

				except:
					# This vertex does not exist in the array yet; insert it at the end.
					localIndex = len(self._vertices)

					self._vertices.append(vertex)

				self._indices.append(localIndex)

		for vertex in self._vertices:
			vertex.transform(worldMatrix, rotationMatrix)

	@property
	def vertices(self):
		return list(self._vertices)

	@property
	def indices(self):
		return list(self._indices)

###################################################################################################

class UbxMesh(object):
	def __init__(self, name):
		self._name = name # type: str
		self._clusters = [] # type: list[UbxMeshCluster]

	def addCluster(self, cluster):
		if cluster:
			self._clusters.append(cluster)

	def isValid(self):
		return len(self._clusters) > 0

	@property
	def name(self):
		return self._name

	@property
	def clusters(self):
		return list(self._clusters)

###################################################################################################

def save(outputPath, objects, precisionScale, useLocalClusters, globalMatrix):
	meshes = [] # type: list[UbxMesh]

	for obj in objects:
		bm = bmesh.new()
		bm.from_mesh(obj.data)

		# UBX requires all meshes to be triangulated.
		bmesh.ops.triangulate(bm, faces = bm.faces[:])

		# Create a new UV layer if one does not exist.
		if not bm.loops.layers.uv.active:
			bm.loops.layers.uv.new()

		# Create a new color layer if one does not exist.
		if not bm.loops.layers.color.active:
			bm.loops.layers.color.new()

		worldMatrix = globalMatrix @ obj.matrix_world
		rotationMatrix = globalMatrix.to_3x3() @ obj.rotation_quaternion.to_matrix()

		openList = {
			face.index: UbxMeshFace(face, bm.loops.layers)
			for face in bm.faces[:]
		} # type: dict[int, UbxMeshFace]
		closedList = set() # type: set[UbxMeshFace]
		uniqueVertices = set() # type: set[UbxMeshVertex]

		# The bmesh object is no longer needed now that we've extracted all the face data into the open list.
		bm.free()

		mesh = UbxMesh(obj.name)

		def closeFace(_face):
			closedList.add(_face)
			uniqueVertices.update(_face.vertices)

			del openList[_face.index]

		def flushCluster():
			if closedList:
				# Create a new cluster object and add it to the mesh.
				mesh.addCluster(UbxMeshCluster(worldMatrix, rotationMatrix, closedList))

				# Clear the closed list so we can begin building the next cluster.
				closedList.clear()
				uniqueVertices.clear()

		# Build the list of mesh clusters.
		while openList:
			cachedFace = None
			cachedScore = 0
			duplicateFaces = set()

			if not closedList:
				# The current cluster is empty; close the first face in the open list to get it started.
				closeFace(list(openList.values())[0])

			for _, openFace in openList.items():
				# We accept only the faces with the best fit, meaning the most adjacent
				# faces will be selected for the cluster. This is very slow, but it should
				# guarantee that clusters will have the tighted packing possible.
				score = 0

				for closedFace in closedList:
					commonVertices = openFace.vertices & closedFace.vertices

					if len(commonVertices) == 3:
						# Duplicate face; no need to consider it at all.
						duplicateFaces.add(openFace)
						score = -1
						break

					score += len(commonVertices)

				if score > cachedScore:
					# This open face is the best fit (so far) in the current cluster.
					cachedFace = openFace
					cachedScore = score

			# Remove any duplicate faces that were detected during the adjacent face search.
			for face in duplicateFaces:
				del openList[face.index]

			if not useLocalClusters and not cachedFace:
				# If an adjacent face could not be found and we're not forcing local clusters,
				# we can add any face to the current cluster.
				cachedFace = list(openList.values())[0]

			if cachedFace:
				# UBX mesh clusters have a maximum vertex buffer size of 32. If we're going to
				# exceed that limit, we have no choice but to flush the current cluster.
				if len(uniqueVertices) + len(cachedFace.vertices - uniqueVertices) > 32:
					flushCluster()

				closeFace(cachedFace)

			else:
				# There are no more faces we are able to add to this cluster;
				# flush it to the mesh so we can start working on the next one.
				flushCluster()

		# There is nothing left in the open list, making the current closed list the final cluster for the mesh.
		flushCluster()

		# Make sure the mesh is valid before continuing.
		assert mesh.isValid(), "Somehow ended up with a mesh that does not contain any clusters; this should never happen"
		meshes.append(mesh)

	assert len(meshes) > 0, "No meshes to export; this should never happen"

	# Build a JSON-compatible dictionary of all the processed mesh data.
	jsonMeshes = []
	for mesh in meshes:
		jsonClusters = []
		for cluster in mesh.clusters:
			jsonVertices = []
			for vertex in cluster.vertices:
				jsonVertices.append({
					"x": vertex.position.x,
					"y": vertex.position.y,
					"z": vertex.position.z,
					"nx": vertex.normal.x,
					"ny": vertex.normal.y,
					"nz": vertex.normal.z,
					"u": vertex.texCoord.x,
					"v": vertex.texCoord.y,
					"r": vertex.color.x,
					"g": vertex.color.y,
					"b": vertex.color.z,
					"a": vertex.color.w,
				})

			jsonClusters.append({
				"vertices": jsonVertices,
				"indices": cluster.indices,
			})

		jsonMeshes.append({
			"name": mesh.name,
			"clusters": jsonClusters,
		})

	jsonRoot = {
		"precision_scale": precisionScale,
		"meshes": jsonMeshes,
	}

	# Write the UBX file to disk.
	with open(outputPath, "w") as f:
		json.dump(jsonRoot, f, indent=4, sort_keys=True)

###################################################################################################
