import openai

from app.core.config import settings

# 使用你的 OPENAI API KEY
openai_client = openai.AsyncOpenAI(api_key=settings.OPENAI_API_KEY)


# === Trivia 生成 ===
async def generate_trivia(next_step_text: str) -> str:
    """
    生成豆知识（异步）。
    如果步骤比较忙，GPT 会返回 "今回は暇ではない"。
    """
    try:
        response = await openai_client.chat.completions.create(
            model="gpt-4o",  # 你也可以换成 gpt-4o-mini
            messages=[
                {
                    "role": "user",
                    "content": f"""
                    以下の料理手順で、メインで使用する食材に関する面白い豆知識を1文で教えてください。
                    おすすめの音楽も教えてください。

                    手順：
                    {next_step_text}
                    """
                }
            ],
            max_tokens=300,
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        return f"（Trivia生成エラー: {e}）"


# === 画像验证 ===
async def verify_step_image(current_instructions: str, base64_image: str) -> str:
    """
    GPT 多模态验证，判断当前步骤是否与图片一致。
    返回值： "はい" 或 "いいえ"。
    """
    try:
        response = await openai_client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": f"""
                            以下の全体手順を参考に、最新の手順が画像と合っているか判定してください。
                            回答は「はい」または「いいえ」だけ。

                            全体手順：
                            {current_instructions}
                            """
                        },
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/jpeg;base64,{base64_image}"
                            }
                        }
                    ]
                }
            ],
            max_tokens=300,
        )
        return response.choices[0].message.content.strip().lower()
    except Exception as e:
        return f"（画像判定エラー: {e}）"
