from fastapi import APIRouter
from pydantic import BaseModel
from typing import List
from app.db import db

router = APIRouter()
# 选择集合（表）
collection = db["recipes"]  # 改成你要用的 collection 名，比如 movies


# 请求模型
class RecipeRequest(BaseModel):
    ingredients: List[str]


# 响应模型
class RecipeResponse(BaseModel):
    steps: List[str]


# 路由：生成菜谱
@router.post("/recipe", response_model=RecipeResponse)
def generate_recipe(payload: RecipeRequest):
    input_ingredients = set(payload.ingredients)
    print(f"Received ingredients接收到的食材: {input_ingredients}")
    # 查询数据库所有菜谱
    recipes = list(collection.find())
    print(f"Available recipes可用的菜谱数量: {len(recipes)}")
    # 简单匹配：ingredients 重合度最高的 recipe
    best_match = None
    best_score = -1

    for recipe in recipes:
        recipe_ingredients = set(
            [ingredient["name"] for ingredient in recipe.get("ingredients", [])]
        )

        # 计算匹配度（交集大小）
        score = len(input_ingredients & recipe_ingredients)

        if score > best_score:
            best_match = recipe
            best_score = score

    if best_match:
        # 返回这个菜谱的步骤
        return RecipeResponse(steps=best_match.get("steps", []))
    else:
        # 没找到 → 返回默认
        return RecipeResponse(steps=["適切なレシピが見つかりませんでした。"])
