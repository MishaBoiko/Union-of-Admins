import json
import logging
import os
from aiogram import Bot, Dispatcher, F, types
from aiogram.filters import Command
from aiogram.types import ChatType, ChatMemberStatus
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

temp_links = {}

@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    await message.answer("Напиши команду /setgroup у групі, яку хочеш прив'язати.")

@dp.message(Command("setgroup"), F.chat.type.in_([ChatType.GROUP, ChatType.SUPERGROUP]))
async def cmd_setgroup(message: types.Message):
    group_id = message.chat.id
    user_id = message.from_user.id
    temp_links[user_id] = group_id

    try:
        await bot.send_message(user_id, "Тепер надішли мені в особисті повідомлення @username каналу.")
    except Exception:
        await message.reply("Напиши мені в особисті повідомлення, будь ласка, і потім повтори команду /setgroup.")
        return

    await message.reply("Перевір особисті повідомлення — я написав інструкції.")

@dp.message(F.text.startswith("@"))
async def set_channel_username(message: types.Message):
    user_id = message.from_user.id
    group_id = temp_links.get(user_id)

    if not group_id:
        await message.answer("Спочатку у групі напиши команду /setgroup, щоб прив’язати групу.")
        return

    channel_username = message.text.strip()
    data = load_db()
    data[str(group_id)] = channel_username  # зберігаємо за group_id, щоб можна було швидко знайти канал для групи
    save_db(data)

    await message.answer(
        f"""✅ Зв’язка оновлена!
Група: <code>{group_id}</code>
Канал: {channel_username}"""
    )
    del temp_links[user_id]

# Перевірка повідомлень у групі
@dp.message(F.chat.type.in_([ChatType.GROUP, ChatType.SUPERGROUP]))
async def check_subscription(message: types.Message):
    group_id = message.chat.id
    user_id = message.from_user.id
    data = load_db()
    channel_username = data.get(str(group_id))

    if not channel_username:
        # Якщо канал не заданий для групи — нічого не перевіряємо
        return

    try:
        member = await bot.get_chat_member(chat_id=channel_username, user_id=user_id)
    except Exception:
        # Якщо бот не може отримати інформацію (наприклад, канал закритий або немає прав)
        # можна або пропустити, або видалити повідомлення
        await message.delete()
        return

    # Перевіряємо, що користувач підписаний (member.status != 'left' і != 'kicked')
    if member.status in ['left', 'kicked']:
        # Видаляємо повідомлення і пишемо користувачу в приватні
        try:
            await message.delete()
        except Exception:
            pass
        try:
            await bot.send_message(user_id, f"Ви повинні підписатися на канал {channel_username}, щоб писати в групі.")
        except Exception:
            pass

