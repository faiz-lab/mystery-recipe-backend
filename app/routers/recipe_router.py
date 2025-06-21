from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List
from app.services.recommender import RecipeRecommender
from app.schemas.recipe_schema import RecipeRecommendationResponse

router = APIRouter(prefix="/recipes")

class RecommendRequest(BaseModel):
    available_ingredients: List[str]
    required_ingredients: List[str]
    max_cooking_time: int

@router.post("/recommend", response_model=RecipeRecommendationResponse)
async def recommend_recipe(request: RecommendRequest):
    recommender = RecipeRecommender()
    result = await recommender.recommend_recipe(
        available_ingredients=request.available_ingredients,
        required_ingredients=request.required_ingredients,
        max_cooking_time=request.max_cooking_time,
    )

    if result is None:
        raise HTTPException(status_code=404, detail="No suitable recipe found.")

    return result
