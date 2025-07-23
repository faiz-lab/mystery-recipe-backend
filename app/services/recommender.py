import pprint
import json
import re
from typing import List, Optional
from app.schemas.recipe_schema import (
    IngredientItem,
    StepItem,
    RecipeRecommendationResponse, AvailableIngredient, RequiredIngredient,
)
from app.core.db import get_collection
from app.services.gpt_generator import generate_recipe_by_gpt

class RecipeRecommender:
    def __init__(self, recipe_col=None):
        self.recipe_col = recipe_col or get_collection("recipe_list")

    async def recommend_recipe(
        self,
        available_ingredients: List[AvailableIngredient],  # [{ name, quantity, unit }]
        required_ingredients: List[RequiredIngredient],
        max_cooking_time: int,
    ) -> Optional[RecipeRecommendationResponse]:

        available_ids = [item.model_dump() for item in available_ingredients]

        print("[RecommendRequest]")
        pprint.pprint({"available_ids": available_ids,
                       "required_ids": required_ingredients,
                       "max_cooking_time": max_cooking_time
                       })

        # ✅ 构建 MongoDB pipeline
        match_conditions = {
            "cooking_time": {"$lte": max_cooking_time},
            "ingredients": {
                "$all": [
                    {"$elemMatch": {"name": req_ingr.name}, "amount": {"gte": req_ingr.amount}} for req_ingr in required_ingredients
                ]
            },
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
                                            {"$eq": ["$$ingr.name", ing["name"]]},
                                            {"$lte": ["$$ingr.amount", ing["quantity"]]}
                                        ]
                                    }
                                    for ing in available_ids
                                ]
                            }
                        }
                    }
                ]
            }
        }

        pipeline = [
            {"$match": match_conditions},
            {"$sample": {"size": 1}},
            {"$unset": ["_id"]}
        ]
        cursor = await self.recipe_col.aggregate(pipeline)
        result = await cursor.to_list(length=1)
        # ✅ 打印结果
        print("\n[MongoDB Query Result]")
        if result:
            pprint.pprint(result[0])  # 打印第一条
        else:
            print("No matching recipe found.")
        if not result:
            gpt_recipe = await generate_recipe_by_gpt(
                available_ingredients=available_ids,
                required_ingredients=required_ingredients,
                max_cooking_time=max_cooking_time,
            )

            match = re.search(r'```(?:json)?\s*(\{.*?})\s*```', gpt_recipe, re.DOTALL)
            if match:
                gpt_recipe = match.group(1)

            try:
                recipe = json.loads(gpt_recipe)
            except json.JSONDecodeError:
                raise ValueError("GPTが不正なJSONを返しました")

            insert_result = await self.recipe_col.insert_one(recipe)
            recipe["_id"] = str(insert_result.inserted_id)

            ingredient_items = [
                IngredientItem(
                    ingredient_id=ing.get("ingredient_id") or ing.get("name"),
                    quantity=ing.get("amount") or ing.get("quantity") or 0,
                    unit=ing.get("unit") or ""
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
                recommend_reason="GPTによる提案レシピです",
            )

        selected = result[0]
        ingredient_items = [
            IngredientItem(
                ingredient_id=ing.get("ingredient_id") or ing.get("name"),
                quantity=ing.get("quantity") or ing.get("amount") or 0,
                unit=ing.get("unit") or ""
            )
            for ing in selected["ingredients"]
        ]
        step_items = [StepItem(**step) for step in selected["steps"]]

        return RecipeRecommendationResponse(
            name=selected["name"],
            ingredients=ingredient_items,
            steps=step_items,
            missing_ingredients=[],
            recommend_score=1.0,
            recommend_reason="おすすめレシピを見つけました！",
        )
