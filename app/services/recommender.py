import random
import json
from typing import List, Optional

from app.schemas.recipe_schema import (
    IngredientItem,
    StepItem,
    RecipeRecommendationResponse,
    AvailableIngredient,
    RequiredIngredient,
)
from datetime import datetime
from app.core.db import db, get_collection
from app.services.gpt_generator import generate_recipe_by_gpt


class RecipeRecommender:
    """Recipe recommendation service."""

    def __init__(self, recipe_col=None):
        self.recipe_col = recipe_col or get_collection("recipe_list")

    async def _find_from_db(
        self,
        available: List[str],
        required: List[str],
        max_time: int,
    ) -> Optional[dict]:
        """Find a matching recipe document from MongoDB."""
        cursor = self.recipe_col.find({"cooking_time": {"$lte": max_time}})
        docs = await cursor.to_list(length=None)
        candidates = []
        for doc in docs:
            names = [ing.get("ingredient_id") or ing.get("name") for ing in doc.get("ingredients", [])]
            if not all(r in names for r in required):
                continue
            if not set(names).issubset(set(available)):
                continue
            candidates.append(doc)
        if not candidates:
            return None
        return random.choice(candidates)

    async def recommend_recipe(
        self,
        available_ingredients: List[AvailableIngredient],
        required_ingredients: List[RequiredIngredient],
        max_cooking_time: int,
    ) -> Optional[RecipeRecommendationResponse]:
        """Recommend recipe based on ingredients and cooking time."""
        available_names = [item.name for item in available_ingredients]
        required_names = [item.name for item in required_ingredients]

        recipe_doc = await self._find_from_db(available_names, required_names, max_cooking_time)

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