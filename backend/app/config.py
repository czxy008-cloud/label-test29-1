"""
应用配置模块
从 .env 文件加载环境变量配置
"""

from pydantic_settings import BaseSettings
from pydantic import Field
from typing import List


class Settings(BaseSettings):
    """应用全局配置类"""

    # 数据库配置
    DB_HOST: str = Field(default="localhost", description="数据库主机地址")
    DB_PORT: int = Field(default=5432, description="数据库端口")
    DB_USER: str = Field(default="postgres", description="数据库用户名")
    DB_PASSWORD: str = Field(default="postgres", description="数据库密码")
    DB_NAME: str = Field(default="survey_db", description="数据库名称")

    # JWT 配置
    SECRET_KEY: str = Field(default="change-me-in-production", description="JWT签名密钥")
    ALGORITHM: str = Field(default="HS256", description="JWT加密算法")
    ACCESS_TOKEN_EXPIRE_MINUTES: int = Field(default=1440, description="令牌过期时间(分钟)")

    # CORS 配置
    CORS_ORIGINS: str = Field(
        default="http://localhost:5173,http://localhost:3000",
        description="允许的CORS源地址"
    )

    @property
    def DATABASE_URL(self) -> str:
        """构建数据库连接URL"""
        return f"postgresql://{self.DB_USER}:{self.DB_PASSWORD}@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"

    @property
    def CORS_ORIGINS_LIST(self) -> List[str]:
        """获取CORS源地址列表"""
        return [origin.strip() for origin in self.CORS_ORIGINS.split(",")]

    class Config:
        """Pydantic配置"""
        env_file = ".env"
        case_sensitive = True


# 创建全局配置实例
settings = Settings()
