import hashlib
import json
import shutil
from datetime import datetime, timezone
from pathlib import Path

from src.run_log import append_run_log

SOURCE_FILES = [
    Path("data/customers.csv"),
    Path("data/orders.json"),
    Path("data/products.parquet"),
]
RAW_DIR = Path("raw/files")
MANIFEST_PATH = RAW_DIR / "manifest.json"


def sha256_of(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()


def load_manifest() -> dict:
    if MANIFEST_PATH.exists():
        return json.loads(MANIFEST_PATH.read_text())
    return {}


def save_manifest(manifest: dict) -> None:
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    tmp = MANIFEST_PATH.with_suffix(".tmp")
    tmp.write_text(json.dumps(manifest, indent=2))
    tmp.replace(MANIFEST_PATH)


def ingest_files() -> dict:
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    manifest = load_manifest()
    copied, skipped = 0, 0

    for src in SOURCE_FILES:
        if not src.exists():
            raise FileNotFoundError(f"Expected source file not found: {src}")

        file_hash = sha256_of(src)
        existing = manifest.get(src.name)

        if existing and existing.get("sha256") == file_hash:
            skipped += 1
            continue

        dest = RAW_DIR / src.name
        shutil.copy2(src, dest)
        manifest[src.name] = {
            "ingested_at_utc": datetime.now(timezone.utc).isoformat(),
            "byte_size": src.stat().st_size,
            "sha256": file_hash,
        }
        copied += 1

    save_manifest(manifest)
    return {"copied": copied, "skipped": skipped}


if __name__ == "__main__":
    start = datetime.now(timezone.utc).isoformat()
    try:
        result = ingest_files()
        append_run_log(
            "file_sources",
            start,
            "success",
            records_read=result["copied"] + result["skipped"],
            records_written=result["copied"],
        )
        print(result)
    except Exception as e:
        append_run_log("file_sources", start, "failed", error_message=str(e))
        raise