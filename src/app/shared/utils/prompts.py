# 📋 app/shared/utils/prompts.py
"""
📋 prompts.py — завантажує та форматує текстові шаблони для OpenAI.
"""

# 🔠 Системні імпорти
import logging																# 🧾 Логування
import json																	# 🧮 JSON-обробка
from enum import Enum														# 🏷️ Типобезпечні константи

# 🧩 Внутрішні модулі проєкту
from app.shared.utils.logger import LOG_NAME								# 🪪 Базове імʼя логера
from .prompt_loader import load_prompt, load_ocr_asset						# 📂 Завантаження промтів та OCR

# ================================
# 🧾 ІНІЦІАЛІЗАЦІЯ ЛОГЕРА
# ================================
logger = logging.getLogger(f"{LOG_NAME}.ai")

# ================================
# 🏷️ ENUMS ДЛЯ ТИПОБЕЗПЕЧНОСТІ
# ================================
class PromptType(str, Enum):
	MUSIC = "music"
	HASHTAGS = "hashtags"
	WEIGHT = "weight"
	CLOTHING_TYPE = "clothing_type"
	TRANSLATION = "translation"
	SLOGAN = "slogan"

class ChartType(str, Enum):
    GENERAL = "general"       # 📐 Класична таблиця
    UNIQUE = "unique"         # 🖌️ Адаптивна таблиця
    UNIQUE_GRID = "unique_grid"  # 🔲 Сіткова таблиця (вага × зріст)

# ================================
# 🏗️ ПІДГОТОВКА ШАБЛОНІВ ПРИ СТАРТІ
# ================================
_BASE_OCR_PROMPT_TEMPLATE = load_ocr_asset("base.txt")								# 📄 Базовий шаблон для OCR
_PROMPTS_LIBRARY = {}															    # 🗂️ Словник шаблонів

missing_files = []																	# ❌ Відсутні файли
for pt in PromptType:
	try:
		_PROMPTS_LIBRARY[pt] = load_prompt(f"{pt.value}.txt")					    # 📥 Завантаження шаблону
	except FileNotFoundError:
		missing_files.append(f"{pt.value}.txt")

if missing_files:
	raise RuntimeError(f"🚨 Критична помилка: відсутні файли промтів: {', '.join(missing_files)}")

# ================================
# 🏭 ПУБЛІЧНІ ФУНКЦІЇ-КОНСТРУКТОРИ
# ================================

def get_size_chart_prompt(chart_type: ChartType) -> str:
	"""
	📏 Отримує промт для таблиці розмірів, збираючи його з шаблону та JSON-прикладу.
	"""
	if chart_type not in ChartType:
		raise ValueError(f"Невідомий тип таблиці розмірів: '{chart_type}'")
        
	logger.debug(f"Запит промта для таблиці розмірів типу: '{chart_type.value}'")

	example_file = f"example_{chart_type.value}.json"
	try:
		example_data = json.loads(load_ocr_asset(example_file))						# 📂 Завантаження прикладу
	except (FileNotFoundError, json.JSONDecodeError) as e:
		logger.error(f"❌ Не вдалося завантажити або розпарсити приклад для OCR: {example_file} - {e}")
		raise ValueError(f"Некоректний файл прикладу для OCR: {example_file}")

	conditions = {
		ChartType.UNIQUE: "Поверни лише JSON і нічого більше...",
		ChartType.GENERAL: "Поверни JSON з масивами значень..."
	}

	prompt = _BASE_OCR_PROMPT_TEMPLATE.format(
		extra_conditions=conditions.get(chart_type, ""),
		example_json=json.dumps(example_data, indent=4, ensure_ascii=False)
	)

	logger.debug(f"📤 Згенерований OCR промт ({chart_type.value}):\n{prompt[:400]}...")
	return prompt

def get_prompt(prompt_type: PromptType, **kwargs) -> str:
	"""
	🧠 Повертає текстовий промт із шаблону, підставляючи параметри.
	""" 
	
	if prompt_type not in PromptType:
		raise ValueError(f"Невідомий тип промта: '{prompt_type}'")

	logger.debug(f"Запит промта типу: '{prompt_type.value}' з параметрами: {list(kwargs.keys())}")

	prompt_template = _PROMPTS_LIBRARY.get(prompt_type)
	if not prompt_template:
		raise ValueError(f"Промт '{prompt_type.value}' не знайдено!")

	safe_kwargs = {k: v if v is not None else "" for k, v in kwargs.items()}		# 🧼 Безпечне форматування
	formatted_prompt = prompt_template.format(**safe_kwargs)

	logger.debug(f"📤 Згенерований промт ({prompt_type.value}):\n{formatted_prompt[:400]}...")
	return formatted_prompt
