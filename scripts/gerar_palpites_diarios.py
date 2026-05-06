import sys
import random
import json
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

QTD_FINAL = 7
MAX_TENTATIVAS = 75000
VERSAO = "v12.0-rl-dynamic-weights"

def gerar_pool():
    return list(range(1, 26))

def gerar_jogo(pool):
    return sorted(random.sample(pool, 15))

def calcular_metricas(nums):
    pares = sum(n % 2 == 0 for n in nums)
    soma = sum(nums)
    # Distribuição por linhas (1-5, 6-10, etc)
    dist = [sum(1 for n in nums if i <= n < i+5) for i in range(1, 26, 5)]
    return pares, soma, dist

def score_validacao(nums):
    pares, soma, dist = calcular_metricas(nums)
    score = 1.0
    if not (7 <= pares <= 9): score *= 0.80
    if not (175 <= soma <= 215): score *= 0.85
    if max(dist) > 5: score *= 0.70
    return score

# --- ESPECIALISTAS (SUB-MODELOS) ---
def get_score_bayes(nums, base_scores):
    if not base_scores: return 0.5
    scores = [base_scores.get(tuple([n]), 0.5) for n in nums]
    return float(np.mean(scores))

def get_score_momentum(nums, ultimo):
    repetidos = len(set(nums) & set(ultimo))
    return 1.2 if repetidos == 9 else (1.0 if repetidos in [8, 10] else 0.7)

def get_score_markov(nums, hist):
    score = 0
    for n in nums:
        atraso = 0
        for concurso in hist:
            if n in concurso: break
            atraso += 1
        score += 1.1 if atraso == 1 else (1.0 if atraso == 0 else 0.8)
    return score / 15

# --- NOVO: AGENTE DE REINFORCEMENT LEARNING (v12.0) ---
def auditoria_pesos_dinamicos(ultimo_real, base_scores, hist_recente):
    """
    Simula os modelos contra o sorteio real de ontem para definir os pesos de hoje.
    """
    print("🧠 Agente RL: Auditando performance do último sorteio...")
    
    # 1. Qual dezena o Bayes sugeriria? (Top 15 com maior score individual)
    top_bayes = sorted(range(1, 26), key=lambda n: base_scores.get(tuple([n]), 0), reverse=True)[:15]
    acerto_bayes = len(set(top_bayes) & set(ultimo_real))
    
    # 2. Qual dezena o Markov sugeriria? (Foco em atraso 1)
    acerto_markov = len(set(n for n in range(1, 26) if n not in list(hist_recente)[0]) & set(ultimo_real))

    # Normalização de Recompensa (Softmax simplificado)
    total = acerto_bayes + acerto_markov + 1e-6
    w_bayes = max(0.20, acerto_bayes / total) # Mínimo de 20% para não atrofiar o modelo
    w_markov = 1.0 - w_bayes
    
    print(f"   📈 Recompensa Bayes: {acerto_bayes} | Markov: {acerto_markov}")
    print(f"   ⚖️ Novos Pesos -> Bayes: {w_bayes:.2f} | Markov: {w_markov:.2f}")
    
    return w_bayes, w_markov

def main():
    supabase = get_supabase()
    fuso = pytz.timezone('America/Sao_Paulo')
    hoje = datetime.now(fuso).date().isoformat()

    print(f"\n🚀 Gerador {VERSAO} iniciado")

    # Busca histórico para Auditoria
    res_db = supabase.table("lotofacil_concursos").select("concurso,dezenas").order("concurso", desc=True).limit(5).execute().data
    
    hist_recente = []
    for r in res_db:
        d = json.loads(r["dezenas"]) if isinstance(r["dezenas"], str) else r["dezenas"]
        hist_recente.append(set(int(x) for x in d))

    ultimo_real = list(hist_recente)[0]
    concurso_ref = int(str(res_db[0]["concurso"]).strip()) + 1

    fator_global = obter_fator_aprendizado_global()["fator"]
    base_scores, rec_scores = calcular_score_combinacoes_reais()

    # ACIONA O CÉREBRO RL
    w_bayes, w_markov = auditoria_pesos_dinamicos(ultimo_real, base_scores, hist_recente)

    candidatos = []
    vistos = set()
    pool = gerar_pool()

    for _ in range(MAX_TENTATIVAS):
        if len(candidatos) >= 5000: break
        jogo = gerar_jogo(pool)
        key = tuple(jogo)
        if key in vistos: continue
        vistos.add(key)

        # Lógica de Ensemble Dinâmico
        s_bayes = get_score_bayes(jogo, base_scores)
        s_momentum = get_score_momentum(jogo, ultimo_real)
        s_markov = get_score_markov(jogo, hist_recente)
        
        # Pesos decididos pelo Agente RL
        score_base = (s_bayes * w_bayes) + (s_markov * w_markov)
        score_base *= s_momentum # Momentum age como multiplicador de tendência
        
        final = score_base * score_validacao(jogo) * fator_global
        candidatos.append({"nums": jogo, "score": final})

    candidatos.sort(key=lambda x: x["score"], reverse=True)
    finais = []
    for cand in candidatos:
        if any(len(set(cand["nums"]) ^ set(f["nums"])) < 9 for f in finais): continue
        finais.append(cand)
        if len(finais) == QTD_FINAL: break

    print("\n🏆 RESULTADO RL v12.0:")
    payload = []
    for i, p in enumerate(finais, start=1):
        print(f"{i}º | Score: {p['score']:.6f} | {p['nums']}")
        pares, soma, _ = calcular_metricas(p["nums"])
        payload.append({
            "data_referencia": hoje, "concurso_referencia": concurso_ref, "indice_palpite": i,
            "tipo": "fixo" if i == 1 else "estatistico", "numeros": json.dumps(p["nums"]),
            "pares": pares, "impares": 15-pares, "soma_total": soma,
            "processado": False, "conferido": False, "versao_gerador": VERSAO,
            "metricas": {"pesos": {"bayes": w_bayes, "markov": w_markov}, "score": p['score']}
        })

    supabase.table("palpites_validos").delete().eq("data_referencia", hoje).eq("concurso_referencia", concurso_ref).execute()
    supabase.table("palpites_validos").insert(payload).execute()
    print(f"\n✅ v12.0 concluída. Pesos calibrados com sucesso.")

if __name__ == "__main__":
    main()

