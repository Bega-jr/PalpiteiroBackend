import sys
from pathlib import Path

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
    """Calcula quais números faltam e qual o número do ciclo atual."""
    if not historico:
        return sorted(list(range(1, 26))), 1

    todos_25 = set(range(1, 26))
    sorteados_no_ciclo = set()
    contador_ciclos = 1

    for concurso in historico:
        sorteados_no_ciclo.update(concurso["numeros"])
        if sorteados_no_ciclo == todos_25:
            sorteados_no_ciclo = set()
            contador_ciclos += 1

    faltam = sorted(todos_25 - sorteados_no_ciclo)
    
    # Se o último concurso fechou o ciclo, faltam os 25 para o próximo
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
    supabase.table("estatisticas_numeros").delete().eq("data_referencia", data_ref).execute()
    if payload:
        supabase.table("estatisticas_numeros").insert(payload).execute()

def main():
    supabase = get_supabase()
    print("🚀 Processamento Lotofácil 2026")

    try:
        ultimo = supabase.table("lotofacil_concursos").select("concurso,data").order("concurso", desc=True).limit(1).execute()
        if not ultimo.data:
            raise RuntimeError("Banco vazio")

        data_ref = ultimo.data[0]["data"]
        concurso_n = ultimo.data[0]["concurso"]

        historico = carregar_base_service()
        df_scores = obter_estatisticas_com_score()
        medias = calcular_medias_recentes()
        listas = obter_top_listas(df_scores)

        # Cálculo do Ciclo e Número do Ciclo
        numeros_faltantes, num_ciclo = calcular_ciclo_historico(historico)

       payload_diario = {
            "data_referencia": data_ref,
            "concurso": concurso_n,       # Agora salvando o número do concurso
            "numero_ciclo": num_ciclo,     # Agora salvando o número do ciclo
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

        # Armazenamos o concurso e ciclo em um campo de log ou na própria tabela
        print(f"📡 Concurso: {concurso_n} | Ciclo Atual: {num_ciclo}")

        supabase.table("estatisticas_diarias_v2").delete().eq("data_referencia", data_ref).execute()
        supabase.table("estatisticas_diarias_v2").insert(payload_diario).execute()
        
        salvar_estatisticas_numeros(data_ref, df_scores)
        print(f"✅ Sucesso! Faltam {len(numeros_faltantes)} números para fechar o ciclo {num_ciclo}.")

    except Exception as e:
        print(f"❌ Erro: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
