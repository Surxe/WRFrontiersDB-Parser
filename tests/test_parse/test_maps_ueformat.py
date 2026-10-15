import os
import sys
import tempfile
import unittest

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from maps_fixtures import build_model  # noqa: E402
from maps import ueformat  # noqa: E402

VERTICES = [[0, 0, 0], [100, 0, 0], [0, 100, 0], [0, 0, 100]]
INDICES = [0, 1, 2, 0, 2, 3]


class TestReadUEModel(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()

    def tearDown(self):
        self.temp_dir.cleanup()

    def _write(self, data):
        model_file = os.path.join(self.temp_dir.name, "model.uemodel")
        with open(model_file, "wb") as output_file:
            output_file.write(data)
        return model_file

    def test_read_compressed(self):
        model = ueformat.read_uemodel(self._write(build_model(VERTICES, INDICES)))
        self.assertEqual(model.object_path, "/Game/SM_Test.SM_Test")
        self.assertEqual(len(model.lods), 1)
        np.testing.assert_array_equal(model.lods[0].vertices, np.asarray(VERTICES, dtype=np.float32))
        np.testing.assert_array_equal(model.lods[0].indices, [[0, 1, 2], [0, 2, 3]])
        self.assertEqual(model.lods[0].sections[0].material, "/Game/M_Test.M_Test")
        self.assertEqual(model.lods[0].sections[0].num_faces, 2)
        self.assertIsNone(model.bones)

    def test_read_uncompressed(self):
        model = ueformat.read_uemodel(self._write(build_model(VERTICES, INDICES, compressed=False)))
        self.assertEqual(model.lods[0].indices.shape, (2, 3))

    def test_read_16_bit_indices(self):
        model = ueformat.read_uemodel(self._write(build_model(VERTICES, INDICES, index_dtype="<u2")))
        np.testing.assert_array_equal(model.lods[0].indices, [[0, 1, 2], [0, 2, 3]])
        self.assertEqual(model.lods[0].indices.dtype, np.uint32)

    def test_read_collision_hulls(self):
        hulls = [(VERTICES, [0, 1, 2, 1, 2, 3])]
        model = ueformat.read_uemodel(self._write(build_model(VERTICES, INDICES, hulls)))
        self.assertEqual(len(model.collision), 1)
        self.assertEqual(model.collision[0].vertices.shape, (4, 3))
        self.assertEqual(model.collision[0].indices.tolist(), [[0, 1, 2], [1, 2, 3]])

    def test_read_skeleton(self):
        bones = [("Root", -1, (0, 0, 0), (0, 0, 0, 1), (1, 1, 1)), ("Arm", 0, (1.5, 2, 3), (0, 0, 0.5, 0.5), (1, 1, 2))]
        model = ueformat.read_uemodel(self._write(build_model(VERTICES, INDICES, bones=bones)))
        self.assertEqual([(bone.name, bone.parent) for bone in model.bones], [("Root", -1), ("Arm", 0)])
        self.assertEqual(model.bones[1].position, (1.5, 2.0, 3.0))
        self.assertEqual(model.bones[1].rotation, (0.0, 0.0, 0.5, 0.5))
        self.assertEqual(model.bones[1].scale, (1.0, 1.0, 2.0))

    def test_skipping_lods(self):
        model = ueformat.read_uemodel(self._write(build_model(VERTICES, INDICES)), lods=False)
        self.assertEqual(model.lods, [])

    def test_rejects_other_magic(self):
        with self.assertRaises(ueformat.UEFormatError):
            ueformat.read_uemodel(self._write(b"NOTAMODEL" + b"\x00" * 32))

    def test_rejects_old_version(self):
        with self.assertRaises(ueformat.UEFormatError):
            ueformat.read_uemodel(self._write(build_model(VERTICES, INDICES, version=9)))

    def test_rejects_other_identifier(self):
        with self.assertRaises(ueformat.UEFormatError):
            ueformat.read_uemodel(self._write(build_model(VERTICES, INDICES, identifier="UEANIM")))

    def test_rejects_truncated_file(self):
        data = build_model(VERTICES, INDICES, compressed=False)
        with self.assertRaises(ueformat.UEFormatError):
            ueformat.read_uemodel(self._write(data[:-10]))


if __name__ == "__main__":
    unittest.main()
