import sys
from pathlib import Path
import numpy as np

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.append(str(BASE_DIR))

from app.services.supabase_service import get_supabase
from app.services.estatisticas_service import (
    calcular_medias_recentes,
    obter_estatisticas_com_score,
    obter_top_listas,
    carregar_historico
)

# ---------------------------------------------------
# FUNÇÕES AUXILIARES
# ---------------------------------------------------

def normalizar(col):
    return (col - col.min()) / (col.max() - col.min() + 1e-9)


def calcular_tendencia(historico, numero, janela=25):
    ultimos = historico[-janela:]
    presencas = [1 if numero in h["numeros"] else 0 for h in ultimos]
    return float(np.mean(presencas))


def calcular_ciclo_historico_completo(historico):
    todos_25 = set(range(1, 26))
    sorteados_no_ciclo = set()
    numero_do_ciclo = 1

    for conc in historico:
        sorteados_no_ciclo.update(conc["numeros"])
        if sorteados_no_ciclo == todos_25:
            sorteados_no_ciclo = set()
            numero_do_ciclo += 1

    faltam = sorted(todos_25 - sorteados_no_ciclo)
    if not faltam:
        faltam = list(range(1, 26))

    return faltam, numero_do_ciclo


# ---------------------------------------------------
# CLASSIFICAÇÃO DE CENÁRIO
# ---------------------------------------------------

def classificar_cenario(df, medias):
    top_quentes = df.sort_values("score", ascending=False).head(5)
    top_atrasados = df.sort_values("atraso", ascending=False).head(5)

    media_score_top = top_quentes["score"].mean()
    media_atraso_top = top_atrasados["atraso"].mean()

    media_pares = medias.get("pares_media", 0)

    if media_score_top > 0.75:
        return "EXPANSAO_QUENTES"

    if media_atraso_top > 8:
        return "RECUPERACAO_ATRASADOS"

    if media_pares >= 9:
        return "DOMINANCIA_PARES"

    if abs(medias.get("soma_media", 0) - 195) < 5:
        return "EQUILIBRIO_TOTAL"

    return "ALTA_VARIANCIA"


# ---------------------------------------------------
# OBTÉM CENÁRIO DOMINANTE
# ---------------------------------------------------

def obter_cenario_dominante(supabase, limite=10):
    res = (
        supabase
        .table("memoria_cenarios")
        .select("tipo_cenario")
        .order("created_at", desc=True)
        .limit(limite)
        .execute()
    )

    if not res.data:
        return None  # fallback automático

    tipos = [r["tipo_cenario"] for r in res.data]

    return max(set(tipos), key=tipos.count)


# ---------------------------------------------------
# AJUSTE DE PESOS POR CENÁRIO
# ---------------------------------------------------

def ajustar_pesos_por_cenario(df, cenario):
    if not cenario:
        return df  # primeira execução

    if cenario == "EXPANSAO_QUENTES":
        df["score"] = (
            df["freq_norm"] * 0.45 +
            df["tendencia_norm"] * 0.35 +
            df["atraso_norm"] * 0.10 +
            df["score_norm"] * 0.10
        )

    elif cenario == "RECUPERACAO_ATRASADOS":
        df["score"] = (
            df["atraso_norm"] * 0.40 +
            df["tendencia_norm"] * 0.25 +
            df["freq_norm"] * 0.20 +
            df["score_norm"] * 0.15
        )

    elif cenario == "DOMINANCIA_PARES":
        df["score"] = df["score"] * 1.05

    elif cenario == "EQUILIBRIO_TOTAL":
        df["score"] = (
            df["freq_norm"] * 0.30 +
            df["tendencia_norm"] * 0.30 +
            df["atraso_norm"] * 0.20 +
            df["score_norm"] * 0.20
        )

    return df


# ---------------------------------------------------
# MAIN
# ---------------------------------------------------

def main():
    supabase = get_supabase()
    print("🚀 Processamento Estatístico Inteligente iniciado")

    try:
        historico = carregar_historico()
        ultimo = historico[-1]

        concurso_atual = ultimo["concurso"]
        data_atual = ultimo["data"]
        dezenas_hoje = set(ultimo["numeros"])

        print(f"📌 Concurso {concurso_atual} | Data {data_atual}")

        df = obter_estatisticas_com_score()
        medias = calcular_medias_recentes()

        df.loc[df["numero"].isin(dezenas_hoje), "atraso"] = 0

        df["tendencia"] = df["numero"].apply(
            lambda n: calcular_tendencia(historico, n)
        )

        df["freq_norm"] = normalizar(df["frequencia"])
        df["atraso_norm"] = 1 - normalizar(df["atraso"])
        df["tendencia_norm"] = normalizar(df["tendencia"])
        df["score_norm"] = normalizar(df["score"])

        # 🔥 Base inicial neutra
        df["score"] = (
            df["freq_norm"] * 0.35 +
            df["tendencia_norm"] * 0.30 +
            df["atraso_norm"] * 0.20 +
            df["score_norm"] * 0.15
        )

        # 🧠 Buscar cenário dominante
        cenario_dominante = obter_cenario_dominante(supabase)

        if cenario_dominante:
            print(f"🧠 Cenário dominante identificado: {cenario_dominante}")
        else:
            print("🧠 Primeira execução - sem histórico de cenário")

        # 🔄 Ajustar pesos conforme cenário dominante
        df = ajustar_pesos_por_cenario(df, cenario_dominante)

        listas = obter_top_listas(df)
        numeros_faltantes, ciclo_contagem = calcular_ciclo_historico_completo(historico)

        # 🔥 Classifica cenário atual
        tipo_cenario_atual = classificar_cenario(df, medias)

        payload_memoria = {
            "data_referencia": data_atual,
            "concurso": int(concurso_atual),
            "numero_ciclo": int(ciclo_contagem),
            "tipo_cenario": tipo_cenario_atual,
            "score_global": float(df["score"].mean()),
            "numeros_quentes": listas["numeros_quentes"],
            "numeros_frios": listas["numeros_frios"],
            "numeros_atrasados": numeros_faltantes,
            "media_soma": float(medias.get("soma_media", 0)),
            "media_pares": float(medias.get("pares_media", 0))
        }

        supabase.table("memoria_cenarios").insert(payload_memoria).execute()

        print(f"✅ Cenário atual salvo: {tipo_cenario_atual}")

    except Exception as e:
        print(f"❌ Erro crítico: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
