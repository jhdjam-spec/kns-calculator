"""Извлечение Q-H кривых из табличных данных PDF (Pedrollo VX и подобные).

Многие производители публикуют Q-H паспортные данные не графиками, а
табличной матрицей: в заголовке — Q-значения (м³/ч или л/мин), в строках —
модели насосов; на пересечении — H (м). Это идеальный кейс для pdfplumber:
текст vector, цифры — обычные строки.

Этот модуль:
    1. Сканирует все ``DocumentChunk.tables`` (формат pdfplumber-runner).
    2. Эвристически определяет, какие таблицы — Q-H матрицы.
    3. Парсит Q-заголовок и H-строки, нормализует единицы, чистит склейки
       (pdfplumber иногда схлопывает соседние числа в одну ячейку: ``'33 3'``).
    4. Возвращает ``dict[model_name, list[QHPoint]]``.

Для Pedrollo VX 50 Hz:
    - Каждая страница 2-таблица содержит до 4 моделей (single-phase + three-phase
      имеют идентичные Q-H, поэтому в одной строке указаны оба имени, например
      ``'VXm 8/35'`` и ``'VX 8/35'`` — записываем для обоих).
    - Q-значения даются и в м³/ч, и в л/мин (две строки заголовка); используем
      м³/ч (приоритет), при отсутствии — конвертируем л/мин → м³/ч (×0.06).

Подход на pure-функциях, без сайд-эффектов: на вход — chunks, на выход — dict.
"""

from __future__ import annotations

import re
from typing import Any

from pump_calculator.etl.pdf.docling_runner import DocumentChunk
from pump_calculator.etl.schemas import QHPoint

# ---------------------------------------------------------------------------
# Низкоуровневые парсеры
# ---------------------------------------------------------------------------

# Модель Pedrollo VX/VXm: "VX 8/35", "VXm 10/50", допускаем пробелы и регистр.
_MODEL_RE = re.compile(r"^V[Xx]m?\s*\d+\s*/\s*\d+$")

# Маркеры расхода/напора в подписях ячеек.
_Q_LABEL_RE = re.compile(r"\bQ\b|m\s*³\s*/\s*h|м\s*³\s*/\s*ч|m3\s*/\s*h|м3\s*/\s*ч", re.IGNORECASE)
_LMIN_LABEL_RE = re.compile(r"l\s*/\s*min|л\s*/\s*мин", re.IGNORECASE)
_H_LABEL_RE = re.compile(r"\bH\b|metres|meters|метр", re.IGNORECASE)


def _parse_float(s: str | None) -> float | None:
    """Аккуратно распарсить число из ячейки таблицы.

    Поддерживает:
        - десятичную запятую: ``"8,5"`` → ``8.5``
        - окружающие пробелы и неразрывные пробелы
        - пустые/None → ``None``
    """
    if s is None:
        return None
    text = str(s).strip().replace("\xa0", " ").replace(",", ".").replace(" ", "")
    if not text:
        return None
    try:
        return float(text)
    except ValueError:
        return None


def _split_numeric_cell(cell: str | None) -> list[float]:
    """Разбить ячейку на список чисел.

    pdfplumber на широких таблицах иногда склеивает два соседних значения
    в одну ячейку через пробел: ``'33 3'`` (на самом деле 33 и 36 из колонок,
    которые алгоритм границ принял за одну). Также встречаются составные
    значения вида ``'4.5 3.'`` — берём только первое полное число.

    Стратегия:
        - сначала нормализуем (запятая → точка, неразрывный пробел → обычный)
        - расщепляем по whitespace
        - каждый токен пробуем как float; пропускаем нечисловые
        - неполные «обрывки» вроде ``'3.'`` отбрасываем (нет смысла угадывать)
    """
    if cell is None:
        return []
    text = str(cell).strip().replace("\xa0", " ").replace(",", ".")
    if not text:
        return []
    out: list[float] = []
    for token in text.split():
        # Игнорируем «обрывки» — токены, заканчивающиеся точкой без цифры после.
        if token.endswith(".") and len(token) > 1 and token[:-1].replace(".", "").isdigit():
            # Например '3.' — это неполное число, но всё-таки int 3 валиден.
            try:
                out.append(float(token[:-1]))
            except ValueError:
                continue
            continue
        try:
            out.append(float(token))
        except ValueError:
            continue
    return out


# ---------------------------------------------------------------------------
# Эвристика: является ли таблица Q-H матрицей
# ---------------------------------------------------------------------------


def _row_has_model(row: list[str]) -> list[str]:
    """Найти в строке имена моделей (в формате ``VX 8/35`` / ``VXm 10/50``).

    Возвращает список найденных имён (без повторений, в порядке появления).
    """
    seen: list[str] = []
    for cell in row:
        if cell is None:
            continue
        s = str(cell).strip()
        if _MODEL_RE.match(s):
            normalized = re.sub(r"\s+", " ", s).strip()
            if normalized not in seen:
                seen.append(normalized)
    return seen


def _is_qh_table(table: dict[str, Any]) -> bool:
    """Проверить, похожа ли таблица на Q-H матрицу.

    Критерии:
        1. В заголовке (header) или первых двух строках есть как минимум 4
           числовых значения подряд (Q-значения вдоль оси).
        2. Есть строка с `H metres`/`H` подписью или строка модели по regex.
    """
    header = [c if c is not None else "" for c in table.get("header", [])]
    df = table.get("df", [])

    # Числа в заголовке
    header_numbers: list[float] = []
    for cell in header:
        header_numbers.extend(_split_numeric_cell(cell))
    if len(header_numbers) < 4:
        # Может быть, числа Q вынесены в первую строку df (иногда pdfplumber
        # помещает заголовок в df[0] вместо header).
        first_row_numbers: list[float] = []
        if df:
            for cell in df[0]:
                first_row_numbers.extend(_split_numeric_cell(cell))
        if len(first_row_numbers) < 4:
            return False

    # Ищем модель или метку H в df
    has_model_or_h = False
    for row in df[:6]:  # достаточно посмотреть первые несколько строк
        if _row_has_model(list(row)):
            has_model_or_h = True
            break
        if any(c and _H_LABEL_RE.search(str(c)) for c in row):
            has_model_or_h = True
            break
    return has_model_or_h


# ---------------------------------------------------------------------------
# Извлечение Q-значений из заголовка
# ---------------------------------------------------------------------------


def _q_cells_after_label(cells: list, label_re: re.Pattern) -> list[float]:
    """Из ячеек собрать числа справа от ячейки, в которой найден label.

    Если label не найден — пустой список.
    """
    label_idx = -1
    for i, cell in enumerate(cells):
        if cell and label_re.search(str(cell)):
            label_idx = i
            break
    if label_idx < 0:
        return []
    nums: list[float] = []
    for cell in cells[label_idx + 1 :]:
        nums.extend(_split_numeric_cell(cell))
    return nums


def _extract_q_values(table: dict[str, Any]) -> tuple[list[float], str]:
    """Извлечь упорядоченный список Q-значений и единицу измерения.

    Возвращает:
        (q_values, unit), где unit ∈ {"m3h", "l_min"}.

    Pedrollo-структура:
        header (row 0): [None, None, 'POWER (P2) kW HP', None, 'm Q l/', '³/h',
                         '0', '3', '6', '12', '18', '21', '24', '27', '30', '33', None]
        df[0]  (row 1): [None, None, None, None, None, 'min',
                         '0', '50', '100', '200', '300', '350', '400', ...]

    Стратегия:
        1. Найти в header ячейку с подписью м³/ч (``Q``, ``m³/h``, ``м³/ч``).
           Числа ПОСЛЕ этой ячейки — Q в м³/ч.
        2. Если шаг 1 не дал результата, искать в первой строке df ячейку
           с ``l/min`` или ``min``; числа после — Q в л/мин (конвертируем ×0.06).
        3. Иначе — fallback: все числа header, помечаем как m3h.
    """
    header = [c if c is not None else "" for c in table.get("header", [])]
    df = table.get("df", [])

    # 1) Q в м³/ч из header (после метки ``³/h`` / ``m³/h`` / ``м³/ч``)
    m3h_label = re.compile(r"³\s*/\s*h|m\s*³\s*/\s*h|м\s*³\s*/\s*ч|m3\s*/\s*h", re.IGNORECASE)
    q_m3h_from_header = _q_cells_after_label(header, m3h_label)
    if len(q_m3h_from_header) >= 4:
        return q_m3h_from_header, "m3h"

    # 2) Q в л/мин из df[0] (после метки ``min``)
    lmin_label = re.compile(r"\bl\s*/\s*min|\bmin\b|л\s*/\s*мин", re.IGNORECASE)
    if df:
        first_row = list(df[0])
        q_lmin = _q_cells_after_label(first_row, lmin_label)
        if len(q_lmin) >= 4:
            return q_lmin, "l_min"

    # 3) Fallback: все числа header
    fallback: list[float] = []
    for cell in header:
        fallback.extend(_split_numeric_cell(cell))
    return fallback, "m3h"


def _normalize_q_to_m3h(q_values: list[float], unit: str) -> list[float]:
    """Конвертировать Q в м³/ч, если был дан в л/мин."""
    if unit == "l_min":
        return [round(v * 0.06, 4) for v in q_values]
    return q_values


# ---------------------------------------------------------------------------
# Сборка QHPoint для одной строки модели
# ---------------------------------------------------------------------------


def _extract_h_values_from_row(row: list[str]) -> list[float]:
    """Из строки таблицы вытащить числовые H-значения (по порядку).

    В Pedrollo VX строка модели имеет структуру:
        ``['VXm 8/35', 'VX 8/35', '0.55', '0.75', 'H metres', None, '9', '8', ...]``
    То есть колонки 0-1 — имена моделей, 2-3 — мощности (kW + HP), 4 —
    подпись ``H metres``, далее H-значения.

    Стратегия:
        - Если в строке есть ячейка с подписью ``H``/``H metres``/``metres``,
          берём числа ПОСЛЕ этой ячейки — это и есть H.
        - Иначе пропускаем ячейки с именем модели (VX/VXm) и максимум 2-3
          числовые ячейки (потенциальные P_kW + P_HP).
    """
    # Найти индекс ячейки с подписью H
    h_label_idx = -1
    for i, cell in enumerate(row):
        if cell and _H_LABEL_RE.search(str(cell)):
            h_label_idx = i
            break

    if h_label_idx >= 0:
        # H-значения — справа от метки H metres
        nums: list[float] = []
        for cell in row[h_label_idx + 1 :]:
            nums.extend(_split_numeric_cell(cell))
        return nums

    # Fallback: модель → пропуск 2 power-чисел
    nums = []
    for cell in row:
        nums.extend(_split_numeric_cell(cell))
    # Pedrollo: первые 2 числа — мощности (kW, HP). Если row начинается с
    # имён моделей (нечисловые ячейки) — числа уже без них; отрезаем 2.
    if len(nums) > 2:
        return nums[2:]
    return nums


def _pair_q_with_h(
    q_values: list[float],
    row_numbers: list[float],
) -> list[QHPoint]:
    """Сопоставить Q-значения и H-числа из строки модели.

    Стратегия:
        - В строке модели первые 1-2 числа — мощности (kW, HP). Если общее
          число чисел больше числа Q-значений ровно на 1-3 — отрезаем начало.
        - Если ровно совпадает — pair up как есть.
        - Если меньше — pair первые ``len(row_numbers)`` Q-значений
          (модель слабее, у неё короче кривая).
        - Игнорируем нулевые H в конце (но не нулевую первую точку — shutoff).
    """
    if not q_values or not row_numbers:
        return []

    n_q = len(q_values)
    n_r = len(row_numbers)

    if n_r > n_q:
        # Отрезаем начало (мощности и пр.)
        h_values = row_numbers[n_r - n_q :]
    else:
        h_values = list(row_numbers)

    points: list[QHPoint] = []
    for q, h in zip(q_values, h_values, strict=False):
        if q < 0 or h < 0:
            continue
        points.append(QHPoint(Q_m3h=q, H_m=h))

    # Обрезаем «хвост» нулей (когда у модели реально кривая короче):
    # удаляем точки H==0 в конце, но оставляем первую точку даже если H==0
    # (хотя для центробежных насосов shutoff head всегда > 0).
    while len(points) > 1 and points[-1].H_m == 0:
        points.pop()

    return points


# ---------------------------------------------------------------------------
# Главная функция модуля
# ---------------------------------------------------------------------------


def extract_qh_curves_from_chunks(
    chunks: list[DocumentChunk],
) -> dict[str, list[QHPoint]]:
    """Извлечь Q-H кривые для всех моделей из табличных данных PDF.

    Алгоритм:
        1. Перебрать все ``chunk.tables``.
        2. Для каждой таблицы определить, является ли она Q-H матрицей
           (см. :func:`_is_qh_table`).
        3. Распарсить Q-заголовок и единицы измерения.
        4. Для каждой строки, в которой найдено имя модели, собрать H-числа
           и связать с Q-значениями.

    Если модель встречается несколько раз (single-phase + three-phase в одной
    строке, либо повторно в другой таблице) — записываем кривую для каждого
    имени; при повторе в другой таблице переписываем (последняя таблица —
    обычно более полная).

    Returns:
        Словарь ``{model_name: [QHPoint, ...]}``. Имя модели нормализовано:
        одинарный пробел между префиксом и типоразмером, без лишних пробелов
        внутри типоразмера.
    """
    result: dict[str, list[QHPoint]] = {}

    for chunk in chunks:
        for table in chunk.tables or []:
            if not _is_qh_table(table):
                continue

            q_values, unit = _extract_q_values(table)
            if len(q_values) < 3:
                continue
            q_m3h = _normalize_q_to_m3h(q_values, unit)

            df = table.get("df", [])
            for row in df:
                row_list = list(row)
                models = _row_has_model(row_list)
                if not models:
                    continue
                # Сопоставляем H после очистки — берём числа из всей строки,
                # отрезая мощности с начала.
                row_nums = _extract_h_values_from_row(row_list)
                # Убираем числа, которые точно являются Q-индексами или
                # P-номиналами: типичные мощности < 4 kW, и они идут парой
                # (kW, HP). Просто полагаемся на хвостовое выравнивание в
                # _pair_q_with_h.
                points = _pair_q_with_h(q_m3h, row_nums)
                if len(points) < 3:
                    continue
                for model in models:
                    result[model] = points

    return result
