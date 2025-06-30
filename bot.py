import telebot
from telebot.apihelper import ApiTelegramException
import os
import downloader
import config
import keyboards
import json
import logging
from pathlib import Path
from database import db_manager
import yt_dlp

# ВАЖНО: Для корректной работы проверки подписки нужны публичные каналы с @username
# Или используйте числовые ID каналов, но тогда бот должен быть администратором этих каналов
REQUIRED_CHANNELS = [
    {"id": "-1002397757887", "name": "НАРОД | Робота Київ🇺🇦", "url": "https://t.me/+vPRsg7xEfb4yZWEy"},
    {"id": "-1002400023551", "name": "НАРОД | Віддалена робота🇺🇦", "url": "https://t.me/+lB3HA50hyLIxNGNi"},
    {"id": "-1002649530761", "name": "НАРОД | Робота Вишневе🇺🇦", "url": "https://t.me/+GfUSmrF1tLwyMGQ6"},
]

bot = telebot.TeleBot(config.token)
adm_state = {}

# Настройка логирования
logging.basicConfig(
    level=logging.INFO, 
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('bot.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)

def safe_text(text):
    if text is None:
        return ""
    return str(text).encode("utf-8", "ignore").decode("utf-8")

def extract_user_data(user):
    """Извлекает данные пользователя из объекта Telegram User"""
    return {
        'user_id': user.id,
        'username': user.username,
        'first_name': user.first_name,
        'last_name': user.last_name,
        'language_code': user.language_code,
        'is_bot': user.is_bot,
        'is_premium': getattr(user, 'is_premium', False)  # На случай если поле отсутствует
    }

def check_subscriptions(user_id):
    """Проверяет подписки пользователя на все необходимые каналы"""
    unsubscribed = []
    
    for channel in REQUIRED_CHANNELS:
        try:
            # Получаем информацию об участнике канала
            member = bot.get_chat_member(channel['id'], user_id)
            
            logging.info(f"User {user_id} status in channel {channel['id']}: {member.status}")
            
            if member.status in ["left", "kicked"]:
                logging.info(f"User {user_id} is not subscribed to {channel['name']}")
                unsubscribed.append(channel)
            else:
                logging.info(f"User {user_id} is subscribed to {channel['name']}")
                
        except ApiTelegramException as e:
            logging.warning(f"API Error while checking {channel['id']} for user {user_id}: {e}")
            
            if "user not found" in str(e).lower() or "not found" in str(e).lower():
                logging.info(f"User {user_id} not found in channel {channel['name']} - not subscribed")
                unsubscribed.append(channel)
            elif "bot is not a member" in str(e).lower() or "forbidden" in str(e).lower():
                logging.error(f"Bot is not admin in channel {channel['name']}. Cannot check subscription.")
                unsubscribed.append(channel)
            else:
                logging.error(f"Unknown API error for channel {channel['name']}: {e}")
                unsubscribed.append(channel)
                
        except Exception as e:
            logging.error(f"Unexpected error while checking {channel['id']} for user {user_id}: {e}")
            unsubscribed.append(channel)
    
    logging.info(f"User {user_id} unsubscribed channels: {len(unsubscribed)}")
    return unsubscribed

@bot.message_handler(commands=['start'])
def start_command(message):
    user_id = message.from_user.id
    username = message.from_user.username or "Unknown"
    logging.info(f"Start command from user {user_id} (@{username})")
    
    # Сохраняем полную информацию о пользователе
    user_data = extract_user_data(message.from_user)
    db_manager.save_user(user_data)
    
    unsubscribed = check_subscriptions(user_id)
    if unsubscribed:
        send_subscription_message(user_id, unsubscribed)
    else:
        bot.send_message(user_id, safe_text('*Добро пожаловать! Отправьте ссылку на YouTube видео для скачивания.*'), 
                        parse_mode="markdown", reply_markup=keyboards.main_menu())

def send_subscription_message(user_id, unsubscribed_channels):
    text = "⚠️ *Для использования бота необходимо подписаться на все каналы:*\n\n"
    markup = telebot.types.InlineKeyboardMarkup(row_width=1)
    
    for i, ch in enumerate(unsubscribed_channels, 1):
        text += f"{i}. [{ch['name']}]({ch['url']})\n"
        markup.add(telebot.types.InlineKeyboardButton(f"📢 {ch['name']}", url=ch['url']))
    
    text += "\n_После подписки на все каналы нажмите кнопку ниже:_"
    markup.add(telebot.types.InlineKeyboardButton("✅ Проверить подписку", callback_data="check_subscription"))
    
    try:
        bot.send_message(user_id, safe_text(text), parse_mode="markdown", reply_markup=markup, disable_web_page_preview=True)
    except Exception as e:
        logging.error(f"Error sending subscription message: {e}")
        # Fallback без markdown
        simple_text = "Для использования бота необходимо подписаться на все каналы."
        bot.send_message(user_id, simple_text, reply_markup=markup)

@bot.message_handler(func=lambda message: True)
def handle_message(message):
    user_id = message.from_user.id
    
    # Сохраняем/обновляем пользователя в базе данных
    user_data = extract_user_data(message.from_user)
    db_manager.save_user(user_data)
    
    # Проверяем подписки
    unsubscribed = check_subscriptions(user_id)
    if unsubscribed:
        send_subscription_message(user_id, unsubscribed)
        return

    # Обработка команд админа
    if message.text == 'panda' and user_id in config.admin_ids:
        bot.send_message(user_id, safe_text('🥰 *Привет, админ!*'), 
                        parse_mode='markdown', reply_markup=keyboards.admin_menu())
        return
    
    # Обработка состояний админа
    if user_id in adm_state:
        handle_admin_state(message, user_id)
        return
    
    # Обработка YouTube ссылок
    if 'youtube.com' in message.text.lower() or 'youtu.be' in message.text.lower():
        download_youtube_video(message, user_id)
    elif message.text == '⚙️ Главное меню':
        bot.send_message(user_id, safe_text('*Главное меню*'), 
                        parse_mode='markdown', reply_markup=keyboards.main_menu())
    else:
        bot.send_message(user_id, safe_text('*Отправьте ссылку на YouTube видео для скачивания.*'), 
                        parse_mode='markdown', reply_markup=keyboards.main_menu())

def handle_admin_state(message, user_id):
    state = adm_state[user_id]
    
    if state['state'] == 'change':
        try:
            config.settings[state['who']] = message.text
            with open('settings.json', 'w', encoding='utf-8') as f:
                json.dump(config.settings, f, indent=4, ensure_ascii=False)
            del adm_state[user_id]
            bot.send_message(user_id, safe_text('*Настройка изменена!*'), 
                           parse_mode='markdown', reply_markup=keyboards.admin_menu())
        except Exception as e:
            logging.error(f"Error saving settings: {e}")
            bot.send_message(user_id, safe_text('❌ Ошибка при сохранении настроек.'))
    
    elif state['state'] == 'sendall':
        good, bad = 0, 0
        all_users = db_manager.get_all_users()
        
        for user in all_users:
            try:
                bot.send_message(user['user_id'], safe_text(message.text), parse_mode='markdown')
                good += 1
            except Exception as e:
                logging.warning(f"Failed to send message to {user['user_id']}: {e}")
                bad += 1
        
        del adm_state[user_id]
        bot.send_message(user_id, safe_text(f'*Рассылка завершена:*\n✅ Доставлено: {good}\n❌ Не доставлено: {bad}'), 
                        parse_mode='markdown', reply_markup=keyboards.admin_menu())

def get_video_title(url):
    """Получает название видео по URL"""
    try:
        ydl_opts = {
            'quiet': True,
            'no_warnings': True,
        }
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            return info.get('title', 'Unknown')
    except:
        return 'Unknown'

def download_youtube_video(message, user_id):
    msg = bot.send_message(user_id, safe_text('⏳ _Идёт загрузка..._'), parse_mode='markdown')
    download_obj = None
    video_title = None
    file_size = None
    success = False
    
    try:
        logging.info(f"Starting download for user {user_id}: {message.text}")
        
        # Получаем название видео
        video_title = get_video_title(message.text)
        
        # Создаем объект загрузчика
        download_obj = downloader.Download(message.text)
        video_path = download_obj.file
        
        if not video_path or not os.path.exists(video_path):
            raise FileNotFoundError("Файл не был загружен")
        
        # Проверяем размер файла
        file_size = os.path.getsize(video_path)
        if file_size > 50 * 1024 * 1024:  # 50MB
            raise Exception("Файл слишком большой для отправки через Telegram")
        
        # Обновляем сообщение
        bot.edit_message_text(safe_text('✅ _Готово! Отправляю файл..._'), 
                             user_id, msg.message_id, parse_mode='markdown')
        
        # Отправляем файл
        with open(video_path, 'rb') as video:
            bot.send_video(
                chat_id=message.chat.id,
                video=video,
                caption="Не встиг занудьгувати? \n\nНасолоджуйся, бро😎",
                supports_streaming=True,  # Поддержка потокового воспроизведения
                width=1920,  # Ширина видео (если известна)
                height=1080,  # Высота видео (если известна)
                duration=None  # Длительность (если известна)
            )
        
        success = True
        logging.info(f"Successfully sent video to user {user_id}")
        
        # Удаляем сообщение о загрузке
        try:
            bot.delete_message(user_id, msg.message_id)
        except:
            pass
            
    except Exception as e:
        error_msg = str(e)
        logging.error(f"Download error for user {user_id}: {error_msg}")
        
        try:
            bot.edit_message_text(safe_text(f'❌ Помилка при скачуванні відео: {error_msg}'), 
                                 user_id, msg.message_id)
        except:
            bot.send_message(user_id, safe_text(f'❌ Помилка при скачуванні відео: {error_msg}'))
    
    finally:
        # Записываем информацию о загрузке в базу данных
        db_manager.add_download(
            user_id=user_id,
            video_url=message.text,
            video_title=video_title,
            file_size=file_size,
            success=success
        )
        
        # Очищаем временные файлы
        if download_obj:
            try:
                download_obj.cleanup()
            except:
                pass

@bot.callback_query_handler(func=lambda call: True)
def callbacks(call):
    user_id = call.from_user.id
    
    try:
        if call.data == 'check_subscription':
            unsubscribed = check_subscriptions(user_id)
            if unsubscribed:
                bot.answer_callback_query(call.id, f"❌ Подпишитесь на все каналы!\nОсталось: {len(unsubscribed)}", show_alert=True)
                # Обновляем сообщение с актуальным списком
                send_subscription_message(user_id, unsubscribed)
                try:
                    bot.delete_message(user_id, call.message.message_id)
                except:
                    pass
            else:
                bot.answer_callback_query(call.id, "✅ Отлично! Добро пожаловать!")
                bot.edit_message_text(safe_text('*🎉 Добро пожаловать!*\n\nТеперь вы можете пользоваться ботом.\nОтправьте ссылку на YouTube видео для скачивания.'), 
                                    user_id, call.message.message_id, 
                                    parse_mode='markdown', reply_markup=keyboards.main_menu())
        
        elif call.data == 'menu':
            bot.edit_message_text(safe_text('*Главное меню*'), 
                                user_id, call.message.message_id, 
                                parse_mode='markdown', reply_markup=keyboards.main_menu())
        
        elif call.data == 'information':
            bot.edit_message_text(safe_text('ℹ️ *Информация о боте*'), 
                                user_id, call.message.message_id, 
                                parse_mode='markdown', reply_markup=keyboards.information())
        
        # Админские callback'и
        elif call.data in ['base_export_json', 'base_export_sql', 'base_settings', 'bot_statistics', 
                          'change_channel_id', 'change_channel_url', 'sendall']:
            handle_admin_callbacks(call)
            
    except Exception as e:
        logging.error(f"Callback error: {e}")
        bot.answer_callback_query(call.id, "Произошла ошибка")

def handle_admin_callbacks(call):
    user_id = call.from_user.id
    
    if user_id not in config.admin_ids:
        bot.answer_callback_query(call.id, "❌ Доступ запрещен!")
        return
    
    if call.data == 'base_export_json':
        try:
            # Экспортируем в JSON
            json_file = db_manager.export_to_json()
            
            # Получаем статистику
            stats = db_manager.get_statistics()
            
            with open(json_file, 'rb') as f:
                bot.send_document(
                    user_id, 
                    f,
                    caption=f"📊 *База пользователей (JSON)*\n\n"
                           f"👥 Всего пользователей: {stats.get('total_users', 0)}\n"
                           f"🔥 Активных: {stats.get('active_users', 0)}\n"
                           f"📥 Всего загрузок: {stats.get('total_downloads', 0)}\n"
                           f"✅ Успешных: {stats.get('successful_downloads', 0)}\n"
                           f"📈 Успешность: {stats.get('success_rate', 0):.1f}%",
                    parse_mode='markdown'
                )
            
            # Удаляем временный файл
            os.remove(json_file)
            
        except Exception as e:
            logging.error(f"JSON export error: {e}")
            bot.send_message(user_id, "❌ Ошибка при экспорте в JSON")
    
    elif call.data == 'base_export_sql':
        try:
            # Экспортируем в SQL
            sql_file = db_manager.export_to_sql()
            
            if sql_file:
                with open(sql_file, 'rb') as f:
                    bot.send_document(
                        user_id, 
                        f,
                        caption="🗄️ *Экспорт базы данных (SQL)*\n\nПолная копия базы данных со схемой и данными",
                        parse_mode='markdown'
                    )
                
                # Удаляем временный файл
                os.remove(sql_file)
            else:
                bot.send_message(user_id, "❌ Ошибка при создании SQL экспорта")
            
        except Exception as e:
            logging.error(f"SQL export error: {e}")
            bot.send_message(user_id, "❌ Ошибка при экспорте в SQL")
    
    elif call.data == 'bot_statistics':
        try:
            stats = db_manager.get_statistics()
            
            stats_text = f"""📊 *Статистика бота*

👥 *Пользователи:*
• Всего: {stats.get('total_users', 0)}
• Активных: {stats.get('active_users', 0)}

📥 *Загрузки:*
• Всего: {stats.get('total_downloads', 0)}
• Успешных: {stats.get('successful_downloads', 0)}
• Успешность: {stats.get('success_rate', 0):.1f}%

🏆 *Топ пользователей:*"""

            top_users = stats.get('top_users', [])
            for i, user in enumerate(top_users[:5], 1):
                name = user.get('first_name', '') or user.get('username', f"ID{user['user_id']}")
                stats_text += f"\n{i}. {name} - {user['download_count']} загрузок"
            
            bot.send_message(user_id, safe_text(stats_text), parse_mode='markdown')
            
        except Exception as e:
            logging.error(f"Statistics error: {e}")
            bot.send_message(user_id, "❌ Ошибка при получении статистики")
    
    elif call.data == 'base_settings':
        try:
            settings_text = json.dumps(config.settings, indent=2, ensure_ascii=False)
            
            # Создаем временный файл
            settings_file = f'settings_export_{user_id}.json'
            with open(settings_file, 'w', encoding='utf-8') as f:
                f.write(settings_text)
            
            with open(settings_file, 'rb') as f:
                bot.send_document(
                    user_id,
                    f,
                    caption="⚙️ Текущие настройки бота"
                )
            
            # Удаляем временный файл
            os.remove(settings_file)
            
        except Exception as e:
            logging.error(f"Settings export error: {e}")
            bot.send_message(user_id, "❌ Ошибка при экспорте настроек")
    
    elif call.data == 'change_channel_id':
        adm_state[user_id] = {'state': 'change', 'who': 'channel_id'}
        bot.send_message(user_id, "Отправьте новый ID канала:")
    
    elif call.data == 'change_channel_url':
        adm_state[user_id] = {'state': 'change', 'who': 'channel_url'}
        bot.send_message(user_id, "Отправьте новую ссылку на канал:")
    
    elif call.data == 'sendall':
        adm_state[user_id] = {'state': 'sendall'}
        bot.send_message(user_id, "Отправьте сообщение для рассылки:")

if __name__ == "__main__":
    # Создаем необходимые папки
    Path("downloads").mkdir(exist_ok=True)
    
    # Инициализируем базу данных
    db_manager.init_database()
    
    logging.info("Bot starting...")
    try:
        bot.remove_webhook()
        bot.infinity_polling(none_stop=True, timeout=10, long_polling_timeout=5)
    except Exception as e:
        logging.error(f"Bot crashed: {e}")
        raise