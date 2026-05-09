"""
永温麻将 FastAPI 入口
"""
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import RedirectResponse
from api.routes import router as rest_router
from api.routes_admin import router as admin_router
from api.websocket import router as ws_router
import os

app = FastAPI(title="永温麻将")

# CORS（允许前端开发访问）
from fastapi.middleware.cors import CORSMiddleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(rest_router, prefix="/api")
app.include_router(admin_router, prefix="/api/admin")
app.include_router(ws_router)


@app.get("/health")
async def health():
    return {"status": "ok"}


# 前端静态文件
import os
backend_dir = os.path.dirname(os.path.abspath(__file__))  # .../wenzhou_mahjong/backend
project_dir = os.path.dirname(backend_dir)               # .../wenzhou_mahjong
frontend_path = os.path.join(project_dir, "frontend")
if os.path.exists(frontend_path):
    app.mount("/static", StaticFiles(directory=frontend_path), name="static")


@app.get("/")
async def root():
    """重定向到前端"""
    return RedirectResponse(url="/static/index.html")
