import bpy
import bpy_types
import sys, array
from . import builder

"""
Author: Bowie
This exporter defines a pretty basic export for
OGL compatible vertex buffer

Vertex Format (using bit position to toggle availability):
(1 << 0) : POSITION
(1 << 1) : NORMAL
(1 << 2) : UV0
(1 << 3) : TANGENT + BITANGENT
(1 << 4) : UV1 (NOT IMPLEMENTED YET)
(1 << 5) : COLOR (NOT IMPLEMENTED YET)
(1 << 6) : BONE_WEIGHTS + IDS (NOT IMPLEMENTED YET)
(1 << 7) : TWEEN (NOT IMPLEMENTED YET)
"""
VTF_POS     = (1<<0)
VTF_NORMAL  = (1<<1)
VTF_UV0     = (1<<2)
VTF_TANGENT_BITANGENT      = (1<<3)
VTF_UV1     = (1<<4)
VTF_COLOR   = (1<<5)
VTF_BONE_DATA   = (1<<6)
VTF_TWEEN   = (1<<7)

VTF_DEFAULT = VTF_POS | VTF_NORMAL | VTF_UV0


# helper to make binary buffer
def make_buffer(format, data):
    buf = array.array(format, data)
    if sys.byteorder != 'little':
        buf.byteswap()
    return buf

# compute bytes per vertex
def bytesPerVertex(vtx_format):
    totalSize = 0
    if vtx_format & VTF_POS: totalSize += 12
    if vtx_format & VTF_NORMAL: totalSize += 12
    if vtx_format & VTF_UV0: totalSize += 8
    if vtx_format & VTF_TANGENT_BITANGENT: totalSize += 24
    if vtx_format & VTF_UV1: totalSize += 8
    if vtx_format & VTF_COLOR: totalSize += 12
    if vtx_format & VTF_BONE_DATA: totalSize += 20

    return totalSize
##

def extract_buffers(mesh, format):
    m = mesh #bpy.data.meshes.new("Shit")

    # compute tangent first?
    m.calc_tangents()
    # loop data + vertices
    loops = m.loops
    verts = m.vertices
    uvs = m.uv_layers

    # check format
    if format & VTF_UV0:
        if len(uvs) < 1:
            raise Exception("Requested uv0, but no uv map at all!")

    if format & VTF_UV1:
        if len(uvs) < 2:
            raise Exception("Requested uv1, but no second uv layer!")

    # unique vertices
    u_verts = []

    # indices per materials
    indices = []
    for mat in m.materials:
        indices.append([])

    # loop over polys (already triangulated)
    for p in m.polygons:
        # our triangle index
        tri = []
        for l_id in p.loop_indices:
            l = loops[l_id]
            # compute vertex data
            u_vert = []

            if format & VTF_POS:
                v = verts[l.vertex_index].co
                u_vert.append([v.x, v.z, -v.y])

            if format & VTF_NORMAL:
                n = l.normal
                u_vert.append([n.x, n.z, -n.y])

            if format & VTF_UV0:
                uv = uvs[0].data[l_id].uv
                u_vert.append([uv.x, uv.y])

            if format & VTF_TANGENT_BITANGENT:
                tgt = l.tangent
                btg = l.bitangent
                u_vert.append([tgt.x, tgt.z, -tgt.y, btg.x, btg.z, -btg.y])
            
            if format & VTF_UV1:
                uv = uvs[1].data[l_id].uv
                u_vert.append([uv.x, uv.y])

            # get its index
            if u_vert not in u_verts:
                u_verts.append(u_vert)
            
            v_idx = u_verts.index(u_vert)
            tri.append(v_idx)
        # add to appropriate mat_id?
        indices[p.material_index].append(tri)
    
    # return tuple of vb, ib
    return (u_verts, indices)

# return tuple of vertexbuffer, indexbuffer
def write_node_ascii(file, node, mesh_id):
    parent_id = -1
    if node.parent:
        parent_id = node.parent._id
    bmin = (
        min(node.aabb.min[0], node.aabb.max[0]),
        min(node.aabb.min[2], node.aabb.max[2]),
        min(-node.aabb.min[1], -node.aabb.max[1]),
    )

    bmax = (
        max(node.aabb.min[0], node.aabb.max[0]),
        max(node.aabb.min[2], node.aabb.max[2]),
        max(-node.aabb.min[1], -node.aabb.max[1]),
    )
    txt = "node[%d]: parent(%d), aabb(%.2f %.2f %.2f | %.2f %.2f %.2f) mesh_id(%d)\n" % (
        node._id, parent_id, bmin[0], bmin[1], bmin[2],
        bmax[0], bmax[1], bmax[2], mesh_id
    )
    file.write(txt)

def write_ascii(filepath, tree, mesh, me, format=VTF_DEFAULT):
    f = open(filepath, "w")

    goodNodes = builder.collectGoodLeaves(tree)

    me.report({'INFO'}, "writing headers...")

    f.write("name: %s\n" % (mesh.name))
    f.write("node_count: %d\n" % (builder.nodeCount(tree)))
    f.write("mesh_objects: %d\n" % (len(goodNodes)))
    f.write("submesh_per_object: %d\n" % (len(mesh.materials)))

    # write node data
    queue = [tree]

    while len(queue):
        n = queue.pop(0)
        # do something
        mesh_id = -1
        if n in goodNodes:
            mesh_id = goodNodes.index(n)

        write_node_ascii(f, n, mesh_id)

        if not n.isLeaf():
            queue.append(n.children[0])
            queue.append(n.children[1])

    # write mesh data
    for (id, n) in enumerate(goodNodes):
        mo = builder.createSplitMesh(n, mesh)
        # do something
        (vb, ib) = extract_buffers(mo, format)
        f.write("mesh[%d]: name(%s) vertex_count(%d) unique_verts(%d) poly_count(%d)\n" % (id, mo.name, len(mo.vertices), len(vb), len(mo.polygons)))

        # write vb?
        for (id, v) in enumerate(vb):
            str = "v[%d]:" % id
            # depending on format
            c = 0
            if format & VTF_POS:
                d = v[c]
                str += " pos(%.2f %.2f %.2f)" % (d[0], d[1], d[2])
                c+=1
            if format & VTF_NORMAL:
                d = v[c]
                str += " norm(%.2f %.2f %.2f)" % (d[0], d[1], d[2])
                c+=1
            if format & VTF_UV0:
                d = v[c]
                str += " uv0(%.2f %.2f)" % (d[0], d[1])
                c+=1
            if format & VTF_TANGENT_BITANGENT:
                d = v[c]
                str += " tgt(%.2f %.2f %.2f | %.2f %.2f %.2f)" % (d[0], d[1], d[2], d[3], d[4], d[5])
                c+=1
            if format & VTF_UV1:
                d = v[c]
                str += " uv1(%.2f %.2f)" % (d[0], d[1])
                c+=1
            str += "\n"
            f.write(str)
        
        # write ib
        for (id, ids) in enumerate(ib):
            f.write("submesh[%d]: tris(%d)\n" % (id, len(ids)))
            # write all of em
            for (t_id, t) in enumerate(ids):
                str = "t[%d]:" % t_id
                for v_idx in t:
                    str += " %d" % v_idx
                str += "\n"
                f.write(str)
        # discard
        builder.deleteMeshObject(mo)
    
    # close
    f.close()


# write the tree, but in binary file
# 1b: vertex_format
# 1b: bytes_per_vertex
# 2b: node_count
# 2b: mesh_obj_count
# 2b: material_count (submeshes per mesh)
# 32b: object_name
# [node_count x 36b](nodes), which has: 
# {
#  - 4b: id
#  - 4b: parent_id (-1 if no parent)
#  - 24b: 6 float (aabb min - max)
#  - 4b: mesh_object_id (-1 if no mesh_object)
# }
# [mesh_obj_count x (4b + material_count x 4b + bytes_per_vertex x vertex_count + triangle_count x 6b)](meshes), which has:
# {
#  - 4b: mesh_data_block_size (how many bytes until the end of this mesh, after this 4b here)
#  - 2b: vertex_count
#  - 2b: triangle_count
#  - [material_count x 4b](submesh_data)
#  - {
#     - 2b: start_idx
#     - 2b: num_elems -> triangle_count x 3
#  - }
#  - { vertex_buffers }
#  - [triangle_count x 3 x 2b]{ index_buffers }
# }
def write_binary(filepath, tree, mesh, me, format=VTF_DEFAULT):
    print("BINARY_WRITE: %s" % filepath)

    f = open(filepath, "wb")

    # collect good leaves
    goodLeaves = builder.collectGoodLeaves(tree)

    # write header
    wb_header(f, format, bytesPerVertex(format), builder.nodeCount(tree), len(goodLeaves), len(mesh.materials), mesh.name)

    # write node data
    queue = [tree]
    while len(queue):
        n = queue.pop(0)
        mesh_id = -1
        if n in goodLeaves:
            mesh_id = goodLeaves.index(n)

        wb_node(f, n, mesh_id)

        if not n.isLeaf():
            queue.append(n.children[0])
            queue.append(n.children[1])

    # write mesh
    for n in goodLeaves:
        mo = builder.createSplitMesh(n, mesh)

        (vb, ib) = extract_buffers(mo, format)
        wb_mesh_data(f, mo, format)

        builder.deleteMeshObject(mo)

    f.close()

# 1b: vertex_format
# 1b: bytes_per_vertex
# 2b: node_count
# 2b: mesh_obj_count
# 2b: material_count (submeshes per mesh)
# 32b: object_name
def wb_header(file, format, bpv, node_count, mesh_count, submesh_count, name):
    f = file
    f.write(make_buffer('B', [format, bpv]))
    f.write(make_buffer('H', [node_count, mesh_count, submesh_count]))
    b = bytearray(name, 'utf-8')
    pb = b.ljust(32, b'\0')
    f.write(pb)

# [node_count x 36b](nodes), which has: 
# {
#  - 4b: id
#  - 4b: parent_id (-1 if no parent)
#  - 24b: 6 float (aabb min - max)
#  - 4b: mesh_object_id (-1 if no mesh_object)
# }
def wb_node(file, node, mesh_id=1):
    f = file
    parent_id = -1
    if node.parent:
        parent_id = node.parent._id
    
    f.write(make_buffer('l', [node._id, parent_id]))
    # recompute bbox (rotation)
    bmin = (
        min(node.aabb.min[0], node.aabb.max[0]),
        min(node.aabb.min[2], node.aabb.max[2]),
        min(-node.aabb.min[1], -node.aabb.max[1]),
    )

    bmax = (
        max(node.aabb.min[0], node.aabb.max[0]),
        max(node.aabb.min[2], node.aabb.max[2]),
        max(-node.aabb.min[1], -node.aabb.max[1]),
    )
    f.write(make_buffer('f', [bmin[0], bmin[1], bmin[2], bmax[0], bmax[1], bmax[2]]))
    f.write(make_buffer('l', [mesh_id]))

# write mesh data
# [mesh_obj_count x (4b + material_count x 4b + bytes_per_vertex x vertex_count + triangle_count x 6b)](meshes), which has:
# {
#  - 4b: mesh_data_block_size (how many bytes until the end of this mesh, after this 4b here)
#  - 2b: vertex_count
#  - 2b: triangle_count
#  - [material_count x 4b](submesh_data)
#  - {
#     - 2b: start_idx
#     - 2b: num_elems -> triangle_count x 3
#  - }
#  - { vertex_buffers }
#  - [triangle_count x 3 x 2b]{ index_buffers }
# }
def wb_mesh_data(file, mesh, format):
    f = file
    (vb, ib) = extract_buffers(mesh, format)
    vsize = bytesPerVertex(format)
    vcount = len(vb)
    pcount = len(mesh.polygons)
    smcount = len(mesh.materials)
    block_size = 4 + 4 + smcount * 4 + vcount * vsize + pcount * 6

    # write mesh header
    f.write(make_buffer('L', [block_size]))
    f.write(make_buffer('H', [vcount, pcount]))
    # write start and end?
    offset = 0
    for ids in ib:
        start = offset
        elem_count = len(ids) * 3
        f.write(make_buffer('H', [start, elem_count]))
        offset += elem_count * 2
    # write vbuffer?
    for v in vb:
        d = 0
        if format & VTF_POS:
            data = v[d]
            f.write(make_buffer('f', data))
            d+=1
        if format & VTF_NORMAL:
            data = v[d]
            f.write(make_buffer('f', data))
            d+=1
        if format & VTF_UV0:
            data = v[d]
            f.write(make_buffer('f', data))
            d+=1
        if format & VTF_TANGENT_BITANGENT:
            data = v[d]
            f.write(make_buffer('f', data))
            d+=1
        if format & VTF_UV1:
            data = v[d]
            f.write(make_buffer('f', data))
            d+=1
    # write id buffer
    for ids in ib:
        for t in ids:
            f.write(make_buffer('H', t))



def do_write_tree(context, filepath, format, me, max_depth, criterion, max_threshold, write_mode):
    print("Should have written the tree in format(%d), max_depth(%d), max_%s(%.2f) in %s" % (
        format, max_depth, criterion, max_threshold, write_mode
    ))
    
    # check if there's a mesh object
    o = context.selected_objects
    if len(o) == 0:
        me.report({'ERROR'}, 'No object selected!')
        return {'CANCELLED'}
    m = o[0].data
    if type(m) != bpy_types.Mesh:
        me.report({'ERROR'}, 'Selected object was not a mesh, doofus!')
        return {'CANCELLED'}

    # we can go on
    tree = builder.KDTreeNode(max_threshold, max_depth, criterion, m, True)
    print("\nDEBUG PRINT: tree contain (%d) nodes\n" % (builder.nodeCount(tree)))
    tree.print()

    # depending on something
    if write_mode == "ascii":
        write_ascii(filepath, tree, m, me, format)
    else:
        write_binary(filepath, tree, m, me, format)

    me.report({'INFO'}, "File written to %s" % filepath)
    return {'FINISHED'}

