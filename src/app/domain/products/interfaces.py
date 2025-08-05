# app/domain/products/interfaces.py
"""
🧩 Интерфейсы для получения данных о продуктах.
"""
from abc import ABC, abstractmethod
from typing import List, Optional
from .entities import ProductInfo

# ================================
# 🏛️ ИНТЕРФЕЙСЫ
# ================================

class IProductDataProvider(ABC):
    """Контракт для любого источника данных о товаре."""
    @abstractmethod
    async def get_product_info(self) -> ProductInfo:
        """Получает информацию о конкретном товаре."""
        pass

class ICollectionDataProvider(ABC):
    """Контракт для любого источника данных о коллекции."""
    @abstractmethod
    async def get_product_links(self) -> List[str]:
        """Получает список ссылок на товары в коллекции."""
        pass

class IProductSearchProvider(ABC):
    """Контракт для сервиса, который ищет товар по текстовому запросу."""
    @abstractmethod
    async def resolve(self, query: str) -> Optional[str]:
        """Ищет товар и возвращает URL или None."""
        pass