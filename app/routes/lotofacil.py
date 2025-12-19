from flask import Blueprint, jsonify
from app.services.lotofacil_service import (
    ultimos_concursos,
    concurso_por_numero,
)
from app.statistics import gerar_estatisticas

lotofacil_bp = Blueprint("lotofacil", __name__)


@lotofacil_bp.route("/ultimos/<int:quantidade>")
def ultimos(quantidade):
    return jsonify(ultimos_concursos(quantidade))


@lotofacil_bp.route("/concurso/<int:numero>")
def concurso(numero):
    return jsonify(concurso_por_numero(numero))


@lotofacil_bp.route("/estatisticas")
def estatisticas():
    return jsonify(gerar_estatisticas())
