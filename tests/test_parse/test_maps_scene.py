import json
import math
import os
import sys
import tempfile
import unittest

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from maps_fixtures import write_scene  # noqa: E402
from maps import scene  # noqa: E402

LEVELS = [
    {"index": 0, "name": "Arena", "kind": "persistent", "parent": None},
    {"index": 1, "name": "Arena_Geo", "kind": "streaming_always_loaded", "parent": 0},
    {"index": 2, "name": "LI_Prefab", "kind": "level_instance", "parent": 1},
    {"index": 3, "name": "Arena_Spearhead", "kind": "streaming_dynamic", "parent": 0},
    {"index": 4, "name": "LI_Prefab", "kind": "level_instance", "parent": 3},
    {"index": 5, "name": "Arena_Gone", "kind": "streaming_dynamic", "parent": 0, "missing": True},
    {"index": 6, "name": "LI_Half", "kind": "level_instance", "parent": 0},
]


class TestTransforms(unittest.TestCase):
    def test_quat_matrix_identity(self):
        np.testing.assert_allclose(scene.quat_matrix([0, 0, 0, 1]), np.eye(3))

    def test_quat_matrix_yaw_turns_x_into_y(self):
        half = math.radians(90) / 2
        rotated = scene.quat_matrix([0, 0, math.sin(half), math.cos(half)]) @ np.array([1.0, 0.0, 0.0])
        np.testing.assert_allclose(rotated, [0, 1, 0], atol=1e-12)

    def test_trs_matrix_scales_then_rotates_then_translates(self):
        half = math.radians(90) / 2
        matrix = scene.trs_matrix([10, 20, 30], [0, 0, math.sin(half), math.cos(half)], [2, 3, 4])
        np.testing.assert_allclose(scene.apply(matrix, np.array([[1.0, 0.0, 0.0]])), [[10, 22, 30]], atol=1e-12)
        np.testing.assert_allclose(scene.apply(matrix, np.array([[0.0, 0.0, 1.0]])), [[10, 20, 34]], atol=1e-12)

    def test_instance_matrix_matches_transform_matrix(self):
        transform = {"t": [1, 2, 3], "q": [0.1, 0.2, 0.3, 0.927], "s": [1, 2, 3]}
        instance = transform["t"] + transform["q"] + transform["s"]
        np.testing.assert_allclose(scene.instance_matrix(instance), scene.transform_matrix(transform))

    def test_forward_is_local_x_axis(self):
        half = math.radians(180) / 2
        direction = scene.forward({"t": [0, 0, 0], "q": [0, 0, math.sin(half), math.cos(half)], "s": [5, 5, 5]})
        np.testing.assert_allclose(direction, [-1, 0, 0], atol=1e-12)


class TestScene(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        actors = [
            {"id": 0, "level": 0, "name": "A", "class": "Actor", "components": []},
            {"id": 1, "level": 4, "name": "B", "class": "Actor", "template": "T", "props": {"Body": {"Profile": "Custom"}, "Order": 2}, "components": []},
        ]
        templates = {"T": {"Body": {"Profile": "BlockAll", "Enabled": True}, "Score": 5}}
        write_scene(self.temp_dir.name, "Arena", LEVELS, actors, templates)
        self.scene = scene.Scene(self.temp_dir.name, "Arena")

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_navmesh_bounds_span_every_navmesh(self):
        actors = []
        for index, vertices in enumerate(([[0, 0, 0], [100, 50, 10]], [[-20, 10, 5], [30, 300, 8]])):
            navmesh = f"maps/Arena/navmesh{index}.json"
            with open(os.path.join(self.temp_dir.name, navmesh), "w", encoding="utf-8") as navmesh_file:
                json.dump({"tiles": [{"vertices": vertices}]}, navmesh_file)
            actors.append({"navmesh": {"file": navmesh}})
        low, high = self.scene.navmesh_bounds(actors)
        np.testing.assert_allclose(low, [-20, 0, 0])
        np.testing.assert_allclose(high, [100, 300, 10])

    def test_navmesh_bounds_of_a_map_without_navmesh(self):
        self.assertIsNone(self.scene.navmesh_bounds())

    def test_actors_are_streamed_in_order(self):
        self.assertEqual([actor["id"] for actor in self.scene.actors()], [0, 1])

    def test_streaming_root_of_nested_level_instance(self):
        self.assertEqual(self.scene.streaming_root(4)["name"], "Arena_Spearhead")
        self.assertEqual(self.scene.streaming_root(2)["name"], "Arena_Geo")
        self.assertEqual(self.scene.streaming_root(0)["name"], "Arena")

    def test_streaming_root_of_a_streaming_level_is_itself(self):
        self.assertEqual(self.scene.streaming_root(3)["name"], "Arena_Spearhead")

    def test_level_instance_in_the_persistent_level_belongs_to_it(self):
        self.assertEqual(self.scene.streaming_root(6)["name"], "Arena")

    def test_active_levels_without_dynamic_levels(self):
        self.assertEqual(self.scene.active_levels().tolist(), [True, True, True, False, False, False, True])

    def test_active_levels_with_named_dynamic_level(self):
        self.assertEqual(self.scene.active_levels(["Arena_Spearhead"]).tolist(), [True, True, True, True, True, False, True])

    def test_level_names_skips_missing_levels(self):
        self.assertEqual(self.scene.level_names("streaming_dynamic"), ["Arena_Spearhead"])

    def test_effective_props_merges_structs_field_by_field(self):
        actor = list(self.scene.actors())[1]
        self.assertEqual(self.scene.effective_props(actor), {"Body": {"Profile": "Custom", "Enabled": True}, "Score": 5, "Order": 2})

    def test_effective_props_does_not_modify_the_template(self):
        actor = list(self.scene.actors())[1]
        self.scene.effective_props(actor)
        self.assertEqual(self.scene.templates["T"]["Body"]["Profile"], "BlockAll")

    def test_effective_props_without_template(self):
        self.assertEqual(self.scene.effective_props({"props": {"X": 1}}), {"X": 1})


class TestObjectName(unittest.TestCase):
    def test_object_name_of_level_actor_reference(self):
        reference = {"ObjectName": "BP_Start_C'Arena_Spearhead:PersistentLevel.BP_Start_C_1'", "ObjectPath": "/Game/Maps/Arena_Spearhead.2"}
        self.assertEqual(scene.object_name(reference), "BP_Start_C_1")

    def test_object_name_of_asset_reference(self):
        self.assertEqual(scene.object_name({"ObjectName": "Texture2D'T_Icon'", "ObjectPath": "/Game/UI/T_Icon.0"}), "T_Icon")

    def test_object_name_of_non_reference(self):
        self.assertIsNone(scene.object_name({"X": 1}))
        self.assertIsNone(scene.object_name(3))


if __name__ == "__main__":
    unittest.main()
