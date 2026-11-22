"""Builders for the map tests: synthetic .uemodel files and map exports."""
import json
import os
import struct
import sys

import numpy as np
import zstandard

SRC_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "src")
for path in (os.path.join(SRC_DIR, "parse"), SRC_DIR):
    if path not in sys.path:
        sys.path.insert(0, path)

IDENTITY = {"t": [0, 0, 0], "q": [0, 0, 0, 1], "s": [1, 1, 1]}


def fstring(text):
    data = text.encode("utf-8")
    return struct.pack("<i", len(data)) + data


def attribute(name, payload):
    return fstring(name) + struct.pack("<i", len(payload)) + payload


def attribute_set(attributes):
    return struct.pack("<i", len(attributes)) + b"".join(attributes)


def build_model(vertices=(), indices=(), hulls=(), bones=None, compressed=True, version=10, identifier="UEMODEL",
                index_dtype="<u4"):
    """A UEFormat .uemodel: one LOD (if any vertices), convex hulls, and a skeleton of
    ``bones`` = [(name, parent, pos, quat, scale)]."""
    root = []
    if len(vertices):
        vertex_data = struct.pack("<i", len(vertices)) + np.asarray(vertices, dtype="<f4").tobytes()
        index_data = struct.pack("<i", len(indices)) + np.asarray(indices, dtype=index_dtype).tobytes()
        materials = struct.pack("<i", 1) + fstring("Slot0") + fstring("/Game/M_Test.M_Test") + struct.pack("<ii", 0, len(indices) // 3)
        lod = fstring("LOD0") + attribute_set([
            attribute("VERTICES", vertex_data), attribute("INDICES", index_data), attribute("MATERIALS", materials)])
        root.append(attribute("LODS", struct.pack("<i", 1) + lod))
    if hulls:
        hull_data = struct.pack("<i", len(hulls))
        for hull_vertices, hull_indices in hulls:
            hull_data += fstring("hull")
            hull_data += struct.pack("<i", len(hull_vertices)) + np.asarray(hull_vertices, dtype="<f4").tobytes()
            hull_data += struct.pack("<i", len(hull_indices)) + np.asarray(hull_indices, dtype="<i4").tobytes()
        root.append(attribute("COLLISION", hull_data))
    if bones is not None:
        bone_data = struct.pack("<i", len(bones))
        for name, parent, pos, rot, scale in bones:
            bone_data += fstring(name) + struct.pack("<i", parent) + struct.pack("<3f", *pos) + struct.pack("<4f", *rot)
            bone_data += struct.pack("<3f", *scale)
        root.append(attribute("SKELETON", attribute_set([attribute("BONES", bone_data)])))
    body = attribute_set(root)

    header = b"UEFORMAT" + fstring(identifier) + bytes([version]) + fstring("SM_Test") + fstring("/Game/SM_Test.SM_Test")
    if compressed:
        packed = zstandard.ZstdCompressor().compress(body)
        return header + b"\x01" + fstring("ZSTD") + struct.pack("<ii", len(body), len(packed)) + packed
    return header + b"\x00" + body


def write_scene(export_dir, map_name, levels, actors, templates=None, meshes=None):
    """A map export: ``maps/<map>/scene.json`` + ``actors.jsonl``."""
    map_dir = os.path.join(export_dir, "maps", map_name)
    os.makedirs(map_dir, exist_ok=True)
    data = {
        "world": f"/Game/Maps/{map_name}.{map_name}",
        "name": map_name,
        "exported_utc": "2026-10-06T00:00:00Z",
        "actors_file": "actors.jsonl",
        "stats": {"levels": len(levels), "actors": len(actors), "unique_meshes": len(meshes or {})},
        "levels": levels,
        "templates": templates or {},
        "meshes": meshes or {},
        "collision_response_sets": [],
        "warnings": [],
    }
    with open(os.path.join(map_dir, "scene.json"), "w", encoding="utf-8") as scene_file:
        json.dump(data, scene_file)
    with open(os.path.join(map_dir, "actors.jsonl"), "w", encoding="utf-8") as actors_file:
        for actor in actors:
            actors_file.write(json.dumps(actor) + "\n")
    return map_dir


def moved(x, y, z, scale=1.0):
    return {"t": [x, y, z], "q": [0, 0, 0, 1], "s": [scale, scale, scale]}


BASE_ENGINE_INI = """[/Script/Engine.CollisionProfile]
+Profiles=(Name="NoCollision",CollisionEnabled=NoCollision,ObjectTypeName="WorldStatic",CustomResponses=((Channel="Visibility",Response=ECR_Ignore),(Channel="Camera",Response=ECR_Ignore)),HelpMessage="No collision",bCanModify=False)
+Profiles=(Name="BlockAll",CollisionEnabled=QueryAndPhysics,ObjectTypeName="WorldStatic",CustomResponses=,HelpMessage="Blocks all",bCanModify=False)
+Profiles=(Name="Pawn",CollisionEnabled=QueryAndPhysics,ObjectTypeName="Pawn",CustomResponses=((Channel="Visibility",Response=ECR_Ignore)),HelpMessage="Pawn",bCanModify=False)
"""

DEFAULT_ENGINE_INI = """[/Script/Engine.PhysicsSettings]
DefaultGravityZ=-1400.000000

[/Script/Engine.CollisionProfile]
-Profiles=(Name="BlockAll",CollisionEnabled=QueryAndPhysics,ObjectTypeName="WorldStatic",CustomResponses=,HelpMessage="Blocks all",bCanModify=False)
+Profiles=(Name="BlockAll",CollisionEnabled=QueryAndPhysics,bCanModify=False,ObjectTypeName="WorldStatic",CustomResponses=,HelpMessage="Blocks all")
+Profiles=(Name="BlockAllDynamic",CollisionEnabled=QueryAndPhysics,bCanModify=False,ObjectTypeName="WorldDynamic",CustomResponses=,HelpMessage="")
+Profiles=(Name="OverlapAllDynamic",CollisionEnabled=QueryOnly,bCanModify=False,ObjectTypeName="WorldDynamic",CustomResponses=((Channel="WorldStatic",Response=ECR_Overlap),(Channel="Pawn",Response=ECR_Overlap)),HelpMessage="")
+Profiles=(Name="InvisibleWall",CollisionEnabled=QueryAndPhysics,bCanModify=False,ObjectTypeName="WorldStatic",CustomResponses=((Channel="Visibility",Response=ECR_Ignore)),HelpMessage="")
+Profiles=(Name="Walking",CollisionEnabled=QueryAndPhysics,bCanModify=True,ObjectTypeName="Walking",CustomResponses=((Channel="Pawn",Response=ECR_Ignore),(Channel="Walking")),HelpMessage="")
+Profiles=(Name="DestructibleBlockAll",CollisionEnabled=QueryAndPhysics,bCanModify=True,ObjectTypeName="Destructible",CustomResponses=,HelpMessage="")
+DefaultChannelResponses=(Channel=ECC_GameTraceChannel1,DefaultResponse=ECR_Block,bTraceType=False,bStaticObject=False,Name="Projectile")
+DefaultChannelResponses=(Channel=ECC_GameTraceChannel5,DefaultResponse=ECR_Ignore,bTraceType=False,bStaticObject=False,Name="Walking")
+DefaultChannelResponses=(Channel=ECC_GameTraceChannel7,DefaultResponse=ECR_Block,bTraceType=False,bStaticObject=False,Name="MapBoundariesWall")
+EditProfiles=(Name="Pawn",CustomResponses=((Channel="Projectile",Response=ECR_Ignore)))
+EditProfiles=(Name="NoCollision",CustomResponses=((Channel="WorldStatic",Response=ECR_Ignore),(Channel="Pawn",Response=ECR_Ignore),(Channel="MapBoundariesWall",Response=ECR_Ignore)))
+ProfileRedirects=(OldName="BlockingVolume",NewName="InvisibleWall")
"""


def write_config(export_dir):
    """The two .ini files the collision profiles come from, cut down to a few profiles."""
    for relative, text in (("Engine/Config/BaseEngine.ini", BASE_ENGINE_INI),
                           ("WRFrontiers/Config/DefaultEngine.ini", DEFAULT_ENGINE_INI)):
        path = os.path.join(export_dir, "config", relative)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as ini_file:
            ini_file.write(text)
