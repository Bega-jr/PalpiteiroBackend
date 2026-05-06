import sys
import json
import random
import numpy as np
import pytz
from pathlib import Path
from datetime import datetime
from collections import Counter

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.append(str(BASE_DIR))

from app.services.supabase_service import get_supabase
from app.services.aprendizado_service_v3 import obter_fator_aprendizado_global
from app.services.estatisticas_combinacao_v3 import calcular_score_combinacoes_reais

from scripts.processamento_diario_lotofacil import (
    carregar_historico, 
    calcular_ciclo_historico_completo,
    extrair_estrutura,
    buscar_cenario_similar
)

QTD_FINAL = 7
MAX_TENTATIVAS = 90000 # Aumentado para compensar os filtros mais rígidos
VERSAO = "v13.0-safety-filters"

def calcular_metricas_v13(nums):
    pares = sum(n % 2 == 0 for n in nums)
    impares = 15 - pares
    soma = sum(nums)
    # Calcula maior sequência de números seguidos
    seq_max = 1
    atual = 1
    for i in range(len(nums)-1):
        if nums[i+1] == nums[i] + 1:
            atual += 1
            seq_max = max(seq_max, atual)
        else:
            atual = 1
    return pares, impares, soma, seq_max

def score_seguranca(nums):
    pares, impares, soma, seq_max = calcular_metricas_v13(nums)
    score = 1.0
    
    # Filtro Estrito de Soma (Ideal 165-215)
    if soma < 160 or soma > 220:
        score *= 0.20 # Corte pesado para somas extremas
    
    # Filtro de Paridade (Ideal 7-8-9 ímpares)
    if impares > 10 or impares < 5:
        score *= 0.30
        
    # Filtro de Sequências Longas
    if seq_max > 5:
        score *= 0.50

    return score

def main():
    supabase = get_supabase()
    fuso = pytz.timezone('America/Sao_Paulo')
    hoje = datetime.now(fuso).date().isoformat()

    print(f"🛡️ {VERSAO} | Aplicando filtros de segurança estritos...")

    historico = carregar_historico()
    ultimo_real = historico[-1]
    pendentes_ciclo, num_ciclo = calcular_ciclo_historico_completo(historico)
    concurso_ref = int(ultimo_real["concurso"]) + 1
    
    base_scores, _ = calcular_score_combinacoes_reais()
    fator_global = obter_fator_aprendizado_global()["fator"]

    # Busca o último ajuste de regime
    try:
        reg_db = supabase.table("memoria_regimes").select("tipo_regime").order("concurso", desc=True).limit(1).execute().data[0]
        ajuste_regime = 1.15 if "QUENTES" in reg_db["tipo_regime"] else 1.0
    except:
        ajuste_regime = 1.0

    candidatos = []
    pool = list(range(1, 26))

    for _ in range(MAX_TENTATIVAS):
        if len(candidatos) >= 5000: break
        
        jogo = sorted(random.sample(pool, 15))
        
        # 1. Base IA
        s_base = np.mean([base_scores.get(tuple([n]), 0.5) for n in jogo])
        
        # 2. Match de Memória (Bônus para o que já funcionou)
        est = extrair_estrutura(jogo)
        mem = buscar_cenario_similar(supabase, est)
        s_memoria = 1.0
        match_real = False
        if mem:
            score_real = float(mem.get("score_medio_real", 0))
            if score_real > 0: 
                s_memoria = 1.25 # Bônus de confiança
                match_real = True

        # 3. Filtros Estritos v13
        s_safety = score_seguranca(jogo)

        # 4. Momentum (9 repetidas é o alvo)
        repetidos = len(set(jogo) & set(ultimo_real["numeros"]))
        s_momentum = 1.2 if repetidos == 9 else 1.0

        score_final = s_base * s_memoria * s_safety * s_momentum * fator_global * ajuste_regime
        
        if score_final > 0.05: # Só aceita se passar pelo filtro básico
            candidatos.append({"nums": jogo, "score": score_final, "match": match_real})

    # Seleção Final
    candidatos.sort(key=lambda x: x["score"], reverse=True)
    finais = []
    for cand in candidatos:
        if any(len(set(cand["nums"]) ^ set(f["nums"])) < 9 for f in finais): continue
        finais.append(cand)
        if len(finais) == QTD_FINAL: break

    print(f"\n💾 Salvando {len(finais)} palpites blindados...")
    payload = []
    for i, p in enumerate(finais, start=1):
        pares, impares, soma, _ = calcular_metricas_v13(p["nums"])
        payload.append({
            "data_referencia": hoje, "concurso_referencia": concurso_ref, "indice_palpite": i,
            "tipo": "fixo" if i == 1 else "estatistico", "numeros": json.dumps(p["nums"]),
            "pares": pares, "impares": impares, "soma_total": soma,
            "processado": False, "conferido": False, "versao_gerador": VERSAO,
            "metricas": {
                "score": round(p['score'], 6),
                "memoria_match": p['match'],
                "soma_total": soma
            }
        })

    supabase.table("palpites_validos").delete().eq("data_referencia", hoje).eq("concurso_referencia", concurso_ref).execute()
    supabase.table("palpites_validos").insert(payload).execute()
    print(f"✅ v13.0 concluída. Somas e paridades estabilizadas.")

if __name__ == "__main__":
    main()



