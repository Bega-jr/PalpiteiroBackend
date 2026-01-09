import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.append(str(BASE_DIR))

from app.services.supabase_service import get_supabase
from app.services.estatisticas_service import (
    calcular_medias_recentes,
    obter_estatisticas_com_score,
    obter_top_listas
)

def calcular_ciclo_historico_seguro(historico):
    if not historico:
        return sorted(list(range(1, 26))), 1

    todos_25 = set(range(1, 26))
    sorteados_no_ciclo = set()
    contador_ciclos = 1
    
    # Identifica o último sorteio para auditoria
    ultimo_sorteio_real = set(historico[-1]["numeros"])

    for concurso in historico:
        sorteados_no_ciclo.update(concurso["numeros"])
        if sorteados_no_ciclo == todos_25:
            sorteados_no_ciclo = set()
            contador_ciclos += 1

    faltam = sorted(todos_25 - sorteados_no_ciclo)
    
    # TRAVA DE SEGURANÇA: Se o número saiu no último concurso, ele DEVE ser removido de 'faltam'
    # Isso corrige bugs de dessincronização de cache do banco
    faltam = [n for n in faltam if n not in ultimo_sorteio_real]
    
    if not faltam:
        faltam = sorted(list(range(1, 26)))
        
    return sorted(faltam), contador_ciclos

def main():
    supabase = get_supabase()
    print("🚀 Processamento Diário - Verificação de Ciclo 2026")

    try:
        # Força busca sem cache para garantir o último concurso
        historico = carregar_historico() 
        ultimo_conc_data = historico[-1]
        
        concurso_n = ultimo_conc_data["concurso"]
        # Busca a data real do último concurso para o payload
        data_res = supabase.table("lotofacil_concursos").select("data").eq("concurso", concurso_n).single().execute()
        data_ref = data_res.data["data"]

        df_scores = obter_estatisticas_com_score()
        medias = calcular_medias_recentes()
        listas = obter_top_listas(df_scores)

        # Cálculo com a trava de segurança para o número 25
        numeros_faltantes, num_ciclo = calcular_ciclo_historico_seguro(historico)

        payload_diario = {
            "data_referencia": data_ref,
            "concurso": int(concurso_n),
            "numero_ciclo": int(num_ciclo),
            "numeros_quentes": listas.get("numeros_quentes", []),
            "numeros_frios": listas.get("numeros_frios", []),
            "numeros_atrasados": numeros_faltantes,
            "atrasados_ranking": listas.get("atrasados_ranking", []),
            "media_soma": float(medias.get("soma_media", 0)),
            "media_pares": float(medias.get("pares_media", 0)),
            "media_impares": float(medias.get("impares_media", 0)),
            "media_primos": float(medias.get("primos_media", 0)),
            "sequencias_comuns": [3, 4]
        }

        # Limpa e Insere
        supabase.table("estatisticas_diarias_v2").delete().eq("data_referencia", data_ref).execute()
        supabase.table("estatisticas_diarias_v2").insert(payload_diario).execute()
        
        print(f"✅ Sucesso! Concurso {concurso_n} processado.")
        print(f"🎯 Ciclo {num_ciclo} | Faltantes reais: {numeros_faltantes}")

    except Exception as e:
        print(f"❌ Erro: {e}")

if __name__ == "__main__":
    main()

if __name__ == "__main__":
    main()
