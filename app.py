import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go

st.set_page_config(page_title="FLY Program Dashboard", layout="wide", page_icon="💙")

# ----------------------------------------------------------------------------
# THEME
# ----------------------------------------------------------------------------
BLUE_DARK = "#0B3D91"
BLUE_MAIN = "#1f77b4"
BLUE_MID = "#4C9BE8"
BLUE_LIGHT = "#A9CCE3"
BLUE_PALE = "#EAF2FB"
GRAY = "#6b7280"
BLUE_SCALE = [BLUE_DARK, BLUE_MAIN, BLUE_MID, "#7FB3E8", BLUE_LIGHT, "#CFE3F5"]

px.defaults.color_discrete_sequence = BLUE_SCALE
px.defaults.template = "plotly_white"

st.markdown(f"""
<style>
    .stMetric {{
        background-color: {BLUE_PALE};
        border: 1px solid {BLUE_LIGHT};
        border-radius: 10px;
        padding: 12px 10px 6px 10px;
    }}
    h1, h2, h3 {{ color: {BLUE_DARK}; }}
    .caption-note {{ color: {GRAY}; font-size: 0.85rem; }}
</style>
""", unsafe_allow_html=True)


# ----------------------------------------------------------------------------
# DATA LOADING & CLEANING
# ----------------------------------------------------------------------------
def norm_id(series: pd.Series) -> pd.Series:
    """Normalize Student ID to a clean string (handles float-read numeric IDs
    like 100075.0 as well as manual 'SI####' IDs)."""
    return (
        series.astype(str)
        .str.strip()
        .str.replace(r"\.0$", "", regex=True)
        .replace({"nan": np.nan})
    )


# The 6 pre/post assessment topics live in inconsistently-named columns
# (note the stray space before "Assessment" in two of them). Mapping them
# explicitly avoids accidentally sweeping in the "Total ... Score" columns,
# which is what produced the broken/empty categories in the old chart.
MODULE_COLS = {
    "Earning Income": ("Pre -Assessment Earning Income Score", "Post-Assessment Earning Income Score"),
    "Investing": ("Pre -Assessment Investing Score", "Post-Assessment Investing Score"),
    "Managing Credit": ("Pre-Assessment Managing Credit Score", "Post-Assessment Managing Credit Score"),
    "Saving": ("Pre-Assessment Saving Score", "Post-Assessment Saving Score"),
    "Spending": ("Pre-Assessment Spending Score", "Post-Assessment Spending Score"),
    "Managing Risk": ("Pre-Assessment Managing Risk Score", "Post-Assessment Managing Risk Score"),
}


@st.cache_data
def load_data():
    scores_raw = pd.read_csv("outputs/clean_scores.csv", low_memory=False)
    attendance_summary = pd.read_csv("outputs/attendance_summary.csv")
    demographics = pd.read_csv("outputs/clean_demographics.csv", low_memory=False)

    scores_raw["Student ID"] = norm_id(scores_raw["Student ID"])
    attendance_summary["Student ID"] = norm_id(attendance_summary["Student ID"])
    demographics["Student ID"] = norm_id(demographics["Student ID"])
    demographics = demographics.drop_duplicates(subset="Student ID")

    # --- IMPORTANT: clean_scores.csv is at the (Student, Program, Assignment)
    # grain -- one row per quiz/lesson. The "Total Score(Pre/Post-assessment)"
    # and module pre/post columns are stored at the (Student, Program) grain
    # and are simply repeated on every assignment row for that enrollment.
    # If we don't de-duplicate first, every chart built on those columns
    # over-counts the same student 3-20x (this was the bug behind the old
    # "Module Performance" chart). We build one de-duplicated table for
    # enrollment-level analysis (attendance %, total/module scores) and
    # keep the raw table only for the assignment-level quiz scores.
    enrollment = scores_raw.drop_duplicates(subset=["Student ID", "Program Name"]).copy()

    enrollment["Assessment Improvement"] = (
        enrollment["Total Score(Post-assessment)"] - enrollment["Total Score(Pre-assessment)"]
    )

    return scores_raw, enrollment, attendance_summary, demographics


scores_raw, enrollment, attendance, demographics = load_data()

# ----------------------------------------------------------------------------
# SIDEBAR FILTERS
# ----------------------------------------------------------------------------
st.sidebar.header("Filters")

status_options = sorted(enrollment["Status"].dropna().unique().tolist())
default_status = [s for s in status_options if s in ("Completed", "Confirmed")]
selected_status = st.sidebar.multiselect("Enrollment status", status_options, default=default_status)

program_options = sorted(enrollment["Program Name"].dropna().unique().tolist())
selected_programs = st.sidebar.multiselect("Program(s)", program_options, default=[])

st.sidebar.caption(
    "Status defaults to Completed/Confirmed only, excluding Canceled/No-Show/Prospect "
    "records that were never really delivered."
)

enr_f = enrollment.copy()
if selected_status:
    enr_f = enr_f[enr_f["Status"].isin(selected_status)]
if selected_programs:
    enr_f = enr_f[enr_f["Program Name"].isin(selected_programs)]

scores_f = scores_raw[scores_raw["Student ID"].isin(enr_f["Student ID"])]
if selected_programs:
    scores_f = scores_f[scores_f["Program Name"].isin(selected_programs)]

att_f = attendance[attendance["Student ID"].isin(enr_f["Student ID"])]

# ----------------------------------------------------------------------------
# HEADER + KPIs
# ----------------------------------------------------------------------------
st.title("Financial Literacy Youth (FLY) Program Dashboard")
st.caption("Fiscal Year 2025–2026 (Jul 2025 – Jun 2026)")

valid_pairs = enr_f.dropna(subset=["Total Score(Pre-assessment)", "Total Score(Post-assessment)"])

c1, c2, c3, c4, c5 = st.columns(5)
c1.metric("Students Served", f"{demographics['Student ID'].nunique():,}")
c2.metric("Enrollments (Student × Program)", f"{enr_f.shape[0]:,}")
c3.metric("Avg Attendance Rate", f"{att_f['Attendance Rate'].mean():.1f}%")
c4.metric(
    "Avg Assessment Gain",
    f"{valid_pairs['Assessment Improvement'].mean():.1f} pts" if len(valid_pairs) else "N/A",
    help="Post minus pre total assessment score, points on a 0-100 scale.",
)
c5.metric("Enrollments w/ full pre+post data", f"{len(valid_pairs):,} ({len(valid_pairs)/max(len(enr_f),1)*100:.0f}%)")

st.caption(
    "Only a minority of enrollments have both a pre- and a post-assessment on file "
    "(most students have just a quiz score or partial data). The KPI and charts below "
    "are always computed only on records that actually have the data required, and "
    "sample sizes (n) are labeled so small groups aren't over-interpreted."
)

st.divider()

# ----------------------------------------------------------------------------
# LEARNING OUTCOMES
# ----------------------------------------------------------------------------
st.header("📈 Learning Outcomes")

col1, col2 = st.columns(2)

with col1:
    if len(valid_pairs):
        fig = px.scatter(
            valid_pairs,
            x="Total Score(Pre-assessment)",
            y="Total Score(Post-assessment)",
            color="Assessment Improvement",
            color_continuous_scale=BLUE_SCALE[::-1],
            title=f"Pre vs. Post Assessment Score (n={len(valid_pairs)} enrollments)",
            hover_data=["Program Name"],
            labels={"Total Score(Pre-assessment)": "Pre-Assessment Score",
                    "Total Score(Post-assessment)": "Post-Assessment Score"},
        )
        fig.add_shape(type="line", x0=0, y0=0, x1=100, y1=100,
                      line=dict(color=GRAY, dash="dash"))
        fig.add_annotation(x=15, y=90, text="Above line = improved", showarrow=False,
                            font=dict(color=GRAY, size=11))
        fig.update_layout(xaxis_range=[0, 100], yaxis_range=[0, 100])
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("No enrollments with both pre- and post-assessment scores in the current filter.")

with col2:
    if len(valid_pairs):
        fig = px.histogram(
            valid_pairs,
            x="Assessment Improvement",
            nbins=20,
            title="Distribution of Learning Gains",
            labels={"Assessment Improvement": "Post − Pre Score (pts)"},
        )
        fig.add_vline(x=0, line_dash="dot", line_color=GRAY)
        fig.add_vline(
            x=valid_pairs["Assessment Improvement"].mean(),
            line_color=BLUE_DARK,
            annotation_text=f"Avg: {valid_pairs['Assessment Improvement'].mean():.1f}",
        )
        pct_negative = (valid_pairs["Assessment Improvement"] < 0).mean() * 100
        st.plotly_chart(fig, use_container_width=True)
        st.caption(f"{pct_negative:.0f}% of enrollments with paired data show a score decline post-program.")
    else:
        st.info("No data to plot.")

st.divider()

# ----------------------------------------------------------------------------
# MODULE PERFORMANCE (topic-level pre/post)
# ----------------------------------------------------------------------------
st.header("Module (Topic) Performance")

module_rows = []
for module, (pre_col, post_col) in MODULE_COLS.items():
    d = enr_f.dropna(subset=[pre_col, post_col])
    if len(d):
        module_rows.append({
            "Module": module,
            "Avg Pre-Score": d[pre_col].mean(),
            "Avg Post-Score": d[post_col].mean(),
            "Avg Gain": (d[post_col] - d[pre_col]).mean(),
            "n": len(d),
        })
module_df = pd.DataFrame(module_rows).sort_values("Avg Gain", ascending=False)

if not module_df.empty:
    col1, col2 = st.columns([3, 2])
    with col1:
        plot_df = module_df.melt(
            id_vars=["Module", "n"], value_vars=["Avg Pre-Score", "Avg Post-Score"],
            var_name="Stage", value_name="Score"
        )
        fig = px.bar(
            plot_df, x="Module", y="Score", color="Stage", barmode="group",
            title="Average Score Before vs. After, by Topic",
            color_discrete_map={"Avg Pre-Score": BLUE_LIGHT, "Avg Post-Score": BLUE_DARK},
            text_auto=".0f",
        )
        fig.update_layout(yaxis_range=[0, 100])
        st.plotly_chart(fig, use_container_width=True)
    with col2:
        fig = px.bar(
            module_df, x="Avg Gain", y="Module", orientation="h",
            title="Average Gain by Topic (sample size labeled)",
            text=module_df.apply(lambda r: f"+{r['Avg Gain']:.1f} (n={r['n']})", axis=1),
            color="Avg Gain", color_continuous_scale=BLUE_SCALE[::-1],
        )
        fig.update_traces(textposition="outside")
        fig.update_layout(showlegend=False, coloraxis_showscale=False)
        st.plotly_chart(fig, use_container_width=True)
    st.caption(
        "'Spending' shows the smallest average gain — worth a look at whether that unit's "
        "content or pacing needs revisiting."
    )
else:
    st.warning("No module-level pre/post pairs found in the current filter.")

st.divider()

# ----------------------------------------------------------------------------
# LESSON / QUIZ PERFORMANCE (assignment-level, much bigger sample)
# ----------------------------------------------------------------------------
st.header("Lesson Quiz Performance")
st.caption(
    "Unlike the topic pre/post assessment (small sample above), quiz scores exist for "
    "almost every lesson attended — a more statistically robust view of where students "
    "struggle day-to-day."
)

quiz = scores_f.dropna(subset=["Assignment", "Score"])
if len(quiz):
    quiz_agg = quiz.groupby("Assignment")["Score"].agg(["mean", "count"]).reset_index()
    quiz_agg.columns = ["Assignment", "Avg Score", "n"]
    quiz_agg = quiz_agg.sort_values("Avg Score")

    fig = px.bar(
        quiz_agg, x="Avg Score", y="Assignment", orientation="h",
        title="Average Quiz Score by Lesson (sorted, lowest first)",
        text=quiz_agg.apply(lambda r: f"{r['Avg Score']:.0f} (n={r['n']})", axis=1),
        color="Avg Score", color_continuous_scale=BLUE_SCALE[::-1],
    )
    fig.update_traces(textposition="outside")
    fig.update_layout(coloraxis_showscale=False, height=420)
    st.plotly_chart(fig, use_container_width=True)
else:
    st.info("No quiz scores in the current filter.")

st.divider()

# ----------------------------------------------------------------------------
# ATTENDANCE ANALYSIS
# ----------------------------------------------------------------------------
st.header("Attendance Analysis")

col1, col2 = st.columns(2)
with col1:
    fig = px.histogram(
        att_f, x="Attendance Rate", nbins=20,
        title="Attendance Rate Distribution (per student)",
    )
    fig.add_vline(x=att_f["Attendance Rate"].mean(), line_color=BLUE_DARK,
                  annotation_text=f"Avg: {att_f['Attendance Rate'].mean():.0f}%")
    st.plotly_chart(fig, use_container_width=True)
    st.caption(
        f"{(att_f['Attendance Rate'] >= 80).mean()*100:.0f}% of students hit ≥80% attendance, "
        f"but {(att_f['Attendance Rate'] < 50).mean()*100:.0f}% are below 50% — a wide split, "
        "not a normal curve."
    )

with col2:
    merged_ai = enr_f.merge(att_f[["Student ID", "Attendance Rate"]], on="Student ID", how="inner")
    merged_ai = merged_ai.dropna(subset=["Attendance Rate", "Assessment Improvement"])
    if len(merged_ai) >= 5:
        corr = merged_ai["Attendance Rate"].corr(merged_ai["Assessment Improvement"])
        fig = px.scatter(
            merged_ai, x="Attendance Rate", y="Assessment Improvement",
            title=f"Attendance vs. Learning Gain (n={len(merged_ai)}, r={corr:.2f})",
        )
        # Manual linear trendline (avoids requiring the optional statsmodels dependency)
        x = merged_ai["Attendance Rate"].values
        y = merged_ai["Assessment Improvement"].values
        slope, intercept = np.polyfit(x, y, 1)
        x_line = np.linspace(x.min(), x.max(), 50)
        fig.add_trace(go.Scatter(
            x=x_line, y=slope * x_line + intercept, mode="lines",
            line=dict(color=BLUE_DARK, width=3), name="Trend",
        ))
        fig.add_hline(y=0, line_dash="dot", line_color=GRAY)
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("Not enough overlapping attendance + assessment data to plot a correlation.")

# Program-level attendance leaderboard (uses full per-record attendance, more n than pairs)
prog_att = enr_f.merge(att_f[["Student ID", "Attendance Rate"]], on="Student ID", how="inner")
prog_att_agg = (
    prog_att.groupby("Program Name")
    .agg(Avg_Attendance=("Attendance Rate", "mean"), Students=("Student ID", "nunique"))
    .reset_index()
)
prog_att_agg = prog_att_agg[prog_att_agg["Students"] >= 5].sort_values("Avg_Attendance")

if len(prog_att_agg):
    top_bottom = pd.concat([prog_att_agg.head(8), prog_att_agg.tail(8)]).drop_duplicates()
    fig = px.bar(
        top_bottom, x="Avg_Attendance", y="Program Name", orientation="h",
        title="Highest & Lowest Attendance Programs (min. 5 students)",
        text=top_bottom.apply(lambda r: f"{r['Avg_Attendance']:.0f}% (n={r['Students']})", axis=1),
        color="Avg_Attendance", color_continuous_scale=BLUE_SCALE[::-1],
    )
    fig.update_traces(textposition="outside")
    fig.update_layout(coloraxis_showscale=False, height=500)
    st.plotly_chart(fig, use_container_width=True)

st.divider()

# ----------------------------------------------------------------------------
# EQUITY ANALYSIS
# ----------------------------------------------------------------------------
st.header("⚖️ Equity Analysis")
st.caption(
    "Composition of who FLY serves, plus attendance and learning-gain outcomes by group. "
    "Groups with fewer than 5 students are dropped from outcome charts to avoid noisy averages."
)

demo_att = demographics.merge(att_f[["Student ID", "Attendance Rate"]], on="Student ID", how="inner")
demo_gain = demographics.merge(
    valid_pairs[["Student ID", "Assessment Improvement"]], on="Student ID", how="inner"
)

demo_groups = ["Gender", "Age Group", "Ethnicity", "Household Annual Income"]

for group in demo_groups:
    st.subheader(group)
    c1, c2, c3 = st.columns(3)

    with c1:
        comp = demographics[group].value_counts(dropna=True).reset_index()
        comp.columns = [group, "Students"]
        fig = px.pie(comp, names=group, values="Students", title=f"Who We Serve: {group}",
                     color_discrete_sequence=BLUE_SCALE, hole=0.4)
        fig.update_layout(height=320, showlegend=True)
        st.plotly_chart(fig, use_container_width=True)

    with c2:
        d = demo_att.dropna(subset=[group])
        agg = d.groupby(group).agg(Avg_Attendance=("Attendance Rate", "mean"),
                                    n=("Student ID", "nunique")).reset_index()
        agg = agg[agg["n"] >= 5].sort_values("Avg_Attendance")
        if len(agg):
            fig = px.bar(agg, x="Avg_Attendance", y=group, orientation="h",
                         title="Avg Attendance %", text=agg.apply(lambda r: f"n={r['n']}", axis=1),
                         color_discrete_sequence=[BLUE_MAIN])
            fig.update_layout(height=320, showlegend=False)
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.caption("Not enough data.")

    with c3:
        d = demo_gain.dropna(subset=[group])
        agg = d.groupby(group).agg(Avg_Gain=("Assessment Improvement", "mean"),
                                    n=("Student ID", "nunique")).reset_index()
        agg = agg[agg["n"] >= 5].sort_values("Avg_Gain")
        if len(agg):
            fig = px.bar(agg, x="Avg_Gain", y=group, orientation="h",
                         title="Avg Learning Gain (pts)", text=agg.apply(lambda r: f"n={r['n']}", axis=1),
                         color_discrete_sequence=[BLUE_DARK])
            fig.update_layout(height=320, showlegend=False)
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.caption("Not enough paired assessment data for this group.")

st.divider()

# ----------------------------------------------------------------------------
# SEASONAL / OPERATIONAL TREND
# ----------------------------------------------------------------------------
st.header("📅 Attendance Trend Across the Year")
st.caption(
    "Uses the detailed attendance log (clean_attendance.csv), excluding 'No Class' days, "
    "to show how the present-rate moves month to month — useful for spotting fatigue or "
    "seasonal drop-off."
)

try:
    detail = pd.read_csv("outputs/clean_attendance.csv", low_memory=False)
    detail["Date"] = pd.to_datetime(detail["Date"], errors="coerce")
    detail = detail[detail["Attendance Status"] != "No Class"].dropna(subset=["Date"])
    detail["Month"] = detail["Date"].dt.to_period("M").dt.to_timestamp()
    trend = detail.groupby("Month")["Present_Flag"].mean().reset_index()
    trend["Present_Flag"] *= 100

    fig = px.line(
        trend, x="Month", y="Present_Flag", markers=True,
        title="Monthly Present Rate (Aug 2025 – Jun 2026)",
        labels={"Present_Flag": "Present Rate (%)"},
        color_discrete_sequence=[BLUE_DARK],
    )
    fig.update_traces(line_width=3, marker_size=8)
    st.plotly_chart(fig, use_container_width=True)

    peak_month = trend.loc[trend["Present_Flag"].idxmax(), "Month"].strftime("%B %Y")
    low_month = trend.loc[trend["Present_Flag"].idxmin(), "Month"].strftime("%B %Y")
    st.caption(f"Attendance peaked in **{peak_month}** and bottomed out in **{low_month}**.")
except FileNotFoundError:
    st.info("clean_attendance.csv not found in outputs/ — skipping trend view.")

st.success("Dashboard loaded successfully.")