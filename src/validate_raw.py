from pathlib import Path
import json
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]

def main():
    assert (ROOT / "raw/files/customers.csv").exists(), "customers.csv not ingested"
    manifest = json.loads((ROOT / "raw/files/manifest.json").read_text())
    assert all("sha256" in v for v in manifest.values()), "manifest missing hashes"

    events_path = ROOT / "raw/api/events.jsonl"
    events = [json.loads(l) for l in events_path.read_text().splitlines() if l.strip()]
    ids = [e["event_id"] for e in events]
    assert len(ids) == len(set(ids)), "duplicate event_id found in raw output"
    assert all("_ingested_at" in e for e in events), "missing _ingested_at on API records"

    log = pd.read_csv(ROOT / "outputs/run_log.csv")
    assert not log.empty, "run log is empty"

    print("All validation checks passed.")

if __name__ == '__main__':
    main()