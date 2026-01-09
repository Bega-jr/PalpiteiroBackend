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
    if not historico:
        return sorted(list(range(1, 26)))

    todos_25 = set(range(1, 26))
    sorteados_no_ciclo = set()

    for concurso in historico:
        sorteados_no_ciclo.update(concurso["numeros"])
        if sorteados_no_ciclo == todos_25:
            sorteados_no_ciclo = set()

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

        # Usamos apenas a data_referencia para o payload, conforme seu esquema original
        data_ref = ultimo.data[0]["data"]
        concurso_n = ultimo.data[0]["concurso"]

        # 1. Carrega Histórico e Estatísticas
        historico = carregar_base_service()
        df_scores = obter_estatisticas_com_score()
        medias = calcular_medias_recentes()
        listas = obter_top_listas(df_scores)

        # 2. Calcula o Ciclo
        numeros_faltantes_ciclo = calcular_ciclo_atual(historico)

        # 3. Monta o Payload (Removido campo 'concurso' para evitar erro de Schema)
        payload_diario = {
            "data_referencia": data_ref,
            "numeros_quentes": listas["numeros_quentes"],
            "numeros_frios": listas["numeros_frios"],
            "numeros_atrasados": numeros_faltantes_ciclo,
            "atrasados_ranking": listas["atrasados_ranking"],
            "media_soma": float(medias.get("soma_media", 0)),
            "media_pares": float(medias.get("pares_media", 0)),
            "media_impares": float(medias.get("impares_media", 0)),
            "media_primos": float(medias.get("primos_media", 0)),
            "sequencias_comuns": [3, 4],
        }

        # 4. Salva no Banco
        print(f"📡 Enviando dados do concurso {concurso_n} ({data_ref})...")
        
        supabase.table("estatisticas_diarias_v2").delete().eq("data_referencia", data_ref).execute()
        supabase.table("estatisticas_diarias_v2").insert(payload_diario).execute()
        
        salvar_estatisticas_numeros(data_ref, df_scores)

        print(f"✅ Processamento concluído com sucesso!")

    except Exception as e:
        print(f"❌ Erro: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()

if __name__ == "__main__":
    main()
