import os
import json
from datetime import datetime
from supabase import create_client, Client

# Configuração de Ambiente
SUPABASE_URL = os.getenv("SUPABASE_URL", "").strip()
SUPABASE_KEY = os.getenv("SUPABASE_KEY", "").strip()
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

def conferir_historico():
    print(f"🚀 Iniciando Conferência 2026 - {datetime.now()}")

    # 1. Busca resultados oficiais da lotofacil_concursos
    res_oficiais = supabase.table("lotofacil_concursos").select("concurso, dezenas, data").order("concurso", desc=True).execute()
    if not res_oficiais.data:
        print("❌ Nenhum concurso oficial encontrado.")
        return

    for sorteio in res_oficiais.data:
        concurso_id = sorteio['concurso']
        data_ref = sorteio['data']
        dezenas_sorteadas = set(map(int, sorteio['dezenas']))

        # 2. Busca palpites do sistema para esta data
        palpites_res = supabase.table("palpites_validos").select("*").eq("data_referencia", data_ref).execute()
        
        if not palpites_res.data:
            continue

        print(f"🔍 Processando Concurso {concurso_id}...")
        
        # Agrupamento por tipo de palpite
        resumo_por_tipo = {}

        for p in palpites_res.data:
            # Tratamento de limpeza das strings de números
            raw_nums = p.get("numeros")
            if isinstance(raw_nums, str):
                clean_nums = raw_nums.strip('"').replace('\\', '')
                numeros_lista = json.loads(clean_nums)
            else:
                numeros_lista = raw_nums
            
            numeros_palpite = set(map(int, numeros_lista))
            tipo = p.get("tipo", "fixo")
            acertos = len(numeros_palpite & dezenas_sorteadas)

            if tipo not in resumo_por_tipo:
                resumo_por_tipo[tipo] = {
                    "11": 0, "12": 0, "13": 0, "14": 0, "15": 0, 
                    "qtd_total": 0
                }
            
            resumo_por_tipo[tipo]["qtd_total"] += 1
            if acertos >= 11:
                resumo_por_tipo[tipo][str(acertos)] += 1

        # 3. Gravação na tabela palpites_resultados_reais (Schema 2026)
        for tipo, dados in resumo_por_tipo.items():
            registro = {
                "data_referencia": data_ref,
                "concurso_inicio": concurso_id,
                "concurso_fim": concurso_id,
                "tipo_palpite": tipo,
                "versao_gerador": "v1.0",
                "qtd_palpites": dados["qtd_total"],
                "acertos_11": dados["11"],
                "acertos_12": dados["12"],
                "acertos_13": dados["13"],
                "acertos_14": dados["14"],
                "acertos_15": dados["15"],
                "total_concursos": 1
            }

            # O Upsert funciona aqui devido à sua constraint UNIQUE (concurso_inicio, concurso_fim, tipo_palpite, versao_gerador)
            try:
                supabase.table("palpites_resultados_reais").upsert(registro).execute()
                print(f"✅ Concurso {concurso_id} [{tipo}] atualizado com {dados['qtd_total']} palpites.")
            except Exception as e:
                print(f"❌ Erro ao gravar concurso {concurso_id}: {e}")

if __name__ == "__main__":
    conferir_historico()


if __name__ == "__main__":
    conferir_historico()
