import sys
from pathlib import Path
import numpy as np
import pandas as pd

# -----------------------------------
# Configuração base
# -----------------------------------
BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.append(str(BASE_DIR))

from app.services.supabase_service import get_supabase
from app.services.estatisticas_service import (
    calcular_medias_recentes,
    obter_estatisticas_com_score,
    obter_top_listas,
    carregar_historico
)

# -----------------------------------
# Utilidades
# -----------------------------------
def normalizar(col):
    min_val = col.min()
    max_val = col.max()

    if max_val - min_val == 0:
        return pd.Series([0.5] * len(col))

    return (col - min_val) / (max_val - min_val)


def calcular_tendencia_vetorizado(historico, janela=25):
    """
    Calcula tendência de forma vetorizada (mais rápido).
    """
    ultimos = historico[-janela:]
    contador = {n: 0 for n in range(1, 26)}

    for conc in ultimos:
        for n in conc["numeros"]:
            contador[n] += 1

    return {n: contador[n] / janela for n in range(1, 26)}


def calcular_ciclo_historico_completo(historico):
    todos = set(range(1, 26))
    sorteados = set()
    ciclo = 1

    for conc in historico:
        sorteados.update(conc["numeros"])
        if sorteados == todos:
            sorteados = set()
            ciclo += 1

    faltam = sorted(todos - sorteados)
    if not faltam:
        faltam = list(range(1, 26))

    return faltam, ciclo


# -----------------------------------
# Execução principal
# -----------------------------------
def main():
    supabase = get_supabase()
    print("🚀 Processamento Estatístico Probabilístico iniciado")

    try:
        # 1️⃣ Histórico
        historico = carregar_historico()

        if not historico:
            raise Exception("Histórico vazio.")

        ultimo = historico[-1]
        concurso_atual = ultimo["concurso"]
        data_atual = ultimo["data"]
        dezenas_hoje = set(ultimo["numeros"])

        print(f"📌 Concurso {concurso_atual} | Data {data_atual}")

        # 2️⃣ Estatísticas base
        df = obter_estatisticas_com_score()
        medias = calcular_medias_recentes()

        # 3️⃣ Ajusta atraso (zera sorteados hoje)
        df.loc[df["numero"].isin(dezenas_hoje), "atraso"] = 0

        # 4️⃣ Tendência vetorizada
        tendencias = calcular_tendencia_vetorizado(historico, janela=25)
        df["tendencia"] = df["numero"].map(tendencias)

        # 5️⃣ Normalizações
        df["freq_norm"] = normalizar(df["frequencia"])
        df["atraso_norm"] = 1 - normalizar(df["atraso"])
        df["tendencia_norm"] = normalizar(df["tendencia"])
        df["score_antigo_norm"] = normalizar(df["score"])

        # 6️⃣ Novo score ponderado real
        df["score"] = (
            df["freq_norm"] * 0.35 +
            df["tendencia_norm"] * 0.30 +
            df["atraso_norm"] * 0.20 +
            df["score_antigo_norm"] * 0.15
        ).round(6)

        # 7️⃣ Rankings
        listas = obter_top_listas(df)
        numeros_faltantes, ciclo_contagem = calcular_ciclo_historico_completo(historico)

        # 8️⃣ Payload diário
        payload_diario = {
            "data_referencia": data_atual,
            "concurso": int(concurso_atual),
            "numero_ciclo": int(ciclo_contagem),
            "numeros_quentes": listas["numeros_quentes"],
            "numeros_frios": listas["numeros_frios"],
            "numeros_atrasados": numeros_faltantes,
            "atrasados_ranking": listas["atrasados_ranking"],
            "media_soma": float(medias.get("soma_media", 0)),
            "media_pares": float(medias.get("pares_media", 0)),
            "media_impares": float(medias.get("impares_media", 0)),
            "media_primos": float(medias.get("primos_media", 0)),
            "sequencias_comuns": [3, 4]
        }

        # 9️⃣ Salva estatística diária
        supabase.table("estatisticas_diarias_v2") \
            .delete().eq("data_referencia", data_atual).execute()

        supabase.table("estatisticas_diarias_v2") \
            .insert(payload_diario).execute()

        # 🔟 Salva estatísticas por número
        payload_numeros = [
            {
                "data_referencia": data_atual,
                "numero": int(row.numero),
                "frequencia": int(row.frequencia),
                "atraso": int(row.atraso),
                "score": float(row.score),
                "tendencia": float(row.tendencia)
            }
            for row in df.itertuples()
        ]

        supabase.table("estatisticas_numeros") \
            .delete().eq("data_referencia", data_atual).execute()

        supabase.table("estatisticas_numeros") \
            .insert(payload_numeros).execute()

        print("✅ Estatísticas atualizadas com score probabilístico real")
        print(f"🎯 Ciclo {ciclo_contagem} | Base pronta para geração")

    except Exception as e:
        print(f"❌ Erro crítico: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
