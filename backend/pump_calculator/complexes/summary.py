"""Сводная BOM по многообъектному комплексу."""
from __future__ import annotations

from collections import defaultdict

from .models import Complex, ComplexBOMSummary


def build_complex_bom_summary(complex_obj: Complex) -> ComplexBOMSummary:
    """Сводная спецификация: группирует одинаковые позиции, суммирует стоимости.

    Например, если 3 КНС используют один и тот же насос KAIQUAN 65WQ — он будет
    одной строкой с qty=3 в сводной BOM.
    """
    # Стоимость по типам объектов
    cost_by_kind: dict[str, float] = defaultdict(float)
    # Сводная BOM с группировкой по article+name
    consolidated: dict[tuple[str, str], dict] = {}

    for site in complex_obj.sites:
        for obj in site.objects:
            cost_by_kind[obj.object_kind] += obj.estimated_cost_rub
            for item in obj.bom:
                key = (item.get("article", ""), item.get("name", ""))
                if key in consolidated:
                    consolidated[key]["quantity"] += item.get("quantity", 1)
                    consolidated[key]["total_rub"] += (
                        item.get("quantity", 1) * item.get("price_rub", 0)
                    )
                else:
                    consolidated[key] = {
                        "name": item.get("name", ""),
                        "article": item.get("article", ""),
                        "quantity": item.get("quantity", 1),
                        "price_rub": item.get("price_rub", 0),
                        "total_rub": item.get("quantity", 1) * item.get("price_rub", 0),
                        "units": item.get("units", "шт"),
                    }

    bom_list = sorted(consolidated.values(), key=lambda x: -x["total_rub"])

    notes = [
        f"Комплекс {complex_obj.code}: {complex_obj.total_objects} объектов "
        f"на {len(complex_obj.sites)} площадках",
        f"Суммарная стоимость: {complex_obj.total_estimated_cost_rub:,.0f} ₽".replace(",", " "),
        f"Уникальных позиций в BOM: {len(consolidated)}",
    ]

    return ComplexBOMSummary(
        complex_code=complex_obj.code,
        complex_name=complex_obj.name,
        total_objects=complex_obj.total_objects,
        total_sites=len(complex_obj.sites),
        total_cost_rub=complex_obj.total_estimated_cost_rub,
        cost_breakdown_by_kind=dict(cost_by_kind),
        bom_consolidated=bom_list,
        notes=notes,
    )
