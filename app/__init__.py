"""
Flask app factory.
We use the 'app factory pattern' (a function that returns a Flask app)
so that testing and managing multiple configs (dev/prod) is easier
in the future.
"""

from flask import Flask
from app.config import UPLOAD_FOLDER, FLASK_DEBUG, BASE_DIR, SECRET_KEY
from app.logger import get_logger
from app.db import init_db
import os

logger = get_logger(__name__)


def create_app():
    # template_folder and static_folder are set explicitly because this
    # package (app/) lives one level below the project root, while the
    # templates/ and static/ folders live at the project root itself.
    # Without this, Flask would look for them inside app/ and fail to
    # find them.
    app = Flask(
        __name__,
        template_folder=os.path.join(BASE_DIR, "templates"),
        static_folder=os.path.join(BASE_DIR, "static")
    )
    app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER
    app.config["DEBUG"] = FLASK_DEBUG
    app.secret_key = SECRET_KEY

    # Create the SQLite tables (e.g. users) if they don't exist yet
    init_db()

    # Blueprints are registered here as new routes are added
    from app.routes.health import health_bp
    from app.routes.upload import upload_bp
    from app.routes.ask import ask_bp
    from app.routes.pages import pages_bp
    from app.routes.auth import auth_bp
    from app.routes.history import history_bp
    from app.routes.documents import documents_bp
    app.register_blueprint(health_bp)
    app.register_blueprint(upload_bp)
    app.register_blueprint(ask_bp)
    app.register_blueprint(pages_bp)
    app.register_blueprint(auth_bp)
    app.register_blueprint(history_bp)
    app.register_blueprint(documents_bp)

    logger.info("Flask app initialized successfully.")
    return app