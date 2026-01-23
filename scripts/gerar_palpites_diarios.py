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

# Configurações para 2026
QTD_PALPITES = 7
VERSAO_GERADOR = "v7.2-resilient-pool-2026"

def obter_metricas_completas(nums):
    pares = sum(1 for n in nums if n % 2 == 0)
    soma = sum(nums)
    linhas = [0] * 5
    for n in nums:
        linhas[(n - 1) // 5] += 1
    return {"pares": pares, "soma": soma, "linhas": linhas}

def main():
    supabase = get_supabase()
    hoje = datetime.now().date().isoformat()
    
    # 1. SETUP DE DADOS
    try:
        # Busca último concurso para regra de repetição
        res_con = supabase.table("lotofacil_concursos").select("concurso, dezenas").order("concurso", desc=True).limit(1).execute()
        concurso_ref = res_con.data[0]["concurso"]
        ultimos = list(map(int, res_con.data[0]["dezenas"]))
        
        # BUSCA DE POOL (Tratamento para View com múltiplos registros)
        # Buscamos um limite alto para garantir que pegamos todos os números cadastrados
        res_pool = supabase.table("estatisticas_numeros").select("numero, score").execute()
        
        # Deduplicação: Garante apenas 1 registro por número (o de maior score)
        dict_pool = {}
        for r in res_pool.data:
            num = int(r["numero"])
            score = float(r["score"])
            if num not in dict_pool or score > dict_pool[num]:
                dict_pool[num] = score
        
        # Ordena e pega os 25 melhores números únicos
        sorted_pool = sorted(dict_pool.items(), key=lambda x: x[1], reverse=True)
        pool = sorted([item[0] for item in sorted_pool[:25]])
        
        if len(pool) < 15:
            logging.error(f"❌ Erro Crítico: Apenas {len(pool)} dezenas únicas encontradas. Verifique a tabela estatisticas_numeros.")
            return
            
        print(f"🎱 Pool Processado em 2026: {len(pool)} dezenas únicas prontas.")
            
    except Exception as e:
        logging.error(f"❌ Erro ao carregar dados do Supabase: {e}")
        return

    fator = obter_fator_aprendizado_global().get("fator", 1.0)
    # Aprende com os últimos 1000 resultados oficiais (Base Estatística Sólida)
    scores_db = calcular_score_combinacoes_reais(1000)

    print(f"🚀 Iniciando Geração Adaptativa v7.2 [Concurso Ref: {concurso_ref}]")

    candidatos = []
    usados = set()

    # Hierarquia de 5 a 0 (Prioridade para Padrões de Elite do Histórico)
    for nivel in range(5, -1, -1):
        if len(candidatos) >= QTD_PALPITES: break
        
        print(f"  🔍 Tentando Nível {nivel}...")
        tentativas = 40000 if nivel == 5 else 20000
        
        for _ in range(tentativas):
            if len(candidatos) >= QTD_PALPITES: break
            
            # Garante 15 números únicos do pool limpo
            nums = sorted(random.sample(pool, 15))
            t_nums = tuple(nums)
            if t_nums in usados: continue
            
            m = obter_metricas_completas(nums)
            metr_adv = extrair_metricas_jogo(nums)
            chave = (round(metr_adv["soma"] / 10) * 10, metr_adv["pares"], metr_adv["primos"], tuple(metr_adv["linhas"]))
            
            score_base = scores_db.get(chave, 0)
            score_final = aplicar_fator_aprendizado(score_base, fator)
            
            valido = True
            
            # --- REGRAS POR NÍVEL ---
            if nivel == 5:
                # MODO ELITE: Padrão deve ter ocorrido no histórico real
                if score_base == 0: valido = False
                if valido and not all(1 <= x <= 5 for x in m["linhas"]): valido = False
                if valido and score_final < 0.05: valido = False

            elif nivel >= 4:
                if not all(1 <= x <= 5 for x in m["linhas"]): valido = False
                if valido and not (155 <= m["soma"] <= 225): valido = False
            
            elif nivel >= 3:
                if not (160 <= m["soma"] <= 220) or not (6 <= m["pares"] <= 9): valido = False
                
            elif nivel >= 2:
                rep = len(set(nums) & set(ultimos))
                if not (8 <= rep <= 11): valido = False
                
            elif nivel >= 1:
                if score_final < 0.001: valido = False

            if valido:
                # Evita jogos muito similares entre os palpites do dia
                if any(len(set(nums) & set(ex["nums"])) > 13 for ex in candidatos): 
                    continue
                
                candidatos.append({
                    "nums": nums, 
                    "score": score_final, 
                    "m": m, 
                    "nivel": nivel
                })
                usados.add(t_nums)

    if not candidatos:
        logging.error("❌ Falha crítica: Nenhuma combinação gerada.")
        return

    # Ranking final por Score
    ranking = sorted(candidatos, key=lambda x: x["score"], reverse=True)[:QTD_PALPITES]
    registros = []
    
    print("\n🏆 RANKING FINAL (Geração 2026):")
    for idx, r in enumerate(ranking, 1):
        print(f"{idx}º | Nível {r['nivel']} | Score {round(r['score'], 5)} | {r['nums']}")
        
        registros.append({
            "data_referencia": hoje,
            "concurso_referencia": concurso_ref,
            "indice_palpite": idx,
            "tipo": "elite" if r['nivel'] == 5 else "estatistico",
            "numeros": json.dumps(r["nums"]),
            "pares": r["m"]["pares"],
            "impares": 15 - r["m"]["pares"],
            "soma_total": r["m"]["soma"],
            "metricas": json.dumps({
                "v": VERSAO_GERADOR,
                "origem": f"Nivel {r['nivel']}",
                "score": r["score"]
            })
        })

    # Persistência no Supabase
    try:
        supabase.table("palpites_validos").delete().eq("concurso_referencia", concurso_ref).execute()
        if registros:
            supabase.table("palpites_validos").insert(registros).execute()
            print(f"\n✅ Sucesso: {len(registros)} palpites salvos no Supabase.")
    except Exception as e:
        logging.error(f"❌ Erro ao persistir dados: {e}")

if __name__ == "__main__":
    main()



