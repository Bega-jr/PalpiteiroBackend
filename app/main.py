from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# Importação dos routers
from app.routes.health import router as health_router
from app.routes.home import router as home_router
from app.routes.ultimos import router as ultimos_router
from app.routes.concurso import router as concurso_router
from app.routes.estatisticas import router as estatisticas_router
from app.routes.palpites import router as palpites_router
from app.routes.historico import router as historico_router
from app.routes.resultados import router as resultados_router
from app.routes.home_desempenho import router as home_desempenho_router

app = FastAPI(
    title="Palpiteiro Backend",
    description="API para o aplicativo Palpiteiro - palpites inteligentes na loteria",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# ======================================================
# CORS
# ======================================================

origins = [
    # Frontend produção
    "https://palpiteiro-ia.netlify.app",
    "https://palpiteiro-frontend.vercel.app",
    "https://palpiteiro.vercel.app",

    # Backend
    "https://palpiteiro-backend.vercel.app",

    # Desenvolvimento local
    "http://localhost:3000",
    "http://localhost:5173",
    "http://localhost:8080",
    "http://127.0.0.1:8080",

    # GitHub Codespaces
    "https://glowing-xylophone-7495ww5x9wvfpg75-8080.app.github.dev",

    # Lovable
    "https://lovable.dev",
    "https://gpt-engineer.lovable.app",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_origin_regex=r"https://.*\.app\.github\.dev",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ======================================================
# ROOT
# ======================================================

@app.get("/", tags=["Root"])
def root():
    return {
        "status": "ok",
        "service": "Palpiteiro Backend",
        "message": "API rodando com sucesso!"
    }

# ======================================================
# ROUTERS
# ======================================================

app.include_router(health_router, tags=["Health"])
app.include_router(home_router, tags=["Home"])
app.include_router(ultimos_router, tags=["Últimos Resultados"])
app.include_router(concurso_router, tags=["Concurso"])
app.include_router(estatisticas_router, tags=["Estatísticas"])
app.include_router(palpites_router, tags=["Palpites"])
app.include_router(historico_router, tags=["Histórico"])
app.include_router(resultados_router, tags=["Resultados"])
app.include_router(home_desempenho_router, tags=["Home Desempenho"])

# ======================================================
# STARTUP
# ======================================================

@app.on_event("startup")
def startup_event():
    print("✅ Palpiteiro Backend iniciado com sucesso!")
