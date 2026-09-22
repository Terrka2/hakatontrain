#! /usr/bin/env bash
# Копирует общий fixture бэкенда в моки фронта. Запускать после любого изменения fixture.
set -e
cd "$(dirname "$0")/.."
cp backend/app/fixtures/demo_city.json frontend/src/mocks/demo_city.json
echo "frontend/src/mocks/demo_city.json обновлён"
