# app/core/auth.py
import os
import httpx
from fastapi import Request, HTTPException

CLERK_SECRET_KEY = os.getenv("CLERK_SECRET_KEY")
CLERK_BASE_URL = "https://api.clerk.com/v1"

async def verify_clerk_token(request: Request):
    authorization = request.headers.get("Authorization")
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing Authorization header")

    token = authorization.split("Bearer ")[1]

    async with httpx.AsyncClient() as client:
        resp = await client.get(
            f"{CLERK_BASE_URL}/sessions/{token}",
            headers={"Authorization": f"Bearer {CLERK_SECRET_KEY}"}
        )

    if resp.status_code != 200:
        raise HTTPException(status_code=401, detail="Invalid token")

    session_data = resp.json()
    user_id = session_data.get("user_id")
    return user_id
