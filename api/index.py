from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# Inclusão dos routers (SEM prefixo para bater com o esperado)
app.include_router(health_router, tags=["Health"])
app.include_router(debug_router, tags=["Debug"])
app.include_router(ultimos_router, tags=["Últimos Resultados"])
app.include_router(concurso_router, tags=["Concurso"])
app.include_router(estatisticas_router, tags=["Estatísticas"])
app.include_router(palpites_router, tags=["Palpites"])
app.include_router(historico_router, tags=["Histórico"])

app = FastAPI(
    title="Palpiteiro Backend",
    description="API para o aplicativo Palpiteiro - palpites inteligentes na loteria",
    version="1.0.0",
    docs_url="/docs",      # Swagger UI
    redoc_url="/redoc"     # ReDoc (já estava funcionando)
)

# ========================
# Configuração de CORS
# ========================
# Lista de origens permitidas
origins = [
    "https://palpiteiro-ia.netlify.app",     # Seu frontend em produção
    "http://localhost:5173",                 # Desenvolvimento local (Vite)
    "http://localhost:3000",                 # Caso use outro porto no futuro
    "https://palpiteiro-frontend.vercel.app",  # Caso deploy no Vercel também
]

# Em ambiente de desenvolvimento local, às vezes é útil permitir tudo temporariamente
# (comente essa linha em produção se quiser mais segurança)
# origins = ["*"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],      # Permite GET, POST, PUT, DELETE, OPTIONS etc.
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
app.include_router(health_router, prefix="/health", tags=["Health"])
app.include_router(debug_router, prefix="/debug", tags=["Debug"])
app.include_router(ultimos_router, prefix="/ultimos", tags=["Últimos Resultados"])
app.include_router(concurso_router, prefix="/concurso", tags=["Concurso"])
app.include_router(estatisticas_router, prefix="/estatisticas", tags=["Estatísticas"])
app.include_router(palpites_router, prefix="/palpites", tags=["Palpites"])
app.include_router(historico_router, prefix="/historico", tags=["Histórico"])

# Opcional: mensagem de startup
@app.on_event("startup")
def startup_event():
    print("Palpiteiro Backend iniciado com sucesso!")
    print(f"Documentação disponível em: {app.docs_url} e {app.redoc_url}")
