import json
from pathlib import Path

import pandas as pd


def validate() -> None:
    # File ingestion checks
    assert Path("raw/files/customers.csv").exists(), "customers.csv not ingested"
    assert Path("raw/files/orders.json").exists(), "orders.json not ingested"
    assert Path("raw/files/products.parquet").exists(), "products.parquet not ingested"

    manifest = json.loads(Path("raw/files/manifest.json").read_text())
    assert all("sha256" in v for v in manifest.values()), "manifest missing hashes"
    assert all("ingested_at_utc" in v for v in manifest.values()), "manifest missing ingestion timestamps"

    # API ingestion checks
    events = [
        json.loads(line)
        for line in Path("raw/api/events.jsonl").read_text().splitlines()
        if line.strip()
    ]
    ids = [e["event_id"] for e in events]
    assert len(ids) == len(set(ids)), "duplicate event_id found in raw output"
    assert all("_ingested_at" in e for e in events), "missing _ingested_at on API records"
    assert all("updated_at" in e for e in events), "missing updated_at on API records"

    # Watermark checks
    watermark = json.loads(Path("state/api_watermark.json").read_text())
    assert watermark.get("watermark"), "watermark not persisted"

    # Run log checks
    log = pd.read_csv("outputs/run_log.csv")
    assert not log.empty, "run log is empty"
    assert set(log["status"].unique()) <= {"success", "failed"}, "unexpected status value in run log"

    print("All validation checks passed.")


if __name__ == "__main__":
    validate()