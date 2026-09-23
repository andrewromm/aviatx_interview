"""Проверка СТРУКТУРЫ result.json. Значения не проверяются.

Только стандартная библиотека, ничего ставить не нужно.

    python validate.py result.json
"""

import json
import re
import sys

DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
ERROR_KINDS = {
    "invalid_minutes",
    "number_as_text",
    "self_reference",
    "ambiguous_reference",
    "unknown_reference",
}
NOTE_VALUES = {"EFF", "EBT", "NA", None}

ROOT_FIELDS = {
    "aircraft": str,
    "tasks_total": int,
    "duplicate_codes": list,
    "hours_by_type": dict,
    "errors": list,
    "tasks": list,
}

TASK_FIELDS = {
    "row": (int,),
    "code": (str,),
    "type": (str,),
    "cw_date": (str, type(None)),
    "cw_date_note": (str, type(None)),
    "cw_hours": (int, float, type(None)),
    "cw_cycles": (int, type(None)),
    "next_due_date": (str, type(None)),
    "next_due_is_manual": (bool,),
    "next_due_is_frozen": (bool,),
    "primary_row": (int, type(None)),
    "related_rows": (list,),
}


def check(data) -> list[str]:
    problems: list[str] = []

    if not isinstance(data, dict):
        return ["корень должен быть объектом"]

    for name, expected in ROOT_FIELDS.items():
        if name not in data:
            problems.append(f"нет обязательного поля {name!r}")
        elif not isinstance(data[name], expected) or isinstance(data[name], bool):
            problems.append(
                f"{name!r}: ожидался {expected.__name__}, получен "
                f"{type(data[name]).__name__}"
            )
    for name in set(data) - set(ROOT_FIELDS):
        problems.append(f"лишнее поле в корне: {name!r}")
    if problems:
        return problems

    non_strings = [
        code for code in data["duplicate_codes"] if not isinstance(code, str)
    ]
    if non_strings:
        problems.append(
            f"duplicate_codes: элементы должны быть строками — {non_strings}"
        )
    elif data["duplicate_codes"] != sorted(set(data["duplicate_codes"])):
        problems.append("duplicate_codes должен быть отсортирован и без повторов")

    for key, value in data["hours_by_type"].items():
        if not isinstance(key, str):
            problems.append(f"hours_by_type: ключ не строка — {key!r}")
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            problems.append(f"hours_by_type[{key!r}] должен быть числом")
    if list(data["hours_by_type"]) != sorted(data["hours_by_type"]):
        problems.append("ключи hours_by_type должны быть отсортированы")

    error_fields = {"row", "column", "kind", "raw"}
    sortable = True
    for index, item in enumerate(data["errors"]):
        where = f"errors[{index}]"
        if not isinstance(item, dict):
            problems.append(f"{where}: должен быть объектом")
            sortable = False
            continue
        for field in error_fields:
            if field not in item:
                problems.append(f"{where}: нет поля {field!r}")
                sortable = False
        if set(item) - error_fields:
            problems.append(f"{where}: лишние поля {sorted(set(item) - error_fields)}")
        if item.get("kind") not in ERROR_KINDS:
            problems.append(
                f"{where}: kind={item.get('kind')!r} вне списка {sorted(ERROR_KINDS)}"
            )
        if not isinstance(item.get("row"), int) or isinstance(item.get("row"), bool):
            problems.append(f"{where}: row должен быть целым")
            sortable = False
        for field in ("column", "raw"):
            if field in item and not isinstance(item[field], str):
                problems.append(f"{where}: {field} должен быть строкой")
                sortable = False

    # сортировку проверяем только когда типы полей уже в порядке:
    # на смешанных типах сравнение само упало бы с TypeError
    if sortable:
        keys = [(e["row"], e["column"], e["raw"]) for e in data["errors"]]
        if keys != sorted(keys):
            problems.append("errors должен быть отсортирован по (row, column, raw)")

    if not data["tasks"]:
        problems.append("tasks пуст — в файле есть строки с данными")
    if data["tasks_total"] != len(data["tasks"]):
        problems.append(
            f"tasks_total={data['tasks_total']}, а в tasks {len(data['tasks'])} записей"
        )

    rows = []
    for index, task in enumerate(data["tasks"]):
        where = f"tasks[{index}]"
        if not isinstance(task, dict):
            problems.append(f"{where}: должен быть объектом")
            continue
        for field, types in TASK_FIELDS.items():
            if field not in task:
                problems.append(f"{where}: нет поля {field!r}")
                continue
            value = task[field]
            if bool not in types and isinstance(value, bool):
                problems.append(f"{where}.{field}: булево значение недопустимо")
            elif not isinstance(value, types):
                names = "/".join(t.__name__ for t in types)
                problems.append(
                    f"{where}.{field}: ожидался {names}, получен {type(value).__name__}"
                )
        for field in set(task) - set(TASK_FIELDS):
            problems.append(f"{where}: лишнее поле {field!r}")

        for field in ("cw_date", "next_due_date"):
            value = task.get(field)
            if isinstance(value, str) and not DATE_RE.match(value):
                problems.append(
                    f"{where}.{field}: ожидался формат YYYY-MM-DD, получено {value!r}"
                )
        if task.get("cw_date_note") not in NOTE_VALUES:
            problems.append(
                f"{where}.cw_date_note: {task.get('cw_date_note')!r} "
                f"вне списка EFF/EBT/NA/null"
            )
        if isinstance(task.get("related_rows"), list):
            for item in task["related_rows"]:
                if isinstance(item, bool) or not isinstance(item, int):
                    problems.append(
                        f"{where}.related_rows: элемент не целое число — {item!r}"
                    )
        if isinstance(task.get("row"), int):
            rows.append(task["row"])

    if rows:
        if rows != sorted(rows):
            problems.append("tasks должен идти в порядке возрастания row")
        if len(rows) != len(set(rows)):
            problems.append("номера строк в tasks повторяются")

    return problems


def main() -> int:
    if len(sys.argv) != 2:
        print("использование: python validate.py result.json")
        return 2
    with open(sys.argv[1], encoding="utf-8") as handle:
        data = json.load(handle)

    problems = check(data)
    if not problems:
        print("OK — структура соответствует схеме")
        print(f"   записей в tasks: {len(data['tasks'])}")
        print(f"   записей в errors: {len(data['errors'])}")
        return 0

    print(f"НЕ ПРОШЛО — {len(problems)} замечаний по структуре:")
    for problem in problems[:40]:
        print(f"  - {problem}")
    if len(problems) > 40:
        print(f"  ... и ещё {len(problems) - 40}")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
