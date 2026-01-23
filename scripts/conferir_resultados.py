import os
import json
import logging
from datetime import datetime
from supabase import create_client, Client

# Configuração de Logs para monitoramento em 2026
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')

# -----------------------------------
# Configuração Supabase
# -----------------------------------
SUPABASE_URL = os.getenv("SUPABASE_URL", "").strip()
SUPABASE_KEY = os.getenv("SUPABASE_KEY", "").strip()

if not SUPABASE_URL or not SUPABASE_KEY:
    logging.error("❌ Variáveis de ambiente SUPABASE_URL ou SUPABASE_KEY não configuradas.")
    exit(1)

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# -----------------------------------
# Conferência com Feedback Loop
# -----------------------------------
def conferir_historico():
    logging.info(f"🚀 Iniciando Conferência 2026 - {datetime.now().strftime('%d/%m/%Y %H:%M')}")

    # 1. Resultados oficiais (Busca os últimos 10 para conferência/ajuste)
    res_oficiais = (
        supabase.table("lotofacil_concursos")
        .select("concurso, dezenas, data")
        .order("concurso", desc=True)
        .limit(10) 
        .execute()
    )

    if not res_oficiais.data:
        logging.error("❌ Nenhum concurso oficial encontrado no banco.")
        return

    for sorteio in res_oficiais.data:
        concurso_alvo = sorteio["concurso"]
        data_oficial = sorteio["data"]
        dezenas_sorteadas = set(map(int, sorteio["dezenas"]))

        # LÓGICA DE ALVO: O palpite gerado PARA o 3595 usa o 3594 como referência
        concurso_referencia_utilizado = concurso_alvo - 1

        # 2. Busca palpites que foram criados para este sorteio
        palpites_res = (
            supabase.table("palpites_validos")
            .select("id, numeros, tipo, acertos")
            .eq("concurso_referencia", concurso_referencia_utilizado)
            .execute()
        )

        if not palpites_res.data:
            continue

        # Filtra para processar apenas se ainda não houver conferência (evita loops desnecessários)
        # Se quiser forçar re-conferência, remova a condição 'p["acertos"] is None'
        logging.info(f"🔍 Concurso {concurso_alvo}: Conferindo {len(palpites_res.data)} palpites...")

        resumo_por_tipo = {}

        for p in palpites_res.data:
            try:
                raw_nums = p.get("numeros")
                # Tratamento resiliente do JSON de números
                if isinstance(raw_nums, str):
                    nums = json.loads(raw_nums.strip('"').replace("\\", ""))
                else:
                    nums = raw_nums
                
                numeros_palpite = set(map(int, nums))
                
                # CÁLCULO DE ACERTOS
                qtd_acertos = len(numeros_palpite & dezenas_sorteadas)
                tipo = p.get("tipo", "estatistico")

                # --- MELHORIA PRINCIPAL: FEEDBACK LOOP ---
                # Atualiza o palpite individual para que o gerador possa APRENDER com ele
                supabase.table("palpites_validos") \
                    .update({"acertos": qtd_acertos}) \
                    .eq("id", p["id"]) \
                    .execute()

                # Acumula para o resumo estatístico
                if tipo not in resumo_por_tipo:
                    resumo_por_tipo[tipo] = {"11":0,"12":0,"13":0,"14":0,"15":0,"total":0}
                
                resumo_por_tipo[tipo]["total"] += 1
                if qtd_acertos >= 11:
                    resumo_por_tipo[tipo][str(qtd_acertos)] += 1

            except Exception as e:
                logging.error(f"⚠️ Erro ao conferir palpite ID {p.get('id')}: {e}")
                continue

        # 3. Persistência do Resumo para Dashboard
        for tipo, dados in resumo_por_tipo.items():
            versao = "v7.3-fixo-2026"

            # Remove resumo antigo para este concurso/tipo e insere o novo (Upsert manual)
            supabase.table("palpites_resultados_reais") \
                .delete() \
                .eq("concurso_inicio", concurso_alvo) \
                .eq("tipo_palpite", tipo) \
                .execute()

            registro = {
                "data_referencia": data_oficial,
                "concurso_inicio": concurso_alvo,
                "concurso_fim": concurso_alvo,
                "tipo_palpite": tipo,
                "versao_gerador": versao,
                "qtd_palpites": dados["total"],
                "acertos_11": dados["11"],
                "acertos_12": dados["12"],
                "acertos_13": dados["13"],
                "acertos_14": dados["14"],
                "acertos_15": dados["15"],
                "total_concursos": 1
            }

            supabase.table("palpites_resultados_reais").insert(registro).execute()
            logging.info(f"✅ Resultado Salvo: Concurso {concurso_alvo} [{tipo}] -> {dados['11']} acertos de 11.")

    logging.info("🎯 Conferência finalizada com sucesso.")

if __name__ == "__main__":
    conferir_historico()

