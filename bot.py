import asyncio
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from database import get_or_create_user, get_next_card, submit_review, env
from database import get_or_create_user, get_next_card, submit_review, get_card_by_id, env
from database import get_or_create_user, get_next_card, submit_review, get_card_by_id, get_user_level, set_user_level, env
BOT_TOKEN = env.get("BOT_TOKEN")
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()


def rating_keyboard(card_id: str):
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="😵 Забыл", callback_data=f"rate:{card_id}:1"),
            InlineKeyboardButton(text="😐 Сложно", callback_data=f"rate:{card_id}:2"),
        ],
        [
            InlineKeyboardButton(text="🙂 Норм", callback_data=f"rate:{card_id}:3"),
            InlineKeyboardButton(text="😎 Легко", callback_data=f"rate:{card_id}:4"),
        ]
    ])

def level_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=f"HSK {i}", callback_data=f"level:{i}") for i in range(1, 4)],
        [InlineKeyboardButton(text=f"HSK {i}", callback_data=f"level:{i}") for i in range(4, 7)],
    ])


@dp.message(Command("level"))
async def cmd_level(message: types.Message):
    await message.answer("Выбери свой уровень HSK:", reply_markup=level_keyboard())


@dp.callback_query(F.data.startswith("level:"))
async def handle_level(callback: types.CallbackQuery):
    _, level = callback.data.split(":")
    user_id = get_or_create_user(callback.from_user.id, callback.from_user.username, callback.from_user.first_name)
    set_user_level(user_id, int(level))
    await callback.message.edit_text(f"Уровень установлен: HSK {level}")
    await callback.answer()
@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    user_id = get_or_create_user(message.from_user.id, message.from_user.username, message.from_user.first_name)
    await message.answer(
        f"Привет, {message.from_user.first_name}! Ты зарегистрирован в HSK Trainer.\n"
        f"Напиши /study чтобы начать повторение."
    )


@dp.message(Command("study"))
async def cmd_study(message: types.Message):
    user_id = get_or_create_user(message.from_user.id, message.from_user.username, message.from_user.first_name)
    next_card = get_next_card(user_id)

    if not next_card:
        level = get_user_level(user_id)
        await message.answer(
            f"Карточек для HSK {level} пока нет или все изучены.\n"
            f"Смени уровень командой /level"
        )
        return

    card = next_card["cards"]
    text = f"{card['hanzi']}\n\n{card['pinyin']}"
    await message.answer(text, reply_markup=rating_keyboard(card["id"]))


@dp.callback_query(F.data.startswith("rate:"))
async def handle_rating(callback: types.CallbackQuery):
    _, card_id, rating = callback.data.split(":")
    user_id = get_or_create_user(callback.from_user.id, callback.from_user.username, callback.from_user.first_name)

    card_info = get_card_by_id(card_id)
    translation = card_info["translation"] if card_info else "—"

    submit_review(user_id, card_id, int(rating))

    await callback.message.edit_text(
        f"{callback.message.text}\n\n📖 Перевод: {translation}\n\n✅ Записано"
    )
    await callback.answer()

    next_card = get_next_card(user_id)
    if next_card:
        card = next_card["cards"]
        text = f"{card['hanzi']}\n\n{card['pinyin']}"
        await callback.message.answer(text, reply_markup=rating_keyboard(card["id"]))
    else:
        await callback.message.answer("На сегодня карточек больше нет 🎉")


async def main():
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())