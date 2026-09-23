"""Сверка значений в result.json с эталоном.

Эталона в репозитории нет — только хеши каждой клетки (expected_hashes.json).
Поэтому скрипт может сказать «эта колонка разошлась в таких-то строках», но не
может показать, какое значение ожидалось.

Только стандартная библиотека.

    python selfcheck.py result.json
"""

import hashlib
import json
import os
import sys

SALT = "aviatx-interview"
HASHES = "expected_hashes.json"

ROOT_FIELDS = ["aircraft", "duplicate_codes", "hours_by_type"]
TASK_FIELDS = [
    "code",
    "type",
    "cw_date",
    "cw_date_note",
    "cw_hours",
    "cw_cycles",
    "next_due_date",
    "next_due_is_manual",
    "next_due_is_frozen",
    "primary_row",
    "related_rows",
]
ERROR_FIELDS = ["row", "column", "kind", "raw"]
SHOW = 8


def normalize(value):
    """Приводит значение к виду, не зависящему от мелочей представления.

    50.0 и 50 — одно и то же; 1.5699999999999998 и 1.57 — тоже: хвост float
    после перевода ЧЧ:ММ мы не считаем ошибкой.
    """
    if isinstance(value, bool):
        return value
    if isinstance(value, float):
        rounded = round(value, 2)
        return int(rounded) if rounded == int(rounded) else rounded
    if isinstance(value, list):
        return [normalize(item) for item in value]
    if isinstance(value, dict):
        return {key: normalize(value[key]) for key in sorted(value)}
    return value


def digest(name, value):
    payload = json.dumps(
        normalize(value), ensure_ascii=False, sort_keys=True, separators=(",", ":")
    )
    raw = f"{SALT}|{name}|{payload}".encode("utf-8")
    return hashlib.sha256(raw).hexdigest()[:16]


def error_digest(item):
    return digest("error", [item.get(field) for field in ERROR_FIELDS])


def build_hashes(expected):
    """Строит файл хешей из эталонного ответа. Используется генератором."""
    return {
        "version": 1,
        "tasks_total": expected["tasks_total"],
        "root": {name: digest(name, expected[name]) for name in ROOT_FIELDS},
        "tasks": {
            str(task["row"]): {
                field: digest(field, task[field]) for field in TASK_FIELDS
            }
            for task in expected["tasks"]
        },
        "errors": {
            "count": len(expected["errors"]),
            "entries": sorted(error_digest(item) for item in expected["errors"]),
        },
    }


def compare(actual, hashes):
    """Возвращает (строки отчёта, всё ли сошлось)."""
    report = []
    ok = True

    for name in ROOT_FIELDS:
        if digest(name, actual.get(name)) == hashes["root"][name]:
            report.append(f"OK   {name}")
        else:
            report.append(f"--   {name}: не совпадает")
            ok = False

    expected_rows = {int(row) for row in hashes["tasks"]}
    actual_by_row = {
        task["row"]: task
        for task in actual.get("tasks") or []
        if isinstance(task, dict) and isinstance(task.get("row"), int)
    }

    missing = sorted(expected_rows - set(actual_by_row))
    extra = sorted(set(actual_by_row) - expected_rows)
    if missing:
        report.append(f"--   нет строк ({len(missing)}): {missing[:SHOW]}")
        ok = False
    if extra:
        report.append(f"--   лишние строки ({len(extra)}): {extra[:SHOW]}")
        ok = False

    matched = sorted(expected_rows & set(actual_by_row))
    report.append(
        f"     строк сошлось по номеру: {len(matched)} из {len(expected_rows)}"
    )

    for field in TASK_FIELDS:
        bad = [
            row
            for row in matched
            if digest(field, actual_by_row[row].get(field))
            != hashes["tasks"][str(row)][field]
        ]
        if bad:
            report.append(
                f"--   {field}: расходится в {len(bad)} строках — {bad[:SHOW]}"
                + (" ..." if len(bad) > SHOW else "")
            )
            ok = False
        else:
            report.append(f"OK   {field}")

    wanted = set(hashes["errors"]["entries"])
    got = {
        error_digest(item)
        for item in (actual.get("errors") or [])
        if isinstance(item, dict)
    }
    found = len(wanted & got)
    report.append(f"     дефектов найдено: {found} из {hashes['errors']['count']}")
    if found != hashes["errors"]["count"]:
        ok = False
    if got - wanted:
        report.append(f"--   лишних записей в errors: {len(got - wanted)}")
        ok = False

    return report, ok


def main():
    if len(sys.argv) != 2:
        print("использование: python selfcheck.py result.json")
        return 2

    here = os.path.dirname(os.path.abspath(__file__))
    with open(os.path.join(here, HASHES), encoding="utf-8") as handle:
        hashes = json.load(handle)
    with open(sys.argv[1], encoding="utf-8") as handle:
        actual = json.load(handle)

    report, ok = compare(actual, hashes)
    print("\n".join(report))
    print()
    print("ВСЁ СОШЛОСЬ" if ok else "ЕСТЬ РАСХОЖДЕНИЯ — смотрите строки со знаком --")

    summary = os.environ.get("GITHUB_STEP_SUMMARY")
    if summary:
        with open(summary, "a", encoding="utf-8") as handle:
            handle.write("## Сверка значений\n\n```\n")
            handle.write("\n".join(report))
            handle.write("\n```\n")

    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
