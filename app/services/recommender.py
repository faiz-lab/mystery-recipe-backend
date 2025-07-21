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
        self.recipe_col = recipe_col or get_collection("recipe_list")

    async def recommend_recipe(
        self,
        available_ingredients: List[dict],  # [{ name, quantity, unit }]
        required_ingredients: List[str],
        max_cooking_time: int,
    ) -> Optional[RecipeRecommendationResponse]:

        available_ids = [item.get("name") for item in available_ingredients]

        print("[RecommendRequest]")
        pprint.pprint({"available_ids": available_ids, "required_ids": required_ingredients})

        pipeline = [
            {
                "$match": {
                    "$expr": {
                        "$setIsSubset": [
                            {
                                "$map": {
                                    "input": "$ingredients",
                                    "as": "ing",
                                    "in": "$$ing.name"
                                }
                            },
                            available_ids
                        ]
                    },
                    "ingredients.name": {"$all": required_ingredients},
                    "cooking_time": {"$lte": max_cooking_time}
                }
            },
            {"$sample": {"size": 1}}
        ]

        cursor = await self.recipe_col.aggregate(pipeline)
        result = await cursor.to_list(length=1)

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
        ingredient_items = [IngredientItem(**ing) for ing in selected["ingredients"]]
        step_items = [StepItem(**step) for step in selected["steps"]]

        return RecipeRecommendationResponse(
            name=selected["name"],
            ingredients=ingredient_items,
            steps=step_items,
            missing_ingredients=[],
            recommend_score=1.0,
            recommend_reason="おすすめレシピを見つけました！",
        )
