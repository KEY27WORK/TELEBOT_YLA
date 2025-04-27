""" 🖼️ image_downloader.py — завантаження зображень з URL.

🔹 Клас:
- `ImageDownloader` — відповідає за:
    - отримання зображення з мережі
    - збереження на диск
    - обробку помилок

📌 Використовує:
- `requests` для HTTP-запитів
- `logging` для логування

✅ Принципи SOLID:
- SRP — клас відповідає тільки за завантаження зображень
- DIP — не залежить від зовнішніх обробників або сервісів
"""

# 🧱 Системні імпорти
import logging
import requests
from typing import Optional


class ImageDownloader:
    """ 📥 Клас для завантаження зображень по URL і збереження на диск.
    """

    def __init__(self, image_path: str = "size_chart.png"):
        """ 🔧 Ініціалізація завантажувача.

        :param image_path: Шлях до файлу, куди буде збережено зображення.
        """
        self.image_path = image_path

    def download(self, img_url: str) -> Optional[str]:
        """ 🚀 Завантажує зображення з URL та зберігає його.

        :param img_url: URL зображення.
        :return: Шлях до збереженого файлу або None при помилці.
        """
        logging.info(f"📥 Завантаження зображення з {img_url}...")

        if not img_url:
            logging.error("❌ URL зображення відсутній!")
            return None

        try:
            response = requests.get(img_url, stream=True)
            response.raise_for_status()

            with open(self.image_path, "wb") as file:
                for chunk in response.iter_content(1024):
                    file.write(chunk)

            logging.info(f"✅ Зображення успішно збережено: {self.image_path}")
            return self.image_path

        except requests.RequestException as e:
            logging.error(f"❌ Помилка завантаження зображення: {e}")
            return None
