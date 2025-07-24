from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime
from bson import ObjectId
from app.core.utils import PyObjectId


# ===============================
# 🔹 内部统一模型（后端逻辑 & DB 存储）
# ===============================
class IngredientItem(BaseModel):
    ingredient_id: str = Field(..., description="標準化された食材ID（ingredient_masterに対応）")
    quantity: float = Field(..., description="数量（例: 100）")
    unit: str = Field(..., description="単位（例: g, ml）")


class StepItem(BaseModel):
    step_no: int = Field(..., description="手順番号（1から）")
    instruction: str = Field(..., description="調理手順の説明")


# ===============================
# 🔹 API 入力モデル（フロントエンド → API）
# ===============================
class AvailableIngredient(BaseModel):
    name: str = Field(..., description="食材名（例: キャベツ）")
    quantity: float = Field(..., description="数量（例: 100）")
    unit: str = Field(..., description="単位（例: g, ml）")

class RequiredIngredient(BaseModel):
    name: str = Field(..., description="食材名（例: キャベツ）")
    amount: float = Field(..., description="数量（例: 100）")

class RecipeRecommendationRequest(BaseModel):
    user_id: Optional[str] = None  # ✅ 新增
    max_cooking_time: int = Field(..., description="最大調理時間（分）")
    required_ingredients: List[RequiredIngredient] = Field(default_factory=list, description="必ず使用する食材名（例: ['キャベツ']）")
    available_ingredients: List[AvailableIngredient] = Field(..., description="利用可能な食材リスト [{name, quantity, unit}]")

# ===============================
# 🔹 API 出力モデル（API → フロントエンド）
# ===============================
class RecipeRecommendationResponse(BaseModel):
    name: str = Field(..., description="レシピ名")
    cooking_time: Optional[int] = Field(None, description="調理時間（分）")
    ingredients: List[IngredientItem] = Field(..., description="レシピに必要な食材")
    servings: Optional[int] = Field(None, description="人数分")
    recipe_img_url: Optional[str] = Field(None, description="レシピ画像URL")
    recipe_url: Optional[str] = Field(None, description="参照レシピURL")
    steps: List[StepItem] = Field(..., description="調理手順")
    missing_ingredients: List[str] = Field(default_factory=list, description="不足している食材")
    recommend_score: float = Field(..., description="推薦スコア（例: 1.0）")
    recommend_reason: str = Field(..., description="推薦理由")


# ===============================
# 🔹 内部レシピスキーマ（MongoDB 保存用）
# ===============================
class RecipeSchema(BaseModel):
    id: PyObjectId = Field(alias="_id")
    name: str = Field(..., description="レシピ名")
    description: Optional[str] = Field(None, description="レシピの説明")
    image_url: Optional[str] = Field(None, description="画像URL")
    ingredients: List[IngredientItem] = Field(..., description="レシピに必要な食材")
    steps: List[StepItem] = Field(..., description="調理手順")
    tags: List[str] = Field(default_factory=list, description="タグ（例: ['和食', 'スープ']）")
    cuisine: str = Field(..., description="料理の種類（例: 和食）")
    difficulty: str = Field(..., description="難易度（例: easy, normal, hard）")
    cooking_time: int = Field(..., description="調理時間（分）")
    servings: int = Field(..., description="人数分")
    generated_by: str = Field(..., description="作成者またはGPT")
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    class Config:
        allow_population_by_field_name = True
        json_encoders = {ObjectId: str}
