# Референсы B4 · Объяснимый приоритет

> **Референсы фиксированы.** Агент пишет код в стиле и структуре этих файлов и не предлагает свою архитектуру, другие библиотеки, другую раскладку файлов. Расхождение референса с контрактом — контракт главнее; напиши об этом в отчёте. Папку `docs/references/` менять нельзя.

## Какие образцы применять
- `docs/references/_patterns/backend_block/`

## Что зафиксировано контрактом (не обсуждается)
Порт блока (сигнатуры — из контракта, реализация — по образцу):
```python
# backend/app/blocks/priority/__init__.py
def score(cluster: Cluster, reports: list[Report], history: list[Report], ctx: Context,
          weights: dict[str, float] | None = None) -> Priority: ...

# backend/app/blocks/priority/factors/<code>.py — по одному файлу на фактор:
def evaluate(cluster, reports, history, ctx) -> tuple[float | None, list[str]]: ...   # (score 0..1 | None, evidence)
```
| Код | Фактор | Вес | Как считать |
|---|---|---|---|
| `HZ` | Опасность | 0.25 | база по категории (manhole 0.9, tree 0.7, water_leak 0.6, pothole 0.5, streetlight 0.4, traffic_sign 0.5, garbage 0.2, public_space 0.1) + 0.2 за `extracted.injured` или слова-сигналы; максимум 1 |
| `DM` | Спрос | 0.15 | `min(1, (кол-во обращений + сумма confirmations) / 10)` |
| `AG` | Возраст | 0.15 | `min(1, дней с first_reported_at / 14)` |
| `SP` | Соц. объекты | 0.15 | school/kindergarten/hospital ≤ 150 м → 1.0; ≤ 300 м → 0.5; иначе 0. Нет инфраструктуры в ctx → `None` |
| `RC` | Повтор | 0.10 | в `history` есть решённое обращение той же категории ≤ 60 м за 12 мес → 1.0, иначе 0. Пустая history → `None` |
| `EX` | Мероприятие | 0.10 | **дополнительный блок X1.** В ядре всегда `None` (`ctx.events` пуст) → вес перераспределяется перенормировкой. Формула — в контракте X1 |
| `WX` | Погода | 0.05 | tree при ветре ≥ 15 м/с → 1; water_leak при t ≤ 0 → 1; иначе 0. Нет погоды → `None` |
| `VF` | Достоверность | 0.05 | доля обращений с фото или `verification.status` in (plausible, confirmed) |

`score = 100 × Σ(w·s) / Σ(w)` только по факторам, где `s is not None` (перенормировка при пропусках).
**Аварийный минимум:** если `HZ.score ≥ 0.9`, итоговый балл не ниже 80; разница добавляется отдельным фактором `code="FL"`, `label="Аварийный минимум"`, `weight=0`, `points=разница`, с `evidence`.
`points` фактора = его доля в итоговых баллах. `confidence` = доля веса факторов с данными.
`needs_review = confidence < 0.5` ИЛИ любое обращение кластера `verification.status == "suspicious"`.

Переключатель уровня: —. По умолчанию L0. Ошибка L1 → откат на L0 + запись в лог.

## Куда смотреть в каркасе
- `backend/app/blocks/priority/**`
- `backend/tests/blocks/priority/**`

## Данные для тестов
Только `backend/app/fixtures/demo_city.json` (фронт — `frontend/src/mocks/demo_city.json`, копия). Эталон — раздел `expect`. Критерии приёмки, которые должны стать тестами:
1. Кластер `r011` (открытый люк у детсада) → `score ≥ expect.min_score_manhole` и есть фактор `FL`; кластер `r001` → `score ≥ expect.min_score_school_pothole`. Эталон на полном контексте без мероприятий: 80 (аварийный минимум; «сырой» балл ≈ 57) и ≈ 81.9.
2. Эти два кластера — первые два по баллу и на L0, и на L1.
3. Кластер `r005` получает `score ≤ expect.max_score_low_noise`.
4. Сумма `points` всех факторов = `score` ± 0.1.
5. При `ctx.weather=None` и пустой инфраструктуре балл считается, `WX` и `SP` имеют `score=None`, `confidence < 1`.
6. Кластер `r006` (suspicious) → `needs_review=True`.
7. Кластер `r001`: в `RC.evidence` упомянуто `r016`.
8. При пустом `ctx.events` фактор `EX` имеет `score=None` и серый статус «нет данных», балл не ломается.
9. У каждого фактора с `score > 0` непустой `evidence` на русском.
