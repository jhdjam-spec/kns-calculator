"""Phase 5 — ETL для расширения БД насосов.

Назначение: превратить разрозненные источники данных
(PDF-каталоги, Excel-прайсы, веб-конфигураторы) в структурированные записи
формата `02_dataset/pumps/schema.json`.

Текущие источники (по приоритету):
  1. Ручной ввод JSON — `RawPumpRecord` через CLI
  2. PDF-каталоги через `docling` (TODO в Phase 5.1)
  3. Q-H кривые через `WebPlotDigitizer` (TODO в Phase 5.2)
  4. Wilo-Select / Grundfos PC — Playwright парсинг (TODO в Phase 5.3)

Сейчас реализовано:
  - schemas.py    — RawPumpRecord, QHPoint
  - curve_fitter.py — параболическая регрессия Q-H, поиск Q_BEP
  - importer.py   — конвертация в формат pumps.json + валидация
  - cli.py        — запуск как `python -m pump_calculator.etl.cli ...`
"""

"""NB: НЕТ eager-импортов модулей curve_fitter/importer на уровне пакета.
Эти модули требуют numpy (dev-dep для ETL), которая не входит в YC Functions zip.
Если нужен curve_fitter — импортируй напрямую:
    from pump_calculator.etl.curve_fitter import QHCurve, fit_qh_curve

Это позволяет incoming_classifier (P5 CRM) работать в YC Functions runtime
без numpy. См. commit 5ea50ab + 502 fix в YC backend.
"""

__all__: list[str] = []
