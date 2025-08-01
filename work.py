import logging
import os
import json
from pathlib import Path
from aiogram import Bot, Dispatcher, types
from aiogram.types import ChatPermissions
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
import asyncio

# === Конфігурація ===
API_TOKEN = os.getenv('API_TOKEN', '7739860939:AAFvk9wdbdpCJ5L17WSb7YkaORGU09LTsDE')
DATA_FILE = Path("db.json")

# === Логування ===
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# === Ініціалізація ===
bot = Bot(token=API_TOKEN)
dp = Dispatcher(bot=bot)

# === FSM ===
class ChannelSetup(StatesGroup):
    waiting_for_channel = State()
    waiting_for_group = State()

# === JSON-функції ===
def load_user_channels():
    if DATA_FILE.exists():
        try:
            with open(DATA_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except json.JSONDecodeError:
            logger.warning("⚠️ db.json поврежден. Перезаписываю...")
            DATA_FILE.write_text("{}", encoding="utf-8")
            return {}
    return {}

def save_user_channels(data):
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
        f.flush()

# === Команди ===
@dp.message(Command('start'))
async def cmd_start(message: types.Message, state: FSMContext):
    await message.answer('Введите юзернейм канала (с @), на который нужно сделать обязательную подписку:')
    await state.set_state(ChannelSetup.waiting_for_channel)

@dp.message(ChannelSetup.waiting_for_channel)
async def process_channel_username(message: types.Message, state: FSMContext):
    channel_username = message.text.strip()
    if not channel_username.startswith('@'):
        channel_username = '@' + channel_username

    await state.update_data(channel=channel_username)
    await message.answer(f'Канал {channel_username} принят. Теперь отправьте ID группы или перешлите сообщение из неё.')
    await state.set_state(ChannelSetup.waiting_for_group)

@dp.message(ChannelSetup.waiting_for_group)
async def process_group_id(message: types.Message, state: FSMContext):
    user_id = str(message.from_user.id)
    data = await state.get_data()
    channel_username = data.get('channel')

    group_id = None

    if message.forward_from_chat:
        group_id = message.forward_from_chat.id
    elif message.text:
        if 't.me/' in message.text or 'telegram.me/' in message.text:
            try:
                username = message.text.split('/')[-1].split('?')[0]
                chat_info = await bot.get_chat(f"@{username}")
                group_id = chat_info.id
            except Exception:
                await message.answer('❌ Не удалось получить информацию о группе.')
                return
        elif message.text.isdigit():
            group_id = int(message.text)
        else:
            await message.answer('❗ Отправьте ссылку на группу, ID или пересланное сообщение.')
            return
    else:
        await message.answer('❗ Отправьте ссылку на группу, ID или пересланное сообщение.')
        return

    try:
        group_info = await bot.get_chat(group_id)
        bot_member = await bot.get_chat_member(group_id, bot.id)

        if bot_member.status not in ['administrator', 'creator']:
            await message.answer('⚠️ Бот должен быть администратором в группе.')
            await state.clear()
            return

        try:
            await bot.get_chat(channel_username)
        except Exception:
            await message.answer(f'⚠️ Бот не имеет доступа к каналу {channel_username}.')
            await state.clear()
            return

        # Загрузка и сохранение
        user_channels = load_user_channels()
        if user_id not in user_channels:
            user_channels[user_id] = {}

        user_channels[user_id][str(group_id)] = channel_username
        save_user_channels(user_channels)

        await message.answer(f'✅ Готово!\nКанал: {channel_username}\nГруппа: {group_info.title}')
        await state.clear()

    except Exception as e:
        logger.error(f"Ошибка при настройке: {e}")
        await message.answer('❌ Не удалось сохранить настройки.')
        await state.clear()

# === Перевірка повідомлень ===
@dp.message()
async def check_subscription(message: types.Message):
    if message.chat.type not in ['group', 'supergroup']:
        return

    user_id = str(message.from_user.id)
    chat_id = str(message.chat.id)

    user_channels = load_user_channels()
    if user_id not in user_channels or chat_id not in user_channels[user_id]:
        return

    channel_username = user_channels[user_id][chat_id]

    try:
        await bot.get_chat(channel_username)
        member = await bot.get_chat_member(channel_username, int(user_id))

        if member.status in ['member', 'administrator', 'creator']:
            return  # підписаний

        await message.delete()
        username = message.from_user.username
        mention = f"@{username}" if username else f"пользователь {user_id}"
        await bot.send_message(
            chat_id=message.chat.id,
            text=f"🔒 {mention}, подпишитесь на канал {channel_username}, чтобы писать в этом чате."
        )
        await bot.restrict_chat_member(
            chat_id=message.chat.id,
            user_id=message.from_user.id,
            permissions=ChatPermissions(can_send_messages=False)
        )

    except Exception as e:
        logger.error(f"Ошибка при проверке подписки: {e}")

# === Запуск ===
if __name__ == '__main__':
    async def main():
        logger.info("✅ Бот запущен.")
        await dp.start_polling(bot)
    asyncio.run(main())
