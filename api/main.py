from fastapi import FastAPI
from api.routers import palpites

app = FastAPI()
app.include_router(palpites.router)
