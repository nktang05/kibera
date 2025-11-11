import streamlit as st
import pandas as pd
import sqlite3
import numpy as np

# ---------------------------------------------------
# DATABASE CONNECTION
# ---------------------------------------------------
DB_PATH = "csv4db/kibera_survey.sqlite"

def get_connection():
    return sqlite3.connect(DB_PATH, check_same_thread=False)

con = get_connection()

# list columns from master table
master_columns = pd.read_sql("PRAGMA table_info(master);", con)["name"].tolist()

# ---------------------------------------------------
# STREAMLIT LAYOUT
# ---------------------------------------------------
st.set_page_config(page_title="Kibera Survey Query Tool", layout="wide")

st.title("Kibera Survey Query Tool")

# Codebook link
st.markdown(
    """
    <a href="https://docs.google.com/spreadsheets/d/.../edit"
       target="_blank"
       style="background-color:#007bff; padding:10px 18px; color:white; text-decoration:none; border-radius:5px;">
       Kibera Codebook
    </a>
    """,
    unsafe_allow_html=True
)

st.markdown("---")

# ---------------------------------------------------
# SIDEBAR — GROUPED QUERY
# ---------------------------------------------------
st.sidebar.header("Grouped Query")

group_col = st.sidebar.selectbox("Group By:", master_columns)
run_group = st.sidebar.button("Run Grouped Query")

# Placeholder for grouped results
grouped_area = st.empty()


# ---------------------------------------------------
# SIDEBAR — CUSTOM SQL
# ---------------------------------------------------
st.sidebar.markdown("---")
st.sidebar.header("Pivot Table (Custom Query Only)")

enable_pivot = st.sidebar.checkbox("Enable Pivot Table", value=False)

pivot_row = None
pivot_col = None


# ---------------------------------------------------
# MAIN PAGE — CUSTOM SQL INPUT
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

    # Download
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

        # CSV download
        st.download_button(
            "Download Custom Results CSV",
            custom_df.to_csv(index=False),
            file_name="custom_query_results.csv",
            mime="text/csv"
        )

    except Exception as e:
        custom_results_area.error(f"Error: {e}")


# ---------------------------------------------------
# PIVOT TABLE (CUSTOM QUERY ONLY)
# ---------------------------------------------------
if enable_pivot and run_custom and custom_df is not None:

    st.subheader("Pivot Table")

    # Only allow pivot if results exist
    cols = custom_df.columns.tolist()

    pivot_row = st.sidebar.selectbox("Pivot Row:", cols)
    pivot_col = st.sidebar.selectbox("Pivot Column:", cols)
    run_pivot = st.sidebar.button("Generate Pivot Table")

    if run_pivot:

        df = custom_df.copy()

        # Expand summarized data if count column exists
        if "count" in df.columns:
            df = df.loc[df.index.repeat(df["count"].astype(int))]

        # Pivot using counts
        pivot_table = (
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

        pivot_table["Total"] = pivot_table.sum(axis=1)
        total_row = pivot_table.sum(axis=0).to_frame().T
        total_row.index = ["Total"]

        pivot_table = pd.concat([pivot_table, total_row])

        pivot_area.dataframe(pivot_table)

        # Download pivot csv
        pivot_download_area.download_button(
            "Download Pivot CSV",
            pivot_table.to_csv(),
            file_name="pivot_table.csv",
            mime="text/csv"
        )