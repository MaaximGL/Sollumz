from .properties import CollisionMatFlags
from ..resources.bound import *
from ..tools.meshhelper import *
from ..sollumz_properties import BoundType, PolygonType, MaterialType, DrawableType, FragmentType


class NoGeometryError(Exception):
    message = 'Sollumz Bound Geometry has no geometry!'


class VerticesLimitError(Exception):
    pass


def init_poly_bound(poly_bound, obj, materials):
    # materials = obj.parent.data.materials.values()
    mat_index = 0
    try:
        mat_index = materials.index(obj.active_material)
    except:
        add_material(obj.active_material, materials)
        mat_index = len(materials) - 1
    poly_bound.material_index = mat_index

    return poly_bound


def add_material(material, materials):
    if material and material.sollum_type == MaterialType.COLLISION:
        mat_item = MaterialItem()
        mat_item.type = material.collision_properties.collision_index
        mat_item.procedural_id = material.collision_properties.procedural_id
        mat_item.room_id = material.collision_properties.room_id
        mat_item.ped_density = material.collision_properties.ped_density
        mat_item.material_color_index = material.collision_properties.material_color_index

        # Assign flags
        for flag_name in CollisionMatFlags.__annotations__.keys():
            # flag_exists = getattr(material.collision_flags, flag_name)
            if flag_name in material.collision_flags:
                mat_item.flags.append(f"FLAG_{flag_name.upper()}")

        materials.append(mat_item)


def polygon_from_object(obj, geometry, export_settings):
    vertices = geometry.vertices
    materials = geometry.materials
    geom_center = geometry.geometry_center
    world_pos = obj.matrix_world.to_translation()

    if obj.sollum_type == PolygonType.BOX:
        box = init_poly_bound(Box(), obj, materials)
        indices = []
        bound_box = [obj.matrix_world @ Vector(pos) for pos in obj.bound_box]
        corners = [bound_box[0], bound_box[5], bound_box[2], bound_box[7]]
        for vert in corners:
            vertices.append(vert - geom_center)
            indices.append(len(vertices) - 1)

        box.v1 = indices[0]
        box.v2 = indices[1]
        box.v3 = indices[2]
        box.v4 = indices[3]

        return box
    elif obj.sollum_type == PolygonType.SPHERE:
        sphere = init_poly_bound(Sphere(), obj, materials)
        vertices.append(world_pos - geom_center)
        sphere.v = len(vertices) - 1
        bound_box = get_total_bounds(obj)

        radius = VectorHelper.get_distance_of_vectors(
            bound_box[1], bound_box[2]) / 2

        sphere.radius = radius

        return sphere
    elif obj.sollum_type == PolygonType.CYLINDER or obj.sollum_type == PolygonType.CAPSULE:
        bound = None
        if obj.sollum_type == PolygonType.CYLINDER:
            bound = init_poly_bound(Cylinder(), obj, materials)
        elif obj.sollum_type == PolygonType.CAPSULE:
            bound = init_poly_bound(Capsule(), obj, materials)

        bound_box = get_total_bounds(obj)

        # Get bound height
        height = VectorHelper.get_distance_of_vectors(
            bound_box[0], bound_box[1])
        radius = VectorHelper.get_distance_of_vectors(
            bound_box[1], bound_box[2]) / 2

        if obj.sollum_type == PolygonType.CAPSULE:
            height = height - (radius * 2)

        vertical = Vector((0, 0, height / 2))
        vertical.rotate(obj.matrix_world.to_euler('XYZ'))

        v1 = world_pos - vertical
        v2 = world_pos + vertical

        vertices.append(v1 - geom_center)
        vertices.append(v2 - geom_center)

        bound.v1 = len(vertices) - 2
        bound.v2 = len(vertices) - 1

        bound.radius = radius

        return bound


def triangle_from_face(face):
    triangle = Triangle()
    triangle.material_index = face.material_index

    triangle.v1 = face.vertices[0]
    triangle.v2 = face.vertices[1]
    triangle.v3 = face.vertices[2]

    return triangle


def geometry_from_object(obj, sollum_type=BoundType.GEOMETRYBVH, export_settings=None):
    geometry = None

    if sollum_type == BoundType.GEOMETRYBVH:
        geometry = BoundGeometryBVH()
    elif sollum_type == BoundType.GEOMETRY:
        geometry = BoundGeometry()
    else:
        return ValueError('Invalid argument for geometry sollum_type!')

    geometry = init_bound_item(geometry, obj)
    geometry.geometry_center = obj.location
    geometry.composite_position = Vector()

    # Ensure object has geometry
    found = False
    vertices = {}
    # Get child poly bounds
    for child in get_children_recursive(obj):
        if child.sollum_type == PolygonType.TRIANGLE:

            found = True
            mesh = child.to_mesh()
            mesh.calc_normals_split()
            mesh.calc_loop_triangles()

            # mats
            for material in mesh.materials:
                add_material(material, geometry.materials)

            # vert colors
            for poly in mesh.polygons:
                for loop_index in range(poly.loop_start, poly.loop_start + poly.loop_total):
                    #vi = mesh.loops[loop_index].vertex_index
                    #geometry.vertices.append((child.matrix_world @ mesh.vertices[vi].co) - geometry.geometry_center)
                    if(len(mesh.vertex_colors) > 0):
                        geometry.vertex_colors.append(
                            mesh.vertex_colors[0].data[loop_index].color)
                    # geometry.polygons.append(tiangle_from_mesh_loop(mesh.loops[loop_index]))

            for tri in mesh.loop_triangles:
                triangle = Triangle()
                triangle.material_index = tri.material_index

                vert_indices = []
                for loop_idx in tri.loops:
                    loop = mesh.loops[loop_idx]
                    vertex = tuple((
                        child.matrix_world @ mesh.vertices[loop.vertex_index].co) - geometry.geometry_center)

                    if vertex in vertices:
                        idx = vertices[vertex]
                    else:
                        idx = len(vertices)
                        vertices[vertex] = len(vertices)
                        geometry.vertices.append(Vector(vertex))

                    vert_indices.append(idx)

                triangle.v1 = vert_indices[0]
                triangle.v2 = vert_indices[1]
                triangle.v3 = vert_indices[2]
                geometry.polygons.append(triangle)

    for child in get_children_recursive(obj):
        poly = polygon_from_object(child, geometry, export_settings)
        if poly:
            found = True
            geometry.polygons.append(poly)
    if not found:
        raise NoGeometryError()

    print(len(geometry.vertices))
    # Check vert count
    if len(geometry.vertices) > 32767:
        raise VerticesLimitError(
            f"{obj.name} can only have at most 32767 vertices!")

    return geometry


def init_bound_item(bound_item, obj):
    init_bound(bound_item, obj)
    # Get flags from object
    for prop in dir(obj.composite_flags1):
        value = getattr(obj.composite_flags1, prop)
        if value == True:
            bound_item.composite_flags1.append(prop.upper())

    for prop in dir(obj.composite_flags2):
        value = getattr(obj.composite_flags2, prop)
        if value == True:
            bound_item.composite_flags2.append(prop.upper())

    position, rotation, scale = obj.matrix_world.decompose()
    bound_item.composite_position = position
    bound_item.composite_rotation = rotation.normalized()
    # Get scale directly from matrix (decompose gives incorrect scale)
    bound_item.composite_scale = Vector(
        (obj.matrix_world[0][0], obj.matrix_world[1][1], obj.matrix_world[2][2]))
    if obj.active_material and obj.active_material.sollum_type == MaterialType.COLLISION:
        bound_item.material_index = obj.active_material.collision_properties.collision_index

    return bound_item


def init_bound(bound, obj):
    bbmin, bbmax = get_bound_extents(obj, world=False)
    bound.box_min = bbmin
    bound.box_max = bbmax
    center = get_bound_center(obj, world=False)
    bound.box_center = center
    bound.sphere_center = center
    bound.sphere_radius = get_obj_radius(obj, world=False)
    bound.procedural_id = obj.bound_properties.procedural_id
    bound.room_id = obj.bound_properties.room_id
    bound.ped_density = obj.bound_properties.ped_density
    bound.poly_flags = obj.bound_properties.poly_flags
    bound.inertia = Vector(obj.bound_properties.inertia)
    bound.volume = obj.bound_properties.volume
    bound.margin = obj.margin

    return bound


def bound_from_object(obj, export_settings):
    if obj.sollum_type == BoundType.BOX:
        bound = init_bound_item(BoundBox(), obj)
        bound.box_max = obj.bound_dimensions
        bound.box_min = obj.bound_dimensions * -1
        return bound
    elif obj.sollum_type == BoundType.SPHERE:
        bound = init_bound_item(BoundSphere(), obj)
        bound.sphere_radius = obj.bound_radius
        return bound
    elif obj.sollum_type == BoundType.CYLINDER:
        bound = init_bound_item(BoundCylinder(), obj)
        bound.sphere_radius = obj.bound_radius
        return bound
    elif obj.sollum_type == BoundType.CAPSULE:
        bound = init_bound_item(BoundCapsule(), obj)
        bound.sphere_radius = obj.bound_radius
        return bound
    elif obj.sollum_type == BoundType.DISC:
        bound = init_bound_item(BoundDisc(), obj)
        bound.sphere_radius = obj.bound_radius
        # bound.composite_scale = obj.scale
        # bound.composite_rotation = obj.rotation_euler.to_quaternion()
        bound.margin = obj.margin
        return bound
    elif obj.sollum_type == BoundType.CLOTH:
        return init_bound_item(BoundCloth(), obj)
    elif obj.sollum_type == BoundType.GEOMETRY:
        return geometry_from_object(obj, BoundType.GEOMETRY, export_settings)
    elif obj.sollum_type == BoundType.GEOMETRYBVH:
        return geometry_from_object(obj, BoundType.GEOMETRYBVH, export_settings)


def composite_from_object(obj, export_settings):
    composite = init_bound(BoundsComposite(), obj)

    for child in get_children_recursive(obj):
        bound = bound_from_object(child, export_settings)
        if bound:
            composite.children.append(bound)

    return composite


def bounds_from_object(obj, export_settings):
    bounds = BoundFile()

    composite = composite_from_object(obj, export_settings)
    bounds.composite = composite

    return bounds


def export_ybn(obj, filepath, export_settings):
    bounds_from_object(obj, export_settings).write_xml(filepath)
