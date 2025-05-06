from fastapi import FastAPI
from api.routes import containers

app = FastAPI()

app.include_router(containers.router)