from app.services.supabase_service import get_supabase
from app.services.palpites_service import gerar_palpites_em_memoria
from fastapi import HTTPException
import traceback
from datetime import date


def executar_backtest(
    concurso_inicio: int,
    concurso_fim: int,
    qtd_palpites: int = 7,
    tipo_palpite: str = "fixo",
    versao_gerador: str = "v1.0"
):
    """
    Executa backtest REAL e grava resumo em palpites_resultados_reais
    """
    try:
        supabase = get_supabase()

        concursos = (
            supabase
            .table("lotofacil_concursos")
            .select("concurso, dezenas")
            .gte("concurso", concurso_inicio)
            .lte("concurso", concurso_fim)
            .order("concurso")
            .execute()
        ).data or []

        if not concursos:
            raise Exception("Concursos não encontrados")

        resultado = {
            11: 0,
            12: 0,
            13: 0,
            14: 0,
            15: 0
        }

        for c in concursos:
            dezenas = set(int(d) for d in c["dezenas"])
            palpites = gerar_palpites_em_memoria(qtd_palpites)

            for palpite in palpites:
                acertos = len(set(palpite) & dezenas)
                if acertos >= 11:
                    resultado[acertos] += 1

        payload = {
            "data_referencia": date.today().isoformat(),
            "concurso_inicio": concurso_inicio,
            "concurso_fim": concurso_fim,
            "tipo_palpite": tipo_palpite,
            "versao_gerador": versao_gerador,
            "qtd_palpites": qtd_palpites,
            "acertos_11": resultado[11],
            "acertos_12": resultado[12],
            "acertos_13": resultado[13],
            "acertos_14": resultado[14],
            "acertos_15": resultado[15],
            "total_concursos": len(concursos)
        }

        # evita duplicidade (idempotente)
        supabase.table("palpites_resultados_reais") \
            .delete() \
            .eq("concurso_inicio", concurso_inicio) \
            .eq("concurso_fim", concurso_fim) \
            .eq("tipo_palpite", tipo_palpite) \
            .eq("versao_gerador", versao_gerador) \
            .execute()

        supabase.table("palpites_resultados_reais").insert(payload).execute()

        return {
            "status": "ok",
            "resultado": payload
        }

    except Exception as e:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))

