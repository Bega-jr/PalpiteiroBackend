import sys
import json
import random
import logging
from pathlib import Path
from datetime import datetime

# Configuração de Logs
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.append(str(BASE_DIR))

from app.services.supabase_service import get_supabase
from app.services.aprendizado_service_v3 import obter_fator_aprendizado_global, aplicar_fator_aprendizado
from app.services.estatisticas_combinacao_v3 import calcular_score_combinacoes_reais, extrair_metricas_jogo

# ======================================================
# Configurações Flexíveis
# ======================================================
QTD_PALPITES = 7
VERSAO_GERADOR = "v3.9.2-auto-adjust"
MAX_CICLOS_GERACAO = 60000 
SIMILARIDADE_MAXIMA = 13 

# Parâmetros Base
SOMA_MIN, SOMA_MAX = 150, 230 # Levemente expandido
PARES_MIN, PARES_MAX = 4, 11  # Levemente expandido
SEQ_MAX_BASE = 5
SCORE_MIN_BASE = 0.05 # Reduzido para aumentar vazão inicial

def calcular_metricas_base(nums):
    pares = sum(1 for n in nums if n % 2 == 0)
    return pares, 15 - pares, sum(nums)

def validar_completo(nums, scores, score_min, ultimos, fator, seq_max_tol):
    # 1. Filtros Matemáticos
    pares, _, soma = calcular_metricas_base(nums)
    if not (SOMA_MIN <= soma <= SOMA_MAX): return False, 0.0
    if not (PARES_MIN <= pares <= PARES_MAX): return False, 0.0
    
    # 2. Sequência (Usando tolerância dinâmica)
    atual = seq = 1
    for i in range(1, 15):
        if nums[i] == nums[i - 1] + 1:
            atual += 1
            seq = max(seq, atual)
        else:
            atual = 1
    if seq > seq_max_tol: return False, 0.0

    # 3. Repetição
    repetidos = len(set(nums) & set(ultimos))
    if not (7 <= repetidos <= 12): return False, 0.0

    # 4. Score
    m = extrair_metricas_jogo(nums)
    chave = (round(m["soma"] / 10) * 10, m["pares"], m["primos"], tuple(m["linhas"]))
    score_final = aplicar_fator_aprendizado(scores.get(chave, 0), fator)

    return (score_final >= score_min), score_final

def main():
    supabase = get_supabase()
    hoje = datetime.now().date().isoformat()
    
    try:
        res_con = supabase.table("lotofacil_concursos").select("concurso, dezenas").order("concurso", desc=True).limit(1).execute()
        concurso_ref = res_con.data[0]["concurso"]
        ultimos = list(map(int, res_con.data[0]["dezenas"]))
        
        # Aumentamos para 23 dezenas para dar mais "espaço" ao algoritmo
        res_pool = supabase.table("estatisticas_numeros").select("numero").order("score", desc=True).limit(23).execute()
        pool = [r["numero"] for r in res_pool.data]
    except: return

    fator = obter_fator_aprendizado_global().get("fator", 1.0)
    scores = calcular_score_combinacoes_reais()
    
    candidatos = []
    usados = set()
    
    # Parâmetros de ajuste dinâmico
    current_score_min = SCORE_MIN_BASE
    current_seq_max = SEQ_MAX_BASE

    print(f"🚀 Iniciando busca (Pool: 23, Fator: {fator})")

    for ciclo in range(MAX_CICLOS_GERACAO):
        # A cada 15k tentativas sem sucesso, relaxa os filtros
        if ciclo > 0 and ciclo % 15000 == 0 and len(candidatos) < QTD_PALPITES:
            current_score_min *= 0.5
            current_seq_max += 1
            print(f"⚠️ Relaxando filtros: Score Min > {current_score_min:.4f}, Seq Max > {current_seq_max}")

        nums = sorted(random.sample(pool, 15))
        if tuple(nums) in usados: continue

        valido, s_final = validar_completo(nums, scores, current_score_min, ultimos, fator, current_seq_max)
        
        if valido:
            if any(len(set(nums) & set(ex["numeros"])) > SIMILARIDADE_MAXIMA for ex in candidatos):
                continue
            usados.add(tuple(nums))
            candidatos.append({"numeros": nums, "score": s_final})

        if len(candidatos) >= QTD_PALPITES: break

    if not candidatos:
        print("❌ Critérios restritivos demais mesmo após relaxamento.")
        return

    ranking = sorted(candidatos, key=lambda x: x["score"], reverse=True)
    registros = []
    
    print(f"\n✅ Sucesso: {len(ranking)} palpites gerados em {ciclo} ciclos.")
    
    for i, r in enumerate(ranking, 1):
        p, imp, soma = calcular_metricas_base(r["numeros"])
        registros.append({
            "data_referencia": hoje,
            "concurso_referencia": concurso_ref,
            "indice_palpite": i,
            "tipo": "estatistico",
            "numeros": json.dumps(r["numeros"]),
            "pares": p, "impares": imp, "soma_total": soma,
            "metricas": json.dumps({"versao": VERSAO_GERADOR, "score": r["score"]})
        })

    supabase.table("palpites_validos").delete().eq("concurso_referencia", concurso_ref).execute()
    supabase.table("palpites_validos").insert(registros).execute()

if __name__ == "__main__":
    main()

