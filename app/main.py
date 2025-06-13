from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.routers import recipe

app = FastAPI()

# CORS 设置，允许前端访问
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 生产环境改成你的前端域名
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 注册路由
app.include_router(recipe.router)

@app.get("/")
def read_root():
    return {"message": "Hello ミステリーレシピ!"}
