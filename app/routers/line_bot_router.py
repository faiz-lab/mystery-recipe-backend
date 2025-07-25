from fastapi import APIRouter, Request
from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError
from linebot.models import MessageEvent, TextMessage, ImageMessage, TextSendMessage
from datetime import datetime
import asyncio
import base64
import logging

from app.core.config import settings
from app.core.db import db
from app.services.gpt_service import generate_trivia, verify_step_image

# ======================
# 常量 & 初始化
# ======================
router = APIRouter(prefix="/line", tags=["LINE Bot"])
line_bot_api = LineBotApi(settings.LINE_CHANNEL_ACCESS_TOKEN)
handler = WebhookHandler(settings.LINE_CHANNEL_SECRET)
logger = logging.getLogger(__name__)

COMMAND_REGISTER = "食材を登録する"
COMMAND_START = "スタート"
COMMAND_NEXT = "次へ"

# ======================
# 工具函数
# ======================
async def send_message_async(user_id: str, text: str):
    """异步推送消息"""
    await asyncio.to_thread(line_bot_api.push_message, user_id, TextSendMessage(text=text))

async def reply_message_async(reply_token: str, text: str):
    """异步回复用户"""
    await asyncio.to_thread(line_bot_api.reply_message, reply_token, TextSendMessage(text=text))

# ======================
# 通知接口
# ======================
@router.post("/notify")
async def notify_line(data: dict):
    user_id = data.get("user_id")
    message = data.get("message", "登録完了")
    await send_message_async(user_id, message)
    return {"status": "ok"}

# ======================
# 回调接口（LINE Webhook）
# ======================
@router.post("/callback")
async def callback(request: Request):
    signature = request.headers.get("X-Line-Signature")
    body = await request.body()
    try:
        handler.handle(body.decode(), signature)
    except InvalidSignatureError:
        logger.error("Invalid LINE signature")
        return {"error": "Invalid signature"}
    return {"status": "ok"}

# ======================
# 文字消息处理
# ======================
@handler.add(MessageEvent, message=TextMessage)
def handle_text(event):
    asyncio.create_task(process_text(event.source.user_id, event.message.text.strip(), event.reply_token))

async def process_text(user_id: str, text: str, reply_token: str):
    try:
        if text == COMMAND_REGISTER:
            await send_message_async(user_id, f"こちらから登録ページを開いてください👇\nhttps://your-ui-domain?user_id={user_id}")
            return

        if text in (COMMAND_START, "登録完了"):
            await handle_start(user_id)
            return

        if text == COMMAND_NEXT:
            await handle_next_step(user_id)
            return

        await send_message_async(user_id, '「食材を登録する」「スタート」「次へ」のいずれかを送信してください。')

    except Exception as e:
        logger.exception(f"Error processing text: {e}")
        await send_message_async(user_id, "エラーが発生しました。もう一度お試しください。")

# ======================
# 处理「スタート」或「登録完了」
# ======================
async def handle_start(user_id: str):
    user = await db.users.find_one({"_id": user_id})
    recipe = user.get("current_recipe") if user else None

    if not recipe:
        await send_message_async(user_id, "おすすめできるレシピが見つかりませんでした。")
        return

    first_step = recipe["steps"][0]["instruction"]
    servings = recipe.get("servings", "不明")
    reply = (
        f"今回作る料理は『{servings}』の料理です！頑張りましょう！\n\n"
        f"ステップ1: {first_step}\nこの工程が終わったら写真を送ってください📸"
    )

    # 初始化 current_step = 1
    await db.users.update_one({"_id": user_id}, {"$set": {"current_step": 1, "updated_at": datetime.now()}})
    await send_message_async(user_id, reply)

# ======================
# 处理「次へ」
# ======================
async def handle_next_step(user_id: str):
    user = await db.users.find_one({"_id": user_id})
    if not user or "current_recipe" not in user:
        await send_message_async(user_id, "スタートから始めてください。")
        return

    step_index = user.get("current_step", 1)
    recipe = user["current_recipe"]
    recipe_name = recipe.get("name", "不明な料理")
    recipe_url = recipe.get("recipe_url", "")

    if step_index >= len(recipe["steps"]):
        reply = (
            "🎉 全てのステップが完了しました！お疲れ様でした。\n\n"
            f"今回作った料理名は「{recipe_name}」でした！\n\n"
            f"レシピURLはこちら👇\n{recipe_url}"
        )
        await send_message_async(user_id, reply)
        return

    step_text = recipe["steps"][step_index]["instruction"]
    trivia_task = asyncio.create_task(generate_trivia(step_text))
    update_task = asyncio.create_task(
        db.users.update_one({"_id": user_id}, {"$set": {"current_step": step_index + 1, "updated_at": datetime.now()}})
    )
    trivia, _ = await asyncio.gather(trivia_task, update_task)

    reply = f"ステップ{step_index + 1}: {step_text}" + (f"\n\n🧠 うんちく:\n{trivia}" if trivia else "")
    await send_message_async(user_id, reply)

# ======================
# 图片消息处理
# ======================
@handler.add(MessageEvent, message=ImageMessage)
def handle_image(event):
    asyncio.create_task(process_image(event.source.user_id, event.message.id, event.reply_token))

async def process_image(user_id: str, message_id: str, reply_token: str):
    try:
        await reply_message_async(reply_token, "画像を確認しています...")

        user = await db.users.find_one({"_id": user_id})
        if not user or "current_recipe" not in user:
            await send_message_async(user_id, "レシピ情報が見つかりません。")
            return

        step_index = max(user.get("current_step", 1) - 1, 0)
        recipe = user["current_recipe"]

        # 只传递当前步骤及前一步，减少 token 消耗
        relevant_steps = recipe["steps"][max(0, step_index - 1): step_index + 1]
        instructions = "\n".join([f"ステップ{i+1}: {s['instruction']}" for i, s in enumerate(relevant_steps)])

        # 下载图片并转 base64
        content = line_bot_api.get_message_content(message_id)
        image_bytes = b"".join(chunk for chunk in content.iter_content())
        base64_image = base64.b64encode(image_bytes).decode("utf-8")

        result = await verify_step_image(instructions, base64_image)

        if "はい" in result:
            next_index = step_index + 1
            if next_index < len(recipe["steps"]):
                next_step_text = recipe["steps"][next_index]["instruction"]
                trivia = await generate_trivia(next_step_text)

                reply = f"✅ OK！\nステップ{next_index + 1}: {next_step_text}" + (f"\n\n🧠 うんちく:\n{trivia}" if trivia else "")
                await db.users.update_one({"_id": user_id}, {"$set": {"current_step": next_index + 1, "updated_at": datetime.utcnow()}})
            else:
                reply = "🎉 料理が完成しました！"
                await db.users.update_one({"_id": user_id}, {"$set": {"current_step": next_index + 1, "updated_at": datetime.utcnow()}})
        else:
            reply = "😅 画像が手順と合っていないようです。"

        await send_message_async(user_id, reply)

    except Exception as e:
        logger.exception(f"Error processing image: {e}")
        await send_message_async(user_id, "画像処理でエラーが発生しました。もう一度お試しください。")
