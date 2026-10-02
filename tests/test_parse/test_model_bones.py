import os
import struct
import sys
import tempfile
import types
import unittest

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


def _fstr(s):
    b = s.encode()
    return struct.pack('<i', len(b)) + b


def _uemodel(version, bones):
    """Uncompressed .uemodel holding only a BONES chunk."""
    data = b''
    for name, parent, pos, rot, scale in bones:
        data += _fstr(name) + struct.pack('<i', parent) + struct.pack('<3f', *pos) + struct.pack('<4f', *rot)
        if version >= 10:
            data += struct.pack('<3f', *scale)
    chunk = _fstr('BONES') + struct.pack('<i', len(data) + 4) + struct.pack('<i', len(bones)) + data
    return b'UEFORMAT' + _fstr('UEMODEL') + bytes([version]) + _fstr('SK_Test') + b'\x00' + chunk


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

    def test_v9_has_no_scale(self):
        bones = self._load(9)
        self.assertEqual(bones[1]['pos'], [13.65, -216.39, 267.74])
        self.assertIsNone(bones[1]['scale'])


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


if __name__ == '__main__':
    unittest.main()
