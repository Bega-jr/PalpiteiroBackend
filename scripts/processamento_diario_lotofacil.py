import sys
from pathlib import Path

# Configuração de diretório base
BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.append(str(BASE_DIR))

from app.services.supabase_service import get_supabase
from app.services.estatisticas_service import (
    calcular_medias_recentes,
    obter_estatisticas_com_score,
    obter_numeros_mais_atrasados
)

# --------------------------------------------------
# HISTÓRICO COMPLETO (ORDEM CRONOLÓGICA)
# --------------------------------------------------
def carregar_historico():
    """Carrega o histórico do primeiro ao último para cálculo de ciclos."""
    supabase = get_supabase()

    res = (
        supabase
        .table("lotofacil_concursos")
        .select("concurso,data,dezenas")
        .order("concurso", desc=False) # Importante: Ascendente para lógica de ciclo
        .execute()
    )

    if not res.data:
        return []

    return [
        {
            "concurso": r["concurso"],
            "data": r["data"],
            "numeros": [int(n) for n in r["dezenas"]],
        }
        for r in res.data
    ]


# --------------------------------------------------
# CÁLCULO DE CICLO REAL (CORRIGIDO)
# --------------------------------------------------
def calcular_ciclo_atual(historico):
    """
    Identifica quais números faltam para fechar o ciclo atual.
    O ciclo reinicia quando todas as 25 dezenas foram sorteadas.
    """
    if not historico:
        return sorted(list(range(1, 26)))

    todos_25 = set(range(1, 26))
    sorteados_no_ciclo_atual = set()

    for concurso in historico:
        sorteados_no_ciclo_atual.update(concurso["numeros"])
        
        # Se completou as 25, o ciclo fechou. 
        # O próximo concurso iniciará um novo set.
        if sorteados_no_ciclo_atual == todos_25:
            sorteados_no_ciclo_atual = set()

    # O que restar em sorteados_no_ciclo_atual são os números que já saíram no ciclo aberto
    faltam = sorted(todos_25 - sorteados_no_ciclo_atual)
    
    # Se 'faltam' estiver vazio aqui, significa que o último concurso fechou o ciclo exatamente.
    # Portanto, para o próximo concurso, faltam todos os 25.
    return faltam if faltam else sorted(list(range(1, 26)))


# --------------------------------------------------
# SALVAR ESTATÍSTICAS POR NÚMERO
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

    # Limpa apenas os dados daquela data específica para evitar duplicidade
    supabase.table("estatisticas_numeros") \
        .delete() \
        .eq("data_referencia", data_ref) \
        .execute()

    if payload:
        supabase.table("estatisticas_numeros").insert(payload).execute()


# --------------------------------------------------
# MAIN (ORQUESTRADOR)
# --------------------------------------------------
def main():
    supabase = get_supabase()
    print("🚀 Iniciando Processamento Lotofácil 2026")

    try:
        # 1. Busca último concurso para referência
        ultimo = (
            supabase
            .table("lotofacil_concursos")
            .select("concurso,data")
            .order("concurso", desc=True)
            .limit(1)
            .execute()
        )

        if not ultimo.data:
            raise RuntimeError("Nenhum concurso encontrado no banco de dados.")

        concurso_n = ultimo.data[0]["concurso"]
        data_ref = ultimo.data[0]["data"]

        print(f"📌 Referência: Concurso {concurso_n} em {data_ref}")

        # 2. Carrega dados e executa serviços
        historico = carregar_historico()
        medias = calcular_medias_recentes() # Recomenda-se validar se este serviço usa dados atualizados
        df_scores = obter_estatisticas_com_score()
        atrasados_ranking = obter_numeros_mais_atrasados()

        if df_scores.empty:
            raise RuntimeError("Erro: DataFrame de scores está vazio.")

        # 3. Rankings de Quentes e Frios
        numeros_quentes = (
            df_scores.sort_values("score", ascending=False)
            .head(5)["numero"]
            .astype(int).tolist()
        )

        numeros_frios = (
            df_scores.sort_values("score", ascending=True)
            .head(5)["numero"]
            .astype(int).tolist()
        )

        # 4. Cálculo do Ciclo (Lógica Corrigida)
        numeros_faltantes_ciclo = calcular_ciclo_atual(historico)

        # 5. Preparação do Payload para estatisticas_diarias_v2
        payload_diario = {
            "data_referencia": data_ref,
            "concurso": concurso_n,
            "numeros_quentes": numeros_quentes,
            "numeros_frios": numeros_frios,
            "numeros_atrasados": numeros_faltantes_ciclo, # Números que faltam para fechar o ciclo
            "atrasados_ranking": atrasados_ranking,       # Ranking geral de atraso (frequência)
            "media_soma": round(medias.get("soma_media", 0), 2),
            "media_pares": round(medias.get("pares_media", 0), 2),
            "media_impares": round(medias.get("impares_media", 0), 2),
            "media_primos": round(medias.get("primos_media", 0), 2),
            "sequencias_comuns": [3, 4],
            "atualizado_em": data_ref
        }

        # 6. Persistência no Supabase
        # Limpa registros antigos para evitar sobreposição de dados no front
        supabase.table("estatisticas_diarias_v2") \
            .delete() \
            .eq("data_referencia", data_ref) \
            .execute()

        supabase.table("estatisticas_diarias_v2").insert(payload_diario).execute()

        # Salva detalhes individuais por número
        salvar_estatisticas_numeros(data_ref, df_scores)

        print(f"✅ Sucesso! Ciclo atual falta: {numeros_faltantes_ciclo}")

    except Exception as e:
        print(f"❌ Erro crítico no processamento: {str(e)}")
        sys.exit(1)


if __name__ == "__main__":
    main()

