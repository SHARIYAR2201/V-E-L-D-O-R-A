from contextlib import asynccontextmanager
from fastapi import APIRouter, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from .config import settings
from .db import Base, engine
from .disclaimers import DISCLAIMERS
from .routers import admin, ai, auth, me, meta, nutrition, plans, tracking


@asynccontextmanager
async def lifespan(_):
    Base.metadata.create_all(engine)
    yield


app = FastAPI(title="V-E-L-D-O-R-A API", version="1.0.0", lifespan=lifespan,
              description=" ".join(DISCLAIMERS))
app.add_middleware(CORSMiddleware, allow_origins=settings.cors_origins.split(","), allow_methods=["*"], allow_headers=["*"])
api = APIRouter(prefix="/api")
for r in (auth.router, me.router, nutrition.router, tracking.router, plans.router, ai.router, meta.router, admin.router):
    api.include_router(r)


@api.get("/health", tags=["meta"])
def health():
    return {"status": "ok"}


app.include_router(api)
