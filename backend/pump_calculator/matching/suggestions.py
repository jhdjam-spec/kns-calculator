"""UX-проза для триггеров — «Возможно вы имели в виду…» suggestions.

Содержит ОДНУ функцию `build_suggestions()` (~1265 строк), которая на основе
list[str] триггеров формирует list[InputSuggestion] с двухуровневым
объяснением (reason_engineer / reason_manager). Frontend рендерит таб
«Инженер»/«Менеджер» по этим полям.

Backlog: разделить на отдельные модули EXT-1.py..EXT-17.py + LEG-1.py..LEG-11.py
(каждое EXT — отдельный case). Сейчас единый файл для удобства navigation
по матчингу trigger ↔ suggestion.
"""

from __future__ import annotations

import math

from pump_calculator.matching.triggers import (
    _check_ext_9_nitrification,
    _check_ext_15_phosphorus,
    _check_ext_16_denitrification,
    _ext_8_uv_dose_required,
)
from pump_calculator.schemas import (
    ComputedHydraulics,
    InputSuggestion,
    L0Input,
    L1Input,
)


def build_suggestions(
    L0: L0Input, L1: L1Input | None, computed: ComputedHydraulics, triggers: list[str]
) -> list:
    """«Возможно вы имели в виду...» — мягкие предложения исправить вход.

    Каждое предложение включает физическое/гидравлическое/математическое
    обоснование (формула + следствие). Frontend рендерит модалку «Применить?».
    Никогда не модифицирует L0/L1 — только предлагает.
    """
    suggestions = []

    # 1. Q < 0.1 м³/ч — частая опечатка единиц измерения
    # Физика: типичный человек потребляет ~0.2 м³/сут = 0.0083 м³/ч.
    # КНС на 1 человека — 0.5+ м³/ч (с пиковыми коэф. К_сут × К_час).
    if L0.Q_m3h < 0.1:
        Q_lpm = L0.Q_m3h * 60   # из л/мин → м³/ч если перепутали
        Q_lps = L0.Q_m3h * 3.6  # из л/с → м³/ч если перепутали
        eng_text = (
            f"📏 Единица: Q={L0.Q_m3h} м³/ч = {L0.Q_m3h * 1000:.1f} л/час "
            f"= {L0.Q_m3h * 1000 / 60:.2f} л/мин — это меньше расхода обычного крана.\n"
            f"💡 Если в опросном листе указано {L0.Q_m3h} л/мин, "
            f"в м³/ч это будет {Q_lpm:.1f} (×60).\n"
            f"💡 Если {L0.Q_m3h} л/с — то {Q_lps:.1f} м³/ч (×3.6).\n"
            f"📐 Норма СНиП 2.04.01-85 для бытовой канализации: "
            f"≥ 0.5 м³/ч на 1 человека (с учётом К_неравн = 2.5)."
        )
        mgr_text = (
            f"⚠️ Q={L0.Q_m3h} м³/ч — это меньше расхода одного кухонного крана.\n"
            f"💧 Если клиент дал расход в л/мин — то в правильных единицах "
            f"это {Q_lpm:.1f} м³/ч.\n"
            f"💧 Если в л/с — то {Q_lps:.1f} м³/ч.\n"
            f"📞 Уточните у клиента в каких единицах присылал данные. "
            f"Иначе подберём огромный насос на 5+ кВт за 200+ тыс ₽ — "
            f"для микро-расхода это переплата ×20 и быстрая поломка из-за "
            f"коротких циклов вкл/выкл (защита двигателя ≤6 циклов/час)."
        )
        suggestions.append(InputSuggestion(
            field="Q_m3h",
            current_value=f"{L0.Q_m3h}",
            suggested_value=f"{Q_lpm:.1f}",
            reason=eng_text,
            reason_engineer=eng_text,
            reason_manager=mgr_text,
            severity="critical",
        ))

    # 2. dH отрицательный — нарушение определения «насос как генератор давления»
    # Физика: уравнение Бернулли P₁/(ρg) + z₁ + v²/(2g) = P₂/(ρg) + z₂ + v²/(2g) + h_тр
    # При z₂ < z₁ (отрицательный геометрический напор) насос НЕ нужен —
    # жидкость сама течёт под действием силы тяжести (gh).
    if L0.dH_m is not None and L0.dH_m < 0:
        eng_dh = (
            f"⚖️ Физика: dH = z₂ - z₁ = разность отметок (точка сброса минус "
            f"точка забора). dH={L0.dH_m} м означает что приёмник на |{L0.dH_m}| м "
            f"НИЖЕ источника.\n"
            f"🔬 По уравнению Бернулли P₁/(ρg) + z₁ = P₂/(ρg) + z₂ + h_тр: "
            f"при z₂ < z₁ жидкость течёт самотёком, насос не нужен.\n"
            f"💡 Если приёмник ВЫШЕ источника на {abs(L0.dH_m)} м — "
            f"уберите минус и поставьте {abs(L0.dH_m)}.\n"
            f"📐 По СП 32 §6.4 насос требуется только при положительном "
            f"геометрическом напоре + потерях на трение."
        )
        mgr_dh = (
            f"🌊 dH={L0.dH_m} м — точка сброса НИЖЕ точки забора. "
            f"Вода и так потечёт сама собой, насос не нужен.\n"
            f"💰 Решение: уточните у клиента схему — где источник, где приёмник?\n"
            f"  • Если перепутали знак — поставьте +{abs(L0.dH_m)} м, "
            f"тогда подберём насос (стандартная КНС 200-1500 тыс ₽).\n"
            f"  • Если действительно самотёк — нужен только самотёчный "
            f"коллектор и колодец (60-200 тыс ₽, без насоса вообще).\n"
            f"⏱ Без уточнения тратить время на подбор насоса бессмысленно — "
            f"клиент откажется когда увидит чек."
        )
        suggestions.append(InputSuggestion(
            field="dH_m",
            current_value=f"{L0.dH_m}",
            suggested_value=f"{abs(L0.dH_m)}",
            reason=eng_dh,
            reason_engineer=eng_dh,
            reason_manager=mgr_dh,
            severity="critical",
        ))

    # 3. L < 5 м для Q > 50 м³/ч — несоразмерно
    # Гидравлика: для серьёзных расходов внутриплощадочная трасса обычно
    # 30-100+ м (оборудование разнесено). L < 5 м физически возможен только
    # для микро-объектов (квартира).
    if L0.L_m is not None and L0.L_m < 5 and L0.Q_m3h > 50:
        eng_l = (
            f"📏 L={L0.L_m} м для Q={L0.Q_m3h} м³/ч — несоразмерно.\n"
            f"🔬 Гидравлика: для Q={L0.Q_m3h} м³/ч типовая трасса "
            f"30-100+ м (соединение между КНС, ОС, выпуском). "
            f"L<5 м означает почти отсутствие трубы.\n"
            f"💡 Возможно вы имели в виду {L0.L_m * 10} м (опечатка ×10)?\n"
            f"📐 Для Q≥50 м³/ч обычная норма: L_внутри = 50-200 м, "
            f"L_вне = 200-2000 м (СП 32 §6.5)."
        )
        mgr_l = (
            f"📏 Трасса {L0.L_m} м при расходе {L0.Q_m3h} м³/ч — "
            f"подозрительно мало. Так бывает только если КНС стоит "
            f"прямо у точки сброса (внутри здания).\n"
            f"💰 Если на самом деле трасса {L0.L_m * 10} м (типичная опечатка) — "
            f"подбор изменится: понадобится более мощный насос (+10-30% к цене) "
            f"и больший диаметр трубы.\n"
            f"📞 Уточните у клиента: какое реальное расстояние между КНС "
            f"и точкой сброса/ОС? Если ошибиться — насос не вытянет напор "
            f"и стоки пойдут наружу через 1-2 месяца эксплуатации."
        )
        suggestions.append(InputSuggestion(
            field="L_m",
            current_value=f"{L0.L_m}",
            suggested_value=f"{L0.L_m * 10}",
            reason=eng_l,
            reason_engineer=eng_l,
            reason_manager=mgr_l,
            severity="warning",
        ))

    # 4. v < 0.5 м/с (заиливание) — pipe_D_mm слишком велик
    # СП 32 §5.4: минимальная скорость самоочищения для канализационных
    # стоков v_min = 0.7 м/с (бытовые), 1.0 м/с (производственные).
    # При v < v_min осадок не уносится потоком, происходит заиливание.
    # Формула: D = sqrt(4Q/(πv)), для v=1.2 м/с (оптимум по СП 32).
    if L1 and L1.pipe_D_mm and computed.v_ms < 0.5:
        Q_m3s = L0.Q_m3h / 3600
        D_optimal = math.sqrt(4 * Q_m3s / (math.pi * 1.2)) * 1000
        for std in [50, 65, 80, 100, 125, 150, 200, 250, 300]:
            if std >= D_optimal:
                D_optimal = std
                break
        eng_vlow = (
            f"🔬 Гидравлика: при D={L1.pipe_D_mm} мм скорость "
            f"v=Q/A=Q/(πD²/4)={computed.v_ms:.3f} м/с.\n"
            f"⚠ По СП 32 §5.4 для бытовой канализации v_min=0.7 м/с — "
            f"при меньших скоростях осадок (взвешенные вещества) не "
            f"уносится, происходит ЗАИЛИВАНИЕ за месяцы.\n"
            f"📐 Расчёт оптимального D: D = √(4Q/(πv)), для v=1.2 м/с "
            f"(середина допустимого диапазона 0.7-2.5 м/с) → "
            f"D = √(4·{Q_m3s:.4f}/(π·1.2))·1000 = {D_optimal} мм (стандартный DN).\n"
            f"💡 Замените pipe_D_mm на {D_optimal}."
        )
        mgr_vlow = (
            f"🌊 Труба DN{int(L1.pipe_D_mm)} слишком широкая для расхода "
            f"{L0.Q_m3h} м³/ч — вода течёт медленно ({computed.v_ms:.2f} м/с), "
            f"осадок (песок, тряпки) оседает прямо в трубе.\n"
            f"💰 Через 3-6 мес труба зарастёт изнутри, насос будет давить "
            f"в забитую трубу — поломка двигателя 80-200 тыс ₽.\n"
            f"💡 Решение: труба DN{int(D_optimal)} вместо DN{int(L1.pipe_D_mm)} — "
            f"экономия на трубе ~30-50% + насос проработает 10 лет вместо 2.\n"
            f"📞 Если клиент настаивает на DN{int(L1.pipe_D_mm)} — "
            f"закладывайте промывку трассы 2 раза в год (40-80 тыс ₽/год OPEX)."
        )
        suggestions.append(InputSuggestion(
            field="L1.pipe_D_mm",
            current_value=f"{L1.pipe_D_mm}",
            suggested_value=f"{D_optimal}",
            reason=eng_vlow,
            reason_engineer=eng_vlow,
            reason_manager=mgr_vlow,
            severity="warning",
        ))

    # 5. v > 3 м/с (эрозия) — pipe_D_mm слишком мал
    # СП 32 §5.4: v_max=2.5 м/с (бытовые), 3.0 м/с (производственные).
    # При v > v_max начинается абразивный износ труб (особенно ПЭ),
    # повышается риск гидроудара (Δp_гидроудар ~ ρ·a·Δv по Жуковскому).
    if L1 and L1.pipe_D_mm and computed.v_ms > 3.0:
        Q_m3s = L0.Q_m3h / 3600
        D_optimal = math.sqrt(4 * Q_m3s / (math.pi * 1.2)) * 1000
        for std in [50, 65, 80, 100, 125, 150, 200, 250, 300]:
            if std >= D_optimal:
                D_optimal = std
                break
        # Расчёт давления гидроудара по Жуковскому
        a_pe100 = 320  # скорость волны в PE100 (м/с)
        delta_p_bar = 1000 * a_pe100 * computed.v_ms / 1e5
        eng_vhigh = (
            f"🔬 Гидравлика: при D={L1.pipe_D_mm} мм скорость "
            f"v={computed.v_ms:.2f} м/с.\n"
            f"⚠ СП 32 §5.4: v_max=2.5 м/с — иначе абразивный износ "
            f"трубы (срок службы падает в 2-3 раза) и эрозия фасонок.\n"
            f"💥 Жуковский: при резком закрытии клапана Δp = ρ·a·Δv = "
            f"1000·320·{computed.v_ms:.2f} ≈ {delta_p_bar:.1f} бар "
            f"(только для PE100, для стали ×3). Может разорвать трубу.\n"
            f"📐 Оптимум: D = √(4Q/(πv)) для v=1.2 м/с → {D_optimal} мм.\n"
            f"💡 Замените pipe_D_mm на {D_optimal}."
        )
        mgr_vhigh = (
            f"🌊 Труба DN{int(L1.pipe_D_mm)} слишком узкая для расхода "
            f"{L0.Q_m3h} м³/ч — вода летит со скоростью {computed.v_ms:.1f} м/с, "
            f"стенки трубы стирает песок и взвесь как наждачкой.\n"
            f"💰 Последствия:\n"
            f"  • Срок службы ПЭ-трубы падает с 50 лет до 15-20 лет.\n"
            f"  • При закрытии клапана возможен гидроудар ~{delta_p_bar:.0f} бар — "
            f"риск разрыва трубы (замена трассы 500-2000 тыс ₽).\n"
            f"💡 Решение: труба DN{int(D_optimal)} вместо DN{int(L1.pipe_D_mm)} — "
            f"увеличение цены трубы ~25-40%, но окупится в первые 5 лет.\n"
            f"⏱ Срок поставки больших диаметров +1-2 недели."
        )
        suggestions.append(InputSuggestion(
            field="L1.pipe_D_mm",
            current_value=f"{L1.pipe_D_mm}",
            suggested_value=f"{D_optimal}",
            reason=eng_vhigh,
            reason_engineer=eng_vhigh,
            reason_manager=mgr_vhigh,
            severity="warning",
        ))

    # 6. PE100/PP/PVC + горячая жидкость → деградация полимера
    # Материаловедение: ПЭ100 имеет температуру длительной эксплуатации до 60°C
    # (паспорт ISO 4427). При T > 60°C ускоряется ползучесть, падает долговечность
    # с 50 лет (норма) до 5-10 лет. Сталь — до 200°C при PN16.
    pipe_mat = L1.pipe_material if L1 else None
    temp_c = L1.liquid_temp_c if L1 else None
    if pipe_mat in ("pe100_sdr17", "pp", "pvc") and temp_c is not None and temp_c > 60:
        # Для PP допустимо до 70°C, но запас ниже
        eng_pipe = (
            f"🧪 Материаловедение: {pipe_mat} имеет T_max = 60°C "
            f"для длительной эксплуатации (ISO 4427 для ПЭ100).\n"
            f"📉 При T={temp_c}°C ползучесть ускоряется по закону "
            f"Аррениуса (k = A·exp(-E_a/RT)): срок службы падает "
            f"с 50 лет до 5-10 лет. Возможно разрушение трубы за месяцы.\n"
            f"💡 Замените на steel_seamless_new — до 200°C при PN ≤ 16 бар, "
            f"либо cast_iron_new — до 150°C, дешевле стали."
        )
        mgr_pipe = (
            f"🔥 Полимерная труба ({pipe_mat}) не выдержит стоки T={temp_c}°C — "
            f"размягчится и потечёт через 6-12 мес. Производитель не покрывает "
            f"гарантией работу >60°C.\n"
            f"💰 Замена трубы по материалам:\n"
            f"  • Сталь бесшовная (до 200°C) — +80-150% к цене ПЭ.\n"
            f"  • Чугун ВЧШГ (до 150°C) — +50-100% к цене ПЭ, дешевле стали.\n"
            f"⏱ Срок поставки стали/чугуна 2-4 недели против 1-2 для ПЭ.\n"
            f"📞 Если оставить ПЭ — клиент через год придёт менять всю трассу "
            f"за свой счёт (500-1500 тыс ₽) и будет ругать нас за плохой подбор."
        )
        suggestions.append(InputSuggestion(
            field="L1.pipe_material",
            current_value=f"{pipe_mat}",
            suggested_value="steel_seamless_new",
            reason=eng_pipe,
            reason_engineer=eng_pipe,
            reason_manager=mgr_pipe,
            severity="critical",
        ))

    # 7. inflow > Q насоса × 1.5 — баланс масс не выполняется
    # Закон сохранения массы: dV/dt = Q_in - Q_out. Если Q_in > Q_out,
    # уровень в приёмной камере растёт линейно: ΔV = (Q_in - Q_out)·t.
    # При V_камеры=10 м³ и Δ=80 м³/ч переполнение через t = 10/80*60 = 7.5 мин.
    if L1 and L1.inflow_per_hour_m3 and L1.inflow_per_hour_m3 > L0.Q_m3h * 1.5:
        suggested_Q = round(L1.inflow_per_hour_m3 * 1.2, 1)
        delta = L1.inflow_per_hour_m3 - L0.Q_m3h
        # Время переполнения камеры 5м³ при текущем балансе
        t_overflow_min = 5.0 / delta * 60 if delta > 0 else float("inf")
        eng_inflow = (
            f"⚖️ Баланс масс (закон сохранения): dV/dt = Q_in - Q_out.\n"
            f"При Q_in={L1.inflow_per_hour_m3} > Q_out={L0.Q_m3h} м³/ч "
            f"уровень растёт со скоростью {delta:.1f} м³/ч.\n"
            f"⏱ Камера 5 м³ переполнится за {t_overflow_min:.1f} мин — "
            f"стоки пойдут на улицу.\n"
            f"💡 Решение 1: Q_насоса = Q_in × 1.2 = {suggested_Q} м³/ч "
            f"(+20% запас по СП 32 §6.5).\n"
            f"💡 Решение 2: 2-3 насоса параллельно (1+1 рабочий+резерв).\n"
            f"💡 Решение 3: увеличить V_камеры (буфер) — но это OPEX, не CAPEX."
        )
        mgr_inflow = (
            f"⚖️ Приток в КНС ({L1.inflow_per_hour_m3} м³/ч) больше, чем "
            f"вытаскивает насос ({L0.Q_m3h} м³/ч). Камера переполнится "
            f"за {t_overflow_min:.0f} минут, стоки польются на улицу.\n"
            f"💰 Решения:\n"
            f"  • Поставить насос побольше Q={suggested_Q} м³/ч — "
            f"+20-40% к цене насоса.\n"
            f"  • Поставить 2 насоса в параллель (раб+рез по СП 32) — "
            f"+60-100% к цене (2× оборудования).\n"
            f"⏱ Без увеличения мощности — первый ливень = аварийный звонок "
            f"клиента + штраф Росприроднадзора 100-500 тыс ₽ "
            f"за загрязнение земли (КоАП ст.8.6).\n"
            f"📞 Срочно уточните реальный приток у клиента (паспорт объекта)."
        )
        suggestions.append(InputSuggestion(
            field="Q_m3h",
            current_value=f"{L0.Q_m3h}",
            suggested_value=f"{suggested_Q}",
            reason=eng_inflow,
            reason_engineer=eng_inflow,
            reason_manager=mgr_inflow,
            severity="critical",
        ))

    # ──────────────────────────────────────────────────────────────────
    # 2026-05-10: 10 научных расширений — suggestions с 2-level reasons
    # ──────────────────────────────────────────────────────────────────

    # EXT-1: боковое давление грунта (СП 22.13330.2016 §5.6.5)
    # v0.3 (2026-05-13): теперь учитывает L1.soil_type (PhD-Mechanics audit
    # P1-4) и σ_водн = γ_w·z_w при УГВ выше дна (P0-3, реальный кейс
    # эталона Евпатория). Если soil_type не задан — fallback на default
    # sand_medium (старое поведение, K_a=0.33).
    if "auto_lateral_earth_pressure" in triggers and L1 and L1.install_depth_inlet_mm:
        # v0.4 (2026-05-13): рефакторинг под единый GroundContext
        # (Sc.D. cross-domain P0 «N×M связность soil/gwl/T»). γ/φ/K_a/K_p
        # читаются из coefficients.json soil_parameters_sp22.
        from pump_calculator.structural import (
            GroundContext,
            check_corpus_strength,
        )
        ctx = GroundContext.from_l1(L1)
        z_m = ctx.install_depth_m
        result = check_corpus_strength(ctx, z_max_m=z_m)
        gamma = ctx.gamma_kN_m3
        phi = ctx.phi_deg
        K_a = ctx.K_a
        K_p = ctx.K_p
        sigma_x_grunt_kpa = result["pressure_breakdown"]["soil_active_kPa"]
        sigma_x_water_kpa = result["pressure_breakdown"]["water_kPa"]
        sigma_x_kpa = result["sigma_total_kPa"]
        sigma_p_kpa = result["pressure_breakdown"]["passive_resistance_kPa"]
        gwl_note = ""
        if sigma_x_water_kpa > 0:
            z_w = ctx.gwl_above_bottom_m
            gwl_note = (
                f"\n💧 УГВ ({ctx.groundwater_level_m:.1f} м от земли) выше дна "
                f"корпуса на {z_w:.1f} м. СП 22 §5.6.5: добавляется "
                f"σ_водн = γ_w·z_w = 9.81·{z_w:.1f} ≈ {sigma_x_water_kpa:.1f} кПа."
            )
        sigma_PE_kpa = result["sigma_allowable_kPa"]
        overstress_note = ""
        if sigma_x_kpa > sigma_PE_kpa:
            overstress_note = (
                f"\n🚨 σ_x={sigma_x_kpa:.0f} кПа > σ_доп ПЭ100 SDR17 (50 кПа). "
                f"Рекомендация: {result['recommendation']}."
            )
        # K_p — пассивный отпор грунта для глубоких котлованов ≥5 м
        # (откол грунта при открытой траншее, СП 22 §5.6.2).
        kp_note = ""
        if z_m >= 5.0:
            kp_note = (
                f"\n🪨 K_p={K_p:.2f} (пассивный отпор грунта) — при открытом "
                f"котловане σ_p = γ·z·K_p ≈ {sigma_p_kpa:.0f} кПа удерживает "
                f"стенку. Контролировать откол при глубине ≥5 м."
            )
        eng = (
            f"🪨 СП 22.13330.2016 «Основания зданий и сооружений», §5.6.5 — "
            f"расчёт горизонтального давления грунта по теории Кулона.\n"
            f"📐 Формула: σ_x = γ·z·K_a + γ_w·z_w (при УГВ выше дна), "
            f"K_a = tan²(45°-φ/2).\n"
            f"Грунт: {ctx.label} (γ={gamma} кН/м³, φ={phi}°, K_a={K_a:.2f}).\n"
            f"При z={z_m:.1f} м: σ_грунт = {gamma}·{z_m:.1f}·{K_a:.2f} ≈ "
            f"{sigma_x_grunt_kpa:.1f} кПа.{gwl_note}\n"
            f"Σ σ_x ≈ {sigma_x_kpa:.1f} кПа на стенку корпуса.{overstress_note}{kp_note}\n"
            f"⚠ Для ПЭ-корпуса σ_доп=50 кПа (SDR17) / 80 кПа (SDR11) по ISO 9080. "
            f"При превышении — рёбра жёсткости и/или ж/б обойма."
        )
        mgr = (
            f"🏗 Глубина {z_m:.1f} м, грунт: {ctx.label}.\n"
            f"💰 Давление грунта {sigma_x_kpa:.0f} кПа на корпус.\n"
            f"  • Если σ_x ≤ 50 кПа — стандартный ПЭ100 SDR17 OK.\n"
            f"  • Если 50-80 кПа — нужен SDR11 (+15-25% цены корпуса).\n"
            f"  • Если >80 кПа — рёбра жёсткости (+150-300 тыс ₽) "
            f"или ж/б обойма (+800 тыс — 1.5 млн ₽).\n"
            f"⏱ Срок изготовления усиленного корпуса +3-5 недель.\n"
            f"📞 Передайте инженеру для расчёта по СП 22.13330."
        )
        suggestions.append(InputSuggestion(
            field="L1.install_depth_inlet_mm",
            current_value=f"{L1.install_depth_inlet_mm}",
            suggested_value=f"{L1.install_depth_inlet_mm}",
            reason=eng,
            reason_engineer=eng,
            reason_manager=mgr,
            severity="critical",
        ))

    # EXT-17 (2026-05-13): шпунт траншеи под котлован КНС (СП 45.13330.2017 §6.1).
    # Sub T cross-domain P2. Используем единый GroundContext + проверку
    # SAFE_SLOPE_BY_DEPTH из trench_stability.
    if (
        "auto_trench_sheet_pile_required" in triggers
        and L1
        and L1.install_depth_inlet_mm
    ):
        from pump_calculator.structural import (
            GroundContext,
            check_trench_stability,
        )
        ctx_t = GroundContext.from_l1(L1)
        z_m = ctx_t.install_depth_m
        trench = check_trench_stability(ctx_t, depth_m=z_m)
        slope = trench.safe_slope_ratio_m_per_h
        h_clear = trench.horizontal_clearance_m
        kp_text = (
            f"K_p={ctx_t.K_p:.2f} (пассивное сопротивление "
            f"σ_p = γ·z·K_p ≈ {trench.passive_resistance_kPa:.0f} кПа)"
        )
        if trench.sheet_pile_required:
            eng_t = (
                f"🪵 СП 45.13330.2017 §6.1 «Земляные сооружения, "
                f"основания и фундаменты»:\n"
                f"📐 z_котл = {z_m:.1f} м, грунт «{ctx_t.label}», "
                f"{kp_text}.\n"
                f"⚠ {trench.sheet_pile_reason}\n"
                f"📐 Без шпунта откос требует горизонтальной отбивки "
                f"{h_clear:.1f} м (slope {slope:.2f}:1), что "
                f"увеличит объём земработ в "
                f"{(1 + slope * 2) ** 2:.1f} раз."
            )
            mgr_t = (
                f"🚧 Глубина котлована {z_m:.1f} м, грунт: {ctx_t.label}.\n"
                "💰 Шпунтовое ограждение:\n"
                "  • Лёгкое (ПВХ Larssen 600) — 7-15 тыс ₽/м² по контуру\n"
                "  • Стандартное (металл Л5УМ) — 18-30 тыс ₽/м² по контуру\n"
                "⏱ Срок поставки 2-4 недели + 1 неделя забивка.\n"
                "📞 Передайте инженеру для расчёта периметра + "
                "согласования с СЭС/архитектурой."
            )
            suggestions.append(InputSuggestion(
                field="L1.install_depth_inlet_mm",
                current_value=f"{L1.install_depth_inlet_mm}",
                suggested_value=f"{L1.install_depth_inlet_mm}",
                reason=eng_t,
                reason_engineer=eng_t,
                reason_manager=mgr_t,
                severity="warning",
            ))
        else:
            eng_t = (
                f"🪨 СП 45.13330.2017 §6.1 — открытый откос допустим:\n"
                f"📐 z = {z_m:.1f} м, грунт «{ctx_t.label}», "
                f"slope = {slope:.2f}:1 (горизонт.:вертикал.).\n"
                f"📐 Горизонтальная отбивка: {h_clear:.1f} м от низа.\n"
                f"📐 {kp_text}."
            )
            mgr_t = (
                f"🚧 Котлован глубиной {z_m:.1f} м без шпунта.\n"
                f"💰 Откос с горизонтальной отбивкой {h_clear:.1f} м.\n"
                f"⏱ Объём земработ: проверьте, что площадка позволяет "
                f"{h_clear * 2:.1f} м свободного пространства вокруг корпуса."
            )
            suggestions.append(InputSuggestion(
                field="L1.install_depth_inlet_mm",
                current_value=f"{L1.install_depth_inlet_mm}",
                suggested_value=f"{L1.install_depth_inlet_mm}",
                reason=eng_t,
                reason_engineer=eng_t,
                reason_manager=mgr_t,
                severity="info",
            ))

    # EXT-2: класс нагрузки крышки (СП 35.13330)
    if "auto_traffic_load_class" in triggers and L1:
        eng = (
            f"🚛 СП 35.13330 «Мосты и трубы», табл.6.4 — классы нагрузки крышек "
            f"по EN 124:\n"
            f"  • A15 (15 кН) — пешеходные зоны\n"
            f"  • B125 (125 кН) — паркинги легковых\n"
            f"  • C250 (250 кН) — заездные карманы\n"
            f"  • D400 (400 кН) — проезжие части дорог\n"
            f"📐 При install_depth={L1.install_depth_inlet_mm} мм без павильона "
            f"крышка находится на уровне земли — высокий риск наезда транспорта.\n"
            f"⚠ Чугунная D400 обязательна если возможен заезд авто."
        )
        mgr = (
            "🚧 Корпус КНС без павильона на малой глубине — крышка на уровне земли.\n"
            "💰 Стоимость крышки по классам:\n"
            "  • A15 (тротуар) — 8-15 тыс ₽\n"
            "  • B125 (паркинг) — 25-40 тыс ₽\n"
            "  • D400 (дорога) — 60-120 тыс ₽\n"
            "⏱ Уточните у клиента: возможен ли заезд авто над КНС? "
            "Если да — закладывайте D400, иначе риск разрушения за 1 сезон."
        )
        suggestions.append(InputSuggestion(
            field="L1.cover_load_class",
            current_value="не задано",
            suggested_value="D400",
            reason=eng,
            reason_engineer=eng,
            reason_manager=mgr,
            severity="critical",
        ))

    # EXT-3: заземление (ПУЭ 1.7)
    if "auto_grounding_required" in triggers and L1:
        why = "взрывозащита" if L1.Ex_required else "I категория надёжности"
        eng = (
            f"⚡ ПУЭ 1.7 «Заземление и защитные меры», п.1.7.103 — "
            f"требование к заземляющему устройству для {why}.\n"
            f"📐 R_зазем ≤ 4 Ом для системы TN-S; ≤ 10 Ом для повторного "
            f"заземления (ПУЭ 1.7.62).\n"
            f"🔬 Расчёт по СО 153-34.21.122: R = ρ_грунта/(2π·L)·ln(2L/d), "
            f"где ρ — удельное сопротивление грунта (Ом·м), L — длина "
            f"электрода, d — диаметр.\n"
            f"⚠ Для Ex-зон обязательно: уравнивание потенциалов всех "
            f"металлических корпусов + контур ≤ 4 Ом."
        )
        mgr = (
            f"⚡ Для объекта с {why} требуется отдельный контур заземления.\n"
            f"💰 Стоимость:\n"
            f"  • Базовый контур (3-5 электродов) — 35-60 тыс ₽\n"
            f"  • Молниеотвод + уравнивание — 80-150 тыс ₽\n"
            f"  • Замер сопротивления + протокол — 12-18 тыс ₽\n"
            f"⏱ Монтаж 2-4 дня. Без протокола замера ввод в эксплуатацию "
            f"запрещён (Ростехнадзор)."
        )
        suggestions.append(InputSuggestion(
            field="L1.grounding_required",
            current_value="не учтено",
            suggested_value="контур ≤ 4 Ом",
            reason=eng,
            reason_engineer=eng,
            reason_manager=mgr,
            severity="critical",
        ))

    # EXT-4: молниезащита (СО 153-34.21.122)
    if "auto_lightning_protection_required" in triggers:
        eng = (
            "🌩 СО 153-34.21.122-2003 «Молниезащита зданий и сооружений», "
            "п.2.2 — наземное здание подлежит классификации по уровню защиты:\n"
            "  • I уровень — взрывоопасные зоны (Ex)\n"
            "  • II уровень — пожароопасные / I категория надёжности\n"
            "  • III-IV уровень — обычные здания\n"
            "📐 Зона защиты молниеотвода (одиночный стержень): "
            "R_зоны = 1.5·h_стержня (тип А).\n"
            "⚠ Для электрооборудования внутри павильона — обязательны УЗИП "
            "класса I (ГОСТ Р 51992-2011), I_имп ≥ 25 кА."
        )
        mgr = (
            "🌩 Наземный павильон требует молниезащиты (СО 153-34.21.122).\n"
            "💰 Комплект:\n"
            "  • Молниеотвод-стержень с креплением — 25-45 тыс ₽\n"
            "  • УЗИП класса I в ШУ — 18-30 тыс ₽\n"
            "  • Контур + спуск + протокол — 60-90 тыс ₽\n"
            "📞 Один удар молнии без защиты убивает ШУ + ЧРП "
            "(~400 тыс ₽ замены) и приводит к пожару павильона."
        )
        suggestions.append(InputSuggestion(
            field="L1.lightning_protection",
            current_value="не учтено",
            suggested_value="молниеотвод + УЗИП",
            reason=eng,
            reason_engineer=eng,
            reason_manager=mgr,
            severity="critical",
        ))

    # EXT-5: утепление труб (СП 41-103)
    if "auto_pipe_insulation_required" in triggers and L1:
        reason_short = (
            "горячая жидкость (>40°C)"
            if (L1.liquid_temp_c and L1.liquid_temp_c > 40)
            else "холодный регион (горы)"
        )
        eng = (
            f"🧊 СП 41-103-2000 «Тепловая изоляция оборудования и "
            f"трубопроводов», табл.7.1 — требования к толщине изоляции.\n"
            f"📐 Тепловой поток через стенку: q = 2πλΔT/ln(D₂/D₁) Вт/м, "
            f"где λ — коэф. теплопроводности изоляции (Вт/м·К).\n"
            f"Для пеноПЭ λ=0.04, при ΔT=50°C, D₁=110, D₂=160 мм: "
            f"q ≈ 33 Вт/м.\n"
            f"Причина: {reason_short}.\n"
            f"⚠ Без изоляции в холодных регионах — замерзание за 4-8 ч "
            f"простоя; для горячих стоков — потери температуры > 5°C/100 м."
        )
        mgr = (
            f"🧊 Требуется утепление напорной трассы ({reason_short}).\n"
            f"💰 Стоимость:\n"
            f"  • Трубчатая ПЭ-изоляция (Energoflex) — 250-450 ₽/п.м\n"
            f"  • Минвата с фольгой (для горячих) — 500-800 ₽/п.м\n"
            f"  • Кожух из оцинковки — +600-900 ₽/п.м\n"
            f"  • Монтаж — 200-300 ₽/п.м\n"
            f"⏱ Для трассы 100 м: ориентир 130-200 тыс ₽ под ключ."
        )
        suggestions.append(InputSuggestion(
            field="L1.pipe_insulation",
            current_value="не учтено",
            suggested_value="требуется изоляция",
            reason=eng,
            reason_engineer=eng,
            reason_manager=mgr,
            severity="warning",
        ))

    # EXT-6: греющий кабель
    if "auto_heating_cable_required" in triggers and L1 and L1.altitude_m is not None:
        # Бытовая мощность саморегулирующегося кабеля ~30 Вт/м
        eng = (
            f"🔥 Греющий кабель для напорной трассы — высота "
            f"{L1.altitude_m:.0f} м (горный регион, минимальная T_зимы < -25°C).\n"
            f"📐 Расчёт мощности: P = K·π·D·(T_внутр - T_окр)/R_изол, "
            f"где K — коэф. теплопередачи (Вт/м²·К).\n"
            f"Для DN50-150 без изоляции: P ≈ 30 Вт/м (саморегулирующийся "
            f"кабель типа FROSTOP-Black, Raychem или Lavita).\n"
            f"⚠ Запитка через УЗО 30 мА (ПУЭ 7.1.79). При длине трассы L "
            f"общая мощность P_total = 30·L Вт."
        )
        mgr = (
            f"🔥 Объект на высоте {L1.altitude_m:.0f} м (горы) — "
            f"в зимние морозы трубы замёрзнут за часы простоя.\n"
            f"💰 Греющий кабель саморегулирующийся 30 Вт/м:\n"
            f"  • Кабель — 850-1200 ₽/п.м\n"
            f"  • Терморегулятор + датчик — 8-15 тыс ₽\n"
            f"  • УЗО 30 мА + автомат — 4-7 тыс ₽\n"
            f"  • Монтаж + запенивание — 400-600 ₽/п.м\n"
            f"⏱ Для трассы 100 м: 150-200 тыс ₽ комплект + монтаж."
        )
        suggestions.append(InputSuggestion(
            field="L1.heating_cable",
            current_value="не учтено",
            suggested_value="30 Вт/м саморегулирующийся",
            reason=eng,
            reason_engineer=eng,
            reason_manager=mgr,
            severity="warning",
        ))

    # EXT-7: седиментация Stokes
    if "auto_sedimentation_check" in triggers:
        # v_осаж по Стоксу для песчинки 0.5 мм, ρ=2650 кг/м³
        rho_p = 2650
        rho_w = 1000
        g = 9.81
        d_m = 0.5e-3
        mu = 1e-3
        v_sed = (rho_p - rho_w) * g * d_m**2 / (18 * mu)  # м/с
        eng = (
            f"⚗ Закон Стокса для седиментации частиц в промстоках:\n"
            f"📐 v_осаж = (ρ_частицы - ρ_воды)·g·d²/(18·μ)\n"
            f"Для песчинки d=0.5 мм, ρ_p=2650 кг/м³, μ=1e-3 Па·с:\n"
            f"v_осаж = (2650-1000)·9.81·(5e-4)²/(18·1e-3) ≈ {v_sed*1000:.1f} мм/с "
            f"= {v_sed*60*100:.1f} см/мин.\n"
            f"⚠ При Q={L0.Q_m3h} м³/ч (industrial) поток в DN150 v≈{L0.Q_m3h*4/3600/3.14/0.15**2:.2f} м/с — "
            f"крупные частицы (>0.5 мм) оседают в трубе и приёмной камере.\n"
            f"💡 Решение: песколовка / гидроциклон до КНС "
            f"(СП 32 §7.4 — обязательна для содержания песка >100 мг/л)."
        )
        mgr = (
            f"⚗ Промстоки с малым расходом Q={L0.Q_m3h} м³/ч — поток "
            f"медленный, песок оседает в трубах и насосе.\n"
            f"💰 Песколовка тангенциальная DN300:\n"
            f"  • Корпус ПЭ — 85-140 тыс ₽\n"
            f"  • Гидроциклон чугунный — 180-320 тыс ₽\n"
            f"  • Монтаж + обвязка — 40-70 тыс ₽\n"
            f"⏱ Без песколовки замена рабочего колеса насоса каждые "
            f"6-12 мес (1 колесо = 80-200 тыс ₽)."
        )
        suggestions.append(InputSuggestion(
            field="L1.sand_separator",
            current_value="не учтено",
            suggested_value="песколовка/гидроциклон",
            reason=eng,
            reason_engineer=eng,
            reason_manager=mgr,
            severity="warning",
        ))

    # EXT-8: УФ/озон обеззараживание (v0.4: dose дифференцирована по target_discharge)
    if "auto_disinfection_required" in triggers:
        uv_dose, target = _ext_8_uv_dose_required(L1)
        eng = (
            f"🦠 СанПиН 2.1.5.980-00 «Гигиенические требования к охране "
            f"поверхностных вод», п.4.1.5 — обеззараживание стоков "
            f"перед сбросом в водоём (хоз-бытовые Q={L0.Q_m3h} > 100 м³/ч).\n"
            f"📐 УФ-доза по МУК 4.3.2030-05: D = I·t ≥ {uv_dose} мДж/см² "
            f"для целевого сброса '{target}' (E.coli 3 lg, колифаги 2 lg).\n"
            f"📐 NB для непрозрачных стоков (turbidity > 30 NTU) — озон "
            f"вместо УФ: C·t ≥ 5 мг·мин/л.\n"
            f"⚠ Хлорирование запрещено для сброса в рыбохозяйственные "
            f"водоёмы (Приказ Росрыболовства №20).\n"
            f"💡 30 мДж/см² — стандарт general_use; для fishery_water "
            f"требуется 80-120 мДж/см² с предобработкой."
        )
        mgr = (
            f"🦠 Q={L0.Q_m3h} м³/ч хоз-бытовых, сброс в '{target}' — "
            f"по СанПиН требуется УФ-доза {uv_dose} мДж/см².\n"
            f"💰 Варианты:\n"
            f"  • УФ-стерилизатор Sita / Wedeco на Q=100-200 — 380-650 тыс ₽\n"
            f"  • Озонатор 50-100 г/ч — 850 тыс — 1.5 млн ₽\n"
            f"  • Контактная камера + смеситель — 120-220 тыс ₽\n"
            f"  • Лампы УФ замена раз в год — 35-60 тыс ₽/год OPEX\n"
            f"⏱ Без обеззараживания штраф Росприроднадзора 250-500 тыс ₽ "
            f"(ст.8.13 КоАП) + остановка сброса."
        )
        suggestions.append(InputSuggestion(
            field="L1.disinfection",
            current_value="не учтено",
            suggested_value="УФ или озон",
            reason=eng,
            reason_engineer=eng,
            reason_manager=mgr,
            severity="warning",
        ))

    # EXT-9: нитри/денитрификация (v0.4: точный расчёт по NH4 / C:N / target)
    if "auto_nitrification_check" in triggers:
        # Перевычисляем dict-параметры (single source of truth — _check_ext_9_nitrification)
        ext9 = _check_ext_9_nitrification(L0, L1, computed)
        if ext9 is None:
            # Safety: триггер прошёл, но детали не совпали (T/UI desync).
            # Используем generic-фолбэк без чисел.
            ext9 = {
                "nh4": 25.0, "bod5": 250.0, "c_to_n": 10.0,
                "T": 20.0, "nh4_limit": 2.0, "target": "municipal_sewage",
                "srt_min_d": 15.0,
            }
        eng = (
            f"🧪 Нитри/денитрификация в ЛОС (СП 32.13330 §9.2.5 + Henze IWA "
            f"2008 §3.4).\n"
            f"📐 Параметры стоков: NH4_in={ext9['nh4']:.0f} мг/л > "
            f"ПДК={ext9['nh4_limit']} мг/л для '{ext9['target']}', "
            f"C:N=БПК5/N={ext9['c_to_n']:.1f}, T={ext9['T']:.0f}°C.\n"
            f"📐 Кинетика по Monod: μ = μ_max·S/(K_s+S), где для "
            f"Nitrosomonas μ_max=0.8 сут⁻¹, K_s≈1 мг/л NH4-N (Henze IWA "
            f"§3.4, Arrhenius θ=1.103).\n"
            f"📐 SRT_min = 15·1.103^(15−T) = {ext9['srt_min_d']:.1f} сут.\n"
            f"⚠ Условия для биоты (нитрификаторы Nitrosomonas+Nitrobacter):\n"
            f"  • Возраст ила θ_c ≥ {ext9['srt_min_d']:.0f} сут\n"
            f"  • Аэрация DO ≥ 2 мг/л в зоне нитрификации\n"
            f"  • MLSS 3-5 г/л (активный ил), пенный индекс <150 мл/г\n"
            f"  • T 12-35°C (вне диапазона нитрификаторы гибнут)\n"
            f"  • pH 7.5-8.5 (оптимум для аммоний-окисляющих)\n"
            f"  • Рециркуляция нитратов 200-400% для денитрификации.\n"
            f"📐 Объём аэротенка: V = Q·SRT_min/MLSS·(1+R_recycle)."
        )
        mgr = (
            f"🧪 Аммоний NH4={ext9['nh4']:.0f} мг/л превышает норматив "
            f"({ext9['nh4_limit']} мг/л для '{ext9['target']}') — нужна "
            f"биологическая очистка (аэротенк с активным илом).\n"
            f"💰 ЛОС на Q={L0.Q_m3h} м³/ч с нитри/денитри:\n"
            f"  • Аэротенк ж/б 50-150 м³ — 1.5-3.5 млн ₽\n"
            f"  • Воздуходувка + аэраторы — 450-850 тыс ₽\n"
            f"  • Вторичный отстойник — 380-720 тыс ₽\n"
            f"  • Автоматика DO/pH/NH4 — 280-450 тыс ₽\n"
            f"⏱ Срок: 4-6 нед проектирование+поставка, ~600-1200 тыс ₽ "
            f"к стоимости ЛОС. Запуск биоценоза 4-8 недель.\n"
            f"📞 Передайте инженеру-технологу для расчёта по реальным "
            f"показателям сточных вод (БПК, ХПК, NH4, P)."
        )
        suggestions.append(InputSuggestion(
            field="L1.nitrification_required",
            current_value="не учтено",
            suggested_value="аэротенк θ_c≥10 сут",
            reason=eng,
            reason_engineer=eng,
            reason_manager=mgr,
            severity="warning",
        ))

    # EXT-15 (Phase 34+ P2): удаление фосфора (Metcalf & Eddy §8-3)
    if "auto_phosphorus_removal" in triggers:
        ext15 = _check_ext_15_phosphorus(L0, L1)
        if ext15 is None:
            # Safety fallback на случай UI desync
            ext15 = {
                "p_in_mgL": 8.0, "p_target_mgL": 0.2, "p_remove_mgL": 7.8,
                "method": "fecl3", "dose_mg_per_L": 61.2,
                "yearly_dose_kg_per_year": 5360.0,
                "method_note": "FeCl3 (Fe:P=1.5)",
                "target": "general_use",
            }
        eng = (
            f"🧪 Удаление фосфора (Metcalf & Eddy 5th §8-3 «Phosphorus Removal»).\n"
            f"📐 Параметры: P_in={ext15['p_in_mgL']:.1f} мг/л > "
            f"ПДК={ext15['p_target_mgL']} мг/л для '{ext15['target']}'.\n"
            f"📐 Метод: {ext15.get('method_note', ext15.get('method', 'fecl3'))}.\n"
            f"📐 ΔP = {ext15['p_remove_mgL']:.2f} мг/л, "
            f"доза реагента = {ext15['dose_mg_per_L']:.1f} мг/л.\n"
            f"📐 Стехиометрия FeCl3: 1.5 моль Fe / 1 моль P × M(FeCl3)/M(P) "
            f"= 1.5 × 162.2/30.97 ≈ 7.85 (мг FeCl3 на мг ΔP).\n"
            f"📋 ПДК P_total: рыбхоз 0.05 (Приказ Минсельхоза №552), "
            f"общ. 0.2 (СанПиН 2.1.5.980-00), полив 1.0, гор. канализация 5.0."
        )
        yearly_kg = ext15.get("yearly_dose_kg_per_year", 0)
        if yearly_kg >= 1000:
            yearly_str = f"{yearly_kg / 1000:.1f} т/год"
        else:
            yearly_str = f"{yearly_kg:.0f} кг/год"
        mgr = (
            f"🧪 Фосфор P={ext15['p_in_mgL']:.1f} мг/л выше норматива "
            f"({ext15['p_target_mgL']} мг/л) — нужно химическое осаждение "
            f"или биологическое EBPR.\n"
            f"💰 На Q={L0.Q_m3h} м³/ч:\n"
            f"  • Доза FeCl3 ≈ {ext15['dose_mg_per_L']:.0f} мг/л → "
            f"~{yearly_str} реагента\n"
            f"  • Дозирующая станция (насос + ёмкость + АСУ) — 350-650 тыс ₽\n"
            f"  • Если EBPR (биология) — анаэробный селектор +V_aerotank×0.2\n"
            f"⏱ FeCl3 — готовое решение (2-4 нед), EBPR — 6-8 нед запуска биоты.\n"
            f"📞 Передайте инженеру-технологу для выбора реагент vs EBPR по "
            f"OPEX (FeCl3 примерно 25-40 ₽/кг, EBPR — только электроэнергия)."
        )
        suggestions.append(InputSuggestion(
            field="L1.phosphorus_removal",
            current_value="не учтено",
            suggested_value=f"{ext15.get('method', 'fecl3').upper()} {ext15['dose_mg_per_L']:.0f} мг/л",
            reason=eng,
            reason_engineer=eng,
            reason_manager=mgr,
            severity="warning",
        ))

    # EXT-16 (Phase 34+ P2): денитрификация (Henze IWA §3.5)
    if "auto_denitrification_required" in triggers:
        ext16 = _check_ext_16_denitrification(L0, L1, computed)
        if ext16 is None:
            ext16 = {
                "no3_in_mgL": 50.0, "no3_target_mgL": 40.0, "no3_remove_mgL": 10.0,
                "cn_ratio": 5.0, "methanol_needed": False, "methanol_dose_mgL": 0.0,
                "recycle_ratio_pct": 25.0, "T_correction": 1.0, "T_c": 20.0,
                "V_anoxic_to_aerobic_ratio": 0.3,
                "target": "fishery_water",
            }
        eng = (
            f"🧪 Денитрификация NO3⁻ → N2↑ (Henze IWA 2008 §3.5 + "
            f"Metcalf & Eddy 5th §8-7).\n"
            f"📐 Параметры: NO3-N после нитрификации ≈ {ext16['no3_in_mgL']:.0f} "
            f"мг/л > ПДК={ext16['no3_target_mgL']:.0f} мг/л для '{ext16['target']}'.\n"
            f"📐 ΔNO3-N = {ext16['no3_remove_mgL']:.1f} мг/л, "
            f"C:N = БПК5/NO3 = {ext16['cn_ratio']:.1f}.\n"
            f"📐 Метанол: {'нужен' if ext16['methanol_needed'] else 'НЕ нужен'} "
            f"(C:N {'<4' if ext16['methanol_needed'] else '≥4'}), "
            f"доза {ext16['methanol_dose_mgL']:.1f} мг/л CH3OH "
            f"(стехиометрия 2.47 г/г NO3-N).\n"
            f"📐 Рециркуляция нитратов R = {ext16['recycle_ratio_pct']:.0f}% "
            f"(MLE pre-DN, Ludzack-Ettinger 1962).\n"
            f"📐 V_аноксич/V_аэроб ≈ {ext16['V_anoxic_to_aerobic_ratio']} "
            f"(HRT 1-3 ч в аноксической зоне).\n"
            f"📐 T-коррекция Arrhenius θ=1.07: k(T)/k(20) = "
            f"{ext16['T_correction']:.2f} при T={ext16['T_c']:.0f}°C.\n"
            f"📋 ПДК NO3-N: рыбхоз 40 (Приказ Минсельхоза №552), общ. 45, "
            f"полив 50, гор. канализация 80."
        )
        methanol_part = (
            f"  • Метанол {ext16['methanol_dose_mgL']:.0f} мг/л — "
            f"дозирующая система +250-400 тыс ₽\n"
            if ext16["methanol_needed"]
            else "  • Метанол НЕ нужен (углерода в стоках достаточно)\n"
        )
        mgr = (
            f"🧪 Нитраты NO3 {ext16['no3_in_mgL']:.0f} мг/л превышают ПДК "
            f"({ext16['no3_target_mgL']:.0f} для '{ext16['target']}') — нужна "
            f"анаэробная зона в аэротенке.\n"
            f"💰 На Q={L0.Q_m3h} м³/ч:\n"
            f"  • Дополнительная аноксическая зона ~30-50% от V_аэробной "
            f"— +25-40% к стоимости аэротенка\n"
            f"  • Рециркуляционный насос (R={ext16['recycle_ratio_pct']:.0f}%) "
            f"— 80-180 тыс ₽\n"
            f"{methanol_part}"
            f"  • Контроль NO3/DO/ORP — +120-220 тыс ₽\n"
            f"⏱ Срок: 4-6 нед проектирование. Запуск денитрифицирующей биоты "
            f"~3-5 недель параллельно нитрификации.\n"
            f"📞 Передайте технологу для расчёта объёма аноксической зоны и "
            f"схемы рециркуляции (MLE vs Bardenpho)."
        )
        suggestions.append(InputSuggestion(
            field="L1.denitrification_required",
            current_value="не учтено",
            suggested_value=f"аноксич. зона + R={ext16['recycle_ratio_pct']:.0f}%",
            reason=eng,
            reason_engineer=eng,
            reason_manager=mgr,
            severity="warning",
        ))

    # EXT-12 (v0.3 2026-05-13): термический derating двигателя (IEC 60034-1 §8.10)
    if "auto_motor_thermal_derate" in triggers and L1 and L1.liquid_temp_c is not None:
        T = L1.liquid_temp_c
        # K_derate из coefficients.json motor_thermal_derating_iec60034
        _K_DERATE_TABLE = [
            (40, 1.00), (50, 0.90), (60, 0.80), (65, 0.70), (70, 0.60),
        ]
        K = 1.0
        for T_max, k_val in _K_DERATE_TABLE:
            if T <= T_max:
                K = k_val
                break
        else:
            K = 0.60
        derate_pct = int((1.0 - K) * 100)
        eng = (
            f"🔥 IEC 60034-1:2017 §8.10.2 «Temperature derating» — "
            f"снижение допустимой мощности двигателя при повышенной "
            f"температуре жидкости.\n"
            f"📐 Поправка K_derate = {K:.2f} ({derate_pct}% derating) при "
            f"T_жидк = {T:.0f}°C.\n"
            f"  • T ≤40°C: K=1.00 (номинал, класс изоляции F)\n"
            f"  • T 41-50°C: K=0.90 (граница F)\n"
            f"  • T 51-60°C: K=0.80 + обязателен класс H (180°C)\n"
            f"  • T 61-65°C: K=0.70 + PTC-термистор обмотки\n"
            f"  • T >65°C: K=0.60 + jacket cooling или поверхностный насос\n"
            f"⚠ Без derate двигатель сгорает за 1-3 месяца. ГОСТ Р 52776."
        )
        mgr = (
            f"🌡 Температура стоков {T:.0f}°C — выше нормы для стандартного "
            f"двигателя.\n"
            f"💰 Нужны:\n"
            f"  • Двигатель класса H (изоляция 180°C) — +25-40% к цене насоса\n"
            f"  • PTC-термистор обмотки + защита класса 10A в ШУ — +15-30 тыс ₽\n"
            f"  • Запас мощности {derate_pct}% — берите следующий типоразмер\n"
            f"⏱ Срок изготовления Ex-H исполнения +6-10 недель.\n"
            f"📞 Передайте инженеру для подбора Wilo Rexa SUPRA-class или "
            f"KSB Amarex KRT с water-jacket cooling."
        )
        suggestions.append(InputSuggestion(
            field="L1.liquid_temp_c",
            current_value=f"{T:.0f}°C",
            suggested_value=f"K_derate={K:.2f}, изоляция H",
            reason=eng,
            reason_engineer=eng,
            reason_manager=mgr,
            severity="critical" if T > 60 else "warning",
        ))

    # EXT-13 (v0.3 2026-05-13): анаэробная биокоррозия бетона при простоях
    if "auto_anaerobic_corrosion_risk" in triggers:
        cycles = (computed.cycles_per_hour_estimate
                  if computed and computed.cycles_per_hour_estimate is not None
                  else 0.0)
        eng = (
            "🦠 Metcalf & Eddy «Wastewater Engineering» 5th ed. (2014) §5-4 — "
            "анаэробная биокоррозия бетона КНС.\n"
            "📐 Механизм:\n"
            "  • При простое >12ч сульфаты SO4²⁻ восстанавливаются "
            "бактериями Desulfovibrio до H2S (анаэробно).\n"
            "  • H2S мигрирует в крышку, где влажная плёнка + Thiobacillus → "
            "H2SO4 (pH 1-2).\n"
            "  • Скорость разрушения бетона: 5-15 мм/год по своду крышки.\n"
            f"⚠ Расчётные циклы вкл/выкл: {cycles:.2f}/ч — слишком "
            f"редкие пуски (норма 2-15/ч).\n"
            "📋 Меры:\n"
            "  • Защитное покрытие бетона эпоксидом (Sika, MasterSeal) — "
            "20 лет ресурса\n"
            "  • Вентиляция приёмной камеры 8-12 крат/ч (СП 60.13330 §7.5)\n"
            "  • Nitrate-shock dosing (NaNO3, 50-100 мг/л при простоях)\n"
            "  • Или замена на ПЭ/стеклопластик корпус (нет H2S коррозии)."
        )
        mgr = (
            "🦠 Большие интервалы между запусками → биокоррозия бетона.\n"
            "💰 Защита:\n"
            "  • Эпоксидное покрытие бетонной крышки — 80-150 тыс ₽\n"
            "  • Вентилятор + воздуховоды — 45-90 тыс ₽\n"
            "  • Дозатор нитратов NaNO3 (опционально) — 35-60 тыс ₽\n"
            "  • Или сразу ПЭ-корпус (Серво-Юг default) — без коррозии\n"
            "⏱ Без защиты бетонный корпус разрушится за 5-10 лет вместо 50.\n"
            "📞 Передайте инженеру для решения о материале корпуса."
        )
        suggestions.append(InputSuggestion(
            field="L1.corpus_material",
            current_value="bетон (предполагается)",
            suggested_value="pe (ПЭ) или защитное покрытие бетона",
            reason=eng,
            reason_engineer=eng,
            reason_manager=mgr,
            severity="warning",
        ))

    # EXT-10: гидробак ВНС (СП 30.13330)
    if "auto_hydrobak_required" in triggers:
        # V_бака = (Q_max - Q_min)·t_цикл/4, типовое t_цикл=6 мин (10 пусков/час)
        Q_min = L0.Q_m3h * 0.2  # типовое 20% от номинала
        Q_max = L0.Q_m3h
        t_cycle_min = 6.0
        V_bak_l = (Q_max - Q_min) * 1000 * (t_cycle_min / 60) / 4
        eng = (
            f"💧 СП 30.13330.2020 «Внутренний водопровод», п.11.7 — "
            f"гидроаккумулятор для повысительной насосной с переменным расходом.\n"
            f"📐 Расчёт ёмкости: V_бака = (Q_max - Q_min)·t_цикл / 4·a, "
            f"где a — число включений/час (обычно ≤ 10), t_цикл — "
            f"длительность одного цикла.\n"
            f"Для Q_max={Q_max:.1f}, Q_min={Q_min:.1f} м³/ч, t=6 мин:\n"
            f"V = ({Q_max:.1f} - {Q_min:.1f}) · 1000 · (6/60) / 4 ≈ "
            f"{V_bak_l:.0f} литров.\n"
            f"⚠ Без гидробака ЧРП работает в режиме «дёрганья» — "
            f"частые пуски, гидроудары, износ обратного клапана."
        )
        mgr = (
            f"💧 Q={L0.Q_m3h} м³/ч ВНС чистой воды — нужен гидроаккумулятор "
            f"для сглаживания пиков (СП 30.13330).\n"
            f"💰 Мембранный гидробак ~{V_bak_l:.0f} л:\n"
            f"  • Reflex / Wester / Джилекс 500-1000 л — 45-95 тыс ₽\n"
            f"  • Большой 2000-5000 л — 180-380 тыс ₽\n"
            f"  • Манометр + предохранительный клапан — 8-15 тыс ₽\n"
            f"  • Подключение + мембраны замена раз в 5 лет — 12-25 тыс ₽\n"
            f"⏱ Без гидробака — частые пуски ЧРП (ресурс ЧРП -50%, "
            f"замена 280-450 тыс ₽ через 2-3 года вместо 6-8)."
        )
        suggestions.append(InputSuggestion(
            field="L1.hydrobak_volume_l",
            current_value="не учтено",
            suggested_value=f"{V_bak_l:.0f} л",
            reason=eng,
            reason_engineer=eng,
            reason_manager=mgr,
            severity="warning",
        ))

    # EXT-11: anti-buoyancy при УГВ > 0 (СП 32 §6.3 + Архимед).
    # Если УГВ выше отметки земли, площадка затоплена — корпус КНС всплывёт
    # без бетонного пригруза. Critical, suggestion с ценой пригруза.
    if (
        "auto_groundwater_above_surface" in triggers
        and L1
        and L1.groundwater_level_m is not None
    ):
        gw = L1.groundwater_level_m
        # Грубая оценка V_корпуса по Q (см. _estimate_corpus_volume_m3).
        if L0.Q_m3h <= 30:
            V_corpus = 5.7
        elif L0.Q_m3h <= 60:
            V_corpus = 6.8
        elif L0.Q_m3h <= 130:
            V_corpus = 12.6
        elif L0.Q_m3h <= 252:
            V_corpus = 28.3
        else:
            V_corpus = 55.4
        # F_Архимеда = ρ·g·V (ρ=1000, g=9.81)
        F_arch_kn = 1000 * 9.81 * V_corpus / 1000.0  # кН
        F_arch_t = F_arch_kn / 9.81  # тонн (масса эквивалента)
        # V_бетона ≥ F / (ρ_бет_эфф · g), ρ_эфф_подвода = 1400
        V_concrete_m3 = F_arch_kn * 1000.0 / (1400.0 * 9.81)
        eng = (
            f"⚓ Закон Архимеда + СП 32.13330.2018 §6.3 — расчёт пригруза.\n"
            f"📐 Подъёмная сила: F = ρ_воды · g · V_корпуса = "
            f"1000 · 9.81 · {V_corpus:.1f} = {F_arch_kn:.0f} кН ({F_arch_t:.1f} тонн).\n"
            f"📐 Удержание ж/б пригрузом: V_бетон ≥ F / (ρ_бет_эфф · g), "
            f"где ρ_бет_эфф = ρ_бет − ρ_воды = 2400 − 1000 = 1400 кг/м³ "
            f"(бетон сам в воде).\n"
            f"V_бетон = {F_arch_kn:.0f} · 1000 / (1400 · 9.81) ≈ "
            f"{V_concrete_m3:.1f} м³ ж/б класса B20-B25.\n"
            f"При УГВ = {gw:+.1f} м (выше уровня земли) площадка постоянно "
            f"затоплена — без пригруза корпус всплывёт за 1-3 года при паводке.\n"
            f"⚠ K_запаса = 1.1 (СП 32 §6.3); для Ex-зон и I категории — 1.5."
        )
        mgr = (
            f"⚓ УГВ выше земли на {gw:+.1f} м — площадка затоплена. "
            f"Без бетонного пригруза корпус КНС всплывёт через 2-3 года "
            f"при первом паводке.\n"
            f"💰 Стоимость:\n"
            f"  • Ж/б пригруз ({V_concrete_m3:.1f} м³ ≈ {F_arch_t:.0f} тонн) — "
            f"200-500 тыс ₽ сразу (бетон + арматура + опалубка).\n"
            f"  • Усиление обоймы корпуса по СП 22 §5.4 — +50-150 тыс ₽.\n"
            f"⚠ Если не учесть: аварийный ремонт (откопка + монтаж пригруза + "
            f"замена корпуса) — 500-1500 тыс ₽ + остановка КНС на 2 недели.\n"
            f"📞 Передайте инженеру для детального расчёта по СП 32 §6.3 "
            f"(structural/ballast.py)."
        )
        suggestions.append(InputSuggestion(
            field="L1.groundwater_level_m",
            current_value=f"{gw:+.1f}",
            suggested_value=f"ж/б пригруз {V_concrete_m3:.1f} м³",
            reason=eng,
            reason_engineer=eng,
            reason_manager=mgr,
            severity="critical",
        ))

    # ──────────────────────────────────────────────────────────────────
    # 2026-05-11: 11 legacy triggers без отдельной InputSuggestion —
    # дополняем 2-level пояснения для UI «возможно вы имели в виду».
    # Frontend рендерит таб «Инженер»/«Менеджер» по reason_engineer/_manager.
    # ──────────────────────────────────────────────────────────────────

    # LEG-1: auto_q_high — Q > 500 м³/ч
    if "auto_q_high" in triggers:
        eng = (
            f"📈 Q={L0.Q_m3h} м³/ч > 500 — выход за диапазон бюджетных серий "
            f"(ANTARUS / Pedrollo / CNP заканчиваются на ~400-500 м³/ч).\n"
            f"🔬 Для такого расхода применяются промышленные классы: "
            f"  • Центробежные одноступенчатые (KSB Sewabloc, Wilo EMU FA) "
            f"до 1500 м³/ч.\n"
            f"  • Многоступенчатые ЦНС (ЦНС-300, ЦНС-500) для напоров > 50 м.\n"
            f"📐 NPSHr таких насосов 5-8 м — требуется проверка кавитации.\n"
            f"⚠ AOR-зона уже на 70-115% BEP; работа вне AOR резко снижает "
            f"ресурс рабочего колеса (СП 32 §6.5)."
        )
        mgr = (
            f"🏭 Расход {L0.Q_m3h} м³/ч — это уже промышленный масштаб "
            f"(район/посёлок/завод).\n"
            f"💰 Цена:\n"
            f"  • Насос промышленный — 500 тыс — 2.5 млн ₽ за единицу.\n"
            f"  • КНС-комплект 2+1 — 3-8 млн ₽ под ключ.\n"
            f"⏱ Срок поставки нестандартного заказа — 4-8 недель "
            f"(склада нет, делают под проект).\n"
            f"📞 Обязательно передайте инженеру — нужен индивидуальный "
            f"расчёт магистральной КНС, бюджетные серии не подойдут."
        )
        suggestions.append(InputSuggestion(
            field="Q_m3h",
            current_value=f"{L0.Q_m3h}",
            suggested_value="промышленная КНС, инженерный подбор",
            reason=eng,
            reason_engineer=eng,
            reason_manager=mgr,
            severity="warning",
        ))

    # LEG-2: auto_h_high — H_full > 80 м
    if "auto_h_high" in triggers:
        eng = (
            f"📈 H_full={computed.H_full_m:.1f} м > 80 — за пределами "
            f"одноступенчатых центробежных канализационных насосов.\n"
            f"🔬 Для H>80 нужны:\n"
            f"  • Многоступенчатые насосы CR/MFL/ЦНС (вертикальные in-line).\n"
            f"  • Либо бустер-станция: 2 КНС последовательно с промежуточным "
            f"резервуаром (СП 32 §6.5).\n"
            f"📐 NPSH_required растёт с числом ступеней (NPSHr ~ k·√i) — "
            f"риск кавитации при низком подпоре."
        )
        mgr = (
            f"⛰ Напор {computed.H_full_m:.0f} м — это подъём на 20+ этажей. "
            f"Обычные канализационные насосы такое не вытягивают.\n"
            f"💰 Цена:\n"
            f"  • Многоступенчатый насос CR/MFL — 600 тыс — 1.2 млн ₽.\n"
            f"  • Бустер-станция (2 КНС) — 1.5-3 млн ₽.\n"
            f"⏱ Спецзаказ под проект, срок 4-6 недель.\n"
            f"📞 Передайте инженеру — нужен расчёт по двум вариантам "
            f"(одна высоконапорная vs две последовательные)."
        )
        suggestions.append(InputSuggestion(
            field="H_full_m",
            current_value=f"{computed.H_full_m:.1f}",
            suggested_value="multi-stage или бустер",
            reason=eng,
            reason_engineer=eng,
            reason_manager=mgr,
            severity="warning",
        ))

    # LEG-3: auto_industrial — wastewater_type=industrial
    if "auto_industrial" in triggers:
        eng = (
            "🏭 Промстоки требуют индустриального класса оборудования:\n"
            "📐 free_passage насоса ≥ 35-50 мм (вместо 10-20 для бытовых).\n"
            "📐 Материалы: чугун ВЧШГ / нерж 316L (против абразива и "
            "коррозии); сталь для t > 60°C.\n"
            "⚡ Электрика по зонам ATEX (если есть органика/растворители): "
            "II 2G Ex db IIB T4 — насос+ЩУ+датчики уровня.\n"
            "🧪 Возможна необходимость песколовки/гидроциклона перед КНС "
            "(СП 32 §7.4) и аэротенка для биологии (СП 32 §9)."
        )
        mgr = (
            f"🏭 Промстоки ({L0.Q_m3h} м³/ч) — это совсем другой класс "
            f"оборудования, не бытовой.\n"
            f"💰 Наценка к бытовому варианту:\n"
            f"  • Чугунный/нержавеющий насос — +50-100% к цене.\n"
            f"  • ATEX-исполнение (если требуется) — ещё +30-50%.\n"
            f"  • Песколовка/гидроциклон — +200-500 тыс ₽.\n"
            f"⏱ Срок поставки 6-10 недель (производство под заказ).\n"
            f"📞 Уточните у клиента: состав стоков (pH, T, абразив, "
            f"взрывоопасность), это влияет на цену в 2-3 раза."
        )
        suggestions.append(InputSuggestion(
            field="wastewater_type",
            current_value="industrial",
            suggested_value="индустриальный класс, требуется анализ стоков",
            reason=eng,
            reason_engineer=eng,
            reason_manager=mgr,
            severity="warning",
        ))

    # LEG-4: auto_fire_protection
    if "auto_fire_protection" in triggers:
        eng = (
            "🔥 Пожарная насосная установка (ПНУ) — отдельный класс по СП "
            "8.13130.2020 «Источники наружного противопожарного водоснабжения» "
            "и СП 10.13130.2020 «Внутренний противопожарный водопровод».\n"
            "📐 Обязательный состав:\n"
            "  • Резервуар пожарного запаса (V по СП 8 §6 = 3 ч × Q_расч).\n"
            "  • Насос рабочий + резервный (1+1, СП 10 §6.5).\n"
            "  • Жокей-насос для поддержания давления.\n"
            "  • Автоматика по ГОСТ Р 53325 (датчики давления, ШУ ПНУ).\n"
            "⚠ Расчёт Q_расч и H_расч зависит от категории помещения "
            "(А-Д), типа спринклеров, длины самых удалённых ветвей."
        )
        mgr = (
            "🔥 Пожарная установка — это не наш стандартный профиль. "
            "Требует индивидуального проектирования и сертификации МЧС.\n"
            "💰 Ориентир:\n"
            "  • Насосы + ШУ ПНУ — 400 тыс — 1.5 млн ₽.\n"
            "  • Резервуар 50-200 м³ — 500 тыс — 1.5 млн ₽.\n"
            "  • Проект + согласование с МЧС — 200-500 тыс ₽.\n"
            "⏱ Полный цикл (проект → согласование → монтаж → испытания) — "
            "1-3 месяца.\n"
            "📞 Передайте инженеру и менеджеру по пожарным проектам — "
            "это смежная компетенция, отдельный продукт."
        )
        suggestions.append(InputSuggestion(
            field="wastewater_type",
            current_value="fire_protection",
            suggested_value="пожарная установка, отдельное проектирование",
            reason=eng,
            reason_engineer=eng,
            reason_manager=mgr,
            severity="critical",
        ))

    # LEG-5: auto_ex — Ex_required=True
    if "auto_ex" in triggers and L1 and L1.Ex_required:
        eng = (
            "⚠ Взрывозащищённое исполнение по ТР ТС 012/2011 и ГОСТ "
            "IEC 60079-0:\n"
            "📐 Маркировка для КНС: II 2G Ex db IIB T4 Gb или II 3G "
            "Ex eb IIA T3.\n"
            "🔬 Применяется когда в стоках возможны летучие "
            "углеводороды/растворители (АЗС, нефтебазы, СТО, химпром).\n"
            "⚡ Требования:\n"
            "  • NPSHa critical (нельзя допускать кавитацию — искра).\n"
            "  • Корпус двигателя: алюминий/чугун с искробезопасным "
            "монтажом, кабельные вводы Ex e.\n"
            "  • ШУ — в отдельном безопасном помещении или Ex-исполнение.\n"
            "  • Заземление обязательно (ПУЭ 7.3.139) + протокол замера."
        )
        mgr = (
            "⚡ Взрывозащищённый насос — спецзаказ для опасных зон "
            "(АЗС, нефтебаза, химия).\n"
            "💰 Наценка к стандартному исполнению:\n"
            "  • Насос Ex (Grundfos SE/SL, Wilo EMU FA) — +30-50%.\n"
            "  • Ex-кабель + вводы — +50-100 тыс ₽.\n"
            "  • Сертификат Ex-зоны от Ростехнадзора — 80-150 тыс ₽.\n"
            "⏱ Срок поставки 8-12 недель (нет на складе, делают под заказ).\n"
            "📞 Уточните у клиента класс зоны (1/2 = 2G/3G) и группу газов "
            "(IIA/IIB/IIC). Без этого подобрать нельзя."
        )
        suggestions.append(InputSuggestion(
            field="L1.Ex_required",
            current_value="True",
            suggested_value="ATEX II 2G/3G, спецзаказ",
            reason=eng,
            reason_engineer=eng,
            reason_manager=mgr,
            severity="critical",
        ))

    # LEG-6: auto_npsha_low — NPSHa < 5 м (горы)
    if "auto_npsha_low" in triggers and L1 and L1.altitude_m and computed.npsha_m is not None:
        eng = (
            f"🌡 NPSHa={computed.npsha_m:.2f} м < 5 м на высоте "
            f"{L1.altitude_m:.0f} м над уровнем моря.\n"
            f"📐 Формула: NPSHa = (P_atm - P_vapor)/(ρ·g) - H_suction - h_тр.\n"
            f"  • P_atm с высотой падает по барометрической формуле "
            f"(P = P₀·exp(-h/8400)); на 2000 м ~80 кПа vs 101 на 0 м.\n"
            f"  • P_vapor растёт с температурой (при T=60°C ≈ 20 кПа).\n"
            f"⚠ NPSHr типичных канализационных насосов 2-4 м. "
            f"NPSHa - NPSHr < 0.5 м = кавитация (шум, эрозия колеса, "
            f"снижение Q-H кривой).\n"
            f"💡 Решение: насос с низким NPSHr (Grundfos SEG Quick-action, "
            f"WILO Drain TS) либо подпор / снижение T."
        )
        mgr = (
            f"⛰ Объект на высоте {L1.altitude_m:.0f} м — воздух разрежен, "
            f"обычные насосы будут кавитировать (шуметь, ломать колесо).\n"
            f"💰 Последствия:\n"
            f"  • Без спецнасоса — рабочее колесо разрушается за 6-12 мес.\n"
            f"  • Аварийный ремонт + замена колеса — 200-500 тыс ₽.\n"
            f"  • Эксплуатация в шуме > 80 дБ — жалобы клиента.\n"
            f"💡 Решение: насос с низким NPSHr (Grundfos SEG, WILO TS) — "
            f"+20-30% к цене стандартного, но окупится за 2 года.\n"
            f"📞 Передайте инженеру для проверки NPSHr-кривой "
            f"конкретной модели по высоте объекта."
        )
        suggestions.append(InputSuggestion(
            field="L1.altitude_m",
            current_value=f"{L1.altitude_m:.0f}",
            suggested_value="насос с низким NPSHr",
            reason=eng,
            reason_engineer=eng,
            reason_manager=mgr,
            severity="critical",
        ))

    # LEG-7: auto_l_long_zhukovsky — L > 500 м
    if "auto_l_long_zhukovsky" in triggers:
        # Δp_удар = ρ·a·Δv; для PE100 a=320 м/с, для стали ~1100 м/с
        a_pe = 320
        a_steel = 1100
        v_typ = computed.v_ms if computed.v_ms > 0 else 1.5
        dp_pe_bar = 1000 * a_pe * v_typ / 1e5
        dp_steel_bar = 1000 * a_steel * v_typ / 1e5
        eng = (
            f"💥 Закон Жуковского: Δp_удар = ρ·a·Δv, где a — скорость "
            f"распространения волны (м/с).\n"
            f"📐 Для L={L0.L_m:.0f} м, v={v_typ:.2f} м/с:\n"
            f"  • ПЭ100: a≈320 м/с → Δp = 1000·320·{v_typ:.2f} ≈ {dp_pe_bar:.0f} бар.\n"
            f"  • Сталь: a≈1100 м/с → Δp ≈ {dp_steel_bar:.0f} бар.\n"
            f"⚠ Гидроудар возникает при резком закрытии обратного клапана "
            f"или останове насоса — может разорвать трубу/арматуру.\n"
            f"💡 Решения:\n"
            f"  • Обратный клапан с soft-close (демпфирование) — обязателен.\n"
            f"  • Уравнительная башня / воздушный колпак (для длинных трасс).\n"
            f"  • ЧРП на насосе с плавным остановом (rampdown ≥10 с)."
        )
        mgr = (
            f"💥 Трасса {L0.L_m:.0f} м — длинная, при резком останове насоса "
            f"возникает гидроудар (как удар молотом по трубе).\n"
            f"💰 Без защиты:\n"
            f"  • Обычный обратный клапан треснет за 1-3 удара.\n"
            f"  • Возможен разрыв трубы или арматуры — замена 800 тыс — 2 млн ₽ "
            f"(земляные работы + труба + простой).\n"
            f"💡 Решение: обратный клапан с soft-close (демпфер) — "
            f"+40-80 тыс ₽ к стандартному. Окупается с первой аварией.\n"
            f"⏱ Срок поставки клапана с демпфером — 1-2 недели."
        )
        suggestions.append(InputSuggestion(
            field="L_m",
            current_value=f"{L0.L_m:.0f}",
            suggested_value="soft-close клапан обязателен",
            reason=eng,
            reason_engineer=eng,
            reason_manager=mgr,
            severity="warning",
        ))

    # LEG-8: auto_category_I — I категория надёжности
    if "auto_category_I" in triggers:
        eng = (
            "🏛 СП 31.13330.2021 «Водоснабжение. Наружные сети», табл.7.1 — "
            "I категория надёжности (объекты, перерыв в работе которых "
            "недопустим > 10 мин).\n"
            "📐 Требования:\n"
            "  • Резервирование 2+1 минимум (2 рабочих + 1 резерв).\n"
            "  • Два независимых источника электропитания (ПУЭ 1.2.18) "
            "+ АВР на вводе.\n"
            "  • Резервный электроагрегат (ДГУ) или питание от двух подстанций.\n"
            "  • Автоматическое управление, диспетчеризация.\n"
            "⚠ По СП 32 §6.2 для КНС I кат. редундантность пересчитывается:\n"
            "  • Schema 1+1 → 2+1 = 3 насоса.\n"
            "  • Schema 2+1 → 3+1 = 4 насоса."
        )
        mgr = (
            "🏛 I категория надёжности — объект критической важности "
            "(больница, водозабор, металлургия). Простой запрещён > 10 минут.\n"
            "💰 Цена удваивается:\n"
            "  • Насосов 3 вместо 2 (раб+раб+рез) — +50% к насосам.\n"
            "  • Два независимых ввода питания + АВР — 200-500 тыс ₽.\n"
            "  • ДГУ резервный — 600 тыс — 2 млн ₽ (зависит от мощности).\n"
            "  • Автоматика, диспетчеризация — 200-400 тыс ₽.\n"
            "⏱ Срок проектирования и монтажа +4-6 недель.\n"
            "📞 Уточните у клиента: реальная I кат. или просто перестраховка? "
            "Иногда II кат. достаточно (×1.3 вместо ×2)."
        )
        suggestions.append(InputSuggestion(
            field="L1.reliability_category",
            current_value="I",
            suggested_value="2+1 + 2 ввода + ДГУ",
            reason=eng,
            reason_engineer=eng,
            reason_manager=mgr,
            severity="critical",
        ))

    # LEG-9: auto_no_match — кандидатов нет
    if "auto_no_match" in triggers:
        eng = (
            f"🔍 Ни один насос из БД не попадает в envelope "
            f"Q={L0.Q_m3h} м³/ч × H={computed.H_full_m:.1f} м.\n"
            f"📐 Возможные причины:\n"
            f"  • Q или H за диапазоном БД (текущая БД 0.5-500 м³/ч, 5-100 м).\n"
            f"  • Жёсткий фильтр L1 (IP_motor, Ex, wastewater_type) "
            f"отсёк всех кандидатов.\n"
            f"  • Комбинация параметров нетипична (например, Q=1 м³/ч H=80 м — "
            f"нужен бытовой дозирующий, не КНС).\n"
            f"💡 Решения:\n"
            f"  • Ослабить L1-фильтры (попробовать без Ex / без точного IP).\n"
            f"  • Проверить единицы Q (л/с vs м³/ч).\n"
            f"  • Передать инженеру для подбора по импортному каталогу."
        )
        mgr = (
            f"🔍 По заданным параметрам Q={L0.Q_m3h}/H={computed.H_full_m:.1f} "
            f"наших стандартных насосов не нашлось.\n"
            f"💰 Что делать:\n"
            f"  • Уточните данные у клиента (возможно ошибка в единицах).\n"
            f"  • Передайте инженеру для индивидуального подбора.\n"
            f"⏱ Ответ инженера обычно за 1-3 рабочих дня. "
            f"Бывает что подходит импортный/нестандартный насос — "
            f"тогда срок поставки до 8-12 недель и цена +50-100% к каталожной."
        )
        suggestions.append(InputSuggestion(
            field="Q_m3h",
            current_value=f"{L0.Q_m3h}/{computed.H_full_m:.1f}",
            suggested_value="инженерный подбор",
            reason=eng,
            reason_engineer=eng,
            reason_manager=mgr,
            severity="critical",
        ))

    # LEG-10: auto_low_match_count — мало кандидатов (< 2)
    if "auto_low_match_count" in triggers:
        eng = (
            f"⚠ Найден всего 1 насос для Q={L0.Q_m3h}/H={computed.H_full_m:.1f}.\n"
            f"📐 Это значит:\n"
            f"  • Точка работы близка к границе AOR (точка наименьшей энергии).\n"
            f"  • КПД может быть низким (BEP далеко от рабочей точки).\n"
            f"  • Износ ускоренный (работа вне POR/AOR).\n"
            f"⚠ score обычно < 0.4 — насос работать будет, но не оптимально.\n"
            f"💡 Решение: рассмотреть параллельную работу двух меньших "
            f"насосов или сместить точку (другая труба → другой H)."
        )
        mgr = (
            "⚠ По вашим параметрам подходит только 1 насос — он будет "
            "работать, но не в оптимальной точке.\n"
            "💰 Что это значит на практике:\n"
            "  • КПД ниже паспортного на 10-20% → перерасход электричества "
            "30-50% от номинала.\n"
            "  • Для типового насоса 5 кВт это +1500-2500 кВт·ч/год = "
            "+15-30 тыс ₽/год к счёту за свет.\n"
            "  • За 5 лет переплата по OPEX 75-150 тыс ₽.\n"
            "💡 Рекомендуем уточнить параметры с инженером и/или "
            "посмотреть альтернативу (2 меньших насоса в параллель)."
        )
        suggestions.append(InputSuggestion(
            field="Q_m3h",
            current_value=f"{L0.Q_m3h}/{computed.H_full_m:.1f}",
            suggested_value="проверить альтернативы",
            reason=eng,
            reason_engineer=eng,
            reason_manager=mgr,
            severity="warning",
        ))

    # LEG-11: auto_pipe_temp_incompatible — уже обработан suggestion #6 (eng_pipe).
    # Этот блок служит fallback для случаев, когда suggestion #6 не сработал
    # (например, нет L1.pipe_material, но trigger пришёл из другой логики).
    if "auto_pipe_temp_incompatible" in triggers and not any(
        s.field == "L1.pipe_material" for s in suggestions
    ):
        pipe_mat = L1.pipe_material if L1 else "неизвестно"
        temp_c = L1.liquid_temp_c if L1 else 0
        eng = (
            f"🧪 {pipe_mat} + T={temp_c}°C — материал не выдержит длительной "
            f"эксплуатации при такой температуре (ISO 4427 для ПЭ100: T_max=60°C).\n"
            f"📐 По Аррениусу срок службы падает в 5-10 раз. См. полную "
            f"справку в suggestion на pipe_material."
        )
        mgr = (
            f"🔥 Полимерная труба и горячие стоки T={temp_c}°C — несовместимы. "
            f"Через 6-12 мес труба потечёт. См. рекомендацию по замене "
            f"материала (сталь/чугун) в основном suggestion."
        )
        suggestions.append(InputSuggestion(
            field="L1.pipe_material",
            current_value=f"{pipe_mat}",
            suggested_value="steel_seamless_new или cast_iron_new",
            reason=eng,
            reason_engineer=eng,
            reason_manager=mgr,
            severity="critical",
        ))

    return suggestions
