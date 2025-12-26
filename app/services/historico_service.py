import json
import os
from typing import List
from app.models.historico_model import JogoHistorico

ARQUIVO_HISTORICO = "data/historico_jogos.json"


def _garantir_arquivo():
    os.makedirs("data", exist_ok=True)
    if not os.path.exists(ARQUIVO_HISTORICO):
        with open(ARQUIVO_HISTORICO, "w") as f:
            json.dump([], f)


def salvar_jogo(jogo: JogoHistorico):
    _garantir_arquivo()

    with open(ARQUIVO_HISTORICO, "r") as f:
        dados = json.load(f)

    dados.append(jogo.dict())

    with open(ARQUIVO_HISTORICO, "w") as f:
        json.dump(dados, f, indent=2, default=str)


def listar_historico() -> List[JogoHistorico]:
    _garantir_arquivo()

    with open(ARQUIVO_HISTORICO, "r") as f:
        dados = json.load(f)

    return [JogoHistorico(**j) for j in dados]


def resumo_financeiro():
    historico = listar_historico()

    total_investido = sum(j.valor_aposta for j in historico)
    total_retorno = sum(j.valor_premio for j in historico)

    roi = (
        ((total_retorno - total_investido) / total_investido) * 100
        if total_investido > 0 else 0
    )

    return {
        "total_jogos": len(historico),
        "total_investido": round(total_investido, 2),
        "total_retorno": round(total_retorno, 2),
        "roi_percentual": round(roi, 2)
    }
