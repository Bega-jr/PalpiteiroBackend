import sys
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
# HISTÓRICO COMPLETO (FONTE ÚNICA)
# --------------------------------------------------
def carregar_historico():
    supabase = get_supabase()

    res = (
        supabase
        .table("lotofacil_concursos")
        .select("concurso,data,dezenas")
        .order("concurso")
        .execute()
    )

    if not res.data:
        return []

    return [
        {
            "concurso": r["concurso"],
            "data": r["data"],
            "numeros": [int(n) for n in r["dezenas"]],
        }
        for r in res.data
    ]


# --------------------------------------------------
# CICLO REAL (CORRETO)
# --------------------------------------------------
def calcular_ciclo_atual(historico):
    vistos = set()

    for r in reversed(historico):
        vistos.update(r["numeros"])
        if len(vistos) == 25:
            break

    faltam = sorted(set(range(1, 26)) - vistos)
    return faltam


# --------------------------------------------------
def salvar_estatisticas_numeros(data_ref, df_scores):
    supabase = get_supabase()

    payload = [
        {
            "data_referencia": data_ref,
            "numero": int(row["numero"]),
            "frequencia": int(row["frequencia"]),
            "atraso": int(row["atraso"]),
            "score": float(row["score"]),
        }
        for _, row in df_scores.iterrows()
    ]

    # limpa antes para evitar lixo histórico
    supabase.table("estatisticas_numeros") \
        .delete() \
        .eq("data_referencia", data_ref) \
        .execute()

    supabase.table("estatisticas_numeros") \
        .insert(payload) \
        .execute()


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

        concurso = ultimo.data[0]["concurso"]
        data_ref = ultimo.data[0]["data"]

        print(f"📌 Concurso {concurso} | {data_ref}")

        # --------------------------------------------------
        # BASE DE DADOS
        historico = carregar_historico()
        medias = calcular_medias_recentes()
        df_scores = obter_estatisticas_com_score()
        atrasados_ranking = obter_numeros_mais_atrasados()

        if df_scores.empty:
            raise RuntimeError("Estatísticas vazias")

        # --------------------------------------------------
        # RANKINGS
        numeros_quentes = (
            df_scores.sort_values("score", ascending=False)
            .head(5)["numero"]
            .astype(int)
            .tolist()
        )

        numeros_frios = (
            df_scores.sort_values("score")
            .head(5)["numero"]
            .astype(int)
            .tolist()
        )

        # 🔥 CICLO REAL
        numeros_atrasados = calcular_ciclo_atual(historico)

        # --------------------------------------------------
        # estatisticas_diarias_v2 (FONTE DO FRONT)
        payload_diario = {
            "data_referencia": data_ref,
            "numeros_quentes": numeros_quentes,
            "numeros_frios": numeros_frios,
            "numeros_atrasados": numeros_atrasados,
            "atrasados_ranking": atrasados_ranking,
            "media_soma": round(medias["soma_media"], 2),
            "media_pares": round(medias["pares_media"], 2),
            "media_impares": round(medias["impares_media"], 2),
            "media_primos": round(medias.get("primos_media", 0), 2),
            "sequencias_comuns": [3, 4],
        }

        # limpa e recria (garante consistência)
        supabase.table("estatisticas_diarias_v2") \
            .delete() \
            .eq("data_referencia", data_ref) \
            .execute()

        supabase.table("estatisticas_diarias_v2") \
            .insert(payload_diario) \
            .execute()

        # --------------------------------------------------
        # estatisticas_numeros
        salvar_estatisticas_numeros(data_ref, df_scores)

        print("✅ Processamento concluído com sucesso")

    except Exception as e:
        print(f"❌ Erro crítico: {e}")
        raise


# --------------------------------------------------
if __name__ == "__main__":
    main()
