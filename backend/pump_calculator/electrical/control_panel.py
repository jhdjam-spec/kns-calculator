"""Подбор шкафа управления (НКУ) для КНС/ВНС.

Уровни (по образцу Aikon ЩУН-КНС из reference и собственного опыта Серво-Юг):

- **МИНИ** — простой пускатель + поплавки, 30-60 тыс ₽
  Применение: бытовая КНС 2-5 кВт, до 2-х насосов

- **ОПТИ** — софтстарт + ПЛК ОНИКС МК4 (или аналог) + GSM, 60-150 тыс ₽
  Применение: средняя КНС 5-30 кВт, диспетчеризация

- **МАКС** — VFD + АВР + Modbus + SCADA, 150-500 тыс ₽
  Применение: крупная КНС/ВНС 30+ кВт, I категория надёжности

- **ATEX** — взрывозащищённое исполнение + газоанализатор + GSM, от 500 тыс ₽
  Применение: нефтехимия, фильтрат ТКО, опасные среды
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

PanelLevel = Literal["mini", "opti", "max", "atex", "fire"]


@dataclass
class ControlPanelSpec:
    level: PanelLevel
    name: str
    estimated_price_rub_2026: tuple[int, int]  # (мин, макс)
    starting_method: str
    has_plc: bool
    has_vfd: bool
    has_avr: bool
    has_gsm: bool
    has_scada: bool
    has_atex: bool
    ip_class: str
    climate_class: str
    references: list[str]
    notes: list[str]


def select_control_panel(
    P_motor_kw: float,
    n_pumps: int = 2,
    reliability_category: int = 2,
    is_atex_zone: bool = False,
    is_fire_pump: bool = False,
    needs_dispatch: bool = False,
    outdoor_installation: bool = True,
) -> ControlPanelSpec:
    """Подбирает уровень шкафа по характеристикам объекта."""
    references = [
        "ПУЭ 7-е изд., гл. 7.3 (электроустановки в местах содержания воды)",
        "ТР ТС 004/2011 (низковольтное оборудование)",
        "ТР ТС 020/2011 (ЭМС)",
        "ГОСТ Р 51321.1-2012 (НКУ)",
    ]

    # ATEX — приоритет
    if is_atex_zone:
        references.append("ТР ТС 012/2011 (взрывозащита)")
        return ControlPanelSpec(
            level="atex",
            name="ШУ-АТЕХ КНС нефтехимия (Ex db IIB T4 Gb)",
            estimated_price_rub_2026=(500_000, 2_500_000),
            starting_method="VFD" if P_motor_kw > 7.5 else "soft_start",
            has_plc=True,
            has_vfd=P_motor_kw > 7.5,
            has_avr=True,
            has_gsm=True,
            has_scada=True,
            has_atex=True,
            ip_class="IP66",
            climate_class="УХЛ1",
            references=references,
            notes=[
                "Взрывозащищённое исполнение Ex db IIB T4 Gb (нефтехимия, фильтрат ТКО)",
                "Газоанализатор Хоббит-Т (H2S, NH3, CH4) обязателен",
                "Сертификация ТР ТС 012/2011",
                "Барьеры искробезопасности на сигнальных линиях",
            ],
        )

    # Пожарная — отдельный класс
    if is_fire_pump:
        references.append("СП 6.13130.2020 (электрооборудование пож. установок)")
        references.append("СП 10.13130.2020 §6.2 (резервирование)")
        return ControlPanelSpec(
            level="fire",
            name="ШУПН пожарный (СП 10.13130 §6.2)",
            estimated_price_rub_2026=(150_000, 800_000),
            starting_method="direct",  # Пож. насосы — DOL для надёжности пуска
            has_plc=True,
            has_vfd=False,  # Для пож. — DOL (СП 6.13130)
            has_avr=True,    # Обязательно для пож.
            has_gsm=True,
            has_scada=False,
            has_atex=False,
            ip_class="IP54",
            climate_class="УХЛ2" if outdoor_installation else "У1",
            references=references,
            notes=[
                "Пуск прямой (DOL) — надёжность по СП 6.13130",
                "АВР обязательно (2 источника питания)",
                "Тестовый пуск 1 раз в неделю",
                "Ручное включение из помещения охраны",
            ],
        )

    # Категория I (надёжность) → МАКС с АВР
    if reliability_category == 1 or P_motor_kw > 30:
        return ControlPanelSpec(
            level="max",
            name="ШУ-МАКС (VFD + АВР + Modbus + SCADA)",
            estimated_price_rub_2026=(150_000, 500_000),
            starting_method="VFD",
            has_plc=True,
            has_vfd=True,
            has_avr=True,
            has_gsm=True,
            has_scada=True,
            has_atex=False,
            ip_class="IP54" if outdoor_installation else "IP31",
            climate_class="УХЛ1" if outdoor_installation else "У1",
            references=references,
            notes=[
                "VFD для энергоэффективности (экономия 20-50%)",
                "АВР (2 источника) — категория I",
                "Modbus RTU/TCP для диспетчеризации",
                "Резервирование ПЛК (горячий резерв)",
            ],
        )

    # Средний (5-30 кВт) или нужна диспетчеризация → ОПТИ
    if P_motor_kw >= 5.5 or needs_dispatch:
        return ControlPanelSpec(
            level="opti",
            name="ШУ-ОПТИ (софтстарт + ПЛК ОНИКС + GSM)",
            estimated_price_rub_2026=(60_000, 150_000),
            starting_method="soft_start",
            has_plc=True,
            has_vfd=False,
            has_avr=False,
            has_gsm=True,
            has_scada=False,
            has_atex=False,
            ip_class="IP54" if outdoor_installation else "IP31",
            climate_class="УХЛ2" if outdoor_installation else "У1",
            references=references,
            notes=[
                "Софтстарт ABB PSE/Schneider ATS — снижение пускового тока в 3 раза",
                "ПЛК (ОНИКС МК4 / ОВЕН ПЛК / Сегнетика)",
                "GSM-модуль для SMS-аварий",
                "Чередование Lead/Lag по наработке часов",
            ],
        )

    # Малый (≤5 кВт), бытовая КНС → МИНИ
    return ControlPanelSpec(
        level="mini",
        name="ШУ-МИНИ (простой пускатель + поплавки)",
        estimated_price_rub_2026=(30_000, 60_000),
        starting_method="direct",
        has_plc=False,
        has_vfd=False,
        has_avr=False,
        has_gsm=False,
        has_scada=False,
        has_atex=False,
        ip_class="IP54" if outdoor_installation else "IP31",
        climate_class="УХЛ2" if outdoor_installation else "У1",
        references=references,
        notes=[
            "Прямой пуск (DOL) — для P ≤ 5.5 кВт",
            "4-5 поплавковых выключателей",
            "Простая логика чередования",
            "Световая/звуковая авария на крышке",
        ],
    )
