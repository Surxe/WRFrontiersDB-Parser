import json
import os
import sys
import tempfile
import unittest
from pathlib import Path

src_path = os.path.join(os.path.dirname(__file__), '..', '..', 'src')
parse_path = os.path.join(src_path, 'parse')
sys.path.insert(0, src_path)
sys.path.insert(0, parse_path)

from maps import physics  # noqa: E402


def write(path: Path, text: str):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


class TestMapPhysics(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        config = self.root / "config"
        write(config / "Engine/Config/BaseEngine.ini",
              "[/Script/Engine.PhysicsSettings]\nDefaultGravityZ=-980.0\nDefaultTerminalVelocity=4000.0\n")
        write(config / "WRFrontiers/Config/DefaultEngine.ini",
              "[/Script/Engine.OtherSettings]\nDefaultGravityZ=1.0\n\n"
              "[/Script/Engine.PhysicsSettings]\n; a comment\n+PhysicalSurfaces=(Type=SurfaceType1)\n"
              "DefaultGravityZ=-1400.000000\n")

    def tearDown(self):
        self.tmp.cleanup()

    def write_map(self, map_id, world_settings_props):
        map_dir = self.root / "maps" / map_id
        levels = [{"index": 0, "kind": "persistent", "world_settings_actor": 7},
                  {"index": 1, "kind": "streaming_always_loaded", "world_settings_actor": 9}]
        write(map_dir / "scene.json", json.dumps({"levels": levels}))
        actors = [{"id": 9, "props": {"bGlobalGravitySet": True, "GlobalGravityZ": -1.0}},  # a sublevel's: ignored
                  {"id": 7, "props": world_settings_props}]
        write(map_dir / "actors.jsonl", "\n".join(json.dumps(actor) for actor in actors) + "\n")

    def test_project_ini_overrides_engine_base_in_its_section_only(self):
        self.assertEqual(physics.physics_settings(self.root),
                         {"DefaultGravityZ": -1400.0, "DefaultTerminalVelocity": 4000.0})

    def test_map_without_override_uses_physics_settings(self):
        self.write_map("Plain", {"KillZ": -1000.0})
        self.assertEqual(physics.parse_map_physics(self.root, "Plain", physics.physics_settings(self.root)),
                         {"GravityZ": -1400.0, "TerminalVelocity": 4000.0, "KillZ": -1000.0})

    def test_persistent_world_settings_override_gravity(self):
        self.write_map("Moon", {"bGlobalGravitySet": True, "GlobalGravityZ": -300.0})
        self.assertEqual(physics.parse_map_physics(self.root, "Moon", physics.physics_settings(self.root)),
                         {"GravityZ": -300.0, "TerminalVelocity": 4000.0})

    def test_missing_setting_is_left_out(self):
        (self.root / "config/Engine/Config/BaseEngine.ini").unlink()
        settings = physics.physics_settings(self.root)
        self.assertEqual(settings, {"DefaultGravityZ": -1400.0})
        self.assertEqual(physics.map_physics({}, settings), {"GravityZ": -1400.0})


if __name__ == '__main__':
    unittest.main()
