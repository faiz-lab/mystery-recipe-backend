from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime

# ---------- 完整内部数据模型 ----------

class IngredientMasterSchema(BaseModel):
    id: Optional[str] = Field(default=None, alias="_id")
    standard_name: str
    synonyms: List[str]
    emoji: Optional[str]
    category: str
    confidence: float
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

# ---------- 创建请求体 ----------

class IngredientMasterCreateRequest(BaseModel):
    standard_name: str
    synonyms: List[str]
    emoji: Optional[str] = None
    category: str
    confidence: float

# ---------- 更新请求体 (全部字段可选) ----------

class IngredientMasterUpdateRequest(BaseModel):
    standard_name: Optional[str] = None
    synonyms: Optional[List[str]] = None
    emoji: Optional[str] = None
    category: Optional[str] = None
    confidence: Optional[float] = None

# ---------- 查询返回响应体 ----------

class IngredientMasterResponse(BaseModel):
    id: str = Field(alias="_id")
    standard_name: str
    synonyms: List[str]
    emoji: Optional[str]
    category: str
    confidence: float
    created_at: datetime
    updated_at: datetime
