import os
import json
import logging
from datetime import datetime
from supabase import create_client, Client

logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')

# Configuração Supabase
SUPABASE_URL = os.getenv("SUPABASE_URL", "").strip()
SUPABASE_KEY = os.getenv("SUPABASE_KEY", "").strip()
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

def conferir_historico():
    logging.info(f"🚀 Iniciando Conferência 2026 - {datetime.now()}")

    # 1. Resultados oficiais (todos para garantir retroatividade)
    res_oficiais = supabase.table("lotofacil_concursos").select("concurso, dezenas, data").order("concurso", desc=True).execute()

    if not res_oficiais.data:
        logging.error("❌ Nenhum concurso oficial encontrado.")
        return

    for sorteio in res_oficiais.data:
        concurso_id = sorteio["concurso"]
        data_ref = sorteio["data"]
        dezenas_sorteadas = set(map(int, sorteio["dezenas"]))

        # LÓGICA 2026: O palpite gerado COM BASE NO 3594 é para o sorteio 3595
        # Portanto, buscamos palpites onde concurso_referencia = concurso_id - 1
        concurso_base = concurso_id - 1
        
        palpites_res = (
            supabase.table("palpites_validos")
            .select("id, numeros, tipo")
            .eq("concurso_referencia", concurso_base)
            .execute()
        )

        if not palpites_res.data:
            continue

        logging.info(f"🔍 Conferindo Concurso {concurso_id} (Baseado no {concurso_base})")
        resumo_por_tipo = {}

        for p in palpites_res.data:
            try:
                raw_nums = p.get("numeros")
                if isinstance(raw_nums, str):
                    nums = json.loads(raw_nums.strip('"').replace("\\", ""))
                else:
                    nums = raw_nums
                
                numeros_palpite = set(map(int, nums))
                acertos = len(numeros_palpite & dezenas_sorteadas)
                tipo = p.get("tipo", "estatistico")

                # AÇÃO CRÍTICA: Atualiza o palpite individual para o Aprendizado_V3
                supabase.table("palpites_validos").update({"acertos": acertos}).eq("id", p["id"]).execute()

                # Contabilização para o Resumo Real
                if tipo not in resumo_por_tipo:
                    resumo_por_tipo[tipo] = {"11":0,"12":0,"13":0,"14":0,"15":0,"total":0}
                
                resumo_por_tipo[tipo]["total"] += 1
                if acertos >= 11:
                    resumo_por_tipo[tipo][str(acertos)] += 1

            except Exception as e:
                logging.error(f"Erro ao processar palpite {p['id']}: {e}")
                continue

        # 3. Persistência do Resumo Geral (Dashboard)
        for tipo, dados in resumo_por_tipo.items():
            # Limpa para evitar duplicidade
            supabase.table("palpites_resultados_reais").delete() \
                .eq("concurso_inicio", concurso_id).eq("tipo_palpite", tipo).execute()

            registro = {
                "data_referencia": data_ref,
                "concurso_inicio": concurso_id,
                "concurso_fim": concurso_id,
                "tipo_palpite": tipo,
                "versao_gerador": "v7.3-fixo-2026",
                "qtd_palpites": dados["total"],
                "acertos_11": dados["11"],
                "acertos_12": dados["12"],
                "acertos_13": dados["13"],
                "acertos_14": dados["14"],
                "acertos_15": dados["15"],
                "total_concursos": 1
            }
            supabase.table("palpites_resultados_reais").insert(registro).execute()
            logging.info(f"✅ Salvo Resumo {concurso_id} [{tipo}]: {dados['11']} acertos de 11.")

if __name__ == "__main__":
    conferir_historico()
