from telebot.types import ReplyKeyboardMarkup, InlineKeyboardMarkup, InlineKeyboardButton
import config

def menu():
    markup = ReplyKeyboardMarkup(True, False)
    markup.row_width = 2
    markup.add("⚙️ Головне меню")
    markup.add("👑 Адмін панель")
    return markup

def main_menu():
    markup = InlineKeyboardMarkup()
    markup.row_width = 2
    markup.add(InlineKeyboardButton("ℹ️ Информація", callback_data="information"))
    return markup

def information():
    markup = InlineKeyboardMarkup()
    markup.row(InlineKeyboardButton("🤵Власник", url="https://t.me/Sergeant_MaKs"))
    markup.row(InlineKeyboardButton("🤖Наш флагманський продукт🤖", url="https://t.me/FastVEditorBot"))
    markup.row(InlineKeyboardButton("🏠 Головне меню ", callback_data="menu"))
    return markup

def subscribe():
    markup = InlineKeyboardMarkup()
    markup.add(InlineKeyboardButton("🖥 Перейти", url=config.channel_url))
    markup.add(InlineKeyboardButton("✅ Проверить", callback_data="menu"))
    return markup

def admin_menu():
    markup = InlineKeyboardMarkup()
    markup.row_width = 2
    
    # Экспорт данных
    markup.add(
        InlineKeyboardButton("📊 Экспорт JSON", callback_data="base_export_json"), 
        InlineKeyboardButton("🗄️ Экспорт SQL", callback_data="base_export_sql")
    )
    
    # Статистика и настройки
    markup.add(
        InlineKeyboardButton("📈 Статистика", callback_data="bot_statistics"),
        InlineKeyboardButton("⚙️ Настройки", callback_data="base_settings")
    )
    
    # Изменение настроек
    markup.add(
        InlineKeyboardButton("🔧 CHANNEL_ID", callback_data="change_channel_id"), 
        InlineKeyboardButton("🔨 CHANNEL_URL", callback_data="change_channel_url")
    )
    
    # Рассылка
    markup.add(InlineKeyboardButton("🔊 Рассылка", callback_data="sendall"))
    
    # Возврат в главное меню
    markup.add(InlineKeyboardButton("🔝 В главное меню 🔝", callback_data="menu"))
    
    return markup