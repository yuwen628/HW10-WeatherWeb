from flask import Blueprint, jsonify, request

from services.db_service import database_connected
from services.schema_service import get_schema
from services.weather_service import (
    error,
    get_county_temperatures,
    get_locations,
    get_nearby_weather,
    get_weather_by_location,
    get_weather_summary,
    success,
)


api_bp = Blueprint("api", __name__)


@api_bp.get("/health")
def health():
    connected = database_connected()
    return jsonify(
        {
            "status": "ok" if connected else "error",
            "database": "connected" if connected else "disconnected",
        }
    )


@api_bp.get("/schema")
def schema():
    return jsonify(success(get_schema()))


@api_bp.get("/locations")
def locations():
    return jsonify(success(get_locations()))


@api_bp.get("/weather")
def weather():
    location = request.args.get("location", "").strip()
    if not location:
        payload, status = error("請提供 location 參數")
        return jsonify(payload), status

    data = get_weather_by_location(location)
    if not data:
        payload, status = error("找不到指定地點", 404)
        return jsonify(payload), status

    return jsonify(success(data))


@api_bp.get("/weather/nearby")
def nearby_weather():
    try:
        lat = float(request.args.get("lat", ""))
        lon = float(request.args.get("lon", ""))
    except ValueError:
        payload, status = error("請提供有效的 lat 與 lon")
        return jsonify(payload), status

    data = get_nearby_weather(lat, lon)
    if not data:
        payload, status = error("找不到附近觀測站", 404)
        return jsonify(payload), status

    return jsonify(success(data))


@api_bp.get("/weather/county-temperatures")
def county_temperatures():
    return jsonify(success(get_county_temperatures()))


@api_bp.get("/weather/summary")
def weather_summary():
    location = request.args.get("location", "").strip()
    if not location:
        payload, status = error("請提供 location 參數")
        return jsonify(payload), status

    data = get_weather_summary(location)
    if not data:
        payload, status = error("找不到指定地點", 404)
        return jsonify(payload), status

    return jsonify(success(data))
