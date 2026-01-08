import sys
import random
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.append(str(BASE_DIR))

from app.services.supabase_service import get_supabase
from app.services.estatisticas_service import (
    calcular_medias_recentes,
    obter_estatisticas_com_score,
    obter_numeros_mais_atrasados
)

# --------------------------------------------------
def calcular_metricas_base(dezenas):
    pares = sum(1 for n in dezenas if n % 2 == 0)
    return {
        "soma": sum(dezenas),
        "pares": pares,
        "impares": 15 - pares
    }

# --------------------------------------------------
def salvar_estatisticas_numeros(data_ref, df_scores):
    supabase = get_supabase()

    payload = [
        {
            "data_referencia": data_ref,
            "numero": int(row["numero"]),
            "frequencia": int(row["frequencia"]),
            "atraso": int(row["atraso"]),
            "score": float(row["score"])
        }
        for _, row in df_scores.iterrows()
    ]

    supabase.table("estatisticas_numeros").upsert(
        payload,
        on_conflict="data_referencia,numero"
    ).execute()

# --------------------------------------------------
def main():
    supabase = get_supabase()
    print("🚀 Processamento diário Lotofácil")

    try:
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
        concurso = ultimo.data[0]["concurso"]

        print(f"📌 Concurso {concurso} | {data_ref}")

        medias = calcular_medias_recentes()
        df_scores = obter_estatisticas_com_score()
        atrasados_top = obter_numeros_mais_atrasados()

        if df_scores.empty:
            raise RuntimeError("Estatísticas vazias")

        quentes = df_scores.sort_values("score", ascending=False).head(5)["numero"].tolist()
        frios = df_scores.sort_values("score").head(5)["numero"].tolist()
        atrasados_ranking = df_scores.sort_values("atraso", ascending=False).head(5)["numero"].tolist()

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

        salvar_estatisticas_numeros(data_ref, df_scores)

        print("✅ Processamento concluído com sucesso")

    except Exception as e:
        print(f"❌ Erro crítico: {e}")
        raise

# --------------------------------------------------
if __name__ == "__main__":
    main()

