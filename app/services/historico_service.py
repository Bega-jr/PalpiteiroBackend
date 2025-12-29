import json
import uuid
from pathlib import Path
from datetime import datetime
from typing import List

from app.models.historico_model import JogoHistorico

# ==========================
# CONFIG
# ==========================

ARQUIVO_HISTORICO = Path("data/historico_jogos.json")
ARQUIVO_HISTORICO.parent.mkdir(exist_ok=True)


# ==========================
# HELPERS INTERNOS
# ==========================

def _carregar_historico() -> List[dict]:
    if not ARQUIVO_HISTORICO.exists():
        return []
    with open(ARQUIVO_HISTORICO, "r", encoding="utf-8") as f:
        return json.load(f)


def _salvar_historico(registros: List[dict]):
    with open(ARQUIVO_HISTORICO, "w", encoding="utf-8") as f:
        json.dump(
            registros,
            f,
            indent=2,
            ensure_ascii=False,
            default=str
        )


# ==========================
# API USADA PELAS ROTAS
# ==========================

def salvar_jogo(jogo: JogoHistorico) -> JogoHistorico:
    """
    Salva um jogo completo vindo da API
    """
    historico = _carregar_historico()

    registro = jogo.copy()
    registro.id = jogo.id or str(uuid.uuid4())
    registro.data = jogo.data or datetime.utcnow()

    historico.append(registro.dict())
    _salvar_historico(historico)

    return registro


def listar_historico() -> List[dict]:
    """
    Retorna todo o histórico salvo
    """
    return _carregar_historico()


def resumo_financeiro() -> dict:
    """
    Retorna resumo financeiro / ROI
    """
    historico = _carregar_historico()

    total_apostado = sum(
        float(j.get("valor_aposta", 0))
        for j in historico
    )

    total_premios = sum(
        float(j.get("premio", 0))
        for j in historico
    )

    return {
        "total_jogos": len(historico),
        "total_apostado": total_apostado,
        "total_premios": total_premios,
        "lucro": total_premios - total_apostado,
        "roi": (
            (total_premios - total_apostado) / total_apostado
            if total_apostado > 0 else 0
        )
    }


# ==========================
# COMPATIBILIDADE (opcional)
# ==========================

def registrar_jogo(
    tipo: str,
    numeros: list,
    score_medio=None,
    score_final=None,
    penalidade_sequencia=None,
    valor_aposta=3.0
) -> JogoHistorico:
    """
    Mantido por compatibilidade com código antigo
    """
    jogo = JogoHistorico(
        id=str(uuid.uuid4()),
        data=datetime.utcnow(),
        tipo=tipo,
        numeros=numeros,
        score_medio=score_medio,
        score_final=score_final,
        penalidade_sequencia=penalidade_sequencia,
        valor_aposta=valor_aposta
    )

    return salvar_jogo(jogo)
