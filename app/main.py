from fastapi import FastAPI
from app.routes import results, stats, health

app = FastAPI(
    title="Lotofácil - Resultados Oficiais",
    description="Backend completo da Lotofácil brasileira",
    version="1.0.0"
)

app.include_router(health.router)
app.include_router(results.router)
app.include_router(stats.router)
