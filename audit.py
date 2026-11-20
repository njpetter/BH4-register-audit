"""Audit report tool for the BH-4 guard register CSV."""

import csv
import re
import sys
from collections import defaultdict
from datetime import date, datetime, time, timedelta
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


def calculate_duration(visit_date: date | None, in_time: time | None, out_time: time | None) -> int | None:
    """Return visit duration in minutes, or None if either timestamp is missing."""
    if in_time is None or out_time is None:
        return None
    base_date = visit_date or date(2000, 1, 1)
    in_dt = datetime.combine(base_date, in_time)
    out_dt = datetime.combine(base_date, out_time)
    if out_dt < in_dt:
        # Handle visits that cross midnight
        out_dt += timedelta(days=1)
    return int((out_dt - in_dt).total_seconds() // 60)


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


def format_time(t: time | None, fallback: str = "MISSING") -> str:
    """Format a time as '7:10 PM' without a leading zero."""
    if t is None:
        return fallback
    return t.strftime("%I:%M %p").lstrip("0")


def parse_group_size(raw_size: str) -> int:
    """Parse group size as a positive integer, defaulting to 1 when blank or invalid."""
    try:
        size = int(raw_size.strip())
        return size if size > 0 else 1
    except ValueError:
        return 1


def load_entries(csv_path: Path) -> list[dict]:
    """Load and normalize register entries from a CSV file."""
    entries = []
    with csv_path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            raw_date = (row.get("date") or "").strip()
            visit_date = parse_date(raw_date)
            in_time = parse_time(row.get("in_time") or "")
            out_time = parse_time(row.get("out_time") or "")
            raw_purpose = (row.get("raw_purpose") or "").strip()

            entries.append({
                "entry_id": (row.get("entry_id") or "").strip(),
                "raw_date": raw_date,
                "date": visit_date,
                "date_str": visit_date.isoformat() if visit_date else (raw_date or "UNKNOWN"),
                "affiliation": (row.get("affiliation") or "").strip() or "-",
                "contact_type": (row.get("contact_type") or "").strip() or "-",
                "group_size": parse_group_size(row.get("group_size") or ""),
                "raw_purpose": raw_purpose or "-",
                "category": categorize_purpose(raw_purpose),
                "room_no": (row.get("room_no") or "").strip() or "-",
                "in_time": in_time,
                "out_time": out_time,
                "duration_min": calculate_duration(visit_date, in_time, out_time),
            })
    return entries


def print_table(headers: list[str], rows: list[list[str]], right_align: set[int] | None = None, footer: list[str] | None = None) -> None:
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


def print_header(entries: list[dict], csv_path: Path) -> None:
    """Print overall audit summary and active alert thresholds."""
    dates = [e["date"] for e in entries if e["date"] is not None]
    date_range = f"{min(dates).isoformat()} to {max(dates).isoformat()}" if dates else "N/A"
    total_visits = len(entries)
    total_headcount = sum(e["group_size"] for e in entries)
    unclosed_count = sum(1 for e in entries if e["out_time"] is None)
    closed_count = total_visits - unclosed_count

    print("=" * 72)
    print("BH-4 GUARD REGISTER AUDIT REPORT")
    print("=" * 72)
    print(f"Source file      : {csv_path.name}")
    print(f"Date range       : {date_range}")
    print(f"Total visits     : {total_visits} ({closed_count} closed, {unclosed_count} unclosed)")
    print(f"Total headcount  : {total_headcount} people (including +1/+2 groups)")
    print(f"Flag thresholds  : stay > {MAX_STAY_MINUTES}m ({format_duration(MAX_STAY_MINUTES)}), "
          f"entry >= {LATE_ENTRY_HOUR:02d}:00")


def print_unclosed_entries(entries: list[dict]) -> None:
    """Print entries missing an out_time (possible unlogged exit or still inside)."""
    unclosed = [e for e in entries if e["out_time"] is None]
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
            format_time(e["in_time"]),
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


def print_flagged_entries(entries: list[dict]) -> None:
    """Flag unusually long stays and late entries based on configured thresholds."""
    flagged = []
    for e in entries:
        reasons = []
        if e["duration_min"] is not None and e["duration_min"] > MAX_STAY_MINUTES:
            reasons.append("LONG STAY")
        if e["in_time"] is not None and e["in_time"].hour >= LATE_ENTRY_HOUR:
            reasons.append("LATE ENTRY")
        if reasons:
            flagged.append((e, ", ".join(reasons)))

    print()
    print(f"FLAGGED ENTRIES (Stay > {MAX_STAY_MINUTES}m or Entry >= {LATE_ENTRY_HOUR:02d}:00): {len(flagged)}")
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
            f"{format_time(e['in_time'])} -> {format_time(e['out_time'])}",
            format_duration(e["duration_min"]),
            reasons,
        ]
        for e, reasons in flagged
    ]
    print_table(headers, rows, right_align={0, 5})


def main() -> int:
    csv_path = Path(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT_DATA_FILE
    if not csv_path.is_file():
        print(f"Error: CSV file not found at '{csv_path}'.", file=sys.stderr)
        return 1

    entries = load_entries(csv_path)
    if not entries:
        print(f"No entries found in '{csv_path}'.")
        return 1

    print_header(entries, csv_path)
    print_unclosed_entries(entries)
    print_category_summary(entries)
    print_flagged_entries(entries)
    print()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
