from datetime import datetime, timezone
from fastapi import APIRouter, HTTPException
from linebot import LineBotApi
from app.core.config import settings
from app.core.db import db
from app.routers.line_bot_router import send_message_async
from app.schemas.recipe_schema import RecipeRecommendationResponse, RecipeRecommendationRequest
from app.services.recommender import RecipeRecommender

router = APIRouter(prefix="/recipes", tags=["Recipes"])
recommender = RecipeRecommender()
line_bot_api = LineBotApi(settings.LINE_CHANNEL_ACCESS_TOKEN)


@router.post("/recommendations", response_model=RecipeRecommendationResponse)
async def recommend_recipes(req: RecipeRecommendationRequest):
    """
    Recommend a recipe, save it to the user state, and send an initial message to LINE user.
    """
    # Step 1: 调用推荐逻辑
    recipe = await recommender.recommend_recipe(
        available_ingredients=req.available_ingredients,
        required_ingredients=req.required_ingredients,
        max_cooking_time=req.max_cooking_time,
    )

    if not recipe:
        raise HTTPException(status_code=404, detail="条件に合うレシピが見つかりませんでした")

    # Step 2: 保存用户状态
    if req.user_id:
        await db.users.update_one(
            {"_id": req.user_id},
            {
                "$set": {
                    "current_recipe": recipe.model_dump(),  # 保存推荐结果
                    "current_step": 0,  # 初始化步骤
                    "updated_at": datetime.now(timezone.utc),
                }
            },
            upsert=True,
        )

        # Step 3: 推送 LINE 消息（尝试 catch 异常）
        try:
            recipe_data = recipe.model_dump()
            first_step = recipe_data["steps"][0]["instruction"]
            servings = recipe_data.get("servings", "不明")
            message = (
                f"ピッタリのレシピが見つかりました！\n\n今回作る料理は『{servings}』の料理です！頑張りましょう💪！\n\n"
                f"ステップ1: {first_step}\n\nこの工程が終わったら写真を送ってください📸"
            )
            # ✅ 更新 current_step（表示用户完成第0步，下一次是第1步）
            await db.users.update_one(
                {"_id": req.user_id},
                {"$set": {"current_step": 1, "updated_at": datetime.now(timezone.utc)}}
            )
            await send_message_async(req.user_id, message)
        except Exception as e:  # LINE 推送失败不影响主逻辑
            print(f"[LINE Push Error] user_id={req.user_id}, error={e}")

    return recipe
