import json
import os
import sys
import tempfile
import unittest
from pathlib import Path

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from maps_fixtures import IDENTITY, moved, write_config, write_scene  # noqa: E402
from maps import collision  # noqa: E402
from maps.collision_profiles import CollisionProfiles, layered_arrays, parse_struct  # noqa: E402
from maps.scene import Scene, quat_matrix  # noqa: E402

ROCK = "/Game/Art/SM_Rock.SM_Rock"
GRASS = "/Game/Art/SM_Grass.SM_Grass"
WALL = "/Game/Art/SM_Wall.SM_Wall"
# 90 degrees about Z.
QUARTER_Z = [0, 0, 0.7071067811865476, 0.7071067811865476]
CUBE = [[x, y, z] for x in (-50, 50) for y in (-50, 50) for z in (-50, 50)]


def world(t, q=(0, 0, 0, 1), s=(1, 1, 1)):
    return {"t": list(t), "q": list(q), "s": list(s)}


def profiles(root):
    write_config(str(root))
    return CollisionProfiles.from_config(root / "config")


class TestProfiles(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.profiles = profiles(Path(self.temp_dir.name))

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_parse_struct_nested_lists_quotes_and_empty_values(self):
        value = parse_struct('(Name="A b",List=((Channel="X",Response=ECR_Ignore),(Channel="Y")),Empty=,Flag=False)')
        self.assertEqual(value, {"Name": "A b", "List": [{"Channel": "X", "Response": "ECR_Ignore"}, {"Channel": "Y"}],
                                 "Empty": "", "Flag": "False"})

    def test_layering_removes_and_adds(self):
        arrays = layered_arrays([["+Profiles=a", "+Profiles=b"], ["-Profiles=a", "+Profiles=b", "+Profiles=c", ".Profiles=c"]])
        self.assertEqual(arrays["Profiles"], ["b", "c", "c"])

    def test_channels_defaults_and_edit_profiles(self):
        names = self.profiles.channel_names
        self.assertEqual(names[14], "Projectile")
        self.assertEqual(names[20], "MapBoundariesWall")
        self.assertEqual(self.profiles.default_responses[18], "Ignore")  # Walking's DefaultChannelResponses
        self.assertEqual(self.profiles.default_responses[8], "Ignore")  # the editor gizmo channel
        pawn = self.profiles.robot()
        self.assertEqual(pawn["object_type"], 2)
        self.assertEqual(pawn["responses"][3], "Ignore")  # Visibility, CustomResponses
        self.assertEqual(pawn["responses"][14], "Ignore")  # Projectile, EditProfiles
        self.assertEqual(pawn["responses"][20], "Block")  # MapBoundariesWall, channel default
        walking = self.profiles.profile("Walking")
        self.assertEqual(walking["responses"][18], "Block")  # (Channel="Walking") without a response is Block
        self.assertEqual(self.profiles.profile("BlockingVolume"), self.profiles.profile("InvisibleWall"))  # redirect

    def test_robot_block_test(self):
        blocks = {name: self.profiles.blocks_robot(self.profiles.profile(name))
                  for name in ("BlockAll", "BlockAllDynamic", "InvisibleWall", "DestructibleBlockAll", "NoCollision",
                               "OverlapAllDynamic", "Walking")}
        self.assertEqual(blocks, {"BlockAll": True, "BlockAllDynamic": True, "InvisibleWall": True, "DestructibleBlockAll": True,
                                  "NoCollision": False, "OverlapAllDynamic": False, "Walking": False})


class TestResolve(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.profiles = profiles(Path(self.temp_dir.name))
        self.infos = {ROCK: {"collision": {"default_profile": "NoCollision",
                                           "default_instance": {"CollisionProfileName": "NoCollision"}}}}

    def tearDown(self):
        self.temp_dir.cleanup()

    def resolve(self, actor, component, sets=()):
        return collision.resolve(self.profiles, actor, component, list(sets), self.infos.get)

    def test_static_mesh_actor_takes_its_meshes_default_body(self):
        actor = {"class": "StaticMeshActor", "class_chain": ["StaticMeshActor", "Actor"]}
        component = {"name": "StaticMeshComponent0", "native": "UStaticMeshComponent", "kind": "static_mesh", "mesh": ROCK}
        self.assertFalse(self.profiles.blocks_robot(self.resolve(actor, component)))
        # Once the level turns bUseDefaultCollision off, the actor constructor's BlockAll applies.
        component["collision"] = {"use_default": False}
        self.assertEqual(self.resolve(actor, component), self.profiles.profile("BlockAll"))

    def test_custom_without_responses_keeps_the_native_defaults_responses(self):
        # A landscape spline's boundary wall: Custom, query-enabled, MapBoundariesWall, but its
        # responses are the NoCollision default of a spline mesh, which ignore Pawn.
        actor = {"class": "Landscape", "class_chain": ["Landscape"]}
        component = {"name": "SplineMeshComponent_0", "native": "USplineMeshComponent", "kind": "spline_mesh",
                     "collision": {"profile": "Custom", "enabled": "ECollisionEnabled::QueryAndPhysics",
                                   "object_type": "ECollisionChannel::ECC_GameTraceChannel7"}}
        resolved = self.resolve(actor, component)
        self.assertEqual((resolved["enabled"], resolved["object_type"], resolved["responses"][2]), ("QueryAndPhysics", 20, "Ignore"))
        self.assertFalse(self.profiles.blocks_robot(resolved))
        component["collision"]["responses"] = 0
        self.assertTrue(self.profiles.blocks_robot(self.resolve(actor, component, [{"Visibility": "Ignore"}])))

    def test_constructor_that_disables_collision_after_its_profile(self):
        actor = {"class": "BP_WarpProbe_C", "class_chain": ["BP_WarpProbe_C", "SWarpProbe", "Actor"]}
        component = {"name": "WarpDevice", "native": "UStaticMeshComponent", "kind": "static_mesh"}
        resolved = self.resolve(actor, component)
        self.assertEqual(resolved["enabled"], "NoCollision")
        self.assertEqual(resolved["responses"], self.profiles.profile("BlockAll")["responses"])
        component["collision"] = {"profile": "BlockAll", "enabled": "ECollisionEnabled::QueryAndPhysics"}
        self.assertTrue(self.profiles.blocks_robot(self.resolve(actor, component)))

    def test_volumes_by_actor_class(self):
        brush = {"name": "BrushComponent0", "native": "UBrushComponent", "kind": "brush"}
        blocking = self.resolve({"class": "BlockingVolume", "class_chain": ["BlockingVolume", "Volume", "Brush"]}, brush)
        kill = self.resolve({"class": "KillZVolume", "class_chain": ["KillZVolume", "PhysicsVolume", "Volume", "Brush"]}, brush)
        self.assertTrue(self.profiles.blocks_robot(blocking))
        self.assertFalse(self.profiles.blocks_robot(kill))

    def test_unknown_native_default_is_counted(self):
        unknown = collision.Counter()
        actor = {"class": "BP_New_C", "class_chain": ["BP_New_C", "SNewActor", "Actor"]}
        component = {"name": "Mesh", "native": "UStaticMeshComponent", "kind": "static_mesh", "template": "/Game/BP_New.Default__BP_New_C:Mesh"}
        collision.resolve(self.profiles, actor, component, [], self.infos.get, unknown)
        self.assertEqual(unknown, {"SNewActor.Mesh": 1})

    def test_queried_geometry(self):
        self.assertIsNone(collision.queried_geometry({"boxes": [], "convex": []}))  # default flag, no simple shapes
        self.assertEqual(collision.queried_geometry({"boxes": [{}]}), "simple")
        trimesh = {"vertices": [0, 0, 0, 1, 0, 0, 0, 1, 0], "indices": [0, 1, 2]}
        self.assertEqual(collision.queried_geometry({"trace_flag": "ECollisionTraceFlag::CTF_UseComplexAsSimple", "trimesh": trimesh}), "trimesh")
        self.assertIsNone(collision.queried_geometry({"trace_flag": "ECollisionTraceFlag::CTF_UseSimpleAsComplex", "trimesh": trimesh}))


class TestScale(unittest.TestCase):
    def test_box_extents_scale_along_the_boxs_own_axes(self):
        # A box turned 90 degrees in its body: UE scales its X extent by the body's X scale anyway.
        box = {"center": [10, 20, 30], "q": QUARTER_Z, "size": [100, 40, 20]}
        center, rotation, half = collision.scaled_box(box, [2, 3, -4])
        np.testing.assert_allclose(center, [20, 60, -120])
        np.testing.assert_allclose(rotation, QUARTER_Z)
        np.testing.assert_allclose(half, [100, 60, 40])

    def test_sphere_takes_the_smallest_scale(self):
        center, radius = collision.scaled_sphere({"center": [1, 1, 1], "radius": 50}, [2, -0.5, 3])
        np.testing.assert_allclose(center, [2, -0.5, 3])
        self.assertAlmostEqual(radius, 25)

    def test_capsule_radius_from_xy_and_length_from_z(self):
        # Radius 10, cylinder 40: total half height (40 + 20) / 2 = 30, times |sz| 2 = 60.
        center, rotation, radius, half_length = collision.scaled_capsule(
            {"center": [0, 0, 5], "q": [0, 0, 0, 1], "radius": 10, "length": 40}, [3, -1, 2])
        np.testing.assert_allclose(center, [0, 0, 10])
        self.assertAlmostEqual(radius, 30)
        self.assertAlmostEqual(half_length, 30)  # (60 - 30) * 2 / 2
        # A radius scaled beyond the half height is clamped to it.
        _, _, radius, half_length = collision.scaled_capsule({"center": [0, 0, 0], "radius": 10, "length": 0}, [10, 10, 1])
        self.assertAlmostEqual(radius, 10)
        self.assertAlmostEqual(half_length, 0.05)  # the 0.1 minimum cylinder length

    def test_shape_components(self):
        box = collision.shape_body({"kind": "box", "shape": {"box_extent": [10, 0, 30]}})
        self.assertEqual(box["boxes"][0]["size"], [20, 2.0, 60])  # a zero extent becomes 1
        capsule = collision.shape_body({"kind": "capsule", "shape": {"capsule_radius": 600, "capsule_half_height": 700}})
        self.assertEqual((capsule["capsules"][0]["radius"], capsule["capsules"][0]["length"]), (600, 200))


class TestBuild(unittest.TestCase):
    """A small map: blocking and non-blocking meshes with non-uniform scale, a blocking volume, a
    shape component, a destructible, a moving platform, a landscape, a mode and lighting variants."""

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.root = Path(self.temp_dir.name)
        write_config(str(self.root))
        self.profiles = CollisionProfiles.from_config(self.root / "config")
        assets = self.root / "assets"
        assets.mkdir()
        hull = {"vertices": CUBE, "indices": [0, 1, 2, 1, 3, 2]}
        infos = {
            ROCK: {"collision": {"default_profile": "BlockAll", "boxes": [{"center": [0, 0, 50], "q": QUARTER_Z, "size": [100, 40, 20]}],
                                 "spheres": [{"center": [0, 0, 0], "radius": 10}], "capsules": [], "convex": [hull]}},
            GRASS: {"collision": {"default_profile": "BlockAll", "boxes": [], "spheres": [], "capsules": [], "convex": []}},
            WALL: {"collision": {"default_profile": "BlockAll", "trace_flag": "ECollisionTraceFlag::CTF_UseComplexAsSimple",
                                 "boxes": [], "spheres": [], "capsules": [], "convex": [],
                                 "trimesh": {"vertices": [0, 0, 0, 0, 100, 0, 100, 0, 0], "indices": [0, 1, 2]}}},
        }
        meshes = {}
        for path, info in infos.items():
            name = path.rsplit(".", 1)[-1]
            (assets / f"{name}.meshinfo.json").write_text(json.dumps(info))
            meshes[path] = {"info": f"assets/{name}.meshinfo.json"}

        # Landscape collision: a 3 x 3 grid (2 x 2 cells, one a hole) and its mesh piece.
        blob = bytearray()

        def add(array, type_name):
            blob.extend(b"\0" * (-len(blob) % 4))
            offset = len(blob)
            blob.extend(np.asarray(array).tobytes())
            return {"offset": offset, "count": int(np.asarray(array).size), "type": type_name}

        heights = add(np.array([0, 1, 2, 3, 4, 5, 6, 7, 8], dtype="<u2"), "uint16")
        materials = add(np.array([0, 255, 0, 0], dtype="<u1"), "uint8")
        mesh_vertices = add(np.array([0, 0, 0, 1, 0, 0, 0, 1, 2], dtype="<f4"), "float32")
        mesh_indices = add(np.array([0, 2, 1], dtype="<i4"), "int32")
        map_dir = self.root / "maps" / "Arena"
        map_dir.mkdir(parents=True)
        (map_dir / "collision.bin").write_bytes(bytes(blob))
        landscape_world = world([1000, 2000, 300], s=[100, 100, 128])

        levels = [
            {"index": 0, "name": "Arena", "kind": "persistent", "parent": None},
            {"index": 1, "name": "Arena_Spearhead", "kind": "streaming_dynamic", "parent": 0},
            {"index": 2, "name": "Arena_Sunset_Light", "kind": "streaming_dynamic", "parent": 0},
            {"index": 3, "name": "Arena_Rebalance", "kind": "streaming_dynamic", "parent": 0},
        ]

        def mesh_actor(actor_id, level, mesh, component_world, cls="StaticMeshActor", chain=None, **extra):
            return {"id": actor_id, "level": level, "name": f"A{actor_id}", "class": cls, "class_chain": chain or [cls, "Actor"],
                    "world": component_world, "components": [{"name": "StaticMeshComponent0", "native": "UStaticMeshComponent",
                                                              "kind": "static_mesh", "mesh": mesh, "world": component_world, **extra}]}

        actors = [
            {"id": 0, "level": 0, "name": "WorldSettings", "class": "SWorldSettings", "components": [],
             "props": {"LightingVariants": {"Variants": [{"SubLevelSuffix": "_Sunset_Light", "Weight": 2}]}}},
            mesh_actor(1, 0, ROCK, world([100, 0, 0], QUARTER_Z, [2, 3, 0.5])),
            mesh_actor(2, 0, GRASS, world([0, 0, 0])),  # blocks by profile, no simple shapes: nothing
            mesh_actor(3, 0, WALL, world([0, 500, 0], s=[2, 2, 2])),
            mesh_actor(4, 1, ROCK, world([0, 0, 0])),  # the game mode's sublevel
            mesh_actor(5, 2, ROCK, world([0, 0, 0])),  # a lighting variant
            mesh_actor(6, 3, ROCK, world([0, 0, 0])),  # loaded by nothing: dropped
            mesh_actor(7, 0, ROCK, world([0, 0, 0]), hidden_in_game=True),
            mesh_actor(8, 0, ROCK, world([0, 0, 0]), cls="BP_Crate_C", chain=["BP_Crate_C", "SDestructibleActor", "Actor"],
                       collision={"profile": "DestructibleBlockAll"}),
            {"id": 9, "level": 0, "name": "Platform", "class": "BP_Lift_C", "class_chain": ["BP_Lift_C", "SMovingPlatform", "Actor"],
             "world": IDENTITY, "components": [{"name": "MeshComponent", "native": "UStaticMeshComponent", "kind": "static_mesh",
                                                 "mesh": ROCK, "world": world([0, 0, 900])}]},
            {"id": 10, "level": 0, "name": "Volume", "class": "BlockingVolume", "class_chain": ["BlockingVolume", "Volume", "Brush", "Actor"],
             "world": IDENTITY, "components": [{"name": "BrushComponent0", "native": "UBrushComponent", "kind": "brush",
                                                 "world": world([0, 0, 0], s=[2, 1, 1]), "convex": [hull]}]},
            {"id": 11, "level": 0, "name": "Trigger", "class": "BP_Gate_C", "class_chain": ["BP_Gate_C", "Actor"],
             "world": IDENTITY, "components": [{"name": "Box", "native": "UBoxComponent", "kind": "box", "world": world([0, 0, 0], s=[1, 2, 3]),
                                                 "shape": {"box_extent": [10, 10, 10]}, "collision": {"profile": "BlockAll"}}]},
            {"id": 12, "level": 0, "name": "Landscape", "class": "Landscape", "class_chain": ["Landscape", "Actor"], "world": landscape_world,
             "components": [
                 {"name": "LandscapeHeightfieldCollisionComponent_0", "native": "CookedLandscapeCollisionComponent",
                  "kind": "landscape_collision", "world": landscape_world,
                  "landscape_collision": {"type": "heightfield", "section_base": [0, 0], "collision_scale": 4.0, "rows": 3, "cols": 3,
                                          "min_value": -32768.0, "height_per_unit": 2.0, "heights": heights, "holes": 1,
                                          "cell_materials": materials}},
                 {"name": "LandscapeMeshCollisionComponent_0", "native": "CookedLandscapeMeshCollisionComponent",
                  "kind": "landscape_collision", "world": landscape_world,
                  "landscape_collision": {"type": "mesh", "collision_scale": 4.0, "vertices": mesh_vertices, "indices": mesh_indices}},
             ]},
        ]
        write_scene(str(self.root), "Arena", levels, actors, meshes=meshes)
        scene_file = map_dir / "scene.json"
        scene_data = json.loads(scene_file.read_text())
        scene_data["collision_file"] = "collision.bin"
        scene_file.write_text(json.dumps(scene_data))
        self.scene = Scene(self.root, "Arena")
        self.built = collision.build(self.scene, self.profiles, {"Spearhead": ["Arena_Spearhead"]})
        self.document, self.read = collision.decode(collision.encode(self.built))

    def tearDown(self):
        self.temp_dir.cleanup()

    def colliders(self, kind):
        meta = self.read(self.document[kind]["meta"]) if "meta" in self.document[kind] else None
        return meta

    def test_parts_modes_lighting_and_dropped(self):
        self.assertEqual([(part["id"], part["kind"]) for part in self.document["parts"]],
                         [("base", "base"), ("Arena_Spearhead", "sublevel"), ("Arena_Sunset_Light", "lighting")])
        self.assertEqual(self.document["parts"][2]["weight"], 2.0)
        self.assertEqual(self.document["modes"], {"Spearhead": ["Arena_Spearhead"]})
        self.assertEqual(self.document["lighting"], ["Arena_Sunset_Light"])
        self.assertEqual(self.document["dropped_sublevels"], ["Arena_Rebalance"])

    def test_counts(self):
        # Rock placements: base, mode, lighting, hidden, destructible, platform = 6; the brush adds a hull.
        counts = self.document["counts"]
        self.assertEqual((counts["boxes"], counts["spheres"], counts["hull_instances"]), (6 + 1, 6, 6 + 1))
        self.assertEqual((counts["hulls"], counts["meshes"], counts["mesh_instances"], counts["heightfields"]), (2, 2, 2, 1))
        parts = self.read(self.document["spheres"]["meta"])[:, 0]
        self.assertEqual(sorted(parts.tolist()), [0, 0, 0, 0, 1, 2])

    def test_box_under_rotation_and_non_uniform_scale(self):
        boxes = self.read(self.document["boxes"]["data"])
        first = boxes[0]
        # Body centre (0, 0, 50) scaled to (0, 0, 25), turned 90 degrees, moved by (100, 0, 0).
        np.testing.assert_allclose(first[:3], [100, 0, 25], atol=1e-4)
        expected_q = collision.quat_multiply(QUARTER_Z, QUARTER_Z)
        np.testing.assert_allclose(first[3:7], expected_q, atol=1e-6)
        np.testing.assert_allclose(first[7:], [100, 60, 5], atol=1e-4)  # (100, 40, 20) / 2 * |(2, 3, 0.5)| on the box's own axes

    def test_hull_instance_keeps_the_full_scale_and_render_winding(self):
        instances = self.read(self.document["hull_instances"]["transform"])
        np.testing.assert_allclose(instances[0], [100, 0, 0, *QUARTER_Z, 2, 3, 0.5], atol=1e-6)
        hull_vertices = self.read(self.document["hulls"]["vertices"])
        triangles = self.read(self.document["hulls"]["triangles"])
        ranges = self.read(self.document["hulls"]["ranges"])
        np.testing.assert_allclose(hull_vertices[:8], CUBE)
        self.assertEqual(triangles[:2].tolist(), [[1, 0, 2], [3, 1, 2]])  # body setup order swapped to UE's
        self.assertEqual(ranges[0].tolist(), [0, 8, 0, 2])
        # Placed: world = t + rotate(q, s * v).
        t, q, s = instances[0][:3], instances[0][3:7], instances[0][7:]
        corner = t + quat_matrix(q) @ (s * np.array(CUBE[-1]))
        np.testing.assert_allclose(corner, [100 - 150, 100, 25], atol=1e-4)

    def test_flags(self):
        flags = self.read(self.document["spheres"]["meta"])[:, 1].tolist()
        names = self.document["flags"]
        self.assertIn(names["hidden"], flags)
        self.assertIn(names["destructible"], flags)
        self.assertIn(names["moving"], flags)
        box_meta = self.read(self.document["boxes"]["meta"])
        self.assertEqual(box_meta[-1, 1], names["hidden"])  # the box component: nothing drawn
        destructible = [row for row in self.read(self.document["spheres"]["meta"]) if row[1] == names["destructible"]]
        self.assertEqual(self.document["channels"][destructible[0][2]], "Destructible")
        sources = [self.document["sources"][row[3]] for row in self.read(self.document["spheres"]["meta"])]
        self.assertIn("BP_Crate_C/SM_Rock", sources)

    def test_complex_as_simple_mesh_and_landscape_mesh(self):
        mesh_instances = self.read(self.document["mesh_instances"]["transform"])
        np.testing.assert_allclose(mesh_instances[0], [0, 500, 0, 0, 0, 0, 1, 2, 2, 2])
        # The landscape mesh piece: component scale times (collision scale, collision scale, 1).
        np.testing.assert_allclose(mesh_instances[1], [1000, 2000, 300, 0, 0, 0, 1, 400, 400, 128])
        triangles = self.read(self.document["meshes"]["triangles"])
        self.assertEqual(triangles.tolist(), [[0, 1, 2], [0, 2, 1]])  # kept as exported (already UE's order)

    def test_landscape_heightfield_spacing_heights_and_holes(self):
        grid = self.read(self.document["heightfields"]["grid"])
        decode = self.read(self.document["heightfields"]["decode"])
        transform = self.read(self.document["heightfields"]["transform"])
        heights = self.read(self.document["heightfields"]["heights"])
        holes = self.read(self.document["heightfields"]["holes"])
        self.assertEqual(grid.tolist(), [[3, 3, 0, 0]])
        np.testing.assert_allclose(decode, [[-32768.0, 2.0]])
        # Cell spacing: landscape scale 100 x collision scale 4; z: scale 128 / 128.
        np.testing.assert_allclose(transform[0], [1000, 2000, 300, 0, 0, 0, 1, 400, 400, 1])
        self.assertEqual(holes.tolist(), [0, 1, 0, 0])
        # Vertex (x 2, y 1): height 5 -> -32758 local units, so world z = 300 - 32758.
        x, y = 2, 1
        h = heights[y * 3 + x]
        local = np.array([x, y, decode[0, 0] + h * decode[0, 1]])
        world_point = transform[0, :3] + quat_matrix(transform[0, 3:7]) @ (transform[0, 7:] * local)
        np.testing.assert_allclose(world_point, [1800, 2400, 300 - 32758])

    def test_grass_without_simple_shapes_is_not_exported(self):
        self.assertEqual(self.built.stats["blocking, no queried geometry"], 1)
        self.assertEqual(self.built.stats["dropped (sublevel not loaded)"], 1)


if __name__ == "__main__":
    unittest.main()
