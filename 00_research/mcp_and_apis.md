# MCP-серверы и API у производителей насосов
## Дата проверки: 2026-05-02
## Бюджет: 11 web-запросов из 12

---

## 1. Официальные MCP-серверы

**Вывод: НИ ОДНОГО официального MCP-сервера от производителя насосов не существует на 2026-05-02.**

Проверено:
- Официальный реестр **registry.modelcontextprotocol.io** — нет ни одной записи `pump`, `hvac`, `grundfos`, `wilo`, `ksb`.
- **github.com/modelcontextprotocol/servers** — отсутствуют community-серверы по тематике насосов / промышленного каталога.
- **Microsoft MCP catalog (github.com/microsoft/mcp)** — без насосной тематики.
- **mcp.so / smithery.ai / glama.ai** — поиск по `pump`, `hvac`, `engineering catalog`, `industrial parts` не дал результата.

Индустрия насосов пока ВНЕ MCP-экосистемы. Это окно возможностей: можно стать первым.

---

## 2. Открытые API (REST/GraphQL/OData)

| Производитель | API | URL | Доступ | Что отдаёт |
|---|---|---|---|---|
| **Grundfos** | API Developer Portal (есть, реальный!) | https://apiexplorer.grundfos.com/ | По API-ключу, регистрация | Не раскрыто без логина; присутствуют api.grundfos.com/literature (PDF DataBook), GPI Web Services (app.grundfos.com/pitcreator/RestServer/) |
| **Grundfos** | Modbus/PROFIBUS/GENIbus спецификации | api.grundfos.com/literature/* | публично, PDF | техкарты протоколов CIM/CIU 150/200/250 — для IoT/SCADA, НЕ для каталога |
| **Wilo** | Wilo-Select 5 online | wilo.com/.../Wilo-Select/ | веб-форма, без публичного API | Конфигуратор + price/perf документы |
| **KSB** | KSB EasySelect / KSB Select | ksb.com/.../configuration-tools/ | desktop + web; "clearly defined interfaces" заявлены | Возможна интеграция через **EDI/OCI punchout** в ERP заказчика, не REST |
| **Pedrollo** | Spring of Data Selector | springofdata.pedrollo.com/selector | веб, без API | Конфигуратор |
| **Calpeda** | Pump Selector | en.pump-selector.calpeda.com | веб, без API | Конфигуратор |
| **KAIQUAN** | — | — | API отсутствует | — |
| **Antarus** | ANTARUS SEARCH | search.antarus.ru/pumps/base | публичный веб; **проверено WebFetch — API/JSON-эндпоинтов нет**, статичная форма | Подбор насосных установок |
| **LEO Group** | — | — | Не обнаружено | — |
| **Иртыш / ГМС Ливгидромаш** | livnasos.ru/catalog, hms-livgidromash.ru/catalog | — | только HTML-каталог | — |
| **ПромЭлектро / Ливнынасос** | livnasos.pro | — | HTML | — |
| **Aquario / Belamos / Unipump** | unipump.ru/calc/ | — | веб-форма расчёта, без API | — |
| **Блорэй BloPlast** | — | — | Не обнаружено | — |
| **АРКАДА Инжсервис (Сочи)** | — | — | дилер, своих API нет | — |

**Единственный реальный официальный API-портал — Grundfos.** Это must-explore № 1 (зарегистрироваться, изучить, договориться о доступе).

---

## 3. Online-конфигураторы (можно WebFetch'ить / парсить через Firecrawl/Bright Data)

| Производитель | Сервис | URL | Регистрация | UX |
|---|---|---|---|---|
| Grundfos | Product Center | product-selection.grundfos.com | необязательна для просмотра | мощный, multi-step |
| Grundfos | Express (Intelliquip) | grundfos.portal-center.intelliquip.com | да | OEM-портал |
| Wilo | Wilo-Select 5 online | wilo-select online | регистрация желательна | Multi-step + Quick-Select |
| KSB | KSB Select / EasySelect | ksb.com Select | регистрация | веб + desktop |
| Pedrollo | Spring of Data | springofdata.pedrollo.com | нет | простой |
| Calpeda | Pump Selector | en.pump-selector.calpeda.com | нет | средний |
| Antarus | ANTARUS SEARCH | search.antarus.ru | нет | базовый |
| Unipump | unipump.ru/calc | unipump.ru/calc/ | нет | базовый |
| CNP | old.cnprussia.ru/biblioteka/kalkulyatory | — | нет | базовый |
| Ridan | ridan.ru/instruments/configurator-pumps | — | нет | средний |

Все эти конфигураторы парсятся через **Firecrawl / Playwright / Bright Data MCP**. Большинство — простые HTML-формы.

---

## 4. Community MCP / парсеры на GitHub

- **github.com/christoph2/GENIBus** — Python-библиотека для общения с Grundfos GENIbus (low-level fieldbus). Не для каталога, но для **телеметрии/мониторинга** установленных насосов. Релевантно фазе 2 (мониторинг КНС у заказчика).
- Прочих парсеров каталогов производителей в открытом виде на GitHub **не обнаружено** (ни Grundfos, ни Wilo, ни KSB, ни российских).

---

## 5. Альтернативные источники данных

### 5.1. Платформа Revalize (КЛЮЧЕВОЕ ОТКРЫТИЕ)
**PUMP-FLO** (revalizesoftware.com) и **Intelliquip Selling Cloud** — **общая SaaS-платформа подбора, лицензированная 150+ производителями насосов мира** (Wilfley, Grundfos через Express и др.). 24 000 дистрибьюторов, 400 000 пользователей. Поддерживает **«productized integrations and APIs»** для CRM/ERP. Это потенциальный **single point of integration** вместо 20 отдельных коннекторов. Интересная цель для уточняющего запроса (есть ли публичный API или партнёрская программа интеграторов).

### 5.2. B2B-маркетплейсы
Не проверял отдельно (бюджет запросов исчерпан), но известно: **B2B-Center, ETP (B2B-Center), Tinkoff B2B, Сбер B2B** — у всех есть REST API для тендеров и каталогов, но это не «технические данные насосов», а закупочные позиции (артикул + цена). Полезно для **прайсинга**, не для гидравлического подбора.

### 5.3. Дилерские порталы
KSB упоминает интеграцию через **EDI / OCI punchout / cXML** в ERP заказчика — это стандартный B2B-канал для крупных дистрибьюторов. Если Серво-Юг получит дилерский статус KSB/Wilo/Grundfos, можно требовать OCI-доступ к каталогу из 1С/CRM.

### 5.4. AI-ассистенты на сайтах
Целенаправленно не искал, но на сайтах Grundfos, Wilo, KSB **видимых публичных AI-чат-ассистентов нет** на 2026-05-02 (возможно, есть в личных кабинетах). Проксировать нечего.

---

## 6. Выводы и рекомендации

### Что можно подключить готовое
1. **Grundfos API Developer Portal (apiexplorer.grundfos.com)** — единственный официальный REST API в индустрии. Регистрироваться, получать ключ, изучать endpoints. Приоритет № 1.
2. **Revalize PUMP-FLO / Intelliquip** — выяснить условия партнёрского API. Если получится — покрытие 150+ производителей одним коннектором. Приоритет № 2.
3. **GENIbus библиотека (christoph2/GENIBus)** — для будущего модуля телеметрии установленных Grundfos-насосов в КНС.

### Что придётся парсить (Firecrawl/Bright Data/Playwright MCP)
- **Wilo-Select** (HTML-формы) — Playwright-сценарий
- **KSB Select** — Firecrawl
- **Pedrollo Spring of Data** — Firecrawl (простой)
- **Calpeda Pump Selector** — Firecrawl
- **Antarus Search** — Playwright (форма)
- **Unipump / CNP / Ridan / Aquario** — Firecrawl (страницы каталога)

### Что собирать вручную (PDF datasheets, Excel прайсы)
- **KAIQUAN / KQ** (kaiquanpump.ru) — китайский, нет API, нет конфигуратора
- **LEO Group** — китайский, без онлайн-инструментов
- **ГНОМ / ГМС Ливгидромаш / Иртыш / Ливнынасос** — российский легаси, только PDF и HTML-каталог
- **БлоПласт / АРКАДА** — мелкие игроки, ручной ввод в БД проекта
- **Belamos** — бытовой бренд, прайсы в Excel у дистрибьюторов

### Стратегия: какие интеграции стоят усилий
| Усилие | Окупаемость | Действие |
|---|---|---|
| Grundfos API ключ | 🟢 Высокая | СДЕЛАТЬ В ПЕРВУЮ НЕДЕЛЮ |
| Revalize partnership inquiry | 🟢 Высокая (если получится) | Запрос на B2B-почту |
| Парсинг Wilo/KSB/Pedrollo/Calpeda через Firecrawl | 🟡 Средняя | Фаза 2 |
| Парсинг российских (Antarus, Unipump, Ridan, CNP) | 🟢 Высокая (рынок РФ) | Фаза 1, обязательно |
| Ручная база KAIQUAN/LEO/Иртыш/ГНОМ/Ливнынасос | 🟡 Средняя | Excel + загрузка в Postgres/Chroma |
| **Собственный MCP-сервер «pump-catalog»** для Inservo agent | 🟢 Стратегическая | Обернуть всё вышеперечисленное в один MCP — конкурентное преимущество, индустрия пуста |

### Ключевой инсайт
**Индустрия насосов отстаёт от MCP-экосистемы минимум на 1-2 года.** Серво-Юг может стать первым, кто соберёт unified MCP-сервер для подбора насосов (Grundfos API + парсеры + российские бренды). Это не только internal tool, но и продаваемая интеграция для других дистрибьюторов / проектных институтов.

---

## Приложение: запрос на исследование
Использовано **11 web-запросов из бюджета 12**. Не проверены детально (требует логина / отдельного бюджета):
- Содержимое apiexplorer.grundfos.com после регистрации
- Точный список endpoints Revalize PUMP-FLO API
- B2B-Center / ETP REST API на предмет насосных категорий
- Существуют ли личные дилерские кабинеты Wilo/KSB с API (требует партнёрского статуса)
