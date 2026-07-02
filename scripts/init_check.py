import sqlite3
from pathlib import Path


db_path = Path(__file__).resolve().parents[1] / "data" / "weather.db"

if not db_path.exists():
    raise SystemExit(f"Database not found: {db_path}")

with sqlite3.connect(db_path) as conn:
    count = conn.execute("SELECT COUNT(*) FROM station_observations").fetchone()[0]

print(f"Database ready: {db_path}")
print(f"station_observations rows: {count}")
