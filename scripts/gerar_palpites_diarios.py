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

# ======================================================
# Configurações de 2026
# ======================================================
QTD_PALPITES = 7
VERSAO_GERADOR = "v4.0-resilient-2026"
MAX_CICLOS_GERACAO = 80000 
SIMILARIDADE_MAXIMA = 13 

def calcular_metricas_base(nums):
    pares = sum(1 for n in nums if n % 2 == 0)
    return pares, 15 - pares, sum(nums)

def validar_dinamico(nums, scores, config, ultimos, fator):
    pares, _, soma = calcular_metricas_base(nums)
    
    # Filtros com base na configuração atual (que relaxa com o tempo)
    if not (config['soma_min'] <= soma <= config['soma_max']): return False, 0.0
    if not (config['pares_min'] <= pares <= config['pares_max']): return False, 0.0
    
    repetidos = len(set(nums) & set(ultimos))
    if not (config['rep_min'] <= repetidos <= config['rep_max']): return False, 0.0

    # Score e Métricas Avançadas
    m = extrair_metricas_jogo(nums)
    chave = (round(m["soma"] / 10) * 10, m["pares"], m["primos"], tuple(m["linhas"]))
    score_final = aplicar_fator_aprendizado(scores.get(chave, 0), fator)

    return (score_final >= config['score_min']), score_final

def main():
    supabase = get_supabase()
    hoje = datetime.now().date().isoformat()
    
    # 1. Setup de Dados (Janeiro 2026)
    res_con = supabase.table("lotofacil_concursos").select("concurso, dezenas").order("concurso", desc=True).limit(1).execute()
    concurso_ref = res_con.data[0]["concurso"]
    ultimos = list(map(int, res_con.data[0]["dezenas"]))
    
    # Pool de 23 dezenas (essencial para diversidade)
    res_pool = supabase.table("estatisticas_numeros").select("numero").order("score", desc=True).limit(23).execute()
    pool = [r["numero"] for r in res_pool.data]
    
    fator = obter_fator_aprendizado_global().get("fator", 1.0)
    scores = calcular_score_combinacoes_reais()

    # 2. Configuração de Relaxamento Progressivo
    config = {
        'soma_min': 155, 'soma_max': 225,
        'pares_min': 5, 'pares_max': 10,
        'rep_min': 8, 'rep_max': 11,
        'score_min': 0.08
    }

    candidatos = []
    usados = set()

    print(f"🚀 Iniciando Gerador {VERSAO_GERADOR} [Ref: {concurso_ref}]")

    for ciclo in range(MAX_CICLOS_GERACAO):
        # Relaxamento Automático a cada 10k tentativas
        if ciclo > 0 and ciclo % 10000 == 0:
            config['score_min'] *= 0.4
            config['soma_min'] -= 5
            config['soma_max'] += 5
            config['pares_min'] = max(3, config['pares_min'] - 1)
            config['pares_max'] = min(12, config['pares_max'] + 1)
            config['rep_min'] = max(7, config['rep_min'] - 1)
            config['rep_max'] = min(13, config['rep_max'] + 1)
            print(f"🔄 Filtros relaxados (Ciclo {ciclo}): Score Min {config['score_min']:.4f}")

        nums = sorted(random.sample(pool, 15))
        if tuple(nums) in usados: continue

        valido, s_final = validar_dinamico(nums, scores, config, ultimos, fator)
        
        if valido:
            if any(len(set(nums) & set(ex["numeros"])) > SIMILARIDADE_MAXIMA for ex in candidatos):
                continue
            usados.add(tuple(nums))
            candidatos.append({"numeros": nums, "score": s_final})

        if len(candidatos) >= QTD_PALPITES: break

    # 3. Finalização e Persistência
    ranking = sorted(candidatos, key=lambda x: x["score"], reverse=True)
    registros = []
    
    for i, r in enumerate(ranking, 1):
        p, imp, soma = calcular_metricas_base(r["numeros"])
        registros.append({
            "data_referencia": hoje,
            "concurso_referencia": concurso_ref,
            "indice_palpite": i,
            "tipo": "estatistico",
            "numeros": json.dumps(r["numeros"]),
            "pares": p, "impares": imp, "soma_total": soma,
            "metricas": json.dumps({"v": VERSAO_GERADOR, "score": r["score"], "ciclos": ciclo})
        })

    supabase.table("palpites_validos").delete().eq("concurso_referencia", concurso_ref).execute()
    supabase.table("palpites_validos").insert(registros).execute()
    print(f"✅ Finalizado: {len(registros)} palpites salvos no concurso {concurso_ref}.")

if __name__ == "__main__":
    main()


