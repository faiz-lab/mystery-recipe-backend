from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime
from bson import ObjectId

class PyObjectId(ObjectId):
    @classmethod
    def __get_validators__(cls):
        yield cls.validate

    @classmethod
    def validate(cls, v):
        if isinstance(v, ObjectId):
            return str(v)
        if isinstance(v, str):
            return v
        raise TypeError("Invalid ObjectId")

# ---------- 嵌套子对象 ----------

class IngredientItem(BaseModel):
    ingredient_id: str
    quantity: float
    unit: str

class StepItem(BaseModel):
    step_no: int
    instruction: str

# ---------- 内部存储模型 ----------

class RecipeSchema(BaseModel):
    id: PyObjectId = Field(alias="_id")
    name: str
    description: Optional[str] = None
    image_url: Optional[str] = None
    ingredients: List[IngredientItem]
    steps: List[StepItem]
    tags: List[str]
    cuisine: str
    difficulty: str
    cooking_time: int
    servings: int
    generated_by: str
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    class Config:
        json_encoders = {ObjectId: str}

# ---------- 推荐接口响应模型 ----------

class RecipeRecommendationResponse(BaseModel):
    name: str
    ingredients: List[IngredientItem]
    steps: List[StepItem]
    missing_ingredients: List[str]
    recommend_score: float
    recommend_reason: str
