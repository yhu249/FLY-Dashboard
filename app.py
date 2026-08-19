import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go

st.set_page_config(page_title="FLY Program Dashboard", layout="wide")

# ----------------------------------------------------------------------------
# THEME
# ----------------------------------------------------------------------------
BLUE_DARK = "#0B3D91"
BLUE_MAIN = "#1F77B4"
BLUE_MID = "#4C9BE8"
BLUE_LIGHT = "#A9CCE3"
BLUE_PALE = "#EAF2FB"
GRAY = "#6B7280"
TEAL = "#2A9D8F"
GOLD = "#E9C46A"
ORANGE = "#F4A261"
CORAL = "#E76F51"
PURPLE = "#7A5195"

BLUE_SCALE = [BLUE_DARK, BLUE_MAIN, BLUE_MID, "#7FB3E8", BLUE_LIGHT, "#CFE3F5"]
CATEGORY_COLORS = [BLUE_DARK, TEAL, GOLD, CORAL, PURPLE, BLUE_MID, ORANGE, "#4D908E"]
GAIN_SCALE = [CORAL, ORANGE, GOLD, TEAL, BLUE_DARK]

px.defaults.color_discrete_sequence = CATEGORY_COLORS
px.defaults.template = "plotly_white"

PLOTLY_CONFIG = {
    "displayModeBar": False,
    "responsive": True,
}

st.markdown(
    f"""
<style>
    .stMetric {{
        background-color: {BLUE_PALE};
        border: 1px solid {BLUE_LIGHT};
        border-radius: 10px;
        padding: 12px 10px 6px 10px;
    }}
    h1, h2, h3 {{ color: {BLUE_DARK}; }}
    [data-testid="stPlotlyChart"] {{ overflow-x: hidden; }}

    /* Print/PDF-friendly layout: hide sidebar and prevent charts from spilling
       past the printable page. The interactive app remains the primary view. */
    @media print {{
        [data-testid="stSidebar"] {{ display: none !important; }}
        .block-container {{
            max-width: 100% !important;
            padding-left: 0.5rem !important;
            padding-right: 0.5rem !important;
        }}
        [data-testid="stPlotlyChart"] {{
            break-inside: avoid;
            page-break-inside: avoid;
            max-width: 100% !important;
        }}
    }}
</style>
""",
    unsafe_allow_html=True,
)


# ----------------------------------------------------------------------------
# SMALL DISPLAY HELPERS
# ----------------------------------------------------------------------------
def chart_note(description: str, insight: str | None = None) -> None:
    """Add a short stakeholder-friendly explanation below a visualization.

    The description explains what the chart represents and therefore remains
    valid when a new same-schema dataset is loaded. The optional insight is
    calculated from the currently filtered data, so it updates automatically.
    """
    text = f"**What this shows:** {description}"
    if insight:
        text += f"  \n**Key insight:** {insight}"
    st.caption(text)


def render_chart(fig, *, height: int | None = None, right_margin: int = 40) -> None:
    """Apply consistent responsive sizing and safer margins before rendering."""
    layout_updates = dict(
        autosize=True,
        margin=dict(l=30, r=right_margin, t=70, b=55),
        hoverlabel=dict(font_size=12),
    )
    if height is not None:
        layout_updates["height"] = height
    fig.update_layout(**layout_updates)
    st.plotly_chart(fig, width="stretch", config=PLOTLY_CONFIG)


def padded_range(values: pd.Series, *, include_zero: bool = True, extra: float = 0.25) -> list[float]:
    """Return an axis range with room for outside text labels."""
    clean = pd.to_numeric(values, errors="coerce").dropna()
    if clean.empty:
        return [0, 1]

    vmin = float(clean.min())
    vmax = float(clean.max())
    if include_zero:
        vmin = min(0.0, vmin)
        vmax = max(0.0, vmax)

    span = max(vmax - vmin, 1.0)
    left_pad = span * 0.08 if vmin < 0 else 0.0
    right_pad = span * extra
    return [vmin - left_pad, vmax + right_pad]


def correlation_language(corr: float) -> str:
    if pd.isna(corr):
        return "The correlation is undefined in the current filter because one variable has little or no variation."
    strength = abs(corr)
    if strength < 0.20:
        phrase = "little linear relationship"
    elif strength < 0.40:
        phrase = "a weak linear relationship"
    elif strength < 0.60:
        phrase = "a moderate linear relationship"
    else:
        phrase = "a relatively strong linear relationship"
    direction = "positive" if corr > 0 else "negative"
    return f"The available paired records show {phrase} ({direction}, r={corr:.2f}); this is descriptive, not causal."


# ----------------------------------------------------------------------------
# DATA LOADING & CLEANING
# ----------------------------------------------------------------------------
def norm_id(series: pd.Series) -> pd.Series:
    """Normalize Student ID to a clean string.

    Handles float-read numeric IDs such as 100075.0 as well as manual SI#### IDs.
    """
    return (
        series.astype(str)
        .str.strip()
        .str.replace(r"\.0$", "", regex=True)
        .replace({"nan": np.nan})
    )


# Explicit mapping prevents the repeated enrollment-level pre/post columns from
# being confused with assignment-level quiz fields.
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

    # clean_scores.csv is at the (Student, Program, Assignment) grain. Total
    # pre/post and topic pre/post fields are repeated across assignment rows, so
    # enrollment-level charts must use a de-duplicated table.
    enrollment = scores_raw.drop_duplicates(subset=["Student ID", "Program Name"]).copy()

    enrollment["Assessment Improvement"] = (
        enrollment["Total Score(Post-assessment)"]
        - enrollment["Total Score(Pre-assessment)"]
    )

    return scores_raw, enrollment, attendance_summary, demographics


scores_raw, enrollment, attendance, demographics = load_data()

# ----------------------------------------------------------------------------
# SIDEBAR FILTERS
# ----------------------------------------------------------------------------
st.sidebar.header("Filters")

status_options = sorted(enrollment["Status"].dropna().unique().tolist())
default_status = [s for s in status_options if s in ("Completed", "Confirmed")]
selected_status = st.sidebar.multiselect(
    "Enrollment status", status_options, default=default_status
)

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

att_f = attendance[attendance["Student ID"].isin(enr_f["Student ID"])].copy()
demo_f = demographics[demographics["Student ID"].isin(enr_f["Student ID"])].copy()

# ----------------------------------------------------------------------------
# HEADER + KPIs
# ----------------------------------------------------------------------------
st.title("Financial Literacy Youth (FLY) Program Dashboard")
st.caption("Fiscal Year 2025–2026 (Jul 2025 – Jun 2026)")
st.caption(
    "This is an interactive dashboard: filters and same-schema replacement CSV files "
    "recalculate the metrics and key insights automatically. A PDF or screenshot is only "
    "a static preview of the full Streamlit view."
)

valid_pairs = enr_f.dropna(
    subset=["Total Score(Pre-assessment)", "Total Score(Post-assessment)"]
).copy()

c1, c2, c3, c4, c5 = st.columns(5)
c1.metric("Students Served", f"{enr_f['Student ID'].nunique():,}")
c2.metric("Enrollments (Student × Program)", f"{enr_f.shape[0]:,}")
c3.metric(
    "Avg Attendance Rate",
    f"{att_f['Attendance Rate'].mean():.1f}%" if len(att_f) else "N/A",
)
c4.metric(
    "Avg Assessment Gain",
    f"{valid_pairs['Assessment Improvement'].mean():.1f} pts" if len(valid_pairs) else "N/A",
    help="Post minus pre total assessment score, points on a 0-100 scale.",
)
c5.metric(
    "Enrollments w/ full pre+post data",
    f"{len(valid_pairs):,} ({len(valid_pairs) / max(len(enr_f), 1) * 100:.0f}%)",
)

st.caption(
    "Only a subset of enrollments have both a pre- and a post-assessment on file. "
    "Assessment KPIs and charts therefore use only records with the required paired data, "
    "and sample sizes (n) are shown to discourage over-interpretation of small groups."
)

st.divider()

# ----------------------------------------------------------------------------
# LEARNING OUTCOMES
# ----------------------------------------------------------------------------
st.header("Learning Outcomes")

col1, col2 = st.columns(2)

with col1:
    if len(valid_pairs):
        mean_gain = valid_pairs["Assessment Improvement"].mean()
        pct_improved = (valid_pairs["Assessment Improvement"] > 0).mean() * 100

        fig = px.scatter(
            valid_pairs,
            x="Total Score(Pre-assessment)",
            y="Total Score(Post-assessment)",
            color="Assessment Improvement",
            color_continuous_scale=GAIN_SCALE,
            title=f"Pre vs. Post Assessment Score (n={len(valid_pairs)} enrollments)",
            hover_data=["Program Name"],
            labels={
                "Total Score(Pre-assessment)": "Pre-Assessment Score",
                "Total Score(Post-assessment)": "Post-Assessment Score",
                "Assessment Improvement": "Gain (pts)",
            },
        )
        fig.add_shape(
            type="line",
            x0=0,
            y0=0,
            x1=100,
            y1=100,
            line=dict(color=GRAY, dash="dash"),
        )
        fig.add_annotation(
            x=15,
            y=90,
            text="Above dashed line = improved",
            showarrow=False,
            font=dict(color=GRAY, size=11),
        )
        fig.update_layout(
            xaxis_range=[0, 100],
            yaxis_range=[0, 100],
            coloraxis_colorbar=dict(title="Gain<br>(pts)"),
        )
        render_chart(fig)
        chart_note(
            "Each point is an enrollment with both assessments. Points above the dashed 45° line finished with a higher post-assessment score than pre-assessment score.",
            f"{pct_improved:.0f}% of paired enrollments improved, with an average change of {mean_gain:+.1f} points.",
        )
    else:
        st.info("No enrollments with both pre- and post-assessment scores in the current filter.")

with col2:
    if len(valid_pairs):
        mean_gain = valid_pairs["Assessment Improvement"].mean()
        pct_negative = (valid_pairs["Assessment Improvement"] < 0).mean() * 100
        pct_positive = (valid_pairs["Assessment Improvement"] > 0).mean() * 100

        fig = px.histogram(
            valid_pairs,
            x="Assessment Improvement",
            nbins=20,
            title="Distribution of Learning Gains",
            labels={"Assessment Improvement": "Post − Pre Score (pts)"},
            color_discrete_sequence=[BLUE_MAIN],
        )
        fig.add_vline(
            x=0,
            line_dash="dot",
            line_color=GRAY,
            annotation_text="No change",
        )
        fig.add_vline(
            x=mean_gain,
            line_color=BLUE_DARK,
            annotation_text=f"Average: {mean_gain:+.1f}",
        )
        render_chart(fig)
        chart_note(
            "The histogram shows how much each paired enrollment's total assessment score changed after the program. Values to the right of zero indicate improvement.",
            f"{pct_positive:.0f}% improved and {pct_negative:.0f}% declined; the average change was {mean_gain:+.1f} points.",
        )
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
        module_rows.append(
            {
                "Module": module,
                "Avg Pre-Score": d[pre_col].mean(),
                "Avg Post-Score": d[post_col].mean(),
                "Avg Gain": (d[post_col] - d[pre_col]).mean(),
                "n": len(d),
            }
        )

module_df = pd.DataFrame(module_rows)
if not module_df.empty:
    module_df = module_df.sort_values("Avg Gain", ascending=False)
    strongest = module_df.iloc[0]
    weakest = module_df.iloc[-1]

    col1, col2 = st.columns([3, 2])

    with col1:
        plot_df = module_df.melt(
            id_vars=["Module", "n"],
            value_vars=["Avg Pre-Score", "Avg Post-Score"],
            var_name="Stage",
            value_name="Score",
        )
        plot_df["Stage"] = plot_df["Stage"].map(
            {
                "Avg Pre-Score": "Pre-assessment",
                "Avg Post-Score": "Post-assessment",
            }
        )

        fig = px.bar(
            plot_df,
            x="Module",
            y="Score",
            color="Stage",
            barmode="group",
            title="Average Score Before vs. After, by Topic",
            color_discrete_map={
                "Pre-assessment": BLUE_LIGHT,
                "Post-assessment": BLUE_DARK,
            },
            text_auto=".0f",
            labels={"Stage": "Assessment stage", "Score": "Average score"},
        )
        fig.update_layout(
            yaxis_range=[0, 100],
            legend=dict(title="Assessment stage", orientation="h", yanchor="bottom", y=1.01, x=0),
        )
        render_chart(fig, right_margin=25)
        chart_note(
            "For each financial-literacy topic, the light bar is the average pre-assessment score and the dark bar is the average post-assessment score.",
            f"The largest average gain is in {strongest['Module']} ({strongest['Avg Gain']:+.1f} points).",
        )

    with col2:
        labels = module_df.apply(
            lambda r: f"{r['Avg Gain']:+.1f} (n={int(r['n'])})", axis=1
        )
        fig = px.bar(
            module_df,
            x="Avg Gain",
            y="Module",
            orientation="h",
            title="Average Gain by Topic",
            text=labels,
            color="Avg Gain",
            color_continuous_scale=GAIN_SCALE,
            labels={"Avg Gain": "Average gain (pts)"},
        )
        fig.update_traces(textposition="outside", cliponaxis=False)
        fig.update_xaxes(range=padded_range(module_df["Avg Gain"], extra=0.35))
        fig.update_layout(coloraxis_colorbar=dict(title="Gain<br>(pts)"))
        render_chart(fig, right_margin=90)
        chart_note(
            "Bars rank topics by average post-minus-pre improvement; labels also show the paired sample size for each topic.",
            f"{strongest['Module']} has the highest average gain, while {weakest['Module']} has the lowest ({weakest['Avg Gain']:+.1f} points).",
        )
else:
    st.warning("No module-level pre/post pairs found in the current filter.")

st.divider()

# ----------------------------------------------------------------------------
# LESSON / QUIZ PERFORMANCE (assignment-level)
# ----------------------------------------------------------------------------
st.header("Lesson Quiz Performance")
st.caption(
    "Unlike the topic pre/post assessment above, quiz scores are assignment-level records. "
    "This provides a broader view of which lessons appear easier or harder for students."
)

quiz = scores_f.dropna(subset=["Assignment", "Score"])
if len(quiz):
    quiz_agg = quiz.groupby("Assignment")["Score"].agg(["mean", "count"]).reset_index()
    quiz_agg.columns = ["Assignment", "Avg Score", "n"]
    quiz_agg = quiz_agg.sort_values("Avg Score")

    fig = px.bar(
        quiz_agg,
        x="Avg Score",
        y="Assignment",
        orientation="h",
        title="Average Quiz Score by Lesson (lowest first)",
        text=quiz_agg.apply(
            lambda r: f"{r['Avg Score']:.0f} (n={int(r['n'])})", axis=1
        ),
        color="Avg Score",
        color_continuous_scale=GAIN_SCALE,
        labels={"Avg Score": "Average quiz score"},
    )
    fig.update_traces(textposition="outside", cliponaxis=False)
    upper = max(105.0, float(quiz_agg["Avg Score"].max()) * 1.12)
    fig.update_xaxes(range=[0, upper])
    fig.update_layout(coloraxis_colorbar=dict(title="Avg<br>score"))
    render_chart(fig, height=max(420, 28 * len(quiz_agg) + 120), right_margin=90)

    lowest = quiz_agg.iloc[0]
    highest = quiz_agg.iloc[-1]
    chart_note(
        "Each bar is the average score for one lesson or assignment; labels include both the average score and number of recorded quizzes.",
        f"{lowest['Assignment']} has the lowest average score ({lowest['Avg Score']:.1f}), while {highest['Assignment']} has the highest ({highest['Avg Score']:.1f}) in the current filter.",
    )
else:
    st.info("No quiz scores in the current filter.")

st.divider()

# ----------------------------------------------------------------------------
# ATTENDANCE ANALYSIS
# ----------------------------------------------------------------------------
st.header("Attendance Analysis")

col1, col2 = st.columns(2)

with col1:
    if len(att_f):
        avg_attendance = att_f["Attendance Rate"].mean()
        pct_80 = (att_f["Attendance Rate"] >= 80).mean() * 100
        pct_under_50 = (att_f["Attendance Rate"] < 50).mean() * 100

        fig = px.histogram(
            att_f,
            x="Attendance Rate",
            nbins=20,
            title="Attendance Rate Distribution (per student)",
            color_discrete_sequence=[TEAL],
            labels={"Attendance Rate": "Attendance rate (%)"},
        )
        fig.add_vline(
            x=avg_attendance,
            line_color=BLUE_DARK,
            annotation_text=f"Average: {avg_attendance:.0f}%",
        )
        render_chart(fig)
        chart_note(
            "The histogram shows how student attendance rates are distributed, rather than only reporting one overall average.",
            f"{pct_80:.0f}% of students are at or above 80% attendance, while {pct_under_50:.0f}% are below 50%.",
        )
    else:
        st.info("No attendance data in the current filter.")

with col2:
    merged_ai = enr_f.merge(
        att_f[["Student ID", "Attendance Rate"]], on="Student ID", how="inner"
    )
    merged_ai = merged_ai.dropna(
        subset=["Attendance Rate", "Assessment Improvement"]
    )

    if len(merged_ai) >= 5:
        corr = merged_ai["Attendance Rate"].corr(merged_ai["Assessment Improvement"])
        fig = px.scatter(
            merged_ai,
            x="Attendance Rate",
            y="Assessment Improvement",
            title=f"Attendance vs. Learning Gain (n={len(merged_ai)})",
            labels={
                "Attendance Rate": "Attendance rate (%)",
                "Assessment Improvement": "Learning gain (pts)",
            },
            color_discrete_sequence=[BLUE_MID],
        )
        fig.data[0].name = "Enrollment"
        fig.data[0].showlegend = True

        if merged_ai["Attendance Rate"].nunique() >= 2:
            x = merged_ai["Attendance Rate"].to_numpy()
            y = merged_ai["Assessment Improvement"].to_numpy()
            slope, intercept = np.polyfit(x, y, 1)
            x_line = np.linspace(x.min(), x.max(), 50)
            fig.add_trace(
                go.Scatter(
                    x=x_line,
                    y=slope * x_line + intercept,
                    mode="lines",
                    line=dict(color=BLUE_DARK, width=3),
                    name="Linear trend",
                )
            )

        fig.add_hline(y=0, line_dash="dot", line_color=GRAY)
        fig.update_layout(
            legend=dict(title=None, orientation="h", yanchor="bottom", y=1.01, x=0)
        )
        render_chart(fig)
        chart_note(
            "Each point links a student's attendance rate with the assessment gain recorded for an enrollment. The fitted line summarizes the linear pattern when it can be estimated.",
            correlation_language(corr),
        )
    else:
        st.info("Not enough overlapping attendance + assessment data to plot a correlation.")

# Program-level attendance leaderboard. Attendance Rate comes from the available
# per-student attendance summary and is merged to program enrollments.
prog_att = enr_f.merge(
    att_f[["Student ID", "Attendance Rate"]], on="Student ID", how="inner"
)
prog_att_agg = (
    prog_att.groupby("Program Name")
    .agg(
        Avg_Attendance=("Attendance Rate", "mean"),
        Students=("Student ID", "nunique"),
    )
    .reset_index()
)
prog_att_agg = prog_att_agg[prog_att_agg["Students"] >= 5].sort_values(
    "Avg_Attendance"
)

if len(prog_att_agg):
    top_bottom = pd.concat(
        [prog_att_agg.head(8), prog_att_agg.tail(8)]
    ).drop_duplicates()

    fig = px.bar(
        top_bottom,
        x="Avg_Attendance",
        y="Program Name",
        orientation="h",
        title="Highest & Lowest Attendance Programs (min. 5 students)",
        text=top_bottom.apply(
            lambda r: f"{r['Avg_Attendance']:.0f}% (n={int(r['Students'])})", axis=1
        ),
        color="Avg_Attendance",
        color_continuous_scale=GAIN_SCALE,
        labels={"Avg_Attendance": "Average attendance (%)"},
    )
    fig.update_traces(textposition="outside", cliponaxis=False)
    upper = max(105.0, float(top_bottom["Avg_Attendance"].max()) * 1.10)
    fig.update_xaxes(range=[0, upper])
    fig.update_layout(coloraxis_colorbar=dict(title="Attendance<br>(%)"))
    render_chart(fig, height=max(500, 30 * len(top_bottom) + 120), right_margin=100)

    highest_prog = prog_att_agg.iloc[-1]
    lowest_prog = prog_att_agg.iloc[0]
    chart_note(
        "This comparison highlights programs at the high and low ends of average attendance among programs with at least five students.",
        f"{highest_prog['Program Name']} is highest at {highest_prog['Avg_Attendance']:.0f}%, while {lowest_prog['Program Name']} is lowest at {lowest_prog['Avg_Attendance']:.0f}% in the current filter.",
    )

st.divider()

# ----------------------------------------------------------------------------
# EQUITY ANALYSIS
# ----------------------------------------------------------------------------
st.header("Equity Analysis")
st.caption(
    "This section compares who FLY serves with attendance and learning-gain outcomes "
    "across demographic groups. Groups with fewer than 5 students are excluded from "
    "outcome charts to reduce the risk of over-interpreting unstable averages."
)

demo_att = demo_f.merge(
    att_f[["Student ID", "Attendance Rate"]], on="Student ID", how="inner"
)
demo_gain = demo_f.merge(
    valid_pairs[["Student ID", "Assessment Improvement"]],
    on="Student ID",
    how="inner",
)

demo_groups = ["Gender", "Age Group", "Ethnicity", "Household Annual Income"]

for group in demo_groups:
    st.subheader(group)
    c1, c2, c3 = st.columns(3)

    with c1:
        comp = demo_f[group].value_counts(dropna=True).reset_index()
        comp.columns = [group, "Students"]
        if len(comp):
            fig = px.pie(
                comp,
                names=group,
                values="Students",
                title=f"Who We Serve: {group}",
                color_discrete_sequence=CATEGORY_COLORS,
                hole=0.4,
            )
            fig.update_layout(
                showlegend=True,
                legend=dict(title=group, font=dict(size=10)),
            )
            render_chart(fig, height=360, right_margin=20)

            largest = comp.iloc[0]
            share = largest["Students"] / comp["Students"].sum() * 100
            chart_note(
                f"The donut chart shows the composition of currently selected students by {group.lower()}; the legend identifies each category.",
                f"The largest represented category is {largest[group]} ({share:.0f}% of students with recorded {group.lower()}).",
            )
        else:
            st.caption("No demographic data in the current filter.")

    with c2:
        d = demo_att.dropna(subset=[group])
        agg = (
            d.groupby(group)
            .agg(
                Avg_Attendance=("Attendance Rate", "mean"),
                n=("Student ID", "nunique"),
            )
            .reset_index()
        )
        agg = agg[agg["n"] >= 5].sort_values("Avg_Attendance")

        if len(agg):
            fig = px.bar(
                agg,
                x="Avg_Attendance",
                y=group,
                orientation="h",
                color=group,
                title="Average Attendance %",
                text=agg.apply(
                    lambda r: f"{r['Avg_Attendance']:.0f}% (n={int(r['n'])})",
                    axis=1,
                ),
                color_discrete_sequence=CATEGORY_COLORS,
                labels={"Avg_Attendance": "Average attendance (%)"},
            )
            fig.update_traces(textposition="outside", cliponaxis=False)
            fig.update_xaxes(range=[0, max(105.0, float(agg["Avg_Attendance"].max()) * 1.12)])
            fig.update_layout(showlegend=False)
            render_chart(fig, height=360, right_margin=90)

            hi = agg.iloc[-1]
            lo = agg.iloc[0]
            chart_note(
                f"Bars compare average attendance across {group.lower()} categories; the bar labels show both the rate and the student count used in each average.",
                f"Among groups with n≥5, {hi[group]} has the highest average attendance ({hi['Avg_Attendance']:.0f}%) and {lo[group]} the lowest ({lo['Avg_Attendance']:.0f}%).",
            )
        else:
            st.caption("Not enough attendance data for groups with n≥5.")

    with c3:
        d = demo_gain.dropna(subset=[group])
        agg = (
            d.groupby(group)
            .agg(
                Avg_Gain=("Assessment Improvement", "mean"),
                n=("Student ID", "nunique"),
            )
            .reset_index()
        )
        agg = agg[agg["n"] >= 5].sort_values("Avg_Gain")

        if len(agg):
            fig = px.bar(
                agg,
                x="Avg_Gain",
                y=group,
                orientation="h",
                color=group,
                title="Average Learning Gain (pts)",
                text=agg.apply(
                    lambda r: f"{r['Avg_Gain']:+.1f} (n={int(r['n'])})",
                    axis=1,
                ),
                color_discrete_sequence=CATEGORY_COLORS,
                labels={"Avg_Gain": "Average learning gain (pts)"},
            )
            fig.update_traces(textposition="outside", cliponaxis=False)
            fig.update_xaxes(range=padded_range(agg["Avg_Gain"], extra=0.35))
            fig.update_layout(showlegend=False)
            render_chart(fig, height=360, right_margin=90)

            hi = agg.iloc[-1]
            lo = agg.iloc[0]
            chart_note(
                f"Bars compare average post-minus-pre assessment gains across {group.lower()} categories using only paired assessment records.",
                f"Among groups with n≥5, {hi[group]} shows the highest average gain ({hi['Avg_Gain']:+.1f} points) and {lo[group]} the lowest ({lo['Avg_Gain']:+.1f}).",
            )
        else:
            st.caption("Not enough paired assessment data for groups with n≥5.")

st.divider()

# ----------------------------------------------------------------------------
# SEASONAL / OPERATIONAL TREND
# ----------------------------------------------------------------------------
st.header("Attendance Trend Across the Year")
st.caption(
    "Uses the detailed attendance log (clean_attendance.csv), excluding 'No Class' days, "
    "to show how the present rate changes month to month."
)

try:
    detail = pd.read_csv("outputs/clean_attendance.csv", low_memory=False)
    detail["Date"] = pd.to_datetime(detail["Date"], errors="coerce")

    if "Student ID" in detail.columns:
        detail["Student ID"] = norm_id(detail["Student ID"])
        detail = detail[detail["Student ID"].isin(enr_f["Student ID"])]

    detail = detail[detail["Attendance Status"] != "No Class"].dropna(subset=["Date"])
    detail["Month"] = detail["Date"].dt.to_period("M").dt.to_timestamp()
    trend = detail.groupby("Month")["Present_Flag"].mean().reset_index()
    trend["Present_Flag"] *= 100

    if len(trend):
        trend_start = trend["Month"].min().strftime("%b %Y")
        trend_end = trend["Month"].max().strftime("%b %Y")

        fig = px.line(
            trend,
            x="Month",
            y="Present_Flag",
            markers=True,
            title=f"Monthly Present Rate ({trend_start} – {trend_end})",
            labels={"Present_Flag": "Present Rate (%)", "Month": "Month"},
            color_discrete_sequence=[BLUE_DARK],
        )
        fig.update_traces(
            line_width=3,
            marker_size=8,
            name="Monthly present rate",
            showlegend=True,
        )
        fig.update_layout(
            legend=dict(title=None, orientation="h", yanchor="bottom", y=1.01, x=0)
        )
        render_chart(fig)

        peak = trend.loc[trend["Present_Flag"].idxmax()]
        low = trend.loc[trend["Present_Flag"].idxmin()]
        chart_note(
            "The line tracks the percentage of attendance records marked present in each month, making seasonal changes easier to identify.",
            f"Attendance is highest in {peak['Month'].strftime('%B %Y')} ({peak['Present_Flag']:.0f}%) and lowest in {low['Month'].strftime('%B %Y')} ({low['Present_Flag']:.0f}%) for the selected students.",
        )
    else:
        st.info("No detailed attendance records remain after the current filters.")

except FileNotFoundError:
    st.info("clean_attendance.csv not found in outputs/ — skipping trend view.")

st.success("Dashboard loaded successfully.")