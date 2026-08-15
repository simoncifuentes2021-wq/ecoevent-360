from datetime import datetime
from io import BytesIO
from types import SimpleNamespace

from openpyxl import Workbook

from app.services.logbook_excel_service import MAX_DATES, parse_xlsx


EVENT = SimpleNamespace(start_date=datetime(2026, 2, 20), end_date=datetime(2026, 3, 31))


def workbook(rows, *, header_row=3, activity_column=2, title="check"):
    book = Workbook()
    sheet = book.active
    sheet.title = title
    for row_offset, values in enumerate(rows, header_row):
        for column_offset, value in enumerate(values, activity_column):
            sheet.cell(row_offset, column_offset, value)
    target = BytesIO()
    book.save(target)
    return target.getvalue()


def parse(rows, filename="plan.xlsx", event=EVENT):
    return parse_xlsx(workbook(rows), filename, event)


def codes(result, kind="errors"):
    return {issue["code"] for issue in result[kind]}


def test_valid_matrix_creates_one_instance_per_date_not_per_x():
    result = parse([["Actividad", datetime(2026, 2, 23), datetime(2026, 2, 24), datetime(2026, 2, 25)],
                    ["Oficinas Bodega", "X", "x", None], ["Baños Bodega", "x", None, "X"],
                    ["Limpieza Lounge", None, "X", "x"]])
    assert result["errors"] == []
    assert result["instances_to_create"] == 3
    assert result["scheduled_items_count"] == 6
    assert [[item["title"] for item in day["activities"]] for day in result["days"]] == [
        ["Oficinas Bodega", "Baños Bodega"], ["Oficinas Bodega", "Limpieza Lounge"],
        ["Baños Bodega", "Limpieza Lounge"]]


def test_header_is_discovered_away_from_a1_and_blank_cells_are_ignored():
    result = parse([["Actividad", datetime(2026, 2, 23)], ["A", None]])
    assert "activity_header_missing" not in codes(result)
    assert "nothing_scheduled" in codes(result)


def test_invalid_extension_is_rejected_before_opening():
    result = parse_xlsx(b"not excel", "plan.csv", EVENT)
    assert codes(result) == {"invalid_extension"}


def test_corrupt_xlsx_is_rejected():
    assert codes(parse_xlsx(b"not excel", "plan.xlsx", EVENT)) == {"corrupt_workbook"}


def test_missing_activity_header():
    assert "activity_header_missing" in codes(parse([["Tarea", datetime(2026, 2, 23)], ["A", "X"]]))


def test_duplicate_activity_is_not_merged_silently():
    result = parse([["Actividad", datetime(2026, 2, 23)], ["A", "X"], [" a ", "X"]])
    assert "duplicate_activity" in codes(result, "warnings")
    assert result["scheduled_items_count"] == 2


def test_duplicate_date_is_error():
    result = parse([["Actividad", datetime(2026, 2, 23), datetime(2026, 2, 23)], ["A", "X", "X"]])
    assert "duplicate_date" in codes(result)


def test_scheduled_blank_activity_is_error():
    assert "missing_activity" in codes(parse([["Actividad", datetime(2026, 2, 23)], [None, "X"]]))


def test_unexpected_value_reports_coordinates_and_value():
    result = parse([["Actividad", datetime(2026, 2, 23)], ["A", "yes"]])
    issue = next(item for item in result["warnings"] if item["code"] == "unexpected_value")
    assert (issue["row"], issue["column"], issue["value"]) == (4, 3, "yes")


def test_date_outside_event():
    assert "date_outside_event" in codes(parse([["Actividad", datetime(2027, 1, 1)], ["A", "X"]]))


def test_day_month_year_is_inferred_from_event():
    result = parse([["Actividad", "23-feb"], ["A", "X"]])
    assert result["days"][0]["date"] == "2026-02-23"


def test_ambiguous_day_month_is_rejected():
    event = SimpleNamespace(start_date=datetime(2025, 1, 1), end_date=datetime(2026, 12, 31))
    assert "invalid_date" in codes(parse([["Actividad", "23-feb"], ["A", "X"]], event=event))


def test_completely_empty_date_is_reported():
    result = parse([["Actividad", datetime(2026, 2, 23), datetime(2026, 2, 24)], ["A", "X", None]])
    assert "empty_date" in codes(result, "warnings")


def test_limits_are_enforced():
    headers = ["Actividad"] + [datetime(2026, 2, 23)] * (MAX_DATES + 1)
    assert "limits_exceeded" in codes(parse([headers, ["A"] + ["X"] * (MAX_DATES + 1)]))


def test_formula_is_not_executed_or_treated_as_x():
    result = parse([["Actividad", datetime(2026, 2, 23)], ["A", '=IF(1=1,"X","")']])
    assert result["scheduled_items_count"] == 0
