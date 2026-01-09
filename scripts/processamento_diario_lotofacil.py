import sys
from pathlib import Path

# Configuração de diretório base
BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.append(str(BASE_DIR))

from app.services.supabase_service import get_supabase
from app.services.estatisticas_service import (
    calcular_medias_recentes,
    obter_estatisticas_com_score,
    obter_top_listas,
    carregar_historico  # Certifique-se que esta função no service usa a paginação (while loop)
)

def calcular_ciclo_historico_completo(historico):
    """Calcula o ciclo percorrendo do concurso 1 ao atual."""
    todos_25 = set(range(1, 26))
    sorteados_no_ciclo = set()
    numero_do_ciclo = 1

    for conc in historico:
        sorteados_no_ciclo.update(conc["numeros"])
        if sorteados_no_ciclo == todos_25:
            sorteados_no_ciclo = set()
            numero_do_ciclo += 1

    faltam = sorted(todos_25 - sorteados_no_ciclo)
    if not faltam:
        faltam = sorted(list(range(1, 26)))
        
    return faltam, numero_do_ciclo

def main():
    supabase = get_supabase()
    print("🚀 Iniciando Processamento Completo 2026")

    try:
        # 1. Carrega histórico TOTAL
        historico = carregar_historico()
        ultimo_sorteio = historico[-1] 
        
        concurso_atual = ultimo_sorteio["concurso"]
        data_atual = ultimo_sorteio["data"]
        dezenas_hoje = set(ultimo_sorteio["numeros"])

        print(f"✅ Sucesso ao carregar histórico!")
        print(f"📌 Concurso Identificado: {concurso_atual}")
        print(f"📅 Data Identificada: {data_atual}")
        print(f"🔢 Dezenas Sorteadas: {sorted(list(dezenas_hoje))}")

        # 2. Gera estatísticas baseadas no histórico completo
        df_scores = obter_estatisticas_com_score()
        medias = calcular_medias_recentes()

        # 3. AJUSTE DE SEGURANÇA: Zera o atraso dos números que saíram hoje (ex: número 25)
        for num in dezenas_hoje:
            df_scores.loc[df_scores['numero'] == num, 'atraso'] = 0
        
        # 4. Rankings e Ciclo (Calculado com histórico completo)
        listas = obter_top_listas(df_scores)
        numeros_faltantes, ciclo_contagem = calcular_ciclo_historico_completo(historico)

        # 5. Payload para estatisticas_diarias_v2
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

        # 6. Salva na Tabela Diária
        # Limpa registros da mesma data ou concurso para evitar duplicidade
        supabase.table("estatisticas_diarias_v2").delete().eq("data_referencia", data_atual).execute()
        supabase.table("estatisticas_diarias_v2").insert(payload_diario).execute()

        # 7. Salva Estatísticas Individuais (estatisticas_numeros)
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

        print(f"🏁 Finalizado com sucesso!")
        print(f"🎯 Ciclo {ciclo_contagem} | Faltam: {len(numeros_faltantes)} números")

    except Exception as e:
        print(f"❌ Erro Crítico: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
