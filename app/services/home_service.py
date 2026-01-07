from app.core.supabase import supabase


def obter_dados_home():
    """
    Retorna os dados do último concurso diretamente da view vw_lotofacil_stats
    """
    try:
        response = (
            supabase
            .table("vw_lotofacil_stats")
            .select("*")
            .order("concurso", desc=True)
            .limit(1)
            .execute()
        )

        if not response.data:
            return None

        dados = response.data[0]

        # Trata campos JSON que vêm como string
        if isinstance(dados.get("municipios"), str):
            import json
            dados["municipios"] = json.loads(dados["municipios"])

        return dados

    except Exception as e:
        raise RuntimeError(f"Erro ao buscar dados da home: {str(e)}")
