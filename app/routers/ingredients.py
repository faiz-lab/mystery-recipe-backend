from fastapi import APIRouter
from pydantic import BaseModel
from typing import List
from app.db import db

router = APIRouter()

class Ingredient(BaseModel):
    name: str
    icon: str

@router.get("/", response_model=List[Ingredient])
def get_ingredients():
    ingredients = db.ingredients.find()
    return [{"name": i["name"], "icon": i["icon"]} for i in ingredients]

@router.post("/")
def add_ingredient(ingredient: Ingredient):
    db.ingredients.insert_one(ingredient.dict())
    return {"message": "Ingredient added"}
