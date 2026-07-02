import sqlite3
from datetime import datetime, timedelta

from config import Config
from cwa_to_sqlite import delete_old_observations, fetch_cwa_data, save_stations
from services.db_service import get_connection


UPDATE_THRESHOLD = timedelta(hours=3)


def get_latest_obs_time():
    try:
        with get_connection() as conn:
            row = conn.execute(
                """
                SELECT obs_time
                FROM station_observations
                WHERE obs_time IS NOT NULL
                ORDER BY obs_time DESC
                LIMIT 1
                """
            ).fetchone()
    except sqlite3.Error:
        return None

    if not row:
        return None

    return parse_obs_time(row["obs_time"])


def should_update_weather_data(now=None):
    latest_obs_time = get_latest_obs_time()
    if latest_obs_time is None:
        return True

    current_time = normalized_now(latest_obs_time, now)
    return current_time > latest_obs_time + UPDATE_THRESHOLD


def update_weather_data_if_stale():
    delete_old_observations(Config.DATABASE_PATH)

    if not should_update_weather_data():
        return False

    data = fetch_cwa_data()
    stations = data["cwaopendata"]["dataset"]["Station"]
    save_stations(Config.DATABASE_PATH, stations)
    delete_old_observations(Config.DATABASE_PATH)
    return True


def normalized_now(reference_time, now=None):
    if reference_time.tzinfo is not None:
        if now is None:
            return datetime.now(reference_time.tzinfo)
        if now.tzinfo is None:
            return now.replace(tzinfo=reference_time.tzinfo)
        return now.astimezone(reference_time.tzinfo)

    if now is None:
        return datetime.now()
    if now.tzinfo is not None:
        return now.replace(tzinfo=None)
    return now


def parse_obs_time(value):
    if not value:
        return None

    try:
        return datetime.fromisoformat(value)
    except ValueError:
        return None
