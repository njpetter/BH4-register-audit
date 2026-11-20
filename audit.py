"""Audit report tool for the BH-4 guard register CSV."""

import argparse
import csv
import re
import sys
from collections import defaultdict
from datetime import date, datetime, time
from pathlib import Path

DEFAULT_DATA_FILE = Path(__file__).resolve().parent / "data.csv"

# Thresholds for flagging entries (easy to tweak as needed)
MAX_STAY_MINUTES = 240  # 4 hours
LATE_ENTRY_HOUR = 19    # 7:00 PM (24-hour clock)

# Ordered regex rules to group mixed Hindi/English register purposes
CATEGORY_RULES = [
    ("Cooler/AC", re.compile(r"\b(cooler|ac|a/c|air\s*cond)\b", re.IGNORECASE)),
    ("Electrician", re.compile(r"\b(electrician|electric\w*|bijli|wiring)\b", re.IGNORECASE)),
    ("Carpenter", re.compile(r"\b(carpenter|badhai|furniture|wood)\b", re.IGNORECASE)),
    ("Plumber", re.compile(r"\b(plumber|plumb\w*|pipe|tap)\b", re.IGNORECASE)),
    ("Laundry", re.compile(r"\b(kapda|dhulai|dhobi|laundry|iron|press)\b", re.IGNORECASE)),
    ("Cleaning", re.compile(r"\b(safai|clean\w*|sweep\w*)\b", re.IGNORECASE)),
    ("Visitor", re.compile(r"\b(visitor|milne|guest|parent|friend|family)\b", re.IGNORECASE)),
    ("Other Maintenance", re.compile(r"\b(maintenance|mechanic|repair|tools|technician)\b", re.IGNORECASE)),
]


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    """Parse CLI arguments for CSV path, filters, and flagging thresholds."""
    parser = argparse.ArgumentParser(
        description="Audit and filter BH-4 guard register CSV entries."
    )
    parser.add_argument(
        "csv_file",
        nargs="?",
        default=None,
        help="Optional path to register CSV file (default: data.csv)",
    )
    parser.add_argument(
        "--file",
        dest="file_opt",
        default=None,
        help="Path to register CSV file (alternative to positional path)",
    )
    parser.add_argument(
        "--category",
        default=None,
        help="Case-insensitive partial category filter (e.g. cooler)",
    )
    parser.add_argument(
        "--room",
        default=None,
        help="Case-insensitive partial room filter (e.g. 1161)",
    )
    parser.add_argument(
        "--max-stay",
        type=int,
        default=MAX_STAY_MINUTES,
        help=f"Flag stays longer than N minutes (default: {MAX_STAY_MINUTES})",
    )
    parser.add_argument(
        "--late-hour",
        type=int,
        default=LATE_ENTRY_HOUR,
        help=f"Flag entries at/after hour 0-23 (default: {LATE_ENTRY_HOUR})",
    )

    args = parser.parse_args(argv)
    if args.csv_file is not None and args.file_opt is not None:
        parser.error("Specify the CSV path either positionally or with --file, not both.")
    if args.max_stay < 0:
        parser.error("--max-stay must be 0 or greater.")
    if not (0 <= args.late_hour <= 23):
        parser.error("--late-hour must be between 0 and 23.")

    raw_path = args.file_opt or args.csv_file
    args.csv_path = Path(raw_path) if raw_path else DEFAULT_DATA_FILE
    return args


def parse_date(raw_date: str) -> date | None:
    """Parse inconsistent register date formats (e.g. 02-11-26, 2/11/26) into a date."""
    cleaned = raw_date.strip().replace("/", "-").replace(".", "-")
    if not cleaned:
        return None
    for fmt in ("%d-%m-%y", "%d-%m-%Y", "%Y-%m-%d"):
        try:
            return datetime.strptime(cleaned, fmt).date()
        except ValueError:
            continue
    return None


def parse_time(raw_time: str) -> time | None:
    """Parse 12-hour or 24-hour clock strings into a time object."""
    cleaned = " ".join(raw_time.strip().split())
    if not cleaned:
        return None
    for fmt in ("%I:%M %p", "%I:%M%p", "%H:%M"):
        try:
            return datetime.strptime(cleaned, fmt).time()
        except ValueError:
            continue
    return None


def calculate_duration(
    visit_date: date | None, in_time: time | None, out_time: time | None
) -> tuple[int | None, bool]:
    """Return (duration_minutes, time_order_invalid). Does not wrap across midnight."""
    if in_time is None or out_time is None:
        return None, False
    base_date = visit_date or date(2000, 1, 1)
    in_dt = datetime.combine(base_date, in_time)
    out_dt = datetime.combine(base_date, out_time)
    if out_dt < in_dt:
        return None, True
    return int((out_dt - in_dt).total_seconds() // 60), False


def categorize_purpose(raw_purpose: str) -> str:
    """Map raw Hindi/English purpose text to a clean summary category."""
    text = raw_purpose.strip()
    for category, pattern in CATEGORY_RULES:
        if pattern.search(text):
            return category
    return "Other Maintenance"


def format_duration(minutes: float | int | None) -> str:
    """Format duration in minutes as 'Xh YYm' or 'Ym'."""
    if minutes is None:
        return "N/A"
    total_min = round(minutes)
    hours, mins = divmod(total_min, 60)
    if hours > 0:
        return f"{hours}h {mins:02d}m"
    return f"{mins}m"


def format_entry_time(parsed_time: time | None, status: str, raw_val: str) -> str:
    """Format a parsed time, or show MISSING / INVALID (<raw>) explicitly."""
    if status == "ok" and parsed_time is not None:
        return parsed_time.strftime("%I:%M %p").lstrip("0")
    if status == "invalid":
        return f"INVALID ({raw_val})"
    return "MISSING"


def parse_group_size(raw_size: str) -> tuple[int, str | None]:
    """Parse group size as a positive integer, returning (size, warning_reason)."""
    cleaned = raw_size.strip()
    if not cleaned:
        return 1, "Missing group_size (defaulted to 1)"
    try:
        size = int(cleaned)
    except ValueError:
        return 1, f"Invalid group_size '{cleaned}' (defaulted to 1)"
    if size <= 0:
        return 1, f"Invalid group_size '{cleaned}' (defaulted to 1)"
    return size, None


def load_entries(csv_path: Path) -> tuple[list[dict], list[dict]]:
    """Load register entries and collect explicit row-level data warnings."""
    entries: list[dict] = []
    warnings: list[dict] = []

    def add_warning(row_num: int, entry_id: str, reason: str) -> None:
        warnings.append({
            "row_num": row_num,
            "entry_id": entry_id or "-",
            "reason": reason,
        })

    with csv_path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.reader(handle)
        raw_headers = next(reader, None)
        if not raw_headers:
            return entries, warnings

        headers = [h.strip() for h in raw_headers]
        for raw_row in reader:
            row_num = reader.line_num
            if not raw_row or all(not cell.strip() for cell in raw_row):
                add_warning(row_num, "-", "Empty row skipped")
                continue

            if len(raw_row) > len(headers) and any(cell.strip() for cell in raw_row[len(headers):]):
                add_warning(
                    row_num,
                    raw_row[0].strip() if raw_row else "-",
                    f"Row has {len(raw_row)} columns (expected {len(headers)}); extra columns ignored",
                )

            row = {
                headers[i]: (raw_row[i] if i < len(raw_row) else "")
                for i in range(len(headers))
            }
            entry_id = (row.get("entry_id") or "").strip()

            raw_date = (row.get("date") or "").strip()
            visit_date = parse_date(raw_date)
            if not raw_date:
                date_str = "MISSING"
                add_warning(row_num, entry_id, "Missing date")
            elif visit_date is None:
                date_str = f"INVALID ({raw_date})"
                add_warning(row_num, entry_id, f"Unparseable date '{raw_date}'")
            else:
                date_str = visit_date.isoformat()

            in_time_raw = (row.get("in_time") or "").strip()
            in_time = parse_time(in_time_raw)
            if not in_time_raw:
                in_time_status = "missing"
                add_warning(row_num, entry_id, "Missing in_time")
            elif in_time is None:
                in_time_status = "invalid"
                add_warning(row_num, entry_id, f"Invalid in_time '{in_time_raw}'")
            else:
                in_time_status = "ok"

            out_time_raw = (row.get("out_time") or "").strip()
            out_time = parse_time(out_time_raw)
            if not out_time_raw:
                out_time_status = "missing"
            elif out_time is None:
                out_time_status = "invalid"
                add_warning(
                    row_num,
                    entry_id,
                    f"Invalid out_time '{out_time_raw}' (not counted as unclosed)",
                )
            else:
                out_time_status = "ok"

            duration_min, time_order_invalid = calculate_duration(visit_date, in_time, out_time)
            if time_order_invalid:
                add_warning(
                    row_num,
                    entry_id,
                    f"out_time '{out_time_raw}' is earlier than in_time '{in_time_raw}' (duration skipped)",
                )

            group_size, group_warning = parse_group_size(row.get("group_size") or "")
            if group_warning:
                add_warning(row_num, entry_id, group_warning)

            raw_purpose = (row.get("raw_purpose") or "").strip()
            raw_room = (row.get("room_no") or "").strip()

            entries.append({
                "row_num": row_num,
                "entry_id": entry_id or f"row:{row_num}",
                "raw_date": raw_date,
                "date": visit_date,
                "date_str": date_str,
                "affiliation": (row.get("affiliation") or "").strip() or "-",
                "contact_type": (row.get("contact_type") or "").strip() or "-",
                "group_size": group_size,
                "raw_purpose": raw_purpose or "-",
                "category": categorize_purpose(raw_purpose),
                "raw_room": raw_room,
                "room_no": raw_room or "-",
                "in_time": in_time,
                "in_time_raw": in_time_raw,
                "in_time_status": in_time_status,
                "out_time": out_time,
                "out_time_raw": out_time_raw,
                "out_time_status": out_time_status,
                "duration_min": duration_min,
                "is_unclosed": out_time_status == "missing",
                "is_closed": out_time_status == "ok" and duration_min is not None,
            })
    return entries, warnings


def filter_entries(
    entries: list[dict], category_filter: str | None, room_filter: str | None
) -> list[dict]:
    """Filter entries using case-insensitive partial matching on category and room."""
    result = entries
    if category_filter:
        needle = category_filter.strip().lower()
        result = [e for e in result if needle in e["category"].lower()]
    if room_filter:
        needle = room_filter.strip().lower()
        result = [e for e in result if e["raw_room"] and needle in e["raw_room"].lower()]
    return result


def print_table(
    headers: list[str],
    rows: list[list[str]],
    right_align: set[int] | None = None,
    footer: list[str] | None = None,
) -> None:
    """Print an ASCII-aligned table with optional right-aligned numeric columns and a footer row."""
    right_cols = right_align or set()
    all_rows = [headers] + rows + ([footer] if footer else [])
    widths = [max(len(str(row[i])) for row in all_rows) for i in range(len(headers))]

    def format_row(row: list[str]) -> str:
        cells = []
        for idx, val in enumerate(row):
            text = str(val)
            cells.append(text.rjust(widths[idx]) if idx in right_cols else text.ljust(widths[idx]))
        return "  ".join(cells)

    separator = "  ".join("-" * w for w in widths)
    print(format_row(headers))
    print(separator)
    for row in rows:
        print(format_row(row))
    if footer:
        print(separator)
        print(format_row(footer))


def print_header(
    entries: list[dict],
    csv_path: Path,
    max_stay: int,
    late_hour: int,
    category_filter: str | None,
    room_filter: str | None,
    warning_count: int,
) -> None:
    """Print overall audit summary, active filters, and alert thresholds."""
    dates = [e["date"] for e in entries if e["date"] is not None]
    date_range = f"{min(dates).isoformat()} to {max(dates).isoformat()}" if dates else "N/A"
    total_visits = len(entries)
    total_headcount = sum(e["group_size"] for e in entries)
    closed_count = sum(1 for e in entries if e["is_closed"])
    unclosed_count = sum(1 for e in entries if e["is_unclosed"])
    invalid_time_count = total_visits - closed_count - unclosed_count

    visit_breakdown = f"{closed_count} closed, {unclosed_count} unclosed"
    if invalid_time_count:
        visit_breakdown += f", {invalid_time_count} invalid time"

    active_filters = []
    if category_filter:
        active_filters.append(f"category~='{category_filter}'")
    if room_filter:
        active_filters.append(f"room~='{room_filter}'")

    print("=" * 72)
    print("BH-4 GUARD REGISTER AUDIT REPORT")
    print("=" * 72)
    print(f"Source file      : {csv_path.name}")
    if active_filters:
        print(f"Active filters   : {', '.join(active_filters)}")
    print(f"Date range       : {date_range}")
    print(f"Total visits     : {total_visits} ({visit_breakdown})")
    print(f"Total headcount  : {total_headcount} people (including +1/+2 groups)")
    print(f"Flag thresholds  : stay > {max_stay}m ({format_duration(max_stay)}), "
          f"entry >= {late_hour:02d}:00")
    if warning_count:
        print(f"Data warnings    : {warning_count} (see DATA WARNINGS below)")


def print_matching_entries(entries: list[dict]) -> None:
    """Print all matching entries when a category or room filter is active."""
    print()
    print(f"MATCHING ENTRIES: {len(entries)}")
    print("-" * 72)
    headers = ["ID", "Date", "Category", "Raw Purpose", "Affiliation", "Room", "Group", "In -> Out", "Stay"]
    rows = [
        [
            e["entry_id"],
            e["date_str"],
            e["category"],
            e["raw_purpose"],
            e["affiliation"],
            e["room_no"],
            str(e["group_size"]),
            (
                f"{format_entry_time(e['in_time'], e['in_time_status'], e['in_time_raw'])} -> "
                f"{format_entry_time(e['out_time'], e['out_time_status'], e['out_time_raw'])}"
            ),
            format_duration(e["duration_min"]),
        ]
        for e in entries
    ]
    print_table(headers, rows, right_align={0, 6, 8})


def print_unclosed_entries(entries: list[dict]) -> None:
    """Print entries missing an out_time (possible unlogged exit or still inside)."""
    unclosed = [e for e in entries if e["is_unclosed"]]
    print()
    print(f"UNCLOSED ENTRIES (Missing out_time): {len(unclosed)}")
    print("-" * 72)
    if not unclosed:
        print("None. Every entry has a recorded exit time.")
        return

    headers = ["ID", "Date", "Category", "Raw Purpose", "Affiliation", "Room", "Group", "In Time"]
    rows = [
        [
            e["entry_id"],
            e["date_str"],
            e["category"],
            e["raw_purpose"],
            e["affiliation"],
            e["room_no"],
            str(e["group_size"]),
            format_entry_time(e["in_time"], e["in_time_status"], e["in_time_raw"]),
        ]
        for e in unclosed
    ]
    print_table(headers, rows, right_align={0, 6})


def print_category_summary(entries: list[dict]) -> None:
    """Print grouped stats per category: visits, headcount, last visit, and average stay."""
    grouped = defaultdict(list)
    for entry in entries:
        grouped[entry["category"]].append(entry)

    sorted_categories = sorted(grouped.items(), key=lambda item: (-len(item[1]), item[0]))

    print()
    print("CATEGORY SUMMARY")
    print("-" * 72)

    headers = ["Category", "Visits", "Headcount", "Last Visit", "Avg Stay"]
    rows = []
    for category, items in sorted_categories:
        visits = len(items)
        headcount = sum(i["group_size"] for i in items)
        valid_dates = [i["date"] for i in items if i["date"] is not None]
        last_visit = max(valid_dates).isoformat() if valid_dates else "N/A"
        durations = [i["duration_min"] for i in items if i["duration_min"] is not None]
        avg_stay = format_duration(sum(durations) / len(durations)) if durations else "N/A"
        rows.append([category, str(visits), str(headcount), last_visit, avg_stay])

    all_dates = [e["date"] for e in entries if e["date"] is not None]
    all_durations = [e["duration_min"] for e in entries if e["duration_min"] is not None]
    footer = [
        "TOTAL",
        str(len(entries)),
        str(sum(e["group_size"] for e in entries)),
        max(all_dates).isoformat() if all_dates else "N/A",
        format_duration(sum(all_durations) / len(all_durations)) if all_durations else "N/A",
    ]
    print_table(headers, rows, right_align={1, 2, 4}, footer=footer)


def print_flagged_entries(entries: list[dict], max_stay: int, late_hour: int) -> None:
    """Flag unusually long stays and late entries based on configured thresholds."""
    flagged = []
    for e in entries:
        reasons = []
        if e["duration_min"] is not None and e["duration_min"] > max_stay:
            reasons.append("LONG STAY")
        if e["in_time"] is not None and e["in_time"].hour >= late_hour:
            reasons.append("LATE ENTRY")
        if reasons:
            flagged.append((e, ", ".join(reasons)))

    print()
    print(f"FLAGGED ENTRIES (Stay > {max_stay}m or Entry >= {late_hour:02d}:00): {len(flagged)}")
    print("-" * 72)
    if not flagged:
        print("None. No entries exceeded stay or late-entry thresholds.")
        return

    headers = ["ID", "Date", "Category", "Raw Purpose", "In -> Out", "Stay", "Flags"]
    rows = [
        [
            e["entry_id"],
            e["date_str"],
            e["category"],
            e["raw_purpose"],
            (
                f"{format_entry_time(e['in_time'], e['in_time_status'], e['in_time_raw'])} -> "
                f"{format_entry_time(e['out_time'], e['out_time_status'], e['out_time_raw'])}"
            ),
            format_duration(e["duration_min"]),
            reasons,
        ]
        for e, reasons in flagged
    ]
    print_table(headers, rows, right_align={0, 5})


def print_data_warnings(warnings: list[dict]) -> None:
    """Print explicit row-level data warnings for messy or corrupted rows."""
    if not warnings:
        return
    print()
    print(f"DATA WARNINGS: {len(warnings)}")
    print("-" * 72)
    headers = ["CSV Row", "ID", "Warning"]
    rows = [[str(w["row_num"]), w["entry_id"], w["reason"]] for w in warnings]
    print_table(headers, rows, right_align={0, 1})


def main() -> int:
    args = parse_args()
    csv_path: Path = args.csv_path
    if not csv_path.is_file():
        print(f"Error: CSV file not found at '{csv_path}'.", file=sys.stderr)
        return 1

    entries, warnings = load_entries(csv_path)
    if not entries:
        print(f"No valid entries found in '{csv_path}'.")
        print_data_warnings(warnings)
        return 1

    filtered = filter_entries(entries, args.category, args.room)
    if not filtered:
        print_header(
            filtered,
            csv_path,
            args.max_stay,
            args.late_hour,
            args.category,
            args.room,
            len(warnings),
        )
        print()
        print("No entries matched the given filter(s).")
        print_data_warnings(warnings)
        print()
        return 0

    print_header(
        filtered,
        csv_path,
        args.max_stay,
        args.late_hour,
        args.category,
        args.room,
        len(warnings),
    )
    if args.category or args.room:
        print_matching_entries(filtered)
    print_unclosed_entries(filtered)
    print_category_summary(filtered)
    print_flagged_entries(filtered, args.max_stay, args.late_hour)
    print_data_warnings(warnings)
    print()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
