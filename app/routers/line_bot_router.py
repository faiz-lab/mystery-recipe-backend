from fastapi import APIRouter, Request
from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError
from linebot.models import MessageEvent, TextMessage, ImageMessage, TextSendMessage
import asyncio
import base64

from app.core.config import settings
from app.core.db import db
from app.services.gpt_service import generate_trivia, verify_step_image

router = APIRouter(prefix="/line", tags=["LINE Bot"])

line_bot_api = LineBotApi(settings.LINE_CHANNEL_ACCESS_TOKEN)
handler = WebhookHandler(settings.LINE_CHANNEL_SECRET)


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
def handle_text(event):
    user_id = event.source.user_id
    text = event.message.text.strip()

    line_bot_api.reply_message(event.reply_token, TextSendMessage(text="処理中です…"))
    asyncio.get_event_loop().create_task(process_text(user_id, text))


async def process_text(user_id: str, text: str):
    if text == "食材を登録する":
        link_url = f"https://example.com/?user_id={user_id}"
        reply = f"こちらから登録ページを開いてください👇\n{link_url}"
        line_bot_api.push_message(user_id, TextSendMessage(text=reply))
        return

    if text == "スタート":
        user = await db.users.find_one({"_id": user_id})
        if not user or "current_recipe" not in user:
            line_bot_api.push_message(user_id, TextSendMessage(text="レシピが登録されていません。"))
            return
        await db.users.update_one({"_id": user_id}, {"$set": {"current_step": 0}})
        first_step = user["current_recipe"]["steps"][0]["instruction"]
        trivia = await generate_trivia(first_step)
        reply = f"ステップ1: {first_step}" + (f"\n\n🧠 うんちく:\n{trivia}" if trivia else "")
        line_bot_api.push_message(user_id, TextSendMessage(text=reply))
        return

    if text == "次へ":
        user = await db.users.find_one({"_id": user_id})
        if not user or "current_recipe" not in user:
            line_bot_api.push_message(user_id, TextSendMessage(text="最初からやり直してください。"))
            return
        step_index = user.get("current_step", 0)
        recipe = user["current_recipe"]
        if step_index >= len(recipe["steps"]):
            line_bot_api.push_message(user_id, TextSendMessage(text="全てのステップが完了しました！"))
            return
        step = recipe["steps"][step_index]["instruction"]
        trivia = await generate_trivia(step)
        await db.users.update_one({"_id": user_id}, {"$set": {"current_step": step_index + 1}})
        reply = f"ステップ{step_index + 1}: {step}" + (f"\n\n🧠 うんちく:\n{trivia}" if trivia else "")
        line_bot_api.push_message(user_id, TextSendMessage(text=reply))
        return

    line_bot_api.push_message(user_id, TextSendMessage(text='「スタート」または「次へ」と送ってください。'))


@handler.add(MessageEvent, message=ImageMessage)
def handle_image(event):
    user_id = event.source.user_id
    message_id = event.message.id
    line_bot_api.reply_message(event.reply_token, TextSendMessage(text="画像を確認しています..."))
    asyncio.get_event_loop().create_task(process_image(user_id, message_id))


async def process_image(user_id: str, message_id: str):
    user = await db.users.find_one({"_id": user_id})
    if not user or "current_recipe" not in user:
        line_bot_api.push_message(user_id, TextSendMessage(text="レシピ情報が見つかりません。"))
        return
    step_index = user.get("current_step", 0)
    recipe = user["current_recipe"]
    instructions = "\n".join(
        [f"ステップ{i+1}: {s['instruction']}" for i, s in enumerate(recipe["steps"][: step_index + 1])]
    )
    content = line_bot_api.get_message_content(message_id)
    image_bytes = b"".join(chunk for chunk in content.iter_content())
    base64_image = base64.b64encode(image_bytes).decode("utf-8")
    result = await verify_step_image(instructions, base64_image)

    if "はい" in result:
        if step_index < len(recipe["steps"]):
            next_step_text = recipe["steps"][step_index]["instruction"]
            trivia = await generate_trivia(next_step_text)
            reply = f"✅ OK！\nステップ{step_index + 1}: {next_step_text}" + (f"\n\n🧠 うんちく:\n{trivia}" if trivia else "")
            await db.users.update_one({"_id": user_id}, {"$set": {"current_step": step_index + 1}})
        else:
            reply = "🎉 料理が完成しました！"
    else:
        reply = "😅 画像が手順と合っていないようです。"

    line_bot_api.push_message(user_id, TextSendMessage(text=reply))
