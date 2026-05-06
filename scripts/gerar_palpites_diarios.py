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
MAX_TENTATIVAS = 60000
VERSAO = "v10.5-bayes-conditional"

def gerar_pool():
    return list(range(1, 26))

def gerar_jogo(pool):
    return sorted(random.sample(pool, 15))

def serializar_numeros(nums):
    return json.dumps(nums)

def calcular_metricas(nums):
    pares = sum(n % 2 == 0 for n in nums)
    soma = sum(nums)
    linhas = [
        sum(1 for n in nums if 1 <= n <= 5),
        sum(1 for n in nums if 6 <= n <= 10),
        sum(1 for n in nums if 11 <= n <= 15),
        sum(1 for n in nums if 16 <= n <= 20),
        sum(1 for n in nums if 21 <= n <= 25)
    ]
    return pares, soma, linhas

def score_validacao(nums):
    pares, soma, linhas = calcular_metricas(nums)
    score = 1.0
    if pares < 7 or pares > 9: score *= 0.90 # Faixa ideal da Lotofácil
    if soma < 170 or soma > 215: score *= 0.85
    if max(linhas) > 5: score *= 0.80
    return score

# --- LÓGICA BAYESIANA v10.5 ---
def calcular_score_bayesiano(nums, base_scores):
    """
    Avalia a força da combinação baseada na co-ocorrência 
    estatística (P(A|B)) simplificada.
    """
    if not base_scores: return 1.0
    
    # Extraímos a força média das dezenas do jogo atual baseada no histórico
    scores_presentes = [base_scores.get(tuple([n]), 0.5) for n in nums]
    prob_posterior = np.mean(scores_presentes)
    
    return float(prob_posterior)

def calcular_score_final(nums, base_scores, rec_scores, fator, ultimo_concurso):
    chave = tuple(nums)
    
    # Scores baseados nos serviços de IA
    media_base = np.mean(list(base_scores.values())) if base_scores else 0.5
    base = base_scores.get(chave, media_base)
    
    # Adição do componente Bayesiano v10.5
    bayes = calcular_score_bayesiano(nums, base_scores)
    
    score = (base * 0.40) + (bayes * 0.60) # Bayes tem peso maior nesta versão

    repetidos = len(set(nums) & set(ultimo_concurso))
    if repetidos >= 11 or repetidos <= 7:
        score *= 0.70
    elif repetidos == 9:
        score *= 1.10 # Bônus para a média matemática de repetição (9)

    score *= score_validacao(nums)
    score *= fator
    score *= (1 + np.random.normal(0, 0.01)) # Reduzi o ruído para v10.5
    
    return max(score, 0.01)

def estrutura_linhas(nums):
    return tuple(calcular_metricas(nums)[2])

def diversidade_ok(jogo, selecionados):
    for s in selecionados:
        distancia = len(set(jogo) ^ set(s))
        if distancia < 8: # Aumentei a exigência de diversidade
            return False
    return True

def main():
    supabase = get_supabase()
    
    # Garante fuso de Brasília
    fuso = pytz.timezone('America/Sao_Paulo')
    hoje = datetime.now(fuso).date().isoformat()

    print(f"\n🚀 Gerador {VERSAO} iniciado em {hoje}")

    # Busca último concurso com blindagem de tipo
    res = supabase.table("lotofacil_concursos").select("concurso,dezenas").order("concurso", desc=True).limit(1).execute().data[0]
    concurso_base = int(str(res["concurso"]).strip())
    concurso_ref = concurso_base + 1
    
    dezenas = res["dezenas"]
    if isinstance(dezenas, str):
        ultimo = json.loads(dezenas)
        if isinstance(ultimo, str): ultimo = json.loads(ultimo)
    else:
        ultimo = dezenas
    ultimo = [int(x) for x in ultimo]

    print(f"📌 Gerando para concurso {concurso_ref} | Baseado no {concurso_base}")

    fator = obter_fator_aprendizado_global()["fator"]
    base_scores, rec_scores = calcular_score_combinacoes_reais()

    pool = gerar_pool()
    candidatos = []
    vistos = set()

    print(f"🧠 Calculando {MAX_TENTATIVAS} combinações com Bayes Condicional...")

    for _ in range(MAX_TENTATIVAS):
        if len(candidatos) >= 4000: break # Aumentei o pool de candidatos
        
        jogo = gerar_jogo(pool)
        key = tuple(jogo)
        if key in vistos: continue
        vistos.add(key)

        score = calcular_score_final(jogo, base_scores, rec_scores, fator, ultimo)
        candidatos.append({"nums": jogo, "score": score})

    candidatos.sort(key=lambda x: x["score"], reverse=True)
    
    finais = []
    freq_global = Counter()
    estruturas = set()

    for cand in candidatos:
        nums = cand["nums"]
        est = estrutura_linhas(nums)
        
        if est in estruturas: continue
        
        # Penalidade por repetição excessiva de números entre os 7 jogos
        penalidade = 1.0
        for n in nums:
            if freq_global[n] >= 4: penalidade *= 0.90

        cand["score"] *= penalidade

        if diversidade_ok(nums, [x["nums"] for x in finais]):
            finais.append(cand)
            estruturas.add(est)
            for n in nums: freq_global[n] += 1
        
        if len(finais) == QTD_FINAL: break

    print("\n🏆 TOP 7 SELECIONADOS (v10.5):")
    payload = []
    for i, p in enumerate(finais, start=1):
        print(f"{i}º | score={p['score']:.6f} | {p['nums']}")
        pares, soma, _ = calcular_metricas(p["nums"])
        
        payload.append({
            "data_referencia": hoje,
            "concurso_referencia": concurso_ref,
            "indice_palpite": i,
            "tipo": "fixo" if i == 1 else "estatistico",
            "numeros": json.dumps(p["nums"]),
            "pares": pares,
            "impares": 15 - pares,
            "soma_total": soma,
            "acertos": None,
            "processado": False,
            "conferido": False,
            "versao_gerador": VERSAO,
            "metricas": {"score_bayes": round(float(p["score"]), 6)}
        })

    # Limpeza e Salvamento
    supabase.table("palpites_validos").delete().eq("data_referencia", hoje).eq("concurso_referencia", concurso_ref).execute()
    supabase.table("palpites_validos").insert(payload).execute()
    print(f"\n✅ v10.5 finalizada. {len(payload)} palpites salvos.")

if __name__ == "__main__":
    main()
