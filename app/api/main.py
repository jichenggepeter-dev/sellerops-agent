"""FastAPI application assembly for the SellerOps Agent MVP."""

from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.api.config import WEB_ROOT, get_settings
from app.api.db import init_db
from app.api.routers.core import router as core_router
from app.api.services.policies import ensure_default_policies


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    ensure_default_policies()
    yield


app = FastAPI(
    title="SellerOps Agent API",
    version="0.1.0",
    description="Governed AI operations workspace for support, review, and audit workflows.",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=get_settings().cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(core_router)
app.mount("/assets", StaticFiles(directory=WEB_ROOT), name="assets")

@app.get("/")
def index() -> FileResponse:
    return FileResponse(WEB_ROOT / "index.html")


@app.get("/{path:path}")
def static_files(path: str) -> FileResponse:
    file_path = (WEB_ROOT / path).resolve()
    web_root = WEB_ROOT.resolve()
    if not str(file_path).startswith(str(web_root)) or not file_path.exists():
        raise HTTPException(status_code=404, detail="Not found")
    return FileResponse(file_path)
