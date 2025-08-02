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
bot = Bot(token=API_TOKEN)
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
    waiting_for_group_id = State()
    waiting_for_channel_username = State()

# Команда /start
@dp.message(Command("start"))
async def start_cmd(message: Message, state: FSMContext):
    await message.answer("Надішли будь-яке повідомлення в групу, де доданий цей бот.")
    await state.set_state(LinkGroup.waiting_for_group_id)

# Отримання групи через повідомлення
@dp.message(LinkGroup.waiting_for_group_id, F.chat.type.in_(["group", "supergroup"]))
async def handle_group_message(message: Message, state: FSMContext):
    group_id = message.chat.id
    await state.update_data(group_id=group_id)
    await message.reply("Тепер надішли @username каналу (без лінку, лише @user).")
    await state.set_state(LinkGroup.waiting_for_channel_username)

# Отримання каналу та збереження зв’язки
@dp.message(LinkGroup.waiting_for_channel_username, F.text.startswith("@"))
async def handle_channel_username(message: Message, state: FSMContext):
    user_id = message.from_user.id
    channel_username = message.text.strip()

    data = load_db()
    fsm_data = await state.get_data()
    group_id = fsm_data.get("group_id")

    if not group_id:
        await message.answer("Щось пішло не так. Спробуй знову через /start.")
        return

    # Оновлюємо зв’язку (видаляємо попередню для цього користувача)
    data[str(user_id)] = {
        "group_id": group_id,
        "channel_username": channel_username
    }
    save_db(data)

    await message.answer(
        f"Зв’язка збережена!\nГрупа: <code>{group_id}</code>\nКанал: {channel_username}"
    )
    await state.clear()

# Запуск
async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
