from fastapi import FastAPI

app = FastAPI(
    title="Palpiteiro Backend",
    version="1.0.0"
)

@app.get("/")
def root():
    return {"status": "ok"}

@app.get("/health")
def health():
    return {"status": "healthy"}
