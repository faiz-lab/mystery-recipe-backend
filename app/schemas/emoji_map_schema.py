from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime

# =============== 完整内部数据模型 ===============

class IngredientEmojiMapSchema(BaseModel):
    id: str = Field(alias="_id")  # 通常和 ingredient_master._id 绑定
    emoji: str
    source: str  # e.g. "preset", "gpt_suggested", "user_voted"
    confidence_score: float
    updated_at: datetime

# =============== 创建请求体 ===============

class IngredientEmojiMapCreateRequest(BaseModel):
    id: str  # 绑定的 standard_name (或 ingredient_id 逻辑主键)
    emoji: str
    source: str
    confidence_score: float

# =============== 更新请求体 ===============

class IngredientEmojiMapUpdateRequest(BaseModel):
    emoji: Optional[str] = None
    source: Optional[str] = None
    confidence_score: Optional[float] = None

# =============== 查询返回响应体 ===============

class IngredientEmojiMapResponse(BaseModel):
    id: str = Field(alias="_id")
    emoji: str
    source: str
    confidence_score: float
    updated_at: datetime
