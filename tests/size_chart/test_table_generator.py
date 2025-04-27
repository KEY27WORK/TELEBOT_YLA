"""
🧪 test_table_generator.py — unit-тести для генераторів таблиць розмірів

Перевіряє:
- Генерацію PNG-файлів для всіх типів таблиць
- Наявність файлу після генерації
"""

import os
import pytest
from size_chart.table_generator import (
    GeneralTableGenerator,
    UniqueTableGenerator,
    UniqueGridTableGenerator
)

# === 🔹 Тестові дані ===
sample_general_data = {
    "Title": "Загальна таблиця",
    "Розмір": ["S", "M", "L"],
    "Груди": [86, 90, 94],
    "Талія": [68, 72, 76]
}

sample_unique_data = {
    "Title": "Унікальна таблиця",
    "Розмір": ["S", "M"],
    "Талія": [64.5, 70.2],
    "Довжина": [90.3, 95.1]
}

sample_grid_data = {
    "160": {"50": "S", "60": "M"},
    "170": {"50": "M", "60": "L"},
}

# === 🔹 GeneralTableGenerator ===
@pytest.mark.asyncio
async def test_generate_general_table(tmp_path):
    output_path = tmp_path / "general.png"
    gen = GeneralTableGenerator(sample_general_data, str(output_path))
    path = await gen.generate()
    assert os.path.exists(path)

# === 🔹 UniqueTableGenerator ===
@pytest.mark.asyncio
async def test_generate_unique_table(tmp_path):
    output_path = tmp_path / "unique.png"
    gen = UniqueTableGenerator(sample_unique_data, str(output_path))
    path = await gen.generate()
    assert os.path.exists(path)

# === 🔹 UniqueGridTableGenerator ===
def test_generate_grid_table(tmp_path):
    output_path = tmp_path / "grid.png"
    gen = UniqueGridTableGenerator(sample_grid_data, str(output_path))
    path = gen.generate()
    assert os.path.exists(path)
