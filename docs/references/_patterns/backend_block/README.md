# Образец backend-блока

Раскладка (имя `example` заменяется на `name` блока из контракта):
```
backend/app/blocks/example/__init__.py   порт: только функции из контракта; выбирает l0 или l1 по settings
backend/app/blocks/example/l0.py         детерминированная реализация без сети; работает на fixture
backend/app/blocks/example/l1.py         целевая реализация; любая ошибка → откат на l0
backend/app/api/routes/example.py        роуты: только вызывают порт, роли через require_roles
backend/tests/blocks/example/test_example.py   один тест на критерий приёмки, данные — из fixture
```
Соседний блок импортируется только через порт: `from app.blocks.other import fn`. Никогда `from app.blocks.other.l1 import ...`.
