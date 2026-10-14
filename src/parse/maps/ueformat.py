"""Reader for the UEFormat ``.uemodel`` files BatchExport writes.

One reader for every consumer: the module models (``parsers/model.py``: skeletal
meshes, their LOD0 and reference skeleton) and the maps (static meshes and their
convex collision hulls). Values are left exactly as stored: Unreal space,
centimeters, local to the mesh.

Layout (version 10 and later): a header (magic, identifier, version, object name
and path, compression), then a body of nested named attributes. An attribute is
``[fstring name][i32 byte length][payload]``; an attribute set is a count followed
by that many attributes. The root set holds ``LODS`` (count, then per LOD a name
and an attribute set: ``VERTICES``, ``INDICES``, ``MATERIALS``, ...), ``COLLISION``
(convex hulls) and, for a skeletal mesh, ``SKELETON`` (an attribute set holding
``BONES``).
"""
import gzip
import struct
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import numpy as np
import zstandard

MAGIC = b"UEFORMAT"
# First version that stores the body as nested named attributes, the only layout read here.
MIN_VERSION = 10


class UEFormatError(ValueError):
    """The file is not a UEFormat model this reader understands."""


@dataclass
class MaterialSection:
    slot: str
    material: str
    first_index: int
    num_faces: int


@dataclass
class Lod:
    name: str
    vertices: np.ndarray  # (N, 3) float32
    indices: np.ndarray  # (M, 3) uint32
    sections: List[MaterialSection] = field(default_factory=list)


@dataclass
class ConvexHull:
    name: str
    vertices: np.ndarray  # (N, 3) float32
    indices: np.ndarray  # (M, 3) int32, may be empty


@dataclass
class Bone:
    name: str
    parent: int
    position: Tuple[float, float, float]
    rotation: Tuple[float, float, float, float]  # quaternion x, y, z, w
    scale: Tuple[float, float, float]


@dataclass
class UEModel:
    object_name: str
    object_path: str
    version: int
    lods: List[Lod]
    collision: List[ConvexHull]
    bones: Optional[List[Bone]]  # the mesh's own reference skeleton; None without a SKELETON


class _Reader:
    def __init__(self, data: bytes, offset: int = 0) -> None:
        self.data = data
        self.offset = offset

    def take(self, count: int) -> bytes:
        end = self.offset + count
        if count < 0 or end > len(self.data):
            raise UEFormatError("unexpected end of data")
        chunk = self.data[self.offset:end]
        self.offset = end
        return chunk

    def int32(self) -> int:
        return struct.unpack("<i", self.take(4))[0]

    def byte(self) -> int:
        return self.take(1)[0]

    def floats(self, count: int) -> Tuple[float, ...]:
        return struct.unpack(f"<{count}f", self.take(4 * count))

    def string(self) -> str:
        return self.take(self.int32()).decode("utf-8")

    def array(self, dtype: str, width: int) -> np.ndarray:
        """A count-prefixed array of fixed-size records, ``width`` values each."""
        count = self.int32()
        item_size = np.dtype(dtype).itemsize * width
        values = np.frombuffer(self.take(count * item_size), dtype=dtype)
        return values.reshape(count, width) if width > 1 else values

    def attributes(self) -> Dict[str, bytes]:
        """A count-prefixed set of (name, byte length, payload) attributes."""
        result = {}
        for _ in range(self.int32()):
            name = self.string()
            result[name] = self.take(self.int32())
        return result


def _read_header(reader: _Reader) -> Tuple[str, int, str, str, bytes]:
    """``(identifier, version, object name, object path, decompressed body)``."""
    if reader.take(len(MAGIC)) != MAGIC:
        raise UEFormatError("not a UEFormat file")
    identifier = reader.string()
    version = reader.byte()
    if version < MIN_VERSION:
        raise UEFormatError(f"UEFormat version {version} is older than {MIN_VERSION}")
    object_name = reader.string()
    object_path = reader.string()

    if reader.byte():
        compression = reader.string()
        uncompressed_size = reader.int32()
        compressed_size = reader.int32()
        payload = reader.take(compressed_size)
        if compression == "ZSTD":
            body = zstandard.ZstdDecompressor().decompress(payload, max_output_size=uncompressed_size)
        elif compression == "GZIP":
            body = gzip.decompress(payload)
        else:
            raise UEFormatError(f"unsupported compression {compression}")
    else:
        body = reader.data[reader.offset:]
    return identifier, version, object_name, object_path, body


def _read_indices(payload: bytes) -> np.ndarray:
    """Triangle indices, stored as 32 or (older exports) 16 bits each."""
    count = _Reader(payload).int32()
    width = (len(payload) - 4) // count if count else 4
    flat = _Reader(payload).array("<u2" if width == 2 else "<u4", 1).astype(np.uint32)
    return flat[: len(flat) // 3 * 3].reshape(-1, 3)


def _read_lod(reader: _Reader) -> Lod:
    name = reader.string()
    attributes = reader.attributes()

    vertices = _Reader(attributes["VERTICES"]).array("<f4", 3)
    indices = _read_indices(attributes["INDICES"])

    sections = []
    if "MATERIALS" in attributes:
        section_reader = _Reader(attributes["MATERIALS"])
        for _ in range(section_reader.int32()):
            slot = section_reader.string()
            material = section_reader.string()
            first_index = section_reader.int32()
            num_faces = section_reader.int32()
            sections.append(MaterialSection(slot, material, first_index, num_faces))
    return Lod(name, vertices, indices, sections)


def _read_hull(reader: _Reader) -> ConvexHull:
    name = reader.string()
    vertices = reader.array("<f4", 3)
    flat_indices = reader.array("<i4", 1)
    return ConvexHull(name, vertices, flat_indices[: len(flat_indices) // 3 * 3].reshape(-1, 3))


def _read_bones(payload: bytes) -> List[Bone]:
    reader = _Reader(payload)
    bones = []
    for _ in range(reader.int32()):
        name = reader.string()
        parent = reader.int32()
        bones.append(Bone(name, parent, reader.floats(3), reader.floats(4), reader.floats(3)))
    return bones


def read_uemodel(model_file, lods: bool = True) -> UEModel:
    """Read a ``.uemodel`` file; ``lods=False`` skips the geometry. Raises UEFormatError
    when it cannot be decoded."""
    data = Path(model_file).read_bytes()
    try:
        identifier, version, object_name, object_path, body = _read_header(_Reader(data))
    except UEFormatError as error:
        raise UEFormatError(f"{model_file}: {error}") from None
    if identifier != "UEMODEL":
        raise UEFormatError(f"{model_file}: expected a UEMODEL, got {identifier}")

    root = _Reader(body).attributes()

    read_lods = []
    if lods and "LODS" in root:
        lod_reader = _Reader(root["LODS"])
        read_lods = [_read_lod(lod_reader) for _ in range(lod_reader.int32())]

    collision = []
    if "COLLISION" in root:
        hull_reader = _Reader(root["COLLISION"])
        collision = [_read_hull(hull_reader) for _ in range(hull_reader.int32())]

    bones = None
    if "SKELETON" in root:
        skeleton = _Reader(root["SKELETON"]).attributes()
        if "BONES" in skeleton:
            bones = _read_bones(skeleton["BONES"])

    return UEModel(object_name, object_path, version, read_lods, collision, bones)
