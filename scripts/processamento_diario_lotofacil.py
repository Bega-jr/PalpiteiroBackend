import sys
import random
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.append(str(BASE_DIR))

from app.services.supabase_service import get_supabase
from app.services.estatisticas_service import (
    carregar_dados_para_estatistica,
    calcular_medias_recentes,
    obter_estatisticas_com_score,
)

# ---------------------------------------------------------
# MÉTRICAS SIMPLES
# ---------------------------------------------------------
def calcular_metricas_base(dezenas):
    pares = sum(1 for n in dezenas if n % 2 == 0)
    return {
        "soma": sum(dezenas),
        "pares": pares,
        "impares": 15 - pares
    }

# ---------------------------------------------------------
# CICLO REAL (HISTÓRICO TOTAL)
# ---------------------------------------------------------
def obter_numeros_faltantes_ciclo():
    historico = carregar_dados_para_estatistica()
    vistos = set()

    for concurso in reversed(historico):
        vistos.update(concurso["numeros"])
        if len(vistos) == 25:
            break

    return sorted(set(range(1, 26)) - vistos)

# ---------------------------------------------------------
# MAIN
# ---------------------------------------------------------
def main():
    supabase = get_supabase()
    print("🚀 Processamento diário de estatísticas (Supabase only)")

    try:
        # 🔹 Último concurso real
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

        print(f"📌 Concurso referência: {concurso_ref} ({data_ref})")

        # 🔹 Estatísticas
        analise_medias = calcular_medias_recentes()
        df_scores = obter_estatisticas_com_score()
        faltantes_ciclo = obter_numeros_faltantes_ciclo()

        if df_scores.empty:
            raise RuntimeError("Falha ao calcular estatísticas")

        # 🔹 Rankings
        quentes = df_scores.sort_values("score", ascending=False).head(5)["numero"].tolist()
        frios = df_scores.sort_values("score").head(5)["numero"].tolist()
        atrasados_ranking = df_scores.sort_values("atraso", ascending=False).head(5)["numero"].tolist()

        # -------------------------------------------------
        # estatisticas_diarias_v2
        # -------------------------------------------------
        payload_diario = {
            "data_referencia": data_ref,
            "numeros_quentes": quentes,
            "numeros_frios": frios,
            "numeros_atrasados": faltantes_ciclo,
            "media_soma": round(analise_medias["soma_media"], 2),
            "media_pares": round(analise_medias["pares_media"], 2),
            "media_impares": round(analise_medias["impares_media"], 2),
            "media_primos": round(analise_medias.get("primos_media", 0), 2),
            "sequencias_comuns": [3, 4],
            "atrasados_ranking": atrasados_ranking
        }

        # -------------------------------------------------
        # estatisticas_numeros
        # -------------------------------------------------
        registros_numeros = [
            {
                "data_referencia": data_ref,
                "numero": int(row["numero"]),
                "frequencia": int(row["frequencia"]),
                "atraso": int(row["atraso"]),
                "score": float(row["score"])
            }
            for _, row in df_scores.iterrows()
        ]

        # -------------------------------------------------
        # Persistência
        # -------------------------------------------------
        supabase.table("estatisticas_diarias_v2").delete().eq(
            "data_referencia", data_ref
        ).execute()

        supabase.table("estatisticas_diarias_v2").insert(
            payload_diario
        ).execute()

        supabase.table("estatisticas_numeros").delete().eq(
            "data_referencia", data_ref
        ).execute()

        supabase.table("estatisticas_numeros").insert(
            registros_numeros
        ).execute()

        print("✅ Estatísticas atualizadas com sucesso")

    except Exception as e:
        print(f"❌ Erro crítico: {e}")

if __name__ == "__main__":
    main()

