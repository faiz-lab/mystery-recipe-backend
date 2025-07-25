import logging
from typing import List, Optional

from app.core.db import get_collection
from app.schemas.recipe_schema import (
    IngredientItem,
    StepItem,
    RecipeRecommendationResponse,
    AvailableIngredient,
    RequiredIngredient,
)

logger = logging.getLogger(__name__)


class RecipeRecommender:
    """Recipe recommendation service."""

    def __init__(self, recipe_col=None):
        self.recipe_col = recipe_col or get_collection("recipe_list")

    async def _build_pipeline(
        self,
        available_ingredients: List[AvailableIngredient],
        required_ingredients: List[RequiredIngredient],
        max_time: int,
    ) -> list:
        """构建 MongoDB 查询 pipeline"""
        match_conditions = {"cooking_time": {"$lte": max_time}}

        # 必需食材逻辑：菜谱中每个 required ingredient 的需求量 <= 用户提供量
        if required_ingredients:
            match_conditions["ingredients"] = {
                "$all": [
                    {"$elemMatch": {"name": req.name, "amount": {"$lte": req.amount}}}
                    for req in required_ingredients
                ]
            }

        # 可用食材逻辑：菜谱的每个 ingredient 必须能用 available_ingredients 覆盖
        avail_list = [item.model_dump() for item in available_ingredients]
        if avail_list:
            match_conditions["$expr"] = {
                "$allElementsTrue": [
                    {
                        "$map": {
                            "input": "$ingredients",
                            "as": "ing",
                            "in": {
                                "$anyElementTrue": [
                                    {
                                        "$map": {
                                            "input": avail_list,
                                            "as": "avail",
                                            "in": {
                                                "$and": [
                                                    {"$eq": ["$$ing.name", "$$avail.name"]},
                                                    {"$lte": ["$$ing.amount", "$$avail.quantity"]},
                                                ]
                                            },
                                        }
                                    }
                                ]
                            },
                        }
                    }
                ]
            }

        return [
            {"$match": match_conditions},
            {"$sample": {"size": 1}},  # 随机选一条
            {"$unset": ["_id"]},      # 移除 MongoDB 内部 ID
        ]

    async def _find_from_db(
        self,
        available_ingredients: List[AvailableIngredient],
        required_ingredients: List[RequiredIngredient],
        max_time: int,
    ) -> Optional[dict]:
        """执行 MongoDB 查询，如果没有结果返回 None"""
        try:
            pipeline = await self._build_pipeline(available_ingredients, required_ingredients, max_time)
            cursor = await self.recipe_col.aggregate(pipeline)  # Motor 返回 AsyncIOMotorCommandCursor
            result = await cursor.to_list(length=1)
            return result[0] if result else None
        except Exception as e:
            logger.exception(f"MongoDB 查询失败: {e}")
            return None

    async def recommend_recipe(
        self,
        available_ingredients: List[AvailableIngredient],
        required_ingredients: List[RequiredIngredient],
        max_cooking_time: int,
    ) -> Optional[RecipeRecommendationResponse]:
        """
        根据用户提供的食材和时间推荐菜谱。
        1. 优先从数据库查找
        2. 如果找不到，返回 None
        """
        recipe_doc = await self._find_from_db(available_ingredients, required_ingredients, max_cooking_time)

        if not recipe_doc:
            # 找不到菜谱，直接返回 None（保持你的要求）
            return None

        # 转换 ingredients 和 steps
        ingredients = self._convert_ingredients(recipe_doc.get("ingredients", []))
        steps = self._convert_steps(recipe_doc.get("steps", []))

        return RecipeRecommendationResponse(
            name=recipe_doc.get("name", ""),
            cooking_time=recipe_doc.get("cooking_time", 0),
            ingredients=ingredients,
            servings=recipe_doc.get("servings", "1人前"),
            recipe_img_url=recipe_doc.get("recipe_img_url") or recipe_doc.get("image_url"),
            recipe_url=recipe_doc.get("recipe_url"),
            steps=steps,
            missing_ingredients=[],
            recommend_score=1.0,
            recommend_reason="おすすめレシピを見つけました！",
        )

    @staticmethod
    def _convert_ingredients(raw_ingredients: List[dict]) -> List[IngredientItem]:
        """将 DB/GPT 返回的 ingredients 转换成 IngredientItem 列表"""
        return [
            IngredientItem(
                ingredient_id=ing.get("ingredient_id") or ing.get("name", ""),
                quantity=ing.get("quantity") or ing.get("amount") or 0,
                unit=ing.get("unit", ""),
            )
            for ing in raw_ingredients
        ]

    @staticmethod
    def _convert_steps(raw_steps: List[dict]) -> List[StepItem]:
        """将 DB/GPT 返回的 steps 转换成 StepItem 列表"""
        return [StepItem(**step) for step in raw_steps if isinstance(step, dict)]
