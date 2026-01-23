import sys
import json
import random
import logging
from pathlib import Path
from datetime import datetime

logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.append(str(BASE_DIR))

from app.services.supabase_service import get_supabase
from app.services.aprendizado_service_v3 import obter_fator_aprendizado_global, aplicar_fator_aprendizado
from app.services.estatisticas_combinacao_v3 import calcular_score_combinacoes_reais, extrair_metricas_jogo

QTD_PALPITES = 7
VERSAO_GERADOR = "v6.0-adaptive-cascade-2026"

def obter_metricas_completas(nums):
    pares = sum(1 for n in nums if n % 2 == 0)
    soma = sum(nums)
    linhas = [0] * 5
    for n in nums:
        linhas[(n - 1) // 5] += 1
    return {"pares": pares, "soma": soma, "linhas": linhas}

def main():
    supabase = get_supabase()
    hoje = datetime.now().date().isoformat()
    
    # 1. SETUP DE DADOS (Referência Concurso 3594 - Janeiro 2026)
    try:
        res_con = supabase.table("lotofacil_concursos").select("concurso, dezenas").order("concurso", desc=True).limit(1).execute()
        concurso_ref = res_con.data[0]["concurso"]
        ultimos = list(map(int, res_con.data[0]["dezenas"]))
        
        # Aumentamos para 23 dezenas para maior diversidade estatística
        res_pool = supabase.table("estatisticas_numeros").select("numero").order("score", desc=True).limit(25).execute()
        pool = [r["numero"] for r in res_pool.data]
    except Exception as e:
        logging.error(f"Erro ao carregar dados: {e}")
        return

    fator = obter_fator_aprendizado_global().get("fator", 1.0)
    scores_db = calcular_score_combinacoes_reais()

    # 2. HIERARQUIA DE REGRAS (Prioridade Decrescente)
    # Nível 4: Todos os filtros ativos (Ideal)
    # Nível 0: Sem filtros (Garante a entrega)
    print(f"🚀 Iniciando Geração Adaptativa [Concurso {concurso_ref}]")

    candidatos = []
    usados = set()

    for nivel in range(4, -1, -1):
        if len(candidatos) >= QTD_PALPITES: break
        
        print(f"  🔍 Tentando Nível de Rigidez {nivel}...")
        for _ in range(20000):
            if len(candidatos) >= QTD_PALPITES: break
            
            nums = sorted(random.sample(pool, 15))
            if tuple(nums) in usados: continue
            
            m = obter_metricas_completas(nums)
            valido = True
            
            # Aplicação Cascata
            if nivel >= 4: # Filtro de Linhas (Essencial)
                if not all(1 <= x <= 5 for x in m["linhas"]): valido = False
            if valido and nivel >= 3: # Filtro de Soma e Paridade
                if not (155 <= m["soma"] <= 225) or not (5 <= m["pares"] <= 10): valido = False
            if valido and nivel >= 2: # Filtro de Repetição
                rep = len(set(nums) & set(ultimos))
                if not (7 <= rep <= 12): valido = False
            if valido and nivel >= 1: # Filtro de Score Base
                metr_adv = extrair_metricas_jogo(nums)
                chave = (round(metr_adv["soma"] / 10) * 10, metr_adv["pares"], metr_adv["primos"], tuple(metr_adv["linhas"]))
                score = aplicar_fator_aprendizado(scores_db.get(chave, 0), fator)
                if score < 0.005: valido = False
            else:
                # Cálculo de score para ranking mesmo se o filtro estiver off
                metr_adv = extrair_metricas_jogo(nums)
                chave = (round(metr_adv["soma"] / 10) * 10, metr_adv["pares"], metr_adv["primos"], tuple(metr_adv["linhas"]))
                score = aplicar_fator_aprendizado(scores_db.get(chave, 0), fator)

            if valido:
                # Filtro de similaridade (Sempre mantido para diversidade do volante)
                if any(len(set(nums) & set(ex["nums"])) > 13 for ex in candidatos): continue
                candidatos.append({"nums": nums, "score": score, "m": m, "nivel": nivel})
                usados.add(tuple(nums))

    # 3. PERSISTÊNCIA
    if not candidatos:
        logging.error("Falha crítica: Nenhuma combinação gerada.")
        return

    ranking = sorted(candidatos, key=lambda x: x["score"], reverse=True)[:QTD_PALPITES]
    registros = []
    for idx, r in enumerate(ranking, 1):
        registros.append({
            "data_referencia": hoje,
            "concurso_referencia": concurso_ref,
            "indice_palpite": idx,
            "tipo": "estatistico",
            "numeros": json.dumps(r["nums"]),
            "pares": r["m"]["pares"],
            "impares": 15 - r["m"]["pares"],
            "soma_total": r["m"]["soma"],
            "metricas": json.dumps({"v": VERSAO_GERADOR, "nivel": r["nivel"], "score": r["score"]})
        })

    supabase.table("palpites_validos").delete().eq("concurso_referencia", concurso_ref).execute()
    supabase.table("palpites_validos").insert(registros).execute()
    print(f"✅ Sucesso: {len(registros)} palpites salvos (Referência 2026).")

if __name__ == "__main__":
    main()




