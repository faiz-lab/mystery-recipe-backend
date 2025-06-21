from typing import List, Optional
from pymongo import MongoClient
from bson import ObjectId
from app.schemas.recipe_schema import RecipeSchema
from app.schemas.recipe_schema import (
    IngredientItem,
    StepItem,
    RecipeRecommendationResponse,
)
from app.core.db import get_collection


class RecipeRecommender:
    def __init__(self):
        self.recipe_col = get_collection("recipes")
        self.ingredient_col = get_collection("ingredient_master")

    async def name_to_ids(self, names: List[str]) -> List[str]:
        cursor = self.ingredient_col.find(
            {"$or": [{"standard_name": {"$in": names}}, {"synonyms": {"$in": names}}]}
        )
        results = await cursor.to_list(length=None)
        return [str(r["_id"]) for r in results]

    async def recommend_recipe(
        self,
        available_ingredients: List[str],
        required_ingredients: List[str],
        max_cooking_time: int,
    ) -> Optional[RecipeRecommendationResponse]:
        available_ids = await self.name_to_ids(available_ingredients)
        required_ids = await self.name_to_ids(required_ingredients)

        # 使用 MongoDB aggregation + $sample 实现高效随机推荐
        pipeline = [
            {
                "$match": {
                    "ingredients.ingredient_id": {
                        "$not": {"$elemMatch": {"$nin": available_ids}}
                    },
                    "ingredients.ingredient_id": {"$all": required_ids},
                    "cooking_time": {"$lte": max_cooking_time},
                }
            },
            {"$sample": {"size": 1}},
        ]

        cursor = await self.recipe_col.aggregate(pipeline)
        result = await cursor.to_list(length=1)

        if not result:
            return None

        selected = result[0]
        selected["_id"] = str(selected["_id"])

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
