from fastapi import APIRouter, HTTPException
from app.services.supabase_service import get_supabase

router = APIRouter(prefix="/estatisticas", tags=["Estatísticas"])

@router.get("")
def estatisticas():
    supabase = get_supabase()

    # 1. Busca a última análise diária processada
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

    # 2. Busca os detalhes dos 25 números (para gráfico e tabela)
    res_numeros = (
        supabase.table("estatisticas_numeros")
        .select("numero, frequencia, atraso, score")
        .eq("data_referencia", data_ref)
        .order("numero")
        .execute()
    )

    # 3. Retorno formatado para o componente React
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

