"""
Pages route.
Serves the front-end HTML page(s) of the application.
Kept separate from the API routes (upload, ask) since this handles
rendering a page, not JSON data.
"""

from flask import Blueprint, render_template, session
from app.services.auth_service import login_required_page

pages_bp = Blueprint("pages", __name__)


@pages_bp.route("/", methods=["GET"])
@login_required_page
def index():
    return render_template("index.html", username=session.get("username"))