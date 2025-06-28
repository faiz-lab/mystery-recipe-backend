from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime
from enum import Enum

class CategoryEnum(str, Enum):
    vegetable = "vegetable"
    meat = "meat"
    dairy = "dairy"
    seafood = "seafood"
    grain = "grain"
    other = "other"

class IngredientMasterSchema(BaseModel):
    id: Optional[str] = Field(default=None, alias="_id")
    standard_name: str
    internal_code: str
    synonyms: List[str]
    emoji: Optional[str]
    category: CategoryEnum
    confidence: float = 0.8
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

class IngredientMasterCreateRequest(BaseModel):
    standard_name: str
    internal_code: str
    synonyms: List[str]
    emoji: Optional[str] = None
    category: CategoryEnum
    confidence: float = 0.8

class IngredientMasterUpdateRequest(BaseModel):
    standard_name: Optional[str] = None
    synonyms: Optional[List[str]] = None
    emoji: Optional[str] = None
    category: Optional[CategoryEnum] = None
    confidence: Optional[float] = None

class IngredientMasterResponse(BaseModel):
    id: str = Field(alias="_id")
    standard_name: str
    internal_code: str
    synonyms: List[str]
    emoji: Optional[str]
    category: CategoryEnum
    confidence: float
    created_at: datetime
    updated_at: datetime
