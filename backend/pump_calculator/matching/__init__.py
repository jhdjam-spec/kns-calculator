"""7-шаговый алгоритм первичного подбора насоса.

Соответствует ALGORITHM_SPEC.md §2 и 01_spec/matching.md.

Пакетный layout (рефакторинг 2026-05-13 после Sc.D. cross-domain audit):
- core.py         — select_pumps() orchestrator + apply_l0_defaults + кавитация ISO 9906:2024
                    + _compute_corpus_size (~600 LOC)
- scoring.py      — composite_score + build_score_explanation + pick_top_per_segment
                    + make_pump_result (~600 LOC)
- filtering.py    — filter_by_wastewater_type / envelope / aor / ip_motor / ex (~200 LOC)
- triggers.py     — evaluate_handoff_triggers + _check_ext_9/15/16 + _ext_8_uv_dose (~360 LOC)
- suggestions.py  — build_suggestions UX-проза для 28+ триггеров (~1300 LOC)

Backward-compat: все исторические импорты `from pump_calculator.matching import X`
продолжают работать через re-exports ниже.
"""

from __future__ import annotations

# Re-export core public API
from pump_calculator.matching.core import (
    L0_DEFAULT_DH_M,
    L0_DEFAULT_L_M,
    L0_DEFAULT_WW_TYPE,
    apply_l0_defaults,
    evaluate_cavitation_for_results,
    select_pumps,
)

# Re-export filtering (Шаги 3-5)
from pump_calculator.matching.filtering import (
    filter_by_aor,
    filter_by_envelope,
    filter_by_ex,
    filter_by_ip_motor,
    filter_by_wastewater_type,
)

# Re-export scoring (composite_score, explainer, segment selection)
from pump_calculator.matching.scoring import (
    build_score_explanation,
    composite_score,
    make_pump_result,
    pick_top_per_segment,
)

# Re-export suggestions
from pump_calculator.matching.suggestions import build_suggestions

# Re-export triggers + scientific helpers (Шаг 7)
# NB: _check_ext_9_nitrification / _ext_8_uv_dose_required импортируются
# напрямую тестом test_ext9_nitrification.py — re-export обязателен.
from pump_calculator.matching.triggers import (
    _check_ext_9_nitrification,
    _check_ext_15_phosphorus,
    _check_ext_16_denitrification,
    _ext_8_uv_dose_required,
    evaluate_handoff_triggers,
)

__all__ = [
    # core
    "select_pumps",
    "apply_l0_defaults",
    "evaluate_cavitation_for_results",
    "L0_DEFAULT_DH_M",
    "L0_DEFAULT_L_M",
    "L0_DEFAULT_WW_TYPE",
    # scoring
    "composite_score",
    "build_score_explanation",
    "make_pump_result",
    "pick_top_per_segment",
    # filtering
    "filter_by_wastewater_type",
    "filter_by_envelope",
    "filter_by_aor",
    "filter_by_ip_motor",
    "filter_by_ex",
    # triggers
    "evaluate_handoff_triggers",
    "_check_ext_9_nitrification",
    "_check_ext_15_phosphorus",
    "_check_ext_16_denitrification",
    "_ext_8_uv_dose_required",
    # suggestions
    "build_suggestions",
]
