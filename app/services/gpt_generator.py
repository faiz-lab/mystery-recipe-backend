import openai
from app.core import config
from app.core.config import settings

# 初始化 openai 连接
client = openai.AsyncOpenAI(api_key=settings.OPENAI_API_KEY)

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
