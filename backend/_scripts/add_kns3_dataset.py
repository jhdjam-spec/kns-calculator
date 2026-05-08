"""Добавить 8 насосов + 6 корпусов + 3 шкафа из kns3.zip в БД калькулятора.

Источник: 00_research/kns3_dataset_2026-05-08/kns3_audit_report.md
        + memory reference_kns3_zip_2026-05-08_audit.md

Все записи помечены _engineer_flag=needs_review и _source=kns3.zip — ждут
ручную верификацию по PDF после первичной интеграции.
"""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DS = ROOT / "02_dataset"

# ────────────────────────────────────────────────────────── PUMPS ──

NEW_PUMPS: list[dict] = [
    {
        "id": "cnp-80wq40-12-3qg",
        "brand": "CNP",
        "model": "80WQ40-12-3QG",
        "type": "submersible_sewage",
        "impeller": "vortex",
        "free_passage_mm": 60,
        "envelope": {
            "Q_min_m3h": 25,
            "Q_max_m3h": 60,
            "H_min_m": 8,
            "H_max_m": 16,
            "Q_BEP_m3h": 40,
            "H_BEP_m": 12,
            "eta_BEP_pct": 55.0,
            "NPSHr_at_BEP_m": None,
        },
        "power": {"P_kW": 3.0, "voltage_v": 380, "phase": 3, "ip_rating": "IP68"},
        "discharge": {"DN_mm": 80, "mating_method": "quick_coupling"},
        "wastewater_compat": ["domestic", "drainage"],
        "price_segment": "budget",
        "available_ru": {"status": "imported_china", "distributor": "Аркада"},
        "_engineer_flag": "needs_review",
        "_engineer_note": "Найдено в КП #28052025_1 ООО «Серво-Полимер» — наша КНС D1600 H8500 для Симферополя. Q=40 H=12 P=3кВт DN80 муфта QG. Эталон собственной сделки.",
        "_source": "kns3.zip / KP_28052025.txt",
        "_added": "2026-05-08",
    },
    {
        "id": "masdaf-nmm-100-160",
        "brand": "MAS DAF",
        "model": "NMM 100-160",
        "type": "booster_station",
        "impeller": "centrifugal_closed",
        "free_passage_mm": None,
        "envelope": {
            "Q_min_m3h": 240,
            "Q_max_m3h": 356,
            "H_min_m": 21.6,
            "H_max_m": 41.8,
            "Q_BEP_m3h": 300,
            "H_BEP_m": 32,
            "eta_BEP_pct": 75.0,
            "NPSHr_at_BEP_m": None,
        },
        "power": {"P_kW": 27.9, "voltage_v": 380, "phase": 3, "ip_rating": "IP55"},
        "discharge": {"DN_mm": 100},
        "wastewater_compat": ["clean_water"],
        "price_segment": "standard",
        "available_ru": {
            "status": "imported_turkey",
            "distributor": "MAS DAF (Турция) — официальный дилер РФ",
        },
        "_engineer_flag": "needs_review",
        "_engineer_note": "End Suction Monoblock — НОВЫЙ для нас турецкий бренд. Проверить по паспорту — кривая Q-H, NPSHr, точные точки BEP.",
        "_source": "kns3.zip / архив с TANECO либо ПГК Татьянка",
        "_added": "2026-05-08",
    },
    {
        "id": "shtorm-nes-100-80-260-75-2",
        "brand": "Шторм Ф",
        "model": "NES 100-80-260-75-2",
        "type": "booster_station",
        "impeller": "centrifugal_closed",
        "free_passage_mm": None,
        "envelope": {
            "Q_min_m3h": 100,
            "Q_max_m3h": 200,
            "H_min_m": 60,
            "H_max_m": 100,
            "Q_BEP_m3h": 150,
            "H_BEP_m": 80,
            "eta_BEP_pct": 70.0,
            "NPSHr_at_BEP_m": None,
        },
        "power": {"P_kW": 75.0, "voltage_v": 380, "phase": 3, "ip_rating": "IP54"},
        "discharge": {"DN_mm": 80},
        "wastewater_compat": ["clean_water"],
        "price_segment": "standard",
        "available_ru": {
            "status": "domestic_manufacturer",
            "distributor": "ООО «Шторм Ф» (РФ)",
        },
        "_engineer_flag": "needs_review",
        "_engineer_note": "ПНС повышения давления, комплектный блок. Цена/конкретика не указаны в массиве — ждём паспорт.",
        "_source": "kns3.zip",
        "_added": "2026-05-08",
    },
    {
        "id": "grundfos-cdm-10-11",
        "brand": "Grundfos",
        "model": "CDM 10-11",
        "type": "booster_station",
        "impeller": "centrifugal_closed",
        "free_passage_mm": None,
        "envelope": {
            "Q_min_m3h": 4,
            "Q_max_m3h": 14,
            "H_min_m": 15,
            "H_max_m": 65,
            "Q_BEP_m3h": 10,
            "H_BEP_m": 30,
            "eta_BEP_pct": 60.0,
            "NPSHr_at_BEP_m": None,
        },
        "power": {"P_kW": 1.5, "voltage_v": 380, "phase": 3, "ip_rating": "IP55"},
        "discharge": {"DN_mm": 32},
        "wastewater_compat": ["clean_water", "fire_protection"],
        "price_segment": "premium",
        "available_ru": {
            "status": "imported_eu",
            "distributor": "Grundfos РФ (через дилеров)",
        },
        "_engineer_flag": "needs_review",
        "_engineer_note": "Жокей-насос для пожарной СПД. Точные параметры P_kW требуют сверки по паспорту — оценочно 1.5 кВт.",
        "_source": "kns3.zip",
        "_added": "2026-05-08",
    },
    {
        "id": "grundfos-unilift-ap12-40-06-1",
        "brand": "Grundfos",
        "model": "Unilift AP12.40.06.1",
        "type": "submersible_sewage",
        "impeller": "vortex",
        "free_passage_mm": 35,
        "envelope": {
            "Q_min_m3h": 0.5,
            "Q_max_m3h": 5,
            "H_min_m": 1,
            "H_max_m": 10,
            "Q_BEP_m3h": 3.2,
            "H_BEP_m": 7.8,
            "eta_BEP_pct": 45.0,
            "NPSHr_at_BEP_m": None,
        },
        "power": {"P_kW": 0.6, "voltage_v": 220, "phase": 1, "ip_rating": "IP68"},
        "discharge": {"DN_mm": 40},
        "wastewater_compat": ["domestic", "drainage"],
        "price_segment": "premium",
        "available_ru": {
            "status": "imported_eu",
            "distributor": "Grundfos РФ",
        },
        "_engineer_flag": "needs_review",
        "_engineer_note": "Маломощный погружной для бытового применения. Однофазный 220В. Free passage 35 мм — ограниченное применение.",
        "_source": "kns3.zip",
        "_added": "2026-05-08",
    },
    {
        "id": "gis-sg-40-075-25-0d",
        "brand": "ГИС",
        "model": "SG.40.075.2.5.0D",
        "type": "submersible_sewage",
        "impeller": "channel",
        "free_passage_mm": 40,
        "envelope": {
            "Q_min_m3h": 2,
            "Q_max_m3h": 10,
            "H_min_m": 5,
            "H_max_m": 15,
            "Q_BEP_m3h": 6,
            "H_BEP_m": 9.13,
            "eta_BEP_pct": 50.0,
            "NPSHr_at_BEP_m": None,
        },
        "power": {"P_kW": 0.75, "voltage_v": 380, "phase": 3, "ip_rating": "IP68"},
        "discharge": {"DN_mm": 40},
        "wastewater_compat": ["domestic"],
        "price_segment": "standard",
        "available_ru": {
            "status": "domestic_manufacturer",
            "distributor": "ООО «ГИС» (Симферополь)",
        },
        "_engineer_flag": "needs_review",
        "_engineer_note": "Используется в КНС ГИС ЭКОВЭЛЛ (ж/б футерованных). Малая КНС бытового применения. Точные характеристики уточнить по PDF КНС-6,9.13.",
        "_source": "kns3.zip / GIS-KNS-6-9,13-2-02072025-1",
        "_added": "2026-05-08",
    },
    {
        "id": "fancy-350wq1400-75-6",
        "brand": "Fancy",
        "model": "350WQ1400-75-6",
        "type": "submersible_sewage",
        "impeller": "channel",
        "free_passage_mm": 100,
        "envelope": {
            "Q_min_m3h": 800,
            "Q_max_m3h": 1800,
            "H_min_m": 50,
            "H_max_m": 90,
            "Q_BEP_m3h": 1400,
            "H_BEP_m": 75,
            "eta_BEP_pct": 75.0,
            "NPSHr_at_BEP_m": None,
        },
        "power": {"P_kW": 350.0, "voltage_v": 380, "phase": 3, "ip_rating": "IP68"},
        "discharge": {"DN_mm": 350},
        "wastewater_compat": ["domestic", "industrial"],
        "price_segment": "budget",
        "available_ru": {
            "status": "imported_china",
            "distributor": "ГК ГЕОН (Н.Новгород)",
        },
        "_engineer_flag": "needs_review",
        "_engineer_note": "Найдено в ГЕОН ВКНС-СП-1159 (Q=1159 м³/ч). Очень крупный насос — DN350. Power 350 кВт. Проверить по паспорту, оценка по табличному обозначению.",
        "_source": "kns3.zip / GEON_VKNS_SP_1159",
        "_added": "2026-05-08",
    },
    {
        "id": "fgpu-120-16",
        "brand": "ФГПУ",
        "model": "ФГПУ 120/16",
        "type": "vertical_dry_well",
        "impeller": "channel",
        "free_passage_mm": 80,
        "envelope": {
            "Q_min_m3h": 60,
            "Q_max_m3h": 180,
            "H_min_m": 8,
            "H_max_m": 22,
            "Q_BEP_m3h": 120,
            "H_BEP_m": 16,
            "eta_BEP_pct": 65.0,
            "NPSHr_at_BEP_m": None,
        },
        "power": {"P_kW": 7.5, "voltage_v": 380, "phase": 3, "ip_rating": "IP54"},
        "discharge": {"DN_mm": 100},
        "wastewater_compat": ["industrial", "drainage"],
        "price_segment": "standard",
        "available_ru": {
            "status": "domestic_manufacturer",
            "distributor": "Завод ФГПУ (РФ)",
        },
        "_engineer_flag": "needs_review",
        "_engineer_note": "Российский ПОЛУПОГРУЖНОЙ насос (новый тип `vertical_dry_well` для нашей БД — отличается от submersible тем что мотор сухой над уровнем стоков). Применён в АО «ПГК» Татьянка для песколовушек. Q=120 H=16.",
        "_source": "kns3.zip / 1294907_PGK_2025",
        "_added": "2026-05-08",
    },
    {
        "id": "kaiquan-wq2290-6155-300",
        "brand": "KAIQUAN",
        "model": "WQ2290-6155-300",
        "type": "submersible_sewage",
        "impeller": "channel",
        "free_passage_mm": 120,
        "envelope": {
            "Q_min_m3h": 400,
            "Q_max_m3h": 900,
            "H_min_m": 4,
            "H_max_m": 10,
            "Q_BEP_m3h": 650,
            "H_BEP_m": 7,
            "eta_BEP_pct": 70.0,
            "NPSHr_at_BEP_m": None,
        },
        "power": {"P_kW": 14.5, "voltage_v": 380, "phase": 3, "ip_rating": "IP68"},
        "discharge": {"DN_mm": 300},
        "wastewater_compat": ["domestic", "drainage", "industrial"],
        "price_segment": "budget",
        "available_ru": {
            "status": "imported_china",
            "distributor": "Аркада",
        },
        "_engineer_flag": "needs_review",
        "_engineer_note": "Новый размер DN300 от KAIQUAN. Отличается от существующего kaiquan-wq2290-2136-80 (DN80). Подозрение что у нас в БД был оптимизирован под другую сделку — этот для большой ливневки/дренажа.",
        "_source": "kns3.zip",
        "_added": "2026-05-08",
    },
]

# ────────────────────────────────────────────────────────── CORPORA ──

NEW_CORPORA: list[dict] = [
    {
        "id": "geon-vkns-sp-1159",
        "brand": "ГК ГЕОН",
        "model": "ВКНС-СП-1159",
        "type": "submersible_sewage_station_underground",
        "corpus_material": "стеклопластик",
        "D_mm": 3600,
        "H_mm": 10600,
        "L_mm": None,
        "anchor_plate_D_mm": 4200,
        "Q_m3h_typical": 1159,
        "H_m_typical": 11,
        "configuration": "2+1_redundant",
        "PN": None,
        "wall_thickness_min_mm": None,
        "includes": [
            "Корпус стеклопластиковый D3600 H10600",
            "Анкерная плита D4200",
            "2 насоса Fancy 350WQ1400-75 + 1 резерв",
            "Затворы DN350",
            "Обратные клапаны",
            "Цепи нерж. сталь 316",
            "Шкаф управления",
        ],
        "price_rub_2026": None,
        "price_segment": "premium",
        "manufacturer_url": "https://geongroup.ru",
        "manufacturer_region": "Н.Новгород",
        "_engineer_flag": "needs_review",
        "_engineer_note": "ГК ГЕОН — 13 лет на рынке, заказчики OZON/Wildberries. Один из 4 ТКП по объекту 'ООО Центральный Маркет'. Цена не указана в кп, нужен запрос.",
        "_source": "kns3.zip / GEON_VKNS_SP_1159",
        "_added": "2026-05-08",
    },
    {
        "id": "neowater-kns-dryroom-medium",
        "brand": "Нео Дрейн / Neo Water",
        "model": "КНС с сухой камерой 250 м³",
        "type": "submersible_sewage_station_dry_well",
        "corpus_material": "стеклопластик",
        "D_mm": 2400,
        "H_mm": 6000,
        "L_mm": None,
        "anchor_plate_D_mm": 2800,
        "Q_m3h_typical": 100,
        "H_m_typical": 20,
        "configuration": "1+1+1_warehouse",
        "PN": None,
        "wall_thickness_min_mm": 12,
        "includes": [
            "Стеклопластиковый корпус с сухой камерой",
            "Лотки серий NEO-TOP/NORMAL/PLUS/MASSIVE A15-F900",
            "Резервуары до 250 м³",
            "Насосы по подбору",
        ],
        "price_rub_2026": None,
        "price_segment": "standard",
        "manufacturer_url": "https://neowater.ru",
        "manufacturer_region": "Пересвет МО",
        "_engineer_flag": "needs_review",
        "_engineer_note": "Полный завод 2000 кв.м в Пересвете. Делают и КНС с сухой камерой и лотки DN90-500 (NEO-TOP/NORMAL/PLUS/MASSIVE) и резервуары до 250 м³. Реальные размеры/цены требуют запроса по объекту.",
        "_source": "kns3.zip / Catalog_NeoWater + Catalog_NeoDrain",
        "_added": "2026-05-08",
    },
    {
        "id": "bioproject-kns-typical",
        "brand": "ООО «БиоПроект»",
        "model": "КНС типовая",
        "type": "submersible_sewage_station_underground",
        "corpus_material": "стеклопластик",
        "D_mm": 2000,
        "H_mm": 5000,
        "L_mm": None,
        "anchor_plate_D_mm": 2400,
        "Q_m3h_typical": 50,
        "H_m_typical": 15,
        "configuration": "1+1+1_warehouse",
        "PN": None,
        "wall_thickness_min_mm": 10,
        "includes": [
            "Стеклопластиковый корпус",
            "КНС/ЛОС/КОС/ёмкости в одном производителе",
        ],
        "price_rub_2026": None,
        "price_segment": "premium",
        "manufacturer_url": None,
        "manufacturer_region": "Пересвет МО",
        "_engineer_flag": "needs_review",
        "_engineer_note": "С 2018 года. Премиум-заказчики: РЖД, Минобороны, Росавтодор, Металлоинвест, Мосводоканал, ГК ЕКС. Конкурент-эталон по премиум-сегменту.",
        "_source": "kns3.zip / BioProekt_present",
        "_added": "2026-05-08",
    },
    {
        "id": "gis-ekovell-kns-6-913",
        "brand": "ООО «ГИС»",
        "model": "ЭКОВЭЛЛ КНС-6-9.13",
        "type": "submersible_sewage_station_underground",
        "corpus_material": "concrete_lined",
        "D_mm": 1500,
        "H_mm": 4000,
        "L_mm": None,
        "anchor_plate_D_mm": None,
        "Q_m3h_typical": 6,
        "H_m_typical": 9.13,
        "configuration": "1+1_redundant",
        "PN": None,
        "wall_thickness_min_mm": None,
        "includes": [
            "Ж/б корпус с футеровкой ТУ 23.61.12-001-23107031-2017",
            "Газоанализатор Хоббит-Т",
            "ШУ ГИС ШУ1",
            "Насос ГИС SG.40.075.2.5.0D",
        ],
        "price_rub_2026": None,
        "price_segment": "standard",
        "manufacturer_url": None,
        "manufacturer_region": "Симферополь, Крым",
        "_engineer_flag": "needs_review",
        "_engineer_note": "УНИКАЛЬНАЯ технология — ж/б футерованные КНС (отличаются от стеклопластика и полимера). НОВЫЙ corpus_material='concrete_lined' добавлен. ТУ 23.61.12-001-23107031-2017.",
        "_source": "kns3.zip / GIS-KNS-6-9,13-2-02072025-1",
        "_added": "2026-05-08",
    },
    {
        "id": "kit-minteko-sbo-30",
        "brand": "КИТ ПРО / ГК Минтеко",
        "model": "СБО-30",
        "type": "biological_treatment_unit",
        "corpus_material": "полипропилен",
        "D_mm": 2000,
        "H_mm": 4500,
        "L_mm": None,
        "anchor_plate_D_mm": 2300,
        "Q_m3h_typical": 5.4,
        "H_m_typical": None,
        "configuration": "lOS_30_users",
        "PN": None,
        "wall_thickness_min_mm": None,
        "includes": [
            "Биологическая очистка СБО 4-30 чел",
            "5 типоразмерных линеек",
            "Дилерские скидки 30/35/40%",
        ],
        "price_rub_2026": 432000,
        "price_segment": "budget",
        "manufacturer_url": "https://kits.minteko.ru",
        "manufacturer_region": "РФ",
        "_engineer_flag": "needs_review",
        "_engineer_note": "Полный прайс. 5 линеек: 108-432 тыс ₽ (СБО-4 → СБО-30). Конкурент PEGAS Lite. Дилерские: -30/35/40%. Загрузить в pricing_segments как референс.",
        "_source": "kns3.zip / KIT_septik prices",
        "_added": "2026-05-08",
    },
    {
        "id": "aliva-kns-6-complex",
        "brand": "АЛИВА",
        "model": "АЛИВА-КНС-6 (комплекс из 4 модулей)",
        "type": "submersible_sewage_station_underground",
        "corpus_material": "стеклопластик",
        "D_mm": 2400,
        "H_mm": 5500,
        "L_mm": None,
        "anchor_plate_D_mm": 2800,
        "Q_m3h_typical": 60,
        "H_m_typical": 15,
        "configuration": "1+1_redundant",
        "PN": None,
        "wall_thickness_min_mm": None,
        "includes": [
            "АЛИВА-СЕ1.520131 (септик)",
            "АЛИВА-НЕ-10 (насосный модуль)",
            "АЛИВА-СС-35.3 (стабилизатор)",
            "АЛИВА-КНС-6 (КНС)",
        ],
        "price_rub_2026": None,
        "price_segment": "standard",
        "manufacturer_url": None,
        "manufacturer_region": "РФ",
        "_engineer_flag": "needs_review",
        "_engineer_note": "Комплекс из 4 модулей — септик + насосный модуль + стабилизатор + КНС. Полная схема локальной канализации.",
        "_source": "kns3.zip",
        "_added": "2026-05-08",
    },
]

# ────────────────────────────────────────── CONTROL PANELS ──

# Загрузим текущие панели, добавим новые
NEW_PANELS: list[dict] = [
    {
        "id": "runline-iskra-lite-2pump",
        "brand": "Runline",
        "model": "ШУ КНС с ПЛК «Искра lite»",
        "category": "with_scada",
        "pumps_supported": 2,
        "voltage_v": 380,
        "power_per_pump_kw_min": 0.7,
        "power_per_pump_kw_max": 11.0,
        "phase": 3,
        "ip_rating": "IP65",
        "communication": ["RS-485", "Runline_SCADA", "mobile_app", "radio"],
        "modbus_rtu": True,
        "modbus_tcp": False,
        "gsm_sms": False,
        "remote_access": True,
        "level_sensors_supported": ["floats_x5", "hydrostatic"],
        "protections": [
            "phase_loss",
            "phase_skew",
            "voltage_surge",
            "overload",
            "short_circuit",
        ],
        "voltage_220v_option": True,
        "manufacturer_url": "runline.ru",
        "manufacturer_region": "РФ",
        "manufacturer_age_years": 21,
        "manufacturer_defect_rate_pct": 0.01,
        "deployment_geography": "РФ + СНГ + дальнее зарубежье",
        "deployment_count": 2000,
        "price_rub_2026": None,
        "_engineer_flag": "needs_review",
        "_engineer_note": "ГЛАВНЫЙ артефакт диспетчеризации после Aikon ЩУН. SCADA через RS-485+радио, мобильное/ПК. Поддержка 0.7-11 кВт. 5 поплавков либо гидростат. Применение по всей РФ + ближнее/дальнее зарубежье. 21 год на рынке, 2000+ объектов, брак 0.01%. Запросить прайс отдельно.",
        "_source": "kns3.zip / Shkaf_Runline.pdf (top-level 2.4 МБ)",
        "_added": "2026-05-08",
    },
    {
        "id": "estl-eclmini-380-15-18-s1n",
        "brand": "ESTL-Control",
        "model": "ECLmini -380[15-18]-S1N-NNN1",
        "category": "level_based",
        "pumps_supported": 2,
        "voltage_v": 380,
        "power_per_pump_kw_min": 4.0,
        "power_per_pump_kw_max": 11.0,
        "phase": 3,
        "ip_rating": "IP65",
        "communication": ["4-20mA"],
        "modbus_rtu": False,
        "modbus_tcp": False,
        "gsm_sms": False,
        "remote_access": False,
        "level_sensors_supported": [
            "ultrasonic_il-ec-a_0-15m",
            "floats",
        ],
        "protections": [
            "overload",
            "short_circuit",
            "phase_loss",
        ],
        "voltage_220v_option": False,
        "manufacturer_url": None,
        "manufacturer_region": "РФ",
        "manufacturer_age_years": None,
        "manufacturer_defect_rate_pct": None,
        "deployment_geography": "РФ",
        "deployment_count": None,
        "price_rub_2026": None,
        "_engineer_flag": "needs_review",
        "_engineer_note": "Двухнасосный с ультразвуковым уровнемером IL-EC-A 0-15м, 4-20 мА. Использован в АО ПГК Татьянка. Также есть -380[7-10]-K2N-NNNN (однонасосный).",
        "_source": "kns3.zip / 1294907_PGK_2025",
        "_added": "2026-05-08",
    },
    {
        "id": "gis-shu1-2pump-naruzhnyi",
        "brand": "ГИС",
        "model": "ШУ1 (1р/1р, наружный)",
        "category": "level_based",
        "pumps_supported": 2,
        "voltage_v": 380,
        "power_per_pump_kw_min": 0.55,
        "power_per_pump_kw_max": 5.5,
        "phase": 3,
        "ip_rating": "IP54",
        "communication": [],
        "modbus_rtu": False,
        "modbus_tcp": False,
        "gsm_sms": False,
        "remote_access": False,
        "level_sensors_supported": ["floats"],
        "protections": [
            "AVR",
            "light_sound_alarm",
            "overload",
            "short_circuit",
        ],
        "voltage_220v_option": False,
        "manufacturer_url": None,
        "manufacturer_region": "Симферополь, Крым",
        "manufacturer_age_years": None,
        "manufacturer_defect_rate_pct": None,
        "deployment_geography": "Крым",
        "deployment_count": None,
        "price_rub_2026": None,
        "_engineer_flag": "needs_review",
        "_engineer_note": "Простой шкаф для КНС ГИС ЭКОВЭЛЛ. Без удалённой связи. Поплавки + АВР + светозвуковая сигнализация.",
        "_source": "kns3.zip / GIS-KNS-6-9,13-2-02072025-1",
        "_added": "2026-05-08",
    },
]


def update_pumps(dry_run: bool = False) -> int:
    """Добавить NEW_PUMPS к pumps.json, не дублируя по id."""
    path = DS / "pumps" / "pumps.json"
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    existing_ids = {p["id"] for p in data["pumps"]}
    added = 0
    for p in NEW_PUMPS:
        if p["id"] in existing_ids:
            print(f"  SKIP duplicate: {p['id']}")
            continue
        data["pumps"].append(p)
        added += 1
    data["_updated"] = "2026-05-08"
    if not dry_run:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    print(f"pumps.json: +{added} (now {len(data['pumps'])} total)")
    return added


def update_corpora(dry_run: bool = False) -> int:
    path = DS / "corpora" / "corpora.json"
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    existing_ids = {c["id"] for c in data["corpora"]}
    added = 0
    for c in NEW_CORPORA:
        if c["id"] in existing_ids:
            print(f"  SKIP duplicate: {c['id']}")
            continue
        data["corpora"].append(c)
        added += 1
    data["_updated"] = "2026-05-08"
    if not dry_run:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    print(f"corpora.json: +{added} (now {len(data['corpora'])} total)")
    return added


def update_panels(dry_run: bool = False) -> int:
    # Один производитель = один файл (как в corpora/pegas_engineering.json).
    # Существующий aikon_shun.json не трогаем.

    # Runline
    runline_path = DS / "control_panels" / "runline.json"
    runline_data = {
        "_version": "0.1",
        "_updated": "2026-05-08",
        "_description": "Runline — шкафы управления КНС с ПЛК Искра lite + SCADA. РФ, 21 год на рынке.",
        "_source": "kns3.zip / Shkaf_Runline.pdf",
        "panels": [NEW_PANELS[0]],
    }
    estl_path = DS / "control_panels" / "estl_control.json"
    estl_data = {
        "_version": "0.1",
        "_updated": "2026-05-08",
        "_description": "ESTL-Control ECLmini — двухнасосные/однонасосные шкафы по уровнемеру 4-20мА.",
        "_source": "kns3.zip / 1294907_PGK_2025",
        "panels": [NEW_PANELS[1]],
    }
    gis_path = DS / "control_panels" / "gis_shu1.json"
    gis_data = {
        "_version": "0.1",
        "_updated": "2026-05-08",
        "_description": "ГИС ШУ1 — простой шкаф для КНС ЭКОВЭЛЛ, поплавки+АВР+светозвук.",
        "_source": "kns3.zip / GIS_KNS_2025",
        "panels": [NEW_PANELS[2]],
    }
    if not dry_run:
        for path_, data_ in [
            (runline_path, runline_data),
            (estl_path, estl_data),
            (gis_path, gis_data),
        ]:
            with open(path_, "w", encoding="utf-8") as f:
                json.dump(data_, f, ensure_ascii=False, indent=2)
            print(f"  + {path_.name}")
    print("control_panels: +3 файла (runline.json, estl_control.json, gis_shu1.json)")
    return 3


def main(dry_run: bool = False):
    print(f"Working dir: {ROOT}")
    print(f"Dataset: {DS}")
    print()
    p = update_pumps(dry_run=dry_run)
    c = update_corpora(dry_run=dry_run)
    n = update_panels(dry_run=dry_run)
    print()
    print(f"TOTAL: +{p} насосов, +{c} корпусов, +{n} панелей.")
    if dry_run:
        print("DRY RUN — изменений не записано.")


if __name__ == "__main__":
    import sys

    dry = "--dry-run" in sys.argv
    main(dry_run=dry)
