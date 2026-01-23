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
VERSAO_GERADOR = "v7.0-elite-cascade-2026"

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
        res_con = supabase.table("lotofacil_concursos").select("concurso, dezenas").order("concurso", desc=True).limit(1).execute()
        concurso_ref = res_con.data[0]["concurso"]
        ultimos = list(map(int, res_con.data[0]["dezenas"]))
        
        # Pool Completo de 25 dezenas para permitir que os padrões de elite sejam encontrados
        res_pool = supabase.table("estatisticas_numeros").select("numero").order("score", desc=True).limit(25).execute()
        pool = [r["numero"] for r in res_pool.data]
    except Exception as e:
        logging.error(f"Erro ao carregar dados: {e}")
        return

    fator = obter_fator_aprendizado_global().get("fator", 1.0)
    # Carrega os scores baseados nos últimos 1000 concursos reais
    scores_db = calcular_score_combinacoes_reais(1000)

    print(f"🚀 Iniciando Geração Adaptativa v7.0 [Concurso {concurso_ref}]")

    candidatos = []
    usados = set()

    # Nível 5: MODO ELITE (Apenas padrões de alta frequência do histórico)
    # Nível 4 ao 1: Filtros Adaptativos
    # Nível 0: Segurança Total
    for nivel in range(5, -1, -1):
        if len(candidatos) >= QTD_PALPITES: break
        
        print(f"  🔍 Tentando Nível de Rigidez {nivel}...")
        
        # Aumentamos as tentativas para o Nível Elite para dar tempo de encontrar as chaves
        tentativas = 30000 if nivel == 5 else 15000
        
        for _ in range(tentativas):
            if len(candidatos) >= QTD_PALPITES: break
            
            nums = sorted(random.sample(pool, 15))
            if tuple(nums) in usados: continue
            
            m = obter_metricas_completas(nums)
            metr_adv = extrair_metricas_jogo(nums)
            chave = (round(metr_adv["soma"] / 10) * 10, metr_adv["pares"], metr_adv["primos"], tuple(metr_adv["linhas"]))
            
            score_base = scores_db.get(chave, 0)
            score_final = aplicar_fator_aprendizado(score_base, fator)
            
            valido = True
            
            # --- HIERARQUIA DE REGRAS ---
            if nivel == 5:
                # NÍVEL ELITE: Só aceita padrões que se repetiram no histórico real (score > 0)
                # E que atendam aos requisitos básicos de linha
                if score_base == 0: valido = False
                if valido and not all(1 <= x <= 5 for x in m["linhas"]): valido = False
                if valido and score_final < 0.1: valido = False # Exige um score mínimo de relevância

            if valido and nivel >= 4:
                if not all(1 <= x <= 5 for x in m["linhas"]): valido = False
            
            if valido and nivel >= 3:
                if not (155 <= m["soma"] <= 225) or not (5 <= m["pares"] <= 10): valido = False
                
            if valido and nivel >= 2:
                rep = len(set(nums) & set(ultimos))
                if not (7 <= rep <= 12): valido = False
                
            if valido and nivel >= 1:
                if score_final < 0.005: valido = False

            if valido:
                # Filtro de similaridade (Máximo 13 números repetidos entre os palpites gerados)
                if any(len(set(nums) & set(ex["nums"])) > 13 for ex in candidatos): 
                    continue
                
                candidatos.append({
                    "nums": nums, 
                    "score": score_final, 
                    "m": m, 
                    "nivel": nivel
                })
                usados.add(tuple(nums))

    # 3. PERSISTÊNCIA E RANKING
    if not candidatos:
        logging.error("Falha crítica: Nenhuma combinação gerada.")
        return

    # Ordena pelo Score Final para garantir que os jogos de 'Elite' fiquem no topo
    ranking = sorted(candidatos, key=lambda x: x["score"], reverse=True)[:QTD_PALPITES]
    registros = []
    
    print("\n🏆 PALPITES SELECIONADOS PARA 2026:")
    for idx, r in enumerate(ranking, 1):
        print(f"Palpite {idx} | Nível: {r['nivel']} | Score: {round(r['score'], 5)} | {r['nums']}")
        
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
                "nivel_origem": r["nivel"],
                "score_final": r["score"]
            })
        })

    # Limpeza e Upload
    supabase.table("palpites_validos").delete().eq("concurso_referencia", concurso_ref).execute()
    supabase.table("palpites_validos").insert(registros).execute()
    print(f"\n✅ Finalizado: {len(registros)} palpites persistidos com sucesso.")

if __name__ == "__main__":
    main()





