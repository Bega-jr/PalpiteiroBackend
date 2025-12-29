# from fastapi import APIRouter
# from app.services.lotofacil_service import (
#     ultimos_concursos,
#     concurso_por_numero,
# )
# from app.statistics import gerar_estatisticas

# router = APIRouter(
#     prefix="/lotofacil",
#     tags=["Lotofácil"]
# )


# @router.get("/ultimos/{quantidade}")
# def ultimos(quantidade: int):
#     return ultimos_concursos(quantidade)


# @router.get("/concurso/{numero}")
# def concurso(numero: int):
#     return concurso_por_numero(numero)


# @router.get("/estatisticas")
# def estatisticas():
#     return gerar_estatisticas()
    
