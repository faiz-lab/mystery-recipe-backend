from datetime import datetime

from fastapi import APIRouter, HTTPException
from linebot import LineBotApi
from linebot.models import TextSendMessage

from app.core.config import settings
from app.core.db import db
from app.schemas.recipe_schema import RecipeRecommendationResponse, RecipeRecommendationRequest
from app.services.gpt_service import generate_trivia
from app.services.recommender import RecipeRecommender

router = APIRouter(prefix="/recipes", tags=["Recipes"])
recommender = RecipeRecommender()
line_bot_api = LineBotApi(settings.LINE_CHANNEL_ACCESS_TOKEN)


@router.post("/recommendations", response_model=RecipeRecommendationResponse)
async def recommend_recipes(req: RecipeRecommendationRequest):
    """Recommend a recipe and save it to the user state."""
    recipe = await recommender.recommend_recipe(
        available_ingredients=req.available_ingredients,
        required_ingredients=req.required_ingredients,
        max_cooking_time=req.max_cooking_time,
    )

    if not recipe:
        raise HTTPException(status_code=404, detail="条件に合うレシピが見つかりませんでした")

    if req.user_id:
        await db.users.update_one(
            {"_id": req.user_id},
            {
                "$set": {
                    "current_recipe": recipe.model_dump(),
                    "current_step": 0,
                    "updated_at": datetime.utcnow(),
                }
            },
            upsert=True,
        )

        try:
            first_instruction = recipe.steps[0].instruction if recipe.steps else ""
            trivia = await generate_trivia(first_instruction) if first_instruction else ""
            message = f"おすすめレシピが決まりました！\nステップ1: {first_instruction}"
            if trivia:
                message += f"\n🧠 うんちく: {trivia}"
            line_bot_api.push_message(req.user_id, TextSendMessage(text=message))
        except Exception as e:  # pragma: no cover - push error handling
            print(f"LINE push error: {e}")
    return recipe