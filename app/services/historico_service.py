import json
import uuid
from pathlib import Path
from datetime import datetime
from typing import List

from app.models.historico_model import JogoHistorico

ARQUIVO_HISTORICO = Path("data/historico_jogos.json")
ARQUIVO_HISTORICO.parent.mkdir(exist_ok=True)


def _carregar_historico() -> List[dict]:
    if not ARQUIVO_HISTORICO.exists():
        return []
    with open(ARQUIVO_HISTORICO, "r", encoding="utf-8") as f:
        return json.load(f)


def _salvar_historico(registros: List[dict]):
    with open(ARQUIVO_HISTORICO, "w", encoding="utf-8") as f:
        json.dump(registros, f, indent=2, ensure_ascii=False, default=str)


def registrar_jogo(
    tipo: str,
    numeros: list,
    score_medio=None,
    score_final=None,
    penalidade_sequencia=None,
    valor_aposta=3.0
):
    historico = _carregar_historico()

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

    historico.append(jogo.dict())
    _salvar_historico(historico)

    return jogo
