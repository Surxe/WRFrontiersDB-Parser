import os
import sys
import tempfile
import types
import unittest
from unittest import mock

os.environ['SHOULD_PARSE'] = 'false'
os.environ.setdefault('EXPORT_DIR', '/tmp/test_export')
os.environ.setdefault('OUTPUT_DIR', '/tmp/test_output')

src_path = os.path.join(os.path.dirname(__file__), '..', '..', 'src')
parse_path = os.path.join(src_path, 'parse')
# Parsers import both 'parsers.*' and 'parse.parsers.*'. As in run.py, 'parse' must be
# the src/parse package, not src/parse/parse.py (which wins once src/parse is on sys.path)
if not hasattr(sys.modules.get('parse'), '__path__'):
    parse_pkg = types.ModuleType('parse')
    parse_pkg.__path__ = [parse_path]
    sys.modules['parse'] = parse_pkg
sys.path.insert(0, src_path)
sys.path.insert(0, parse_path)

from parsers import model  # noqa: E402
from maps.ueformat import UEFormatError  # noqa: E402

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from maps_fixtures import build_model  # noqa: E402


def _uemodel(version, bones):
    """Uncompressed .uemodel holding only a skeleton."""
    return build_model(bones=bones, compressed=False, version=version)


def _skel_bone(name, parent, pos, scale=(1.0, 1.0, 1.0)):
    return {'name': name, 'parent': parent, 'pos': list(pos), 'rot': [0.0, 0.0, 0.0, 1.0], 'scale': list(scale)}


class TestLoadUeformatBones(unittest.TestCase):
    BONES = [
        ('Torso', -1, (0, 0, 0), (0, 0, 0, 1), (1, 1, 1)),
        ('Shoulder_L', 0, (13.65, -216.39, 267.74), (0, 0, 0, 1), (1, 1, 2)),
    ]

    def _load(self, version):
        with tempfile.NamedTemporaryFile(suffix='.uemodel', delete=False) as f:
            f.write(_uemodel(version, self.BONES))
        try:
            return model.load_ueformat_bones(f.name)
        finally:
            os.unlink(f.name)

    def test_v10_reads_scale(self):
        bones = self._load(10)
        self.assertEqual([b['name'] for b in bones], ['Torso', 'Shoulder_L'])
        self.assertEqual(bones[1]['parent'], 0)
        self.assertEqual(bones[1]['pos'], [13.65, -216.39, 267.74])
        self.assertEqual(bones[1]['rot'], [0.0, 0.0, 0.0, 1.0])
        self.assertEqual(bones[1]['scale'], [1.0, 1.0, 2.0])

    def test_pre_v10_is_rejected(self):
        with self.assertRaises(UEFormatError):
            self._load(9)

    def test_no_skeleton(self):
        with tempfile.NamedTemporaryFile(suffix='.uemodel', delete=False) as f:
            f.write(build_model([[0, 0, 0], [1, 0, 0], [0, 1, 0]], [0, 1, 2], compressed=False))
        try:
            self.assertIsNone(model.load_ueformat_bones(f.name))
            verts, indices = model.load_ueformat_mesh(f.name)
        finally:
            os.unlink(f.name)
        self.assertEqual((verts, indices), ([0.0, 0.0, 0.0, 1.0, 0.0, 0.0, 0.0, 1.0, 0.0], [0, 1, 2]))


class TestMergeMeshBones(unittest.TestCase):
    """The mesh's own skeleton wins over the shared USkeleton's drifting ref pose."""

    def test_mesh_pose_wins_and_skel_only_bones_are_appended(self):
        # SKEL ref pose 100x off on the shoulder; Gun only exists in the SKEL.
        skel = [
            _skel_bone('Torso', -1, (0, 0, 0)),
            _skel_bone('Gun', 0, (5, 0, 0)),
            _skel_bone('Shoulder_L', 0, (0.14, -2.16, 2.68)),
        ]
        mesh = [
            {**_skel_bone('Torso', -1, (0, 0, 0)), 'scale': None},
            {**_skel_bone('Shoulder_L', 0, (13.65, -216.39, 267.74)), 'scale': [1.0, 1.0, 1.0]},
        ]
        sockets = [{'name': 'Muzzle', 'bone': 1}, {'name': 'Mount', 'bone': 2}, {'name': 'Loose', 'bone': -1}]
        bones = model._merge_mesh_bones(mesh, skel, sockets)

        self.assertEqual([b['name'] for b in bones], ['Torso', 'Shoulder_L', 'Gun'])
        self.assertEqual(bones[1]['pos'], [13.65, -216.39, 267.74])
        self.assertEqual(bones[2]['parent'], 0)
        self.assertEqual(bones[2]['pos'], [5, 0, 0])
        # Pre-v10 mesh bone scale falls back to the SKEL bone's.
        self.assertEqual(bones[0]['scale'], [1.0, 1.0, 1.0])
        # Sockets follow their bone by name.
        self.assertEqual([s['bone'] for s in sockets], [2, 1, -1])

    def test_parents_precede_children(self):
        skel = [_skel_bone('Root', -1, (0, 0, 0)), _skel_bone('A', 0, (1, 0, 0)), _skel_bone('B', 1, (1, 0, 0))]
        mesh = [{**_skel_bone('Root', -1, (0, 0, 0)), 'scale': [1.0, 1.0, 1.0]}]
        bones = model._merge_mesh_bones(mesh, skel, [])
        for i, b in enumerate(bones):
            self.assertLess(b['parent'], i)
        self.assertEqual([(b['name'], b['parent']) for b in bones], [('Root', -1), ('A', 0), ('B', 1)])


class TestParseModels(unittest.TestCase):
    def test_each_model_is_written_before_the_next_is_built(self):
        from parsers.character_module import CharacterModule
        modules = {'A': object(), 'B/C': object(), 'Empty': object()}
        with tempfile.TemporaryDirectory() as tmp:
            out_dir = os.path.join(tmp, 'Models')

            def extract(cm):
                cm_id = next(k for k, v in modules.items() if v is cm)
                written = sorted(os.listdir(out_dir))
                self.assertEqual(written, {'A': [], 'B/C': ['A.json'], 'Empty': ['A.json', 'B_C.json']}[cm_id])
                return None if cm_id == 'Empty' else {'id': cm_id}

            with mock.patch.object(CharacterModule, 'objects', modules), \
                    mock.patch.object(model, 'OPTIONS', types.SimpleNamespace(output_dir=tmp)), \
                    mock.patch.object(model, 'extract_module_model', extract):
                self.assertEqual(model.parse_models(), 2)
            with open(os.path.join(out_dir, 'B_C.json')) as f:
                self.assertEqual(f.read(), '{"id":"B/C"}')


if __name__ == '__main__':
    unittest.main()
