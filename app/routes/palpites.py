from fastapi import APIRouter

router = APIRouter(
    prefix="/palpites",
    tags=["Palpites"]
)

@router.get("/fixo")
def palpites_fixo():
    return {
        "tipo": "fixo",
        "numeros": []
    }

@router.get("/estatisticos")
def palpites_estatisticos():
    return {
        "tipo": "estatistico",
        "numeros": []
    }

@router.post("/gerar")
def gerar_palpites():
    return {
        "status": "ok",
        "palpites": []
    }
