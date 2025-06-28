import openai
import json
import re
from app.core import config
from app.core.config import settings

client = openai.AsyncOpenAI(api_key=settings.OPENAI_API_KEY)

def slugify(text: str) -> str:
    return re.sub(r'[^a-z0-9]+', '_', text.lower()).strip('_')

async def generate_recipe_by_gpt(available_ingredients, required_ingredients, max_cooking_time):
    system_prompt = """
    あなたはプロの料理アシスタントです。
    入力条件を参考に、以下のフォーマットでレシピをJSON形式で出力してください。

    【フォーマット】
    {
      "name": "...",
      "description": "...",
      "ingredients": [{"name": "...", "quantity": ..., "unit": "..."}, ...],
      "steps": [{"step_no": 1, "instruction": "..."}, ...],
      "cuisine": "...",
      "tags": ["...", "..."],
      "difficulty": "...",
      "cooking_time": ...,
      "servings": ...,
      "image_url": "...",
      "author": "GPT Generated"
    }
    """

    user_prompt = f"""
    利用可能食材: {available_ingredients}
    必須食材: {required_ingredients}
    調理時間上限: {max_cooking_time}分
    """

    response = await client.chat.completions.create(
        model=settings.OPENAI_MODEL,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ],
        temperature=0.7,
        max_tokens=1000
    )

    reply = response.choices[0].message.content
    return reply


# Function Calling を使った食材標準化関数
async def call_openai_suggest(user_input: str):
    functions = [
        {
            "name": "normalize_ingredient",
            "description": "食材標準化",
            "parameters": {
                "type": "object",
                "properties": {
                    "standard_name": {"type": "string"},
                    "internal_code": {"type": "string"},
                    "synonyms": {"type": "array", "items": {"type": "string"}},
                    "category": {"type": "string", "enum": ["vegetable", "meat", "dairy", "seafood", "grain", "other"]},
                    "emoji": {"type": "string"},
                    "confidence": {"type": "number"}
                },
                "required": ["standard_name", "internal_code", "category", "confidence"]
            }
        }
    ]

    response = await client.chat.completions.create(
        model=settings.OPENAI_MODEL,
        messages=[
            {"role": "system", "content": "ユーザーが入力した食材名を英語に変換して、標準化してください（例：うなぎ → eel）。"},
            {"role": "user", "content": user_input}
        ],
        functions=functions,
        function_call={"name": "normalize_ingredient"},
        temperature=0.1,
        max_tokens=500
    )

    function_args = response.choices[0].message.function_call.arguments
    parsed = json.loads(function_args)

    # 🛠 修正字段
    standard_name = parsed.get("standard_name", "").strip()

    # 如果是日文或空字符串，fallback 到 Unknown
    if not standard_name or any('\u3040' <= ch <= '\u30ff' for ch in standard_name):
        standard_name = "Unknown"

    # standard_name 要首字母大写
    standard_name = standard_name[:1].upper() + standard_name[1:].lower()

    # internal_code 全部小写，仅保留字母
    internal_code = re.sub(r'[^a-z]', '', standard_name.lower())

    parsed["standard_name"] = standard_name
    parsed["internal_code"] = internal_code

    return {
        "standard_name": parsed["standard_name"],
        "internal_code": parsed["internal_code"],
        "synonyms": parsed.get("synonyms", []),
        "category": parsed.get("category", "other"),
        "emoji": parsed.get("emoji", ""),
        "confidence": parsed.get("confidence", 0.8)
    }
