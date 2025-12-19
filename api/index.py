from flask import Flask

# teste de import isolado
from app import config

app = Flask(__name__)

@app.route("/")
def root():
    return "OK - Flask + config importado"

@app.route("/health")
def health():
    return {"status": "ok"}
