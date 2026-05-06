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

# Importando suas lógicas de Memória e Ciclo
from scripts.processamento_diario_lotofacil import (
    carregar_historico, 
    calcular_ciclo_historico_completo,
    extrair_estrutura,
    buscar_cenario_similar
)

QTD_FINAL = 7
MAX_TENTATIVAS = 80000
VERSAO = "v12.6-full-integrated-brain"

def calcular_metricas_local(nums):
    pares = sum(n % 2 == 0 for n in nums)
    soma = sum(nums)
    dist = [sum(1 for n in nums if i <= n < i+5) for i in range(1, 26, 5)]
    primos = sum(1 for n in nums if n in {2,3,5,7,11,13,17,19,23})
    return pares, soma, dist, primos

def get_score_ciclo(nums, pendentes_ciclo):
    if not pendentes_ciclo or len(pendentes_ciclo) > 15: return 1.0
    encontradas = len(set(nums) & set(pendentes_ciclo))
    total_pendentes = len(pendentes_ciclo)
    if total_pendentes <= 5:
        return 1.6 if (encontradas / total_pendentes) >= 0.8 else 0.4
    return 1.0 + (encontradas * 0.05)

# --- INTEGRAÇÃO COM MEMÓRIA DE REGIMES ---
def obter_ajuste_regime(supabase):
    """Analisa o último regime para ajustar a agressividade da IA."""
    try:
        res = supabase.table("memoria_regimes").select("tipo_regime").order("concurso", desc=True).limit(1).execute()
        if not res.data: return 1.0
        regime = res.data[0]["tipo_regime"]
        # Se o regime é de Expansão de Quentes, bônus para scores altos
        if "QUENTES" in regime: return 1.10
        if "FRIAS" in regime: return 0.95
        return 1.0
    except: return 1.0

def main():
    supabase = get_supabase()
    fuso = pytz.timezone('America/Sao_Paulo')
    hoje = datetime.now(fuso).date().isoformat()

    print(f"🧠 {VERSAO} | Iniciando Motores...")

    # 1. Contexto Histórico e Ciclo
    historico = carregar_historico()
    ultimo_real = historico[-1]
    pendentes_ciclo, num_ciclo = calcular_ciclo_historico_completo(historico)
    concurso_ref = int(ultimo_real["concurso"]) + 1
    
    # 2. IA e Regimes
    base_scores, _ = calcular_score_combinacoes_reais()
    fator_global = obter_fator_aprendizado_global()["fator"]
    ajuste_regime = obter_ajuste_regime(supabase)

    print(f"📊 Ajuste de Regime Detectado: {ajuste_regime}")
    print(f"🚲 Ciclo {num_ciclo} | Pendentes: {len(pendentes_ciclo)}")

    candidatos = []
    pool = list(range(1, 26))

    for _ in range(MAX_TENTATIVAS):
        if len(candidatos) >= 5000: break
        
        jogo = gerar_jogo = sorted(random.sample(pool, 15))
        
        # 1. Score Bayesiano (Média de probabilidades individuais)
        s_base = np.mean([base_scores.get(tuple([n]), 0.5) for n in jogo])
        
        # 2. Lógica de Memória de Cenários (Seu código original)
        est = extrair_estrutura(jogo)
        mem = buscar_cenario_similar(supabase, est)
        s_memoria = 1.0
        if mem:
            score_real = float(mem.get("score_medio_real", 0))
            if score_real >= 4: s_memoria = 1.20
            elif score_real <= 1: s_memoria = 0.80

        # 3. Ciclo e Momentum
        s_ciclo = get_score_ciclo(jogo, pendentes_ciclo)
        repetidos = len(set(jogo) & set(ultimo_real["numeros"]))
        s_momentum = 1.25 if repetidos == 9 else (1.0 if 8 <= repetidos <= 10 else 0.7)

        # SCORE FINAL CONSOLIDADO
        score_final = s_base * s_ciclo * s_memoria * s_momentum * fator_global * ajuste_regime
        candidatos.append({"nums": jogo, "score": score_final, "est": est})

    # Seleção Final por Diversidade
    candidatos.sort(key=lambda x: x["score"], reverse=True)
    finais = []
    for cand in candidatos:
        if any(len(set(cand["nums"]) ^ set(f["nums"])) < 9 for f in finais): continue
        finais.append(cand)
        if len(finais) == QTD_FINAL: break

    print("\n🚀 Salvando Palpites v12.6...")
    payload = []
    for i, p in enumerate(finais, start=1):
        pares, soma, dist, primos = calcular_metricas_local(p["nums"])
        payload.append({
            "data_referencia": hoje, "concurso_referencia": concurso_ref, "indice_palpite": i,
            "tipo": "fixo" if i == 1 else "estatistico", "numeros": json.dumps(p["nums"]),
            "pares": pares, "impares": 15 - pares, "soma_total": soma,
            "processado": False, "conferido": False, "versao_gerador": VERSAO,
            "metricas": {
                "score_final": round(p['score'], 6),
                "ciclo": num_ciclo,
                "regime_ajuste": ajuste_regime,
                "memoria_match": True if p['score'] > 0.5 else False
            }
        })

    # Upsert final
    supabase.table("palpites_validos").delete().eq("data_referencia", hoje).eq("concurso_referencia", concurso_ref).execute()
    supabase.table("palpites_validos").insert(payload).execute()
    
    print(f"✅ Pipeline v12.6 finalizado. Boa sorte para o concurso {concurso_ref}!")

if __name__ == "__main__":
    main()


