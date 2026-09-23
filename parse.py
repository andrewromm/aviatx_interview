"""Заготовка решения.

Нужно дописать parse_workbook(). Всё, что ниже неё, уже готово: сборка
итогового объекта по контракту, сортировки, вывод в stdout.

Менять готовую часть можно, но не обязательно.

    python parse.py status_report.xlsx > result.json
"""

import json
import sys

# запись таска и запись дефекта — обычные словари, поля описаны в задании
Task = dict
Defect = dict


def parse_workbook(path: str) -> tuple[str, list[Task], list[Defect], list[str]]:
    """Разобрать выгрузку.

    Вернуть кортеж из четырёх значений:

        aircraft        — строка с регистрационным номером борта
        tasks           — список записей, по одной на строку данных,
                          в порядке строк листа; поля см. в задании
        errors          — список найденных дефектов данных
        duplicate_codes — коды тасков, встречающиеся на листе больше раза

    Порядок внутри errors и duplicate_codes соблюдать не нужно —
    build_result() отсортирует сам.
    """
    raise NotImplementedError("здесь ваш код")


# ---------------------------------------------------------------------------
# Готовая часть: дописывать не нужно
# ---------------------------------------------------------------------------


def build_result(
    aircraft: str,
    tasks: list[Task],
    errors: list[Defect],
    duplicate_codes: list[str],
) -> dict:
    """Собирает итоговый объект по контракту."""
    hours_by_type: dict[str, float] = {}
    for task in tasks:
        if task["cw_hours"] is not None:
            total = hours_by_type.get(task["type"], 0) + task["cw_hours"]
            hours_by_type[task["type"]] = round(total, 2)

    return {
        "aircraft": aircraft,
        "tasks_total": len(tasks),
        "duplicate_codes": sorted(set(duplicate_codes)),
        "hours_by_type": dict(sorted(hours_by_type.items())),
        "errors": sorted(errors, key=lambda e: (e["row"], e["column"], e["raw"])),
        "tasks": tasks,
    }


def main() -> int:
    if len(sys.argv) != 2:
        print("использование: python parse.py status_report.xlsx", file=sys.stderr)
        return 2

    aircraft, tasks, errors, duplicate_codes = parse_workbook(sys.argv[1])
    result = build_result(aircraft, tasks, errors, duplicate_codes)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
