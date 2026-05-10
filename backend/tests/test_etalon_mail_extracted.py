"""Golden-tests на эталонах из mail dataset (zakaz@inservo.ru, IMAP импорт 2026-05-10).

Источник: ``02_dataset/etalons/from_mail/etalons_extracted_2026-05-10.json``
(83 эталона, извлечено LLM-парсером проектной документации в почте).

Отбор топ-10 по критериям:
  * Заданы ОБА параметра — Q (м³/ч) И H (м);
  * НЕ дубликат публичной БД (поле ``_duplicate_of`` отсутствует);
  * Реалистичный диапазон: 5 ≤ Q ≤ 2000, 5 ≤ H ≤ 100;
  * Разнообразие типоразмеров (малые / средние / крупные) и типов стоков
    (бытовые / пожарные / ливневая).

Допуски (по `feedback_etalons_per_object` и `feedback_kns_calculator_principles`):
  * H_full может быть выше эталонного H на 0–55 % — наш hydraulics всегда
    добавляет потери на трение + safety factor поверх геометрического dH.
    Поэтому передаём ``dH_m = H_etalon`` и ожидаем H_full в диапазоне
    [0.85·H_etalon, 1.55·H_etalon].
  * Для крупных Q > 500 м³/ч и для пожарных контуров корректным результатом
    считается срабатывание engineer_handoff_required (это ожидаемо — кейс
    выходит за L0-конверт калькулятора).

ЦЕЛЬ — защита от регрессий: алгоритм не должен крашиться или менять выдачу
для известных «боевых» сценариев из почты заказчика.
"""
from __future__ import annotations

import pytest

from pump_calculator.matching import select_pumps
from pump_calculator.schemas import L0Input

# Допуск: H_full может быть на 55 % выше эталонного H (потери + safety),
# но не должен быть ниже более чем на 15 %.
H_TOLERANCE_HIGH = 1.55
H_TOLERANCE_LOW = 0.85


def _assert_h_full_in_tolerance(h_full: float, h_etalon: float, code: str) -> None:
    """Универсальный helper: H_full из калькулятора в коридоре [0.85·H, 1.55·H]."""
    lo = h_etalon * H_TOLERANCE_LOW
    hi = h_etalon * H_TOLERANCE_HIGH
    assert lo <= h_full <= hi, (
        f"{code}: H_full={h_full:.1f} м вне коридора [{lo:.1f}; {hi:.1f}] "
        f"от эталонного H={h_etalon} м (допуск 0.85..1.55)"
    )


def _assert_pump_or_handoff(result, code: str) -> None:
    """Либо подобран хотя бы один сегмент, либо явно поднят engineer_handoff."""
    has_any_pump = any(
        getattr(result.results, seg) is not None
        for seg in ("budget", "mid", "premium")
    )
    assert has_any_pump or result.engineer_handoff_required, (
        f"{code}: ни одного насоса не подобрано И handoff не выставлен. "
        f"warnings={result.warnings}"
    )


# ──────────────────────────────────────────────────────────────────────────
# Эталон 1 — 197/22-НК «МГГ Скейтинг», Q=10.2 м³/ч H=16 м (Pedrollo, бытовая)
# ──────────────────────────────────────────────────────────────────────────


class TestEtalon197_22_NK_Skating:
    """code=197/22-НК, client=МГГ Скейтинг, source=Проект Водоотв-е Каток-5.pdf.

    Малая бытовая КНС с насосом Pedrollo для откачки талых вод катка.
    """

    def setup_method(self):
        self.code = "197/22-НК"
        self.Q = 10.2
        self.H = 16.0
        self.L0 = L0Input(Q_m3h=self.Q, dH_m=self.H, L_m=50, wastewater_type="domestic")
        self.result = select_pumps(self.L0)

    def test_does_not_crash(self):
        assert self.result is not None
        assert self.result.candidates_total >= 0

    def test_h_full_in_tolerance(self):
        _assert_h_full_in_tolerance(self.result.computed.H_full_m, self.H, self.code)

    def test_finds_pump_or_handoff(self):
        _assert_pump_or_handoff(self.result, self.code)


# ──────────────────────────────────────────────────────────────────────────
# Эталон 2 — 1578-22-НК ООО «ГИС», Симферополь, Q=12 H=15 (бытовая)
# ──────────────────────────────────────────────────────────────────────────


class TestEtalon1578_22_NK_GIS:
    """code=1578-22-НК, client=ООО «ГИС», city=Симферополь.

    Малая хозбытовая КНС, типичный профиль ИЖС / небольшого объекта.
    """

    def setup_method(self):
        self.code = "1578-22-НК"
        self.Q = 12.0
        self.H = 15.0
        self.L0 = L0Input(Q_m3h=self.Q, dH_m=self.H, L_m=50, wastewater_type="domestic")
        self.result = select_pumps(self.L0)

    def test_does_not_crash(self):
        assert self.result is not None

    def test_h_full_in_tolerance(self):
        _assert_h_full_in_tolerance(self.result.computed.H_full_m, self.H, self.code)

    def test_finds_pump_or_handoff(self):
        _assert_pump_or_handoff(self.result, self.code)


# ──────────────────────────────────────────────────────────────────────────
# Эталон 3 — 29-19-ИОС3, Новороссийск, Q=34.92 H=10 (бытовая)
# ──────────────────────────────────────────────────────────────────────────


class TestEtalon29_19_IOS3_Novorossiysk:
    """code=29-19-ИОС3, city=Новороссийск, source=ИОС3-ОЛ.1 л.1-4 (1).pdf."""

    def setup_method(self):
        self.code = "29-19-ИОС3"
        self.Q = 34.92
        self.H = 10.0
        self.L0 = L0Input(Q_m3h=self.Q, dH_m=self.H, L_m=50, wastewater_type="domestic")
        self.result = select_pumps(self.L0)

    def test_does_not_crash(self):
        assert self.result is not None

    def test_h_full_in_tolerance(self):
        _assert_h_full_in_tolerance(self.result.computed.H_full_m, self.H, self.code)

    def test_finds_pump_or_handoff(self):
        _assert_pump_or_handoff(self.result, self.code)


# ──────────────────────────────────────────────────────────────────────────
# Эталон 4 — 16-20-НВК, Q=36 H=15 (object_type не указан — общая КНС)
# ──────────────────────────────────────────────────────────────────────────


class TestEtalon16_20_NVK:
    """code=16-20-НВК, source=16-20-НВК (1).pdf.

    Дополнительный насос (additional_pumps[1]) Q=36 H=15. Типовая малая КНС.
    """

    def setup_method(self):
        self.code = "16-20-НВК"
        self.Q = 36.0
        self.H = 15.0
        self.L0 = L0Input(Q_m3h=self.Q, dH_m=self.H, L_m=50, wastewater_type="domestic")
        self.result = select_pumps(self.L0)

    def test_does_not_crash(self):
        assert self.result is not None

    def test_h_full_in_tolerance(self):
        _assert_h_full_in_tolerance(self.result.computed.H_full_m, self.H, self.code)

    def test_finds_pump_or_handoff(self):
        _assert_pump_or_handoff(self.result, self.code)


# ──────────────────────────────────────────────────────────────────────────
# Эталон 5 — 09/22-05-ВК ООО «Пантеон» Ставрополь, Q=72 H=14.1 (пожарная/ВПВ)
# ──────────────────────────────────────────────────────────────────────────


class TestEtalon09_22_05_VK_Panteon_Fire:
    """code=09/22-05-ВК, client=ООО «Пантеон», city=Ставрополь.

    Внутренние сети водоснабжения и водоотведения (РД).
    Реальный насос — ANTARUS 2 MST65-125/4/DS1-GPRS (центробежный, не погружной).
    Часть пожарного контура — допускаем engineer_handoff (наземный КМ для
    пожаротушения вне «классического» L0-конверта погружных КНС).
    """

    def setup_method(self):
        self.code = "09/22-05-ВК"
        self.Q = 72.0
        self.H = 14.1
        self.L0 = L0Input(
            Q_m3h=self.Q, dH_m=self.H, L_m=50, wastewater_type="fire_protection"
        )
        self.result = select_pumps(self.L0)

    def test_does_not_crash(self):
        assert self.result is not None

    def test_h_full_in_tolerance(self):
        _assert_h_full_in_tolerance(self.result.computed.H_full_m, self.H, self.code)

    def test_finds_pump_or_handoff(self):
        _assert_pump_or_handoff(self.result, self.code)


# ──────────────────────────────────────────────────────────────────────────
# Эталон 6 — 41/22-30-ИОС2 ФКП «УЗКС Минобороны», Москва, Q=91.44 H=23
# ──────────────────────────────────────────────────────────────────────────


class TestEtalon41_22_30_IOS2_Minoborony:
    """code=41/22-30-ИОС2, client=ФКП «УЗКС Минобороны России», city=Москва.

    Средняя КНС (~91 м³/ч, H=23 м) — оборонный заказчик.
    """

    def setup_method(self):
        self.code = "41/22-30-ИОС2"
        self.Q = 91.44
        self.H = 23.0
        self.L0 = L0Input(Q_m3h=self.Q, dH_m=self.H, L_m=50, wastewater_type="domestic")
        self.result = select_pumps(self.L0)

    def test_does_not_crash(self):
        assert self.result is not None

    def test_h_full_in_tolerance(self):
        _assert_h_full_in_tolerance(self.result.computed.H_full_m, self.H, self.code)

    def test_finds_pump_or_handoff(self):
        _assert_pump_or_handoff(self.result, self.code)


# ──────────────────────────────────────────────────────────────────────────
# Эталон 7 — 221-23-НВК ООО «ВСПК», Q=170 H=60 (пожарный, высоконапорный)
# ──────────────────────────────────────────────────────────────────────────


class TestEtalon221_23_NVK_VSPK_Fire:
    """code=221-23-НВК, client=ООО «ВСПК», source=ПРОЕКТ.pdf.

    Высоконапорная пожарная (Q=170, H=60). Калькулятор ожидаемо поднимет
    engineer_handoff — H>50 м вне «бытового» L0-конверта погружных КНС.
    """

    def setup_method(self):
        self.code = "221-23-НВК"
        self.Q = 170.0
        self.H = 60.0
        self.L0 = L0Input(
            Q_m3h=self.Q, dH_m=self.H, L_m=50, wastewater_type="fire_protection"
        )
        self.result = select_pumps(self.L0)

    def test_does_not_crash(self):
        assert self.result is not None

    def test_h_full_in_tolerance(self):
        _assert_h_full_in_tolerance(self.result.computed.H_full_m, self.H, self.code)

    def test_finds_pump_or_handoff(self):
        # Допускаем handoff — высоконапорный пожарный контур вне L0-конверта.
        _assert_pump_or_handoff(self.result, self.code)


# ──────────────────────────────────────────────────────────────────────────
# Эталон 8 — 20-033-ИОС ООО «СПЛАЙН», Симферополь, Q=615.2 H=38 (Wilo FA)
# ──────────────────────────────────────────────────────────────────────────


class TestEtalon20_033_IOS_Splyn:
    """code=20-033-ИОС, client=ООО «СПЛАЙН», city=Симферополь.

    Реальный насос — Wilo FA 10.78Z-370. Крупная КНС → ожидаем handoff
    (Q > 500 м³/ч за пределами быстрого подбора, нужен инженерный апрув).
    """

    def setup_method(self):
        self.code = "20-033-ИОС"
        self.Q = 615.2
        self.H = 38.0
        self.L0 = L0Input(Q_m3h=self.Q, dH_m=self.H, L_m=50, wastewater_type="domestic")
        self.result = select_pumps(self.L0)

    def test_does_not_crash(self):
        assert self.result is not None

    def test_h_full_in_tolerance(self):
        _assert_h_full_in_tolerance(self.result.computed.H_full_m, self.H, self.code)

    def test_finds_pump_or_handoff(self):
        _assert_pump_or_handoff(self.result, self.code)


# ──────────────────────────────────────────────────────────────────────────
# Эталон 9 — 01-07-20-ИОС2 ООО «РСХБ Управление Активами», Краснодар,
#            Q=684 H=43 (Wilo IL центробежный)
# ──────────────────────────────────────────────────────────────────────────


class TestEtalon01_07_20_IOS2_RSHB:
    """code=01-07-20-ИОС2, client=ООО «РСХБ УА», city=Краснодар.

    Реальный насос — Wilo IL 250/405-110/4 Q (наземный центробежный).
    Крупный объект, ожидаем handoff.
    """

    def setup_method(self):
        self.code = "01-07-20-ИОС2"
        self.Q = 684.0
        self.H = 43.0
        self.L0 = L0Input(Q_m3h=self.Q, dH_m=self.H, L_m=50, wastewater_type="domestic")
        self.result = select_pumps(self.L0)

    def test_does_not_crash(self):
        assert self.result is not None

    def test_h_full_in_tolerance(self):
        _assert_h_full_in_tolerance(self.result.computed.H_full_m, self.H, self.code)

    def test_finds_pump_or_handoff(self):
        _assert_pump_or_handoff(self.result, self.code)


# ──────────────────────────────────────────────────────────────────────────
# Эталон 10 — 18-007-ТХ ООО «СПЛАЙН», Симферополь, Q=1530 H=15 (ливневая)
# ──────────────────────────────────────────────────────────────────────────


class TestEtalon18_007_TH_Splyn_Storm:
    """code=18-007-ТХ, client=ООО «СПЛАЙН», city=Симферополь.

    Крупная ливневая (Q=1530 м³/ч ≈ 425 л/с, H=15 м). Ожидается handoff
    из-за расхода — Q > 1000 м³/ч в L0 практически всегда требует
    инженерного апрува (Phase 18 storm-калькулятор).
    """

    def setup_method(self):
        self.code = "18-007-ТХ"
        self.Q = 1530.0
        self.H = 15.0
        self.L0 = L0Input(Q_m3h=self.Q, dH_m=self.H, L_m=50, wastewater_type="drainage")
        self.result = select_pumps(self.L0)

    def test_does_not_crash(self):
        assert self.result is not None

    def test_h_full_in_tolerance(self):
        _assert_h_full_in_tolerance(self.result.computed.H_full_m, self.H, self.code)

    def test_finds_pump_or_handoff(self):
        _assert_pump_or_handoff(self.result, self.code)


# ──────────────────────────────────────────────────────────────────────────
# Сводный smoke-тест: все 10 эталонов прогоняются без исключений
# ──────────────────────────────────────────────────────────────────────────


@pytest.mark.parametrize(
    "code,Q,H,ww",
    [
        ("197/22-НК", 10.2, 16.0, "domestic"),
        ("1578-22-НК", 12.0, 15.0, "domestic"),
        ("29-19-ИОС3", 34.92, 10.0, "domestic"),
        ("16-20-НВК", 36.0, 15.0, "domestic"),
        ("09/22-05-ВК", 72.0, 14.1, "fire_protection"),
        ("41/22-30-ИОС2", 91.44, 23.0, "domestic"),
        ("221-23-НВК", 170.0, 60.0, "fire_protection"),
        ("20-033-ИОС", 615.2, 38.0, "domestic"),
        ("01-07-20-ИОС2", 684.0, 43.0, "domestic"),
        ("18-007-ТХ", 1530.0, 15.0, "drainage"),
    ],
)
def test_all_mail_etalons_smoke(code: str, Q: float, H: float, ww: str) -> None:
    """Защита от регрессий: ни один из 10 эталонов не должен крашить select_pumps."""
    L0 = L0Input(Q_m3h=Q, dH_m=H, L_m=50, wastewater_type=ww)
    result = select_pumps(L0)
    assert result is not None, f"{code}: select_pumps вернул None"
    assert result.computed is not None, f"{code}: нет computed-блока"
    assert result.computed.H_full_m > 0, f"{code}: H_full <= 0"
