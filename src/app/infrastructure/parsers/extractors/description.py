# 📜 src/app/infrastructure/parsers/extractors/description.py
"""
📜 DescriptionMixin — модуль для побудови текстового опису товару.

🔹 Підтримує дві стратегії (legacy v1 та модульну v2) з конфігурацією через ConfigService.
🔹 Витягує опис із JSON-LD, контейнерів HTML та детальних секцій, зберігаючи списки.
🔹 Підтримує постобробку: markdown, очищення DOM, злиття секцій, обмеження довжини.
"""

from __future__ import annotations

# 🌐 Зовнішні бібліотеки
from bs4.element import NavigableString, PageElement, Tag				# 🧱 Ноди BeautifulSoup

# 🔠 Системні імпорти
import re																# 🧪 Патерни для нормалізації тексту
from dataclasses import dataclass										# 🧾 Налаштування генератора
from typing import (													# 🧰 Типізація й протоколи
    TYPE_CHECKING,
    Dict,
    Iterable,
    List,
    Optional,
    Protocol,
    Sequence,
    Tuple,
    Union,
    cast,
)

# 🧩 Внутрішні модулі проєкту
from app.infrastructure.parsers.extractors.base import (				# 🔗 Спільні утиліти
    Selectors,
    _clean_text_nodes,
    _norm_ws,
    _normalize_description_labels,
    logger,
)

if TYPE_CHECKING:														# 🧠 Типи лише для статичного аналізу
    from bs4 import BeautifulSoup										# noqa: F401


# ================================
# 🧱 ДОПОМІЖНІ СТРУКТУРИ
# ================================
class _DescriptionHost(Protocol):
    """
    🧱 Протокол залежностей, які надає кінцевий екстрактор.
    """

    soup: "BeautifulSoup"												# 🥣 Відпарсений HTML

    def _description_from_json_ld(self) -> Optional[str]:				# 🔍 Опис із JSON-LD
        ...

    def extract_detailed_sections(self, preserve_lists: bool = False) -> Dict[str, str]:	# 🧾 Детальні секції
        ...


@dataclass(frozen=True)
class _DescOptions:
    """
    ⚙️ Параметри рендеру опису.
    """

    as_markdown: bool = True
    preserve_lists: bool = True
    drop_tables: bool = True
    collapse_newlines: bool = True
    max_len: int = 0
    strip_images: bool = True
    strip_links: bool = False
    allowed_inline: Tuple[str, ...] = ("strong", "em", "b", "i")


# ================================
# 🧭 ОСНОВНИЙ МІКСИН
# ================================
class DescriptionMixin:
    """
    🧭 Надає методи для побудови опису (legacy v1 та модульну v2).
    """

    _S: Selectors														# 🧷 Набір селекторів із базового модуля
    _KEY_MAP: Dict[str, str]											# 🗺️ Відповідність ключів секцій
    soup: "BeautifulSoup"												# 🥣 Суп, який постачає кінцева імплементація

    # ================================
    # 🚪 ПУБЛІЧНИЙ ІНТЕРФЕЙС
    # ================================
    def extract_description(self) -> str:
        """
        🚪 Обирає стратегію та повертає нормалізований опис товару.

        Returns:
            str: Результуючий опис.
        """
        from app.config.config_service import ConfigService

        cfg = ConfigService()											# ⚙️ Доступ до конфігурації

        enabled = bool(cfg.get("flags.extractors.description.enabled", False, cast=bool))	# 🔘 Чи ввімкнута нова стратегія
        strategy_raw = cfg.get("flags.extractors.description.strategy", "v1", cast=str) or "v1"
        strategy = strategy_raw.lower()									# 🧭 Назва стратегії
        rollout = int(cfg.get("flags.extractors.description.rollout_percent", 0, cast=int) or 0)	# 📊 Відсоток rollout

        use_v2 = False													# 🔁 Прапор використання v2
        if enabled:
            if strategy == "v2":
                use_v2 = True											# ✅ Примусовий перехід на v2
            elif 0 < rollout < 100:
                import random											# 🎲 Випадковий rollout

                use_v2 = random.randrange(100) < rollout				# 🎯 Порівнюємо з порогом

        logger.debug(
            "🧭 Опис: обрана стратегія=%s enabled=%s strategy_cfg=%s rollout=%s",
            "v2" if use_v2 else "v1",
            enabled,
            strategy,
            rollout,
        )
        return self._extract_description_v2() if use_v2 else self._extract_description_v1()

    # ================================
    # 🪵 LEGACY V1
    # ================================
    def _extract_description_v1(self) -> str:
        """
        🪵 Історична стратегія вивантаження опису (JSON-LD → meta → секції).

        Returns:
            str: Текст опису або порожній рядок.
        """
        host = cast(_DescriptionHost, self)								# 🧭 Забезпечуємо доступ до залежностей
        desc = host._description_from_json_ld()							# 🔍 Перевіряємо JSON-LD
        if desc:
            logger.debug("🧭 v1: використано джерело json_ld")
            return _norm_ws(desc)										# 🧼 Нормалізуємо пробіли

        meta = host.soup.select_one('meta[name="description"]')			# 🔍 Пробуємо meta description
        if isinstance(meta, Tag) and meta.has_attr("content"):
            text = _norm_ws(str(meta.get("content") or ""))				# 🧼 Бережно очищуємо
            if text:
                logger.debug("🧭 v1: використано meta[name=description]")
                return text

        sections = host.extract_detailed_sections()						# 🧾 Падаємо у секції
        desc_keys = {
            value for key, value in self._KEY_MAP.items()
            if key in {"DESCRIPTION", "DESIGN"} and isinstance(value, str)
        }																# 🗝️ Основні ключі
        fallback_probe = ("ОПИС", "DESCRIPTION", "DESIGN")				# 🛟 Фолбек
        for candidate in list(desc_keys) + list(fallback_probe):
            if candidate and sections.get(candidate):
                logger.debug("🧭 v1: використано секцію key=%s", candidate)
                return sections[candidate]

        logger.debug("🧭 v1: опис не знайдено")
        return ""

    # ================================
    # 🧩 НОВА СТРАТЕГІЯ V2
    # ================================
    def _extract_description_v2(self) -> str:
        """
        🧩 Модульна стратегія (JSON-LD → контейнер → секції).

        Returns:
            str: Готовий опис.
        """
        from app.config.config_service import ConfigService

        cfg = ConfigService()											# ⚙️ Конфігурація

        def _cfg_bool(path: str, default: bool) -> bool:
            raw_value = cfg.get(path, default, cast=bool)
            return default if raw_value is None else bool(raw_value)	# 🔘 Гарантуємо bool

        allowed_inline_raw = cfg.get(
            "parser.description.allowed_inline_tags",
            ["strong", "em", "b", "i"],
            cast=list,
        )
        allowed_inline_tuple = tuple(allowed_inline_raw or ["strong", "em", "b", "i"])	# 🔡 Список інлайнів

        opts = _DescOptions(
            as_markdown=_cfg_bool("parser.description.as_markdown", True),
            preserve_lists=_cfg_bool("parser.description.preserve_lists", True),
            drop_tables=_cfg_bool("parser.description.drop_tables", True),
            collapse_newlines=_cfg_bool("parser.description.collapse_newlines", True),
            max_len=max(0, int(cfg.get("parser.description.max_len", 0, cast=int) or 0)),
            strip_images=_cfg_bool("parser.description.strip_images", True),
            strip_links=_cfg_bool("parser.description.strip_links", False),
            allowed_inline=allowed_inline_tuple,
        )
        logger.debug(
            "🧩 v2: налаштовано опції опису: markdown=%s preserve_lists=%s drop_tables=%s max_len=%s",
            opts.as_markdown,
            opts.preserve_lists,
            opts.drop_tables,
            opts.max_len,
        )

        host = cast(_DescriptionHost, self)								# 🧭 Забезпечуємо залежності
        desc = host._description_from_json_ld()							# 🔍 1) JSON-LD
        if desc:
            text = _norm_ws(desc)
            if text and len(text) >= 40:
                logger.debug("🧭 v2: використано json_ld len=%d", len(text))
                return self._postprocess(text, opts)

        container = self._find_description_container()					# 🧍 2) Контейнер за селекторами
        if container:
            cleaned = self._sanitize_container(container, opts)			# 🧼 Очищаємо DOM
            rendered = self._render_description(cleaned, opts)			# 📝 Рендерим у markdown/текст
            if rendered and len(rendered) >= 40:
                logger.debug("🧭 v2: використано контейнер len=%d", len(rendered))
                return self._postprocess(rendered, opts)

        sections_md = self._sections_as_markdown(opts)					# 🧾 3) Збираємо секції у markdown
        if sections_md:
            logger.debug("🧭 v2: використано секції merged_len=%d", len(sections_md))
            return self._postprocess(sections_md, opts)

        logger.debug("🧭 v2: опис не знайдено")
        return ""

    # ================================
    # 🧑‍🔧 ПАЙПЛАЙН ОБРОБКИ DOM
    # ================================
    def _find_description_container(self) -> Optional[Tag]:
        """
        🔍 Повертає перший контейнер опису за списком селекторів.
        """
        host = cast(_DescriptionHost, self)								# 🧭 Забезпечуємо доступ до soup
        for selector in self._S.DESCRIPTION_CONTAINER_LIST:
            element = host.soup.select_one(selector)
            if isinstance(element, Tag):
                logger.debug("🧭 Контейнер опису знайдено селектором %s", selector)
                return element											# ✅ Знайшли відповідний контейнер
        logger.info("ℹ️ Контейнер опису не знайдено жодним селектором.")
        return None

    def _sanitize_container(self, root: Tag, opts: _DescOptions) -> Tag:
        """
        🧼 Очищує DOM від службових елементів, зберігаючи корисний контент.

        Args:
            root (Tag): Контейнер з описом.
            opts (_DescOptions): Налаштування обробки.

        Returns:
            Tag: Очищений DOM.
        """
        removed_service_nodes = 0										# 🧮 Лічильник службових тегів
        for bad in root.select("script, style, noscript, svg, iframe, form"):
            if isinstance(bad, Tag):
                bad.decompose()											# 🧹 Видаляємо службові теги
                removed_service_nodes += 1
        if removed_service_nodes:
            logger.debug("🧹 Видалено службові теги: %d", removed_service_nodes)

        if opts.strip_images:
            removed_images = 0											# 🖼️ Лічильник зображень
            for img in root.select("img, picture, source"):
                if isinstance(img, Tag):
                    img.decompose()										# 🖼️ Прибираємо зображення
                    removed_images += 1
            if removed_images:
                logger.debug("🖼️ Вирізано зображень: %d", removed_images)

        if opts.drop_tables:
            removed_tables = 0											# 📊 Кількість видалених таблиць
            for table in root.select("table"):
                if isinstance(table, Tag):
                    table.decompose()									# 📊 Вирізаємо таблиці
                    removed_tables += 1
            if removed_tables:
                logger.debug("📊 Видалено таблиць: %d", removed_tables)
        else:
            converted_tables = 0										# 🔁 Таблиці перетворені в текст
            for table in root.select("table"):
                if not isinstance(table, Tag):
                    continue
                rows: List[str] = []
                for tr in table.select("tr"):
                    if not isinstance(tr, Tag):
                        continue
                    cells = [
                        cell.get_text(" ", strip=True)
                        for cell in tr.select("th, td")
                        if isinstance(cell, Tag)
                    ]
                    row = " | ".join([cell for cell in cells if cell])
                    if row:
                        rows.append(row)
                replacement = cast(Tag, self.soup.new_tag("p"))				# ✏️ Замінюємо таблицю на <p>
                replacement.string = " / ".join(rows)
                table.replace_with(replacement)
                converted_tables += 1
            if converted_tables:
                logger.debug("📝 Перетворено таблиць на параграфи: %d", converted_tables)

        stripped_links = 0												# 🔗 Лічильник очищених посилань
        sanitized_links = 0											# 🔐 Лічильник очищених атрибутів
        for anchor in root.select("a"):
            if not isinstance(anchor, Tag):
                continue
            if opts.strip_links:
                text = anchor.get_text(" ", strip=True)
                anchor.replace_with(self.soup.new_string(text))			# 🔁 Замінюємо на текстовий вузол
                stripped_links += 1
            else:
                anchor.attrs = {}										# 🔐 Прибираємо атрибути, але зберігаємо тег
                sanitized_links += 1
        if stripped_links or sanitized_links:
            logger.debug(
                "🔗 Оброблено посилань: stripped=%d sanitized=%d",
                stripped_links,
                sanitized_links,
            )

        trash_tokens = ("icon", "badge", "label", "share", "social", "breadcrumbs")
        removed_trash_blocks = 0										# 🗑️ Кількість декоративних блоків
        for candidate in list(root.find_all(True)):
            if not isinstance(candidate, Tag):
                continue
            cls = " ".join(candidate.get("class") or []).lower()
            identifier = str(candidate.get("id") or "").lower()
            if any(token in cls or token in identifier for token in trash_tokens) and candidate is not root:
                candidate.decompose()									# 🗑️ Прибираємо декоративні блоки
                removed_trash_blocks += 1
        if removed_trash_blocks:
            logger.debug("🗑️ Видалено декоративних блоків: %d", removed_trash_blocks)

        trimmed_breaks = 0												# ↩️ Скільки розривів прибрано
        for br in root.select("br"):
            if not isinstance(br, Tag):
                continue
            if not br.next_sibling or str(br.next_sibling).strip() == "":
                sibling = br.next_sibling								# 🔁 Залишаємо один перенос
                while isinstance(sibling, Tag) and sibling.name == "br":
                    next_sibling = sibling.next_sibling
                    sibling.decompose()
                    sibling = next_sibling
                    trimmed_breaks += 1
        if trimmed_breaks:
            logger.debug("↩️ Схлопнуто порожніх переносів: %d", trimmed_breaks)

        removed_empty_nodes = 0										# 🧼 Порожні елементи
        for element in list(root.find_all(True)):
            if not isinstance(element, Tag) or element is root:
                continue
            text = element.get_text(" ", strip=True)
            if not text and element.name not in {"ul", "ol", "li", "p", "h2", "h3", "h4"}:
                element.decompose()										# ❌ Видаляємо порожні блоки
                removed_empty_nodes += 1
        if removed_empty_nodes:
            logger.debug("🧼 Видалено порожніх елементів: %d", removed_empty_nodes)

        return root

    def _render_description(self, root: Tag, opts: _DescOptions) -> str:
        """
        🖨️ Перетворює очищений DOM на markdown або плоский текст.

        Args:
            root (Tag): Відчищений контейнер.
            opts (_DescOptions): Налаштування рендеру.

        Returns:
            str: Готовий текст опису.
        """
        logger.debug(
            "🖨️ Рендер опису: markdown=%s preserve_lists=%s allowed_inline=%s",
            opts.as_markdown,
            opts.preserve_lists,
            ", ".join(opts.allowed_inline),
        )
        blocks: List[str] = []											# 📦 Буфер для шматків опису

        def _render_inline(tag: Tag) -> str:
            text = tag.get_text(" ", strip=True)						# ✏️ Витягуємо текст із тега
            if tag.name in {"strong", "b"}:
                return f"**{text}**" if text else ""					# ✨ Жирний markdown
            if tag.name in {"em", "i"}:
                return f"*{text}*" if text else ""						# ✨ Курсив
            return text												# 🔁 Інші теги повертаємо як plain

        def _render_list(list_tag: Tag, ordered: bool) -> List[str]:
            rendered: List[str] = []									# 📜 Пункти результату
            index = 1													# 🔢 Поточний номер для ordered списку
            for li in list_tag.find_all("li", recursive=False):		# 🔁 Лише верхній рівень
                if not isinstance(li, Tag):
                    continue
                text = _norm_ws(li.get_text(" ", strip=True))			# 🧼 Прибираємо зайві пробіли
                if not text:
                    continue
                bullet = f"{index}." if ordered else "-"				# 🧷 Формуємо маркер
                rendered.append(f"{bullet} {text}")					# ➕ Додаємо рядок
                index += 1												# ➡️ Наступний пункт
            return rendered

        for node in root.children:										# 🔁 Ітеруємо усі дочірні вузли контейнера
            if isinstance(node, NavigableString):
                text = _norm_ws(str(node))								# 🧼 Нормалізуємо текст
                if text:
                    blocks.append(text)								# ➕ Зберігаємо як абзац
                continue
            if not isinstance(node, Tag):
                continue

            name = node.name.lower()									# 🏷️ Робимо регістр однорідним

            if name in {"h2", "h3", "h4"}:
                text = _norm_ws(node.get_text(" ", strip=True))		# 🧼 Текст заголовка
                if not text:
                    continue
                if opts.as_markdown:
                    prefix = "###" if name == "h3" else "##"			# 🧱 Підбираємо рівень markdown
                    blocks.append(f"{prefix} {text}")					# 📌 Додаємо рядок
                else:
                    blocks.append(text)								# 🧾 Plain-текст
                continue

            if name == "p":
                text_parts: List[str] = []								# 📦 Частини параграфа
                for child in node.children:							# 🔁 Проходимо усі дочірні вузли <p>
                    if isinstance(child, NavigableString):
                        normalized = _norm_ws(str(child))				# 🧼 Підчищаємо текст
                        if normalized:
                            text_parts.append(normalized)
                    elif isinstance(child, Tag):
                        if child.name in opts.allowed_inline:
                            rendered = _render_inline(child)			# ✨ Допускаємо інлайн форматування
                        else:
                            rendered = _norm_ws(child.get_text(" ", strip=True))	# 📄 Інакше беремо чистий текст
                        if rendered:
                            text_parts.append(rendered)
                paragraph = _norm_ws(" ".join(text_parts))				# 🧵 Склеюємо частини
                if paragraph:
                    blocks.append(paragraph)							# ➕ Додаємо абзац
                continue

            if name in {"ul", "ol"} and opts.preserve_lists:
                rendered_list = _render_list(node, ordered=(name == "ol"))
                if rendered_list:
                    blocks.extend(rendered_list)						# 📜 Розгортаємо кожен пункт списку
                continue

            fallback_text = _norm_ws(node.get_text(" ", strip=True))	# 🛟 Резервний текст для інших тегів
            if fallback_text:
                blocks.append(fallback_text)							# ➕ Щоб не втратити контент

        text = "\n".join(blocks)										# 🧵 Склеюємо всі блоки
        text = re.sub(r"[ \t]+\n", "\n", text)							# 🧼 Прибираємо хвости пробілів
        text = re.sub(r"\n{3,}", "\n\n", text).strip()					# 🧼 Схлопуємо порожні абзаци
        logger.debug("🖨️ Рендер завершено: blocks=%d len=%d", len(blocks), len(text))
        return text

    def _postprocess(self, text: str, opts: _DescOptions) -> str:
        """
        🧹 Фінальні перетворення тексту: схлопування переносів та обмеження довжини.
        """
        result = text
        if opts.collapse_newlines:
            result = re.sub(r"\n{3,}", "\n\n", result)
            result = re.sub(r"[ \t]+\n", "\n", result)
            result = result.strip()
            logger.debug("🧹 Постобробка: схлопнули переноси, довжина=%d", len(result))
        if opts.max_len > 0 and len(result) > opts.max_len:
            result = result[: opts.max_len].rstrip() + "…"				# ✂️ Додаємо еліпс
            logger.debug("✂️ Обрізано опис до %d символів", opts.max_len)
        return result

    # ================================
    # 🧾 ПРАЦЯ З ДЕТАЛІЗОВАНИМИ СЕКЦІЯМИ
    # ================================
    def _sections_as_markdown(self, opts: _DescOptions) -> str:
        """
        🧾 Перетворює детальні секції у markdown/плоский текст.
        """
        host = cast(_DescriptionHost, self)
        sections = host.extract_detailed_sections(preserve_lists=True)
        if not sections:
            logger.debug("🧾 Секції відсутні — нема що рендерити у markdown.")
            return ""

        priority: List[str] = []
        priority.extend(
            value
            for key, value in self._KEY_MAP.items()
            if key in {"DESCRIPTION", "DESIGN"} and isinstance(value, str)
        )
        priority.extend(
            value
            for key, value in self._KEY_MAP.items()
            if key in {"DETAILS", "FEATURES"} and isinstance(value, str)
        )
        priority.extend(["Description", "Design", "Details", "Features"])

        picked: List[Tuple[str, str]] = []
        seen_values: set[str] = set()
        for key in priority:
            section_value = sections.get(key)
            if not section_value or section_value in seen_values:
                continue
            seen_values.add(section_value)
            picked.append((key, section_value))

        if not picked:
            picked = list(sections.items())
        logger.debug("🧾 Обрано секцій для злиття: total=%d picked=%d", len(sections), len(picked))

        parts: List[str] = []
        for title, body in picked:
            if opts.as_markdown:
                parts.append(f"**{title}**")
                parts.append(body)
            else:
                parts.append(f"{title}: {body}")

        merged = "\n\n".join(part for part in parts if part)
        logger.debug("🧾 Секції зведено у markdown, довжина=%d", len(merged))
        return self._postprocess(merged, opts)

    def extract_detailed_sections(self, preserve_lists: bool = False) -> Dict[str, str]:
        """
        🧾 Витягує секції з заголовками (`<p><strong>`, `<h2>` тощо) у словник.

        Args:
            preserve_lists (bool): Чи зберігати марковані списки у markdown.

        Returns:
            Dict[str, str]: Ключ → текст секції.
        """
        logger.debug("🧾 Витяг секцій: preserve_lists=%s", preserve_lists)
        sections: Dict[str, str] = {}
        container = self._find_description_container()
        if not container:
            logger.debug("🧾 Витяг секцій: контейнер не знайдено.")
            return sections

        key_map = self._KEY_MAP

        def _collect_until_next_strong(
            paragraph: Tag,
            strong_tag: Tag,
        ) -> List[Union[str, NavigableString, Tag, PageElement]]:
            parts: List[Union[str, NavigableString, Tag, PageElement]] = []

            for sibling in strong_tag.next_siblings:
                parts.append(cast(Union[str, NavigableString, Tag, PageElement], sibling))

            next_sibling = paragraph.next_sibling
            while next_sibling is not None:
                if isinstance(next_sibling, Tag) and next_sibling.name == "p" and next_sibling.find("strong"):
                    break
                parts.append(cast(Union[str, NavigableString, Tag, PageElement], next_sibling))
                next_sibling = next_sibling.next_sibling
            return parts

        for paragraph in container.find_all("p"):
            if not isinstance(paragraph, Tag):
                continue
            strong = paragraph.find("strong")
            if not isinstance(strong, Tag):
                continue
            key_raw = _norm_ws(str(strong.get_text(" ", strip=True)).replace(":", ""))
            if not key_raw:
                continue
            mapped_key = key_map.get(key_raw.upper())
            if not mapped_key:
                continue

            parts = _collect_until_next_strong(paragraph, strong)
            value = self._render_section_value(parts, preserve_lists)
            if value:
                sections[mapped_key] = value
                logger.debug("🧾 Секція %s зібрана з <p><strong>.", mapped_key)

        if not sections:
            for heading in container.select("h2, h3, h4, strong"):
                if not isinstance(heading, Tag):
                    continue
                key_candidate = _norm_ws(heading.get_text(" ", strip=True).replace(":", ""))
                mapped_key = key_map.get(key_candidate.upper())
                if not mapped_key:
                    continue

                parts: List[Union[str, NavigableString, Tag, PageElement]] = []
                node = heading.next_sibling
                while node is not None:
                    if isinstance(node, Tag) and node.name in {"h2", "h3", "h4", "strong"}:
                        break
                    parts.append(cast(Union[str, NavigableString, Tag, PageElement], node))
                    node = node.next_sibling
                value = self._render_section_value(parts, preserve_lists)
                if value:
                    sections[mapped_key] = value
                    logger.debug("🧾 Секція %s зібрана з заголовка.", mapped_key)

        if not sections:
            raw_description = cast(_DescriptionHost, self)._description_from_json_ld() or ""
            if not raw_description:
                meta_tag = cast(_DescriptionHost, self).soup.select_one('meta[name="description"]')
                if isinstance(meta_tag, Tag) and meta_tag.has_attr("content"):
                    raw_description = str(meta_tag.get("content") or "")

            if raw_description:
                labels = ["MATERIAL:", "FABRIC WEIGHT:", "FIT:", "DESCRIPTION:", "MODEL:"]
                parsed_sections = _split_description_sections(raw_description, labels)
                for label_key, content in parsed_sections.items():
                    mapped_key = key_map.get(label_key.upper())
                    if mapped_key and content and mapped_key not in sections:
                        sections[mapped_key] = content
                        logger.debug("🧾 Секція %s зібрана з raw description.", mapped_key)

        logger.debug("🧾 Витяг секцій завершено: %d елемент(ів)", len(sections))
        return sections

    def _render_section_value(
        self,
        nodes: Iterable[Union[str, NavigableString, Tag, PageElement]],
        preserve_lists: bool,
    ) -> str:
        """
        🧾 Рендерить значення секції з урахуванням списків (markdown).
        """
        logger.debug("🧾 Рендер секції: preserve_lists=%s", preserve_lists)
        if preserve_lists:
            buffer: List[str] = []
            for node in nodes:
                if isinstance(node, NavigableString):
                    text = _norm_ws(str(node))
                    if text:
                        buffer.append(text)
                    continue
                if isinstance(node, Tag):
                    if node.name in {"ul", "ol"}:
                        ordered = node.name == "ol"
                        index = 1
                        for li in node.find_all("li", recursive=False):
                            if not isinstance(li, Tag):
                                continue
                            text = _norm_ws(li.get_text(" ", strip=True))
                            if not text:
                                continue
                            bullet = f"{index}." if ordered else "-"
                            buffer.append(f"{bullet} {text}")
                            index += 1
                        continue
                    if node.name == "p":
                        text = _norm_ws(node.get_text(" ", strip=True))
                        if text:
                            buffer.append(text)
                        continue
                    fallback_text = _norm_ws(node.get_text(" ", strip=True))
                    if fallback_text:
                        buffer.append(fallback_text)
            rendered = "\n".join(entry for entry in buffer if entry)
            rendered = re.sub(r"\n{3,}", "\n\n", rendered).strip()
            logger.debug("🧾 Рендер секції (markdown) довжина=%d", len(rendered))
            return rendered

        fallback = _clean_text_nodes(nodes)
        logger.debug("🧾 Рендер секції (plain) довжина=%d", len(fallback))
        return fallback


def _split_description_sections(raw_description: str, labels: Sequence[str]) -> Dict[str, str]:
    """
    🪡 Розбиває сирий опис на секції за списком лейблів.

    Args:
        raw_description: Повний текстопис із JSON-LD/meta.
        labels: Перелік міток з двокрапкою, за якими шукаємо секції.

    Returns:
        Dict[str, str]: Мапа {label_without_colon: content}.
    """
    normalized = _normalize_description_labels(_norm_ws(raw_description))
    if not normalized:
        return {}

    label_pattern = "|".join(re.escape(label) for label in labels)
    matcher = re.compile(f"({label_pattern})", re.IGNORECASE)
    sections: Dict[str, str] = {}
    last_label: Optional[str] = None
    last_end = 0
    label_lookup = {label.upper().rstrip(":"): label.rstrip(":") for label in labels}

    for match in matcher.finditer(normalized):
        if last_label:
            sections[last_label] = normalized[last_end : match.start()].strip()
        token = match.group(0).strip()
        label_key = token.upper().rstrip(":")
        last_label = label_lookup.get(label_key, label_key)
        last_end = match.end()

    if last_label:
        sections[last_label] = normalized[last_end:].strip()

    return {key: value for key, value in sections.items() if value}
