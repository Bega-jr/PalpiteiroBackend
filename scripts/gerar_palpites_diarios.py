import sys
import json
import random
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
from scripts.processamento_diario_lotofacil import carregar_historico, extrair_estrutura, buscar_cenario_similar

VERSAO = "v13.5-pro-filters-anti-plagio"
QTD_FINAL = 7
MAX_TENTATIVAS = 100000 # Aumentado para lidar com filtros rigorosos

def calcular_filtros_pro(nums, ultimo_concurso):
    pares = sum(1 for n in nums if n % 2 == 0)
    soma = sum(nums)
    primos = sum(1 for n in nums if n in {2, 3, 5, 7, 11, 13, 17, 19, 23})
    moldura = sum(1 for n in nums if n in {1,2,3,4,5,6,10,11,15,16,20,21,22,23,24,25})
    repetidos = len(set(nums) & set(ultimo_concurso))
    
    # Cálculo de Sequência Max
    seq_max = 1
    atual = 1
    for i in range(len(nums)-1):
        if nums[i+1] == nums[i] + 1:
            atual += 1
            seq_max = max(seq_max, atual)
        else:
            atual = 1
            
    return {
        "pares": pares, "soma": soma, "primos": primos, 
        "moldura": moldura, "repetidos": repetidos, "seq_max": seq_max
    }

def validar_jogo_pro(f):
    """Retorna True se o jogo estiver dentro das zonas estatísticas de elite."""
    if not (165 <= f["soma"] <= 210): return False
    if not (7 <= f["pares"] <= 9): return False
    if not (5 <= f["primos"] <= 6): return False
    if not (9 <= f["moldura"] <= 11): return False
    if not (8 <= f["repetidos"] <= 10): return False
    if f["seq_max"] > 4: return False
    return True

def main():
    supabase = get_supabase()
    fuso = pytz.timezone('America/Sao_Paulo')
    hoje = datetime.now(fuso).date().isoformat()
    
    print(f"🛡️ {VERSAO} | Iniciando Motores...")

    historico = carregar_historico()
    ultimo_real = historico[-1]["numeros"]
    concurso_ref = int(historico[-1]["concurso"]) + 1
    
    # Estatísticas de IA
    base_scores, _ = calcular_score_combinacoes_reais()
    fator_global = obter_fator_aprendizado_global()["fator"]

    candidatos = []
    vistos_historico = set(tuple(sorted(h["numeros"])) for h in historico)
    pool = list(range(1, 26))

    print(f"🧠 Filtrando elite de jogos entre 3.2 milhões de possibilidades...")

    tentativas_validas = 0
    for _ in range(MAX_TENTATIVAS):
        if len(candidatos) >= 5000: break
        
        jogo = sorted(random.sample(pool, 15))
        f = calcular_filtros_pro(jogo, ultimo_real)
        
        # 1. Filtro Anti-Plágio (Nunca sorteado antes)
        if tuple(jogo) in vistos_historico: continue
        
        # 2. Filtros Estatísticos de Elite
        if not validar_jogo_pro(f): continue
        
        tentativas_validas += 1
        
        # 3. Score de IA
        s_base = np.mean([base_scores.get(tuple([n]), 0.5) for n in jogo])
        
        # 4. Match de Memória
        est = extrair_estrutura(jogo)
        mem = buscar_cenario_similar(supabase, est)
        s_memoria = 1.30 if (mem and float(mem.get("score_medio_real", 0)) > 0) else 1.0

        score_final = s_base * s_memoria * fator_global
        candidatos.append({"nums": jogo, "score": score_final, "f": f, "match": (s_memoria > 1)})

    # Estatística de Afunilamento
    # Se 100k tentativas geraram X válidas, podemos estimar o universo real
    estimativa_universo = int((tentativas_validas / MAX_TENTATIVAS) * 3268760)
    print(f"📊 Espaço Amostral Filtrado: ~{estimativa_universo} combinações viáveis.")

    # Seleção Final
    candidatos.sort(key=lambda x: x["score"], reverse=True)
    finais = []
    for cand in candidatos:
        if any(len(set(cand["nums"]) ^ set(f["nums"])) < 10 for f in finais): continue
        finais.append(cand)
        if len(finais) == QTD_FINAL: break

    print(f"\n🏆 TOP 7 PROFISSIONAIS (Concurso {concurso_ref}):")
    payload = []
    for i, p in enumerate(finais, start=1):
        f = p["f"]
        print(f"{i}º | Score: {p['score']:.4f} | {p['nums']} | Soma: {f['soma']} | Primos: {f['primos']}")
        
        payload.append({
            "data_referencia": hoje, "concurso_referencia": concurso_ref, "indice_palpite": i,
            "tipo": "fixo" if i == 1 else "estatistico", "numeros": json.dumps(p["nums"]),
            "pares": f["pares"], "impares": 15 - f["pares"], "soma_total": f["soma"],
            "processado": False, "conferido": False, "versao_gerador": VERSAO,
            "metricas": {
                "score": round(p['score'], 6),
                "universo_estimado": estimativa_universo,
                "memoria_match": p['match'],
                "primos": f["primos"],
                "moldura": f["moldura"]
            }
        })

    # Persistência
    supabase.table("palpites_validos").delete().eq("data_referencia", hoje).eq("concurso_referencia", concurso_ref).execute()
    supabase.table("palpites_validos").upsert(payload).execute()
    print(f"\n✅ v13.5 finalizada. Filtros Pro + Anti-Plágio aplicados.")

if __name__ == "__main__":
    main()



