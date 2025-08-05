# 🔤 app/infrastructure/image_generation/font_service.py
"""
🔤 font_service.py — сервіс для пошуку та завантаження шрифтів.
"""
import os
import logging
from typing import List, Optional
from PIL import Image, ImageFont, ImageDraw
from app.config.config_service import ConfigService
from app.shared.utils.logger import LOG_NAME

logger = logging.getLogger(LOG_NAME)

class FontService:
    def __init__(self, config_service: ConfigService):
        self.bold_font_paths: List[str] = config_service.get("image_generation.font_paths.bold", [])
        self.mono_font_paths: List[str] = config_service.get("image_generation.font_paths.mono", [])

        self._dummy_draw = ImageDraw.Draw(Image.new("RGB", (1, 1)))

    def get_font(self, font_type: str, size: int) -> ImageFont.FreeTypeFont:
        """ Отримує шрифт заданого типу та розміру. """
        paths = self.bold_font_paths if font_type == "bold" else self.mono_font_paths
        
        for font_path in paths:
            if os.path.exists(font_path):
                try:
                    return ImageFont.truetype(font_path, size)
                except IOError:
                    continue
        
        logger.warning(f"⚠️ Шрифт типу '{font_type}' не знайдено, використовується стандартний.")
        return ImageFont.load_default()
    
    def get_text_width(self, text: str, font: ImageFont.FreeTypeFont) -> int:
        """📏 Повертає ширину тексту в пікселях."""
        return int(self._dummy_draw.textlength(str(text), font=font))