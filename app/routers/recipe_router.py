from fastapi import APIRouter, HTTPException
from app.schemas.recipe_schema import RecipeRecommendationResponse, RecipeRecommendationRequest
from app.services.recommender import RecipeRecommender

router = APIRouter(prefix="/recipes", tags=["Recipes"])

recommender = RecipeRecommender()

# ✅ 食材レコメンド API
@router.post("/recommendations", response_model=RecipeRecommendationResponse)
async def recommend_recipes(req: RecipeRecommendationRequest):
    try:
        recipe = await recommender.recommend_recipe(
            available_ingredients=req.available_ingredients,
            required_ingredients=req.required_ingredients,
            max_cooking_time=req.max_cooking_time
        )

        if not recipe:
            raise HTTPException(status_code=404, detail="条件に合うレシピが見つかりませんでした。")

        return recipe

    except Exception as e:
        print("❌ Error in recommend_recipes:", str(e))
        raise HTTPException(status_code=500, detail="レシピ推薦処理でエラーが発生しました")
