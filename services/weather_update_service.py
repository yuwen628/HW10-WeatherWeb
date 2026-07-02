import sqlite3
from datetime import datetime, timedelta

from config import Config
from cwa_to_sqlite import delete_old_observations, fetch_cwa_data, save_stations
from services.db_service import get_connection


UPDATE_THRESHOLD = timedelta(hours=3)
FETCH_COOLDOWN = timedelta(minutes=15)
UPDATE_STATE_ID = 1


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


def should_update_weather_data(now=None, latest_obs_time=None):
    if latest_obs_time is None:
        latest_obs_time = get_latest_obs_time()
    if latest_obs_time is None:
        return True

    current_time = normalized_now(latest_obs_time, now)
    return current_time > latest_obs_time + UPDATE_THRESHOLD


def update_weather_data_if_stale():
    delete_old_observations(Config.DATABASE_PATH)
    latest_obs_time = get_latest_obs_time()

    if not should_update_weather_data(latest_obs_time=latest_obs_time):
        return False

    if is_fetch_in_cooldown(latest_obs_time):
        return False

    data = fetch_cwa_data()
    stations = data["cwaopendata"]["dataset"]["Station"]
    api_latest_obs_time = get_latest_api_obs_time(stations)

    if not is_newer_obs_time(api_latest_obs_time, latest_obs_time):
        record_fetch_attempt(api_latest_obs_time)
        return False

    save_stations(Config.DATABASE_PATH, stations)
    record_fetch_attempt(api_latest_obs_time)
    delete_old_observations(Config.DATABASE_PATH)
    return True


def create_update_state_table(conn):
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS weather_update_state (
            id INTEGER PRIMARY KEY CHECK (id = 1),
            last_fetch_attempt_at TEXT NOT NULL,
            last_api_obs_time TEXT
        )
        """
    )


def get_update_state():
    try:
        with get_connection() as conn:
            create_update_state_table(conn)
            conn.commit()
            row = conn.execute(
                """
                SELECT last_fetch_attempt_at, last_api_obs_time
                FROM weather_update_state
                WHERE id = ?
                """,
                (UPDATE_STATE_ID,),
            ).fetchone()
    except sqlite3.Error:
        return None

    return dict(row) if row else None


def record_fetch_attempt(api_obs_time):
    try:
        with get_connection() as conn:
            create_update_state_table(conn)
            conn.execute(
                """
                INSERT INTO weather_update_state (
                    id,
                    last_fetch_attempt_at,
                    last_api_obs_time
                )
                VALUES (?, ?, ?)
                ON CONFLICT(id) DO UPDATE SET
                    last_fetch_attempt_at = excluded.last_fetch_attempt_at,
                    last_api_obs_time = excluded.last_api_obs_time
                """,
                (
                    UPDATE_STATE_ID,
                    datetime.now().isoformat(timespec="seconds"),
                    api_obs_time.isoformat() if api_obs_time else None,
                ),
            )
            conn.commit()
    except sqlite3.Error:
        return


def is_fetch_in_cooldown(latest_obs_time, now=None):
    if latest_obs_time is None:
        return False

    state = get_update_state()
    if not state:
        return False

    last_attempt_at = parse_obs_time(state["last_fetch_attempt_at"])
    last_api_obs_time = parse_obs_time(state["last_api_obs_time"])
    if last_attempt_at is None or last_api_obs_time is None:
        return False

    if is_newer_obs_time(last_api_obs_time, latest_obs_time):
        return False

    current_time = normalized_now(last_attempt_at, now)
    return current_time <= last_attempt_at + FETCH_COOLDOWN


def get_latest_api_obs_time(stations):
    obs_times = [
        parse_obs_time(station.get("ObsTime", {}).get("DateTime"))
        for station in stations
    ]
    obs_times = [obs_time for obs_time in obs_times if obs_time is not None]
    return max(obs_times) if obs_times else None


def is_newer_obs_time(candidate_time, current_time):
    if current_time is None:
        return True
    if candidate_time is None:
        return True

    return normalized_now(current_time, candidate_time) > current_time


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
