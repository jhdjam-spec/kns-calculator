"""Diff-отчёт: сравнение validated[] с существующим pumps.json.

Используется в ``pipeline.parse_catalog`` (этап 7) и в CLI команде ``review``.
Отчёт в markdown, чтобы человек мог быстро глазами оценить:
    - какие модели НОВЫЕ (будут добавлены при merge)
    - какие СОВПАДАЮТ по id (будут пропущены или перезаписаны)
    - какие были в pumps.json, но не появились в новом прогоне (potential
      deprecated, но мы их НЕ трогаем — только сообщаем)

Контракт: ``build_diff_report(validated_dicts, brand) -> str``.
"""

from __future__ import annotations

from typing import Any

from pump_calculator import catalog
from pump_calculator.etl.importer import _make_pump_id


def _existing_ids_for_brand(brand: str) -> set[str]:
    """Получить id всех насосов в pumps.json для указанного бренда."""
    pumps = catalog.load_pumps()
    return {p["id"] for p in pumps if p.get("brand", "").lower() == brand.lower()}


def _id_for_validated(record: dict[str, Any]) -> str:
    """Сгенерировать id той же логикой, что использует importer."""
    return _make_pump_id(record["brand"], record["model"])


def build_diff_report(validated: list[dict[str, Any]], brand: str) -> str:
    """Сборка markdown-отчёта diff.

    Args:
        validated: list[RawPumpRecord-dict] из pipeline (уже прошли Pydantic).
        brand:     бренд, для которого делался прогон (фильтрует существующий
                   pumps.json для корректного сравнения).

    Returns:
        Markdown-текст готов для записи в ``runs/<id>/07_diff.md`` или вывода
        в stdout через CLI ``etl review``.
    """
    new_ids = {_id_for_validated(r): r for r in validated}
    existing_ids = _existing_ids_for_brand(brand)

    only_new = sorted(new_ids.keys() - existing_ids)
    overlapping = sorted(new_ids.keys() & existing_ids)
    only_existing = sorted(existing_ids - new_ids.keys())

    lines: list[str] = []
    lines.append(f"# ETL diff-отчёт — {brand}")
    lines.append("")
    lines.append(f"- **Новые модели** (будут добавлены): {len(only_new)}")
    lines.append(f"- **Совпадают по id** (skip/overwrite): {len(overlapping)}")
    lines.append(f"- **Уже в БД, но не в прогоне**: {len(only_existing)}")
    lines.append("")

    if only_new:
        lines.append("## Новые модели")
        lines.append("")
        lines.append("| id | model | P_kW | Q_BEP? | qh_points |")
        lines.append("|---|---|---|---|---|")
        for pid in only_new:
            rec = new_ids[pid]
            qh_count = len(rec.get("qh_curve", []))
            lines.append(
                f"| `{pid}` | {rec['model']} | {rec['P_kW']} | "
                f"(вычислится при импорте) | {qh_count} |"
            )
        lines.append("")

    if overlapping:
        lines.append("## Совпадения (потребуется --overwrite для замены)")
        lines.append("")
        for pid in overlapping:
            lines.append(f"- `{pid}`")
        lines.append("")

    if only_existing:
        lines.append("## Уже в БД, не появились в прогоне")
        lines.append("")
        lines.append("Эти записи **не трогаются** — отображены информативно.")
        lines.append("")
        for pid in only_existing:
            lines.append(f"- `{pid}`")
        lines.append("")

    lines.append("---")
    lines.append("")
    lines.append("**Команды для merge:**")
    lines.append("")
    lines.append("```powershell")
    lines.append("# Только новые (skip существующие):")
    lines.append("python -m pump_calculator.etl.cli merge <run_dir>")
    lines.append("# С перезаписью существующих:")
    lines.append("python -m pump_calculator.etl.cli merge <run_dir> --overwrite")
    lines.append("```")

    return "\n".join(lines) + "\n"
