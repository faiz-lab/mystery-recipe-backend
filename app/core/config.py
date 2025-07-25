import os
from pydantic_settings import BaseSettings
from dotenv import load_dotenv

# 加载 .env 文件
load_dotenv()

class Settings(BaseSettings):
    # OpenAI 配置
    OPENAI_API_KEY: str = ""
    OPENAI_MODEL: str = "gpt-4o"

    # MongoDB 配置
    MONGO_URI: str = "mongodb://localhost:27017"
    MONGO_DB_NAME: str = "mystery_recipe"

    # CLERK 配置
    CLERK_SECRET_KEY: str = ""

    # LINE Messaging API 配置 ✅ 新增
    LINE_CHANNEL_ACCESS_TOKEN: str = ""
    LINE_CHANNEL_SECRET: str = ""

    FRONTEND_URL: str = ""

    class Config:
        env_file = f".env.{os.getenv('ENVIRONMENT', 'development')}"
        env_file_encoding = 'utf-8'
        extra = "ignore"  # ✅ 忽略未定义的字段

# 全局实例
settings = Settings()
