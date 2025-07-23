from datetime import datetime
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Any

from app.core.db import db
from app.schemas.recipe_schema import RecipeRecommendationResponse, RecipeRecommendationRequest
from app.services.recommender import RecipeRecommender
from app.services.gpt_service import generate_trivia, verify_step_image

router = APIRouter(prefix="/recipes", tags=["Recipes"])
recommender = RecipeRecommender()


@router.post("/recommendations", response_model=RecipeRecommendationResponse)
async def recommend_recipes(req: RecipeRecommendationRequest):
    """Recommend a recipe and save it to user state."""
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
    return recipe


class ImageVerifyRequest(BaseModel):
    image_base64: str


@router.post("/{user_id}/next-step")
async def next_step(user_id: str) -> Any:
    """Advance to next step and return instructions with trivia."""
    user = await db.users.find_one({"_id": user_id})
    if not user or "current_recipe" not in user:
        raise HTTPException(status_code=404, detail="レシピが登録されていません")

    recipe = user["current_recipe"]
    step_index = user.get("current_step", 0)

    if step_index >= len(recipe["steps"]):
        return {"done": True}

    step = recipe["steps"][step_index]
    trivia = await generate_trivia(step["instruction"])

    await db.users.update_one(
        {"_id": user_id},
        {"$set": {"current_step": step_index + 1, "updated_at": datetime.utcnow()}},
    )

    return {
        "step_no": step_index + 1,
        "instruction": step["instruction"],
        "trivia": trivia,
        "done": step_index + 1 >= len(recipe["steps"]),
    }


@router.post("/{user_id}/verify-image")
async def verify_image(user_id: str, req: ImageVerifyRequest) -> Any:
    """Verify uploaded image with current step."""
    user = await db.users.find_one({"_id": user_id})
    if not user or "current_recipe" not in user:
        raise HTTPException(status_code=404, detail="レシピが登録されていません")

    step_index = max(user.get("current_step", 0) - 1, 0)
    recipe = user["current_recipe"]
    instructions = "\n".join(
        [f"ステップ{i+1}: {s['instruction']}" for i, s in enumerate(recipe["steps"][: step_index + 1])]
    )

    result = await verify_step_image(instructions, req.image_base64)
    return {"result": result}
