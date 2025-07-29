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

@dp.message(Command('start'))
async def cmd_start(message: types.Message):
    try:
        await message.answer("Привіт! Я бот-модератор. Щоб писати в цьому чаті, підпишіться на канал {}".format(CHANNEL_ID))
        logger.info(f"/start від {message.from_user.id}")
    except Exception as e:
        logger.error(f"Помилка у start handler: {e}")

@dp.message()
async def check_subscription(message: types.Message):
    # Логуємо ВСІ повідомлення для тестування
    logger.info(f"Отримано повідомлення: від {message.from_user.id} у чаті {message.chat.id} типу {message.chat.type}")
    
    # Перевіряємо, що це груповий чат
    if message.chat.type not in ["group", "supergroup"]:
        logger.info(f"Повідомлення не в групі: {message.chat.type}")
        return
    
    user_id = message.from_user.id
    chat_id = message.chat.id
    logger.info(f"Обробляємо повідомлення від {user_id} у чаті {chat_id}")
    
    try:
        logger.info(f"Перевіряємо підписку користувача {user_id} на канал {CHANNEL_ID}")
        member = await bot.get_chat_member(CHANNEL_ID, user_id)
        logger.info(f"Користувач {user_id} статус у каналі {CHANNEL_ID}: {member.status}")
        
        if member.status in ['member', 'administrator', 'creator']:
            logger.info(f"Користувач {user_id} підписаний, нічого не робимо")
            return  # Підписаний — нічого не робимо
        else:
            logger.info(f"Користувач {user_id} НЕ підписаний, видаляємо повідомлення")
            await message.delete()
            logger.info(f"Повідомлення від {user_id} видалено")
            
            await asyncio.sleep(0.5)
            
            # Перевіряємо наявність username
            username = message.from_user.username
            user_mention = f"@{username}" if username else f"користувач {user_id}"
            
            logger.info(f"Надсилаємо повідомлення про підписку для {user_mention}")
            await bot.send_message(
                chat_id=chat_id,
                text=f"🔒 {user_mention} чтобы писать в этом чате, пожалуйста, подпишитесь на канал {CHANNEL_ID}"
            )
            logger.info(f"Повідомлення про підписку надіслано")
            
            logger.info(f"Обмежуємо користувача {user_id}")
            await bot.restrict_chat_member(
                chat_id=chat_id,
                user_id=user_id,
                permissions=ChatPermissions(can_send_messages=False)
            )
            logger.info(f"Користувача {user_id} обмежено у чаті {chat_id}")
            
    except Exception as e:
        logger.error(f"Помилка при перевірці підписки або обробці повідомлення: {e}")
        logger.error(f"Деталі помилки: {type(e).__name__}: {str(e)}")

if __name__ == '__main__':
    async def main():
        logger.info("Бот запущено")
        try:
            # Спробуємо polling
            logger.info("Запускаємо polling...")
            await dp.start_polling(bot)
        except Exception as e:
            logger.error(f"Помилка при polling: {e}")
            logger.info("Спробуємо webhook...")
            # Якщо polling не працює, спробуємо webhook
            await dp.start_polling(bot, skip_updates=True)
    asyncio.run(main())
