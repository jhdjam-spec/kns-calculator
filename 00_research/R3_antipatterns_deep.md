# R3. Deep Research — анти-паттерны подбора насосов (extension)

**Дата:** 2026-05-02
**Цель:** расширить базу NOT_OK новыми антипаттернами, не пересекаясь с уже зафиксированными NOT_OK-01..11.
**Источники:** ANSI/HI 9.6.3, Wilo USA, Grundfos, Pumps & Systems, AFT, Tsurumi, Homa, NPCA, Conteches, Jensen Precast, EPCOR, FHWA HEC-24, Ontario Sewage Works Design Guidelines, ИП Cycle Stop Valves, TDK, Macromatic.

---

## 1. BEP-зоны (POR / AOR)

**Стандарт:** ANSI/HI 9.6.3-2017 «Rotodynamic Pumps — Guideline for Allowable Operating Region».

| Регион | Диапазон от Q_BEP | Что означает |
|---|---|---|
| **POR** (Preferred Operating Region) | **70–120%** (для большинства), 80–115% (high-energy) | Зона с минимальной вибрацией, низким радиальным усилием, нормальным сроком службы подшипников/уплотнений. Continuous operation должна быть здесь. |
| **AOR** (Allowable Operating Region) | **40–150%** (расширенный, типично) | Манифактор-defined; жизнь компонентов снижена, но допустима. Кратковременно — OK, длительно — нет. |
| **за AOR** | <40% или >150% | Нестабильное течение, recirculation, кавитация на всасе/выходе, шок-нагрузки, разрушение подшипников за месяцы. |

**Что происходит при выходе за POR:**
- Вибрация растёт по U-кривой от BEP в обе стороны.
- Радиальное усилие на вал → деформация вала → ускоренный износ механических уплотнений (срок жизни ↓ в 2-5 раз).
- При Q << Q_BEP — internal recirculation, surface cavitation на лопастях колеса, эрозия.
- При Q >> Q_BEP — suction cavitation (NPSHr резко растёт), шум, питтинг.

**Связь с уже зафиксированным:** NOT_OK-06 («подбор по нижнему пределу диапазона производителя») — это частный случай AOR-нарушения. Расширяем до полной POR/AOR-логики.

**Калькулятор должен:**
- Для каждого кандидата считать `bep_distance = |Q_user − Q_BEP| / Q_BEP`.
- Жёсткий фильтр: если кандидат вне 40–150% (AOR) — исключать.
- Score-фильтр: предпочтение кандидатам в 70–120% (POR).
- В hand-off pack — явно показывать, в каком регионе работает выбранный насос.

---

## 2. NPSHa и кавитация (уточнение к NOT_OK-04)

**NOT_OK-04 закрыт частично:** для погружного NPSH «не лимитирует». Уточнение из деталей research:

**Где NPSH остаётся критичен ДАЖЕ для погружного:**
1. **T_жидкости > 40°C** (банно-прачечные, промстоки горячие): H_v растёт нелинейно. При T=60°C → H_v ≈ 2.0 м, при T=80°C → H_v ≈ 5.4 м.
2. **Низкий уровень в резервуаре** (cycling по нижнему поплавку): hsubmersion < hmin → подсос воздуха через воронку.
3. **Сильно узкий приёмный отсек** — высокая локальная скорость на всасе.

**NPSH margin (рекомендации Hydraulic Institute ANSI/HI 9.6.1):**
- **NPSHa − NPSHr ≥ 1.0 м (3.3 ft)** ИЛИ
- **NPSHa / NPSHr ≥ 1.1 (минимум), 1.3 (рекомендовано), 1.5+ (для горячих стоков и углеводородов)**.
- Для достижения 100% rated head — нужен margin 1.3–1.7.

**Антипаттерн (новый):**
NPSHa ≈ NPSHr (margin = 0) — паспортно «работает», реально кавитирует, шум, эрозия колеса за 6 месяцев.

---

## 3. Cycling (короткие циклы пуск-стоп) — расширение DEP-17

**Числа из reference (Cycle Stop Valves, Homa, Wilo):**
- Малые двигатели (<2.2 кВт) — типично 20-30 пусков/час max.
- Средние (3-15 кВт) — 10-15 пусков/час max.
- Крупные (15-90 кВт) — 4-8 пусков/час max.
- Очень крупные (>90 кВт) — 3-4 пуска/час max.

**Минимум run-time:** 1 минута работы + 1 минута паузы (для малых); для крупных — 5-10 мин run + 5-10 мин off.

**Дополнительно:**
- Пусковой ток 3-7×Iном → импульс тепла на обмотках. Каждый пуск = ~5-10 секунд эквивалент номинальной работы по тепловыделению.
- Submersible motors имеют **50% duty cycle limit** — не более 30 минут работы в час без специальной размерности.
- При cycling > z_max → класс изоляции обмоток F (155°C) пробивается за 1-3 месяца → межвитковое КЗ.

**Калькулятор обязан:**
- Применять `V_приём ≥ Q_max / (4·z_max)` (формула Pleasants для оптимального V — 4 пуска в цикле).
- При расчёте корпуса КНС — проверять, что V_рабочий объёма (между старт/стоп) даёт ≤ z_max пусков.
- При несовпадении — увеличить V_рабочий или показать предупреждение «требуется ЧРП для variable speed».

---

## 4. Air-locking в напорной канализации

**Новый антипаттерн:** длинная напорка с подъёмами без воздухоотводчиков.

**Где возникает:**
- На локальных high points трассы — газы менее плотны, накапливаются.
- При v < 0.7 м/с — нет уноса пузырей потоком.
- На пуске — воздух в трубах между стоп и старт.

**Последствия:**
- Эффективное сечение трубы уменьшается → H_тр растёт → насос смещается влево по кривой → Q падает → recirculation на колесе → перегрев → стоп.
- Possible reverse flow при остановке.

**Решения, которые калькулятор должен учитывать:**
- При L > 100 м и наличии подъёмов — в BOM добавлять **air release valve** (ARV) на high points.
- Минимальная скорость v ≥ 0.9 м/с для самоочистки (выше «безиливающего» 0.7 м/с — это другое требование).
- Loop-up на конце трассы (anti-siphon loop) — но это уже инженерное решение.

---

## 5. СПД-ошибки (расширение DEP-27, 28, 29)

### 5.1 Размер мембранного бака
**Рекомендация (Wessels, Grundfos, JMP):**
`V_бак ≥ 0.5 × Q_max (л/мин) × минимальный run-time (мин)` — типично **V_бак ≥ Q_max × 1 мин** (как в DEP-28, OK).

Уточнение: **prefactor для air = (P_cut_in − 2 psi) / atmosphere**. Если bak пустой — давление воздуха = 2 psi ниже cut-in.

**Дельта старт/стоп ΔP:**
- Минимум 0.5 бар (7 psi) — иначе cycling.
- Рекомендовано 1.0-1.4 бар (14-20 psi).
- Если ΔP < 0.5 бар — насос пускается каждые 5-10 секунд при малом разборе.

### 5.2 Контроль сухого хода
- Датчик всаса P > 0.2-0.5 бар (3-7 psi) — порог отключения.
- Альтернатива: датчик уровня в источнике.
- Без защиты — выгорание уплотнений за 30 секунд (DEP-29 OK).

### 5.3 Гидроудар при остановке многоступенчатого
**Новый антипаттерн:** многоступенчатый (CR/MVI) высоконапорный без soft-stop при отключении питания → клапан хлопает → ΔP по Жуковскому 30-50 м → разрыв труб у фланцев.

**Решения:**
- Bypass loop с обратным клапаном медленного закрытия.
- Pressure surge tank (анти-гидроударный бак).
- ЧРП с программируемым ramp-down (5-10 сек).

---

## 6. Wearing parts и MTBF

**Литература (Pumps & Systems, Tsurumi, Homa, KSV):**

| Компонент | Типичный ресурс (часы) | Примечание |
|---|---|---|
| Импеллер vortex (хоз-быт) | 15 000–30 000 | Чугун, без абразива |
| Импеллер vortex (промстоки абразив) | 3 000–8 000 | Нерж 304/316 износ |
| Импеллер cutter (ножи) | 2 000–5 000 | Тряпьё → щербит лезвия |
| Механические уплотнения SiC/SiC | 8 000–15 000 | Стандарт wastewater |
| Механические уплотнения Carbon/SiC | 3 000–8 000 | Уступает SiC/SiC |
| Подшипники качения (под двигателем) | 25 000–40 000 | При работе в POR |
| Подшипники при работе вне POR | 5 000–15 000 | Радиальное усилие × 2-3 |
| Масло в камере уплотнений | 1 500 ч / 6 мес | Замена планово (Homa FSP) |

**Новый антипаттерн:**
Калькулятор не показывает оценку TCO (total cost of ownership) с учётом MTBF — менеджер выбирает дешёвый чугунный импеллер для абразива → замена через год → суммарно дороже нерж 316 в 2 раза.

---

## 7. Шкаф управления — расширение DEP-23

### 7.1 Прямой пуск (DOL) > 7.5 кВт
**IEC и местные правила:**
- DOL допустим до **7.5 кВт** (стандартная практика).
- 7.5–22 кВт — **soft-start обязателен** (или Star-Delta).
- > 22 кВт ИЛИ cutter — **soft-start или ЧРП обязательны**.
- > 75 кВт — только **ЧРП** (плавный пуск дорог и менее эффективен).

**Антипаттерн:** прямой пуск 22 кВт → пусковой ток ~150-200 А → провал напряжения сети → срабатывает защита → износ контакторов → отказ за 6-12 мес.

### 7.2 Тепловая защита обмоток (PT100/PTC) — НОВЫЙ ОБЯЗАТЕЛЬНЫЙ
**Из поиска (TDK, Grundfos, WOLONG):**
- **PTC (термистор)** — switch-type, при 130-150°C сопротивление взлетает → реле даёт стоп. Для submersible — стандарт.
- **PT100** — измеряет фактическую температуру, нужен converter. Дороже, для крупных pumps.
- **Биметаллический thermal switch** — дешёвый, но менее надёжный.

**Антипаттерн (НОВЫЙ):** ШУ без термозащиты обмоток для погружного >5.5 кВт. При cycling/cavitation/AOR-работе — winding сгорает за недели.

### 7.3 Защита от обратной фазы (phase reversal)
**Из Macromatic, Grundfos MP204:**
- Centrifugal pump в реверсе НЕ повреждается мгновенно, но при длительном reverse rotation — обратная нагрузка на колесо, вибрация, износ подшипников за часы.
- Cutter в реверсе — НЕМЕДЛЕННОЕ заклинивание ножей.

**Антипаттерн (НОВЫЙ):** ШУ без phase-monitor relay → при перекоммутации сети после АВР — пуск в реверсе.

### 7.4 Защита от пропадания фазы (single-phasing)
- Один работающий phase → 2× ток на оставшихся → сгорание за 5-30 секунд.
- Стандартная mechanical overload reaction time — 20 сек, electronic — < 100 мс.

**Антипаттерн:** только thermal overload без electronic phase monitor для крупных насосов >7.5 кВт.

---

## 8. Корпус КНС — расширение DEP-25, DEP-26

### 8.1 H/D > 4 — неудобство монтажа (уточнение DEP-25)
**Источники:** EPCOR, Jensen Precast, Ontario Design Guidelines.

- **H/D ≤ 3** — оптимум для обслуживания.
- **H/D = 3-4** — допустимо, требует кран-балку или подъёмные приспособления.
- **H/D > 4** — узкий длинный колодец, неудобен для подъёма насосов на цепях.
- **Глубина > 7.3 м (24 ft)** — спецтребования по нормам US (для РФ — индивидуально).

**Дополнительно:**
- Минимум 7 ft headroom над work platform.
- Hatch минимум 24" (610 мм) или больше — должен пройти насос с цепями.

### 8.2 Подъёмная сила при УГВ — расчёт (расширение DEP-26)
**Формула (NPCA Buoyancy White Paper):**
`F_uplift = V_displaced × ρ_water × g`
`F_resist = W_корпус + W_ballast + W_грунт_над_расширением + F_трения_грунт`
`SF = F_resist / F_uplift ≥ 1.10` (норма) или **≥ 1.25** (зоны с УГВ или подтоплением).

**Антипаттерн (НОВЫЙ):** ПЭ корпус (ρ=0.97) с УГВ выше дна без anchoring → SF<1 при опорожнении на сервис → всплывает с разрывом подводящего колодца.

### 8.3 Минимальный зазор между насосом и стенкой
**Источники:** Wilo, Tsurumi, Astral.

- **Submersible borewell:** зазор от стенки скважины ≥ 10-15 мм для установки и flow cooling.
- **Submersible wet-well wastewater:** clearance от стенки ≥ 100 мм (для рециркуляции охлаждающего потока вокруг мотора).
- **Без shroud:** скорость потока вдоль мотора > 0.5 м/с — обязательное условие охлаждения.
- **С shroud:** диаметр shroud на 50-100 мм больше насоса, форсирует поток вдоль мотора.

**Антипаттерн (НОВЫЙ):**
Подбор корпуса D = D_насоса + 100 мм (компактно) → нет cooling flow → перегрев мотора → срабатывание PTC каждые 20 минут → cycling смерть.

---

## НОВЫЕ NOT_OK для добавления в ENGINEER_NOTES

| ID-предлож | Краткая формулировка | Где зафиксировать |
|---|---|---|
| **NOT_OK-12** | Подбор насоса вне AOR (40-150% Q_BEP) — даже если попадает в Q-диапазон производителя, длительная работа разрушит подшипники и уплотнения | algorithm logic, ужесточить фильтр DEP-12 |
| **NOT_OK-13** | NPSH-расчёт игнорируется при T_жидкости > 40°C даже для погружных — горячие стоки кавитируют (банно-прачечные, промстоки) | дополнить NOT_OK-04, расширить DEP-11 |
| **NOT_OK-14** | СПД с ΔP старт/стоп < 0.5 бар → cycling каждые 5-10 секунд, выгорание мотора | новая ветка DEP-28 |
| **NOT_OK-15** | Многоступенчатый СПД без soft-stop / surge protection → гидроудар при отключении → разрыв труб | расширение DEP-27 |
| **NOT_OK-16** | ШУ без PTC/PT100 для погружных > 5.5 кВт — мотор сгорает при первом cycling-сценарии или AOR-работе | расширение DEP-23 |
| **NOT_OK-17** | ШУ без phase-monitor relay (reverse + single-phasing) для трёхфазных насосов > 7.5 кВт | новый DEP в Слое 7 |
| **NOT_OK-18** | Прямой пуск (DOL) > 7.5 кВт — провалы сети, износ контакторов, штрафы от энергоснабжающей | уточнение DEP-23 |
| **NOT_OK-19** | ПЭ-корпус с УГВ выше дна без anchoring SF≥1.25 → всплытие при опорожнении на сервис | дополнить DEP-26 |
| **NOT_OK-20** | Корпус с зазором от насоса до стенки < 100 мм → нарушение cooling flow → перегрев мотора | новый под-DEP в Слое 8 |
| **NOT_OK-21** | Длинная напорка с подъёмами (>100 м, локальные high points) без air release valves → air-lock, остановка подачи | новый DEP в Слое 6 |
| **NOT_OK-22** | Корпус с H/D > 4 → неудобство обслуживания, требует крана для каждого ремонта | уточнение DEP-25 |
| **NOT_OK-23** | Подбор насоса без проверки минимального run-time (typ. 1 мин on / 1 мин off для малых; 5-10 мин для крупных) — мотор перегревается даже в пределах z_max | расширение DEP-17 |

---

## Источники

1. ANSI/HI 9.6.3-2017 — Rotodynamic Pumps Guideline for AOR — https://blog.ansi.org/ansi/ansi-hi-96-3-2017-rotodynamic-pumps-aor-bep/
2. National Pump Company — POR/AOR — https://www.nationalpumpcompany.com/blog/understanding-preferred-allowable-operating-regions
3. Wilo USA — Beyond BEP — https://wilo.com/us/en_us/Training/On-Demand-Resources/Pump-Basics/Operating-Past-BEP/
4. Pumps & Systems — NPSH & Operating Regions — https://www.pumpsandsystems.com/basics-npsh-pump-operating-regions
5. AFT — API-610 BEP recommendations — https://www.aft.com/support/product-tips/are-you-operating-your-pump-off-bep
6. National Pump Company — NPSH Margin — https://www.nationalpumpcompany.com/blog/net-positive-suction-head-npsh-margin
7. WaterWorld — NPSH Margin Important — https://www.waterworld.com/water-utility-management/energy-management/article/16193233/sufficient-npsh-margin-important-to-pump-reliability
8. Cycle Stop Valves — Frequency of Starts — https://cyclestopvalves.com/pages/frequency-of-starts
9. Homa Pump — Submersible failure causes — https://homapump.com/submersible-pump-failure-causes-fixes/
10. Pumps & Systems — Air Valves for Wastewater — https://www.pumpsandsystems.com/air-valves-wastewater
11. Envirep — H-Tec Air Release Valves — https://www.envirep.com/air-release-valves-ensuring-optimal-performance-of-your-force-main/
12. JMP Co — Domestic Water Pressure Booster Sizing — https://jmpco.com/Files/Files/Whitepapers/JMP%20Domestic%20Water%20Pressure%20Booster%20Sizing%20A%20Road%20Map%20for%20Success%20-%20White%20Paper.pdf
13. Wessels — Sizing Pressure Tanks — https://www.westank.com/how-to-size-well-water-and-pressure-booster-tanks/
14. Grundfos — Diaphragm Tank Calculation — https://api.grundfos.com/literature/Grundfosliterature-6859247.pdf
15. Pumps & Systems — Surge Control in Pumping Stations — https://www.pumpsandsystems.com/surge-control-pumping-stations
16. Valmatic — Surge Control PDF — https://www.valmatic.com/Portals/0/pdfs/SurgeControlinPumpingSystems_6-18.pdf
17. Pumps & Systems — Mechanical Seal Design — https://www.pumpsandsystems.com/mechanical-seal-design-protects-submersible-pumps-abrasive-wastewater
18. Tsurumi — Maintenance Tips — https://tsurumipumps.com.au/2026/01/14/maintenance-tips-for-submersible-pumps/
19. Homa — Preventative Maintenance — https://homapump.com/preventative-maintenance-submersible-pumps/
20. Electrical Engineering Portal — DOL Starter — https://electrical-engineering-portal.com/direct-on-line-dol-motor-starter
21. Rockwell — Soft Starter vs VFD — https://literature.rockwellautomation.com/idc/groups/literature/documents/wp/150-wp007_-en-p.pdf
22. Grundfos — PTC Thermistors — https://www.grundfos.com/solutions/learn/research-and-insights/ptc-thermistors
23. TDK — PTC Motor Protection — https://www.tdk-electronics.tdk.com/inf/55/db/PTC/PTC_Motor_protection_M1100.pdf
24. The Driller — Three-phase Pump and Motor Protection — https://www.thedriller.com/articles/86540-three-phase-pump-and-motor-protection
25. Grundfos — Protecting three-phase submersible motors — https://www.grundfos.com/solutions/learn/ecademy/all-courses/the-sp-submersible-pump/protecting-three-phase-submersible-motors
26. NPCA — Buoyancy White Paper — https://www.ajfoss.com/wp-content/uploads/2022/08/NPCA-Buoyancy-White-Paper-2022.pdf
27. Conteches — Stormwater Detention Buoyancy — https://www.conteches.com/knowledge-center/learn/the-stormwater-blog/will-it-float-understanding-stormwater-detention-buoyancy-calculations/
28. Tank Depot — Underground Tank Flotation — https://www.tank-depot.com/blog/complete-guide-on-how-to-prevent-underground-storage-tank-flotation
29. Wilo USA — Submersible Wastewater Pump Basics — https://wilo.com/us/en_us/Training/On-Demand-Resources/Pump-Basics/Submersible-Wastewater-Pump-Basics/
30. EPCOR — Pump Station and Forcemain Design Guidelines — https://www.epcor.com/content/dam/epcor/documents/supporting-documents/volume-3-04-pump-station-and-forcemain-design-guidelines.pdf
31. Jensen Precast — Wet Well Diameter — https://www.jensenprecast.com/resource-hub/product-resources/pump-stations-wet-well-diameter/
32. Astral Pipes — Submersible for Borewell — https://www.astralpipes.com/blogs/how-to-select-submersible-pump-for-borewell/
33. WIKA — Pressure switches in booster pumps — https://blog.wika.com/en/applications/pressure-switches-in-booster-pumps/
34. Wikipedia — Dry running protection — https://en.wikipedia.org/wiki/Dry_running_protection
