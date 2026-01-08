import sys
import random
from pathlib import Path

# ---------------------------------------------------------------------
# CONFIG PATH
# ---------------------------------------------------------------------
BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.append(str(BASE_DIR))

# ---------------------------------------------------------------------
# IMPORTS
# ---------------------------------------------------------------------
from app.services.supabase_service import get_supabase
from app.services.estatisticas_service import (
    calcular_medias_recentes,
    obter_estatisticas_com_score
)

# ---------------------------------------------------------------------
# MÉTRICAS SIMPLES
# ---------------------------------------------------------------------
def calcular_metricas_base(dezenas):
    pares = sum(1 for n in dezenas if n % 2 == 0)
    return {
        "soma": sum(dezenas),
        "pares": pares,
        "impares": 15 - pares
    }

# ---------------------------------------------------------------------
# MAIN
# ---------------------------------------------------------------------
def main():
    supabase = get_supabase()
    print("🚀 Processamento diário Lotofácil (Supabase only)")

    try:
        # -----------------------------------------------------------------
        # 1️⃣ ÚLTIMO CONCURSO REAL
        # -----------------------------------------------------------------
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

        concurso_ref = ultimo.data[0]["concurso"]
        data_ref = ultimo.data[0]["data"]

        print(f"📌 Concurso referência: {concurso_ref} ({data_ref})")

        # -----------------------------------------------------------------
        # 2️⃣ ESTATÍSTICAS REAIS (HISTÓRICO TOTAL)
        # -----------------------------------------------------------------
        analise_medias = calcular_medias_recentes()
        df_scores = obter_estatisticas_com_score()

        if df_scores is None or df_scores.empty:
            raise RuntimeError("Falha ao calcular estatísticas")

        # Rankings principais
        quentes = (
            df_scores.sort_values("score", ascending=False)
            .head(5)["numero"].astype(int).tolist()
        )

        frios = (
            df_scores.sort_values("score")
            .head(5)["numero"].astype(int).tolist()
        )

        atrasados_top = (
            df_scores.sort_values("atraso", ascending=False)
            .head(5)["numero"].astype(int).tolist()
        )

        # -----------------------------------------------------------------
        # 3️⃣ PAYLOAD estatisticas_diarias_v2
        # -----------------------------------------------------------------
        payload_diario = {
            "data_referencia": data_ref,
            "numeros_quentes": quentes,
            "numeros_frios": frios,
            "numeros_atrasados": atrasados_top,
            "media_soma": round(analise_medias.get("soma_media", 0), 2),
            "media_pares": round(analise_medias.get("pares_media", 0), 2),
            "media_impares": round(analise_medias.get("impares_media", 0), 2),
            "media_primos": round(analise_medias.get("primos_media", 0), 2),
            "sequencias_comuns": [3, 4],  # placeholder consciente
            "atrasados_ranking": atrasados_top
        }

        # -----------------------------------------------------------------
        # 4️⃣ PAYLOAD estatisticas_numeros
        # -----------------------------------------------------------------
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

        # -----------------------------------------------------------------
        # 5️⃣ GERAÇÃO DE PALPITES
        # -----------------------------------------------------------------
        registros_palpites = []
        meta_pares = int(round(analise_medias.get("pares_media", 7)))

        base_elite = (
            df_scores.sort_values("score", ascending=False)
            .head(18)["numero"].astype(int).tolist()
        )

        # --- Palpite Fixo (índice 0) ---
        fixo = sorted(set(atrasados_top + base_elite))
        if len(fixo) < 15:
            fixo += random.sample(
                [n for n in range(1, 26) if n not in fixo],
                15 - len(fixo)
            )
        fixo = sorted(fixo[:15])

        m_fixo = calcular_metricas_base(fixo)

        registros_palpites.append({
            "data_referencia": data_ref,
            "indice_palpite": 0,
            "numeros": fixo,
            "soma_total": m_fixo["soma"],
            "pares": m_fixo["pares"],
            "impares": m_fixo["impares"],
            "tipo": "fixo",
            "origem": "sistema",
            "qtd_sequencias": 3,
            "metricas": {
                "score": 0.98,
                "metodo": "ranking_atraso_score"
            },
            "filtros_aplicados": ["atraso_real", "top_scores"]
        })

        # --- Palpites Estatísticos (1 a 10) ---
        for i in range(1, 11):
            for _ in range(100):
                amostra_atraso = random.sample(
                    atrasados_top,
                    min(3, len(atrasados_top))
                )

                restante = random.sample(
                    [n for n in base_elite if n not in amostra_atraso],
                    15 - len(amostra_atraso)
                )

                combinacao = sorted(amostra_atraso + restante)
                m = calcular_metricas_base(combinacao)

                if 145 <= m["soma"] <= 240 and abs(m["pares"] - meta_pares) <= 1:
                    registros_palpites.append({
                        "data_referencia": data_ref,
                        "indice_palpite": i,
                        "numeros": combinacao,
                        "soma_total": m["soma"],
                        "pares": m["pares"],
                        "impares": m["impares"],
                        "tipo": "estatistico",
                        "origem": "sistema",
                        "qtd_sequencias": 3,
                        "metricas": {
                            "score": 0.88,
                            "metodo": "equilibrio_dinamico"
                        },
                        "filtros_aplicados": ["soma", "pares", "atraso"]
                    })
                    break

        # -----------------------------------------------------------------
        # 6️⃣ PERSISTÊNCIA NO SUPABASE
        # -----------------------------------------------------------------
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

        supabase.table("palpites_validos").delete().eq(
            "data_referencia", data_ref
        ).execute()
        supabase.table("palpites_validos").insert(
            registros_palpites
        ).execute()

        print("✅ Processamento concluído com sucesso")

    except Exception as e:
        print(f"❌ Erro crítico: {e}")

# ---------------------------------------------------------------------
if __name__ == "__main__":
    main()
