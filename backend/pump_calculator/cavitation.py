"""Cavitation analysis по ISO 9906:2024 + Karassik 2008.

Theory:
- Thoma cavitation coefficient: σ = NPSHa / H  (Thoma 1932)
- Pump-specific σ_3%: NPSHr при 3% потере H (ISO 9906:2024 §4.2)
- σ_кав (incipient): начало кавитации (visual + acoustic)
- σ_break (breakdown): полная кавитационная коллапс (Q→0)

Critical relation:
- σ_avail = NPSHa / H_full
- σ_req,3% = NPSHr_3% / H_full
- Margin = σ_avail / σ_req,3%
- ISO 9906:2024: Margin ≥ 1.3 для submersible, ≥ 1.5 для surface

Sc.D. audit 2026-05-13 (reference_kns_scd_hydraulics_mechanics_2026-05-13):
ранее использовалась примитивная проверка `NPSHa - NPSHr >= 0.5`,
для многоступенчатых даёт ложно-зелёный сигнал. Этот модуль вводит
полный Thoma-анализ с margin/risk/recommendations.

References:
- ISO 9906:2024 «Rotodynamic pumps — Hydraulic performance acceptance
  tests — Grades 1, 2 and 3» §4.2 (NPSHr 3% criterion)
- Karassik I.J. et al. «Pump Handbook» 4th ed. McGraw-Hill 2008,
  §22.7 «Cavitation and NPSH» (margin factors)
- Thoma D. «Die Kavitation bei Wasserturbinen» 1932 (σ coefficient)
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal

CavitationRisk = Literal["safe", "marginal", "warning", "critical"]
PumpType = Literal["submersible", "surface", "multistage"]

# Thresholds по ISO 9906:2024 + Karassik §22.7
THRESHOLD_SAFE_SURFACE = 1.5      # surface/multistage: безопасно
THRESHOLD_SAFE_SUBMERSIBLE = 1.3  # submersible: безопасно
THRESHOLD_MARGINAL_SURFACE = 1.3  # surface marginal
THRESHOLD_MARGINAL_SUBMERSIBLE = 1.1  # submersible marginal
# margin < 1.0 → critical (кавитация неизбежна)


@dataclass
class CavitationResult:
    """Результат полного кавитационного анализа по ISO 9906:2024."""

    NPSHa_m: float
    NPSHr_3pct_m: float
    H_full_m: float
    sigma_avail: float
    sigma_req_3pct: float
    margin: float
    risk: CavitationRisk
    risk_reason: str
    recommendations: list[str] = field(default_factory=list)


def _thresholds_for(pump_type: PumpType) -> tuple[float, float]:
    """Возвращает (threshold_safe, threshold_marginal) для типа насоса.

    Surface/multistage насосы более чувствительны к NPSH:
    - всас на верх → атм. давление - вакуум всаса в стволе колеса;
    - многоступенчатый → первое колесо отвечает за всю NPSHr,
      ошибка стоит всех ступеней (Karassik §22.7).
    """
    if pump_type in ("surface", "multistage"):
        return THRESHOLD_SAFE_SURFACE, THRESHOLD_MARGINAL_SURFACE
    # submersible (default)
    return THRESHOLD_SAFE_SUBMERSIBLE, THRESHOLD_MARGINAL_SUBMERSIBLE


def analyze_cavitation(
    NPSHa_m: float,
    NPSHr_3pct_m: float,
    H_full_m: float,
    pump_type: PumpType = "submersible",
    liquid_temp_c: float = 20.0,
) -> CavitationResult:
    """Полный кавитационный анализ по ISO 9906:2024.

    Args:
        NPSHa_m: доступный NPSH (физика площадки) — м вод.ст.
        NPSHr_3pct_m: требуемый NPSH насоса при 3% потере H — м.
            Если в паспорте дан только NPSHr (без указания критерия) —
            принимаем что это NPSHr_3% (industry default ISO 9906).
        H_full_m: полный напор насоса на рабочей точке — м.
        pump_type: тип насоса (влияет на threshold по Karassik §22.7).
        liquid_temp_c: температура жидкости — при T > 40°C
            P_vapor растёт, NPSHa эффективно падает → conservative -10%.

    Returns:
        CavitationResult с σ_avail, σ_req, margin, risk и recommendations.
    """
    # Edge case: статика (H=0) — кавитация невозможна
    if H_full_m <= 0:
        return CavitationResult(
            NPSHa_m=NPSHa_m,
            NPSHr_3pct_m=NPSHr_3pct_m,
            H_full_m=0.0,
            sigma_avail=0.0,
            sigma_req_3pct=0.0,
            margin=float("inf"),
            risk="safe",
            risk_reason="H_full = 0, кавитация невозможна (статика)",
            recommendations=[],
        )

    sigma_avail = NPSHa_m / H_full_m
    sigma_req = NPSHr_3pct_m / H_full_m if NPSHr_3pct_m > 0 else 0.0

    if sigma_req <= 0:
        # NPSHr=0 или не задан → формально бесконечный запас, но честнее
        # отдать marginal, так как данные неполные.
        return CavitationResult(
            NPSHa_m=NPSHa_m,
            NPSHr_3pct_m=NPSHr_3pct_m,
            H_full_m=H_full_m,
            sigma_avail=sigma_avail,
            sigma_req_3pct=0.0,
            margin=float("inf"),
            risk="marginal",
            risk_reason=(
                "NPSHr не задан в паспорте — невозможно строго оценить "
                "кавитационный запас. Запросите NPSH-кривую у производителя."
            ),
            recommendations=[
                "Получить NPSH-кривую насоса (заводское ISO 9906 испытание).",
                f"Текущий NPSHa = {NPSHa_m:.2f} м — допустимый верхний предел "
                f"NPSHr для безопасной работы: {NPSHa_m / 1.3:.2f} м.",
            ],
        )

    margin = sigma_avail / sigma_req

    # T-correction (Karassik §22.7.3): при T > 40°C P_vapor растёт,
    # эффективный NPSHa падает на 10-15%. Применяем conservative фактор.
    if liquid_temp_c > 40:
        margin *= 0.9

    threshold_safe, threshold_marginal = _thresholds_for(pump_type)

    # Risk evaluation
    if margin >= threshold_safe:
        risk: CavitationRisk = "safe"
        reason = (
            f"σ_avail/σ_req = {margin:.2f} ≥ {threshold_safe:.1f} "
            f"(ISO 9906:2024, Karassik §22.7 для {pump_type})"
        )
        recs: list[str] = []
    elif margin >= threshold_marginal:
        risk = "marginal"
        reason = (
            f"σ_avail/σ_req = {margin:.2f} в диапазоне "
            f"[{threshold_marginal:.1f}, {threshold_safe:.1f}) — "
            f"приемлемо для {pump_type}, но без запаса на износ"
        )
        recs = [
            "Запас по NPSH на грани — мониторить износ рабочего колеса "
            "(каждые 6 мес виброконтроль ISO 10816-7).",
            "Желательно увеличить NPSHa на 0.5-1 м: больший корпус, "
            "ниже отметка лотка подвода или укоротить всас.",
        ]
    elif margin >= 1.0:
        risk = "warning"
        reason = (
            f"σ_avail/σ_req = {margin:.2f} < {threshold_marginal:.1f} — "
            f"высокий риск кавитации (ISO 9906:2024 не гарантирует "
            f"работу без 3% drop)"
        )
        recs = [
            "Увеличить NPSHa: понизить отметку насоса или укоротить всас.",
            "Рассмотреть насос с меньшим NPSHr (часто = больший импеллер, "
            "ниже rpm — обратная сторона: больше габарит, цена).",
            "Установить датчик вибрации для раннего обнаружения "
            "кавитационного коллапса (ISO 10816-7, alarm > 7.1 мм/с).",
        ]
    else:
        risk = "critical"
        max_npshr = NPSHa_m * 0.7
        reason = (
            f"σ_avail/σ_req = {margin:.2f} < 1.0 — кавитация неизбежна "
            f"(NPSHa={NPSHa_m:.2f} м < NPSHr={NPSHr_3pct_m:.2f} м)"
        )
        recs = [
            "КРИТИЧНО: насос НЕ работоспособен при текущих условиях.",
            "Обязательно: изменить компоновку (буст-насос подкачки, "
            "погружной вместо surface, понизить отметку машзала).",
            f"Альтернатива: насос с NPSHr_3% < {max_npshr:.1f} м "
            f"(0.7 × NPSHa с запасом по Karassik §22.7).",
        ]

    return CavitationResult(
        NPSHa_m=NPSHa_m,
        NPSHr_3pct_m=NPSHr_3pct_m,
        H_full_m=H_full_m,
        sigma_avail=sigma_avail,
        sigma_req_3pct=sigma_req,
        margin=margin,
        risk=risk,
        risk_reason=reason,
        recommendations=recs,
    )


def explain_cavitation_engineer(result: CavitationResult, pump_type: PumpType = "submersible") -> str:
    """2-level reason: инженерное обоснование для auto_cavitation_warning.

    Возвращает многострочный текст с формулой Thoma, числами, цитатой ISO.
    """
    threshold_safe, threshold_marginal = _thresholds_for(pump_type)
    return (
        f"💧 Кавитационный анализ по ISO 9906:2024 + Karassik §22.7:\n"
        f"📐 σ_avail = NPSHa / H_full = {result.NPSHa_m:.2f} / "
        f"{result.H_full_m:.2f} = {result.sigma_avail:.3f}\n"
        f"📐 σ_req,3% = NPSHr_3% / H_full = {result.NPSHr_3pct_m:.2f} / "
        f"{result.H_full_m:.2f} = {result.sigma_req_3pct:.3f}\n"
        f"📐 Margin = σ_avail / σ_req = {result.margin:.2f} "
        f"(порог safe ≥ {threshold_safe:.1f}, marginal ≥ {threshold_marginal:.1f}).\n"
        f"⚠ Risk: {result.risk.upper()} — {result.risk_reason}\n"
        f"📚 ISO 9906:2024 §4.2: «NPSHr определяется как NPSH при котором "
        f"напор насоса падает на 3% от номинального при заданном Q»."
    )


def explain_cavitation_manager(result: CavitationResult) -> str:
    """2-level reason: менеджерское объяснение последствий."""
    if result.risk == "critical":
        return (
            "❌ Кавитация неизбежна — насос будет грохотать как мешок с гайками "
            "и развалит рабочее колесо за 1-3 месяца.\n"
            "💰 Аварийный ремонт + замена колеса: 200-500 тыс ₽.\n"
            "💡 Решение: насос с другой NPSHr или подпитка снизу (буст-насос).\n"
            "📞 Обязательная консультация инженера до заказа."
        )
    if result.risk == "warning":
        return (
            "⚠ Высокий риск кавитации: насос будет шуметь (>80 дБ), "
            "замена колеса через 1-2 года вместо 5-7 лет.\n"
            "💰 Преждевременная замена колеса: 80-150 тыс ₽ + простой 2-5 дней.\n"
            "💡 Решение: понизить отметку приёмной камеры или выбрать насос "
            "с лучшим NPSHr (+10-20% к цене окупится за 2 года)."
        )
    if result.risk == "marginal":
        return (
            "⚡ Кавитационный запас на грани — допустимо, но без права "
            "на ошибку при износе.\n"
            "💡 Регламент: виброконтроль каждые 6 мес (вибродатчик 30-50 тыс ₽). "
            "Резерв импеллера на складе обязателен."
        )
    # safe
    return (
        f"✅ Кавитационный запас в норме (margin={result.margin:.2f}), "
        f"насос проработает паспортные 7-10 лет без преждевременного износа."
    )
