import json
from typing import List, Optional

from app.core.db import get_collection
from app.schemas.recipe_schema import (
    IngredientItem,
    StepItem,
    RecipeRecommendationResponse,
    AvailableIngredient,
    RequiredIngredient,
)
from app.services.gpt_generator import generate_recipe_by_gpt


class RecipeRecommender:
    """Recipe recommendation service."""

    def __init__(self, recipe_col=None):
        self.recipe_col = recipe_col or get_collection("recipe_list")

    async def _find_from_db(
        self,
        available_ingredients: List[AvailableIngredient],
        required_ingredients: List[RequiredIngredient],
        max_time: int,
    ) -> Optional[dict]:
        """
        使用 MongoDB aggregation pipeline 查找符合条件的食谱。
        条件：
        1. cooking_time <= max_time
        2. required_ingredients 中的每个食材必须出现在 recipe.ingredients 且数量足够
        3. recipe.ingredients 中每个食材必须可以由 available_ingredients 提供，且数量足够
        """

        # 构建 aggregation pipeline
        pipeline = [
            {
                "$match": {
                    # 条件1: 調理時間が指定時間以下
                    "cooking_time": {"$lte": max_time},
                    # 条件2: required_ingredients 中的每个食材必须满足
                    "ingredients": {
                        "$all": [
                            {
                                "$elemMatch": {
                                    "name": req_ingr.name,
                                    "amount": {"$gte": req_ingr.amount},
                                }
                            }
                            for req_ingr in required_ingredients
                        ]
                    },
                    # 条件3: 所有食材都必须可以由 available_ingredients 提供
                    "$expr": {
                        "$allElementsTrue": [
                            {
                                "$map": {
                                    "input": "$ingredients",
                                    "as": "ingr",
                                    "in": {
                                        "$or": [
                                            {
                                                "$and": [
                                                    {"$eq": ["$$ingr.name", avail_ingr.name]},
                                                    {"$lte": ["$$ingr.amount", avail_ingr.amount]},
                                                ]
                                            }
                                            for avail_ingr in available_ingredients
                                        ]
                                    },
                                }
                            }
                        ]
                    },
                }
            },
            {"$sample": {"size": 1}},  # 随机选一条
            {"$unset": ["_id"]},       # 移除 _id 字段
        ]

        cursor = self.recipe_col.aggregate(pipeline)
        result = await cursor.to_list(length=1)
        return result[0] if result else None

    async def recommend_recipe(
        self,
        available_ingredients: List[AvailableIngredient],
        required_ingredients: List[RequiredIngredient],
        max_cooking_time: int,
    ) -> Optional[RecipeRecommendationResponse]:
        """Recommend a recipe based on ingredients and cooking time."""

        # 调用 MongoDB 查询
        recipe_doc = await self._find_from_db(available_ingredients, required_ingredients, max_cooking_time)

        # 如果数据库未找到结果，调用 GPT 生成
        if not recipe_doc:
            gpt_recipe = await generate_recipe_by_gpt(
                available_ingredients=[item.model_dump() for item in available_ingredients],
                required_ingredients=required_ingredients,
                max_cooking_time=max_cooking_time,
            )

            recipe_doc = json.loads(gpt_recipe)
            await self.recipe_col.insert_one(recipe_doc)
            recommend_reason = "GPTによる提案レシピです"
            score = 0.9
        else:
            recommend_reason = "おすすめレシピを見つけました！"
            score = 1.0

        # 转换食材和步骤
        ingredients = [
            IngredientItem(
                ingredient_id=ing.get("ingredient_id") or ing.get("name"),
                quantity=ing.get("quantity") or ing.get("amount") or 0,
                unit=ing.get("unit") or "",
            )
            for ing in recipe_doc.get("ingredients", [])
        ]
        steps = [StepItem(**step) for step in recipe_doc.get("steps", [])]

        return RecipeRecommendationResponse(
            name=recipe_doc.get("name", ""),
            cooking_time=recipe_doc.get("cooking_time"),
            ingredients=ingredients,
            servings=recipe_doc.get("servings"),
            recipe_img_url=recipe_doc.get("recipe_img_url") or recipe_doc.get("image_url"),
            recipe_url=recipe_doc.get("recipe_url"),
            steps=steps,
            missing_ingredients=[],
            recommend_score=score,
            recommend_reason=recommend_reason,
        )
