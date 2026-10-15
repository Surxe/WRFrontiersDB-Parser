import json
import os
import stat
import struct
import sys
import tempfile
import unittest
from pathlib import Path

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from maps_fixtures import IDENTITY, build_model, moved, write_scene  # noqa: E402
from maps import bake, cook, scene  # noqa: E402

TETRA_VERTICES = [[0, 0, 0], [100, 0, 0], [0, 100, 0], [0, 0, 100]]
TETRA_INDICES = [0, 1, 2, 0, 1, 3, 0, 2, 3, 1, 2, 3]
ROCK = "/Game/Art/SM_Rock.SM_Rock"
TREE = "/Game/Sparrow/Art/Environment/Foliage/Trees/SM_Tree.SM_Tree"
DRILL = "/Game/Art/SM_Drill.SM_Drill"
MODES = {"Spearhead": ["Spearhead", "Crusher"], "BeaconRush": ["BeaconRush"], "CTF": ["CTF"]}


def static_mesh(actor_id, level, mesh, world, **component):
    return {"id": actor_id, "level": level, "name": f"Actor{actor_id}", "class": "StaticMeshActor", "class_chain": ["StaticMeshActor"],
            "world": world, "components": [{"name": "Mesh", "class": "StaticMeshComponent", "kind": "static_mesh", "mesh": mesh, "world": world, **component}]}


def write_map(export_dir, exported_utc="2026-10-06T00:00:00Z"):
    """Arena: a rock in the playable box and one far outside it, a tree without collision,
    a hidden rock, a Spearhead sublevel with a drill mesh, a spawn and a probe, a Crusher sublevel."""
    os.makedirs(os.path.join(export_dir, "assets"), exist_ok=True)
    with open(os.path.join(export_dir, "assets", "tetra.uemodel"), "wb") as model_file:
        model_file.write(build_model(TETRA_VERTICES, TETRA_INDICES))
    os.makedirs(os.path.join(export_dir, "maps", "Arena", "navmesh"), exist_ok=True)
    with open(os.path.join(export_dir, "maps", "Arena", "navmesh", "mech.json"), "w", encoding="utf-8") as navmesh_file:
        json.dump({"tiles": [{"vertices": [[0, 0, 0], [10000, 10000, 1000]]}]}, navmesh_file)

    levels = [
        {"index": 0, "name": "Arena", "kind": "persistent", "parent": None},
        {"index": 1, "name": "Arena_Spearhead", "kind": "streaming_dynamic", "parent": 0},
        {"index": 2, "name": "arena_crusher", "kind": "streaming_dynamic", "parent": 0},
    ]
    no_collision = {"collision": {"profile": "NoCollision"}}
    actors = [
        {"id": 0, "level": 0, "name": "Nav", "class": "RecastNavMesh", "navmesh": {"file": "maps/Arena/navmesh/mech.json"}, "components": []},
        static_mesh(1, 0, ROCK, moved(1000, 2000, 0)),
        static_mesh(2, 0, ROCK, moved(900000, 0, 0)),
        static_mesh(3, 0, TREE, moved(3000, 3000, 0), **no_collision),
        static_mesh(4, 0, TREE, moved(3500, 3000, 0)),
        static_mesh(5, 0, ROCK, moved(5000, 5000, 0), hidden_in_game=True),
        static_mesh(6, 1, ROCK, moved(6000, 6000, 0)),
        static_mesh(7, 2, DRILL, moved(7000, 7000, 0)),
        {"id": 8, "level": 1, "name": "Start_1", "class": "BP_TeamPlayerStart_C", "class_chain": ["BP_TeamPlayerStart_C", "PlayerStart"],
         "world": {"t": [100.04, 200, 300], "q": [0, 0, 0.7071067811865476, 0.7071067811865476], "s": [1, 1, 1]},
         "props": {"TeamId": {"TeamId": 1}}, "components": []},
        {"id": 9, "level": 2, "name": "Drill_1", "class": "BP_Drill_C", "class_chain": ["BP_Drill_C", "SDrillActor"],
         "world": moved(7000, 7000, 0), "components": []},
    ]
    meshes = {mesh: {"model": "assets/tetra.uemodel"} for mesh in (ROCK, TREE, DRILL)}
    write_scene(export_dir, "Arena", levels, actors, meshes=meshes)
    scene_file = os.path.join(export_dir, "maps", "Arena", "scene.json")
    with open(scene_file, encoding="utf-8") as source:
        data = json.load(source)
    data["exported_utc"] = exported_utc
    with open(scene_file, "w", encoding="utf-8") as target:
        json.dump(data, target)


def fake_gltfpack(directory) -> Path:
    """Stands in for gltfpack: copies -i to -o and logs its options."""
    command = Path(directory) / "gltfpack"
    command.write_text("#!/bin/sh\n"
                       "while [ $# -gt 0 ]; do case $1 in -i) in=$2; shift;; -o) out=$2; shift;; *) echo \"$1\" >> \"$0.log\";; esac; shift; done\n"
                       "cp \"$in\" \"$out\"\n")
    command.chmod(command.stat().st_mode | stat.S_IXUSR)
    return command


def read_glb(glb_file):
    data = Path(glb_file).read_bytes()
    json_length = struct.unpack_from("<I", data, 12)[0]
    document = json.loads(data[20:20 + json_length])
    binary = data[28 + json_length:]

    def array(accessor_index, dtype, width):
        accessor = document["accessors"][accessor_index]
        view = document["bufferViews"][accessor["bufferView"]]
        return np.frombuffer(binary, dtype=dtype, count=accessor["count"] * width, offset=view["byteOffset"]).reshape(-1, width)

    return document, array


class TestMasks(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        write_map(self.temp_dir.name)
        self.baked = bake.bake(scene.Scene(self.temp_dir.name, "Arena"))
        self.by_actor = {int(actor): index for index, actor in enumerate(self.baked["inst_actor"])}

    def tearDown(self):
        self.temp_dir.cleanup()

    def _actors(self, mask):
        return sorted(int(actor) for actor in self.baked["inst_actor"][mask])

    def test_playable_box_is_the_navmesh_with_a_margin(self):
        low, high = cook.playable_box(self.baked)
        np.testing.assert_allclose(low, [-1200, -1200, -1200])
        np.testing.assert_allclose(high, [11200, 11200, 2200])

    def test_drawn_leaves_out_hidden_and_far_instances(self):
        drawn = cook.drawn_mask(self.baked, cook.playable_box(self.baked))
        self.assertEqual(self._actors(drawn), [1, 3, 4, 6, 7])

    def test_foliage_is_foliage_without_collision(self):
        self.assertEqual(self._actors(cook.foliage_mask(self.baked)), [3])

    def test_sublevel_mask_ignores_case(self):
        self.assertEqual(self._actors(cook.sublevel_mask(self.baked, ["Arena_Crusher"])), [7])
        self.assertEqual(self._actors(cook.sublevel_mask(self.baked, ["Arena_Spearhead", "Arena_Crusher"])), [6, 7])

    def test_map_levels_spells_names_as_the_scene_does(self):
        levels = scene.Scene(self.temp_dir.name, "Arena").levels
        self.assertEqual(cook.map_levels("Arena", ["Spearhead", "Crusher", "PostCombat"], levels), ["Arena_Spearhead", "arena_crusher"])


class TestInstancedGlb(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        write_map(self.temp_dir.name)
        self.baked = bake.bake(scene.Scene(self.temp_dir.name, "Arena"))

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_one_mesh_per_library_mesh_one_node_per_instance(self):
        mask = np.isin(self.baked["inst_actor"], [1, 6])
        data, counts = cook.instanced_glb(self.baked, mask)
        glb_file = Path(self.temp_dir.name) / "map.glb"
        glb_file.write_bytes(data)
        document, array = read_glb(glb_file)
        self.assertEqual(len(document["meshes"]), 1)
        self.assertEqual(len(document["nodes"]), 2)
        self.assertEqual(counts, {"instances": 2, "unique_meshes": 1, "unique_triangles": 4, "triangles": 8})
        self.assertEqual(cook.glb_triangles(glb_file), (4, 8))

        primitive = document["meshes"][0]["primitives"][0]
        # Unreal cm (x, y, z) -> glTF m (x, z, y); the swap reverses the winding.
        np.testing.assert_allclose(array(primitive["attributes"]["POSITION"], "<f4", 3),
                                   [[0, 0, 0], [1, 0, 0], [0, 0, 1], [0, 1, 0]])
        self.assertEqual(array(primitive["indices"], "<u4", 1).reshape(-1, 3)[0].tolist(), [0, 2, 1])
        matrix = np.array(document["nodes"][0]["matrix"]).reshape(4, 4).T
        np.testing.assert_allclose(matrix[:3, 3], [10, 0, 20])
        np.testing.assert_allclose(np.linalg.norm(array(primitive["attributes"]["NORMAL"], "<f4", 3), axis=1), 1, atol=1e-6)

    def test_glb_triangles_counts_instancing_copies(self):
        document = {
            "accessors": [{"count": 30}, {"count": 7}],
            "meshes": [{"primitives": [{"indices": 0}]}],
            "nodes": [{"mesh": 0, "extensions": {"EXT_mesh_gpu_instancing": {"attributes": {"TRANSLATION": 1}}}}, {"mesh": 0}, {}],
        }
        glb_file = Path(self.temp_dir.name) / "doc.glb"
        glb_file.write_bytes(cook._glb(document, b""))
        self.assertEqual(cook.glb_triangles(glb_file), (10, 80))


class TestPins(unittest.TestCase):
    def _point(self, kind, props=None, zones=(), team=None):
        point = {"type": kind, "position": [1.04, 2.06, 3.0], "yaw_degrees": 89.96, "props": props or {}, "zones": list(zones)}
        if team is not None:
            point["team"] = team
        return point

    def test_spawn(self):
        self.assertEqual(cook.slim_point(self._point("spawn", team=1)),
                         {"type": "spawn", "team": 1, "position": [1.0, 2.1, 3.0], "yaw": 90.0})

    def test_probe_order_and_capture_zone(self):
        zone = {"component": "CaptureZoneComponent", "half_extent": [5000.0, 5000.0, 6250.0]}
        pin = cook.slim_point(self._point("warp_probe", {"Order": 2}, [zone]))
        self.assertEqual((pin["order"], pin["zone_radius"]), (2, 5000.0))

    def test_beacon_display_order(self):
        self.assertEqual(cook.slim_point(self._point("beacon", {"DisplayOrder": 3}))["order"], 3)

    def test_ctf_team_from_owning_team(self):
        self.assertEqual(cook.slim_point(self._point("ctf_core", {"OwningTeamId": {"TeamId": 0}}))["team"], 0)

    def test_powerup_ids_are_the_spawned_blueprints(self):
        props = {"SpawnableActors": [
            {"SpawnableActor": {"ObjectName": "BlueprintGeneratedClass'BP_PowerUp_DoubleDamage_C'",
                                "ObjectPath": "/Game/Sparrow/Mechanics/PowerUps/Personal/DoubleDamage/BP_PowerUp_DoubleDamage.0"}},
            {"SpawnableActor": {"ObjectPath": "/Game/Sparrow/Mechanics/PowerUps/Teams/Shield/BP_PowerUp_TeamShield.0"}},
            {"SpawnableActor": None},
        ]}
        pin = cook.slim_point(self._point("powerup_spawner", props))
        self.assertEqual(pin["powerup_ids"], ["BP_PowerUp_DoubleDamage", "BP_PowerUp_TeamShield"])

    def test_mode_pins_take_shared_sublevels_and_skip_other_types(self):
        objectives = {"modes": {
            "Spearhead": {"level": "Arena_Spearhead", "points": [self._point("spawn", team=0), self._point("other")]},
            "Crusher": {"level": "Arena_Crusher", "points": [self._point("drill")]},
            "BeaconRush": {"level": "Arena_BeaconRush", "points": [self._point("beacon")]},
        }}
        pins = cook.mode_pins(objectives, ["Arena_Spearhead", "arena_crusher"])
        self.assertEqual([pin["type"] for pin in pins], ["spawn", "drill"])


class TestCookMap(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.root = Path(self.temp_dir.name)
        self.export_dir = self.root / "export"
        write_map(str(self.export_dir))
        self.gltfpack = fake_gltfpack(self.root)

    def tearDown(self):
        self.temp_dir.cleanup()

    def _cook(self, out="out", cache="cache"):
        return cook.cook_map(self.export_dir, "Arena", MODES, self.root / out, self.gltfpack, self.root / cache)

    def test_cook_writes_base_foliage_mode_geometry_and_pins(self):
        pins = self._cook()
        out = self.root / "out"
        self.assertEqual(sorted(path.name for path in out.iterdir()),
                         ["Arena.Spearhead.glb", "Arena.foliage.glb", "Arena.glb", "Arena.json"])
        self.assertEqual(pins["files"], {"base": "Arena.glb", "foliage": "Arena.foliage.glb"})
        self.assertEqual(list(pins["modes"]), ["Spearhead"])
        spearhead = pins["modes"]["Spearhead"]
        self.assertEqual((spearhead["sublevels"], spearhead["file"]), (["Arena_Spearhead", "arena_crusher"], "Arena.Spearhead.glb"))
        self.assertEqual([pin["type"] for pin in spearhead["pins"]], ["spawn", "drill"])
        self.assertEqual(json.loads((out / "Arena.json").read_text()), pins)
        # The rock and the tree that collides (a tree without collision is foliage).
        self.assertEqual(cook.glb_triangles(out / "Arena.glb"), (8, 8))
        self.assertEqual(cook.glb_triangles(out / "Arena.Spearhead.glb"), (8, 8))  # its rock and the shared drill
        self.assertIn("-se", (self.root / "gltfpack.log").read_text().split())

    def test_unchanged_map_is_copied_from_the_cache(self):
        first = self._cook()
        os.remove(self.root / "gltfpack.log")
        # A re-export changes the export time, not the map.
        write_map(str(self.export_dir.parent / "export2"), exported_utc="2026-10-07T00:00:00Z")
        self.export_dir = self.export_dir.parent / "export2"
        second = self._cook(out="out2")
        self.assertEqual(second, first)
        self.assertFalse((self.root / "gltfpack.log").exists())
        for name in cook.cooked_files(first):
            self.assertEqual((self.root / "out2" / name).read_bytes(), (self.root / "out" / name).read_bytes())

    def test_changed_mesh_is_cooked_again(self):
        first = self._cook()
        with open(self.export_dir / "assets" / "tetra.uemodel", "wb") as model_file:
            model_file.write(build_model([[0, 0, 0], [200, 0, 0], [0, 200, 0], [0, 0, 200]], TETRA_INDICES))
        second = self._cook(out="out2")
        self.assertNotEqual(second["input_hash"], first["input_hash"])
        self.assertTrue((self.root / "gltfpack.log").exists())


if __name__ == "__main__":
    unittest.main()
