# 🖼️ src/app/infrastructure/parsers/extractors/images.py
"""
🖼️ ImagesMixin — набір утиліт для отримання головного й додаткових зображень товару.

🔹 Нормалізує URL (Shopify суфікси, query-параметри) та відфільтровує зайві картинки.
🔹 Використовує дані з JSON-LD, HTML-контейнерів та конфігураційних фільтрів.
🔹 Підтримує обмеження списку, відсіювання «малих» зображень та збереження порядку.
"""

from __future__ import annotations

# 🌐 Зовнішні бібліотеки
import re									# 🧪 Регулярні вирази для розпізнавання розмірів
from bs4.element import Tag				# 🧱 Ноди BeautifulSoup

# 🔠 Системні імпорти
from typing import (						# 🧰 Типізації для протоколів і колекцій
    TYPE_CHECKING,
    Any,
    Dict,
    Iterable,
    List,
    Optional,
    Protocol,
    Tuple,
    cast,
)

# 🧩 Внутрішні модулі проєкту
from app.infrastructure.parsers.extractors.base import (			# 🔗 Спільні утиліти для екстракторів
    Selectors,
    _ConfigSnapshot,
    _normalize_image_url,
    _strip_query,
    logger,
    uniq_keep_order,
)

if TYPE_CHECKING:													# 🧠 Підказки лише для аналізу
    from bs4 import BeautifulSoup									# noqa: F401


# ================================
# 🧱 ДОПОМІЖНІ ТИПИ
# ================================
class _ImagesHost(Protocol):
    """
    🧱 Протокол середовища, яке використовує `ImagesMixin`.
    """

    soup: "BeautifulSoup"											# 🥣 DOM-дерево продукту

    def _main_image_from_json_ld(self) -> Optional[str]:			# 🔍 Головне зображення з JSON-LD
        ...

    def _images_from_json_ld(self) -> Iterable[str]:				# 🖼️ Усі зображення з JSON-LD
        ...


# ================================
# 🖼️ МІКСИН ЗОБРАЖЕНЬ
# ================================
class ImagesMixin:
    """
    🖼️ Надає методи для отримання головного та всіх зображень товару.
    """

    _S: Selectors													# 🧷 Набір CSS-селекторів із базового екстрактора

    # ================================
    # 🔧 ДОПОМІЖНІ НОРМАЛІЗАТОРИ
    # ================================
    def _canonicalize_shopify(self, url: str) -> str:
        """
        🔧 Прибирає Shopify-суфікси на кшталт `_200x200` зі шляху.
        """
        cleaned = re.sub(
            r"_(\d+x\d+|\d+x)(?=\.(?:jpe?g|png|webp|avif)(?:$|\?))",
            "",
            url,
            flags=re.IGNORECASE,
        )
        if cleaned != url:
            logger.debug("🧼 Shopify canonicalized: '%s' → '%s'.", url, cleaned)
        return cleaned

    def _normalize_img(self, url: str) -> str:
        """
        🧼 Повний цикл нормалізації: канонізація + обрізка query-параметрів.
        """
        normalized = _normalize_image_url(url)
        canonical = self._canonicalize_shopify(normalized)
        stripped = _strip_query(canonical)
        logger.debug("🧼 normalize_img: '%s' → '%s'.", url, stripped)
        return stripped

    # ================================
    # 🖼️ ГОЛОВНЕ ЗОБРАЖЕННЯ
    # ================================
    def extract_main_image(self) -> str:
        """
        🖼️ Повертає головне зображення (спочатку JSON-LD, далі — HTML-фолбек).
        """
        host = cast(_ImagesHost, self)									# 🧭 Надаємо доступ до soup/json-ld

        logger.debug("🖼️ Починаємо пошук головного зображення.")
        img_url = host._main_image_from_json_ld()						# 🔍 1) Пряма відповідь з JSON-LD
        if img_url:
            logger.debug("🖼️ Головне зображення з JSON-LD: %s", img_url)
            return img_url												# ✅ Якщо там є URL — це найбезпечніше джерело

        for selector in self._S.MAIN_IMAGE_LIST:						# 🔎 2) Проходимо по селекторам DOM
            tag_or_none = host.soup.select_one(selector)				# 🌿 Беремо перший збіг
            if tag_or_none is None:
                continue

            if isinstance(tag_or_none, Tag) and tag_or_none.name == "meta":
                url_candidate = str(tag_or_none.get("content") or "")	# 🏷️ <meta property="og:image">, etc.
                normalized = _normalize_image_url(url_candidate)		# 🧼 Підчищаємо URL
                if normalized:
                    logger.debug("🖼️ DOM meta-селектор '%s' дав головне зображення.", selector)
                    return normalized									# ✅ Знайшли канонічну картинку
                continue

            try:
                tag = cast(Tag, tag_or_none)							# 🧱 Очікуємо звичайний <img>/<picture>
                candidates = [											# 📋 Порядок пріоритетів атрибутів
                    tag.get("src"),									#   • класичний src
                    tag.get("data-src"),								#   • ліниве завантаження
                    tag.get("data-original"),							#   • custom атрибут
                    self._attr_first(token=tag.get("data-srcset")),	#   • беремо перший srcset
                ]
                raw_url = next((str(value) for value in candidates if value), "")	# 🎯 Перший ненульовий атрибут
            except Exception:
                raw_url = str(tag_or_none)								# 🛟 Якщо елемент не тег — беремо str()

            normalized = _normalize_image_url(raw_url)					# 🧼 Нормалізуємо застосовуючи глобальні правила
            if normalized:
                logger.debug("🖼️ DOM селектор '%s' дав головне зображення.", selector)
                return normalized										# ✅ Зупиняємося на першій валідній картинці

        logger.info("🖼️ Головне зображення не знайдено.")
        return ""

    # ================================
    # 🖼️ УСІ ЗОБРАЖЕННЯ
    # ================================
    def extract_all_images(
        self,
        *,
        limit: Optional[int] = None,
        filter_small_images: bool = True,
    ) -> List[str]:
        """
        🖼️ Повертає список усіх зображень, зберігаючи порядок і застосовуючи фільтри.

        Args:
            limit (int | None): Максимальна кількість результатів; None — без обмеження.
            filter_small_images (bool): Чи відсіювати «малі» картинки за розміром.

        Returns:
            List[str]: Нормалізовані URL зображень.
        """
        filters = _ConfigSnapshot.img_filters()							# ⚙️ Зчитуємо налаштування з конфігурації/ENV
        bad_tokens: Tuple[str, ...] = tuple(filters.get("bad_tokens", ()))		# 🛑 Ключові слова, які виключають URL
        allowed_ext: Tuple[str, ...] = tuple(							# 🔚 Дозволені розширення файлів
            filters.get("allowed_ext", (".jpg", ".jpeg", ".png", ".webp", ".avif"))
        )
        min_side = int(filters.get("min_side_px", 0) or 0)				# 📏 Мінімальна сторона превʼю
        logger.debug(
            "🖼️ extract_all_images(limit=%s, filter_small=%s, min_side=%s).",
            limit,
            filter_small_images,
            min_side,
        )

        def _looks_like_product_img(url: str) -> bool:
            if not url:
                return False
            lower = url.lower()
            if not lower.endswith(allowed_ext):
                return False
            size_chart_tokens = (
                "sizechart",
                "size_chart",
                "size-chart",
                "size chart",
                "women-size-chart",
                "mens-size-chart",
            )
            if any(token in lower for token in size_chart_tokens):
                return True											# 📏 Size-chart whitelist
            return not any(token in lower for token in bad_tokens)		# 🚫 Відсіюємо favicon/sprite та інший шум

        def _probably_too_small(url: str) -> bool:
            lower = url.lower()
            match = re.search(											# 🔎 Shopify-суфікси "_400x400"
                r"_(\d+)(?:x(\d+))?(?=\.(?:jpe?g|png|webp|avif)(?:$|\?))",
                lower,
            )
            if match:
                width = int(match.group(1))
                height = int(match.group(2)) if match.group(2) else width
                return min(width, height) < min_side					# 📉 Замалі розміри

            match_width = re.search(r"/(?:w(?:idth)?[_-]?)(\d{1,4})/", lower)	# 🔎 Маркери /w400/ у URL
            if match_width:
                side = int(match_width.group(1))
                return side < min_side									# 📉 Замала ширина
            return False

        host = cast(_ImagesHost, self)									# 🧭 Дає доступ до soup/json-ld

        images: List[str] = []											# 📦 Накопичуємо всі URL
        images.extend(host._images_from_json_ld())						# 1️⃣ Спершу беремо JSON-LD (зазвичай найповніший список)
        logger.debug("🖼️ JSON-LD повернув %d зображень.", len(images))

        for selector in self._S.ALL_IMAGES_LIST:						# 2️⃣ Далі прочісуємо DOM селектор за селектором
            for element in host.soup.select(selector):					# 🔁 Беремо кожен збіг
                try:
                    tag = cast(Tag, element)							# 🧱 Очікуємо <img>/<source>
                    candidates = [										# 📋 Пріоритети джерел URL
                        tag.get("src"),
                        tag.get("data-src"),
                        tag.get("data-original"),
                        self._attr_first(token=tag.get("srcset")),
                        self._attr_first(token=tag.get("data-srcset")),
                    ]
                    raw_url = next((str(value) for value in candidates if value), "")	# 🎯 Перший ненульовий кандидат
                except Exception:
                    raw_url = str(element)								# 🛟 Якщо елемент не тег — використовуємо str()

                normalized = self._normalize_img(raw_url or "")			# 🧼 Канонізуємо та обрізаємо query
                if normalized:
                    images.append(normalized)							# ➕ Додаємо у загальний список

        deduplicated = list(uniq_keep_order(images))					# ♻️ Прибираємо дублікати, зберігаючи порядок
        logger.info(
            "📷 Raw image candidates | total=%d | samples=%s",
            len(deduplicated),
            deduplicated[:10],
        )
        if filter_small_images:
            filtered = [url for url in deduplicated if _looks_like_product_img(url)]	# ✅ Лишаємо лише валідні URL
            filtered = [url for url in filtered if not _probably_too_small(url)]	# 📏 І прибираємо дрібні превʼю
        else:
            filtered = [url for url in deduplicated if _looks_like_product_img(url) or True]	# 🔁 Мінімальний фільтр по токенах

        if isinstance(limit, int) and limit > 0:
            filtered = filtered[:limit]									# ✂️ За потреби обрізаємо список до ліміту

        logger.info(
            "📷 Filtered product images | total=%d | samples=%s",
            len(filtered),
            filtered[:10],
        )
        return filtered													# 📦 Повертаємо чистий список URL

    # ================================
    # 🧰 ДОПОМІЖНІ МЕТОДИ
    # ================================
    @staticmethod
    def _attr_first(*, token: Any) -> Optional[str]:
        """
        🧰 Повертає перший рядок із атрибута (якщо він список/кортеж) або None.
        """
        if token is None:
            return None
        if isinstance(token, str):
            return token.split(" ")[0] if token else None				# 🔗 Беремо перше значення зі srcset
        if isinstance(token, (list, tuple)):
            for value in token:
                if value:
                    return str(value).split(" ")[0]
        return None
