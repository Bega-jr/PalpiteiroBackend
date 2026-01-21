import os
import json
from datetime import datetime
from supabase import create_client, Client

# -----------------------------------
# Configuração Supabase
# -----------------------------------
SUPABASE_URL = os.getenv("SUPABASE_URL", "").strip()
SUPABASE_KEY = os.getenv("SUPABASE_KEY", "").strip()

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# -----------------------------------
# Conferência Oficial
# -----------------------------------
def conferir_historico():
    print(f"🚀 Iniciando Conferência Oficial - {datetime.now()}")

    # 1️⃣ Resultados oficiais
    res_oficiais = (
        supabase.table("lotofacil_concursos")
        .select("concurso, dezenas, data")
        .order("concurso", desc=True)
        .execute()
    )

    if not res_oficiais.data:
        print("❌ Nenhum concurso oficial encontrado.")
        return

    concursos_processados = 0

    for sorteio in res_oficiais.data:
        concurso_id = sorteio["concurso"]
        data_ref = sorteio["data"]
        dezenas_sorteadas = set(map(int, sorteio["dezenas"]))

        # 2️⃣ Palpites GERADOS PARA ESTE CONCURSO
        palpites_res = (
            supabase.table("palpites_validos")
            .select("id, numeros, tipo")
            .eq("concurso_referencia", concurso_id)
            .execute()
        )

        if not palpites_res.data:
            continue

        print(f"🔍 Conferindo concurso {concurso_id} ({len(palpites_res.data)} palpites)")

        resumo_por_tipo = {}

        for p in palpites_res.data:
            raw_nums = p.get("numeros")

            # Correção definitiva do campo numeros
            if isinstance(raw_nums, str):
                try:
                    clean = raw_nums.strip('"').replace("\\", "")
                    numeros = json.loads(clean)
                except Exception:
                    continue
            else:
                numeros = raw_nums

            numeros_palpite = set(map(int, numeros))
            tipo = p.get("tipo", "fixo")

            acertos = len(numeros_palpite & dezenas_sorteadas)

            if tipo not in resumo_por_tipo:
                resumo_por_tipo[tipo] = {
                    "11": 0,
                    "12": 0,
                    "13": 0,
                    "14": 0,
                    "15": 0,
                    "qtd_total": 0
                }

            resumo_por_tipo[tipo]["qtd_total"] += 1

            if acertos >= 11:
                resumo_por_tipo[tipo][str(acertos)] += 1

        # 3️⃣ Persistência (delete + insert seguro)
        for tipo, dados in resumo_por_tipo.items():
            versao = "v1.0"  # pode evoluir depois

            supabase.table("palpites_resultados_reais") \
                .delete() \
                .eq("concurso_inicio", concurso_id) \
                .eq("concurso_fim", concurso_id) \
                .eq("tipo_palpite", tipo) \
                .eq("versao_gerador", versao) \
                .execute()

            registro = {
                "data_referencia": data_ref,
                "concurso_inicio": concurso_id,
                "concurso_fim": concurso_id,
                "tipo_palpite": tipo,
                "versao_gerador": versao,
                "qtd_palpites": dados["qtd_total"],
                "acertos_11": dados["11"],
                "acertos_12": dados["12"],
                "acertos_13": dados["13"],
                "acertos_14": dados["14"],
                "acertos_15": dados["15"],
                "total_concursos": 1
            }

            supabase.table("palpites_resultados_reais").insert(registro).execute()

            print(
                f"✅ Concurso {concurso_id} [{tipo}] "
                f"| Palpites: {dados['qtd_total']} "
                f"| 11+: {dados['11']} "
                f"| 12+: {dados['12']}"
            )

        concursos_processados += 1

    print(f"🎯 Conferência finalizada: {concursos_processados} concursos processados.")

# -----------------------------------
if __name__ == "__main__":
    conferir_historico()
