# 🚀 TELEBOTYLAUKRAINE

Телеграм-бот для просунутої роботи з **e-commerce**:  
парсинг товарів, мульти-регіональна перевірка наявності, розрахунок цін, генерація контенту та інтеграція з OpenAI API.

---

## 📌 Основні можливості

✅ **Парсинг товарів та колекцій** — асинхронне отримання даних із сайтів (ціна, фото, вага, наявність).  
✅ **Розрахунок цін** — бізнес-логіка з урахуванням доставки, комісій та динамічної націнки.  
✅ **Перевірка наявності** — паралельна перевірка кольорів та розмірів у регіонах (США, ЄС, Британія).  
✅ **Обробка таблиць розмірів** — OCR-розпізнавання та генерація таблиць у сантиметрах.  
✅ **Інтеграція з OpenAI** — переклад, генерація хештегів, музичні рекомендації.  
✅ **Playwright + Cloudflare Bypass** — надійний парсинг навіть із захистом Cloudflare.

---

## 📂 Архітектура та структура проєкту

Проєкт побудований за принципами **Clean Architecture**:  
логіка розділена на незалежні шари, що робить код гнучким, тестованим і простим у підтримці.

```bash
📦 TELEBOTYLAUKRAINE					# 🤖 Телеграм-бот для e-commerce
┣ 📂 app                                # 💡 Основний код додатку
┃ ┣ 📂 bot                              # 🤖 Telegram-бот (UI та команди)
┃ ┃ ┣ 📂 commands                       # 📜 Команди та фічі бота
┃ ┃ ┃ ┣ 📜 __init__.py
┃ ┃ ┃ ┣ 📜 base.py
┃ ┃ ┃ ┣ 📜 core_commands_feature.py
┃ ┃ ┃ ┣ 📜 currency_feature.py
┃ ┃ ┃ ┗ 📜 main_menu_feature.py
┃ ┃ ┣ 📂 handlers                       # 🔗 Обробники команд і посилань
┃ ┃ ┃ ┣ 📂 product						# 🛍️ Обробка товарів та колекцій
┃ ┃ ┃ ┃ ┣ 📜 collection_handler.py
┃ ┃ ┃ ┃ ┣ 📜 image_sender.py
┃ ┃ ┃ ┃ ┣ 📜 product_handler.py
┃ ┃ ┃ ┃ ┗ 📜 product_message_builder.py
┃ ┃ ┃ ┣ 📜 __init__.py
┃ ┃ ┃ ┣ 📜 callback_handler.py
┃ ┃ ┃ ┣ 📜 link_handler.py
┃ ┃ ┃ ┗ 📜 size_chart_handler.py
┃ ┃ ┣ 📂 ui                             # 🖼️ Клавіатури та UI-елементи
┃ ┃ ┃ ┣ 📜 __init__.py
┃ ┃ ┃ ┗ 📜 keyboards.py
┃ ┃ ┣ 📜 README.md
┃ ┃ ┣ 📜 __init__.py
┃ ┃ ┗ 📜 main.py                        # 🚀 Точка входу (запуск бота)
┃ ┣ 📂 config                           # ⚙️ Налаштування та DI-контейнер
┃ ┃ ┣ 📂 setup                          # 🛠️ Збірка та ініціалізація компонентів
┃ ┃ ┃ ┣ 📜 __init__.py
┃ ┃ ┃ ┣ 📜 bot_registrar.py
┃ ┃ ┃ ┣ 📜 constants.py
┃ ┃ ┃ ┗ 📜 container.py
┃ ┃ ┣ 📜 README.md
┃ ┃ ┣ 📜 __init__.py
┃ ┃ ┣ 📜 config.json
┃ ┃ ┣ 📜 config.yaml
┃ ┃ ┣ 📜 config_service.py				# 🔑 Робота з конфігами та API-ключами
┃ ┃ ┗ 📜 weights.json
┃ ┣ 📂 domain                           # 🧠 Чиста бізнес-логіка (ядро системи)
┃ ┃ ┣ 📂 availability                   # 🌍 Аггрегація наявності товарів
┃ ┃ ┃ ┣ 📜 interfaces.py
┃ ┃ ┃ ┗ 📜 services.py
┃ ┃ ┣ 📂 pricing                        # 💰 Розрахунок цін та фінансова логіка
┃ ┃ ┃ ┣ 📜 README.md
┃ ┃ ┃ ┣ 📜 __init__.py
┃ ┃ ┃ ┣ 📜 interfaces.py
┃ ┃ ┃ ┗ 📜 services.py
┃ ┃ ┣ 📂 products                       # 📦 Доменні сутності (ProductInfo тощо)
┃ ┃ ┃ ┣ 📜 __init__.py
┃ ┃ ┃ ┣ 📜 entities.py
┃ ┃ ┃ ┗ 📜 interfaces.py
┃ ┃ ┣ 📜 README.md
┃ ┃ ┗ 📜 __init__.py
┃ ┣ 📂 errors                           # 🐞 Обробка помилок
┃ ┃ ┣ 📜 __init__.py
┃ ┃ ┣ 📜 error_handler.py
┃ ┃ ┣ 📜 telegram_errors.py
┃ ┃ ┗ 📜 webdriver_errors.py
┃ ┣ 📂 html_pages                        # 📄 Зразки HTML-сторінок для тестів
┃ ┣ 📂 infrastructure                        # 🏗️ Робота із зовнішнім світом
┃ ┃ ┣ 📂 ai                                  # 🤖 OpenAI (переклад, генерація)
┃ ┃ ┃ ┣ 📜 open_ai_serv.py
┃ ┃ ┃ ┗ 📜 translator.py
┃ ┃ ┣ 📂 availability                        # 🌐 Мульти-регіональна перевірка
┃ ┃ ┃ ┣ 📜 availability_handler.py
┃ ┃ ┃ ┣ 📜 availability_manager.py
┃ ┃ ┃ ┣ 📜 cache_service.py
┃ ┃ ┃ ┣ 📜 config.py
┃ ┃ ┃ ┣ 📜 formatter.py
┃ ┃ ┃ ┗ 📜 report_builder.py
┃ ┃ ┣ 📂 content                             # 🧠 Генерація хештегів
┃ ┃ ┃ ┗ 📜 hashtag_generator.py
┃ ┃ ┣ 📂 currency                            # 💱 Отримання та кешування курсів валют
┃ ┃ ┃ ┣ 📜 currency_converter.py
┃ ┃ ┃ ┣ 📜 currency_manager.py
┃ ┃ ┃ ┗ 📜 current_rate.txt
┃ ┃ ┣ 📂 delivery                            # 🚚 Логіка доставки (Meest)
┃ ┃ ┃ ┗ 📜 meest_delivery_service.py
┃ ┃ ┣ 📂 music                               # 🎵 Робота з музикою
┃ ┃ ┃ ┣ 📜 __init__.py
┃ ┃ ┃ ┣ 📜 music_file_manager.py
┃ ┃ ┃ ┣ 📜 music_recommendation.py
┃ ┃ ┃ ┗ 📜 music_sender.py
┃ ┃ ┣ 📂 parsers                             # 🔎 Парсери товарів і колекцій
┃ ┃ ┃ ┣ 📂 collections
┃ ┃ ┃ ┃ ┗ 📜 universal_collection_parser.py
┃ ┃ ┃ ┣ 📂 product_search
┃ ┃ ┃ ┃ ┗ 📜 search_resolver.py
┃ ┃ ┃ ┣ 📂 products
┃ ┃ ┃ ┃ ┗ 📜 __init__.py
┃ ┃ ┃ ┣ 📜 __init__.py
┃ ┃ ┃ ┣ 📜 base_parser.py
┃ ┃ ┃ ┣ 📜 json_ld_parser.py
┃ ┃ ┃ ┣ 📜 parser_factory.py
┃ ┃ ┃ ┗ 📜 unified_parser.py
┃ ┃ ┣ 📂 size_chart                          # 📏 Таблиці розмірів (OCR, генерація)
┃ ┃ ┃ ┣ 📜 __init__.py
┃ ┃ ┃ ┣ 📜 image_downloader.py
┃ ┃ ┃ ┣ 📜 ocr_service.py
┃ ┃ ┃ ┣ 📜 size_chart_handler.py
┃ ┃ ┃ ┗ 📜 table_generator.py
┃ ┃ ┣ 📂 telegram                            # 📬 Telegram-хендлери
┃ ┃ ┃ ┣ 📂 handlers
┃ ┃ ┃ ┃ ┣ 📜 __init__.py
┃ ┃ ┃ ┃ ┗ 📜 price_calculator_handler.py
┃ ┃ ┃ ┗ 📜 __init__.py
┃ ┃ ┣ 📂 web                                 # 🌐 Playwright та WebDriver
┃ ┃ ┃ ┗ 📜 webdriver_service.py
┃ ┃ ┗ 📜 __init__.py
┃ ┣ 📂 logs                                  # 📝 Логи бота
┃ ┃ ┗ 📜 bot.log
┃ ┣ 📂 shared                                # 🧰 Загальні утиліти
┃ ┃ ┗ 📂 utils
┃ ┃ ┃ ┣ 📜 __init__.py
┃ ┃ ┃ ┣ 📜 logger.py
┃ ┃ ┃ ┣ 📜 prompt_service.py
┃ ┃ ┃ ┣ 📜 prompts.py
┃ ┃ ┃ ┣ 📜 region_utils.py
┃ ┃ ┃ ┣ 📜 url_parser_service.py
┃ ┃ ┃ ┗ 📜 url_utils.py
┃ ┗ 📜 __init__.py
┣ 📂 tests                                   # 🧪 Тести (у розробці)
┣ 📂 music_cache                             # 🎵 Кеш музичних файлів
┣ 📜 .env                                    # 🔐 Ключі API та токени
┣ 📜 pyproject.toml                          # 📦 Залежності (Poetry)
┗ 📜 README.md                               # 📘 Цей файл

⸻

🧩 Шари архітектури

🔹 domain — ядро системи. Тільки чиста логіка та моделі, без зовнішніх залежностей.
🔹 infrastructure — робота із зовнішнім світом: парсери, API, WebDriver, кеші.
🔹 bot — шар презентації (Telegram). Команди, хендлери, відправка повідомлень.
🔹 config — зв’язує всі частини системи через Dependency Injection.

⸻

🚀 Запуск бота

1️⃣ Встановіть залежності:

poetry install

2️⃣ Створіть .env та вкажіть ключі API:

OPENAI_API_KEY=your-key
TELEGRAM_BOT_TOKEN=your-token

3️⃣ Запуск бота:

poetry run python app/bot/main.py


⸻

🛠 Технології
	•	Python 3.11+
	•	Clean Architecture + Dependency Injection
	•	python-telegram-bot (Telegram Bot API)
	•	Playwright + BeautifulSoup
	•	OpenAI GPT-4
	•	yt-dlp (музика)

⸻

👤 Розробник

Кирилл / @key27
📬 Telegram: t.me/key27

⸻

📜 Ліцензія

MIT License