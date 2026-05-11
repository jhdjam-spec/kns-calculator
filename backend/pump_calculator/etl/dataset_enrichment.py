"""Dataset enrichment pipeline — превращаем uploaded ТЗ в эталоны.

Поток
=====

Каждый ``POST /import/parse`` даёт ``TZParseResult`` с ``confidence`` ∈ [0, 1].
В зависимости от confidence:

- ``confidence >= 0.7`` → **auto-accept**: положить запись в
  ``02_dataset/etalons/from_uploads/etalons_uploaded.jsonl``. Это значит,
  что 4 ключевых поля (Q, H, city, wastewater_type) почти все
  заполнены и эталон сразу годен для regression-тестов матчинга.
- ``0.5 <= confidence < 0.7`` → **queue for review**: пишем в
  ``02_dataset/etalons/from_uploads/_queue/<id>.json``, ждём manual
  approve через `/admin/uploads/{id}/approve`.
- ``confidence < 0.5`` → **archive only**: остаётся только в S3,
  в dataset не попадает (слишком мало сигнала, чтобы быть эталоном).

Merge в публичный etalons
=========================

``merge_to_etalons()`` запускается раз в день / вручную и:
1. Читает ``etalons_uploaded.jsonl``.
2. Дедупликация: skip если запись с тем же ``project_code`` или ``(Q,H,city)``
   уже есть в ``public/etalons_public_2026-05-09.json``.
3. (Для MVP) пишет новый список в
   ``public/etalons_from_uploads.json`` — чтобы не трогать canonical файл
   автоматически (manual review перед merge остаётся).

Безопасность
============
``DatasetEnricher`` принимает ``dataset_root`` параметром — тесты могут
указать tmp_path. По умолчанию использует репозиторий
(``<repo>/02_dataset``), вычисленный относительно файла.

Все файловые операции — defensive: если нет прав на запись или директория
не существует, возвращаем ``error``, но не throws.
"""
from __future__ import annotations

import json
import logging
import os
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Константы и пороги
# ---------------------------------------------------------------------------

#: Минимальный confidence для auto-accept в эталоны.
AUTO_ACCEPT_THRESHOLD = 0.7

#: Минимальный confidence для попадания в queue (ниже → только S3 архив).
QUEUE_THRESHOLD = 0.5

#: Статусы upload'ов.
STATUS_AUTO_ACCEPTED = "auto_accepted"
STATUS_QUEUED = "queued"
STATUS_ARCHIVED_ONLY = "archived_only"
STATUS_APPROVED = "approved"
STATUS_REJECTED = "rejected"

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------


def _default_dataset_root() -> Path:
    """Найти ``<repo>/02_dataset`` относительно текущего файла.

    Файл: ``backend/pump_calculator/etl/dataset_enrichment.py``
    → repo root на 3 уровня выше.
    """
    return Path(__file__).resolve().parents[3] / "02_dataset"


# ---------------------------------------------------------------------------
# Public class
# ---------------------------------------------------------------------------


class DatasetEnricher:
    """Категоризация upload'ов + персист в files.

    Все методы возвращают dict с фактами (что произошло, где файл),
    не raise (кроме явных ошибок программирования).
    """

    def __init__(
        self,
        dataset_root: Path | str | None = None,
        *,
        auto_threshold: float = AUTO_ACCEPT_THRESHOLD,
        queue_threshold: float = QUEUE_THRESHOLD,
    ) -> None:
        self.dataset_root = Path(dataset_root) if dataset_root else _default_dataset_root()
        # Writable root для uploads/_queue/_rejected (YC Functions FS read-only,
        # dataset_root указывает на bundled read-only 02_dataset/). Можно
        # переопределить через ENV KNS_DATASET_UPLOADS_ROOT, например /tmp/uploads.
        uploads_override = os.environ.get("KNS_DATASET_UPLOADS_ROOT")
        self.uploads_root = Path(uploads_override) if uploads_override else self.dataset_root
        self.auto_threshold = auto_threshold
        self.queue_threshold = queue_threshold

    # ------------------------------------------------------------------
    # Paths
    # ------------------------------------------------------------------

    @property
    def from_uploads_dir(self) -> Path:
        # Использует writable uploads_root (см. __init__): на YC Functions
        # это /tmp/uploads (ephemeral, но это OK — orchestrator merge'ит в
        # canonical dataset вручную через /admin/uploads/merge).
        return self.uploads_root / "etalons" / "from_uploads"

    @property
    def jsonl_path(self) -> Path:
        return self.from_uploads_dir / "etalons_uploaded.jsonl"

    @property
    def queue_dir(self) -> Path:
        return self.from_uploads_dir / "_queue"

    @property
    def public_etalons_path(self) -> Path:
        return self.dataset_root / "etalons" / "public" / "etalons_public_2026-05-09.json"

    @property
    def public_merge_output(self) -> Path:
        return self.dataset_root / "etalons" / "public" / "etalons_from_uploads.json"

    @property
    def rejected_dir(self) -> Path:
        return self.from_uploads_dir / "_rejected"

    def _ensure_dirs(self) -> None:
        for d in (self.from_uploads_dir, self.queue_dir, self.rejected_dir):
            try:
                d.mkdir(parents=True, exist_ok=True)
            except OSError as e:
                logger.warning("Cannot create %s: %s", d, e)

    # ------------------------------------------------------------------
    # Categorization
    # ------------------------------------------------------------------

    def categorize(self, confidence: float) -> str:
        """Какой treatment получит upload с такой confidence."""
        if confidence >= self.auto_threshold:
            return STATUS_AUTO_ACCEPTED
        if confidence >= self.queue_threshold:
            return STATUS_QUEUED
        return STATUS_ARCHIVED_ONLY

    # ------------------------------------------------------------------
    # Main entry: process_upload
    # ------------------------------------------------------------------

    def process_upload(
        self,
        parsed: dict[str, Any],
        raw_text: str,
        s3_key: str | None,
        *,
        upload_id: str | None = None,
        yadisk_path: str | None = None,
        original_filename: str | None = None,
    ) -> dict[str, Any]:
        """Главная точка интеграции: куда положить upload по confidence.

        Parameters
        ----------
        parsed
            TZParseResult в виде dict (после ``model_dump()``).
        raw_text
            Оригинальный текст ТЗ (для очереди — пишем рядом).
        s3_key
            Ключ raw text в S3 (если S3 сконфигурирован), иначе None.
        upload_id
            Стабильный ID (если уже есть из S3 catalog) — иначе генерируем.
        yadisk_path
            Путь в Я.Диск (если есть) — кладём в record для traceability.

        Returns
        -------
        dict с полями:
            - ``status``: auto_accepted / queued / archived_only
            - ``confidence``: float
            - ``upload_id``: str
            - ``record_path``: Path | None — куда положили (для queued)
            - ``jsonl_appended``: bool — добавили ли в etalons_uploaded.jsonl
            - ``error``: str | None
        """
        confidence = float(parsed.get("confidence", 0.0))
        status = self.categorize(confidence)
        upload_id = upload_id or self._make_upload_id(parsed)

        record = self._build_record(
            parsed=parsed,
            upload_id=upload_id,
            status=status,
            s3_key=s3_key,
            yadisk_path=yadisk_path,
            original_filename=original_filename,
        )

        result: dict[str, Any] = {
            "status": status,
            "confidence": confidence,
            "upload_id": upload_id,
            "record_path": None,
            "jsonl_appended": False,
            "error": None,
        }

        if status == STATUS_ARCHIVED_ONLY:
            # Ничего не пишем в dataset — только S3 архив (уже сделан).
            return result

        try:
            self._ensure_dirs()
        except Exception as e:  # noqa: BLE001
            result["error"] = f"cannot create from_uploads dir: {e}"
            return result

        if status == STATUS_AUTO_ACCEPTED:
            # 1. Append в jsonl
            try:
                self._append_jsonl(record)
                result["jsonl_appended"] = True
                result["record_path"] = str(self.jsonl_path)
            except OSError as e:
                result["error"] = f"jsonl append failed: {e}"
            return result

        # QUEUED — пишем отдельный JSON в _queue/, с raw_text для review.
        queue_path = self.queue_dir / f"{upload_id}.json"
        queue_record = dict(record)
        queue_record["raw_text"] = raw_text
        try:
            queue_path.write_text(
                json.dumps(queue_record, ensure_ascii=False, indent=2), encoding="utf-8"
            )
            result["record_path"] = str(queue_path)
        except OSError as e:
            result["error"] = f"queue write failed: {e}"
        return result

    # ------------------------------------------------------------------
    # Record build
    # ------------------------------------------------------------------

    @staticmethod
    def _build_record(
        *,
        parsed: dict[str, Any],
        upload_id: str,
        status: str,
        s3_key: str | None,
        yadisk_path: str | None,
        original_filename: str | None,
    ) -> dict[str, Any]:
        """Каноничная JSONL-запись для etalons_uploaded."""
        now = datetime.now(UTC).isoformat()
        return {
            "id": upload_id,
            "Q_m3h": parsed.get("Q_m3h"),
            "dH_m": parsed.get("dH_m"),
            "city": parsed.get("city"),
            "wastewater_type": parsed.get("wastewater_type"),
            "project_code": parsed.get("project_code"),
            "project_codes": parsed.get("project_codes") or [],
            "object_type": parsed.get("object_type"),
            "manufacturer": parsed.get("manufacturer"),
            "Ex_required": bool(parsed.get("Ex_required", False)),
            "reliability": parsed.get("reliability"),
            "liquid_temp_c": parsed.get("liquid_temp_c"),
            "confidence": float(parsed.get("confidence", 0.0)),
            "status": status,
            "source": "user_import",
            "s3_key": s3_key,
            "yadisk_path": yadisk_path,
            "original_filename": original_filename,
            "uploaded_at": now,
        }

    @staticmethod
    def _make_upload_id(parsed: dict[str, Any]) -> str:
        ts = datetime.now(UTC)
        suffix = ""
        pc = parsed.get("project_code")
        if pc:
            # Очистим до alphanumeric
            suffix = "-" + "".join(c for c in str(pc) if c.isalnum())[:10]
        return f"upload-{ts.strftime('%Y-%m-%d-%H%M%S')}{suffix}"

    # ------------------------------------------------------------------
    # JSONL operations
    # ------------------------------------------------------------------

    def _append_jsonl(self, record: dict[str, Any]) -> None:
        self.jsonl_path.parent.mkdir(parents=True, exist_ok=True)
        line = json.dumps(record, ensure_ascii=False) + "\n"
        with self.jsonl_path.open("a", encoding="utf-8") as f:
            f.write(line)

    def read_uploaded(self) -> list[dict[str, Any]]:
        """Прочитать все записи из etalons_uploaded.jsonl."""
        if not self.jsonl_path.exists():
            return []
        out: list[dict[str, Any]] = []
        for line in self.jsonl_path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                out.append(json.loads(line))
            except json.JSONDecodeError:
                continue
        return out

    def read_queue(self) -> list[dict[str, Any]]:
        """Все queue-файлы (для admin/uploads UI)."""
        if not self.queue_dir.exists():
            return []
        out: list[dict[str, Any]] = []
        for p in sorted(self.queue_dir.glob("*.json")):
            try:
                out.append(json.loads(p.read_text(encoding="utf-8")))
            except (OSError, json.JSONDecodeError) as e:
                logger.warning("bad queue file %s: %s", p, e)
        return out

    # ------------------------------------------------------------------
    # Admin operations: approve / reject
    # ------------------------------------------------------------------

    def approve(self, upload_id: str) -> dict[str, Any]:
        """Manual approve queued upload → переместить в etalons_uploaded.jsonl.

        Returns {"ok": bool, "error": str | None, "record": dict | None}.
        """
        queue_path = self.queue_dir / f"{upload_id}.json"
        if not queue_path.exists():
            return {"ok": False, "error": f"not in queue: {upload_id}", "record": None}
        try:
            data = json.loads(queue_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as e:
            return {"ok": False, "error": f"bad queue file: {e}", "record": None}
        # Очищаем raw_text перед добавлением в jsonl — там лишний balласт.
        data.pop("raw_text", None)
        data["status"] = STATUS_APPROVED
        data["approved_at"] = datetime.now(UTC).isoformat()
        try:
            self._append_jsonl(data)
        except OSError as e:
            return {"ok": False, "error": f"append failed: {e}", "record": data}
        try:
            queue_path.unlink()
        except OSError as e:
            logger.warning("cannot remove queue file %s: %s", queue_path, e)
        return {"ok": True, "error": None, "record": data}

    def reject(self, upload_id: str, reason: str | None = None) -> dict[str, Any]:
        """Manual reject queued upload → переместить в _rejected/."""
        queue_path = self.queue_dir / f"{upload_id}.json"
        if not queue_path.exists():
            return {"ok": False, "error": f"not in queue: {upload_id}"}
        try:
            self.rejected_dir.mkdir(parents=True, exist_ok=True)
            data = json.loads(queue_path.read_text(encoding="utf-8"))
            data["status"] = STATUS_REJECTED
            data["rejected_at"] = datetime.now(UTC).isoformat()
            data["reject_reason"] = reason or ""
            (self.rejected_dir / f"{upload_id}.json").write_text(
                json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8"
            )
            queue_path.unlink()
            return {"ok": True, "error": None}
        except (OSError, json.JSONDecodeError) as e:
            return {"ok": False, "error": str(e)}

    # ------------------------------------------------------------------
    # Merge to public etalons
    # ------------------------------------------------------------------

    def merge_to_etalons(self) -> dict[str, Any]:
        """Merge ``etalons_uploaded.jsonl`` → ``etalons_from_uploads.json``.

        Дедупликация против ``etalons_public_2026-05-09.json``:
        - skip если ``project_code`` совпадает (case-insensitive);
        - skip если ``(Q±5%, H±5%, city)`` совпадает.

        Пишем именно в отдельный ``etalons_from_uploads.json``, чтобы не
        ломать canonical файл — финальный merge остаётся manual.
        """
        uploaded = self.read_uploaded()
        if not uploaded:
            return {
                "merged_count": 0,
                "skipped_dedup": 0,
                "output_path": None,
                "error": "no uploaded records",
            }
        public_records = self._load_public_etalons()
        existing_codes = {
            str(r.get("code", "")).strip().lower()
            for r in public_records
            if r.get("code")
        }

        new_records: list[dict[str, Any]] = []
        skipped = 0
        for rec in uploaded:
            pc = rec.get("project_code")
            if pc and str(pc).strip().lower() in existing_codes:
                skipped += 1
                continue
            if self._near_duplicate(rec, public_records):
                skipped += 1
                continue
            new_records.append(rec)

        out_path = self.public_merge_output
        try:
            out_path.parent.mkdir(parents=True, exist_ok=True)
            out_path.write_text(
                json.dumps(new_records, ensure_ascii=False, indent=2), encoding="utf-8"
            )
        except OSError as e:
            return {
                "merged_count": 0,
                "skipped_dedup": skipped,
                "output_path": None,
                "error": f"write failed: {e}",
            }
        return {
            "merged_count": len(new_records),
            "skipped_dedup": skipped,
            "output_path": str(out_path),
            "error": None,
        }

    def _load_public_etalons(self) -> list[dict[str, Any]]:
        if not self.public_etalons_path.exists():
            return []
        try:
            data = json.loads(self.public_etalons_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as e:
            logger.warning("Cannot read public etalons: %s", e)
            return []
        return data if isinstance(data, list) else []

    @staticmethod
    def _near_duplicate(rec: dict[str, Any], existing: list[dict[str, Any]]) -> bool:
        """``(Q±5%, H±5%, city)`` уже есть в existing → True."""
        q = rec.get("Q_m3h")
        h = rec.get("dH_m")
        city = (rec.get("city") or "").strip().lower()
        if not (q and h and city):
            return False
        for ex in existing:
            ex_q = ex.get("Q_m3h")
            ex_h = ex.get("H_m") or ex.get("dH_m")
            ex_city = (ex.get("location") or ex.get("city") or "").strip().lower()
            if not (ex_q and ex_h and ex_city):
                continue
            if city not in ex_city and ex_city not in city:
                continue
            if abs(q - ex_q) / max(q, 1) > 0.05:
                continue
            if abs(h - ex_h) / max(h, 1) > 0.05:
                continue
            return True
        return False


# ---------------------------------------------------------------------------
# Module-level convenience
# ---------------------------------------------------------------------------


def enrich_from_parse(
    parsed: dict[str, Any],
    raw_text: str,
    *,
    s3_key: str | None = None,
    yadisk_path: str | None = None,
    upload_id: str | None = None,
    original_filename: str | None = None,
    dataset_root: str | None = None,
) -> dict[str, Any]:
    """Удобная wrapper-функция: process_upload с default enricher.

    Можно отключить через ENV ``KNS_DATASET_ENRICHMENT_DISABLED=1`` —
    тогда returns ``{"status": "disabled", ...}`` (для prod-окружений
    с read-only FS на YC Functions).
    """
    if os.environ.get("KNS_DATASET_ENRICHMENT_DISABLED") == "1":
        return {
            "status": "disabled",
            "confidence": float(parsed.get("confidence", 0.0)),
            "upload_id": upload_id,
            "record_path": None,
            "jsonl_appended": False,
            "error": "dataset enrichment disabled by ENV",
        }
    root = dataset_root or os.environ.get("KNS_DATASET_ROOT")
    enricher = DatasetEnricher(dataset_root=root)
    return enricher.process_upload(
        parsed=parsed,
        raw_text=raw_text,
        s3_key=s3_key,
        upload_id=upload_id,
        yadisk_path=yadisk_path,
        original_filename=original_filename,
    )
