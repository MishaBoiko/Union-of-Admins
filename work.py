import logging
import os
import json
from pathlib import Path
from aiogram import Bot, Dispatcher, types
from aiogram.types import ChatPermissions
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram import F
import asyncio

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

API_TOKEN = os.getenv('API_TOKEN', 'YOUR_BOT_TOKEN')

bot = Bot(token=API_TOKEN)
dp = Dispatcher()

DATA_FILE = Path("db.json")

def load_user_channels():
    if DATA_FILE.exists():
        try:
            with open(DATA_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except json.JSONDecodeError:
            logger.warning("⚠️ JSON пошкоджений або порожній. Створюю новий...")
            DATA_FILE.write_text("{}", encoding="utf-8")
            return {}
    return {}

def save_user_channels(data):
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
        f.flush()

class ChannelSetup(StatesGroup):
    waiting_for_group_id = State()

@dp.message(Command("start"))
async def set_channel_command(message: types.Message, state: FSMContext):
    if message.chat.type != "private":
        return await message.reply("⚠️ Ця команда працює лише в особистих повідомленнях боту.")
    
    await message.answer("👥 Відправ ID групи (можеш переслати будь-яке повідомлення з чату).")
    await state.set_state(ChannelSetup.waiting_for_group_id)

@dp.message(ChannelSetup.waiting_for_group_id)
async def process_group_id(message: types.Message, state: FSMContext):
    if not message.forward_from_chat or message.forward_from_chat.type not in ['group', 'supergroup']:
        return await message.reply("❌ Це не схоже на переслане повідомлення з групи.")

    group_id = message.forward_from_chat.id
    await state.clear()

    await message.answer(f"✅ Відмінно! Тепер введи юзернейм каналу для підписки (наприклад, @mychannel).")

    @dp.message(F.text.startswith("@"))
    async def process_channel_username(m: types.Message):
        channel_username = m.text.strip()
        user_channels = load_user_channels()
        user_channels[str(group_id)] = channel_username
        save_user_channels(user_channels)
        await m.answer(f"✅ Канал {channel_username} прив'язано до групи {group_id}!")
        dp.message.unregister(process_channel_username)

@dp.message()
async def check_subscription(message: types.Message):
    if message.chat.type not in ['group', 'supergroup']:
        return

    chat_id = str(message.chat.id)
    user_id = message.from_user.id

    user_channels = load_user_channels()
    if chat_id not in user_channels:
        return

    channel_username = user_channels[chat_id]

    try:
        await bot.get_chat(channel_username)
        member = await bot.get_chat_member(channel_username, user_id)

        if member.status in ['member', 'administrator', 'creator']:
            return

        await message.delete()

        username = message.from_user.username
        mention = f"@{username}" if username else f"користувач {user_id}"
        await bot.send_message(
            chat_id=message.chat.id,
            text=f"🔒 {mention}, підпишіться на канал {channel_username}, щоб писати в цьому чаті."
        )

        await bot.restrict_chat_member(
            chat_id=message.chat.id,
            user_id=user_id,
            permissions=ChatPermissions(can_send_messages=False)
        )

    except Exception as e:
        logger.error(f"❌ Помилка перевірки підписки: {e}")

async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
