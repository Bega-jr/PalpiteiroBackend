from fastapi import APIRouter, HTTPException
from app.services.supabase_service import get_supabase
# Importa o motor matemático real v3 que sua engine v19.0 usa
from app.services.estatisticas_combinacao_v3 import calcular_score_combinacoes_reais

router = APIRouter(prefix="/estatisticas", tags=["Estatísticas"])

# ======================================================
# 🆓 ROTA ATUAL / GRATUITA (MANTIDA E PRESERVADA)
# ======================================================
@router.get("")
def estatisticas_publicas():
    supabase = get_supabase()

    # 1. Busca a última análise diária processada no banco
    res_diaria = (
        supabase.table("estatisticas_diarias_v2")
        .select("*")
        .order("data_referencia", desc=True)
        .limit(1)
        .execute()
    )

    if not res_diaria.data:
        raise HTTPException(status_code=404, detail="Estatísticas não processadas.")

    diaria = res_diaria.data[0]
    data_ref = diaria["data_referencia"]
    num_concurso = diaria.get("concurso", "---")
    num_ciclo = diaria.get("numero_ciclo", "---")

    # 2. Busca os detalhes dos 25 números para a tabela atual
    res_numeros = (
        supabase.table("estatisticas_numeros")
        .select("numero, frequencia, atraso, score")
        .eq("data_referencia", data_ref)
        .order("numero")
        .execute()
    )

    # Contrato original preservado intacto - NENHUM GRÁFICO OU TABELA DO SITE ANTIGO VAI QUEBRAR!
    return {
        "estatisticas": res_numeros.data,
        "analise": {
            "soma_media": diaria["media_soma"],
            "pares_media": diaria["media_pares"],
            "impares_media": diaria["media_impares"],
            "primos_media": diaria["media_primos"],
            "data_referencia": data_ref
        },
        "ciclo": {
            "faltam": diaria["numeros_atrasados"],
            "total_faltam": len(diaria["numeros_atrasados"]),
            "numero_ciclo": num_ciclo
        },
        "listas": {
            "numeros_quentes": diaria["numeros_quentes"],
            "numeros_frios": diaria["numeros_frios"],
            "atrasados_ranking": diaria["atrasados_ranking"]
        },
        "meta": {
            "fonte": f"Concurso {num_concurso} | Ciclo {num_ciclo}",
            "total_numeros": len(res_numeros.data)
        }
    }


# ======================================================
# 👑 NOVA ROTA ADVANCED / PREMIUM (Motor v3 Conectado)
# ======================================================
@router.get("/premium")
def estatisticas_premium():
    """
    Retorna a matriz real de combinatórias e sub-conjuntos aprendidos pela IA v19.0.
    """
    try:
        supabase = get_supabase()

        # Executa o aprendizado real v3 dos últimos 1000 concursos usando o cache do pipeline
        scores, metadata = calcular_score_combinacoes_reais(limite_concursos=1000, usar_cache=True)

        if not scores:
            raise HTTPException(status_code=404, detail="Matriz adaptativa v3 indisponível")

        # Puxa o status macro de controle do Meta-Learning passado
        ultimo_regime = (
            supabase.table("memoria_regimes")
            .select("tipo_regime, score_global")
            .order("concurso", desc=True)
            .limit(1)
            .execute()
        )

        tipo_regime = "NEUTRO"
        score_global = 0.5000
        if ultimo_regime.data:
            tipo_regime = ultimo_regime.data[0].get("tipo_regime", "NEUTRO")
            score_global = float(ultimo_regime.data[0].get("score_global", 0.50))

        # Formata as tuplas de Buckets estruturais para entrega JSON limpa
        padroes_formatados = []
        padroes_ordenados = sorted(scores.items(), key=lambda x: x[1], reverse=True)

        for chave, score in padroes_ordenados[:30]:  # Top 30 estruturas mais eficientes da IA
            soma_b, pares_b, primos_b, linhas_b = chave
            meta = metadata.get(chave, {"hits_15": 0, "hits_14": 0, "hits_13": 0})

            padroes_formatados.append({
                "hash_padrrao": f"S{soma_b}-P{pares_b}-PR{primos_b}",
                "faixa_soma": f"{soma_b - 10} a {soma_b + 10}",
                "faixa_pares": f"{pares_b} a {pares_b + 1}",
                "faixa_primos": f"{primos_b} a {primos_b + 1}",
                "distribuicao_linhas": "-".join(map(str, linhas_b)),
                "score_convergencia": round(float(score), 4),
                "hits": {
                    "premiacoes_15": int(meta.get("hits_15", 0)),
                    "premiacoes_14": int(meta.get("hits_14", 0)),
                    "premiacoes_13": int(meta.get("hits_13", 0))
                }
            })

        return {
            "status": "ok",
            "motor_inteligencia": "v19.0-genetic-context",
            "regime_ativo": tipo_regime,
            "score_global_matriz": round(score_global, 4),
            "padroes_aprendidos": padroes_formatados
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro ao processar visão premium: {str(e)}")

