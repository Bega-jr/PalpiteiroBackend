from fastapi import FastAPI
from app.routes.concurso import router as concurso_router

app = FastAPI(
    title="Palpiteiro Backend",
    version="1.0.0"
)

@app.get("/")
def root():
    return {"status": "ROOT_OK"}

# 🔥 REGISTRA A ROTA
app.include_router(concurso_router)
