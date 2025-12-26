from fastapi import APIRouter, HTTPException

router = APIRouter(
    prefix="/palpites",
    tags=["Palpites"]
)

# =====================================================
# PALPITE FIXO (FREE)
# =====================================================
@router.get("/fixo")
def palpites_fixo():
    """
    Palpite fixo com trava de números
    """
    return {
        "status": "ok",
        "tipo": "fixo",
        "numeros": []
    }

# =====================================================
# PALPITES ESTATÍSTICOS (FREE)
# =====================================================
@router.get("/estatisticos")
def palpites_estatisticos():
    """
    Palpites baseados em estatísticas (placeholder)
    """
    return {
        "status": "ok",
        "tipo": "estatistico",
        "total": 0,
        "palpites": []
    }

# =====================================================
# GERADOR GERAL (FREE / VIP)
# =====================================================
@router.post("/gerar")
def gerar_palpites(
    total_palpites: int = 7,
    vip: bool = False,
    numeros_fixos: list[int] | None = None
):
    """
    Endpoint central de geração
    No VIP permitirá interação futura
    """
    try:
        return {
            "status": "ok",
            "vip": vip,
            "total_palpites": total_palpites,
            "numeros_fixos": numeros_fixos or [],
            "palpites": []
        }

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Erro ao gerar palpites: {str(e)}"
        )
