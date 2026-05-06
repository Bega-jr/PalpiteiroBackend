import sys
from pathlib import Path
import numpy as np
from datetime import datetime

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.append(str(BASE_DIR))

from app.services.supabase_service import get_supabase
from app.services.estatisticas_service import (
    calcular_medias_recentes,
    obter_estatisticas_com_score,
    obter_top_listas,
    carregar_historico
)

# ======================================================
# NORMALIZAÇÃO
# ======================================================
def normalizar(col):
    return (col - col.min()) / (col.max() - col.min() + 1e-9)

# ======================================================
# TENDÊNCIA
# ======================================================
def calcular_tendencia(historico, numero, janela=25):
    ultimos = historico[-janela:]
    presencas = [1 if numero in h["numeros"] else 0 for h in ultimos]
    return float(np.mean(presencas))

# ======================================================
# CICLO
# ======================================================
def calcular_ciclo_historico_completo(historico):
    todos_25 = set(range(1, 26))
    sorteados = set()
    ciclo = 1

    for conc in historico:
        sorteados.update(conc["numeros"])
        if sorteados == todos_25:
            sorteados = set()
            ciclo += 1

    faltam = sorted(todos_25 - sorteados)
    return faltam if faltam else list(range(1, 26)), ciclo

# ======================================================
# EXTRAI ESTRUTURA DO CONCURSO
# ======================================================
def extrair_estrutura(nums):
    return {
        "soma_faixa": int(round(sum(nums) / 10) * 10),
        "pares": sum(1 for n in nums if n % 2 == 0),
        "primos": sum(1 for n in nums if n in {2,3,5,7,11,13,17,19,23}),
        "linhas": [
            sum(1 for n in nums if 1 <= n <= 5),
            sum(1 for n in nums if 6 <= n <= 10),
            sum(1 for n in nums if 11 <= n <= 15),
            sum(1 for n in nums if 16 <= n <= 20),
            sum(1 for n in nums if 21 <= n <= 25),
        ]
    }

# ======================================================
# BUSCAR CENÁRIO SIMILAR (MEMÓRIA)
# ======================================================
def buscar_cenario_similar(supabase, estrutura):
    res = (
        supabase
        .table("memoria_cenarios")
        .select("*")
        .eq("soma_faixa", estrutura["soma_faixa"])
        .eq("pares", estrutura["pares"])
        .eq("primos", estrutura["primos"])
        .execute()
    )

    if not res.data:
        return None

    melhor = None
    menor_diff = 999

    for r in res.data:
        diff = sum(abs(a - b) for a, b in zip(r["linhas"], estrutura["linhas"]))
        if diff < menor_diff:
            menor_diff = diff
            melhor = r

    return melhor

# ======================================================
# AJUSTE DE PESO POR MEMÓRIA REAL
# ======================================================
def ajustar_por_memoria(df, memoria):
    if not memoria:
        print("🧠 Sem memória")
        return df

    score_real = float(memoria.get("score_medio_real", 0))
    print(f"🧠 score_real={score_real}")

    if score_real >= 5:
        df["score"] *= 1.10
    elif score_real <= 1:
        df["score"] *= 0.90

    return df

# ======================================================
# MAIN
# ======================================================
def main():
    supabase = get_supabase()
    print("🚀 Processamento Inteligente com Memória iniciado")

    try:
        historico = carregar_historico()
        ultimo = historico[-1]

        concurso = ultimo["concurso"]
        data = ultimo["data"]
        dezenas = ultimo["numeros"]

        print(f"📌 Concurso {concurso} | Data {data}")

        df = obter_estatisticas_com_score()
        
        df.loc[df["numero"].isin(dezenas), "atraso"] = 0

        df["tendencia"] = df["numero"].apply(
            lambda n: calcular_tendencia(historico, n)
        )

        df["freq_norm"] = normalizar(df["frequencia"])
        df["atraso_norm"] = 1 - normalizar(df["atraso"])
        df["tendencia_norm"] = normalizar(df["tendencia"])
        df["score_norm"] = normalizar(df["score"])

        # BASE NEUTRA
        df["score"] = (
            df["freq_norm"] * 0.35 +
            df["tendencia_norm"] * 0.30 +
            df["atraso_norm"] * 0.20 +
            df["score_norm"] * 0.15
        )

        # ==================================================
        # MEMÓRIA DE CENÁRIO
        # ==================================================
        estrutura_atual = extrair_estrutura(dezenas)
        memoria = buscar_cenario_similar(supabase, estrutura_atual)

        df = ajustar_por_memoria(df, memoria)

        # SALVAR MEMÓRIA (UPSERT)
        payload_memoria = {
            "soma_faixa": estrutura_atual["soma_faixa"],
            "pares": estrutura_atual["pares"],
            "primos": estrutura_atual["primos"],
            "linhas": estrutura_atual["linhas"],
            "ultima_aparicao": data,
            "updated_at": datetime.now().isoformat()
        }

        supabase.table("memoria_cenarios") \
            .upsert(payload_memoria, on_conflict="soma_faixa,pares,primos,linhas") \
            .execute()

        print("✅ Memória estrutural atualizada")

        # ==================================================
        # NOVO: SALVAR MEMÓRIA DE REGIMES (DETERMINA O "CLIMA")
        # ==================================================
        faltantes, ciclo = calcular_ciclo_historico_completo(historico)
        
        # Cálculo do Regime: Quente vs Frio
        # Se as dezenas sorteadas tinham score alto, regime de Expansão
        media_score_sorteados = df[df["numero"].isin(dezenas)]["score"].mean()
        
        regime_tipo = "NEUTRO"
        if media_score_sorteados > 0.55: regime_tipo = "EXPANSAO_QUENTES"
        elif media_score_sorteados < 0.45: regime_tipo = "CONTRACAO_FRIAS"

        payload_regime = {
            "data_referencia": data,
            "concurso": int(concurso),
            "numero_ciclo": int(ciclo),
            "tipo_regime": regime_tipo,
            "score_global": float(media_score_sorteados),
            "media_soma": float(sum(dezenas)),
            "media_pares": int(estrutura_atual["pares"])
        }

        # Upsert para não duplicar se rodar o mesmo concurso 2x
        supabase.table("memoria_regimes") \
            .upsert(payload_regime, on_conflict="concurso") \
            .execute()

        print(f"📡 Memória de Regimes atualizada: {regime_tipo} (Score: {media_score_sorteados:.4f})")

        # ==================================================
        # FINALIZAÇÃO
        # ==================================================
        print("✅ Estatísticas prontas")
        print(f"🎯 Ciclo {ciclo}")

    except Exception as e:
        print(f"❌ Erro crítico: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()

