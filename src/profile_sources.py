from pathlib import Path
import json, csv
import pandas as pd

DATA_DIR = Path(__file__).resolve().parents[1] / 'data'

def profile_csv(path):
    size_bytes = path.stat().st_size
    df = pd.read_csv(path)
    print(f"\n--- {path.name} ---")
    print(f"File size: {size_bytes} bytes")
    print(f"Rows: {df.shape[0]}, Columns: {df.shape[1]}")
    print("Dtypes:")
    print(df.dtypes)
    print("Missing values by column:")
    print(df.isnull().sum())
    print(f"Exact duplicate rows: {df.duplicated(keep=False).sum()}")
    if "customer_id" in df.columns:
        print(f"customer_id unique: {df['customer_id'].is_unique} "
              f"(duplicate keys: {df['customer_id'].duplicated().sum()})")
    return df

def profile_json(path):
    data = json.loads(path.read_text())
    assert isinstance(data, list), "Root structure is not a list of records"
    print(f"\n--- {path.name} ---")
    print(f"Record count: {len(data)}")
    keys = set()
    nested = set()
    for record in data:
        keys.update(record.keys())
        for k, v in record.items():
            if isinstance(v, dict):
                nested.add(k)
    print(f"Top-level keys: {sorted(keys)}")
    print(f"Nested fields: {nested}")
    missing = {k: sum(1 for r in data if k not in r) for k in keys}
    print(f"Missing/absent-key counts: {missing}")
    print(f"Sample record: {json.dumps(data[0], indent=2)}")
    return data

def profile_parquet(path):
    size_bytes = path.stat().st_size
    df = pd.read_parquet(path, engine="pyarrow")
    print(f"\n--- {path.name} ---")
    print(f"File size: {size_bytes} bytes")
    print(f"Shape: {df.shape}")
    print("Dtypes:")
    print(df.dtypes)
    print("Missing values by column:")
    print(df.isnull().sum())
    return df

if __name__ == '__main__':
    profile_csv(DATA_DIR / 'customers.csv')
    profile_json(DATA_DIR / 'orders.json')
    profile_parquet(DATA_DIR / 'products.parquet')