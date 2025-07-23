from datetime import datetime
from app.core.db import get_collection

# 获取 MongoDB 集合
user_state_col = get_collection("users")

# === 保存用户食谱 ===
def save_user_recipe(user_id: str, recipe: dict):
    """
    保存用户当前的食谱，并将 current_step 重置为 0。
    如果用户已存在，覆盖 recipe。
    """
    now = datetime.now()
    user_state_col.update_one(
        {"_id": user_id},
        {
            "$set": {
                "current_recipe": recipe,
                "current_step": 0,
            },
            "$setOnInsert": {"created_at": now}
        },
        upsert=True
    )

# === 获取用户状态 ===
def get_user_state(user_id: str) -> dict:
    """
    返回用户状态文档，包含 recipe 和 current_step。
    如果不存在，返回 None。
    """
    return user_state_col.find_one({"user_id": user_id})

# === 更新用户当前步骤 ===
def update_step(user_id: str, step_index: int):
    """
    更新 current_step。
    """
    user_state_col.update_one(
        {"user_id": user_id},
        {"$set": {"current_step": step_index, "updated_at": datetime.utcnow()}}
    )

# === 重置用户状态 ===
def reset_user_state(user_id: str):
    """
    删除用户的 current_step 和 recipe（用于重新开始）。
    """
    user_state_col.update_one(
        {"user_id": user_id},
        {"$unset": {"recipe": "", "current_step": ""}}
    )
