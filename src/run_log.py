import csv
import uuid
from datetime import datetime, timezone
from pathlib import Path

LOG_PATH = Path("outputs/run_log.csv")
HEADER = [
    "run_id", "started_at", "finished_at", "status", "source",
    "records_read", "records_written", "duplicates_removed",
    "watermark_before", "watermark_after", "error_message",
]


def append_run_log(
    source: str,
    start_time: str,
    status: str,
    records_read: int = 0,
    records_written: int = 0,
    duplicates_removed: int = 0,
    watermark_before=None,
    watermark_after=None,
    error_message: str = "",
) -> None:
    LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    new_file = not LOG_PATH.exists()
    with LOG_PATH.open("a", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=HEADER)
        if new_file:
            writer.writeheader()
        writer.writerow({
            "run_id": str(uuid.uuid4()),
            "started_at": start_time,
            "finished_at": datetime.now(timezone.utc).isoformat(),
            "status": status,
            "source": source,
            "records_read": records_read,
            "records_written": records_written,
            "duplicates_removed": duplicates_removed,
            "watermark_before": watermark_before,
            "watermark_after": watermark_after,
            "error_message": error_message,
        })