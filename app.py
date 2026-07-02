from flask import Flask
from flask_cors import CORS

from config import Config
from routes.api_routes import api_bp
from routes.page_routes import page_bp


def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)
    CORS(app)

    app.register_blueprint(page_bp)
    app.register_blueprint(api_bp, url_prefix="/api")

    return app


app = create_app()


if __name__ == "__main__":
    app.run(
        host="0.0.0.0",
        port=Config.PORT,
        debug=Config.FLASK_ENV == "development",
        use_reloader=False,
    )
