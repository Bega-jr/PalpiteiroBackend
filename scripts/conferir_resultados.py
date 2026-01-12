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

    # 1. Busca resultados oficiais
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

        print(f"🔍 Processando Concurso {concurso_id} ({data_ref})...")
        resumo_por_tipo = {}

        for p in palpites_res.data:
            # Limpeza de números (tratamento de aspas extras)
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

        # 3. Gravação na tabela palpites_resultados_reais (Delete + Insert)
        for tipo, dados in resumo_por_tipo.items():
            versao = "v1.0"
            
            # Deleta registro existente para evitar erro de chave duplicada (23505)
            supabase.table("palpites_resultados_reais").delete()\
                .eq("concurso_inicio", concurso_id)\
                .eq("concurso_fim", concurso_id)\
                .eq("tipo_palpite", tipo)\
                .eq("versao_gerador", versao)\
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

            try:
                supabase.table("palpites_resultados_reais").insert(registro).execute()
                print(f"✅ Concurso {concurso_id} [{tipo}] gravado com {dados['qtd_total']} palpites.")
            except Exception as e:
                print(f"❌ Erro ao inserir concurso {concurso_id}: {e}")

if __name__ == "__main__":
    conferir_historico()

