from app.services.supabase_service import get_supabase
from app.services.palpites_service import gerar_palpites_validos
from fastapi import HTTPException
import json
import traceback

# ==========================
# BACKTEST
# ==========================

def executar_backtest(
    concurso_inicio: int,
    concurso_fim: int,
    qtd_palpites: int = 7
):
    try:
        supabase = get_supabase()

        # gera palpites reais do sistema
        gerar_palpites_validos(qtd_palpites)

        palpites = (
            supabase
            .table("palpites_validos")
            .select("numeros")
            .order("id", desc=True)
            .limit(qtd_palpites)
            .execute()
            .data
        )

        concursos = (
            supabase
            .table("lotofacil_concursos")
            .select("concurso, dezenas")
            .gte("concurso", concurso_inicio)
            .lte("concurso", concurso_fim)
            .order("concurso")
            .execute()
            .data
        )

        if not concursos:
            raise Exception("Nenhum concurso encontrado")

        resumo = []

        for conc in concursos:
            resultado = set(int(n) for n in conc["dezenas"])

            for idx, palpite in enumerate(palpites):
                numeros_palpite = set(json.loads(palpite["numeros"]))
                acertos = len(resultado & numeros_palpite)

                resumo.append({
                    "concurso": conc["concurso"],
                    "palpite": idx,
                    "acertos": acertos
                })

        return {
            "status": "ok",
            "concurso_inicio": concurso_inicio,
            "concurso_fim": concurso_fim,
            "total_registros": len(resumo),
            "resultado": resumo
        }

    except Exception as e:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))

