import json
from pathlib import Path
from collections import Counter

PATH = Path("data/orders.json")

def profile_json(path: Path) -> None:
    data = json.loads(path.read_text())
    assert isinstance(data, list), "Root structure is not a list of records"

    print(f"Record count: {len(data)}")

    all_keys = Counter()
    nested_fields = set()
    for record in data:
        all_keys.update(record.keys())
        for k, v in record.items():
            if isinstance(v, dict):
                nested_fields.add(k)

    print(f"Top-level keys: {sorted(all_keys.keys())}")
    print(f"Nested fields: {nested_fields}")

    missing_by_key = {k: len(data) - c for k, c in all_keys.items()}
    print(f"Missing/absent-key counts: {missing_by_key}")

    sample = data[0]
    print("\nSample record:")
    print(json.dumps(sample, indent=2))

    print("\nLikely timestamp fields: those with 'date' or 'at' in the name.")
    print("Likely numeric fields: amount/total/quantity-style fields.")

    print("\nShipping representation options:")
    print("  1. Flatten shipping.* into top-level columns (shipping_city, shipping_zip, ...).")
    print("  2. Keep shipping as a nested/struct or JSON column and parse downstream.")

if __name__ == "__main__":
    profile_json(PATH)