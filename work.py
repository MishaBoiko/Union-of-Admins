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
    waiting_for_group = State()

# Словарь для хранения каналов по пользователям и группам
# Структура: {user_id: {group_id: channel_username}}
USER_CHANNELS = {}

@dp.message(Command('start'))
async def cmd_start(message: types.Message, state: FSMContext):
    await message.answer('Введите ЮЗ канала на который нужно ОП')
    await state.set_state(ChannelSetup.waiting_for_channel)
    logger.info(f"/start от {message.from_user.id} в чате {message.chat.id}")

@dp.message(ChannelSetup.waiting_for_channel)
async def process_channel_username(message: types.Message, state: FSMContext):
    channel_username = message.text.strip()
    
    # Проверяем, начинается ли с @
    if not channel_username.startswith('@'):
        channel_username = '@' + channel_username
    
    # Сохраняем канал во временное хранилище
    await state.update_data(channel=channel_username)
    await message.answer(f'Канал {channel_username} принят. Теперь отправьте ID группы где бот должен работать (или перешлите сообщение из группы).')
    await state.set_state(ChannelSetup.waiting_for_group)
    logger.info(f"Канал принят: {channel_username} пользователем {message.from_user.id}")

@dp.message(ChannelSetup.waiting_for_group)
async def process_group_id(message: types.Message, state: FSMContext):
    user_id = message.from_user.id
    
    # Получаем сохраненный канал
    data = await state.get_data()
    channel_username = data.get('channel')
    
    # Определяем ID группы
    group_id = None
    group_title = None
    
    if message.forward_from_chat:
        # Если переслано сообщение из группы
        group_id = message.forward_from_chat.id
        group_title = message.forward_from_chat.title
        logger.info(f"Получена пересланная группа: {group_title} (ID: {group_id})")
    elif message.text:
        # Проверяем, является ли текст ссылкой на группу
        if 't.me/' in message.text or 'telegram.me/' in message.text:
            try:
                # Извлекаем username из ссылки
                if 't.me/' in message.text:
                    username = message.text.split('t.me/')[-1].split('/')[0]
                else:
                    username = message.text.split('telegram.me/')[-1].split('/')[0]
                
                # Убираем @ если есть
                if username.startswith('@'):
                    username = username[1:]
                
                # Получаем информацию о чате
                chat_info = await bot.get_chat(f"@{username}")
                group_id = chat_info.id
                group_title = chat_info.title
                logger.info(f"Получена группа по ссылке: {group_title} (ID: {group_id})")
            except Exception as e:
                logger.error(f"Ошибка при обработке ссылки на группу: {e}")
                await message.answer('❌ Не удалось получить информацию о группе по ссылке. Попробуйте переслать сообщение из группы или ввести ID группы.')
                return
        elif message.text.isdigit():
            # Если введен ID группы
            group_id = int(message.text)
            logger.info(f"Получен ID группы: {group_id}")
        else:
            await message.answer('Пожалуйста, перешлите сообщение из группы, отправьте ссылку на группу или введите ID группы.')
            return
    else:
        await message.answer('Пожалуйста, перешлите сообщение из группы, отправьте ссылку на группу или введите ID группы.')
        return
    
    try:
        # Проверяем доступ к группе
        chat_info = await bot.get_chat(group_id)
        logger.info(f"Группа найдена: {chat_info.title} (ID: {group_id})")
        
        # Проверяем права бота в группе
        bot_member = await bot.get_chat_member(group_id, bot.id)
        logger.info(f"Бот в группе {group_id}: {bot_member.status}")
        
        if bot_member.status not in ['administrator', 'creator']:
            await message.answer(f'⚠️ Бот должен быть администратором в группе "{chat_info.title}". Добавьте бота как администратора и попробуйте снова.')
            await state.clear()
            return
        
        # Проверяем доступ к каналу
        try:
            channel_info = await bot.get_chat(channel_username)
            logger.info(f"Канал найден: {channel_info.title}")
        except Exception as e:
            logger.warning(f"Не удалось получить доступ к каналу {channel_username}: {e}")
            await message.answer(f'⚠️ Не удалось получить доступ к каналу {channel_username}. Убедитесь, что бот добавлен в канал.')
            await state.clear()
            return
        
        # Инициализируем словарь для пользователя, если его нет
        if user_id not in USER_CHANNELS:
            USER_CHANNELS[user_id] = {}
        
        # Очищаем старые настройки для этой группы у этого пользователя и сохраняем новые
        if group_id in USER_CHANNELS[user_id]:
            old_channel = USER_CHANNELS[user_id][group_id]
            logger.info(f"Пользователь {user_id} заменяет старый канал {old_channel} на новый {channel_username} для группы {group_id}")
        
        USER_CHANNELS[user_id][group_id] = channel_username
        
        await message.answer(f'✅ Настройки сохранены!\n\nГруппа: {chat_info.title}\nКанал: {channel_username}\n\nБот готов к работе в указанной группе.')
        await state.clear()
        logger.info(f"Настройки сохранены для пользователя {user_id}: группа {group_id} -> канал {channel_username}")
        
    except Exception as e:
        logger.error(f"Ошибка при настройке группы: {e}")
        await message.answer(f'❌ Ошибка: не удалось получить доступ к группе. Убедитесь, что:\n1. ID группы правильный\n2. Бот добавлен в группу\n3. У бота есть права администратора')
        await state.clear()

@dp.message()
async def check_subscription(message: types.Message):
    # Логируем ВСЕ сообщения для диагностики
    logger.info(f"Получено сообщение: от {message.from_user.id} в чате {message.chat.id} типа {message.chat.type}")
    
    chat_id = message.chat.id
    
    # Проверяем, установлен ли канал для этой группы у этого пользователя
    user_id = message.from_user.id
    if user_id not in USER_CHANNELS or chat_id not in USER_CHANNELS[user_id]:
        logger.info(f"Канал не установлен для пользователя {user_id} в чате {chat_id}")
        return
    
    channel_id = USER_CHANNELS[user_id][chat_id]
    logger.info(f"Используем канал {channel_id} для пользователя {user_id} в чате {chat_id}")
    
    logger.info(f"message_thread_id: {message.message_thread_id}")
    # Проверяем, что это групповой чат
    if message.chat.type not in ["group", "supergroup"]:
        logger.info(f"Сообщение не в группе: {message.chat.type}")
        return
    
    logger.info(f"Обрабатываем сообщение в группе {chat_id}")
    try:
        logger.info(f"Проверяем подписку пользователя {user_id} на канал {channel_id}")
        
        # Проверяем, может ли бот получить информацию о канале
        try:
            chat_info = await bot.get_chat(channel_id)
            logger.info(f"Канал {channel_id} найден: {chat_info.title}")
        except Exception as e:
            logger.error(f"Бот не может получить доступ к каналу {channel_id}: {e}")
            await message.answer(f"⚠️ Бот не может проверить подписку на канал {channel_id}. Убедитесь, что бот добавлен в канал как администратор.")
            return
        
        # Проверяем подписку пользователя
        member = await bot.get_chat_member(channel_id, user_id)
        logger.info(f"Пользователь {user_id} статус в канале {channel_id}: {member.status}")
        
        if member.status in ['member', 'administrator', 'creator']:
            logger.info(f"Пользователь {user_id} подписан, ничего не делаем")
            return  # Подписан — ничего не делаем
        else:
            logger.info(f"Пользователь {user_id} НЕ подписан, удаляем сообщение")
            await message.delete()
            logger.info(f"Сообщение от {user_id} удалено")
            await asyncio.sleep(0.5)
            username = message.from_user.username
            user_mention = f"@{username}" if username else f"пользователь {user_id}"
            logger.info(f"Отправляем сообщение о подписке для {user_mention}")
            await bot.send_message(
                chat_id=chat_id,
                text=f"🔒 {user_mention} чтобы писать в этом чате, пожалуйста, подпишитесь на канал {channel_id}"
            )
            logger.info(f"Сообщение о подписке отправлено")
            logger.info(f"Ограничиваем пользователя {user_id}")
            await bot.restrict_chat_member(
                chat_id=chat_id,
                user_id=user_id,
                permissions=ChatPermissions(can_send_messages=False)
            )
            logger.info(f"Ограничен пользователь {user_id} в чате {chat_id}")
    except Exception as e:
        logger.error(f"Ошибка при проверке подписки или обработке сообщения: {e}")
        logger.error(f"Детали ошибки: {type(e).__name__}: {str(e)}")

if __name__ == '__main__':
    async def main():
        logger.info("Бот запущен")
        await dp.start_polling(bot)
    asyncio.run(main())
