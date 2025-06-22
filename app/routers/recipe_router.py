from fastapi import APIRouter, Depends
from pydantic import BaseModel
from typing import List, Union
from app.services.recommender import RecipeRecommender
from app.schemas.recipe_schema import RecipeRecommendationResponse

router = APIRouter(prefix="/recipes")

def get_recommender():
    return RecipeRecommender()

class RecommendRequest(BaseModel):
    available_ingredients: List[str]
    required_ingredients: List[str]
    max_cooking_time: int

class RecommendResponse(BaseModel):
    success: bool
    found: bool
    data: Union[RecipeRecommendationResponse, None] = None
    message: Union[str, None] = None

@router.post("/recommend", response_model=RecommendResponse)
async def recommend_recipe(request: RecommendRequest, recommender: RecipeRecommender = Depends(get_recommender)):
    result = await recommender.recommend_recipe(
        available_ingredients=request.available_ingredients,
        required_ingredients=request.required_ingredients,
        max_cooking_time=request.max_cooking_time,
    )

    if result is None:
        return RecommendResponse(
            success=True,
            found=False,
            message="条件に合うレシピが見つかりませんでした。"
        )

    return RecommendResponse(
        success=True,
        found=True,
        data=result
    )
