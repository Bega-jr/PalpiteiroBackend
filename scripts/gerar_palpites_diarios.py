import sys
import json
import random
import logging
from pathlib import Path
from datetime import datetime

# Configuração de Logs
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')

# ======================================================
# Setup
# ======================================================
BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.append(str(BASE_DIR))

try:
    from app.services.supabase_service import get_supabase
    from app.services.aprendizado_service_v3 import (
        obter_fator_aprendizado_global,
        aplicar_fator_aprendizado
    )
    from app.services.estatisticas_combinacao_v3 import (
        calcular_score_combinacoes_reais,
        extrair_metricas_jogo
    )
except ImportError as e:
    logging.error(f"Erro ao importar serviços: {e}")
    sys.exit(1)

# ======================================================
# Configurações Otimizadas (Dados para 2026)
# ======================================================
QTD_PALPITES = 7
VERSAO_GERADOR = "v3.9.1-pro-diversity"
MAX_TENTATIVAS_PALPITE = 15000
MAX_CICLOS_GERACAO = 50000
SIMILARIDADE_MAXIMA = 12 

SOMA_MIN, SOMA_MAX = 155, 225
PARES_MIN, PARES_MAX = 5, 10
SEQ_MAX = 5
REPET_MIN, REPET_MAX = 7, 12
LINHA_MIN, LINHA_MAX = 1, 5
SCORE_MIN_BASE = 0.1

# ======================================================
# Funções Auxiliares de Alta Performance
# ======================================================
def calcular_metricas_base(nums):
    pares = sum(1 for n in nums if n % 2 == 0)
    soma = sum(nums)
    return pares, 15 - pares, soma

def validar_sequencia_rapida(nums):
    atual = seq = 1
    for i in range(1, 15):
        if nums[i] == nums[i - 1] + 1:
            atual += 1
            if atual > SEQ_MAX: return False
        else:
            atual = 1
    return True

def validar_linhas_rapido(nums):
    contagem = [0, 0, 0, 0, 0]
    for n in nums:
        idx = (n - 1) // 5
        contagem[idx] += 1
    
    for c in contagem:
        if not (LINHA_MIN <= c <= LINHA_MAX):
            return False
    return True

def validar_completo(nums, scores, score_min, ultimos, fator):
    """
    Retorna (bool, float): (Status da validade, Score final)
    Importante: Sempre retorna dois valores para evitar erro de desempacotamento.
    """
    # 1. Filtros Matemáticos Rápidos
    pares, _, soma = calcular_metricas_base(nums)
    if not (SOMA_MIN <= soma <= SOMA_MAX): return False, 0.0
    if not (PARES_MIN <= pares <= PARES_MAX): return False, 0.0
    
    # 2. Filtros de Padrão
    if not validar_sequencia_rapida(nums): return False, 0.0
    if not validar_linhas_rapido(nums): return False, 0.0

    # 3. Filtro de Repetição do Último Concurso
    repetidos = len(set(nums) & set(ultimos))
    if not (REPET_MIN <= repetidos <= REPET_MAX): return False, 0.0

    # 4. Cálculo de Score
    m = extrair_metricas_jogo(nums)
    chave = (round(m["soma"] / 10) * 10, m["pares"], m["primos"], tuple(m["linhas"]))
    
    score_base = scores.get(chave, 0)
    score_final = aplicar_fator_aprendizado(score_base, fator)

    return (score_final >= score_min), score_final

# ======================================================
# Lógica Principal
# ======================================================
def main():
    supabase = get_supabase()
    hoje = datetime.now().date().isoformat()

    print(f"\n🚀 Gerador {VERSAO_GERADOR} iniciado em 2026")

    try:
        res_concurso = supabase.table("lotofacil_concursos").select("concurso, dezenas").order("concurso", desc=True).limit(1).execute()
        if not res_concurso.data: raise ValueError("Banco de dados vazio.")
        
        concurso_ref = res_concurso.data[0]["concurso"]
        ultimos = list(map(int, res_concurso.data[0]["dezenas"]))

        # Pool expandido para 22 para maior diversidade
        res_pool = supabase.table("estatisticas_numeros").select("numero").order("score", desc=True).limit(22).execute()
        pool = [r["numero"] for r in res_pool.data]
        
    except Exception as e:
        logging.error(f"Erro nos dados: {e}")
        return

    fator = obter_fator_aprendizado_global().get("fator", 1.0)
    scores = calcular_score_combinacoes_reais()
    
    print(f"🧠 Fator: {fator} | 🎱 Pool: {len(pool)} dezenas | 📊 Ref: Concurso {concurso_ref}")

    # Limpeza de palpites prévios do mesmo concurso
    supabase.table("palpites_validos").delete().eq("concurso_referencia", concurso_ref).execute()

    candidatos = []
    usados = set()
    ciclos = 0

    while len(candidatos) < QTD_PALPITES and ciclos < MAX_CICLOS_GERACAO:
        ciclos += 1
        nums = sorted(random.sample(pool, 15))
        t_nums = tuple(nums)

        if t_nums in usados: continue

        # Agora desempacota corretamente os 2 valores
        e_valido, s_final = validar_completo(nums, scores, SCORE_MIN_BASE, ultimos, fator)
        
        if e_valido:
            # Filtro de similaridade entre os palpites gerados
            if any(len(set(nums) & set(ex["numeros"])) > SIMILARIDADE_MAXIMA for ex in candidatos):
                continue

            usados.add(t_nums)
            candidatos.append({"numeros": nums, "score": s_final})

        if ciclos % 10000 == 0:
            print(f"⏳ Tentativas: {ciclos} | Sucessos: {len(candidatos)}")

    if not candidatos:
        print("❌ Nenhum palpite gerado com os critérios atuais.")
        return

    # Ordenação por Score decrescente
    ranking = sorted(candidatos, key=lambda x: x["score"], reverse=True)

    print("\n🏆 RANKING FINAL:")
    registros = []
    for i, r in enumerate(ranking, 1):
        nums = r["numeros"]
        p, imp, soma = calcular_metricas_base(nums)
        print(f"{i}º | score={round(r['score'],6)} | {nums}")

        registros.append({
            "data_referencia": hoje,
            "concurso_referencia": concurso_ref,
            "indice_palpite": i,
            "tipo": "fixo" if i == 1 else "estatistico",
            "numeros": json.dumps(nums),
            "pares": p,
            "impares": imp,
            "soma_total": soma,
            "metricas": json.dumps({
                "versao": VERSAO_GERADOR,
                "score_final": r["score"],
                "ciclos": ciclos
            })
        })

    try:
        supabase.table("palpites_validos").insert(registros).execute()
        print(f"\n✅ Processo concluído. {len(registros)} palpites salvos.")
    except Exception as e:
        logging.error(f"Erro ao salvar: {e}")

if __name__ == "__main__":
    main()

