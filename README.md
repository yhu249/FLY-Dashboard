# FLY Program Dashboard

This repo turns Salesforce exports into a cleaned dataset and an interactive
dashboard for the Financial Literacy Youth (FLY) program.

It has two steps:
1. **Clean the data** — `scripts/data_cleaning.py` reads your raw exports and
   produces tidy CSV files in `outputs/`.
2. **View the dashboard** — `app.py` reads those cleaned CSVs and displays
   charts in your web browser.

This guide focuses on what you'll actually need later: **swapping in next
year's data (FY26-27, etc.)** — where files go, what must not change, and
what to do if a new export looks different from this year's.

---

## 1. One-time setup (only do this once)

### 1.1 Install Python
If you don't already have Python installed, download it from
[python.org/downloads](https://www.python.org/downloads/) (version 3.10 or
newer). On Windows, check the box **"Add Python to PATH"** during install.

### 1.2 Open a terminal in this folder
- **Mac**: Open the "Terminal" app, type `cd ` (with a space), then drag this
  folder into the terminal window and press Enter.
- **Windows**: Open this folder in File Explorer, click the address bar,
  type `cmd`, and press Enter.

### 1.3 Install the required packages
```
pip install -r requirements.txt
```
Only needed once per computer.

---

## 2. Folder structure — and how the script finds your files

```
FLY-Dashboard/                <- put this whole folder anywhere on your computer
├── data/
│   └── raw_data/             <- your raw Salesforce exports go here
├── outputs/                  <- cleaned files appear here automatically
├── scripts/
│   └── data_cleaning.py
├── app.py
├── requirements.txt
└── README.md
```

**You do not need to edit any file path or line of code to use this on your
own computer.** The script automatically figures out where it lives and
looks for `data/raw_data/` right next to it, no matter where you put the
whole `FLY-Dashboard` folder (Desktop, Documents, an external drive, etc.).
Just keep the folders nested exactly as shown above.

### If you ever need to point it at a different raw-data location
This is optional and most people will never need it — skip unless, for
example, you want your raw files to live in a shared Dropbox/Google Drive
folder instead of inside `FLY-Dashboard/data/raw_data/`.

Open `scripts/data_cleaning.py` in a plain text editor (Notepad, TextEdit in
plain-text mode, or VS Code) and find these two lines near the top:

```python
RAW_PATH = BASE_PATH / "data" / "raw_data"
OUTPUT_PATH = BASE_PATH / "outputs"
```

Replace `RAW_PATH` with the exact folder path where your files live. For example:

```python
# Mac / macOS example:
RAW_PATH = Path("/Users/yourname/Dropbox/FLY Data/raw_data")

# Windows example:
RAW_PATH = Path(r"C:\Users\yourname\Dropbox\FLY Data\raw_data")
```
Save the file after editing. `OUTPUT_PATH` can be changed the same way if
you want the cleaned CSVs saved somewhere else.

---

## 3. Required files — every time you refresh the data

**All three files below are required.** The script reads all three before
it does anything else — if even one is missing or misnamed, the script
stops immediately with an error and **nothing gets cleaned, not even
partially**. So before running anything, confirm all three are sitting in
`data/raw_data/`:

| # | Required file name (must match exactly) | Format | Feeds into |
|---|---|---|---|
| 1 | `Brown 2025-2026 Program Scores by Student ID.xlsx` | Excel (.xlsx) | Learning outcomes, module performance, quiz scores |
| 2 | `Brown Program Attendance Jul2025_Jun2026.csv` | CSV (.csv) | Attendance analysis, attendance trend |
| 3 | `Brown Student Demographics.xlsx` | Excel (.xlsx) | Equity analysis (gender/age/ethnicity/income breakdowns) |

**Watch out for automatic renaming.** Files downloaded from Slack, email,
or a browser sometimes get their spaces swapped for underscores (e.g.
`Brown_Student_Demographics.xlsx`). Rename the file back to match the table
above exactly — spaces, not underscores — or the script won't find it.

**File name will change every year.** File #2's name contains the date
range (`Jul2025_Jun2026`). When FY26-27 data arrives, the sponsor's export
will likely be named `..._Jul2026_Jun2027.csv` instead. **You must rename it
back to the exact name in the table above** (or ask your analyst to update
that filename inside `data_cleaning.py`) — the script looks for that exact
string and won't auto-detect a new date range on its own.

---

## 4. Required columns — what to check if next year's file "looks different"

The script matches columns **by their exact header name**, not by position.
If Salesforce changes a column title, adds/removes a column, or the export
template changes next year, the script will fail at whichever column it
can't find.

**Before running a new year's data through the pipeline, open each file and
compare its header row (row 1) against the checklist below.** This is just
eyeballing column titles — no coding needed.

### File 1: Program Scores (`...Program Scores by Student ID.xlsx`)
Must contain these exact column headers:
`Student ID`, `Score`, `Assignment`, `Status`, `Program Name`, `Program Code`,
`Total Score(Pre-assessment)`, `Total Score(Post-assessment)`,
and the 12 module pre/post columns (Earning Income, Investing, Managing
Credit, Saving, Spending, Managing Risk — one Pre and one Post column each).

### File 2: Program Attendance (`...Program Attendance...csv`)
Must contain: `Student ID`, `Created Date`, `Date`, `Attendance Status`,
`Volunteer Job: Volunteer Job Name`, `Program Name`.

### File 3: Student Demographics (`...Student Demographics.xlsx`)
Must contain: `Student ID`, `Age Group`, `Ethnicity`, `Gender`,
`Household Annual Income`, `Created Date`.

### What to do if a header doesn't match
- **If it's just a wording difference** (e.g. `StudentID` instead of
  `Student ID`, or a trailing space in a column name): open the raw file in
  Excel and rename the header cell to match the checklist exactly, then
  save and re-run.
- **If a whole column is missing or genuinely new**: don't try to fix the
  script yourself — send the new file to your analyst so the column mapping
  in `data_cleaning.py` can be updated to match. Trying to force-fit
  mismatched columns will silently produce wrong numbers rather than an
  obvious error.

---

## 5. Running the cleaning script

```
python scripts/data_cleaning.py
```
*(Mac: use `python3` instead of `python` if the first doesn't work.)*

Success looks like:
```
Cleaning pipeline completed successfully.

Output Summary:
Scores: (5134, 26)
Attendance: (83645, 10)
Demographics: (1230, 13)
Attendance Summary: (1115, 4)
```

If you see a red error instead, it's almost always Section 3 (a missing/
misnamed file) or Section 4 (a renamed/missing column) — check those first.

---

## 6. Running the dashboard

```
streamlit run app.py
```
A browser tab opens automatically at `http://localhost:8501`. If not, copy
that address into your browser manually. Press `Ctrl + C` in the terminal to
stop it.

---

## 7. Full refresh workflow (do this every time you get new data)

1. Open the new export files and check their column headers against
   Section 4.
2. Rename each file to exactly match the names in Section 3 (fix any
   underscore/date issues).
3. Drop them into `data/raw_data/`, replacing the old versions.
4. Run `python scripts/data_cleaning.py` — confirm you see the success
   message with row counts that look reasonable (not 0 rows, no errors).
5. Run `streamlit run app.py` and spot-check a couple of charts against
   numbers you already know, to sanity-check the refresh.

---

## Troubleshooting

| Problem | Likely cause | Where to look |
|---|---|---|
| `FileNotFoundError` | A raw file is missing, misnamed, or has underscores instead of spaces | Section 3 |
| `KeyError: 'Student ID'` (or similar column name) | The raw export is missing that exact column, or it was renamed by Salesforce | Section 4 |
| Script runs, but row counts look way too low (e.g. `(0, 26)`) | Wrong file was dropped in, or the file is a different sheet/format than expected | Section 3 & 4 |
| Dashboard opens but shows blank/empty charts | The cleaning script wasn't run first, or `outputs/` is empty | Run Section 5 before Section 6 |
| `ModuleNotFoundError` | Packages weren't installed | Re-run Section 1.3 |

If you hit an error you can't resolve, copy the full red error message from
the terminal and send it along with the raw file's header row — that's
usually enough to pinpoint exactly what changed.
