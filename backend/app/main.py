from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from . import routes_api, routes_ws

app = FastAPI(title="Showtime Notes")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(routes_api.router)
app.include_router(routes_ws.router)
