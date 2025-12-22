import json
import os
import random
from datetime import date
from app.services.estatisticas_service import obter_estatisticas_base

CACHE_DIR = "app/cache"
CACHE_FILE = os.path.join(CACHE_DIR, "palpite_fixo.json")


# =====================================================
# GARANTE PASTA DE CACHE
# =====================================================
os.makedirs(CACHE_DIR, exist_ok=True)


# =====================================================
# PALPITE FIXO DIÁRIO
# =====================================================
def gerar_palpite_fixo():
    hoje = date.today().isoformat()

    # 🔹 tenta ler cache
    if os.path.exists(CACHE_FILE):
        with open(CACHE_FILE, "r", encoding="utf-8") as f:
            cache = json.load(f)

        if cache.get("data") == hoje:
            return cache["numeros"]

    # 🔹 gera novo palpite
    numeros = _gerar_palpite_base()

    # 🔹 salva cache
    with open(CACHE_FILE, "w", encoding="utf-8") as f:
        json.dump(
            {"data": hoje, "numeros": numeros},
            f,
            ensure_ascii=False,
            indent=2
        )

    return numeros


# =====================================================
# BASE ESTATÍSTICA DO PALPITE FIXO
# =====================================================
def _gerar_palpite_base():
    df = obter_estatisticas_base()

    quentes = df.sort_values("frequencia", ascending=False).head(8)["numero"].tolist()
    equilibrados = df.sort_values("frequencia", ascending=False).iloc[8:16]["numero"].tolist()
    frios = df.sort_values("frequencia").head(10)["numero"].tolist()

    jogo = (
        random.sample(quentes, 6)
        + random.sample(equilibrados, 6)
        + random.sample(frios, 3)
    )

    return sorted(set(jogo))
