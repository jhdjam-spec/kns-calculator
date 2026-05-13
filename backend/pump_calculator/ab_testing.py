"""A/B testing framework для научных триггеров и алгоритмов подбора.

Sc.D. Cross-Domain audit 2026-05-13: «A/B testing научных триггеров не
реализовано». Этот модуль закрывает finding: feature flags через ENV
с детерминированным bucketing'ом по hash(key).

Архитектура
-----------
- ``FeatureFlag(name, default_pct)`` — обёртка над ENV var ``AB_FLAG_<NAME>``.
- ``percent`` читается из ENV на каждом вызове (hot-reload через restart YC
  Function — на cold start подхватит свежие значения; для warm-restart нужно
  явно re-deploy).
- ``is_enabled_for(key)`` — детерминированный bucket: ``hash(name:key) % 10000``
  сравнивается с ``percent * 10000``. Один и тот же ``key`` всегда попадает
  в один и тот же bucket — repeat-stable rollout.
- Хэш — MD5 (не для криптографии, только для равномерного распределения).

Примеры использования
---------------------
::

    AB_FLAG_NEW_EXT9_NITRIFICATION=0.5   # 50% получают новый EXT-9
    AB_FLAG_THOMA_CAVITATION=1.0          # 100% (полный rollout)
    AB_FLAG_GROUNDCONTEXT_LATERAL=0.1     # 10% canary
    AB_FLAG_EN_LOCALIZATION=0.0           # off

В коде::

    from pump_calculator.ab_testing import THOMA_CAVITATION, is_flag_on

    if is_flag_on(THOMA_CAVITATION, request_id=req_id):
        result = evaluate_cavitation_for_results(...)
    else:
        result = legacy_npshalow_check(...)

Backlog
-------
- Метрики в Sentry: tag ``flag.<name>=on/off`` для split-анализа.
- Sticky bucketing по user_id с persistent storage (Redis / YDB).
- /admin/flags POST для on-the-fly изменения без redeploy.
"""

from __future__ import annotations

import hashlib
import os
from dataclasses import dataclass, field


@dataclass(frozen=True)
class FeatureFlag:
    """Один feature flag с детерминированным bucket'ом.

    Parameters
    ----------
    name : str
        Имя флага. ENV var = ``AB_FLAG_<NAME.upper()>``.
    default_pct : float
        Дефолтная доля включения в [0.0, 1.0]. Используется если ENV не задан
        или содержит мусор. Значения вне диапазона clamp'ятся.
    description : str
        Человекочитаемое описание (для ``/admin/flags`` endpoint).
    """

    name: str
    default_pct: float = 0.0
    description: str = field(default="")

    @property
    def env_var(self) -> str:
        """Имя ENV-переменной для этого флага."""
        return f"AB_FLAG_{self.name.upper()}"

    @property
    def percent(self) -> float:
        """Текущая доля включения, [0.0, 1.0].

        Читает ENV на каждом вызове (нет caching). Если ENV не задан или
        содержит не-число — возвращается ``default_pct``. Значения вне
        диапазона clamp'ятся к [0, 1].
        """
        val = os.environ.get(self.env_var)
        if val is None:
            return _clamp(self.default_pct)
        try:
            return _clamp(float(val))
        except (TypeError, ValueError):
            return _clamp(self.default_pct)

    def is_enabled_for(self, key: str | None) -> bool:
        """Включён ли флаг для конкретного ``key`` (request_id / user_id).

        Bucket: ``int(md5(name + ":" + key), 16) % 10000 < percent * 10000``.
        Один и тот же key всегда в одном bucket'е → repeat-stable rollout.
        Если ``key`` пустой/None — используется константа ``"anonymous"``
        (все anon-пользователи попадают в один bucket — это окей для
        smoke-теста, но для строгого A/B нужен real ID).
        """
        pct = self.percent
        if pct >= 1.0:
            return True
        if pct <= 0.0:
            return False
        bucket_key = key if key else "anonymous"
        # MD5 — не для криптографии, только для равномерного распределения.
        # nosec: B324 — known-non-crypto use.
        digest = hashlib.md5(f"{self.name}:{bucket_key}".encode()).hexdigest()
        bucket = int(digest, 16) % 10000
        return bucket < int(pct * 10000)


# ──────────────────────────────────────────────────────────────────────────
# Predefined flags — централизованный реестр.
#
# Дизайн-решение: каждый научный/UX trigger, который мы хотим тестировать,
# регистрируется здесь. Альтернатива (динамическая регистрация в местах
# использования) ломает /admin/flags (нет способа собрать список).
# ──────────────────────────────────────────────────────────────────────────

NEW_EXT9_NITRIFICATION = FeatureFlag(
    name="new_ext9_nitrification",
    default_pct=1.0,
    description=(
        "Новая логика EXT-9 (T-gate 10-40°C + Ex-exclusion). "
        "Sc.D. P0 fix 2026-05-13."
    ),
)
"""Триггер EXT-9 (нитрификация) с T-gate. По умолчанию 100%."""

THOMA_CAVITATION = FeatureFlag(
    name="thoma_cavitation",
    default_pct=1.0,
    description=(
        "ISO 9906:2024 кавитационный анализ (Thoma σ_кав) вместо примитивного "
        "NPSHa-NPSHr≥0.5. Sc.D. Hydraulics 2026-05-13."
    ),
)
"""Полный кавитационный анализ по ISO 9906:2024. По умолчанию 100%."""

GROUNDCONTEXT_LATERAL = FeatureFlag(
    name="groundcontext_lateral",
    default_pct=1.0,
    description=(
        "EXT-1 с σ_x = γ·z·K_a + γ_w·z_w + dynamic порог по грунту "
        "(СП 22.13330 §5.6.5). Sc.D. Mechanics 2026-05-13."
    ),
)
"""GroundContext с УГВ-компонентой и σ_x по типу грунта. По умолчанию 100%."""

EN_LOCALIZATION = FeatureFlag(
    name="en_localization",
    default_pct=0.0,
    description=(
        "EN-локализация error messages через Accept-Language header. "
        "Sc.D. Cross-Domain 2026-05-13. Текущий статус: opt-in."
    ),
)
"""EN-локализация. По умолчанию OFF (можно включить через header)."""

MOTOR_THERMAL_DERATE = FeatureFlag(
    name="motor_thermal_derate",
    default_pct=1.0,
    description=(
        "IEC 60034-1 §8.10 тепловой derate двигателя при liquid_temp_c>40°C. "
        "Sc.D. Electrical 2026-05-13."
    ),
)
"""IEC 60034-1 thermal derate. По умолчанию 100%."""

ANAEROBIC_CORROSION_RISK = FeatureFlag(
    name="anaerobic_corrosion_risk",
    default_pct=1.0,
    description=(
        "Триггер биокоррозии бетона при простое >12ч (Metcalf §5-4). "
        "Sc.D. Biology 2026-05-13."
    ),
)
"""Анаэробная биокоррозия бетона. По умолчанию 100%."""


# Регистрационный реестр всех известных флагов (для /admin/flags).
ALL_FLAGS: dict[str, FeatureFlag] = {
    flag.name: flag
    for flag in (
        NEW_EXT9_NITRIFICATION,
        THOMA_CAVITATION,
        GROUNDCONTEXT_LATERAL,
        EN_LOCALIZATION,
        MOTOR_THERMAL_DERATE,
        ANAEROBIC_CORROSION_RISK,
    )
}


# ──────────────────────────────────────────────────────────────────────────
# Public helpers
# ──────────────────────────────────────────────────────────────────────────


def is_flag_on(
    flag: FeatureFlag,
    *,
    request_id: str | None = None,
    user_id: str | None = None,
) -> bool:
    """Включён ли ``flag`` для данного user/request.

    Приоритет ключей: ``user_id`` > ``request_id`` > ``"anonymous"``.
    Использовать ``user_id`` если он стабилен между запросами (sticky bucket),
    иначе ``request_id`` (бакет меняется на каждый запрос — годится для
    бернулли-эксперимента, но не для A/B-cohort).
    """
    key = user_id or request_id
    return flag.is_enabled_for(key)


def list_flags_snapshot() -> dict[str, dict[str, object]]:
    """Снапшот всех зарегистрированных флагов для ``/admin/flags`` endpoint.

    Returns
    -------
    dict
        ``{name: {"percent": float, "env_var": str, "description": str}}``
    """
    return {
        name: {
            "percent": flag.percent,
            "env_var": flag.env_var,
            "default_pct": flag.default_pct,
            "description": flag.description,
        }
        for name, flag in ALL_FLAGS.items()
    }


# ──────────────────────────────────────────────────────────────────────────
# Internals
# ──────────────────────────────────────────────────────────────────────────


def _clamp(value: float) -> float:
    """Clamp value to [0.0, 1.0]."""
    if value < 0.0:
        return 0.0
    if value > 1.0:
        return 1.0
    return value


__all__ = [
    "ALL_FLAGS",
    "ANAEROBIC_CORROSION_RISK",
    "EN_LOCALIZATION",
    "GROUNDCONTEXT_LATERAL",
    "MOTOR_THERMAL_DERATE",
    "NEW_EXT9_NITRIFICATION",
    "THOMA_CAVITATION",
    "FeatureFlag",
    "is_flag_on",
    "list_flags_snapshot",
]
