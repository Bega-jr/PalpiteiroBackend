import sys
import json
import random
import logging
from pathlib import Path
from datetime import datetime

logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.append(str(BASE_DIR))

from app.services.supabase_service import get_supabase
from app.services.aprendizado_service_v3 import obter_fator_aprendizado_global, aplicar_fator_aprendizado
from app.services.estatisticas_combinacao_v3 import calcular_score_combinacoes_reais, extrair_metricas_jogo

# ======================================================
# CONFIGURAÇÕES DE PRIORIDADE (2026)
# ======================================================
QTD_PALPITES = 7
VERSAO_GERADOR = "v5.0-priority-cascade"

def obter_metricas_completas(nums):
    pares = sum(1 for n in nums if n % 2 == 0)
    soma = sum(nums)
    # Distribuição por linhas
    linhas = [0] * 5
    for n in nums:
        linhas[(n - 1) // 5] += 1
    return {"pares": pares, "soma": soma, "linhas": linhas}

def main():
    supabase = get_supabase()
    hoje = datetime.now().date().isoformat()
    
    # 1. SETUP DE DADOS
    res_con = supabase.table("lotofacil_concursos").select("concurso, dezenas").order("concurso", desc=True).limit(1).execute()
    concurso_ref = res_con.data[0]["concurso"]
    ultimos = list(map(int, res_con.data[0]["dezenas"]))
    
    res_pool = supabase.table("estatisticas_numeros").select("numero").order("score", desc=True).limit(23).execute()
    pool = [r["numero"] for r in res_pool.data]
    
    fator = obter_fator_aprendizado_global().get("fator", 1.0)
    scores_db = calcular_score_combinacoes_reais()

    # 2. DEFINIÇÃO DE REGRAS POR PRIORIDADE
    # Se não houver sucesso, removeremos a última regra da lista sucessivamente
    regras_prioridade = [
        {"id": "linhas", "desc": "Distribuição por Linhas (1-5)"},
        {"id": "soma", "desc": "Soma entre 155-225"},
        {"id": "pares", "desc": "Pares entre 5-10"},
        {"id": "repeticao", "desc": "Repetidos do anterior (7-12)"},
        {"id": "score", "desc": "Score Mínimo Evolutivo (>0.01)"}
    ]

    candidatos = []
    tentativas_por_estagio = 15000

    print(f"🚀 Iniciando Cascata de Prioridade [Concurso {concurso_ref}]")

    # Loop de relaxamento: começa com todas as regras, e vai removendo a menos importante
    for i in range(len(regras_prioridade), 0, -1):
        regras_ativas = [r["id"] for r in regras_prioridade[:i]]
        print(f"  🔍 Testando com {i} regras ativas: {regras_ativas}")
        
        candidatos = []
        usados = set()
        
        for _ in range(tentativas_por_estagio):
            nums = sorted(random.sample(pool, 15))
            t_nums = tuple(nums)
            if t_nums in usados: continue
            
            m = obter_metricas_completas(nums)
            valido = True
            
            # Execução das validações baseada na prioridade ativa
            if "linhas" in regras_ativas:
                if not all(1 <= x <= 5 for x in m["linhas"]): valido = False
            if valido and "soma" in regras_ativas:
                if not (155 <= m["soma"] <= 225): valido = False
            if valido and "pares" in regras_ativas:
                if not (5 <= m["pares"] <= 10): valido = False
            if valido and "repeticao" in regras_ativas:
                rep = len(set(nums) & set(ultimos))
                if not (7 <= rep <= 12): valido = False
            if valido and "score" in regras_ativas:
                metr_adv = extrair_metricas_jogo(nums)
                chave = (round(metr_adv["soma"] / 10) * 10, metr_adv["pares"], metr_adv["primos"], tuple(metr_adv["linhas"]))
                score = aplicar_fator_aprendizado(scores_db.get(chave, 0), fator)
                if score < 0.01: valido = False
            else:
                score = 0.0001 # Fallback para ordenação se o filtro de score estiver desativado

            if valido:
                # Diversidade (Sempre ativa para evitar jogos iguais)
                if any(len(set(nums) & set(ex["nums"])) > 13 for ex in candidatos): continue
                candidatos.append({"nums": nums, "score": score, "metricas": m})
                usados.add(t_nums)
            
            if len(candidatos) >= QTD_PALPITES: break
        
        if len(candidatos) >= QTD_PALPITES:
            print(f"  ✅ Sucesso no nível {i}!")
            break

    # 3. PERSISTÊNCIA DOS DADOS
    if not candidatos:
        print("❌ Erro fatal: impossível gerar palpites mesmo sem regras.")
        return

    ranking = sorted(candidatos, key=lambda x: x["score"], reverse=True)
    registros = []
    for idx, r in enumerate(ranking, 1):
        registros.append({
            "data_referencia": hoje,
            "concurso_referencia": concurso_ref,
            "indice_palpite": idx,
            "tipo": "estatistico",
            "numeros": json.dumps(r["nums"]),
            "pares": r["metricas"]["pares"],
            "impares": 15 - r["metricas"]["pares"],
            "soma_total": r["metricas"]["soma"],
            "metricas": json.dumps({"v": VERSAO_GERADOR, "rules_level": i, "score": r["score"]})
        })

    # Limpeza e Insert Seguro
    supabase.table("palpites_validos").delete().eq("concurso_referencia", concurso_ref).execute()
    if registros:
        supabase.table("palpites_validos").insert(registros).execute()
        print(f"🏆 {len(registros)} palpites salvos com sucesso.")

if __name__ == "__main__":
    main()



