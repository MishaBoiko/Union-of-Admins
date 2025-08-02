import json
import re
from aiogram import Bot, Dispatcher, types
from aiogram.types import Message
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.utils.keyboard import InlineKeyboardBuilder
import asyncio

API_TOKEN = '7739860939:AAFvk9wdbdpCJ5L17WSb7YkaORGU09LTsDE'

bot = Bot(token=API_TOKEN)
dp = Dispatcher(storage=MemoryStorage())

db_file = 'db.json'

def load_db():
    try:
        with open(db_file, 'r') as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {}

def save_db(data):
    with open(db_file, 'w') as f:
        json.dump(data, f, indent=4)

class LinkStates(StatesGroup):
    waiting_for_group = State()
    waiting_for_channel = State()

@dp.message(Command("start"))
async def start_command(message: Message, state: FSMContext):
    await state.clear()
    await state.set_state(LinkStates.waiting_for_group)
    await message.answer("🔗 Відправ посилання на групу:")

@dp.message(LinkStates.waiting_for_group)
async def process_group_link(message: Message, state: FSMContext):
    group_link = extract_username_from_link(message.text)
    if not group_link:
        await message.answer("❌ Невірне посилання. Спробуй ще раз.")
        return

    try:
        chat = await bot.get_chat(group_link)
        if chat.type not in ["group", "supergroup"]:
            raise ValueError("Це не група")
    except Exception:
        await message.answer("❌ Не вдалося знайти групу. Перевір посилання!")
        return

    await state.update_data(group=group_link)
    await state.set_state(LinkStates.waiting_for_channel)
    await message.answer("📢 Тепер надішли посилання на канал:")

@dp.message(LinkStates.waiting_for_channel)
async def process_channel_link(message: Message, state: FSMContext):
    channel_link = extract_username_from_link(message.text)
    if not channel_link:
        await message.answer("❌ Невірне посилання. Спробуй ще раз.")
        return

    try:
        chat = await bot.get_chat(channel_link)
        if chat.type != "channel":
            raise ValueError("Це не канал")
    except Exception:
        await message.answer("❌ Не вдалося знайти канал. Перевір посилання!")
        return

    data = await state.get_data()
    group = data.get("group")

    db = load_db()
    db[str(message.from_user.id)] = {
        "group": group,
        "channel": channel_link
    }
    save_db(db)

    await message.answer(f"✅ Зв’язка збережена!\nГрупа: {group}\nКанал: {channel_link}")
    await state.clear()


def extract_username_from_link(link: str) -> str | None:
    match = re.match(r"https?://t\.me/([a-zA-Z0-9_]{5,})", link)
    if match:
        return match.group(1)
    return None

if __name__ == '__main__':
    async def main():
        await dp.start_polling(bot)
    asyncio.run(main())
