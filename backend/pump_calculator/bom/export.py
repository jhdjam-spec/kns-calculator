"""Экспорт BOM в CSV / Markdown."""
from __future__ import annotations

import csv
import io

from .builder import BOMSpecification


def export_bom_csv(spec: BOMSpecification) -> str:
    """Экспорт спецификации в CSV (для импорта в Excel/ГРАНД-Смету)."""
    buf = io.StringIO()
    writer = csv.writer(buf, delimiter=";", quoting=csv.QUOTE_MINIMAL)
    writer.writerow([
        "№", "Раздел", "Наименование", "Артикул", "Производитель",
        "Кол-во", "Ед.изм", "Цена, ₽", "Сумма, ₽", "Срок, дн", "Поставщик", "Примечание",
    ])
    for i, item in enumerate(spec.items, start=1):
        writer.writerow([
            i,
            item.section,
            item.name,
            item.article,
            item.manufacturer,
            item.quantity,
            item.units,
            item.price_rub_2026,
            item.total_rub,
            item.lead_time_days,
            item.supplier,
            item.note,
        ])
    writer.writerow([
        "", "", "ИТОГО", "", "", "", "", "", spec.total_rub, "", "", "",
    ])
    return buf.getvalue()


def export_bom_markdown(spec: BOMSpecification) -> str:
    """Экспорт спецификации в Markdown-таблицу."""
    lines = [
        f"# Спецификация — {spec.project_name or spec.project_code}",
        "",
        "| № | Раздел | Наименование | Артикул | Кол-во | Цена ₽ | Сумма ₽ |",
        "|---|---|---|---|---|---|---|",
    ]
    for i, item in enumerate(spec.items, start=1):
        lines.append(
            f"| {i} | {item.section} | {item.name} | {item.article or '—'} | "
            f"{item.quantity} {item.units} | {item.price_rub_2026:,.0f} | {item.total_rub:,.0f} |"
        )
    lines.append("")
    lines.append(f"**ИТОГО:** {spec.total_rub:,.0f} ₽")
    lines.append("")
    lines.append("## Распределение по разделам")
    for section, total in sorted(spec.by_section.items(), key=lambda x: -x[1]):
        pct = total / spec.total_rub * 100 if spec.total_rub else 0
        lines.append(f"- **{section}**: {total:,.0f} ₽ ({pct:.1f}%)")
    return "\n".join(lines).replace(",", " ")
