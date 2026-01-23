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
# Configurações Otimizadas
# ======================================================
QTD_PALPITES = 7
VERSAO_GERADOR = "v3.9-pro-diversity"
MAX_TENTATIVAS_PALPITE = 15000
MAX_CICLOS_GERACAO = 50000
SIMILARIDADE_MAXIMA = 12  # Evita jogos com mais de 12 números repetidos entre si

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
    # Dicionário de faixas otimizado
    contagem = [0, 0, 0, 0, 0]
    for n in nums:
        idx = (n - 1) // 5
        contagem[idx] += 1
    
    for c in contagem:
        if not (LINHA_MIN <= c <= LINHA_MAX):
            return False
    return True

def validar_completo(nums, scores, score_min, ultimos, fator):
    # 1. Filtros Matemáticos Rápidos (Short-circuit)
    pares, _, soma = calcular_metricas_base(nums)
    if not (SOMA_MIN <= soma <= SOMA_MAX): return False
    if not (PARES_MIN <= pares <= PARES_MAX): return False
    
    # 2. Filtros de Padrão (Sequência e Linhas)
    if not validar_sequencia_rapida(nums): return False
    if not validar_linhas_rapido(nums): return False

    # 3. Filtro de Repetição do Último Concurso
    repetidos = len(set(nums) & set(ultimos))
    if not (REPET_MIN <= repetidos <= REPET_MAX): return False

    # 4. Cálculo de Score (Custo Computacional maior, fica por último)
    m = extrair_metricas_jogo(nums)
    chave = (round(m["soma"] / 10) * 10, m["pares"], m["primos"], tuple(m["linhas"]))
    
    score_base = scores.get(chave, 0)
    score_final = aplicar_fator_aprendizado(score_base, fator)

    return score_final >= score_min, score_final

# ======================================================
# Lógica Principal
# ======================================================
def main():
    supabase = get_supabase()
    hoje = datetime.now().date().isoformat()

    print(f"\n🚀 Gerador {VERSAO_GERADOR} iniciado")

    # Busca segura de dados
    try:
        res_concurso = supabase.table("lotofacil_concursos").select("concurso, dezenas").order("concurso", desc=True).limit(1).execute()
        if not res_concurso.data: raise ValueError("Nenhum concurso encontrado no banco.")
        
        concurso_ref = res_concurso.data[0]["concurso"]
        ultimos = list(map(int, res_concurso.data[0]["dezenas"]))

        # Aumento do Pool para 22 números (Melhor diversidade)
        res_pool = supabase.table("estatisticas_numeros").select("numero").order("score", desc=True).limit(22).execute()
        pool = [r["numero"] for r in res_pool.data]
        
    except Exception as e:
        logging.error(f"Erro ao buscar dados iniciais: {e}")
        return

    fator = obter_fator_aprendizado_global().get("fator", 1.0)
    scores = calcular_score_combinacoes_reais()
    
    print(f"🧠 Fator: {fator} | 🎱 Pool: {len(pool)} dezenas | 📊 Ref: Concurso {concurso_ref}")

    # Limpeza de palpites do dia/concurso para evitar duplicidade no banco
    supabase.table("palpites_validos").delete().eq("concurso_referencia", concurso_ref).execute()

    candidatos = []
    usados = set()
    ciclos = 0

    while len(candidatos) < QTD_PALPITES and ciclos < MAX_CICLOS_GERACAO:
        ciclos += 1
        nums = sorted(random.sample(pool, 15))
        t_nums = tuple(nums)

        if t_nums in usados: continue

        e_valido, s_final = validar_completo(nums, scores, SCORE_MIN_BASE, ultimos, fator)
        
        if e_valido:
            # Checagem de Diversidade: Evita que os palpites sejam quase iguais entre si
            if any(len(set(nums) & set(existente["numeros"])) > SIMILARIDADE_MAXIMA for existente in candidatos):
                continue

            usados.add(t_nums)
            candidatos.append({"numeros": nums, "score": s_final})

        if ciclos % 10000 == 0:
            print(f"⏳ Ciclo {ciclos}... Gerados: {len(candidatos)}")

    if not candidatos:
        print("❌ Falha: Nenhum palpite atendeu aos critérios.")
        return

    # Ordenação por Score
    ranking = sorted(candidatos, key=lambda x: x["score"], reverse=True)

    print("\n🏆 RANKING FINAL (DIVERSIFICADO):")
    registros = []
    for i, r in enumerate(ranking, 1):
        nums = r["numeros"]
        p, imp, soma = calcular_metricas_base(nums)
        
        print(f"{i}º | score={round(r['score'],6)} | {nums} | Soma: {soma}")

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
                "repetidos_anterior": len(set(nums) & set(ultimos))
            })
        })

    # Persistência
    try:
        supabase.table("palpites_validos").insert(registros).execute()
        print(f"\n✅ Sucesso: {len(registros)} palpites salvos no Supabase.\n")
    except Exception as e:
        logging.error(f"Erro ao salvar no banco: {e}")

if __name__ == "__main__":
    main()

