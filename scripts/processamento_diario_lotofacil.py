import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.append(str(BASE_DIR))

from app.services.supabase_service import get_supabase
from app.services.estatisticas_service import (
    calcular_medias_recentes,
    obter_estatisticas_com_score,
    obter_top_listas,
    carregar_historico
)

def calcular_ciclo_final(historico):
    """Calcula o ciclo garantindo que o último concurso seja respeitado."""
    todos_25 = set(range(1, 26))
    sorteados_no_ciclo = set()
    contador_ciclos = 1
    
    # Ordem cronológica
    for conc in historico:
        sorteados_no_ciclo.update(conc["numeros"])
        if sorteados_no_ciclo == todos_25:
            sorteados_no_ciclo = set()
            contador_ciclos += 1
            
    faltam = sorted(todos_25 - sorteados_no_ciclo)
    return (faltam if faltam else sorted(list(range(1, 26)))), contador_ciclos

def main():
    supabase = get_supabase()
    print("🚀 Processamento Diário Lotofácil 2026")

    try:
        # 1. Carrega o histórico COMPLETO e ATUALIZADO
        historico = carregar_historico()
        ultimo_sorteio = historico[-1]
        dezenas_sorteadas_hoje = set(ultimo_sorteio["numeros"])
        concurso_n = ultimo_sorteio["concurso"]
        data_ref = ultimo_sorteio["data"]

        print(f"📌 Analisando Concurso {concurso_n} - Dezenas: {dezenas_sorteadas_hoje}")

        # 2. Gera estatísticas base
        df_scores = obter_estatisticas_com_score()
        medias = calcular_medias_recentes()
        
        # --- CORREÇÃO DE CONSISTÊNCIA (HARD FIX) ---
        # Se o 25 saiu hoje, o atraso DEVE ser 0 e ele não pode estar no topo do ranking de atraso
        for num in dezenas_sorteadas_hoje:
            df_scores.loc[df_scores['numero'] == num, 'atraso'] = 0
        
        # Recalcula as listas após a correção do atraso
        listas = obter_top_listas(df_scores)
        numeros_faltantes, num_ciclo = calcular_ciclo_final(historico)
        # -------------------------------------------

        payload_diario = {
            "data_referencia": data_ref,
            "concurso": int(concurso_n),
            "numero_ciclo": int(num_ciclo),
            "numeros_quentes": listas["numeros_quentes"],
            "numeros_frios": listas["numeros_frios"],
            "numeros_atrasados": numeros_faltantes,
            "atrasados_ranking": listas["atrasados_ranking"],
            "media_soma": float(medias.get("soma_media", 0)),
            "media_pares": float(medias.get("pares_media", 0)),
            "media_impares": float(medias.get("impares_media", 0)),
            "media_primos": float(medias.get("primos_media", 0)),
            "sequencias_comuns": [3, 4]
        }

        # Salva resultados
        supabase.table("estatisticas_diarias_v2").delete().eq("data_referencia", data_ref).execute()
        supabase.table("estatisticas_diarias_v2").insert(payload_diario).execute()

        # Salva estatísticas individuais
        payload_numeros = [
            {
                "data_referencia": data_ref,
                "numero": int(row["numero"]),
                "frequencia": int(row["frequencia"]),
                "atraso": int(row["atraso"]),
                "score": float(row["score"]),
            }
            for _, row in df_scores.iterrows()
        ]
        supabase.table("estatisticas_numeros").delete().eq("data_referencia", data_ref).execute()
        supabase.table("estatisticas_numeros").insert(payload_numeros).execute()

        print(f"✅ Processado com Sucesso! Ciclo: {num_ciclo} | Faltam: {numeros_faltantes}")

    except Exception as e:
        print(f"❌ Erro: {e}")

if __name__ == "__main__":
    main()
