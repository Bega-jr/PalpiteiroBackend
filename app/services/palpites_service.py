from app.services.supabase_service import get_supabase


def obter_todos_palpites():
    """
    Busca TODOS os registros da tabela palpites, sem filtro algum.
    Retorna exatamente o que o Supabase devolver.
    """
    supabase = get_supabase()

    response = (
        supabase
        .table("palpites")
        .select("*")
        .order("created_at", desc=True)
        .execute()
    )

    # Logs essenciais para diagnóstico
    print("🔍 SUPABASE DATA:", response.data)
    print("⚠️ SUPABASE ERROR:", response.error)

    return response.data or []
