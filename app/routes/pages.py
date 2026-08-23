"""
Pages route.
Serves the front-end HTML page(s) of the application.
Kept separate from the API routes (upload, ask) since this handles
rendering a page, not JSON data.
"""

from flask import Blueprint, render_template

pages_bp = Blueprint("pages", __name__)


@pages_bp.route("/", methods=["GET"])
def index():
    return render_template("index.html")