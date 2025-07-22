from fastapi import APIRouter, Request
from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError
from linebot.models import MessageEvent, TextMessage, TextSendMessage
import asyncio
import base64

from app.schemas.recipe_schema import AvailableIngredient
from app.services.recommender import RecipeRecommender
from app.core.db import get_collection
from app.services.db_service import save_user_recipe, get_user_state, update_step
from app.services.line_bot_service import generate_trivia, verify_step_image
from app.core.config import settings

router = APIRouter(prefix="/line", tags=["LINE Bot"])

line_bot_api = LineBotApi(settings.LINE_CHANNEL_ACCESS_TOKEN)
handler = WebhookHandler(settings.LINE_CHANNEL_SECRET)

ingredient_col = get_collection("user_ingredients")
recommender = RecipeRecommender()

@router.post("/callback")
async def callback(request: Request):
    signature = request.headers.get("X-Line-Signature")
    body = await request.body()
    try:
        handler.handle(body.decode(), signature)
    except InvalidSignatureError:
        return {"error": "Invalid signature"}
    return {"status": "ok"}

@handler.add(MessageEvent, message=TextMessage)
def handle_text_message(event):
    user_id = event.source.user_id
    text = event.message.text.strip()

    # ✅ 先立即回复
    line_bot_api.reply_message(event.reply_token, TextSendMessage(text="処理中です…"))

    asyncio.get_event_loop().create_task(process_text_async(user_id, text))

async def process_text_async(user_id, text):
    if text == "食材を登録する":
        link_url = f"http://192.168.197.95:5173/?user_id={user_id}"
        reply_text = f"こちらから登録ページを開いてください👇\n{link_url}"

    elif text == "スタート":
        user_doc = await ingredient_col.find_one({"user_id": user_id})
        if not user_doc or "ingredients" not in user_doc:
            reply_text = "食材が登録されていません。まず食材を登録してください。"
        else:
            # ✅ 获取完整库存对象
            available_ingredients = [
                AvailableIngredient(**{
                    "name": ing.get("ingredient_id") or ing.get("name"),
                    "quantity": float(ing.get("quantity", 0)),
                    "unit": ing.get("unit", "")
                })
                for ing in user_doc["ingredients"]
            ]

            required_ingredients = []  # 未来可以支持用户选择必用食材
            max_cooking_time = 30

            # ✅ 调用升级后的推荐器
            recipe = await recommender.recommend_recipe(
                available_ingredients=available_ingredients,
                required_ingredients=required_ingredients,
                max_cooking_time=max_cooking_time
            )

            if not recipe:
                reply_text = "条件に合うレシピが見つかりませんでした。"
            else:
                save_user_recipe(user_id, recipe.model_dump())
                first_step = recipe.steps[0].instruction
                reply_text = f"レシピ「{recipe.name}」を見つけました！\n\nステップ1: {first_step}\nこの工程が終わったら写真を送ってください📸"

    elif text == "次へ":
        user_state = get_user_state(user_id)
        if not user_state or "recipe" not in user_state:
            reply_text = "ステップが存在しません。スタートからやり直してください。"
        else:
            step_index = user_state.get("current_step", 0) + 1
            recipe = user_state["recipe"]
            if step_index < len(recipe["steps"]):
                next_step = recipe["steps"][step_index]["instruction"]
                update_step(user_id, step_index)
                reply_text = f"📝 手動で次のステップに進みます。\n\nステップ{step_index + 1}: {next_step}\n終わったら写真を送ってください📸"

                trivia = await generate_trivia(next_step)
                if trivia and "今回は暇ではない" not in trivia:
                    reply_text += f"\n\n🧠 うんちく:\n{trivia}"
            else:
                reply_text = "🎉 全てのステップが完了しました！お疲れ様でした。"

    else:
        reply_text = '「スタート」または「次へ」と送ってください。'

    # ✅ 最终推送
    if reply_text:
        line_bot_api.push_message(user_id, TextSendMessage(text=reply_text))
