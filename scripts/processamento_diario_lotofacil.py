import sys
import random
from pathlib import Path

# ------------------------------------------------------------------
# PATH
# ------------------------------------------------------------------
BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.append(str(BASE_DIR))

# ------------------------------------------------------------------
# IMPORTS
# ------------------------------------------------------------------
from app.services.supabase_service import get_supabase
from app.services.estatisticas_service import (
    calcular_medias_recentes,
    obter_estatisticas_com_score,
    obter_numeros_mais_atrasados
)

# ------------------------------------------------------------------
# MÉTRICAS SIMPLES
# ------------------------------------------------------------------
def calcular_metricas_base(dezenas):
    pares = sum(1 for n in dezenas if n % 2 == 0)
    return {
        "soma": sum(dezenas),
        "pares": pares,
        "impares": 15 - pares
    }

# ------------------------------------------------------------------
# SALVAR ESTATISTICAS_NUMEROS (UPSERT)
# ------------------------------------------------------------------
def salvar_estatisticas_numeros(supabase, data_ref, df_scores):
    payload = []

    for _, row in df_scores.iterrows():
        payload.append({
            "data_referencia": data_ref,
            "numero": int(row["numero"]),
            "frequencia": int(row["frequencia"]),
            "atraso": int(row["atraso"]),
            "score": float(row["score"])
        })

    supabase.table("estatisticas_numeros").upsert(
        payload,
        on_conflict="data_referencia,numero"
    ).execute()

# ------------------------------------------------------------------
# MAIN
# ------------------------------------------------------------------
def main():
    supabase = get_supabase()

    print("🚀 Processamento diário Lotofácil")

    try:
        # ------------------------------------------------------------
        # ÚLTIMO CONCURSO
        # ------------------------------------------------------------
        ultimo = (
            supabase
            .table("lotofacil_concursos")
            .select("concurso,data")
            .order("concurso", desc=True)
            .limit(1)
            .execute()
        )

        if not ultimo.data:
            raise RuntimeError("Nenhum concurso encontrado")

        data_ref = ultimo.data[0]["data"]
        concurso_ref = ultimo.data[0]["concurso"]

        print(f"📌 Concurso {concurso_ref} | Data {data_ref}")

        # ------------------------------------------------------------
        # CÁLCULOS
        # ------------------------------------------------------------
        medias = calcular_medias_recentes()
        df_scores = obter_estatisticas_com_score()
        atrasados_top = obter_numeros_mais_atrasados()

        if df_scores is None or df_scores.empty:
            raise RuntimeError("Falha ao calcular estatísticas")

        # ------------------------------------------------------------
        # RANKINGS
        # ------------------------------------------------------------
        quentes = (
            df_scores.sort_values("score", ascending=False)
            .head(5)["numero"].astype(int).tolist()
        )

        frios = (
            df_scores.sort_values("score")
            .head(5)["numero"].astype(int).tolist()
        )

        atrasados_ranking = (
            df_scores.sort_values("atraso", ascending=False)
            .head(5)["numero"].astype(int).tolist()
        )

        # ------------------------------------------------------------
        # ESTATISTICAS_DIARIAS_V2
        # ------------------------------------------------------------
        payload_diario = {
            "data_referencia": data_ref,
            "numeros_quentes": quentes,
            "numeros_frios": frios,
            "numeros_atrasados": atrasados_top,
            "media_soma": round(medias["soma_media"], 2),
            "media_pares": round(medias["pares_media"], 2),
            "media_impares": round(medias["impares_media"], 2),
            "media_primos": round(medias.get("primos_media", 0), 2),
            "sequencias_comuns": [3, 4],
            "atrasados_ranking": atrasados_ranking
        }

        supabase.table("estatisticas_diarias_v2").upsert(
            payload_diario,
            on_conflict="data_referencia"
        ).execute()

        # ------------------------------------------------------------
        # ESTATISTICAS_NUMEROS
        # ------------------------------------------------------------
        salvar_estatisticas_numeros(supabase, data_ref, df_scores)

        print("✅ Estatísticas atualizadas com sucesso")

    except Exception as e:
        print(f"❌ Erro crítico: {e}")
        raise

# ------------------------------------------------------------------
# ENTRYPOINT
# ------------------------------------------------------------------
if __name__ == "__main__":
    main()
