from services.db_service import get_connection


def get_schema():
    with get_connection() as conn:
        tables = conn.execute(
            "SELECT name FROM sqlite_master WHERE type = 'table' ORDER BY name"
        ).fetchall()

        schema = []
        for table in tables:
            table_name = table["name"]
            columns = conn.execute(f"PRAGMA table_info({table_name})").fetchall()
            schema.append(
                {
                    "table": table_name,
                    "columns": [
                        {
                            "name": column["name"],
                            "type": column["type"],
                            "not_null": bool(column["notnull"]),
                            "primary_key": bool(column["pk"]),
                        }
                        for column in columns
                    ],
                }
            )

    return schema
