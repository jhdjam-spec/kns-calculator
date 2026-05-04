# R4 — Учебники по гидравлике, насосам и КНС: deep-research

**Дата:** 2026-05-04 (после команды Константина «найди учебные пособия и обучись на них»)
**Способ:** 3 параллельных агента + критический фильтр на «что добавит ценность нашему калькулятору»

---

## 1. Учебники по гидравлике (общая)

### Русскоязычные (PDF свободные)

| Источник | URL | Применение |
|---|---|---|
| **Идельчик И.Е.** «Справочник по гидравлическим сопротивлениям» 3-е изд. 1992 | [PDF на takir.ru](https://takir.ru/pdf/Idelchik-spravochnik-po-gidravlichesim-soprotivleniyam.pdf) / [Totalarch](https://books.totalarch.com/handbook_of_hydraulic_resistance) | **Первоисточник для ζ.** Главы 4–7 — отводы, тройники, диафрагмы, клапаны. Содержит зависимости ζ = f(Re, шероховатость, R/D). |
| **Чугаев Р.Р.** «Гидравлика» 4-е изд. 1982 | [PDF на tiiame.uz](https://staff.tiiame.uz/storage/users/4/books/Tpjb4StU60BnjENwRkDVGW43UzGTEg6P9wSmMDCE.pdf) / [dwg.ru](https://dwg.ru/dnl/10113) | Глава о неустановившихся течениях — формула скорости волны через модули упругости. |
| **Шевелев Ф.А., Шевелев А.Ф.** «Таблицы для гидравлического расчёта водопроводных труб» 2007 | [PDF PSU](https://elib.psu.by/bitstream/123456789/9149/7/Таблицы%20Шевелева%20гидравлического%20расчёта.pdf) | Альтернатива Дарси: `1000·i = A·v²/D^m` с таб A, m по материалам. Для L2-режима / валидации. |
| **Альтшуль/Калицун/Майрановский** «Примеры расчётов по гидравлике» 1977 | [obuchalka.org](https://obuchalka.org/2013061371819/primeri-raschetov-po-gidravlike-altshul-a-d-kalicun-v-i-mairanovskii-f-g-1977.html) | Числовые примеры, не «Гидравлические сопротивления» как монография. |
| **Лукиных А.А., Лукиных Н.А.** «Таблицы для гидравлического расчёта канализационных сетей и дюкеров (Павловский)» 1974 | [petro-eng.ru PDF](https://petro-eng.ru/doc%20info/libr/tablici_lukinyh.pdf) / [c-o-k.ru](https://www.c-o-k.ru/library/document/13688) | Самотёчная гидравлика. Не для нашего напорного, но пригодится для будущих расширений. |
| **Лукиных онлайн-калькулятор** | [vik.by](https://vik.by/instruments/30-lukinyh) / [rtp.ru](https://rtp.ru/information/lukinyh/) | Готовый веб-инструмент для Q-сравнения. |
| **СУСУ методичка по гидроудару** | [PDF](https://www.miass.susu.ru/wp-content/uploads/2023/06/gidravlicheskii_ydar.pdf) | Расчёт T_крит и амплитуды для непрямого удара (у нас сейчас бинарный триггер L>500). |

### Англоязычные

| Источник | URL | Применение |
|---|---|---|
| **Crane TP-410** «Flow of Fluids Through Valves, Fittings & Pipe» | [PDF (RG старое изд.)](https://www.researchgate.net/profile/Brian-Hanley-6/post/.../Flow+of+Fluids+-+Through+Valve,+Fittings+and+Pipes.pdf) / [tp410.com платно](https://tp410.com) | K-factor с поправкой на Re. Эталонный референс международной инженерии. |
| **Wikipedia: Darcy friction factor** | [link](https://en.wikipedia.org/wiki/Darcy_friction_factor_formulae) | Все известные явные аппроксимации Колбрук-Уайт. |
| **EngineerExcel: Swamee-Jain** | [link](https://engineerexcel.com/swamee-jain-equation/) | Явная альтернатива fluids.friction_factor (fallback). |

---

## 2. Учебники по насосам

### Англоязычные (PDF свободные)

| Источник | URL | Применение |
|---|---|---|
| **Lobanoff & Ross** "Centrifugal Pumps: Design and Application" 2nd 1992 | [bayanbox.ir PDF](https://bayanbox.ir/view/5586871201060897614/01-LOBANOFF-PART-1.pdf) | Карты Ns/КПД, sanity-check для БД. |
| **Karassik et al.** "Pump Handbook" 4-е изд. 2008 | [accessengineeringlibrary платно](https://www.accessengineeringlibrary.com/content/book/9780071460446) | Method of characteristics для гидроудара в разветвлённых трассах. |
| **Grundfos Pump Handbook** | [scribd](https://www.scribd.com/doc/28664725/GRUNDFOS-Pump-Handbook) / [pdfcoffee](https://pdfcoffee.com/grundfos-pump-handbook-pdf-free.html) | Базовая теория; Grundfos engineering manual 2 RU — [PDF](https://www.grundfos.com/content/dam/local/ru-ru/page-assets/support/documents/book/book-ww-engineering-manual-2-70267333-0819.pdf). |
| **KSB Centrifugal Pump Lexicon** | [ksb.com](https://www.ksb.com/en-global/centrifugal-pump-lexicon) | Онлайн справочник: specific speed nq, suction specific speed S, affinity laws, system curve hysteresis. |
| **Flygt Midrange Design Recommendations** | [PDF](https://www.xylem.com/siteassets/brand/flygt/resources/flygt-resources/design-recommendations---for-pump-stations-with-midrange-centrifugal-flygt-wastewater-pumps.pdf) | Таблицы геометрии sump для каждого типоразмера + swirl angle ≤5°. |
| **Flygt PSS Handbook 2nd ed 2025** | [PDF](https://www.xylem.com/siteassets/brand/flygt/resources/guideline/flygt_pss-handbook_2nd-edition-2025_en-a4.pdf) | Air pockets / venting, формула air-release valves через профиль трассы. |
| **Wilo USA Pump Basics** | [Submersible Wastewater](https://wilo.com/us/en_us/Training/On-Demand-Resources/Pump-Basics/Submersible-Wastewater-Pump-Basics/) | Регистрация. |

### Hydraulic Institute Standards (платные, есть превью)

| Источник | Превью | Применение |
|---|---|---|
| **HI 9.6.1-2024** NPSH Margin | [pumps.org](https://www.pumps.org/2025/03/18/understanding-the-2024-updates-to-ansi-hi-9-6-1-rotodynamic-pumps-guideline-for-npsh-margin/) | NPSHR vs NPSH3, margin = max(1.0 м, 1.1×NPSHR). У нас «0.5–1.5 м» без обоснования. |
| **HI 9.6.3-2024** Operating Regions | [pumps.org](https://www.pumps.org/product/ansi-hi-9-6-3-rotodynamic-pumps-guideline-for-operating-regions/) / [ANSI Blog](https://blog.ansi.org/ansi/ansi-hi-96-3-2017-rotodynamic-pumps-aor-bep/) | Поправка POR на specific speed Ns: при Ns<4500 (US) или kW>1MW POR сужается. |
| **HI 9.6.7-2021** Viscosity | [pumps.org](https://www.pumps.org/product/ansi-hi-9-6-7-2021-rotodynamic-pumps-guideline-for-effects-of-liquid-viscosity-on-performance/) | Поправка для шламовых стоков ρ=1050–1200 (у нас в §13 уже учтена частично). |
| **HI 9.8-2024** Pump Intake Design | [TOC PDF](https://www.pumps.org/wp-content/uploads/2025/02/TOC-HI-9.8-2024.pdf) / [preview](https://webstore.ansi.org/preview-pages/HI/preview_ANSI+HI+9-8-1998.pdf) | **Формула минимального погружения**: `S/D = 1 + 2.3·Fr` (Fr = v/√(g·D)). У нас отсутствует. |

### Русские учебники по насосам

| Источник | URL | Применение |
|---|---|---|
| **Карелин В.Я., Минаев А.В.** «Насосы и насосные станции» 1986 МИСИ | [proektant.org PDF](https://www.proektant.org/books/1986/1986_Karelin_V_Ya_Minaev_A_V_Nasosy_i_nasosnye_stancii_Uchebnik_dlya_vuzov.pdf) | Совместная работа насос/сеть, тех-эк сравнение. |
| **Лобачёв П.В.** «Насосы и насосные станции» | [stroykanasha.ru PDF](https://stroykanasha.ru/upload/iblock/23f/Lobachev_Nasosy_i_nasosnye_stantsii.PDF) | |
| **Турк, Минаев, Карелин** «Насосы и насосные станции» 1976 | [Totalarch](https://books.totalarch.com/pumps_and_pumping_stations_1976) | |
| **Яковлев С.В., Ласков Ю.М.** «Канализация» 1987 МИСИ | [djvu.online](https://djvu.online/file/XanlW0WUjJKpG) | Учебник, разделы по КНС. |
| **ГМС Ливгидромаш** ГНОМ-каталог | [hms-livgidromash.ru](https://www.hms-livgidromash.ru/catalog/nasosy-gnom-drenazhnye-pogruzhnye-monoblochnye-dlya-gryaznoy-vody.html) | Паспорта серии для пополнения БД. |
| **Ливнынасос** НФК | [livnasos.ru](https://www.livnasos.ru/) | |

---

## 3. КНС/нормативы РФ

### Нормативные документы

| Источник | URL | Что там |
|---|---|---|
| **СП 32.13330.2018 + Изм.№1–4** | [eng-in PDF](https://www.eng-in.ru/images/spravka/normativ/SP32133302018.pdf) / [meganorm](https://meganorm.ru/mega_doc/norm_update_26042025/pravila/0/sp_32_13330_2018_svod_pravil_kanalizatsiya_naruzhnye_seti_i.html) / [docs.cntd.ru](http://docs.cntd.ru/document/554820821) / [TN.ru Изм.№2](https://nav.tn.ru/documents/regulatory/ast_s_sp_32_13330_2018_izm2/) | Базовый СП. Табл.16/17, п.7.4, п.8.2.10, п.8.2.15. |
| **СП 31.13330.2021** Водоснабжение | [Минстрой PDF](https://www.minstroyrf.gov.ru/upload/iblock/02f/31.pdf) / [docs.cntd.ru](https://docs.cntd.ru/document/728474306) | **п.11 регламентирует гидрорасчёт напорной канализации** (СП 32 делегирует) — это упущено в нашей цитате. |
| **СП 30.13330.2020** Внутренние ВиК | [ГАРАНТ табл.А.2](https://base.garant.ru/400383625/b89690251be5277812a78962f6302560/) / [Минстрой PDF](https://minstroyrf.gov.ru/upload/iblock/f41/SP-30.pdf) | Нормы л/сут·чел. У нас 11 строк, реально ~50. |
| **МДС 40-2.2000** | [meganorm](https://meganorm.ru/Data2/1/4294851/4294851725.htm) | Мини-КНС для частных домов <1 м³/сут. |
| **СП 40-102-2000** Полимерные трубы | [docs.cntd.ru](http://docs.cntd.ru/document/1200007490) | Для ПЭ100 SDR. |

### Методички и онлайн-калькуляторы

| Источник | URL | Что там |
|---|---|---|
| **АВОК** «Расчёт КНС по сводам правил» (статья 8095) | [abok.ru](https://www.abok.ru/for_spec/articles.php?nid=8095) | Расширенная формула резервуара с учётом Q_min, не только Q_max. |
| **Журнал ВСТ 2014/1** Расчёт ёмкости приёмного резервуара | [vstmag.ru](http://www.vstmag.ru/ru/archives-all/2014/2014-1/5025-raschet-jemkosti-prijemnogo) | |
| **Flotenk** Расчёт приёмного резервуара | [flotenk.ru](https://flotenk.ru/press-centr/posts/raschet-priemnogo-rezervuara-dlya-kanalizatsionnoy-nasosnoy-stantsii/) | Формулы для 1 и нескольких насосов, табл z. |
| **Stormwater** Несколько однотипных насосов | [stormwater.ru](http://stormwater.ru/o-kompanii/stati/raschet-emkosti-priemnogo-rezervuarakns-s-neskoljkimi-odnotipnymi-rabochimi-nasosami/) | Расширенная формула с (α-1)·ΔH·S. |
| **Shop-Flumtec** Российский+европейский подход | [shop-flumtec.ru](https://shop-flumtec.ru/blog/obzory/raschyet-kns/) | Беларусь СН 4.01.02-2019: V_p = 0.9·Q_h/z. |
| **MFMC Коломна** Методика подбора | [kolomna.mfmc.ru](https://kolomna.mfmc.ru/info/articles/raschet-proizvoditelnosti-kanalizatsionnoy-nasosnoy-stantsii/) | Полная цепочка Q→H→V. |
| **HelyX systems** Пример расчёта | [PDF](https://helyx-systems.com/calculators/include/pdf/kns/example.pdf) | Разбор конкретной задачи. |
| **Лимкор** Расчёт КНС | [limkor.org](https://www.limkor.org/stati/raschet-kns.htm) | |
| **НИИ ВОДГЕО 2015** Поверхностный сток | [vo-da.ru](https://www.vo-da.ru/book/guide) | КНС поверхностного стока. |

---

## 4. Что узнал — ключевые формулы и правила, которых у нас нет

### 4.1 Гидравлика

| # | Формула / правило | Источник | Куда добавить |
|---|---|---|---|
| H1 | Скорость ударной волны через модули упругости: `a = 1/√(ρ·(1/K_ж + D/(E_тр·δ)))` — даёт зависимость от SDR (ПЭ100 SDR17 a≈350 м/с, SDR21 a≈300) | Чугаев §17 | `coefficients.json::wave_speed_ms_by_pipe_material` — расширить на SDR |
| H2 | Непрямой гидроудар: `ΔH = ΔH_прям × (T_крит/t_закрытия)` при t > T_крит | СУСУ методичка | `formulas.md §11` — расширить от бинарного триггера |
| H3 | Поправка ζ_отвода на Re при Re<10⁵ (множитель 1.3–2.0) | Идельчик гл.6 | `coefficients.json::local_resistance_zeta` |
| H4 | Шевелев `1000·i = A·v²/D^m` | Шевелев 2007 | Новый блок `shevelev_AM_table` для L2-режима |
| H5 | Swamee-Jain как fallback для friction_factor | Wikipedia | `hydraulics.py::calc_friction_factor` |
| H6 | k_э для корсис: ПЭ100 (k=0.007) + локальные ζ ≈0.05 на стык каждые 6 м | inner.su, СП 31 п.11 | engineer_note к korsis |

### 4.2 Насосы

| # | Формула / правило | Источник | Куда |
|---|---|---|---|
| P1 | **Specific speed Ns** = `n·√Q / H^0.75` — фильтр и penalty для Ns<15 (низкий КПД) или Ns>80 (риск кавитации) | KSB Lexicon, Lobanoff гл.2 | `matching.py::composite_score` — добавить Ns_compatibility |
| P2 | **Suction specific speed S** > 11000 (US) — кавитация на нижней границе AOR | Lobanoff гл.2 | Penalty в score |
| P3 | NPSHR vs NPSH3, margin = `max(1.0 м, 1.1·NPSHR)` | HI 9.6.1-2024 | `formulas.md §4` — заменить «0.5–1.5 м» |
| P4 | Поправка POR на Ns: при Ns<4500 (US) или kW>1MW POR сужается до 80–110% | HI 9.6.3-2024 | `coefficients.json::ansi_hi_963_operating_regions` |
| P5 | **Минимальное погружение S/D = 1 + 2.3·Fr** (Fr = v/√(g·D)) | HI 9.8 | Новый блок `intake_design` в coefficients |
| P6 | **Swirl angle ≤ 5°** в форбуэе | HI 9.8, Flygt | Чек-лист для геометрии корпуса |
| P7 | NPSHr при VFD-режиме корректировать на N² | HI 9.6.1-2024 | NOT_OK |
| P8 | Параллельная работа разных насосов — overload меньшего | Lobanoff гл.7 | NOT_OK |

### 4.3 КНС / резервуар

| # | Формула / правило | Источник | Куда |
|---|---|---|---|
| K1 | **V_min = Q_1н × 5/60** м³ — нижний контроль объёма (откачка одним за 5 мин) | АВОК, Flotenk | `formulas.md §7` — новая формула |
| K2 | Расширенная формула для α≥2 насосов: `V = (T·Q)/(4n·1000) + (α-1)·ΔH·S` | Flotenk, Stormwater | `formulas.md §7` |
| K3 | **ΔP_сброс** ≥1 м (бытовые), ≥3–5 м (дождевые) — добавить в `H_full` | МФМЦ, СП 31 | `formulas.md §1` |
| K4 | z (пусков/час) по СП 32 п.8.2.15: ≤22 кВт→6, 22–55→10, ≥55→15 — у нас перевёрнуто | СП 32, АВОК | `coefficients.json::pump_starts_per_hour_max` — пересмотреть! |
| K5 | Дождевая канализация: z=10–20, скорость самоочищения 0.6 м/с при P=0.33 | АВОК | Отдельная ветка алгоритма |
| K6 | Минимальная скорость 1.0 м/с в напорной канализации — **жёсткий фильтр**, не рекомендация | СП 32 §5.4 | `hydraulics.py::auto_select_diameter_mm` |
| K7 | Якорная плита SF: `F_подъём = ρ_воды·g·V_корпуса; F_якоря = вес плиты + грунт − архимед; SF≥1.10` | Стандарт NPCA | Новая функция расчёта |
| K8 | Категория надёжности → требования к АСУ/АВР/складу (I — резерв на складе, II — поставка ≤72ч, III — без обязательств) | СП 32 п.6.1 | `coefficients.json::reliability_category_requirements` |
| K9 | Минимальное время цикла `t_min = 60/z` мин — рабочий объём `V_раб > (Q_нас−Q_приток)·t_min` | СП 32 п.8.2.15 | `formulas.md §7` |
| K10 | Минимальный диаметр самотёчной d≥150 мм, коллекторов d≥200 мм, напорной от 1 насоса d≥40 мм | СП 32 §5.3 | Жёсткий фильтр |

---

## 5. Дополнительные NOT_OK (24..35) к нашим 23

Из учебников и Hydraulic Institute материалов:

- **NOT_OK-24**: Stop-level ниже верхней части мотора без cooling jacket → перегрев (Crane Pumps, Wilo Basics)
- **NOT_OK-25**: Cooling jacket с pumped media стоков с волокнами → засорение охлаждающего контура (Grundfos Dry installation)
- **NOT_OK-26**: «Залив» сухопостовленного погружного через discharge при первом пуске — cavitation за минуты (Crane Pumps Dry Run)
- **NOT_OK-27**: Цилиндрический корпус КНС с плоским дном без бенчинга → накопление осадка, H2S, коррозия (Flygt Midrange)
- **NOT_OK-28**: Впуск напорки в приёмный резервуар выше уровня воды (cascade) → захват воздуха, swirl (HI 9.8, Flygt)
- **NOT_OK-29**: Outflow inlet напротив впуска насоса → swirl >5°, cavitation, vibration (HI 9.8)
- **NOT_OK-30**: NPSHr из паспорта при VFD-режиме без коррекции на N² (HI 9.6.1-2024)
- **NOT_OK-31**: Параллельная работа 2 насосов разной мощности — меньший в overload (Lobanoff гл.7)
- **NOT_OK-32**: Cutter-pump на L_напорки >50м с DN50 → fibres re-aggregate (ropes), забивает обратный клапан (Grundfos)
- **NOT_OK-33**: Stop level выше уровня минимального self-cleaning — осадок не вымывается (Flygt PSS)
- **NOT_OK-34**: PE100 SDR17 с горизонтальными петлями без vent valves в high points → air-pockets → recirculation (Flygt PSS)
- **NOT_OK-35**: Подбор насоса по Q без учёта Ns — низкий Ns даёт КПД ≤55%, высокий → кавитация (Lobanoff, KSB Lexicon)

---

## 6. Резюме приоритетов по влиянию на калькулятор

### Tier 1 — критично, ломает нынешний подбор:

1. **K4 (z по СП 32)** — у нас в `coefficients.json` шкала перевёрнута. Влияет на формулу V резервуара. **Срочный фикс.**
2. **K1 (V_min = Q×5/60)** — нижний контроль объёма отсутствует. Калькулятор может выдать резервуар, в котором насос будет cycling-смерть.
3. **K6 (мин.скорость 1.0 м/с — жёсткий фильтр)** — сейчас рекомендация, не фильтр. Может проходить D, при котором заиливание гарантировано.
4. **P5 (S/D = 1+2.3·Fr)** — расчёт высоты корпуса без формулы погружения. Корпус может быть слишком мелкий → кавитация.

### Tier 2 — улучшение качества:

5. **P1 (Ns в score)** — добавит penalty для Ns<15 и Ns>80, отсеет низкоэффективные.
6. **K2, K9 (расширенный V для α насосов + t_min)** — точнее для 2+1, 3+1 схем.
7. **NOT_OK-24..35** — расширение `ENGINEER_NOTES.md` с новыми анти-паттернами.

### Tier 3 — для будущих расширений:

8. **K7 (якорный SF)** — для зон с УГВ выше дна корпуса (юг РФ, прибрежные).
9. **H4 (Шевелев A,m)** — для L2-режима валидации.
10. **K8 (требования по категории надёжности → АВР/АСУ)** — для генерации спецификации ШУ.

---

## 7. Что делать в коде дальше

Конкретные правки идут в следующий коммит:
1. `02_dataset/theory/formulas.md` — добавить §15 «V_min, t_min, ΔP_сброс, мин.погружение» с формулами K1, K2, K9, P5, K3
2. `02_dataset/ENGINEER_NOTES.md` — добавить NOT_OK-24..35
3. `02_dataset/theory/coefficients.json` — добавить блоки `intake_design`, `reliability_category_requirements`; пересмотреть `pump_starts_per_hour_max` под СП 32
4. Новые тесты в `backend/tests/test_calibration_*` для эталонных чисел из учебников

Реальная имплементация всего этого в Python — отдельная фаза (Phase 8.5 «соответствие СП 32 и HI 9.6.x»). Сейчас фиксирую теорию.
