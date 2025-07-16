import unicodedata
import re
from enum import Enum
from typing import List, Optional

from fastapi import APIRouter
from pydantic import BaseModel
from rapidfuzz import process

from app.core.db import get_collection
from app.core.unit_converter import convert_to_standard
from app.services.gpt_generator import call_openai_suggest

router = APIRouter(prefix="/ingredients")
ingredient_col = get_collection("ingredient_master")
feedback_col = get_collection("ingredient_feedback")


# ---------- Enum ----------
class CategoryEnum(str, Enum):
    vegetable = "vegetable"
    meat = "meat"
    dairy = "dairy"
    seafood = "seafood"
    grain = "grain"
    other = "other"


# ---------- Models ----------
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


# ---------- Utils ----------
def normalize_input(text: str) -> str:
    return unicodedata.normalize("NFKC", text.strip().lower())


def normalize_list(strings: List[str]) -> List[str]:
    return list(set(normalize_input(s) for s in strings))


def build_response_with_unit(status: str, doc: dict, quantity: float, unit: str) -> dict:
    standard_unit, standard_quantity = convert_to_standard(unit, quantity, doc["internal_code"])
    return {
        "status": status,
        "data": {
            "standard_name": doc["standard_name"],
            "internal_code": doc["internal_code"],
            "synonyms": sorted(set(doc.get("synonyms", []))),
            "emoji": doc.get("emoji", ""),
            "category": doc.get("category", "other"),
            "confidence": doc.get("confidence", 1.0),
            "quantity": quantity,
            "unit": unit,
            "standard_quantity": standard_quantity,
            "standard_unit": standard_unit,
            "source": status
        }
    }


# ---------- /resolve ----------
@router.post("/resolve")
async def resolve_ingredient(request: NormalizeRequest):
    raw = request.raw_input.strip()

    # Step 1: 解析「名称 + 数量 + 单位」
    match = re.match(r"([\wぁ-んァ-ン一-龥]+)\s*([\d\.]+)?\s*([^\d\s]*)", raw)
    if not match:
        return {"status": "invalid_format", "message": "形式を確認してください（例: 玉ねぎ 1個）"}

    name = match.group(1)
    quantity = float(match.group(2)) if match.group(2) else 1
    unit = match.group(3) or "個"
    user_input = normalize_input(name)

    # Step 2: 精确匹配
    doc = await ingredient_col.find_one({
        "$or": [
            {"standard_name": user_input},
            {"internal_code": user_input},
            {"synonyms": user_input}
        ]
    })
    if doc:
        return build_response_with_unit("hit", doc, quantity, unit)

    # Step 3: 模糊匹配
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
            return build_response_with_unit("fuzzy", candidates[best_match], quantity, unit)

    # Step 4: GPT 补充
    result = await call_openai_suggest(user_input)
    if result:
        slug_code = normalize_input(result["internal_code"])
        existing = await ingredient_col.find_one({"internal_code": slug_code})

        if existing:
            norm_user_input = normalize_input(request.raw_input)
            if norm_user_input not in normalize_list(existing.get("synonyms", [])):
                await ingredient_col.update_one(
                    {"_id": existing["_id"]},
                    {"$addToSet": {"synonyms": norm_user_input}}
                )
                existing["synonyms"].append(request.raw_input)
            return build_response_with_unit("hit_gpt", existing, quantity, unit)

        return {"status": "suggest", "data": result}

    return {
        "status": "not_found",
        "message": "該当する食材を見つかりませんでした。"
    }


# ---------- /feedback ----------
@router.post("/feedback")
async def feedback_handler(request: FeedbackRequest):
    await feedback_col.insert_one(request.model_dump())

    if not request.accepted:
        return {"success": True}

    doc = request.correction or await call_openai_suggest(request.user_input)

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


# ---------- /create ----------
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
