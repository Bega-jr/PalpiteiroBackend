from fastapi import APIRouter

router = APIRouter(prefix="/palpites", tags=["Palpites"])

@router.get("/")
def teste_palpites():
    return {"status": "palpites router OK"}
