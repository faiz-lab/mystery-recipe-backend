from typing import List, Optional
from app.schemas.recipe_schema import IngredientItem, StepItem, RecipeRecommendationResponse
from app.core.db import get_collection

class RecipeRecommender:
    def __init__(self, recipe_col=None, ingredient_col=None):
        # MongoDB のコレクションを初期化
        self.recipe_col = recipe_col or get_collection("recipes")
        self.ingredient_col = ingredient_col or get_collection("ingredient_master")

    async def name_to_ids(self, names: List[str]) -> List[str]:
        # 食材名（標準名・同義語）から ingredient_id を取得
        cursor = self.ingredient_col.find({"$or": [
            {"standard_name": {"$in": names}},
            {"synonyms": {"$in": names}}
        ]})
        results = await cursor.to_list(length=None)
        return [str(r["_id"]) for r in results]

    async def recommend_recipe(
        self,
        available_ingredients: List[str],  # 冷蔵庫にある食材
        required_ingredients: List[str],   # 必ず使いたい食材
        max_cooking_time: int,             # 最大調理時間
    ) -> Optional[RecipeRecommendationResponse]:
        # 入力された食材名を ingredient_id に変換
        available_ids = await self.name_to_ids(available_ingredients)
        required_ids = await self.name_to_ids(required_ingredients)

        # MongoDB の集計パイプラインを作成
        pipeline = [
            {"$match": {
                "$expr": {"$setIsSubset": ["$ingredients.ingredient_id", available_ids]},
                "ingredients.ingredient_id": {"$all": required_ids},
                "cooking_time": {"$lte": max_cooking_time},
            }},
            {"$sample": {"size": 1}}  # 条件に合うレシピからランダムに1件抽出
        ]

        cursor = await self.recipe_col.aggregate(pipeline)
        result = await cursor.to_list(length=1)

        if not result:
            # 条件に合うレシピが存在しない場合
            return None

        selected = result[0]

        # MongoDB から取得した食材・手順情報を Pydantic モデルに変換
        ingredient_items = [IngredientItem(**ing) for ing in selected["ingredients"]]
        step_items = [StepItem(**step) for step in selected["steps"]]

        # 最終的なレスポンスデータを整形
        response = RecipeRecommendationResponse(
            name=selected["name"],
            ingredients=ingredient_items,
            steps=step_items,
            missing_ingredients=[],
            recommend_score=1.0,
            recommend_reason="おすすめのレシピを見つけました！"
        )
        return response