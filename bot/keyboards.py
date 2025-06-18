"""
⌨️ keyboards.py — модуль для створення клавіатур Telegram-бота.

🔹 Клас `Keyboard`:
- Генерує головне меню (`main_menu`)
- Генерує inline-меню для роботи з курсом валют (`currency_menu`)
- Генерує inline-меню для допомоги (`help_menu`)

Використовує:
- Telegram ReplyKeyboardMarkup та InlineKeyboardMarkup
"""

# 🌐 Telegram API
from telegram import ReplyKeyboardMarkup, InlineKeyboardMarkup, InlineKeyboardButton


class Keyboard:
    """
    Клас для створення клавіатур Telegram-бота.
    """

                                                                                                                                                
    @staticmethod                                                                                                                                 
    def main_menu() -> ReplyKeyboardMarkup:                                                                                                       
        """                                                                                                                                       
        📋 Головне меню бота.                                                                                                                     
                                                                                                                                                  
        :return: ReplyKeyboardMarkup з основними пунктами.                                                                                        
        """                                                                                                                                       
        keyboard = [                                                                                                                              
            ["🔗 Вставляти посилання товарів", "📦 Мої замовлення"],                                                                              
            ["📚 Режим колекцій", "📏 Таблиця розмірів"],                                                                                         
            ["💱 Курс валют", "❓ Допомога"],                                                                                                     
            ["🧮 Режим розрахунку товару", "🌍 Перевірити розміри в регіонах"],                                                                   
            ["⏹️ Вимкнути режим"]                                                                                                                  
        ]                                                                                                                                         
        return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)    
 
    @staticmethod
    def currency_menu() -> InlineKeyboardMarkup:
        """
        💱 Меню для керування курсом валют.

        :return: InlineKeyboardMarkup з кнопками для перегляду та зміни курсу.
        """
        keyboard = [
            [InlineKeyboardButton("📊 Показати курс", callback_data="show_rate")],
            [InlineKeyboardButton("✏️ Встановити курс", callback_data="set_rate")]
        ]
        return InlineKeyboardMarkup(keyboard)

    @staticmethod
    def help_menu() -> InlineKeyboardMarkup:
        """
        🆘 Меню допомоги.

        :return: InlineKeyboardMarkup з кнопками допомоги та підтримки.
        """
        keyboard = [
            [InlineKeyboardButton("📝 FAQ", callback_data="faq")],
            [InlineKeyboardButton("📖 Як користуватись ботом?", callback_data="help_usage")],
            [InlineKeyboardButton("📞 Зв'язатися з підтримкою", callback_data="help_support")]
        ]
        return InlineKeyboardMarkup(keyboard)


