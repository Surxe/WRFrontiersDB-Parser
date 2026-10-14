import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from maps_fixtures import IDENTITY, write_scene  # noqa: E402
from maps import objectives, scene  # noqa: E402


def reference(class_name, level, name):
    return {"ObjectName": f"{class_name}'{level}:PersistentLevel.{name}'", "ObjectPath": f"/Game/Maps/{level}.1"}


class TestClassify(unittest.TestCase):
    def test_classify_blueprint_class(self):
        self.assertEqual(objectives.classify(["BP_WarpProbe_C", "SSpawnPointBase", "Actor"]), "warp_probe")

    def test_classify_by_native_ancestor(self):
        self.assertEqual(objectives.classify(["BP_TeamPlayerStart_C", "STeamPlayerStart", "PlayerStart", "Actor"]), "spawn")

    def test_classify_prefers_the_most_derived_class(self):
        self.assertEqual(objectives.classify(["BP_PowerUpSpawner_C", "SSpawner", "Actor"]), "powerup_spawner")

    def test_classify_unknown(self):
        self.assertEqual(objectives.classify(["StaticMeshActor", "Actor"]), "other")


class TestExtract(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        levels = [
            {"index": 0, "name": "Arena", "kind": "persistent", "parent": None, "world_settings_actor": 0},
            {"index": 1, "name": "Arena_Spearhead", "kind": "streaming_dynamic", "parent": 0},
            {"index": 2, "name": "Arena_Sunset_Light", "kind": "streaming_dynamic", "parent": 0},
        ]
        start = {
            "id": 2, "level": 1, "name": "Start_1", "label": "Start", "class": "BP_BlockablePlayerStart_C",
            "class_chain": ["BP_BlockablePlayerStart_C", "PlayerStart", "Actor"], "template": "Start",
            "world": {"t": [100, 200, 300], "q": [0, 0, 0.7071067811865476, 0.7071067811865476], "s": [1, 1, 1]},
            "props": {"TeamId": {"TeamId": 1}},
            "components": [
                {"name": "Capsule", "class": "CapsuleComponent", "kind": "capsule",
                 "world": {"t": [100, 200, 300], "q": [0, 0, 0, 1], "s": [2, 2, 3]},
                 "shape": {"capsule_radius": 22.0, "capsule_half_height": 44.0}},
                {"name": "Logic", "class": "SFocusComponent", "kind": "logic"},
            ],
        }
        probe = {
            "id": 3, "level": 1, "name": "Probe_0", "class": "BP_WarpProbe_C", "class_chain": ["BP_WarpProbe_C", "Actor"],
            "template": "Probe", "world": IDENTITY,
            "props": {"Order": 2, "PlayerSpawns": [reference("BP_BlockablePlayerStart_C", "Arena_Spearhead", "Start_1")]},
            "components": [
                {"name": "Zone", "class": "StaticMeshComponent", "kind": "static_mesh", "mesh": "/Game/SM_Cylinder.SM_Cylinder",
                 "world": {"t": [0, 0, 0], "q": [0, 0, 0, 1], "s": [10, 10, 2]}, "hidden_in_game": True},
            ],
        }
        actors = [
            {"id": 0, "level": 0, "name": "Settings", "class": "SWorldSettings", "class_chain": ["SWorldSettings"],
             "world": IDENTITY, "props": {"LocalizedName": {"SourceString": "The Arena"}}, "components": []},
            {"id": 1, "level": 1, "name": "Settings", "class": "SWorldSettings", "class_chain": ["SWorldSettings"],
             "world": IDENTITY, "components": []},
            start,
            probe,
            {"id": 4, "level": 2, "name": "Sun", "class": "DirectionalLight", "class_chain": ["DirectionalLight", "Actor"],
             "world": IDENTITY, "components": []},
        ]
        templates = {
            "Start": {"TeamId": {"TeamId": 0}, "UberGraphFrame": {}},
            "Probe": {"Score": 5, "CaptureSound": reference("AkAudioEvent", "Sounds", "AKE_Capture"),
                      "Root": reference("SceneComponent", "Arena_Spearhead", "Probe_0.Zone")},
        }
        meshes = {"/Game/SM_Cylinder.SM_Cylinder": {"bounds": {"origin": [0, 0, 50], "box_extent": [50, 50, 50], "sphere_radius": 87}}}
        write_scene(self.temp_dir.name, "Arena", levels, actors, templates, meshes)
        self.extracted = objectives.extract(scene.Scene(self.temp_dir.name, "Arena"))

    def tearDown(self):
        self.temp_dir.cleanup()

    def _point(self, name):
        return next(point for point in self.extracted["modes"]["Spearhead"]["points"] if point["name"] == name)

    def test_extract_names_modes_after_their_sublevel(self):
        self.assertEqual(list(self.extracted["modes"]), ["Spearhead"])
        self.assertEqual(self.extracted["modes"]["Spearhead"]["level"], "Arena_Spearhead")
        self.assertEqual(self.extracted["modes"]["Spearhead"]["counts"], {"spawn": 1, "warp_probe": 1})

    def test_extract_reads_display_name_from_world_settings(self):
        self.assertEqual(self.extracted["display_name"], "The Arena")

    def test_extract_spawn_team_overrides_the_template(self):
        self.assertEqual(self._point("Start_1")["team"], 1)

    def test_extract_spawn_facing(self):
        start = self._point("Start_1")
        self.assertAlmostEqual(start["yaw_degrees"], 90.0, places=5)
        self.assertEqual(start["position"], [100, 200, 300])

    def test_extract_capsule_zone_is_scaled_into_the_world(self):
        zone = self._point("Start_1")["zones"][0]
        self.assertEqual((zone["kind"], zone["radius"], zone["half_height"]), ("capsule", 44.0, 132.0))

    def test_extract_mesh_zone_uses_the_mesh_bounds(self):
        zone = self._point("Probe_0")["zones"][0]
        self.assertEqual(zone["half_extent"], [500.0, 500.0, 100.0])
        self.assertEqual(zone["local_center"], [0.0, 0.0, 100.0])
        self.assertTrue(zone["hidden"])

    def test_extract_links_point_at_actors_of_the_level(self):
        self.assertEqual(self._point("Probe_0")["links"], {"PlayerSpawns": ["Start_1"]})

    def test_extract_props_keep_values_and_drop_references(self):
        props = self._point("Probe_0")["props"]
        self.assertEqual(props, {"Order": 2, "Score": 5})
        self.assertNotIn("UberGraphFrame", self._point("Start_1")["props"])


if __name__ == "__main__":
    unittest.main()
