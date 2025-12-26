import json
import os
from datetime import date

CAMINHO = "data/historico_jogos.json"


def salvar_jogo(jogo):
    os.makedirs("data", exist_ok=True)

    historico = []
    if os.path.exists(CAMINHO):
        with open(CAMINHO, "r", encoding="utf-8") as f:
            historico = json.load(f)

    historico.append(jogo)

    with open(CAMINHO, "w", encoding="utf-8") as f:
        json.dump(historico, f, indent=2, ensure_ascii=False)
