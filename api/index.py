from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# Importação dos routers
from app.routes.health import router as health_router
from app.routes.debug import router as debug_router
from app.routes.ultimos import router as ultimos_router
from app.routes.concurso import router as concurso_router
from app.routes.estatisticas import router as estatisticas_router
from app.routes.palpites import router as palpites_router
from app.routes.historico import router as historico_router

app = FastAPI(
    title="Palpiteiro Backend",
    description="API para o aplicativo Palpiteiro - palpites inteligentes na loteria",
    version="1.0.0",
    docs_url="/docs",      # Swagger UI
    redoc_url="/redoc"     # ReDoc
)

# ========================
# Configuração de CORS
# ========================
# Atualizado para suportar Lovable, Netlify e Localhost
origins = [
    "https://palpiteiro-ia.netlify.app",       # Produção Netlify
    "https://lovable.dev",                     # Editor Lovable
    "https://gpt-engineer.lovable.app",        # Preview Lovable Geral
    "http://localhost:5173",                   # Vite Local
    "http://localhost:3000",                   # Porta alternativa
    "https://palpiteiro-frontend.vercel.app",  # Produção Vercel
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    # Permite URLs dinâmicas do Lovable via Regex
    allow_origin_regex="https://.*\.lovable\.app", 
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ========================
# Rota raiz
# ========================
@app.get("/", tags=["Root"])
def root():
    return {
        "status": "ok",
        "service": "Palpiteiro Backend",
        "message": "API rodando com sucesso! Acesse /docs ou /redoc para a documentação."
    }

# ========================
# Inclusão dos routers
# ========================
app.include_router(health_router, tags=["Health"])
app.include_router(debug_router, tags=["Debug"])
app.include_router(ultimos_router, tags=["Últimos Resultados"])
app.include_router(concurso_router, tags=["Concurso"])
app.include_router(estatisticas_router, tags=["Estatísticas"])
app.include_router(palpites_router, tags=["Palpites"])
app.include_router(historico_router, tags=["Histórico"])

# Mensagem de startup
@app.on_event("startup")
def startup_event():
    print("Palpiteiro Backend iniciado com sucesso!")
    print("CORS configurado para Netlify e Lovable.")

