"""Центральный реестр нормативной базы калькулятора КНС.

ЗАЧЕМ:
- Каждый расчёт должен явно ссылаться на действующий норматив (СП/ГОСТ/ТР ТС/ФЗ).
- Версии нормативов меняются (СП 32 имел Изм.№4 от 17.01.2025; СП 8.13130 — Изм.№1 от 01.03.2024).
- Калькулятор должен быть юридически воспроизводим: расчёт от 2026-05 должен
  ссылаться на конкретные редакции, а не на общие "СП 32.13330".
- Режим энциклопедии в UI должен показывать пользователю формулу + цитату + ссылку
  на актуальный текст норматива.

КАК:
- Каждый норматив описан как `Regulation` с полями: code, edition, in_force_from,
  superseded_by, url_consultant, url_official, scope.
- Модули расчётов импортируют константы из этого файла и кладут их в `references`
  ответа API.
- При изменении норматива (выходит новая редакция) — обновить здесь, и все модули
  автоматически начнут ссылаться на новую версию.

Источники для дат и URL:
- docs.cntd.ru — официальный текст СП в актуальной редакции
- minstroyrf.gov.ru — Минстрой РФ
- mchs.gov.ru — МЧС (нормативы 13130)
- Реестр документов в национальной системе стандартизации (gostinfo.ru)
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Literal


@dataclass(frozen=True)
class Regulation:
    """Запись о нормативе: код, редакция, область применения, ссылки."""

    code: str                          # Код норматива, например "СП 32.13330.2018"
    title: str                         # Полное название
    edition: str                       # Редакция или год: "2018 + Изм.№4 от 17.01.2025"
    in_force_from: str                 # Дата ввода в действие (ISO YYYY-MM-DD)
    superseded_by: str | None = None   # Если норматив отменён — что вместо
    url_official: str = ""             # Ссылка на официальный источник (cntd/minstroy/mchs)
    scope: str = ""                    # Краткое описание области применения
    category: Literal[
        "sewerage", "water_supply", "fire_safety",
        "climate", "structural", "tech_regulation",
        "electrical", "occupational_safety", "sanitary"
    ] = "sewerage"


# ============================================================================
# КАНАЛИЗАЦИЯ И ВОДОСНАБЖЕНИЕ (наружные и внутренние сети)
# ============================================================================

SP_32 = Regulation(
    code="СП 32.13330.2018",
    title="Канализация. Наружные сети и сооружения",
    edition="2018 + Изм.№1 (2019) + Изм.№2 (2020) + Изм.№3 (2022) + Изм.№4 (17.01.2025)",
    in_force_from="2018-12-23",
    url_official="https://docs.cntd.ru/document/554820821",
    scope="Расчёт расходов сточных вод, ливневой канализации, выбор труб, насосных станций",
    category="sewerage",
)

SP_32_2012 = Regulation(
    code="СП 32.13330.2012",
    title="Канализация. Наружные сети и сооружения (предыдущая редакция)",
    edition="2012",
    in_force_from="2013-01-01",
    superseded_by="СП 32.13330.2018",
    url_official="https://docs.cntd.ru/document/1200094427",
    scope="Используется только для эталонных расчётов и реконструкции (Z_асфальт=0.28)",
    category="sewerage",
)

SP_30 = Regulation(
    code="СП 30.13330.2020",
    title="Внутренний водопровод и канализация зданий",
    edition="2020 + Изм.№1 (2022)",
    in_force_from="2021-06-30",
    url_official="https://docs.cntd.ru/document/573135590",
    scope="Расчёт расходов холодной/горячей воды и стоков внутри зданий, диаметры стояков",
    category="water_supply",
)

SP_31 = Regulation(
    code="СП 31.13330.2021",
    title="Водоснабжение. Наружные сети и сооружения",
    edition="2021",
    in_force_from="2022-06-26",
    url_official="https://docs.cntd.ru/document/727733100",
    scope="Расчёт расходов на хозпитьевые нужды, водозабор, насосные станции водоснабжения (ВНС)",
    category="water_supply",
)

SP_399 = Regulation(
    code="СП 399.1325800.2018",
    title="Здания и сооружения. Правила проектирования сетей водоснабжения и водоотведения",
    edition="2018",
    in_force_from="2019-04-29",
    url_official="https://docs.cntd.ru/document/552045366",
    scope="Уточнение СП 30/СП 31 для застройки",
    category="water_supply",
)

# ============================================================================
# ПОЖАРНАЯ БЕЗОПАСНОСТЬ (СП 13130, ФЗ 123)
# ============================================================================

SP_8_13130 = Regulation(
    code="СП 8.13130.2020",
    title="Системы противопожарной защиты. Источники наружного противопожарного водоснабжения",
    edition="2020 + Изм.№1 (01.03.2024)",
    in_force_from="2020-12-29",
    url_official="https://docs.cntd.ru/document/566388979",
    scope="Расход и резервуары на наружное пожаротушение, гидранты, давление",
    category="fire_safety",
)

SP_10_13130 = Regulation(
    code="СП 10.13130.2020",
    title="Системы противопожарной защиты. Внутренний противопожарный водопровод",
    edition="2020 + Изм.№1 (2024)",
    in_force_from="2020-12-29",
    url_official="https://docs.cntd.ru/document/566388978",
    scope="Внутренний ППВ — пожарные краны, расходы струй, насосные установки",
    category="fire_safety",
)

SP_485 = Regulation(
    code="СП 485.1311500.2020",
    title="Установки пожаротушения автоматические. Нормы и правила проектирования",
    edition="2020 (заменил СП 5.13130.2009)",
    in_force_from="2020-09-01",
    url_official="https://docs.cntd.ru/document/566421869",
    scope="Спринклерные/дренчерные установки, расход, время работы",
    category="fire_safety",
)
# Deprecated alias — старое имя ссылалось на СП 5.13130 (отменён в 2020).
# Не использовать в новом коде; ref("SP_485", ...).
SP_5_13130 = SP_485

FZ_123 = Regulation(
    code="123-ФЗ",
    title="Технический регламент о требованиях пожарной безопасности",
    edition="2008 + последние изм. 25.12.2023",
    in_force_from="2009-05-01",
    url_official="https://docs.cntd.ru/document/902111644",
    scope="Категории зданий по пожарной опасности, степень огнестойкости, классы К0/К1/К2/К3",
    category="fire_safety",
)

# ============================================================================
# КЛИМАТ И ГРУНТ
# ============================================================================

SP_131 = Regulation(
    code="СП 131.13330.2020",
    title="Строительная климатология",
    edition="2020 + Изм.№2 (2024)",
    in_force_from="2021-06-25",
    url_official="https://docs.cntd.ru/document/573659358",
    scope="Температуры наиболее холодной пятидневки, средняя годовая температура, осадки, ветер",
    category="climate",
)

SP_25 = Regulation(
    code="СП 25.13330.2020",
    title="Основания и фундаменты на вечномёрзлых грунтах",
    edition="2020",
    in_force_from="2020-12-29",
    url_official="https://docs.cntd.ru/document/566431764",
    scope="Промерзание грунта, глубина заложения труб в северных регионах",
    category="climate",
)

# ============================================================================
# ПРОЧНОСТЬ И КОНСТРУКЦИИ
# ============================================================================

SP_20 = Regulation(
    code="СП 20.13330.2016",
    title="Нагрузки и воздействия",
    edition="2016 + Изм.№4 (2024)",
    in_force_from="2017-06-04",
    url_official="https://docs.cntd.ru/document/456044318",
    scope="Снеговые, ветровые, грунтовые нагрузки, расчёт павильонов и крышек КНС",
    category="structural",
)

SP_14 = Regulation(
    code="СП 14.13330.2018",
    title="Строительство в сейсмических районах",
    edition="2018 (с изм.) + ОСР-2015 (карты сейсмического районирования)",
    in_force_from="2018-11-25",
    url_official="https://docs.cntd.ru/document/551989895",
    scope="Сейсмичность площадки, повышающие коэффициенты для оборудования",
    category="structural",
)

SP_49 = Regulation(
    code="СП 49.13330.2010",
    title="Безопасность труда в строительстве. Часть 1. Общие требования",
    edition="2010 (актуализированная редакция СНиП 12-03-2001) + изменения",
    in_force_from="2011-05-20",
    url_official="https://docs.cntd.ru/document/1200084098",
    scope="Лестницы, переходные площадки, ограждения внутри КНС/ВНС",
    category="occupational_safety",
)
# Deprecated alias — старая отменённая ссылка СП 12-104-2002.
SP_12_04 = SP_49

# ============================================================================
# ТЕХНИЧЕСКИЕ РЕГЛАМЕНТЫ ТАМОЖЕННОГО СОЮЗА
# ============================================================================

TR_TS_010 = Regulation(
    code="ТР ТС 010/2011",
    title="О безопасности машин и оборудования",
    edition="2011 + изм. 2014, 2016, 2020",
    in_force_from="2013-02-15",
    url_official="https://docs.cntd.ru/document/902320560",
    scope="Сертификация насосов, шкафов, КНС как готового оборудования (ЕАС-маркировка)",
    category="tech_regulation",
)

TR_TS_012 = Regulation(
    code="ТР ТС 012/2011",
    title="О безопасности оборудования для работы во взрывоопасных средах",
    edition="2011",
    in_force_from="2013-02-15",
    url_official="https://docs.cntd.ru/document/902320559",
    scope="Взрывозащищённое исполнение (ATEX/IECEx) — IIB-T3, II-T4 для нефтехимии",
    category="tech_regulation",
)

TR_TS_020 = Regulation(
    code="ТР ТС 020/2011",
    title="Электромагнитная совместимость технических средств",
    edition="2011",
    in_force_from="2013-02-15",
    url_official="https://docs.cntd.ru/document/902320551",
    scope="ЭМС шкафов автоматики, частотных преобразователей",
    category="tech_regulation",
)

TR_TS_004 = Regulation(
    code="ТР ТС 004/2011",
    title="О безопасности низковольтного оборудования",
    edition="2011",
    in_force_from="2013-02-15",
    url_official="https://docs.cntd.ru/document/902320551",
    scope="Шкафы управления, эл/двигатели до 1 кВ",
    category="tech_regulation",
)

# ============================================================================
# ЭЛЕКТРИКА
# ============================================================================

PUE_7 = Regulation(
    code="ПУЭ 7-е изд.",
    title="Правила устройства электроустановок",
    edition="7-е издание (с изм. до 2024)",
    in_force_from="2003-01-01",
    url_official="https://docs.cntd.ru/document/1200003114",
    scope="Заземление, защита от КЗ, выбор сечения кабелей, классы взрывозащиты",
    category="electrical",
)

GOST_R_50571 = Regulation(
    code="ГОСТ Р 50571.x",
    title="Электроустановки низковольтные (серия)",
    edition="разные годы по частям",
    in_force_from="изд. с 1994",
    url_official="https://docs.cntd.ru/",
    scope="Защита от поражения током, селективность защит, тип системы заземления (TN-C/TN-S/TT)",
    category="electrical",
)

# ============================================================================
# ИСПЫТАНИЯ И КАЧЕСТВО НАСОСОВ
# ============================================================================

GOST_6134 = Regulation(
    code="ГОСТ 6134-2007 / ISO 9906:2012",
    title="Насосы динамические. Методы испытаний",
    edition="ГОСТ 6134-2007 (ISO 9906:2012 IDT)",
    in_force_from="2009-01-01",
    url_official="https://docs.cntd.ru/document/1200071822",
    scope="Снятие Q-H характеристик, NPSH, КПД, классы 1U/2U/3B точности",
    category="tech_regulation",
)

ISO_9906 = Regulation(
    code="ISO 9906:2012",
    title="Rotodynamic pumps — Hydraulic performance acceptance tests — Grades 1, 2 and 3",
    edition="2012 (текущая)",
    in_force_from="2012-05-15",
    url_official="https://www.iso.org/standard/41202.html",
    scope="Международный стандарт испытаний насосов (используется производителями для паспортов)",
    category="tech_regulation",
)

IEC_60034 = Regulation(
    code="IEC 60034-1 / ГОСТ IEC 60034-1-2014",
    title="Машины электрические вращающиеся. Номинальные данные и характеристики",
    edition="ГОСТ 2014, IEC 2017",
    in_force_from="2016-01-01",
    url_official="https://docs.cntd.ru/document/1200115700",
    scope="Тепловые классы изоляции (B/F/H), режимы работы S1-S10, КПД IE2/IE3/IE4",
    category="tech_regulation",
)

# ============================================================================
# КАЧЕСТВО ВОДЫ И СТОКОВ
# ============================================================================

SANPIN_2_1_3684 = Regulation(
    code="СанПиН 2.1.3684-21",
    title="Санитарно-эпидемиологические требования к содержанию территорий, водоснабжению",
    edition="2021 (заменил СанПиН 2.1.4.1074-01)",
    in_force_from="2021-03-01",
    url_official="https://docs.cntd.ru/document/573536177",
    scope="Качество питьевой воды, защита источников",
    category="sanitary",
)
# Deprecated alias — старое имя ссылалось на отменённый СанПиН 2.1.4.1074-01.
SANPIN_2_1_4 = SANPIN_2_1_3684

PP_728 = Regulation(
    code="ПП РФ № 728",
    title="Об утверждении Правил холодного водоснабжения и водоотведения",
    edition="29.07.2013 + изм. до 2024",
    in_force_from="2013-08-09",
    url_official="https://docs.cntd.ru/document/499038947",
    scope="Нормативы сброса стоков в централизованные системы, штрафы за превышение",
    category="sanitary",
)

PP_644 = Regulation(
    code="ПП РФ № 644",
    title="Правила холодного водоснабжения и водоотведения",
    edition="29.07.2013 (актуально на 2024)",
    in_force_from="2013-09-14",
    url_official="https://docs.cntd.ru/document/499040180",
    scope="Договорные отношения с водоканалом, плата за сверхнормативный сброс",
    category="sanitary",
)

PRIKAZ_MSH_552 = Regulation(
    code="Приказ Минсельхоза РФ № 552",
    title="Об утверждении нормативов качества воды водных объектов рыбохозяйственного значения",
    edition="13.12.2016",
    in_force_from="2017-01-01",
    url_official="https://docs.cntd.ru/document/420389120",
    scope="ПДК для сброса в рыбохозяйственные водоёмы (более жёсткие, чем хозбытовые)",
    category="sanitary",
)

# ============================================================================
# СВОДНЫЙ РЕЕСТР
# ============================================================================

ALL_REGULATIONS: dict[str, Regulation] = {
    # Канализация и водоснабжение
    "SP_32": SP_32,
    "SP_32_2012": SP_32_2012,
    "SP_30": SP_30,
    "SP_31": SP_31,
    "SP_399": SP_399,
    # Пожарка
    "SP_8_13130": SP_8_13130,
    "SP_10_13130": SP_10_13130,
    "SP_485": SP_485,
    "SP_5_13130": SP_485,  # deprecated alias
    "FZ_123": FZ_123,
    # Климат
    "SP_131": SP_131,
    "SP_25": SP_25,
    # Прочность
    "SP_20": SP_20,
    "SP_14": SP_14,
    "SP_49": SP_49,
    "SP_12_04": SP_49,  # deprecated alias
    # ТР ТС
    "TR_TS_010": TR_TS_010,
    "TR_TS_012": TR_TS_012,
    "TR_TS_020": TR_TS_020,
    "TR_TS_004": TR_TS_004,
    # Электрика
    "PUE_7": PUE_7,
    "GOST_R_50571": GOST_R_50571,
    # Насосы
    "GOST_6134": GOST_6134,
    "ISO_9906": ISO_9906,
    "IEC_60034": IEC_60034,
    # Санитария
    "SANPIN_2_1_3684": SANPIN_2_1_3684,
    "SANPIN_2_1_4": SANPIN_2_1_3684,  # deprecated alias
    "PP_728": PP_728,
    "PP_644": PP_644,
    "PRIKAZ_MSH_552": PRIKAZ_MSH_552,
}


@dataclass(frozen=True)
class RegulationReference:
    """Ссылка на конкретный пункт норматива в результате расчёта.

    Используется в API: `references: list[RegulationReference]` в каждом ответе.
    Frontend показывает в режиме энциклопедии: «Q_r формула 8 СП 32 §6.2.4 → текст»
    """

    regulation_code: str         # "СП 32.13330.2018"
    section: str                 # "§6.2.4 формула 8"
    purpose: str                 # "Расчёт пикового расхода ливневой канализации"
    quote: str = ""              # Опционально — дословная цитата из норматива
    url: str = ""                # Прямая ссылка на пункт (если есть)


def ref(reg_key: str, section: str, purpose: str, quote: str = "") -> RegulationReference:
    """Удобный конструктор RegulationReference.

    Использование в модулях:
        from .regulations import ref
        notes_refs = [
            ref("SP_8_13130", "§6.3 табл. 1", "Расход на наружное пожаротушение"),
            ref("FZ_123", "ст. 32", "Категория здания по пожарной опасности"),
        ]
    """
    if reg_key not in ALL_REGULATIONS:
        raise KeyError(f"Unknown regulation key: {reg_key}. Add it to regulations.py")
    reg = ALL_REGULATIONS[reg_key]
    return RegulationReference(
        regulation_code=reg.code,
        section=section,
        purpose=purpose,
        quote=quote,
        url=reg.url_official,
    )


def list_regulations_by_category(category: str) -> list[Regulation]:
    """Возвращает все нормативы категории (для UI-энциклопедии)."""
    return [r for r in ALL_REGULATIONS.values() if r.category == category]


def get_regulation(code_or_key: str) -> Regulation | None:
    """Поиск норматива по коду (СП 32.13330.2018) или ключу (SP_32)."""
    if code_or_key in ALL_REGULATIONS:
        return ALL_REGULATIONS[code_or_key]
    for reg in ALL_REGULATIONS.values():
        if reg.code == code_or_key:
            return reg
    return None
