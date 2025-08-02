import asyncio
import json
import os
from aiogram import Bot, Dispatcher, F
from aiogram.types import Message
from aiogram.filters import CommandStart
from aiogram.fsm.state import StatesGroup, State
from aiogram.fsm.context import FSMContext
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.exceptions import TelegramBadRequest

API_TOKEN = '7739860939:AAFvk9wdbdpCJ5L17WSb7YkaORGU09LTsDE'

bot = Bot(token=API_TOKEN, parse_mode="HTML")
dp = Dispatcher(storage=MemoryStorage())

DB_FILE = "db.json"
if not os.path.exists(DB_FILE):
    with open(DB_FILE, "w") as f:
        json.dump({}, f)

def load_db():
    with open(DB_FILE, "r") as f:
        return json.load(f)

def save_db(data):
    with open(DB_FILE, "w") as f:
        json.dump(data, f, indent=4)

class SetupStates(StatesGroup):
    waiting_for_group = State()
    waiting_for_channel = State()

@dp.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext):
    await message.answer("🔗 Відправ посилання на групу:")
    await state.set_state(SetupStates.waiting_for_group)

@dp.message(SetupStates.waiting_for_group)
async def get_group_link(message: Message, state: FSMContext):
    text = message.text.strip()
    if not text.startswith("https://t.me/"):
        await message.answer("❗ Надішли посилання на групу у форматі https://t.me/назва")
        return
    username = text.split("https://t.me/")[1].strip("/")
    try:
        chat = await bot.get_chat(username)
        if not chat.type.endswith("group"):
            await message.answer("⚠️ Це не група!")
            return
        await state.update_data(group_id=chat.id)
        await message.answer("📢 Тепер надішли посилання на канал:")
        await state.set_state(SetupStates.waiting_for_channel)
    except TelegramBadRequest:
        await message.answer("❌ Не вдалося знайти групу. Перевір посилання!")

@dp.message(SetupStates.waiting_for_channel)
async def get_channel_link(message: Message, state: FSMContext):
    text = message.text.strip()
    if not text.startswith("https://t.me/"):
        await message.answer("❗ Надішли посилання на канал у форматі https://t.me/назва")
        return
    username = text.split("https://t.me/")[1].strip("/")
    try:
        chat = await bot.get_chat(username)
        if chat.type != "channel":
            await message.answer("⚠️ Це не канал!")
            return
        data = await state.get_data()
        group_id = str(data["group_id"])
        db = load_db()
        db[group_id] = {"required_channel": f"@{username}"}
        save_db(db)
        await message.answer(f"✅ Успішно прив'язав канал @{username} до групи!")
        await state.clear()
    except TelegramBadRequest:
        await message.answer("❌ Не вдалося знайти канал. Перевір посилання!")

async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
