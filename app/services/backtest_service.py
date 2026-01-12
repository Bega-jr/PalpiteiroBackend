from app.services.supabase_service import get_supabase
from app.services.palpites_service import gerar_palpites_em_memoria
from fastapi import HTTPException
import traceback


def executar_backtest(concurso_inicio, concurso_fim, qtd_palpites=7):
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
            "total_concursos": len(concursos),
            "acertos": {11: 0, 12: 0, 13: 0, 14: 0, 15: 0}
        }

        for c in concursos:
            dezenas = set(int(d) for d in c["dezenas"])
            palpites = gerar_palpites_em_memoria(qtd_palpites)

            for palpite in palpites:
                acertos = len(set(palpite) & dezenas)
                if acertos >= 11:
                    resultado["acertos"][acertos] += 1

        return resultado

    except Exception as e:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))
