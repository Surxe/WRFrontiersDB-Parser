"""The pinned gltfpack (meshoptimizer) the map cook compresses with.

Downloaded on first use into the Parser's ``build/gltfpack/`` and checked by the
version it reports, so every machine cooks with the same build and the output
stays byte-identical across runs (git then dedupes unchanged maps in the data repo).
"""
import io
import os
import stat
import subprocess
import zipfile
from pathlib import Path
from typing import List

import requests
from loguru import logger

GLTFPACK_VERSION = "1.3"
GLTFPACK_URL = f"https://github.com/zeux/meshoptimizer/releases/download/v{GLTFPACK_VERSION}/gltfpack-ubuntu.zip"
GLTFPACK_DIR = Path(__file__).resolve().parents[3] / "build" / "gltfpack"


def installed_version(gltfpack_cmd: Path) -> str:
    """The version an installed gltfpack reports (``gltfpack 1.3`` -> ``1.3``), or ''."""
    if not gltfpack_cmd.is_file():
        return ""
    try:
        result = subprocess.run([str(gltfpack_cmd), "-v"], capture_output=True, text=True, timeout=30)
    except OSError:
        return ""
    words = (result.stdout or result.stderr).split()
    return words[1] if len(words) > 1 and words[0] == "gltfpack" else ""


def ensure_gltfpack(gltfpack_dir: Path = GLTFPACK_DIR) -> Path:
    """Path of the pinned gltfpack, downloading it when missing or another version."""
    gltfpack_cmd = gltfpack_dir / "gltfpack"
    if installed_version(gltfpack_cmd) == GLTFPACK_VERSION:
        return gltfpack_cmd

    logger.info(f"Downloading gltfpack {GLTFPACK_VERSION} from {GLTFPACK_URL}")
    response = requests.get(GLTFPACK_URL, timeout=120)
    response.raise_for_status()
    gltfpack_dir.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(io.BytesIO(response.content)) as archive:
        member = next(name for name in archive.namelist() if os.path.basename(name) == "gltfpack")
        gltfpack_cmd.write_bytes(archive.read(member))
    gltfpack_cmd.chmod(gltfpack_cmd.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)

    version = installed_version(gltfpack_cmd)
    if version != GLTFPACK_VERSION:
        raise RuntimeError(f"{gltfpack_cmd} reports version {version!r}, expected {GLTFPACK_VERSION}")
    return gltfpack_cmd


def run_gltfpack(gltfpack_cmd: Path, input_file: Path, output_file: Path, options: List[str]) -> str:
    """Run gltfpack; returns its output (warnings). Raises on failure."""
    result = subprocess.run([str(gltfpack_cmd), "-i", str(input_file), "-o", str(output_file), *options],
                            capture_output=True, text=True)
    output = (result.stdout + result.stderr).strip()
    if result.returncode != 0:
        raise RuntimeError(f"gltfpack failed on {input_file} ({result.returncode}): {output}")
    return output
