"""
Extract project etalons from mail dataset (extracted_text.jsonl).
Output: 02_dataset/etalons/from_mail/etalons_extracted_2026-05-10.json
"""
import json
import re
import sys
from pathlib import Path

ROOT = Path("C:/Users/User/Desktop/kns-calculator-repo")
SRC = ROOT / "02_dataset/_inbox/yadisk_kns/extracted_text.jsonl"
PUBLIC = ROOT / "02_dataset/etalons/public/etalons_public_2026-05-09.json"
OUT_DIR = ROOT / "02_dataset/etalons/from_mail"
OUT = OUT_DIR / "etalons_extracted_2026-05-10.json"
NOPUMP = OUT_DIR / "files_no_pump_data_2026-05-10.json"

OUT_DIR.mkdir(parents=True, exist_ok=True)

# ---------- spam filters ----------
SPAM_TOKENS = [
    "flexbe", "target.my.com", "mcd.com", "vk.com/away", "ozon.ru", "wildberries",
    "ipk-rbs", "ecargentum", "mail.ru notif", "unsubscribe", "bot.flow", "amocrm",
    "joom.com", "aliexpress", "promo.kassa", "Сбермаркет", "СберМаркет",
    "купон на скидку", "распродажа", "вебинар", "марафон", "бесплатный курс",
]
SPAM_NAMES = ["news", "promo", "newsletter", "rassyl"]
# Catalogs and reference materials — not real project deals
CATALOG_TOKENS = [
    "каталог", "catalog", "прайс", "price", "референс", "reference",
    "коммерческое предложение", "коммпредл", "ятаган",
]

PUMP_KEYWORDS = ["насос", "pump", "м³/ч", "м3/ч", "м3 / ч", "Q=", "Q =", "H=", "H ="]
INDUSTRY_TERMS = ["КНС", "ВНС", "ЛОС", "ВЗиС", "пожарн", "канализ", "водопровод", "очистн", "ливнев"]


def is_spam(rec: dict) -> bool:
    name = (rec.get("name") or "").lower()
    text = rec.get("text") or ""
    if not text:
        return True
    if any(s in name for s in SPAM_NAMES):
        return True
    sample = text[:5000].lower()
    if any(s.lower() in sample for s in SPAM_TOKENS):
        return True
    return False


def is_catalog(rec: dict) -> bool:
    name = (rec.get("name") or "").lower()
    if any(t in name for t in CATALOG_TOKENS):
        return True
    return False


def has_engineering(text: str) -> bool:
    if not text:
        return False
    sample = text[:20000]
    has_pump = any(k.lower() in sample.lower() for k in PUMP_KEYWORDS)
    has_industry = any(k.lower() in sample.lower() for k in INDUSTRY_TERMS)
    return has_pump or has_industry


# ---------- field extractors ----------
RE_CODE = re.compile(
    r"\b(\d{1,5}[-/](?:\d{1,4}[-/])?(?:[А-ЯA-Z\d]{1,8}[-./]?){1,4}(?:[А-ЯA-Z\d]{1,5})?)\b"
)
RE_CODE_STRICT = re.compile(
    r"\b(\d{2,5}[-/]\d{1,4}(?:[-/]\d{1,4})?[-/](?:НВК|НК|РД|ИОС|ТХ|ВК|К1|К2|К3|К4|КЖ|АР|ПЗ|НВВ|НВ|ТКР|ОЛ|ОЛ\d|АТМ|АК|АТХ|АИБ|ВН|ВО|ИОС\d?[\.\d]*|НВК\d?))(?:[-/]?[А-ЯA-Z\d\.]{0,8})?\b",
    re.IGNORECASE,
)
RE_CODE_FILE = re.compile(r"^([\w\d\-\./]{4,40}?-(?:НВК|НК|РД|ИОС|ТХ|ВК|К1|К2|ОЛ|АТМ|НВВ))", re.IGNORECASE)

RE_Q = re.compile(
    r"Q\s*[=≈:]?\s*([\d]+[.,]?\d*)\s*(м(?:\^?3|³)?\s*/\s*(?:ч|час|h)|m3/h|л\s*/\s*с|l/s)",
    re.IGNORECASE,
)
# Match "Q=88.6 м³/ч" OR plain "352 м3/ч" OR "15 л/с"
RE_Q_LOOSE = re.compile(
    r"(?:Q[\s=≈:]*)?([\d]+[.,]?\d*)\s*(м(?:\^?3|³)?\s*/\s*[чh]|л\s*/\s*с)",
    re.IGNORECASE,
)
# H near Q: matches "H=35 м", "Н=35 м", "35 м.в.ст.", "35 м.в.с.", "35 м в.ст."
RE_H = re.compile(
    r"(?:^|[\s,;.()])(?:[HНн]\s*[=≈:]?\s*)?([\d]+[.,]?\d*)\s*(?:м\.?\s*в\.?\s*с(?:т)?|м(?![/³^\dа-я]))",
    re.IGNORECASE,
)
# Strict: only when explicit Н=
RE_H_STRICT = re.compile(
    r"(?:^|[\s,;.])[HНн]\s*[=≈:]\s*([\d]+[.,]?\d*)\s*м(?![/³^\dа-я])",
    re.IGNORECASE,
)
RE_P = re.compile(r"(?:N|P|мощн[а-я]*)\s*[=≈:]?\s*([\d]+[.,]?\d*)\s*кВт", re.IGNORECASE)
RE_DIAM = re.compile(r"(?:Ø|d\s*[=:]?\s*|диаметр[а-я]*\s*[:=]?\s*)\s*(\d{3,4})", re.IGNORECASE)
RE_HEIGHT = re.compile(r"(?:высот[а-я]*|H\s*корп[а-я]*)\s*[:=]?\s*(\d{3,5})\s*мм", re.IGNORECASE)
RE_VFIRE = re.compile(r"(?:V\s*=?\s*|объ[её]м\s*=?\s*)(\d{2,4})\s*м(?:\^?3|³)", re.IGNORECASE)
RE_YEAR = re.compile(r"(?:^|[^\d])(20[12]\d)(?:[^\d]|$)")

CITY_PATTERNS = [
    "Краснодар", "Сочи", "Симферополь", "Ялта", "Севастополь", "Евпатория",
    "Москва", "Санкт-Петербург", "Екатеринбург", "Новосибирск", "Казань",
    "Ростов", "Воронеж", "Волгоград", "Ставрополь", "Майкоп", "Анапа",
    "Геленджик", "Новороссийск", "Туапсе", "Армавир", "Тихорецк", "Темрюк",
    "Тимашевск", "Лабинск", "Динская", "Динской", "Каневская", "Кореновск",
    "Тбилисская", "Гулькевичи", "Усть-Лабинск", "Пятигорск", "Минеральные Воды",
    "Кисловодск", "Нальчик", "Грозный", "Махачкала", "Владикавказ", "Магас",
    "Феодосия", "Керчь", "Алушта", "Судак", "Бахчисарай", "Джанкой",
    "Мариуполь", "Донецк", "Луганск", "Бердянск", "Мелитополь", "Волноваха",
    "Херсон", "Запорожье", "Геническ", "Алчевск", "Скадовск",
    "Алматы", "Нур-Султан", "Астана", "Шымкент", "Атырау", "Актау", "Уральск",
    "Мысхако", "Темиртау", "Караганда", "Тбилиси", "Минск", "Ереван",
]

OBJECT_TYPE_PATTERNS = [
    ("ливнев", "ливневая КНС"),
    ("кнс", "КНС"),
    ("внс", "ВНС"),
    ("взис", "ВЗиС"),
    ("очистн", "ЛОС"),
    ("лос", "ЛОС"),
    ("пожарн", "пожарная насосная"),
    ("канализац", "канализация"),
    ("водопровод", "водопровод"),
]

PUMP_BRANDS = [
    "ANTARUS", "Антарус", "ANTARUS-2", "ANTARUS 2",
    "Grundfos", "GRUNDFOS", "Грундфос",
    "Wilo", "WILO", "Вило",
    "KSB", "Sewatec",
    "Pedrollo", "Педролло",
    "CNP", "ЦНП",
    "KAIQUAN", "Кайцюань",
    "LEO", "Лео",
    "Fancy", "Фэнси",
    "ГНОМ", "Гном",
    "Иртыш", "ЦМФ", "ЦМК", "ЦМ", "СД", "СМ",
    "СМЗ",
    "ARTWIND",
    "JETEX", "Jetex",
    "Vandjord",
    "HELYX",
    "Блорэй",
    "VXm", "СНп", "СНм", "ВТм", "СН",
    "MAS DAF",
    "ИСТРАТЕХ", "Истратех",
    "Шторм Ф",
    "ГИС",
    "ФГПУ",
    "ЦНС",
]


def first_or_none(lst):
    return lst[0] if lst else None


def parse_float(s):
    if s is None:
        return None
    s = str(s).replace(",", ".").strip()
    try:
        return float(s)
    except ValueError:
        return None


DATE_RE = re.compile(r"^\d{1,2}[.\-/]\d{1,2}[.\-/]\d{2,4}$")
PHONE_RE = re.compile(r"^\d{2,4}[-./]\d{2,4}[-./]\d{2,4}$")


def is_bad_code(code: str) -> bool:
    if not code:
        return True
    if DATE_RE.match(code):
        return True
    if PHONE_RE.match(code) and not re.search(r"[А-ЯA-Z]", code):
        return True
    if len(code) < 4 or len(code) > 60:
        return True
    return False


def extract_code(name: str, text: str):
    """Try to detect project code from filename first, then from text."""
    # Try filename — must contain Russian project suffix
    base = re.sub(r"\.\w+$", "", name)
    base = re.sub(r"\s*\(\d+\)\s*$", "", base)
    m = re.search(
        r"([\w\d]+[-./][\w\d\-./]{2,40}?-(?:НВК|НК|РД|ИОС|ТХ|ВК|ОЛ|АТМ|НВВ|АИБ|ИГДИ))",
        base,
        re.IGNORECASE,
    )
    if m:
        code = m.group(1)
        code = re.sub(r"[\s_]+$", "", code)
        if not is_bad_code(code):
            return code
    # Try first 3000 chars of text
    sample = (text or "")[:5000]
    m = re.search(
        r"\b(\d{2,5}[-/]\d{1,4}(?:[-/]\d{1,4})?[-./](?:НВК|НК|РД|ИОС|ТХ|ВК|ОЛ|АТМ|НВВ|АИБ|ИГДИ)\d*)\b",
        sample,
        re.IGNORECASE,
    )
    if m:
        code = m.group(1)
        if not is_bad_code(code):
            return code
    # Try shifr label
    m = re.search(r"шифр[:\s№]*([\w\d\-./]{5,40})", sample, re.IGNORECASE)
    if m:
        code = m.group(1).strip().rstrip(".,;")
        if not is_bad_code(code):
            return code
    return None


def extract_city(text: str):
    sample = (text or "")[:5000]
    for c in CITY_PATTERNS:
        if re.search(r"\b" + re.escape(c), sample, re.IGNORECASE):
            return c
    return None


def extract_object_type(text: str, name: str):
    sample = ((name or "") + " " + (text or "")[:3000]).lower()
    found = []
    for k, v in OBJECT_TYPE_PATTERNS:
        if k in sample:
            if v not in found:
                found.append(v)
    if found:
        return "/".join(found[:3])
    return None


def extract_year(text: str, name: str):
    for src in [name or "", (text or "")[:5000]]:
        m = RE_YEAR.search(src)
        if m:
            y = int(m.group(1))
            if 2015 <= y <= 2026:
                return y
    return None


def extract_client(text: str):
    sample = (text or "")[:5000]
    # ООО/ЗАО/АО/ИП
    m = re.search(r'(?:Заказчик|заказчик)\s*[:\-–]?\s*([«"]?[А-ЯA-Z][^\n,;]{4,120})', sample)
    if m:
        return m.group(1).strip().rstrip(".,;").strip("«»\"' ")
    m = re.search(r'\b((?:ООО|ЗАО|ПАО|АО|ИП|ФГУП|МУП|ГУП)\s+[«"]?[^\n,;]{3,80}[»"]?)', sample)
    if m:
        return m.group(1).strip().rstrip(".,;")
    return None


PUMP_CONTEXT_KEYWORDS = re.compile(
    r"(насос|КНС|ВНС|ЛОС|пожарн|перекач|стоки|ливнев|канализ|подач|производит|расход|Q\s*=)",
    re.IGNORECASE,
)


def extract_pump(text: str):
    """Find pump records. Q must have hour-based units. Pump context required."""
    sample = text or ""
    pumps = []
    seen = set()
    for m in RE_Q_LOOSE.finditer(sample):
        unit = m.group(2).lower()
        Q = parse_float(m.group(1))
        if Q is None:
            continue
        # Convert л/с to m³/h
        if "л" in unit and "с" in unit:
            Q = Q * 3.6
        # Filter implausible
        if Q > 50000 or Q < 0.05:
            continue
        # Look for pump context within +/- 200 chars
        ctx_full = sample[max(0, m.start() - 200):m.end() + 200]
        if not PUMP_CONTEXT_KEYWORDS.search(ctx_full):
            continue
        # H — search next 100 chars (typical "Q=X H=Y" or "X м3/ч Y м.в.ст." pattern)
        ctx_after = sample[m.end():m.end() + 100]
        h_match = RE_H.search(ctx_after)
        if not h_match:
            # Try strict H= within full window
            h_match = RE_H_STRICT.search(ctx_full)
        H = parse_float(h_match.group(1)) if h_match else None
        if H is not None and (H > 500 or H < 0.3):
            H = None
        # Power
        p_match = RE_P.search(ctx_full)
        P = parse_float(p_match.group(1)) if p_match else None
        if P is not None and (P > 1000 or P < 0.05):
            P = None
        # Model from ctx
        model = None
        for brand in PUMP_BRANDS:
            mb = re.search(r"\b" + re.escape(brand) + r"[\s\-./\w]{0,40}", ctx_full, re.IGNORECASE)
            if mb:
                model = mb.group(0).strip().rstrip(".,;")
                if len(model) > 80:
                    model = model[:80]
                break
        # Dedupe (same Q,H,model)
        key = (round(Q, 1), round(H, 1) if H else None, model)
        if key in seen:
            continue
        seen.add(key)
        pumps.append({"Q_m3h": round(Q, 2), "H_m": H, "P_kW": P, "model": model})
    return pumps


def extract_los(text: str):
    sample = text or ""
    los = []
    for m in re.finditer(r"(?:ЛОС|очистн[а-я]*\s+сооружен[а-я]*)[\s\S]{0,400}", sample, re.IGNORECASE):
        ctx = m.group(0)[:400]
        # capacity in PE (чел) or m3/day
        pe = re.search(r"(\d{1,5})\s*(?:чел|пэ)", ctx, re.IGNORECASE)
        q = re.search(r"(\d{1,4}[.,]?\d*)\s*м(?:\^?3|³)\s*/\s*сут", ctx, re.IGNORECASE)
        model = None
        for brand in ["Топас", "BIO", "Юнилос", "ASTRA", "Тверь", "Биокси", "Тополь"]:
            mb = re.search(r"\b" + brand + r"[\s\-/\w]{0,30}", ctx, re.IGNORECASE)
            if mb:
                model = mb.group(0).strip()[:60]
                break
        if pe or q or model:
            los.append({
                "Q_pe": int(pe.group(1)) if pe else None,
                "Q_m3day": parse_float(q.group(1)) if q else None,
                "model": model,
            })
            if len(los) >= 3:
                break
    return los


def extract_fire_tanks(text: str):
    sample = (text or "")[:8000]
    m = re.search(r"пожарн[а-я]*\s+(?:резервуар[а-я]*|емкост[а-я]*|бак[а-я]*)[\s\S]{0,200}", sample, re.IGNORECASE)
    if not m:
        return None
    ctx = m.group(0)[:300]
    v = RE_VFIRE.search(ctx)
    cnt = re.search(r"(\d)\s*(?:шт|×|х)\s*\d", ctx)
    if v:
        return {
            "V_m3": parse_float(v.group(1)),
            "count": int(cnt.group(1)) if cnt else None,
        }
    return None


def extract_housing_dim(text: str):
    sample = (text or "")[:5000]
    d = RE_DIAM.search(sample)
    h = RE_HEIGHT.search(sample)
    if d or h:
        return {
            "diameter_mm": int(d.group(1)) if d else None,
            "height_mm": int(h.group(1)) if h else None,
        }
    return None


# ---------- main ----------
def main():
    public_codes = set()
    public_files = set()
    if PUBLIC.exists():
        with open(PUBLIC, encoding="utf-8") as f:
            pub = json.load(f)
        for e in pub:
            if e.get("code"):
                public_codes.add(e["code"].lower().strip())
            sf = e.get("source_file", "")
            for fname in re.split(r",|;", sf):
                fname = fname.strip()
                if fname:
                    public_files.add(fname.lower())

    print(f"[i] Loaded {len(public_codes)} existing codes, {len(public_files)} source files")

    extracted = []
    no_pump = []
    catalogs = []
    spam_count = 0
    catalog_count = 0
    total = 0
    no_engineering = 0

    with open(SRC, encoding="utf-8") as f:
        for line in f:
            total += 1
            try:
                rec = json.loads(line)
            except json.JSONDecodeError:
                continue
            if rec.get("error"):
                continue
            text = rec.get("text") or ""
            name = rec.get("name") or ""
            if is_spam(rec):
                spam_count += 1
                continue
            if is_catalog(rec):
                catalog_count += 1
                catalogs.append({"name": name, "size": rec.get("size")})
                continue
            if not has_engineering(text):
                no_engineering += 1
                continue

            code = extract_code(name, text)
            pumps = extract_pump(text)
            los = extract_los(text)
            fire_tanks = extract_fire_tanks(text)
            obj_type = extract_object_type(text, name)
            city = extract_city(text)
            year = extract_year(text, name)
            client = extract_client(text)
            housing = extract_housing_dim(text)

            # If no pump and no LOS — record into "no_pump" file
            if not pumps and not los and not fire_tanks:
                no_pump.append({
                    "name": name,
                    "code_guess": code,
                    "object_type": obj_type,
                    "city": city,
                    "size": rec.get("size"),
                    "reason": "no Q/H/LOS/fire_tank parsed",
                })
                continue

            # Duplicate check
            dup_of = None
            if code:
                if code.lower().strip() in public_codes:
                    dup_of = code
            if not dup_of and name.lower() in public_files:
                dup_of = name

            entry = {
                "code": code,
                "client": client,
                "object_type": obj_type,
                "city": city,
                "year": year,
                "source_file": name,
                "source_path": rec.get("path"),
            }
            if pumps:
                # Take main = highest Q, fire = second largest if differs
                pumps_sorted = sorted(pumps, key=lambda p: p.get("Q_m3h", 0), reverse=True)
                main = pumps_sorted[0]
                entry["vns_hozpit"] = {
                    "model": main.get("model"),
                    "Q_m3h": main.get("Q_m3h"),
                    "H_m": main.get("H_m"),
                    "P_kW": main.get("P_kW"),
                }
                if len(pumps_sorted) >= 2:
                    entry["additional_pumps"] = [
                        {
                            "model": p.get("model"),
                            "Q_m3h": p.get("Q_m3h"),
                            "H_m": p.get("H_m"),
                            "P_kW": p.get("P_kW"),
                        }
                        for p in pumps_sorted[1:5]
                    ]
            if los:
                entry["los"] = los
            if fire_tanks:
                entry["fire_tanks"] = fire_tanks
            if housing:
                entry["housing"] = housing
            if dup_of:
                entry["_duplicate_of"] = dup_of

            extracted.append(entry)

    # Dedupe by canonical (Q,H,code) — keep first
    canon_seen = set()
    unique = []
    for e in extracted:
        v = e.get("vns_hozpit", {})
        key = (
            (e.get("code") or "").lower().strip(),
            round(v.get("Q_m3h"), 1) if v.get("Q_m3h") else None,
            round(v.get("H_m"), 1) if v.get("H_m") else None,
            (e.get("source_file") or "").lower().replace(" (1)", "").replace(" (2)", "").strip(),
        )
        if key in canon_seen:
            continue
        canon_seen.add(key)
        unique.append(e)
    extracted = unique

    # Save outputs
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(extracted, f, ensure_ascii=False, indent=2)
    with open(NOPUMP, "w", encoding="utf-8") as f:
        json.dump(no_pump, f, ensure_ascii=False, indent=2)

    # Stats
    duplicates = sum(1 for e in extracted if e.get("_duplicate_of"))
    print(f"[stats] total_records={total}")
    print(f"[stats] spam_filtered={spam_count}")
    print(f"[stats] catalogs_filtered={catalog_count}")
    print(f"[stats] no_engineering={no_engineering}")
    print(f"[stats] no_pump_data={len(no_pump)}")
    print(f"[stats] extracted={len(extracted)} ({duplicates} duplicates)")
    print(f"[saved] {OUT}")
    print(f"[saved] {NOPUMP}")
    # Save catalogs list separately
    cat_path = OUT_DIR / "catalogs_filtered_2026-05-10.json"
    with open(cat_path, "w", encoding="utf-8") as f:
        json.dump(catalogs, f, ensure_ascii=False, indent=2)
    print(f"[saved] {cat_path}")


if __name__ == "__main__":
    main()
