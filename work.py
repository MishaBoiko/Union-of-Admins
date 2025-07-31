import logging
import os
from aiogram import Bot, Dispatcher, types
from aiogram.types import ChatPermissions
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
import asyncio

# Получаем переменные окружения или используем значения по умолчанию
API_TOKEN = os.getenv('API_TOKEN', '7739860939:AAFvk9wdbdpCJ5L17WSb7YkaORGU09LTsDE')

# Настройка логирования
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

bot = Bot(token=API_TOKEN)
dp = Dispatcher()

# Состояния для FSM
class ChannelSetup(StatesGroup):
    waiting_for_channel = State()

# Словарь для хранения каналов по группам
CHANNELS = {}

@dp.message(Command('start'))
async def cmd_start(message: types.Message, state: FSMContext):
    await message.answer('Введите ЮЗ канала на который нужно ОП')
    await state.set_state(ChannelSetup.waiting_for_channel)
    logger.info(f"/start от {message.from_user.id} в чате {message.chat.id}")

@dp.message(ChannelSetup.waiting_for_channel)
async def process_channel_username(message: types.Message, state: FSMContext):
    chat_id = message.chat.id
    channel_username = message.text.strip()
    
    # Проверяем, начинается ли с @
    if not channel_username.startswith('@'):
        channel_username = '@' + channel_username
    
    # Сохраняем канал для конкретной группы
    CHANNELS[chat_id] = channel_username
    await message.answer(f'Канал {channel_username} установлен для этой группы! Бот готов к работе.\n\nПримечание: для корректной работы убедитесь, что бот добавлен в канал {channel_username} как администратор.')
    await state.clear()
    logger.info(f"Канал установлен для чата {chat_id}: {channel_username} пользователем {message.from_user.id}")

@dp.message()
async def check_subscription(message: types.Message):
    chat_id = message.chat.id
    
    # Проверяем, установлен ли канал для этой группы
    if chat_id not in CHANNELS:
        return
    
    channel_id = CHANNELS[chat_id]
    
    logger.info(f"message_thread_id: {message.message_thread_id}")
    # Проверяем, что это групповой чат
    if message.chat.type not in ["group", "supergroup"]:
        return
    user_id = message.from_user.id
    try:
        member = await bot.get_chat_member(channel_id, user_id)
        logger.info(f"Пользователь {user_id} статус в канале {channel_id}: {member.status}")
        if member.status in ['member', 'administrator', 'creator']:
            return  # Подписан — ничего не делаем
        else:
            await message.delete()
            await asyncio.sleep(0.5)
            username = message.from_user.username
            user_mention = f"@{username}" if username else f"пользователь {user_id}"
            await bot.send_message(
                chat_id=chat_id,
                text=f"🔒 {user_mention} чтобы писать в этом чате, пожалуйста, подпишитесь на канал {channel_id}"
            )
            await bot.restrict_chat_member(
                chat_id=chat_id,
                user_id=user_id,
                permissions=ChatPermissions(can_send_messages=False)
            )
            logger.info(f"Ограничен пользователь {user_id} в чате {chat_id}")
    except Exception as e:
        logger.error(f"Ошибка при проверке подписки или обработке сообщения: {e}")

if __name__ == '__main__':
    async def main():
        logger.info("Бот запущен")
        await dp.start_polling(bot)
    asyncio.run(main())
