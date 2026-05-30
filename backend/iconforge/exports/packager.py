"""Pack a built directory tree into a single ZIP for delivery."""
from __future__ import annotations

import zipfile
from pathlib import Path


def build_zip(pack_dir: Path, zip_path: Path) -> Path:
    """Zip every file under `pack_dir` into `zip_path`. Returns the zip path."""
    zip_path.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for f in sorted(pack_dir.rglob("*")):
            if f.is_file():
                zf.write(f, arcname=f.relative_to(pack_dir).as_posix())
    return zip_path
