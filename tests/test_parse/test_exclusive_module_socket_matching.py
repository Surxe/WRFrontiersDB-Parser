import importlib.util
import os
import sys
import unittest

os.environ['SHOULD_PARSE'] = 'false'
os.environ.setdefault('EXPORT_DIR', '/tmp/test_export')
os.environ.setdefault('OUTPUT_DIR', '/tmp/test_output')

src_path = os.path.join(os.path.dirname(__file__), '..', '..', 'src')
parse_path = os.path.join(src_path, 'parse')
sys.path.insert(0, parse_path)

spec = importlib.util.spec_from_file_location(
    "exclusive_module_socket_matching",
    os.path.join(parse_path, "exclusive_module_socket_matching.py"),
)
matching = importlib.util.module_from_spec(spec)
spec.loader.exec_module(matching)

resolve_exclusive_module_socket_assignments = (
    matching.resolve_exclusive_module_socket_assignments
)
ExclusiveAssignmentError = matching.ExclusiveAssignmentError


class TestExclusiveModuleSocketMatching(unittest.TestCase):
    def test_light_and_heavy_weapon_sockets(self):
        socket_to_types = {
            "light_socket": {"DA_ModuleType_Weapon.0"},
            "heavy_socket": {"DA_ModuleType_Weapon.0", "DA_ModuleType_WeaponHeavy.0"},
        }

        socket_to_type, type_to_socket = resolve_exclusive_module_socket_assignments(
            socket_to_types
        )

        self.assertEqual(socket_to_type["light_socket"], "DA_ModuleType_Weapon.0")
        self.assertEqual(socket_to_type["heavy_socket"], "DA_ModuleType_WeaponHeavy.0")
        self.assertEqual(type_to_socket["DA_ModuleType_Weapon.0"], "light_socket")
        self.assertEqual(type_to_socket["DA_ModuleType_WeaponHeavy.0"], "heavy_socket")

    def test_multi_pass_chain(self):
        socket_to_types = {
            "socket_a": {"type_x", "type_y", "type_z"},
            "socket_b": {"type_y"},
            "socket_c": {"type_z"},
        }

        socket_to_type, type_to_socket = resolve_exclusive_module_socket_assignments(
            socket_to_types
        )

        self.assertEqual(socket_to_type["socket_b"], "type_y")
        self.assertEqual(socket_to_type["socket_c"], "type_z")
        self.assertEqual(socket_to_type["socket_a"], "type_x")
        self.assertEqual(type_to_socket["type_x"], "socket_a")
        self.assertEqual(type_to_socket["type_y"], "socket_b")
        self.assertEqual(type_to_socket["type_z"], "socket_c")

    def test_symmetric_ambiguity_raises(self):
        socket_to_types = {
            "socket_a": {"type_x", "type_y"},
            "socket_b": {"type_x", "type_y"},
        }

        with self.assertRaises(ExclusiveAssignmentError):
            resolve_exclusive_module_socket_assignments(socket_to_types)

    def test_empty_compatible_list_raises(self):
        socket_to_types = {
            "empty_socket": set(),
        }

        with self.assertRaises(ExclusiveAssignmentError):
            resolve_exclusive_module_socket_assignments(socket_to_types)

    def test_shared_single_compatible_type(self):
        socket_to_types = {
            "DA_ModuleSocketType_ShoulderL.0": {"DA_ModuleType_Shoulder.0"},
            "DA_ModuleSocketType_ShoulderR.0": {"DA_ModuleType_Shoulder.0"},
        }

        socket_to_type, type_to_socket = resolve_exclusive_module_socket_assignments(
            socket_to_types
        )

        self.assertEqual(
            socket_to_type["DA_ModuleSocketType_ShoulderL.0"],
            "DA_ModuleType_Shoulder.0",
        )
        self.assertEqual(
            socket_to_type["DA_ModuleSocketType_ShoulderR.0"],
            "DA_ModuleType_Shoulder.0",
        )
        self.assertEqual(
            type_to_socket["DA_ModuleType_Shoulder.0"],
            "DA_ModuleSocketType_ShoulderL.0",
        )

    def test_exhausted_pool_raises(self):
        socket_to_types = {
            "socket_a": {"type_x", "type_y"},
            "socket_b": {"type_x"},
            "socket_c": {"type_y"},
        }

        with self.assertRaises(ExclusiveAssignmentError):
            resolve_exclusive_module_socket_assignments(socket_to_types)


if __name__ == "__main__":
    unittest.main()
