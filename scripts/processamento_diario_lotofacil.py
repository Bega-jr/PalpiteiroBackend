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
    carregar_historico as carregar_base_service
)

def calcular_ciclo_historico(historico):
    """Calcula quais números faltam e qual o número do ciclo atual desde o início."""
    if not historico:
        return sorted(list(range(1, 26))), 1

    todos_25 = set(range(1, 26))
    sorteados_no_ciclo = set()
    contador_ciclos = 1

    # Percorre cronologicamente para contar os ciclos corretamente
    for concurso in historico:
        sorteados_no_ciclo.update(concurso["numeros"])
        if sorteados_no_ciclo == todos_25:
            sorteados_no_ciclo = set()
            contador_ciclos += 1

    faltam = sorted(todos_25 - sorteados_no_ciclo)
    
    # Se o ciclo fechou no último sorteio, o próximo concurso inicia um novo
    if not faltam:
        faltam = sorted(list(range(1, 26)))
        
    return faltam, contador_ciclos

def salvar_estatisticas_numeros(data_ref, df_scores):
    supabase = get_supabase()
    payload = [
        {
            "data_referencia": data_ref,
            "numero": int(row["numero"]),
            "frequencia": int(row["frequencia"]),
            "atraso": int(row["atraso"]),
            "score": float(row["score"]),
        }
        for _, row in df_scores.iterrows()
    ]
    # Limpa dados da data para evitar duplicados
    supabase.table("estatisticas_numeros").delete().eq("data_referencia", data_ref).execute()
    if payload:
        supabase.table("estatisticas_numeros").insert(payload).execute()

def main():
    supabase = get_supabase()
    print("🚀 Iniciando Processamento Lotofácil 2026")

    try:
        # 1. Obter referência do último concurso sorteado
        ultimo_res = supabase.table("lotofacil_concursos").select("concurso,data").order("concurso", desc=True).limit(1).execute()
        if not ultimo_res.data:
            raise RuntimeError("Nenhum concurso encontrado no banco.")

        ultimo_concurso = ultimo_res.data[0]
        data_ref = ultimo_concurso["data"]
        concurso_n = ultimo_concurso["concurso"]

        # 2. Carregar Histórico e Gerar Estatísticas
        historico = carregar_base_service()
        df_scores = obter_estatisticas_com_score()
        medias = calcular_medias_recentes()
        listas = obter_top_listas(df_scores)

        # 3. Calcular Ciclo e Contador
        numeros_faltantes, num_ciclo = calcular_ciclo_historico(historico)

        # 4. Montar Payload para estatisticas_diarias_v2
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

        # 5. Salvar no Supabase
        print(f"📡 Salvando Concurso {concurso_n} | Ciclo {num_ciclo}")
        
        supabase.table("estatisticas_diarias_v2").delete().eq("data_referencia", data_ref).execute()
        supabase.table("estatisticas_diarias_v2").insert(payload_diario).execute()
        
        salvar_estatisticas_numeros(data_ref, df_scores)
        
        print(f"✅ Processamento concluído: Ciclo {num_ciclo} (Faltam {len(numeros_faltantes)})")

    except Exception as e:
        print(f"❌ Erro Crítico: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    main()
