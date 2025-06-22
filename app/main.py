# main.py
from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from app.routers import recipe_router

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ✅ 加入全局 HTTP Header 规范中间件
@app.middleware("http")
async def add_standard_headers(request: Request, call_next):
    response: Response = await call_next(request)

    # 标准 Content-Type (统一编码声明)
    if response.headers.get("Content-Type") is None:
        response.headers["Content-Type"] = "application/json; charset=utf-8"

    # Cache-Control 策略 (生产环境可以调整为更长)
    response.headers["Cache-Control"] = "public, max-age=600"

    # 其他安全性标准可以加入 (可选强化)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"

    return response

app.include_router(recipe_router.router)

@app.get("/")
def read_root():
    return {"message": "Hello ミステリーレシピ!"}
