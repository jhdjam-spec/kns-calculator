# pump_calculator (backend)

Backend engine для kns-calculator. Работающий MVP алгоритма первичного подбора насосов для КНС/НС/СПД.

## Установка

```bash
cd backend
pip install -e .
# или с dev-зависимостями
pip install -e ".[dev]"
```

## Запуск API

```bash
uvicorn pump_calculator.api:app --reload --port 8000
```

OpenAPI docs: <http://localhost:8000/docs>

## Использование как библиотека

```python
from pump_calculator import select_pumps
from pump_calculator.schemas import L0Input

result = select_pumps(L0Input(
    Q_m3h=21.2,
    dH_m=10.0,
    L_m=0.0,
    wastewater_type="domestic"
))

print(result.results.budget.brand, result.results.budget.model)
# → KAIQUAN 50WQ/S 20-22-3
```

## Тесты

```bash
pytest
```

Эталонный тест верификации — `tests/test_matching_myshako.py` — должен пройти, иначе алгоритм поломан.

## Архитектура

```
pump_calculator/
├── schemas.py       Pydantic-модели L0/L1/Output
├── catalog.py       Загрузка ../02_dataset/ JSON-файлов
├── hydraulics.py    H_full, Дарси-Альтшуль, Жуковский, AOR/POR
├── matching.py      7-шаговый алгоритм + composite score
└── api.py           FastAPI app
```

См. также [`../ALGORITHM_SPEC.md`](../ALGORITHM_SPEC.md) и [`../01_spec/matching.md`](../01_spec/matching.md).
