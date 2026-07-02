import sqlite3
from pathlib import Path


db_path = Path(__file__).resolve().parents[1] / "data" / "weather.db"

with sqlite3.connect(db_path) as conn:
    tables = conn.execute("SELECT name FROM sqlite_master WHERE type = 'table'").fetchall()
    print("Tables:")
    for (table_name,) in tables:
        print(f"- {table_name}")
        for column in conn.execute(f"PRAGMA table_info({table_name})"):
            print(f"  {column}")
