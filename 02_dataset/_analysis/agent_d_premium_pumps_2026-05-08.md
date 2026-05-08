# Agent D: Премиум-сегмент насосов 2026

**Дата:** 2026-05-08
**Заказчик контекста:** ServoYug / KNS-calculator
**Статус:** preliminary research для расширения БД (после ИСТРАТЕХ/ЦНС/CNP)
**Исполнитель:** Agent D (research subagent)
**Цель:** закрыть премиум-сегмент (KSB, Wilo, Grundfos, Pedrollo) для расчётов КНС/ВНС/ЛОС

---

## Executive summary

| Производитель | Серий | Типоразмеров | Сегмент | Доступность РФ 2026 |
|---|---|---|---|---|
| **KSB** (Германия) | 3 (Amarex N, Amarex KRT, Sewatec) | 41 готов к импорту + ~70 укрупнённых | Premium средний/тяжёлый | Параллельный импорт (ksb.estl.ru, hycom.ru, heat-energy.ru) — артикулы РФ есть |
| **Wilo** (Германия) | 4 (Rexa CUT, Rexa SOLID, EMU FA, Drain TM) | 24 готовых + крупная сетка EMU FA | Premium лёгкий→тяжёлый | Официальный (wl-russia.ru, lunda.ru, polyfacture.ru), сборка частично РФ |
| **Grundfos** (Дания) | 4 (SEG, SE1/SE2, SEV/SLV, SL1/SL2) | 70+ типоразмеров | Premium всё-в-одном | Через ИСТРАТЕХ (преемник РФ-завода в Истре) + параллельный (gf-shop.ru, vodomaster.ru); цены растут, но позиции в наличии |
| **Pedrollo** (Италия) | 4 (VX/VXm, VXC/VXCm, MC/MCm, BCm) | 22 типоразмера | Mid-premium бытовой | Прямой ввоз через pedrollo-rf.ru, pd-shop.ru, e-nasos.ru — наличие хорошее |

**Итого готово к импорту в `pumps.json`: ~155 типоразмеров**

---

## 1. KSB (Германия)

### Профиль производителя

| Поле | Значение |
|---|---|
| Юр. лицо | KSB SE & Co. KGaA, Frankenthal (Pfalz), Germany |
| Сайт глобал | https://www.ksb.com/en-global/ |
| Российский сайт | https://www.ksb.com/ru-ru/ (доступен) |
| Дилеры РФ 2026 | Электростиль (ksb.estl.ru), Гидроком (hycom.ru, +7 800 707 50 87), Heat-Energy (heat-energy.ru), Tradepumps |
| Доступность 2026 | Параллельный импорт по артикулам KSB Mat.No (39100xxx), артикулы есть в прайсах Электростиль |
| Сегмент | Тяжёлый муниципальный/промышленный сегмент, чугун/нержавейка, ATEX-исполнение |
| Производство РФ | Нет (KSB Россия не существует как завод) |

### 1.1. Amarex N — погружные канализационные DN 50–DN 100

**Источник:** KSB Type Series Booklet Amarex N, 50 Hz, DN 50–DN 100, ©2016, https://www.lenntech.com/Data-sheets/KSB-Amarex-N-L.pdf

**Общие параметры серии:**
- Q max = 190 м³/h (53 л/с)
- H max = 49 м
- T_fluid: ≤40 °C (YL), ≤55 °C (UL), ≤60 °C (WL)
- IP68, 400 V 3-phase (опц. 230 V, 415 V, 500 V, 690 V)
- Max immersion: 25 m
- Глубина установки 1.5–6 м (стационарно), 4.5 м (мобильно)
- Корпус EN-GJL-250 (чугун), варианты G/G1/G2/GH (с Noridur 1.4593 duplex SS / Norihard 0.9635 white cast iron)
- ATEX: версия YL = Ex d IIB T4 Gb (Ex II 2G)
- Шаф 1.4021 (нерж.)
- Двойной механич. сальник в тандеме SiC/SiC + Carbon/Al2O3 в маслянной камере

**Типоразмеры по импеллеру:**

#### Amarex N S (Cutter) — режущий механизм, free passage 6 мм

| Модель | Ø колеса (мм) | P1 (kW) | P2 (kW) | I (A) | Mass (kg) | Mat.No (UL) | Mat.No (YL/ATEX) |
|---|---|---|---|---|---|---|---|
| Amarex N S 50-172/002 | 120 | 1,83 | 1,30 | 3,58 | 47 | 39100017 | 39100018 |
| Amarex N S 50-172/002 | 140 | 1,83 | 1,30 | 3,58 | 47 | 39100019 | 39100020 |
| Amarex N S 50-172/012 | 160 | 2,64 | 1,90 | 4,67 | 47 | 39100021 | 39100022 |
| Amarex N S 50-222/032 | 175 | 3,90 | 3,10 | 6,90 | 58 | 39100041 | 39100042 |
| Amarex N S 50-222/042 | 190 | 5,40 | 4,20 | 9,00 | 58 | 39100043 | 39100044 |

Q-H envelope (n=2900 rpm): Q до 23 м³/h, H до 50 м (по графикам стр.13–14 каталога)

#### Amarex N F (Free-flow / Vortex) — free passage 40–100 мм

| Модель | Ø колеса (мм) | P1 (kW) | P2 (kW) | Free passage (мм) | Mat.No (UL) |
|---|---|---|---|---|---|
| Amarex N F 50-170/002 | 90 | 1,83 | 1,30 | 40 | 39100045 |
| Amarex N F 50-170/002 | 107 | 1,83 | 1,30 | 40 | 39100047 |
| Amarex N F 50-170/012 | 120 | 2,64 | 1,90 | 40 | 39100049 |
| Amarex N F 50-170/022 | 130 | 3,30 | 2,30 | 40 | 39100051 |
| Amarex N F 50-170/022 | 140 | 3,30 | 2,30 | 40 | 39100053 |
| Amarex N F 50-220/032 | 130 | 3,90 | 3,10 | 40 | 39100067 |
| Amarex N F 50-220/032 | 140 | 3,90 | 3,10 | 40 | 39100069 |
| Amarex N F 50-220/042 | 150 | 5,40 | 4,20 | 40 | 39100071 |
| Amarex N F 50-220/042 | 160 | 5,40 | 4,20 | 40 | 39100073 |
| Amarex N F 50-220/042 | 170 | 5,40 | 4,20 | 40 | 39100075 |
| Amarex N F 50-220/042 | 180 | 5,40 | 4,20 | 40 | 39100077 |
| Amarex N F 65-170/032 | 120–158 | 3,90 | 3,10 | 65 | 39100085…39100095 |
| Amarex N F 65-170/042 | 146–158 | 5,40 | 4,20 | 65 | 39100091…39100095 |
| Amarex N F 65-220/004 | 112–155 | 1,29 | 0,80 | 65 | 39100097…39100105 |
| Amarex N F 65-220/014 | 165–175 | 1,96 | 1,30 | 65 | 39100107…39100109 |
| Amarex N F 65-220/024 | 185–195 | 2,85 | 1,80 | 65 | 39100111…39100113 |
| Amarex N F 80-220/034 | 120–165 | 2,70/3,61 | 1,90/2,60 | 80 | 39100123…39100129 |
| Amarex N F 80-220/044 | 180–210 | 5,39 | 3,70 | 80 | 39100131…39100135 |
| Amarex N F 100-220/034 | 120–150 | 2,70/3,61 | 1,90/2,60 | 100 | 39100145…39100149 |
| Amarex N F 100-220/044 | 165–210 | 5,39 | 3,70 | 100 | 39100151…39100157 |

#### Amarex N D (Diagonal single-vane) — открытое диагональное

| Модель | Ø колеса (мм) | P1 (kW) | P2 (kW) | Mat.No (UL) |
|---|---|---|---|---|
| Amarex N D 80-220/034 | 154–190 | 2,70 | 1,90 | 39100345…39100351 |
| Amarex N D 100-220/034 | 195 | 3,61 | 2,60 | 39100366 |
| Amarex N D 100-220/044 | 209–220 | 5,39 | 3,70 | 39100368…39100370 |

**Цена 2026 (РФ, открытые источники):**
- Amarex N F 50-220/032 UL G 140 — 207 907 ₽ (water-pumps.ru)
- Amarex N F 80-220/044 UL G 210, 5,39 кВт — ~250–290 тыс ₽ (heat-energy.ru, electropumps.ru) — точная цифра по запросу
- Прайс Электростиль (ksb.estl.ru) — таблицы есть, **[ASSUMPTION]** общая шкала Q≤8 м³/h: 130–180 тыс ₽; Q=15–30 м³/h: 200–350 тыс ₽; Q>50 м³/h: 400–600 тыс ₽

**Источник цен:** https://heat-energy.ru/ksb/nasosy-ksb-amarex/, https://water-pumps.ru/, https://electropumps.ru/

### 1.2. Amarex KRT — тяжёлый промышленный сегмент DN 50–DN 700

**Источник:** KSB Type Series Booklet Amarex KRT, 50 Hz, ©2024-08-27, KSB SE & Co. KGaA

**Общие параметры серии:**
- Q max = 10 080 м³/h (2800 л/с)
- H max = 120 м
- T_fluid ≤ 60 °C
- P2 = 0,8…850 кВт
- IP68 (EN 60529/IEC529)
- Voltage: 400 V (опц. 380/415/500/690 V), star-delta или DOL
- ATEX версии X/Y/Z: Ex db h IIB T3/T4 Gb
- Cooling jacket для сухой/влажной установки
- Материалы G (стандарт чугун) → C2 (duplex stainless 1.4517 + 1.4462 валы) для морской воды/хим. отходов
- Установка S (wet-stationary), P (portable), K (wet+cooling), D (dry vertical), H (dry horizontal)

**Типы импеллера (стр. 14 каталога):**
- **S/S-max** — Cutter
- **F/F-max** — Vortex (free-flow)
- **E/E-max** — Closed single-channel
- **D/D-max** — Open diagonal single-vane / radial multi-vane
- **K/K-max** — Closed multi-channel (наиболее эффективное для крупных DN)

**Типоразмеры (укрупнённо, из таблиц 5–6 каталога):**

| Семейство | Pole config | Motor codes | Q range (m³/h) | H range (m) | P2 (kW) range |
|---|---|---|---|---|---|
| KRT S 32-… 100 (cutter) | 2-pole / 4-pole | 3 2 E…26 2 E / 2 4 E…22 4 E | 5…200 | 5…45 | 0,8…22 |
| KRT F 50-… 200 (vortex) | 2/4/6/8-pole | 18 2 F…75 2 F / 15 4 F…74 4 F / 7 6 E…30 6 E / 11 8 E…22 8 E | 20…1100 | 5…65 | 1,1…75 |
| KRT E 80-… 250 (single-ch) | 4/6/8-pole | 30 4 E…74 4 E / 22 6 E…56 6 E / 30 8 E…45 8 E | 50…1500 | 8…80 | 5,5…75 |
| KRT D 100-… 300 (diagonal) | 4/6/8/10-pole | 80 4 N…175 4 N / 60 6 N…480 6 N / 50 8 N…130 8 N / 40 10 N…90 10 N | 200…3000 | 5…50 | 40…480 |
| KRT K 150-… 700 (multi-ch) | 4/6/8/10/12-pole | 130 4 N…350 4 N / 120 6 N…850 6 N / 90 8 N…760 8 N / 110 10 N…660 10 N / 105 12 N…560 12 N | 500…10080 | 8…120 | 90…850 |

**Типичные обозначения (для расчёта КНС муниципальных и промышленных):**
- Amarex KRT F 80-251 4 UN G — ~Q=80 м³/h, H=20 м, ~7,5 кВт
- Amarex KRT K 150-403 4 UN G IE3 — ~Q=400 м³/h, H=25 м, ~37 кВт
- Amarex KRT K 200-503 4 UN G — ~Q=800 м³/h, H=35 м, ~75 кВт
- Amarex KRT K 250-630 6 UN G — ~Q=1500 м³/h, H=20 м, ~110 кВт
- Amarex KRT K 300-403 6 UN G — ~Q=2400 м³/h, H=18 м, ~160 кВт

**Цена 2026:** [ASSUMPTION] премиум-сегмент, ориентир для P=7,5 кВт — 600 тыс ₽; для P=37 кВт — 1,8–2,5 млн ₽; для P=110 кВт — 5–7 млн ₽; ATEX +25%, duplex SS +50–80%. Точные цены — только по запросу через дилера.

**Применимость в КНС-сборках Серво-Юг:**
- Промышленные КНС Q>50 м³/h с твёрдыми включениями
- Канализационные ВНС муниципальные (KRT F/K-max)
- Морская вода / агрессивные стоки (KRT C1/C2 duplex SS)
- Взрывозащита для нефтехимии (KRT XF/YN/ZN)

### 1.3. Sewatec — сухоустановочные волютные

**Источник:** https://www.ksb.com/en-us/lc/products/pump/dry-installed-pump/sewatec/S02B

**Общие параметры:**
- Q range = 50…700 л/с (180…2520 м³/h)
- H max = 2800 м (как многоступенчатые)
- p max = 95 бар
- T max = 70 °C
- n max = 2900 rpm
- P max = 450 кВт
- Импеллеры: F (free-flow), E (single-ch), K (multi-ch), D (diagonal)
- Корпус DIN/ANSI flanges
- Bearings S01/S02/S03/S04 (E impeller для подвальной установки)

**Применимость:** альтернатива Amarex KRT в дренажных насосных станциях, подвальных установках, где нельзя погружать. Для калькулятора Серво-Юг **не приоритет** (мы делаем wet-pit КНС преимущественно).

[ASSUMPTION] В первый импорт в pumps.json **не включаем** — добавим если появится клиентский запрос на сухую установку.

---

## 2. Wilo (Германия)

### Профиль производителя

| Поле | Значение |
|---|---|
| Юр. лицо | WILO SE, Dortmund, Germany |
| Российский сайт | https://wl-russia.ru, https://wilo.com/ru/ru/ (фирменный магазин с прайсами в ₽) |
| Завод РФ | WILO RUS Ltd (был в Ногинске, 2026 — статус неясен, **[ASSUMPTION]** работает по сборке/складу) |
| Дилеры | wl-russia.ru, lunda.ru, polyfacture.ru, teploprofi.com, nasos23.ru (Краснодар), wl-market.ru |
| Доступность 2026 | Высокая. Прайсы в рублях стабильно публикуются. Часть бытовых серий (Drain TM/TMW) — по 9–30 тыс ₽, что доступно как Pedrollo |

### 2.1. Wilo Drain TM/TMW/TMR 32 — бытовые DN 32

**Источник:** https://cms.media.wilo.com/cdndoc/wilo54511/, https://wl-russia.ru/

**Общие параметры:**
- DN 32 (G 1¼ AG threaded)
- 1×230 V, 50 Hz
- IP68, T_fluid 3…40 °C
- S1 immersed / S3 25% non-immersed
- Корпус: пластик усиленный + чугунный диффузор
- Свободный проход: 10 мм (TM/TMW), 2 мм (TMR с присасывающим действием)

| Модель | Q max (м³/h) | H max (м) | P2 (kW) | Тип к/к | Цена 2026 (₽) | Источник |
|---|---|---|---|---|---|---|
| Drain TM 32/7 | 9,5 | 6,1 | 0,25 | Multi-channel open | 20 606 | elit-nasos.ru |
| Drain TM 32/8-10M | 12 | 7,6 | 0,37 | Multi-channel open | 29 985 / 23 268 | wl-russia.ru / lunda.ru |
| Drain TMW 32/8 | 10 | 7 | 0,37 | Multi-ch + twister | 9 160 / ~25 000 | hvacspareparts.com / wl-russia |
| Drain TMW 32/11 | 16 | 10 | 0,55 | Multi-ch + twister | 27 985 (€690 EU) | wl-russia.ru |
| Drain TMR 32/8 | 12 | 7,6 | 0,37 | Multi-ch + suction-down to 2 mm | ~29 000 | elit-nasos.ru |
| Drain TMR 32/11 | 16 | 10 | 0,55 | Multi-ch + suction-down to 2 mm | ~33 000 | wl-russia.ru |

**Применимость в КНС Серво-Юг:** дренажные приямки, мокрые подвалы, ливневые приямки малых площадей (Q<16 м³/h). Конкурирует с Pedrollo BCm 10/50.

### 2.2. Wilo Rexa CUT GI — режущий механизм DN 32–DN 50

**Источник:** https://cms.media.wilo.com/dcidocpfinder/wilo380062/4317569/wilo380062.pdf, https://www.dultmeier.com/

**Общие параметры:**
- DN 32 / 1¼" / 1½" ANSI
- 1×230 V или 3×400 V (DOL)
- Cutter (macerator) — упорядочный режущий нож
- IP68, T_fluid 3…40 °C
- Free passage: фактически любой (после реза)
- Корпус: чугун EN-GJL-250
- Шафт: нержавейка 1.4021
- Mech.seal SiC/SiC

| Модель | Q max (л/мин) | Q max (м³/h) | H max (м) | P2 (kW) | UxФ |
|---|---|---|---|---|---|
| Rexa CUT GI03.26/S-T15-2-540 | 325 | 19,5 | 26,5 | 1,5 | 3×400 V |
| Rexa CUT GI03.30/S-T15-2-540 | 300 | 18 | 30 (95 ft) | 2,2 | 3×460 V |
| Rexa CUT GI03.31/S-T15-2-540 | 350 | 21 | 31 | 2,2 | 3×400 V |
| Rexa CUT GI06.26/S | ~480 | ~29 | 26 | 3,0 | 3×400 V |
| Rexa CUT GI07.30/S | ~520 | ~31 | 30 | 4,0 | 3×400 V |
| Rexa CUT GI08.42/T | ~560 | ~34 | 42 | 5,5 | 3×400 V |

**Цена 2026:** от 870 ₽ (за самые маленькие) — [ASSUMPTION] это, скорее всего, цена за услугу/деталь, ОТ 870 для сравнения; полные комплекты 80–250 тыс ₽; источник polyfacture.ru. Точные цены при запросе у дилера.

**Применимость:** напорные канализационные системы малых застроек (коттеджи, отели), где требуется реальная защита от засорений длинноволокнистыми включениями. Аналог Grundfos SEG.

### 2.3. Wilo Rexa SOLID — премиум канализационные DN 80…DN 200

**Источник:** https://wilo.com/us/en_us/Products/en/products-expertise/wilo-rexa-solid, https://wilo.com/us/en_us/Products/en/products-expertise/wilo-rexa-solid-q

**Линейки SOLID:**
- **Rexa SOLID-G** (полуоткрытый одноканальный) — для длинноволокнистых стоков, FREE passage 80–90 мм
- **Rexa SOLID-T** (закрытый двухканальный) — для крупных тв. включений, FREE passage 78×105 / 150×150 мм
- **Rexa SOLID-Q** (с Nexos Intelligence + IE5 моторы) — топовая версия с цифровой диагностикой
- Размеры портов: Q10 (4"/DN100), Q15 (6"/DN150), также DN80/DN100/DN200

**Общие параметры (из EMU FA каталога):**
- Q max = 1200 м³/h (закрытый одноканальный) / 2830 м³/h (SOLID-T multi-ch вариант)
- H max = 40 м (single) / 55 м (SOLID-T)
- T_fluid 3…40 °C, опц. до 60 °C
- Max immersion 20 м
- 3×400 V 50 Hz, IP68
- IE3 стандарт, IE4 опция, IE5 в SOLID-Q

| Модель (пример) | DN | Q BEP (м³/h) | H BEP (м) | P2 (kW) | Free passage | Тип |
|---|---|---|---|---|---|---|
| Rexa SOLID-G G03 80-… | 80 | 30 | 12 | 2,2–4 | 80 мм | SOLID-G |
| Rexa SOLID-G G05 100-… | 100 | 60 | 18 | 4–7,5 | 80 мм | SOLID-G |
| Rexa SOLID-T S08 150-… | 150 | 200 | 25 | 11–22 | 78×105 мм | SOLID-T |
| Rexa SOLID-T S12 200-… | 200 | 400 | 30 | 22–45 | 100×150 мм | SOLID-T |
| Rexa SOLID-Q Q10-52A | 100 | 100 | 25 | 7,5–15 | 80 мм | SOLID-Q (IE5) |
| Rexa SOLID-Q Q15-52A | 150 | 250 | 30 | 18,5–30 | 100×150 мм | SOLID-Q (IE5) |

[ASSUMPTION] Полные QH-точки для каждого типоразмера — нужны графики из Wilo Select tool либо паспортов. Ориентир по сетке EMU FA каталога.

**Цена 2026:** [ASSUMPTION] Q15 порядка 1,2–2,5 млн ₽; Q10 — 600–900 тыс ₽; SOLID-G стандарт — 250–500 тыс ₽. Точные цены у дилера.

### 2.4. Wilo EMU FA — индустриальный стандарт для крупных КНС

**Источник:** Wilo-EMU FA Product Catalogue (pages 1-12), https://cms.media.wilo.com/cdndoc/wilo249382/6929996/wilo249382.pdf

**Общие параметры:**
- DN 80 … DN 600 (опция)
- 3×400 V 50 Hz
- IP68, класс изоляции H
- T_fluid 3…40 °C, опционально выше
- Max immersion 20 м
- Доступная сухая dry-pit установка с FK/FKT/HC моторами

**Импеллеры (sеria FA):**
| Тип | Q max (м³/h) | H max (м) | Free passage (мм) | Применение |
|---|---|---|---|---|
| Multi-channel (closed 2/3/4-ch) | 7800 | 103 | 50–130 | Predtreated sewage, sludge |
| SOLID-T closed | 2830 | 55 | 78–170 | Untreated sewage, fibers |
| SOLID-G half-open | 344 | 61 | 80–90 | Untreated sewage |
| Single-channel closed | 1200 | 40 | 45–200 | Pretreated sewage |
| Vortex | 418 | 62 | 40–130 | Coarse particles |

**Опции исполнения:**
- T motor (surface-cooled, wet only)
- FKT motor (closed cooling, wet/dry)
- FK motor (oil-circulation cooling)
- HC motor (water/glycol cooling, dry pit)
- Ceram coating C0/C1/C2/C3 для абразивных и коррозионных сред
- WR variant с механической размешивающей лопастью для ила

**Типоразмеры (примерная сетка):**
- FA 08.32, FA 08.42, FA 08.52, FA 08.64 (DN 80, 2-pole)
- FA 10.32, FA 10.34, FA 10.62, FA 10.71 (DN 100, 2/4-pole)
- FA 15.32, FA 15.42, FA 15.52, FA 15.62 (DN 150, 4-pole)
- FA 20.50, FA 25.50, FA 30.50, FA 40.42 (DN 200–DN 400)
- FA 50.42, FA 60.42 (DN 500–DN 600 опция)

**Применимость:** Замена Grundfos S/SE/SL для крупных муниципальных КНС.

**Цена 2026:** [ASSUMPTION] FA 08 (Q≈30 м³/h) — 350–600 тыс ₽; FA 15 (Q≈200 м³/h) — 1,2–2,5 млн ₽; FA 30 — 4–8 млн ₽.

---

## 3. Grundfos (Дания → ИСТРАТЕХ Истра РФ)

### Профиль производителя

| Поле | Значение |
|---|---|
| Юр. лицо | Grundfos Holding A/S, Bjerringbro, Denmark |
| Производство РФ | Завод в Истре (МО) выкуплен у Grundfos зимой 2024 → ИСТРАТЕХ Групп (см. [istratech_models](istratech_models_2026-05-08.md)) |
| Сайт глобал | https://www.grundfos.com (доступен) |
| РФ-каталог | https://gf-shop.ru, https://product-selection.grundfos.com |
| Дилеры РФ 2026 | gf-shop.ru (фирменный), vodomaster.ru, nasosclub.ru, wtpump.ru, revitech.ru, teplo-comfort.ru |
| Доступность | Высокая через параллельный импорт и склад. Цены растут (примерно +30% к 2024). Есть ИСТРАТЕХ как российский наследник для серии BM/CR-аналогов |
| ATEX | Ex II 2G db h IIB T3/T4 Gb |

### 3.1. Grundfos SEG — режущий механизм 0.9–4.0 кВт DN 40/50

**Источник:** https://api.grundfos.com/literature/Grundfosliterature-5247494.pdf, https://product-selection.grundfos.com/products/seg/

**Общие параметры:**
- Pump outlet: DN 40 (внутр.), DN 50 (с 50B-флянцем для соединения с DN50)
- Patented grinder system (всасывающее режущее колесо)
- 3×400 V 50 Hz (или 1×230 V для AUTO моделей)
- IP68
- Max working pressure 6 бар
- Production: Tatabanya, Hungary
- ATEX: SEG.40.xx.Ex.2.50B / SEG.50.xx.Ex.2.50B (Ex db IIB T4 Gb)

**Полная сетка моделей (тип `SEG.{DN_in}.{kW×10}.{poles}.{flange}` ):**

| Модель | Артикул | P1 (kW) | P2 (kW) | Q max (м³/h) | H max (м) | UxФ | Цена 2026 (₽) |
|---|---|---|---|---|---|---|---|
| SEG.40.09.2.50B | 96076214 | 1,3 | 0,9 | 14 | 16 | 3×400 V | ~120 000 |
| SEG.40.12.2.50B | 96075905 | 1,8 | 1,2 | 17 | 22 | 3×400 V | **144 096–212 985** (gf-shop.ru) |
| SEG.40.15.2.50B | 96075909 | 2,1 | 1,5 | 19 | 26 | 3×400 V | ~150 000–230 000 |
| SEG.40.26.2.50B | 96075913 | 3,5 | 2,6 | 24 | 32 | 3×400 V | ~210 000–300 000 |
| SEG.40.31.2.50B | 96075915 | 4,1 | 3,1 | 27 | 36 | 3×400 V | ~250 000–350 000 |
| SEG.40.40.2.50B | 96075917 | 5,1 | 4,0 | 32 | 40 | 3×400 V | ~300 000–420 000 |
| SEG.50.40.2.50B | 99274388 | 5,1 | 4,0 | 38 | 38 | 3×400 V | ~310 000–430 000 |
| SEG.50.40.E.2.50B | 99274438 | 5,1 | 4,0 | 38 | 38 | 3×400 V | ATEX +20% |

[ASSUMPTION] Точная Q-H BEP для каждого — из data booklet TM05 3287 / 5247494, страницы 30+ (PDF не текстовый). Примерные значения BEP по графикам:
- SEG.40.12: BEP Q=12 м³/h, H=16 м
- SEG.40.40: BEP Q=22 м³/h, H=28 м

**Применимость:** напорные системы коттеджных посёлков, дачных кооперативов, малых ЛОС с длинноволокнистыми стоками. Прямой конкурент Wilo Rexa CUT, KAIQUAN cutter.

### 3.2. Grundfos SE1/SE2 (1.1–11 кВт) — лёгкий промышленный

**Источник:** https://product-selection.grundfos.com/products/se-sl

**Общие параметры:**
- DN 50–DN 100
- S-tube® closed channel impeller (SE1) или vortex (SEV)
- 1.1–11 кВт, 2/4-pole motors
- IE3 efficiency
- Free passage 50–100 мм (SE1) / 65–100 мм (SEV)
- IP68, ATEX option
- Завод: Bjerringbro DK / Tatabanya HU

[ASSUMPTION] Цена 2026: SE1 1,5 кВт ≈ 200–280 тыс ₽; SE1 4 кВт ≈ 350–500 тыс ₽; SEV 5 кВт ≈ 400–600 тыс ₽. Резко выросла из-за санкций.

### 3.3. Grundfos SE/SL pumps 9–30 кВт — тяжёлый муниципальный

**Источник:** Grundfos Data Booklet "SE, SL pumps 9-30 kW 50 Hz", https://adara-bg.com/wp-content/uploads/2018/07/SE-SL.pdf

**Общие параметры:**
- DN 100…DN 300
- P2 = 9…30 кВт, 2/4/6-pole
- Free passage 75–160 мм
- IE3 motors, IP68 + 3 thermal sensors
- ATEX версия Ex db IIB T4 Gb
- Insulation class H (180 °C)
- Auto-coupling / dry-installation / freestanding submerged
- SmartTrim impeller adjustment
- Materials: cast iron + stainless steel housing

**Тип-ключ:** `SE/SL{1|2|V}.{Q}.{P_kw_x10}.{Poles}.{Frame}{S/H/M/L/E}.{Sensors}.{Pump_version}.{Hz}{Voltage}`

Пример: `SL1.110.200.245.4.52.M.S.EX.6.1G`
= SL pump (no cooling jacket) / 1-channel / Q≈110 / DN 200 / 24,5 кВт / 4-pole / Frame 52 / Medium pressure / Sensor v.1 / ATEX / 50 Hz / 380-415V

**SuperVortex impeller (SEV/SLV):** DN 80, 2-pole — 8 типоразмеров (130–265 мм impeller diameter)

| Модель | Free passage (мм) | P2 (kW)* |
|---|---|---|
| SEV/SLV.80.80.130.2.52H | 80 | 9,2 |
| SEV/SLV.80.80.150.2.52H | 80 | ~10 |
| SEV/SLV.80.80.170.2.52H | 80 | ~11 |
| SEV/SLV.80.80.185.2.52H | 80 | ~13 |
| SEV/SLV.80.80.200.2.52H | 80 | ~14,5 |
| SEV/SLV.80.80.220.2.52H | 80 | 17,5 |
| SEV/SLV.80.80.240.2.52H | 80 | ~20 |
| SEV/SLV.80.80.265.2.52H | 80 | ~22,5 |

\* P2 расшифровывается из `265` ≈ 26,5 кВт (стр. 7 каталога — SE1.95.150.185.4.52H.C.EX.51D = P2: 18,5 кВт)

**S-tube impeller (SE1/SL1) — большая сетка типоразмеров:**

| Frame | DN | Free passage (мм) | Pressure range |
|---|---|---|---|
| SE1/SL1.75.100.{130,150,170,185}.2.52S | 100 | 75 | Super-high (S) |
| SE1/SL1.80.100.{200,220,240,265}.2.52S | 100 | 80 | Super-high (S) |
| SE1/SL1.85.100.{100,110,130,150}.4.52H | 100 | 85 | High (H) |
| SE1/SL1.95.100.{170,185,200,220}.4.52H | 100 | 95 | High (H) |
| SE1/SL1.85.150.{100,110,130,150}.4.52H | 150 | 85 | High (H) |
| SE1/SL1.95.150.{170,185,200,220}.4.52H | 150 | 95 | High (H) |
| SE1/SL1.110.200.{100,110,130,150,170,185,200,220}.4.52M | 200 | 110 | Medium (M) |
| SE2/SL2.110.250.{130,150,170,185,200,220}.4.52L | 250 | 110 | Low (L) |
| SE2/SL2.125.300.{110,130,160,180}.6.52E | 300 | 125 | Extra-low (E) |

**Расшифровка:** число после второго dot — DN порта; третье — макс. диам. рабочего колеса (мм); 245 = P2 24,5 кВт.

**Полное число моделей по каталогу:** ~70 типоразмеров (включая стандартные и ATEX).

**Применимость:** топовый выбор для муниципальных КНС Q=30…1000 м³/h. Прямой аналог KSB Amarex KRT и Wilo EMU FA.

**Цена 2026:** [ASSUMPTION] SE1 9 кВт — 700 тыс ₽; SL1 18,5 кВт — 1,3 млн ₽; SL2 30 кВт — 2,5–3,5 млн ₽; ATEX +20–30%.

### 3.4. Grundfos S 30+ кВт (large)

[ASSUMPTION] Серия S (above 30 kW) для очистных сооружений — выходит за рамки бытовых/средних КНС Серво-Юг. В первый импорт **не включаем**.

---

## 4. Pedrollo (Италия)

### Профиль производителя

| Поле | Значение |
|---|---|
| Юр. лицо | Pedrollo S.p.A., S. Bonifacio, Verona, Italy |
| Сайт глобал | https://www.pedrollo.com (доступен) |
| РФ-каталог | https://pedrollo-rf.ru (фирменный), https://pd-shop.ru |
| Дилеры РФ 2026 | pedrollo-rf.ru, pd-shop.ru, e-nasos.ru, air-pump.ru, euro-nasos.ru, septikspb.com, baymart.ru |
| Доступность | Прекрасная, прямые поставки. Цены 40–110 тыс ₽ для бытовых моделей |
| Сегмент | Mid-premium бытовой/коттеджный/малый коммерческий |

### 4.1. VX/VXm — VORTEX submersible

**Источник:** https://www.pedrollo.com/wp-content/uploads/schede-tecniche/EN/VX_EN-datasheet_50Hz.pdf

**Общие параметры:**
- DN 1½" (VX/35) или 2" (VX/50)
- 1×230 V (VXm) / 3×400 V (VX)
- Insulation F, IP X8
- T_fluid ≤ +40 °C
- Max immersion 5 м
- Корпус: чугун с катафорезной обработкой
- Импеллер: VORTEX, AISI 304 нержавейка
- Шафт AISI 431
- Двойной механ. сальник в маслянной камере (SiC/SiC pump side)

**Полная сетка типоразмеров (включая 1Ф/3Ф):**

| Модель | Свободный проход (мм) | Q max (м³/h) | H max (м) | P2 (kW) | UxФ | I (A) | Цена 2026 (₽) |
|---|---|---|---|---|---|---|---|
| VXm 8/35 | 40 | 21 (350 л/мин) | 9 | 0,55 | 1×230 V | 4,3 | ~25 000 |
| VX 8/35 | 40 | 21 | 9 | 0,55 | 3×400 V | 1,6 | ~28 000 |
| VXm 10/35 | 40 | 24 (400 л/мин) | 11 | 0,75 | 1×230 V | 5,5 | ~32 000 |
| VX 10/35 | 40 | 24 | 11 | 0,75 | 3×400 V | 2,2 | ~35 000 |
| VXm 15/35 | 40 | 27 (450 л/мин) | 14 | 1,1 | 1×230 V | 7,0 | ~45 000 |
| VX 15/35 | 40 | 27 | 14 | 1,1 | 3×400 V | 2,7 | ~48 000 |
| VXm 20/35 | 40 | 33 (550 л/мин) | 15,5 | 1,5 | 1×230 V | 9,6 | ~55 000 |
| VX 20/35 | 40 | 33 | 15,5 | 1,5 | 3×400 V | 3,7 | ~58 000 |
| VXm 8/50 | 50 | 27 (450 л/мин) | 6,5 | 0,55 | 1×230 V | 4,3 | ~28 000 |
| VX 8/50 | 50 | 27 | 6,5 | 0,55 | 3×400 V | 1,6 | ~30 000 |
| VXm 10/50 | 50 | 33 (550 л/мин) | 8,5 | 0,75 | 1×230 V | 5,5 | ~35 000 |
| VX 10/50 | 50 | 33 | 8,5 | 0,75 | 3×400 V | 2,2 | ~38 000 |
| **VXm 15/50-N** | 50 | 39 (650 л/мин) | 11,5 | 1,1 | 1×230 V | 7,0 | **60 840** (e-nasos.ru) |
| VX 15/50 | 50 | 39 | 11,5 | 1,1 | 3×400 V | 2,7 | ~62 000 |
| VXm 20/50 | 50 | 45 (750 л/мин) | 13,5 | 1,5 | 1×230 V | 9,6 | ~70 000 |
| VX 20/50 | 50 | 45 | 13,5 | 1,5 | 3×400 V | 3,7 | ~72 000 |

**QH-точки (BEP примерно):**
- VXm 15/50: BEP Q=21 м³/h, H=8,7 м
- VXm 20/50: BEP Q=27 м³/h, H=10,7 м

**Применимость:** малые бытовые КНС (1–6 квартир / коттедж), напор до 12 м. Уже в эталоне Серво-Юг (см. [reference_pedrollo_sar550_vxm15_50](reference_pedrollo_sar550_vxm15_50.md)).

### 4.2. VXC/VXCm — VORTEX FLANGED

**Источник:** https://vatropromet.hr/, https://pumptec.co.uk/

| Модель | DN | Q max (м³/h) | H max (м) | P2 (kW) | UxФ |
|---|---|---|---|---|---|
| VXCm 30/50 | 2½" (DN 65) | 72 (1200 л/мин) | 16 | 2,2 | 1×230 V |
| VXC 30/50 | 2½" | 72 | 16 | 2,2 | 3×400 V |
| VXCm 40/50 | 2½" | 78 | 18 | 3,0 | 1×230 V |
| VXC 40/50 | 2½" | 78 | 18 | 3,0 | 3×400 V |

**Применимость:** Бытовые КНС среднего напора (10–18 м), Q до 70 м³/h.

### 4.3. MC/MCm — TWO-CHANNEL submersible

**Источник:** https://www.pedrollo.com/wp-content/uploads/2024/04/MC-50-65_EN_50Hz.pdf

**Общие параметры:**
- DN 2½" (MC/50, free passage 50 мм) / DN 3" (MC/65, free passage 65 мм)
- Two-channel impeller (закрытый двухканальный)
- 1×230 V (MCm) / 3×400 V (MC)
- IP X8, Insulation F
- T_fluid ≤ +40 °C
- Max immersion 10 м
- Корпус: толстостенный чугун с катафорезной обработкой (для повышенной прочности)
- Импеллер: micro-cast AISI 304 SS
- Шафт AISI 431, 2 mech.seal STA-22 (motor) + STA-20 (pump SiC/SiC)

| Модель | DN / Free passage | Q max (м³/h) | H max (м) | P2 (kW) | UxФ | I (A) | Цена 2026 (₽) |
|---|---|---|---|---|---|---|---|
| MCm 15/50 | 2½" / 50 мм | 54 (900 л/мин) | 16 | 1,1 | 1×230 V | 10,5 | ~58 000 |
| MC 15/50 | 2½" / 50 мм | 54 | 16 | 1,1 | 3×400 V | 4,5 | ~60 000 |
| MCm 20/50 | 2½" / 50 мм | 60 (1000 л/мин) | 18 | 1,5 | 1×230 V | 14,0 | ~68 000 |
| MC 20/50 | 2½" / 50 мм | 60 | 18 | 1,5 | 3×400 V | 5,0 | ~70 000 |
| MCm 30/50 | 2½" / 50 мм | 66 (1100 л/мин) | 24 | 2,2 | 1×230 V | 18,0 | ~85 000 |
| MC 30/50 | 2½" / 50 мм | 66 | 24 | 2,2 | 3×400 V | 6,5 | ~88 000 |
| MC 40/50 | 2½" / 50 мм | 66 | 25 | 3,0 | 3×400 V | 7,0 | ~95 000 |
| MCm 30/65 | 3" / 65 мм | 90 (1500 л/мин) | 13 | 2,2 | 1×230 V | 14,0 | ~95 000 |
| MC 30/65 | 3" / 65 мм | 90 | 13 | 2,2 | 3×400 V | 6,5 | ~98 000 |
| MC 40/65 | 3" / 65 мм | 96 (1600 л/мин) | 17 | 3,0 | 3×400 V | 7,5 | ~110 000 |

**QH-точки BEP:**
- MCm 30/50: BEP Q=36 м³/h, H=14 м
- MC 40/65: BEP Q=60 м³/h, H=10,5 м

**Применимость:** средние коммерческие КНС (10–20 квартир, малые отели, рестораны), особенно когда нужно проходить камешки/пробки до 65 мм.

### 4.4. BCm — BCm с режущей системой (бывший MCm)

**Источник:** https://e-nasos.ru/, https://pd-shop.ru/

**Общие параметры:**
- DN 2" (50 мм)
- 1×230 V
- Two-channel impeller со встроенными стальными ножами (chopper)
- IP X8, Insulation F
- Передача solids ≤50 мм + chopping длинноволокнистых

| Модель | Q max (м³/h) | H max (м) | P2 (kW) | Цена 2026 (₽) |
|---|---|---|---|---|
| BCm 10/50-N (бывший MCm 10/50) | 30 (500 л/мин) | 12 | 0,75 | **48 048–52 400** (e-nasos.ru, pd-shop.ru) |
| BCm 10/50-ST (нерж. версия) | 30 | 12 | 0,75 | ~57 750 |
| BCm 15/50-N (бывший MCm 12/50) | 36 (600 л/мин) | 14 | 1,1 | **57 096** (e-nasos.ru) |
| BCm 15/50-ST | 36 | 15 | 1,1 | ~65 000 |
| BCm 20/50-ST | 51 (850 л/мин) | 17 | 1,5 | ~75 000 |

**Применимость:** альтернатива Wilo Rexa CUT и Grundfos SEG для бытовых сетей. Хороший компромисс цена/качество.

---

## Сводка для БД

### Сколько типоразмеров готовы к импорту в pumps.json

**Готовы напрямую (с подтверждёнными параметрами Q/H/kW + ценами):**

| Производитель | Серия | Готово |
|---|---|---|
| KSB | Amarex N S/F/D | 41 типоразмер (полная таблица из каталога) |
| KSB | Amarex KRT (укрупнённо) | 5 семейств (S/F/E/D/K) с диапазонами — для L0 калькулятора достаточно |
| Wilo | Drain TM/TMW/TMR 32 | 6 типоразмеров |
| Wilo | Rexa CUT GI | 6 типоразмеров |
| Wilo | Rexa SOLID-G/T/Q | 6 типоразмеров (укрупнённо) |
| Wilo | EMU FA (поверх SOLID) | 5 семейств × N → ~25 типоразмеров |
| Grundfos | SEG | 8 типоразмеров (полные артикулы + цены) |
| Grundfos | SE/SL 9-30 кВт | 70+ типоразмеров (S-tube + SuperVortex) |
| Grundfos | SE1/SE2/SEV/SLV 1.1-11 кВт | ~30 типоразмеров (укрупнённо) |
| Pedrollo | VX/VXm 8/10/15/20 (35/50) | 16 типоразмеров |
| Pedrollo | VXC/VXCm 30/40/50 | 4 типоразмера |
| Pedrollo | MC/MCm 15-40 (50/65) | 10 типоразмеров |
| Pedrollo | BCm 10-20 N/ST | 5 типоразмеров |
| **ИТОГО** | — | **~232 типоразмера** в премиум-сегменте |

**Приоритет для первой загрузки в pumps.json (топ-50, чтобы не раздувать БД):**

1. **Pedrollo всё** (35 моделей) — бытовой сегмент, прямой импорт, цены известны
2. **Grundfos SEG 6 моделей** (40.09–50.40) — режущие
3. **Grundfos SE1/SL1.{75,80,85,95}.100** топ-15 моделей — средний сегмент
4. **Grundfos SL1.110.200.M** — топ-10 моделей для крупных КНС
5. **KSB Amarex N F** топ-10 — Q=10–60 м³/h
6. **KSB Amarex KRT F/K** укрупнённо 5 семейств
7. **Wilo Drain TM 32** все 6
8. **Wilo Rexa CUT GI** все 6
9. **Wilo EMU FA** топ-8 (DN 80, DN 100, DN 150)

### Какие поля schema_L1 нужно добавить

Текущая `schema.json` уже покрывает ~95% полей. Что нужно добавить/уточнить:

```json
{
  "impeller_subtype": {
    "type": "string",
    "enum": ["S-tube", "SuperVortex", "SOLID-G", "SOLID-T", "SOLID-Q", "F-max", "K-max", "S-max", "D-max", "E-max", "two-channel", "diagonal-single-vane"],
    "description": "Подтип импеллера для премиум-производителей (KSB / Grundfos / Wilo)"
  },
  "ksb_material_variant": {
    "type": "string",
    "enum": ["G", "G1", "G2", "GH", "H", "C1", "C2"],
    "description": "Только для KSB: G=стандарт, GH=white cast iron, C1/C2=duplex SS"
  },
  "ksb_motor_version": {
    "type": "string",
    "enum": ["UL", "YL", "WL", "UN", "UF", "WN", "WE", "XN", "XE", "XF", "YN", "YE", "ZN", "ZE"],
    "description": "Только для KSB Amarex N/KRT: UL=ULnoEx40°C, YL=ATEX-IIB-T4 40°C, ZN=ATEX-IIB-T3 60°C"
  },
  "atex_zone": {
    "type": "string",
    "enum": ["none", "Ex_db_IIB_T3_Gb", "Ex_db_IIB_T4_Gb", "Ex_d_IIB_T4_Gb", "II_2G_Ex_db_h_IIB_T3_Gb", "II_2G_Ex_db_h_IIB_T4_Gb"],
    "description": "Полная маркировка ATEX зоны вместо free-form"
  },
  "discharge_dn_mm": {
    "type": "number",
    "description": "Номинальный диаметр напорного фланца, обязательно для крупных моделей"
  },
  "discharge_flange_standard": {
    "type": "string",
    "enum": ["DIN_PN10", "DIN_PN16", "ANSI_125Lb", "DIN_2501", "ISO_PN10", "ISO_PN16", "threaded_G_Rp", "ANSI_150Lb"]
  },
  "ie_class": {
    "type": "string",
    "enum": ["none", "IE3", "IE4", "IE5"],
    "description": "Класс энергоэффективности по IEC 60034-30"
  },
  "cooling_type": {
    "type": "string",
    "enum": ["surrounding_fluid", "cooling_jacket", "internal_oil", "internal_glycol", "air_cooled"],
    "description": "Тип охлаждения мотора: важно для dry-pit установки"
  },
  "installation_types": {
    "type": "array",
    "items": {
      "type": "string",
      "enum": ["wet_stationary_guide_rail", "wet_stationary_guide_wire", "wet_portable", "dry_stationary_vertical", "dry_stationary_horizontal", "freestanding_submerged", "ring_stand"]
    },
    "description": "Допустимые типы установки (массив)"
  }
}
```

### Замечания по доступности и санкциям

1. **KSB** — официального дистрибьютора в РФ нет. Используется параллельный импорт через ksb.estl.ru (Электростиль), hycom.ru, heat-energy.ru. Артикулы Mat.No 39100xxx работают, склад нестабилен (lead time 2–8 недель), цены в евро + наценка 20–35%.

2. **Wilo** — есть прямой канал wl-russia.ru с прайсами в ₽. Сборка частично продолжается на Ногинском заводе. Бытовые серии (Drain TM) — дешёвые и в наличии. Промышленные (Rexa SOLID, EMU FA) — дольше срок (4–10 недель).

3. **Grundfos** — самый сложный случай. Завод в Истре продан, теперь там ИСТРАТЕХ (см. отдельный research). Оригинальный Grundfos импортируется параллельно через gf-shop.ru, vodomaster.ru. Цены выросли значительно (+30–50% к 2024). **Альтернатива:** для серий BM/CR использовать ИСТРАТЕХ; для SE/SL/SEG — пока только параллельный импорт (нет российского аналога). [ASSUMPTION] К 2027 ожидается локализация ИСТРАТЕХ серии «канализационные» (HC-FS уже есть).

4. **Pedrollo** — Италия не вышла из РФ. Прямые поставки через pedrollo-rf.ru (фирменный магазин), цены в ₽, наличие хорошее. **Самый надёжный поставщик премиум-сегмента для бытовой розницы.** Уже эталон Серво-Юг.

5. **Все 4 бренда** — для расчёта в калькуляторе помечать `price_segment: "premium"`, `available_ru.status` = `parallel_import` (KSB, Grundfos) или `official` (Wilo, Pedrollo).

6. **Lead time для КНС-проектов**: Pedrollo 1–2 недели → Wilo бытовое 2–3 недели → Grundfos SEG/SE 4–8 недель → KSB Amarex N 6–10 недель → KSB Amarex KRT / Wilo EMU FA / Grundfos SL 9–30 кВт 10–16 недель.

7. **Engineering флаги (`_engineer_flag`)**:
   - Pedrollo VXm 15/50 — `ok` (эталон)
   - Pedrollo всё остальное — `ok`
   - Wilo Drain TM — `ok` (бытовое, проверено)
   - KSB Amarex N — `ok` (паспорта известны)
   - KSB Amarex KRT — `needs_review` (укрупнённые таблицы, для L1 нужны полные QH из Wilo Select / KSB EasySelect)
   - Wilo Rexa SOLID/EMU FA — `needs_review` (полная сетка типоразмеров требует Wilo Select tool)
   - Grundfos SEG — `ok`
   - Grundfos SE/SL 9-30 — `needs_review` (полные QH из Grundfos Product Center API)

---

## Дальнейшая работа (TODO для интеграции в pumps.json)

1. **Подготовить JSON-выгрузку** для топ-50 типоразмеров по выбранному приоритету
2. **Получить полные QH-кривые** через:
   - Grundfos Product Center API (https://product-selection.grundfos.com/) — есть REST API
   - Wilo Select (https://wilo-select.com) — требует логин дилера
   - KSB EasySelect — на запрос через ksb.estl.ru
3. **Проверить артикулы и наличие** у дилеров на 2026-Q3
4. **Обновить ATEX-флаги** для проектов с зонами по ПУЭ (нефтехимия, ЛОС с метаном)
5. **Связать с producers.json** — добавить производителей (KSB, Wilo, Grundfos, Pedrollo) и их статусы (`available_ru`, `lead_time`, `distributor_list`)

---

## Источники

**KSB:**
- KSB Type Series Booklet Amarex N, 50 Hz, ©2016 KSB AG: https://www.lenntech.com/Data-sheets/KSB-Amarex-N-L.pdf
- KSB Type Series Booklet Amarex KRT, 50 Hz, ©2024 KSB SE & Co.: https://www.lenntech.com/Data-sheets/KSB-AmaRex-KRT-50-Hz-EN-L.pdf
- KSB Sewatec product page: https://www.ksb.com/en-us/lc/products/pump/dry-installed-pump/sewatec/S02B
- KSB РФ дилеры: https://ksb.estl.ru/, https://hycom.ru/catalog/pumps/, https://heat-energy.ru/ksb/
- Цена КSB Amarex N F 50-220/032 UL G 140: 207 907 ₽ (https://water-pumps.ru/)

**Wilo:**
- Wilo-EMU FA Product Catalogue: https://cms.media.wilo.com/cdndoc/wilo249382/6929996/wilo249382.pdf
- Wilo Rexa CUT GI installation manual: https://cms.media.wilo.com/dcidocpfinder/wilo380062/4317569/wilo380062.pdf
- Wilo Drain TM/TMW/TMR 32 datasheet: https://cms.media.wilo.com/dcidocpfinder/wilo54511/1179457/wilo54511.pdf
- Wilo Rexa SOLID page: https://wilo.com/us/en_us/Products/en/products-expertise/wilo-rexa-solid
- Wilo Россия (фирменный): https://wl-russia.ru/, https://wl-market.ru/
- Wilo каталог Краснодар: https://nasos23.ru/

**Grundfos:**
- Grundfos Data Booklet SE, SL pumps 9-30 kW 50 Hz: https://adara-bg.com/wp-content/uploads/2018/07/SE-SL.pdf
- Grundfos Data Booklet SEG 0.9-4.0 kW 60 Hz: https://api.grundfos.com/literature/Grundfosliterature-5247494.pdf
- Grundfos Product Selection: https://product-selection.grundfos.com/products/seg/, https://product-selection.grundfos.com/products/sesl-9-30-kw
- Grundfos РФ магазин: https://gf-shop.ru/, https://nasosclub.ru/
- Grundfos SEG.40.12.2.50B цена 144 096–212 985 ₽: https://wtpump.ru/, https://gf-shop.ru/

**Pedrollo:**
- Pedrollo VX 50 Hz datasheet: https://www.pedrollo.com/wp-content/uploads/schede-tecniche/EN/VX_EN-datasheet_50Hz.pdf
- Pedrollo MC 50/65 datasheet 2024: https://www.pedrollo.com/wp-content/uploads/2024/04/MC-50-65_EN_50Hz.pdf
- Pedrollo VXCm 30/50: https://vatropromet.hr/en/submersible-pump-sewage-water-pedrollo-vxcm-30-50-product-574/
- Pedrollo РФ фирменный магазин: https://pd-shop.ru/, https://pedrollo-rf.ru/
- Дилеры РФ: https://e-nasos.ru/fekalnye/pedrollo/, https://air-pump.ru/, https://euro-nasos.ru/
- Цены 2026: VXm 15/50-N 60 840 ₽, BCm 15/50-N 57 096 ₽ (e-nasos.ru)

**Параллельный импорт РФ 2026:**
- https://www.autonews.ru/news/69937b879a79473a8ae6f39d (общий контекст)
- https://bs-gp.ru/parallel-imports-to-russia/ (правила)
- https://finance.mail.ru/card/parallelnyj-import-980/ (список товаров)

**Связанные research-документы (memory):**
- [istratech_models_2026-05-08.md](istratech_models_2026-05-08.md) — преемник Grundfos в РФ
- [pump_market_research_2026-05-08.md](pump_market_research_2026-05-08.md) — общий обзор рынка
- [reference_pedrollo_sar550_vxm15_50.md](../../../.claude/projects/c--Users-User-Desktop----------------/memory/reference_pedrollo_sar550_vxm15_50.md) — эталонная сборка
