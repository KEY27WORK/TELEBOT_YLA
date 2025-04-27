""" 🧭 webdriver_service.py — керування Selenium WebDriver для парсингу YoungLA.

🔹 Клас `WebDriverService`:
- Налаштовує Chrome WebDriver
- Завантажує HTML-сторінки з обробкою помилок
- Підтримує автоматичний перезапуск WebDriver при збої
- Реалізує Singleton (єдиний екземпляр на процес)
- Працює з контекстним менеджером (with WebDriverService() as driver)

Використовує:
- selenium для автоматизації браузера
- logging для логування подій
"""

# 🧱 Системні імпорти
import logging
import time

# 🌐 Selenium API
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By


class WebDriverService:
    """ 🧭 Клас-обгортка для Chrome WebDriver (Singleton).

    - Автоматично запускає драйвер
    - Підтримує restart та перевірку стану
    - Забезпечує стабільну роботу парсера при збої сторінки
    """

    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance.driver = None
        return cls._instance

    def setup_driver(self) -> None:
        """ 🔧 Ініціалізує Chrome WebDriver з потрібними параметрами.
        """
        if self.driver:
            logging.info("⚙️ WebDriver вже активний.")
            return

        logging.info("🚀 Запускаємо WebDriver...")
        options = Options()
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-gpu")
        options.add_argument("--window-size=1920,1080")
        options.add_argument("--disable-dev-shm-usage")

        try:
            self.driver = webdriver.Chrome(service=Service(), options=options)
            logging.info("✅ WebDriver успішно запущено.")
        except Exception as e:
            logging.error(f"❌ Помилка запуску WebDriver: {e}")
            self.driver = None

    def get_driver(self):
        """ 🔁 Повертає активний WebDriver, перезапускаючи його при необхідності.
        """
        if self.driver is None or not self.is_driver_alive():
            logging.warning("⚠️ WebDriver неактивний. Перезапускаємо...")
            self.setup_driver()
        return self.driver

    def quit_driver(self):
        """ 🛑 Завершує роботу драйвера."""
        if self.driver:
            logging.info("🧨 Закриваємо WebDriver...")
            self.driver.quit()
            self.driver = None
            logging.info("✅ WebDriver успішно завершено.")

    def restart_driver(self):
        """ 🔄 Перезапуск WebDriver."""
        logging.warning("🔄 Перезапуск WebDriver...")
        self.quit_driver()
        self.setup_driver()

    def is_driver_alive(self) -> bool:
        """ 🩺 Перевіряє, чи активний WebDriver (чи є відкриті вікна).
        """
        try:
            return self.driver and self.driver.window_handles
        except Exception:
            return False

    def fetch_page_source(self, url: str, max_retries: int = 5, retry_delay: int = 3) -> str | None:
        """ 🌐 Завантажує HTML-код сторінки.

        :param url: URL сторінки
        :param max_retries: Кількість спроб при невдачі
        :param retry_delay: Затримка між спробами (сек)
        :return: HTML або None
        """
        if not self.driver or not self.is_driver_alive():
            self.setup_driver()

        for attempt in range(1, max_retries + 1):
            try:
                logging.info(f"🌍 Спроба {attempt}/{max_retries}: завантаження {url}")
                self.driver.get(url)

                WebDriverWait(self.driver, 10).until(
                    EC.presence_of_element_located((By.TAG_NAME, "body"))
                )

                page_source = self.driver.page_source

                # Перевірка на капчу
                if "Your connection needs to be verified" in page_source or \
                   "Please complete the security check" in page_source:
                    logging.warning("⚠️ Виявлено захист Cloudflare! Повторна спроба...")
                    continue

                logging.info("✅ Сторінка успішно завантажена.")
                return page_source

            except Exception as e:
                logging.error(f"❌ Помилка завантаження сторінки: {e}")

                # Якщо драйвер "вмер" — перезапустимо
                if "no such window" in str(e) or "target window already closed" in str(e):
                    logging.warning("⚠️ Вікно WebDriver закрилось! Перезапуск...")
                    self.restart_driver()
                    continue

                if attempt < max_retries:
                    logging.info(f"🔄 Повтор через {retry_delay} сек...")
                    time.sleep(retry_delay)

        logging.error("❌ Спроби завантажити сторінку вичерпано.")
        return None

    def refresh_page(self):
        """ 🔄 Оновлює поточну сторінку."""
        if self.driver:
            logging.info("🔃 Оновлення сторінки...")
            self.driver.refresh()

    def __enter__(self):
        """ ▶️ Автоматичний запуск WebDriver у with-контексті."""
        self.setup_driver()
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        """ ⏹️ Завершення WebDriver при виході з контексту."""
        self.quit_driver()
