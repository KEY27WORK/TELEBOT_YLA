""" 🧠 prompt_service.py — сервіс генерації промтів для OpenAI GPT-4.

Цей модуль:
- Забезпечує генерацію промтів для різних задач (переклад, хештеги, слогани, музика тощо).
- Використовується в TranslatorService, HashtagGenerator, MusicRecommendation.
- Логує запити до системи промтів.

Використовує:
- Системне логування (console + файл)
- Функції get_prompt, get_size_chart_prompt з utils.prompts
"""

# 🧱 Системні імпорти
import logging

# 📦 Локальні утиліти
from utils.prompts import get_prompt, get_size_chart_prompt


class PromptService:
    """ 🔧 Сервіс для створення промтів до OpenAI.
    
    Залежить від шаблонів промтів у файлі prompts.py.
    """

    @staticmethod
    def get_slogan_prompt(title: str, description: str) -> str:
        """ 🎯 Промт для генерації слогану.

        :param title: Назва товару
        :param description: Опис товару
        :return: Текст промта
        """
        return get_prompt("slogan", title=title, description=description)

    @staticmethod
    def get_music_prompt(title: str, description: str, image_url: str) -> str:
        """ 🎵 Промт для підбору музики.

        :param title: Назва товару
        :param description: Опис товару
        :param image_url: Посилання на зображення
        :return: Текст промта
        """
        return get_prompt("music", title=title, description=description, image_url=image_url)

    @staticmethod
    def get_translation_prompt(text: str) -> str:
        """ 🌍 Промт для перекладу опису товару.

        :param text: Опис товару англійською
        :return: Промт з інструкціями перекладу
        """
        return get_prompt("translation", text=text)

    @staticmethod
    def get_clothing_type_prompt(title: str) -> str:
        """ 🧥 Промт для визначення типу одягу.

        :param title: Назва товару
        :return: Промт до GPT
        """
        return get_prompt("clothing_type", title=title)

    @staticmethod
    def get_weight_prompt(title: str, description: str, image_url: str) -> str:
        """ ⚖️ Промт для оцінки ваги товару.

        :param title: Назва
        :param description: Опис
        :param image_url: Картинка
        :return: Промт
        """
        return get_prompt("weight", title=title, description=description, image_url=image_url)

    @staticmethod
    def get_hashtags_prompt(title: str, description: str) -> str:
        """ #️⃣ Промт для генерації AI-хештегів.

        :param title: Назва
        :param description: Опис
        :return: Промт
        """
        return get_prompt("hashtags", title=title, description=description)

    @staticmethod
    def get_size_chart_prompt(chart_type: str) -> str:
        """ 📏 Промт для конвертації таблиці розмірів.

        :param chart_type: Тип таблиці (наприклад, men's shorts)
        :return: Промт
        """
        logging.info(f"🔎 Отримання промта для розміру: {chart_type}")
        return get_size_chart_prompt(chart_type)

