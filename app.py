"""
Application entry point.
Run karne ke liye: python app.py
"""

from app import create_app

app = create_app()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)