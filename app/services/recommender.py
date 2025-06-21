from typing import List, Optional
from pymongo import MongoClient
from random import choice
from bson import ObjectId
from app.schemas.recipe_schema import RecipeSchema
from app.schemas.recipe_schema import IngredientItem, StepItem, RecipeRecommendationResponse
from app.core.db import get_collection

class RecipeRecommender:
    def __init__(self):
        self.recipe_col = get_collection("recipes")
        self.ingredient_col = get_collection("ingredient_master")

    async def name_to_ids(self, names: List[str]) -> List[str]:
        cursor = self.ingredient_col.find({"$or": [
            {"standard_name": {"$in": names}},
            {"synonyms": {"$in": names}}
        ]})
        results = await cursor.to_list(length=None)
        return [str(r["_id"]) for r in results]  # 转为字符串形式，方便匹配

    async def recommend_recipe(
        self,
        available_ingredients: List[str],
        required_ingredients: List[str],
        max_cooking_time: int,
    ) -> Optional[RecipeRecommendationResponse]:
        available_ids = await self.name_to_ids(available_ingredients)
        required_ids = await self.name_to_ids(required_ingredients)

        # 查询符合条件的食谱
        query = {
            "ingredients.ingredient_id": {"$not": {"$elemMatch": {"$nin": available_ids}}},
            "cooking_time": {"$lte": max_cooking_time},
        }

        cursor = self.recipe_col.find(query)
        candidates = await cursor.to_list(length=None)

        filtered = []
        for recipe in candidates:
            recipe_ids = [ing["ingredient_id"] for ing in recipe["ingredients"]]
            if all(req_id in recipe_ids for req_id in required_ids):
                filtered.append(recipe)

        if not filtered:
            return None
        selected = choice(filtered)
        selected["_id"] = str(selected["_id"])

        # 构造返回数据
        ingredient_items = [IngredientItem(**ing) for ing in selected["ingredients"]]
        step_items = [StepItem(**step) for step in selected["steps"]]

        response = RecipeRecommendationResponse(
            name=selected["name"],
            ingredients=ingredient_items,
            steps=step_items,
            missing_ingredients=[],
            recommend_score=1.0,
            recommend_reason="おすすめのレシピを見つけました！"
        )
        return response