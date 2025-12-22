from fastapi import FastAPI
from app.routes.concurso import router as concurso_router
from app.routes.statistics import router as statistics_router
from app.routes.debug import router as debug_router
from app.routes.palpites import router as palpites_router

app = FastAPI(
    title="Palpiteiro Backend",
    version="1.0.0"
)

@app.get("/")
def root():
    return {"status": "ROOT_OK"}

# 🔥 REGISTRO DAS ROTAS
app.include_router(concurso_router)
app.include_router(statistics_router)
app.include_router(debug_router)
app.include_router(palpites_router)
