import logging
import json
import os
from aiogram import Bot, Dispatcher, types, F
from aiogram.enums import ChatMemberStatus, ChatType
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.exceptions import TelegramBadRequest
import asyncio

API_TOKEN = os.getenv("API_TOKEN", "ВАШ_ТОКЕН")

bot = Bot(token=API_TOKEN, parse_mode="HTML")
dp = Dispatcher(storage=MemoryStorage())

DB_FILE = "db.json"

def load_db():
    try:
        with open(DB_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        return {}

def save_db(data):
    with open(DB_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

class LinkStates(StatesGroup):
    waiting_for_channel = State()
    waiting_for_group = State()

# /start — початок діалогу
@dp.message(Command("start"))
async def start_cmd(message: types.Message, state: FSMContext):
    await message.answer("👋 Надішли посилання на канал у форматі <code>@назва_каналу</code>")
    await state.set_state(LinkStates.waiting_for_channel)

# Отримуємо канал
@dp.message(LinkStates.waiting_for_channel)
async def process_channel(message: types.Message, state: FSMContext):
    channel = message.text.strip()
    if not channel.startswith("@"):
        await message.answer("❗ Це не схоже на посилання @каналу. Спробуй ще раз.")
        return
    await state.update_data(channel=channel)
    await message.answer("🔗 Тепер надішли посилання на групу у форматі <code>https://t.me/назва_групи</code>")
    await state.set_state(LinkStates.waiting_for_group)

# Отримуємо групу і зберігаємо
@dp.message(LinkStates.waiting_for_group)
async def process_group(message: types.Message, state: FSMContext):
    group_link = message.text.strip()
    if not group_link.startswith("https://t.me/"):
        await message.answer("❗ Це не схоже на посилання групи. Спробуй ще раз.")
        return

    group_username = group_link.replace("https://t.me/", "")
    try:
        group_chat = await bot.get_chat(group_username)
        if group_chat.type not in [ChatType.GROUP, ChatType.SUPERGROUP]:
            await message.answer("❌ Це не група.")
            return

        data = await state.get_data()
        group_id = str(group_chat.id)
        db = load_db()
        db[group_id] = {
            "required_channel": data["channel"]
        }
        save_db(db)

        await message.answer(
            f"✅ Прив’язка успішна:\n"
            f"Група: <b>{group_chat.title}</b>\n"
            f"Канал: {data['channel']}"
        )
        await state.clear()
    except TelegramBadRequest:
        await message.answer("❌ Не вдалося знайти групу. Перевір, чи доданий бот туди як адмін.")

# Перевірка підписки в групі
@dp.message()
async def check_sub(message: types.Message):
    if message.chat.type not in [ChatType.SUPERGROUP, ChatType.GROUP]:
        return

    db = load_db()
    group_id = str(message.chat.id)

    if group_id not in db:
        return

    required_channel = db[group_id]["required_channel"]
    try:
        member = await bot.get_chat_member(required_channel, message.from_user.id)
        if member.status in [ChatMemberStatus.LEFT, ChatMemberStatus.KICKED]:
            raise Exception("Not subscribed")
    except:
        try:
            await message.delete()
            await message.answer(
                f"🔒 Щоб писати в цій групі, підпишись на {required_channel}",
                reply_markup=types.InlineKeyboardMarkup(
                    inline_keyboard=[
                        [types.InlineKeyboardButton(
                            text="🔗 Підписатися",
                            url=f"https://t.me/{required_channel.replace('@', '')}"
                        )]
                    ]
                )
            )
        except:
            pass

# Запуск
async def main():
    logging.basicConfig(level=logging.INFO)
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
