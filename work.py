import json
import logging
import os
import asyncio

from aiogram import Bot, Dispatcher, F, types
from aiogram.filters import Command
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.enums.chat_type import ChatType
from aiogram.enums.chat_member_status import ChatMemberStatus

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

API_TOKEN = os.getenv("BOT_TOKEN", "7739860939:AAFvk9wdbdpCJ5L17WSb7YkaORGU09LTsDE")
if API_TOKEN == "":
    raise RuntimeError("Не заданий токен бота. Встанови BOT_TOKEN в змінних середовища.")

if "7739860939:AAFvk9wdbdpCJ5L17WSb7YkaORGU09LTsDE" in API_TOKEN:
    logging.warning("Використовується хардкоднений токен. Рекомендується задати BOT_TOKEN як змінну середовища у продакшн середовищі.")

bot = Bot(
    token=API_TOKEN,
    default=DefaultBotProperties(parse_mode=ParseMode.HTML),
)
dp = Dispatcher()

DB_FILE = "db.json"
temp_links: dict[int, int] = {}  # user_id -> group_id

def load_db() -> dict:
    if os.path.exists(DB_FILE):
        try:
            with open(DB_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            logging.error("Не вдалося прочитати DB: %s", e)
            return {}
    return {}

def save_db(data: dict):
    try:
        with open(DB_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=4)
    except Exception as e:
        logging.error("Не вдалося записати DB: %s", e)

def is_user_admin_in_chat(chat_member: types.ChatMember) -> bool:
    return chat_member.status in (ChatMemberStatus.ADMINISTRATOR, ChatMemberStatus.CREATOR)

@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    await message.answer("Привіт! Щоб прив’язати групу до каналу, зайди в потрібну групу як адмін і виконай команду /setgroup там.")

@dp.message(Command("setgroup"), F.chat.type.in_([ChatType.GROUP, ChatType.SUPERGROUP]))
async def cmd_setgroup(message: types.Message):
    group_id = message.chat.id
    user_id = message.from_user.id

    try:
        member = await bot.get_chat_member(chat_id=group_id, user_id=user_id)
    except Exception as e:
        logging.warning("Не вдалося отримати статус користувача в групі: %s", e)
        await message.reply("Не можу перевірити ваш статус у цій групі. Переконайтесь, що я маю доступ до групи.")
        return

    if not is_user_admin_in_chat(member):
        await message.reply("Тільки адміністратори можуть прив’язувати цю групу до каналу.")
        return

    temp_links[user_id] = group_id

    try:
        await bot.send_message(user_id, "Тепер надішли мені в особисті повідомлення @username каналу, який хочеш прив’язати до цієї групи.")
    except Exception:
        await message.reply("Напиши мені в особисті повідомлення, будь ласка, і потім повтори команду /setgroup.")
        return

    await message.reply("Я надіслав інструкції в особисті повідомлення. Перевір їх.")

@dp.message(F.text.startswith("@"), F.chat.type == ChatType.PRIVATE)
async def set_channel_username(message: types.Message):
    user_id = message.from_user.id
    group_id = temp_links.get(user_id)

    if not group_id:
        await message.answer("Спочатку у групі напиши команду /setgroup, щоб прив’язати групу.")
        return

    raw_username = message.text.strip()
    if not raw_username.startswith("@"):
        await message.answer("Ім'я каналу повинно починатися з @. Спробуй ще раз.")
        return

    try:
        chat = await bot.get_chat(raw_username)
    except Exception as e:
        logging.error("Не вдалося знайти канал %s: %s", raw_username, e)
        await message.answer("Не вдалося знайти канал за цим username. Перевірте, чи правильно написано, і чи я доданий до каналу.")
        return

    data = load_db()
    data[str(group_id)] = {
        "channel_id": chat.id,
        "channel_username": raw_username
    }
    save_db(data)

    await message.answer(
        f"""✅ Зв’язка оновлена!
Група: <code>{group_id}</code>
Канал: {raw_username} (id: <code>{chat.id}</code>)"""
    )
    temp_links.pop(user_id, None)

@dp.message(Command("status"), F.chat.type.in_([ChatType.GROUP, ChatType.SUPERGROUP]))
async def cmd_status(message: types.Message):
    group_id = message.chat.id
    data = load_db()
    entry = data.get(str(group_id))
    if not entry:
        await message.reply("Ця група не прив’язана до жодного каналу.")
        return

    channel_username = entry.get("channel_username", "невідомо")
    channel_id = entry.get("channel_id", "невідомо")
    await message.reply(f"Прив’язана група → канал:\nКанал: {channel_username} (id: {channel_id})")

@dp.message(Command("unlink"), F.chat.type.in_([ChatType.GROUP, ChatType.SUPERGROUP]))
async def cmd_unlink(message: types.Message):
    group_id = message.chat.id
    data = load_db()
    if str(group_id) in data:
        data.pop(str(group_id))
        save_db(data)
        await message.reply("Прив’язка до каналу була видалена.")
    else:
        await message.reply("Ця група не була прив’язана до жодного каналу.")

@dp.message(F.chat.type.in_([ChatType.GROUP, ChatType.SUPERGROUP]))
async def check_subscription(message: types.Message):
    group_id = message.chat.id
    user_id = message.from_user.id
    data = load_db()
    entry = data.get(str(group_id))

    if not entry:
        return

    channel_id = entry.get("channel_id")
    channel_username = entry.get("channel_username", "")

    if not channel_id:
        return

    try:
        member = await bot.get_chat_member(chat_id=channel_id, user_id=user_id)
    except Exception as e:
        logging.debug("Не вдалося отримати участь користувача %s в каналі %s: %s", user_id, channel_id, e)
        try:
            await message.delete()
        except Exception:
            pass
        try:
            await bot.send_message(user_id, f"Щоб писати в групі, підпишись на канал {channel_username or channel_id}.")
        except Exception:
            pass
        return

    if member.status in (ChatMemberStatus.LEFT, ChatMemberStatus.KICKED):
        try:
            await message.delete()
        except Exception:
            pass
        try:
            await bot.send_message(user_id, f"Ви повинні підписатися на канал {channel_username or channel_id}, щоб писати в групі.")
        except Exception:
            pass

async def on_shutdown():
    logging.info("Завершення роботи бота...")
    try:
        await bot.session.close()
    except Exception as e:
        logging.warning("Помилка при закритті сесії бота: %s", e)

async def main():
    logging.info("Запуск бота...")
    try:
        await dp.start_polling(bot, shutdown=on_shutdown)
    except Exception as e:
        logging.exception("Помилка в процесі polling: %s", e)
    finally:
        await on_shutdown()

if __name__ == '__main__':
    asyncio.run(main())
