import logging
import os
from aiogram import Bot, Dispatcher, types
from aiogram.types import ChatPermissions
from aiogram.filters import Command
import asyncio

# Отримуємо змінні середовища або використовуємо значення за замовчуванням
API_TOKEN = os.getenv('API_TOKEN', '7739860939:AAFvk9wdbdpCJ5L17WSb7YkaORGU09LTsDE')
CHANNEL_ID = os.getenv('CHANNEL_ID', '@shifuweb3')

# Налаштування логування
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

bot = Bot(token=API_TOKEN)
dp = Dispatcher()

@dp.message()
async def check_subscription(message: types.Message):
    # Перевіряємо, що це груповий чат
    if message.chat.type not in ["group", "supergroup"]:
        return
    user_id = message.from_user.id
    chat_id = message.chat.id
    try:
        member = await bot.get_chat_member(CHANNEL_ID, user_id)
        logger.info(f"Користувач {user_id} статус у каналі {CHANNEL_ID}: {member.status}")
        if member.status in ['member', 'administrator', 'creator']:
            return  # Підписаний — нічого не робимо
        else:
            await message.delete()
            await asyncio.sleep(0.5)
            await bot.send_message(
                chat_id=chat_id,
                text=f"🔒 @{message.from_user.username} чтобы писать в этом чате,пожалуйста,подпишитесь на канал {CHANNEL_ID}"
            )
            await bot.restrict_chat_member(
                chat_id=chat_id,
                user_id=user_id,
                permissions=ChatPermissions(can_send_messages=False)
            )
            logger.info(f"Обмежено користувача {user_id} у чаті {chat_id}")
    except Exception as e:
        logger.error(f"Помилка при перевірці підписки або обробці повідомлення: {e}")

if __name__ == '__main__':
    async def main():
        logger.info("Бот запущено")
        await dp.start_polling(bot)
    asyncio.run(main())
