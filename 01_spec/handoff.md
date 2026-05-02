# Hand-off Package для инженера

> Версия 1.0 — 2026-05-02. Автор: sales engineer / док-документооборот.
> Контекст: менеджер сделал первичный подбор по 4 полям (Q, dH, L, тип стоков) и получил топ-3 насоса (бюджет/средний/премиум). Чтобы сделка двинулась — пакет уходит инженеру для уточнённого расчёта.
> Эталоны: `характеристики_КНС.png` (Telegram Desktop), кейс «АртВинд Мысхако» (`АВ.1382.08.23-М-НК.pdf`), КП Аркада 29.01.2026, опросники Иртыш-Омск / TehnoSfera / superkns.

---

## Артефакт 1. PDF опросник клиенту (схема полей)

JSON-схема для генератора PDF (jsPDF / pdfmake / WeasyPrint).
Каждое поле: `id`, `label`, `type`, `unit`, `required`, `autofill_from`, `placeholder`, `validate`, `engineer_only`.

```json
{
  "form_id": "kns_questionnaire_v1",
  "title": "Опросный лист на канализационную насосную станцию (КНС)",
  "subtitle": "Для уточнённого подбора оборудования. Заполнить и подписать.",
  "header": {
    "logo": "servo-yug.png",
    "doc_no": {"id": "doc_no", "label": "№ КП / Заявки", "type": "string", "autofill_from": "L0.calc_id"},
    "date": {"id": "date", "label": "Дата", "type": "date", "autofill_from": "system.today"},
    "manager": {"id": "manager_name", "label": "Менеджер", "type": "string", "autofill_from": "L0.manager.name"},
    "manager_phone": {"id": "manager_phone", "label": "Контакт менеджера", "type": "phone", "autofill_from": "L0.manager.phone"}
  },
  "sections": [
    {
      "id": "s1_object",
      "title": "1. Объект и заказчик",
      "fields": [
        {"id": "object_name", "label": "Название объекта", "type": "string", "required": true, "autofill_from": "L0.client.object"},
        {"id": "object_address", "label": "Адрес / координаты", "type": "string"},
        {"id": "client_company", "label": "Заказчик (юр.лицо)", "type": "string", "autofill_from": "L0.client.company"},
        {"id": "client_contact", "label": "Контактное лицо + телефон", "type": "string", "autofill_from": "L0.client.contact"},
        {"id": "object_type", "label": "Тип объекта", "type": "select", "options": ["Жилой комплекс", "Гостиница / апарт", "Промышленный", "Автомойка", "Объект Минобороны", "Другое"]},
        {"id": "stage", "label": "Стадия проекта", "type": "select", "options": ["Идея/концепция", "ЭП", "ПД", "РД", "Тендер", "Эксплуатация"]}
      ]
    },
    {
      "id": "s2_stoki",
      "title": "2. Параметры стоков",
      "fields": [
        {"id": "stoki_type", "label": "Тип стоков", "type": "select", "required": true, "options": ["Хоз-бытовые", "Дождевые/ливневые", "Производственные", "Смешанные", "Жироуловитель", "Иловые"], "autofill_from": "L0.stoki_type"},
        {"id": "Q_avg_day", "label": "Q среднесуточный", "type": "number", "unit": "м³/сут", "autofill_from": "L0.Q_avg_day"},
        {"id": "Q_peak_h", "label": "Q пиковый", "type": "number", "unit": "м³/ч", "autofill_from": "computed.Q_peak_h"},
        {"id": "K_gen", "label": "Коэффициент неравномерности K_gen.max", "type": "number", "default": 2.5, "autofill_from": "computed.K_gen", "engineer_only": true, "hint": "СП 32.13330 табл. 2"},
        {"id": "salvo_volume", "label": "Залповый объём (если есть)", "type": "number", "unit": "м³"},
        {"id": "T_min", "label": "Температура стоков, мин", "type": "number", "unit": "°C", "default": 8},
        {"id": "T_max", "label": "Температура стоков, макс", "type": "number", "unit": "°C", "default": 30},
        {"id": "abrasive", "label": "Абразивность (песок, окалина)", "type": "select", "options": ["Низкая", "Средняя", "Высокая"]},
        {"id": "fibers", "label": "Длинноволокнистые включения (тряпки/салфетки)", "type": "boolean"},
        {"id": "fats", "label": "Жиры (рестораны, мойки)", "type": "boolean"},
        {"id": "pH", "label": "pH стоков", "type": "number", "default": 7.0, "validate": "1..14"},
        {"id": "density", "label": "Плотность", "type": "number", "unit": "кг/м³", "default": 1000},
        {"id": "free_passage_required", "label": "Требуемый свободный проход", "type": "number", "unit": "мм", "engineer_only": true, "default": 50}
      ]
    },
    {
      "id": "s3_geom",
      "title": "3. Геометрия и трасса",
      "fields": [
        {"id": "dH_geom", "label": "Геодезический перепад dH", "type": "number", "unit": "м", "required": true, "autofill_from": "L0.dH"},
        {"id": "L_press", "label": "Длина напорного трубопровода L", "type": "number", "unit": "м", "required": true, "autofill_from": "L0.L"},
        {"id": "depth_inlet", "label": "Глубина заложения подводящего", "type": "number", "unit": "м", "default": 2.5},
        {"id": "ground_drop", "label": "Перепад от рельефа на трассе", "type": "number", "unit": "м"},
        {"id": "inlet_direction_clock", "label": "Направление подводящего (часы 1..12)", "type": "select", "options": [1,2,3,4,5,6,7,8,9,10,11,12]},
        {"id": "press_direction_clock", "label": "Направление напорного (часы 1..12)", "type": "select", "options": [1,2,3,4,5,6,7,8,9,10,11,12]},
        {"id": "ground_water_level", "label": "Уровень грунтовых вод (УГВ)", "type": "number", "unit": "м от поверхности"},
        {"id": "soil_type", "label": "Тип грунта", "type": "select", "options": ["Песок", "Супесь", "Суглинок", "Глина", "Скала", "Насыпной"]},
        {"id": "seismic", "label": "Сейсмика", "type": "select", "options": ["до 6 баллов", "7", "8", "9+"]},
        {"id": "climate_zone", "label": "Климатический район (СП 131.13330)", "type": "string"}
      ]
    },
    {
      "id": "s4_inlet",
      "title": "4. Подводящий трубопровод",
      "fields": [
        {"id": "inlet_D", "label": "Диаметр D подводящего (DN)", "type": "number", "unit": "мм"},
        {"id": "inlet_material", "label": "Материал", "type": "select", "options": ["Корсис ПЭ", "Гофра ПЭ", "Гладкая ПЭ100", "Чугун", "Сталь", "Керамика", "ВЧШГ"]},
        {"id": "inlet_count", "label": "Количество вводов", "type": "number", "default": 1},
        {"id": "inlet_connection", "label": "Тип соединения", "type": "select", "options": ["Раструб", "Сварка", "Фланец", "Резиновое уплотнение"]},
        {"id": "inlet_slope", "label": "Уклон самотёчной части", "type": "number", "unit": "‰", "engineer_only": true}
      ]
    },
    {
      "id": "s5_press",
      "title": "5. Напорный трубопровод",
      "fields": [
        {"id": "press_D", "label": "Диаметр D напорного (DN)", "type": "number", "unit": "мм", "autofill_from": "computed.press_D_recommended", "hint": "Авто-предложение по v=1.5..2.0 м/с, инженер уточнит"},
        {"id": "press_material", "label": "Материал", "type": "select", "options": ["ПЭ100 SDR17", "ПЭ100 SDR11", "Сталь dy", "ВЧШГ", "Нерж. AISI304/316"]},
        {"id": "press_branches", "label": "Кол-во отводов/разветвлений", "type": "number", "default": 0},
        {"id": "press_elev_marks", "label": "Высотные отметки (профиль)", "type": "textarea", "hint": "Точки трассы: ПК / отметка"},
        {"id": "press_PN", "label": "Класс давления PN", "type": "select", "options": ["PN6", "PN10", "PN16", "PN25"], "default": "PN10"},
        {"id": "valves_count", "label": "Кол-во задвижек по трассе", "type": "number", "default": 0},
        {"id": "check_valves_count", "label": "Кол-во обратных клапанов по трассе", "type": "number", "default": 0}
      ]
    },
    {
      "id": "s6_corpus",
      "title": "6. Корпус КНС",
      "fields": [
        {"id": "corpus_D", "label": "Диаметр корпуса D_корп", "type": "select", "unit": "мм", "options": [1500, 1590, 1800, 2000, 2200, 2400, 2700, 3000, 3500, 4200, "Другой"], "autofill_from": "computed.corpus_D_suggested"},
        {"id": "corpus_H", "label": "Высота корпуса H_корп", "type": "number", "unit": "мм", "autofill_from": "computed.corpus_H_suggested"},
        {"id": "corpus_material", "label": "Материал корпуса", "type": "select", "options": ["ПЭ (Серво-Юг)", "ПП", "Стеклопластик", "Нерж. сталь", "Бетон сборный"]},
        {"id": "hatch_class", "label": "Класс люка", "type": "select", "options": ["A15 пешеходный", "B125", "C250", "D400 проезжая"]},
        {"id": "service_platform", "label": "Сервисная площадка", "type": "boolean"},
        {"id": "insulation_heating", "label": "Утепление + обогрев", "type": "boolean", "hint": "Юг РФ — обычно нет"},
        {"id": "ventilation", "label": "Вентиляция / биофильтр", "type": "select", "options": ["Естественная", "Принудительная", "С угольным фильтром"]}
      ]
    },
    {
      "id": "s7_redundancy",
      "title": "7. Резервирование и комплектация",
      "fields": [
        {"id": "scheme", "label": "Схема резервирования", "type": "select", "required": true, "options": ["1+1 (1 раб + 1 рез)", "2+1", "2+2", "3+1", "N+0 без резерва"], "default": "1+1", "hint": "СП 32.13330 табл. 17"},
        {"id": "warehouse_pump", "label": "Насос на склад заказчика", "type": "boolean", "default": false}
      ]
    },
    {
      "id": "s8_electric",
      "title": "8. Электроснабжение и автоматика",
      "fields": [
        {"id": "voltage", "label": "Напряжение", "type": "select", "options": ["220 В 1ф", "380 В 3ф", "6 кВ"], "default": "380 В 3ф"},
        {"id": "category", "label": "Категория электроснабжения", "type": "select", "options": ["I", "II", "III"], "default": "II"},
        {"id": "avr", "label": "АВР (автомат. ввод резерва)", "type": "boolean"},
        {"id": "soft_start", "label": "Плавный пуск", "type": "boolean", "default": true},
        {"id": "vfd", "label": "ЧРП (частотный преобразователь)", "type": "boolean"},
        {"id": "level_sensor", "label": "Датчики уровня", "type": "select", "options": ["Поплавки 4 шт", "Поплавки 5 шт", "Гидростатический", "УЗ", "Радар"], "default": "Поплавки 4 шт"},
        {"id": "cabinet_brand_pref", "label": "Предпочтение по шкафу", "type": "select", "options": ["Любой", "ОНИКС", "Блорэй ШУК", "Свой производитель"]}
      ]
    },
    {
      "id": "s9_special",
      "title": "9. Особые требования",
      "fields": [
        {"id": "ex_proof", "label": "Взрывозащищённость Ex", "type": "boolean", "hint": "Обычно для пром. стоков с растворителями"},
        {"id": "ip_class", "label": "Класс защиты IP насоса", "type": "select", "options": ["IP68", "IP69K"], "default": "IP68"},
        {"id": "telemetry", "label": "Диспетчеризация", "type": "multiselect", "options": ["GSM/SMS", "Modbus RTU", "Modbus TCP", "OPC-UA", "Интеграция в АСУ ТП заказчика"]},
        {"id": "fire_pump_combined", "label": "Совмещение с пожаротушением", "type": "boolean"},
        {"id": "noise_limit", "label": "Ограничение по шуму", "type": "number", "unit": "дБ"},
        {"id": "warranty_extra", "label": "Расширенная гарантия", "type": "boolean"}
      ]
    },
    {
      "id": "s10_sign",
      "title": "10. Подпись и согласование",
      "fields": [
        {"id": "client_signer_name", "label": "ФИО подписанта со стороны заказчика", "type": "string"},
        {"id": "client_signer_role", "label": "Должность", "type": "string"},
        {"id": "client_sign_date", "label": "Дата подписи", "type": "date"},
        {"id": "client_signature", "label": "Подпись / печать", "type": "signature_block"},
        {"id": "notes", "label": "Примечания заказчика", "type": "textarea"}
      ]
    }
  ],
  "footer": {
    "text": "Серво-Юг • inservo.ru • +7-XXX-XXX-XX-XX. Опросный лист действителен 30 дней.",
    "version": "v1.0 (2026-05-02)"
  }
}
```

---

## Артефакт 2. Черновая BOM-спецификация

### Структура BOM-черновика

Таблица позиций из 7-10 строк, формируется автоматически по результату первичного подбора. Менеджер показывает клиенту → клиент выбирает сегмент (бюджет/средний/премиум) → черновик уходит инженеру для финализации.

**Поля строки BOM:**

| Ключ | Тип | Описание |
|---|---|---|
| `pos` | int | Позиция (1..N) |
| `category` | enum | `pump` / `auto_coupling` / `valve_gate` / `check_valve` / `guides` / `chain` / `floats` / `cabinet` / `corpus` / `extra` |
| `name` | string | Наименование |
| `brand` | string | Бренд |
| `model` | string | Модель/артикул |
| `dn` | int | Условный диаметр (если применимо) |
| `qty` | int | Количество (учитывает резерв и склад) |
| `unit_price` | float | Ориентировочная цена за ед., ₽ |
| `total_price` | float | Сумма позиции |
| `source` | string | Прайс-источник (Аркада 2026, прямой, и т.п.) |
| `note` | string | Опционально (например: «уточнить у инженера») |

### Справочник минимального комплекта обвязки КНС (3 сегмента)

#### Бюджет (Q ~20-30 м³/ч, H ~15-20 м, бытовые) — baseline АртВинд Мысхако

| Поз | Категория | Наименование | Бренд | Модель | DN | Кол-во | Цена ₽ | Источник |
|---|---|---|---|---|---|---|---|---|
| 1 | pump | Насос фекальный погружной | KAIQUAN | 50WQ/S202-3 (3 кВт) | 50 | 2 (1р+1р) | 75 000 | Аркада 2026 |
| 2 | auto_coupling | Автомуфта (трубная муфта) | KAIQUAN | АТМ-50 | 50 | 2 | 22 700 | Аркада 2026 |
| 3 | valve_gate | Задвижка шиберная (с ножом) | КНР/БиА | DN50 PN10 | 50 | 2 | 13 200 | Аркада 2026 |
| 4 | check_valve | Обратный клапан шаровый | КНР | DN50 PN10 | 50 | 2 | 6 600 | Аркада 2026 |
| 5 | guides | Направляющие (нерж. труба + кронштейны) | — | AISI304, 2 шт + кронштейны | — | 1 компл. | 18 000 | Аркада 2026 |
| 6 | chain | Цепь подъёмная нерж. с карабином | — | AISI304, L=4 м | — | 2 | 3 500 | Аркада 2026 |
| 7 | floats | Поплавковые выключатели | КНР/Magic Switch | MAC-3, кабель 10 м | — | 4 | 5 000 | Аркада 2026 |
| 8 | cabinet | Шкаф управления | ОНИКС | МК4-2×3кВт-АВР-плавный пуск, IP65 | — | 1 | 220 000 | Аркада 2026 |
| 9 | corpus | Корпус КНС из ПЭ | Серво-Юг | КНС D1500 / H3200 | — | 1 | 350 000 | placeholder |

**ИТОГО ориентировочно:** ~ 920 000 ₽ (без проектирования, доставки, монтажа, ПНР).

#### Средний (Q ~70-150 м³/ч, H ~20-30 м, бытовые/смешанные) — на базе Antarus / Иртыш

| Поз | Категория | Наименование | Бренд | Модель | DN | Кол-во | Цена ₽ | Источник |
|---|---|---|---|---|---|---|---|---|
| 1 | pump | Насос фекальный погружной | Antarus / Иртыш | HK2-100-серия (7.5-15 кВт) | 100 | 3 (1р+1р+склад) | 250 000 | прямые прайсы |
| 2 | auto_coupling | Автомуфта | по бренду насоса | АТМ-100 | 100 | 3 | 65 000 | прямые |
| 3 | valve_gate | Задвижка клиновая обрезин. клин | VAG / Hawle | EKO+ DN100 PN10 | 100 | 2 | 38 000 | прямые |
| 4 | check_valve | Обратный клапан шаровый | VAG / ADL | DN100 PN10 | 100 | 2 | 28 000 | прямые |
| 5 | guides | Направляющие нерж. | — | AISI304 DN65 | — | 1 компл. | 45 000 | Аркада |
| 6 | chain | Цепь нерж. | — | AISI304 L=5 м | — | 3 | 6 000 | — |
| 7 | floats | Гидростатический датчик уровня + 2 аварийных поплавка | OTT / Endress | гидростат 0-5 м | — | 1+2 | 35 000 | — |
| 8 | cabinet | ШУ с плавным пуском + АВР + GSM | ОНИКС / Блорэй | МК4-3×11кВт-3хП-АВР-СМС | — | 1 | 380 000 | Аркада |
| 9 | corpus | Корпус КНС ПЭ | Серво-Юг | КНС D2000 / H4500 | — | 1 | 620 000 | placeholder |
| 10 | extra | Жироуловитель (если общепит) | Rainpark | GLS-10 | — | опц. | 180 000 | прямые |

**ИТОГО ориентировочно:** ~ 1.7-2.1 млн ₽.

#### Премиум (Q ~250+ м³/ч или Ex / промышленные / Минобороны)

| Поз | Категория | Наименование | Бренд | Модель | DN | Кол-во | Цена ₽ | Источник |
|---|---|---|---|---|---|---|---|---|
| 1 | pump | Насос фекальный погружной (или Grundfos/Wilo при доступности) | Antarus / KAIQUAN | HK2-150-28-22 (22 кВт) или KQ YW2368 | 150 | 3 (2р+1р) | 450 000-1 350 000 | прямые / Аркада |
| 2 | auto_coupling | Автомуфта DN150-400 | по бренду | АТМ-150..400 | 150-400 | 3 | 90 000-262 000 | Аркада |
| 3 | valve_gate | Задвижка клиновая | VAG | EKO+ DN150 PN10/16 | 150 | 2-3 | 65 000-85 000 | прямые |
| 4 | check_valve | Обратный клапан | VAG | DN150-400 PN10 | 150-400 | 2-3 | 55 000-223 000 | прямые |
| 5 | compensator | Компенсатор резинометалл. | ADL | DN150 PN10 | 150 | 2 | 28 000 | прямые |
| 6 | guides | Направляющие нерж. AISI316 (для агрессивных) | — | AISI316 | — | 1 компл. | 90 000 | — |
| 7 | floats | Радар уровня + аварийные поплавки | VEGA / Rosemount | VEGAPULS C21 | — | 1+2 | 120 000 | — |
| 8 | cabinet | ШУ с PLC+HMI+ЧРП на каждый насос+АВР+ модбас в АСУ ТП | ОНИКС | 3×110-PLC-HMI-С-В IP54 | — | 1 | 750 000 | Аркада |
| 9 | corpus | Корпус КНС ПЭ или стеклопластик | Серво-Юг / Блорэй | КНС D3000+ / H4500+ | — | 1 | 1 100 000+ | placeholder |
| 10 | extra | Газоанализатор H₂S / CH₄ + биофильтр / угольный фильтр вентиляции | Drager | Polytron + биофильтр | — | 1 компл. | 250 000 | — |

**ИТОГО ориентировочно:** ~ 3.5-7+ млн ₽.

> Источники цен: Аркада КП 29.01.2026 (актуальный baseline), исторические КП Беловодск/Белогорск/Минобороны, кейс «КНС 70 л/с» (Antarus). Все цены ориентировочные → инженер уточняет.

### Сохранение
- JSON-файл BOM (для CRM): `bom_<calc_id>.json`
- PDF-черновик (для клиента): `bom_<calc_id>.pdf` — на одном листе А4, с шапкой Серво-Юг, с ИТОГО и припиской «Цены ориентировочные. Финал — после расчёта инженера.»

---

## Артефакт 3. JSON-payload для CRM

```json
{
  "schema_version": "1.0",
  "calc_id": "uuid-v4",
  "timestamp": "2026-05-02T18:00:00+03:00",
  "source": "calc.servo-yug.ru",

  "manager": {
    "id": "user_123",
    "name": "Иван Иванов",
    "email": "ivanov@servo-yug.ru",
    "phone": "+7-XXX-XXX-XX-XX",
    "department": "Отдел продаж Адлер"
  },

  "client": {
    "company": "ООО Заказчик",
    "inn": "0123456789",
    "object": "ЖК Жемчужина, Сочи",
    "city": "Сочи",
    "contact_name": "Петров П.П.",
    "contact_phone": "+7-XXX-XXX-XX-XX",
    "contact_email": "petrov@example.ru",
    "stage": "ПД"
  },

  "inputs_L0": {
    "comment": "Что менеджер ввёл вручную в режиме Любитель",
    "Q_avg_day": 240,
    "Q_unit": "m3/day",
    "dH": 18,
    "L": 350,
    "stoki_type": "household",
    "object_type": "residential"
  },

  "inputs_L1": {
    "comment": "Расширенные поля если менеджер заполнил (опционально)",
    "K_gen": 2.5,
    "T_min": 8,
    "press_D_assumed": 110,
    "scheme": "1+1"
  },

  "computed": {
    "Q_peak_h": 25,
    "Q_peak_ls": 6.94,
    "H_total": 22.5,
    "H_geom": 18,
    "H_friction": 3.2,
    "H_local": 0.8,
    "H_reserve": 0.5,
    "press_D_recommended": 110,
    "velocity_ms": 1.7,
    "corpus_D_suggested": 1800,
    "corpus_H_suggested": 4200,
    "free_passage_required": 50
  },

  "primary_selection": {
    "budget": {
      "pump_brand": "KAIQUAN",
      "pump_model": "50WQ/S202-3",
      "pump_kw": 3,
      "duty_point": {"Q": 22.9, "H": 17.4, "eta": 0.464},
      "bom_total_rub": 920000,
      "bom_ref": "bom_<calc_id>_budget.json"
    },
    "mid": {
      "pump_brand": "Antarus",
      "pump_model": "HK2-100-...",
      "pump_kw": 11,
      "duty_point": {"Q": 25, "H": 22.5},
      "bom_total_rub": 1750000,
      "bom_ref": "bom_<calc_id>_mid.json"
    },
    "premium": {
      "pump_brand": "Grundfos",
      "pump_model": "SLV.80.100.40",
      "pump_kw": 4,
      "duty_point": {"Q": 25, "H": 22.5},
      "available_in_ru": false,
      "bom_total_rub": null,
      "bom_ref": null,
      "fallback_to": "mid"
    }
  },

  "artifacts": {
    "questionnaire_pdf_url": "s3://servo-calc/<calc_id>/questionnaire.pdf",
    "draft_bom_pdf_url": "s3://servo-calc/<calc_id>/bom_draft.pdf",
    "draft_bom_json_url": "s3://servo-calc/<calc_id>/bom_draft.json",
    "calc_log_url": "s3://servo-calc/<calc_id>/calc.log"
  },

  "engineer_assigned": null,
  "engineer_response_due": "2026-05-04T18:00:00+03:00",
  "status": "pending_engineer_review",
  "trigger_reason": "default",
  "trigger_details": "Q>200 м³/сут OR L>500 м",

  "manager_notes": "Клиент торопится, нужен ответ к среде",

  "history": [
    {"ts": "2026-05-02T17:55:00+03:00", "event": "L0_submitted", "actor": "manager_123"},
    {"ts": "2026-05-02T17:58:00+03:00", "event": "primary_selection_done", "actor": "system"},
    {"ts": "2026-05-02T18:00:00+03:00", "event": "engineer_handoff", "actor": "manager_123", "trigger": "manager_request"}
  ]
}
```

### Описание полей
- `schema_version` — версия схемы payload, для обратной совместимости.
- `calc_id` — UUID для всех артефактов и истории.
- `inputs_L0` — то, что обязательно вводит менеджер (Q, dH, L, тип стоков).
- `inputs_L1` — расширенные опциональные поля (если менеджер прошёл по визарду дальше).
- `computed` — всё, что пересчитал движок (вкл. потери напора, рекомендованный D напорного, типоразмер корпуса).
- `primary_selection` — три варианта `budget` / `mid` / `premium` с моделью насоса и ссылкой на BOM.
- `artifacts` — S3-ссылки на PDF/JSON (S3 = Timeweb Cloud, согласно ADR проекта Серво-Юг).
- `trigger_reason` — почему ушло инженеру (см. ниже).
- `history` — события для аудита.

---

## Mapping L0/L1/L2 → опросник

| Поле опросника | Источник | Логика автозаполнения |
|---|---|---|
| `header.doc_no` | `L0.calc_id` | первые 8 символов uuid + дата |
| `header.date` | system | `today()` |
| `header.manager_*` | `L0.manager.*` | копия |
| `s1.object_name` | `L0.client.object` | копия, поле остаётся редактируемым |
| `s1.client_company` | `L0.client.company` | копия |
| `s1.client_contact` | `L0.client.contact_name` + `contact_phone` | конкат |
| `s1.object_type` | `L0.object_type` | прямое значение |
| `s2.stoki_type` | `L0.stoki_type` | mapping: household→Хоз-бытовые, storm→Дождевые/ливневые, industrial→Производственные |
| `s2.Q_avg_day` | `L0.Q_avg_day` (если введено в м³/сут) | копия; иначе пересчитать из л/с или м³/ч |
| `s2.Q_peak_h` | `computed.Q_peak_h` | = Q_avg_day × K_gen / 24 |
| `s2.K_gen` | `computed.K_gen` | таблица СП 32.13330 по Q_avg_sec |
| `s2.T_min/T_max` | defaults (8/30) | если `inputs_L1` не заполнено — оставляем дефолты |
| `s2.free_passage_required` | logic | по `stoki_type`: household→50 мм, industrial→80 мм, storm→40 мм |
| `s3.dH_geom` | `L0.dH` | копия |
| `s3.L_press` | `L0.L` | копия |
| `s4-5.*_D` (диаметры) | `inputs_L1` или `computed` | если менеджер не задал — `computed.press_D_recommended` (формула v=1.5..2.0 м/с) |
| `s5.press_PN` | `computed.PN_required` | по H_total и запасу 1.5 |
| `s6.corpus_D` | `computed.corpus_D_suggested` | по типоразмерному ряду Серво-Юг (1500/1800/2000/2200/2400/2700/3000/3500/4200) |
| `s6.corpus_H` | `computed.corpus_H_suggested` | = глубина_подводящего + ход_насоса + запас |
| `s7.scheme` | `inputs_L1.scheme` ИЛИ default | по табл. 17 СП 32.13330: Q≤30 м³/ч → 1+1, Q>30 → 2+1 как минимум |
| `s8.voltage` | logic | если суммарная P_pump > 4 кВт → 380В; иначе 220В |
| `s8.category` | logic | Минобороны/мед./инфра → I; жилое → II; ИЖС → III |
| `s8.soft_start` | default true | для P>5.5 кВт |
| `s9.ex_proof` | logic | true если `stoki_type==industrial` И есть растворители (поле флаг) |
| `s9.fire_pump_combined` | inputs_L1 | по умолчанию false |

> Принцип: всё, что калькулятор может посчитать сам — заполнено как «предложение инженера», но поле остаётся редактируемым в PDF (через формы Adobe или экспорт в DOCX).

---

## Триггеры передачи инженеру (hand-off)

Объединяю триггеры из этапа A2 (контекст) и добавляю инженерные.

### Автоматические (`trigger_reason: "auto_*"`)

| Код | Условие | Почему |
|---|---|---|
| `auto_q_high` | `Q_avg_day > 200 м³/сут` или `Q_peak_h > 50 м³/ч` | средние и крупные КНС всегда требуют инженерного расчёта |
| `auto_l_long` | `L > 500 м` | длинные трассы → потери трения требуют точного расчёта по Дарси-Вейсбаху |
| `auto_dh_high` | `dH > 30 м` или `H_total > 40 м` | многоступенчатый насос или специальный подбор |
| `auto_industrial` | `stoki_type ∈ {industrial, fats, sludge}` | требует подбора по агрессивности, абразивности, свободному проходу |
| `auto_ex` | `ex_proof = true` | взрывозащита требует сертификации |
| `auto_no_match` | топ-3 пуст или `eta < 0.4` для всех | нет насоса в БД, который попадает в рабочую зону |
| `auto_npsh_warning` | расчётный NPSHa < NPSHr × 1.3 | риск кавитации, нужен пересчёт |
| `auto_redundancy_special` | `scheme ∈ {2+2, 3+1, 3+2}` | СП 32.13330 категории I |
| `auto_unit_mismatch` | расход в нестандартных единицах или сильно отличающийся K_gen | sanity check |

### По запросу менеджера (`trigger_reason: "manager_request"`)

| Код | Описание |
|---|---|
| `mgr_client_critical` | клиент крупный / госконтракт / тендер |
| `mgr_complex_geom` | сложная трасса (перевалы, перепады, несколько отводов) |
| `mgr_competitor_quote` | у клиента уже есть КП от конкурента, нужен инженерный аргумент |
| `mgr_doubt` | менеджер не уверен в результате топ-3 |
| `mgr_special_request` | особое требование клиента (ЧРП, диспетчеризация в АСУ ТП, нестандартный корпус) |

### По неуверенности алгоритма (`trigger_reason: "algo_uncertainty"`)

| Код | Условие |
|---|---|
| `algo_low_confidence` | внутренний скоринг < 0.7 (например, рабочая точка вне «зелёной зоны» Q-H кривой) |
| `algo_db_gap` | в БД нет насоса нужного типоразмера, подбор по экстраполяции |
| `algo_pricelist_stale` | прайс старше 60 дней — цена ориентировочная, нужно подтверждение |

> По умолчанию (`trigger_reason: "default"`) пакет уходит инженеру **всегда**, если менеджер нажал «Продолжить с инженером» — даже если все автотриггеры спокойные. Инженер — обязательный gate для платящего клиента.

---

## Email-шаблон инженеру

**Тема:** `[КНС-расчёт {{calc_id_short}}] {{client.company}} / {{client.object}} — {{Q_avg_day}} м³/сут, dH={{dH}} м`

**Тело:**
```
Привет, {{engineer.name}}!

Передаю на уточнённый расчёт. Менеджер: {{manager.name}} ({{manager.phone}}).
Клиент: {{client.company}}, объект {{client.object}}, {{client.city}}.
Первичные данные: Q={{Q_avg_day}} м³/сут, dH={{dH}} м, L={{L}} м, стоки {{stoki_type}}.
Топ-3 предложение: бюджет {{primary.budget.pump_model}} / средний {{primary.mid.pump_model}}.
Триггер передачи: {{trigger_reason}} ({{trigger_details}}).

Артефакты:
- Опросник клиенту: {{questionnaire_pdf_url}}
- Черновая BOM: {{draft_bom_pdf_url}}
- Полный JSON в CRM: {{crm_link}}

Срок ответа: {{engineer_response_due}} (SLA 48 ч).
Если нужны уточнения — менеджер на связи.

— calc.servo-yug.ru
```

> Если отправляется через Telegram-бот вместо email — то же самое, но кратче, и кнопки `[Принять]` / `[Запросить уточнения у клиента]` / `[Отказ]`.

---

## SLA flow

```
T0   Менеджер ввёл L0 (Q, dH, L, тип) → калькулятор за <5 сек выдал топ-3.
     Менеджер показал клиенту, обсудили.

T0+  Менеджер нажал «Передать инженеру» (или сработал auto-триггер).
     Калькулятор:
       1) сгенерировал PDF опросник (autofill из L0/L1/computed)
       2) сгенерировал PDF + JSON черновой BOM
       3) собрал CRM-payload
       4) отправил email + Telegram инженеру
       5) поставил статус "pending_engineer_review"

T0+24h SLA-1: если инженер не подтвердил приём — авто-напоминание +
       уведомление руководителю отдела.

T0+48h SLA-2 (целевой ответ): инженер должен:
       - подтвердить топ-3 ИЛИ предложить альтернативу
       - выдать финализированный BOM (статус "engineer_approved")
       - либо запросить опросник у клиента (статус "awaiting_client_questionnaire")

T0+72h SLA-эскалация: если ответа нет — авто-эскалация на тех. директора.

Статусы CRM (видны менеджеру в реальном времени):
  pending_engineer_review     ← пакет ушёл, инженер ещё не открыл
  engineer_in_progress        ← инженер взял в работу
  awaiting_client_questionnaire ← инженер ждёт заполненный опросник от клиента
  engineer_approved           ← готов финальный BOM, можно делать КП
  engineer_rejected           ← задача требует пересмотра входных данных
  cancelled                   ← клиент отказался

Менеджер видит:
  • цвет-индикатор (🟢/🟡/🔴 по таймеру SLA)
  • lastUpdate timestamp
  • кнопку «Поторопить инженера» (после T0+24h)
  • кнопку «Скачать готовое КП» (после engineer_approved)
```

### Метрики (для дашборда)
- среднее время от T0 до engineer_approved (целевое < 36 ч)
- доля автотриггеров vs ручных (балансировка нагрузки на инженеров)
- доля engineer_rejected (качество L0-входа менеджера)
- отказ клиентов после показа черновой BOM (UX-индикатор)

---

## Open questions

1. **Полный модельный ряд корпусов КНС Серво-Юг** — сейчас знаем только D=1500/1590/1800/4200 из спецификаций. Запросить у Константина матрицу (диаметры × высоты × объёмы × вес × цена). Без этого `computed.corpus_D_suggested` работает на эвристиках.
2. **Прайс на корпуса Серво-Юг** — текущая цена 350 000 ₽ для D1500/H3200 — placeholder из инвентаризации, не подтверждена. Нужна актуальная матрица от производства Адыгея.
3. **Доступность Grundfos / Wilo / KSB в РФ-2026** — по факту параллельный импорт, цены и сроки нестабильны. Решить: показывать ли premium-сегмент по умолчанию или скрывать с кнопкой «Запросить европейский аналог»?
4. **Антipattern из CHAT_SUMMARY ⚠️1**: на скрине FullSizeRender в опроснике Q=36 м³/ч H=60 м, а в готовом подборе LEO 0.75 кВт (макс H=8 м). Нужно подтвердить у Константина — это две разных КНС или ошибка инженера. От ответа зависит, считать ли LEO 50SWU12 надёжным образцом для БД.
5. **Кто будет инженером по умолчанию?** Сейчас в Серво-Юг нет роли «инженер-расчётчик КНС» в org-структуре проекта. Решить: один человек, очередь, или round-robin между несколькими.
6. **CRM-целевая система** — Bitrix24 / amoCRM / собственный Inservo registry? От этого зависит формат интеграции payload.
7. **S3-хранилище** — Timeweb Cloud S3 (как в ADR Inservo) или локально на сервере calc.servo-yug.ru?
8. **Подпись клиента в PDF** — графическая (Adobe Acrobat) или достаточно ФИО+дата+«согласовано» по почте?
9. **Версионирование BOM** — что если инженер изменил BOM, клиент уже видел черновик? Нужна `bom_version` и diff-нотификация менеджеру.
10. **Локализация** — на ru/uz (для южных регионов с трудовыми мигрантами) — нужно ли в опросном листе?

---

## UX-кейс «1 минута менеджера»

Это сценарный пример, как менеджер ОП проходит весь поток от L0 до отправки hand-off-пакета инженеру за ~60 секунд. Опорный кейс — клон Мысхако/АртВинд (Q≈21 м³/ч, dH=15, L=350, хоз-быт).

| t, сек | Действие менеджера | Что делает калькулятор |
|---|---|---|
| 0..10 | Открывает `calc.servo-yug.ru`, выбирает «Любитель», вводит: Q=240 м³/сут, dH=18 м, L=350 м, тип «Хоз-бытовые». | Валидация полей, конвертация в м³/ч, применение K_gen=2.5. |
| 10..20 | Жмёт «Подобрать». | Расчёт H_total=22.5 м, подбор D_напорного=110, выдача топ-3 (бюджет KAIQUAN 50WQ/S202-3, средний Antarus HK2, премиум-fallback). |
| 20..30 | Видит 3 карточки с ценой и КПД, выбирает бюджет (по запросу клиента). | Подсветка триггеров (`auto_l_long`? нет — L=350<500). Триггер «default» = передача инженеру по нажатию кнопки. |
| 30..40 | Заполняет 4 поля шапки: компания, объект, ФИО+тел контакта, город. | Сохраняет в `client.*` payload. |
| 40..50 | Жмёт «Передать инженеру». | Генерирует questionnaire.pdf (autofill 27 полей из L0+L1+computed), bom_draft.pdf (9 строк KAIQUAN-сегмента ~ 920 000 ₽), JSON-payload, заливает в S3. |
| 50..60 | Видит уведомление «Пакет отправлен инженеру Сидорову, ответ к 04.05 18:00». | Email + Telegram-карточка инженеру с 3 кнопками. CRM-статус `pending_engineer_review`, таймер SLA. |

**Что менеджер НЕ делает руками:** не считает напор, не выбирает DN, не ищет цены, не пишет письмо инженеру, не прикладывает PDF. Всё делает калькулятор по L0 + дефолтам.

**Что инженер получает:** письмо с 3 ссылками (опросник, BOM-черновик, JSON-карточка) + краткое резюме «Q=240 м³/сут, dH=18 м, L=350 м, бюджет — KAIQUAN 50WQ/S202-3, нужно подтвердить или предложить альтернативу».

**KPI первой минуты:** L0 ввод <30 с, hand-off <60 с, ноль свободного текста кроме ФИО/контактов.

---

**Конец документа.**
**Версия 1.1 от 2026-05-02 — sales engineer + Claude.**
**Следующий шаг:** прототипировать схему опросника в JSON-генераторе (jsPDF/pdfmake) на тестовом calc_id и прогнать через эталонный кейс «АртВинд Мысхако».
