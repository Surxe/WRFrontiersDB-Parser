import json
import os
import sys
import tempfile
import unittest

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from maps_fixtures import IDENTITY, build_model, moved, write_scene  # noqa: E402
from maps import bake, scene  # noqa: E402

TETRA_VERTICES = [[0, 0, 0], [100, 0, 0], [0, 100, 0], [0, 0, 100]]
TETRA_INDICES = [0, 1, 2, 0, 1, 3, 0, 2, 3, 1, 2, 3]
MESH = "/Game/SM_Tetra.SM_Tetra"
CRATE = "/Game/SM_Crate.SM_Crate"
HOUDINI_PLACEHOLDER = "/HoudiniEngine/default_reference_static_mesh.default_reference_static_mesh"


def box(low, high):
    return [list(low), list(high)]


def box_hull(low, high):
    """A convex hull: the 8 corners of a box and its 12 triangles."""
    low, high = np.array(low, dtype=float), np.array(high, dtype=float)
    corners = [[x, y, z] for x in (low[0], high[0]) for y in (low[1], high[1]) for z in (low[2], high[2])]
    faces = [0, 1, 3, 0, 3, 2, 4, 6, 7, 4, 7, 5, 0, 4, 5, 0, 5, 1, 2, 3, 7, 2, 7, 6, 0, 2, 6, 0, 6, 4, 1, 5, 7, 1, 7, 3]
    return {"vertices": corners, "indices": faces}


class TestMergeParts(unittest.TestCase):
    def test_merge_parts_offsets_face_indices(self):
        part = (np.zeros((3, 3)), np.array([[0, 1, 2]]))
        vertices, faces = bake._merge_parts([part, part])
        self.assertEqual(len(vertices), 6)
        self.assertEqual(faces.tolist(), [[0, 1, 2], [3, 4, 5]])

    def test_merge_parts_of_nothing_is_empty(self):
        vertices, faces = bake._merge_parts([])
        self.assertEqual((len(vertices), len(faces)), (0, 0))


class TestIsNoCollision(unittest.TestCase):
    def test_component_disables_collision(self):
        self.assertTrue(bake._is_no_collision({"collision": {"enabled": "ECollisionEnabled::NoCollision"}}, None))
        self.assertTrue(bake._is_no_collision({"collision": {"profile": "NoCollision"}}, None))

    def test_component_setting_wins_over_mesh_default(self):
        mesh = {"collision": {"default_profile": "NoCollision"}}
        self.assertFalse(bake._is_no_collision({"collision": {"profile": "BlockAll"}}, mesh))

    def test_mesh_default_applies_when_component_sets_nothing(self):
        self.assertTrue(bake._is_no_collision({}, {"collision": {"default_profile": "NoCollision"}}))
        self.assertFalse(bake._is_no_collision({}, {"collision": {"default_profile": "BlockAll"}}))


class TestIsMapBoundary(unittest.TestCase):
    def test_boundary_by_collision_object_type(self):
        component = {"collision": {"object_type": "ECollisionChannel::ECC_GameTraceChannel7"}}
        self.assertTrue(bake._is_map_boundary(component))

    def test_boundary_by_mesh_name(self):
        for mesh in ("/Game/Maps/EM1/SM_EM1_MapBoundaries.SM_EM1_MapBoundaries",
                     "/Game/Maps/Tortuga/SM_TortugaMapBorders.SM_TortugaMapBorders",
                     "/Game/BlockoutToolsAssets/SM_FiringRangeBoundaries.SM_FiringRangeBoundaries",
                     "/Game/BlockoutToolsAssets/SM_Fade.SM_Fade",
                     "/Game/BlockoutToolsAssets/SM_Fade_02.SM_Fade_02",
                     "/Game/Maps/Terminus_v1/SM_GameplayBoard_Main.SM_GameplayBoard_Main"):
            self.assertTrue(bake._is_map_boundary({"mesh": mesh}), mesh)

    def test_meshes_that_only_sound_like_a_boundary_are_not(self):
        for mesh in ("/Game/Art/SM_ConcretePlatform_Border_02_Straight.SM_ConcretePlatform_Border_02_Straight",
                     "/Game/Art/SM_TM_PlatformEdge_Top_20m.SM_TM_PlatformEdge_Top_20m",
                     "/Game/Art/SM_FadeOutPlane.SM_FadeOutPlane",
                     "/Game/Art/SM_LowerLaneBorderEnd.SM_LowerLaneBorderEnd"):
            self.assertFalse(bake._is_map_boundary({"mesh": mesh}), mesh)

    def test_other_components_are_not_boundaries(self):
        self.assertFalse(bake._is_map_boundary({"collision": {"object_type": "ECollisionChannel::ECC_WorldStatic"}}))
        self.assertFalse(bake._is_map_boundary({"mesh": None}))
        self.assertFalse(bake._is_map_boundary({}))


class TestEnclosingVolumeFlags(unittest.TestCase):
    NAVMESH = (np.array([0.0, 0.0, 0.0]), np.array([1000.0, 1000.0, 200.0]))

    def _flags(self, bounds, hulls):
        return bake.enclosing_volume_flags(np.array(bounds, dtype=float), np.array(hulls), *self.NAVMESH).tolist()

    def test_slab_above_the_navmesh_is_the_ceiling(self):
        self.assertEqual(self._flags([box([-100, -100, 500], [1100, 1100, 600])], [1]), [bake.FLAG_MAP_CEILING])

    def test_ceiling_with_stray_navmesh_on_top_of_it(self):
        self.assertEqual(self._flags([box([-100, -100, 150], [1100, 1100, 160])], [1]), [bake.FLAG_MAP_CEILING])

    def test_volume_in_pieces_around_the_navmesh_is_the_wall(self):
        self.assertEqual(self._flags([box([-100, -100, 0], [1100, 1100, 600])], [12]), [bake.FLAG_MAP_BOUNDARY])

    def test_volume_covering_part_of_the_map_is_neither(self):
        self.assertEqual(self._flags([box([0, 0, 0], [400, 1000, 600]), box([0, 0, 500], [400, 1000, 600])], [12, 1]), [0, 0])

    def test_one_piece_level_with_the_navmesh_is_neither(self):
        self.assertEqual(self._flags([box([-100, -100, -500], [1100, 1100, 100])], [1]), [0])

    def test_no_volumes(self):
        self.assertEqual(self._flags(np.zeros((0, 2, 3)), np.zeros(0, dtype=int)), [])


def write_arena(export_dir):
    """A small map: a mesh, hidden crates, a dynamic-level brush, a landscape, level instances."""
    os.makedirs(os.path.join(export_dir, "assets"))
    with open(os.path.join(export_dir, "assets", "tetra.uemodel"), "wb") as model_file:
        model_file.write(build_model(TETRA_VERTICES, TETRA_INDICES))

    heights = np.full((3, 5), 32768 + 128, dtype="<u2")
    os.makedirs(os.path.join(export_dir, "maps", "Arena_landscape"))
    heights.tofile(os.path.join(export_dir, "maps", "Arena_landscape", "land.r16"))
    landscape = {
        "heightfield": "maps/Arena_landscape/land.r16", "width": 5, "height": 3, "origin": [10, 20],
        "z_offset": 32768, "z_scale": 1 / 128, "component_size_quads": 2, "components": [[0, 0]],
    }
    levels = [
        {"index": 0, "name": "Arena", "kind": "persistent", "parent": None},
        {"index": 1, "name": "Arena_Spearhead", "kind": "streaming_dynamic", "parent": 0},
        {"index": 2, "name": "LI_Half", "kind": "level_instance", "parent": 0},
        {"index": 3, "name": "LI_Probe", "kind": "level_instance", "parent": 1},
    ]
    actors = [
        {"id": 0, "level": 0, "name": "Wall", "class": "StaticMeshActor", "components": [
            {"name": "Mesh", "kind": "static_mesh", "mesh": MESH, "world": moved(1000, 0, 0, 2.0)}]},
        {"id": 1, "level": 0, "name": "Crates", "class": "Actor", "hidden": True, "components": [
            {"name": "ISM", "kind": "instanced_static_mesh", "mesh": CRATE, "world": IDENTITY,
             "instances": [[0, 0, 0, 0, 0, 0, 1, 1, 1, 1], [500, 0, 0, 0, 0, 0, 1, 1, 1, 1]]}]},
        {"id": 2, "level": 1, "name": "Blocker", "class": "BlockingVolume", "class_chain": ["BlockingVolume", "Volume"], "components": [
            {"name": "Brush", "kind": "brush", "world": IDENTITY, "collision": {"profile": "NoCollision"},
             "convex": [{"vertices": TETRA_VERTICES, "indices": TETRA_INDICES}]}]},
        {"id": 3, "level": 0, "name": "Land", "class": "Landscape", "world": moved(0, 0, 0, 100.0),
         "landscape": landscape, "components": []},
        {"id": 4, "level": 0, "name": "Ghost", "class": "StaticMeshActor", "components": [
            {"name": "Mesh", "kind": "static_mesh", "mesh": "/Game/SM_Missing.SM_Missing", "world": IDENTITY}]},
        {"id": 5, "level": 2, "name": "HalfWall", "class": "StaticMeshActor", "components": [
            {"name": "Mesh", "kind": "static_mesh", "mesh": MESH, "world": IDENTITY}]},
        {"id": 6, "level": 3, "name": "ProbeBase", "class": "StaticMeshActor", "components": [
            {"name": "Mesh", "kind": "static_mesh", "mesh": MESH, "world": IDENTITY}]},
        {"id": 7, "level": 0, "name": "default_reference_static_mesh_instancer_0_0", "class": "Actor", "components": [
            {"name": "InstancedStaticMeshComponent_0", "kind": "instanced_static_mesh", "mesh": HOUDINI_PLACEHOLDER,
             "world": IDENTITY, "instances": [[0, 0, 0, 0, 0, 0, 1, 1, 1, 1]]}]},
    ]
    meshes = {
        MESH: {"model": "assets/tetra.uemodel"},
        CRATE: {"model": "assets/tetra.uemodel"},
        "/Game/SM_Missing.SM_Missing": {"missing": True},
        HOUDINI_PLACEHOLDER: {"missing": True},
    }
    write_scene(export_dir, "Arena", levels, actors, meshes=meshes)
    return scene.Scene(export_dir, "Arena")


class TestBake(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.baked = bake.bake(write_arena(self.temp_dir.name), landscape_stride=1)

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_bake_lists_one_instance_per_placement(self):
        self.assertEqual(self.baked["inst_actor"].tolist(), [0, 1, 1, 2, 3, 5, 6])
        self.assertEqual(self.baked["inst_kind"].tolist(), [
            bake.KIND_STATIC_MESH, bake.KIND_INSTANCED_MESH, bake.KIND_INSTANCED_MESH, bake.KIND_BRUSH, bake.KIND_LANDSCAPE,
            bake.KIND_STATIC_MESH, bake.KIND_STATIC_MESH])

    def test_bake_shares_a_mesh_between_its_instances(self):
        self.assertEqual(self.baked["inst_mesh"][1], self.baked["inst_mesh"][2])
        self.assertEqual(self.baked["mesh_names"].count(CRATE), 1)

    def test_bake_flags(self):
        flags = self.baked["inst_flags"].tolist()
        self.assertEqual(flags[0], 0)
        self.assertEqual(flags[1], bake.FLAG_HIDDEN)
        self.assertEqual(flags[3], bake.FLAG_NO_COLLISION | bake.FLAG_DYNAMIC_LEVEL)
        # A level instance is as dynamic as the level it is placed in.
        self.assertEqual(flags[5:], [0, bake.FLAG_DYNAMIC_LEVEL])

    def test_bake_reports_meshes_without_geometry(self):
        self.assertTrue(any("SM_Missing" in warning for warning in self.baked["warnings"]))

    def test_bake_skips_houdini_placeholder_silently(self):
        # Houdini Engine's stand-in mesh isn't in the game files: no instance and no warning
        self.assertFalse(any("HoudiniEngine" in warning for warning in self.baked["warnings"]))
        self.assertNotIn(HOUDINI_PLACEHOLDER, self.baked["mesh_names"])

    def test_bake_instance_bounds_are_in_world_space(self):
        bounds = self.baked["inst_aabb"]
        np.testing.assert_allclose(bounds[0], [[1000, 0, 0], [1200, 200, 200]])
        np.testing.assert_allclose(bounds[2], [[500, 0, 0], [600, 100, 100]])

    def test_bake_landscape_grid(self):
        land = self.baked["mesh_names"].index("maps/Arena_landscape/land.r16")
        offsets = self.baked["mesh_vertex_offset"]
        vertices = self.baked["mesh_vertices"][offsets[land]:offsets[land + 1]]
        np.testing.assert_allclose(vertices.min(axis=0), [10, 20, 1])
        np.testing.assert_allclose(vertices.max(axis=0), [14, 22, 1])
        # Only the 2x2 quads under the one component are triangulated.
        self.assertEqual(int(self.baked["mesh_face_offset"][land + 1] - self.baked["mesh_face_offset"][land]), 8)
        np.testing.assert_allclose(self.baked["inst_aabb"][4], [[1000, 2000, 100], [1400, 2200, 100]])

    def test_bake_without_navmesh(self):
        self.assertIsNone(self.baked["navmesh"])

    def test_level_mask_excludes_dynamic_levels_unless_named(self):
        self.assertEqual(bake.level_mask(self.baked).tolist(), [True, True, True, False, True, True, False])
        self.assertEqual(bake.level_mask(self.baked, ["Arena_Spearhead"]).tolist(), [True] * 7)

    def test_streaming_roots_follow_level_instances(self):
        self.assertEqual([root["name"] for root in bake.streaming_roots(self.baked)],
                         ["Arena", "Arena_Spearhead", "Arena", "Arena_Spearhead"])


class TestBakeBoundary(unittest.TestCase):
    """A map fenced in three ways at once: a wall mesh, a ring-shaped volume and a ceiling."""

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        export_dir = self.temp_dir.name
        os.makedirs(os.path.join(export_dir, "assets"))
        with open(os.path.join(export_dir, "assets", "fade.uemodel"), "wb") as model_file:
            model_file.write(build_model([[-100, -100, 0], [100, -100, 0], [100, -100, 100]], [0, 1, 2]))
        os.makedirs(os.path.join(export_dir, "maps", "Arena_navmesh"))
        with open(os.path.join(export_dir, "maps", "Arena_navmesh", "mech.json"), "w", encoding="utf-8") as navmesh_file:
            json.dump({"tiles": [{"vertices": [[-80, -80, 0], [80, 80, 20]]}]}, navmesh_file)

        def volume(actor_id, name, hulls):
            return {"id": actor_id, "level": 0, "name": name, "class": "BlockingVolume", "class_chain": ["BlockingVolume", "Volume"],
                    "components": [{"name": "Brush", "kind": "brush", "world": IDENTITY, "convex": hulls}]}

        fade = "/Game/BlockoutToolsAssets/SM_Fade_02.SM_Fade_02"
        actors = [
            {"id": 0, "level": 0, "name": "Nav", "class": "RecastNavMesh", "navmesh": {"file": "maps/Arena_navmesh/mech.json"}, "components": []},
            {"id": 1, "level": 0, "name": "Fade", "class": "StaticMeshActor", "components": [
                {"name": "Mesh", "kind": "static_mesh", "mesh": fade, "world": IDENTITY}]},
            volume(2, "Ring", [box_hull([-100, 90, 0], [100, 100, 50]), box_hull([-100, -100, 0], [-90, 100, 50])]),
            volume(3, "Ceiling", [box_hull([-100, -100, 300], [100, 100, 310])]),
            volume(4, "Pillar", [box_hull([0, 0, 0], [10, 10, 50]), box_hull([0, 0, 50], [10, 10, 90])]),
        ]
        levels = [{"index": 0, "name": "Arena", "kind": "persistent", "parent": None}]
        write_scene(export_dir, "Arena", levels, actors, meshes={fade: {"model": "assets/fade.uemodel"}})
        self.baked = bake.bake(scene.Scene(export_dir, "Arena"))

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_flags(self):
        self.assertEqual(self.baked["inst_flags"].tolist(), [bake.FLAG_MAP_BOUNDARY, bake.FLAG_MAP_BOUNDARY, bake.FLAG_MAP_CEILING, 0])

    def test_boundary_mask_is_the_wall_without_the_ceiling(self):
        self.assertEqual(bake.boundary_mask(self.baked).tolist(), [True, True, False, False])

    def test_navmesh_bounds_are_kept(self):
        low, high = self.baked["navmesh"]
        np.testing.assert_allclose(low, [-80, -80, 0])
        np.testing.assert_allclose(high, [80, 80, 20])


if __name__ == "__main__":
    unittest.main()
