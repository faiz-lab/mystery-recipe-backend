from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime

# ✅ 单个库存食材项
class InventoryItem(BaseModel):
    name: str = Field(..., description="食材名（例: 玉ねぎ）")
    quantity: float = Field(..., description="数量（例: 200）")
    unit: str = Field(..., description="単位（例: g, 個）")

# ✅ 全量更新请求体（PUT /users/{user_id}/inventory）
class InventoryRequest(BaseModel):
    items: List[InventoryItem]

# ✅ PATCH 部分更新请求体
class InventoryPatchRequest(BaseModel):
    update: Optional[List[InventoryItem]] = Field(default_factory=list, description="追加または更新する食材リスト")
    remove: Optional[List[str]] = Field(default_factory=list, description="削除する食材名のリスト")

# ✅ 获取库存响应体（GET /users/{user_id}/inventory）
class InventoryResponse(BaseModel):
    user_id: str = Field(..., description="ユーザーID")
    inventory: List[InventoryItem] = Field(default_factory=list, description="現在の在庫")
    updated_at: Optional[datetime] = Field(None, description="最後更新日時")
