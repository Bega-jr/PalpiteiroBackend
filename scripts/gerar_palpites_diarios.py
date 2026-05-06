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
# Importando suas lógicas existentes do Passo 1
from scripts.processamento_diario_lotofacil import (
    carregar_historico, 
    calcular_ciclo_historico_completo,
    extrair_estrutura,
    buscar_cenario_similar
)

QTD_FINAL = 7
MAX_TENTATIVAS = 75000
VERSAO = "v12.5-integrated-brain"

def gerar_jogo(pool):
    return sorted(random.sample(pool, 15))

def calcular_metricas_local(nums):
    pares = sum(n % 2 == 0 for n in nums)
    soma = sum(nums)
    dist = [sum(1 for n in nums if i <= n < i+5) for i in range(1, 26, 5)]
    return pares, soma, dist

# --- INTEGRANDO SUA LÓGICA DE CICLO ---
def get_score_ciclo(nums, pendentes_ciclo):
    if not pendentes_ciclo or len(pendentes_ciclo) > 12:
        return 1.0
    
    encontradas = len(set(nums) & set(pendentes_ciclo))
    total_pendentes = len(pendentes_ciclo)
    
    # Se faltam poucas (até 5), bônus agressivo para fechamento
    if total_pendentes <= 5:
        taxa = encontradas / total_pendentes
        return 1.5 if taxa >= 0.8 else 0.4
    
    return 1.0 + (encontradas * 0.05)

# --- INTEGRANDO SUA LÓGICA DE MEMÓRIA ---
def get_ajuste_memoria(nums, supabase):
    est = extrair_estrutura(nums)
    memoria = buscar_cenario_similar(supabase, est)
    if not memoria: return 1.0
    
    score_real = float(memoria.get("score_medio_real", 0))
    if score_real >= 4: return 1.15
    if score_real <= 1: return 0.85
    return 1.0

def main():
    supabase = get_supabase()
    fuso = pytz.timezone('America/Sao_Paulo')
    hoje = datetime.now(fuso).date().isoformat()

    print(f"🧠 {VERSAO} | Iniciando integração total...")

    # 1. Carregar Dados de Contexto (Ciclo e Histórico)
    historico = carregar_historico()
    ultimo_real_concurso = historico[-1]
    pendentes_ciclo, num_ciclo = calcular_ciclo_historico_completo(historico)
    
    concurso_ref = int(ultimo_real_concurso["concurso"]) + 1
    ultimo_sorteio = ultimo_real_concurso["numeros"]

    print(f"📌 Concurso Ref: {concurso_ref} | Cicto Atual: {num_ciclo}")
    print(f"🚲 Dezenas pendentes no Ciclo: {pendentes_ciclo}")

    # 2. IA Scores e RL weights (da v12.0)
    base_scores, _ = calcular_score_combinacoes_reais()
    fator_global = obter_fator_aprendizado_global()["fator"]

    candidatos = []
    pool = list(range(1, 26))

    print(f"🚀 Gerando candidatos com Memória e Ciclo...")

    for _ in range(MAX_TENTATIVAS):
        if len(candidatos) >= 5000: break
        
        jogo = gerar_jogo(pool)
        
        # Score Bayesiano Base
        s_base = np.mean([base_scores.get(tuple([n]), 0.5) for n in jogo])
        
        # Ajuste de Ciclo
        s_ciclo = get_score_ciclo(jogo, pendentes_ciclo)
        
        # Ajuste de Memória de Cenário
        s_memoria = get_ajuste_memoria(jogo, supabase)
        
        # Repetição do último (Momentum)
        repetidos = len(set(jogo) & set(ultimo_sorteio))
        s_momentum = 1.2 if repetidos == 9 else (1.0 if repetidos in [8, 10] else 0.7)

        score_final = s_base * s_ciclo * s_memoria * s_momentum * fator_global
        candidatos.append({"nums": jogo, "score": score_final})

    # Seleção Final
    candidatos.sort(key=lambda x: x["score"], reverse=True)
    finais = []
    for cand in candidatos:
        if any(len(set(cand["nums"]) ^ set(f["nums"])) < 9 for f in finais): continue
        finais.append(cand)
        if len(finais) == QTD_FINAL: break

    # Salvamento
    print("\n💾 Populando Tabelas...")
    payload = []
    for i, p in enumerate(finais, start=1):
        pares, soma, _ = calcular_metricas_local(p["nums"])
        payload.append({
            "data_referencia": hoje, "concurso_referencia": concurso_ref, "indice_palpite": i,
            "tipo": "fixo" if i == 1 else "estatistico", "numeros": json.dumps(p["nums"]),
            "pares": pares, "impares": 15-pares, "soma_total": soma,
            "processado": False, "conferido": False, "versao_gerador": VERSAO,
            "metricas": {"score": round(p['score'], 6), "ciclo": num_ciclo, "pendentes": list(pendentes_ciclo)}
        })

    # Limpa e Insere
    supabase.table("palpites_validos").delete().eq("data_referencia", hoje).eq("concurso_referencia", concurso_ref).execute()
    supabase.table("palpites_validos").insert(payload).execute()
    
    print(f"✅ Tabelas populadas. {len(payload)} palpites prontos para o concurso {concurso_ref}.")

if __name__ == "__main__":
    main()

