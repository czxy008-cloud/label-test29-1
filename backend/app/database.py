"""
数据库连接配置模块
"""

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from app.config import settings

# 创建数据库引擎
engine = create_engine(
    settings.DATABASE_URL,
    pool_pre_ping=True,
    pool_recycle=3600,
    echo=False
)

# 创建会话工厂
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# 创建ORM模型基类
Base = declarative_base()


def get_db():
    """
    获取数据库会话的依赖项
    使用生成器确保会话在请求结束后正确关闭
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
