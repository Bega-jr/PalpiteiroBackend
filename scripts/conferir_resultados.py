import os
import json
from datetime import datetime
from supabase import create_client, Client

# =========================
# CONFIG (Mesma do seu script funcional)
# =========================
SUPABASE_URL = os.getenv("SUPABASE_URL", "").strip()
SUPABASE_KEY = os.getenv("SUPABASE_KEY", "").strip()
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

def conferir_historico():
    print(f"🚀 Iniciando Conferência Histórica - {datetime.now()}")

    # 1. Busca todos os resultados oficiais
    res_oficiais = supabase.table("lotofacil_concursos").select("concurso, dezenas, data").order("concurso", desc=True).execute()
    if not res_oficiais.data:
        print("❌ Nenhum concurso oficial encontrado.")
        return

    # 2. Itera sobre os concursos
    for sorteio in res_oficiais.data:
        concurso_id = sorteio['concurso']
        data_ref = sorteio['data']
        dezenas_sorteadas = set(map(int, sorteio['dezenas']))

        # 3. Busca palpites do sistema para esta data
        palpites_res = supabase.table("palpites_validos").select("*").eq("data_referencia", data_ref).execute()
        
        if not palpites_res.data:
            continue

        print(f"🔍 Conferindo Concurso {concurso_id} ({data_ref})...")
        resumo = {}

        for p in palpites_res.data:
            # Tratamento de aspas duplas (conforme discutido)
            raw_nums = p.get("numeros")
            if isinstance(raw_nums, str):
                clean_nums = raw_nums.strip('"').replace('\\', '')
                numeros_lista = json.loads(clean_nums)
            else:
                numeros_lista = raw_nums
            
            numeros_palpite = set(map(int, numeros_lista))
            tipo = p.get("tipo", "fixo")
            acertos = len(numeros_palpite & dezenas_sorteadas)

            if tipo not in resumo:
                resumo[tipo] = {"11":0, "12":0, "13":0, "14":0, "15":0}
            
            if acertos >= 11:
                resumo[tipo][str(acertos)] += 1

        # 4. Grava na tabela de resultados (UPSERT por Concurso e Tipo)
        for tipo, counts in resumo.items():
            # Excluímos o antigo para evitar duplicados
            supabase.table("palpites_resultados_reais").delete().eq("concurso", concurso_id).eq("tipo_palpite", tipo).execute()
            
            # Insere o novo resumo
            supabase.table("palpites_resultados_reais").insert({
                "concurso": concurso_id,
                "tipo_palpite": tipo,
                "versao_gerador": "v1.0",
                "acertos_11": counts["11"],
                "acertos_12": counts["12"],
                "acertos_13": counts["13"],
                "acertos_14": counts["14"],
                "acertos_15": counts["15"],
                "total_concursos": 1,
                "data_referencia": data_ref
            }).execute()
            print(f"✅ Concurso {concurso_id} [{tipo}] gravado.")

if __name__ == "__main__":
    conferir_historico()
