# Instructions

- Following Playwright test failed.
- Explain why, be concise, respect Playwright best practices.
- Provide a snippet of code with the fix, if possible.

# Test info

- Name: mobile.spec.ts >> Mobile (375×667) >> Mobile phone link visible (tel:)
- Location: e2e\mobile.spec.ts:52:7

# Error details

```
Error: expect(locator).toBeVisible() failed

Locator:  locator('a[href^="tel:"]').first()
Expected: visible
Received: hidden
Timeout:  7000ms

Call log:
  - Expect "toBeVisible" with timeout 7000ms
  - waiting for locator('a[href^="tel:"]').first()
    10 × locator resolved to <a href="tel:+78002224457" class="hidden md:flex items-center gap-2 text-ink-50 text-sm font-mono hover:text-accent-500 transition-colors min-h-11">…</a>
       - unexpected value "hidden"

```

# Page snapshot

```yaml
- generic [active] [ref=e1]:
  - link "К содержимому" [ref=e2] [cursor=pointer]:
    - /url: "#main"
  - 'status "Статус калькулятора: бета-версия" [ref=e3]':
    - generic [ref=e4]:
      - img [ref=e5]
      - paragraph [ref=e7]:
        - strong [ref=e8]: Бета.
        - text: Точность ±15% — финальный расчёт у инженера.
  - banner [ref=e9]:
    - generic [ref=e10]:
      - link "И·С ИНСЕРВО" [ref=e11] [cursor=pointer]:
        - /url: "#hero"
        - generic [ref=e13]: И·С
        - generic [ref=e14]: ИНСЕРВО
      - generic [ref=e15]:
        - link "Позвонить 8 800 222 44 57" [ref=e16] [cursor=pointer]:
          - /url: tel:+78002224457
          - img [ref=e17]
          - generic [ref=e19]: 8-800
        - 'button "Тема: Авто. Нажмите чтобы переключить." [ref=e20] [cursor=pointer]':
          - img [ref=e21]
        - button "Открыть меню" [ref=e23] [cursor=pointer]:
          - img [ref=e24]
  - main [ref=e25]:
    - generic [ref=e30]:
      - generic [ref=e31]: КАЛЬКУЛЯТОР · 2026
      - heading "Подбор насоса для КНС, ЛОС и СПД за минуту" [level=1] [ref=e33]:
        - text: Подбор насоса
        - text: для КНС, ЛОС и СПД
        - text: за минуту
      - paragraph [ref=e34]: КНС — канализационные насосные станции · ЛОС — локальные очистные сооружения · СПД — станции повышения давления
      - paragraph [ref=e35]: От ТЗ до спецификации с гидравликой по СП 32.13330. Без регистрации. От производителя оборудования с 2009 года.
      - generic [ref=e36]:
        - generic [ref=e37]:
          - generic [ref=e38]: Расход Q, м³/ч
          - spinbutton "Расход Q, м³/ч" [ref=e39]: "21.2"
        - button "Рассчитать" [ref=e40] [cursor=pointer]:
          - text: Рассчитать
          - img [ref=e41]
      - generic [ref=e43]:
        - generic [ref=e44]:
          - img [ref=e45]
          - text: Без регистрации
        - generic [ref=e48]: ·
        - generic [ref=e49]:
          - img [ref=e50]
          - text: 284 модели в базе
        - generic [ref=e54]: ·
        - generic [ref=e55]:
          - img [ref=e56]
          - text: Производство в Адыгее
      - generic [ref=e59]:
        - button "Скачать техзадание DOCX" [ref=e60] [cursor=pointer]:
          - img [ref=e61]
          - text: Скачать техзадание DOCX
          - img [ref=e65]
        - button "Скачать опросный лист DOCX" [ref=e67] [cursor=pointer]:
          - img [ref=e68]
          - text: Скачать опросный лист DOCX
          - img [ref=e72]
    - generic [ref=e75]:
      - generic [ref=e76]:
        - generic [ref=e77]: ПРОЦЕСС
        - heading "Четыре минуты от ТЗ до спецификации" [level=2] [ref=e79]:
          - text: Четыре минуты от ТЗ
          - text: до спецификации
      - generic [ref=e80]:
        - generic [ref=e81]:
          - generic [ref=e82]:
            - generic [ref=e83]: "01"
            - img [ref=e84]
          - heading "Введите параметры" [level=3] [ref=e87]
          - paragraph [ref=e88]: Расход Q (м³/ч), напор H (м), тип объекта. Если не знаете расход — встроенный помощник посчитает по числу квартир, гостиничных номеров или площади кровли.
        - generic [ref=e89]:
          - generic [ref=e90]:
            - generic [ref=e91]: "02"
            - img [ref=e92]
          - heading "Алгоритм считает" [level=3] [ref=e95]
          - paragraph [ref=e96]: Гидравлика по СП 32.13330. Проверка попадания в рабочую зону насоса (AOR — Allowable Operating Range, POR — Preferred Operating Range по ANSI/HI). Фильтр по типу рабочего колеса (импеллера) и проходному сечению — чтобы насос не забивался волокнами или включениями. Сравнение 284 моделей за миллисекунды.
        - generic [ref=e97]:
          - generic [ref=e98]:
            - generic [ref=e99]: "03"
            - img [ref=e100]
          - heading "Получите спецификацию" [level=3] [ref=e103]
          - paragraph [ref=e104]: Топ-3 насоса в трёх ценовых сегментах (бюджет / средний / премиум) с диапазоном цены комплекта (±10%). Опросный лист DOCX и черновик BOM (списка оборудования) — для тендера или КП за 1 рабочий день.
    - generic [ref=e106]:
      - generic [ref=e107]:
        - generic [ref=e108]: Два режима работы
        - heading "Подбор насоса или проект целиком?" [level=2] [ref=e109]
        - paragraph [ref=e110]: Калькулятор работает в двух режимах. Выберите тот, что подходит вашей задаче.
      - generic [ref=e111]:
        - 'link "Полный расчёт проекта Рекомендуем Проект целиком Выбираете тип объекта (ИЖС, ЖК, АЗС, гостиница и т.п.), вводите базовые параметры — калькулятор прогонит расчёты по всем инженерным системам: КНС (канализация), ВНС (водоснабжение), пожаротушение, очистные (ЛОС), электрика, климат и прочность корпуса. Все расчёты сразу Ссылки на СП и ГОСТ Готов к защите проекта Для ГИП и инженера-проектировщика Запустить визард проекта" [ref=e112] [cursor=pointer]':
          - /url: /project
          - generic [ref=e113]:
            - generic [ref=e114]: Полный расчёт проекта
            - generic [ref=e115]: Рекомендуем
          - generic [ref=e116]: Проект целиком
          - generic [ref=e117]:
            - text: "Выбираете тип объекта (ИЖС, ЖК, АЗС, гостиница и т.п.), вводите базовые параметры — калькулятор прогонит расчёты по всем инженерным системам:"
            - strong [ref=e118]: КНС
            - text: (канализация),
            - strong [ref=e119]: ВНС
            - text: (водоснабжение), пожаротушение, очистные (ЛОС), электрика, климат и прочность корпуса.
          - generic [ref=e120]:
            - generic [ref=e121]: Все расчёты сразу
            - generic [ref=e122]: Ссылки на СП и ГОСТ
            - generic [ref=e123]: Готов к защите проекта
            - generic [ref=e124]: Для ГИП и инженера-проектировщика
          - generic [ref=e125]:
            - text: Запустить визард проекта
            - img [ref=e126]
        - 'link "Быстрый подбор насоса Только насос 4 поля: расход Q м³/ч, перепад высот dH м, длина напорной линии L м, тип стоков. Получаете топ-3 моделей в трёх ценовых сегментах с предварительной стоимостью комплекта. Для оперативного КП или ранней оценки бюджета. Подбор за 30 сек Бюджет / средний / премиум Только насос Для менеджера и ГИП Перейти к подбору" [ref=e128] [cursor=pointer]':
          - /url: "#calculator"
          - generic [ref=e129]: Быстрый подбор насоса
          - generic [ref=e130]: Только насос
          - generic [ref=e131]:
            - text: "4 поля: расход"
            - strong [ref=e132]: Q
            - text: м³/ч, перепад высот
            - strong [ref=e133]: dH
            - text: м, длина напорной линии
            - strong [ref=e134]: L
            - text: м, тип стоков. Получаете топ-3 моделей в трёх ценовых сегментах с предварительной стоимостью комплекта. Для оперативного КП или ранней оценки бюджета.
          - generic [ref=e135]:
            - generic [ref=e136]: Подбор за 30 сек
            - generic [ref=e137]: Бюджет / средний / премиум
            - generic [ref=e138]: Только насос
            - generic [ref=e139]: Для менеджера и ГИП
          - generic [ref=e140]:
            - text: Перейти к подбору
            - img [ref=e141]
      - link "📚 Или откройте Энциклопедию инженера ВК" [ref=e144] [cursor=pointer]:
        - /url: /teach
        - text: 📚 Или откройте Энциклопедию инженера ВК
        - img [ref=e145]
    - generic [ref=e149]:
      - generic [ref=e150]:
        - generic [ref=e151]: ПОДБОР
        - heading "Введите параметры объекта" [level=2] [ref=e153]
        - paragraph [ref=e154]: Расчёт сразу после ввода. Результат — топ-3 насоса в трёх ценовых сегментах (бюджет / средний / премиум) с диапазоном цены комплекта.
      - generic [ref=e156]:
        - generic [ref=e157]:
          - generic [ref=e158]:
            - generic [ref=e159]: Тип стоков
            - generic [ref=e160]:
              - button "Бытовая" [ref=e161] [cursor=pointer]
              - button "Дождевая" [ref=e162] [cursor=pointer]
              - button "Промышленная" [ref=e163] [cursor=pointer]
              - button "СПД (чистая вода)" [ref=e164] [cursor=pointer]
              - button "Пожаротушение" [ref=e165] [cursor=pointer]
            - generic [ref=e166]: Хозбытовые стоки от жилья и офисов
          - generic [ref=e167]:
            - generic [ref=e168]:
              - generic [ref=e169]: Расход Q
              - button "Не знаю Q" [ref=e170] [cursor=pointer]:
                - img [ref=e171]
                - text: Не знаю Q
            - generic [ref=e174]:
              - spinbutton "Расход Q" [ref=e175]: "21.2"
              - generic [ref=e176]:
                - button "м³/ч" [ref=e177] [cursor=pointer]
                - button "л/с" [ref=e178] [cursor=pointer]
                - button "м³/сут" [ref=e179] [cursor=pointer]
          - button "Расширенные параметры" [ref=e180] [cursor=pointer]:
            - img [ref=e181]
            - text: Расширенные параметры
          - button "Рассчитать подбор" [ref=e184] [cursor=pointer]
        - generic [ref=e187]:
          - generic [ref=e188]: Превью результата
          - paragraph [ref=e189]: Введите расход Q и нажмите «Рассчитать» — здесь появится рекомендованный насос с диапазоном цены и спецификацией.
    - generic [ref=e192]:
      - generic [ref=e193]:
        - generic [ref=e194]: ПРОИЗВОДИТЕЛЬ
        - heading "Производим. Не перепродаём." [level=2] [ref=e196]:
          - text: Производим.
          - text: Не перепродаём.
        - paragraph [ref=e197]: Серво-Юг с 2009 года выпускает канализационные насосные станции, локальные очистные сооружения и резервуары. Своё производство в Адыгее, шеф-монтаж по Краснодарскому краю и югу России.
        - generic [ref=e198]:
          - generic [ref=e199]:
            - generic [ref=e201]: "17"
            - generic [ref=e203]:
              - img [ref=e204]
              - text: лет на рынке
          - generic [ref=e207]:
            - generic [ref=e209]: "284"
            - generic [ref=e211]:
              - img [ref=e212]
              - text: модели насосов в базе
          - generic [ref=e216]:
            - generic [ref=e218]: 1400+
            - generic [ref=e219]:
              - img [ref=e220]
              - text: станций введено в эксплуатацию
          - generic [ref=e223]:
            - generic [ref=e225]: "7"
            - generic [ref=e227]:
              - img [ref=e228]
              - text: регионов поставки
      - generic [ref=e234]:
        - generic [ref=e235]: ПРОИЗВОДСТВЕННЫЙ ЦЕХ
        - generic [ref=e236]: Адыгея, аул Хатукай
        - generic [ref=e237]: Сварка коллекторов, сборка щитов управления, гидроиспытания
    - generic [ref=e240]:
      - generic [ref=e241]:
        - generic [ref=e242]: ОБЪЕКТЫ
        - heading "Реальные расчёты — подобраны и поставлены" [level=2] [ref=e244]:
          - text: Реальные расчёты —
          - text: подобраны и поставлены
      - generic [ref=e245]:
        - generic [ref=e246]:
          - generic [ref=e247]:
            - img [ref=e248]
            - generic [ref=e259]: Гостиница 4★
          - generic [ref=e260]:
            - generic [ref=e261]: Анапа · 2025
            - generic [ref=e262]: 120 номеров
            - generic [ref=e263]:
              - generic [ref=e264]:
                - generic [ref=e265]: Q
                - generic [ref=e266]: 26 м³/ч
              - generic [ref=e267]:
                - generic [ref=e268]: H
                - generic [ref=e269]: 14 м
            - generic [ref=e270]:
              - generic [ref=e271]: Установлено
              - generic [ref=e272]: Pedrollo MCm 40 ×2
        - generic [ref=e273]:
          - generic [ref=e274]:
            - img [ref=e275]
            - generic [ref=e286]: ЖК
          - generic [ref=e287]:
            - generic [ref=e288]: Краснодар · 2024
            - generic [ref=e289]: 320 квартир
            - generic [ref=e290]:
              - generic [ref=e291]:
                - generic [ref=e292]: Q
                - generic [ref=e293]: 45 м³/ч
              - generic [ref=e294]:
                - generic [ref=e295]: H
                - generic [ref=e296]: 18 м
            - generic [ref=e297]:
              - generic [ref=e298]: Установлено
              - generic [ref=e299]: Antarus AK2 80 ×2+1
        - generic [ref=e300]:
          - generic [ref=e301]:
            - img [ref=e302]
            - generic [ref=e313]: ТРЦ
          - generic [ref=e314]:
            - generic [ref=e315]: Ростов-на-Дону · 2024
            - generic [ref=e316]: 30 000 м²
            - generic [ref=e317]:
              - generic [ref=e318]:
                - generic [ref=e319]: Q
                - generic [ref=e320]: 120 м³/ч
              - generic [ref=e321]:
                - generic [ref=e322]: H
                - generic [ref=e323]: 28 м
            - generic [ref=e324]:
              - generic [ref=e325]: Установлено
              - generic [ref=e326]: KAIQUAN WQ200-12 ×3
        - generic [ref=e327]:
          - generic [ref=e328]:
            - img [ref=e329]
            - generic [ref=e340]: Дренаж кровли
          - generic [ref=e341]:
            - generic [ref=e342]: Сочи · 2025
            - generic [ref=e343]: 5 га асфальта
            - generic [ref=e344]:
              - generic [ref=e345]:
                - generic [ref=e346]: Q
                - generic [ref=e347]: 974 м³/ч
              - generic [ref=e348]:
                - generic [ref=e349]: H
                - generic [ref=e350]: 23.6 м
            - generic [ref=e351]:
              - generic [ref=e352]: Установлено
              - generic [ref=e353]: ONIS SW250 ×3
    - generic [ref=e354]:
      - img [ref=e356]
      - generic [ref=e364]:
        - generic [ref=e365]: ИНЖЕНЕР
        - heading "Готовы передать данные инженеру?" [level=2] [ref=e367]:
          - text: Готовы передать данные
          - text: инженеру?
        - paragraph [ref=e368]: Получите спецификацию с печатью, расчётом гидравлики и сертификатами за 1 рабочий день. Прямой контакт с ведущим инженером — без call-центров.
        - generic [ref=e369]:
          - link "8 (800) 222-44-57" [ref=e370] [cursor=pointer]:
            - /url: tel:+78002224457
            - img [ref=e371]
            - generic [ref=e373]: 8 (800) 222-44-57
            - img [ref=e374]
          - button "Скачать опросный лист" [ref=e376] [cursor=pointer]:
            - img [ref=e377]
            - text: Скачать опросный лист
        - paragraph [ref=e381]: без регистрации · ответ в течение 1 рабочего дня
    - generic [ref=e383]:
      - generic [ref=e384]:
        - generic [ref=e385]: FAQ
        - heading "Частые вопросы" [level=2] [ref=e387]
      - generic [ref=e388]:
        - generic [ref=e389]:
          - button "Чем подбор по калькулятору отличается от расчёта проектного института?" [expanded] [ref=e390] [cursor=pointer]:
            - generic [ref=e391]: Чем подбор по калькулятору отличается от расчёта проектного института?
            - img [ref=e393]
          - region "Чем подбор по калькулятору отличается от расчёта проектного института?" [ref=e394]:
            - paragraph [ref=e396]: Калькулятор делает первичный подбор по гидравлическим параметрам Q (расход) и H (напор) — для тендера, ТЭО (технико-экономического обоснования) или КП. Это инженерный ориентир за минуты, не замена проекту. Для сложных объектов (I категория надёжности, длинные трассы, агрессивные среды) расчёт уточняет инженер Серво-Юг — и результат соответствует требованиям СП 32.13330 (канализация наружная) и СП 10.13130 (внутренний пожарный водопровод).
        - generic [ref=e397]:
          - button "Можно ли получить КМД-чертёж (рабочую документацию) после подбора?" [ref=e398] [cursor=pointer]:
            - generic [ref=e399]: Можно ли получить КМД-чертёж (рабочую документацию) после подбора?
            - img [ref=e401]
          - paragraph [ref=e402]: Да. КМД — конструкции металлические деталировочные (рабочие чертежи на изготовление). После передачи данных инженеру (через DOCX-опросник или звонок) высылаем спецификацию с печатью, схему обвязки и КМД на станцию в формате PDF / DWG за 1 рабочий день.
        - generic [ref=e403]:
          - button "Какие гарантии на оборудование и какой срок поставки?" [ref=e404] [cursor=pointer]:
            - generic [ref=e405]: Какие гарантии на оборудование и какой срок поставки?
            - img [ref=e407]
          - paragraph [ref=e408]: На станции собственного производства — 24 месяца, на насосы — 12 месяцев согласно гарантии производителя. Срок поставки стандартных решений — от 7 рабочих дней при предоплате, нестандартных (большие диаметры, корпуса >D2400 мм) — от 30 дней.
        - generic [ref=e409]:
          - button "Подходит ли подбор для объектов с переменным расходом (гостиницы, ЖК)?" [ref=e410] [cursor=pointer]:
            - generic [ref=e411]: Подходит ли подбор для объектов с переменным расходом (гостиницы, ЖК)?
            - img [ref=e413]
          - paragraph [ref=e414]: "Да. Калькулятор учитывает СП 30.13330 прил. А.2: коэффициент часовой неравномерности 2.5–4.5 встроен в QHelper по типу объекта. Для нестандартного режима (производство со сменами) — выберите помощник «Расход на смену» или передайте данные инженеру."
        - generic [ref=e415]:
          - button "Делаете ли вы шеф-монтаж и пусконаладку (ПНР) в Краснодарском крае?" [ref=e416] [cursor=pointer]:
            - generic [ref=e417]: Делаете ли вы шеф-монтаж и пусконаладку (ПНР) в Краснодарском крае?
            - img [ref=e419]
          - paragraph [ref=e420]: Да. Шеф-монтаж и ПНР (пусконаладочные работы) — собственными бригадами по Краснодарскому краю, Адыгее, Ростовской области, Крыму и Ставрополью. На дальние регионы — выезд по согласованию (стоимость рассчитывается отдельно).
        - generic [ref=e421]:
          - button "Как учитывается заглубление и грунтовые воды?" [ref=e422] [cursor=pointer]:
            - generic [ref=e423]: Как учитывается заглубление и грунтовые воды?
            - img [ref=e425]
          - paragraph [ref=e426]: Глубина заложения и УГВ (уровень грунтовых вод) — параметры расширенного расчёта. Если вода стоит выше дна КНС — корпус усиливается противоразмывными рёбрами, для глубин >6 м применяется стеклопластиковый корпус. Калькулятор предложит подходящий материал; финальная проверка — у инженера по геологическим данным с участка.
  - contentinfo [ref=e427]:
    - generic [ref=e428]:
      - generic [ref=e429]:
        - generic [ref=e430]:
          - generic [ref=e431]:
            - generic [ref=e433]: И·С
            - generic [ref=e434]: ИНСЕРВО · Серво-Юг
          - paragraph [ref=e435]: Производство КНС, ЛОС, СПД и резервуаров с 2009 года. Подбор оборудования, шеф-монтаж и сервис.
        - generic [ref=e436]:
          - generic [ref=e437]: Продукт
          - list [ref=e438]:
            - listitem [ref=e439]:
              - link "Калькулятор подбора" [ref=e440] [cursor=pointer]:
                - /url: "#calculator"
            - listitem [ref=e441]:
              - link "Калькуляторы ёмкостей" [ref=e442] [cursor=pointer]:
                - /url: /tanks
            - listitem [ref=e443]:
              - link "Как работает алгоритм" [ref=e444] [cursor=pointer]:
                - /url: "#how"
            - listitem [ref=e445]:
              - link "FAQ" [ref=e446] [cursor=pointer]:
                - /url: "#faq"
        - generic [ref=e447]:
          - generic [ref=e448]: Производство
          - list [ref=e449]:
            - listitem [ref=e450]:
              - link "О компании" [ref=e451] [cursor=pointer]:
                - /url: "#trust"
            - listitem [ref=e452]: Сертификаты
            - listitem [ref=e453]: Объекты
            - listitem [ref=e454]: Договорная оферта
        - generic [ref=e455]:
          - generic [ref=e456]: Контакты
          - list [ref=e457]:
            - listitem [ref=e458]:
              - link "8 (800) 222-44-57" [ref=e459] [cursor=pointer]:
                - /url: tel:+78002224457
                - img [ref=e460]
                - generic [ref=e462]: 8 (800) 222-44-57
            - listitem [ref=e463]:
              - link "zakaz@inservo.ru" [ref=e464] [cursor=pointer]:
                - /url: mailto:zakaz@inservo.ru
                - img [ref=e465]
                - text: zakaz@inservo.ru
            - listitem [ref=e468]:
              - img [ref=e469]
              - generic [ref=e472]: Адыгея, аул Хатукай — производство и склад
      - generic [ref=e474]:
        - paragraph [ref=e475]:
          - text: Калькулятор разработан и реализован
          - link "Студией интеграции умных решений Константина Морозова" [ref=e476] [cursor=pointer]:
            - /url: https://inservo.ru
          - text: — INSERVO Studio.
        - paragraph [ref=e477]: "«Каждая КНС — как картина: всё точно, ничего лишнего.»"
        - paragraph [ref=e478]: Opensource · Лицензия MIT · © 2026 K. Morozov
      - generic [ref=e479]:
        - generic [ref=e480]: © 2009–2026 · ИНСЕРВО · Серво-Юг
        - generic [ref=e481]: Сделано в Краснодарском крае
  - alert [ref=e482]
```

# Test source

```ts
  1   | import { test, expect } from "@playwright/test";
  2   | import { checkRouteOk, collectPageErrors, ROUTES } from "./helpers";
  3   | 
  4   | /**
  5   |  * Mobile viewport tests — burger menu, theme toggle, touch targets, a11y.
  6   |  * Viewport: 375 × 667 (iPhone SE base).
  7   |  *
  8   |  * Используем chromium с mobile viewport (без webkit, чтобы не тянуть лишний браузер).
  9   |  */
  10  | test.use({
  11  |   viewport: { width: 375, height: 667 },
  12  |   userAgent:
  13  |     "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1",
  14  |   hasTouch: true,
  15  |   isMobile: true,
  16  | });
  17  | 
  18  | test.describe("Mobile (375×667)", () => {
  19  |   test("Home loads on mobile, no JS errors", async ({ page }) => {
  20  |     const { errors } = collectPageErrors(page);
  21  |     await checkRouteOk(page, ROUTES.home);
  22  |     await page.waitForLoadState("networkidle", { timeout: 15_000 }).catch(() => {});
  23  |     expect(errors, `JS errors on mobile home: ${errors.join("\n")}`).toEqual([]);
  24  |   });
  25  | 
  26  |   test("Burger menu button visible on mobile", async ({ page }) => {
  27  |     await page.goto(ROUTES.home);
  28  |     const burger = page.getByRole("button", { name: /меню|menu|открыть/i }).first();
  29  |     await expect(burger).toBeVisible();
  30  |   });
  31  | 
  32  |   test("Burger opens drawer, ESC closes it", async ({ page }) => {
  33  |     await page.goto(ROUTES.home);
  34  |     const burger = page.getByRole("button", { name: /открыть меню|меню|menu/i }).first();
  35  |     await burger.click();
  36  |     const drawer = page.locator('[role="dialog"][aria-modal="true"]');
  37  |     await expect(drawer).toBeVisible();
  38  |     // aria-expanded should be true after open
  39  |     await expect(burger).toHaveAttribute("aria-expanded", "true");
  40  | 
  41  |     // Esc closes drawer
  42  |     await page.keyboard.press("Escape");
  43  |     await expect(drawer).toBeHidden({ timeout: 3_000 }).catch(async () => {
  44  |       // fallback: click close button
  45  |       const closeBtn = page.getByRole("button", { name: /закрыть|close/i });
  46  |       if ((await closeBtn.count()) > 0) {
  47  |         await closeBtn.first().click();
  48  |       }
  49  |     });
  50  |   });
  51  | 
  52  |   test("Mobile phone link visible (tel:)", async ({ page }) => {
  53  |     await page.goto(ROUTES.home);
  54  |     const tel = page.locator('a[href^="tel:"]').first();
> 55  |     await expect(tel).toBeVisible();
      |                       ^ Error: expect(locator).toBeVisible() failed
  56  |   });
  57  | 
  58  |   test("Theme toggle button present and clickable", async ({ page }) => {
  59  |     await page.goto(ROUTES.home);
  60  |     const themeBtn = page
  61  |       .locator("button[aria-label^='Тема'], button[title^='Тема']")
  62  |       .first();
  63  |     await expect(themeBtn).toBeVisible();
  64  |     const labelBefore = await themeBtn.getAttribute("aria-label");
  65  |     await themeBtn.click();
  66  |     await page.waitForTimeout(300);
  67  |     const labelAfter = await themeBtn.getAttribute("aria-label");
  68  |     expect(
  69  |       labelBefore !== labelAfter,
  70  |       `theme aria-label should cycle (before=${labelBefore}, after=${labelAfter})`,
  71  |     ).toBe(true);
  72  |   });
  73  | 
  74  |   test("Theme toggle changes <html> class (light/dark)", async ({ page }) => {
  75  |     await page.goto(ROUTES.home);
  76  |     const themeBtn = page
  77  |       .locator("button[aria-label^='Тема'], button[title^='Тема']")
  78  |       .first();
  79  | 
  80  |     const getHtmlClass = async () => page.evaluate(() => document.documentElement.className);
  81  | 
  82  |     const initial = await getHtmlClass();
  83  |     // Click 3 times — cycle auto→light→dark→auto
  84  |     await themeBtn.click();
  85  |     await page.waitForTimeout(150);
  86  |     const c1 = await getHtmlClass();
  87  |     await themeBtn.click();
  88  |     await page.waitForTimeout(150);
  89  |     const c2 = await getHtmlClass();
  90  | 
  91  |     // At least one of c1/c2 should differ from initial
  92  |     const changed = c1 !== initial || c2 !== initial;
  93  |     expect(changed, `<html> className should change after theme cycles (init=${initial}, c1=${c1}, c2=${c2})`).toBe(true);
  94  |   });
  95  | 
  96  |   test("Main CTA button has touch target ≥44px on mobile", async ({ page }) => {
  97  |     await page.goto(ROUTES.home);
  98  |     const btn = page.getByRole("button", { name: /Рассчитать/i }).first();
  99  |     await expect(btn).toBeVisible();
  100 |     const box = await btn.boundingBox();
  101 |     expect(box, "CTA button has bounding box").not.toBeNull();
  102 |     // Hero CTA height — should be ≥44 (sm:h-16=64, base h-14=56)
  103 |     expect(box!.height, `CTA height = ${box!.height}px`).toBeGreaterThanOrEqual(44);
  104 |   });
  105 | 
  106 |   test("Burger button has touch target ≥44px", async ({ page }) => {
  107 |     await page.goto(ROUTES.home);
  108 |     const burger = page.getByRole("button", { name: /открыть меню|меню/i }).first();
  109 |     const box = await burger.boundingBox();
  110 |     expect(box).not.toBeNull();
  111 |     expect(box!.height, `Burger height = ${box!.height}px`).toBeGreaterThanOrEqual(44);
  112 |     expect(box!.width, `Burger width = ${box!.width}px`).toBeGreaterThanOrEqual(44);
  113 |   });
  114 | 
  115 |   test("Skip-link visible on focus", async ({ page }) => {
  116 |     await page.goto(ROUTES.home);
  117 |     // Tab once → skip-link should be in focus
  118 |     await page.keyboard.press("Tab");
  119 |     const skip = page.locator('a[href="#main"]');
  120 |     await expect(skip).toBeFocused();
  121 |   });
  122 | 
  123 |   test("Drawer NAV_LINKS rendered after opening", async ({ page }) => {
  124 |     await page.goto(ROUTES.home);
  125 |     const burger = page.getByRole("button", { name: /открыть меню|меню/i }).first();
  126 |     await burger.click();
  127 |     const drawer = page.locator('[role="dialog"]');
  128 |     // Expect at least 4 nav links inside drawer
  129 |     const navLinks = drawer.locator("a");
  130 |     expect(await navLinks.count()).toBeGreaterThanOrEqual(4);
  131 |   });
  132 | });
  133 | 
```