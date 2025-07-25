from fastapi import APIRouter, Query
from typing import List
from collections import defaultdict
from app.core.db import get_collection
import openai
from app.core.config import settings
from datetime import datetime
from pydantic import BaseModel
from app.schemas.inventory_schema import InventoryItem
from app.core.db import db

ingredient_col = get_collection("ingredient_list")
router = APIRouter(prefix="/ingredients", tags=["Ingredients"])

# ✅ 初始化 OpenAI 客户端
openai.api_key = settings.OPENAI_API_KEY

@router.get("")
async def get_ingredients(
    search: str = Query("", description="検索キーワード"),
    categories: List[str] = Query([], description="カテゴリフィルター"),
    group_by: str = Query("", description="グルーピングキー（例: category)")
):
    query = {}
    if search:
        query["$or"] = [
            {"name": {"$regex": search, "$options": "i"}},
            {"synonyms": {"$regex": search, "$options": "i"}}
        ]
    if categories:
        query["category"] = {"$in": categories}

    # ✅ 如果需要分组返回
    if group_by == "category":
        cursor = ingredient_col.find(query)
        docs = await cursor.to_list(length=None)

        grouped = defaultdict(list)
        for doc in docs:
            grouped[doc.get("category", "その他")].append({
                "name": doc.get("name", ""),
                "units": doc.get("units", []),
            })
        return {"group_by": "category", "data": grouped, "source": "db"}

    # ✅ 第一步：MongoDB 正常查询
    cursor = ingredient_col.find(query)
    docs = await cursor.to_list(length=None)

    # 如果 MongoDB 命中 → 直接返回
    if docs:
        return {
            "results": [
                {
                    "name": doc.get("name", ""),
                    "highlight_name": (
                        doc.get("name", "").replace(search, f"<mark>{search}</mark>")
                        if search else doc.get("name", "")
                    ),
                    "category": doc.get("category", ""),
                    "units": doc.get("units", []),
                }
                for doc in docs
            ],
            "total": len(docs),
            "source": "db"
        }

    # ✅ 第二步：调用 OpenAI 生成候选
    if search:
        try:
            gpt_response = openai.OpenAI().chat.completions.create(
                model="gpt-4o",  # 可换成 gpt-4o
                messages=[
                    {
                        "role": "system",
                        "content": "あなたは食材名のマッチングエンジンです。"
                    },
                    {
                        "role": "user",
                        "content": f"""
                        ユーザーが入力した食材: {search}
                        以下のルールで候補を3つ提案してください：
                        - 日本語の食材名のみ
                        - 食材名だけ、カンマ区切り
                        """
                    }
                ],
                max_tokens=100
            )
            suggestions_text = gpt_response.choices[0].message.content
            if suggestions_text is not None:
                suggestions = [s.strip() for s in suggestions_text.split(",") if s.strip()]
            else:
                suggestions = []
        except Exception as e:
            print(f"OpenAI API error: {e}")
            suggestions = []

        # ✅ 如果 GPT 提供了候选 → 回到 MongoDB 再查
        fallback_results = []
        if suggestions:
            query = {
                "$or": [
                    {"name": {"$in": suggestions}},
                    {"synonyms": {"$in": suggestions}}
                ]
            }
            cursor = ingredient_col.find(query)
            fallback_docs = await cursor.to_list(length=None)

            for doc in fallback_docs:
                fallback_results.append({
                    "name": doc.get("name", ""),
                    "highlight_name": doc.get("name", ""),
                    "category": doc.get("category", ""),
                    "units": doc.get("units", []),
                })

    # ✅ 搜索词为空 → 返回空数组
    return {"results": [], "total": 0, "source": "db"}


class IngredientRegisterRequest(BaseModel):
    user_id: str
    ingredients: List[InventoryItem]
