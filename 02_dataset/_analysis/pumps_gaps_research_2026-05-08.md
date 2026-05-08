# Pumps Gaps Research — 2026-05-08

Цель: закрыть 4 критические дыры покрытия Q-H в БД насосов калькулятора КНС/НС/ЛОС
(текущие 223 насоса, 16 брендов).

Все данные — из открытых источников: сайты производителей и официальных дилеров РФ,
интернет-магазины, технические каталоги в PDF. Цены РФ берутся как ориентир («от»).
Где паспорт открыто не нашёл — пометка `requires_dealer_quote = true`.

---

## ТОП-10 моделей для закрытия дыр

### Зона 1. Q≥1500 м³/ч, H=5–10 м (большие дренажные/ливневые)

#### 1.1 Sulzer ABS XFP 305M / 305N

- ID: `sulzer-xfp-305m`
- Бренд / модель: Sulzer ABS XFP 305 (Premium Efficiency IE3)
- Q_BEP: 1800–2400 м³/ч (DN300), H_BEP: 8–14 м, P_kW: 75–120, NPSHr: ~6 м
- Цена: открыто не публикуется, ориентир ≥ 4 500 000 ₽, **требует запроса дилеру**
- Источник: <https://www.sulzer.com/-/media/files/products/pumps/submersible-pumps/brochures/xfp_submersiblepumps_e10238.pdf>
- Закрывает: Q=1500–2500, H=8–14 (большие КНС бытовых стоков, ливневая магистральная)

#### 1.2 ANDRITZ Ritz серии SW 22 — модель SW 200-460.Z/A/TV

- ID: `andritz-sw-200-460-z`
- Q_BEP: ~1100–1600 м³/ч, H_BEP: 8–12 м, P_kW: ~75
- Цена: запрос дилеру (Sevit, Baumgroup), не публикуется открыто
- Источник: <http://sevit.pro/product/sw-22-%D0%BC%D0%BE%D0%B4%D0%B5%D0%BB%D1%8C-sw-200-460-z-a-tvam3g-141-4-ds-mk/>,
  <https://baumgroup.ru/produktsiya/nasosy/proizvoditeli/andritz/>
- Закрывает: Q=1100–1600, H=8–12 (промливневая, дренаж карьеров)

#### 1.3 KSB Sewatec D 300 / D 350 (сухая установка)

- ID: `ksb-sewatec-d300`
- Q_BEP: 1500–3000 м³/ч (общий диапазон серии до 5040 м³/ч), H_BEP: 10–25 м, до 93 м
- Цена: ушёл с рынка РФ, через параллельный импорт Hycom / Кронштадт
- Источник: <https://www.ksb.com/ru-ru/lc/produkcija/nasos/nasos-suhoj-ustanovki/sewatec/S02B>,
  <https://www.kron.spb.ru/products/nasosnoe-oborudovanie/ksb/ksb-sewatec/>
- Закрывает: Q=1500–3000, H=10–25 (городская КНС, очистные)

---

### Зона 2. Q=3000–5000 м³/ч, H=10–30 м (магистральные)

#### 2.1 Насосэнергомаш СД 2400/75 (1СД2400/75)

- ID: `nem-sd-2400-75`
- Q_BEP: 2400 м³/ч, H_BEP: 75 м, P_kW: ~630, n=730 об/мин
- Цена: **1 365 650 ₽** (открыто, nprom.ru, 2025)
- Источник: <https://nprom.ru/nasos-1sd2400-75.html>,
  <https://www.nasosdon.ru/nasosy-sd-sdv>
- Закрывает: Q=2400, H=70–80 (на самом деле напорная, но единственный открытый РФ-аналог;
  закрывает зону 4 «H=80, Q=2400»)

#### 2.2 KSB Sewatec K (большие типоразмеры до 10 000 м³/ч)

- ID: `ksb-sewatec-k600`
- Q_BEP: 3500–6000 м³/ч, H_BEP: 15–30 м
- Цена: запрос дилеру (Hycom, Кронштадт)
- Источник: <https://hycom.ru/catalog/pumps/sewatec>
- Закрывает: Q=3000–5000, H=10–30 (городские КНС Водоканала)

#### 2.3 Sulzer ABS XFP 401 / 601

- ID: `sulzer-xfp-601`
- Q_BEP: 3000–5000 м³/ч, H_BEP: 10–20 м, P_kW: 250–520
- Цена: запрос дилеру, ориентир ≥ 9 000 000 ₽
- Источник: <https://www.sulzer.com/en/shared/products/submersible-sewage-pump-type-abs-xfp>
- Закрывает: Q=3000–5000, H=10–20 (магистраль, очистные крупных городов)

---

### Зона 3. H=100–200 м, Q=20–100 м³/ч (СПД I категории, пожарные)

#### 3.1 Wilo Helix V 5205-2/16/V (артикул 4150909)

- ID: `wilo-helix-v-5205-2-16`
- Q_BEP: 50–80 м³/ч, H_BEP: ~180 м (16 ст.), P_kW: 30–37, NPSHr: ~3,5 м
- Цена: **1 133 682 ₽** (открыто, wl-russia.ru, 2025)
- Источник: <https://wl-russia.ru/vertikalnyj-mnogostupenchatyj-nasos-wilo-helix-v-5205-2-16-v>
- Закрывает: H=150–200, Q=50–80 (СПД I кат., пожаротушение высотных)

#### 3.2 KSB Movitec V 60/12 / V 90/8 (вертикальный высокого давления)

- ID: `ksb-movitec-v60-12`
- Q_BEP: 60–90 м³/ч, H_BEP до 228 м (по серии), P_kW до 22 (макс. серии)
- Цена: запрос дилеру (Hycom)
- Источник: <https://www.ksb.com/ru-ru/lc/produkcija/nasos/sekcionnyj-nasos-/movitec/M12A>,
  <https://hycom.ru/catalog/pumps/movitec-v-vf-vs>
- Закрывает: H=100–200, Q=60–90

#### 3.3 Grundfos CR 95 / CR 125 / CR 155 (high-flow vertical multistage)

- ID: `grundfos-cr-95-5`
- Q_BEP: 95–155 м³/ч, H_BEP: 100–250 м (до ~50 бар по серии), P_kW: 22–75
- Цена: запрос дилеру, через параллельный импорт. Серия CR — до ~725 psi (~500 м напора)
- Источник: <https://www.grundfos.com/us/campaign/new-cr>,
  <https://api.grundfos.com/literature/Grundfosliterature-1847.pdf>
- Закрывает: H=100–250, Q=95–155 (СПД I кат. крупных объектов)

---

### Зона 4. H=80 м, Q≥600 м³/ч (мощные напорные СПД)

#### 4.1 KSB Etanorm 200-150-400 (CC01 / CC11)

- ID: `ksb-etanorm-200-150-400`
- Q_BEP: 350–600 м³/ч, H_BEP: 60–80 м (по типоразмеру 400), P_kW: 45 (паспорт),
  до 90 кВт в варианте 1450 об/мин
- Цена: запрос дилеру, но артикул открыт у нескольких дилеров
- Источник: <https://ksb.nt-rt.ru/price/product/1452699>,
  <https://heat-energy.ru/ksb/nasosy-ksb-etanorm/nasos-ksb-etanorm-200-150-400-cc01-art-48254647>
- Закрывает: Q=400–600, H=60–80 (крупные СПД ВНС)

#### 4.2 Pedrollo F 65/250C (горизонтальный консольный)

- ID: `pedrollo-f-65-250c`
- Q_BEP: 100 м³/ч, H_BEP: 68 м, P_kW: 30, DN_in/out: 80/65
- Цена: **783 328 – 792 220 ₽** (открыто, e-nasos.ru, teploprofi.com, 2025)
- Источник: <https://e-nasos.ru/poverhnostnye/pedrollo/tsentrobejnye/f/f65-250/f-65-250c>,
  <https://www.teploprofi.com/catalogue/show/nasos-pedrollo-f-65-250c/>
- Закрывает: H=60–80, Q=80–110 (средние СПД); НЕ закрывает Q≥600 — это бэкап для нижней
  части дыры. Для Q≥600 H=80 → 4.1 KSB Etanorm 200-150-400

#### 4.3 Catayskий насос-завод К 100-65-250 (открытый отечественный аналог)

- ID: `katayskiy-k-100-65-250`
- Q_BEP: 100 м³/ч, H_BEP: 80 м, P_kW: 45, n=2900 об/мин, масса 485 кг
- Цена: **125 600 ₽** (открыто, kontmotor.ru, 2025) — отечественный, дешёвый
- Источник: <https://kontmotor.ru/variant/153>
- Закрывает: H=80, Q=100 (бюджетный отечественный); для Q≥600 — нужен ANTARUS MPH/MLH
  по запросу через ANTARUS Search

---

## Что ещё проверить (action items)

1. **ANTARUS MLH / MPH** — горизонтальные многоступенчатые. Программа подбора
   <https://search.antarus.ru/pumps/base> закрывает все 4 зоны, но точные модели —
   только через инженерный запрос (нет открытого PDF-каталога с матрицей Q-H по моделям).
   Контакт: 8 (800) 550-50-70.
2. **CNP TD / TD-LCK / NLK** (китайская инженерная серия) — для замены KSB Etanorm.
   Открытый каталог + цены у dn.ru / cnpump.ru.
3. **СМЗ КИТ ВД 200-150-400 / ВД 300-280-580** — отечественный аналог Etanorm
   (Серпуховский МЗ). Открытые прайсы у smz-kit.ru.
4. **Wilo Rexa SOLID-Q (PE 200/250)** — DN300/DN400 для Q=1500–2500 H=10. Каталог PDF
   <https://cms.media.wilo.com/cdndoc/wilo198555/2110524/wilo198555.pdf> — содержит
   полную матрицу, нужно вытянуть BEP-точки.
5. **ГНОМ Ливгидромаш** — серия только до Q=300 м³/ч (10-10/16-25/100-25), для
   зоны 1 Q≥1500 НЕ подходит. Использовать только в L0 для малых КНС Q<300.

## Поля БД, которые добавить при импорте этих 10 моделей

- `price_rub_2026` — где открыто, проставить (модели 2.1, 3.1, 4.2, 4.3 — ✓ есть цена)
- `price_source_url` — обязательно
- `requires_dealer_quote` — bool, true для KSB / Sulzer / ANDRITZ / Grundfos
- `npshr_m` — паспортные значения (вытащить из PDF datasheets)
- `gap_zone` — enum: `Q1500_low_head` / `Q3000_main` / `H150_fire` / `H80_high_flow`
- `import_status` — enum: `available_RF` / `parallel_import` / `sanctioned`
- `verified_by` — string + дата

## Покрытие после импорта (расчётно)

| Дыра | Было | Станет |
|---|---|---|
| Q≥1500, H=5–10 | 0–2 | +3 (1.1 + 1.2 + 1.3) → 5+ |
| Q=3000+ | 3 | +2 (2.2 + 2.3) → 5 |
| H=150 м | 1 | +3 (3.1 + 3.2 + 3.3) → 4 |
| H=80, Q≥600 | 2 | +1 (4.1) → 3 |

Итого 10 новых моделей, 4 с открытыми ценами (2.1, 3.1, 4.2, 4.3),
6 требуют запроса дилеру.

## Источники (полный список)

- KSB: <https://www.ksb.com/ru-ru/>, <https://hycom.ru/>, <https://www.kron.spb.ru/>
- Sulzer: <https://www.sulzer.com/en/shared/products/submersible-sewage-pump-type-abs-xfp>
- ANDRITZ: <https://baumgroup.ru/produktsiya/nasosy/proizvoditeli/andritz/>,
  <http://sevit.pro/>
- Wilo: <https://wilo.ru/>, <https://wl-russia.ru/>,
  <https://cms.media.wilo.com/cdndoc/wilo198555/2110524/wilo198555.pdf>
- Grundfos: <https://www.grundfos.com/us/campaign/new-cr>,
  <https://api.grundfos.com/literature/Grundfosliterature-1847.pdf>
- Pedrollo: <https://e-nasos.ru/>, <https://www.teploprofi.com/>
- ANTARUS: <https://search.antarus.ru/>, <https://antarus.su/>
- Насосэнергомаш / СД: <https://nprom.ru/nasos-1sd2400-75.html>,
  <https://www.nasosdon.ru/nasosy-sd-sdv>
- Катайский НЗ: <https://kontmotor.ru/variant/153>
- Ливгидромаш ГНОМ: <https://www.hms-livgidromash.ru/catalog/nasosy/gnom/>
