import os
from pydantic_settings import BaseSettings
from dotenv import load_dotenv

# 载入 .env 文件
load_dotenv()

class Settings(BaseSettings):
    # OpenAI 配置
    OPENAI_API_KEY: str = ""
    OPENAI_MODEL: str = "gpt-4o"

    # MongoDB 配置
    MONGO_URI: str = "mongodb://localhost:27017"
    MONGO_DB_NAME: str = "mystery_recipe"

    # CLERK 配置（顺便一起集成）
    CLERK_SECRET_KEY: str = ""

    class Config:
        env_file = f".env.{os.getenv('ENVIRONMENT', 'development')}"
        env_file_encoding = 'utf-8'

# 生成全局配置实例
settings = Settings()
