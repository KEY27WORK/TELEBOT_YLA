#!/bin/bash

# Путь к твоей AI-Agent виртуалке
AI_AGENT_PATH="$HOME/ai-agent"

# Путь к твоему проекту
PROJECT_PATH="$HOME/TELEBOTYLAUKRAINE"

# Переходим в проект
cd "$PROJECT_PATH" || { echo "❌ Проект не найден!"; exit 1; }

# Активируем AI Agent виртуалку
source "$AI_AGENT_PATH/bin/activate"

# Запускаем Open Interpreter строго внутри проекта
interpreter
