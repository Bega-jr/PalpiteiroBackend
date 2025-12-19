from flask import Flask

from app.services.lotofacil_service import load_lotofacil_data

app = Flask(__name__)

@app.route("/")
def root():
    return "OK - Flask + service importado"

@app.route("/health")
def health():
    return {"status": "ok"}
