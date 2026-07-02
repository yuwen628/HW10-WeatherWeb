from flask import Blueprint, current_app, render_template

from services.weather_update_service import update_weather_data_if_stale


page_bp = Blueprint("pages", __name__)


@page_bp.get("/")
def index():
    try:
        update_weather_data_if_stale()
    except Exception:
        current_app.logger.exception("Failed to update weather data before rendering index.")

    return render_template("index.html")
