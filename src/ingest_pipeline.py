from pathlib import Path
from datetime import datetime, timezone
import json, hashlib, shutil, csv, uuid, os
import requests

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / 'data'; RAW = ROOT / 'raw'; STATE = ROOT / 'state'
API_URL = 'http://127.0.0.1:8000/api/events'
RUN_LOG = ROOT / 'outputs' / 'run_log.csv'
LOG_HEADER = ["run_id", "source", "start_time", "end_time", "status",
              "records_read", "records_written", "duplicates_removed",
              "watermark_before", "watermark_after", "error_message"]

def utc_now(): return datetime.now(timezone.utc).isoformat()

def sha256_file(path):
    h = hashlib.sha256()
    with path.open('rb') as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b''):
            h.update(chunk)
    return h.hexdigest()

def load_watermark():
    p = STATE / 'api_watermark.json'
    if not p.exists(): return None
    return json.loads(p.read_text())['updated_at']

def save_watermark(value):
    STATE.mkdir(exist_ok=True)
    tmp = STATE / 'api_watermark.json.tmp'
    tmp.write_text(json.dumps({'updated_at': value}, indent=2))
    tmp.replace(STATE / 'api_watermark.json')

def append_run_log(source, start_time, status, records_read=0, records_written=0,
                    duplicates_removed=0, watermark_before=None, watermark_after=None,
                    error_message=""):
    RUN_LOG.parent.mkdir(parents=True, exist_ok=True)
    new_file = not RUN_LOG.exists()
    with RUN_LOG.open("a", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=LOG_HEADER)
        if new_file:
            writer.writeheader()
        writer.writerow({
            "run_id": str(uuid.uuid4()), "source": source, "start_time": start_time,
            "end_time": utc_now(), "status": status, "records_read": records_read,
            "records_written": records_written, "duplicates_removed": duplicates_removed,
            "watermark_before": watermark_before, "watermark_after": watermark_after,
            "error_message": error_message,
        })

def ingest_files():
    files_dir = RAW / 'files'
    files_dir.mkdir(parents=True, exist_ok=True)
    manifest_path = files_dir / 'manifest.json'
    manifest = json.loads(manifest_path.read_text()) if manifest_path.exists() else {}

    source_files = [DATA / 'customers.csv', DATA / 'orders.json', DATA / 'products.parquet']
    copied, skipped = 0, 0

    for src in source_files:
        file_hash = sha256_file(src)
        existing = manifest.get(src.name)
        if existing and existing['sha256'] == file_hash:
            skipped += 1
            continue
        shutil.copy2(src, files_dir / src.name)
        manifest[src.name] = {
            'source_file': src.name,
            'ingested_at': utc_now(),
            'bytes': src.stat().st_size,
            'sha256': file_hash,
        }
        copied += 1

    manifest_path.write_text(json.dumps(manifest, indent=2))
    return {"copied": copied, "skipped": skipped}

def fetch_api_page(page, per_page=20, updated_after=None):
    params = {'page': page, 'per_page': per_page}
    if updated_after: params['updated_after'] = updated_after
    r = requests.get(API_URL, params=params, timeout=30)
    r.raise_for_status()
    return r.json()

def ingest_api():
    api_dir = RAW / 'api'
    api_dir.mkdir(parents=True, exist_ok=True)
    raw_file = api_dir / 'events.jsonl'

    watermark_before = load_watermark()

    new_items = []
    page = 1
    while True:
        payload = fetch_api_page(page, updated_after=watermark_before)
        new_items.extend(payload['items'])
        if not payload['has_more']:
            break
        page += 1

    now_iso = utc_now()
    for rec in new_items:
        rec['_ingested_at'] = now_iso
        rec['_source'] = 'rest_api_events'

    existing = []
    if raw_file.exists():
        existing = [json.loads(l) for l in raw_file.read_text().splitlines() if l.strip()]

    combined = existing + new_items
    best = {}
    for rec in combined:
        eid = rec['event_id']
        if eid not in best or rec['updated_at'] > best[eid]['updated_at']:
            best[eid] = rec
    deduped = list(best.values())
    duplicates_removed = len(combined) - len(deduped)

    tmp = api_dir / 'events.jsonl.tmp'
    with tmp.open('w') as f:
        for rec in sorted(deduped, key=lambda r: r['event_id']):
            f.write(json.dumps(rec) + '\n')
    os.replace(tmp, raw_file)

    watermark_after = max((r['updated_at'] for r in deduped), default=watermark_before)
    if watermark_after:
        save_watermark(watermark_after)

    return {
        "records_read": len(new_items), "records_written": len(deduped),
        "duplicates_removed": duplicates_removed,
        "watermark_before": watermark_before, "watermark_after": watermark_after,
    }

if __name__ == '__main__':
    RAW.mkdir(exist_ok=True); STATE.mkdir(exist_ok=True)

    start = utc_now()
    try:
        result = ingest_files()
        append_run_log("file_sources", start, "success",
                        records_read=result["copied"] + result["skipped"],
                        records_written=result["copied"])
        print("ingest_files:", result)
    except Exception as e:
        append_run_log("file_sources", start, "failed", error_message=str(e))
        raise

    start = utc_now()
    try:
        result = ingest_api()
        append_run_log("rest_api_events", start, "success", **result)
        print("ingest_api:", result)
    except Exception as e:
        append_run_log("rest_api_events", start, "failed", error_message=str(e))
        raise