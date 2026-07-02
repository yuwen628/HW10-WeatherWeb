import math
from datetime import datetime, timedelta

from services.db_service import get_connection


def success(data=None, message="ok"):
    return {"success": True, "message": message, "data": data}


def error(message, status_code=400):
    return {"success": False, "message": message, "data": None}, status_code


def get_locations():
    with get_connection() as conn:
        rows = conn.execute(
            """
            SELECT so.station_id, so.station_name, so.county_name, so.town_name, so.latitude, so.longitude
            FROM station_observations AS so
            JOIN (
                SELECT station_id, MAX(obs_time) AS obs_time
                FROM station_observations
                GROUP BY station_id
            ) AS latest
              ON latest.station_id = so.station_id
             AND latest.obs_time = so.obs_time
            WHERE latitude IS NOT NULL
              AND longitude IS NOT NULL
            ORDER BY county_name, town_name, station_name
            """
        ).fetchall()

    return [
        {
            "id": row["station_id"],
            "name": row["station_name"],
            "county": row["county_name"],
            "town": row["town_name"],
            "lat": row["latitude"],
            "lon": row["longitude"],
        }
        for row in rows
    ]


def get_weather_by_location(location):
    row = find_station(location)
    if not row:
        return None

    return {
        "location": row["station_name"],
        "station_id": row["station_id"],
        "county": row["county_name"],
        "town": row["town_name"],
        "lat": row["latitude"],
        "lon": row["longitude"],
        "updated_at": format_time(row["obs_time"]),
        "current": row_to_current(row),
        "forecast": build_forecast(row),
    }


def find_station(location):
    query = f"%{location}%"
    with get_connection() as conn:
        return conn.execute(
            """
            SELECT *
            FROM station_observations
            WHERE station_id = ?
               OR station_name LIKE ?
               OR county_name LIKE ?
               OR town_name LIKE ?
            ORDER BY
                CASE
                    WHEN station_id = ? THEN 0
                    WHEN station_name = ? THEN 1
                    ELSE 2
                END,
                obs_time DESC,
                station_name
            LIMIT 1
            """,
            (location, query, query, query, location, location),
        ).fetchone()


def get_nearby_weather(lat, lon):
    locations = get_locations()
    if not locations:
        return None

    nearest = min(locations, key=lambda item: haversine(lat, lon, item["lat"], item["lon"]))
    weather = get_weather_by_location(nearest["id"])
    if weather:
        weather["distance_km"] = round(haversine(lat, lon, nearest["lat"], nearest["lon"]), 2)

    return weather


def get_county_temperatures():
    with get_connection() as conn:
        rows = conn.execute(
            """
            SELECT so.county_name,
                   AVG(so.air_temperature) AS average_temperature,
                   COUNT(so.air_temperature) AS station_count,
                   MAX(so.obs_time) AS latest_obs_time
            FROM station_observations AS so
            JOIN (
                SELECT station_id, MAX(obs_time) AS obs_time
                FROM station_observations
                GROUP BY station_id
            ) AS latest
              ON latest.station_id = so.station_id
             AND latest.obs_time = so.obs_time
            WHERE so.county_name IS NOT NULL
              AND so.air_temperature IS NOT NULL
            GROUP BY so.county_name
            ORDER BY so.county_name
            """
        ).fetchall()

    return [
        {
            "county": row["county_name"],
            "temperature": round(row["average_temperature"], 1),
            "station_count": row["station_count"],
            "updated_at": format_time(row["latest_obs_time"]),
        }
        for row in rows
    ]


def get_weather_summary(location):
    weather = get_weather_by_location(location)
    if not weather:
        return None

    current = weather["current"]
    summary_parts = [f"{weather['location']}目前天氣{current['weather'] or '無明確天氣描述'}"]
    temperature = current["temperature"]
    humidity = current["humidity"]
    rain_probability = current["rain_probability"]
    wind_speed = current["wind_speed"]

    if temperature is not None:
        summary_parts.append(f"氣溫約 {temperature:g} 度")
        if temperature > 32:
            summary_parts.append("天氣偏熱，外出請補充水分並注意防曬")

    if humidity is not None:
        summary_parts.append(f"相對濕度 {humidity:g}%")

    if rain_probability is not None and rain_probability > 60:
        summary_parts.append("降雨機率偏高，建議攜帶雨具")
    elif current["precipitation"] and current["precipitation"] > 0:
        summary_parts.append("近期已有降雨紀錄，路面可能濕滑")

    if wind_speed is not None and wind_speed >= 8:
        summary_parts.append("風勢較強，請留意戶外活動安全")

    return {"location": weather["location"], "summary": "，".join(summary_parts) + "。"}


def row_to_current(row):
    precipitation = row["precipitation"]
    return {
        "temperature": row["air_temperature"],
        "humidity": row["relative_humidity"],
        "rain_probability": estimate_rain_probability(precipitation, row["relative_humidity"]),
        "precipitation": precipitation,
        "wind_speed": row["wind_speed"],
        "wind_direction": row["wind_direction"],
        "weather": row["weather"],
        "air_pressure": row["air_pressure"],
        "daily_high_temperature": row["daily_high_temperature"],
        "daily_low_temperature": row["daily_low_temperature"],
    }


def build_forecast(row):
    base_time = parse_time(row["obs_time"]) or datetime.now()
    current_temp = row["air_temperature"]
    current_humidity = row["relative_humidity"]
    rain_probability = estimate_rain_probability(row["precipitation"], current_humidity)

    forecast = []
    for index, hours in enumerate((3, 6, 9, 12, 24), start=1):
        item_time = base_time + timedelta(hours=hours)
        forecast.append(
            {
                "time": item_time.strftime("%Y-%m-%d %H:%M:%S"),
                "temperature": adjust_temperature(current_temp, index),
                "humidity": adjust_humidity(current_humidity, index),
                "rain_probability": max(0, min(100, rain_probability + (index % 3 - 1) * 8)),
                "wind_speed": row["wind_speed"],
                "weather": row["weather"],
            }
        )

    return forecast


def estimate_rain_probability(precipitation, humidity):
    if precipitation is not None and precipitation > 0:
        return min(95, 65 + precipitation * 5)
    if humidity is None:
        return 20
    if humidity >= 85:
        return 55
    if humidity >= 70:
        return 35
    return 15


def adjust_temperature(value, index):
    if value is None:
        return None
    offsets = [0.8, 1.2, 0.4, -0.6, -1.0]
    return round(value + offsets[index - 1], 1)


def adjust_humidity(value, index):
    if value is None:
        return None
    offsets = [-3, -5, -1, 4, 6]
    return max(0, min(100, round(value + offsets[index - 1], 1)))


def parse_time(value):
    if not value:
        return None
    try:
        return datetime.fromisoformat(value)
    except ValueError:
        return None


def format_time(value):
    parsed = parse_time(value)
    if not parsed:
        return value
    return parsed.strftime("%Y-%m-%d %H:%M:%S")


def haversine(lat1, lon1, lat2, lon2):
    radius_km = 6371
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = (
        math.sin(dlat / 2) ** 2
        + math.cos(math.radians(lat1))
        * math.cos(math.radians(lat2))
        * math.sin(dlon / 2) ** 2
    )
    return radius_km * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
