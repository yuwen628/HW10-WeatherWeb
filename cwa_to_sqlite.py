import json
import os
import ssl
import sqlite3
from datetime import datetime, timedelta
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import urlopen


BASE_URL = "https://opendata.cwa.gov.tw/fileapi/v1/opendataapi"
ENV_PATH = Path(".env")


def load_env(path):
    if not path.exists():
        return

    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue

        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


def as_number(value):
    if value in (None, "", "-99"):
        return None

    try:
        return float(value)
    except ValueError:
        return None


def get_wgs84_coordinate(geo_info):
    coordinates = geo_info.get("Coordinates", [])
    for coordinate in coordinates:
        if coordinate.get("CoordinateName") == "WGS84":
            return coordinate

    return coordinates[0] if coordinates else {}


def fetch_cwa_data():
    api_key = os.getenv("CWA_API_KEY")
    data_id = os.getenv("CWA_DATA_ID", "O-A0001-001")

    if not api_key:
        raise RuntimeError("請先在 .env 設定 CWA_API_KEY")

    params = urlencode(
        {
            "Authorization": api_key,
            "downloadType": os.getenv("CWA_DOWNLOAD_TYPE", "WEB"),
            "format": os.getenv("CWA_FORMAT", "JSON"),
        }
    )
    url = f"{BASE_URL}/{data_id}?{params}"

    context = ssl.create_default_context(cafile=get_certifi_path())
    if hasattr(ssl, "VERIFY_X509_STRICT"):
        context.verify_flags &= ~ssl.VERIFY_X509_STRICT

    with urlopen(url, timeout=30, context=context) as response:
        return json.loads(response.read().decode("utf-8"))


def get_certifi_path():
    try:
        import certifi
    except ImportError:
        return None

    return certifi.where()


def create_table(conn):
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS station_observations (
            station_id TEXT NOT NULL,
            station_name TEXT,
            obs_time TEXT NOT NULL,
            county_name TEXT,
            town_name TEXT,
            county_code TEXT,
            town_code TEXT,
            latitude REAL,
            longitude REAL,
            altitude REAL,
            weather TEXT,
            precipitation REAL,
            wind_direction REAL,
            wind_speed REAL,
            air_temperature REAL,
            relative_humidity REAL,
            air_pressure REAL,
            daily_high_temperature REAL,
            daily_high_time TEXT,
            daily_low_temperature REAL,
            daily_low_time TEXT,
            raw_json TEXT NOT NULL,
            PRIMARY KEY (station_id, obs_time)
        )
        """
    )


def station_to_row(station):
    geo_info = station.get("GeoInfo", {})
    weather_element = station.get("WeatherElement", {})
    coordinate = get_wgs84_coordinate(geo_info)
    daily_high = (
        weather_element.get("DailyExtreme", {})
        .get("DailyHigh", {})
        .get("TemperatureInfo", {})
    )
    daily_low = (
        weather_element.get("DailyExtreme", {})
        .get("DailyLow", {})
        .get("TemperatureInfo", {})
    )

    return {
        "station_id": station.get("StationId"),
        "station_name": station.get("StationName"),
        "obs_time": station.get("ObsTime", {}).get("DateTime"),
        "county_name": geo_info.get("CountyName"),
        "town_name": geo_info.get("TownName"),
        "county_code": geo_info.get("CountyCode"),
        "town_code": geo_info.get("TownCode"),
        "latitude": as_number(coordinate.get("StationLatitude")),
        "longitude": as_number(coordinate.get("StationLongitude")),
        "altitude": as_number(geo_info.get("StationAltitude")),
        "weather": weather_element.get("Weather"),
        "precipitation": as_number(weather_element.get("Now", {}).get("Precipitation")),
        "wind_direction": as_number(weather_element.get("WindDirection")),
        "wind_speed": as_number(weather_element.get("WindSpeed")),
        "air_temperature": as_number(weather_element.get("AirTemperature")),
        "relative_humidity": as_number(weather_element.get("RelativeHumidity")),
        "air_pressure": as_number(weather_element.get("AirPressure")),
        "daily_high_temperature": as_number(daily_high.get("AirTemperature")),
        "daily_high_time": daily_high.get("Occurred_at", {}).get("DateTime"),
        "daily_low_temperature": as_number(daily_low.get("AirTemperature")),
        "daily_low_time": daily_low.get("Occurred_at", {}).get("DateTime"),
        "raw_json": json.dumps(station, ensure_ascii=False),
    }


def save_stations(db_path, stations):
    rows = [station_to_row(station) for station in stations]
    columns = list(rows[0].keys()) if rows else []
    placeholders = ", ".join([f":{column}" for column in columns])
    update_columns = [column for column in columns if column not in ("station_id", "obs_time")]
    updates = ", ".join([f"{column} = excluded.{column}" for column in update_columns])

    conn = sqlite3.connect(db_path)
    try:
        create_table(conn)
        if rows:
            conn.executemany(
                f"""
                INSERT INTO station_observations ({", ".join(columns)})
                VALUES ({placeholders})
                ON CONFLICT(station_id, obs_time) DO UPDATE SET {updates}
                """,
                rows,
            )

        total = conn.execute("SELECT COUNT(*) FROM station_observations").fetchone()[0]
        conn.commit()
    finally:
        conn.close()

    return len(rows), total


def delete_old_observations(db_path, keep_days=1):
    conn = sqlite3.connect(db_path)
    try:
        row = conn.execute(
            """
            SELECT obs_time
            FROM station_observations
            WHERE obs_time IS NOT NULL
            ORDER BY obs_time DESC
            LIMIT 1
            """
        ).fetchone()
        if not row:
            return 0

        latest_obs_time = parse_obs_time(row[0])
        if latest_obs_time is None:
            return 0

        cutoff = (latest_obs_time - timedelta(days=keep_days)).isoformat()
        cursor = conn.execute(
            """
            DELETE FROM station_observations
            WHERE obs_time <= ?
            """,
            (cutoff,),
        )
        deleted_count = cursor.rowcount
        conn.commit()
    except sqlite3.Error:
        return 0
    finally:
        conn.close()

    return deleted_count


def parse_obs_time(value):
    if not value:
        return None

    try:
        return datetime.fromisoformat(value)
    except ValueError:
        return None


def main():
    load_env(ENV_PATH)
    data = fetch_cwa_data()
    stations = data["cwaopendata"]["dataset"]["Station"]
    db_path = os.getenv("CWA_SQLITE_DB", "data/weather.db")
    saved_count, total_count = save_stations(db_path, stations)
    deleted_count = delete_old_observations(db_path)
    total_count -= deleted_count

    print(f"Saved {saved_count} station observations to {db_path}.")
    print(f"Deleted {deleted_count} station observations older than 1 day.")
    print(f"Total rows in station_observations: {total_count}")


if __name__ == "__main__":
    main()
