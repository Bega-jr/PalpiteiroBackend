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
    print("🚀 Processamento Estruturado Lotofácil 2026")

    try:
        # 1. Carrega histórico (deve retornar todos os concursos do 1 ao mais atual)
        historico = carregar_historico()
        ultimo_sorteio = historico[-1] # Pega o mais recente
        
        dezenas_hoje = set(ultimo_sorteio["numeros"])
        concurso_atual = ultimo_sorteio["concurso"]
        data_atual = ultimo_sorteio["data"]

        print(f"📊 Analisando Concurso {concurso_atual} | Dezenas: {sorted(list(dezenas_hoje))}")

        # 2. Gera estatísticas (Frequência e Scores)
        df_scores = obter_estatisticas_com_score()
        medias = calcular_medias_recentes()

        # ---------------------------------------------------------
        # AJUSTE DE SEGURANÇA: ZERAR ATRASO DOS NÚMEROS QUE SAÍRAM
        # ---------------------------------------------------------
        # Garante que números sorteados hoje tenham atraso 0 no banco
        for num in dezenas_hoje:
            df_scores.loc[df_scores['numero'] == num, 'atraso'] = 0
        
        # 3. Calcula Ciclo e Listas atualizadas
        listas = obter_top_listas(df_scores)
        numeros_faltantes, ciclo_contagem = calcular_ciclo_historico_completo(historico)

        # 4. Monta o Payload para estatisticas_diarias_v2
        payload_diario = {
            "data_referencia": data_atual,
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

        # 5. Salva no Supabase
        # Tabela Diária
        supabase.table("estatisticas_diarias_v2").delete().eq("data_referencia", data_atual).execute()
        supabase.table("estatisticas_diarias_v2").insert(payload_diario).execute()

        # Tabela por Número
        payload_numeros = [
            {
                "data_referencia": data_atual,
                "numero": int(row["numero"]),
                "frequencia": int(row["frequencia"]),
                "atraso": int(row["atraso"]),
                "score": float(row["score"]),
            }
            for _, row in df_scores.iterrows()
        ]
        supabase.table("estatisticas_numeros").delete().eq("data_referencia", data_atual).execute()
        supabase.table("estatisticas_numeros").insert(payload_numeros).execute()

        print(f"✅ Sucesso! Ciclo {ciclo_contagem} atualizado. Faltam: {numeros_faltantes}")

    except Exception as e:
        print(f"❌ Erro no processamento: {str(e)}")

if __name__ == "__main__":
    main()
