from flask import Blueprint, jsonify
from app.statistics import estatisticas_globais

stats_bp = Blueprint(
    "stats",
    __name__,
    url_prefix="/lotofacil"
)


@stats_bp.route("/estatisticas", methods=["GET"])
def estatisticas():
    return jsonify(estatisticas_globais())

