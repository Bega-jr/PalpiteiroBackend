from fastapi import FastAPI
from app.routes.health import router as health_router
from app.routes.estatisticas import router as estatisticas_router
#from app.routes.ultimos import router as ultimos_router
#from app.routes.concurso import router as concurso_router
#from app.routes.debug import router as debug_router
#from app.routes.palpites import router as palpites_router  # 🔥 AQUI
 
app = FastAPI(
    title="Palpiteiro Backend",
    version="1.0.0"
)
 
@app.get("/")
def root():
    return {"status": "ok", "service": "Palpiteiro Backend"}
 
app.include_router(health_router)
app.include_router(estatisticas_router)
#app.include_router(ultimos_router)
#app.include_router(concurso_router)
#app.include_router(debug_router)
#app.include_router(palpites_router)  # 🔥 ESSENCIAL
