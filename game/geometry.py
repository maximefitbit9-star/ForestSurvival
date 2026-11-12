"""Procedural low-poly geometry builders (cylinders, cones, boxes, spheres).

All models in this game are generated original assets; nothing is copied.
"""
import math

from panda3d.core import (
    GeomVertexFormat, GeomVertexData, GeomVertexWriter, Geom, GeomTriangles,
    GeomNode, NodePath, LPoint3f)


def _start_primitive(name):
    vdata = GeomVertexData(name, GeomVertexFormat.get_v3n3c4(), Geom.UHStatic)
    vdata.set_num_rows(64)
    vertex = GeomVertexWriter(vdata, "vertex")
    normal = GeomVertexWriter(vdata, "normal")
    colour = GeomVertexWriter(vdata, "color")
    return vdata, vertex, normal, colour


def make_cylinder(radius, height, colour, segments=8, z0=0.0):
    vdata, vertex, normal, colour_w = _start_primitive("cyl")
    r, g, b = colour
    for i in range(segments):
        a0 = i / segments * 2 * math.pi
        a1 = (i + 1) / segments * 2 * math.pi
        for ang, z in ((a0, z0), (a0, z0 + height), (a1, z0), (a1, z0 + height)):
            vertex.add_data3f(math.cos(ang) * radius, math.sin(ang) * radius, z)
            normal.add_data3f(math.cos(ang), math.sin(ang), 0)
            colour_w.add_data4f(r, g, b, 1)
    tris = GeomTriangles(Geom.UHStatic)
    for i in range(segments):
        v = i * 4
        tris.add_vertices(v, v + 2, v + 1)
        tris.add_vertices(v + 1, v + 2, v + 3)
    geom = Geom(vdata)
    geom.add_primitive(tris)
    node = GeomNode("cyl")
    node.add_geom(geom)
    return node


def make_cone(radius, height, colour, segments=8, z0=0.0):
    vdata, vertex, normal, colour_w = _start_primitive("cone")
    r, g, b = colour
    apex = 4
    for i in range(segments):
        a0 = i / segments * 2 * math.pi
        a1 = (i + 1) / segments * 2 * math.pi
        vertex.add_data3f(math.cos(a0) * radius, math.sin(a0) * radius, z0)
        vertex.add_data3f(math.cos(a1) * radius, math.sin(a1) * radius, z0)
        vertex.add_data3f(math.cos(a0) * radius, math.sin(a0) * radius, z0 + height)
        vertex.add_data3f(0, 0, z0 + height)
        normal.add_data3f(math.cos(a0), math.sin(a0), 0.4)
        normal.add_data3f(math.cos(a1), math.sin(a1), 0.4)
        normal.add_data3f(math.cos(a0), math.sin(a0), 0.4)
        normal.add_data3f(0, 0, 1)
        for _ in range(4):
            colour_w.add_data4f(r, g, b, 1)
    tris = GeomTriangles(Geom.UHStatic)
    for i in range(segments):
        v = i * 4
        tris.add_vertices(v, v + 1, v + 2)
        tris.add_vertices(v + 1, v + 3, v + 2)
    geom = Geom(vdata)
    geom.add_primitive(tris)
    node = GeomNode("cone")
    node.add_geom(geom)
    return node


def make_box(width, depth, height, colour, z0=0.0):
    vdata, vertex, normal, colour_w = _start_primitive("box")
    r, g, b = colour
    w, d, h = width / 2, depth / 2, height
    faces = [
        ((-w, -d, z0), (-w, -d, z0 + h), (-w, d, z0), (-w, d, z0 + h), (-1, 0, 0)),
        ((w, -d, z0), (w, d, z0), (w, -d, z0 + h), (w, d, z0 + h), (1, 0, 0)),
        ((-w, -d, z0), (w, -d, z0), (-w, -d, z0 + h), (w, -d, z0 + h), (0, -1, 0)),
        ((-w, d, z0), (-w, d, z0 + h), (w, d, z0), (w, d, z0 + h), (0, 1, 0)),
        ((-w, -d, z0), (-w, d, z0), (w, -d, z0), (w, d, z0), (0, 0, -1)),
        ((-w, -d, z0 + h), (w, -d, z0 + h), (-w, d, z0 + h), (w, d, z0 + h), (0, 0, 1)),
    ]
    for v0, v1, v2, v3, n in faces:
        for v in (v0, v1, v2, v3):
            vertex.add_data3f(*v)
            normal.add_data3f(*n)
            colour_w.add_data4f(r, g, b, 1)
    tris = GeomTriangles(Geom.UHStatic)
    for f in range(len(faces)):
        v = f * 4
        tris.add_vertices(v, v + 1, v + 2)
        tris.add_vertices(v + 1, v + 3, v + 2)
    geom = Geom(vdata)
    geom.add_primitive(tris)
    tris2 = GeomTriangles(Geom.UHStatic)
    node = GeomNode("box")
    node.add_geom(geom)
    return node


def make_sphere(radius, colour, segments=8):
    vdata, vertex, normal, colour_w = _start_primitive("sphere")
    r, g, b = colour
    rows = segments // 2
    for i in range(segments):
        for j in range(rows):
            a0, a1 = i / segments * 2 * math.pi, (i + 1) / segments * 2 * math.pi
            p0, p1 = j / rows * math.pi, (j + 1) / rows * math.pi
            def pt(a, p):
                return (radius * math.sin(p) * math.cos(a),
                        radius * math.sin(p) * math.sin(a),
                        radius * math.cos(p))
            for v in (pt(a0, p0), pt(a0, p1), pt(a1, p0), pt(a1, p1)):
                vertex.add_data3f(*v)
                normal.add_data3f(v[0] / radius, v[1] / radius, v[2] / radius)
                colour_w.add_data4f(r, g, b, 1)
    tris = GeomTriangles(Geom.UHStatic)
    for i in range(segments):
        for j in range(rows):
            v = (i * rows + j) * 4
            tris.add_vertices(v, v + 2, v + 1)
            tris.add_vertices(v + 1, v + 2, v + 3)
    geom = Geom(vdata)
    geom.add_primitive(tris)
    node = GeomNode("sphere")
    node.add_geom(geom)
    return node
