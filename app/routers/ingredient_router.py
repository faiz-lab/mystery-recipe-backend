from fastapi import APIRouter
from pydantic import BaseModel
from typing import List
from app.core.db import get_collection

class IngredientItem(BaseModel):
    internal_code: str
    standard_name: str
    emoji: str
    synonyms: List[str]

router = APIRouter(prefix="/ingredients")
ingredient_col = get_collection("ingredient_master")

@router.get("/dictionary", response_model=List[IngredientItem])
async def get_ingredient_dictionary():
    cursor = ingredient_col.find({})
    results = await cursor.to_list(length=None)
    return [
        IngredientItem(
            internal_code=doc["internal_code"],
            standard_name=doc["standard_name"],
            emoji=doc.get("emoji", ""),
            synonyms=doc.get("synonyms", [])
        ).model_dump()  # ⭐ 重点：转换成 dict 返回
        for doc in results
    ]
