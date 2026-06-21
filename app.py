"""
app.py — Streamlit web interface for LocalizeQA

Run with: streamlit run app.py
"""

import os
import csv
import io
import streamlit as st
import plotly.graph_objects as go
import plotly.express as px
from dotenv import load_dotenv
from openai import OpenAI
from translator import translate, CONTENT_TYPES
from evaluator import evaluate, format_report
from fixer import fix
from database import (
    get_connection, save_record, get_all_records,
    get_stats, get_stats_by_type, get_common_issues,
)

load_dotenv()

# === Page Config ===
st.set_page_config(
    page_title="LocalizeQA",
    page_icon="🌐",
    layout="wide",
)

# === Initialize ===
@st.cache_resource
def get_client():
    api_key = os.getenv("DEEPSEEK_API_KEY")
    if not api_key or api_key == "your_api_key_here":
        return None
    return OpenAI(api_key=api_key, base_url="https://api.deepseek.com")


def get_db():
    return get_connection()


# === Sidebar Navigation ===
st.sidebar.title("🌐 LocalizeQA")
st.sidebar.markdown("AI-Powered Localization QA")
st.sidebar.divider()

page = st.sidebar.radio(
    "Navigate",
    ["🔤 Translation Workspace", "📊 Quality Dashboard", "📋 History", "📁 Batch Processing"],
    label_visibility="collapsed",
)

client = get_client()
if client is None:
    st.error("⚠️ DEEPSEEK_API_KEY not found. Please set it in your .env file.")
    st.stop()


# =============================================
# Page 1: Translation Workspace
# =============================================
if page == "🔤 Translation Workspace":
    st.title("🔤 Translation Workspace")
    st.markdown("Input English travel content and get translated, evaluated, and fixed automatically.")

    col1, col2 = st.columns([1, 1])

    with col1:
        content_type = st.selectbox(
            "Content Type",
            options=list(CONTENT_TYPES.keys()),
            format_func=lambda x: f"{CONTENT_TYPES[x]} ({x})",
        )

        source_text = st.text_area(
            "English Source Text",
            height=200,
            placeholder="Paste your English travel content here...",
        )

        run_button = st.button("🚀 Translate & Evaluate", type="primary", use_container_width=True)

    with col2:
        if run_button and source_text.strip():
            conn = get_db()

            # Step 1: Translate
            with st.spinner("Translating..."):
                try:
                    translation = translate(source_text, content_type, client)
                except Exception as e:
                    st.error(f"Translation failed: {e}")
                    st.stop()

            st.subheader("Chinese Translation")
            st.info(translation)

            # Step 2: Evaluate
            with st.spinner("Evaluating quality..."):
                try:
                    eval_result = evaluate(source_text, translation, content_type, client)
                except Exception as e:
                    st.error(f"Evaluation failed: {e}")
                    st.stop()

            overall = eval_result.get("overall_score", 0)

            # Score display
            st.subheader("Quality Score")
            score_cols = st.columns(5)
            dimensions = [
                ("Accuracy", "accuracy"),
                ("Fluency", "fluency"),
                ("Cultural", "cultural_adaptation"),
                ("Terminology", "terminology"),
                ("Overall", None),
            ]

            for col_idx, (label, key) in enumerate(dimensions):
                with score_cols[col_idx]:
                    if key:
                        score = eval_result.get(key, {}).get("score", 0)
                    else:
                        score = overall
                    color = "🟢" if score >= 4.5 else "🟡" if score >= 3.5 else "🔴"
                    st.metric(label, f"{color} {score}/5")

            # Issues
            all_issues = []
            for dim in ["accuracy", "fluency", "cultural_adaptation", "terminology"]:
                for issue in eval_result.get(dim, {}).get("issues", []):
                    all_issues.append(f"**{dim}**: {issue}")

            if all_issues:
                st.subheader("Issues Found")
                for issue in all_issues:
                    st.markdown(f"- {issue}")

            # Step 3: Fix
            if all_issues:
                with st.spinner("Generating fixes..."):
                    try:
                        fix_result = fix(source_text, translation, eval_result, client)
                    except Exception as e:
                        st.error(f"Fix failed: {e}")
                        fix_result = None

                if fix_result and fix_result["had_issues"]:
                    st.subheader("Improved Translation")
                    st.success(fix_result["fixed_translation"])
            else:
                fix_result = None

            # Summary
            summary = eval_result.get("summary", "")
            if summary:
                st.caption(f"📝 {summary}")

            # Save to database
            try:
                save_record(conn, source_text, translation, content_type, eval_result, fix_result)
            except Exception:
                pass

            conn.close()

        elif run_button:
            st.warning("Please enter some text to translate.")


# =============================================
# Page 2: Quality Dashboard
# =============================================
elif page == "📊 Quality Dashboard":
    st.title("📊 Quality Dashboard")

    conn = get_db()
    stats = get_stats(conn)
    by_type = get_stats_by_type(conn)
    common_issues = get_common_issues(conn)
    records = get_all_records(conn)
    conn.close()

    if not stats or stats.get("total", 0) == 0:
        st.info("No data yet. Run some translations or the benchmark first!")
        st.code("python benchmark.py", language="bash")
        st.stop()

    # Top metrics
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Total Translations", stats["total"])
    m2.metric("Average Score", f"{stats['avg_overall']}/5.0")
    m3.metric("Issue Rate", f"{stats['total_with_issues'] / stats['total'] * 100:.0f}%")
    m4.metric("Score Range", f"{stats['min_score']}–{stats['max_score']}")

    st.divider()

    col1, col2 = st.columns([1, 1])

    with col1:
        # Dimension scores radar chart
        st.subheader("Score by Dimension")
        categories = ["Accuracy", "Fluency", "Cultural\nAdaptation", "Terminology"]
        values = [
            stats["avg_accuracy"],
            stats["avg_fluency"],
            stats["avg_cultural"],
            stats["avg_terminology"],
        ]

        fig = go.Figure()
        fig.add_trace(go.Scatterpolar(
            r=values + [values[0]],
            theta=categories + [categories[0]],
            fill="toself",
            name="Average Score",
            line_color="#4F8BF9",
        ))
        fig.update_layout(
            polar=dict(radialaxis=dict(visible=True, range=[0, 5])),
            showlegend=False,
            height=350,
            margin=dict(t=30, b=30),
        )
        st.plotly_chart(fig, width='stretch')

    with col2:
        # Score by content type
        st.subheader("Score by Content Type")
        if by_type:
            type_names = [CONTENT_TYPES.get(r["content_type"], r["content_type"]) for r in by_type]
            type_scores = [r["avg_score"] for r in by_type]
            type_counts = [r["count"] for r in by_type]

            fig2 = go.Figure()
            fig2.add_trace(go.Bar(
                x=type_names,
                y=type_scores,
                text=[f"{s}/5.0<br>({c} samples)" for s, c in zip(type_scores, type_counts)],
                textposition="auto",
                marker_color=["#4F8BF9", "#36B37E", "#FFAB00", "#FF5630"],
            ))
            fig2.update_layout(
                yaxis=dict(range=[0, 5.5], title="Average Score"),
                height=350,
                margin=dict(t=30, b=30),
            )
            st.plotly_chart(fig2, width='stretch')

    # Score distribution over time
    if records:
        st.subheader("Score Trend")
        scores_over_time = [
            {"index": i + 1, "score": r["overall_score"]}
            for i, r in enumerate(reversed(records))
            if r["overall_score"] > 0
        ]
        if scores_over_time:
            fig3 = px.line(
                scores_over_time,
                x="index",
                y="score",
                markers=True,
                labels={"index": "Translation #", "score": "Overall Score"},
            )
            fig3.update_layout(
                yaxis=dict(range=[0, 5.5]),
                height=300,
                margin=dict(t=10, b=30),
            )
            st.plotly_chart(fig3, width='stretch')

    # Common issues
    if common_issues:
        st.subheader("Top Issues")
        for issue, count in common_issues:
            st.markdown(f"- **[{count}x]** {issue}")


# =============================================
# Page 3: History
# =============================================
elif page == "📋 History":
    st.title("📋 Translation History")

    conn = get_db()
    records = get_all_records(conn)
    conn.close()

    if not records:
        st.info("No translations yet. Try the Translation Workspace first!")
        st.stop()

    # Filters
    filter_col1, filter_col2 = st.columns([1, 1])
    with filter_col1:
        type_filter = st.selectbox(
            "Filter by type",
            ["All"] + list(CONTENT_TYPES.values()),
        )
    with filter_col2:
        issue_filter = st.selectbox(
            "Filter by status",
            ["All", "With Issues", "No Issues"],
        )

    # Apply filters
    filtered = records
    if type_filter != "All":
        type_key = [k for k, v in CONTENT_TYPES.items() if v == type_filter]
        if type_key:
            filtered = [r for r in filtered if r["content_type"] == type_key[0]]

    if issue_filter == "With Issues":
        filtered = [r for r in filtered if r["had_issues"]]
    elif issue_filter == "No Issues":
        filtered = [r for r in filtered if not r["had_issues"]]

    st.caption(f"Showing {len(filtered)} of {len(records)} records")

    # Display records
    for r in filtered:
        score = r["overall_score"]
        icon = "🟢" if score >= 4.5 else "🟡" if score >= 3.5 else "🔴"
        type_label = CONTENT_TYPES.get(r["content_type"], r["content_type"])

        with st.expander(
            f"{icon} {score}/5.0 — {type_label} — {r['created_at'][:16]}"
        ):
            st.markdown("**English Source:**")
            st.text(r["source_text"])

            st.markdown("**Chinese Translation:**")
            st.info(r["translated_text"])

            # Scores
            s1, s2, s3, s4 = st.columns(4)
            s1.metric("Accuracy", f"{r['accuracy_score']}/5")
            s2.metric("Fluency", f"{r['fluency_score']}/5")
            s3.metric("Cultural", f"{r['cultural_score']}/5")
            s4.metric("Terminology", f"{r['terminology_score']}/5")

            if r["summary"]:
                st.caption(f"📝 {r['summary']}")

            if r["had_issues"] and r["fixed_text"]:
                st.markdown("**Fixed Translation:**")
                st.success(r["fixed_text"])


# =============================================
# Page 4: Batch Processing
# =============================================
elif page == "📁 Batch Processing":
    st.title("📁 Batch Processing")
    st.markdown("Upload a CSV file to translate multiple items at once.")

    st.markdown("""
    **CSV Format Requirements:**
    - Column 1: `content_type` — one of: hotel_faq, car_rental, city_guide, transport
    - Column 2: `source_text` — English text to translate
    
    Example:
    """)
    st.code("content_type,source_text\nhotel_faq,\"The pool is open from 7 AM to 10 PM.\"\ncar_rental,\"Return the car with a full tank.\"", language="csv")

    uploaded_file = st.file_uploader("Upload CSV", type=["csv"])

    if uploaded_file:
        # Parse CSV
        content = uploaded_file.read().decode("utf-8")
        reader = csv.DictReader(io.StringIO(content))
        rows = list(reader)

        st.info(f"Found {len(rows)} items in the CSV.")

        if st.button("🚀 Process All", type="primary"):
            conn = get_db()
            progress = st.progress(0)
            results_container = st.container()

            for i, row in enumerate(rows):
                content_type = row.get("content_type", "").strip()
                source_text = row.get("source_text", "").strip()

                if content_type not in CONTENT_TYPES or not source_text:
                    with results_container:
                        st.warning(f"Row {i+1}: Skipped (invalid content_type or empty text)")
                    continue

                with results_container:
                    st.markdown(f"**[{i+1}/{len(rows)}]** {source_text[:60]}...")

                try:
                    translation = translate(source_text, content_type, client)
                    eval_result = evaluate(source_text, translation, content_type, client)
                    fix_result = fix(source_text, translation, eval_result, client)
                    save_record(conn, source_text, translation, content_type, eval_result, fix_result)

                    score = eval_result.get("overall_score", 0)
                    with results_container:
                        st.markdown(f"  Score: {score}/5.0 ✓")
                except Exception as e:
                    with results_container:
                        st.error(f"  Failed: {e}")

                progress.progress((i + 1) / len(rows))

            conn.close()
            st.success("Batch processing complete! Check the Dashboard for results.")
