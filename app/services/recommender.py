import pprint
from typing import List, Optional
from app.schemas.recipe_schema import (
    IngredientItem,
    StepItem,
    RecipeRecommendationResponse,
)
from app.core.db import get_collection


class RecipeRecommender:
    def __init__(self, recipe_col=None):
        self.recipe_col = recipe_col or get_collection("recipes")

    async def recommend_recipe(
        self,
        available_ingredients: List[str],
        required_ingredients: List[str],
        max_cooking_time: int,
    ) -> Optional[RecipeRecommendationResponse]:

        print("[RecommendRequest]")
        pprint.pprint(
            {
                "available_codes": available_ingredients,
                "required_codes": required_ingredients,
            }
        )

        pipeline = [
            {
                "$match": {
                    "$expr": {
                        "$setIsSubset": [
                            "$ingredients.ingredient_id",
                            available_ingredients,
                        ]
                    },
                    "ingredients.ingredient_id": {"$all": required_ingredients},
                    "cooking_time": {"$lte": max_cooking_time},
                }
            },
            {"$sample": {"size": 1}},
        ]

        cursor = await self.recipe_col.aggregate(pipeline)
        result = await cursor.to_list(length=1)

        print("[Aggregation Result]")
        pprint.pprint(result)

        if not result:
            return None

        selected = result[0]

        ingredient_items = [IngredientItem(**ing) for ing in selected["ingredients"]]
        step_items = [StepItem(**step) for step in selected["steps"]]

        response = RecipeRecommendationResponse(
            name=selected["name"],
            ingredients=ingredient_items,
            steps=step_items,
            missing_ingredients=[],
            recommend_score=1.0,
            recommend_reason="おすすめのレシピを見つけました！",
        )
        return response
