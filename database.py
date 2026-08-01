import os
import datetime
from supabase import create_client, Client
from fsrs import Scheduler, Card, Rating

with open(".env", "r", encoding="utf-8-sig") as f:
    raw_content = f.read()
print("СЫРОЕ СОДЕРЖИМОЕ .env:")
print(repr(raw_content))
print("---конец---")
# Ручной парсер .env вместо python-dotenv — на случай проблем с кодировкой
import os

def load_env_manually(filepath=".env"):
    """Локально читает .env вручную, если файл существует. На сервере (Railway) переменные уже в os.environ."""
    env_vars = {}
    if os.path.exists(filepath):
        with open(filepath, "r", encoding="utf-8-sig") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                key, value = line.split("=", 1)
                env_vars[key.strip()] = value.strip()
    return env_vars


_local_env = load_env_manually()
env = {**os.environ, **_local_env}

url = env.get("SUPABASE_URL")
key = env.get("SUPABASE_SERVICE_KEY")


def get_or_create_user(telegram_id: int, username: str, first_name: str):
    existing = supabase.table("users").select("id").eq("telegram_id", telegram_id).execute()
    if existing.data:
        return existing.data[0]["id"]

    new_user = supabase.table("users").insert({
        "telegram_id": telegram_id,
        "username": username,
        "first_name": first_name
    }).execute()
    return new_user.data[0]["id"]


def get_due_cards(user_id: str):
    due = supabase.table("user_progress") \
        .select("*, cards(*)") \
        .eq("user_id", user_id) \
        .lte("due_date", "now()") \
        .execute()
    return due.data


if __name__ == "__main__":
    user_id = get_or_create_user(123456789, "test_user", "Test")
    print("User ID:", user_id)

    due = get_due_cards(user_id)
    print("Карточек к повторению:", len(due))


def load_env_manually(filepath=".env"):
    """Локально читает .env вручную, если файл существует. На сервере (Railway) переменные уже в os.environ."""
    env_vars = {}
    if os.path.exists(filepath):
        with open(filepath, "r", encoding="utf-8-sig") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                key, value = line.split("=", 1)
                env_vars[key.strip()] = value.strip()
    return env_vars


_local_env = load_env_manually()
env = {**os.environ, **_local_env}  # локальный .env имеет приоритет при разработке

url = env.get("SUPABASE_URL")
key = env.get("SUPABASE_SERVICE_KEY")

supabase: Client = create_client(url, key)
scheduler = Scheduler()


def get_or_create_user(telegram_id: int, username: str, first_name: str):
    existing = supabase.table("users").select("id").eq("telegram_id", telegram_id).execute()
    if existing.data:
        return existing.data[0]["id"]
    new_user = supabase.table("users").insert({
        "telegram_id": telegram_id,
        "username": username,
        "first_name": first_name
    }).execute()
    return new_user.data[0]["id"]


def get_next_card(user_id: str):
    """Берёт карточку, которая уже due, либо новую — строго в рамках текущего уровня юзера."""
    level = get_user_level(user_id)

    due = supabase.table("user_progress") \
        .select("*, cards(*)") \
        .eq("user_id", user_id) \
        .lte("due_date", datetime.datetime.utcnow().isoformat()) \
        .execute()

    # фильтруем due-карточки по уровню (join не даёт фильтровать по вложенной таблице напрямую)
    due_filtered = [row for row in due.data if row["cards"]["hsk_level"] == level]
    if due_filtered:
        return due_filtered[0]

    seen = supabase.table("user_progress").select("card_id").eq("user_id", user_id).execute()
    seen_ids = [row["card_id"] for row in seen.data]

    query = supabase.table("cards").select("*").eq("hsk_level", level)
    if seen_ids:
        query = query.not_.in_("id", seen_ids)
    new_card = query.limit(1).execute()

    if not new_card.data:
        return None

    card = new_card.data[0]
    supabase.table("user_progress").insert({
        "user_id": user_id,
        "card_id": card["id"]
    }).execute()

    return {"card_id": card["id"], "cards": card, "difficulty": 5.0, "stability": 1.0, "reps": 0}


def submit_review(user_id: str, card_id: str, rating_value: int):
    """rating_value: 1=Again, 2=Hard, 3=Good, 4=Easy"""
    progress = supabase.table("user_progress").select("*").eq("user_id", user_id).eq("card_id", card_id).execute()

    if not progress.data:
        # записи ещё нет — создаём с дефолтными значениями
        supabase.table("user_progress").insert({
            "user_id": user_id,
            "card_id": card_id
        }).execute()
        progress = supabase.table("user_progress").select("*").eq("user_id", user_id).eq("card_id", card_id).execute()

    row = progress.data[0]
    fsrs_card = Card(
        due=datetime.datetime.fromisoformat(row["due_date"]) if row.get("due_date") else datetime.datetime.utcnow(),
        stability=row.get("stability", 1.0),
        difficulty=row.get("difficulty", 5.0),
    )
    rating_map = {1: Rating.Again, 2: Rating.Hard, 3: Rating.Good, 4: Rating.Easy}
    updated_card, review_log = scheduler.review_card(fsrs_card, rating_map[rating_value])

    supabase.table("user_progress").update({
        "difficulty": updated_card.difficulty,
        "stability": updated_card.stability,
        "due_date": updated_card.due.isoformat(),
        "last_review": datetime.datetime.utcnow().isoformat(),
        "reps": row.get("reps", 0) + 1
    }).eq("user_id", user_id).eq("card_id", card_id).execute()

    supabase.table("review_logs").insert({
        "user_id": user_id,
        "card_id": card_id,
        "rating": rating_value,
        "predicted_retrievability": scheduler.get_card_retrievability(fsrs_card)
    }).execute()

def get_card_by_id(card_id: str):
    result = supabase.table("cards").select("*").eq("id", card_id).execute()
    if result.data:
        return result.data[0]
    return None


def get_user_level(user_id: str):
    result = supabase.table("users").select("hsk_level").eq("id", user_id).execute()
    return result.data[0]["hsk_level"] if result.data else 1


def set_user_level(user_id: str, level: int):
    supabase.table("users").update({"hsk_level": level}).eq("id", user_id).execute()