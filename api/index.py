from flask import Flask
from app.routes.lotofacil import lotofacil_bp

def create_app():
    app = Flask(__name__)

    app.register_blueprint(lotofacil_bp, url_prefix="/lotofacil")

    @app.route("/health")
    def health():
        return {"status": "ok"}

    return app


app = create_app()
