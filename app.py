import streamlit as st
import sqlite3
import pandas as pd

# ---------------------------------------------------
# CONNECT TO DATABASE
# ---------------------------------------------------
DB_PATH = "csv4db/kibera_survey.sqlite"
con = sqlite3.connect(DB_PATH)

# Load master column list safely
try:
    master_columns = pd.read_sql("PRAGMA table_info(master);", con)["name"].tolist()
except:
    master_columns = []


# ---------------------------------------------------
# PAGE SETTINGS
# ---------------------------------------------------
st.set_page_config(page_title="Kibera Survey Query Tool", layout="wide")

st.title("Kibera User Interface")
st.write("Nicole Tang — 2025")

# ---------------------------------------------------
# SHOW DATABASE TABLE NAMES
# ---------------------------------------------------
st.subheader("Available Tables in Database")

tables_df = pd.read_sql(
    "SELECT name FROM sqlite_master WHERE type='table';",
    con
)
table_names = tables_df["name"].tolist()

if len(table_names) > 0:
    cols = st.columns(len(table_names))
    for i, t in enumerate(table_names):
        cols[i].markdown(
            f"""
            <div style="
                padding:8px 12px;
                background-color:#f0f2f6;
                border-radius:6px;
                text-align:center;
                font-weight:600;
                border:1px solid #ddd;">
                {t}
            </div>
            """,
            unsafe_allow_html=True
        )

st.download_button(
    "Download Table List",
    tables_df.to_csv(index=False),
    file_name="database_tables.csv",
    mime="text/csv"
)

st.markdown("---")


# ---------------------------------------------------
# SIDEBAR — GROUPED QUERY
# ---------------------------------------------------
st.sidebar.header("Grouped Query")

group_col = st.sidebar.selectbox("Group By:", master_columns)
run_group = st.sidebar.button("Run Grouped Query")

grouped_area = st.empty()

# ---------------------------------------------------
# SIDEBAR — PIVOT SETTINGS
# ---------------------------------------------------
st.sidebar.markdown("---")
st.sidebar.header("Pivot Table (Custom Query Only)")

enable_pivot = st.sidebar.checkbox("Enable Pivot Table", value=False)

# ---------------------------------------------------
# MAIN — CUSTOM SQL
# ---------------------------------------------------
st.subheader("Custom SQL Query")

custom_sql = st.text_area(
    "Enter SQL Query:",
    value="SELECT * FROM master LIMIT 10;",
    height=150
)

run_custom = st.button("Run Custom Query")
custom_results_area = st.empty()

pivot_area = st.empty()
pivot_download_area = st.empty()

# ---------------------------------------------------
# GROUPED QUERY EXECUTION
# ---------------------------------------------------
if run_group:
    sql = f"""
        SELECT {group_col} AS value, COUNT(*) AS count
        FROM master
        GROUP BY {group_col};
    """

    grouped_df = pd.read_sql(sql, con)
    grouped_area.dataframe(grouped_df)

    st.sidebar.download_button(
        "Download Grouped CSV",
        grouped_df.to_csv(index=False),
        file_name=f"grouped_{group_col}.csv",
        mime="text/csv"
    )


# ---------------------------------------------------
# CUSTOM SQL EXECUTION
# ---------------------------------------------------
custom_df = None

if run_custom:
    try:
        custom_df = pd.read_sql(custom_sql, con)
        custom_results_area.dataframe(custom_df)

        st.download_button(
            "Download Custom Results CSV",
            custom_df.to_csv(index=False),
            file_name="custom_query_results.csv",
            mime="text/csv"
        )

    except Exception as e:
        custom_results_area.error(f"Error: {e}")


# ---------------------------------------------------
# PIVOT TABLE GENERATION
# ---------------------------------------------------
if enable_pivot and run_custom and custom_df is not None:

    st.subheader("Pivot Table From Custom Query")

    cols = custom_df.columns.tolist()

    pivot_row = st.sidebar.selectbox("Pivot Row:", cols)
    pivot_col = st.sidebar.selectbox("Pivot Column:", cols)
    run_pivot = st.sidebar.button("Generate Pivot Table")

    if run_pivot:

        df = custom_df.copy()

        # Expand summarized count data
        if "count" in df.columns:
            df = df.loc[df.index.repeat(df["count"].astype(int))]

        # Correct pivot — always counts rows
        pivot = (
            df.groupby([pivot_row, pivot_col])
              .size()
              .reset_index(name="count")
              .pivot_table(
                  index=pivot_row,
                  columns=pivot_col,
                  values="count",
                  fill_value=0
              )
        )

        pivot["Total"] = pivot.sum(axis=1)
        total_row = pivot.sum(axis=0).to_frame().T
        total_row.index = ["Total"]

        pivot = pd.concat([pivot, total_row])

        pivot_area.dataframe(pivot)

        pivot_download_area.download_button(
            "Download Pivot CSV",
            pivot.to_csv(),
            file_name="pivot_table.csv",
            mime="text/csv"
        )
