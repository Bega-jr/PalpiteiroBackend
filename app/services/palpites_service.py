from app.services.supabase_service import get_supabase


def obter_todos_palpites_debug():
    """
    Busca TODOS os registros da tabela palpites_validos
    Retorna os dados crus, sem tratamento algum.
    """
    supabase = get_supabase()

    response = (
        supabase
        .table("palpites_validos")
        .select("*")
        .execute()
    )

    # Logs essenciais (Vercel / Render)
    print("🔍 SUPABASE DATA:", response.data)
    print("❌ SUPABASE ERROR:", response.error)

    if response.error:
        raise Exception(response.error.message)

    return response.data or []
