"""
email_dump.py — IMAP-выгрузка писем mail.ru с фильтрацией по теме КНС/ВНС/НВК/ЛОС/насосы.

Использование:
    python scripts/email_dump.py                       # весь архив, профильный фильтр
    python scripts/email_dump.py --since 2025-11-09    # последние 6 месяцев
    python scripts/email_dump.py --no-filter           # все письма без фильтра
    python scripts/email_dump.py --dry-run             # только посчитать совпадения
    python scripts/email_dump.py --limit 100           # ограничить число писем

Учётка:
    ~/.claude/.secrets/mail_ru.user   — email
    ~/.claude/.secrets/mail_ru.token  — пароль приложения (не основной!)

Куда складывает:
    02_dataset/_inbox/{YYYY-MM-DD}_email_dump/{from_short}_{subject_short}/
        ├── email.txt                — заголовки + тело письма
        ├── meta.json                — машиночитаемые метаданные
        └── <attachments>            — вложения с оригинальными именами
"""

from __future__ import annotations

import argparse
import email
import imaplib
import json
import os
import re
import ssl
import sys
import unicodedata
from datetime import datetime
from email.header import decode_header, make_header
from email.message import Message
from pathlib import Path

IMAP_HOST = "imap.mail.ru"
IMAP_PORT = 993
SECRETS_DIR = Path(os.path.expanduser("~/.claude/.secrets"))
USER_FILE = SECRETS_DIR / "mail_ru.user"
TOKEN_FILE = SECRETS_DIR / "mail_ru.token"

REPO_ROOT = Path(__file__).resolve().parent.parent
INBOX_ROOT = REPO_ROOT / "02_dataset" / "_inbox"

# Расширенный профильный набор по согласованию 2026-05-09
SUBJECT_KEYWORDS = [
    # Аббревиатуры подсистем
    "КНС", "ВНС", "НС", "НВК", "НК", "ЛОС", "КОС",
    # Документы
    "КП", "ОЛ", "ТЗ", "ТКП", "опросн", "коммерческ", "техзадан", "запрос",
    "счёт", "счет", "оплат", "конъюнкт", "коньюктур", "спецификац", "ВОР",
    # Оборудование
    "насос", "резервуар", "ёмкост", "емкост", "арматур", "корпус",
    # Системы
    "водоснабжен", "канализац", "ливн", "ливнев", "пожаротуш", "очистн",
    "стоки", "сточ", "пульт", "автоматик", "электрик", "щит",
    # Производители
    "ANTARUS", "Pedrollo", "Grundfos", "Wilo", "KSB", "CNP", "ANTAРUS",
    "Полипластик", "BIO", "Топас",
]

ATTACHMENT_EXT_ALLOWED = {
    ".pdf", ".docx", ".doc", ".xlsx", ".xls", ".dwg", ".dxf", ".zip",
    ".rar", ".7z", ".jpg", ".jpeg", ".png", ".tif", ".tiff", ".gsfx",
    ".csv", ".txt",
}


def _decode_mime(value: str | None) -> str:
    if not value:
        return ""
    try:
        return str(make_header(decode_header(value)))
    except Exception:
        return value


def _safe_name(value: str, maxlen: int = 80) -> str:
    """Превращает произвольную строку в безопасное имя папки/файла."""
    value = unicodedata.normalize("NFKC", value or "")
    value = re.sub(r"[^\w\s.\-+]", "_", value, flags=re.UNICODE)
    value = re.sub(r"\s+", "_", value).strip("._-")
    return value[:maxlen] or "no_name"


def _matches_filter(subject: str, body_preview: str) -> bool:
    target = (subject + " " + body_preview).lower()
    return any(kw.lower() in target for kw in SUBJECT_KEYWORDS)


def _extract_body(msg: Message) -> tuple[str, str]:
    """Возвращает (text_body, html_preview_first_500_chars)."""
    text_body = ""
    html_body = ""
    if msg.is_multipart():
        for part in msg.walk():
            ctype = part.get_content_type()
            disp = str(part.get("Content-Disposition") or "")
            if "attachment" in disp:
                continue
            try:
                payload = part.get_payload(decode=True) or b""
                charset = part.get_content_charset() or "utf-8"
                decoded = payload.decode(charset, errors="replace")
            except Exception:
                continue
            if ctype == "text/plain" and not text_body:
                text_body = decoded
            elif ctype == "text/html" and not html_body:
                html_body = decoded
    else:
        try:
            payload = msg.get_payload(decode=True) or b""
            charset = msg.get_content_charset() or "utf-8"
            text_body = payload.decode(charset, errors="replace")
        except Exception:
            text_body = ""
    if not text_body and html_body:
        text_body = re.sub(r"<[^>]+>", " ", html_body)
        text_body = re.sub(r"\s+", " ", text_body).strip()
    return text_body, html_body[:500]


def _save_attachments(msg: Message, target_dir: Path) -> list[dict]:
    saved: list[dict] = []
    if not msg.is_multipart():
        return saved
    for part in msg.walk():
        disp = str(part.get("Content-Disposition") or "")
        if "attachment" not in disp.lower() and not part.get_filename():
            continue
        filename = _decode_mime(part.get_filename() or "") or "attachment.bin"
        ext = Path(filename).suffix.lower()
        if ext and ATTACHMENT_EXT_ALLOWED and ext not in ATTACHMENT_EXT_ALLOWED:
            continue
        payload = part.get_payload(decode=True)
        if not payload:
            continue
        safe = _safe_name(filename, maxlen=120) or "attachment.bin"
        if not Path(safe).suffix:
            safe += ext or ".bin"
        out = target_dir / safe
        i = 1
        while out.exists():
            out = target_dir / f"{Path(safe).stem}_{i}{Path(safe).suffix}"
            i += 1
        out.write_bytes(payload)
        saved.append({"filename": filename, "saved_as": out.name, "size": len(payload)})
    return saved


def _load_credentials() -> tuple[str, str]:
    if not USER_FILE.exists() or not TOKEN_FILE.exists():
        sys.stderr.write(
            f"[!] Не найдены файлы {USER_FILE} и/или {TOKEN_FILE}.\n"
            "    Создайте пароль приложения mail.ru и сохраните:\n"
            "    Set-Content $env:USERPROFILE\\.claude\\.secrets\\mail_ru.user "
            "'your@mail.ru' -Encoding UTF8 -NoNewline\n"
            "    Set-Content $env:USERPROFILE\\.claude\\.secrets\\mail_ru.token "
            "'<16-значный-пароль>' -Encoding UTF8 -NoNewline\n"
        )
        sys.exit(2)
    user = USER_FILE.read_text(encoding="utf-8").strip()
    token = TOKEN_FILE.read_text(encoding="utf-8").strip()
    if not user or not token:
        sys.stderr.write("[!] Файлы учётки пусты.\n")
        sys.exit(2)
    return user, token


def main() -> int:
    p = argparse.ArgumentParser(description="IMAP dump mail.ru → _inbox/")
    p.add_argument("--since", default=None, help="YYYY-MM-DD; пусто = весь архив")
    p.add_argument("--folder", default="INBOX", help="IMAP-папка (по умолчанию INBOX)")
    p.add_argument("--limit", type=int, default=0, help="Ограничить число писем (0 = все)")
    p.add_argument("--no-filter", action="store_true", help="Скачать все письма без тематического фильтра")
    p.add_argument("--dry-run", action="store_true", help="Только показать что было бы скачано")
    args = p.parse_args()

    user, token = _load_credentials()
    today = datetime.now().strftime("%Y-%m-%d")
    out_root = INBOX_ROOT / f"{today}_email_dump"
    out_root.mkdir(parents=True, exist_ok=True)

    print(f"[*] Подключение к {IMAP_HOST}:{IMAP_PORT} как {user}")
    ctx = ssl.create_default_context()
    M = imaplib.IMAP4_SSL(IMAP_HOST, IMAP_PORT, ssl_context=ctx)
    try:
        M.login(user, token)
    except imaplib.IMAP4.error as e:
        sys.stderr.write(f"[!] Ошибка авторизации: {e}\n")
        sys.stderr.write("    Проверьте: 1) включена двухфакторная авторизация, "
                         "2) пароль — приложения, не основной, 3) IMAP включён в настройках mail.ru.\n")
        return 3

    typ, _ = M.select(args.folder, readonly=True)
    if typ != "OK":
        sys.stderr.write(f"[!] Не удаётся открыть папку {args.folder}\n")
        return 4

    if args.since:
        date_imap = datetime.strptime(args.since, "%Y-%m-%d").strftime("%d-%b-%Y")
        criteria = f'(SINCE "{date_imap}")'
    else:
        criteria = "ALL"
    print(f"[*] IMAP search: {criteria}")
    typ, data = M.search(None, criteria)
    if typ != "OK":
        sys.stderr.write("[!] IMAP search failed\n")
        return 5
    nums = data[0].split()
    print(f"[*] Найдено писем: {len(nums)}")
    if args.limit:
        nums = nums[-args.limit:]
        print(f"[*] Ограничено до {len(nums)} последних")

    matched = 0
    skipped_filter = 0
    saved_attachments_total = 0
    manifest: list[dict] = []

    for idx, num in enumerate(nums, 1):
        typ, msg_data = M.fetch(num, "(RFC822)")
        if typ != "OK" or not msg_data or not msg_data[0]:
            continue
        msg = email.message_from_bytes(msg_data[0][1])
        subject = _decode_mime(msg.get("Subject"))
        from_addr = _decode_mime(msg.get("From"))
        date_hdr = msg.get("Date") or ""
        body_text, body_preview = _extract_body(msg)

        if not args.no_filter:
            if not _matches_filter(subject, body_text[:2000]):
                skipped_filter += 1
                continue

        matched += 1
        from_short = _safe_name(re.findall(r"[\w.+-]+@[\w-]+\.[\w.-]+", from_addr)[0]
                                if "@" in from_addr else from_addr, 40)
        subj_short = _safe_name(subject, 50)
        try:
            dt = email.utils.parsedate_to_datetime(date_hdr)
            date_short = dt.strftime("%Y%m%d_%H%M") if dt else "no_date"
        except Exception:
            date_short = "no_date"

        folder_name = f"{date_short}__{from_short}__{subj_short}"
        target = out_root / folder_name
        if args.dry_run:
            print(f"  [dry] {folder_name}")
            continue
        target.mkdir(parents=True, exist_ok=True)

        # Тело письма
        (target / "email.txt").write_text(
            f"From: {from_addr}\nDate: {date_hdr}\nSubject: {subject}\n\n{body_text}",
            encoding="utf-8",
        )

        # Вложения
        atts = _save_attachments(msg, target)
        saved_attachments_total += len(atts)

        manifest.append({
            "uid": num.decode() if isinstance(num, bytes) else str(num),
            "date": date_hdr,
            "from": from_addr,
            "subject": subject,
            "folder": folder_name,
            "attachments": atts,
            "body_preview": body_text[:500],
        })

        if idx % 50 == 0:
            print(f"  ... обработано {idx}/{len(nums)} (matched={matched})")

    M.close()
    M.logout()

    if not args.dry_run:
        (out_root / "manifest.json").write_text(
            json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8"
        )

    print()
    print(f"[+] Итого: matched={matched}, skipped_filter={skipped_filter}, "
          f"attachments={saved_attachments_total}")
    print(f"[+] Папка: {out_root}")
    if matched and not args.dry_run:
        print(f"[+] Манифест: {out_root / 'manifest.json'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
