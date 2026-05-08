"""Phase 24: Электрические расчёты для КНС/ВНС.

Источники:
- ПУЭ 7-е издание (с изм. до 2024)
- ТР ТС 004/2011 (низковольтное), 020/2011 (ЭМС), 012/2011 (ATEX)
- ГОСТ Р 50571 (электроустановки)
- ГОСТ IEC 60034-1-2014 (двигатели)
- СП 6.13130.2020 (электрооборудование пожарных установок)
- СП 31.13330.2021 §6.5 (категории надёжности)

Покрытие:
- Подбор сечения кабеля (по нагреву, по ΔU, по КЗ)
- Подбор автоматического выключателя
- Расчёт пускового тока и метода пуска
- Категория надёжности электроснабжения
- Подбор шкафа управления (МИНИ/ОПТИ/МАКС/ATEX) — по описанию из энциклопедии Aikon
"""
from .cable import (
    CABLE_SECTIONS_MM2,
    CableSelection,
    select_cable_section,
)
from .control_panel import (
    ControlPanelSpec,
    select_control_panel,
)
from .motor import (
    MotorPowerCalc,
    calc_full_load_current,
    calc_motor_power_required,
)
from .protection import (
    ProtectionDevice,
    select_circuit_breaker,
)

__all__ = [
    "CABLE_SECTIONS_MM2",
    "CableSelection",
    "ControlPanelSpec",
    "MotorPowerCalc",
    "ProtectionDevice",
    "calc_full_load_current",
    "calc_motor_power_required",
    "select_cable_section",
    "select_circuit_breaker",
    "select_control_panel",
]
