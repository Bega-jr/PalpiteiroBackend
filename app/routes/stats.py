from flask import Blueprint, jsonify
from app.services.lotofacil_service import (
    ultimos_concursos,
    concurso_por_numero,
    estatisticas
)

stats_bp = Blueprint("lotofacil", __name__, url_prefix="/lotofacil")


@stats_bp.route("/ultimos/<int:qtd>")
def ultimos(qtd):
    try:
        return jsonify(ultimos_concursos(qtd))
    except Exception as e:
        return jsonify({"erro": str(e)}), 500


@stats_bp.route("/concurso/<int:numero>")
def concurso(numero):
    try:
        resultado = concurso_por_numero(numero)
        if not resultado:
            return jsonify({"erro": "Concurso não encontrado"}), 404
        return jsonify(resultado)
    except Exception as e:
        return jsonify({"erro": str(e)}), 500


@stats_bp.route("/estatisticas")
def stats():
    try:
        return jsonify(estatisticas())
    except Exception as e:
        return jsonify({"erro": str(e)}), 500
