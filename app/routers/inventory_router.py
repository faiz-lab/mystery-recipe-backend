from fastapi import APIRouter, HTTPException
from datetime import datetime

from app.core.db import db
from app.schemas.inventory_schema import InventoryRequest, InventoryResponse, InventoryPatchRequest

router = APIRouter(prefix="/users", tags=["Inventory"])

# ✅ 获取用户库存
@router.get("/{user_id}/inventory", response_model=InventoryResponse)
async def get_inventory(user_id: str):
    user = await db.users.find_one({"_id": user_id}, {"inventory": 1, "updated_at": 1})
    if not user:
        return InventoryResponse(user_id=user_id, inventory=[], updated_at=None)

    return InventoryResponse(
        user_id=user_id,
        inventory=user.get("inventory", []),
        updated_at=user.get("updated_at")
    )


# ✅ PATCH 更新用户库存（部分更新）
@router.patch("/{user_id}/inventory")
async def patch_inventory(user_id: str, req: InventoryPatchRequest):
    # ✅ 获取当前库存
    user = await db.users.find_one({"_id": user_id})
    current_inventory = user.get("inventory", []) if user else []
    inventory_map = {item["name"]: item for item in current_inventory}

    # ✅ 更新操作
    for item in req.update or []:
        inventory_map[item.name] = item.dict()

    # ✅ 删除操作
    for name in req.remove or []:
        inventory_map.pop(name, None)

    # ✅ 新库存列表
    new_inventory = list(inventory_map.values())

    # ✅ 保存到 MongoDB
    result = await db.users.update_one(
        {"_id": user_id},
        {"$set": {"inventory": new_inventory, "updated_at": datetime.utcnow()}},
        upsert=True
    )

    return {
        "success": True,
        "message": "Inventory patched successfully",
        "modified_count": result.modified_count,
        "upserted_id": str(result.upserted_id) if result.upserted_id else None
    }