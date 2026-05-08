"""Parse pegas_full_dump.json -> structured pegas_engineering.json for kns-calculator."""
import io
import json
import re
import sys

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

DUMP_PATH = r'C:\Users\User\Desktop\kns-calculator-repo\backend\_scripts\pegas_full_dump.json'
OUT_PATH = r'C:\Users\User\Desktop\kns-calculator-repo\02_dataset\corpora\pegas_engineering.json'


def parse_price(s):
    if s is None or s == '':
        return None
    s = str(s).replace('р.', '').replace('\xa0', ' ').replace(' ', '').replace(',', '.')
    s = s.strip()
    if not s:
        return None
    try:
        v = float(s)
        return int(round(v))
    except ValueError:
        return None


def parse_num(s):
    if s is None or s == '':
        return None
    if isinstance(s, (int, float)):
        return s
    s = str(s).strip().replace(',', '.').replace('\xa0', '').replace(' ', '')
    if not s:
        return None
    try:
        v = float(s)
        if v.is_integer():
            return int(v)
        return v
    except ValueError:
        return None


def parse_dims_dxshxv(s):
    if not s:
        return None
    parts = re.split(r'[*х×x/]', str(s).strip())
    parts = [p.strip() for p in parts if p.strip()]
    if len(parts) >= 3:
        try:
            return {
                "L_cm": float(parts[0].replace(',', '.')),
                "W_cm": float(parts[1].replace(',', '.')),
                "H_cm": float(parts[2].replace(',', '.')),
            }
        except ValueError:
            return None
    return None


def parse_dh(s):
    if not s:
        return None
    parts = re.split(r'[*х×x]', str(s).strip())
    parts = [p.strip() for p in parts if p.strip()]
    if len(parts) == 2:
        try:
            return {
                "D_cm": float(parts[0].replace(',', '.')),
                "H_cm": float(parts[1].replace(',', '.')),
            }
        except ValueError:
            return None
    return None


_TR = {
    'а': 'a', 'б': 'b', 'в': 'v', 'г': 'g', 'д': 'd', 'е': 'e', 'ж': 'zh',
    'з': 'z', 'и': 'i', 'й': 'y', 'к': 'k', 'л': 'l', 'м': 'm', 'н': 'n',
    'о': 'o', 'п': 'p', 'р': 'r', 'с': 's', 'т': 't', 'у': 'u', 'ф': 'f',
    'х': 'h', 'ц': 'c', 'ч': 'ch', 'ш': 'sh', 'щ': 'sch', 'ъ': '', 'ы': 'y',
    'ь': '', 'э': 'e', 'ю': 'yu', 'я': 'ya'
}


def slugify(s):
    s = str(s).lower().strip().replace('ё', 'e')
    s = ''.join(_TR.get(c, c) for c in s)
    s = re.sub(r'[^a-z0-9]+', '-', s)
    s = re.sub(r'-+', '-', s).strip('-')
    return s


with open(DUMP_PATH, encoding='utf-8') as f:
    d = json.load(f)

sheets = d['sheets']
problematic = []


def parse_sbo_row(row, mode):
    if len(row) < 8 or not row[0]:
        return None
    name = row[0].strip()
    persons = row[1]
    if persons and '-' in str(persons):
        try:
            persons_max = int(str(persons).split('-')[1])
        except (ValueError, IndexError):
            persons_max = None
    else:
        persons_max = parse_num(persons)
    return {
        "id": slugify("pegas-base-" + name + "-" + mode),
        "label": name,
        "discharge_mode": mode,
        "capacity_persons": persons_max,
        "capacity_persons_raw": persons,
        "Q_m3sut": parse_num(row[2]),
        "salvo_discharge_l": parse_num(row[3]),
        "power_kw": parse_num(row[4]),
        "weight_kg": parse_num(row[5]),
        "dimensions_cm": parse_dims_dxshxv(row[6]),
        "dimensions_raw": row[6],
        "price_rub_2023": parse_price(row[7]),
    }


# === pegas_base ===
pegas_base_models = []
for row in sheets['СБО PEGAS'][6:15]:
    m = parse_sbo_row(row, 'gravity')
    if m:
        pegas_base_models.append(m)
for row in sheets['СБО PEGAS'][17:26]:
    m = parse_sbo_row(row, 'pressure')
    if m:
        pegas_base_models.append(m)

pegas_base_addons = []
for row in sheets['СБО PEGAS'][28:32]:
    if not row or not row[0]:
        continue
    name = row[0].strip().split('\n')[0].split(' скидок')[0]
    pegas_base_addons.append({
        "id": slugify("pegas-addon-" + name),
        "label": name,
        "description": row[1] if len(row) > 1 else None,
        "price_rub_2023": parse_price(row[7] if len(row) > 7 else (row[-1] if row else None)),
    })

pegas_base_extensions = []
for row in sheets['СБО PEGAS'][2:4]:
    if len(row) >= 5 and row[3]:
        pegas_base_extensions.append({
            "id": slugify("pegas-extension-" + row[3]),
            "label": "Удлинительная горловина " + row[3] + " мм",
            "size_mm_raw": row[3],
            "price_rub_2023": parse_price(row[4]),
        })

# === pegas_premium ===
pegas_premium_models = []
for row in sheets['PEGAS PREMIUM'][4:9]:
    if not row or not row[0]:
        continue
    pegas_premium_models.append({
        "id": slugify("pegas-premium-" + row[0]),
        "label": row[0].strip(),
        "capacity_persons": parse_num(row[1]),
        "Q_m3sut": parse_num(row[2]),
        "salvo_discharge_l": parse_num(row[3]),
        "dimensions_cm": parse_dims_dxshxv(row[4]),
        "dimensions_raw": row[4],
        "weight_kg": parse_num(row[5]),
        "price_rub_2023": parse_price(row[6]),
    })

# === pegas_ekonom ===
pegas_ekonom_models = []
for row in sheets['PEGAS EKONOM'][2:6]:
    if not row or not row[0]:
        continue
    pegas_ekonom_models.append({
        "id": slugify("pegas-ekonom-" + row[0]),
        "label": row[0].strip(),
        "capacity_persons": parse_num(row[1]),
        "Q_m3sut": parse_num(row[2]),
        "salvo_discharge_l": parse_num(row[3]),
        "weight_kg": parse_num(row[4]),
        "dimensions_cm": parse_dims_dxshxv(row[5]),
        "dimensions_raw": row[5],
        "price_rub_2023": parse_price(row[7]),
    })

# === pegas_lite ===
pegas_lite_models = []
for row in sheets['PEGAS LITE'][2:5]:
    if not row or not row[0]:
        continue
    pegas_lite_models.append({
        "id": slugify("pegas-lite-" + row[0]),
        "label": row[0].strip(),
        "capacity_persons": parse_num(row[1]),
        "Q_m3sut": parse_num(row[2]),
        "salvo_discharge_l": parse_num(row[3]),
        "weight_kg": parse_num(row[4]),
        "dimensions_cm": parse_dims_dxshxv(row[5]),
        "dimensions_raw": row[5],
        "price_rub_2023": parse_price(row[7]),
    })

# === pegas_s_65 ===
pegas_s_models = []
for row in sheets['PEGAS S 65%'][2:7]:
    if not row or not row[0]:
        continue
    pegas_s_models.append({
        "id": slugify("pegas-s-" + row[0]),
        "label": row[0].strip(),
        "capacity_persons": parse_num(row[1]),
        "Q_m3sut": parse_num(row[2]),
        "salvo_discharge_l": parse_num(row[3]),
        "weight_kg": parse_num(row[4]),
        "dimensions_cm": parse_dims_dxshxv(row[5]),
        "dimensions_raw": row[5],
        "price_rub_2023": parse_price(row[6]),
    })
for row in sheets['PEGAS S 65%'][8:12]:
    if not row or not row[0]:
        continue
    pegas_s_models.append({
        "id": slugify("pegas-s-" + row[0]),
        "label": row[0].strip(),
        "capacity_persons": parse_num(row[1]),
        "Q_m3sut": parse_num(row[2]),
        "salvo_discharge_l": parse_num(row[3]),
        "weight_kg": parse_num(row[4]),
        "dimensions_cm": parse_dims_dxshxv(row[5]),
        "dimensions_raw": row[5],
        "price_rub_2023": parse_price(row[6]),
    })

pegas_s_extensions = []
for row in sheets['PEGAS S 65%'][14:16]:
    if len(row) >= 2 and row[0]:
        pegas_s_extensions.append({
            "id": slugify("pegas-s-extension-" + row[0]),
            "label": "Удлинительная горловина " + row[0] + " мм",
            "size_mm_raw": row[0],
            "price_rub_2023": parse_price(row[1]),
        })

# === pegas_pro ===
pegas_pro_models = []
for row in sheets['Пром'][3:8]:
    if not row or not row[0]:
        continue
    pegas_pro_models.append({
        "id": slugify("pegas-prom-" + row[0] + "-gravity"),
        "label": row[0].strip(),
        "discharge_mode": "gravity",
        "capacity_persons": parse_num(row[1]),
        "Q_m3sut": parse_num(row[2]),
        "salvo_discharge_l": parse_num(row[3]),
        "weight_kg": parse_num(row[4]),
        "dimensions_cm": parse_dims_dxshxv(row[5]),
        "dimensions_raw": row[5],
        "price_rub_2023": parse_price(row[6]),
    })
for row in sheets['Пром'][9:14]:
    if not row or not row[0]:
        continue
    pegas_pro_models.append({
        "id": slugify("pegas-prom-" + row[0] + "-pressure"),
        "label": row[0].strip(),
        "discharge_mode": "pressure",
        "capacity_persons": parse_num(row[1]),
        "Q_m3sut": parse_num(row[2]),
        "salvo_discharge_l": parse_num(row[3]),
        "weight_kg": parse_num(row[4]),
        "dimensions_cm": parse_dims_dxshxv(row[5]),
        "dimensions_raw": row[5],
        "price_rub_2023": parse_price(row[6]),
    })
for row in sheets['Пром'][17:21]:
    if not row or not row[0]:
        continue
    persons_raw = row[1]
    persons_max = None
    m = re.search(r'(\d+)', str(persons_raw))
    if m:
        persons_max = int(m.group(1))
    pegas_pro_models.append({
        "id": slugify("pegas-pro-" + row[0]),
        "label": row[0].strip(),
        "tier": "pro",
        "capacity_persons": persons_max,
        "capacity_persons_raw": persons_raw,
        "Q_m3sut": parse_num(row[2]),
        "salvo_discharge_l": parse_num(row[3]),
        "weight_kg": parse_num(row[4]),
        "dimensions_cm": parse_dims_dxshxv(row[5]),
        "dimensions_raw": row[5],
        "price_rub_2023": parse_price(row[6]),
        "_engineer_note": "PEGAS PRO — модульные ЛОС для коттеджных посёлков, гостиниц, пищпрома",
    })

# === pegas_caissons ===
pegas_caissons_models = []
for row in sheets['Кессоны'][1:7]:
    if not row or not row[0]:
        continue
    dims = parse_dh(row[1])
    pegas_caissons_models.append({
        "id": slugify("pegas-caisson-" + row[0]),
        "label": "Кессон " + row[0].strip(),
        "dimensions_cm": dims,
        "dimensions_raw": row[1],
        "D_mm": int(dims["D_cm"] * 10) if dims else None,
        "H_mm": int(dims["H_cm"] * 10) if dims else None,
        "price_rub_2023": parse_price(row[2]),
    })

pegas_caisson_addons = []
for row in sheets['Кессоны'][8:10]:
    if not row or not row[0]:
        continue
    pegas_caisson_addons.append({
        "id": slugify("pegas-caisson-mufta-" + row[0]),
        "label": row[0].strip(),
        "price_rub_2023": parse_price(row[1]),
    })

# === pegas_pogreba ===
pegas_pogreba_models = []
for row in sheets['Погреба'][1:4]:
    if not row or not row[0]:
        continue
    dims = parse_dh(row[1])
    pegas_pogreba_models.append({
        "id": slugify("pegas-pogreb-cyl-" + row[0]),
        "label": "Погреб (цилиндрический ПП) " + row[0].strip(),
        "shape": "cylindrical",
        "dimensions_cm": dims,
        "dimensions_raw": row[1],
        "D_mm": int(dims["D_cm"] * 10) if dims else None,
        "H_mm": int(dims["H_cm"] * 10) if dims else None,
        "neck_diameter_mm": parse_num(row[3]),
        "wall_thickness": row[4] if len(row) > 4 else None,
        "blocks": parse_num(row[5]),
        "price_rub_2023": parse_price(row[6]),
    })
for row in sheets['Погреба'][10:13]:
    if not row or not row[0]:
        continue
    dims = parse_dh(row[1])
    pegas_pogreba_models.append({
        "id": slugify("pegas-pogreb-sq-" + row[0]),
        "label": "Погреб (квадратный ПП) " + row[0].strip(),
        "shape": "rectangular",
        "dimensions_cm": dims,
        "dimensions_raw": row[1],
        "neck_dimensions_raw": row[3] if len(row) > 3 else None,
        "wall_thickness": row[4] if len(row) > 4 else None,
        "blocks": parse_num(row[5]),
        "price_rub_2023": parse_price(row[6]),
    })

# === pegas_kns ===
pegas_kns_models = []
for row in sheets['КНС'][2:14]:
    if not row or not row[0]:
        continue
    pegas_kns_models.append({
        "id": slugify("pegas-kns-" + row[0]),
        "label": row[0].strip(),
        "L_mm": parse_num(row[1]),
        "W_mm": parse_num(row[2]),
        "H_mm": parse_num(row[3]),
        "D_mm": parse_num(row[1]),
        "price_rub_2023_corpus_only": parse_price(row[4]),
        "_note": "Цена ТОЛЬКО за корпус. Обвязка (насосы, ШУ, трубы, фланцы) считается отдельно по ТЗ.",
    })

# === pegas_grease_traps ===
pegas_grease_models = []
for row in sheets['Жир'][2:12]:
    if not row or not row[0]:
        continue
    pegas_grease_models.append({
        "id": slugify("pegas-grease-undersink-" + row[0]),
        "label": row[0].strip(),
        "subtype": "under_sink",
        "Q_m3h": parse_num(row[1]),
        "peak_l": parse_num(row[2]),
        "dimensions_mm_raw": row[3],
        "price_rub_2023": parse_price(row[4]),
    })
for row in sheets['Жир'][16:20]:
    if not row or not row[0]:
        continue
    pegas_grease_models.append({
        "id": slugify("pegas-grease-r-pro-" + row[0]),
        "label": row[0].strip(),
        "subtype": "cylindrical_vertical_R_pro",
        "Q_m3h": parse_num(row[1]),
        "peak_l": parse_num(row[2]),
        "dimensions_mm_raw": row[3],
        "price_rub_2023": parse_price(row[4]),
    })
for row in sheets['Жир'][23:32]:
    if not row or not row[0]:
        continue
    pegas_grease_models.append({
        "id": slugify("pegas-grease-s-pro-" + row[0]),
        "label": row[0].strip(),
        "subtype": "rectangular_S_pro",
        "Q_m3h": parse_num(row[1]),
        "peak_l": parse_num(row[2]),
        "dimensions_mm_raw": row[3],
        "price_rub_2023": parse_price(row[4]),
    })
for row in sheets['Жир'][36:46]:
    if not row or not row[0]:
        continue
    pegas_grease_models.append({
        "id": slugify("pegas-grease-h-pro-" + row[0]),
        "label": row[0].strip(),
        "subtype": "cylindrical_horizontal_H_pro",
        "Q_m3h": parse_num(row[1]),
        "volume_l": parse_num(row[2]),
        "dimensions_mm_raw": row[3],
        "price_rub_2023": parse_price(row[4]),
    })

# === pegas_pools ===
pegas_pools_models = []
for row in sheets['Купели, чаши бассейна'][8:17]:
    if not row or not row[0]:
        continue
    rid = "pegas-kupel-round-" + str(row[0]) + "x" + str(row[1]) + "x" + str(row[2])
    pegas_pools_models.append({
        "id": slugify(rid),
        "label": "Купель круглая " + str(row[0]) + "x" + str(row[1]) + "x" + str(row[2]) + " м, V=" + str(row[3]) + " м³",
        "category": "kupel",
        "shape": "round",
        "L_m": parse_num(row[0]),
        "W_m": parse_num(row[1]),
        "depth_m": parse_num(row[2]),
        "V_m3": parse_num(row[3]),
        "price_rub_2023_no_uv": parse_price(row[4]),
        "price_rub_2023_with_uv": parse_price(row[5]) if len(row) > 5 else None,
    })
for row in sheets['Купели, чаши бассейна'][19:25]:
    if not row or not row[0]:
        continue
    rid = "pegas-kupel-square-" + str(row[0]) + "x" + str(row[1]) + "x" + str(row[2])
    pegas_pools_models.append({
        "id": slugify(rid),
        "label": "Купель квадратная " + str(row[0]) + "x" + str(row[1]) + "x" + str(row[2]) + " м, V=" + str(row[3]) + " м³",
        "category": "kupel",
        "shape": "square",
        "L_m": parse_num(row[0]),
        "W_m": parse_num(row[1]),
        "depth_m": parse_num(row[2]),
        "V_m3": parse_num(row[3]),
        "price_rub_2023_no_uv": parse_price(row[4]),
        "price_rub_2023_with_uv": parse_price(row[5]) if len(row) > 5 else None,
    })
for row in sheets['Купели, чаши бассейна'][28:36]:
    if not row or not row[0]:
        continue
    rid = "pegas-kupel-corner-r" + str(row[0]) + "d" + str(row[1])
    pegas_pools_models.append({
        "id": slugify(rid),
        "label": "Купель угловая R=" + str(row[0]) + " м, h=" + str(row[1]) + " м, V=" + str(row[2]) + " м³",
        "category": "kupel",
        "shape": "corner",
        "radius_m": parse_num(row[0]),
        "depth_m": parse_num(row[1]),
        "V_m3": parse_num(row[2]),
        "price_rub_2023_no_uv": parse_price(row[3]),
        "price_rub_2023_with_uv": parse_price(row[4]) if len(row) > 4 else None,
    })
for row in sheets['Купели, чаши бассейна'][41:54]:
    if not row or not row[0]:
        continue
    rid = "pegas-pool-square-" + str(row[0]) + "x" + str(row[1]) + "x" + str(row[2])
    pegas_pools_models.append({
        "id": slugify(rid),
        "label": "Бассейн квадратный " + str(row[0]) + "x" + str(row[1]) + "x" + str(row[2]) + " м, V=" + str(row[3]) + " м³",
        "category": "pool",
        "shape": "square",
        "L_m": parse_num(row[0]),
        "W_m": parse_num(row[1]),
        "depth_m": parse_num(row[2]),
        "V_m3": parse_num(row[3]),
        "price_rub_2023": parse_price(row[4]),
    })
for row in sheets['Купели, чаши бассейна'][56:60]:
    if not row or not row[0]:
        continue
    rid = "pegas-pool-round-" + str(row[0]) + "x" + str(row[1]) + "x" + str(row[2])
    pegas_pools_models.append({
        "id": slugify(rid),
        "label": "Бассейн круглый " + str(row[0]) + "x" + str(row[1]) + "x" + str(row[2]) + " м, V=" + str(row[3]) + " м³",
        "category": "pool",
        "shape": "round",
        "L_m": parse_num(row[0]),
        "W_m": parse_num(row[1]),
        "depth_m": parse_num(row[2]),
        "V_m3": parse_num(row[3]),
        "price_rub_2023": parse_price(row[4]),
    })
for row in sheets['Купели, чаши бассейна'][62:74]:
    if not row or not row[0]:
        continue
    rid = "pegas-pool-oval-" + str(row[0]) + "x" + str(row[1]) + "x" + str(row[2])
    pegas_pools_models.append({
        "id": slugify(rid),
        "label": "Бассейн овальный " + str(row[0]) + "x" + str(row[1]) + "x" + str(row[2]) + " м, V=" + str(row[3]) + " м³",
        "category": "pool",
        "shape": "oval",
        "L_m": parse_num(row[0]),
        "W_m": parse_num(row[1]),
        "depth_m": parse_num(row[2]),
        "V_m3": parse_num(row[3]),
        "price_rub_2023": parse_price(row[4]),
    })

# === pegas_tanks_accumulator ===
pegas_tanks = []
for row in sheets['Накопительные'][3:7]:
    if not row or not row[0]:
        continue
    pegas_tanks.append({
        "id": slugify("pegas-tank-vert-" + str(row[0]) + "m3"),
        "label": "Накопительная ёмкость вертикальная " + str(row[0]) + " м³",
        "orientation": "vertical",
        "V_m3": parse_num(row[0]),
        "D_mm": parse_num(row[1]),
        "H_mm": parse_num(row[2]),
        "neck_dimensions_raw": row[3],
        "price_rub_2023": parse_price(row[4]),
    })
for row in sheets['Накопительные'][10:14]:
    if not row or not row[0]:
        continue
    pegas_tanks.append({
        "id": slugify("pegas-tank-hor-" + str(row[0]) + "m3"),
        "label": "Накопительная ёмкость горизонтальная " + str(row[0]) + " м³",
        "orientation": "horizontal",
        "V_m3": parse_num(row[0]),
        "D_mm": parse_num(row[1]),
        "L_mm": parse_num(row[2]),
        "neck_dimensions_raw": row[3],
        "price_rub_2023": parse_price(row[4]),
    })
for row in sheets['Накопительные'][17:21]:
    if not row or not row[0]:
        continue
    pegas_tanks.append({
        "id": slugify("pegas-tank-pnd-" + str(row[0]) + "m3"),
        "label": "Накопительная ёмкость PND армированная " + str(row[0]) + " м³",
        "orientation": "vertical",
        "material": "ПНД армированная труба",
        "V_m3": parse_num(row[0]),
        "D_mm": parse_num(row[1]),
        "L_mm": parse_num(row[2]),
        "neck_dimensions_raw": row[3],
        "price_rub_2023": parse_price(row[4]),
    })

# === Build final ===
result = {
    "_version": "0.1",
    "_updated": "2026-05-08",
    "_source": "Цены ПЕГАС ИНЖИНИРИНГ.xlsx из массива КНС 2.zip",
    "_description": "Прайс-лист PEGAS Engineering: ЛОС бытовые/промышленные, септики, КНС-корпуса, накопители, жироуловители, кессоны, погреба, купели, бассейны.",
    "_engineer_note": "Главный конкурент Серво-Юг по бытовым ЛОС 3-200 чел. Цены 2023 года (поле price_rub_2023). Источник — официальный xlsx прайс-лист дилерам.",
    "_competitor": "PEGAS Engineering",
    "_brand": "PEGAS",
    "_corpus_material": "ПП (полипропилен чешский)",
    "_wall_thickness_typical": "8-10 мм",
    "lines": {
        "pegas_lite": {
            "label": "PEGAS Lite",
            "tier": "budget",
            "use_case": "ИЖС, малые ЛОС с компрессором",
            "_description": "Простая бюджетная серия 4-секционных СБО на 3-7 человек.",
            "models": pegas_lite_models,
        },
        "pegas_ekonom": {
            "label": "PEGAS Ekonom",
            "tier": "ultra_budget",
            "use_case": "Сезонная эксплуатация, дача, режим выходного дня",
            "_description": "Сверхбюджетная серия 3-секционных СБО на 3-5 человек, есть варианты 'пр' (принудительный сброс).",
            "models": pegas_ekonom_models,
        },
        "pegas_base": {
            "label": "СБО PEGAS",
            "tier": "base",
            "use_case": "Базовая линейка ЛОС 3-15 чел, варианты самотечный/принудительный/LOW",
            "_description": "Главная линейка станций биологической очистки PEGAS, 4 камеры, очистка до 98%. Серия LOW для сложных грунтов (плывун, высокий УГВ, торфяники).",
            "models": pegas_base_models,
            "extensions": pegas_base_extensions,
            "addons": pegas_base_addons,
        },
        "pegas_premium": {
            "label": "PEGAS PREMIUM",
            "tier": "premium",
            "use_case": "Водоохранная зона, сброс в водоёмы",
            "_description": "Премиум серия с двухступенчатой аэрацией (компрессор + насос + УФ-лампа). Pedrollo (Италия) + Hiblow (Япония). Корпус 10 мм. Только принудительный, вход 85 см.",
            "models": pegas_premium_models,
        },
        "pegas_s_65": {
            "label": "PEGAS S (65%)",
            "tier": "septic_anaerobic",
            "use_case": "Энергонезависимые септики-отстойники для песчаных/супесчаных грунтов с низким УГВ",
            "_description": "Анаэробные септики без компрессора/насоса. 4-секционные. Требуется отдельный расчёт фильтрующих сооружений.",
            "models": pegas_s_models,
            "extensions": pegas_s_extensions,
        },
        "pegas_pro": {
            "label": "PEGAS Промышленные / PEGAS PRO",
            "tier": "industrial",
            "use_case": "Адм.здания, гостиницы, склады, рестораны, коттеджные посёлки, пищпром",
            "_description": "СГБО PEGAS 20-50 чел (повышенная производительность) + PEGAS PRO 75-200 (модульные ЛОС с УФ).",
            "models": pegas_pro_models,
        },
        "pegas_kns": {
            "label": "PEGAS КНС (корпуса)",
            "tier": "kns_corpus",
            "use_case": "Корпуса КНС/НС для бытовых стоков",
            "_description": "Цилиндрические корпуса ПП Ø1000-1900 мм, H=3000-4000 мм. Цена ТОЛЬКО за корпус — обвязка (насосы, ШУ, трубы, фланцы) считается отдельно по ТЗ.",
            "_engineer_note": "Прямой конкурент Серво-Юг и Plastek-Group в сегменте бытовых КНС. Корпус 8 мм ПП литой бесшовный, до 9 м высоты, до 3 м диаметра.",
            "models": pegas_kns_models,
        },
        "pegas_grease_traps": {
            "label": "PEGAS Жироуловители",
            "tier": "grease_trap",
            "use_case": "Кафе, рестораны, столовые, рыбозаводы",
            "_description": "4 подгруппы: под мойку (Pegas 25-175), Pegas R pro (цилиндрические вертикальные), Pegas S pro (прямоугольные напольные), Pegas H pro (цилиндрические горизонтальные подземные).",
            "models": pegas_grease_models,
        },
        "pegas_tanks_accumulator": {
            "label": "PEGAS Накопительные ёмкости",
            "tier": "tank_accumulator",
            "use_case": "Сбор бытовых/технических стоков, выгребные ямы",
            "_description": "ПП ёмкости 3-30 м³. Вертикальные, горизонтальные и из армированной ПНД-трубы (для крупных).",
            "models": pegas_tanks,
        },
        "pegas_caissons": {
            "label": "PEGAS Кессоны",
            "tier": "caisson",
            "use_case": "Скважины, насосное оборудование",
            "_description": "Кессоны для скважин — корпус ПП 8 мм цилиндрический, литой, бесшовный.",
            "models": pegas_caissons_models,
            "addons": pegas_caisson_addons,
        },
        "pegas_pogreba": {
            "label": "PEGAS Погреба",
            "tier": "cellar",
            "use_case": "Хранение продуктов",
            "_description": "Цилиндрические (8-10 мм) и квадратные (80 мм) погреба ПП. В комплекте лампа, лестница, полки, вытяжка.",
            "models": pegas_pogreba_models,
        },
        "pegas_pools": {
            "label": "PEGAS Купели и бассейны",
            "tier": "pools",
            "use_case": "Купели и чаши бассейнов",
            "_description": "ПП купели (круглые/квадратные/угловые, варианты с УФ и без) и бассейны (квадратные/круглые/овальные, чешский ПП с УФ).",
            "_note": "Не профильный продукт для kns-calculator, оставлено для полноты прайс-листа.",
            "models": pegas_pools_models,
        },
    }
}

with open(OUT_PATH, 'w', encoding='utf-8') as f:
    json.dump(result, f, ensure_ascii=False, indent=2)

print("Saved to " + OUT_PATH)
print()
total = 0
for k, v in result["lines"].items():
    n = len(v.get("models", []))
    extras = []
    if "extensions" in v:
        extras.append("+" + str(len(v["extensions"])) + " ext")
    if "addons" in v:
        extras.append("+" + str(len(v["addons"])) + " addon")
    extra_str = " (" + ", ".join(extras) + ")" if extras else ""
    total += n
    print("  " + k + ": " + str(n) + " models" + extra_str)
print()
print("Total models: " + str(total))
