"""Удаляет шумовые письма из уже выполненного импорта mail.ru.

Шум = массовые рассылки, инстаграм-уведомления, трекинг звонков, отчёты по
сайтам. Полезной информации для калькулятора КНС они не несут.

Что делает:
1. Проходит letters_index.jsonl и parsed/*.json
2. Для каждого письма проверяет is_noise(sender, subject) из импорт-скрипта
3. Если шум — удаляет соответствующие raw/<slug>.eml,
   parsed/<slug>.json и attachments/<slug>/
4. Перезаписывает letters_index.jsonl без шумных строк
5. UID этих писем в state.json остаются — НЕ перезагрузим их при следующем
   запуске импорта (новый is_noise отсечёт их и без того, плюс state.json
   гарантирует что не качается повторно).

ВАЖНО: на самом ящике mail.ru НИЧЕГО не меняется. Cleanup только локальный.
"""
from __future__ import annotations

import json
import shutil
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
INBOX = REPO / "02_dataset" / "_inbox" / "mail_ru_imap"
RAW = INBOX / "raw"
PARSED = INBOX / "parsed"
ATTACH = INBOX / "attachments"
INDEX = INBOX / "letters_index.jsonl"

# Импортируем фильтр из самого импорт-скрипта — единый источник истины
sys.path.insert(0, str(REPO / "scripts"))
from mail_ru_imap_import import is_noise  # noqa: E402


def main(dry_run: bool = False) -> int:
    if not INDEX.exists():
        print(f"Нет {INDEX} — нечего чистить", file=sys.stderr)
        return 1

    kept: list[dict] = []
    noise_slugs: list[str] = []
    total = 0

    with INDEX.open(encoding="utf-8") as f:
        for line in f:
            total += 1
            d = json.loads(line)
            sender = d.get("from", "")
            subject = d.get("subject", "")
            if is_noise(sender, subject):
                noise_slugs.append(d["slug"])
            else:
                kept.append(d)

    print(f"Всего: {total}, шум: {len(noise_slugs)}, остаётся: {len(kept)}",
          file=sys.stderr)

    if dry_run:
        print("DRY RUN — ничего не удалено. Образцы шума:", file=sys.stderr)
        for slug in noise_slugs[:10]:
            print(f"  - {slug}", file=sys.stderr)
        return 0

    # Удаляем файлы
    deleted_eml = 0
    deleted_json = 0
    deleted_attach = 0
    for slug in noise_slugs:
        eml = RAW / f"{slug}.eml"
        if eml.exists():
            eml.unlink()
            deleted_eml += 1
        js = PARSED / f"{slug}.json"
        if js.exists():
            js.unlink()
            deleted_json += 1
        ad = ATTACH / slug
        if ad.exists() and ad.is_dir():
            shutil.rmtree(ad)
            deleted_attach += 1

    # Перезаписываем индекс
    backup = INDEX.with_suffix(".jsonl.before_cleanup")
    if not backup.exists():
        INDEX.rename(backup)
    else:
        INDEX.unlink()
    with INDEX.open("w", encoding="utf-8") as f:
        for d in kept:
            f.write(json.dumps(d, ensure_ascii=False) + "\n")

    print(
        f"Удалено: {deleted_eml} .eml, {deleted_json} .json, "
        f"{deleted_attach} папок вложений. Индекс перезаписан "
        f"(бэкап → {backup.name}).",
        file=sys.stderr,
    )
    return 0


if __name__ == "__main__":
    dry = "--dry-run" in sys.argv
    sys.exit(main(dry_run=dry))
