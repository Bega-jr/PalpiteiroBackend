import json
import os
import random
from datetime import date

CACHE_DIR = "app/cache"
CACHE_FILE = os.path.join(CACHE_DIR, "palpite_fixo.json")

os.makedirs(CACHE_DIR, exist_ok=True)


# =====================================================
# PALPITE FIXO DIÁRIO (COM FALLBACK)
# =====================================================
def gerar_palpite_fixo():
    hoje = date.today().isoformat()

    # 🔹 tenta cache
    if os.path.exists(CACHE_FILE):
        try:
            with open(CACHE_FILE, "r", encoding="utf-8") as f:
                cache = json.load(f)

            if cache.get("data") == hoje:
                return cache["numeros"]
        except Exception:
            pass  # nunca derruba a rota

    # 🔹 gera novo palpite
    numeros = _gerar_palpite_base_seguro()

    # 🔹 salva cache
    try:
        with open(CACHE_FILE, "w", encoding="utf-8") as f:
            json.dump(
                {"data": hoje, "numeros": numeros},
                f,
                ensure_ascii=False,
                indent=2
            )
    except Exception:
        pass

    return numeros


# =====================================================
# PALPITE BASE (NUNCA QUEBRA)
# =====================================================
def _gerar_palpite_base_seguro():
    try:
        from app.services.estatisticas_service import obter_estatisticas_base

        df = obter_estatisticas_base()

        # garante colunas
        if not {"numero", "frequencia"}.issubset(df.columns):
            raise ValueError("Estrutura inválida")

        quentes = df.sort_values("frequencia", ascending=False).head(8)["numero"].tolist()
        equilibrados = df.sort_values("frequencia", ascending=False).iloc[8:16]["numero"].tolist()
        frios = df.sort_values("frequencia").head(10)["numero"].tolist()

        jogo = (
            random.sample(quentes, 6)
            + random.sample(equilibrados, 6)
            + random.sample(frios, 3)
        )

        return sorted(set(jogo))

    except Exception:
        # 🔥 FALLBACK TOTAL (NUNCA CAI)
        return sorted(random.sample(range(1, 26), 15))
