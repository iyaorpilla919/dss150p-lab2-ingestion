import pandas as pd
from pathlib import Path

PARQUET_PATH = Path("data/products.parquet")
CSV_PATH = Path("data/products.csv")
JSON_PATH = Path("data/products.json")

def profile_parquet(path: Path) -> pd.DataFrame:
    size_bytes = path.stat().st_size
    df = pd.read_parquet(path, engine="pyarrow")
    print(f"Parquet size: {size_bytes} bytes")
    print(f"Shape: {df.shape}")
    print("Dtypes:")
    print(df.dtypes)
    return df

def compare_formats() -> None:
    if CSV_PATH.exists():
        csv_size = CSV_PATH.stat().st_size
        csv_df = pd.read_csv(CSV_PATH)
        print(f"\nCSV size: {csv_size} bytes, dtypes inferred on read: {dict(csv_df.dtypes)}")
    if JSON_PATH.exists():
        json_size = JSON_PATH.stat().st_size
        print(f"JSON size: {json_size} bytes")

if __name__ == "__main__":
    profile_parquet(PARQUET_PATH)
    compare_formats()
    print("\nParquet preserves exact schema/types and is columnar (fast analytics, small size),")
    print("but it is not a common operational/transactional source format since operational")
    print("systems emit row-oriented, human-readable, append-friendly formats (CSV/JSON/DB rows).")