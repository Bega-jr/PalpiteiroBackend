from flask import Flask
import traceback

def create_app():
    app = Flask(__name__)

    try:
        from app.routes.lotofacil import lotofacil_bp
        app.register_blueprint(lotofacil_bp, url_prefix="/lotofacil")
    except Exception as e:
        @app.route("/startup-error")
        def startup_error():
            return {
                "error": "Erro ao carregar rotas",
                "details": str(e),
                "trace": traceback.format_exc()
            }, 500

    @app.route("/health")
    def health():
        return {"status": "ok"}

    return app


app = create_app()
