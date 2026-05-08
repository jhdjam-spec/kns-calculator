"""Phase 31: Энциклопедия — отдача статей и фрагментов в API.

Источник — markdown-файлы в `02_dataset/_analysis/encyclopedia/`.
6 базовых тематик (fire, water, electrical, hydraulics, structural, los).

Используется:
- UI drawer drill-down (при клике на любой результат → фрагмент с формулой)
- Раздел /teach (полные статьи + интерактивные примеры из эталонов)
"""
from .registry import (
    ENCYCLOPEDIA_TOPICS,
    EXAMPLES_REGISTRY,
    get_topic_full,
    get_topic_section,
    list_topics,
)

__all__ = [
    "ENCYCLOPEDIA_TOPICS",
    "EXAMPLES_REGISTRY",
    "get_topic_full",
    "get_topic_section",
    "list_topics",
]
