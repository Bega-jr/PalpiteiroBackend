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
MAX_TENTATIVAS = 65000
VERSAO = "v11.0-ensemble-models"

def gerar_pool():
    return list(range(1, 26))

def gerar_jogo(pool):
    return sorted(random.sample(pool, 15))

def calcular_metricas(nums):
    pares = sum(n % 2 == 0 for n in nums)
    soma = sum(nums)
    linhas = [sum(1 for n in nums if i <= n < i+5) for i in range(1, 26, 5)]
    return pares, soma, linhas

def score_validacao(nums):
    pares, soma, linhas = calcular_metricas(nums)
    score = 1.0
    if not (7 <= pares <= 9): score *= 0.85
    if not (175 <= soma <= 210): score *= 0.85
    if max(linhas) > 5: score *= 0.75
    return score

# --- MODELO 1: BAYESIANO (Co-ocorrência) ---
def get_score_bayes(nums, base_scores):
    if not base_scores: return 0.5
    scores_presentes = [base_scores.get(tuple([n]), 0.5) for n in nums]
    return float(np.mean(scores_presentes))

# --- MODELO 2: MOMENTUM (Frequência Curta) ---
def get_score_momentum(nums, ultimo_concurso):
    # Dezenas que tendem a se manter (repetição do último)
    repetidos = len(set(nums) & set(ultimo_concurso))
    if repetidos == 9: return 1.2
    if repetidos in [8, 10]: return 1.0
    return 0.7

# --- MODELO 3: REENTRADA (Lei das Médias) ---
def get_score_reentrada(nums, ultimo_concurso):
    # Foca em dezenas que NÃO saíram no último (geralmente voltam 5 a 6)
    ausentes_ultimo = set(range(1, 26)) - set(ultimo_concurso)
    presentes_ausentes = len(set(nums) & ausentes_ultimo)
    if presentes_ausentes in [5, 6]: return 1.1
    return 0.8

def calcular_score_ensemble(nums, base_scores, rec_scores, fator, ultimo):
    # Pesos do Ensemble
    s_bayes = get_score_bayes(nums, base_scores)
    s_momentum = get_score_momentum(nums, ultimo)
    s_reentrada = get_score_reentrada(nums, ultimo)
    
    # Integração ponderada
    score_base = (s_bayes * 0.50) + (s_momentum * 0.25) + (s_reentrada * 0.25)
    
    # Validações estruturais e aprendizado global
    final = score_base * score_validacao(nums) * fator
    
    # Ruído controlado para diversidade genética
    return final * (1 + np.random.normal(0, 0.01))

def main():
    supabase = get_supabase()
    fuso = pytz.timezone('America/Sao_Paulo')
    hoje = datetime.now(fuso).date().isoformat()

    print(f"\n🚀 Gerador {VERSAO} iniciado")

    # Dados do último concurso
    res = supabase.table("lotofacil_concursos").select("concurso,dezenas").order("concurso", desc=True).limit(1).execute().data[0]
    concurso_base = int(str(res["concurso"]).strip())
    concurso_ref = concurso_base + 1
    
    ultimo = json.loads(res["dezenas"])
    if isinstance(ultimo, str): ultimo = json.loads(ultimo)
    ultimo = [int(x) for x in ultimo]

    fator = obter_fator_aprendizado_global()["fator"]
    base_scores, rec_scores = calcular_score_combinacoes_reais()

    candidatos = []
    vistos = set()
    pool = gerar_pool()

    print(f"🧠 Executando Ensemble Model em {MAX_TENTATIVAS} iterações...")

    for _ in range(MAX_TENTATIVAS):
        if len(candidatos) >= 5000: break
        
        jogo = gerar_jogo(pool)
        key = tuple(jogo)
        if key in vistos: continue
        vistos.add(key)

        score = calcular_score_ensemble(jogo, base_scores, rec_scores, fator, ultimo)
        candidatos.append({"nums": jogo, "score": score})

    # Ranking e Seleção por Diversidade
    candidatos.sort(key=lambda x: x["score"], reverse=True)
    finais = []
    freq_global = Counter()

    for cand in candidatos:
        nums = cand["nums"]
        
        # Filtro de distância Ensemble (mínimo 9 dezenas diferentes)
        if any(len(set(nums) ^ set(f["nums"])) < 9 for f in finais):
            continue

        finais.append(cand)
        for n in nums: freq_global[n] += 1
        if len(finais) == QTD_FINAL: break

    print("\n🏆 RESULTADO ENSEMBLE v11.0:")
    payload = []
    for i, p in enumerate(finais, start=1):
        print(f"{i}º | Score: {p['score']:.6f} | {p['nums']}")
        pares, soma, _ = calcular_metricas(p["nums"])
        
        payload.append({
            "data_referencia": hoje,
            "concurso_referencia": concurso_ref,
            "indice_palpite": i,
            "tipo": "fixo" if i == 1 else "estatistico",
            "numeros": json.dumps(p["nums"]),
            "pares": pares, "impares": 15 - pares, "soma_total": soma,
            "processado": False, "conferido": False,
            "versao_gerador": VERSAO,
            "metricas": {"score_ensemble": round(float(p["score"]), 6)}
        })

    # Persistência
    supabase.table("palpites_validos").delete().eq("data_referencia", hoje).eq("concurso_referencia", concurso_ref).execute()
    supabase.table("palpites_validos").insert(payload).execute()
    print(f"\n✅ Pipeline v11.0 finalizado com sucesso.")

if __name__ == "__main__":
    main()
