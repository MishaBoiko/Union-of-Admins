import json
import logging
import os
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext
from aiogram.types import Message
from aiogram.fsm.storage.memory import MemoryStorage
import asyncio

# Ініціалізація логування та токена
logging.basicConfig(level=logging.INFO)
API_TOKEN = '7739860939:AAFvk9wdbdpCJ5L17WSb7YkaORGU09LTsDE'

# Ініціалізація бота та диспетчера
bot = Bot(token=API_TOKEN, parse_mode="HTML")
dp = Dispatcher(storage=MemoryStorage())

# Шлях до файлу з базою даних
DB_FILE = "db.json"

def load_db():
    if os.path.exists(DB_FILE):
        with open(DB_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}

def save_db(data):
    with open(DB_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

# Стани FSM
class LinkGroup(StatesGroup):
    waiting_for_group = State()
    waiting_for_channel = State()

# Команда /start в особистці
@dp.message(Command("start"))
async def cmd_start(message: Message, state: FSMContext):
    await message.answer("Напиши команду /setgroup в тій групі, яку хочеш прив'язати.")
    await state.set_state(LinkGroup.waiting_for_group)

# /setgroup у групі
@dp.message(Command("setgroup"), F.chat.type.in_(["group", "supergroup"]))
async def cmd_setgroup(message: Message, state: FSMContext):
    group_id = message.chat.id
    user_id = message.from_user.id
    await state.update_data(group_id=group_id, user_id=user_id)
    await message.reply("Тепер повернись до особистих повідомлень з ботом і надішли @username каналу.")

# Отримання @каналу в особистці
@dp.message(LinkGroup.waiting_for_group, F.text.startswith("@"))
async def set_channel_username(message: Message, state: FSMContext):
    channel_username = message.text.strip()
    user_id = message.from_user.id

    data = load_db()
    fsm_data = await state.get_data()
    group_id = fsm_data.get("group_id")

    if not group_id:
        await message.answer("Спочатку надішли /setgroup в групі, а потім введи канал.")
        return

    # Записуємо нову зв'язку, видаляючи стару
    data[str(user_id)] = {
        "group_id": group_id,
        "channel_username": channel_username
    }
    save_db(data)

    await message.answer(f"""✅ Зв’язка оновлена!
    Група: <code>{group_id}</code>
    Канал: {channel_username}""")


# Запуск
async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
