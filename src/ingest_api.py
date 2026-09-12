import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

import requests

from src.run_log import append_run_log

BASE_URL = "http://127.0.0.1:8000/api/events"
RAW_DIR = Path("raw/api")
RAW_FILE = RAW_DIR / "events.jsonl"
STATE_DIR = Path("state")
WATERMARK_PATH = STATE_DIR / "api_watermark.json"


def read_watermark() -> Optional[str]:
    if WATERMARK_PATH.exists():
        return json.loads(WATERMARK_PATH.read_text()).get("watermark")
    return None


def write_watermark(value: str) -> None:
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    tmp = WATERMARK_PATH.with_suffix(".tmp")
    tmp.write_text(json.dumps({"watermark": value}))
    tmp.replace(WATERMARK_PATH)


def fetch_all_pages(updated_after: Optional[str]) -> list[dict]:
    items = []
    page = 1
    while True:
        params = {"page": page, "per_page": 25}
        if updated_after:
            params["updated_after"] = updated_after
        resp = requests.get(BASE_URL, params=params, timeout=10)
        resp.raise_for_status()
        payload = resp.json()
        items.extend(payload["items"])
        if not payload.get("has_more"):
            break
        page += 1
    return items


def load_existing_raw() -> list[dict]:
    if RAW_FILE.exists():
        with RAW_FILE.open() as f:
            return [json.loads(line) for line in f if line.strip()]
    return []


def deduplicate(records: list[dict]) -> tuple[list[dict], int]:
    """Keep one logical record per event_id: the one with the greatest
    updated_at. event_id alone is not enough to decide which copy is
    current, since the source deliberately repeats event_id values."""
    best: dict[str, dict] = {}
    for rec in records:
        eid = rec["event_id"]
        if eid not in best or rec["updated_at"] > best[eid]["updated_at"]:
            best[eid] = rec
    deduped = list(best.values())
    duplicates_removed = len(records) - len(deduped)
    return deduped, duplicates_removed


def write_raw_atomic(records: list[dict]) -> None:
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    tmp = RAW_FILE.with_suffix(".tmp")
    with tmp.open("w") as f:
        for rec in sorted(records, key=lambda r: r["event_id"]):
            f.write(json.dumps(rec) + "\n")
    os.replace(tmp, RAW_FILE)


def run_ingest_api() -> dict:
    watermark_before = read_watermark()
    new_items = fetch_all_pages(watermark_before)

    now_iso = datetime.now(timezone.utc).isoformat()
    for rec in new_items:
        rec["_ingested_at"] = now_iso
        rec["_source"] = "rest_api_events"

    existing = load_existing_raw()
    combined = existing + new_items
    deduped, duplicates_removed = deduplicate(combined)

    # Raw write happens BEFORE the watermark is touched.
    write_raw_atomic(deduped)

    watermark_after = max((r["updated_at"] for r in deduped), default=watermark_before)
    if watermark_after:
        write_watermark(watermark_after)

    return {
        "records_read": len(new_items),
        "records_written": len(deduped),
        "duplicates_removed": duplicates_removed,
        "watermark_before": watermark_before,
        "watermark_after": watermark_after,
    }


if __name__ == "__main__":
    start = datetime.now(timezone.utc).isoformat()
    try:
        result = run_ingest_api()
        append_run_log("rest_api_events", start, "success", **result)
        print(result)
    except Exception as e:
        # Watermark was never touched above this point on failure,
        # so a failed run cannot advance it.
        append_run_log("rest_api_events", start, "failed", error_message=str(e))
        raise