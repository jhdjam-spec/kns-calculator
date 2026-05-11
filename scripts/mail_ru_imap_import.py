r"""IMAP-импорт писем mail.ru в _inbox/mail_ru_imap.

ИНВАРИАНТ: на самом почтовом ящике zakaz@inservo.ru НИЧЕГО не меняется.
Все папки открываются в readonly-режиме (см. process_folder).
Письма не помечаются прочитанными, не удаляются, не перемещаются.

Цель — получить из почты ИНФОРМАЦИЮ, которой ещё нет в датасете:
1. Тексты писем (часто в теле — уточнения параметров, согласования, история).
2. Вложения, которых нет в 02_dataset (дедупликация по sha1/size+name).

Архитектура:
1. Подключение IMAP4_SSL к imap.mail.ru:993 (логин + пароль приложения).
2. Поиск по расширенному профильному фильтру (тема + ПОЛНОЕ тело + имена вложений).
3. Загрузка .eml + parsed/*.json с полным текстом + manifest вложений (status: saved/dedup).
4. Дедуп: вложение пропускается, если уже есть в 02_dataset (по sha1, size+name, name).
5. Идемпотентность: state.json — повторный запуск не скачивает уже виденные UID.
6. Сводный letters_index.jsonl — одна строка на письмо для grep / jq / FTS.

Учётные данные читаются из %USERPROFILE%\.claude\.secrets\mail_ru.{user,token}
(либо через переменные окружения MAIL_RU_USER, MAIL_RU_TOKEN — приоритет у env).

CLI:
    python mail_ru_imap_import.py                # все папки, весь архив
    python mail_ru_imap_import.py --folder INBOX --since 2024-01-01 --limit 100
    python mail_ru_imap_import.py --reset-state  # перекачать всё с нуля
    python mail_ru_imap_import.py --dry-run      # без записи на диск
"""
from __future__ import annotations

import argparse
import email
import email.header
import email.utils
import hashlib
import imaplib
import json
import logging
import os
import re
import sys
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from email.message import Message
from pathlib import Path
# --- Константы ----------------------------------------------------------------

IMAP_HOST = "imap.mail.ru"
IMAP_PORT = 993

REPO_ROOT = Path(__file__).resolve().parent.parent
INBOX_DIR = REPO_ROOT / "02_dataset" / "_inbox" / "mail_ru_imap"
RAW_DIR = INBOX_DIR / "raw"
ATTACH_DIR = INBOX_DIR / "attachments"
PARSED_DIR = INBOX_DIR / "parsed"
STATE_FILE = INBOX_DIR / "state.json"
LOG_FILE = INBOX_DIR / "import.log"
FINGERPRINT_FILE = INBOX_DIR / "dataset_fingerprint.json"
LETTERS_INDEX = INBOX_DIR / "letters_index.jsonl"  # одна строка на письмо, для grep/jq
WANTED_FILE = INBOX_DIR / "wanted_filenames.json"  # имена файлов из ручного датасета

SECRETS_DIR = Path(os.environ.get("USERPROFILE", str(Path.home()))) / ".claude" / ".secrets"
USER_FILE = SECRETS_DIR / "mail_ru.user"
TOKEN_FILE = SECRETS_DIR / "mail_ru.token"

# Расширенный профильный фильтр: KNS + смежные темы (ливневка, ЛОС, насосы, тендеры, сделки)
KEYWORDS_RU = [
    # === КНС / насосы — прямые ===
    "КНС", "канализационно-насосная", "канализационная насосная",
    "канализационно насосная", "канализационная насосная станция",
    "насосная станция", "насосный агрегат", "насосная установка",
    "насос", "насосы", "погружной насос", "поверхностный насос",
    "дренажный насос", "фекальный насос", "циркуляционный насос",
    "повышение давления", "повысительная насосная", "ВНС",
    "станция повышения давления", "СПД", "ПНС",
    # === Параметры ===
    "производительность", "напор", "расход",
    " Q=", " Q ", "Q,", "Q ", "м3/ч", "м³/ч", "л/с", "л/мин",
    " H=", " H ", "H,", "H ", "м.вод.ст", "м вод.ст", "метров водяного",
    "DN", "Ду ", "Ду=", "ИП68", "IP68",
    # === Смежные продукты ===
    "ЛОС", "локальные очистные", "очистные сооружения",
    "ливневка", "ливневая канализация", "дождеприёмник",
    "сепаратор нефтепродуктов", "пескоуловитель",
    "септик", "биотуалет", "выгребная яма",
    # === Производственные узлы ===
    "запорная арматура", "обратный клапан", "затвор",
    "ПЛК", "АСУ", "диспетчеризация", "SCADA", "телеметрия",
    "щит управления", "ЩУ", "ЩУН", "шкаф управления", "частотник",
    "преобразователь частоты", "ЧРП",
    # === Инженерные термины ===
    "опросный лист", "опросник", "техническое задание", "ТЗ",
    "коммерческое предложение", "КП ", "тендер", "котировочная заявка",
    "проект", "расчёт", "гидравлический расчёт",
    "паспорт", "сертификат", "руководство по эксплуатации",
    "монтаж", "пусконаладка", "ПНР", "сервис", "обслуживание",
    # === Бренды и партнёры (RU + EN транслитерация) ===
    "Серво", "INSERVO", "Серво-Полимер", "Серво-Юг",
    # Премиум зарубежные
    "Pedrollo", "Педролло",
    "Grundfos", "Грундфос",
    "WILO", "Вило",
    "KSB", "КСБ",
    "Calpeda", "Калпеда",
    "DAB", "ДАБ",
    "Lowara", "Ловара",
    "Speroni", "Сперони",
    "Ebara", "Эбара",
    "Xylem", "Ксилем",
    "Sulzer", "Зульцер",
    "Tsurumi", "Цуруми",
    "ITT Goulds",
    # Бюджет/Азия
    "ANTARUS", "Антарус",
    "KAIQUAN", "Кайцюань",
    "CNP",
    "LEO", "Лео",
    "Fancy", "Фанси",
    "Vandjord",
    "MAS DAF",
    "Шторм Ф", "Storm",
    # РФ-производители
    "ГНОМ", "Иртыш", "СМЗ",
    "Ливгидромаш", "ГМС", "ЦНС",
    "ИСТРАТЕХ", "Истратех", "Istratech",
    "ЭНА", "Эна",
    "Промнасос",
    "Ярославский завод", "ЯЗМ",
    # Шкафы / ЩУ
    "Aikon", "Айкон",
    "PEGAS", "Пегас",
    # Корпуса / ЛОС
    "Plastek", "Пластек",
    "Rainpark", "Рейнпарк",
    "BloPlast", "Блопласт", "БЛОРЭЙ",
    "ПЛЕС", "ПЛЁС", "Плёс",
    "БИОГАРД", "Биогард",
    "Байкал",
    "TOPOL", "ТОПОЛ", "ТОПАС", "TOPAS",
    "ЕВРОБИОН", "Евробион",
    "ЭКО-ЕНОТ", "ФИНТЕК", "FINTEK",
    "ЭКОЛАЙН",
    # === Ёмкости / резервуары / стеклопластик ===
    "емкость", "ёмкость", "резервуар", "накопительная",
    "стеклопластик", "химстойкая", "ёмкости", "емкости",
    "пожарный резервуар", "противопожарный",
]
KEYWORDS_EN = [
    "pump station", "sewage pump", "lift station",
    "stormwater", "sewer pump", "wastewater",
    "tender", "proposal", "RFQ", "RFP", "datasheet",
    "Pedrollo", "Grundfos", "WILO", "KSB",
]

# Расширения вложений, которые сохраняем (всё прочее — пропуск)
ATTACH_EXT = {
    ".pdf", ".dwg", ".dxf", ".docx", ".doc", ".xlsx", ".xls",
    ".jpg", ".jpeg", ".png", ".tif", ".tiff", ".bmp",
    ".zip", ".rar", ".7z", ".tar", ".gz",
    ".txt", ".csv", ".rtf", ".odt",
}

# --- Структуры данных --------------------------------------------------------


@dataclass
class State:
    """Состояние импорта (UID письма уже скачаны — пропускаем)."""

    seen_uids: dict[str, list[str]] = field(default_factory=dict)
    last_run: str = ""

    def is_seen(self, folder: str, uid: str) -> bool:
        return uid in self.seen_uids.get(folder, [])

    def mark(self, folder: str, uid: str) -> None:
        self.seen_uids.setdefault(folder, []).append(uid)

    def save(self, path: Path) -> None:
        self.last_run = datetime.now(timezone.utc).isoformat()
        path.write_text(
            json.dumps(
                {"seen_uids": self.seen_uids, "last_run": self.last_run},
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )

    @classmethod
    def load(cls, path: Path) -> "State":
        if not path.exists():
            return cls()
        data = json.loads(path.read_text(encoding="utf-8"))
        return cls(seen_uids=data.get("seen_uids", {}), last_run=data.get("last_run", ""))


@dataclass
class ImportStats:
    folders: int = 0
    candidates: int = 0
    downloaded: int = 0
    skipped_seen: int = 0
    skipped_filter: int = 0
    attachments_saved: int = 0
    attachments_dedup: int = 0  # уже есть в датасете
    errors: int = 0


# --- Утилиты -----------------------------------------------------------------


def setup_logging(log_path: Path) -> logging.Logger:
    log_path.parent.mkdir(parents=True, exist_ok=True)
    logger = logging.getLogger("mail_ru_imap")
    logger.setLevel(logging.INFO)
    fmt = logging.Formatter("%(asctime)s [%(levelname)s] %(message)s", "%H:%M:%S")
    fh = logging.FileHandler(log_path, encoding="utf-8")
    fh.setFormatter(fmt)
    sh = logging.StreamHandler(sys.stdout)
    sh.setFormatter(fmt)
    logger.handlers = [fh, sh]
    return logger


def load_credentials() -> tuple[str, str]:
    """Берём логин/пароль из env или из ~/.claude/.secrets/."""
    user = os.environ.get("MAIL_RU_USER", "").strip()
    token = os.environ.get("MAIL_RU_TOKEN", "").strip()
    if not user and USER_FILE.exists():
        user = USER_FILE.read_text(encoding="utf-8").strip()
    if not token and TOKEN_FILE.exists():
        token = TOKEN_FILE.read_text(encoding="utf-8").strip()
    if not user or not token:
        raise RuntimeError(
            "Не найдены креды mail.ru. Создайте файлы:\n"
            f"  {USER_FILE}\n  {TOKEN_FILE}\n"
            "или задайте MAIL_RU_USER / MAIL_RU_TOKEN в окружении."
        )
    return user, token


def decode_mime(value: str | None) -> str:
    if not value:
        return ""
    parts = email.header.decode_header(value)
    out: list[str] = []
    for chunk, enc in parts:
        if isinstance(chunk, bytes):
            try:
                out.append(chunk.decode(enc or "utf-8", errors="replace"))
            except (LookupError, UnicodeDecodeError):
                out.append(chunk.decode("utf-8", errors="replace"))
        else:
            out.append(chunk)
    return "".join(out).strip()


def safe_filename(name: str, max_len: int = 120) -> str:
    name = re.sub(r"[<>:\"/\\|?*\x00-\x1f]", "_", name).strip().strip(".")
    if len(name) > max_len:
        stem, dot, ext = name.rpartition(".")
        if dot and len(ext) <= 6:
            name = stem[: max_len - len(ext) - 1] + "." + ext
        else:
            name = name[:max_len]
    return name or "unnamed"


def matches_keywords(text: str) -> bool:
    if not text:
        return False
    t = text.lower()
    return any(kw.lower() in t for kw in KEYWORDS_RU + KEYWORDS_EN)


# --- Шумовой blacklist (источник: первый прогон 1495 писем, INBOX 2020) ------
# Эти отправители/паттерны = трекинг звонков, инстаграм-уведомления, отчёты
# по сайтам, обучения. Не несут полезной информации для калькулятора.

NOISE_SENDER_DOMAINS = {
    "leadback.ru",            # 701 шт — «Успешный звонок с сайта ...»
    "mail.instagram.com",     # 59 — instagram-уведомления
    "instagram.com",
    "dr-mail.com",            # 24 — трекинг
    "youla.ru",               # 8 — Юла
    "ipkrbs.ru",              # обучения по 44-ФЗ/госзакупкам
    "monocrystal.com",        # массовые рассылки
    "market-post.website",
    "marketpost.website",
    "tradeemail.website",
    "ekbpromo.ru",
    "inbox.ru",               # обычно рассылки (личные коллеги через bk.ru)
    "facebook.com",
    "facebookmail.com",
    "linkedin.com",
    "linkedinmail.com",
    "vk.com",
}

# Паттерны темы — если subject начинается с одного из них, это шум.
NOISE_SUBJECT_PATTERNS = (
    "успешный звонок с сайта",
    "бот поймал клиента в чате",
    "журнал диалога из чата",
    "отчёт по вашим сайтам",
    "отчет по вашим сайтам",
    "мультичат: статистика",
    "мультичат:статистика",
    "звонки не поступают",
    "ваш домен ",
    "запланируйте свое обучение",
    "напоминаем вам о предстоящем",
    "see vvm.,",                       # instagram digest
    "see what's been happening on instagram",
    "have new posts",
    "see ",                            # instagram digest вариант
)


def is_noise(sender: str, subject: str) -> bool:
    """Шумовое письмо? Проверяем домен отправителя и шаблон темы."""
    s_lower = (sender or "").lower()
    # домен: ищем @domain в любом виде
    for dom in NOISE_SENDER_DOMAINS:
        if f"@{dom}" in s_lower or f"<{dom}" in s_lower:
            return True
    subj_lower = (subject or "").strip().lower()
    return any(subj_lower.startswith(pat) for pat in NOISE_SUBJECT_PATTERNS)


# --- PII-редактирование (источник: backend/_scripts/anonymize_etalons.py) ----

_TEL_RE = re.compile(r"\+?\d?\s?\(?\d{3}\)?[\s-]?\d{3}[\s-]?\d{2}[\s-]?\d{2}")
_EMAIL_RE = re.compile(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}")
_INN_RE = re.compile(r"\bИНН\s*\d{10,12}\b|\b\d{10}\b(?=\D|$)")
_OGRN_RE = re.compile(r"\b(?:ОГРН|ОГРНИП)\s*\d{13,15}\b|\b\d{13}\b")
_ADDR_RE = re.compile(r"\b\d{6},?\s+[гГ]\.?\s*[А-Я][а-я]+[^,]*?,\s*ул\.?[^,]*", re.UNICODE)


def redact_pii(s: str) -> str:
    if not s:
        return s
    s = _TEL_RE.sub("[тел]", s)
    s = _EMAIL_RE.sub("[email]", s)
    s = _INN_RE.sub("[ИНН]", s)
    s = _OGRN_RE.sub("[ОГРН]", s)
    s = _ADDR_RE.sub("[адрес]", s)
    return s


def extract_full_text(msg: Message) -> str:
    """Полный текст письма (plain + html→text) для индексации и матчинга.

    Тело письма часто содержит ключевую переписку: уточнения параметров,
    согласования, история сделки — даже если вложений нет. Сохраняем целиком.
    """
    pieces: list[str] = []
    for part in msg.walk():
        if part.get_content_maintype() == "multipart":
            continue
        ctype = part.get_content_type()
        if ctype not in ("text/plain", "text/html"):
            continue
        try:
            payload = part.get_payload(decode=True)
            if payload is None:
                continue
            charset = part.get_content_charset() or "utf-8"
            text = payload.decode(charset, errors="replace")
        except (LookupError, UnicodeDecodeError):
            continue
        if ctype == "text/html":
            # выкидываем теги, схлопываем &nbsp; и &amp;
            text = re.sub(r"<(script|style)[^>]*>.*?</\1>", " ", text,
                          flags=re.DOTALL | re.IGNORECASE)
            text = re.sub(r"<[^>]+>", " ", text)
            text = (text.replace("&nbsp;", " ").replace("&amp;", "&")
                    .replace("&lt;", "<").replace("&gt;", ">").replace("&quot;", '"'))
        pieces.append(text)
    joined = "\n".join(pieces)
    return re.sub(r"[ \t]+", " ", joined).strip()


def extract_text_snippet(msg: Message, limit: int = 500) -> str:
    """Короткий snippet — для имени файла и лога."""
    full = extract_full_text(msg)
    flat = re.sub(r"\s+", " ", full).strip()
    return flat[:limit]


# --- Дедупликация по датасету ------------------------------------------------


def norm_filename(name: str) -> str:
    """Нормализация имени файла — должна совпадать с build_dataset_fingerprint.norm_name."""
    n = name.lower()
    if "." in n:
        n = n.rsplit(".", 1)[0]
    n = re.sub(r"\s*\(\d+\)\s*$", "", n)
    n = re.sub(r"\s*копия\s*\d*\s*$", "", n)
    n = re.sub(r"[\s_\-‐-―]+", " ", n)
    n = re.sub(r"\b\d{2,4}[._\-]\d{1,2}[._\-]\d{2,4}\b", "", n)
    n = re.sub(r"\s+", " ", n).strip()
    return n


@dataclass
class Fingerprint:
    """Индекс уже имеющихся в датасете файлов — для пропуска вложений-дублей."""

    by_sha1: dict[str, list[str]] = field(default_factory=dict)
    by_size_name: dict[str, list[str]] = field(default_factory=dict)
    by_name: dict[str, list[str]] = field(default_factory=dict)

    @classmethod
    def load(cls, path: Path) -> "Fingerprint":
        if not path.exists():
            return cls()
        data = json.loads(path.read_text(encoding="utf-8"))
        return cls(
            by_sha1=data.get("by_sha1", {}),
            by_size_name=data.get("by_size_name", {}),
            by_name=data.get("by_name", {}),
        )

    def match(self, payload: bytes, filename: str) -> tuple[str, str] | None:
        """Возвращает (стратегия, путь_в_датасете) если файл уже есть, иначе None."""
        if not payload or not filename:
            return None
        digest = hashlib.sha1(payload).hexdigest()
        if digest in self.by_sha1:
            return ("sha1", self.by_sha1[digest][0])
        nm = norm_filename(filename)
        key_sn = f"{len(payload)}::{nm}"
        if key_sn in self.by_size_name:
            return ("size+name", self.by_size_name[key_sn][0])
        # name-only — слабый сигнал; используем только если имя длиннее 5 символов
        if len(nm) >= 6 and nm in self.by_name:
            return ("name", self.by_name[nm][0])
        return None


def imap_search_uids(
    conn: imaplib.IMAP4_SSL, since: str | None, before: str | None
) -> list[str]:
    """SEARCH ALL/SINCE/BEFORE — фильтр по ключевым словам делаем уже локально (надёжнее)."""
    criteria: list[str] = []
    if since:
        dt = datetime.strptime(since, "%Y-%m-%d")
        criteria += ["SINCE", dt.strftime("%d-%b-%Y")]
    if before:
        dt = datetime.strptime(before, "%Y-%m-%d")
        criteria += ["BEFORE", dt.strftime("%d-%b-%Y")]
    if not criteria:
        criteria = ["ALL"]
    typ, data = conn.uid("SEARCH", None, *criteria)
    if typ != "OK" or not data or not data[0]:
        return []
    return data[0].decode().split()


# Папки, которые по умолчанию пропускаем
SKIP_FOLDERS_RU = {
    "Спам", "Корзина", "Черновики", "Отправленные", "Архив",
    "Trash", "Spam", "Drafts", "Junk", "Deleted Messages",
}


def imap_utf7_decode(name: str) -> str:
    """Декодер IMAP4 modified UTF-7 (RFC 3501) для имён папок."""
    out: list[str] = []
    i = 0
    while i < len(name):
        ch = name[i]
        if ch == "&":
            j = name.find("-", i)
            if j == -1:
                out.append(name[i:])
                break
            chunk = name[i + 1:j]
            if not chunk:
                out.append("&")
            else:
                # IMAP4 mUTF-7: ',' заменяется на '/' для base64
                b64 = chunk.replace(",", "/") + "===="
                try:
                    import base64
                    decoded = base64.b64decode(b64).decode("utf-16-be", errors="replace")
                    out.append(decoded)
                except Exception:
                    out.append(name[i:j + 1])
            i = j + 1
        else:
            out.append(ch)
            i += 1
    return "".join(out)


def list_folders(conn: imaplib.IMAP4_SSL, include_all: bool = False) -> list[tuple[str, str]]:
    """Возвращает список (raw_name, display_name). raw_name — для SELECT, display — для логов."""
    typ, data = conn.list()
    if typ != "OK":
        return [("INBOX", "INBOX")]
    folders: list[tuple[str, str]] = []
    pattern = re.compile(r'\((?P<flags>[^)]*)\)\s+"(?P<delim>[^"]*)"\s+(?P<name>.*)')
    for raw in data:
        line = raw.decode("utf-8", errors="replace")
        m = pattern.match(line)
        if not m:
            continue
        name = m.group("name").strip()
        if name.startswith('"') and name.endswith('"'):
            name = name[1:-1]
        display = imap_utf7_decode(name)
        if not include_all and display in SKIP_FOLDERS_RU:
            continue
        folders.append((name, display))
    return folders or [("INBOX", "INBOX")]


def fetch_message(conn: imaplib.IMAP4_SSL, uid: str) -> Message | None:
    typ, data = conn.uid("FETCH", uid, "(RFC822)")
    if typ != "OK" or not data or not data[0]:
        return None
    raw_bytes = data[0][1] if isinstance(data[0], tuple) else None
    if not raw_bytes:
        return None
    return email.message_from_bytes(raw_bytes)


def connect_imap(user: str, token: str, logger: logging.Logger) -> imaplib.IMAP4_SSL:
    """Создаёт новое IMAP4_SSL-соединение и логинится. Бросает исключение при ошибке."""
    conn = imaplib.IMAP4_SSL(IMAP_HOST, IMAP_PORT)
    conn.login(user, token)
    logger.info("(re)connected to %s:%d as %s", IMAP_HOST, IMAP_PORT, user)
    return conn


def save_attachments(
    msg: Message,
    dest: Path,
    logger: logging.Logger,
    fp: Fingerprint,
) -> tuple[int, int, list[dict]]:
    """Сохраняет вложения, пропуская те, что уже есть в датасете.

    Возвращает (saved, dedup, manifest), где manifest — список записей
    {filename, size, sha1, status, dataset_path?} для каждого вложения.
    """
    saved = 0
    dedup = 0
    manifest: list[dict] = []
    for part in msg.walk():
        if part.get_content_maintype() == "multipart":
            continue
        disp = part.get("Content-Disposition") or ""
        filename = part.get_filename()
        if not filename and "attachment" not in disp.lower():
            continue
        if filename:
            filename = decode_mime(filename)
        else:
            ctype = part.get_content_type().replace("/", "_")
            filename = f"part_{saved + dedup + 1}.{ctype}"
        ext = Path(filename).suffix.lower()
        if ext and ext not in ATTACH_EXT:
            continue
        payload = part.get_payload(decode=True)
        if not payload:
            continue

        size = len(payload)
        digest = hashlib.sha1(payload).hexdigest()
        record = {
            "filename": filename,
            "size": size,
            "sha1": digest,
        }

        match = fp.match(payload, filename)
        if match is not None:
            strategy, ds_path = match
            record["status"] = "dedup"
            record["dedup_strategy"] = strategy
            record["dataset_path"] = ds_path
            manifest.append(record)
            dedup += 1
            logger.info("    ↩ дубль (%s): %s → уже есть %s",
                        strategy, filename, ds_path)
            continue

        dest.mkdir(parents=True, exist_ok=True)
        out = dest / safe_filename(filename)
        if out.exists():
            stem, suf = out.stem, out.suffix
            i = 1
            while out.exists():
                out = dest / f"{stem}__{i}{suf}"
                i += 1
        try:
            out.write_bytes(payload)
            saved += 1
            record["status"] = "saved"
            record["saved_as"] = str(out.relative_to(REPO_ROOT))
        except OSError as exc:
            logger.warning("Не сохранить вложение %s: %s", filename, exc)
            record["status"] = "error"
            record["error"] = str(exc)
        manifest.append(record)
    return saved, dedup, manifest


def build_meta(
    msg: Message,
    folder: str,
    uid: str,
    snippet: str,
    body: str,
    attachments_manifest: list[dict],
    wanted_hits: list[str] | None = None,
) -> dict:
    return {
        "folder": folder,
        "uid": uid,
        "message_id": msg.get("Message-ID", ""),
        "from": decode_mime(msg.get("From")),
        "to": decode_mime(msg.get("To")),
        "cc": decode_mime(msg.get("Cc")),
        "date": msg.get("Date", ""),
        "subject": decode_mime(msg.get("Subject")),
        "snippet": snippet,
        "body": body,
        "body_chars": len(body),
        "attachments": attachments_manifest,
        "wanted_hits": wanted_hits or [],
        "imported_at": datetime.now(timezone.utc).isoformat(),
    }


def append_letters_index(meta: dict, slug: str) -> None:
    """Одна строка JSON на письмо — для grep / jq / поиска по корпусу."""
    LETTERS_INDEX.parent.mkdir(parents=True, exist_ok=True)
    light = {
        "slug": slug,
        "folder": meta["folder"],
        "uid": meta["uid"],
        "date": meta["date"],
        "from": meta["from"],
        "to": meta["to"],
        "subject": meta["subject"],
        "body_chars": meta["body_chars"],
        "snippet": meta["snippet"],
        "attachments": [
            {"filename": a["filename"], "status": a["status"],
             "sha1": a.get("sha1", ""),
             "dataset_path": a.get("dataset_path", "")}
            for a in meta["attachments"]
        ],
    }
    with LETTERS_INDEX.open("a", encoding="utf-8") as f:
        f.write(json.dumps(light, ensure_ascii=False) + "\n")


# --- Режим targeted: матчинг по именам файлов из ручного датасета -----------


@dataclass
class Wanted:
    """Индекс имён файлов, которые пользователь скачал вручную."""

    exact_names: set[str] = field(default_factory=set)
    normalized: set[str] = field(default_factory=set)

    @classmethod
    def load(cls, path: Path) -> "Wanted":
        if not path.exists():
            return cls()
        data = json.loads(path.read_text(encoding="utf-8"))
        return cls(
            exact_names={n.lower() for n in data.get("exact_names", [])},
            normalized=set(data.get("normalized", [])),
        )

    def match_attachments(self, msg: Message) -> list[str]:
        """Возвращает список имён файлов в письме, которые есть в wanted-индексе."""
        hits: list[str] = []
        for part in msg.walk():
            if part.get_content_maintype() == "multipart":
                continue
            fn = part.get_filename()
            if not fn:
                continue
            fn = decode_mime(fn)
            if fn.lower() in self.exact_names:
                hits.append(fn)
                continue
            nm = norm_filename(fn)
            if nm and nm in self.normalized:
                hits.append(fn)
        return hits


# --- Главный цикл ------------------------------------------------------------


def process_folder(
    conn: imaplib.IMAP4_SSL,
    folder_raw: str,
    folder_display: str,
    state: State,
    args: argparse.Namespace,
    stats: ImportStats,
    logger: logging.Logger,
    fp: Fingerprint,
    wanted: Wanted | None = None,
    creds: tuple[str, str] | None = None,
) -> imaplib.IMAP4_SSL:
    """Возвращает актуальный conn (после возможных reconnect-ов)."""
    # ВАЖНО: readonly=True — на сервере НИЧЕГО не меняем.
    # Не выставляем \Seen, не удаляем, не перемещаем, не помечаем.
    # На самом ящике zakaz@inservo.ru всё остаётся как было.
    if conn is None and creds is not None:
        conn = connect_imap(creds[0], creds[1], logger)
    typ, _ = conn.select(f'"{folder_raw}"', readonly=True)
    if typ != "OK":
        logger.warning("Не открыть папку %s — пропускаю", folder_display)
        return conn
    stats.folders += 1
    uids = imap_search_uids(conn, args.since, args.before)
    if args.limit:
        uids = uids[-args.limit:]  # последние N
    logger.info("Папка %s: %d писем в выборке", folder_display, len(uids))

    consecutive_errors = 0  # сбрасывается при успешном FETCH
    processed_since_save = 0

    for uid in uids:
        stats.candidates += 1
        if state.is_seen(folder_display, uid) and not args.reset_state:
            stats.skipped_seen += 1
            continue
        # FETCH с автореконнектом при socket/SSL разрыве
        msg = None
        for attempt in range(3):
            try:
                msg = fetch_message(conn, uid)
                consecutive_errors = 0
                break
            except (imaplib.IMAP4.error, OSError, ConnectionError) as exc:
                consecutive_errors += 1
                err_text = str(exc)
                # SSL EOF / соединение разорвано — пробуем реконнект
                if creds and ("EOF" in err_text or "socket" in err_text.lower()
                              or "abort" in err_text.lower() or "BYE" in err_text
                              or "closed" in err_text.lower() or attempt < 2):
                    logger.warning("FETCH UID=%s att=%d: %s — reconnect",
                                   uid, attempt + 1, err_text[:120])
                    try:
                        try:
                            conn.logout()
                        except Exception:
                            pass
                        time.sleep(2 + attempt * 3)  # 2s, 5s
                        conn = connect_imap(creds[0], creds[1], logger)
                        conn.select(f'"{folder_raw}"', readonly=True)
                        continue  # retry
                    except Exception as recon_exc:
                        logger.error("Reconnect failed: %s", recon_exc)
                        time.sleep(10)
                        continue
                logger.error("FETCH UID=%s: %s", uid, err_text[:120])
                break
        # Сохраняем state и при skip, и при ошибке — раз в 200 проверенных UID
        processed_since_save += 1
        if processed_since_save >= 200 and not args.dry_run:
            state.save(STATE_FILE)
            processed_since_save = 0
        if msg is None:
            stats.errors += 1
            # Если 50+ ошибок подряд — папка явно не работает, прерываем её
            if consecutive_errors >= 50:
                logger.error("Папка %s: 50+ ошибок подряд, прерываю", folder_display)
                break
            continue

        subject = decode_mime(msg.get("Subject"))
        sender = decode_mime(msg.get("From"))
        # Дешёвая проверка ДО парсинга тела — шум сразу скипаем.
        if is_noise(sender, subject):
            stats.skipped_filter += 1
            state.mark(folder_display, uid)
            continue
        # === Режим targeted: матч по именам вложений из ручного датасета ===
        wanted_hits: list[str] = []
        if args.match_wanted and wanted is not None:
            wanted_hits = wanted.match_attachments(msg)
            if not wanted_hits:
                # Письмо не содержит ни одного из «нужных» файлов — пропускаем.
                stats.skipped_filter += 1
                state.mark(folder_display, uid)
                continue

        body_raw = extract_full_text(msg)
        body = body_raw if args.no_redact else redact_pii(body_raw)
        snippet = re.sub(r"\s+", " ", body).strip()[:500]

        # В обычном режиме — фильтр по ключевым словам.
        # В targeted режиме матч уже произошёл по имени вложения, фильтр пропускаем.
        if not args.match_wanted:
            attach_names = " ".join(
                decode_mime(p.get_filename() or "") for p in msg.walk()
                if p.get_filename()
            )
            haystack = f"{subject}\n{body}\n{attach_names}"
            if not matches_keywords(haystack):
                stats.skipped_filter += 1
                state.mark(folder_display, uid)
                continue

        # Сохраняем .eml + meta.json
        try:
            date_hdr = email.utils.parsedate_to_datetime(msg.get("Date") or "")
        except (TypeError, ValueError):
            date_hdr = None
        date_prefix = date_hdr.strftime("%Y-%m-%d") if date_hdr else "0000-00-00"
        slug = safe_filename(f"{date_prefix}_{folder_display}_{uid}_{subject[:60]}", 150)

        if args.no_attachments:
            # Только тело + meta, вложения не парсим (но raw .eml сохраняем)
            saved = dedup = 0
            manifest: list[dict] = []
            if not args.dry_run:
                RAW_DIR.mkdir(parents=True, exist_ok=True)
                PARSED_DIR.mkdir(parents=True, exist_ok=True)
                (RAW_DIR / f"{slug}.eml").write_bytes(msg.as_bytes())
                meta = build_meta(msg, folder_display, uid, snippet, body, manifest, wanted_hits)
                (PARSED_DIR / f"{slug}.json").write_text(
                    json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8"
                )
                append_letters_index(meta, slug)
            stats.downloaded += 1
            state.mark(folder_display, uid)
            logger.info(
                "✓ %s [%s] %s | body=%d (wanted: %s)",
                date_prefix, folder_display, subject[:60], len(body),
                ", ".join(wanted_hits) if wanted_hits else "—",
            )
            if stats.downloaded % 25 == 0 and not args.dry_run:
                state.save(STATE_FILE)
            continue
        elif args.dry_run:
            # В dry-run всё равно прогоняем дедуп — чтобы получить честные счётчики
            saved = dedup = 0
            for part in msg.walk():
                if part.get_content_maintype() == "multipart":
                    continue
                fn = part.get_filename()
                if not fn:
                    continue
                fn = decode_mime(fn)
                if Path(fn).suffix.lower() not in ATTACH_EXT:
                    continue
                pl = part.get_payload(decode=True)
                if not pl:
                    continue
                if fp.match(pl, fn) is not None:
                    dedup += 1
                else:
                    saved += 1
            stats.attachments_saved += saved
            stats.attachments_dedup += dedup
        else:
            RAW_DIR.mkdir(parents=True, exist_ok=True)
            PARSED_DIR.mkdir(parents=True, exist_ok=True)
            (RAW_DIR / f"{slug}.eml").write_bytes(msg.as_bytes())
            saved, dedup, manifest = save_attachments(msg, ATTACH_DIR / slug, logger, fp)
            meta = build_meta(msg, folder_display, uid, snippet, body, manifest, wanted_hits)
            (PARSED_DIR / f"{slug}.json").write_text(
                json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8"
            )
            append_letters_index(meta, slug)
            stats.attachments_saved += saved
            stats.attachments_dedup += dedup

        stats.downloaded += 1
        state.mark(folder_display, uid)
        logger.info(
            "✓ %s [%s] %s | body=%d вложения: +%d ↩%d",
            date_prefix, folder_display, subject[:60], len(body), saved, dedup,
        )

        if stats.downloaded % 25 == 0 and not args.dry_run:
            state.save(STATE_FILE)


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="IMAP импорт писем mail.ru → 02_dataset/_inbox/mail_ru_imap")
    p.add_argument("--folder", help="Имя папки IMAP (по умолчанию — все папки)")
    p.add_argument("--since", help="Дата начала YYYY-MM-DD (по умолчанию весь архив)")
    p.add_argument("--before", help="Дата конца YYYY-MM-DD")
    p.add_argument("--limit", type=int, help="Не больше N последних писем на папку")
    p.add_argument("--reset-state", action="store_true", help="Игнорировать seen_uids — перекачать заново")
    p.add_argument("--dry-run", action="store_true", help="Только подсчёт, без записи на диск")
    p.add_argument("--include-trash", action="store_true",
                   help="Включить служебные папки (Спам, Корзина, Черновики и т.д.)")
    p.add_argument("--no-redact", action="store_true",
                   help="Не маскировать PII (телефоны/email/ИНН/ОГРН) в телах писем")
    p.add_argument("--match-wanted", action="store_true",
                   help="Targeted-режим: брать только письма, где приложены файлы "
                        "из 02_dataset/_inbox/mail_ru_imap/wanted_filenames.json")
    p.add_argument("--no-attachments", action="store_true",
                   help="Не сохранять вложения вообще (только тела + meta).")
    args = p.parse_args(argv)

    INBOX_DIR.mkdir(parents=True, exist_ok=True)
    logger = setup_logging(LOG_FILE)
    logger.info("=== Старт импорта mail.ru → %s ===", INBOX_DIR)

    try:
        user, token = load_credentials()
    except RuntimeError as exc:
        logger.error(str(exc))
        return 2

    try:
        conn = connect_imap(user, token, logger)
    except imaplib.IMAP4.error as exc:
        logger.error("LOGIN failed: %s", exc)
        return 3

    state = State.load(STATE_FILE)
    fp = Fingerprint.load(FINGERPRINT_FILE)
    wanted = Wanted.load(WANTED_FILE) if args.match_wanted else None
    if args.match_wanted:
        if not wanted or not wanted.exact_names:
            logger.error(
                "Не найден %s или индекс пуст. Запустите: "
                "python scripts/build_wanted_filenames.py", WANTED_FILE,
            )
            return 4
        logger.info("Targeted-режим: %d имён файлов в wanted",
                    len(wanted.exact_names))
    if not (fp.by_sha1 or fp.by_name):
        logger.warning(
            "Не найден %s — дедупликация против датасета отключена. "
            "Запустите: python scripts/build_dataset_fingerprint.py",
            FINGERPRINT_FILE,
        )
    else:
        logger.info(
            "Fingerprint датасета: %d sha1, %d имён — дедуп активен",
            len(fp.by_sha1), len(fp.by_name),
        )
    stats = ImportStats()
    started = time.time()

    try:
        if args.folder:
            folders: list[tuple[str, str]] = [(args.folder, args.folder)]
        else:
            folders = list_folders(conn, include_all=args.include_trash)
            logger.info(
                "Будет обработано папок: %d → %s",
                len(folders),
                ", ".join(d for _, d in folders),
            )
        for folder_raw, folder_display in folders:
            try:
                if conn is None:
                    conn = connect_imap(user, token, logger)
                conn = process_folder(
                    conn, folder_raw, folder_display, state, args, stats, logger, fp,
                    wanted=wanted, creds=(user, token),
                )
            except (imaplib.IMAP4.error, OSError, ConnectionError, AttributeError) as exc:
                logger.error("Папка %s: %s — пробую переподключиться", folder_display, exc)
                stats.errors += 1
                try:
                    try:
                        if conn is not None:
                            conn.logout()
                    except Exception:
                        pass
                    time.sleep(5)
                    conn = connect_imap(user, token, logger)
                except Exception as e2:
                    logger.error("Reconnect перед следующей папкой не удался: %s", e2)
                    conn = None
                    time.sleep(30)
                    continue
    finally:
        if not args.dry_run:
            state.save(STATE_FILE)
        try:
            conn.logout()
        except Exception:
            pass

    elapsed = time.time() - started
    logger.info(
        "=== Готово за %.1f с | папок=%d, кандидатов=%d, скачано=%d, "
        "пропущено(seen)=%d, пропущено(фильтр)=%d, "
        "вложений новых=%d, дублей с датасетом=%d, ошибок=%d ===",
        elapsed,
        stats.folders,
        stats.candidates,
        stats.downloaded,
        stats.skipped_seen,
        stats.skipped_filter,
        stats.attachments_saved,
        stats.attachments_dedup,
        stats.errors,
    )
    return 0 if stats.errors == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
