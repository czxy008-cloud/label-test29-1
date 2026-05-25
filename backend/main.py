"""
FastAPI 应用入口文件
在线投票调查系统后端服务
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.database import engine, Base
from app.routers import auth, surveys, votes, admin

# 创建数据库表（如果不存在）
Base.metadata.create_all(bind=engine)

# 创建 FastAPI 应用
app = FastAPI(
    title="在线投票调查系统 API",
    description="基于 FastAPI 的在线投票调查系统后端API，支持问卷创建、投票、数据统计等功能",
    version="1.0.0",
    docs_url="/api/docs",
    redoc_url="/api/redoc",
)

# 配置 CORS 中间件
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS_LIST,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 注册路由
app.include_router(auth.router)
app.include_router(surveys.router)
app.include_router(votes.router)
app.include_router(admin.router)


@app.get("/api/health", tags=["健康检查"])
async def health_check():
    """
    健康检查端点
    """
    return {
        "status": "healthy",
        "version": "1.0.0",
    }


@app.get("/", tags=["根路径"])
async def root():
    """
    根路径
    """
    return {
        "name": "在线投票调查系统 API",
        "version": "1.0.0",
        "docs": "/api/docs",
        "redoc": "/api/redoc",
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
