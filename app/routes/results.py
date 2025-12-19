from fastapi import APIRouter
from app.services import get_concurso

router = APIRouter(prefix="/lotofacil", tags=["Lotofácil"])

@router.get("/concurso/{concurso_id}")
def concurso(concurso_id: int):
    return get_concurso(concurso_id)
