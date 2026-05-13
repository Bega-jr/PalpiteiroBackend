import sys
import json
import numpy as np

from pathlib import Path
from datetime import datetime

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.append(str(BASE_DIR))

from app.services.supabase_service import get_supabase


VERSAO = "bootstrap-v2.1-feedback-loop"

PRIMOS = {2,3,5,7,11,13,17,19,23}


# ======================================================
# AUX
# ======================================================
def parse_numeros(valor):

    if not valor:
        return []

    if isinstance(valor, list):
        return [int(x) for x in valor]

    if isinstance(valor, str):

        try:
            return [int(x) for x in json.loads(valor)]
        except:
            return []

    return []


def extrair_estrutura(nums):

    linhas_lista = [

        sum(1 for n in nums if 1 <= n <= 5),
        sum(1 for n in nums if 6 <= n <= 10),
        sum(1 for n in nums if 11 <= n <= 15),
        sum(1 for n in nums if 16 <= n <= 20),
        sum(1 for n in nums if 21 <= n <= 25),

    ]

    return {

        "soma_faixa": int(
            round(sum(nums) / 10) * 10
        ),

        "pares": sum(
            1 for n in nums if n % 2 == 0
        ),

        "primos": sum(
            1 for n in nums if n in PRIMOS
        ),

        "linhas": linhas_lista,

        "hash_estrutura": "-".join(
            map(str, linhas_lista)
        )
    }


# ======================================================
# MAIN
# ======================================================
def main():

    supabase = get_supabase()

    print(
        f"🚀 [{VERSAO}] Iniciando Bootstrap de Memória Estrutural"
    )

    historico = supabase.table(
        "lotofacil_concursos"
    ).select(
        "concurso,dezenas"
    ).order(
        "concurso"
    ).execute().data

    print(
        f"📊 Concursos carregados: "
        f"{len(historico)}"
    )

    estruturas = {}
    mapa_resultados = {}

    for row in historico:

        nums = parse_numeros(
            row["dezenas"]
        )

        if not nums:
            continue
            
        mapa_resultados[int(row["concurso"])] = set(nums)

        estrutura = extrair_estrutura(
            nums
        )

        chave = (

            estrutura["soma_faixa"],
            estrutura["pares"],
            estrutura["primos"],
            estrutura["hash_estrutura"]

        )

        if chave not in estruturas:

            estruturas[chave] = {

                "soma_faixa":
                    estrutura["soma_faixa"],

                "pares":
                    estrutura["pares"],

                "primos":
                    estrutura["primos"],

                "linhas":
                    estrutura["linhas"],

                "hash_estrutura":
                    estrutura["hash_estrutura"],

                "vezes_gerado":
                    0
            }

        estruturas[chave][
            "vezes_gerado"
        ] += 1

    payload = []

    agora = datetime.now().isoformat()

    for item in estruturas.values():

        payload.append({

            "soma_faixa":
                item["soma_faixa"],

            "pares":
                item["pares"],

            "primos":
                item["primos"],

            "linhas":
                item["linhas"],

            "hash_estrutura":
                item["hash_estrutura"],

            "vezes_gerado":
                item["vezes_gerado"],

            "acertos_11": 0,
            "acertos_12": 0,
            "acertos_13": 0,
            "acertos_14": 0,
            "acertos_15": 0,

            "score_medio_real": 0,

            "tendencia": 0,
            "saturacao": 0,

            "updated_at":
                agora
        })

    print(
        f"🧠 Estruturas únicas mapeadas: "
        f"{len(payload)}"
    )

    # 🛠️ CORREÇÃO ESTRUTURAL: Clear & Insert para anular erro 42P10
    print("🧹 Limpando tabela memoria_cenarios antes da carga...")
    supabase.table("memoria_cenarios").delete().neq("soma_faixa", -1).execute()
    
    print("📥 Gravando cenários mapeados...")
    # Envia em blocos de 200 para evitar quebras por timeout de payloads gigantescos
    for i in range(0, len(payload), 200):
        supabase.table("memoria_cenarios").insert(payload[i:i+200]).execute()

    print("✅ Fase 1: Memória de cenários atualizada com sucesso.")

    # =====================================================
    # FASE 2: RETROALIMENTAÇÃO COMPLETA (FEEDBACK LOOP)
    # =====================================================
    print("\n🔄 Iniciando Fase 2: Retroalimentação do Ciclo de Aprendizado por Erro...")
    
    todos_palpites = supabase.table("palpites_validos")\
        .select("concurso_referencia,numeros")\
        .order("concurso_referencia").execute().data
        
    if not todos_palpites:
        print("⚠️ Nenhum palpite antigo localizado para retroalimentação.")
        return
        
    palpites_por_concurso = {}
    for p in todos_palpites:
        cc = int(p["concurso_referencia"])
        if cc not in palpites_por_concurso:
            palpites_por_concurso[cc] = []
        palpites_por_concurso[cc].append(parse_numeros(p["numeros"]))
        
    payload_feedback = []
    
    for cc, lista_jogos in palpites_por_concurso.items():
        if cc not in mapa_resultados:
            continue
            
        resultado_real = mapa_resultados[cc]
        acertos_do_concurso = []
        
        for jogo in lista_jogos:
            if not jogo:
                continue
            acertos = len(set(jogo) & resultado_real)
            acertos_do_concurso.append(acertos)
            
        if not acertos_do_concurso:
            continue
            
        media_acertos = float(np.mean(acertos_do_concurso))
        
        if media_acertos < 9.0:
            fator_correcao = 0.92  
        elif media_acertos >= 11.0:
            fator_correcao = 1.05  
        else:
            fator_correcao = 1.00  
            
        payload_feedback.append({
            "concurso_referencia": cc,
            "media_acertos_ia": round(media_acertos, 2),
            "fator_correcao": fator_correcao
        })
        
    if payload_feedback:
        print(f"🧹 Limpando tabela memoria_feedback_loop...")
        supabase.table("memoria_feedback_loop").delete().neq("concurso_referencia", -1).execute()
        
        print(f"📥 Gravando {len(payload_feedback)} registros de aprendizado no Supabase...")
        for i in range(0, len(payload_feedback), 200):
            supabase.table("memoria_feedback_loop").insert(payload_feedback[i:i+200]).execute()
        print("✅ Fase 2 concluída com sucesso! Base de conhecimento viva.")
    else:
        print("ℹ️ Nenhuma correspondência de palpites antigos encontrada.")


if __name__ == "__main__":
    main()

