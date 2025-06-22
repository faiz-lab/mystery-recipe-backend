from typing import List, Optional
from app.schemas.recipe_schema import IngredientItem, StepItem, RecipeRecommendationResponse
from app.core.db import get_collection
import pprint
import re

class RecipeRecommender:
    def __init__(self, recipe_col=None, ingredient_col=None):
        # MongoDB のコレクションを初期化
        self.recipe_col = recipe_col or get_collection("recipes")
        self.ingredient_col = ingredient_col or get_collection("ingredient_master")

    async def name_to_ids(self, names: List[str]) -> List[str]:
        """
        食材名（標準名・同義語）から ingredient_id (_id) を取得（模糊マッチ対応）
        """
        if not names:
            return []

        or_conditions = []
        for name in names:
            safe_name = re.escape(name)
            or_conditions.append({"standard_name": {"$regex": f"^{safe_name}$", "$options": "i"}})
            or_conditions.append({"synonyms": {"$regex": f"^{safe_name}$", "$options": "i"}})

        cursor = self.ingredient_col.find({"$or": or_conditions})
        results = await cursor.to_list(length=None)

        # debug log
        print("=== Ingredient lookup ===")
        pprint.pprint(or_conditions)
        pprint.pprint(results)

        return [str(r["_id"]) for r in results]

    async def recommend_recipe(
        self,
        available_ingredients: List[str],
        required_ingredients: List[str],
        max_cooking_time: int,
    ) -> Optional[RecipeRecommendationResponse]:

        # 入力食材名 → ingredient_id (_id) に変換
        available_ids = list(set(await self.name_to_ids(available_ingredients)))
        required_ids = list(set(await self.name_to_ids(required_ingredients)))

        # debug log
        print(f"[RecommendRequest] available_ids={available_ids} required_ids={required_ids}")

        if not available_ids:
            print("No available ingredients matched. Return None.")
            return None

        match_stage = {
            "$match": {
                "$expr": {"$setIsSubset": ["$ingredients.ingredient_id", available_ids]},
                "ingredients.ingredient_id": {"$all": required_ids},
                "cooking_time": {"$lte": max_cooking_time}
            }
        }

        pipeline = [
            match_stage,
            {"$sample": {"size": 1}}
        ]

        cursor = await self.recipe_col.aggregate(pipeline)
        result = await cursor.to_list(length=1)

        if not result:
            print("No recipe matched criteria.")
            return None

        selected = result[0]

        ingredient_items = [self.parse_ingredient(ing) for ing in selected["ingredients"]]
        step_items = [self.parse_step(step) for step in selected["steps"]]

        response = RecipeRecommendationResponse(
            name=selected["name"],
            ingredients=ingredient_items,
            steps=step_items,
            missing_ingredients=[],  # ここは将来的に改善できる余地あり
            recommend_score=1.0,
            recommend_reason="おすすめのレシピを見つけました！"
        )
        return response

    def parse_ingredient(self, raw: dict) -> IngredientItem:
        return IngredientItem(
            ingredient_id=raw["ingredient_id"],
            quantity=raw["quantity"],
            unit=raw["unit"]
        )

    def parse_step(self, raw: dict) -> StepItem:
        return StepItem(
            step_no=raw["step_no"],
            instruction=raw["instruction"]
        )
