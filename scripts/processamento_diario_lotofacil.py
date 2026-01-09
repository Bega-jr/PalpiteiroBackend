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

def calcular_ciclo_historico_completo(historico):
    """
    Percorre do concurso 1 até o último para identificar o ciclo atual
    e quais dezenas realmente faltam.
    """
    todos_25 = set(range(1, 26))
    sorteados_no_ciclo = set()
    numero_do_ciclo = 1

    # Ordena explicitamente por concurso ascendente para garantir a cronologia
    historico_ordenado = sorted(historico, key=lambda x: x["concurso"])

    for conc in historico_ordenado:
        sorteados_no_ciclo.update(conc["numeros"])
        
        # Se completou as 25 dezenas, fecha o ciclo e inicia o próximo
        if sorteados_no_ciclo == todos_25:
            sorteados_no_ciclo = set()
            numero_do_ciclo += 1

    faltam = sorted(todos_25 - sorteados_no_ciclo)
    
    # Se 'faltam' for vazio, o último concurso fechou o ciclo perfeitamente
    if not faltam:
        faltam = sorted(list(range(1, 26)))
        
    return faltam, numero_do_ciclo

def main():
    supabase = get_supabase()
    print("🚀 Iniciando Processamento Completo 2026")

    try:
        # 1. Carrega histórico TOTAL (com a nova função de paginação)
        historico = carregar_historico()
        ultimo_sorteio = historico[-1] 
        
        concurso_atual = ultimo_sorteio["concurso"]
        data_atual = ultimo_sorteio["data"]
        dezenas_hoje = set(ultimo_sorteio["numeros"])

        # LOG DE CONFERÊNCIA - Verifique isso no terminal
        print(f"✅ Sucesso ao carregar histórico!")
        print(f"📌 Concurso Identificado: {concurso_atual}")
        print(f"📅 Data Identificada: {data_atual}")
        print(f"🔢 Dezenas: {sorted(list(dezenas_hoje))}")

        if concurso_atual < 3000:
            print("⚠️ AVISO: O script ainda está pegando concursos antigos. Verifique a paginação.")

        # 2. Gera estatísticas baseadas no histórico completo
        df_scores = obter_estatisticas_com_score() # Certifique-se que esta func usa o novo carregar_historico
        medias = calcular_medias_recentes()

        # 3. Força atraso zero para o que saiu hoje
        for num in dezenas_hoje:
            df_scores.loc[df_scores['numero'] == num, 'atraso'] = 0
        
        # 4. Rankings e Ciclo
        listas = obter_top_listas(df_scores)
        numeros_faltantes, ciclo_contagem = calcular_ciclo_historico_completo(historico)

        # 5. Payload
        payload_diario = {
            "data_referencia": data_ref, # Use data_atual obtida do historico[-1]
            "concurso": int(concurso_atual),
            "numero_ciclo": int(ciclo_contagem),
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

        # 6. Delete por concurso/data para garantir limpeza
        supabase.table("estatisticas_diarias_v2").delete().eq("concurso", concurso_atual).execute()
        supabase.table("estatisticas_diarias_v2").insert(payload_diario).execute()

        print(f"🏁 Finalizado! Ciclo {ciclo_contagem} salvo para o concurso {concurso_atual}.")

    except Exception as e:
        print(f"❌ Erro: {e}")

if __name__ == "__main__":
    main()
