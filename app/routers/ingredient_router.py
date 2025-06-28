import unicodedata
from enum import Enum
from typing import List, Optional

from fastapi import APIRouter
from pydantic import BaseModel
from rapidfuzz import process

from app.core.db import get_collection
from app.services.gpt_generator import call_openai_suggest

router = APIRouter(prefix="/ingredients")
ingredient_col = get_collection("ingredient_master")
feedback_col = get_collection("ingredient_feedback")


class CategoryEnum(str, Enum):
    vegetable = "vegetable"
    meat = "meat"
    dairy = "dairy"
    seafood = "seafood"
    grain = "grain"
    other = "other"


class IngredientMasterSchema(BaseModel):
    id: Optional[str] = None
    standard_name: str
    internal_code: str
    synonyms: List[str]
    emoji: Optional[str]
    category: CategoryEnum
    confidence: float = 0.8


class NormalizeRequest(BaseModel):
    raw_input: str


class CorrectionData(BaseModel):
    standard_name: str
    internal_code: str
    synonyms: List[str]
    emoji: Optional[str] = None
    category: CategoryEnum
    confidence: float = 0.8


class FeedbackRequest(BaseModel):
    user_input: str
    accepted: bool
    correction: Optional[CorrectionData] = None

def normalize_list(strings: List[str]) -> List[str]:
    return list(set(normalize_input(s) for s in strings))

def normalize_input(text: str) -> str:
    return unicodedata.normalize("NFKC", text.strip().lower())

def build_response(status: str, doc: dict) -> dict:
    return {
        "status": status,
        "data": {
            "standard_name": doc["standard_name"],
            "internal_code": doc["internal_code"],
            "synonyms": sorted(set(doc.get("synonyms", []))),
            "emoji": doc.get("emoji", ""),
            "category": doc.get("category", "other"),
            "confidence": doc.get("confidence", 1.0),
        }
    }

# --- /resolve Endpoint ---

@router.post("/resolve")
async def resolve_ingredient(request: NormalizeRequest):
    user_input = normalize_input(request.raw_input)

    # 1. 精确查找
    doc = await ingredient_col.find_one({
        "$or": [
            {"standard_name": user_input},
            {"internal_code": user_input},
            {"synonyms": user_input}
        ]
    })
    if doc:
        return build_response("hit", doc)

    # 2. 模糊匹配
    all_docs = await ingredient_col.find({}).to_list(length=None)
    candidates = {}
    for d in all_docs:
        fields = [d["standard_name"], d["internal_code"]] + d.get("synonyms", [])
        for s in fields:
            norm = normalize_input(s)
            if norm not in candidates:
                candidates[norm] = d

    match_result = process.extractOne(user_input, list(candidates.keys()))
    if match_result:
        best_match, score, _ = match_result
        if score >= 85:
            return build_response("fuzzy", candidates[best_match])

    # 3. GPT 兜底
    result = await call_openai_suggest(user_input)
    if result:
        slug_code = normalize_input(result["internal_code"])
        existing = await ingredient_col.find_one({"internal_code": slug_code})
        if existing:
            norm_user_input = normalize_input(request.raw_input)
            if norm_user_input not in [normalize_input(s) for s in existing.get("synonyms", [])]:
                await ingredient_col.update_one(
                    {"_id": existing["_id"]},
                    {"$addToSet": {"synonyms": norm_user_input}}
                )
                existing["synonyms"].append(request.raw_input)
            return build_response("hit_gpt", existing)

        return {"status": "suggest", "data": result}

    return {
        "status": "not_found",
        "message": "該当する食材を見つかりませんでした。"
    }

@router.post("/feedback")
async def feedback_handler(request: FeedbackRequest):
    await feedback_col.insert_one(request.model_dump())

    if not request.accepted:
        return {"success": True}

    doc = request.correction or await call_openai_suggest(request.user_input)

    # 🛠 确保 doc 是 CorrectionData 类型
    if isinstance(doc, dict):
        doc = CorrectionData(**doc)

    doc.synonyms = normalize_list(doc.synonyms)

    exist = await ingredient_col.find_one({"internal_code": doc.internal_code})
    if not exist:
        await ingredient_col.insert_one({
            "internal_code": doc.internal_code,
            "standard_name": doc.standard_name,
            "synonyms": doc.synonyms,
            "emoji": doc.emoji or "",
            "category": doc.category.value,
            "confidence": doc.confidence,
            "source": "gpt+user"
        })

    return {"success": True}


@router.post("/create", response_model=IngredientMasterSchema)
async def create_ingredient(ingredient: IngredientMasterSchema):
    clean_synonyms = normalize_list(ingredient.synonyms)
    clean_internal_code = normalize_input(ingredient.internal_code)

    data = {
        "standard_name": ingredient.standard_name,
        "internal_code": clean_internal_code,
        "synonyms": clean_synonyms,
        "emoji": ingredient.emoji or "",
        "category": ingredient.category.value,
        "confidence": ingredient.confidence,
        "source": "manual"
    }

    await ingredient_col.insert_one(data)
    return IngredientMasterSchema(**data)
