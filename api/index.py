from fastapi import FastAPI

from app.routes.health import router as health_router
from app.routes.results import router as results_router
from app.routes.stats import router as stats_router

app = FastAPI(
    title="Lotofácil - Resultados Oficiais",
    description="Backend oficial da Lotofácil brasileira",
    version="1.0.0"
)

app.include_router(health_router)
app.include_router(results_router)
app.include_router(stats_router)
