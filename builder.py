import bpy

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

def spawnAABB(obj):
    m = obj.data
    # calculate aabb
    b = AABB()
    for (v_idx, v) in enumerate(m.vertices):
        if v_idx == 0:
            b.min = list(v.co)
            b.max = list(v.co)
        else:
            b.encase(list(v.co))

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

    addMeshObject("AABB", verts, faces)



msgBox("Some Bish", "INFORMATION!!")