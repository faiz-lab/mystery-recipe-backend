import pprint
import json
import re
from typing import List, Optional
from app.schemas.recipe_schema import (
    IngredientItem,
    StepItem,
    RecipeRecommendationResponse,
)
from app.core.db import get_collection
from app.services.gpt_generator import generate_recipe_by_gpt


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
            gpt_recipe = await generate_recipe_by_gpt(
                available_ingredients=available_ingredients,
                required_ingredients=required_ingredients,
                max_cooking_time=max_cooking_time,
            )

            if not gpt_recipe.strip():
                raise ValueError("GPTの応答が空です")

            # 抽取 ```json ... ``` 中的 JSON（如果有）
            match = re.search(r'```(?:json)?\s*(\{.*?})\s*```', gpt_recipe, re.DOTALL)
            if match:
                gpt_recipe = match.group(1)

            try:
                recipe = json.loads(gpt_recipe)
            except json.JSONDecodeError as e:
                print("❌ GPT返回的内容不是合法JSON：")
                print(gpt_recipe)
                raise ValueError("GPTが不正なJSONを返しました") from e

            insert_result = await self.recipe_col.insert_one(recipe)
            recipe["_id"] = str(insert_result.inserted_id)
            ingredient_items = [
                IngredientItem(
                    ingredient_id=ing.get("ingredient_id") or ing.get("name"),
                    quantity=ing["quantity"],
                    unit=ing["unit"]
                )
                for ing in recipe["ingredients"]
            ]
            step_items = [StepItem(**step) for step in recipe["steps"]]

            return RecipeRecommendationResponse(
                name=recipe["name"],
                ingredients=ingredient_items,
                steps=step_items,
                missing_ingredients=[],
                recommend_score=0.9,
                recommend_reason="これはGPTが提案したレシピです。",
            )

        # 命中数据库时
        selected = result[0]
        ingredient_items = [IngredientItem(**ing) for ing in selected["ingredients"]]
        step_items = [StepItem(**step) for step in selected["steps"]]

        return RecipeRecommendationResponse(
            name=selected["name"],
            ingredients=ingredient_items,
            steps=step_items,
            missing_ingredients=[],
            recommend_score=1.0,
            recommend_reason="おすすめのレシピを見つけました！",
        )
