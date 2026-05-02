# Датасет производителей насосов для калькулятора КНС/НС/СПД

**Версия:** 1.1 (по решению заказчика 02.05.2026 удалены Иртыш и ГНОМ — оставлены 8 брендов)
**Дата:** 2026-05-02
**Автор:** субагент-исследователь (15 веб-запросов)
**Скоуп:** только КНС (канализационные погружные/фекальные), НС (водопроводные/дренажные), СПД (станции повышения давления, многоступенчатые центробежные). Бытовые скважинные/бассейные/циркуляционные исключены.

> **Исключены из датасета v1.1:** Иртыш (Завод Взлёт, Омск) и ГНОМ (ГМС Ливгидромаш, Ливны). Разделы оставлены ниже как архив (см. п. 4 и 5) — могут пригодиться для гос-тендеров и дренажных задач, но в основной БД калькулятора не учитываются.

---

## Сводная таблица (v1.1 — 8 брендов)

| # | Бренд | Страна | Доступность РФ 2026 | Сегмент цен | Онлайн-селектор |
|---|---|---|---|---|---|
| 1 | KAIQUAN (KQ) | Китай | Официально (АСО, бывш. ACO Russia) | Бюджет | Нет (PDF-каталоги) |
| 2 | Antarus | Россия | Официально | Средний | Да (search.antarus.su, регистрация) |
| 3 | LEO Group | Китай | Официально (NT-RT, «Новые Технологии») | Бюджет | Нет (PDF) |
| 4 | Aquario / Belamos / Unipump | Россия/Китай (OEM) | Официально | Бюджет | Нет |
| 5 | Grundfos | Дания | Официально + параллельный импорт | Премиум | Да (Grundfos Product Center, регистрация) |
| 6 | Wilo | Германия | Официально (российская сборка + параллельный импорт) | Премиум | Да (Wilo-Select 4 / selectonline.ru, регистрация) |
| 7 | KSB | Германия | Официально (Электростиль, Гидроком) | Премиум | Да (KSB EasySelect, без регистрации для базового) |
| 8 | Pedrollo | Италия | Официально (pedrollo.ru) | Средний | Да (springofdata.pedrollo.com, регистрация) |

> Старая нумерация (1–10) сохранена в разделах ниже для совместимости со ссылками; в новой сводной таблице — пересортировано как 1–8.

---

## 1. KAIQUAN (KQ Pump)

- **Страна:** Китай (Шанхай)
- **Материнская компания:** Shanghai Kaiquan Pump Group Co., Ltd. (основана 1995). 7 предприятий, 5 промзон в Шанхае, Чжэцзяне, Хэфэе, Шицзячжуане, Шэньяне.
- **Сайт:** [kaiquan.com.cn](https://en.kaiquan.com.cn/), [kqpump.com](https://www.kqpump.com/)
- **RU-дистрибьютор:**
  - Основной официальный с 2022 — **АСО (acorussia.ru)** — [acorussia.ru/produkty/nasosnye-stancii/nasosy-kaiquan](https://www.acorussia.ru/produkty/nasosnye-stancii/nasosy-kaiquan), склад в РФ.
  - Также: Петроплан (СПб), BaumGroup, HydroUnit, kqpump.ru.
  - Неподтверждено: «АРКАДА Сочи» — в открытых источниках не нашёл, нужно уточнить у пользователя.
- **availability_ru_2026:** ✅ официально (склад РФ)
- **Сегменты:** КНС (фекальные/сточные), НС (дренаж, водозабор)
- **Флагманские серии:**
  - **WQ/E (WQ/EC)** — малые погружные сточные ≤7.5 кВт. [PDF каталог WQ/E](https://www.kqpump.com/uploads/Catalog--WQE%20Small%20Submersible%20Sewage%20Pump.pdf), [WQ/EC PDF](http://www.kqpump.com/uploads/Catalog--WQ-EC-Series-Small-Submersible-Sewage-Pump.pdf).
  - **WQ (11–22 кВт и >30 кВт)** — средние/большие погружные. [PDF](https://www.kqpump.com/uploads/Catalog--WQ%20Submersible%20Sewage%20Pump.pdf). У серии 30+ кВт есть «smart pump» с облачным мониторингом, датчиками вибрации, температуры подшипников/обмоток, утечки в масляной камере.
  - **WQB** — взрывозащищённое исполнение.
  - **KQSS/KQSW** — двойного всасывания (СПД/большие НС).
  - **KQWH/KQH** — поверхностные одноступенчатые моноблочные.
  - **KQSN** — поверхностные с двойным всасом.
- **Q_range:** ~5–4000 м³/ч (по серии WQ); WQ/E ~5–500 м³/ч
- **H_range:** 5–80 м (типично для КНС-сегмента)
- **Power_range:** 0.75–200 кВт и выше
- **Материалы:** чугун, нерж по запросу
- **Защита:** **IP68**, F-class изоляция, есть Ex-исполнение (WQB)
- **Online selector:** **Нет** (только PDF)
- **Catalog PDF:** [WQ](https://www.kqpump.com/uploads/Catalog--WQ%20Submersible%20Sewage%20Pump.pdf), [WQ/E](https://www.kqpump.com/uploads/Catalog--WQE%20Small%20Submersible%20Sewage%20Pump.pdf), [WQ/EC](http://www.kqpump.com/uploads/Catalog--WQ-EC-Series-Small-Submersible-Sewage-Pump.pdf)
- **Datasheet:** Q-H, КПД, NPSH, мощность, габариты — стандартный набор
- **Price segment:** Бюджет
- **Typical_price 50WQ 3 кВт эквивалент:** не нашёл публично (нужен запрос в АСО / Петроплан / BaumGroup) — ориентир по рынку 80–150 тыс. ₽
- **Lead time:** склад РФ — от наличия (1–7 дней), под заказ — 8–12 нед из Китая
- **Гарантия:** 12–24 мес. (зависит от дилера)
- **Сервисные центры:** через АСО и сеть дилеров (Москва, СПб, регионы)
- **Notes:** Лучшее соотношение цена/характеристика среди китайцев. Делается «под Grundfos» по типоразмерам. Удобно подбирать как замену зарубежного при импортозамещении.

---

## 2. Antarus

- **Страна:** Россия (продукция позиционируется как российский бренд)
- **Сайт:** [antarus.su](https://antarus.su/) (домен .su, не .ru!)
- **RU-дистрибьютор:** прямой производитель/импортёр; представители: Теплосервис-Москва, Vito Group, Элита и др.
- **availability_ru_2026:** ✅ официально
- **Сегменты:** КНС (НК1/НК2), НС, СПД, гидромодули, многоступенчатые, моноблочные, скважинные, дренажные. ~1000 позиций.
- **Флагманские серии:**
  - **НК1** — погружной канализационный с закрытым одноканальным РК (для волокнистых стоков). [antarus.su/pump/canalization/nk1](https://antarus.su/pump/canalization/nk1)
  - **НК2** — двухканальное закрытое РК. [antarus.su/pump/canalization/nk2](https://antarus.su/pump/canalization/nk2). BIM-модель: [bimlib.pro](https://bimlib.pro/model/nasosyantarusnk2/41448/)
  - **MLV** — многоступенчатые вертикальные (СПД), пример станция 2MLV3-6.
- **Online selector:** ✅ [search.antarus.su](https://search.antarus.su/) — программа подбора. Категории: насосные установки, гидромодули, насосы, канализационные, станции I подъёма (водозабор), станции в подземном исполнении (в разработке). **Требуется регистрация.**
- **Catalog PDF:** на сайте по разделам.
- **Price segment:** Средний
- **Typical_price:** есть прайс на станции у дистрибьюторов (например 2MLV3-6 ≈ 700 526 ₽ у Теплосервис-Сибирь). Цена единичного НК1/НК2 — нужно уточнять.
- **Lead time:** склад РФ
- **Notes:** Хороший российский конкурент Wilo/Grundfos в среднем сегменте; есть готовые BIM-модели — плюс для проектировщиков. Подозрение: возможна сборка из импортных компонентов (типично для рос. брендов).

---

## 3. LEO Group

- **Страна:** Китай (LEO Group Pump)
- **Сайт:** [leoglobal.com](https://leoglobal.com/), [leopumps-europe.com](https://www.leopumps-europe.com/)
- **RU-дистрибьютор:** «Новые Технологии» (NT-RT) — [leo.nt-rt.ru](https://leo.nt-rt.ru/en/catalog/pogruznye-nasosy). Представительства в РФ, Беларуси, Казахстане, Армении и др.
- **availability_ru_2026:** ✅ официально
- **Сегменты:** Бытовые + коммерческие. Для нашей задачи: дренажные, фекальные, многоступенчатые, повысительные. Присутствуют в 140 странах.
- **Флагманские серии:**
  - **LKS-P / LKS-PW / LKS-S / LKS-SE** — погружные сточные/дренажные.
  - **XKS / XKS-P / XKS-PW / XKS-S / XKS-SW** — погружные канализационные.
  - **EKS, AKS, LSW, LDW, STK** — сегменты дренажа/фекалов.
  - **QDX, QDX-LA** — малые погружные (на грани с бытовыми).
- **Online selector:** Нет (PDF-каталоги)
- **Price segment:** Бюджет (ниже KAIQUAN по позиционированию)
- **Notes:** Часто используется как «entry-level», для нашей задачи (КНС/НС промышленные) — узкое окно применений (LKS-P, XKS).

---

## 4. ~~Иртыш (ОДО «Предприятие Взлёт», г. Омск)~~ — ИСКЛЮЧЁН (v1.1)

> ⚠️ По решению заказчика от 02.05.2026 Иртыш исключён из основного датасета. Раздел сохранён ниже только как архивная справка.

- **Страна:** Россия (Омск, ул. Завертяева, 36)
- **Производитель:** ОДО «Предприятие Взлёт» — [vzlet-omsk.ru](https://www.vzlet-omsk.ru/)
- **availability_ru_2026:** ✅ официально (отечественное производство)
- **Сегменты:** КНС (ПФ — фекальные), НС (ПД — дренажные, ППс — шламовые), также серии ЦМК/ЦМФ/ЦМЛ.
- **Флагманские серии:**
  - **ПФ Иртыш** — погружные фекальные. [vzlet-omsk.ru/pf-pogruzhnye-fekalnye-nasosy](https://www.vzlet-omsk.ru/pf-pogruzhnye-fekalnye-nasosy)
  - **ПД Иртыш** — погружные дренажные, до **H=125 м**, частицы до **12 мм**. [vzlet-omsk.ru/pd-pogruzhnye-drenazhnye-nasosy](https://www.vzlet-omsk.ru/pd-pogruzhnye-drenazhnye-nasosy)
  - **ППс** — шламовые/песковые.
  - **ЦМК / ЦМФ** — центробежные моноблочные канализационные/фекальные (стационарные с удлинённым валом). Модели: ЦМК 16-16…ЦМК 130-22, ЦМФ 60-30…ЦМФ 400-20.
  - **ЦМЛ** — серия Иртыш у Электрогидромаш ([nasos-egm.ru/production/pumps/nasos_irtich/nas_cml](https://nasos-egm.ru/production/pumps/nasos_irtich/nas_cml)).
- **Q_range:** 16–400 м³/ч (по серии ЦМФ — до 400)
- **H_range:** 10–125 м
- **Материалы:** чугун (стандарт), нерж — спец-исполнение
- **Online selector:** Нет
- **Price segment:** Средний (рос. производство, без NDS)
- **Lead time:** Омск — 1–4 нед в зависимости от загрузки
- **Notes:** Государственно-промышленный сегмент, высокая лояльность рос. ВКХ, стандарт для гос-тендеров. Аналоги: ампика.ру, mskompany.ru, nasos-egm.ru — много дилеров.

---

## 5. ~~ГНОМ (АО «ГМС Ливгидромаш»)~~ — ИСКЛЮЧЁН (v1.1)

> ⚠️ По решению заказчика от 02.05.2026 ГНОМ исключён из основного датасета. Раздел сохранён ниже только как архивная справка.

- **Страна:** Россия (Ливны, Орловская обл.) — часть ГК «ГМС»
- **Сайт:** [hms-livgidromash.ru](https://www.hms-livgidromash.ru/catalog/nasosy-gnom-drenazhnye-pogruzhnye-monoblochnye-dlya-gryaznoy-vody.html)
- **availability_ru_2026:** ✅ официально, ключевой отечественный производитель
- **Сегменты:** Дренажные погружные (НС/строительный дренаж). Слабее в КНС-фекалах (там чаще ЦМК/ЦМФ).
- **Флагманские серии:**
  - **ГНОМ** = «грязевой насос одноступенчатый моноблочный». Модели: ГНОМ 10-10, 16-16, 40-25 и др. (Q м³/ч × H м).
  - **ГНОМ Г S1** — для горячей воды до 95 °C. [hms-livgidromash.ru/catalog/gnom-g.html](https://www.hms-livgidromash.ru/catalog/gnom-g.html)
- **Q_range:** 6–53 м³/ч (стандартный ряд)
- **H_range:** 6–25 м
- **Параметры жидкости:** плотность до 1100 кг/м³, твёрдые частицы до 10 % массы, плотность частиц до 2500 кг/м³, размер до 5 мм.
- **Исполнения:** бытовые чугун, облегчённые пластик, промышленные до 35 °C, повышенной температуры до 60 °C, **взрывозащищённые**.
- **Online selector:** Нет
- **Price segment:** Бюджет/Средний
- **Notes:** Строительный/аварийный дренаж — стандарт де-факто. Для КНС напрямую не подходит (нужны ПФ Иртыш или WQ KAIQUAN), но как альтернатива для дренажных задач — обязателен в калькуляторе.

---

## 6. Aquario / Belamos / Unipump

- **Страна:** РФ-бренды (с китайским OEM производством); Aquario позиционируется как итало-китайская сборка.
- **Сайты:** [belamos.net](https://belamos.net/), unipump.ru, aquario.ru
- **availability_ru_2026:** ✅ официально, массовый рынок
- **Сегменты:** Преимущественно бытовой/малокоммерческий: скважинные, дренажные, фекальные малые. Для промышленных КНС/НС НЕ подходят. **Для нашего калькулятора — на грани scope**, можно включить как «entry-level» для малых частных КНС (коттеджи).
- **Флагманские серии (релевантные):**
  - Belamos: скважинные центробежные, дренажные малые ([belamos.net/drenazhnye-nasosy](https://belamos.net/drenazhnye-nasosy)).
  - Unipump: дренажные, фекальные.
  - Aquario: универсал.
- **Q_range:** 1–20 м³/ч (бытовой сегмент)
- **H_range:** 5–80 м
- **Online selector:** Нет
- **Price segment:** Бюджет
- **Notes:** В калькуляторе для коммерческих КНС/НС использовать ОСТОРОЖНО, в основном для мини-КНС частных домов. По умолчанию исключить из БД промышленного калькулятора.

---

## 7. Grundfos

- **Страна:** Дания (Бьеррингбро)
- **Сайт:** [grundfos.com](https://www.grundfos.com/), [ru.grundfos.com](https://ru.grundfos.com/) (продолжает работу в РФ-сегменте)
- **RU-дистрибьютор:** ранее ООО «Грундфос Истра» (рос. завод). После 2022 — официальный канал ограничен; присутствуют дилеры (НасосКлаб, helion-ltd, Гидроком). **Параллельный импорт продлён до конца 2026** (ФЗ № 463-ФЗ от дек. 2025). НО в апреле 2025 из перечня параллельного импорта исключены 47 позиций «электродвигатели, насосы, подшипники» где есть локализация в РФ.
- **availability_ru_2026:** ⚠️ преимущественно через параллельный импорт + остатки рос. сборки. Часть моделей (где есть локализация) под санкционным давлением.
- **Сегменты:** КНС, НС, СПД — всё.
- **Флагманские серии:**
  - **SL / SE** (9–30 кВт и более) — погружные сточные с импеллером S-tube/SuperVortex. [ru.grundfos.com/products/find-product/se-and-sl-9-30-kw.html](https://ru.grundfos.com/products/find-product/se-and-sl-9-30-kw.html). Стоки с включениями до 160 мм.
  - **SEV / SLV** — со свободным проходом, городские сети.
  - **DP / EF / KP** — малые дренажные.
  - **Hydro MPC** — станции повышения давления (СПД) на базе CR/CRE. Пример: Hydro MPC-E 3 CRE 10-3 ([nasosclub.ru](https://nasosclub.ru/catalog/ustanovki-dlya-povysheniya-davleniya/grundfos-povishenie/hydro_mpc_e/)).
  - **Hydro MX** — большие СПД.
  - **CR / CRE / CRN / CRI** — многоступенчатые вертикальные.
- **Q_range:** 1–10 000+ м³/ч (целая линейка)
- **H_range:** 5–250+ м
- **Material:** чугун + нерж 304/316
- **Защита:** IP68, Ex
- **Online selector:** ✅ **Grundfos Product Center (GPC)** — [product-selection.grundfos.com](https://product-selection.grundfos.com/) и [ru.grundfos.com/grundfos-product-center.html](https://ru.grundfos.com/grundfos-product-center.html). Регистрация требуется для продвинутых функций (проекты, сохранения), базовый подбор Q-H + замена доступен. Поддерживает Hydro MPC, SE, SL, CR.
- **Catalog PDF:** [Industrial Gines Grundfos Price List 2025](https://industrialgines.com/en/catalog-price-list-grundfos-2025/) — цены ЕС.
- **Price segment:** Премиум
- **Typical_price 50WQ 3 кВт экв (SEV.65.65.30):** ориентир 350–600 тыс. ₽ (параллельный импорт)
- **Lead time:** 4–12 нед (зависит от канала)
- **Гарантия:** 24 мес.
- **Notes:** Эталон. В калькуляторе обязателен как референс для Q-H кривых. Цена 3–5x от KAIQUAN.

---

## 8. Wilo

- **Страна:** Германия (Дортмунд)
- **Сайт:** [wilo.com](https://wilo.com/ru/ru/), [wilo.ru](https://wilo.ru/)
- **RU-дистрибьютор:** ООО «ВИЛО РУС» — [wl-russia.ru](https://wl-russia.ru/) (сертифицированный магазин). Часть продукции (EMU FA, EMU KS, Drain, Rexa BLOC) производится/собирается в РФ. Сертификаты соответствия Таможенного союза.
- **availability_ru_2026:** ✅ преимущественно официально (рос. сборка) + ⚠️ часть через параллельный импорт.
- **Сегменты:** КНС, НС, СПД — полная линейка.
- **Флагманские серии:**
  - **Wilo-Rexa CUT** — фекальные с измельчителем. [wl-russia.ru/rexa-cut](https://wl-russia.ru/rexa-cut)
  - **Wilo-Rexa PRO** — основные погружные канализационные. [wl-russia.ru/rexa-pro](https://wl-russia.ru/rexa-pro)
  - **Wilo-Rexa SUPRA / FIT / UNI / Solid** — линейка КНС.
  - **Wilo-EMU FA** — большие промышленные погружные, рос. производство.
  - **Wilo-EMU KS / KPR** — дренажные. [wl-russia.ru/emu-ks](https://wl-russia.ru/emu-ks)
  - **Wilo-Drain TP / MTC** — дренажные/КНС.
  - **Wilo-Padus UNI** — для коттеджного сегмента.
  - **Wilo-Helix / Multivert MVI** — многоступенчатые СПД.
  - **Wilo-COR / COR-2 MVIE** — станции повышения давления.
- **Q_range:** 1–8000+ м³/ч
- **H_range:** 5–200+ м
- **Online selector:** ✅ **Wilo-Select 4** — [wilo.com/ru/ru/Решения/Подбор и определение размеров/Программа подбора оборудования Wilo-Select-4/](https://wilo.com/ru/ru/) и [selectonline.ru](https://selectonline.ru/). Веб + Win-приложение. **3 шага: гидравлический подбор по рабочей точке, поиск по артикулу/названию, экспорт BIM/CAD/документов.** Поддержка цен в рублях. **Регистрация рекомендована** для прайс-листов и сохранения проектов.
- **Catalog PDF:** на сайте wilo.com по продуктам.
- **Price segment:** Премиум (близок к Grundfos)
- **Typical_price 50WQ 3 кВт экв (Rexa PRO V05):** 300–500 тыс. ₽
- **Lead time:** 2–8 нед (рос. сборка быстрее)
- **Гарантия:** 24 мес.
- **Сервисные центры:** Москва, СПб, региональные дилеры
- **Notes:** Сильный российский присутствие; программа Wilo-Select 4 с экспортом BIM — ценнейший референс для калькулятора.

---

## 9. KSB

- **Страна:** Германия (Франкенталь)
- **Сайт:** [ksb.com](https://www.ksb.com/), [ksb-rus.ru](https://ksb-rus.ru/), [ООО «КСБ»](https://xn--80aaigboe2bzaiqsf7i.xn--p1ai/ksb)
- **RU-дистрибьютор:** ООО «КСБ» (Москва), Электростиль — [ksb.estl.ru](http://ksb.estl.ru/), Гидроком — [hycom.ru/catalog/pumps/](https://hycom.ru/catalog/pumps/), InterPumps, KRON.
- **availability_ru_2026:** ✅ официально (через ООО КСБ и сеть дилеров) + параллельный импорт по отдельным сериям.
- **Сегменты:** КНС, НС, СПД, промышленные процессы.
- **Флагманские серии:**
  - **Amarex** — погружные сточные (КНС). Аналог SL/Rexa.
  - **Amarex KRT** — большие промышленные погружные (от 30 кВт).
  - **Sewatec** — спирально-корпусные сухие установки (для КНС в сухой камере, аналог LCD/LCI у KAIQUAN).
  - **Movitec** — многоступенчатые вертикальные центробежные (СПД). [kron.spb.ru/products/nasosnoe-oborudovanie/ksb/ksb-movitec/](https://www.kron.spb.ru/products/nasosnoe-oborudovanie/ksb/ksb-movitec/)
  - **Multitec** — высоконапорные многоступенчатые.
  - **Etabloc / Etaline / Etanorm** — горизонтальные центробежные.
  - **Hyamat** — станции повышения давления.
- **Q_range:** 1–10 000+ м³/ч
- **H_range:** 5–300+ м
- **Online selector:** ✅ **KSB EasySelect** — [ksb.com/ksb-en/Select_your_pumps_and_valves/ksb-easyselect/](https://www.ksb.com/ksb-en/Select_your_pumps_and_valves/ksb-easyselect/) и [products.ksb.com/global/product-configurators/easyselect/](https://products.ksb.com/global/product-configurators/easyselect/). Универсальный конфигуратор по применениям. Также есть **KSB HELPS PumpSelection**. Базовый подбор без регистрации; для скачивания — регистрация.
- **Catalog PDF:** на ksb.com по сериям.
- **Price segment:** Премиум
- **Typical_price 50WQ 3 кВт экв (Amarex N S 32-160):** 250–450 тыс. ₽
- **Lead time:** 4–10 нед
- **Гарантия:** 24 мес.
- **Notes:** Сильны в больших КНС (Amarex KRT) и сухих установках (Sewatec). EasySelect — самый «открытый» из премиум селекторов.

---

## 10. Pedrollo (+ Calpeda, DAB как альтернативы)

- **Страна:** Италия (Pedrollo S.p.A., Сан-Бонифачо, Верона)
- **Сайт:** [pedrollo.com](https://www.pedrollo.com/), [pedrollo.ru](https://www.pedrollo.ru/) (офиц. дистрибьютор в РФ)
- **RU-дистрибьютор:** [pedrollo.ru](https://www.pedrollo.ru/), e-nasos.ru, vodomaster.ru, mvk-spb.ru.
- **availability_ru_2026:** ✅ официально
- **Сегменты:** Преимущественно средний коммерческий — НС, СПД, скважинные. КНС-фекальные есть, но не топ-серия (лучше Grundfos/Wilo/KSB).
- **Флагманские серии:**
  - **MC / MCm** — многоступенчатые СПД.
  - **PVm / PV** — вертикальные многоступенчатые.
  - **VX / VXm** — погружные канализационные с открытым РК (≤2 кВт, малая КНС).
  - **MC-серия** — средние горизонтальные.
  - **TOP, TR, RX** — дренажные (RXm 3/20, RX 4/40).
  - **4SR / 6SR** — скважинные многоступенчатые.
- **Q_range:** 1–500 м³/ч
- **H_range:** 5–250 м
- **Online selector:** ✅ **The Spring of Data** — [springofdata.pedrollo.com/selector](https://springofdata.pedrollo.com/selector). Регистрация (T&C). Также **PowerTank Selector Tool** для аккумуляторов давления.
- **Catalog PDF:** на pedrollo.com и pedrollo.ru.
- **Price segment:** Средний (между Grundfos и LEO)
- **Typical_price:** доступнее премиума на 30–40 %
- **Lead time:** 2–4 нед (склад РФ)
- **Гарантия:** 24 мес.
- **Notes:** Хорошая альтернатива в среднем сегменте. Слабее премиум-3 на больших КНС (>30 кВт). Calpeda и DAB — итальянские конкуренты с похожими профилями.

---

## Источники

### KAIQUAN
- [KAIQUAN WQ Catalog PDF](https://www.kqpump.com/uploads/Catalog--WQ%20Submersible%20Sewage%20Pump.pdf)
- [KAIQUAN WQ/E Catalog PDF](https://www.kqpump.com/uploads/Catalog--WQE%20Small%20Submersible%20Sewage%20Pump.pdf)
- [АСО — официальный дилер KAIQUAN в РФ](https://www.acorussia.ru/produkty/nasosnye-stancii/nasosy-kaiquan)
- [Петроплан — серии WQ](https://petroplanpro.spb.ru/catalog/kaiquan_mnogofunkcionalnye_nasosy/pogrujnye_nasosy_kaiquan/seriia_wq_pogrujnye_nasosy_dlia_stochnyh_vod/)

### Antarus
- [antarus.su](https://antarus.su/)
- [antarus.su/pump/canalization/nk1](https://antarus.su/pump/canalization/nk1)
- [antarus.su/pump/canalization/nk2](https://antarus.su/pump/canalization/nk2)
- [search.antarus.su — селектор](https://search.antarus.su/)
- [BIM Library — НК2](https://bimlib.pro/model/nasosyantarusnk2/41448/)

### LEO
- [leo.nt-rt.ru — RU дистрибьютор](https://leo.nt-rt.ru/en/catalog/pogruznye-nasosy)
- [leoglobal.com](https://leoglobal.com/)

### Иртыш / ВЗЛЁТ
- [vzlet-omsk.ru/pf-pogruzhnye-fekalnye-nasosy](https://www.vzlet-omsk.ru/pf-pogruzhnye-fekalnye-nasosy)
- [vzlet-omsk.ru/pd-pogruzhnye-drenazhnye-nasosy](https://www.vzlet-omsk.ru/pd-pogruzhnye-drenazhnye-nasosy)
- [nasos-egm.ru — Иртыш ЦМК](https://nasos-egm.ru/catalog/nasosnoe_oborudovanie/marka_nasosa/irtysh_tsmk/)

### ГНОМ
- [hms-livgidromash.ru — каталог ГНОМ](https://www.hms-livgidromash.ru/catalog/nasosy-gnom-drenazhnye-pogruzhnye-monoblochnye-dlya-gryaznoy-vody.html)
- [pumpedia.ru — ГНОМ Ливгидромаш](https://pumpedia.ru/product/drenazhnye-nasosy/gnom/livgidromash/)

### Grundfos
- [ru.grundfos.com/grundfos-product-center.html](https://ru.grundfos.com/grundfos-product-center.html)
- [SE/SL 9-30 кВт](https://ru.grundfos.com/products/find-product/se-and-sl-9-30-kw.html)
- [Industrial Gines Price List 2025](https://industrialgines.com/en/catalog-price-list-grundfos-2025/)
- [Параллельный импорт до 2026](https://news-novgorod.ru/society/2025/12/27/36604.html)

### Wilo
- [wl-russia.ru — официальный магазин](https://wl-russia.ru/)
- [Wilo-Select 4](https://wilo.com/ru/ru/)
- [selectonline.ru](https://selectonline.ru/)
- [wl-russia.ru/rexa-pro](https://wl-russia.ru/rexa-pro)

### KSB
- [products.ksb.com — конфигураторы](https://products.ksb.com/global/product-configurators/)
- [KSB EasySelect](https://www.ksb.com/ksb-en/Select_your_pumps_and_valves/ksb-easyselect/)
- [ksb-rus.ru](https://ksb-rus.ru/)
- [Электростиль — официальный дилер](http://ksb.estl.ru/)

### Pedrollo
- [pedrollo.ru](https://www.pedrollo.ru/)
- [Spring of Data Selector](https://springofdata.pedrollo.com/selector)
- [vodomaster.ru/brands/pedrollo](https://vodomaster.ru/brands/pedrollo/)

---

## Закрытые пробелы и открытые вопросы для deep-research

1. **Цены 50WQ 3 кВт эквивалентов** — публично не находятся. Запросить прайсы в ACORussia, BaumGroup, ВЗЛЁТ, ВИЛО РУС.
2. **АРКАДА Сочи** как дилер KAIQUAN — не подтвердилось в открытых источниках. Уточнить контакт у пользователя.
3. **JSON/XML с Q-H кривыми** ни один производитель не выкладывает open-data — нужно парсить PDF или интегрироваться через API селекторов (Wilo-Select 4 имеет экспорт, GPC — внутри). Ключевой блок для калькулятора.
4. **Списки исключений из параллельного импорта** на 2026 — апрель 2025 убрали 47 позиций (электродвигатели, насосы, подшипники). Уточнить актуальный перечень для каждой серии.
5. **Antarus реальный страновой состав компонентов** (РФ vs импорт) — не раскрывается; влияет на классификацию для гос-тендеров (44-ФЗ/223-ФЗ, требования к локализации).
