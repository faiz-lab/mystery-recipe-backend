from fastapi import APIRouter, HTTPException
from app.schemas.recipe_schema import RecipeRecommendationResponse, RecipeRecommendationRequest
from app.services.recommender import RecipeRecommender

router = APIRouter(prefix="/recipes", tags=["Recipes"])

recommender = RecipeRecommender()

@router.post("/recommendations", response_model=RecipeRecommendationResponse)
async def recommend_recipes(req: RecipeRecommendationRequest):
    """
    レシピ推薦 API
    - max_cooking_time: 最大調理時間（分）
    - required_ingredients: 必ず使いたい食材名
    - available_ingredients: [{name, quantity, unit}]
    """
    try:
        print("🔍 [Recommend API] Request Body:")
        print(req.model_dump(exclude_unset=True), "\n")

        recipe = await recommender.recommend_recipe(
            available_ingredients=req.available_ingredients,
            required_ingredients=req.required_ingredients,
            max_cooking_time=req.max_cooking_time
        )

        if not recipe:
            raise HTTPException(
                status_code=404,
                detail="条件に合うレシピが見つかりませんでした"
            )

        return recipe

    except HTTPException as http_err:
        raise http_err  # 404 はそのまま返す

    except Exception as e:
        print("❌ [Error] recommend_recipes:", e)
        raise HTTPException(
            status_code=500,
            detail=f"レシピ推薦処理でエラーが発生しました: {str(e)}"
        )
