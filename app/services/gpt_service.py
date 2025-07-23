import openai
from app.core.config import settings

openai_client = openai.AsyncOpenAI(api_key=settings.OPENAI_API_KEY)

async def generate_trivia(step_text: str) -> str:
    """Generate short trivia text for the given cooking step."""
    try:
        response = await openai_client.chat.completions.create(
            model=settings.OPENAI_MODEL,
            messages=[
                {
                    "role": "user",
                    "content": f"""
                    以下の料理手順に関連する豆知識を1文で教えてください。
                    暇ならおすすめの音楽も教えてください。
                    忙しい場合は『今回は暇ではない』とだけ答えてください。

                    手順:
                    {step_text}
                    """,
                }
            ],
            max_tokens=300,
        )
        return response.choices[0].message.content.strip()
    except Exception as e:  # pragma: no cover - OpenAI failure
        return f"(Trivia生成エラー: {e})"


async def verify_step_image(instructions: str, base64_image: str) -> str:
    """Verify step image with GPT. Return 'はい' or 'いいえ'."""
    try:
        response = await openai_client.chat.completions.create(
            model=settings.OPENAI_MODEL,
            messages=[
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": f"""
                            以下の全体手順を参考に、最新の手順が画像と合っているか判定してください。
                            回答は「はい」または「いいえ」だけ。

                            全体手順:
                            {instructions}
                            """,
                        },
                        {
                            "type": "image_url",
                            "image_url": {"url": f"data:image/jpeg;base64,{base64_image}"},
                        },
                    ],
                }
            ],
            max_tokens=50,
        )
        return response.choices[0].message.content.strip().lower()
    except Exception as e:  # pragma: no cover - OpenAI failure
        return f"(画像判定エラー: {e})"
