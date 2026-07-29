from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from database import (
    get_or_create_user,
    get_next_card,
    submit_review,
    get_card_by_id,
    get_user_level,
    set_user_level,
)

app = FastAPI()

# CORS нужен, чтобы фронтенд (с другого домена) мог обращаться к этому API
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # на проде лучше указать конкретный домен фронтенда
    allow_methods=["*"],
    allow_headers=["*"],
)


class UserRequest(BaseModel):
    telegram_id: int
    username: str | None = None
    first_name: str | None = None


class ReviewRequest(BaseModel):
    telegram_id: int
    card_id: str
    rating: int


class LevelRequest(BaseModel):
    telegram_id: int
    level: int


@app.post("/api/user")
def api_get_or_create_user(req: UserRequest):
    user_id = get_or_create_user(req.telegram_id, req.username, req.first_name)
    level = get_user_level(user_id)
    return {"user_id": user_id, "hsk_level": level}


@app.get("/api/next-card/{telegram_id}")
def api_next_card(telegram_id: int):
    user_id = get_or_create_user(telegram_id, None, None)
    card = get_next_card(user_id)
    if not card:
        raise HTTPException(status_code=404, detail="Нет доступных карточек")
    return card


@app.post("/api/submit-review")
def api_submit_review(req: ReviewRequest):
    user_id = get_or_create_user(req.telegram_id, None, None)
    submit_review(user_id, req.card_id, req.rating)
    translation = get_card_by_id(req.card_id)
    return {"status": "ok", "translation": translation["translation"] if translation else None}


@app.post("/api/set-level")
def api_set_level(req: LevelRequest):
    user_id = get_or_create_user(req.telegram_id, None, None)
    set_user_level(user_id, req.level)
    return {"status": "ok", "hsk_level": req.level}


@app.get("/")
def root():
    return {"status": "HSK Trainer API работает"}