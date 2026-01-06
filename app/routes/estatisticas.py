from fastapi import APIRouter, HTTPException
from app.services.supabase_service import get_supabase

router = APIRouter(prefix="/estatisticas", tags=["Estatísticas"])

supabase = get_supabase()


@router.get("")
def obter_estatisticas():
    """
    Endpoint único de estatísticas da Lotofácil
    Fonte da verdade: vw_estatisticas_numeros_atuais
    """
    try:
        # =====================================================
        # 1️⃣ ESTATÍSTICAS POR NÚMERO (VIEW ATUAL)
        # =====================================================
        resp_numeros = (
            supabase
            .table("vw_estatisticas_numeros_atuais")
            .select("numero, frequencia, atraso, score")
            .order("numero")
            .execute()
        )

        if not resp_numeros.data:
            raise HTTPException(
                status_code=500,
                detail="View vw_estatisticas_numeros_atuais não retornou dados"
            )

        estatisticas = [
            {
                "numero": int(n["numero"]),
                "frequencia": int(n["frequencia"]),
                "atraso": int(n["atraso"]),
                "score": float(n["score"]),
            }
            for n in resp_numeros.data
        ]

        # =====================================================
        # 2️⃣ ANÁLISE DIÁRIA (RESUMO)
        # =====================================================
        resp_analise = (
            supabase
            .table("estatisticas_diarias_v2")
            .select(
                "soma_media, pares_media, impares_media, primos_media, data_referencia"
            )
            .order("data_referencia", desc=True)
            .limit(1)
            .execute()
        )

        analise = resp_analise.data[0] if resp_analise.data else {
            "soma_media": 0,
            "pares_media": 0,
            "impares_media": 0,
            "primos_media": 0,
            "data_referencia": None,
        }

        # =====================================================
        # 3️⃣ CICLO (ATRASO > 0)
        # =====================================================
        faltam = sorted([
            n["numero"]
            for n in estatisticas
            if n["atraso"] > 0
        ])

        ciclo = {
            "faltam": faltam,
            "total_faltam": len(faltam),
        }

        # =====================================================
        # 4️⃣ META / CONTEXTO
        # =====================================================
        meta = {
            "data_referencia": analise["data_referencia"],
            "total_numeros": len(estatisticas),
            "fonte": "vw_estatisticas_numeros_atuais",
        }

        # =====================================================
        # 5️⃣ RESPOSTA FINAL (CONTRATO DO FRONT)
        # =====================================================
        return {
            "estatisticas": estatisticas,
            "analise": analise,
            "ciclo": ciclo,
            "meta": meta,
        }

    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ Erro em /estatisticas: {e}")
        raise HTTPException(
            status_code=500,
            detail="Erro interno ao carregar estatísticas"
        )
