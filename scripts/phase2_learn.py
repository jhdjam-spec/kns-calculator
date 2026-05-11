"""Phase 2 — learned_profile.json из import.log + letters_index.jsonl.

Берёт wanted-матчи из import.log (строки `[INFO] ✓ <date> [<folder>] <subject>`)
и привязывает к записям letters_index.jsonl по folder+date+subject.

Результат: 02_dataset/_inbox/mail_ru_imap/learned_profile.json
"""
from __future__ import annotations

import json
import re
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
INBOX = ROOT / "02_dataset" / "_inbox" / "mail_ru_imap"
LOG = INBOX / "import.log"
INDEX = INBOX / "letters_index.jsonl"
OUT = INBOX / "learned_profile.json"

# Регексп строки матча в логе:
# 02:10:39 [INFO] ✓ 2026-05-04 [INBOX] Заявка на КНС... | body=919 (wanted: ...)
MATCH_RE = re.compile(
    r"^\d{2}:\d{2}:\d{2}\s+\[INFO\]\s+✓\s+(\S+)\s+\[([^\]]+)\]\s+(.+?)\s+\|\s+body=\d+\s+\(wanted:\s+(.+?)\)\s*$"
)
# Шифры проектов: МЯ-12-345, ABC-12.34, 012022358, и т.д.
PROJECT_CODE_RE = re.compile(
    r"\b(?:[А-ЯA-Z]{2,5}[-.][\w-]+|\d{6,12}|[А-Я]{2,4}\d{2,4}[-./]\d+)\b",
    re.UNICODE,
)
# Маркеры темы — фразы, регулярно встречающиеся в wanted-письмах
SUBJECT_MARKERS = [
    "ТЗ", "КП", "запрос", "заявка", "тендер", "проект", "коммерческое",
    "поставка", "закупка", "опросный", "ОЛ", "оборудование",
    "очистные", "канализация", "водоснабжение", "водоотведение",
    "КНС", "ЛОС", "резервуар", "емкост", "ёмкост",
    "FW:", "Re:", "RE:", "FWD:",
]


def parse_log_matches() -> list[dict]:
    """Парсит import.log и возвращает список матчей."""
    if not LOG.exists():
        return []
    matches = []
    for raw in LOG.read_text(encoding="utf-8", errors="replace").splitlines():
        m = MATCH_RE.match(raw)
        if not m:
            continue
        date_str, folder, subject, wanted_files_str = m.groups()
        wanted_files = [s.strip() for s in wanted_files_str.split(",")]
        matches.append({
            "date": date_str,
            "folder": folder,
            "subject": subject.strip(),
            "wanted_files": wanted_files,
        })
    return matches


def load_index() -> list[dict]:
    """Загружает letters_index.jsonl."""
    if not INDEX.exists():
        return []
    out = []
    for raw in INDEX.read_text(encoding="utf-8", errors="replace").splitlines():
        raw = raw.strip()
        if not raw:
            continue
        try:
            out.append(json.loads(raw))
        except json.JSONDecodeError:
            pass
    return out


def attach_senders(matches: list[dict], idx: list[dict]) -> list[dict]:
    """Привязывает к каждому матчу from/to из index по folder+subject (date частично)."""
    # Index по (folder, normalized_subject_prefix)
    by_key: dict[tuple[str, str], dict] = {}
    for entry in idx:
        folder = entry.get("folder", "")
        subject = entry.get("subject", "")[:60]
        by_key[(folder, subject[:30])] = entry
    enriched = []
    for m in matches:
        folder = m["folder"]
        subject_prefix = m["subject"][:30]
        match_entry = by_key.get((folder, subject_prefix))
        if match_entry:
            m["from"] = match_entry.get("from", "")
            m["to"] = match_entry.get("to", "")
            m["full_subject"] = match_entry.get("subject", m["subject"])
        enriched.append(m)
    return enriched


def extract_email_domain(from_field: str) -> str:
    if not from_field:
        return ""
    m = re.search(r"<([^>]+)>", from_field)
    addr = m.group(1) if m else from_field
    if "@" in addr:
        return addr.split("@", 1)[1].lower().strip()
    return ""


def build_profile(matches: list[dict]) -> dict:
    senders_full = Counter()
    domains = Counter()
    project_codes = Counter()
    subject_words = Counter()
    by_year = Counter()
    by_year_month = Counter()
    folders = Counter()

    marker_counts = Counter()

    for m in matches:
        folders[m["folder"]] += 1

        from_field = m.get("from", "")
        if from_field:
            senders_full[from_field] += 1
            d = extract_email_domain(from_field)
            if d:
                domains[d] += 1

        # Год по дате (формат 2026-05-04)
        date = m["date"]
        if len(date) >= 7:
            by_year[date[:4]] += 1
            by_year_month[date[:7]] += 1

        # Проектные коды
        full_subj = m.get("full_subject") or m["subject"]
        for code in PROJECT_CODE_RE.findall(full_subj):
            if len(code) >= 5:  # фильтр шумовых коротких чисел
                project_codes[code] += 1

        # Маркеры
        for marker in SUBJECT_MARKERS:
            if marker.lower() in full_subj.lower():
                marker_counts[marker] += 1

        # Слова темы (длиннее 3)
        for word in re.findall(r"\b[А-Яа-яA-Za-z]{4,}\b", full_subj):
            subject_words[word.lower()] += 1

    trusted_senders = [d for d, c in domains.most_common() if c >= 2]
    return {
        "generated_at": "2026-05-10T02:30:00+03:00",
        "source_log": str(LOG),
        "source_index": str(INDEX),
        "matches_total": len(matches),
        "by_year": dict(by_year.most_common()),
        "by_year_month": dict(by_year_month.most_common(36)),
        "folders": dict(folders.most_common()),
        "top_senders": dict(senders_full.most_common(20)),
        "top_domains": dict(domains.most_common(30)),
        "trusted_senders": trusted_senders,
        "project_codes_seen": dict(project_codes.most_common(50)),
        "subject_markers": dict(marker_counts.most_common()),
        "top_subject_words": dict(subject_words.most_common(40)),
    }


def main() -> int:
    matches = parse_log_matches()
    idx = load_index()
    enriched = attach_senders(matches, idx)
    profile = build_profile(enriched)
    OUT.write_text(
        json.dumps(profile, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(f"✓ wrote {OUT}")
    print(f"  matches_total = {profile['matches_total']}")
    print(f"  trusted_senders = {len(profile['trusted_senders'])}")
    print(f"  project_codes = {len(profile['project_codes_seen'])}")
    print("  top_domains:")
    for d, c in list(profile["top_domains"].items())[:10]:
        print(f"    {d}: {c}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
