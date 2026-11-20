# BH-4 Guard Register Audit Tool

Built for **Satyajit Mishra** (Security Guard) at **Boys Hostel 4 (BH-4), IIIT Allahabad**, based on desk fieldwork observed on **November 20, 2026**.

At the BH-4 ground-floor desk, maintenance staff (cooler, AC, electrician, carpenter, plumber), laundry/cleaning workers, and visitors are all logged in a single paper register with mixed Hindi/English handwriting, inconsistent date formats, `+1`/`+2` group counts, and occasional missing exit times. `audit.py` reads an anonymized CSV transcript of those pages (`data.csv`) and prints a terminal audit report with unclosed entries, category summaries, flagged stays/late arrivals, and explicit warnings for corrupted rows.

## How to Run

Requires **Python 3.10+** (standard library only — no `pip install` needed).

Run from inside `BH4-register-audit/`:

```bash
# Full summary report on data.csv
python audit.py

# Filter by category (case-insensitive partial match)
python audit.py --category cooler

# Filter by room number
python audit.py --room 1161

# Override stay duration (minutes) and late-entry hour (0-23) thresholds
python audit.py --max-stay 120 --late-hour 17

# Run against a different CSV file (positional path or --file)
python audit.py --file path/to/other.csv
```

Default thresholds (`MAX_STAY_MINUTES = 240`, `LATE_ENTRY_HOUR = 19`) and keyword grouping rules (`CATEGORY_RULES`) are defined at the top of `audit.py` so they can be edited directly or overridden via CLI flags.

## Real Output

### Default report (`python audit.py`)

```text
========================================================================
BH-4 GUARD REGISTER AUDIT REPORT
========================================================================
Source file      : data.csv
Date range       : 2026-11-02 to 2026-11-20
Total visits     : 30 (29 closed, 1 unclosed)
Total headcount  : 43 people (including +1/+2 groups)
Flag thresholds  : stay > 240m (4h 00m), entry >= 19:00

UNCLOSED ENTRIES (Missing out_time): 1
------------------------------------------------------------------------
ID  Date        Category  Raw Purpose   Affiliation  Room  Group  In Time
--  ----------  --------  ------------  -----------  ----  -----  -------
29  2026-11-20  Laundry   Kapda Dhulai  Pipalgaon    -         1  7:10 PM

CATEGORY SUMMARY
------------------------------------------------------------------------
Category           Visits  Headcount  Last Visit  Avg Stay
-----------------  ------  ---------  ----------  --------
Cooler/AC              13         23  2026-11-16    2h 20m
Carpenter               5          6  2026-11-19    3h 28m
Electrician             4          6  2026-11-18    1h 05m
Cleaning                2          2  2026-11-20    3h 08m
Laundry                 2          2  2026-11-20    3h 30m
Other Maintenance       2          2  2026-11-18       30m
Plumber                 1          1  2026-11-17    2h 15m
Visitor                 1          1  2026-11-19    1h 05m
-----------------  ------  ---------  ----------  --------
TOTAL                  30         43  2026-11-20    2h 17m

FLAGGED ENTRIES (Stay > 240m or Entry >= 19:00): 8
------------------------------------------------------------------------
ID  Date        Category   Raw Purpose         In -> Out              Stay  Flags     
--  ----------  ---------  ------------------  -------------------  ------  ----------
 1  2026-11-02  Cleaning   Safai / General     10:30 AM -> 4:00 PM  5h 30m  LONG STAY 
 4  2026-11-03  Carpenter  Carpenter Tools     10:30 AM -> 5:10 PM  6h 40m  LONG STAY 
12  2026-11-12  Cooler/AC  Cooler              8:15 AM -> 12:45 PM  4h 30m  LONG STAY 
15  2026-11-13  Cooler/AC  Cooler              10:50 AM -> 4:15 PM  5h 25m  LONG STAY 
16  2026-11-13  Carpenter  Carpenter           9:15 AM -> 2:05 PM   4h 50m  LONG STAY 
20  2026-11-16  Cooler/AC  Cooler Maintenance  12:25 PM -> 5:10 PM  4h 45m  LONG STAY 
21  2026-11-16  Cooler/AC  Cooler              10:30 AM -> 5:10 PM  6h 40m  LONG STAY 
29  2026-11-20  Laundry    Kapda Dhulai        7:10 PM -> MISSING      N/A  LATE ENTRY
```

### Filtered lookup (`python audit.py --category cooler`)

```text
========================================================================
BH-4 GUARD REGISTER AUDIT REPORT
========================================================================
Source file      : data.csv
Active filters   : category~='cooler'
Date range       : 2026-11-02 to 2026-11-16
Total visits     : 13 (13 closed, 0 unclosed)
Total headcount  : 23 people (including +1/+2 groups)
Flag thresholds  : stay > 240m (4h 00m), entry >= 19:00

MATCHING ENTRIES: 13
------------------------------------------------------------------------
ID  Date        Category   Raw Purpose         Affiliation  Room  Group  In -> Out               Stay
--  ----------  ---------  ------------------  -----------  ----  -----  --------------------  ------
 2  2026-11-02  Cooler/AC  Cooler Tools        IIITA        1005      1  11:07 AM -> 11:32 AM     25m
 3  2026-11-02  Cooler/AC  Cooler Work         IIITA        -         3  4:00 PM -> 5:10 PM    1h 10m
 6  2026-11-05  Cooler/AC  Cooler Maintenance  IIITA        1245      1  10:30 AM -> 10:50 AM     20m
 7  2026-11-05  Cooler/AC  AC Work             IIITA        -         1  12:15 PM -> 1:10 PM      55m
10  2026-11-11  Cooler/AC  Cooler              IIITA        -         3  10:40 AM -> 12:55 PM  2h 15m
12  2026-11-12  Cooler/AC  Cooler              IIITA        -         1  8:15 AM -> 12:45 PM   4h 30m
13  2026-11-12  Cooler/AC  Cooler              IIITA        -         1  10:15 AM -> 12:00 PM  1h 45m
14  2026-11-13  Cooler/AC  Cooler              IIITA        -         1  10:50 AM -> 11:45 AM     55m
15  2026-11-13  Cooler/AC  Cooler              IIITA        -         1  10:50 AM -> 4:15 PM   5h 25m
18  2026-11-15  Cooler/AC  Cooler              IIITA        1318      3  11:30 AM -> 11:50 AM     20m
19  2026-11-16  Cooler/AC  Cooler              IIITA        -         2  11:40 AM -> 12:40 PM  1h 00m
20  2026-11-16  Cooler/AC  Cooler Maintenance  IIITA        -         3  12:25 PM -> 5:10 PM   4h 45m
21  2026-11-16  Cooler/AC  Cooler              IIITA        -         2  10:30 AM -> 5:10 PM   6h 40m

UNCLOSED ENTRIES (Missing out_time): 0
------------------------------------------------------------------------
None. Every entry has a recorded exit time.

CATEGORY SUMMARY
------------------------------------------------------------------------
Category   Visits  Headcount  Last Visit  Avg Stay
---------  ------  ---------  ----------  --------
Cooler/AC      13         23  2026-11-16    2h 20m
---------  ------  ---------  ----------  --------
TOTAL          13         23  2026-11-16    2h 20m

FLAGGED ENTRIES (Stay > 240m or Entry >= 19:00): 4
------------------------------------------------------------------------
ID  Date        Category   Raw Purpose         In -> Out              Stay  Flags    
--  ----------  ---------  ------------------  -------------------  ------  ---------
12  2026-11-12  Cooler/AC  Cooler              8:15 AM -> 12:45 PM  4h 30m  LONG STAY
15  2026-11-13  Cooler/AC  Cooler              10:50 AM -> 4:15 PM  5h 25m  LONG STAY
20  2026-11-16  Cooler/AC  Cooler Maintenance  12:25 PM -> 5:10 PM  4h 45m  LONG STAY
21  2026-11-16  Cooler/AC  Cooler              10:30 AM -> 5:10 PM  6h 40m  LONG STAY
```

## What It Gets Wrong / Shouldn't Be Trusted For

- **Still requires manual CSV entry:** `audit.py` does not read handwritten register photos. Someone still has to transcribe paper entries into CSV first, and transcription errors carry straight into the report.
- **Keyword rules can misclassify vague notes:** Purpose grouping uses simple regex keyword matching. Ambiguous, misspelled, or unfamiliar Hindi/English notes (for example, `"General"`, `"Kaam"`, or typos) can land in `Other Maintenance` or the wrong bucket.
- **Missing `out_time` does not prove someone is still inside:** An unclosed row often just means a worker or visitor left without signing out at the desk. Treat `UNCLOSED ENTRIES` as a check list, not a live occupancy count.
- **Overnight stays are not supported:** If `out_time` is earlier than `in_time`, the script skips the duration and prints a `DATA WARNING` instead of adding 24 hours. Measuring genuine stays past midnight would require an explicit `out_date` column.
- **Blank rooms limit `--room` lookups:** Many register entries leave `room_no` empty or say `"All Room"`, so `--room <number>` only finds visits where a room number was actually written down.

## Repository Structure

```text
BH4-register-audit/
├── README.md        # Usage guide, real output, and limitations
├── audit.py         # Pure standard-library Python CLI audit tool
├── data.csv         # 30 anonymized real entries from the BH-4 guard register
├── research.md      # Problem framing, existing alternatives, and reading notes
├── fieldwork.md     # Desk visit notes from BH-4 (Nov 20, 2026)
├── reflection.md    # Project reflection and takeaways
├── photos/          # Timestamped guard desk photos
└── ai-chats/        # AI collaboration logs
```

## Demo Video

https://drive.google.com/file/d/1MX77fzbVUzMwxNjZz0TslxCoVGemmt0V/view?usp=drive_link
