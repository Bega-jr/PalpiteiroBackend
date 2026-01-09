from fastapi import APIRouter, HTTPException
from app.services.supabase_service import get_supabase

router = APIRouter(prefix="/estatisticas", tags=["Estatísticas"])

@router.get("")
def estatisticas():
    supabase = get_supabase()

    # 1. Busca os dados processados da tabela diária (o mais recente)
    res_diaria = (
        supabase.table("estatisticas_diarias_v2")
        .select("*")
        .order("data_referencia", desc=True)
        .limit(1)
        .execute()
    )

    if not res_diaria.data:
        raise HTTPException(status_code=404, detail="Estatísticas não encontradas. Rode o processamento.")

    diaria = res_diaria.data[0]
    data_ref = diaria["data_referencia"]

    # 2. Busca os detalhes de cada número para a tabela/gráfico
    res_numeros = (
        supabase.table("estatisticas_numeros")
        .select("numero, frequencia, atraso, score")
        .eq("data_referencia", data_ref)
        .order("numero")
        .execute()
    )

    # 3. Formata a resposta para o Front-end
    return {
        "estatisticas": res_numeros.data,
        "analise": {
            "soma_media": diaria["media_soma"],
            "pares_media": diaria["media_pares"],
            "impares_media": diaria["media_impares"],
            "primos_media": diaria["media_primos"],
            "data_referencia": data_ref  # Exibe a data real no Hero do Front
        },
        "ciclo": {
            "faltam": diaria["numeros_atrasados"],
            "total_faltam": len(diaria["numeros_atrasados"])
        },
        "listas": {
            "numeros_quentes": diaria["numeros_quentes"],
            "numeros_frios": diaria["numeros_frios"],
            "atrasados_ranking": diaria["atrasados_ranking"]
        },
        "meta": {
            "fonte": f"Concurso {diaria.get('concurso', 'Atualizado')}", # Mostra o número do concurso se existir
            "total_numeros": 25
        }
    }
