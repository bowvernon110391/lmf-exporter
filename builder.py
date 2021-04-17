import bpy, math

class AABB:
    def __init__(self, vectorInit = None):
        self.min = [0,0,0]
        self.max = [0,0,0]

        if vectorInit:
            self.min = list(vectorInit)
            self.max = list(vectorInit)

    # return tuple of center?
    def center(self):
        return (
            0.5 * (self.min[0] + self.max[0]),
            0.5 * (self.min[1] + self.max[1]),
            0.5 * (self.min[2] + self.max[2]),
        )

    # volume
    def volume(self):
        w = self.max[0] - self.min[0]
        h = self.max[1] - self.min[1]
        d = self.max[2] - self.min[2]
        return w * h * d

    # try to encase a single point
    def encase(self, v):
        self.min[0] = min(self.min[0], v[0])
        self.min[1] = min(self.min[1], v[1])
        self.min[2] = min(self.min[2], v[2])

        self.max[0] = max(self.max[0], v[0])
        self.max[1] = max(self.max[1], v[1])
        self.max[2] = max(self.max[2], v[2])

    # try to unionize with another aabb
    def union(self, aabb):
        self.min[0] = min(self.min[0], aabb.min[0])
        self.min[1] = min(self.min[1], aabb.min[1])
        self.min[2] = min(self.min[2], aabb.min[2])

        self.max[0] = max(self.max[0], aabb.max[0])
        self.max[1] = max(self.max[1], aabb.max[1])
        self.max[2] = max(self.max[2], aabb.max[2])

    # find largest axis to split
    # 0=x, 1=y, 2=z
    def findSplittingAxis(self):
        xlen = self.max[0] - self.min[0]
        ylen = self.max[1] - self.min[1]
        zlen = self.max[2] - self.min[2]

        if xlen > ylen and xlen > zlen:
            return 0
        elif ylen > xlen and ylen > zlen:
            return 1
        else:
            return 2

# another kdtreenode? heh
# this just contain the polygons
# the vertices would be used when rebuilding 
# the split meshes I guess
class KDTreeNode:
    def __init__(self, max_polys=5000, max_depth=10, mesh=None):
        # some default property is inbound, I guess
        self.children = [None, None]
        self._depth = 0
        self._id = 0
        self._maxPolys = max_polys
        self._maxDepth = max_depth
        self.aabb = AABB()
        self.polys = []
        self.verts = []
        self.axisId = 0
        self.parent = None

        print("KDTREE: init with max_depth(%d), max_polys(%d)" % (max_depth, max_polys))
        
        # step below only valid if mesh was provided
        if mesh is not None:
            self.buildFromPolys(mesh.polygons, mesh.vertices)
            # self.split()

    # is it leaf? leaf has no children
    def isLeaf(self):
        return self.children[0] is None and self.children[1] is None

    # build node from polysoup
    def buildFromPolys(self, polys, verts):
        # save reference?
        self.verts = verts
        # compute aabb first?
        for (p_idx, p) in enumerate(polys):
            if p_idx == 0:
                self.aabb = faceAABB(p, verts)
            else:
                self.aabb.union(faceAABB(p, verts))
        # save splitting axis
        self.axisId = self.aabb.findSplittingAxis()
        # copy them sorted order
        self.polys = getSortedPolys(polys, verts, self.axisId)
        # split
        self.split()

    # split
    def split(self):
        # should we?
        if self._depth >= self._maxDepth or len(self.polys) <= self._maxPolys:
            print("SPLIT_ABORTED: depth(%d), polycount(%d)" % (self._depth, len(self.polys)))
            return
        # welp, we could go further. go on!
        # make two children?
        self.children[0] = KDTreeNode(self._maxPolys, self._maxDepth)
        self.children[1] = KDTreeNode(self._maxPolys, self._maxDepth)

        # set relation and id and depth
        self.children[0].parent = self
        self.children[0]._id = self._id * 2 + 1
        self.children[0]._depth = self._depth + 1

        self.children[1].parent = self
        self.children[1]._id = self._id * 2 + 2
        self.children[1]._depth = self._depth + 1

        # split polys (already sorted)
        median = math.trunc(len(self.polys)/2)
        lpolys = self.polys[:median]
        rpolys = self.polys[median:]

        # build children
        self.children[0].buildFromPolys(lpolys, self.verts)
        self.children[1].buildFromPolys(rpolys, self.verts)

        # remove our data
        self.polys = []
        self.verts = []

    # print something?
    def print(self):
        tr = self
        # print some info?
        parent_id = -1
        if tr.parent is not None:
            parent_id = tr.parent._id
        print("(%s)node[%d]: parent(%d) depth(%d) aabb(%.2f %.2f %.2f | %.2f %.2f %.2f) poly(%d)" % (
            ("BRANCH", "LEAF")[tr.isLeaf()],
            tr._id, parent_id, tr._depth, tr.aabb.min[0], tr.aabb.min[1], tr.aabb.min[2],
            tr.aabb.max[0], tr.aabb.max[1], tr.aabb.max[2], len(tr.polys)
        ))

        # add children if we're not leaf
        if not tr.isLeaf():
            tr.children[0].print()
            tr.children[1].print()


def msgBox(message = "", title = "Message Box", icon = 'INFO'):

    def draw(self, context):
        self.layout.label(text=message)

    bpy.context.window_manager.popup_menu(draw, title = title, icon = icon)

def addMeshObject(name, verts, faces, edges=None, col="Collection"):
    if edges is None:
        edges = []

    mesh = bpy.data.meshes.new(name)
    obj = bpy.data.objects.new(name, mesh)
    col = bpy.data.collections.get(col)
    col.objects.link(obj)
    mesh.from_pydata(verts, edges, faces)

# output aabb from face data
def faceAABB(polygon, vertices):
    # just iterate over all vertices?
    p = polygon
    b = None
    # iterate all over face
    for (idx, v_id) in enumerate(p.vertices):
        v = list(vertices[v_id].co)
        if b is None:
            b = AABB(v)
        else:
            b.encase(v)
    return b

# output aabb from mesh
def meshAABB(mesh):
    m = mesh
    # just use vertices in this case
    b = None
    for (v_idx, v) in enumerate(m.vertices):
        pos = list(v.co)
        if v_idx == 0:
            b = AABB(pos)
        else:
            b.encase(pos)
    return b

# return polygons, sorted by aabb and split axis
def getSortedPolys(polys, verts, axisId):
    # copy list
    ps = list(polys)

    def sortByAxis(p):
        b = faceAABB(p, verts)
        return b.center()[axisId]

    ps.sort(key=sortByAxis)
    return ps

# spawn aabb from aabb data
def spawnAABB(aabb, name="AABB", col="Collection"):
    b = aabb
    
    # got aabb, build cube
    verts = [
        (b.min[0], b.min[1], b.max[2]),
        (b.max[0], b.min[1], b.max[2]),
        (b.max[0], b.max[1], b.max[2]),
        (b.min[0], b.max[1], b.max[2]),
        (b.max[0], b.min[1], b.min[2]),
        (b.min[0], b.min[1], b.min[2]),
        (b.min[0], b.max[1], b.min[2]),
        (b.max[0], b.max[1], b.min[2]),
    ]

    faces = [
        [0, 1, 2, 3],
        [4, 5, 6, 7],
        [1, 4, 7, 2],
        [5, 0, 3, 6],
        [3, 2, 7, 6],
        [5, 4, 1, 0],
    ]

    addMeshObject(name, verts, faces, None, col)

# spawn aabbs of faces...
def buildAABBs(obj, col):
    m = obj.data
    verts = m.vertices
    # iterate all over polys
    msgBox("BUILDING AABBS>>>")
    for (p_idx, p) in enumerate(m.polygons):
        b = faceAABB(p, verts)
        spawnAABB(b, "AABB_%d" % p_idx, col)
    msgBox("DONE!")

# collect leaf nodes
def collectLeaves(node):
    stack = [node]
    leaves = []
    # iterate
    while len(stack):
        tr = stack.pop()
        if tr.isLeaf():
            leaves.append(tr)
        else:
            stack.append(tr.children[0])
            stack.append(tr.children[1])
    return leaves

# test
# buildAABBs(bpy.context.selected_objects[0], "aabb")
# spawnAABB(meshAABB(bpy.context.selected_objects[0].data))
# test sorted polys?
mesh = bpy.context.selected_objects[0].data

print("Building KDTree...")
node = KDTreeNode(100, 10, mesh)

print("Debug Printing...")
node.print()

print("Collecting leaves node only")
leaves = collectLeaves(node)
print("Got %d leaves" % len(leaves))
print("Spawning aabbs of leaves...")

# iterative method?
stack = [node]
while len(stack):
    tr = stack.pop()
    colname = "depth_%d" % tr._depth
    col = bpy.data.collections.get(colname)
    if col is None:
        col = bpy.data.collections.new(colname)
        bpy.context.scene.collection.children.link(col)
    # okay, build our aabb
    spawnAABB(tr.aabb, "AABB_%d" % tr._id, colname)
    # add children
    if not tr.isLeaf():
        stack.append(tr.children[0])
        stack.append(tr.children[1])