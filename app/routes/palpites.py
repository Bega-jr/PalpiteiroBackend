from fastapi import APIRouter

router = APIRouter(prefix="/palpites")

@router.get("/teste")
def teste():
    return {"ok": True}

