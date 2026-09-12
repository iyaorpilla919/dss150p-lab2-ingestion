import requests

BASE_URL = "http://127.0.0.1:8000/api/events"

def fetch_page(page: int, per_page: int = 10, updated_after: str | None = None) -> dict:
    params = {"page": page, "per_page": per_page}
    if updated_after:
        params["updated_after"] = updated_after
    resp = requests.get(BASE_URL, params=params, timeout=10)
    resp.raise_for_status()
    return resp.json()

if __name__ == "__main__":
    page1 = fetch_page(1)
    page2 = fetch_page(2)

    for label, payload in [("Page 1", page1), ("Page 2", page2)]:
        print(f"\n{label}")
        print(f"  page={payload['page']} per_page={payload['per_page']} "
              f"total={payload['total']} has_more={payload['has_more']} "
              f"next_page={payload.get('next_page')}")
        sample = payload["items"][0]
        print(f"  sample event_id={sample['event_id']} updated_at={sample['updated_at']} "
              f"amount={sample['amount']} metadata={sample.get('metadata')}")

    print("\nProcessing only page 1 is incomplete because has_more=true means additional")
    print("records exist beyond the first page's per_page limit; total exceeds one page's items.")