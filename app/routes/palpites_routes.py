from flask import Blueprint, jsonify
from app.services.palpites_service import gerar_7_palpites, gerar_palpite_fixo

palpites_bp = Blueprint("palpites", __name__)


# =====================================================
# PALPITE FIXO (PÚBLICO)
# =====================================================

@palpites_bp.route("/palpite/fixo", methods=["GET"])
def palpite_fixo():
    jogo = gerar_palpite_fixo()
    return jsonify({
        "tipo": "palpite_fixo",
        "numeros": jogo
    })


# =====================================================
# PALPITES ESTATÍSTICOS (FUTURO VIP)
# =====================================================

@palpites_bp.route("/palpite/estatisticos", methods=["GET"])
def palpites_estatisticos():
    palpites = gerar_7_palpites()
    return jsonify({
        "tipo": "estatisticos",
        "palpites": palpites
    })
