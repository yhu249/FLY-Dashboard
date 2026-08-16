"""
FLY Initiative Data Cleaning Pipeline

This script cleans raw FLY datasets and creates analysis-ready datasets
for dashboard development.

Input:
    data/raw_data/

Output:
    outputs/

Cleaning principles:
    - Preserve original scores including valid zeros
    - Keep Student ID as string
    - Resolve attendance duplicates using Created Date
    - Create student-level attendance summaries
"""


import pandas as pd
import numpy as np
from pathlib import Path


# ==============================
# Define paths
# ==============================

BASE_PATH = Path(__file__).resolve().parent.parent

RAW_PATH = BASE_PATH / "data" / "raw_data"
OUTPUT_PATH = BASE_PATH / "outputs"

OUTPUT_PATH.mkdir(exist_ok=True)


# ==============================
# Helper functions
# ==============================

def clean_student_id(df):
    """
    Standardize Student ID as string.
    Student IDs contain both numerical IDs and manually created IDs starting with SI.
    """

    df = df.copy()

    if "Student ID" in df.columns:
        df["Student ID"] = (
            df["Student ID"]
            .astype("string")
            .str.strip()
        )

        # Remove missing IDs
        df = df[df["Student ID"].notna()]

    return df



# ==============================
# Clean Program Scores
# ==============================

def clean_scores(scores):

    scores = scores.copy()

    # Standardize Student ID
    scores = clean_student_id(scores)


    # Convert score columns to numeric
    numeric_cols = [
        "Score",
        "Total Score(Pre-assessment)",
        "Total Score(Post-assessment)"
    ]

    for col in numeric_cols:
        scores[col] = pd.to_numeric(
            scores[col],
            errors="coerce"
        )


    # Sponsor clarification:
    # Score = 0 means student did not participate.
    # Convert these values into missing values.

    zero_as_missing_cols = [
        "Score",
        "Total Score(Pre-assessment)",
        "Total Score(Post-assessment)"
    ]

    for col in zero_as_missing_cols:
        scores[col] = scores[col].replace(
            0,
            pd.NA
        )


    # Calculate assessment improvement
    # Only calculated when both pre and post scores exist.

    scores["Assessment Improvement"] = (
        scores["Total Score(Post-assessment)"]
        -
        scores["Total Score(Pre-assessment)"]
    )


    # Sort for consistency

    if "Program Name" in scores.columns:
        scores = scores.sort_values(
            by=[
                "Student ID",
                "Program Name"
            ]
        )


    return scores



# ==============================
# Clean Program Attendance
# ==============================

def clean_attendance(attendance):

    attendance = attendance.copy()


    attendance = clean_student_id(attendance)


    # Convert dates

    date_cols = [
        "Created Date",
        "Date"
    ]

    for col in date_cols:
        if col in attendance.columns:
            attendance[col] = pd.to_datetime(
                attendance[col],
                errors="coerce"
            )


    # Remove duplicate attendance records
    # Keep latest created record based on sponsor instruction

    attendance = (
        attendance
        .sort_values("Created Date")
        .drop_duplicates(
            subset=[
                "Student ID",
                "Date",
                "Volunteer Job: Volunteer Job Name"
            ],
            keep="last"
        )
    )


    # Create analysis flag
    # P = Present

    attendance["Present_Flag"] = (
        attendance["Attendance Status"]
        .eq("P")
        .astype(int)
    )


    return attendance



# ==============================
# Clean Student Demographics
# ==============================

def clean_demographics(demographics):

    demographics = demographics.copy()


    demographics = clean_student_id(
        demographics
    )


    # Convert created date

    if "Created Date" in demographics.columns:
        demographics["Created Date"] = pd.to_datetime(
            demographics["Created Date"],
            errors="coerce"
        )


    return demographics



# ==============================
# Main pipeline
# ==============================

def main():

    print("Loading raw data...")


    scores = pd.read_excel(
        RAW_PATH /
        "Brown 2025-2026 Program Scores by Student ID.xlsx"
    )


    attendance = pd.read_csv(
        RAW_PATH /
        "Brown Program Attendance Jul2025_Jun2026.csv"
    )


    demographics = pd.read_excel(
        RAW_PATH /
        "Brown Student Demographics.xlsx"
    )


    print("Cleaning datasets...")


    clean_scores_df = clean_scores(scores)

    clean_attendance_df = clean_attendance(
        attendance
    )

    clean_demographics_df = clean_demographics(
        demographics
    )


    # Save outputs

    clean_scores_df.to_csv(
        OUTPUT_PATH / "clean_scores.csv",
        index=False
    )

    clean_attendance_df.to_csv(
        OUTPUT_PATH / "clean_attendance.csv",
        index=False
    )


    clean_demographics_df.to_csv(
        OUTPUT_PATH / "clean_demographics.csv",
        index=False
    )


    # Attendance summary for dashboard

    attendance_valid = clean_attendance_df[
        clean_attendance_df["Attendance Status"] != "No Class"
    ]


    attendance_summary = (
        attendance_valid
        .groupby("Student ID")
        .agg(
            Total_Attendance_Records=(
                "Student ID",
                "count"
            ),
            Present_Count=(
                "Present_Flag",
                "sum"
            )
        )
        .reset_index()
    )

    attendance_summary["Attendance Rate"] = (
        attendance_summary["Present_Count"]
        /
        attendance_summary["Total_Attendance_Records"]
        *
        100
    )


    attendance_summary.to_csv(
        OUTPUT_PATH / "attendance_summary.csv",
        index=False
    )


    print(
        """
Cleaning pipeline completed successfully.

Output Summary:
Scores: {}
Attendance: {}
Demographics: {}
Attendance Summary: {}
""".format(
            clean_scores_df.shape,
            clean_attendance_df.shape,
            clean_demographics_df.shape,
            attendance_summary.shape
        )
    )



if __name__ == "__main__":
    main()