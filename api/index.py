from fastapi import FastAPI
from app.routes.health import router as health_router
from app.routes.estatisticas import router as estatisticas_router

app = FastAPI()
app.include_router(health_router)
app.include_router(estatisticas_router)
