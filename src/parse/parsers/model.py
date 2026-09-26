# Add two levels of parent dirs to sys path
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

"""Extract per-module hitbox + untextured model data into the minimal storage structure.

For every parsed CharacterModule that carries a mesh, read the exported art assets
(SK_*.json mesh meta, SKEL_*.json skeleton + sockets, PHYS_*.json physics capsules,
SK_*.uemodel geometry) and emit ONE compact JSON per module:

    <output_dir>/Models/<CharacterModuleId>.json

Schema (goal: minimal storage, fast to convert, universally applicable):
    {
      "id", "source",
      "coordinate_system": "UE cm; X forward, Y right, Z up",
      "bounds": {origin, extent, sphere_radius},
      "bones":    [ {name, parent, pos:[x,y,z], rot:[qx,qy,qz,qw], scale:[sx,sy,sz]} ],  # local, parent-relative
      "sockets":  [ {name, bone, loc:[x,y,z], rot:[pitch,yaw,roll]} ],                   # bone-relative
      "capsules": [ {bone, center:[x,y,z], rot:[pitch,yaw,roll], radius, length} ],      # bone-relative
      "boxes":    [ {bone, center:[x,y,z], rot:[pitch,yaw,roll], extent:[x,y,z]} ],
      "spheres":  [ {bone, center:[x,y,z], radius} ],
      "meshes":   [ {asset, verts:[x,y,z,...], indices:[a,b,c,...], num_tris} ]          # module space, LOD0
    }
"""

import struct
import json
from loguru import logger

try:
    import zstandard
    HAS_ZSTD = True
except ImportError:
    HAS_ZSTD = False

from utils import OPTIONS, asset_path_to_file_path, get_json_data, resolve_path_case_insensitive, asset_to_data

MODEL_FILE_VERSION = 1


# ---------------- .uemodel (UEFormat) geometry reading ----------------

def _i32(b, i):
    return struct.unpack_from('<i', b, i)[0], i + 4

def _fstr(b, i):
    n, i = _i32(b, i)
    return b[i:i + n].decode('utf-8', 'replace'), i + n

def read_ueformat_payload(raw: bytes):
    """Return the decompressed chunk payload from a .uemodel file (UEFormat v9/v10)."""
    if raw[:8] != b'UEFORMAT':
        raise ValueError("not a UEFORMAT file")
    i = 8
    ident, i = _fstr(raw, i)
    ver, i = raw[i], i + 1
    # v10+ adds an ObjectPath fstring before the compression flag; v9 doesn't.
    # Locate the compression marker robustly instead of walking the header.
    for ctype in (b'ZSTD', b'GZIP', b'LZ4'):
        mark = b'\x04\x00\x00\x00' + ctype
        p = raw.find(mark)
        if p >= 0:
            j = p + len(mark)
            usize, j = _i32(raw, j)
            csize, j = _i32(raw, j)
            blob = raw[j:j + csize]
            if ctype == b'ZSTD':
                if not HAS_ZSTD:
                    raise RuntimeError("zstandard package is required for ZSTD .uemodel files")
                return zstandard.ZstdDecompressor().decompress(blob, max_output_size=usize)
            if ctype == b'GZIP':
                import gzip
                return gzip.decompress(blob)
            raise NotImplementedError(f"unsupported ueformat compression {ctype}")
    # Uncompressed: payload starts after object-name fstring + is_compressed bool
    obj, i = _fstr(raw, i)
    comp, i = raw[i], i + 1
    return raw[i:]

def find_ueformat_chunk(d, name):
    """Locate a chunk by name. Layout (v9/v10 compatible): [fstring name][i32 size][i32 count][data].
    `size` includes the trailing count i32; returns (count, data_offset, size)."""
    nb = name.encode()
    k = d.find(nb)
    while k >= 0:
        if k >= 4 and struct.unpack_from('<i', d, k - 4)[0] == len(nb):
            size = struct.unpack_from('<i', d, k + len(nb))[0]
            count = struct.unpack_from('<i', d, k + len(nb) + 4)[0]
            return count, k + len(nb) + 8, size
        k = d.find(nb, k + 1)
    return None

def load_ueformat_mesh(uemodel_path):
    """Read LOD0 positions + triangle indices from a .uemodel file."""
    raw = open(uemodel_path, 'rb').read()
    d = read_ueformat_payload(raw)
    vch = find_ueformat_chunk(d, 'VERTICES')
    ich = find_ueformat_chunk(d, 'INDICES')
    if not vch or not ich:
        raise ValueError(f"{uemodel_path}: missing VERTICES or INDICES chunk")
    vc, vo, _ = vch
    verts = struct.unpack_from(f'<{vc * 3}f', d, vo)
    ic, io, isize = ich
    ibytes = (isize - 4) // ic if ic else 2
    ifmt = 'H' if ibytes == 2 else 'i'
    indices = struct.unpack_from(f'<{ic}{ifmt}', d, io)
    if indices and max(indices) >= vc:
        raise ValueError(f"{uemodel_path}: index out of range")
    return verts, indices


# ---------------- asset resolution ----------------

def _mesh_json_files(mesh_asset_path):
    """asset path (/Game/.../SK_X.1) -> (SK json path, uemodel path, SKEL json path, PHYS json path)."""
    sk_json = asset_path_to_file_path(mesh_asset_path)  # <export>/.../SK_X.json
    uemodel = sk_json[:-len('.json')] + '.uemodel'
    skel_json = None
    phys_json = None
    try:
        data = get_json_data(sk_json)
        sk_mesh = next((e for e in data if e.get('Type') == 'SkeletalMesh'), None)
    except Exception:
        sk_mesh = None
    if sk_mesh is not None:
        props = sk_mesh.get('Properties', {})
        skel_ref = props.get('Skeleton') or {}
        phys_ref = props.get('PhysicsAsset') or {}
        for ref, attr in ((skel_ref, 'skel'), (phys_ref, 'phys')):
            obj_path = ref.get('ObjectPath')
            if not obj_path:
                continue
            base = asset_path_to_file_path(obj_path)[:-len('.json')]
            if attr == 'skel':
                skel_json = base + '.json'
            else:
                phys_json = base + '.json'
    return sk_json, uemodel, skel_json, phys_json


# ---------------- per-asset extraction ----------------

def _extract_skeleton(skel_json):
    """Reference skeleton: local (parent-relative) bones + bone-relative sockets."""
    data = get_json_data(skel_json)
    skel = next((e for e in data if e.get('Type') == 'Skeleton'), None)
    bones = []
    sockets = []
    if skel is None:
        return bones, sockets
    rs = skel.get('ReferenceSkeleton', {})
    info = rs.get('FinalRefBoneInfo') or []
    pose = rs.get('FinalRefBonePose') or []
    name2i = {}
    for i, (bi, bp) in enumerate(zip(info, pose)):
        name2i[bi['Name']] = i
        rot = bp.get('Rotation') or {}
        tr = bp.get('Translation') or {}
        sc = bp.get('Scale3D') or {}
        bones.append({
            'name': bi['Name'],
            'parent': bi['ParentIndex'],
            'pos': [round(tr.get('X', 0), 3), round(tr.get('Y', 0), 3), round(tr.get('Z', 0), 3)],
            'rot': [round(rot.get('X', 0), 6), round(rot.get('Y', 0), 6),
                    round(rot.get('Z', 0), 6), round(rot.get('W', 1), 6)],
            'scale': [round(sc.get('X', 1), 4), round(sc.get('Y', 1), 4), round(sc.get('Z', 1), 4)],
        })
    # sockets exported as SkeletalMeshSocket elements of the skeleton package
    for e in data:
        if e.get('Type') != 'SkeletalMeshSocket':
            continue
        pr = e.get('Properties', {})
        loc = pr.get('RelativeLocation') or {}
        rot = pr.get('RelativeRotation') or {}
        bone_name = pr.get('BoneName', '')
        sockets.append({
            'name': pr.get('SocketName', ''),
            'bone': name2i.get(bone_name, -1),
            'loc': [round(loc.get('X', 0), 3), round(loc.get('Y', 0), 3), round(loc.get('Z', 0), 3)],
            'rot': [round(rot.get('Pitch', 0), 4), round(rot.get('Yaw', 0), 4), round(rot.get('Roll', 0), 4)],
        })
    return bones, sockets

def _rot3(rot):
    return [round(rot.get('Pitch', 0), 4), round(rot.get('Yaw', 0), 4), round(rot.get('Roll', 0), 4)]

def _pos3(vec):
    return [round(vec.get('X', 0), 3), round(vec.get('Y', 0), 3), round(vec.get('Z', 0), 3)]

def _extract_physics(phys_json, name2i):
    """Physics asset AggGeom primitives, bone-relative (as authored)."""
    capsules, boxes, spheres = [], [], []
    data = get_json_data(phys_json)
    for e in data:
        pr = e.get('Properties', {})
        ag = pr.get('AggGeom')
        if not ag:
            continue
        bone = name2i.get(pr.get('BoneName', ''), -1)
        for sp in ag.get('SphylElems', []):
            capsules.append({
                'bone': bone,
                'center': _pos3(sp.get('Center') or {}),
                'rot': _rot3(sp.get('Rotation') or {}),
                'radius': round(sp.get('Radius', 0), 2),
                'length': round(sp.get('Length', 0), 2),
            })
        for bx in ag.get('BoxElems', []):
            boxes.append({
                'bone': bone,
                'center': _pos3(bx.get('Center') or {}),
                'rot': _rot3(bx.get('Rotation') or {}),
                'extent': [round(bx.get('X', 0), 2), round(bx.get('Y', 0), 2), round(bx.get('Z', 0), 2)],
            })
        for s in ag.get('SphereElems', []):
            spheres.append({
                'bone': bone,
                'center': _pos3(s.get('Center') or {}),
                'radius': round(s.get('Radius', 0), 2),
            })
    return capsules, boxes, spheres

def _extract_bounds(sk_json):
    try:
        sk = next((e for e in get_json_data(sk_json) if e.get('Type') == 'SkeletalMesh'), None)
    except Exception:
        return None
    if sk is None:
        return None
    b = sk.get('ImportedBounds') or {}
    o = b.get('Origin') or {}
    ex = b.get('BoxExtent') or {}
    return {
        'origin': _pos3(o),
        'extent': _pos3(ex),
        'sphere_radius': round(b.get('SphereRadius', 0), 2),
    }

def _extract_adapters(adapter_refs):
    """Resolve each adapter BP -> its StaticMesh's 'Adapter' socket offset.

    That socket's RelativeLocation is the weapon root offset relative to the
    parent module's socket bone, applied by the game when mounting.
    """
    from utils import path_to_index
    adapters = []
    for ref in adapter_refs or []:
        mount_way = ref.get('mount_way')
        adapter_path = ref.get('adapter_path')
        offset = None
        try:
            bp_file = asset_path_to_file_path(adapter_path)
            bp_data = get_json_data(bp_file)
            bp_index = path_to_index(adapter_path) if isinstance(bp_data, list) else None
            bp_gen = bp_data[bp_index] if bp_index is not None else bp_data
            cdo = bp_gen.get('ClassDefaultObject') if bp_gen else None
            cdo_data = asset_to_data(cdo) if cdo else {}
            static_mesh_ref = (cdo_data.get('Properties') or {}).get('StaticMesh')
            if static_mesh_ref:
                sm_json = asset_path_to_file_path(static_mesh_ref['ObjectPath'])
                for e in get_json_data(sm_json):
                    if e.get('Type') == 'StaticMeshSocket' and (e.get('Properties') or {}).get('SocketName') == 'Adapter':
                        loc = (e.get('Properties') or {}).get('RelativeLocation') or {}
                        offset = [round(loc.get('X', 0), 3), round(loc.get('Y', 0), 3), round(loc.get('Z', 0), 3)]
                        break
        except Exception as e:
            logger.debug(f"Adapter socket resolution failed for {adapter_path}: {e}")
        adapters.append({'mount_way': mount_way, 'offset': offset})
    return [a for a in adapters if a['offset'] is not None]


# ---------------- per-module model ----------------

def extract_module_model(character_module):
    """Build the minimal model structure for one CharacterModule. Returns dict or None."""
    mesh_refs = getattr(character_module, 'meshes', []) or []
    if not mesh_refs:
        return None

    bones = []
    sockets = []
    capsules, boxes, spheres = [], [], []
    meshes = []
    bounds = None
    source = None

    for ref in mesh_refs:
        mesh_asset_path = ref.get('mesh_path')
        if not mesh_asset_path:
            continue
        try:
            sk_json, uemodel, skel_json, phys_json = _mesh_json_files(mesh_asset_path)
        except Exception as e:
            logger.debug(f"Model extraction {character_module.id}: could not resolve {mesh_asset_path}: {e}")
            continue

        name2i = {}
        if skel_json and os.path.exists(resolve_path_case_insensitive(skel_json)):
            try:
                m_bones, m_sockets = _extract_skeleton(skel_json)
                if not bones:
                    # First skeletal mesh defines the module skeleton; later
                    # components (e.g. the 4 chassis legs) share it.
                    bones = m_bones
                    sockets = m_sockets
            except Exception as e:
                logger.debug(f"Model extraction {character_module.id}: skeleton failed: {e}")
        # Physics prims reference bones by name; always resolve against the
        # module skeleton (shared across the module's components).
        name2i = {b['name']: i for i, b in enumerate(bones)}

        if phys_json and os.path.exists(resolve_path_case_insensitive(phys_json)):
            try:
                m_caps, m_boxes, m_spheres = _extract_physics(phys_json, name2i)
                capsules.extend(m_caps); boxes.extend(m_boxes); spheres.extend(m_spheres)
            except Exception as e:
                logger.debug(f"Model extraction {character_module.id}: physics failed: {e}")

        if bounds is None:
            bounds = _extract_bounds(sk_json)
        if source is None:
            source = mesh_asset_path

        uemodel_path = resolve_path_case_insensitive(uemodel)
        if os.path.exists(uemodel_path):
            try:
                verts, indices = load_ueformat_mesh(uemodel_path)
                meshes.append({
                    'asset': os.path.basename(sk_json)[:-len('.json')],
                    'verts': [round(v, 2) for v in verts],
                    'indices': [int(i) for i in indices],
                    'num_tris': len(indices) // 3,
                })
            except Exception as e:
                logger.debug(f"Model extraction {character_module.id}: geometry failed for {uemodel_path}: {e}")

    if not meshes and not bones and not capsules and not boxes and not spheres:
        return None

    adapters = _extract_adapters(getattr(character_module, 'adapters', []) or [])

    return {
        'version': MODEL_FILE_VERSION,
        'id': character_module.id,
        'source': source,
        'coordinate_system': 'UE cm; X forward, Y right, Z up',
        'bounds': bounds,
        'bones': bones,
        'sockets': sockets,
        'adapters': adapters,
        'capsules': capsules,
        'boxes': boxes,
        'spheres': spheres,
        'meshes': meshes,
    }

def parse_models(to_file=True):
    """Extract a model for every parsed CharacterModule. Returns {id: model}."""
    from parsers.character_module import CharacterModule

    models = {}
    for cm_id, cm in CharacterModule.objects.items():
        try:
            model = extract_module_model(cm)
        except Exception as e:
            logger.warning(f"Model extraction failed for {cm_id}: {e}")
            model = None
        if model is not None:
            models[cm_id] = model

    if to_file:
        out_dir = os.path.join(OPTIONS.output_dir, 'Models')
        os.makedirs(out_dir, exist_ok=True)
        for cm_id, model in models.items():
            safe_id = cm_id.replace('/', '_')
            with open(os.path.join(out_dir, f'{safe_id}.json'), 'w', encoding='utf-8') as f:
                json.dump(model, f, separators=(',', ':'))
        logger.info(f"Wrote {len(models)} module models to {out_dir}")
    return models

if __name__ == "__main__":
    parse_models(to_file=True)
