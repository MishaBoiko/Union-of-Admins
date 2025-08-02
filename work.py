import json
import logging
import os
from aiogram import Bot, Dispatcher, F
from aiogram.filters import Command
from aiogram.types import Message
import asyncio

logging.basicConfig(level=logging.INFO)
API_TOKEN = '7739860939:AAFvk9wdbdpCJ5L17WSb7YkaORGU09LTsDE'

bot = Bot(token=API_TOKEN, parse_mode="HTML")
dp = Dispatcher()

DB_FILE = "db.json"

def load_db():
    if os.path.exists(DB_FILE):
        with open(DB_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}

def save_db(data):
    with open(DB_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

# Тимчасове сховище для групи по user_id
temp_links = {}

# Команда /start у особистих повідомленнях
@dp.message(Command("start"))
async def cmd_start(message: Message):
    await message.answer("Напиши команду /setgroup у групі, яку хочеш прив'язати.")

# Команда /setgroup у групі
@dp.message(Command("setgroup"), F.chat.type.in_(["group", "supergroup"]))
async def cmd_setgroup(message: Message):
    group_id = message.chat.id
    user_id = message.from_user.id
    temp_links[user_id] = group_id

    try:
        await bot.send_message(user_id, "Тепер надішли мені в особисті повідомлення @username каналу.")
    except Exception:
        await message.reply("Напиши мені в особисті повідомлення, будь ласка, і потім повтори команду /setgroup.")
        return

    await message.reply("Перевір особисті повідомлення — я написав інструкції.")

# Отримання @каналу в особистих повідомленнях
@dp.message(F.text.startswith("@"))
async def set_channel_username(message: Message):
    user_id = message.from_user.id
    group_id = temp_links.get(user_id)

    if not group_id:
        await message.answer("Спочатку у групі напиши команду /setgroup, щоб прив’язати групу.")
        return

    channel_username = message.text.strip()
    data = load_db()
    data[str(user_id)] = {
        "group_id": group_id,
        "channel_username": channel_username
    }
    save_db(data)

    await message.answer(
        f"""✅ Зв’язка оновлена!
Група: <code>{group_id}</code>
Канал: {channel_username}"""
    )
    del temp_links[user_id]

async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
