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
MAX_TENTATIVAS = 70000 # Aumentado para explorar mais estados
VERSAO = "v11.5-markov-temporal"

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

# --- MODELO 2: MOMENTUM (Repetição) ---
def get_score_momentum(nums, ultimo_concurso):
    repetidos = len(set(nums) & set(ultimo_concurso))
    if repetidos == 9: return 1.2
    if repetidos in [8, 10]: return 1.0
    return 0.7

# --- NOVO MODELO 3: CADEIA DE MARKOV (Memória Temporal) ---
def get_score_markov(nums, historico_recente):
    """
    Analisa a probabilidade de transição baseado nos últimos estados das dezenas.
    historico_recente: Lista de sets dos últimos 5 concursos.
    """
    score_markov = 0
    for n in nums:
        atraso = 0
        for i, concurso in enumerate(historico_recente):
            if n in concurso:
                break
            atraso += 1
        
        # Lógica de Reentrada: Números com atraso 1 ou 2 têm pico de retorno
        if atraso == 1: score_markov += 1.1  # Pula 1 concurso e volta (Frequente)
        elif atraso == 0: score_markov += 1.0 # Saiu no último (Manutenção)
        elif atraso >= 3: score_markov += 0.8 # Dezenas "frias" demais demoram a voltar
        else: score_markov += 0.9
            
    return score_markov / 15

def calcular_score_ensemble_markov(nums, base_scores, rec_scores, fator, ultimo, hist_recente):
    s_bayes = get_score_bayes(nums, base_scores)
    s_momentum = get_score_momentum(nums, ultimo)
    s_markov = get_score_markov(nums, hist_recente)
    
    # Integração v11.5: Adicionando peso temporal
    score_base = (s_bayes * 0.40) + (s_momentum * 0.30) + (s_markov * 0.30)
    
    final = score_base * score_validacao(nums) * fator
    return final * (1 + np.random.normal(0, 0.01))

def main():
    supabase = get_supabase()
    fuso = pytz.timezone('America/Sao_Paulo')
    hoje = datetime.now(fuso).date().isoformat()

    print(f"\n🚀 Gerador {VERSAO} iniciado")

    # Busca últimos 5 concursos para a Cadeia de Markov
    res_db = supabase.table("lotofacil_concursos").select("concurso,dezenas").order("concurso", desc=True).limit(5).execute().data
    
    if not res_db:
        print("❌ Erro: Histórico insuficiente.")
        return

    # Processa histórico recente
    hist_recente = []
    for r in res_db:
        d = r["dezenas"]
        if isinstance(d, str): d = json.loads(d)
        if isinstance(d, str): d = json.loads(d)
        hist_recente.append(set(int(x) for x in d))

    ultimo = list(hist_recente[0])
    concurso_base = int(str(res_db[0]["concurso"]).strip())
    concurso_ref = concurso_base + 1

    print(f"📌 Analisando transições de estado para concurso {concurso_ref}")

    fator = obter_fator_aprendizado_global()["fator"]
    base_scores, rec_scores = calcular_score_combinacoes_reais()

    candidatos = []
    vistos = set()
    pool = gerar_pool()

    print(f"🧠 Executando Markov-Ensemble ({MAX_TENTATIVAS} iterações)...")

    for _ in range(MAX_TENTATIVAS):
        if len(candidatos) >= 5000: break
        
        jogo = gerar_jogo(pool)
        key = tuple(jogo)
        if key in vistos: continue
        vistos.add(key)

        score = calcular_score_ensemble_markov(jogo, base_scores, rec_scores, fator, ultimo, hist_recente)
        candidatos.append({"nums": jogo, "score": score})

    candidatos.sort(key=lambda x: x["score"], reverse=True)
    finais = []

    for cand in candidatos:
        nums = cand["nums"]
        # Diversidade v11.5: Mantendo distância 9
        if any(len(set(nums) ^ set(f["nums"])) < 9 for f in finais):
            continue
        finais.append(cand)
        if len(finais) == QTD_FINAL: break

    print("\n🏆 RESULTADO MARKOV-ENSEMBLE v11.5:")
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
            "metricas": {"score_markov_ensemble": round(float(p["score"]), 6)}
        })

    supabase.table("palpites_validos").delete().eq("data_referencia", hoje).eq("concurso_referencia", concurso_ref).execute()
    supabase.table("palpites_validos").insert(payload).execute()
    print(f"\n✅ Pipeline v11.5 finalizado.")

if __name__ == "__main__":
    main()
