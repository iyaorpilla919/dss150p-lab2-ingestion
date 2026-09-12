import pandas as pd
from pathlib import Path

PATH = Path("data/customers.csv")

def profile_csv(path: Path) -> None:
    size_bytes = path.stat().st_size
    df = pd.read_csv(path)

    print(f"File size: {size_bytes} bytes")
    print(f"Rows: {df.shape[0]}, Columns: {df.shape[1]}")

    print("\nColumn / inferred type:")
    for col in df.columns:
        print(f"  {col}: {df[col].dtype}")

    print("\nMissing values by column:")
    print(df.isnull().sum())

    dup_rows = df.duplicated(keep=False)
    print(f"\nExact duplicate rows: {dup_rows.sum()}")

    if "customer_id" in df.columns:
        is_unique = df["customer_id"].is_unique
        n_dupes = df["customer_id"].duplicated().sum()
        print(f"\ncustomer_id unique: {is_unique} (duplicate keys: {n_dupes})")

    print("\nCandidate validation rules:")
    print("  1. customer_id must be non-null and unique.")
    print("  2. email must match a valid email pattern.")
    print("  3. signup_date must be a parseable date not in the future.")

if __name__ == "__main__":
    profile_csv(PATH)