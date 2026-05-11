"""Regex-парсер инженерных параметров Q/H из писем + текстов файлов.

Источники:
1. 02_dataset/_inbox/mail_ru_imap/letters_index.jsonl (8711 писем, snippet 200-3000 chars)
2. 02_dataset/_inbox/yadisk_kns/extracted_text.jsonl (339 файлов, текст 4.3 МБ)

Выход:
- 02_dataset/_analysis/crm_extracted_params_2026-05-10.json
  Структурированный список лидов с заполненными {Q, H, type, city, contact, source}
"""
from __future__ import annotations
import json
import re
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LETTERS = ROOT / "02_dataset" / "_inbox" / "mail_ru_imap" / "letters_index.jsonl"
FILES_TXT = ROOT / "02_dataset" / "_inbox" / "yadisk_kns" / "extracted_text.jsonl"
OUT = ROOT / "02_dataset" / "_analysis" / "crm_extracted_params_2026-05-10.json"

# === Regex'ы для извлечения ===

# Q (расход): "Q=12 м3/ч", "расход 5 л/с", "производительность до 50 м³/ч",
# "12,5 м3/час", "10 л/с"
QH_RE = re.compile(
    r"""
    (?P<param>Q|расход|производительност\w*|подач\w*|H|напор)
    \s*[=:~≈\-]?\s*(?:до\s+|от\s+|не\s+менее\s+)?
    (?P<value>\d+(?:[.,]\d+)?)
    \s*(?P<unit>м3/ч|м³/ч|м3/час|м³/час|м3·ч|л/с|л/мин|м\b|метр\w*|т/ч)
    """,
    re.IGNORECASE | re.VERBOSE | re.UNICODE,
)

# Объём ёмкости: "емкость 15 м3", "резервуар V=110 м³", "100 м3"
VOL_RE = re.compile(
    r"""
    (?:
      (?:V\s*[=≈~]?\s*|объём\s*[=:~]?\s*|объем\s*[=:~]?\s*|вместимост\w*\s*|емкость\s+)
      (?P<value>\d+(?:[.,]\d+)?)
      \s*(?P<unit>м3|м³|кубо?\w*)
    )|(?:
      (?P<value2>\d+(?:[.,]\d+)?)
      \s*(?P<unit2>м3|м³)\s*(?:ёмкост|емкост|резервуар)
    )
    """,
    re.IGNORECASE | re.VERBOSE | re.UNICODE,
)

# Диаметры: "ø2000", "D=1200", "Ду 200", "DN 50", "ф2,4м"
DN_RE = re.compile(
    r"""
    (?:
      (?:Ду|DN|D|ø|∅|ф)\s*[=:~]?\s*(?P<value>\d{1,4}(?:[.,]\d+)?)
      \s*(?P<unit>мм|м|сот\w*)?
    )
    """,
    re.IGNORECASE | re.VERBOSE | re.UNICODE,
)

# Города (популярные в РФ юг + Крым + крупные)
CITIES = [
    "Краснодар", "Ростов", "Сочи", "Анапа", "Геленджик", "Туапсе", "Темрюк",
    "Новороссийск", "Армавир", "Ставрополь", "Пятигорск", "Махачкала",
    "Симферополь", "Ялта", "Севастополь", "Керчь", "Феодосия", "Евпатория",
    "Белогорск", "Бахчисарай", "Алушта", "Судак",
    "Москва", "Санкт-Петербург", "Питер", "Воронеж", "Волгоград", "Саратов",
    "Самара", "Казань", "Уфа", "Екатеринбург", "Челябинск", "Новосибирск",
    "Луганск", "Донецк", "Мариуполь", "Бердянск",
    "Балаково", "Батайск", "Новочеркасск",
]
CITY_RE = re.compile(r"\b(" + "|".join(CITIES) + r")\b", re.IGNORECASE)

# Тип объекта (по ключевым словам)
TYPE_KEYS = {
    "КНС": ["КНС", "канализационная насосная", "насосная станция канализационн"],
    "ЛОС": ["ЛОС", "локальные очистные", "очистные сооружения", "очистные хоз"],
    "ливневые_очистные": ["ливневые очистные", "ливневая канализация", "очистные ливневые", "сепаратор нефтепродуктов"],
    "септик": ["септик"],
    "ёмкость_накопит": ["накопительная емкость", "накопительный резервуар", "емкость накопит"],
    "ёмкость_хим": ["химстойкая", "хим стойкая", "ХИМ"],
    "ёмкость_пожарная": ["пожарный резервуар", "противопожарный резервуар"],
    "повышение_давления": ["повышение давления", "повысительная", "СПД", "ВНС"],
    "пескоуловитель": ["пескоуловитель"],
    "жироуловитель": ["жироуловитель", "ЛОС-Ж"],
    "колодец": ["колодец", "колодцы"],
}

CONTACT_RE = re.compile(r"<([^@>]+@[^>]+)>")


def detect_types(text: str) -> list[str]:
    t = text.lower()
    found = []
    for typ, keys in TYPE_KEYS.items():
        for k in keys:
            if k.lower() in t:
                found.append(typ)
                break
    return found


def parse_qh(text: str) -> dict:
    """Возвращает {Q_m3h, Q_ls, H_m, V_m3, DN_mm} из текста, если найдено."""
    out = {}
    for m in QH_RE.finditer(text[:8000]):
        param = m.group("param").lower()
        try:
            v = float(m.group("value").replace(",", "."))
        except ValueError:
            continue
        unit = m.group("unit").lower()
        if param.startswith(("q", "расход", "производит", "подач")):
            if "м3" in unit or "м³" in unit:
                if "м3/час" in unit or "м3/ч" in unit or "м³/ч" in unit:
                    if "Q_m3h" not in out:
                        out["Q_m3h"] = v
            elif "л/с" in unit:
                if "Q_ls" not in out:
                    out["Q_ls"] = v
            elif "л/мин" in unit:
                if "Q_lmin" not in out:
                    out["Q_lmin"] = v
            elif "т/ч" in unit:
                if "Q_th" not in out:
                    out["Q_th"] = v
        elif param.startswith(("h", "напор")):
            if unit == "м" or "метр" in unit:
                if "H_m" not in out:
                    out["H_m"] = v
    # Объём
    for m in VOL_RE.finditer(text[:8000]):
        v = m.group("value") or m.group("value2")
        if v:
            try:
                vv = float(v.replace(",", "."))
                if "V_m3" not in out and 0.5 <= vv <= 5000:
                    out["V_m3"] = vv
            except ValueError:
                pass
    # DN
    for m in DN_RE.finditer(text[:8000]):
        try:
            v = int(float(m.group("value").replace(",", ".")))
            if 10 <= v <= 5000 and "DN_mm" not in out:
                out["DN_mm"] = v
        except (ValueError, TypeError):
            pass
    return out


def detect_city(text: str) -> str | None:
    m = CITY_RE.search(text)
    return m.group(1) if m else None


def main() -> int:
    OUT.parent.mkdir(parents=True, exist_ok=True)
    leads = []

    # === 1. Письма ===
    if LETTERS.exists():
        n_total = 0
        for line in LETTERS.read_text(encoding="utf-8", errors="replace").splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                e = json.loads(line)
            except json.JSONDecodeError:
                continue
            n_total += 1
            full = " ".join(filter(None, [e.get("subject", ""), e.get("snippet", "")]))
            params = parse_qh(full)
            if not params:
                continue
            types = detect_types(full)
            city = detect_city(full)
            from_addr = ""
            mfrom = CONTACT_RE.search(e.get("from", ""))
            if mfrom:
                from_addr = mfrom.group(1)
            leads.append({
                "source": "mail",
                "id": e.get("slug") or f"{e.get('folder','')}-{e.get('uid','')}",
                "date": e.get("date", ""),
                "from": e.get("from", "")[:100],
                "from_email": from_addr,
                "subject": e.get("subject", "")[:200],
                "city": city,
                "types": types,
                "params": params,
                "snippet": e.get("snippet", "")[:500],
            })
        print(f"Mail: scanned {n_total}, leads with params: {sum(1 for l in leads if l['source']=='mail')}")

    # === 2. Файлы Я.Диска ===
    if FILES_TXT.exists():
        n_total = 0
        for line in FILES_TXT.read_text(encoding="utf-8", errors="replace").splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                e = json.loads(line)
            except json.JSONDecodeError:
                continue
            n_total += 1
            text = e.get("text") or ""
            if not text:
                continue
            params = parse_qh(text)
            if not params:
                continue
            types = detect_types(text[:5000])
            city = detect_city(text[:5000])
            leads.append({
                "source": "yadisk",
                "id": e.get("path"),
                "name": e.get("name", ""),
                "ext": e.get("ext", ""),
                "size": e.get("size", 0),
                "city": city,
                "types": types,
                "params": params,
                "text_excerpt": text[:500].replace("\n", " "),
            })
        print(f"Yadisk: scanned {n_total}, leads with params total: {len(leads)}")

    # === Сводка ===
    by_source = Counter(l["source"] for l in leads)
    by_type = Counter()
    for l in leads:
        for t in l["types"]:
            by_type[t] += 1
    by_city = Counter(l["city"] for l in leads if l.get("city"))
    with_q = sum(1 for l in leads if "Q_m3h" in l["params"] or "Q_ls" in l["params"])
    with_h = sum(1 for l in leads if "H_m" in l["params"])
    with_v = sum(1 for l in leads if "V_m3" in l["params"])
    with_qh = sum(1 for l in leads if (("Q_m3h" in l["params"]) or ("Q_ls" in l["params"])) and "H_m" in l["params"])

    summary = {
        "generated_at": "2026-05-10T13:50:00+03:00",
        "total_leads": len(leads),
        "by_source": dict(by_source),
        "by_type": dict(by_type.most_common()),
        "by_city_top20": dict(by_city.most_common(20)),
        "with_Q": with_q,
        "with_H": with_h,
        "with_V": with_v,
        "with_Q_and_H_both": with_qh,
        "leads": leads,
    }
    OUT.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\n✓ written {OUT}")
    print(f"  total_leads = {len(leads)}")
    print(f"  by_source = {dict(by_source)}")
    print(f"  by_type top-10:")
    for t, c in by_type.most_common(10):
        print(f"    {c:4d}  {t}")
    print(f"  cities top-10:")
    for c, n in by_city.most_common(10):
        print(f"    {n:4d}  {c}")
    print(f"  with_Q={with_q}  with_H={with_h}  with_V={with_v}  with_Q+H={with_qh}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
