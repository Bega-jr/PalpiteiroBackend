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

# --------------------------------------------------
# CÁLCULO DE CICLO REAL (CORRIGIDO)
# --------------------------------------------------
def calcular_ciclo_atual(historico):
    """Lógica para identificar números que faltam para fechar o ciclo"""
    if not historico:
        return sorted(list(range(1, 26)))

    todos_25 = set(range(1, 26))
    sorteados_no_ciclo = set()

    # O histórico deve vir ordenado do mais antigo para o mais novo
    for concurso in historico:
        sorteados_no_ciclo.update(concurso["numeros"])
        if sorteados_no_ciclo == todos_25:
            sorteados_no_ciclo = set() # Ciclo fechou, reseta

    faltam = sorted(todos_25 - sorteados_no_ciclo)
    return faltam if faltam else sorted(list(range(1, 26)))

# --------------------------------------------------
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

# --------------------------------------------------
def main():
    supabase = get_supabase()
    print("🚀 Processamento Lotofácil 2026")

    try:
        # Pega a referência do último concurso
        ultimo = supabase.table("lotofacil_concursos").select("concurso,data").order("concurso", desc=True).limit(1).execute()
        if not ultimo.data:
            raise RuntimeError("Banco vazio")

        concurso_n = ultimo.data[0]["concurso"]
        data_ref = ultimo.data[0]["data"]

        # 1. Carrega Histórico e Estatísticas usando seu Service
        historico = carregar_base_service()
        df_scores = obter_estatisticas_com_score()
        medias = calcular_medias_recentes()
        
        # 2. Usa a função 'obter_top_listas' que existe no seu service
        listas = obter_top_listas(df_scores)

        # 3. Calcula o Ciclo Corretamente
        # Passamos o histórico (que o carregar_base_service já traz ordenado por concurso)
        numeros_faltantes_ciclo = calcular_ciclo_atual(historico)

        # 4. Monta o Payload para a Tabela Diária (v2)
        payload_diario = {
            "data_referencia": data_ref,
            "concurso": concurso_n,
            "numeros_quentes": listas["numeros_quentes"],
            "numeros_frios": listas["numeros_frios"],
            "numeros_atrasados": numeros_faltantes_ciclo, # Ciclo real
            "atrasados_ranking": listas["atrasados_ranking"], # Ranking de maior atraso atual
            "media_soma": float(medias.get("soma_media", 0)),
            "media_pares": float(medias.get("pares_media", 0)),
            "media_impares": float(medias.get("impares_media", 0)),
            "media_primos": float(medias.get("primos_media", 0)),
            "sequencias_comuns": [3, 4],
        }

        # 5. Salva no Banco
        supabase.table("estatisticas_diarias_v2").delete().eq("data_referencia", data_ref).execute()
        supabase.table("estatisticas_diarias_v2").insert(payload_diario).execute()
        
        salvar_estatisticas_numeros(data_ref, df_scores)

        print(f"✅ Concurso {concurso_n} processado. Ciclo falta: {len(numeros_faltantes_ciclo)} números.")

    except Exception as e:
        print(f"❌ Erro: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
